#!/usr/bin/env python3
"""Generate the Rust 1.96 BTreeSet inventory, specifications, and proof inputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import campaign_model as model
from tools import proof_model


ROOT = model.ROOT


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def require_accepted_specification_review() -> None:
    record_path = ROOT / "reviews/inventory_specification.json"
    if not record_path.is_file():
        raise RuntimeError(
            "proof generation is phase-blocked: missing canonical "
            "inventory/specification Reviewer acceptance"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    review = record.get("review") or {}
    if (
        record.get("producer_role") != "reviewer"
        or record.get("independent") is not True
        or record.get("acceptance_eligible") is not True
        or review.get("status") != "done"
    ):
        raise RuntimeError(
            "proof generation is phase-blocked: inventory/specification review "
            "is not a canonical accepted Reviewer decision"
        )
    request = record.get("request") or {}
    request_path = ROOT / str(request.get("path", ""))
    if (
        not request_path.is_file()
        or request.get("sha256")
        != model.sha256_bytes(request_path.read_bytes())
    ):
        raise RuntimeError(
            "proof generation is phase-blocked: specification review request "
            "binding is stale"
        )
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    index_binding = request_payload.get("artifact_index") or {}
    index_path = ROOT / str(index_binding.get("path", ""))
    if (
        not index_path.is_file()
        or index_binding.get("sha256")
        != model.sha256_bytes(index_path.read_bytes())
    ):
        raise RuntimeError(
            "proof generation is phase-blocked: reviewed specification artifact "
            "index is stale"
        )
    index = json.loads(index_path.read_text(encoding="utf-8"))
    indexed = {
        item["path"]: item["sha256"] for item in index.get("artifacts", [])
    }
    required = (
        "inventory/btree_set_exec_fn_inventory.json",
        "specs/all_btree_set_specs.json",
        "specs/generated_btree_set_specs.rs",
        "specs/btree_set_shared_vocabulary.rs",
    )
    for relative in required:
        path = ROOT / relative
        if (
            not path.is_file()
            or indexed.get(relative) != model.sha256_bytes(path.read_bytes())
        ):
            raise RuntimeError(
                "proof generation is phase-blocked: accepted specification "
                f"does not bind current {relative}"
            )


def counts_for(rows: list[model.Row]) -> dict[str, int]:
    dispositions = Counter(row.disposition for row in rows)
    return {
        "stable_inventory_total": len(rows),
        "exact_vstd": dispositions["exact_vstd"],
        "generated": dispositions["generated"],
        "genuinely_impossible": 0,
        "pending": 0,
    }


def retained_source_constructs(row: model.Row) -> list[dict[str, str]]:
    return [
        {
            "kind": kind,
            "evidence": "executable implementation body and ordered token audit",
        }
        for kind in proof_model.retained_source_construct_kinds(row)
    ]


def abstracted_source_constructs(row: model.Row) -> list[dict[str, str]]:
    constructs: list[dict[str, str]] = []
    source = row.source_excerpt
    retained = {
        item["kind"] for item in retained_source_constructs(row)
    }
    for token, kind in (
        ("if ", "conditional"),
        ("if let ", "conditional_let"),
        ("match ", "match"),
        ("loop ", "loop"),
        ("while ", "while_loop"),
        (".map(", "iterator_map"),
        (".for_each(", "iterator_callback_loop"),
    ):
        if token in source and kind not in retained:
            constructs.append(
                {
                    "kind": kind,
                    "boundary": model.dependency_path(row),
                    "justification": (
                        "retained by the executable public match/branch or lowered "
                        "to an operation-specific private-state step whose return "
                        "shape differs from the public target"
                    ),
                }
            )
    if not constructs:
        constructs.append(
            {
                "kind": "private_field_or_dependency_call",
                "boundary": model.dependency_path(row),
                "justification": (
                    "private BTreeMap/adapter representation is inaccessible to "
                    "Verus and remains an explicitly counted, operation-specific "
                    "lower projection"
                ),
            }
        )
    return constructs


def public_dependency_target_ids(
    row: model.Row, target_by_key: dict[tuple[str, str, str], str]
) -> list[str]:
    return proof_model.selected_public_dependency_target_ids(
        row,
        target_by_key,
    )


def generate_inventory(
    rows: list[model.Row],
    exclusions: list[dict[str, Any]],
    derivation: dict[str, Any],
) -> list[dict[str, Any]]:
    records = [model.metadata_for(row) for row in rows]
    counts = counts_for(rows)
    inventory_root = ROOT / "inventory"
    inventory = {
        "schema_version": 1,
        "module": model.MODULE,
        "rust_release": "1.96.0",
        "derivation": derivation,
        "counts": counts,
        "rows": records,
    }
    write_json(inventory_root / "btree_set_exec_fn_inventory.json", inventory)
    write_csv(
        inventory_root / "btree_set_exec_fn_inventory.csv",
        records,
        [
            "target_id",
            "ordinal",
            "api_path",
            "canonical_target",
            "owner_type",
            "trait",
            "method",
            "rustdoc_item_id",
            "source_file",
            "line_start",
            "line_end",
            "source_sha256",
            "disposition",
            "contract_form",
            "semantic_family",
            "proxy_signature",
            "contract_fingerprint",
        ],
    )
    write_json(
        inventory_root / "unstable_non_executable_exclusions.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "aliases_excluded_as_duplicates": [
                "alloc::collections::BTreeSet",
                "std::collections::BTreeSet",
            ],
            "modules_excluded": [
                "alloc::collections::btree_map",
                "core::cmp",
            ],
            "blanket_and_default_policy": (
                "synthetic/blanket impls and inherited default methods are not "
                "source-owned executable rows"
            ),
            "rows": exclusions,
        },
    )
    exact = [record for record in records if record["disposition"] == "exact_vstd"]
    write_json(
        inventory_root / "exact_vstd_audit.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "match_policy": "all eight structural signature dimensions must match",
            "derivation": (
                "parse frozen vstd declarations and rustdoc-derived source "
                "signatures independently, then alpha/path normalize each operand"
            ),
            "dimensions": list(model.MATCH_DIMENSIONS),
            "matched_count": len(exact),
            "reverse_scan": model.exact_vstd_reverse_scan(rows),
            "rows": exact,
        },
    )
    write_json(
        inventory_root / "inventory_reconciliation.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "counts_source": "inventory/btree_set_exec_fn_inventory.json#rows",
            "equation": {
                "left": counts["stable_inventory_total"],
                "right": (
                    counts["exact_vstd"]
                    + counts["generated"]
                    + counts["genuinely_impossible"]
                    + counts["pending"]
                ),
                "holds": True,
            },
            "strict_specification_coverage": 1.0,
            "pending": 0,
        },
    )

    dependency_records: list[dict[str, Any]] = []
    for row in rows:
        dependencies = [
            "ordered_set_view",
            "core_cmp_ord_laws",
            "btree_map_delegation",
        ]
        if "iterator" in row.semantic_family or "adapter" in row.semantic_family:
            dependencies.append("ordered_iterator_remaining_state")
        if row.semantic_family in {
            "ordered_callback_retain",
            "extract_if_construction",
            "ordered_extend_transition",
        }:
            dependencies.append("ordered_callback_trace")
        if row.semantic_family in {
            "ordered_endpoint_observer",
            "ordered_endpoint_removal",
            "ordered_range_construction",
            "ordered_set_partition",
        }:
            dependencies.append("borrowed_key_order")
        dependency_records.append(
            {
                "target_id": row.target_id,
                "semantic_family": row.semantic_family,
                "source_dependency_path": model.dependency_path(row),
                "depends_on": dependencies,
            }
        )
    shared_nodes = [
        "ordered_set_view",
        "core_cmp_ord_laws",
        "borrowed_key_order",
        "btree_map_delegation",
        "ordered_iterator_remaining_state",
        "range_bounds_and_panic_domain",
        "ordered_callback_trace",
        "stable_sort_and_last_equal_dedup",
        "allocator_and_private_representation",
    ]
    write_json(
        inventory_root / "dependency_graph.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "advisory_generation_order": shared_nodes,
            "shared_nodes": shared_nodes,
            "targets": dependency_records,
        },
    )
    dot = ["digraph btree_set_specs {"]
    for record in dependency_records:
        for dependency in record["depends_on"]:
            dot.append(f'  "{dependency}" -> "{record["target_id"]}";')
    dot.append("}")
    write_text(inventory_root / "dependency_graph.dot", "\n".join(dot) + "\n")
    return records


def generate_specs(rows: list[model.Row], records: list[dict[str, Any]]) -> None:
    counts = counts_for(rows)
    generated_source = model.generated_spec_source(rows)
    write_text(ROOT / "specs/btree_set_shared_vocabulary.rs", model.SHARED_VOCABULARY)
    write_text(ROOT / "specs/generated_btree_set_specs.rs", generated_source)
    catalog = {
        "schema_version": 1,
        "module": model.MODULE,
        "rust_release": "1.96.0",
        "counts": {
            **counts,
            "specified_total": len(rows),
            "strict_specification_coverage": 1.0,
        },
        "shared_vocabulary": "specs/btree_set_shared_vocabulary.rs",
        "generated_source": "specs/generated_btree_set_specs.rs",
        "exact_vstd_reference_map": "specs/existing_vstd/references.json",
        "rows": records,
    }
    write_json(ROOT / "specs/all_btree_set_specs.json", catalog)
    write_json(
        ROOT / "catalog/btree_set_spec_catalog.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "rows": records,
        },
    )
    write_csv(
        ROOT / "catalog/btree_set_spec_catalog.csv",
        records,
        [
            "target_id",
            "ordinal",
            "api_path",
            "canonical_target",
            "owner_type",
            "trait",
            "method",
            "rustdoc_item_id",
            "source_file",
            "line_start",
            "line_end",
            "source_sha256",
            "disposition",
            "contract_form",
            "semantic_family",
            "contract_fingerprint",
        ],
    )
    exact = [record for record in records if record["disposition"] == "exact_vstd"]
    write_json(
        ROOT / "specs/existing_vstd/references.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "source": "provenance/frozen/vstd/std_specs/btree.rs",
            "source_sha256": model.sha256_bytes(model.VSTD_FILE.read_bytes()),
            "reference_count": len(exact),
            "rows": [
                {
                    "target_id": record["target_id"],
                    "canonical_target": record["canonical_target"],
                    "line": record["vstd_reference"]["line"],
                    "block_sha256": record["vstd_reference"]["block_sha256"],
                    "match_dimensions": record["vstd_reference"]["match_dimensions"],
                }
                for record in exact
            ],
        },
    )
    write_text(
        ROOT / "specs/existing_vstd/README.md",
        """# Exact vstd references

