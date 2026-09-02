#!/usr/bin/env python3
"""Fail-closed aggregate verification for the Rust 1.96 BTreeMap campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_campaign
import run_verus_matrix
import verify_provenance


POSITIVE_VERUS_RESULT = re.compile(
    r"verification results::\s+\d+ verified, 0 errors"
)
MUTATION_VERUS_RESULT = re.compile(
    r"verification results::\s+\d+ verified, ([1-9]\d*) errors"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


LEGACY_LOWERING_TOKENS = (
    "SourceCallCursor",
    "source_private_",
    "source_semantics",
    "begin_source_lowering",
    "lower_source_call_",
    "PrivateCallEffect",
    "modeled_private_calls",
    "source_effects_well_formed",
    "source_call_transition",
    "source_call_completed",
    "struct SourceState",
    "struct Outcome",
)

ALLOWLISTED_BOUNDARY_KINDS = set(generate_campaign.SOURCE_BOUNDARY_KINDS)


def check_target_local_boundaries(
    target_id: str,
    live_row: Any,
    implementation: str,
) -> list[str]:
    """Reject whole-target contract delegation inside one proof harness.

    The scan is restricted to the target-local lowering section so that the
    shared vocabulary block (external type specifications, uninterpreted
    ordered-map observations and broadcast axioms) is never mistaken for a
    target-local implementation boundary.
    """
    errors: list[str] = []
    prefix = f"{target_id}: "
    analysis = generate_campaign.analyze_target_local_lowering(live_row, implementation)
    if not analysis["has_target_local_section"]:
        return [prefix + "implementation has no target-local lowering section"]
    for token in analysis["legacy_tokens"]:
        errors.append(prefix + f"legacy lowering token {token} remains")
    if analysis["target_external_body"]:
        errors.append(prefix + "public target body is external_body")
    if analysis["target_assume_specification"]:
        errors.append(prefix + "public target is assumed by assume_specification")
    if not analysis["target_body_is_executable"]:
        errors.append(prefix + "public target body is not executable")
    if (
        not analysis["boundaries"]
        and not analysis["has_executable_source_call"]
    ):
        errors.append(
            prefix
            + "target has neither an operation-local boundary nor an executable "
            "source call"
        )
    for boundary in analysis["malformed_boundaries"]:
        for problem in boundary["problems"]:
            errors.append(
                prefix + f"boundary {boundary['name']}: {problem}"
            )
    for name in analysis["unused_boundaries"]:
        errors.append(prefix + f"declared boundary {name} is never used")
    for name in analysis["undeclared_external_boundaries"]:
        errors.append(
            prefix
            + f"target-local external_body helper {name} has no boundary declaration"
        )
    for name in analysis["contract_cloning_boundaries"]:
        errors.append(
            prefix
            + f"boundary {name} duplicates or subsumes the whole target contract"
        )
    for boundary in analysis["boundaries"]:
        if boundary["kind"] not in ALLOWLISTED_BOUNDARY_KINDS:
            errors.append(
                prefix + f"boundary {boundary['name']} kind is not allowlisted"
            )
    delegation = analysis["terminal_delegation"]
    if delegation is not None and not delegation["allowed"]:
        errors.append(
            prefix
            + "target returns the unchanged result of terminal external boundary "
            + f"{delegation['boundary']}"
        )
    return errors


def expected_mutation_manifest(live_row: Any) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "target_id": live_row.target_id,
        "scope": "accepted_public_target_postconditions",
        "selection_policy": (
            "negate every textually distinct accepted public "
            "postcondition (only the behavioral consequent for a "
            "top-level implication), retain every other contract "
            "clause and all preconditions, and execute an independent "
            "copy of the source-shaped target body"
        ),
        "accepted_public_postcondition_count": len(
            generate_campaign.source_lowering_plan(live_row).ensures
        ),
        "mutated_public_postcondition_count": len(
            generate_campaign.behavioral_mutations(live_row)
        ),
        "unmutated_public_postconditions": [],
        "excluded_mutation_scopes": [
            (
                "operation-local external boundary contracts are trust "
                "accounting surfaces, not executable implementation bodies"
            )
        ],
        "mutants": [
            generate_campaign.mutation_manifest_entry(live_row, mutation)
            for mutation in generate_campaign.behavioral_mutations(live_row)
        ],
    }


def check_mutation_artifacts(
    target_id: str,
    live_row: Any,
    mutation_source: str,
    manifest: dict[str, Any],
) -> list[str]:
    """Bind every recorded mutation to one unique generated function."""

    errors: list[str] = []
    expected = expected_mutation_manifest(live_row)
    if manifest != expected:
        errors.append(f"{target_id}: mutation manifest differs from generated code")
    if mutation_source != generate_campaign.mutation_harness_source(live_row):
        errors.append(f"{target_id}: mutation harness differs from generator output")
    base_source = generate_campaign.mutation_harness_base_source(
        live_row, mutation_source
    )
    if base_source != generate_campaign.implementation_harness_source(live_row):
        errors.append(
            f"{target_id}: non-mutant harness content differs from implementation"
        )

    mutations = generate_campaign.behavioral_mutations(live_row)
    fingerprints = [mutation.fingerprint_sha256 for mutation in mutations]
    if len(fingerprints) != len(set(fingerprints)):
        errors.append(f"{target_id}: mutation fingerprints are not distinct")
    manifest_fingerprints = [
        mutant.get("fingerprint_sha256")
        for mutant in manifest.get("mutants", [])
    ]
    if len(manifest_fingerprints) != len(set(manifest_fingerprints)):
        errors.append(f"{target_id}: manifested mutations are not distinct")
    artifact_hashes = [
        mutant.get("verification_artifact_sha256")
        for mutant in manifest.get("mutants", [])
    ]
    if len(artifact_hashes) != len(set(artifact_hashes)):
        errors.append(
            f"{target_id}: mutation verification artifacts are not distinct"
        )

    expected_functions = {mutation.function for mutation in mutations}
    emitted_functions = set(
        re.findall(
            r"pub\s+(?:proof\s+)?fn\s+(mutation_[A-Za-z0-9_]+)\b",
            mutation_source,
        )
    )
    if emitted_functions != expected_functions:
        errors.append(
            f"{target_id}: mutation function set differs from manifest"
        )
    for mutation in mutations:
        rendered = generate_campaign.render_behavioral_mutation(
            live_row, mutation
        )
        if mutation_source.count(rendered) != 1:
            errors.append(
                f"{target_id}: {mutation.function} does not exactly match "
                "its manifested operation, preconditions, and postcondition"
            )
        target_call = f"rust_1_96_target_{live_row.item_id}("
        if target_call in rendered:
            errors.append(
                f"{target_id}: {mutation.function} calls the verified target "
                "instead of executing a copied source-shaped body"
            )
        body = generate_campaign.target_function_body(
            (
                f"{generate_campaign.TARGET_LOCAL_SECTION_BEGIN}\n"
                "verus! {\n\n"
                + rendered.replace(
                    f"pub fn {mutation.function}",
                    f"pub fn rust_1_96_target_{live_row.item_id}",
                    1,
                )
                + "\n\n}\n"
                + generate_campaign.TARGET_LOCAL_SECTION_END
            ),
            live_row.item_id,
        )
        expected_body = "\n".join(
            generate_campaign.source_lowering_plan(live_row).body
        )
        if body != expected_body:
            errors.append(
                f"{target_id}: {mutation.function} does not execute the "
                "source-shaped target body"
            )
    return errors


def verify_phase_order_record(selected_rows: list[Any]) -> list[str]:
    errors: list[str] = []
    path = ROOT / "verification/premature_phase_ordering.json"
    if not path.is_file():
        return ["phase-order archival record is missing"]
    record = load_json(path)
    review_path = ROOT / "reviews/inventory_specification.json"
    file_count, tree_sha256 = generate_campaign.generated_harness_tree_digest(
        selected_rows
    )
    expected_files = list(generate_campaign.GENERATED_HARNESS_FILES)
    if (
        record.get("schema_version") != 2
        or record.get("record_kind") != "phase_order_archive"
        or not record.get("proof_phase_authorized")
        or not record.get("proof_tree_generated_after_authorization")
    ):
        errors.append("phase-order archival record is not post-authorization")
    if (
        record.get("generated_harness_files") != expected_files
        or record.get("file_count") != file_count
        or record.get("tree_sha256") != tree_sha256
    ):
        errors.append("phase-order generated proof-tree binding is stale")
    if (
        record.get("authorization_review")
        != "reviews/inventory_specification.json"
        or not review_path.is_file()
        or record.get("authorization_review_sha256")
        != sha256_file(review_path)
    ):
        errors.append("phase-order authorization review binding is stale")
    if record.get("accepted_as_proof_evidence"):
        latest_path = (
            ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
        )
        latest = load_json(latest_path) if latest_path.is_file() else {}
        if (
            record.get("proof_status")
            != "accepted_by_fresh_post_authorization_matrix"
            or record.get("verus_matrix_manifest")
            != "verification/evidence/verus_matrix/latest_manifest.json"
            or record.get("verus_matrix_manifest_sha256")
            != (sha256_file(latest_path) if latest_path.is_file() else None)
            or record.get("verus_matrix_run_id") != latest.get("run_id")
            or record.get("verus_matrix_summary_sha256")
            != latest.get("summary_sha256")
        ):
            errors.append("phase-order dynamic evidence binding is stale")
    elif record.get("proof_status") != "generated_pending_fresh_dynamic_evidence":
        errors.append("phase-order proof status is inconsistent")
    return errors


def verify_static(*, include_proofs: bool = True) -> list[str]:
    errors: list[str] = []
    provenance_errors = verify_provenance.verify_manifest(
        verify_provenance.load_manifest(), ROOT
    )
    errors.extend(f"provenance: {error}" for error in provenance_errors)

    rustdoc = load_json(generate_campaign.RUSTDOC)
    live_rows, live_exclusions = generate_campaign.derive_inventory(rustdoc["index"])
    for live_row in live_rows:
        live_row.semantic_family = generate_campaign.semantic_family(live_row)
        live_row.principal_behavior = generate_campaign.principal_behavior(live_row)
        live_row.canonical_target = generate_campaign.canonical_target(live_row)
        live_row.proxy_signature = generate_campaign.proxy_parts(live_row)[0]
    inventory_path = ROOT / "inventory/btree_map_exec_fn_inventory.json"
    catalog_path = ROOT / "specs/all_btree_map_specs.json"
    if not inventory_path.is_file() or not catalog_path.is_file():
        return [*errors, "missing inventory or all-spec catalog"]
    inventory = load_json(inventory_path)
    catalog = load_json(catalog_path)
    rows = inventory["rows"]
    live_keys = [
        (row.owner["name"], row.trait, row.function["name"], row.item_id)
        for row in live_rows
    ]
    stored_keys = [
        (row["owner_type"], row["trait"], row["method"], row["rustdoc_item_id"])
        for row in rows
    ]
    if stored_keys != live_keys:
        errors.append("stored inventory differs from live Rustdoc/source derivation")
    expected_counts = {
        "stable_inventory_total": len(live_rows),
        "exact_vstd": sum(row.disposition == "exact_vstd" for row in live_rows),
        "generated": sum(row.disposition == "generated" for row in live_rows),
        "genuinely_impossible": sum(
            row.disposition == "genuinely_impossible" for row in live_rows
        ),
        "pending": sum(row.disposition == "pending" for row in live_rows),
    }
    if inventory["counts"] != expected_counts:
        errors.append(f"inventory counts differ: {inventory['counts']}")
    if catalog["counts"]["stable_inventory_total"] != len(rows):
        errors.append("all-spec catalog total differs from inventory")
    if catalog["counts"]["specified_total"] != 150:
        errors.append("all-spec catalog specified total is not 150")
    if catalog["counts"]["strict_specification_coverage"] != 150 / 151:
        errors.append("strict specification coverage is not 150/151")
    catalog_ids = [row["target_id"] for row in catalog["rows"]]
    target_ids = [row["target_id"] for row in rows]
    if catalog_ids != target_ids or len(set(target_ids)) != len(target_ids):
        errors.append("catalog/inventory target IDs are missing, extra, or duplicated")

    exclusion_path = ROOT / "inventory/unstable_non_executable_exclusions.json"
    exclusions = load_json(exclusion_path)["rows"]
    if len(exclusions) != len(live_exclusions):
        errors.append("stored exclusion rows differ from live derivation")
    if sum(item["kind"] == "implicit_lifecycle_hook" for item in exclusions) != 2:
        errors.append("implicit Drop lifecycle hooks are not explicitly accounted")

    generated_path = ROOT / "specs/generated_btree_map_specs.rs"
    vocabulary_path = ROOT / "specs/btree_map_shared_vocabulary.rs"
    generated = generated_path.read_text()
    vocabulary = vocabulary_path.read_text()
    if generated.count("pub assume_specification") != 137:
        errors.append("generated spec file does not contain 137 direct assume specifications")
    if "axiom_btree_map_extend_refs" in vocabulary:
        errors.append("unbound reference Extend axiom remains in shared vocabulary")
    impossible_packets = (("extend_ref_outlives.json", 3),)
    for filename, attempt_count in impossible_packets:
        impossible = load_json(ROOT / "impossibility" / filename)
        if impossible["status"] not in {
            "pending_independent_row_approval",
            "accepted_by_independent_reviewer",
        }:
            errors.append(f"{filename}: impossibility packet has invalid status")
        if len(impossible["attempts"]) != attempt_count:
            errors.append(
                f"{filename}: expected {attempt_count} concrete attempts"
            )
    index_row = next(row for row in rows if row["trait"] == "Index")
    if index_row["contract"]["requires"] != []:
        errors.append("Index direct contract incorrectly records a local requires clause")
    if index_row["contract"]["ensures"] != [
        (
            "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() "
            "==> maps_borrowed_key_to_value(this@, key, *result)"
        )
    ]:
        errors.append("Index recorded ensures differs from emitted assume specification")
    if len(index_row["contract"].get("inherited_requires", [])) != 1:
        errors.append("Index inherited IndexSpec precondition bridge is missing")
    if "axiom_btree_map_index_req" not in vocabulary:
        errors.append("IndexSpec borrowed-membership bridge is missing")
    resolution = load_json(ROOT / "research/index_binding_resolution.json")
    expected_resolution_contract = {
        "direct_requires": index_row["contract"]["requires"],
        "inherited_requires": index_row["contract"]["inherited_requires"],
        "ensures": index_row["contract"]["ensures"],
    }
    if resolution["accepted_contract"] != expected_resolution_contract:
        errors.append("Index resolution accepted contract differs from inventory record")
    if resolution["target"]["contract"] != index_row["contract"]:
        errors.append("Index resolution embedded target differs from inventory record")
    forbidden = ("ensures true", "requires false", "arbitrary()")
    for pattern in forbidden:
        if pattern in generated:
            errors.append(f"anti-vacuity violation in generated specs: {pattern}")

    generated_rows = [row for row in rows if row["disposition"] == "generated"]
    for row in generated_rows:
        live_row = next(
            live_row
            for live_row in live_rows
            if live_row.item_id == row["rustdoc_item_id"]
        )
        guard = generate_campaign.comparison_guard(live_row)
        for clause in row["contract"]["requires"]:
            if clause.startswith("key_obeys_cmp_spec"):
                errors.append(
                    f"{row['target_id']}: caller obligation is comparator-guarded"
                )
        for clause in row["contract"]["ensures"]:
            guarded = clause.startswith("key_obeys_cmp_spec")
            if guard is not None and not clause.startswith(f"{guard} ==>"):
                errors.append(f"{row['target_id']}: behavior lacks comparator guard")
            if guard is None and guarded:
                errors.append(
                    f"{row['target_id']}: order-independent behavior is comparator-guarded"
                )
    required_vocabulary = (
        "pub open spec fn ordered_range_domain",
        "pub open spec fn ordered_key_in_range",
        "pub open spec fn ordered_split_partition",
        "pub open spec fn ordered_callback_filter",
        "pub open spec fn extract_if_lifecycle",
        "pub open spec fn extract_if_state_coherent",
        "pub open spec fn extract_if_callback_model_functional",
        "pub uninterp spec fn extract_if_yielded_pairs",
        "pub uninterp spec fn extract_if_current_map",
        "pub trait ExtractIfIteratorModel",
        "pub open spec fn ordered_callback_unwind_contract",
        "pub open spec fn borrowed_removal_functional",
        "pub uninterp spec fn borrowed_key_value_updated",
        "pub open spec fn owning_iterator_transfer",
        "pub uninterp spec fn ordered_handle_final_map",
        "pub open spec fn ordered_map_cmp",
        "pub open spec fn ordered_map_partial_cmp",
    )
    for declaration in required_vocabulary:
        if declaration not in vocabulary:
            errors.append(f"missing source-backed shared vocabulary: {declaration}")
    for forbidden_helper in (
        "mutable_lookup_frame",
        "pub uninterp spec fn ordered_key_in_range",
        "pub uninterp spec fn ordered_split_partition",
        "pub uninterp spec fn ordered_callback_filter<",
        "pub uninterp spec fn extract_if_initial",
        "entry_return_map",
        "entry_consumed_post_map",
        "entry_branch_result",
        "pub uninterp spec fn entry_mutable_frame",
        "pub uninterp spec fn entry_and_modify_transition",
    ):
        if forbidden_helper in vocabulary:
            errors.append(f"opaque principal-behavior helper remains: {forbidden_helper}")
    if ".ordered_remaining().drop_first()" not in generated:
        errors.append("forward iterator contracts do not preserve exact remaining sequence")
    if ".ordered_remaining().drop_last()" not in generated:
        errors.append("backward iterator contracts do not preserve exact remaining sequence")
    extract_if_row = next(
        row
        for row in generated_rows
        if row["rustdoc_item_id"] == 1413
    )
    extract_if_ensures = extract_if_row["contract"]["ensures"]
    for required_clause in (
        "final(this)@ == old(this)@",
        "extract_if_visited_keys::<K, V, _>(&result) == Seq::<K>::empty()",
        (
            "extract_if_yielded_pairs::<K, V, _>(&result)"
            " == Seq::<(K, V)>::empty()"
        ),
        "extract_if_current_map::<K, V, _>(&result) == old(this)@",
        "ordered_callback_unwind_contract",
    ):
        if not any(required_clause in clause for clause in extract_if_ensures):
            errors.append(
                f"{extract_if_row['target_id']}: missing construction clause "
                f"{required_clause}"
            )
    extract_if_next = next(
        row
        for row in generated_rows
        if row["rustdoc_item_id"] == 1854
    )
    next_contract = " ".join(extract_if_next["contract"]["ensures"])
    for required_clause in (
        "extract_next_consumed_keys",
        "extract_current_map",
        "extract_yielded_pairs",
        "extract_state_coherent",
    ):
        if required_clause not in next_contract:
            errors.append(
                f"{extract_if_next['target_id']}: missing ExtractIf next "
                f"transition clause {required_clause}"
            )
    extract_if_size_hint = next(
        row
        for row in generated_rows
        if row["rustdoc_item_id"] == 1855
    )
    if not any(
        "this.extract_current_map().len()" in clause
        for clause in extract_if_size_hint["contract"]["ensures"]
    ):
        errors.append(
            f"{extract_if_size_hint['target_id']}: upper size hint is not "
            "the live borrowed-map length"
        )
    retain_row = next(
        row
        for row in generated_rows
        if row["rustdoc_item_id"] == 1404
    )
    if not any(
        "ordered_callback_unwind_contract" in clause
        for clause in retain_row["contract"]["ensures"]
    ):
        errors.append(
            f"{retain_row['target_id']}: callback unwind retention is missing"
        )
    if generated.count("ordered_callback_unwind_contract") < 2:
        errors.append("callback unwind retention is not emitted for both callback APIs")
    if vocabulary.count(
        "#[verifier::prophetic]\n#[verifier::prophetic]"
    ):
        errors.append("duplicated prophetic attribute remains in shared vocabulary")

    static_audits = (
        "source_binding_audit.json",
        "signature_generic_shape_audit.json",
        "source_fidelity_audit.json",
        "anti_vacuity_audit.json",
        "shared_helper_usage_audit.json",
        "outcome_equivalence_audit.json",
        "inventory_exclusion_audit.json",
        "phase_ordering_audit.json",
    )
    for name in static_audits:
        path = ROOT / "verification/audits" / name
        if not path.is_file() or not load_json(path)["status"].startswith("passed"):
            errors.append(f"static audit not passed: {name}")
    if not include_proofs:
        return errors

    harness_root = ROOT / "proof_harnesses"
    actual_dirs = {path.name for path in harness_root.iterdir() if path.is_dir()}
    selected_rows = [
        row for row in rows if row["disposition"] in {"exact_vstd", "generated"}
    ]
    expected_dirs = {row["target_id"] for row in selected_rows}
    if actual_dirs != expected_dirs:
        errors.append(
            f"proof_harness directory mismatch missing={sorted(expected_dirs-actual_dirs)} "
            f"extra={sorted(actual_dirs-expected_dirs)}"
        )
    selected_live_rows = [
        next(
            live_row
            for live_row in live_rows
            if live_row.item_id == row["rustdoc_item_id"]
        )
        for row in selected_rows
    ]
    errors.extend(verify_phase_order_record(selected_live_rows))
    required = {
        "implementation_proof.rs",
        "completeness_proof.rs",
        "mutation_proof.rs",
        "source_excerpt.rs",
        "contract_binding.json",
        "contract_equivalence.json",
        "transformation_manifest.json",
        "dependency_assumptions.json",
        "trust_boundaries.json",
        "mutations.json",
    }
    literal_external_body = 0
    for row in selected_rows:
        target_root = harness_root / row["target_id"]
        missing = sorted(name for name in required if not (target_root / name).is_file())
        if missing:
            errors.append(f"{row['target_id']}: missing harness files {missing}")
            continue
        excerpt = target_root / "source_excerpt.rs"
        if sha256_file(excerpt) != row["source_sha256"]:
            errors.append(f"{row['target_id']}: source excerpt hash mismatch")
        implementation = (target_root / "implementation_proof.rs").read_text()
        completeness = (target_root / "completeness_proof.rs").read_text()
        mutation = (target_root / "mutation_proof.rs").read_text()
        proof_texts = {
            "implementation_proof.rs": implementation,
            "completeness_proof.rs": completeness,
            "mutation_proof.rs": mutation,
        }
        literal_by_file = {
            name: text.count("#[verifier::external_body]")
            for name, text in proof_texts.items()
        }
        target_literal_external_body = sum(literal_by_file.values())
        literal_external_body += target_literal_external_body
        if "SourceState" in implementation or "struct Outcome" in implementation:
            errors.append(f"{row['target_id']}: scalar implementation proxy remains")
        if "SourceState" in completeness or "struct Outcome" in completeness:
            errors.append(f"{row['target_id']}: scalar completeness proxy remains")
        if "extern crate alloc;" not in implementation:
            errors.append(
                f"{row['target_id']}: implementation lacks the alloc crate binding"
            )
        for token in LEGACY_LOWERING_TOKENS:
            if token in implementation:
                errors.append(
                    f"{row['target_id']}: legacy lowering token {token} remains"
                )
        if "pub assume_specification" in implementation:
            errors.append(
                f"{row['target_id']}: implementation redeclares an assumed public target"
            )
        contract_text = json.dumps(row["contract"], sort_keys=True)
        contract_hash = hashlib.sha256(contract_text.encode()).hexdigest()
        for proof_name, text in (
            ("implementation_proof.rs", implementation),
            ("completeness_proof.rs", completeness),
        ):
            if f"Accepted contract sha256: {contract_hash}" not in text:
                errors.append(
                    f"{row['target_id']}: {proof_name} lacks exact contract hash binding"
                )
        if f"pub fn rust_1_96_target_{row['rustdoc_item_id']}" not in implementation:
            errors.append(f"{row['target_id']}: target implementation body is not executable")
        live_row = next(
            item
            for item in live_rows
            if item.item_id == row["rustdoc_item_id"]
        )
        _, live_inputs, live_output, live_where, proof_requires, proof_ensures = (
            generate_campaign.proof_contract(live_row)
        )
        if implementation != generate_campaign.implementation_harness_source(
            live_row
        ):
            errors.append(
                f"{row['target_id']}: implementation harness differs from "
                "generator output"
            )
        if completeness != generate_campaign.completeness_harness_source(
            live_row
        ):
            errors.append(
                f"{row['target_id']}: completeness harness differs from "
                "generator output"
            )
        target_call = generate_campaign.actual_target_call(live_row, live_inputs)
        target_marker = f"pub fn rust_1_96_target_{row['rustdoc_item_id']}"
        target_body = implementation.split(target_marker, 1)[1]
        if target_call in implementation:
            errors.append(
                f"{row['target_id']}: circular same-target API call remains"
            )
        errors.extend(
            check_target_local_boundaries(
                row["target_id"], live_row, implementation
            )
        )
        expected_calls = generate_campaign.source_call_names(live_row)
        expected_boundaries = generate_campaign.source_boundary_names(live_row)
        declared_boundaries = [
            boundary["boundary-op"]
            for boundary in generate_campaign.parse_target_local_boundaries(
                implementation
            )
        ]
        if declared_boundaries != expected_boundaries:
            errors.append(
                f"{row['target_id']}: declared operation-local boundaries are stale"
            )
        executable_body = generate_campaign.target_function_body(
            implementation, row["rustdoc_item_id"]
        )
        for boundary_name in expected_boundaries:
            if f"{boundary_name}(" not in executable_body:
                errors.append(
                    f"{row['target_id']}: boundary {boundary_name} is not composed "
                    "by the executable target body"
                )
        for _, rust_type, _ in live_inputs:
            if rust_type not in target_body.split("    ensures", 1)[0]:
                errors.append(
                    f"{row['target_id']}: implementation signature lost type {rust_type}"
                )
        if live_output is not None and live_output not in target_body.split(
            "    ensures", 1
        )[0]:
            errors.append(
                f"{row['target_id']}: implementation signature lost output {live_output}"
            )
        target_header = target_body.split("    let mut source_cursor", 1)[0]
        for clause in proof_ensures:
            if clause not in target_header:
                errors.append(
                    f"{row['target_id']}: implementation omits contract clause {clause}"
                )
        if "pub proof fn completeness" not in completeness:
            errors.append(f"{row['target_id']}: completeness proof is absent")
        if "pub open spec fn equivalent" not in completeness:
            errors.append(f"{row['target_id']}: completeness equivalence is absent")
        if "SourceState" in completeness or "Outcome" in completeness:
            errors.append(f"{row['target_id']}: completeness uses a scalar proxy type")
        if "assume(" in completeness:
            errors.append(f"{row['target_id']}: completeness contains an assumption")
        theorem_header = completeness.split("pub proof fn completeness", 1)[-1].split(
            "    requires", 1
        )[0]
        for predicate in generate_campaign.split_top_level_predicates(live_where):
            if predicate not in theorem_header:
                errors.append(
                    f"{row['target_id']}: completeness omits generic bound {predicate}"
                )
        lifetime_erased_output = (
            re.sub(
                r"&'[A-Za-z_][A-Za-z0-9_]*\s+",
                "&",
                live_output,
            )
            if live_output is not None
            else None
        )
        mutable_lifetime_erased_output = (
            re.sub(
                r"&'[A-Za-z_][A-Za-z0-9_]*\s+mut\b",
                "&mut",
                live_output,
            )
            if live_output is not None
            else None
        )
        if (
            live_output is not None
            and live_output not in completeness
            and lifetime_erased_output not in completeness
            and mutable_lifetime_erased_output not in completeness
        ):
            errors.append(
                f"{row['target_id']}: completeness omits the actual result type"
            )
        for name, rust_type, _ in live_inputs:
            if rust_type.startswith("&") and "mut " in rust_type:
                base = re.sub(
                    r"^&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\s+",
                    "",
                    rust_type,
                )
                for prefix in ("post1_", "post2_"):
                    if f"{prefix}{name}: {base}" not in completeness:
                        errors.append(
                            f"{row['target_id']}: completeness omits "
                            f"{prefix}{name}: {base}"
                        )
        equivalence = load_json(target_root / "contract_equivalence.json")
        if f"Contract class: {equivalence['kind']}" not in completeness:
            errors.append(f"{row['target_id']}: completeness equivalence class mismatch")
        relative_requires = generate_campaign.completeness_relative_requires(
            live_row
        )
        if equivalence.get("completeness_requires") != relative_requires:
            errors.append(
                f"{row['target_id']}: completeness functionality boundary is stale"
            )
        for clause in relative_requires:
            if clause not in completeness:
                errors.append(
                    f"{row['target_id']}: completeness omits relative hypothesis {clause}"
                )
        mutation_manifest = load_json(target_root / "mutations.json")
        errors.extend(
            check_mutation_artifacts(
                row["target_id"],
                live_row,
                mutation,
                mutation_manifest,
            )
        )
        binding = load_json(target_root / "contract_binding.json")
        if binding["contract"] != row["contract"]:
            errors.append(f"{row['target_id']}: harness contract binding differs from inventory")
        if binding["model_profile"] not in implementation:
            # The profile appears in transformation metadata and is encoded in the body;
            # requiring it in the source comment prevents accidental template drift.
            errors.append(f"{row['target_id']}: model profile is absent from implementation")
        clause_count = (
            len(row["contract"]["requires"])
            + len(row["contract"].get("inherited_requires", []))
            + len(row["contract"]["ensures"])
        )
        if len(binding["projection"]) != clause_count:
            errors.append(f"{row['target_id']}: contract projection is not clause-complete")
        transformation = load_json(target_root / "transformation_manifest.json")
        recorded_calls = [
            item["source_call"] for item in transformation["source_call_lowerings"]
        ]
        if recorded_calls != expected_calls:
            errors.append(f"{row['target_id']}: source-call lowering list is stale")
        if any(call in {"let", "where", "match", "if", "for", "while"} for call in recorded_calls):
            errors.append(f"{row['target_id']}: source-call lowering contains a keyword")
        realizations = generate_campaign.source_call_realizations(live_row)
        for index, call in enumerate(transformation["source_call_lowerings"]):
            expected_flags = generate_campaign.source_call_effect_flags(
                live_row,
                call["source_call"],
                index,
                live_inputs,
            )
            if call.get("modeled_effects") != expected_flags:
                errors.append(
                    f"{row['target_id']}: private-call effects are missing or stale"
                )
            if "lowered_to" in call:
                errors.append(
                    f"{row['target_id']}: stale cursor lowering reference remains"
                )
            realized_by = call.get("realized_by")
            if realized_by != realizations.get(call["source_call"]):
                errors.append(
                    f"{row['target_id']}: source call {call['source_call']} is not "
                    "bound to its realising operation"
                )
            if realized_by not in set(expected_boundaries) | {"target_control_flow"}:
                errors.append(
                    f"{row['target_id']}: source call {call['source_call']} names an "
                    "unknown realising operation"
                )
        if "retained_private_boundary" in transformation:
            errors.append(
                f"{row['target_id']}: transformation manifest still claims a private "
                "source closure boundary"
            )
        recorded_boundaries = transformation.get("retained_operation_local_boundaries")
        if recorded_boundaries != generate_campaign.source_boundary_manifest(live_row):
            errors.append(
                f"{row['target_id']}: operation-local boundary manifest is stale"
            )
        for boundary in recorded_boundaries or []:
            for field in (
                "name",
                "kind",
                "modeled_source_operation",
                "source_span",
                "source_sha256",
                "source_tokens",
                "footprint",
                "mode",
            ):
                if not boundary.get(field):
                    errors.append(
                        f"{row['target_id']}: boundary {boundary.get('name')} lacks {field}"
                    )
            footprint = boundary.get("footprint") or {}
            if not footprint.get("reads") or not footprint.get("writes"):
                errors.append(
                    f"{row['target_id']}: boundary {boundary.get('name')} lacks a footprint"
                )
        trust = load_json(target_root / "trust_boundaries.json")
        expected_trust_scan = generate_campaign.scan_harness_trust(
            target_root,
            live_row,
            generate_campaign.derive_trust_categories(live_row),
        )
        if trust != expected_trust_scan:
            errors.append(f"{row['target_id']}: trust metadata misstates target markers")
        if trust.get("target_external_body") or trust.get(
            "target_assume_specification"
        ):
            errors.append(f"{row['target_id']}: target-level trust boundary remains")
        for stale in (
            "private_source_closure_boundary",
            "private_source_closure_covers_target_contract",
        ):
            if stale in trust:
                errors.append(
                    f"{row['target_id']}: trust metadata still claims {stale}"
                )
        if trust.get("boundary_covers_target_contract"):
            errors.append(
                f"{row['target_id']}: an operation-local boundary covers the whole "
                "target contract"
            )
        if trust.get("legacy_lowering_tokens"):
            errors.append(
                f"{row['target_id']}: trust metadata records legacy lowering tokens"
            )
        if (
            not trust.get("operation_local_boundaries")
            and not generate_campaign.analyze_target_local_lowering(
                live_row, implementation
            )["has_executable_source_call"]
        ):
            errors.append(
                f"{row['target_id']}: trust metadata lists neither an "
                "operation-local boundary nor an executable source call"
            )
        manifest_root = ROOT / "proof_manifests" / row["target_id"]
        for name in (
            "source_body.json",
            "transformation_manifest.json",
            "dependency_assumption_manifest.json",
        ):
            if not (manifest_root / name).is_file():
                errors.append(f"{row['target_id']}: missing proof manifest {name}")
    if literal_external_body <= 0:
        errors.append("shared external type/model boundaries were not accounted")

    frozen = load_json(ROOT / "frozen_inputs/file_manifest.json")
    if len(frozen["targets"]) != len(selected_rows):
        errors.append("frozen input target binding count differs from inventory")
    if frozen["source_manifest_sha256"] != sha256_file(
        ROOT / "provenance/source_manifest.json"
    ):
        errors.append("frozen source manifest hash is stale")
    return errors


def verify_verus_evidence(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    latest_path = ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
    if not latest_path.is_file():
        return ["missing active Verus matrix manifest"]
    latest = load_json(latest_path)
    summary_path = ROOT / latest["summary"]
    if not summary_path.is_file():
        return ["active Verus matrix summary is missing"]
    if sha256_file(summary_path) != latest["summary_sha256"]:
        errors.append("active Verus matrix summary hash is stale")
    summary = load_json(summary_path)
    phase = load_json(ROOT / "verification/premature_phase_ordering.json")
    run_manifest_path = ROOT / latest["run_root"] / "manifest.json"
    run_manifest = (
        load_json(run_manifest_path) if run_manifest_path.is_file() else {}
    )
    source_snapshot = run_manifest.get("source_snapshot") or {}
    if (
        not summary.get("artifact_tree_unchanged")
        or summary.get("generated_harness_tree_sha256")
        != phase.get("tree_sha256")
        or source_snapshot.get("generated_harness_tree_sha256")
        != phase.get("tree_sha256")
        or source_snapshot.get("generated_harness_file_count")
        != phase.get("file_count")
    ):
        errors.append("Verus matrix does not bind one unchanged generated tree")
    expected = len(rows)
    for field in (
        "passed_targets",
        "implementation_actual_verus_verified",
        "completeness_actual_verus_verified",
        "mutations_rejected",
    ):
        if summary.get(field) != expected:
            errors.append(f"Verus matrix {field}={summary.get(field)} != {expected}")
    expected_mutation_functions = sum(
        len(
            load_json(
                ROOT
                / "proof_harnesses"
                / row["target_id"]
                / "mutations.json"
            )["mutants"]
        )
        for row in rows
    )
    if (
        summary.get("expected_mutation_functions")
        != expected_mutation_functions
        or summary.get("mutation_functions_rejected")
        != expected_mutation_functions
    ):
        errors.append(
            "Verus matrix mutation function rejection count is incomplete"
        )
    if summary.get("status") != "passed" or not summary.get("generated_spec_no_verify"):
        errors.append("Verus matrix did not pass all modes")
    evidence_names = (
        "implementation_no_verify",
        "implementation_actual_verus",
        "completeness_no_verify",
        "completeness_actual_verus",
        "mutation_actual_verus",
    )
    for row in rows:
        evidence = ROOT / "proof_harnesses" / row["target_id"] / "evidence"
        for name in evidence_names:
            record_path = evidence / f"{name}.json"
            if not record_path.is_file():
                errors.append(f"{row['target_id']}: missing evidence {name}")
                continue
            record = load_json(record_path)
            if not record.get("passed"):
                errors.append(f"{row['target_id']}: failed evidence {name}")
            source = ROOT / record["source"]
            if not source.is_file() or sha256_file(source) != record["source_sha256"]:
                errors.append(f"{row['target_id']}: stale evidence input {name}")
            stdout_path = evidence / f"{name}.stdout"
            stderr_path = evidence / f"{name}.stderr"
            if not stdout_path.is_file() or not stderr_path.is_file():
                errors.append(f"{row['target_id']}: missing output sidecars {name}")
                continue
            stdout = stdout_path.read_text()
            stderr = stderr_path.read_text()
            if (
                hashlib.sha256(stdout.encode()).hexdigest()
                != record.get("stdout_sha256")
                or hashlib.sha256(stderr.encode()).hexdigest()
                != record.get("stderr_sha256")
            ):
                errors.append(f"{row['target_id']}: stale output sidecars {name}")
            combined = stdout + "\n" + stderr
            if name in {
                "implementation_actual_verus",
                "completeness_actual_verus",
            } and POSITIVE_VERUS_RESULT.search(combined) is None:
                errors.append(f"{row['target_id']}: missing positive Verus result {name}")
            if name == "mutation_actual_verus":
                match = MUTATION_VERUS_RESULT.search(combined)
                rejected = int(match.group(1)) if match is not None else 0
                mutation_manifest = load_json(
                    ROOT
                    / "proof_harnesses"
                    / row["target_id"]
                    / "mutations.json"
                )
                expected_names = [
                    mutant["function"]
                    for mutant in mutation_manifest["mutants"]
                ]
                expected_rejected = len(expected_names)
                diagnostic_analysis = (
                    run_verus_matrix.analyze_mutation_diagnostics(
                        source.read_text(),
                        combined,
                        expected_names,
                    )
                )
                if (
                    rejected != expected_rejected
                    or not diagnostic_analysis["passed"]
                    or record.get("expected_mutation_functions")
                    != expected_rejected
                    or record.get("expected_mutation_function_names")
                    != expected_names
                    or record.get("rejected_mutation_functions") != rejected
                    or sorted(
                        record.get("rejected_mutation_function_names") or []
                    )
                    != sorted(expected_names)
                    or record.get("mutation_diagnostics")
                    != diagnostic_analysis["diagnostics"]
                ):
                    errors.append(
                        f"{row['target_id']}: not all mutation functions were rejected"
                    )
    return errors


def verify_feedback(
    rows: list[dict[str, Any]],
    *,
    require_reconciliation: bool = True,
) -> list[str]:
    errors: list[str] = []
    expected = sum(row["disposition"] == "generated" for row in rows)
    latest_path = (
        ROOT
        / "verification/evidence/btree_map_feedback_determinism/latest_manifest.json"
    )
    if not latest_path.is_file():
        return ["missing active feedback manifest"]
    latest = load_json(latest_path)
    summary_path = ROOT / latest["summary"]
    summary = load_json(summary_path)
    if sha256_file(summary_path) != latest.get("summary_sha256"):
        errors.append("active feedback summary hash is stale")
    if summary["expected_targets"] != expected or summary["completed_targets"] != expected:
        errors.append("feedback target count differs from generated inventory")
    if summary["typecheck_passed"] != expected:
        errors.append("not every generated contract passed feedback typecheck")
    if summary["missing_targets"] or summary["extra_targets"]:
        errors.append("feedback has missing or extra target evidence")
    if (
        summary.get("checker_errors")
        or summary.get("sat_targets")
        or summary.get("blocking_anti_vacuity")
    ):
        errors.append("feedback has a blocking checker or anti-vacuity result")
    limitations = set(summary.get("checker_limitations") or [])
    if limitations:
        if not require_reconciliation:
            if summary.get("status") != "passed_with_checker_limitations":
                errors.append("raw feedback limitation status was overwritten")
            return errors
        reconciliation_rel = latest.get("reconciliation")
        reconciliation_path = ROOT / reconciliation_rel if reconciliation_rel else None
        if (
            reconciliation_path is None
            or not reconciliation_path.is_file()
            or sha256_file(reconciliation_path)
            != latest.get("reconciliation_sha256")
        ):
            return [*errors, "feedback checker limitations lack immutable reconciliation"]
        reconciliation = load_json(reconciliation_path)
        resolved = set(
            reconciliation.get("resolved_by_actual_completeness") or []
        )
        if (
            reconciliation.get("status") != "passed"
            or reconciliation.get("raw_feedback_summary_sha256")
            != sha256_file(summary_path)
            or reconciliation.get("unresolved_after_resolution")
            or reconciliation.get("checker_errors_after_resolution")
            or reconciliation.get("sat_after_resolution")
            or limitations != resolved
        ):
            errors.append("feedback completeness reconciliation is incomplete or stale")
        matrix_latest = load_json(
            ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
        )
        reconciled_matrix_path = ROOT / reconciliation.get(
            "matrix_manifest",
            "__missing_matrix_manifest__",
        )
        if (
            reconciliation.get("matrix_run_id") != matrix_latest.get("run_id")
            or not reconciled_matrix_path.is_file()
            or reconciliation.get("matrix_manifest_sha256")
            != (
                sha256_file(reconciled_matrix_path)
                if reconciled_matrix_path.is_file()
                else None
            )
        ):
            errors.append("feedback completeness reconciliation binds a stale matrix")
        generated_by_target = {
            row["canonical_target"]: row
            for row in rows
            if row["disposition"] == "generated"
        }
        bindings = {
            binding["target"]: binding
            for binding in reconciliation.get("equivalence_bindings") or []
        }
        if set(bindings) != resolved:
            errors.append("feedback reconciliation equivalence bindings are incomplete")
        for target in sorted(resolved):
            row = generated_by_target.get(target)
            if row is None:
                errors.append(f"feedback resolution has unknown target: {target}")
                continue
            binding = bindings.get(target) or {}
            evidence_path = ROOT / binding.get("completeness_evidence", "")
            equivalence_path = ROOT / binding.get("equivalence", "")
            if not evidence_path.is_file():
                errors.append(f"feedback resolution lacks evidence: {target}")
                continue
            evidence = load_json(evidence_path)
            source = ROOT / evidence["source"]
            if (
                not evidence.get("passed")
                or not source.is_file()
                or sha256_file(source) != evidence.get("source_sha256")
                or sha256_file(evidence_path)
                != binding.get("completeness_evidence_sha256")
                or not equivalence_path.is_file()
                or sha256_file(equivalence_path)
                != binding.get("equivalence_sha256")
                or binding.get("target_id") != row["target_id"]
            ):
                errors.append(f"feedback resolution evidence is failed or stale: {target}")
    elif summary.get("status") != "passed":
        errors.append("strict feedback gate did not pass")
    if limitations and summary.get("status") != "passed_with_checker_limitations":
        errors.append("raw feedback limitation status was overwritten")
    return errors


def feedback_tree_digest(raw_root: Path) -> tuple[int, str]:
    paths = sorted(
        [
            *raw_root.glob("targets/*/summary.json"),
            *raw_root.glob("targets/*/round_*/contract_harness.rs"),
            *raw_root.glob("targets/*/round_*/det_harness.rs"),
            *raw_root.glob("targets/*/round_*/repair_evidence.json"),
        ],
        key=lambda path: str(path.relative_to(raw_root)),
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(raw_root)).encode())
        digest.update(b"\0")
        digest.update(sha256_file(path).encode())
        digest.update(b"\n")
    return len(paths), digest.hexdigest()


def verify_specification_evidence(*, require_review: bool) -> list[str]:
    errors: list[str] = []
    for name, expected_mode in (
        ("generated_spec_no_verify", "no_verify"),
        ("generated_spec_actual_verus", "actual_verus"),
    ):
        path = ROOT / "specs/evidence" / f"{name}.json"
        if not path.is_file():
            errors.append(f"missing specification evidence: {name}")
            continue
        record = load_json(path)
        if not record.get("passed") or record.get("returncode") != 0:
            errors.append(f"failed specification evidence: {name}")
        if record.get("mode") != expected_mode:
            errors.append(f"wrong specification evidence mode: {name}")
        for value in (record.get("inputs") or {}).values():
            source = ROOT / value["path"]
            if not source.is_file() or sha256_file(source) != value["sha256"]:
                errors.append(f"stale specification evidence input: {name}:{value['path']}")

    latest_path = (
        ROOT
        / "verification/evidence/btree_map_feedback_determinism/latest_manifest.json"
    )
    if not latest_path.is_file():
        errors.append("missing active specification feedback manifest")
    else:
        latest = load_json(latest_path)
        summary_path = ROOT / latest["summary"]
        binding_path = ROOT / latest["input_binding"]
        if (
            not summary_path.is_file()
            or sha256_file(summary_path) != latest.get("summary_sha256")
        ):
            errors.append("active specification feedback summary is stale")
        if (
            not binding_path.is_file()
            or sha256_file(binding_path) != latest.get("input_binding_sha256")
        ):
            errors.append("active specification feedback input binding is stale")
        if summary_path.is_file() and binding_path.is_file():
            summary = load_json(summary_path)
            binding = load_json(binding_path)
            if summary.get("expected_targets") != 137 or summary.get(
                "completed_targets"
            ) != 137:
                errors.append("specification feedback does not cover 137 generated rows")
            if summary.get("typecheck_passed") != 137:
                errors.append("not every generated contract passed feedback typecheck")
            if summary.get("missing_targets") or summary.get("extra_targets"):
                errors.append("specification feedback has missing or extra rows")
            if summary.get("checker_errors") or summary.get("sat_targets"):
                errors.append("specification feedback has checker errors or SAT witnesses")
            if summary.get("blocking_anti_vacuity"):
                errors.append("specification feedback has blocking anti-vacuity issues")
            if summary.get("reclassified_without_rerun"):
                errors.append("specification feedback was reclassified without rerun")
            repairs = summary.get("targeted_determinism_repairs")
            if repairs and repairs.get("status") != "passed":
                errors.append("targeted specification determinism repairs failed")
            for value in (binding.get("inputs") or {}).values():
                source = ROOT / value["path"]
                if not source.is_file() or sha256_file(source) != value["sha256"]:
                    errors.append(
                        f"stale specification feedback input: {value['path']}"
                    )
            if binding.get("binding_kind") != "run_completion":
                errors.append("specification feedback lacks launch-run completion binding")
            raw = binding.get("raw_evidence") or {}
            raw_root = ROOT / raw.get("root", "")
            if raw_root.is_dir():
                file_count, digest = feedback_tree_digest(raw_root)
                if (
                    file_count != raw.get("bound_file_count")
                    or digest != raw.get("tree_sha256")
                ):
                    errors.append("specification feedback raw evidence digest is stale")
            else:
                errors.append("specification feedback raw evidence root is missing")
            inventory = load_json(
                ROOT / "inventory/btree_map_exec_fn_inventory.json"
            )
            errors.extend(
                f"specification {error}"
                for error in verify_feedback(
                    inventory["rows"],
                    require_reconciliation=False,
                )
            )

    if require_review:
        review_path = ROOT / "reviews/inventory_specification.json"
        review = load_json(review_path) if review_path.is_file() else {}
        if (
            review.get("producer_role") != "reviewer"
            or not review.get("independent")
            or (review.get("review") or {}).get("status") != "done"
            or not review.get("proof_phase_authorized")
        ):
            errors.append("inventory/specification reviewer gate is not accepted")
        impossible = load_json(ROOT / "impossibility/extend_ref_outlives.json")
        if (
            impossible.get("status") != "accepted_by_independent_reviewer"
            or impossible.get("review_evidence")
            != "reviews/inventory_specification.json"
        ):
            errors.append("reference Extend impossibility lacks current row-level approval")
    return errors


def expected_proof_review_binding(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_path = ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
    latest = load_json(latest_path)
    phase_path = ROOT / "verification/premature_phase_ordering.json"
    phase = load_json(phase_path)
    mutation_functions = sum(
        len(
            load_json(
                ROOT
                / "proof_harnesses"
                / row["target_id"]
                / "mutations.json"
            )["mutants"]
        )
        for row in rows
    )
    return {
        "verus_matrix_manifest": str(latest_path.relative_to(ROOT)),
        "verus_matrix_manifest_sha256": sha256_file(latest_path),
        "verus_matrix_run_id": latest["run_id"],
        "verus_matrix_summary": latest["summary"],
        "verus_matrix_summary_sha256": latest["summary_sha256"],
        "generated_harness_tree_sha256": phase["tree_sha256"],
        "selected_targets": len(rows),
        "mutation_functions": mutation_functions,
        "inventory_review": "reviews/inventory_specification.json",
        "inventory_review_sha256": sha256_file(
            ROOT / "reviews/inventory_specification.json"
        ),
    }


def verify_proof_review_binding(
    rows: list[dict[str, Any]],
    record: dict[str, Any] | None = None,
) -> list[str]:
    if record is None:
        path = ROOT / "reviews/proof_completeness.json"
        if not path.is_file():
            return ["missing independent reviewer gate: proof_completeness"]
        record = load_json(path)
    if record.get("evidence_bindings") != expected_proof_review_binding(rows):
        return ["proof/completeness review does not bind current evidence"]
    return []


def expected_final_review_binding() -> dict[str, Any]:
    matrix_path = ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
    matrix = load_json(matrix_path)
    feedback_path = (
        ROOT
        / "verification/evidence/btree_map_feedback_determinism/latest_manifest.json"
    )
    feedback = load_json(feedback_path)
    aggregate_path = ROOT / "proof_inventory/aggregate_coverage.json"
    artifact_path = ROOT / "verification/audits/artifact_integrity_audit.json"
    proof_review_path = ROOT / "reviews/proof_completeness.json"
    phase_path = ROOT / "verification/premature_phase_ordering.json"
    return {
        "verus_matrix_manifest": str(matrix_path.relative_to(ROOT)),
        "verus_matrix_manifest_sha256": sha256_file(matrix_path),
        "verus_matrix_run_id": matrix["run_id"],
        "verus_matrix_summary_sha256": matrix["summary_sha256"],
        "feedback_manifest": str(feedback_path.relative_to(ROOT)),
        "feedback_manifest_sha256": sha256_file(feedback_path),
        "feedback_run_id": feedback["run_id"],
        "aggregate": str(aggregate_path.relative_to(ROOT)),
        "aggregate_sha256": sha256_file(aggregate_path),
        "artifact_integrity_audit": str(artifact_path.relative_to(ROOT)),
        "artifact_integrity_audit_sha256": sha256_file(artifact_path),
        "proof_review": str(proof_review_path.relative_to(ROOT)),
        "proof_review_sha256": sha256_file(proof_review_path),
        "phase_order_archive": str(phase_path.relative_to(ROOT)),
        "phase_order_archive_sha256": sha256_file(phase_path),
    }


def verify_final_review_binding(
    record: dict[str, Any] | None = None,
) -> list[str]:
    if record is None:
        path = ROOT / "reviews/final_aggregate.json"
        if not path.is_file():
            return ["missing independent reviewer gate: final_aggregate"]
        record = load_json(path)
    if record.get("evidence_bindings") != expected_final_review_binding():
        return ["final aggregate review does not bind current evidence"]
    return []


def verify_reviews(selected_rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    reviewer_names: list[str] = []
    for gate in ("inventory_specification", "proof_completeness", "final_aggregate"):
        path = ROOT / "reviews" / f"{gate}.json"
        if not path.is_file():
            errors.append(f"missing independent reviewer gate: {gate}")
            continue
        record = load_json(path)
        review = record.get("review") or {}
        identity = record.get("reviewer_identity") or {}
        if identity.get("name"):
            reviewer_names.append(identity["name"])
        if (
            record.get("producer_role") != "reviewer"
            or review.get("status") != "done"
            or not record.get("independent")
            or identity.get("authored_campaign_artifacts") is not False
        ):
            errors.append(f"reviewer gate is not accepted: {gate}")
    if len(reviewer_names) != 3 or len(set(reviewer_names)) != 3:
        errors.append("reviewer gates do not have three distinct identities")
    errors.extend(verify_proof_review_binding(selected_rows))
    errors.extend(verify_final_review_binding())
    return errors


def verify_dynamic() -> list[str]:
    inventory = load_json(ROOT / "inventory/btree_map_exec_fn_inventory.json")
    rows = inventory["rows"]
    selected_rows = [
        row for row in rows if row["disposition"] in {"exact_vstd", "generated"}
    ]
    errors = verify_specification_evidence(require_review=True)
    errors.extend(verify_verus_evidence(selected_rows))
    errors.extend(verify_feedback(rows))
    errors.extend(verify_reviews(selected_rows))
    impossible = load_json(ROOT / "impossibility/extend_ref_outlives.json")
    if impossible.get("status") != "accepted_by_independent_reviewer":
        errors.append("reference Extend impossibility lacks final row-level approval")
    for name in (
        "proof_evidence_audit.json",
        "feedback_determinism_audit.json",
        "artifact_integrity_audit.json",
    ):
        path = ROOT / "verification/audits" / name
        if not path.is_file() or load_json(path).get("status") != "passed":
            errors.append(f"dynamic audit not passed: {name}")
    aggregate = load_json(ROOT / "proof_inventory/aggregate_coverage.json")
    for field in (
        "selected_targets",
        "actual_verus_verified",
        "completeness_verified",
        "mutation_rejected",
    ):
        if aggregate.get(field) != len(selected_rows):
            errors.append(
                f"aggregate {field}={aggregate.get(field)} != {len(selected_rows)}"
            )
    expected_mutation_functions = sum(
        len(
            load_json(
                ROOT
                / "proof_harnesses"
                / row["target_id"]
                / "mutations.json"
            )["mutants"]
        )
        for row in selected_rows
    )
    if aggregate.get("mutation_functions_rejected") != expected_mutation_functions:
        errors.append("aggregate mutation function count is incomplete")
    if aggregate.get("pending") != 0:
        errors.append("aggregate pending is nonzero")
    if aggregate.get("target_external_body") != 0:
        errors.append("target-level external_body count is nonzero")
    if "private_source_closure_contract_boundaries" in aggregate:
        errors.append("aggregate still reports a private-source closure metric")
    if aggregate.get("boundaries_covering_target_contract") != 0:
        errors.append(
            "aggregate reports boundaries covering the whole target contract"
        )
    if aggregate.get("operation_local_source_boundaries", 0) < len(selected_rows):
        errors.append(
            "aggregate reports fewer operation-local boundaries than targets"
        )
    if aggregate.get("harness_literal_external_body_occurrences", 0) <= 0:
        errors.append("proof-harness shared model boundaries are not accounted")
    if aggregate.get("spec_helper_model_external_body_occurrences", 0) <= 0:
        errors.append("spec helper/model external_body trust is not accounted")
    certification = load_json(
        ROOT / "proof_inventory/active_aggregate_certification.json"
    )
    if certification.get("status") != "accepted":
        errors.append("active aggregate certification is not accepted")
    aggregate_rel = certification.get("aggregate")
    if not aggregate_rel:
        errors.append("active aggregate certification lacks aggregate binding")
    elif certification.get("aggregate_sha256") != sha256_file(
        ROOT / aggregate_rel
    ):
        errors.append("active aggregate certification hash is stale")
    final_review_rel = certification.get("final_review")
    if not final_review_rel:
        errors.append("active aggregate certification lacks final review binding")
    elif certification.get("final_review_sha256") != sha256_file(
        ROOT / final_review_rel
    ):
        errors.append("active final-review certification hash is stale")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "--specification-only",
        action="store_true",
        help="verify inventory/specification artifacts without reading proof artifacts",
    )
    parser.add_argument(
        "--pre-review",
        action="store_true",
        help="allow the specification reviewer and row approval to remain pending",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = verify_static(include_proofs=not args.specification_only)
    if args.specification_only and not args.static_only:
        errors.extend(
            verify_specification_evidence(require_review=not args.pre_review)
        )
    if not args.static_only and not args.specification_only:
        errors.extend(verify_dynamic())
    inventory = load_json(ROOT / "inventory/btree_map_exec_fn_inventory.json")
    counts = inventory["counts"]
    impossible = load_json(ROOT / "impossibility/extend_ref_outlives.json")
    report = {
        "schema_version": 1,
        "mode": (
            "specification"
            if args.specification_only
            else "static"
            if args.static_only
            else "aggregate"
        ),
        "status": "passed" if not errors else "failed",
        "counts": {
            **counts,
            "selected_contracts": counts["exact_vstd"] + counts["generated"],
        },
        "proof_artifacts_checked": not args.specification_only,
        "impossibility_review_status": impossible.get("status"),
        "errors": errors,
    }
    if not args.pre_review:
        (ROOT / "verification").mkdir(exist_ok=True)
        (ROOT / "verification/aggregate_check.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"BTreeMap campaign verification failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    if args.specification_only:
        impossibility_label = (
            "1 reviewer-approved impossibility"
            if impossible.get("status") == "accepted_by_independent_reviewer"
            else "1 impossibility pending independent review"
        )
        print(
            "BTreeMap specification verification passed: "
            "151 stable rows, 150 selected contracts, 13 exact-vstd, "
            f"137 generated, {impossibility_label}, "
            "proof artifacts not read"
        )
    else:
        print(
            "BTreeMap campaign verification passed: "
            "151 stable rows, 150 selected proofs, 13 exact-vstd, "
            "137 generated, 1 reviewed impossible, pending=0"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
