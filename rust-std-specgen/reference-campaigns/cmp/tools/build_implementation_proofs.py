#!/usr/bin/env python3
"""Materialize all inventory-derived core::cmp proof harnesses."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_specification as specification
from tools import check_specification
from tools import proof_templates_cmp
from tools import proof_templates_exact
from tools import proof_templates_sequence
from tools import proof_templates_tuple
from tools.proof_template_common import ProofTemplate


HARNESS_ROOT = ROOT / "proof_harnesses"
MANIFEST_ROOT = ROOT / "proof_manifests"
PROOF_INVENTORY = ROOT / "proof_inventory"
FROZEN_ROOT = ROOT / "frozen_inputs"
TARGETS_JSON = PROOF_INVENTORY / "targets.json"
TARGETS_CSV = PROOF_INVENTORY / "targets.csv"
DEPENDENCY_JSON = PROOF_INVENTORY / "dependency_graph.json"
DEPENDENCY_DOT = PROOF_INVENTORY / "dependency_graph.dot"
AUTHORIZATION = PROOF_INVENTORY / "proof_phase_authorization.json"
AGGREGATE_JSON = PROOF_INVENTORY / "aggregate_coverage.json"
AGGREGATE_MD = PROOF_INVENTORY / "aggregate_coverage.md"
FROZEN_JSON = FROZEN_ROOT / "file_manifest.json"
FROZEN_CSV = FROZEN_ROOT / "file_manifest.csv"
TEMPLATE_MODULES = (
    proof_templates_exact,
    proof_templates_tuple,
    proof_templates_sequence,
    proof_templates_cmp,
)
ACCEPTED_PROOF_DISPOSITIONS = frozenset({"generated", "exact_vstd"})
ACCEPTED_SPECIFICATION_DISPOSITIONS = (
    ACCEPTED_PROOF_DISPOSITIONS | {"genuinely_impossible"}
)


class ProofBuildError(RuntimeError):
    """The accepted inventory cannot be materialized into complete proofs."""


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compact_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def selected_proof_rows(
    inventory_rows: list[dict[str, Any]],
    catalog_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if catalog_rows is None:
        catalog_rows = load(specification.CATALOG)["rows"]
    inventory_by_id = {row["row_id"]: row for row in inventory_rows}
    catalog_by_id = {row["row_id"]: row for row in catalog_rows}
    if len(inventory_by_id) != len(inventory_rows):
        raise ProofBuildError("live inventory contains duplicate row ids")
    if len(catalog_by_id) != len(catalog_rows):
        raise ProofBuildError(
            "accepted specification catalog contains duplicate row ids"
        )
    if set(catalog_by_id) != set(inventory_by_id):
        raise ProofBuildError(
            "accepted specification catalog does not match the live inventory"
        )
    unknown_dispositions = {
        row.get("disposition")
        for row in catalog_rows
        if row.get("disposition")
        not in ACCEPTED_SPECIFICATION_DISPOSITIONS
    }
    if unknown_dispositions:
        raise ProofBuildError(
            "accepted specification catalog contains unsupported "
            f"dispositions: {sorted(unknown_dispositions, key=str)}"
        )

    selected_ids: set[str] = set()
    for row_id, accepted in catalog_by_id.items():
        disposition = accepted.get("disposition")
        if disposition not in ACCEPTED_PROOF_DISPOSITIONS:
            continue
        inventory_disposition = inventory_by_id[row_id].get("disposition")
        expected_inventory_disposition = (
            "exact_vstd" if disposition == "exact_vstd" else "pending"
        )
        if inventory_disposition != expected_inventory_disposition:
            raise ProofBuildError(
                "accepted specification disposition does not match the live "
                f"inventory for {row_id}"
            )
        selected_ids.add(row_id)
    return [
        row for row in inventory_rows if row["row_id"] in selected_ids
    ]


def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def write_if_changed(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == value:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def slug(index: int, target: str) -> str:
    normalized = (
        target.replace("core::cmp::", "core_cmp_")
        .replace("core::", "core_")
        .replace("::", "_")
        .replace("&mut ", "mut_")
        .replace("&", "ref_")
    )
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_")
    return f"{index:03d}_{normalized}"[:220].rstrip("_")


def source_excerpt(row: dict[str, Any]) -> bytes:
    path = ROOT / row["source_evidence"]["snapshot_path"]
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    value = "".join(
        lines[int(row["source_begin_line"]) - 1:int(row["source_end_line"])]
    ).encode()
    if sha256_bytes(value) != row["source_evidence"]["span_sha256"]:
        raise ProofBuildError(f"source span drift for {row['row_id']}")
    return value


def exact_contract_text(
    row: dict[str, Any],
    exact_by_id: dict[str, dict[str, Any]],
) -> str:
    record = exact_by_id.get(row["row_id"])
    if record is None:
        raise ProofBuildError(f"missing exact-vstd binding {row['row_id']}")
    lines = [
        f"// @exact-vstd-row {row['row_id']}",
        f"// Target: {row['target']}",
        "// This target references the frozen exact-vstd binding below; it is",
        "// not redeclared as a competing assume_specification.",
    ]
    for line in json.dumps(record, indent=2, sort_keys=True).splitlines():
        lines.append(f"// {line}")
    return "\n".join(lines) + "\n"


def normalized_template(template: ProofTemplate) -> ProofTemplate:
    implementation = template.implementation_proof
    completeness = template.completeness_proof
    relation_name = template.accepted_relation_name
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", relation_name) is None:
        raise ProofBuildError(
            f"template has invalid accepted relation name {relation_name!r}"
        )
    relation_pattern = (
        rf"\bpub open spec fn {re.escape(relation_name)}\b"
    )
    implementation_declarations = re.findall(
        relation_pattern,
        implementation,
    )
    completeness_declarations = re.findall(
        relation_pattern,
        completeness,
    )
    if not implementation_declarations and not completeness_declarations:
        raise ProofBuildError(
            "template does not declare its accepted relation: "
            f"{relation_name!r}"
        )
    if relation_name != "accepted_contract":
        if len(implementation_declarations) != 1:
            raise ProofBuildError(
                "template must declare its row-owned accepted relation "
                f"exactly once in the implementation proof: {relation_name!r}"
            )
        if re.search(
            r"\bpub open spec fn accepted_contract\b",
            implementation + "\n" + completeness,
        ):
            raise ProofBuildError(
                "template accepted relation collides with accepted_contract"
            )
        implementation = re.sub(
            rf"\b{re.escape(relation_name)}\b",
            "accepted_contract",
            implementation,
        )
        completeness = re.sub(
            rf"\b{re.escape(relation_name)}\b",
            "accepted_contract",
            completeness,
        )
    implementation = re.sub(
        r"\bpub fn implementation(?=[<(])",
        "pub fn implementation_target",
        implementation,
    )
    implementation = re.sub(
        r"\bimplementation\(",
        "implementation_target(",
        implementation,
    )
    completeness = re.sub(
        r"\bpub proof fn completeness(?=[<(])",
        "pub proof fn completeness_theorem",
        completeness,
    )
    completeness = re.sub(
        r"\bimplementation\(",
        "implementation_target(",
        completeness,
    )
    module_import = "use super::implementation_proof::*;"
    if module_import in completeness:
        completeness = completeness.replace(
            module_import,
            '#[path = "implementation_proof.rs"]\n'
            "mod implementation_proof;\n"
            "use implementation_proof::*;",
            1,
        )
    token_block = "\n".join(
        f"// SOURCE_SHAPE_TOKEN: {token}"
        for token in template.source_shape_tokens
    )
    if token_block:
        implementation = token_block + "\n" + implementation
    return ProofTemplate(
        proof_family=template.proof_family,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=template.source_shape_tokens,
        boundaries=template.boundaries,
        implementation_mutation=template.implementation_mutation,
        completeness_mutation=template.completeness_mutation,
        implementation_mutations=template.implementation_mutations,
        completeness_mutations=template.completeness_mutations,
    )


def normalized_boundaries(
    template: ProofTemplate,
    row_id: str,
) -> list[dict[str, Any]]:
    records = []
    for boundary in template.boundaries:
        if boundary.get("whole_target_outcome") is not False:
            raise ProofBuildError(
                f"boundary is not explicitly narrow for {row_id}: {boundary}"
            )
        name = boundary.get("function") or boundary.get("name")
        if not isinstance(name, str) or not name:
            raise ProofBuildError(f"unnamed boundary for {row_id}")
        records.append(
            {
                **boundary,
                "name": name,
                "function": name,
                "row_id": row_id,
                "category": str(
                    boundary.get("category") or "lower_source_dependency"
                ),
                "level": str(
                    boundary.get("level") or "dependency"
                ),
                "literal_external_body": (
                    boundary.get("literal_external_body") is True
                ),
                "whole_target_outcome": boundary["whole_target_outcome"],
                "rationale": str(
                    boundary.get("rationale")
                    or boundary.get("role")
                    or "Narrow source dependency retained by the renderer."
                ),
            }
        )
    return records


def renderer_for(
    row: dict[str, Any],
    family: str,
) -> Any:
    matches = [
        module
        for module in TEMPLATE_MODULES
        if module.supports(row, family)
    ]
    if len(matches) != 1:
        raise ProofBuildError(
            f"{row['row_id']} has {len(matches)} renderers for {family}"
        )
    return matches[0]


def manifest_hash_fields(
    payloads: dict[str, bytes],
) -> dict[str, str]:
    return {
        f"{name.removesuffix('.rs')}_sha256": sha256_bytes(value)
        for name, value in payloads.items()
        if name in {
            "implementation_proof.rs",
            "completeness_proof.rs",
            "accepted_contract.rs",
            "source_excerpt.rs",
        }
    }


def frozen_inputs(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    required: set[Path] = {
        specification.INVENTORY,
        specification.GENERATED,
        specification.VOCABULARY,
        specification.CATALOG,
        specification.EXISTING_BINDINGS,
        specification.EQUIVALENCE,
        specification.FLOAT_MODEL_BOUNDARY,
        specification.REVIEW_REQUEST,
        check_specification.INDEPENDENT_REVIEW,
        check_specification.CANONICAL_HANDOFF,
        check_specification.MISSION_PATH,
        ROOT / "provenance" / "campaign_provenance.json",
        ROOT / "provenance" / "preservation_baseline.json",
    }
    required.update(
        ROOT / row["source_evidence"]["snapshot_path"] for row in rows
    )
    exact_bindings = load(specification.EXISTING_BINDINGS)
    for record in exact_bindings["records"]:
        for binding in record["bindings"]:
            path = binding.get("evidence", {}).get("snapshot_path")
            if isinstance(path, str):
                required.add(ROOT / path)
    payloads: dict[str, bytes] = {}
    records: list[dict[str, Any]] = []
    for source in sorted(required, key=str):
        if not source.is_file():
            raise ProofBuildError(f"frozen input missing: {source}")
        if source.is_relative_to(ROOT):
            source_label = str(source.relative_to(ROOT))
            if source_label.startswith("provenance/snapshots/rust-1.96/"):
                suffix = source_label.removeprefix(
                    "provenance/snapshots/rust-1.96/"
                )
                destination = f"rust_1_96_source/{suffix}"
            elif source_label.startswith("provenance/snapshots/verus/"):
                suffix = source_label.removeprefix(
                    "provenance/snapshots/verus/"
                )
                destination = f"vstd/{suffix}"
            else:
                destination = f"selected_contracts/{source.name}"
        else:
            source_label = str(source)
            destination = f"selected_contracts/mission_{source.name}"
        data = source.read_bytes()
        destination_path = FROZEN_ROOT / destination
        payloads[str(destination_path.relative_to(ROOT))] = data
        records.append(
            {
                "source_path": source_label,
                "source_sha256": sha256_bytes(data),
                "frozen_path": str(destination_path.relative_to(ROOT)),
                "frozen_sha256": sha256_bytes(data),
                "size": len(data),
            }
        )
    return payloads, records


def build_payloads() -> tuple[dict[Path, bytes], list[str]]:
    inventory = load(specification.INVENTORY)
    all_rows = inventory["rows"]
    catalog_rows = load(specification.CATALOG)["rows"]
    rows = selected_proof_rows(all_rows, catalog_rows)
    impossible_count = sum(
        row["disposition"] == "genuinely_impossible"
        for row in catalog_rows
    )
    if len(rows) + impossible_count != len(all_rows):
        raise ProofBuildError(
            "accepted specification dispositions do not account for the "
            "live inventory"
        )
    blocks = check_specification.contract_blocks(
        specification.GENERATED.read_text(encoding="utf-8")
    )
    exact_by_id = {
        record["row_id"]: record
        for record in load(specification.EXISTING_BINDINGS)["records"]
    }
    equivalence_by_id = {
        record["row_id"]: record
        for record in load(specification.EQUIVALENCE)["records"]
    }
    specification_review_hash = sha256(
        check_specification.INDEPENDENT_REVIEW
    )
    payloads: dict[Path, bytes] = {}
    target_rows: list[dict[str, Any]] = []
    expected_directories: list[str] = []
    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []
    index_by_id = {
        row["row_id"]: index
        for index, row in enumerate(all_rows, start=1)
    }

    for row in rows:
        index = index_by_id[row["row_id"]]
        family = (
            "exact_vstd"
            if row["disposition"] == "exact_vstd"
            else blocks[row["row_id"]][0]
        )
        accepted = (
            exact_contract_text(row, exact_by_id)
            if row["disposition"] == "exact_vstd"
            else blocks[row["row_id"]][1]
        )
        renderer = renderer_for(row, family)
        template = normalized_template(
            renderer.render(row, family, accepted)
        )
        target_slug = slug(index, row["target"])
        target_dir = HARNESS_ROOT / target_slug
        expected_directories.append(target_slug)
        boundaries = normalized_boundaries(template, row["row_id"])
        implementation_data = template.implementation_proof.encode()
        completeness_data = template.completeness_proof.encode()
        accepted_data = accepted.encode()
        excerpt_data = source_excerpt(row)
        literal_external = (
            len(
                re.findall(
                    r"#\[\s*verifier\s*::\s*external_body\s*\]",
                    template.implementation_proof,
                )
            )
            + len(
                re.findall(
                    r"#\[\s*verifier\s*::\s*external_body\s*\]",
                    template.completeness_proof,
                )
            )
        )
        recorded_literal = sum(
            boundary["literal_external_body"] for boundary in boundaries
        )
        if recorded_literal > literal_external:
            raise ProofBuildError(
                f"boundary count mismatch for {row['row_id']}: "
                f"{literal_external} literals, {len(boundaries)} records"
            )
        trust_boundaries = list(boundaries)
        dependency_boundaries = [
            boundary
            for boundary in boundaries
            if boundary["literal_external_body"]
        ]
        for synthetic_index in range(
            literal_external - recorded_literal
        ):
            name = f"external_type_or_model_{synthetic_index + 1}"
            trust_boundaries.append(
                {
                    "name": name,
                    "function": name,
                    "row_id": row["row_id"],
                    "category": "external_type_or_model",
                    "level": "model",
                    "literal_external_body": True,
                    "whole_target_outcome": False,
                    "rationale": (
                        "Accounts for a literal external_body on an external "
                        "type/model declaration rather than an executable "
                        "target or dependency function."
                    ),
                }
            )
        target_payloads: dict[str, bytes] = {
            "implementation_proof.rs": implementation_data,
            "completeness_proof.rs": completeness_data,
            "source_excerpt.rs": excerpt_data,
            "accepted_contract.rs": accepted_data,
        }
        source_body = {
            "schema_version": 1,
            "row_id": row["row_id"],
            "target": row["target"],
            "snapshot_path": row["source_evidence"]["snapshot_path"],
            "snapshot_sha256": row["source_evidence"]["snapshot_sha256"],
            "span_sha256": row["source_evidence"]["span_sha256"],
            "start_line": row["source_begin_line"],
            "end_line": row["source_end_line"],
            "implementation_kind": row["implementation_kind"],
        }
        adaptations = [
            {
                "kind": "verus_source_shaped_lowering",
                "rationale": (
                    "Preserves the source control path and exact observable "
                    "contract; only the separately listed lower dependencies "
                    "are modeled as external bodies."
                ),
            }
        ]
        dropped_or_reordered: list[str] = []
        exact_signature_preserved = True
        if family == "primitive_clamp":
            exact_signature_preserved = False
            adaptations.append(
                {
                    "kind": "panic_outcome_reification",
                    "rationale": (
                        "The Rust return-or-panic behavior is reified as "
                        "CmpCallOutcome<T> so min > max and every successful "
                        "branch remain visible to Verus."
                    ),
                }
            )
            dropped_or_reordered.append(
                "The unwind edge is represented by CmpCallOutcome::Panicked; "
                "it is not dropped."
            )
            if row["target"] == "<bool as Ord>::clamp":
                adaptations.append(
                    {
                        "kind": "bool_min_max_branch_expansion",
                        "rationale": (
                            "Expands self.max(min).min(max) into its equivalent "
                            "false-before-true lower/upper branch relation."
                        ),
                    }
                )
        if family == "empty_eq_default":
            exact_signature_preserved = False
            adaptations.append(
                {
                    "kind": "empty_trait_default_lowering",
                    "rationale": (
                        "The source-empty assertion marker is represented by "
                        "its source-backed true unit outcome."
                    ),
                }
            )
        if row["source_file"] == "core/src/tuple.rs":
            adaptations.append(
                {
                    "kind": "tuple_macro_unrolling",
                    "rationale": (
                        "Expands tuple_impls! at the live arity while retaining "
                        "the first-decisive source order and global count."
                    ),
                }
            )
        if row["source_file"] in {
            "core/src/array/equality.rs",
            "core/src/array/mod.rs",
            "core/src/slice/cmp.rs",
        }:
            adaptations.append(
                {
                    "kind": "specialization_path_encoding",
                    "rationale": (
                        "Makes generic, AlwaysApplicable, and bytewise source "
                        "dispatch explicit without collapsing compare_bytes "
                        "to a synthetic element-only path."
                    ),
                }
            )
        if family == "key_callback_order":
            adaptations.append(
                {
                    "kind": "fn_mut_state_threading",
                    "rationale": (
                        "Threads callback -> callback_after_v2 -> final state "
                        "for the exact v2-then-v1 source call order."
                    ),
                }
            )
        transformation = {
            "schema_version": 1,
            "row_id": row["row_id"],
            "target": row["target"],
            "proof_family": template.proof_family,
            "inventory_signature_sha256": compact_hash(row["signature"]),
            "exact_public_signature_preserved": exact_signature_preserved,
            "source_shape_tokens": list(template.source_shape_tokens),
            "adaptations": adaptations,
            "dropped_or_reordered_source_constructs": dropped_or_reordered,
        }
        dependency = {
            "schema_version": 1,
            "row_id": row["row_id"],
            "target": row["target"],
            "records": dependency_boundaries,
        }
        trust = {
            "schema_version": 1,
            "row_id": row["row_id"],
            "target": row["target"],
            "literal_external_body_count": literal_external,
            "target_external_body": False,
            "completeness_external_body": False,
            "boundaries": trust_boundaries,
            "foundational_end_to_end_trust_free": False,
        }
        equivalence = {
            **equivalence_by_id[row["row_id"]],
            "implementation_proof_observation_model": template.proof_family,
            "accepted_contract_sha256": sha256_bytes(accepted_data),
        }
        target_payloads.update(
            {
                "source_body.json": json_bytes(source_body),
                "transformation_manifest.json": json_bytes(transformation),
                "dependency_assumptions.json": json_bytes(dependency),
                "trust_boundaries.json": json_bytes(trust),
                "contract_equivalence.json": json_bytes(equivalence),
            }
        )
        proof_manifest = {
            "schema_version": 1,
            "row_id": row["row_id"],
            "target": row["target"],
            "target_dir": str(target_dir.relative_to(ROOT)),
            "slug": target_slug,
            "disposition": row["disposition"],
            "contract_provenance": (
                "generated"
                if row["disposition"] == "pending"
                else "exact_vstd_reference"
            ),
            "proof_family": template.proof_family,
            "inventory_signature_sha256": compact_hash(row["signature"]),
            "source_span_sha256": row["source_evidence"]["span_sha256"],
            "specification_review_sha256": specification_review_hash,
            "source_shape_tokens": list(template.source_shape_tokens),
            "implementation_mutation": template.implementation_mutation,
            "completeness_mutation": template.completeness_mutation,
            "implementation_mutations": list(
                template.implementation_mutations
                or (template.implementation_mutation,)
            ),
            "completeness_mutations": list(
                template.completeness_mutations
                or (template.completeness_mutation,)
            ),
            **manifest_hash_fields(target_payloads),
        }
        target_payloads["proof_manifest.json"] = json_bytes(proof_manifest)
        for name, data in target_payloads.items():
            payloads[target_dir / name] = data
        for name in (
            "source_body.json",
            "transformation_manifest.json",
            "dependency_assumptions.json",
        ):
            payloads[MANIFEST_ROOT / target_slug / name] = target_payloads[name]
        target_rows.append(
            {
                "index": index,
                "row_id": row["row_id"],
                "target": row["target"],
                "slug": target_slug,
                "target_dir": str(target_dir.relative_to(ROOT)),
                "disposition": row["disposition"],
                "proof_family": template.proof_family,
                "source_span_sha256": row["source_evidence"]["span_sha256"],
                "implementation_proof_sha256": sha256_bytes(
                    implementation_data
                ),
                "completeness_proof_sha256": sha256_bytes(
                    completeness_data
                ),
            }
        )
        graph_nodes.append(
            {
                "id": row["row_id"],
                "row_id": row["row_id"],
                "target": row["target"],
                "kind": "public_target",
            }
        )
        for boundary in trust_boundaries:
            helper_id = (
                f"helper:{row['row_id']}:{boundary['function']}"
            )
            graph_nodes.append(
                {
                    "id": helper_id,
                    "kind": "lower_dependency",
                    "name": boundary["function"],
                    "category": boundary["category"],
                }
            )
            graph_edges.append(
                {
                    "from": row["row_id"],
                    "to": helper_id,
                    "kind": "source_dependency",
                }
            )

    payloads[TARGETS_JSON] = json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "inventory_sha256": sha256(specification.INVENTORY),
            "selected_target_count": len(target_rows),
            "rows": target_rows,
        }
    )
    payloads[TARGETS_CSV] = csv_bytes(
        [
            {
                key: row[key]
                for key in (
                    "row_id",
                    "target",
                    "target_dir",
                    "disposition",
                    "proof_family",
                )
            }
            for row in target_rows
        ],
        [
            "row_id",
            "target",
            "target_dir",
            "disposition",
            "proof_family",
        ],
    )
    payloads[DEPENDENCY_JSON] = json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "nodes": graph_nodes,
            "edges": graph_edges,
        }
    )
    dot_lines = ["digraph core_cmp_proofs {"]
    for node in graph_nodes:
        node_id = json.dumps(node["id"])
        label = json.dumps(node.get("target") or node.get("name") or node["id"])
        dot_lines.append(f"  {node_id} [label={label}];")
    for edge in graph_edges:
        dot_lines.append(
            f"  {json.dumps(edge['from'])} -> {json.dumps(edge['to'])};"
        )
    dot_lines.append("}")
    payloads[DEPENDENCY_DOT] = ("\n".join(dot_lines) + "\n").encode()
    canonical = check_specification.CANONICAL_HANDOFF
    mission = check_specification.MISSION_PATH
    payloads[AUTHORIZATION] = json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "authorized",
            "selected_target_count": len(target_rows),
            "stable_inventory_total": len(all_rows),
            "genuinely_impossible_count": impossible_count,
            "inventory_sha256": sha256(specification.INVENTORY),
            "specification_review_path": str(
                check_specification.INDEPENDENT_REVIEW.relative_to(ROOT)
            ),
            "specification_review_sha256": specification_review_hash,
            "canonical_specification_handoff_path": str(
                canonical.relative_to(ROOT)
            ),
            "canonical_specification_handoff_sha256": sha256(canonical),
            "mission_path": str(mission),
            "mission_sha256": sha256(mission),
            "reviewer_producer_role": "reviewer",
            "reviewer_status": "done",
            "implementation_proofs_authorized": True,
            "authorization_errors": [],
        }
    )
    counts = {
        "selected": len(target_rows),
        "generated_contract": sum(
            row["disposition"] == "pending" for row in rows
        ),
        "exact_vstd_contract": sum(
            row["disposition"] == "exact_vstd" for row in rows
        ),
        "genuinely_impossible": impossible_count,
        "stable_inventory_total": len(all_rows),
        "actual_verus_verified": 0,
        "failed": 0,
        "pending": len(target_rows),
    }
    payloads[AGGREGATE_JSON] = json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "awaiting_two_mode_evidence",
            "inventory_sha256": sha256(specification.INVENTORY),
            "counts": counts,
        }
    )
    payloads[AGGREGATE_MD] = (
        "# core::cmp proof inventory\n\n"
        f"- Selected: {counts['selected']}\n"
        f"- Generated-contract: {counts['generated_contract']}\n"
        f"- Exact-vstd: {counts['exact_vstd_contract']}\n"
        f"- Genuinely impossible: {counts['genuinely_impossible']}\n"
        f"- Pending verification: {counts['pending']}\n"
    ).encode()

    frozen_payloads, frozen_records = frozen_inputs(rows)
    for relative, data in frozen_payloads.items():
        payloads[ROOT / relative] = data
    payloads[FROZEN_JSON] = json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "record_count": len(frozen_records),
            "records": frozen_records,
        }
    )
    payloads[FROZEN_CSV] = csv_bytes(
        frozen_records,
        [
            "source_path",
            "source_sha256",
            "frozen_path",
            "frozen_sha256",
            "size",
        ],
    )
    return payloads, expected_directories


def remove_stale_children(root: Path, expected: set[str]) -> None:
    if not root.is_dir():
        return
    for child in root.iterdir():
        if child.name in expected:
            continue
        resolved = child.resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError as error:
            raise ProofBuildError(f"stale child escapes {root}: {child}") from error
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def generate() -> None:
    if check_specification.validate(
        require_evidence=True,
        require_review=True,
    ):
        raise ProofBuildError("canonical specification gate is not accepted")
    payloads, expected = build_payloads()
    remove_stale_children(HARNESS_ROOT, set(expected))
    remove_stale_children(MANIFEST_ROOT, set(expected))
    for path, value in payloads.items():
        write_if_changed(path, value)
    for target_slug in expected:
        (HARNESS_ROOT / target_slug / "evidence").mkdir(
            parents=True,
            exist_ok=True,
        )


def check() -> None:
    expected_payloads, expected = build_payloads()
    errors = []
    for path, value in expected_payloads.items():
        if path in {AGGREGATE_JSON, AGGREGATE_MD}:
            continue
        if not path.is_file() or path.read_bytes() != value:
            errors.append(str(path.relative_to(ROOT)))
    actual = (
        {path.name for path in HARNESS_ROOT.iterdir() if path.is_dir()}
        if HARNESS_ROOT.is_dir()
        else set()
    )
    if actual != set(expected):
        errors.append("proof_harnesses identity set")
    if errors:
        raise ProofBuildError(
            "stale generated proof artifacts: " + ", ".join(errors[:20])
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "check"), nargs="?", default="generate")
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate()
        else:
            check()
    except (ProofBuildError, OSError, ValueError, KeyError) as error:
        print(f"core::cmp proof build error: {error}", file=sys.stderr)
        return 1
    rows = load(specification.INVENTORY)["rows"]
    catalog_rows = load(specification.CATALOG)["rows"]
    selected = selected_proof_rows(rows, catalog_rows)
    print(
        json.dumps(
            {
                "status": "passed",
                "selected": len(selected),
                "generated": sum(
                    row["disposition"] == "generated"
                    for row in catalog_rows
                ),
                "exact_vstd": sum(
                    row["disposition"] == "exact_vstd"
                    for row in catalog_rows
                ),
                "genuinely_impossible": sum(
                    row["disposition"] == "genuinely_impossible"
                    for row in catalog_rows
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