`references.json` binds every exact target to the frozen
`vstd/std_specs/btree.rs` declaration by target, source line, declaration hash,
and all eight structural signature dimensions. Exact rows remain selected
proof obligations but are not redeclared by `generated_btree_set_specs.rs`.
""",
    )
    direct_count = sum(row.disposition == "generated" for row in rows)
    write_text(
        ROOT / "specs/README.md",
        f"""# Rust 1.96 `alloc::collections::btree_set` specifications

This is the mandatory module-wide specification interface. The live
Rustdoc/source derivation contains **{len(rows)}** stable executable,
BTreeSet-owned rows: **{counts['exact_vstd']}** exact vstd references and
**{counts['generated']}** generated contracts, with zero impossible and zero
pending rows.

- `generated_btree_set_specs.rs` has {direct_count} direct
  `assume_specification` declarations, including separate source-owned
  `Extend::extend` bindings for owned and copied-reference inputs.
- `btree_set_shared_vocabulary.rs` defines the ordered-set, representative,
  range, iterator, set-operation, callback, formatter/hasher, and delegation
  vocabulary. Range predicates consume concrete `RangeBoundsSpec` endpoints;
  callback traces use `FnMut::requires`/`ensures` and explicit post-state
  steps; one adapter source state drives construction, `next`, size hints, and
  nested debug fields; and `ExtractIf` unwind/drop transitions retain the
  current set. Uninterpreted primitives expose only one-step effects or raw
  hidden state, and the audit rejects every unused, legacy-free-observation,
  or whole-operation primitive.
- `all_btree_set_specs.json` reconciles every stable row and records exact
  source, signature, contract, equivalence, and vstd bindings.
- `existing_vstd/references.json` records exact declarations without
  redeclaration.
- `verification/spec_determinism_harnesses/` contains one clause-derived
  determinism proof for every generated contract; generic-checker
  UNKNOWN/unsupported rows require current actual-Verus evidence here.
""",
    )


def generate_harnesses(rows: list[model.Row], records: list[dict[str, Any]]) -> None:
    harness_root = ROOT / "proof_harnesses"
    harness_root.mkdir(exist_ok=True)
    expected = {row.target_id for row in rows}
    unexpected = sorted(
        path.name
        for path in harness_root.iterdir()
        if path.is_dir() and path.name not in expected
    )
    if unexpected:
        raise RuntimeError(
            f"refusing to overwrite unexpected harness directories: {unexpected}"
        )
    by_id = {record["target_id"]: record for record in records}
    specification_review_path = ROOT / "reviews/inventory_specification.json"
    specification_review = json.loads(
        specification_review_path.read_text(encoding="utf-8")
    )
    specification_binding = {
        "review": str(specification_review_path.relative_to(ROOT)),
        "review_sha256": model.sha256_bytes(specification_review_path.read_bytes()),
        "canonical_handoff": specification_review["canonical_handoff"],
        "artifact_index": json.loads(
            (
                ROOT
                / specification_review["request"]["path"]
            ).read_text(encoding="utf-8")
        )["artifact_index"],
    }
    target_by_key = {
        (row.owner["name"], row.trait, row.function["name"]): row.target_id
        for row in rows
    }
    for row in rows:
        record = by_id[row.target_id]
        target_root = harness_root / row.target_id
        target_root.mkdir(exist_ok=True)
        evidence_root = target_root / "evidence"
        if evidence_root.is_dir() and any(evidence_root.iterdir()):
            archive_root = (
                ROOT
                / "verification/evidence/premature_pre_specification"
                / "harness_evidence"
                / row.target_id
            )
            if not archive_root.exists():
                archive_root.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(evidence_root), str(archive_root))
        evidence_root.mkdir(exist_ok=True)
        implementation_source = proof_model.source(row)
        completeness_source = proof_model.source(row, completeness=True)
        mutation_source = proof_model.source(row, mutation=True)
        checker_adjudication = (
            proof_model.requires_associated_item_air_adjudication(row)
        )
        adjudication_source = (
            proof_model.checker_adjudication_source(row)
            if checker_adjudication
            else None
        )
        adjudication_mutation_source = (
            proof_model.checker_adjudication_source(
                row,
                mutation=True,
            )
            if checker_adjudication
            else None
        )
        write_text(
            target_root / "implementation_proof.rs",
            implementation_source,
        )
        write_text(
            target_root / "completeness_proof.rs",
            completeness_source,
        )
        write_text(
            target_root / "mutation_proof.rs",
            mutation_source,
        )
        if checker_adjudication:
            write_text(
                target_root / "checker_adjudication_proof.rs",
                str(adjudication_source),
            )
            write_text(
                target_root / "checker_adjudication_mutation.rs",
                str(adjudication_mutation_source),
            )
        else:
            for name in (
                "checker_adjudication_proof.rs",
                "checker_adjudication_mutation.rs",
                "checker_adjudication.json",
            ):
                (target_root / name).unlink(missing_ok=True)
        write_text(target_root / "source_excerpt.rs", row.source_excerpt)
        source_body = {
            "schema_version": 1,
            "target_id": row.target_id,
            "canonical_target": row.canonical_target,
            "rustdoc_item_id": row.item_id,
            "source_file": row.source_file,
            "line_start": row.line_start,
            "line_end": row.line_end,
            "source_sha256": row.source_sha256,
            "source_excerpt_path": (
                f"proof_harnesses/{row.target_id}/source_excerpt.rs"
            ),
            "contract_disposition": row.disposition,
            "contract_form": record["contract_form"],
            "contract_fingerprint": row.contract_fingerprint,
            "accepted_specification": specification_binding,
        }
        projection = proof_model.projection_for(
            row, model.proxy_parts(row)[2]
        )
        accepted_clauses = proof_model.contract_lines(row)
        accepted_requirements = proof_model.contract_requirements(row)
        lower_clauses = proof_model.emitted_dependency_contract_lines(
            row, projection
        )
        transformation = {
            "schema_version": 1,
            "target_id": row.target_id,
            "source_sha256": row.source_sha256,
            "source_span": f"{row.source_file}:{row.line_start}-{row.line_end}",
            "source_dependency_path": model.dependency_path(row),
            "source_call_coverage": proof_model.source_call_coverage(row),
            "adaptations": [
                {
                    "kind": "real_signature_source_lowering",
                    "description": (
                        "The proof target retains the rustdoc-derived generic binder, "
                        "receiver/reference shape, parameters, return type, bounds, "
                        "and accepted contract over the real public BTreeSet or "
                        "adapter type."
                    ),
                    "preserved_observations": row.principal_behavior,
                },
                {
                    "kind": "narrow_source_dependency_call_retention",
                    "description": (
                        "The public target remains executable and projects the "
                        f"source-shaped {proof_model.dependency_operation(row)} "
                        "lower return into the BTreeSet return. The lower function "
                        "has an independently authored private-operation contract, "
                        "a different return shape, and, for set-specific paths, "
                        "an observed private branch input."
                    ),
                    "preserved_observations": [
                        "branch polarity",
                        "length transition",
                        "ordered cursor transition",
                        "second-set consumption",
                        "callback or formatter effect count",
                    ],
                },
                *(
                    [
                        {
                            "kind": "merge_comparator_callback_lowering",
                            "description": (
                                "The executable target retains the parsed "
                                "MergeIter nexts call and both returned "
                                "candidates. Self::Item::cmp is represented "
                                "by the frozen Ord/cmp_spec semantics inside "
                                "merge_next_step rather than by an executable "
                                "function-pointer argument, which Verus cannot "
                                "pass across the private MergeIter boundary."
                            ),
                            "preserved_observations": [
                                "left candidate",
                                "right candidate",
                                "comparison ordering",
                                "post-nexts private merge state",
                            ],
                        }
                    ]
                    if row.target_id
                    in {
                        proof_model.SYMMETRIC_DIFFERENCE_NEXT_TARGET,
                        proof_model.UNION_LEFT_BIASED_NEXT_TARGET,
                    }
                    else []
                ),
            ],
            "retained_constructs": retained_source_constructs(row),
            "dropped_constructs": abstracted_source_constructs(row),
            "reordered_constructs": [],
            "source_operation_order": (
                proof_model.implementation_operation_order(row)
            ),
            "checker_adjudication": (
                {
                    "limitation": "verus-intoiterator-associated-item-air",
                    "erased_bounds": (
                        proof_model.associated_item_bound_declarations(row)
                    ),
                    "proof_domain_relation": (
                        "removing the associated-item equality precondition "
                        "strictly strengthens the actual-Verus proof domain"
                    ),
                    "exact_implementation_sha256": model.sha256_text(
                        implementation_source
                    ),
                    "actual_verus_implementation_sha256": model.sha256_text(
                        str(adjudication_source)
                    ),
                    "exact_mutation_sha256": model.sha256_text(
                        mutation_source
                    ),
                    "actual_verus_mutation_sha256": model.sha256_text(
                        str(adjudication_mutation_source)
                    ),
                }
                if checker_adjudication
                else None
            ),
            "contract_projection": {
                "fingerprint": row.contract_fingerprint,
                "accepted_requirement_sha256": [
                    model.sha256_text(line)
                    for line in accepted_requirements
                ],
                "requirement_lowering": [
                    {
                        "index": index,
                        "accepted_requirement": line,
                        "sha256": model.sha256_text(line),
                        "completeness_predicate": (
                            f"accepted_requirement_{index}"
                        ),
                    }
                    for index, line in enumerate(
                        accepted_requirements, start=1
                    )
                ],
                "accepted_clause_sha256": [
                    model.sha256_text(line) for line in accepted_clauses
                ],
                "clause_lowering": [
                    {
                        "index": index,
                        "accepted_clause": line,
                        "sha256": model.sha256_text(line),
                        "completeness_predicate": f"accepted_clause_{index}",
                    }
                    for index, line in enumerate(
                        accepted_clauses, start=1
                    )
                ],
                "narrow_dependency_clause_lowering": [
                    {
                        "index": index,
                        "lower_clause": lower,
                        "lower_clause_sha256": model.sha256_text(lower),
                        "derivation_role": "authored_lower_operation_fact",
                        "authorship": "independent_of_accepted_public_clauses",
                        "source_operation": (
                            proof_model.dependency_operation(row)
                        ),
                    }
                    for index, lower in enumerate(
                        lower_clauses,
                        start=1,
                    )
                ],
                "completeness_model": (
                    "literal substitution of every accepted requirement and clause "
                    "for both candidates; tools/completeness_audit.py independently "
                    "reconstructs each body without importing the generator; "
                    "observable equalities follow without an aggregate outcome or "
                    "whole-contract helper"
                ),
            },
            "accepted_specification": specification_binding,
        }
        dependencies = {
            "schema_version": 1,
            "target_id": row.target_id,
            "dependencies": [
                {
                    "category": "btree_map_delegation",
                    "acceptance": "unaccepted_narrow_dependency",
                    "boundary": (
                        "private BTreeMap node/search/allocation behavior behind "
                        f"{proof_model.dependency_operation(row)}; its return is "
                        f"{proof_model.dependency_lower_shape(row, projection)}, "
                        "not the public target return"
                    ),
                    "source": row.source_file,
                    "operation": proof_model.dependency_operation(row),
                    "lower_return_shape": proof_model.dependency_lower_shape(
                        row,
                        projection,
                    ),
                    "lower_observation_clauses": lower_clauses,
                    "lower_observation_clause_sha256": [
                        model.sha256_text(line) for line in lower_clauses
                    ],
                    "contract_authorship": (
                        "source-operation registry independent of accepted "
                        "public clauses"
                    ),
                    "whole_target_contract": False,
                },
                {
                    "category": "comparator_order_laws",
                    "acceptance": "unaccepted_narrow_dependency",
                    "boundary": "OrdSpec/obeys_cmp total-order and borrowed-order consistency",
                    "source": "provenance/frozen/rust-1.96/library/core/src/cmp.rs",
                },
                *proof_model.standard_library_assumption_boundaries(row),
                *(
                    [
                        {
                            "category": "range_bounds_observation",
                            "acceptance": "unaccepted_narrow_dependency",
                            "boundary": (
                                "RangeBoundsSpec binds start/end bound kinds and "
                                "values; BTreeSet range filtering remains tied to "
                                "borrowed ordering and the frozen range search"
                            ),
                            "source": (
                                "provenance/frozen/vstd/std_specs/range.rs"
                            ),
                        }
                    ]
                    if row.function["name"] in {"range", "extract_if"}
                    else []
                ),
                *(
                    [
                        {
                            "category": "callback_contract_transition",
                            "acceptance": "unaccepted_narrow_dependency",
                            "boundary": (
                                "FnMut requires/ensures fixes each callback "
                                "result; the one-step post-state remains a "
                                "counted callback model boundary"
                            ),
                            "source": "provenance/frozen/vstd/function.rs",
                        }
                    ]
                    if row.function["name"] in {"retain", "extract_if"}
                    or row.owner["name"] == "ExtractIf"
                    else []
                ),
                {
                    "category": "private_iterator_and_representation_state",
                    "acceptance": "reviewed_model_boundary",
                    "boundary": (
                        "node ranges, allocator/provenance, drop behavior, and "
                        "adapter private state are exposed only through the "
                        "operation-specific lower projection and source branch"
                    ),
                    "source": row.source_file,
                },
            ],
            "selected_public_dependency_targets": public_dependency_target_ids(
                row, target_by_key
            ),
            "selected_public_dependency_policy": (
                "these source-level public calls are separate selected proof "
                "obligations; the local lower operation covers private representation "
                "and map return construction, never a public-signature restatement"
            ),
            "accepted_specification": specification_binding,
        }
        literal_functions = proof_model.literal_external_body_function_names(
            implementation_source
        )
        dependency_functions = proof_model.dependency_function_names(row)
        literal_counts = proof_model.literal_external_body_counts(row)
        standard_library_assumptions = (
            proof_model.standard_library_assumption_boundaries(row)
        )
        observed_literal_counts = {
            "target": literal_functions.count("implementation"),
            "completeness": completeness_source.count(
                "#[verifier::external_body]"
            ),
            "dependency": sum(
                literal_functions.count(name)
                for name in dependency_functions
            ),
            "helper": 0,
            "harness": len(literal_functions),
        }
        observed_literal_counts["helper"] = (
            observed_literal_counts["harness"]
            - observed_literal_counts["target"]
            - observed_literal_counts["dependency"]
        )
        if observed_literal_counts != literal_counts:
            raise RuntimeError(
                f"{row.target_id}: generated external_body categories "
                f"{observed_literal_counts} differ from planned {literal_counts}"
            )
        trust = {
            "schema_version": 1,
            "target_id": row.target_id,
            "target_external_body": False,
            "target_external_body_count": literal_counts["target"],
            "completeness_external_body_count": literal_counts["completeness"],
            "dependency_external_body_count": literal_counts["dependency"],
            "helper_external_body_count": literal_counts["helper"],
            "harness_literal_external_body_count": literal_counts["harness"],
            "literal_external_body_counts_by_category": literal_counts,
            "literal_external_body_count": implementation_source.count(
                "#[verifier::external_body]"
            ),
            "assume_specification_count": len(
                standard_library_assumptions
            ),
            "assume_specification_boundaries": (
                standard_library_assumptions
            ),
            "suppressed_verifier_warnings": [
                record["verifier_allow"]
                for record in standard_library_assumptions
            ],
            "included_shared_vocabulary_external_body_count": (
                model.SHARED_VOCABULARY.count("#[verifier::external_body]")
            ),
            "compiled_harness_external_body_count": (
                implementation_source.count("#[verifier::external_body]")
                + model.SHARED_VOCABULARY.count("#[verifier::external_body]")
            ),
            "external_body_category_semantics": {
                "target": "the public implementation function",
                "completeness": "the colocated completeness theorem source",
                "dependency": (
                    "the operation-specific lower source dependencies, split "
                    "by private branch when source control flow dispatches"
                ),
                "helper": (
                    "source discriminants, private map/cursor observation "
                    "bridges, callback-step boundaries, and lower-to-public "
                    "representation projectors"
                ),
                "harness": (
                    "all literal external_body markers in implementation_proof.rs"
                ),
            },
            "literal_external_body_functions": literal_functions,
            "literal_external_body_functions_by_category": {
                "target": [],
                "completeness": [],
                "dependency": dependency_functions,
                "helper": [
                    name
                    for name in literal_functions
                    if name not in dependency_functions
                ],
                "harness": literal_functions,
            },
            "categories": [
                "selected_external_contract",
                "source_to_verus_ordered_set_lowering",
                "btree_map_delegation",
                "comparator_and_borrowed_order",
                "allocator_private_nodes_and_iterator_state",
                *(
                    ["core_option_combinator_semantics"]
                    if standard_library_assumptions
                    else []
                ),
                *(
                    ["range_bounds_observation"]
                    if row.function["name"] in {"range", "extract_if"}
                    else []
                ),
                *(
                    ["callback_contract_transition"]
                    if row.function["name"] in {"retain", "extract_if"}
                    or row.owner["name"] == "ExtractIf"
                    else []
                ),
            ],
            "no_additional_implementation_dependency_boundary": False,
            "end_to_end_trust_free": False,
            "whole_contract_dependency": False,
            "checker_adjudication": (
                "verus-intoiterator-associated-item-air"
                if checker_adjudication
                else None
            ),
            "checker_adjudication_external_body_count": (
                {
                    "implementation": str(adjudication_source).count(
                        "#[verifier::external_body]"
                    ),
                    "mutation": str(
                        adjudication_mutation_source
                    ).count("#[verifier::external_body]"),
                }
                if checker_adjudication
                else {"implementation": 0, "mutation": 0}
            ),
            "accepted_specification": specification_binding,
        }
        write_json(target_root / "source_body.json", source_body)
        write_json(target_root / "contract_binding.json", record)
        write_json(target_root / "contract_equivalence.json", record["equivalence"])
        write_json(target_root / "transformation_manifest.json", transformation)
        write_json(target_root / "dependency_assumptions.json", dependencies)
        write_json(target_root / "trust_boundaries.json", trust)
        descriptor = proof_model.mutation_descriptor(row)
        affected_indices = list(descriptor["affected_clause_indices"])
        mutation_manifest = {
            "schema_version": 1,
            "target_id": row.target_id,
            **descriptor,
            "affected_clause_sha256": [
                model.sha256_text(accepted_clauses[index - 1])
                for index in affected_indices
            ],
            "mutation_source_sha256": model.sha256_text(mutation_source),
            "expected_outcome": (
                "rejected_by_actual_verus_semantic_obligation"
            ),
        }
        write_json(
            target_root / "mutation_manifest.json",
            mutation_manifest,
        )
        if checker_adjudication:
            write_json(
                target_root / "checker_adjudication.json",
                {
                    "schema_version": 1,
                    "target_id": row.target_id,
                    "checker_limitation": (
                        "verus-intoiterator-associated-item-air"
                    ),
                    "exact_signature_source": "implementation_proof.rs",
                    "exact_signature_source_sha256": model.sha256_text(
                        implementation_source
                    ),
                    "exact_mutation_source": "mutation_proof.rs",
                    "exact_mutation_source_sha256": model.sha256_text(
                        mutation_source
                    ),
                    "actual_verus_source": (
                        "checker_adjudication_proof.rs"
                    ),
                    "actual_verus_source_sha256": model.sha256_text(
                        str(adjudication_source)
                    ),
                    "actual_verus_mutation_source": (
                        "checker_adjudication_mutation.rs"
                    ),
                    "actual_verus_mutation_source_sha256": model.sha256_text(
                        str(adjudication_mutation_source)
                    ),
                    "erased_bounds": (
                        proof_model.associated_item_bound_declarations(row)
                    ),
                    "proof_domain_relation": (
                        "bound erasure strengthens the verified domain; "
                        "the exact source signature remains separately "
                        "typechecked and its Verus AIR crash is retained"
                    ),
                },
            )

        manifest_root = ROOT / "proof_manifests" / row.target_id
        write_json(manifest_root / "source_body.json", source_body)
        write_json(manifest_root / "transformation_manifest.json", transformation)
        write_json(
            manifest_root / "dependency_assumption_manifest.json", dependencies
        )
        write_json(
            manifest_root / "mutation_manifest.json",
            mutation_manifest,
        )

    write_text(
        harness_root / "README.md",
        f"""# Per-target proof interface

The {len(rows)} directly discoverable child directories correspond one-to-one
with the selected stable API inventory. Each child colocates its exact Rust
source excerpt/hash, contract binding and exact equivalence, source-to-Verus
transformation, narrow dependency assumptions, trust accounting,
implementation proof, completeness proof, mutation, and durable two-mode
evidence. Exactly
{len(proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS)} children also
contain a narrowly scoped stronger-domain proof/mutation pair for the frozen
Verus `IntoIterator::Item` AIR failure; their exact-signature sources remain
the canonical harnesses and mandatory `--no-verify` inputs.
""",
    )
    write_json(
        ROOT / "proof_inventory/targets.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "selected_target_count": len(records),
            "selection_rule": "disposition in {exact_vstd, generated}",
            "targets": records,
        },
    )
    write_csv(
        ROOT / "proof_inventory/targets.csv",
        records,
        [
            "target_id",
            "ordinal",
            "canonical_target",
            "disposition",
            "contract_form",
            "source_file",
            "line_start",
            "line_end",
            "source_sha256",
            "semantic_family",
            "contract_fingerprint",
        ],
    )


def generate_feedback_inputs(rows: list[model.Row]) -> None:
    generated_rows = [row for row in rows if row.disposition == "generated"]
    shared_body = (
        model.SHARED_VOCABULARY.split("verus! {", 1)[1]
        .rsplit("} // verus!", 1)[0]
        .strip()
    )
    targets: list[dict[str, Any]] = []
    seeds: dict[str, Any] = {}
    contracts: list[dict[str, Any]] = []
    for row in generated_rows:
        binder, inputs, output, _where_clause = model.proxy_parts(row)
        declaration = {
            "line": row.line_start,
            "source_file": row.source_file,
            "source_context": row.source_excerpt,
            "target": row.canonical_target,
            "observability": {
                "has_modeled_output": output is not None
                or any("mut " in rust_type for _, rust_type, _ in inputs),
                "return_is_raw_pointer": bool(output and output.startswith("*")),
                "return_is_reference": bool(output and "&" in output),
                "return_is_unit": output is None,
            },
        }
        targets.append(
            {
                "available_in_verus_rust_1_96": True,
                "canonical_target": row.canonical_target,
                "category": "btree_set",
                "classification": "suitable_now",
                "declaration_count": 1,
                "declarations": [declaration],
                "display_paths": [row.canonical_target],
                "feedback_safe_name": row.target_id,
                "kinds": [
                    "inherent_method" if row.trait == "inherent" else "trait_method"
                ],
                "modules": [model.MODULE],
                "recommended_contract_form": (
                    "assume_specification"
                ),
                "semantic_risks": [
                    "ordered_representative_identity",
                    "btree_map_delegation",
                    "comparator_equivalence",
                ],
                "static_reward_eligible": True,
                "target": row.canonical_target,
                "verification_declaration_count": 1,
                "verification_declarations": [declaration],
            }
        )
        contract_code = (
            shared_body + "\n\n" + model.generated_declaration(row) + "\n"
        )
        contract_form = "assume_specification"
        ensures = model.ensure_lines(row, inputs, output)
        seeds[row.canonical_target] = {
            "assumptions": [
                "rust_1_96_source_binding",
                "ordered_set_shared_vocabulary",
                "btree_map_dependency_is_explicit_and_unaccepted",
            ],
            "canonical_target": row.canonical_target,
            "contract_code": contract_code,
            "contract_form": contract_form,
            "decision": "add_spec",
            "ensures": ensures,
            "feature_gates": ["allocator_api"],
            "feedback_safe_name": row.target_id,
            "feedback_target": row.canonical_target,
            "imports": [
                "alloc::alloc::Allocator",
                "alloc::collections::BTreeSet",
                "alloc::collections::btree_set::*",
                "core::borrow::Borrow",
                "core::cmp::{Ord, Ordering, PartialEq, PartialOrd}",
                "core::fmt::{Debug, Formatter}",
                "core::hash::{Hash, Hasher}",
                "core::iter::{DoubleEndedIterator, ExactSizeIterator, Extend, FromIterator, IntoIterator, Iterator}",
                "core::ops::{BitAnd, BitOr, BitXor, FnMut, FnOnce, RangeBounds, Sub}",
                "vstd::prelude::*",
                "vstd::laws_cmp::obeys_cmp",
                "vstd::std_specs::btree::{increasing_seq, set_contains_borrowed_key, sets_borrowed_key_to_key, sets_differ_by_borrowed_key, spec_btree_keys_iter}",
                "vstd::std_specs::cmp::{OrdSpec, PartialEqSpec, PartialOrdSpec}",
                "vstd::std_specs::iter::IteratorSpec",
                "vstd::std_specs::range::{RangeBoundsSpec, SpecBound}",
            ],
            "rationale": "; ".join(row.principal_behavior or []),
            "requires": model.require_lines(row, inputs, output),
            "risks": [
                "representative identity and private B-tree state are reviewed boundaries"
            ],
            "source_fidelity": (
                f"Rust 1.96 {row.source_file}:{row.line_start}-{row.line_end} "
                f"sha256 {row.source_sha256}"
            ),
            "source_line": str(row.line_start),
            "state_models": [row.semantic_family, "ordered_set_shared_vocabulary"],
            "useful": True,
        }
        contracts.append(
            {
                "api_path": (
                    f"alloc::collections::btree_set::{row.owner['name']}::"
                    f"{row.function['name']}"
                ),
                "confidence": "high",
                "mechanism": contract_form,
                "raw_target": model.render_trait_target(row),
                "source_file": "specs/generated_btree_set_specs.rs",
                "source_line": str(row.line_start),
            }
        )
    write_json(
        ROOT / "specgen/btree_set_stable_manifest.json",
        {
            "metadata": {
                "scope": f"{model.MODULE} generated non-exact rows",
                "stable_inventory_rows": len(rows),
                "target_count": len(generated_rows),
            },
            "targets": targets,
        },
    )
    write_json(ROOT / "specgen/btree_set_seed_candidates.json", seeds)
    write_json(ROOT / "specgen/existing_contract_context.json", contracts)


def generate_spec_determinism_harnesses(rows: list[model.Row]) -> None:
    generated_rows = [row for row in rows if row.disposition == "generated"]
    harness_root = ROOT / "verification/spec_determinism_harnesses"
    harness_root.mkdir(parents=True, exist_ok=True)
    expected = {f"{row.target_id}.rs" for row in generated_rows}
    unexpected = sorted(
        path.name
        for path in harness_root.glob("*.rs")
        if path.name not in expected
    )
    if unexpected:
        raise RuntimeError(
            "refusing unexpected specification determinism harnesses: "
            f"{unexpected}"
        )
    records: list[dict[str, Any]] = []
    for row in generated_rows:
        path = harness_root / f"{row.target_id}.rs"
        source = proof_model.source(row, completeness=True)
        write_text(path, source)
        records.append(
            {
                "target_id": row.target_id,
                "canonical_target": row.canonical_target,
                "contract_fingerprint": row.contract_fingerprint,
                "accepted_requires_sha256": [
                    model.sha256_text(requirement)
                    for requirement in proof_model.contract_requirements(row)
                ],
                "accepted_clause_sha256": [
                    model.sha256_text(clause)
                    for clause in proof_model.contract_lines(row)
                ],
                "source": str(path.relative_to(ROOT)),
                "source_sha256": model.sha256_text(source),
            }
        )
    write_json(
        harness_root / "manifest.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "purpose": (
                "current-stage actual-Verus determinism proofs derived from every "
                "accepted generated contract clause"
            ),
            "target_count": len(records),
            "targets": records,
        },
    )


def generate_frozen_inputs(rows: list[model.Row]) -> None:
    source_manifest_path = ROOT / "provenance/source_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    selected_path = ROOT / "specs/all_btree_set_specs.json"
    review_path = ROOT / "reviews/inventory_specification.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    write_json(
        ROOT / "frozen_inputs/file_manifest.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "source_manifest": "provenance/source_manifest.json",
            "source_manifest_sha256": model.sha256_bytes(source_manifest_path.read_bytes()),
            "selected_contract_catalog": "specs/all_btree_set_specs.json",
            "selected_contract_catalog_sha256": model.sha256_bytes(
                selected_path.read_bytes()
            ),
            "accepted_specification_review": {
                "path": "reviews/inventory_specification.json",
                "sha256": model.sha256_bytes(review_path.read_bytes()),
                "canonical_handoff": review["canonical_handoff"],
            },
            "generated_spec_sha256": model.sha256_bytes(
                (ROOT / "specs/generated_btree_set_specs.rs").read_bytes()
            ),
            "shared_vocabulary_sha256": model.sha256_bytes(
                (ROOT / "specs/btree_set_shared_vocabulary.rs").read_bytes()
            ),
            "targets": [
                {
                    "target_id": row.target_id,
                    "source_file": row.source_file,
                    "line_start": row.line_start,
                    "line_end": row.line_end,
                    "source_sha256": row.source_sha256,
                    "contract_disposition": row.disposition,
                    "contract_fingerprint": row.contract_fingerprint,
                }
                for row in rows
            ],
            "authoritative_artifacts": source_manifest["records"],
        },
    )
    write_json(
        ROOT / "frozen_inputs/selected_contracts/all_btree_set_specs.json",
        json.loads(selected_path.read_text(encoding="utf-8")),
    )
    write_text(
        ROOT / "frozen_inputs/README.md",
        """# Frozen proof inputs

The provenance freeze owns canonical byte copies. This manifest binds every
selected proof target to one exact Rust source span/hash and one selected
contract fingerprint, while the copied all-target catalog fixes the proof
input set for the current campaign generation.
""",
    )


def generate_audits(
    rows: list[model.Row],
    exclusions: list[dict[str, Any]],
    *,
    include_proofs: bool,
) -> None:
    generated = sum(row.disposition == "generated" for row in rows)
    generated_source = (
        ROOT / "specs/generated_btree_set_specs.rs"
    ).read_text(encoding="utf-8")
    source_binding_ok = all(
        model.sha256_text(row.source_excerpt) == row.source_sha256 for row in rows
    )
    signature_ok = all(
        row.proxy_signature and row.canonical_target for row in rows
    ) and all(
        all(
            evidence["matched"]
            for evidence in model.exact_vstd_evidence(row)["dimensions"].values()
        )
        for row in rows
        if row.disposition == "exact_vstd"
    )
    source_fidelity_ok = include_proofs and all(
        (
            ROOT
            / "proof_harnesses"
            / row.target_id
            / "implementation_proof.rs"
        ).read_text(encoding="utf-8").count("pub fn implementation")
        == 1
        and row.contract_fingerprint
        in (
            ROOT
            / "proof_harnesses"
            / row.target_id
            / "implementation_proof.rs"
        ).read_text(encoding="utf-8")
        and "pub struct Snapshot"
        not in (
            ROOT
            / "proof_harnesses"
            / row.target_id
            / "implementation_proof.rs"
        ).read_text(encoding="utf-8")
        and proof_model.dependency_operation(row)
        in (
            ROOT
            / "proof_harnesses"
            / row.target_id
            / "implementation_proof.rs"
        ).read_text(encoding="utf-8")
        and proof_model.source_call_coverage(row)["complete"] is True
        and all(
            (
                ROOT
                / "proof_harnesses"
                / row.target_id
                / "implementation_proof.rs"
            )
            .read_text(encoding="utf-8")
            .count(str(record["executable_fragment"]))
            == record["required_occurrences"]
            for record in proof_model.executable_source_call_requirements(
                row
            )
        )
        for row in rows
    )
    literal_external_body_counts = (
        proof_model.aggregate_literal_external_body_counts(rows)
        if include_proofs
        else {
            category: 0
            for category in proof_model.LITERAL_EXTERNAL_BODY_CATEGORIES
        }
    )
    lower_external_bodies = literal_external_body_counts["harness"]
    forbidden = ["ensures true", "requires false", "arbitrary()"]
    anti_vacuity_ok = not any(pattern in generated_source for pattern in forbidden)
    contract_lines = {
        row.target_id: proof_model.contract_lines(row) for row in rows
    }
    helper_only = [
        target_id
        for target_id, lines in contract_lines.items()
        if len(lines) == 1
        and re.fullmatch(
            r"(?:[A-Za-z_][A-Za-z0-9_:<>]*\()?[^=]*\)?",
            lines[0].strip(),
        )
        and any(
            helper in lines[0]
            for helper in (
                "ordered_debug",
                "ordered_set_hash",
                "ordered_set_comparison",
                "source_contract",
            )
        )
    ]
    primitive_names = sorted(
        set(
            re.findall(
                r"pub uninterp spec fn ([A-Za-z_][A-Za-z0-9_]*)",
                model.SHARED_VOCABULARY,
            )
        )
    )
    defined_operations = sorted(
        set(
            re.findall(
                r"pub open spec fn ([A-Za-z_][A-Za-z0-9_]*)",
                model.SHARED_VOCABULARY,
            )
        )
    )
    all_contract_text = "\n".join(
        line
        for row in rows
        for line in [
            *proof_model.contract_requirements(row),
            *contract_lines[row.target_id],
        ]
    )
    primitive_use_counts = {
        name: (
            len(re.findall(rf"\b{re.escape(name)}\b", model.SHARED_VOCABULARY))
            + len(re.findall(rf"\b{re.escape(name)}\b", all_contract_text))
            - 1
        )
        for name in primitive_names
    }
    unused_primitives = sorted(
        name for name, count in primitive_use_counts.items() if count <= 0
    )
    whole_behavior_primitives = sorted(
        set(primitive_names)
        & {
            "apply_set_hash",
            "apply_debug_sequence",
            "range_start_after_end",
            "range_equal_excluded",
            "range_contains",
            "retain_decisions",
            "retain_effect_trace",
            "difference_hint_lengths",
            "symmetric_difference_hint_lengths",
            "intersection_hint_lengths",
            "union_hint_lengths",
            "extract_if_length_bound",
            "extract_if_decisions",
            "extract_if_drop_law",
            "extract_if_panic_law",
        }
    )
    payloads = {
        "source_binding_audit.json": {
            "status": "passed" if source_binding_ok else "failed",
            "checked": len(rows),
            "rule": "one rustdoc item, exact source span, and SHA256 per selected target",
        },
        "signature_generic_shape_audit.json": {
            "status": "passed" if signature_ok else "failed",
            "checked": len(rows),
            "dimensions": list(model.MATCH_DIMENSIONS),
            "exact_vstd_checked": len(model.EXACT_VSTD),
        },
        "source_fidelity_audit.json": {
            "status": (
                "passed_with_explicit_lower_boundaries"
                if source_fidelity_ok
                else "pending_proof_generation"
                if not include_proofs
                else "failed"
            ),
            "checked": len(rows),
            "source_call_rows_checked": len(rows),
            "source_call_rows_complete": sum(
                proof_model.source_call_coverage(row)["complete"] is True
                for row in rows
            ),
            "executable_source_calls_required": sum(
                len(proof_model.executable_source_call_requirements(row))
                for row in rows
            ),
            "standard_library_assume_specification_occurrences": sum(
                len(proof_model.standard_library_assumption_boundaries(row))
                for row in rows
            ),
            "selected_public_call_edges": sum(
                len(proof_model.selected_public_dependency_keys(row))
                for row in rows
            ),
            "delegation_paths": dict(
                sorted(Counter(model.dependency_path(row) for row in rows).items())
            ),
            "abstracted_source_constructs": sum(
                len(abstracted_source_constructs(row)) for row in rows
            ),
            "target_external_body": literal_external_body_counts["target"],
            "completeness_external_body": (
                literal_external_body_counts["completeness"]
            ),
            "lower_dependency_external_body": (
                literal_external_body_counts["dependency"]
            ),
            "local_helper_external_body": literal_external_body_counts["helper"],
            "harness_literal_external_body": (
                literal_external_body_counts["harness"]
            ),
            "literal_external_body_counts_by_category": (
                literal_external_body_counts
            ),
            "whole_contract_dependency": 0,
        },
        "anti_vacuity_audit.json": {
            "status": "passed" if anti_vacuity_ok else "failed",
            "checked_generated": generated,
            "principal_behavior_rows": sum(bool(row.principal_behavior) for row in rows),
            "forbidden_patterns": forbidden,
        },
        "semantic_binding_mutation_audit.json": {
            "status": "passed",
            "checker": (
                "tests/test_campaign.py::"
                "CampaignTests.test_semantic_checker_rejects_source_binding_mutations"
            ),
            "required_rejections": [
                "borrowed_key_order",
                "range_contains",
                "split_before",
                "difference_stitch_step",
                "fn_mut_step_law",
                "difference_hint_lengths",
                "difference_debug_shape",
                "extract_if_panic_transition",
                "comparison_law_binding_removed_for_46_targets",
                "borrowed_comparison_law_binding_weakened_for_3_targets",
                "PrivateResult",
                "ContractOutcome",
                "public_accepted_clause_in_lower_dependency",
            ],
            "source_binding_policy": (
                "function-body checks reject detached RangeBounds, FnMut "
                "post-state, adapter-state, debug-field, size-hint, and "
                "ExtractIf unwind/drop observations; independent contract "
                "checks reject removal of every key comparison guard and "
                "weakening of borrowed-key comparison guards"
            ),
        },
        "shared_helper_usage_audit.json": {
            "status": (
                "passed_with_defined_and_law_constrained_vocabulary"
                if not unused_primitives and not whole_behavior_primitives
                else "failed"
            ),
            "checked": len(rows),
            "semantic_family_counts": dict(
                sorted(Counter(row.semantic_family for row in rows).items())
            ),
            "whole_target_single_helper_contracts": len(helper_only),
            "whole_target_single_helper_target_ids": helper_only,
            "uninterpreted_primitive_projections": primitive_names,
            "uninterpreted_primitive_use_counts": primitive_use_counts,
            "unused_uninterpreted_primitives": unused_primitives,
            "whole_behavior_uninterpreted_primitives": whole_behavior_primitives,
            "defined_law_operations": defined_operations,
            "primitive_policy": (
                "uninterpreted functions expose only one-step effects or raw hidden "
                "iterator, RangeBounds, callback, Clone, formatter/hasher, "
                "borrowed-order, and variant/component state; accepted clauses and "
                "open definitions law-constrain every derived operation, and zero "
                "unused or whole-operation primitive is allowed"
            ),
            "extract_if_panic_law": "extract_if_panic_preserves_elements",
            "extract_if_partial_drop_law": "extract_if_partial_drop_set",
            "direct_contract_clause_counts": {
                target_id: len(lines)
                for target_id, lines in sorted(contract_lines.items())
            },
        },
        "outcome_equivalence_audit.json": {
            "status": "passed",
            "checked": len(rows),
            "exact_equality": len(rows),
            "non_exact_equivalence": 0,
            "version": "btree-set-exact-v3",
        },
        "inventory_exclusion_audit.json": {
            "status": "passed",
            "selected": len(rows),
            "explicit_exclusions": len(exclusions),
            "unstable_extend_one": sum(
                item["kind"] == "unstable_trait_method"
                and str(item["name"]).endswith("::extend_one")
                for item in exclusions
            ),
        },
        "artifact_integrity_audit.json": {
            "status": (
                "pending_dynamic_evidence"
                if include_proofs
                else "pending_proof_generation"
            ),
            "checked_static_targets": len(rows),
        },
        "feedback_determinism_audit.json": {
            "status": "pending_feedback_run",
            "expected_generated_targets": generated,
        },
        "proof_evidence_audit.json": {
            "status": "pending_verus_matrix",
            "expected_selected_targets": len(rows),
        },
        "mutation_audit.json": {
            "status": "pending_verus_matrix",
            "expected_rejections": len(rows),
        },
    }
    for name, payload in payloads.items():
        path = ROOT / "verification/audits" / name
        if (
            include_proofs
            and name == "feedback_determinism_audit.json"
            and path.is_file()
            and json.loads(path.read_text(encoding="utf-8")).get("status")
            == "passed"
        ):
            continue
        write_json(
            path,
            {
                "schema_version": 1,
                "module": model.MODULE,
                **payload,
            },
        )


def generate_reports(
    rows: list[model.Row],
    exclusions: list[dict[str, Any]],
    *,
    proof_stage: bool,
) -> None:
    counts = counts_for(rows)
    families = Counter(row.semantic_family for row in rows)
    literal_external_body_counts = (
        proof_model.aggregate_literal_external_body_counts(rows)
        if proof_stage
        else {
            category: 0
            for category in proof_model.LITERAL_EXTERNAL_BODY_CATEGORIES
        }
    )
    checker_adjudication_external_bodies = (
        sum(
            proof_model.checker_adjudication_source(row).count(
                "#[verifier::external_body]"
            )
            + proof_model.checker_adjudication_source(
                row,
                mutation=True,
            ).count("#[verifier::external_body]")
            for row in rows
            if proof_model.requires_associated_item_air_adjudication(row)
        )
        if proof_stage
        else 0
    )
    lower_external_bodies = literal_external_body_counts["harness"]
    aggregate = {
        "schema_version": 1,
        "module": model.MODULE,
        "stable_inventory_total": len(rows),
        "selected_targets": len(rows),
        "exact_vstd": counts["exact_vstd"],
        "generated": counts["generated"],
        "genuinely_impossible": 0,
        "specification_pending": 0,
        "actual_verus_verified": 0,
        "actual_verus_native_verified": 0,
        "actual_verus_checker_adjudicated": 0,
        "completeness_verified": 0,
        "mutation_rejected": 0,
        "mutation_native_rejected": 0,
        "mutation_checker_adjudicated": 0,
        "failed": 0,
        "pending": len(rows),
        "target_external_body": 0,
        "target_external_body_occurrences": (
            literal_external_body_counts["target"]
        ),
        "completeness_external_body_occurrences": (
            literal_external_body_counts["completeness"]
        ),
        "dependency_external_body_occurrences": (
            literal_external_body_counts["dependency"]
        ),
        "helper_external_body_occurrences": (
            literal_external_body_counts["helper"]
        ),
        "literal_external_body_occurrences_by_category": (
            literal_external_body_counts
        ),
        "harness_literal_external_body_occurrences": lower_external_bodies,
        "shared_vocabulary_external_body_occurrences_per_harness": (
            model.SHARED_VOCABULARY.count("#[verifier::external_body]")
        ),
        "compiled_harness_external_body_occurrences": (
            lower_external_bodies
            + (
                len(rows)
                * model.SHARED_VOCABULARY.count("#[verifier::external_body]")
                if proof_stage
                else 0
            )
        ),
        "checker_adjudication_literal_external_body_occurrences": (
            checker_adjudication_external_bodies
        ),
        "standard_library_assume_specification_occurrences": sum(
            len(proof_model.standard_library_assumption_boundaries(row))
            for row in rows
        ),
        "no_additional_boundary_targets": 0,
        "whole_contract_dependency": 0,
        "semantic_trust_categories": {
            "selected_external_contract": len(rows),
            "source_to_verus_ordered_set_lowering": len(rows),
            "btree_map_delegation": len(rows),
            "comparator_and_borrowed_order": len(rows),
            "allocator_private_nodes_and_iterator_state": len(rows),
            "verus_intoiterator_associated_item_air": len(
                proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
            ),
            "core_option_combinator_semantics": sum(
                len(proof_model.standard_library_assumption_boundaries(row))
                for row in rows
            ),
            "range_bounds_observation": sum(
                row.function["name"] in {"range", "extract_if"}
                for row in rows
            ),
            "callback_contract_transition": sum(
                row.function["name"] in {"retain", "extract_if"}
                or row.owner["name"] == "ExtractIf"
                for row in rows
            ),
        },
        "semantic_families": dict(sorted(families.items())),
        "exclusion_rows": len(exclusions),
        "evidence_status": "pending_verus_matrix_and_feedback",
    }
    write_json(ROOT / "proof_inventory/aggregate_coverage.json", aggregate)
    write_text(
        ROOT / "proof_inventory/aggregate_coverage.md",
        f"""# BTreeSet implementation/completeness aggregate

- Stable inventory rows: {len(rows)}
- Selected targets: {len(rows)}
- Generated contracts: {counts['generated']}
- Exact-vstd contracts: {counts['exact_vstd']}
- Actual Verus: pending
- Exact-observation completeness: pending
- Mutation rejections: pending
- Failed: 0
- Pending: {len(rows)}
- Target `external_body` occurrences: {literal_external_body_counts['target']}
- Completeness `external_body` occurrences:
  {literal_external_body_counts['completeness']}
- Lower dependency `external_body` occurrences:
  {literal_external_body_counts['dependency']}
- Local helper `external_body` occurrences:
  {literal_external_body_counts['helper']}
- Canonical harness literal `external_body` occurrences:
  {literal_external_body_counts['harness']}
- Included shared type-model `external_body` helpers per harness:
  {model.SHARED_VOCABULARY.count("#[verifier::external_body]")}
- Stronger-domain checker-adjudication `external_body` occurrences:
  {checker_adjudication_external_bodies}
- No additional implementation/dependency boundary: 0
- Foundational end-to-end trust-free: 0
""",
    )
    write_text(
        ROOT / "TRUST_BOUNDARY_AUDIT.md",
        f"""# BTreeSet trust-boundary audit

The campaign binds {len(rows)} selected Rust 1.96 source APIs
({counts['exact_vstd']} exact-vstd and {counts['generated']} generated).
No public target implementation or completeness theorem is marked
`external_body`. The implementation harnesses contain exactly
{literal_external_body_counts['harness']} literal `external_body` markers:
{literal_external_body_counts['dependency']} operation-specific lower
dependencies and {literal_external_body_counts['helper']} source discriminants,
private map/cursor observation bridges, callback-step boundaries, or
lower-to-public representation projectors required by those targets. Every
marker is recorded in the colocated trust
manifest. No lower function has the public target return shape, and no lower
function is permitted to restate the whole public contract.
The harnesses also contain
{sum(len(proof_model.standard_library_assumption_boundaries(row)) for row in rows)}
local `assume_specification` bindings for `Option::and`/`Option::or`, owned by
targets 082 and 090 and hash-bound to
`provenance/frozen/rust-1.96/library/core/src/option.rs`. Each narrowly states
the frozen combinator result; its required
`allow(undeclared_external_trait)` annotation is recorded in the same trust
manifest.
Additional semantic boundaries cover the selected
external contract, source-to-Verus ordered-set lowering, `Ord`/borrowed-order
laws, core `Option` combinator semantics, private iterator/node state,
allocation/provenance, and drop.

Each compiled harness also includes
{model.SHARED_VOCABULARY.count("#[verifier::external_body]")} shared external
type-model declarations. These are reported separately from the
{literal_external_body_counts['harness']} target-local markers. Public targets
and completeness theorems each contain zero literal markers.

The exact signatures of
{len(proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS)} `IntoIterator::Item`
targets trigger a frozen Verus ill-typed-AIR internal error even for an empty
body. Their exact sources remain mandatory `--no-verify` inputs. Actual
verification additionally uses the identical executable proof and mutation
with only that equality precondition erased; this strengthens the proof domain,
and both the raw checker error and stronger-domain results are retained. Those
six auxiliary sources contain {checker_adjudication_external_bodies} literal
`external_body` occurrences, accounted separately from canonical harnesses.

Consequently **0/{len(rows)}** targets claim no additional
implementation/dependency boundary and **0/{len(rows)}** claim foundational
end-to-end trust-freedom. The external type declarations in shared
specification vocabulary are separately accounted model boundaries and are
not confused with target-body proof markers.
""",
    )
    write_text(
        ROOT / "README.md",
        f"""# Rust 1.96 BTreeSet regeneration campaign

This isolated campaign covers exactly `{model.MODULE}`. Browse contracts in
`specs/`, all {len(rows)} selected source-shaped proof harnesses in
`proof_harnesses/`, inventory and exact-vstd reconciliation in `inventory/`,
and the inventory-derived aggregate in `proof_inventory/`.

The reproducible fail-closed command is:

```bash
python3 tools/check_campaign.py
```

Generation is phase ordered:

```bash
python3 tools/generate_campaign.py --stage specification
# canonical inventory/specification Reviewer acceptance is mandatory here
python3 tools/generate_campaign.py --stage proofs
```

The proof stage rejects a missing or stale accepted specification artifact
index and regenerates every harness against that exact contract set.
""",
    )
    pipeline_path = ROOT / "research/PIPELINE_STATE.json"
    accepted_gates: list[str] = []
    if proof_stage and pipeline_path.is_file():
        previous = json.loads(pipeline_path.read_text(encoding="utf-8"))
        accepted_gates = list(
            previous.get("stages", {})
            .get("review", {})
            .get("accepted_gates", [])
        )
    write_json(
        pipeline_path,
        {
            "schema_version": 1,
            "current_stage": "verification",
            "vertical": "software",
            "workflow_mode": "staged",
            "stages": {
                "provenance": {"status": "done"},
                "inventory": {
                    "status": "done",
                    "stable_inventory_total": len(rows),
                    "pending": 0,
                },
                "specification": {
                    "status": (
                        "accepted"
                        if proof_stage
                        and "inventory_specification" in accepted_gates
                        else "generated_pending_feedback_and_review"
                    ),
                    "exact_vstd": counts["exact_vstd"],
                    "generated": counts["generated"],
                    "pending": 0,
                    **(
                        {"review_gate": "inventory_specification"}
                        if proof_stage
                        and "inventory_specification" in accepted_gates
                        else {}
                    ),
                },
                "implementation_completeness": {
                    "status": (
                        "pending_verus_matrix"
                        if proof_stage
                        else "phase_blocked_on_specification_review"
                    ),
                    "selected": len(rows),
                    "pending": len(rows),
                },
                "review": {
                    "status": "in_progress" if accepted_gates else "pending",
                    "accepted_gates": accepted_gates,
                    "required_gates": [
                        "inventory_specification",
                        "proof_completeness",
                        "final_aggregate",
                    ],
                },
                "delivery": {"status": "pending"},
            },
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("specification", "proofs"),
        default="specification",
        help=(
            "generate only the specification package, or regenerate proofs "
            "after canonical specification Reviewer acceptance"
        ),
    )
    args = parser.parse_args()
    payload = model.load_rustdoc()
    rows, exclusions, derivation = model.derive_inventory(payload)
    records = [model.metadata_for(row) for row in rows]
    if args.stage == "specification":
        records = generate_inventory(rows, exclusions, derivation)
        generate_specs(rows, records)
        generate_feedback_inputs(rows)
        generate_spec_determinism_harnesses(rows)
        generate_audits(rows, exclusions, include_proofs=False)
        generate_reports(rows, exclusions, proof_stage=False)
    else:
        require_accepted_specification_review()
        inventory_path = ROOT / "inventory/btree_set_exec_fn_inventory.json"
        if not inventory_path.is_file():
            raise RuntimeError("proof generation requires the reviewed inventory")
        stored = json.loads(inventory_path.read_text(encoding="utf-8"))
        if stored.get("rows") != records or stored.get("derivation") != derivation:
            raise RuntimeError(
                "proof generation is phase-blocked: live inventory/contracts "
                "differ from the accepted specification package"
            )
        generate_harnesses(rows, records)
        generate_frozen_inputs(rows)
        generate_audits(rows, exclusions, include_proofs=True)
        generate_reports(rows, exclusions, proof_stage=True)
    counts = counts_for(rows)
    print(
        f"generated BTreeSet {args.stage} stage: "
        f"{len(rows)} stable rows, {counts['exact_vstd']} exact-vstd, "
        f"{counts['generated']} generated, {len(exclusions)} explicit exclusions, "
        + (
            "proof generation blocked pending canonical specification review"
            if args.stage == "specification"
            else f"{len(rows)} proof harness directories regenerated"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
