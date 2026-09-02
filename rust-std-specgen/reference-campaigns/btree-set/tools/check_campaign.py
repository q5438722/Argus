#!/usr/bin/env python3
"""Fail-closed, inventory-derived aggregate checker for the BTreeSet campaign."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import campaign_model as model
from tools import check_provenance
from tools import completeness_audit
from tools import proof_model
from tools import verus_evidence


ROOT = model.ROOT
SCHEMA = ROOT / "aggregate/schema.json"
INVENTORY = ROOT / "inventory/btree_set_exec_fn_inventory.json"
CATALOG = ROOT / "specs/all_btree_set_specs.json"
EXCLUSIONS = ROOT / "inventory/unstable_non_executable_exclusions.json"
EXACT_AUDIT = ROOT / "inventory/exact_vstd_audit.json"
AGGREGATE = ROOT / "proof_inventory/aggregate_coverage.json"
class CampaignError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["target_id"],
        row["owner_type"],
        row["trait"],
        row["method"],
        row["rustdoc_item_id"],
        row["source_sha256"],
        row["canonical_target"],
        row["disposition"],
        row["contract_fingerprint"],
    )


SURROGATE_TOKENS = (
    "pub struct Snapshot",
    "pub struct Outcome",
    "pub ghost struct Snapshot",
    "pub ghost struct Outcome",
    "ContractInput",
    "ContractOutcome",
    "PrivateResult<",
    "MapAdapterResult<",
    "source_contract_observation",
    "DependencyObservation",
    "pub uninterp spec fn source_sequence",
    "pub uninterp spec fn source_optional_item",
    "pub uninterp spec fn source_set_transition",
    "pub uninterp spec fn source_callback_sequence",
    "accepted_contract(",
    "private_source_branch",
)


def proof_text_policy_errors(
    implementation: str,
    completeness: str,
) -> list[str]:
    errors: list[str] = []
    for token in SURROGATE_TOKENS:
        if token in implementation or token in completeness:
            errors.append(f"surrogate/whole-observation proof is forbidden: {token}")
    return errors


def external_function_start(source: str, name: str) -> int:
    starts = [
        source.find(
            f"#[verifier::external_body]\npub fn {name}{delimiter}"
        )
        for delimiter in ("<", "(")
    ]
    return min((index for index in starts if index >= 0), default=-1)


def compact_rust(source: str) -> str:
    return re.sub(r"\s+", "", source)


def structural_rust(source: str) -> str:
    return (
        compact_rust(source)
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
    )


def canonical_projected_clause(clause: str) -> str:
    canonical = compact_rust(clause)
    replacements = (
        ("union_inner_cursor_remaining", "union_remaining"),
        ("union_inner_state_law", "union_source_state_law"),
        ("union_inner_state", "union_source_state"),
        ("project_map_entry(result)", "result"),
        ("wrapped_btree_map_keys(old(this))", "old(this)@"),
        ("wrapped_btree_map_keys(final(this))", "final(this)@"),
        ("wrapped_btree_map_keys(this)", "this@"),
        ("wrapped_btree_map_keys(other)", "other@"),
        ("wrapped_btree_map_keys(rhs)", "rhs@"),
        (
            "wrapped_btree_map_key_sequence(old(this))",
            "btree_set_sequence(*old(this))",
        ),
        (
            "wrapped_btree_map_key_sequence(final(this))",
            "btree_set_sequence(*final(this))",
        ),
        (
            "wrapped_btree_map_key_sequence(this)",
            "btree_set_sequence(*this)",
        ),
        (
            "wrapped_btree_map_key_sequence(other)",
            "btree_set_sequence(*other)",
        ),
        (
            "wrapped_btree_map_key_sequence(rhs)",
            "btree_set_sequence(*rhs)",
        ),
        ("(result.value)", "result"),
        ("result.value", "result"),
    )
    for old, new in replacements:
        canonical = canonical.replace(old, new)
    canonical = canonical.replace(
        "merge_next_step(union_source_state(*old(this))).state",
        "union_next_step(union_source_state(*old(this))).state",
    )
    if "union_" in canonical:
        guard = "(obeys_cmp::<T>())==>"
        if canonical.startswith(guard):
            canonical = canonical[len(guard) :]
    return canonical.replace("(", "").replace(")", "")


def projected_clause_equivalent(
    lower_clause: str,
    accepted_clause: str,
) -> bool:
    lower = canonical_projected_clause(lower_clause)
    accepted = canonical_projected_clause(accepted_clause)
    return lower == accepted


def selected_public_composition_policy_errors(
    row: model.Row,
    implementation: str,
) -> list[str]:
    if not proof_model.requires_selected_public_composition(row):
        return []
    errors: list[str] = []
    implementation_body = executable_function_body(
        implementation,
        "implementation",
    )
    composition_tokens = proof_model.implementation_order_tokens(row)
    if any(token not in implementation_body for token in composition_tokens):
        errors.append(
            "selected public dependency composition is absent from "
            "the executable target body"
        )
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        expected_receiver = (
            "let other_min = rust_1_96_selected_first(other);"
            if row.semantic_family == "difference_adapter_construction"
            else "let other_max = rust_1_96_selected_last(other);"
        )
        dependency_block = executable_function_body(
            implementation,
            proof_model.dependency_function_name(row),
        )
        for token in (
            expected_receiver,
            "self_iter: Iter<'a, T>",
            "other_iter: Iter<'a, T>",
            "Ghost(source_state): Ghost<SetAdapterState<T>>",
            "result.state@ == source_state",
        ):
            if token not in implementation:
                errors.append(
                    f"selected adapter construction omits {token}"
                )
        if any(
            token in dependency_block
            for token in (
                "this: &'a BTreeSet",
                "other: &'a BTreeSet",
                "wrapped_btree_map_key_sequence(this)",
                "wrapped_btree_map_key_sequence(other)",
            )
        ):
            errors.append(
                "selected adapter lower dependency re-observes complete sets"
            )
    if row.semantic_family in {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }:
        dependency_block = executable_function_body(
            implementation,
            proof_model.dependency_function_name(row),
        )
        for token in (
            "let self_iter = rust_1_96_selected_iter(this);",
            "let other_iter = rust_1_96_selected_iter(other);",
            "Ghost(self_source): Ghost<Seq<&'a T>>",
            "Ghost(other_source): Ghost<Seq<&'a T>>",
        ):
            if token not in implementation:
                errors.append(
                    f"selected merge construction omits {token}"
                )
        if any(
            token in dependency_block
            for token in (
                "this: &'a BTreeSet",
                "other: &'a BTreeSet",
                "wrapped_btree_map_key_sequence(this)",
                "wrapped_btree_map_key_sequence(other)",
            )
        ):
            errors.append(
                "selected merge lower dependency re-observes complete sets"
            )
    if row.function["name"] in {"is_subset", "is_superset"}:
        subset_body = executable_function_body(
            implementation,
            "rust_1_96_selected_is_subset_source",
        )
        for token in (
            "rust_1_96_selected_len(this)",
            "rust_1_96_selected_len(other)",
            "rust_1_96_selected_first(this)",
            "rust_1_96_selected_last(this)",
            "rust_1_96_selected_iter(this)",
            "rust_1_96_selected_iter_next(",
            "rust_1_96_selected_iter_next_back(",
            "rust_1_96_selected_iter_len(&self_iter)",
            "rust_1_96_selected_contains(",
            "while scan_index < this_len",
            f"{proof_model.dependency_function_name(row)}::<T, A>(",
            "Ghost(source)",
        ):
            effective_token = token
            if effective_token not in subset_body:
                errors.append(
                    f"BTreeSet subset source control omits {effective_token}"
                )
        if (
            "let self_min = rust_1_96_selected_first(this);"
            not in subset_body
            or "source == wrapped_btree_map_key_sequence(this)"
            not in implementation
            or "index < source.len()"
            not in implementation
        ):
            errors.append(
                "BTreeSet subset endpoints are not bound to live scan cursors"
            )
        dependency_block = executable_function_body(
            implementation,
            proof_model.dependency_function_name(row),
        )
        if (
            "self_source.unref().to_set().subset_of("
            "other_source.unref().to_set())"
            in implementation
            or "result.value ==" in dependency_block
            or "source_branch:" in dependency_block
            or "front_contained:" in dependency_block
            or "back_contained:" in dependency_block
        ):
            errors.append(
                "BTreeSet subset lower dependency assumes the whole result"
            )
    if row.function["name"] == "retain":
        for token in (
            "let extraction = rust_1_96_selected_extract_if_begin(",
            f"let consumed = {proof_model.dependency_function_name(row)}"
            "::<T, F, A>(",
            "rust_1_96_rejoin_selected_extract_if::<T, A>(",
        ):
            if token not in implementation_body:
                errors.append(
                    f"BTreeSet retain source control omits {token}"
                )
        dependency_block = executable_function_body(
            implementation,
            proof_model.dependency_function_name(row),
        )
        if (
            "iter: ExtractIf<" not in implementation
            or "result.retained@ == retain_selected(source, keeps)"
            not in implementation
            or "set: &mut BTreeSet" in dependency_block
        ):
            errors.append(
                "BTreeSet retain lower dependency bypasses live ExtractIf state"
            )
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        for token in (
            "rust_1_96_selected_cloned_extend_input(iter)",
            "rust_1_96_selected_owned_extend::<T, A>(",
        ):
            if token not in implementation_body:
                errors.append(
                    f"borrowed Extend selected composition omits {token}"
                )
        if "while input_index < input_steps" in implementation_body:
            errors.append(
                "borrowed Extend duplicates the owned Extend insertion loop"
            )
    if proof_model.terminal_override_selected_method(row) is not None:
        selected_call = proof_model.dependency_call_name(row)
        if implementation_body.count(f"{selected_call}(&mut source)") != 1:
            errors.append(
                "terminal override does not make exactly one selected "
                "next/next_back call"
            )
    if (
        model.dependency_path(row) == "btree_set_control_flow"
        and not composition_tokens
    ):
        errors.append("btree_set_control_flow was dropped")
    return errors


def parsed_source_call_policy_errors(
    row: model.Row,
    implementation: str,
) -> list[str]:
    requirements = proof_model.executable_source_call_requirements(row)
    if not requirements:
        return []
    body = executable_function_body(implementation, "implementation")
    errors: list[str] = []
    for record in requirements:
        callee = str(record["callee"])
        required = int(record["required_occurrences"])
        parsed = int(record["source_occurrences"])
        fragment = str(record["executable_fragment"])
        if parsed != required:
            errors.append(
                f"parsed source call {callee} occurs {parsed} times; "
                f"expected {required}"
            )
        observed = body.count(fragment)
        if observed != required:
            errors.append(
                f"parsed source call {callee} has {observed} executable "
                f"retentions; expected {required}"
            )
    return errors


def union_candidate_selection_policy_errors(
    row: model.Row,
    implementation: str,
    mutation: str,
) -> list[str]:
    if not proof_model.union_left_biased_next(row):
        return []
    implementation_body = executable_function_body(
        implementation,
        "implementation",
    )
    mutation_body = executable_function_body(
        mutation,
        "implementation",
    )
    original = "let answer = a_next.or(b_next);"
    changed = "let answer = a_next;"
    lower_call = f"{proof_model.dependency_call_name(row)}(this)"
    errors: list[str] = []
    for label, body in (
        ("implementation", implementation_body),
        ("mutation", mutation_body),
    ):
        for token in (
            lower_call,
            "let a_next = project_map_entry_exec(pair.left);",
            "let b_next = project_map_entry_exec(pair.right);",
        ):
            if body.count(token) != 1:
                errors.append(
                    f"Union {label} does not execute exactly one {token}"
                )
        if "source_branch" in body or "read_source_discriminant" in body:
            errors.append(
                f"Union {label} retains synthetic branch dispatch"
            )
    if implementation_body.count(original) != 1:
        errors.append(
            "Union implementation omits the live left-biased selection"
        )
    if mutation_body.count(changed) != 1:
        errors.append(
            "Union mutation does not alter the live left-biased selection"
        )
    if mutation_body.replace(changed, original, 1) != implementation_body:
        errors.append(
            "Union mutation changes more than the live candidate selection"
        )
    return errors


def reject_projected_dependency_equivalence(row: model.Row) -> bool:
    return (
        proof_model.requires_selected_public_composition(row)
        or proof_model.union_left_biased_next(row)
    )


def adapter_source_loop_policy_errors(
    row: model.Row,
    implementation: str,
) -> list[str]:
    if not proof_model.source_owned_adapter_loop(row):
        return []
    body = executable_function_body(implementation, "implementation")
    errors: list[str] = []
    for token in (
        "_read_source_loop_steps",
        "completed_source_steps",
        "source_steps",
    ):
        if token in body:
            errors.append(
                f"adapter source loop retains synthetic control token {token}"
            )
    required_loops = {
        "Difference": 2,
        "SymmetricDifference": 1,
        "Intersection": 2,
    }[row.owner["name"]]
    if body.count("loop\n") != required_loops:
        errors.append(
            "adapter source loop count does not match the Rust source"
        )
    base = proof_model.dependency_function_name(row)
    call_counts = {
        "Difference": {
            "": 2,
            "_read_source_discriminant": 1,
            "_stitch_peek_other": 1,
            "_stitch_compare": 1,
            "_stitch_next_other": 2,
            "_search_next_self": 1,
            "_search_contains": 1,
            "_iterate_next": 1,
        },
        "SymmetricDifference": {"": 1},
        "Intersection": {
            "": 1,
            "_read_source_discriminant": 1,
            "_stitch_next_b": 1,
            "_stitch_compare": 1,
            "_stitch_advance_a": 1,
            "_stitch_advance_b": 1,
            "_search_next_small": 1,
            "_search_contains": 1,
            "_answer_take": 1,
        },
    }[row.owner["name"]]
    for suffix, expected in call_counts.items():
        callee = proof_model.generic_call_name(row, f"{base}{suffix}")
        observed = body.count(f"{callee}(")
        if observed != expected:
            errors.append(
                f"adapter source operation {callee} has {observed} calls; "
                f"expected {expected}"
            )
    decision_tokens = {
        "Difference": (
            "match order.value",
            "if !contained",
        ),
        "SymmetricDifference": (
            "a_next.and(b_next).is_none()",
            "a_next.or(b_next)",
        ),
        "Intersection": (
            "match order.value",
            "if contained",
        ),
    }[row.owner["name"]]
    for token in decision_tokens:
        if token not in body:
            errors.append(
                f"adapter source loop omits live decision {token}"
            )
    comparison = proof_model.adapter_source_comparison_call_fragment(row)
    if comparison not in body:
        errors.append(
            "adapter source loop omits the source comparison direction"
        )
    return errors


def adapter_source_mutation_policy_errors(
    row: model.Row,
    implementation: str,
    mutation: str,
) -> list[str]:
    if not proof_model.source_owned_adapter_loop(row):
        return []
    errors: list[str] = []
    if any(
        re.search(r"\bsource_order\b", source)
        for source in (implementation, mutation)
    ):
        errors.append(
            "adapter mutation retains a synthetic proof-only source_order guard"
        )
    implementation_body = executable_function_body(
        implementation,
        "implementation",
    )
    mutation_body = executable_function_body(
        mutation,
        "implementation",
    )
    normalize_guards = lambda body: re.sub(
        r"\b(?:true|false)\b",
        "__proof_guard__",
        body,
    )
    if (
        implementation_body != mutation_body
        and normalize_guards(implementation_body)
        == normalize_guards(mutation_body)
    ):
        errors.append(
            "adapter mutation changes only a proof-only boolean guard"
        )
    return errors


def dependency_policy_errors(
    implementation: str,
    dependency_name: str,
    accepted_clauses: list[str],
    expected_lower_clauses: list[str],
    *,
    reject_projected_equivalence: bool = False,
) -> list[str]:
    errors: list[str] = []
    start = external_function_start(implementation, dependency_name)
    end = implementation.find("\n\npub fn implementation", start)
    block = implementation[start:end] if start >= 0 and end >= 0 else ""
    if not block:
        return ["narrow dependency block is not isolated"]
    compact_block = compact_rust(block)
    structural_block = structural_rust(block)
    for lower_clause in expected_lower_clauses:
        if structural_rust(lower_clause) not in structural_block:
            errors.append("dependency omits narrow map observation")
    for clause in accepted_clauses:
        if (
            compact_rust(clause) in compact_block
            and any(
                token in clause
                for token in (
                    "result",
                    "final(",
                    "btree_set_sequence",
                    "_remaining(",
                )
            )
        ):
            errors.append("dependency restates a public accepted clause")
        if reject_projected_equivalence and any(
            projected_clause_equivalent(lower_clause, clause)
            for lower_clause in expected_lower_clauses
        ):
            errors.append(
                "dependency restates a public accepted clause after projection"
            )
    if any(
        token in block
        for token in (
            "btree_set_sequence(*old(",
            "btree_set_sequence(*final(",
            "old(this)@",
            "final(this)@",
        )
    ):
        errors.append(
            "dependency reaches public BTreeSet state instead of opaque map state"
        )
    return errors


def spec_function_body(source: str, name: str) -> str:
    match = re.search(
        rf"\b(?:pub\s+)?(?:open\s+)?spec\s+fn\s+{re.escape(name)}\b",
        source,
    )
    if match is None:
        return ""
    start = source.find("{", match.end())
    if start < 0:
        return ""
    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index]
    return ""


def executable_function_body(source: str, name: str) -> str:
    marker = f"pub fn {name}"
    start = source.rfind(marker)
    if start < 0:
        return ""
    body_start = source.find("\n{\n", start)
    if body_start < 0:
        return ""
    opening = body_start + 1
    depth = 0
    for index in range(opening, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    return ""


def narrowly_evidenced_checker_limitation(
    row: dict[str, Any],
    raw_error_text: str,
) -> bool:
    limitation = row.get("checker_limitation")
    target = row.get("target")
    if limitation == "verus-intoiterator-associated-item-air":
        return (
            "generated ill-typed AIR code" in raw_error_text
            and "IntoIterator./Item" in raw_error_text
        )
    if (
        limitation
        == "spec-determinism-dropped-duplicate-method-where-clause"
    ):
        return (
            target
            == "alloc::collections::btree_set::BTreeSet::<T, A>::append"
            and "trait bound `T: std::cmp::Ord` is not satisfied"
            in raw_error_text
            and "vstd::laws_cmp::obeys_cmp" in raw_error_text
            and "det___rust_std_candidate_equal" in raw_error_text
        )
    return False


def parse_struct_fields(source: str) -> dict[str, tuple[str, ...]]:
    """Map each inline `pub struct Name { .. }` to its ordered field types.

    Tuple/unit structs (``pub struct Name;`` / ``pub struct Name(..);``) are
    recorded with an empty field list so they can still be compared.
    """
    structs: dict[str, tuple[str, ...]] = {}
    for match in re.finditer(r"pub struct (\w+)\s*(<[^>{;(]*>)?\s*", source):
        name = match.group(1)
        rest = source[match.end():]
        if rest[:1] == ";" or rest[:1] == "(":
            structs.setdefault(name, ())
            continue
        if rest[:1] != "{":
            continue
        depth = 0
        end = None
        for index, character in enumerate(rest):
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            continue
        body = rest[1:end]
        fields: list[str] = []
        for raw in body.split(","):
            entry = raw.strip()
            if not entry or ":" not in entry:
                continue
            field_type = entry.split(":", 1)[1].strip()
            fields.append(field_type)
        structs[name] = tuple(fields)
    return structs


def struct_signature(
    structs: dict[str, tuple[str, ...]],
    name: str,
    seen: tuple[str, ...] = (),
) -> tuple:
    """Recursively normalize a struct into a shape signature.

    Local struct-typed fields are expanded to their own signatures so that a
    renamed clone with structurally identical (possibly nested) fields yields
    the same signature as the struct it aliases.
    """
    if name in seen or name not in structs:
        return (name,)
    signature: list = []
    for field_type in structs[name]:
        base = re.match(r"\w+", field_type)
        base_name = base.group(0) if base else ""
        if base_name in structs and base_name != name:
            signature.append(struct_signature(structs, base_name, seen + (name,)))
        else:
            signature.append(field_type)
    return tuple(signature)


def verify_schema() -> list[str]:
    errors: list[str] = []
    if not SCHEMA.is_file():
        return ["missing aggregate/schema.json"]
    schema = load_json(SCHEMA)
    if schema.get("schema_version") != 1:
        errors.append("aggregate schema version is unsupported")
    if schema.get("module") != model.MODULE:
        errors.append("aggregate schema module differs from campaign scope")
    inventory = schema.get("inventory") or {}
    if inventory.get("totals_source") != "inventory_rows":
        errors.append("aggregate totals are not inventory-derived")
    if inventory.get("zero_pending_required") is not True:
        errors.append("aggregate schema does not fail on pending rows")
    if set(inventory.get("dispositions", [])) != {
        "exact_vstd",
        "generated",
        "genuinely_impossible",
        "pending",
    }:
        errors.append("aggregate disposition partition is incomplete")
    exact = schema.get("exact_vstd") or {}
    if exact.get("match_dimensions") != list(model.MATCH_DIMENSIONS):
        errors.append("aggregate exact-vstd dimensions differ from the required eight")
    if exact.get("comparison_derived_from_parsed_declarations") is not True:
        errors.append("aggregate exact-vstd matches are not declaration-derived")
    if exact.get("redeclare") is not False:
        errors.append("aggregate schema permits exact-vstd redeclaration")
    if exact.get("reverse_scan_required") is not True:
        errors.append("aggregate schema omits reverse vstd coverage scanning")
    harness = schema.get("harness") or {}
    for key in (
        "accepted_specification_review_required_before_generation",
        "forbid_generic_source_surrogates",
        "forbid_snapshot_outcome_surrogates",
        "forbid_target_external_body",
        "forbid_whole_contract_dependency",
        "lower_dependency_return_must_differ_from_public_target",
        "one_child_per_selected_target",
        "reject_field_isomorphic_lower_results",
        "require_literal_clause_translation",
        "require_exact_generated_proof_sources",
        "require_narrow_associated_item_checker_adjudication",
        "require_narrow_dependency_clause_lowering",
        "require_clause_derived_completeness",
        "require_operation_specific_lower_contracts",
        "require_projector_observed_mutation",
        "require_source_derived_discriminants",
        "require_source_operation_order",
    ):
        if harness.get(key) is not True:
            errors.append(f"aggregate schema omits fail-closed harness rule {key}")
    trust = schema.get("trust_accounting") or {}
    for key in (
        "category_specific_literal_counts_required",
        "checker_adjudication_surface_required",
        "compiled_harness_surface_required",
        "local_dependency_surface_required",
        "shared_type_model_surface_required",
        "whole_contract_dependency_must_be_zero",
    ):
        if trust.get(key) is not True:
            errors.append(f"aggregate schema omits trust accounting rule {key}")
    adjudication = (
        schema.get("evidence", {})
        .get("associated_item_checker_adjudication", {})
    )
    if adjudication != {
        "affected_target_count": 3,
        "exact_signature_no_verify_required": True,
        "exact_verus_internal_error_required": (
            "verus-intoiterator-associated-item-air"
        ),
        "stronger_bound_erased_actual_verus_required": True,
        "stronger_bound_erased_mutation_rejection_required": True,
    }:
        errors.append(
            "aggregate schema omits narrow associated-item adjudication"
        )
    reviews = schema.get("review_gates") or []
    if reviews != [
        "inventory_specification",
        "proof_completeness",
        "final_aggregate",
    ]:
        errors.append("aggregate schema does not require all three reviewer gates")
    return errors


def required_comparison_law(row: model.Row) -> str | None:
    if row.disposition != "generated":
        return None
    binder, _inputs, _output, where_clause = model.proxy_parts(row)
    bound_map: dict[str, set[str]] = {
        item["name"]: {
            bound.strip()
            for bound in item["bounds"].split("+")
            if bound.strip()
        }
        for item in model.parse_generic_declarations(binder)
    }
    where_text = where_clause.strip()
    if where_text.startswith("where"):
        where_text = where_text[len("where") :].strip()
    for predicate in model.split_top_level(where_text):
        subject, separator, raw_bounds = predicate.partition(":")
        if not separator:
            continue
        bound_map.setdefault(subject.strip(), set()).update(
            bound.strip()
            for bound in raw_bounds.split("+")
            if bound.strip()
        )

    def has_bound(subject: str, bound: str) -> bool:
        return any(
            candidate == bound or candidate.endswith(f"::{bound}")
            for candidate in bound_map.get(subject, set())
        )

    laws: list[str] = []
    if has_bound("&'a T", "Ord"):
        laws.append("obeys_cmp::<&'a T>()")
    elif has_bound("T", "Ord"):
        laws.append("obeys_cmp::<T>()")
    elif has_bound("T", "PartialOrd"):
        laws.append("T::obeys_partial_cmp_spec()")
    for parameter in ("K", "Q"):
        if has_bound(parameter, "Ord"):
            laws.append(f"{parameter}::obeys_cmp_spec()")
    comparison_bound = any(
        has_bound(subject, bound)
        for subject in bound_map
        for bound in ("Ord", "PartialOrd")
    )
    if comparison_bound:
        return " && ".join(dict.fromkeys(laws))
    return None


def verify_contract_semantics(
    live_rows: list[model.Row],
    *,
    vocabulary_override: str | None = None,
) -> list[str]:
    errors: list[str] = []
    vocabulary = (
        model.SHARED_VOCABULARY
        if vocabulary_override is None
        else vocabulary_override
    )
    forbidden_helpers = (
        "source_contract_observation",
        "source_extend_transition",
        "ordered_iterator_set",
        "ordered_iterator_increasing",
        "ordered_iterator_front_matches",
        "ordered_iterator_back_matches",
        "ordered_iterator_equivalent",
        "adapter_size_hint_matches",
        "ordered_range_result",
        "representative_replace_result",
        "ordered_retain_result",
        "append_representatives",
        "ordered_split_partition",
        "extract_if_initial",
        "sorted_input_set",
        "last_equal_input_representative",
        "set_operation_representatives",
        "ordered_set_hash_transition",
        "ordered_set_comparison",
        "ordered_debug_result",
    )
    for helper in forbidden_helpers:
        if re.search(rf"\bspec fn {re.escape(helper)}\b", vocabulary):
            errors.append(f"shared vocabulary retains opaque whole-behavior helper {helper}")
    for required in (
        "btree_set_sequence",
        "difference_sequence",
        "intersection_source_sequence",
        "union_sequence",
        "symmetric_difference_sequence",
        "range_sequence",
        "retain_selected",
        "dedup_last_sorted",
        "retain_decisions_from",
        "hash_items_in_order",
        "debug_entries_in_order",
        "extract_if_panic_preserves_elements",
        "extract_if_partial_drop_set",
        "extract_if_drop_law",
        "extract_if_panic_law",
        "range_order_law",
        "retain_callback_trace_law",
        "difference_source_state_law",
        "symmetric_difference_source_state_law",
        "intersection_source_state_law",
        "union_source_state_law",
        "difference_next_step",
        "symmetric_difference_next_step",
        "intersection_next_step",
        "union_next_step",
    ):
        if f"spec fn {required}" not in vocabulary:
            errors.append(f"shared vocabulary lacks defined semantic operation {required}")
    for derived in (
        "retain_decisions",
        "retain_effect_trace",
        "apply_set_hash",
        "apply_debug_sequence",
        "apply_debug_shape",
        "range_start_after_end",
        "range_equal_excluded",
        "range_contains",
        "difference_hint_lengths",
        "symmetric_difference_hint_lengths",
        "intersection_hint_lengths",
        "union_hint_lengths",
        "extract_if_length_bound",
        "extract_if_decisions",
        "extract_if_drop_law",
        "extract_if_panic_law",
    ):
        if f"pub open spec fn {derived}" not in vocabulary:
            errors.append(
                f"shared vocabulary does not law-constrain derived operation {derived}"
            )
        if f"pub uninterp spec fn {derived}" in vocabulary:
            errors.append(
                f"shared vocabulary leaves derived operation uninterpreted: {derived}"
            )
    for token in (
        "RangeBoundsSpec",
        "SpecBound",
        "spec_start_bound",
        "spec_end_bound",
        "range_bound_order",
        "borrowed_key_projection",
        "borrowed_key_projection_exec",
        "borrowed_key_order",
        "borrowed_key_order_law",
        "sets_borrowed_key_to_key",
    ):
        if token not in vocabulary:
            errors.append(f"range vocabulary omits endpoint observation {token}")
    for token in (
        "hash_length_step",
        "hash_item_step",
        "hash_items_in_order",
        "debug_builder_start",
        "debug_builder_variant",
        "debug_builder_entry",
        "debug_builder_finish",
        "debug_entries_in_order",
    ):
        if token not in vocabulary:
            errors.append(f"effect vocabulary omits ordered primitive {token}")

    forbidden_legacy_primitives = (
        "range_start_bound_kind",
        "range_end_bound_kind",
        "range_item_to_start_order",
        "range_item_to_end_order",
        "retain_callback_keep",
        "retain_callback_next",
        "retain_callback_effect",
        "difference_hint_self_len",
        "difference_hint_other_len",
        "symmetric_difference_hint_left_len",
        "symmetric_difference_hint_right_len",
        "intersection_hint_first_len",
        "intersection_hint_second_len",
        "union_hint_left_len",
        "union_hint_right_len",
        "borrowed_key_less",
        "borrowed_key_equal",
    )
    for primitive in forbidden_legacy_primitives:
        if re.search(
            rf"\bpub\s+uninterp\s+spec\s+fn\s+{re.escape(primitive)}\b",
            vocabulary,
        ):
            errors.append(
                f"shared vocabulary retains source-unbound primitive {primitive}"
            )

    bound_function_tokens: dict[str, tuple[str, ...]] = {
        "range_bound_order": (
            "range.spec_start_bound()",
            "range.spec_end_bound()",
            "cmp_spec",
        ),
        "range_contains": (
            "range.spec_start_bound()",
            "range.spec_end_bound()",
            "borrowed_key_order",
            "SpecBound::Included",
            "SpecBound::Excluded",
            "SpecBound::Unbounded",
        ),
        "borrowed_key_order": (
            "borrowed_key_projection(item).cmp_spec(key)",
        ),
        "borrowed_key_order_law": (
            "borrowed_key_order",
            "sets_borrowed_key_to_key",
            "Ordering::Equal",
        ),
        "borrowed_representative": (
            "borrowed_key_order(&items[0], key) == Ordering::Equal",
        ),
        "remove_borrowed_representative": (
            "borrowed_key_order(&items[0], key) == Ordering::Equal",
        ),
        "split_before": (
            "borrowed_key_order(&items[0], key) == Ordering::Less",
        ),
        "split_at_or_after": (
            "borrowed_key_order(&items[0], key) == Ordering::Less",
        ),
        "difference_stitch_step": (
            "if first.len() == 0",
            "Seq::empty(),\n                            second,",
        ),
        "fn_mut_step_law": (
            "state.requires((item,))",
            "state.ensures((item,), result)",
            "call_ensures::<(&T,), &mut F>",
            "mut_ref_current(callback) == state",
            "mut_ref_future(callback) == post",
        ),
        "retain_callback_trace_law": (
            "fn_mut_step_law",
            "fn_mut_post_state",
        ),
        "difference_hint_lengths": ("difference_source_state",),
        "symmetric_difference_hint_lengths": (
            "symmetric_difference_source_state",
            "merge_left_remaining",
            "merge_right_remaining",
        ),
        "intersection_hint_lengths": ("intersection_source_state",),
        "union_hint_lengths": (
            "union_source_state",
            "merge_left_remaining",
            "merge_right_remaining",
        ),
        "difference_debug_shape": (
            "difference_source_state",
            "state.variant",
            "state.first",
            "state.second",
            "state.lookup",
        ),
        "symmetric_difference_debug_shape": (
            "symmetric_difference_source_state",
            "state.peeked_side",
            "state.peeked",
        ),
        "intersection_debug_shape": (
            "intersection_source_state",
            "state.variant",
            "state.answer",
        ),
        "union_debug_shape": (
            "union_source_state",
            "state.peeked_side",
            "state.peeked",
        ),
        "extract_if_drop_transition": (
            "retained: extract_if_set(iter)",
            "unvisited: extract_if_pending(iter)",
            "active: false",
        ),
        "extract_if_panic_transition": (
            "extract_if_unwind_step",
            "extract_if_set(iter)",
            "extract_if_pending(iter)",
        ),
        "extract_if_unwind_step": (
            "panicking_candidate: candidate",
            "cursor_taken: candidate.is_some()",
            "predicate_unwound: candidate.is_some()",
            "removal_performed: false",
            "unvisited: Seq::empty()",
        ),
        "extract_if_drop_law": (
            "extract_if_drop_transition",
            "extract_if_partial_drop_set",
            "extract_if_initial_set",
            "extract_if_yielded",
        ),
        "extract_if_panic_law": (
            "extract_if_panic_transition",
            "extract_if_panic_preserves_elements",
            "extract_if_partial_drop_set",
            "extract_if_initial_set",
            "extract_if_yielded",
            "transition.panicking_candidate",
            "transition.cursor_taken",
            "transition.predicate_unwound",
            "transition.removal_performed",
        ),
    }
    for function, tokens in bound_function_tokens.items():
        body = spec_function_body(vocabulary, function)
        if not body:
            errors.append(
                f"shared vocabulary lacks source-bound body for {function}"
            )
            continue
        for token in tokens:
            if token not in body:
                errors.append(
                    f"{function} is not source-bound: missing {token}"
                )

    projection_marker = "pub fn borrowed_key_projection_exec"
    projection_function_start = vocabulary.find(projection_marker)
    projection_start = vocabulary.rfind(
        "#[verifier::external_body]",
        0,
        projection_function_start,
    )
    projection_end = vocabulary.find(
        "\n}\n",
        projection_function_start,
    )
    projection_block = (
        vocabulary[projection_start : projection_end + 3]
        if projection_start >= 0 and projection_end >= 0
        else ""
    )
    for token in (
        "#[verifier::external_body]",
        "result == borrowed_key_projection(item)",
        "item.borrow()",
    ):
        if token not in projection_block:
            errors.append(
                "borrowed_key_projection_exec is not source-bound: "
                f"missing {token}"
            )

    family_tokens: dict[str, tuple[str, ...]] = {
        "adapter_specific_size_hint": ("result.0", "result.1"),
        "borrowed_representative_removal": (
            "borrowed_representative",
            "remove_borrowed_representative",
        ),
        "difference_adapter_construction": (
            "difference_sequence",
            ".to_set()",
            "increasing_seq",
        ),
        "extract_if_construction": (
            "range_bounds_law",
            "range_order_law",
            "extract_if_pending",
            "extract_if_decisions",
            "extract_if_set",
            "retain_selected",
            "extract_if_predicate_state",
            "extract_if_initial_set",
            "extract_if_yielded",
            "extract_if_drop_law",
            "extract_if_panic_law",
        ),
        "intersection_adapter_construction": (
            "intersection_source_sequence",
            ".to_set()",
            "increasing_seq",
        ),
        "ordered_callback_retain": (
            "retain_callback_trace_law",
            "retain_decisions",
            "retain_effect_trace",
            "retain_selected",
        ),
        "ordered_debug_format": (
            "apply_debug_shape",
            "debug_shape_law",
            "*final(",
            "result ==",
        ),
        "ordered_endpoint_observer": (
            "btree_set_sequence",
            "result.is_some()",
        ),
        "ordered_endpoint_removal": (
            "btree_set_sequence",
            "drop_",
            "final(",
        ),
        "ordered_extend_transition": (
            "into_iterator_sequence",
            "extend_sequence",
            "btree_set_sequence",
        ),
        "ordered_iterator_backward_step": (
            "result ==",
            "drop_last",
        ),
        "ordered_iterator_clone": ("remaining", "=="),
        "ordered_iterator_construction": (
            "remaining",
            "btree_set_sequence",
            "increasing_seq",
        ),
        "ordered_iterator_empty_default": ("remaining", "Seq::empty()"),
        "ordered_iterator_exact_len": ("result as nat", "remaining"),
        "ordered_iterator_forward_step": ("result ==", "drop_first"),
        "ordered_iterator_terminal_selection": ("result ==", "remaining"),
        "ordered_range_construction": (
            "range_start_after_end",
            "range_equal_excluded",
            "range_bounds_law",
            "range_order_law",
            "range_sequence",
            "increasing_seq",
        ),
        "ordered_set_comparison": ("seq_lex_", "result =="),
        "ordered_set_hash": (
            "apply_set_hash",
            "btree_set_sequence",
            ".len()",
        ),
        "ordered_set_partition": (
            "split_before",
            "split_at_or_after",
            ".union(",
        ),
        "owned_set_operation": (
            "clone_sequence",
            "increasing_seq",
        ),
        "representative_replacement": (
            "cmp_equal_representative",
            "replace_representative",
        ),
        "set_append_transition": (
            "union_sequence",
            "Seq::empty()",
        ),
        "set_clone_transition": ("clone_sequence", "btree_set_sequence"),
        "set_equality": ("seq_eq_spec", "result =="),
        "set_relation_observer": ("result ==",),
        "sorted_deduplicating_conversion": (
            "stable_sorted_sequence",
            "dedup_last_sorted",
            "to_multiset",
            "stable_tie_order",
        ),
        "symmetric_difference_adapter_construction": (
            "symmetric_difference_sequence",
            ".to_set()",
            "increasing_seq",
        ),
        "union_adapter_construction": (
            "union_sequence",
            ".to_set()",
            "increasing_seq",
        ),
    }
    hint_tokens = {
        "Difference": "difference_hint_lengths",
        "SymmetricDifference": "symmetric_difference_hint_lengths",
        "Intersection": "intersection_hint_variant",
        "Union": "union_hint_lengths",
        "ExtractIf": "extract_if_length_bound",
    }
    for row in live_rows:
        if row.disposition != "generated":
            continue
        _binder, inputs, output, _where_clause = model.proxy_parts(row)
        requirements = model.require_lines(row, inputs, output)
        clauses = model.ensure_lines(row, inputs, output)
        joined = "\n".join([*requirements, *clauses])
        if not clauses:
            errors.append(f"{row.target_id}: generated contract has no clauses")
            continue
        if len(clauses) == 1 and "==" not in joined and "<" not in joined:
            errors.append(f"{row.target_id}: principal behavior is one opaque predicate")
        comparison_law = required_comparison_law(row)
        if comparison_law is not None:
            expected_prefix = f"({comparison_law}) ==> ("
            if not comparison_law or any(
                not clause.startswith(expected_prefix)
                for clause in clauses
            ):
                errors.append(
                    f"{row.target_id}: order-dependent contract is not "
                    f"guarded by {comparison_law}"
                )
        for token in family_tokens.get(row.semantic_family, ()):
            if token not in joined:
                errors.append(
                    f"{row.target_id}: {row.semantic_family} omits direct token {token}"
                )
        if row.semantic_family == "adapter_specific_size_hint":
            token = hint_tokens.get(row.owner["name"])
            if token is not None and token not in joined:
                errors.append(
                    f"{row.target_id}: size_hint omits source-specific {token}"
                )
            source_state_token = {
                "Difference": "difference_source_state_law",
                "SymmetricDifference": "symmetric_difference_source_state_law",
                "Intersection": "intersection_source_state_law",
                "Union": "union_source_state_law",
            }.get(row.owner["name"])
            if source_state_token is not None and source_state_token not in joined:
                errors.append(
                    f"{row.target_id}: size_hint is not tied to {source_state_token}"
                )
        if (
            row.semantic_family
            in {
                "difference_adapter_construction",
                "symmetric_difference_adapter_construction",
                "intersection_adapter_construction",
                "union_adapter_construction",
            }
            and "source_state(result)" not in joined
        ):
            errors.append(
                f"{row.target_id}: adapter constructor omits exact source state"
            )
        if (
            row.owner["name"]
            in {"Difference", "SymmetricDifference", "Intersection", "Union"}
            and row.function["name"] == "next"
        ):
            for token in ("source_state_law", "_next_step(", "source_state(*final("):
                if token not in joined:
                    errors.append(
                        f"{row.target_id}: adapter next omits state transition {token}"
                    )
        if row.owner["name"] == "ExtractIf" and row.function["name"] == "next":
            for token in (
                "first_true",
                "extract_if_pending",
                "extract_if_set",
                "extract_if_callback_count",
                "extract_if_predicate_state",
                "retain_callback_state_after",
                "extract_if_initial_set",
                "extract_if_yielded",
                "extract_if_drop_law",
                "extract_if_panic_law",
            ):
                if token not in joined:
                    errors.append(
                        f"{row.target_id}: ExtractIf::next omits {token}"
                    )
    accepted_contract_text = "\n".join(
        line
        for row in live_rows
        for line in [
            *proof_model.contract_requirements(row),
            *proof_model.contract_lines(row),
        ]
    )
    primitive_names = re.findall(
        r"pub uninterp spec fn ([A-Za-z_][A-Za-z0-9_]*)",
        vocabulary,
    )
    for primitive in primitive_names:
        declaration_count = len(
            re.findall(
                rf"pub uninterp spec fn {re.escape(primitive)}\b",
                vocabulary,
            )
        )
        total_uses = len(
            re.findall(rf"\b{re.escape(primitive)}\b", vocabulary)
        ) + len(
            re.findall(rf"\b{re.escape(primitive)}\b", accepted_contract_text)
        )
        if declaration_count != 1:
            errors.append(
                f"uninterpreted primitive declaration is not unique: {primitive}"
            )
        if total_uses <= declaration_count:
            errors.append(f"uninterpreted primitive is unused: {primitive}")
    return errors


def verify_static(*, include_proofs: bool = True) -> list[str]:
    errors = verify_schema()
    try:
        check_provenance.validate(ROOT)
    except Exception as error:
        errors.append(f"provenance: {error}")

    required = (INVENTORY, CATALOG, EXCLUSIONS, EXACT_AUDIT, AGGREGATE)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        return [*errors, f"missing static aggregate artifacts: {missing}"]

    payload = model.load_rustdoc()
    live_rows, live_exclusions, live_derivation = model.derive_inventory(payload)
    live_records = [model.metadata_for(row) for row in live_rows]
    inventory = load_json(INVENTORY)
    rows = inventory.get("rows") or []
    if [row_key(row) for row in rows] != [row_key(row) for row in live_records]:
        errors.append("stored inventory differs from live rustdoc/source derivation")
    if inventory.get("derivation") != live_derivation:
        errors.append("stored inventory derivation metadata is stale")
    target_ids = [row.get("target_id") for row in rows]
    if len(target_ids) != len(set(target_ids)):
        errors.append("inventory target IDs are duplicated")
    item_ids = [row.get("rustdoc_item_id") for row in rows]
    if len(item_ids) != len(set(item_ids)):
        errors.append("inventory rustdoc item bindings are duplicated")
    dispositions = Counter(row.get("disposition") for row in rows)
    derived_counts = {
        "stable_inventory_total": len(rows),
        "exact_vstd": dispositions["exact_vstd"],
        "generated": dispositions["generated"],
        "genuinely_impossible": dispositions["genuinely_impossible"],
        "pending": dispositions["pending"],
    }
    if inventory.get("counts") != derived_counts:
        errors.append(
            f"inventory counts are not row-derived: {inventory.get('counts')} != "
            f"{derived_counts}"
        )
    if len(rows) != sum(
        derived_counts[name]
        for name in ("exact_vstd", "generated", "genuinely_impossible", "pending")
    ):
        errors.append("inventory disposition reconciliation does not hold")
    if derived_counts["pending"] != 0:
        errors.append("inventory has pending rows")
    if any(row.get("disposition") not in {"exact_vstd", "generated"} for row in rows):
        errors.append("this campaign contains an unapproved impossible or unknown row")

    stored_exclusions = load_json(EXCLUSIONS).get("rows")
    if stored_exclusions != live_exclusions:
        errors.append("stored unstable/non-executable exclusions are stale")
    extend_exclusions = [
        row
        for row in live_exclusions
        if row.get("kind") == "unstable_trait_method"
        and str(row.get("name")).endswith("::extend_one")
    ]
    if len(extend_exclusions) != 2:
        errors.append("both unstable Extend::extend_one overrides are not excluded")

    exact_audit = load_json(EXACT_AUDIT)
    exact_rows = [row for row in rows if row["disposition"] == "exact_vstd"]
    if exact_audit.get("dimensions") != list(model.MATCH_DIMENSIONS):
        errors.append("exact-vstd audit dimensions are incomplete")
    if exact_audit.get("matched_count") != len(exact_rows):
        errors.append("exact-vstd audit count differs from inventory rows")
    expected_reverse_scan = model.exact_vstd_reverse_scan(live_rows)
    if exact_audit.get("reverse_scan") != expected_reverse_scan:
        errors.append("exact-vstd reverse declaration scan is stale")
    if expected_reverse_scan.get("complete") is not True:
        errors.append(
            "exact-vstd reverse declaration scan has unmatched, omitted, "
            "or duplicate BTreeSet declarations"
        )
    audit_rows = exact_audit.get("rows") or []
    if [row_key(row) for row in audit_rows] != [row_key(row) for row in exact_rows]:
        errors.append("exact-vstd audit rows differ from inventory exact rows")
    for row in exact_rows:
        reference = row.get("vstd_reference") or {}
        live_row = live_rows[row["ordinal"] - 1]
        expected_reference = model.exact_vstd_evidence(live_row)
        if reference != expected_reference:
            errors.append(
                f"{row['target_id']}: exact-vstd evidence is not parser-derived"
            )
        dimensions = reference.get("dimensions") or {}
        if reference.get("match_dimensions") != list(model.MATCH_DIMENSIONS):
            errors.append(f"{row['target_id']}: exact-vstd match dimension order changed")
        if set(dimensions) != set(model.MATCH_DIMENSIONS) or not all(
            dimensions[name].get("matched") is True for name in model.MATCH_DIMENSIONS
        ):
            errors.append(f"{row['target_id']}: exact-vstd dimension failed")
        if any(
            "source" not in dimensions[name] or "vstd" not in dimensions[name]
            for name in model.MATCH_DIMENSIONS
        ):
            errors.append(
                f"{row['target_id']}: exact-vstd evidence lacks parsed operands"
            )
        line = reference.get("line")
        if not isinstance(line, int):
            errors.append(f"{row['target_id']}: vstd line is missing")
            continue
        try:
            block = model.vstd_block(line)
        except Exception as error:
            errors.append(f"{row['target_id']}: vstd declaration: {error}")
            continue
        if model.sha256_text(block) != reference.get("block_sha256"):
            errors.append(f"{row['target_id']}: vstd declaration hash is stale")

    catalog = load_json(CATALOG)
    if [row_key(row) for row in catalog.get("rows", [])] != [
        row_key(row) for row in rows
    ]:
        errors.append("all-spec catalog differs from inventory")
    expected_catalog_counts = {
        **derived_counts,
        "specified_total": len(rows),
        "strict_specification_coverage": 1.0,
    }
    if catalog.get("counts") != expected_catalog_counts:
        errors.append("all-spec catalog counts are not inventory-derived")
    generated_path = ROOT / "specs/generated_btree_set_specs.rs"
    vocabulary_path = ROOT / "specs/btree_set_shared_vocabulary.rs"
    references_path = ROOT / "specs/existing_vstd/references.json"
    for path in (generated_path, vocabulary_path, references_path, ROOT / "specs/README.md"):
        if not path.is_file():
            errors.append(f"missing mandatory specs interface: {path.relative_to(ROOT)}")
    if generated_path.is_file():
        generated = generated_path.read_text(encoding="utf-8")
        expected_generated = model.generated_spec_source(live_rows)
        if generated != expected_generated:
            errors.append("generated specification source differs from live generation")
        direct_expected = sum(row.disposition == "generated" for row in live_rows)
        if generated.count("pub assume_specification") != direct_expected:
            errors.append("generated direct declaration count differs from inventory")
        for pattern in ("ensures true", "requires false", "arbitrary()"):
            if pattern in generated:
                errors.append(f"anti-vacuity violation in generated specs: {pattern}")
    if vocabulary_path.is_file() and vocabulary_path.read_text(
        encoding="utf-8"
    ) != model.SHARED_VOCABULARY:
        errors.append("shared vocabulary differs from campaign model")
    errors.extend(verify_contract_semantics(live_rows))
    determinism_root = ROOT / "verification/spec_determinism_harnesses"
    determinism_manifest_path = determinism_root / "manifest.json"
    generated_rows = [
        row for row in live_rows if row.disposition == "generated"
    ]
    if not determinism_manifest_path.is_file():
        errors.append("missing specification determinism harness manifest")
    else:
        determinism_manifest = load_json(determinism_manifest_path)
        stored_records = {
            record.get("target_id"): record
            for record in determinism_manifest.get("targets", [])
        }
        expected_records = []
        for row in generated_rows:
            source_path = determinism_root / f"{row.target_id}.rs"
            record = stored_records.get(row.target_id)
            expected_metadata = {
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
                "source": str(source_path.relative_to(ROOT)),
            }
            if record is None or any(
                record.get(key) != value
                for key, value in expected_metadata.items()
            ):
                errors.append(
                    f"{row.target_id}: specification determinism binding is stale"
                )
                continue
            expected_records.append(record)
            if (
                not source_path.is_file()
                or record.get("source_sha256")
                != sha256_file(source_path)
            ):
                errors.append(
                    f"{row.target_id}: specification determinism source hash is stale"
                )
        if (
            determinism_manifest.get("target_count") != len(generated_rows)
            or determinism_manifest.get("targets") != expected_records
        ):
            errors.append("specification determinism manifest is stale")
        actual_sources = {
            path.name for path in determinism_root.glob("*.rs")
        }
        expected_sources = {
            f"{row.target_id}.rs" for row in generated_rows
        }
        if actual_sources != expected_sources:
            errors.append("specification determinism harness set is incomplete")

    catalog_mirror = ROOT / "catalog/btree_set_spec_catalog.json"
    proof_inventory = ROOT / "proof_inventory/targets.json"
    if not catalog_mirror.is_file() or load_json(catalog_mirror).get("rows") != rows:
        errors.append("top-level catalog mirror differs from inventory")
    if not include_proofs:
        static_audits = (
            "source_binding_audit.json",
            "signature_generic_shape_audit.json",
            "anti_vacuity_audit.json",
            "semantic_binding_mutation_audit.json",
            "shared_helper_usage_audit.json",
            "outcome_equivalence_audit.json",
            "inventory_exclusion_audit.json",
        )
        for name in static_audits:
            path = ROOT / "verification/audits" / name
            if not path.is_file() or not str(
                load_json(path).get("status", "")
            ).startswith("passed"):
                errors.append(f"specification audit is not passed: {name}")
        return errors
    if (
        not proof_inventory.is_file()
        or load_json(proof_inventory).get("targets") != rows
    ):
        errors.append("proof inventory differs from selected inventory rows")

    schema = load_json(SCHEMA)
    required_harness_files = set(schema["harness"]["required_files"])
    harness_root = ROOT / "proof_harnesses"
    actual_dirs = (
        {path.name for path in harness_root.iterdir() if path.is_dir()}
        if harness_root.is_dir()
        else set()
    )
    expected_dirs = set(target_ids)
    if actual_dirs != expected_dirs:
        errors.append(
            "proof harness directory mismatch "
            f"missing={sorted(expected_dirs-actual_dirs)} "
            f"extra={sorted(actual_dirs-expected_dirs)}"
        )
    literal_external_body = 0
    lower_author_source = inspect.getsource(
        proof_model.dependency_contract_lines
    )
    if (
        "contract_lines(row" in lower_author_source
        or "lower_state_clause(" in lower_author_source
        or hasattr(proof_model, "lower_state_clause")
    ):
        errors.append(
            "lower contracts are derived from accepted public clauses"
        )
    completeness_generator_source = inspect.getsource(
        proof_model.completeness_clause_body
    )
    if (
        ".expected" in completeness_generator_source
        or "_completeness_shape_body" in completeness_generator_source
    ):
        errors.append(
            "completeness predicates bypass literal clause translation"
        )
    if "from tools import proof_model" in inspect.getsource(
        completeness_audit
    ):
        errors.append(
            "completeness audit imports the proof generator oracle"
        )
    retain_model_source = inspect.getsource(
        proof_model.retain_control_flow_source
    )
    if (
        "#[verifier::external_body]\n"
        "pub proof fn lemma_callback_decision_double_negation"
        in retain_model_source
    ):
        errors.append(
            "retain double-negation remains an admitted proof helper"
        )
    if set(completeness_audit.LITERAL_RECONSTRUCTION_DIGESTS) != set(
        target_ids
    ):
        errors.append(
            "frozen completeness reconstruction does not cover every target"
        )
    specification_review_path = ROOT / "reviews/inventory_specification.json"
    specification_review_sha = (
        sha256_file(specification_review_path)
        if specification_review_path.is_file()
        else None
    )
    if specification_review_sha is None:
        errors.append("proof artifacts exist without accepted specification review")
    by_id = {row["target_id"]: row for row in rows}
    target_by_key = {
        (row.owner["name"], row.trait, row.function["name"]): row.target_id
        for row in live_rows
    }
    for target_id in sorted(expected_dirs & actual_dirs):
        target_root = harness_root / target_id
        missing_files = sorted(
            name for name in required_harness_files if not (target_root / name).is_file()
        )
        if missing_files:
            errors.append(f"{target_id}: missing harness files {missing_files}")
            continue
        row = by_id[target_id]
        excerpt = target_root / "source_excerpt.rs"
        if sha256_file(excerpt) != row["source_sha256"]:
            errors.append(f"{target_id}: exact source excerpt hash mismatch")
        binding_path = target_root / "contract_binding.json"
        if not binding_path.is_file() or row_key(load_json(binding_path)) != row_key(row):
            errors.append(f"{target_id}: contract binding differs from inventory")
        implementation = (target_root / "implementation_proof.rs").read_text(
            encoding="utf-8"
        )
        completeness = (target_root / "completeness_proof.rs").read_text(
            encoding="utf-8"
        )
        mutation = (target_root / "mutation_proof.rs").read_text(encoding="utf-8")
        live_row = live_rows[row["ordinal"] - 1]
        expected_implementation = proof_model.source(live_row)
        expected_completeness = proof_model.source(live_row, completeness=True)
        expected_mutation = proof_model.source(live_row, mutation=True)
        if implementation != expected_implementation:
            errors.append(f"{target_id}: implementation proof differs from generator")
        if completeness != expected_completeness:
            errors.append(f"{target_id}: completeness proof differs from generator")
        if mutation != expected_mutation:
            errors.append(f"{target_id}: mutation proof differs from generator")
        checker_adjudication_required = (
            proof_model.requires_associated_item_air_adjudication(live_row)
        )
        checker_adjudication_paths = {
            "proof": target_root / "checker_adjudication_proof.rs",
            "mutation": (
                target_root / "checker_adjudication_mutation.rs"
            ),
            "manifest": target_root / "checker_adjudication.json",
        }
        expected_checker_adjudication: dict[str, Any] | None = None
        if checker_adjudication_required:
            expected_adjudication_proof = (
                proof_model.checker_adjudication_source(live_row)
            )
            expected_adjudication_mutation = (
                proof_model.checker_adjudication_source(
                    live_row,
                    mutation=True,
                )
            )
            expected_checker_adjudication = {
                "schema_version": 1,
                "target_id": target_id,
                "checker_limitation": (
                    "verus-intoiterator-associated-item-air"
                ),
                "exact_signature_source": "implementation_proof.rs",
                "exact_signature_source_sha256": model.sha256_text(
                    expected_implementation
                ),
                "exact_mutation_source": "mutation_proof.rs",
                "exact_mutation_source_sha256": model.sha256_text(
                    expected_mutation
                ),
                "actual_verus_source": "checker_adjudication_proof.rs",
                "actual_verus_source_sha256": model.sha256_text(
                    expected_adjudication_proof
                ),
                "actual_verus_mutation_source": (
                    "checker_adjudication_mutation.rs"
                ),
                "actual_verus_mutation_source_sha256": model.sha256_text(
                    expected_adjudication_mutation
                ),
                "erased_bounds": (
                    proof_model.associated_item_bound_declarations(
                        live_row
                    )
                ),
                "proof_domain_relation": (
                    "bound erasure strengthens the verified domain; "
                    "the exact source signature remains separately "
                    "typechecked and its Verus AIR crash is retained"
                ),
            }
            if (
                not checker_adjudication_paths["proof"].is_file()
                or checker_adjudication_paths["proof"].read_text(
                    encoding="utf-8"
                )
                != expected_adjudication_proof
                or not checker_adjudication_paths["mutation"].is_file()
                or checker_adjudication_paths["mutation"].read_text(
                    encoding="utf-8"
                )
                != expected_adjudication_mutation
                or not checker_adjudication_paths["manifest"].is_file()
                or load_json(checker_adjudication_paths["manifest"])
                != expected_checker_adjudication
            ):
                errors.append(
                    f"{target_id}: associated-item checker adjudication "
                    "artifacts are stale"
                )
        elif any(
            path.exists() for path in checker_adjudication_paths.values()
        ):
            errors.append(
                f"{target_id}: unexpected associated-item adjudication"
            )
        literal_external_body += implementation.count("#[verifier::external_body]")
        expected_external_bodies = proof_model.literal_external_body_count(
            live_row
        )
        if "pub fn implementation" not in implementation:
            errors.append(f"{target_id}: public target lowering is not executable")
        if "#[verifier::external_body]\npub fn implementation" in implementation:
            errors.append(f"{target_id}: public target is external_body")
        if implementation.count("#[verifier::external_body]") != expected_external_bodies:
            errors.append(
                f"{target_id}: narrow external-body count differs from source plan"
            )
        dependency_name = proof_model.dependency_function_name(live_row)
        dependency_operation = proof_model.dependency_operation(live_row)
        projection = proof_model.projection_for(
            live_row, model.proxy_parts(live_row)[2]
        )
        if f"pub fn {dependency_name}" not in implementation:
            errors.append(f"{target_id}: narrow source dependency was not retained")
        public_output = model.proxy_parts(live_row)[2]
        dependency_return_type = proof_model.dependency_return_type(
            live_row,
            projection,
        )
        dependency_lower_shape = proof_model.dependency_lower_shape(
            live_row,
            projection,
        )
        if dependency_return_type == public_output:
            errors.append(f"{target_id}: dependency returns the public target shape")
        if (
            f"-> (result: {dependency_return_type})" not in implementation
            and dependency_return_type not in implementation
        ):
            errors.append(f"{target_id}: dependency lower return type is not explicit")
        harness_structs = parse_struct_fields(implementation)
        sanctioned_structs = parse_struct_fields(
            proof_model.COMMON_PROJECTION_TYPES
        )
        sanctioned_signatures = {
            struct_signature(sanctioned_structs, name)
            for name in sanctioned_structs
        }
        for struct_name in harness_structs:
            if struct_name in sanctioned_structs:
                continue
            if struct_signature(harness_structs, struct_name) in sanctioned_signatures:
                errors.append(
                    f"{target_id}: lower dependency uses a field-isomorphic "
                    f"alias struct {struct_name}"
                )
        if (
            f"Narrow source dependency: {dependency_operation}" not in implementation
            or f"Lower return shape: {dependency_lower_shape}" not in implementation
        ):
            errors.append(f"{target_id}: lower operation/return shape is not explicit")
        errors.extend(
            f"{target_id}: {error}"
            for error in proof_text_policy_errors(implementation, completeness)
        )
        if proof_model.uses_private_branch(live_row) and not all(
            token in implementation
            for token in (
                "match source_branch",
                "read_source_discriminant",
                "source_branch ==",
            )
        ):
            errors.append(f"{target_id}: BTreeSet source branch control flow is absent")
        if proof_model.uses_private_branch(live_row):
            branch_inputs = proof_model.signature_parts(
                live_row, "implementation"
            )[0]
            selector_source, selector_call = (
                proof_model.branch_selector_source_and_call(
                    live_row, branch_inputs
                )
            )
            if selector_call not in implementation:
                errors.append(
                    f"{target_id}: source discriminant is not derived from "
                    "the observed source state"
                )
            if "Ghost(" in selector_source:
                errors.append(
                    f"{target_id}: source discriminant has no executable input"
                )
            for (
                pattern,
                branch_guard,
                _suffix,
            ), dependency in zip(
                proof_model.branch_arm_specs(live_row),
                proof_model.dependency_function_names(live_row),
                strict=True,
            ):
                block_starts = [
                    implementation.find(
                        f"#[verifier::external_body]\npub fn "
                        f"{dependency}{delimiter}"
                    )
                    for delimiter in ("<", "(")
                ]
                block_start = min(
                    (index for index in block_starts if index >= 0),
                    default=-1,
                )
                next_external = implementation.find(
                    "#[verifier::external_body]",
                    block_start + 1,
                )
                implementation_start = implementation.find(
                    "\npub fn implementation",
                    block_start,
                )
                candidates = [
                    index
                    for index in (next_external, implementation_start)
                    if index >= 0
                ]
                block_end = min(candidates) if candidates else -1
                branch_block = (
                    implementation[block_start:block_end]
                    if block_start >= 0 and block_end >= 0
                    else ""
                )
                operation_fact = proof_model.branch_operation_fact(
                    live_row, pattern, branch_guard
                )
                if (
                    branch_guard not in branch_block
                    or operation_fact not in branch_block
                ):
                    errors.append(
                        f"{target_id}: branch {pattern} lacks a distinct "
                        "private-operation contract"
                    )
            if re.search(
                r"read_source_discriminant\(Ghost\(\s*-?\d+\s*(?:u8|usize|i32|nat)?\s*\)\)",
                implementation,
            ) or re.search(
                r"let source_branch\s*=\s*-?\d+\s*(?:u8|usize|i32|nat)?",
                implementation,
            ):
                errors.append(
                    f"{target_id}: source discriminant is a constant"
                )
        implementation_body = executable_function_body(
            implementation,
            "implementation",
        )
        mutation_body = executable_function_body(
            mutation,
            "implementation",
        )
        if not implementation_body or not mutation_body:
            errors.append(f"{target_id}: executable proof body cannot be parsed")
        source_order_cursor = 0
        for token in proof_model.implementation_order_tokens(live_row):
            token_index = implementation_body.find(
                token,
                source_order_cursor,
            )
            if token_index < 0:
                errors.append(
                    f"{target_id}: source operation order omits or reorders "
                    f"{token}"
                )
                break
            source_order_cursor = token_index + len(token)
        errors.extend(
            f"{target_id}: {error}"
            for error in parsed_source_call_policy_errors(
                live_row,
                implementation,
            )
        )
        errors.extend(
            f"{target_id}: {error}"
            for error in union_candidate_selection_policy_errors(
                live_row,
                implementation,
                mutation,
            )
        )
        if proof_model.source_owned_adapter_loop(live_row):
            errors.extend(
                f"{target_id}: {error}"
                for error in adapter_source_loop_policy_errors(
                    live_row,
                    implementation,
                )
            )
            errors.extend(
                f"{target_id}: {error}"
                for error in adapter_source_mutation_policy_errors(
                    live_row,
                    implementation,
                    mutation,
                )
            )
        elif proof_model.retains_adapter_source_loop(live_row):
            for token in (
                "_read_source_loop_steps",
                "while completed_source_steps < source_steps",
                "assert(completed_source_steps == source_steps)",
            ):
                if token not in implementation_body:
                    errors.append(
                        f"{target_id}: adapter source loop omits {token}"
                    )
        errors.extend(
            f"{target_id}: {error}"
            for error in selected_public_composition_policy_errors(
                live_row,
                implementation,
            )
        )
        if (
            proof_model.uses_private_branch(live_row)
            and not all(
                implementation_body.count(f"{name}(") == 1
                for name in proof_model.dependency_call_names(live_row)
            )
        ):
            errors.append(
                f"{target_id}: source-discriminated lower operation is not "
                "a distinct call in every executable branch arm"
            )
        if row["contract_fingerprint"] not in implementation:
            errors.append(f"{target_id}: implementation lacks contract fingerprint")
        accepted_clauses = proof_model.contract_lines(live_row)
        expected_lower_clauses = proof_model.emitted_dependency_contract_lines(
            live_row, projection
        )
        dependency_start = external_function_start(
            implementation, dependency_name
        )
        dependency_end = implementation.find(
            "\n\npub fn implementation", dependency_start
        )
        dependency_block = (
            implementation[dependency_start:dependency_end]
            if dependency_start >= 0 and dependency_end >= 0
            else ""
        )
        if proof_model.uses_private_branch(live_row):
            branch_inputs = proof_model.signature_parts(
                live_row, "implementation"
            )[0]
            expected_branch = proof_model.branch_source_value(
                live_row, branch_inputs
            )
            if (
                f"source_branch == {expected_branch}"
                not in dependency_block
            ):
                errors.append(
                    f"{target_id}: lower branch contract is not constrained "
                    "by the observed source state"
                )
        if live_row.semantic_family == "ordered_callback_retain":
            for forbidden in (
                "retain_decisions(&f",
                "retain_effect_trace",
                "f: F",
            ):
                if forbidden in dependency_block:
                    errors.append(
                        f"{target_id}: callback remains inside the map boundary"
                    )
            required_tokens = (
                (
                    "let extraction = "
                    "rust_1_96_selected_extract_if_begin(",
                    f"let consumed = {dependency_name}::<T, F, A>(",
                    "rust_1_96_rejoin_selected_extract_if::<T, A>(",
                )
                if proof_model.requires_selected_public_composition(
                    live_row
                )
                else (
                    "while callback_index < callback_steps",
                    "rust_1_96_call_retain_predicate::<T, F>",
                    "let remove = !keep;",
                    "rust_1_96_drop_extracted_decision(remove)",
                )
            )
            for required_token in required_tokens:
                if required_token not in implementation_body:
                    errors.append(
                        f"{target_id}: verified retain callback flow omits "
                        f"{required_token}"
                    )
        if live_row.semantic_family == "extract_if_construction":
            if len(expected_lower_clauses) != 7 or any(
                token in dependency_block
                for token in (
                    "result.callback_count",
                    "result.predicate_state",
                    "result.yielded",
                )
            ):
                errors.append(
                    f"{target_id}: ExtractIf construction is externalized"
                )
            for required_token in (
                "let constructed = MapExtractIfState",
                "predicate_state: Ghost(pred)",
                "callback_count: Ghost(0nat)",
                "yielded: Ghost(Seq::empty())",
                "drop_valid: lower.drop_valid",
                "panic_valid: lower.panic_valid",
            ):
                if required_token not in implementation_body:
                    errors.append(
                        f"{target_id}: verified ExtractIf construction omits "
                        f"{required_token}"
                    )
        if live_row.semantic_family == "sorted_deduplicating_conversion":
            for required_token in (
                "MapStableSortedInput<T>",
                "_stable_sort",
                "let sorted =",
                "dedup_last_sorted(sorted.sorted@)",
            ):
                if required_token not in implementation:
                    errors.append(
                        f"{target_id}: sorted conversion collapses "
                        f"{required_token}"
                    )
        if (
            live_row.semantic_family == "ordered_extend_transition"
            and live_row.target_id
            != "049_BTreeSet_Extend_extend_2153"
        ):
            required_tokens = (
                "while input_index < input_steps",
                "let item =",
                f"{dependency_name}::<T, A>(",
                "insert_keep_existing(before_insert, item)",
            )
            for required_token in required_tokens:
                if required_token not in implementation_body:
                    errors.append(
                        f"{target_id}: Extend iteration omits "
                        f"{required_token}"
                    )
            if re.search(r"\n\s+iter:\s", dependency_block):
                errors.append(
                    f"{target_id}: Extend iterator remains in the bulk "
                    "map dependency"
                )
        if (
            live_row.owner["name"] == "ExtractIf"
            and live_row.function["name"] == "next"
        ):
            if (
                "rust_1_96_call_extract_if_predicate"
                not in implementation_body
                or "observed_remove" not in implementation_body
                or "this: &ExtractIf" not in implementation
            ):
                errors.append(
                    f"{target_id}: ExtractIf callback is not an executable "
                    "branch input"
                )
        errors.extend(
            f"{target_id}: {error}"
            for error in dependency_policy_errors(
                implementation,
                dependency_name,
                accepted_clauses,
                expected_lower_clauses,
                reject_projected_equivalence=(
                    reject_projected_dependency_equivalence(live_row)
                ),
            )
        )
        for clause in accepted_clauses:
            if clause not in implementation:
                errors.append(
                    f"{target_id}: implementation omits accepted contract clause"
                )
        if "pub proof fn completeness" not in completeness:
            errors.append(f"{target_id}: completeness proof is absent")
        if row["contract_fingerprint"] not in completeness:
            errors.append(f"{target_id}: completeness lacks contract fingerprint")
        if re.search(r"\bout\s*==\s*source_", completeness):
            errors.append(f"{target_id}: completeness depends on a whole-outcome source")
        accepted_requirements = proof_model.contract_requirements(live_row)
        for index, requirement in enumerate(accepted_requirements, start=1):
            digest = model.sha256_text(requirement)
            if requirement not in implementation:
                errors.append(
                    f"{target_id}: implementation omits accepted requirement"
                )
            if (
                f"pub open spec fn accepted_requirement_{index}"
                not in completeness
                or f"Accepted requirement {index} sha256: {digest}"
                not in completeness
                or completeness.count(f"accepted_requirement_{index}(") < 2
            ):
                errors.append(
                    f"{target_id}: completeness omits accepted requirement {index}"
                )
        for index, clause in enumerate(accepted_clauses, start=1):
            digest = model.sha256_text(clause)
            if (
                f"pub open spec fn accepted_clause_{index}" not in completeness
                or f"Accepted clause {index} sha256: {digest}" not in completeness
                or completeness.count(f"accepted_clause_{index}(") < 3
            ):
                errors.append(
                    f"{target_id}: completeness is not derived from accepted clause {index}"
                )
        expected_clause_bodies = [
            completeness_audit.reconstruct_clause(live_row, clause)
            for clause in accepted_clauses
        ]
        emitted_clause_bodies: list[str] = []
        for index in range(1, len(accepted_clauses) + 1):
            emitted_body = spec_function_body(
                completeness, f"accepted_clause_{index}"
            ).strip()
            emitted_clause_bodies.append(emitted_body)
            if emitted_body != expected_clause_bodies[index - 1].strip():
                errors.append(
                    f"{target_id}: accepted_clause_{index} body is not the "
                    "mechanical translation of the accepted source clause"
                )
        expected_requirement_bodies = [
            completeness_audit.reconstruct(live_row, requirement)
            for requirement in accepted_requirements
        ]
        emitted_requirement_bodies: list[str] = []
        for index in range(1, len(accepted_requirements) + 1):
            emitted_body = spec_function_body(
                completeness, f"accepted_requirement_{index}"
            ).strip()
            emitted_requirement_bodies.append(emitted_body)
            if emitted_body != expected_requirement_bodies[index - 1].strip():
                errors.append(
                    f"{target_id}: accepted_requirement_{index} body is not the "
                    "mechanical translation of the accepted source requirement"
                )
        if completeness_audit.reconstruction_digest(
            accepted_requirements,
            accepted_clauses,
            emitted_requirement_bodies,
            emitted_clause_bodies,
        ) != completeness_audit.LITERAL_RECONSTRUCTION_DIGESTS.get(
            target_id
        ):
            errors.append(
                f"{target_id}: completeness differs from the frozen "
                "independent literal reconstruction"
            )
        if "left_" not in completeness or "right_" not in completeness:
            errors.append(f"{target_id}: completeness lacks two accepted candidates")
        if "whole-contract dependency" not in completeness:
            errors.append(f"{target_id}: completeness anti-surrogate declaration is absent")
        if "Source-step mutation" not in mutation:
            errors.append(f"{target_id}: source-step mutation is absent")
        mutation_manifest = load_json(target_root / "mutation_manifest.json")
        descriptor = proof_model.mutation_descriptor(live_row)
        affected_indices = list(descriptor["affected_clause_indices"])
        expected_mutation_manifest = {
            "schema_version": 1,
            "target_id": target_id,
            **descriptor,
            "affected_clause_sha256": [
                model.sha256_text(accepted_clauses[index - 1])
                for index in affected_indices
            ],
            "mutation_source_sha256": model.sha256_text(
                expected_mutation
            ),
            "expected_outcome": (
                "rejected_by_actual_verus_semantic_obligation"
            ),
        }
        if mutation_manifest != expected_mutation_manifest:
            errors.append(
                f"{target_id}: source-step mutation manifest is stale"
            )
        dependency_start = external_function_start(
            implementation, dependency_name
        )
        dependency_end = implementation.find(
            "\n\npub fn implementation",
            dependency_start,
        )
        mutation_dependency_start = external_function_start(
            mutation, dependency_name
        )
        mutation_dependency_end = mutation.find(
            "\n\npub fn implementation",
            mutation_dependency_start,
        )
        semantic_implementation_body = implementation_body
        semantic_mutation_body = mutation_body
        if live_row.function["name"] == "is_subset":
            semantic_implementation_body = executable_function_body(
                implementation,
                "rust_1_96_selected_is_subset_source",
            )
            semantic_mutation_body = executable_function_body(
                mutation,
                "rust_1_96_selected_is_subset_source",
            )
        if (
            dependency_start < 0
            or dependency_end < 0
            or mutation_dependency_start < 0
            or mutation_dependency_end < 0
            or implementation[dependency_start:dependency_end]
            != mutation[mutation_dependency_start:mutation_dependency_end]
            or descriptor["original_fragment"]
            not in semantic_implementation_body
            or descriptor["mutated_fragment"]
            not in semantic_mutation_body
            or "mutated_source_step" in implementation
            or "mutated_source_step" in mutation
            or semantic_implementation_body == semantic_mutation_body
            or any(clause not in mutation for clause in accepted_clauses)
        ):
            errors.append(
                f"{target_id}: mutation does not preserve the accepted contract"
            )
        if (
            projection.kind == "set_adapter"
            and not proof_model.requires_selected_public_composition(
                live_row
            )
            and live_row.semantic_family not in {
                "difference_adapter_construction",
                "intersection_adapter_construction",
            }
            and "remaining: Ghost(Seq::empty())" not in mutation_body
        ):
            errors.append(
                f"{target_id}: adapter mutation does not alter a "
                "projector-observed cursor"
            )
        if (
            live_row.semantic_family
            in proof_model.EMPTY_ADAPTER_STATE_MUTATION_FAMILIES
            and not proof_model.requires_selected_public_composition(
                live_row
            )
            and (
                f"state: {proof_model.EMPTY_ADAPTER_STATE_EXPRESSION}"
                not in mutation_body
                or "remaining: Ghost(Seq::empty())" not in mutation_body
            )
        ):
            errors.append(
                f"{target_id}: set-algebra constructor mutation does not "
                "replace both projector-observed adapter state and cursor"
            )
        if (
            projection.kind == "extract_state"
            and (
                "pending: Ghost(Seq::empty())" not in mutation_body
                or "remaining: Ghost(Seq::empty())" not in mutation_body
            )
        ):
            errors.append(
                f"{target_id}: ExtractIf mutation does not alter "
                "projector-observed inner state"
            )
        if (
            projection.kind
            in {
                "set_state",
                "set_state_global",
                "borrowed_iter",
                "borrowed_range",
                "owned_iter",
            }
            and proof_model.mutation_invalidates_projector(
                live_row,
                projection,
            )
            and "valid: false" not in mutation_body
        ):
            errors.append(
                f"{target_id}: representation mutation does not invalidate "
                "the lower-to-public projector"
            )
        if (
            projection.kind in {
                "set_state",
                "set_state_global",
            }
            and not proof_model.mutation_invalidates_projector(
                live_row,
                projection,
            )
            and live_row.semantic_family
            != "sorted_deduplicating_conversion"
            and "keys: Ghost(Seq::empty())" not in mutation_body
        ):
            errors.append(
                f"{target_id}: set mutation does not alter projected keys"
            )
        if (
            projection.kind in {
                "borrowed_iter",
                "borrowed_range",
                "owned_iter",
            }
            and not proof_model.mutation_invalidates_projector(
                live_row,
                projection,
            )
            and "remaining: Ghost(Seq::empty())" not in mutation_body
        ):
            errors.append(
                f"{target_id}: iterator mutation does not alter the "
                "projected cursor"
            )
        trust = load_json(target_root / "trust_boundaries.json")
        expected_literal_counts = proof_model.literal_external_body_counts(
            live_row
        )
        literal_functions = proof_model.literal_external_body_function_names(
            implementation
        )
        observed_literal_counts = {
            "target": literal_functions.count("implementation"),
            "completeness": completeness.count("#[verifier::external_body]"),
            "dependency": sum(
                literal_functions.count(name)
                for name in proof_model.dependency_function_names(live_row)
            ),
            "helper": 0,
            "harness": len(literal_functions),
        }
        observed_literal_counts["helper"] = (
            observed_literal_counts["harness"]
            - observed_literal_counts["target"]
            - observed_literal_counts["dependency"]
        )
        if observed_literal_counts != expected_literal_counts:
            errors.append(
                f"{target_id}: observed external_body categories "
                f"{observed_literal_counts} differ from source plan "
                f"{expected_literal_counts}"
            )
        trust_count_fields = {
            "target_external_body_count": "target",
            "completeness_external_body_count": "completeness",
            "dependency_external_body_count": "dependency",
            "helper_external_body_count": "helper",
            "harness_literal_external_body_count": "harness",
        }
        if (
            trust.get("target_external_body") is not False
            or trust.get("literal_external_body_count")
            != expected_literal_counts["harness"]
            or trust.get("literal_external_body_counts_by_category")
            != expected_literal_counts
            or any(
                trust.get(field) != expected_literal_counts[category]
                for field, category in trust_count_fields.items()
            )
        ):
            errors.append(f"{target_id}: trust metadata permits a target assumption")
        shared_external_bodies = model.SHARED_VOCABULARY.count(
            "#[verifier::external_body]"
        )
        if (
            trust.get("included_shared_vocabulary_external_body_count")
            != shared_external_bodies
            or trust.get("compiled_harness_external_body_count")
            != implementation.count("#[verifier::external_body]")
            + shared_external_bodies
        ):
            errors.append(f"{target_id}: included type-model trust count is stale")
        if trust.get("whole_contract_dependency") is not False:
            errors.append(f"{target_id}: trust metadata permits whole-contract dependency")
        expected_standard_library_assumptions = (
            proof_model.standard_library_assumption_boundaries(live_row)
        )
        if (
            implementation.count("pub assume_specification")
            != len(expected_standard_library_assumptions)
            or trust.get("assume_specification_count")
            != len(expected_standard_library_assumptions)
            or trust.get("assume_specification_boundaries")
            != expected_standard_library_assumptions
            or trust.get("suppressed_verifier_warnings")
            != [
                record["verifier_allow"]
                for record in expected_standard_library_assumptions
            ]
            or implementation.count(
                "#[verifier::allow(undeclared_external_trait)]"
            )
            != len(expected_standard_library_assumptions)
        ):
            errors.append(
                f"{target_id}: standard-library assumption accounting is stale"
            )
        if trust.get("checker_adjudication") != (
            "verus-intoiterator-associated-item-air"
            if checker_adjudication_required
            else None
        ):
            errors.append(
                f"{target_id}: checker adjudication trust metadata is stale"
            )
        expected_adjudication_external_bodies = (
            {
                "implementation": (
                    proof_model.checker_adjudication_source(
                        live_row
                    ).count("#[verifier::external_body]")
                ),
                "mutation": (
                    proof_model.checker_adjudication_source(
                        live_row,
                        mutation=True,
                    ).count("#[verifier::external_body]")
                ),
            }
            if checker_adjudication_required
            else {"implementation": 0, "mutation": 0}
        )
        if (
            trust.get("checker_adjudication_external_body_count")
            != expected_adjudication_external_bodies
        ):
            errors.append(
                f"{target_id}: checker adjudication trust surface is stale"
            )
        accepted_specification = trust.get("accepted_specification") or {}
        if (
            accepted_specification.get("review")
            != "reviews/inventory_specification.json"
            or accepted_specification.get("review_sha256")
            != specification_review_sha
        ):
            errors.append(
                f"{target_id}: proof is not hash-bound to accepted specification"
            )
        dependency_manifest = load_json(target_root / "dependency_assumptions.json")
        expected_selected_dependencies = (
            proof_model.selected_public_dependency_target_ids(
                live_row,
                target_by_key,
            )
        )
        if (
            dependency_manifest.get("selected_public_dependency_targets")
            != expected_selected_dependencies
        ):
            errors.append(
                f"{target_id}: selected public dependency targets are stale"
            )
        map_dependencies = [
            item
            for item in dependency_manifest.get("dependencies", [])
            if item.get("category") == "btree_map_delegation"
        ]
        if (
            len(map_dependencies) != 1
            or map_dependencies[0].get("operation") != dependency_operation
            or map_dependencies[0].get("lower_return_shape")
            != dependency_lower_shape
            or map_dependencies[0].get("lower_observation_clauses")
            != expected_lower_clauses
            or map_dependencies[0].get("lower_observation_clause_sha256")
            != [model.sha256_text(line) for line in expected_lower_clauses]
            or map_dependencies[0].get("contract_authorship")
            != (
                "source-operation registry independent of accepted "
                "public clauses"
            )
            or map_dependencies[0].get("whole_target_contract") is not False
        ):
            errors.append(f"{target_id}: lower dependency manifest is broad or stale")
        standard_library_dependencies = [
            item
            for item in dependency_manifest.get("dependencies", [])
            if item.get("category")
            == "core_option_combinator_semantics"
        ]
        if (
            standard_library_dependencies
            != proof_model.standard_library_assumption_boundaries(live_row)
        ):
            errors.append(
                f"{target_id}: standard-library dependency manifest is stale"
            )
        transformation = load_json(target_root / "transformation_manifest.json")
        expected_transformation_adjudication = (
            {
                "limitation": "verus-intoiterator-associated-item-air",
                "erased_bounds": (
                    proof_model.associated_item_bound_declarations(
                        live_row
                    )
                ),
                "proof_domain_relation": (
                    "removing the associated-item equality precondition "
                    "strictly strengthens the actual-Verus proof domain"
                ),
                "exact_implementation_sha256": model.sha256_text(
                    expected_implementation
                ),
                "actual_verus_implementation_sha256": (
                    expected_checker_adjudication[
                        "actual_verus_source_sha256"
                    ]
                    if expected_checker_adjudication is not None
                    else ""
                ),
                "exact_mutation_sha256": model.sha256_text(
                    expected_mutation
                ),
                "actual_verus_mutation_sha256": (
                    expected_checker_adjudication[
                        "actual_verus_mutation_source_sha256"
                    ]
                    if expected_checker_adjudication is not None
                    else ""
                ),
            }
            if checker_adjudication_required
            else None
        )
        if (
            transformation.get("checker_adjudication")
            != expected_transformation_adjudication
        ):
            errors.append(
                f"{target_id}: transformation checker adjudication is stale"
            )
        if transformation.get("source_operation_order") != (
            proof_model.implementation_operation_order(live_row)
        ):
            errors.append(
                f"{target_id}: source operation order manifest is stale"
            )
        expected_source_calls = proof_model.source_call_coverage(live_row)
        if transformation.get("source_call_coverage") != expected_source_calls:
            errors.append(
                f"{target_id}: source-call coverage manifest is stale"
            )
        elif expected_source_calls["complete"] is not True:
            errors.append(
                f"{target_id}: source-call coverage has unresolved public calls"
            )
        expected_retained = [
            {
                "kind": kind,
                "evidence": (
                    "executable implementation body and ordered token audit"
                ),
            }
            for kind in proof_model.retained_source_construct_kinds(
                live_row
            )
        ]
        if transformation.get("retained_constructs") != expected_retained:
            errors.append(
                f"{target_id}: retained source-control manifest is stale"
            )
        clause_lowering = (
            transformation.get("contract_projection", {})
            .get("clause_lowering", [])
        )
        if clause_lowering != [
            {
                "index": index,
                "accepted_clause": clause,
                "sha256": model.sha256_text(clause),
                "completeness_predicate": f"accepted_clause_{index}",
            }
            for index, clause in enumerate(accepted_clauses, start=1)
        ]:
            errors.append(
                f"{target_id}: accepted-clause completeness lowering is stale"
            )
        requirement_lowering = (
            transformation.get("contract_projection", {})
            .get("requirement_lowering", [])
        )
        if requirement_lowering != [
            {
                "index": index,
                "accepted_requirement": requirement,
                "sha256": model.sha256_text(requirement),
                "completeness_predicate": f"accepted_requirement_{index}",
            }
            for index, requirement in enumerate(
                accepted_requirements, start=1
            )
        ]:
            errors.append(
                f"{target_id}: accepted-requirement completeness lowering is stale"
            )
        narrow_lowering = (
            transformation.get("contract_projection", {})
            .get("narrow_dependency_clause_lowering", [])
        )
        if narrow_lowering != [
            {
                "index": index,
                "lower_clause": lower,
                "lower_clause_sha256": model.sha256_text(lower),
                "derivation_role": "authored_lower_operation_fact",
                "authorship": "independent_of_accepted_public_clauses",
                "source_operation": dependency_operation,
            }
            for index, lower in enumerate(
                expected_lower_clauses,
                start=1,
            )
        ]:
            errors.append(f"{target_id}: narrow dependency clause lowering is stale")
        dropped = transformation.get("dropped_constructs") or []
        if not dropped or any(
            not item.get("boundary") or not item.get("justification")
            for item in dropped
        ):
            errors.append(f"{target_id}: source lowering omissions are not explicit")
        if transformation.get("reordered_constructs"):
            errors.append(f"{target_id}: source constructs were reordered")
        manifest_root = ROOT / "proof_manifests" / target_id
        expected_manifest_files = {
            "source_body.json",
            "transformation_manifest.json",
            "dependency_assumption_manifest.json",
            "mutation_manifest.json",
        }
        actual_manifest_files = (
            {path.name for path in manifest_root.iterdir() if path.is_file()}
            if manifest_root.is_dir()
            else set()
        )
        if actual_manifest_files != expected_manifest_files:
            errors.append(
                f"{target_id}: proof manifest file set differs "
                f"missing={sorted(expected_manifest_files - actual_manifest_files)} "
                f"extra={sorted(actual_manifest_files - expected_manifest_files)}"
            )
        for name in expected_manifest_files:
            if not (manifest_root / name).is_file():
                errors.append(f"{target_id}: missing proof manifest {name}")
        mirrored_mutation = manifest_root / "mutation_manifest.json"
        if (
            mirrored_mutation.is_file()
            and load_json(mirrored_mutation) != expected_mutation_manifest
        ):
            errors.append(
                f"{target_id}: mirrored mutation manifest is stale"
            )
    expected_literal_external_body = sum(
        proof_model.literal_external_body_count(row) for row in live_rows
    )
    if literal_external_body != expected_literal_external_body:
        errors.append(
            "narrow implementation dependency external_body "
            f"count={literal_external_body} != planned={expected_literal_external_body}"
        )
    expected_literal_counts = (
        proof_model.aggregate_literal_external_body_counts(live_rows)
    )
    aggregate = load_json(AGGREGATE)
    aggregate_count_fields = {
        "target_external_body_occurrences": "target",
        "completeness_external_body_occurrences": "completeness",
        "dependency_external_body_occurrences": "dependency",
        "helper_external_body_occurrences": "helper",
        "harness_literal_external_body_occurrences": "harness",
    }
    if (
        aggregate.get("literal_external_body_occurrences_by_category")
        != expected_literal_counts
        or any(
            aggregate.get(field) != expected_literal_counts[category]
            for field, category in aggregate_count_fields.items()
        )
    ):
        errors.append(
            "aggregate category-specific external_body accounting is stale"
        )
    expected_standard_library_assumptions = sum(
        len(proof_model.standard_library_assumption_boundaries(row))
        for row in live_rows
    )
    if (
        aggregate.get(
            "standard_library_assume_specification_occurrences"
        )
        != expected_standard_library_assumptions
        or (
            aggregate.get("semantic_trust_categories") or {}
        ).get("core_option_combinator_semantics")
        != expected_standard_library_assumptions
    ):
        errors.append(
            "aggregate standard-library assumption accounting is stale"
        )

    frozen = ROOT / "frozen_inputs/file_manifest.json"
    if not frozen.is_file():
        errors.append("missing frozen proof-input manifest")
    else:
        frozen_payload = load_json(frozen)
        if len(frozen_payload.get("targets", [])) != len(rows):
            errors.append("frozen target binding count differs from inventory")
        if frozen_payload.get("source_manifest_sha256") != sha256_file(
            ROOT / "provenance/source_manifest.json"
        ):
            errors.append("frozen source manifest binding is stale")
        review_binding = frozen_payload.get("accepted_specification_review") or {}
        review_path = ROOT / str(review_binding.get("path", ""))
        if (
            not review_path.is_file()
            or review_binding.get("sha256") != sha256_file(review_path)
        ):
            errors.append("frozen proof inputs lack current specification review")
        if frozen_payload.get("generated_spec_sha256") != sha256_file(
            ROOT / "specs/generated_btree_set_specs.rs"
        ):
            errors.append("frozen generated-spec binding is stale")
        if frozen_payload.get("shared_vocabulary_sha256") != sha256_file(
            ROOT / "specs/btree_set_shared_vocabulary.rs"
        ):
            errors.append("frozen shared-vocabulary binding is stale")

    static_audits = (
        "source_binding_audit.json",
        "signature_generic_shape_audit.json",
        "source_fidelity_audit.json",
        "anti_vacuity_audit.json",
        "semantic_binding_mutation_audit.json",
        "shared_helper_usage_audit.json",
        "outcome_equivalence_audit.json",
        "inventory_exclusion_audit.json",
    )
    for name in static_audits:
        path = ROOT / "verification/audits" / name
        if not path.is_file() or not str(load_json(path).get("status", "")).startswith(
            "passed"
        ):
            errors.append(f"static audit is not passed: {name}")
    helper_audit_path = ROOT / "verification/audits/shared_helper_usage_audit.json"
    if helper_audit_path.is_file():
        helper_audit = load_json(helper_audit_path)
        helper_only = [
            row.target_id
            for row in live_rows
            if len(proof_model.contract_lines(row)) == 1
            and re.fullmatch(
                r"(?:[A-Za-z_][A-Za-z0-9_:<>]*\()?[^=]*\)?",
                proof_model.contract_lines(row)[0].strip(),
            )
            and any(
                helper in proof_model.contract_lines(row)[0]
                for helper in (
                    "ordered_debug",
                    "ordered_set_hash",
                    "ordered_set_comparison",
                    "source_contract",
                )
            )
        ]
        if helper_audit.get("whole_target_single_helper_target_ids") != helper_only:
            errors.append("shared-helper audit count is asserted rather than computed")
        if helper_audit.get("unused_uninterpreted_primitives") != []:
            errors.append("shared-helper audit reports unused primitives")
        if helper_audit.get("whole_behavior_uninterpreted_primitives") != []:
            errors.append("shared-helper audit permits uninterpreted whole behavior")
        expected_primitive_uses = {
            name: (
                len(
                    re.findall(
                        rf"\b{re.escape(name)}\b",
                        model.SHARED_VOCABULARY,
                    )
                )
                + sum(
                    len(
                        re.findall(
                            rf"\b{re.escape(name)}\b",
                            line,
                        )
                    )
                    for row in live_rows
                    for line in [
                        *proof_model.contract_requirements(row),
                        *proof_model.contract_lines(row),
                    ]
                )
                - 1
            )
            for name in re.findall(
                r"pub uninterp spec fn ([A-Za-z_][A-Za-z0-9_]*)",
                model.SHARED_VOCABULARY,
            )
        }
        if (
            helper_audit.get("uninterpreted_primitive_use_counts")
            != dict(sorted(expected_primitive_uses.items()))
        ):
            errors.append("shared-helper primitive-use accounting is stale")
    return errors


def verify_verus(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    latest_path = ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
    if not latest_path.is_file():
        return ["missing active Verus matrix manifest"]
    latest = load_json(latest_path)
    summary_path = ROOT / str(latest.get("summary", ""))
    if not summary_path.is_file():
        return ["active Verus matrix summary is missing"]
    if latest.get("summary_sha256") != sha256_file(summary_path):
        errors.append("active Verus matrix summary hash is stale")
    summary = load_json(summary_path)
    run_manifest_path = summary_path.parent / "manifest.json"
    if not run_manifest_path.is_file():
        errors.append("active Verus matrix run manifest is missing")
    else:
        run_manifest = load_json(run_manifest_path)
        snapshot = run_manifest.get("source_snapshot") or {}
        review_binding = snapshot.get("accepted_specification_review") or {}
        review_path = ROOT / str(review_binding.get("path", ""))
        if (
            not review_path.is_file()
            or review_binding.get("sha256") != sha256_file(review_path)
        ):
            errors.append("Verus matrix is not bound to accepted specification review")
        for key, relative in (
            ("generated_spec_sha256", "specs/generated_btree_set_specs.rs"),
            ("shared_vocabulary_sha256", "specs/btree_set_shared_vocabulary.rs"),
        ):
            if snapshot.get(key) != sha256_file(ROOT / relative):
                errors.append(f"Verus matrix has stale {key}")
    expected = len(rows)
    checker_adjudicated = len(
        proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
    )
    expected_fields = {
        "expected_targets": expected,
        "completed_targets": expected,
        "passed_targets": expected,
        "implementation_no_verify_passed": expected,
        "implementation_actual_verus_verified": expected,
        "implementation_actual_verus_native_verified": (
            expected - checker_adjudicated
        ),
        "implementation_actual_verus_checker_adjudicated": (
            checker_adjudicated
        ),
        "completeness_no_verify_passed": expected,
        "completeness_actual_verus_verified": expected,
        "mutations_rejected": expected,
        "mutations_native_rejected": expected - checker_adjudicated,
        "mutations_checker_adjudicated": checker_adjudicated,
        "failed_targets": 0,
        "trial_failures": 0,
    }
    for field, value in expected_fields.items():
        if summary.get(field) != value:
            errors.append(f"Verus matrix {field}={summary.get(field)} != {value}")
    if summary.get("status") != "passed" or not summary.get(
        "generated_spec_no_verify"
    ) or not summary.get("generated_spec_actual_verus"):
        errors.append("Verus matrix did not pass all required modes")
    evidence_names = (
        "implementation_no_verify",
        "implementation_actual_verus",
        "completeness_no_verify",
        "completeness_actual_verus",
        "mutation_actual_verus",
    )
    for row in rows:
        evidence = ROOT / "proof_harnesses" / row["target_id"] / "evidence"
        associated_item_adjudication = (
            row["target_id"]
            in proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
        )
        target_summary = evidence / "summary.json"
        if (
            not target_summary.is_file()
            or load_json(target_summary).get("contract_fingerprint")
            != row["contract_fingerprint"]
        ):
            errors.append(
                f"{row['target_id']}: evidence is not contract-fingerprint bound"
            )
        if not (evidence / "versions.json").is_file():
            errors.append(f"{row['target_id']}: missing tool version evidence")
        for name in evidence_names:
            record_path = evidence / f"{name}.json"
            if not record_path.is_file():
                errors.append(f"{row['target_id']}: missing evidence {name}")
                continue
            record = load_json(record_path)
            if record.get("passed") is not True:
                errors.append(f"{row['target_id']}: evidence failed {name}")
            source = ROOT / str(record.get("source", ""))
            if not source.is_file() or record.get("source_sha256") != sha256_file(
                source
            ):
                errors.append(f"{row['target_id']}: stale evidence source {name}")
            if name in {
                "implementation_actual_verus",
                "mutation_actual_verus",
            }:
                if associated_item_adjudication:
                    exact_output = ""
                    for suffix in ("stdout", "stderr"):
                        output_path = evidence / f"{name}.{suffix}"
                        if output_path.is_file():
                            exact_output += output_path.read_text(
                                encoding="utf-8"
                            )
                    fallback_record_path = ROOT / str(
                        record.get(
                            "checker_adjudication_evidence",
                            "",
                        )
                    )
                    expected_fallback_source = (
                        ROOT
                        / "proof_harnesses"
                        / row["target_id"]
                        / (
                            "checker_adjudication_mutation.rs"
                            if name == "mutation_actual_verus"
                            else "checker_adjudication_proof.rs"
                        )
                    )
                    fallback_record = (
                        load_json(fallback_record_path)
                        if fallback_record_path.is_file()
                        else {}
                    )
                    fallback_output = ""
                    fallback_name = (
                        f"{name}_checker_adjudication"
                    )
                    for suffix in ("stdout", "stderr"):
                        output_path = (
                            evidence / f"{fallback_name}.{suffix}"
                        )
                        if output_path.is_file():
                            fallback_output += output_path.read_text(
                                encoding="utf-8"
                            )
                    fallback_passed = (
                        fallback_record.get("passed") is True
                        and expected_fallback_source.is_file()
                        and fallback_record.get("source_sha256")
                        == sha256_file(expected_fallback_source)
                        and record.get(
                            "checker_adjudication_source_sha256"
                        )
                        == fallback_record.get("source_sha256")
                        and record.get(
                            "checker_adjudication_passed"
                        )
                        is True
                    )
                    if name == "mutation_actual_verus":
                        rejection_kind = (
                            verus_evidence.mutation_rejection_kind(
                                fallback_output
                            )
                        )
                        fallback_passed = (
                            fallback_passed
                            and fallback_record.get("returncode") != 0
                            and rejection_kind is not None
                            and fallback_record.get(
                                "mutation_rejection_kind"
                            )
                            == rejection_kind
                            and record.get(
                                "checker_adjudication_rejection_kind"
                            )
                            == rejection_kind
                        )
                    else:
                        fallback_passed = (
                            fallback_passed
                            and fallback_record.get("returncode") == 0
                            and re.search(
                                r"verification results::\s+\d+ "
                                r"verified, 0 errors",
                                fallback_output,
                            )
                            is not None
                        )
                    if (
                        record.get("result_kind")
                        != "checker_adjudicated"
                        or record.get("checker_limitation")
                        != "verus-intoiterator-associated-item-air"
                        or record.get(
                            "exact_checker_failure_matched"
                        )
                        is not True
                        or not (
                            verus_evidence
                            .associated_item_air_limitation_matches(
                                record.get("returncode"),
                                exact_output,
                            )
                        )
                        or not fallback_passed
                    ):
                        errors.append(
                            f"{row['target_id']}: {name} checker "
                            "adjudication is not narrowly evidenced"
                        )
                elif (
                    record.get("result_kind", "native_verus")
                    != "native_verus"
                    or record.get("checker_limitation") is not None
                ):
                    errors.append(
                        f"{row['target_id']}: unexpected checker "
                        f"adjudication for {name}"
                    )
            if name == "mutation_actual_verus":
                if not associated_item_adjudication:
                    mutation_output = ""
                    for suffix in ("stdout", "stderr"):
                        output_path = evidence / f"{name}.{suffix}"
                        if output_path.is_file():
                            mutation_output += output_path.read_text(
                                encoding="utf-8"
                            )
                    rejection_kind = (
                        verus_evidence.mutation_rejection_kind(
                            mutation_output
                        )
                    )
                    if (
                        rejection_kind is None
                        or record.get("mutation_rejection_kind")
                        != rejection_kind
                    ):
                        errors.append(
                            f"{row['target_id']}: mutation evidence lacks "
                            "a semantic Verus rejection"
                        )
                    if (
                        row["target_id"]
                        == proof_model.UNION_LEFT_BIASED_NEXT_TARGET
                        and rejection_kind != "assertion"
                    ):
                        errors.append(
                            f"{row['target_id']}: live candidate-selection "
                            "mutation is not rejected at an assertion"
                        )
                mutation_manifest_path = (
                    ROOT
                    / "proof_harnesses"
                    / row["target_id"]
                    / "mutation_manifest.json"
                )
                if (
                    not mutation_manifest_path.is_file()
                    or load_json(mutation_manifest_path).get(
                        "mutation_source_sha256"
                    )
                    != record.get("source_sha256")
                    or record.get("expectation")
                    != (
                        "exact mutation signature reproduces the narrowly "
                        "matched Verus associated-item AIR failure and "
                        "actual Verus rejects the stronger-domain mutation "
                        "by a semantic proof obligation"
                        if associated_item_adjudication
                        else
                        "actual Verus rejects the type-correct "
                        "source-step mutation by a semantic proof "
                        "obligation"
                    )
                ):
                    errors.append(
                        f"{row['target_id']}: mutation evidence is not "
                        "source-step manifest bound"
                    )
    return errors


def verify_feedback(
    rows: list[dict[str, Any]], *, require_completeness: bool = True
) -> list[str]:
    errors: list[str] = []
    expected = sum(row["disposition"] == "generated" for row in rows)
    by_target = {row["canonical_target"]: row for row in rows}
    latest_path = (
        ROOT
        / "verification/evidence/btree_set_feedback_determinism/latest_manifest.json"
    )
    if not latest_path.is_file():
        return ["missing active feedback determinism manifest"]
    latest = load_json(latest_path)
    summary_path = ROOT / str(latest.get("summary", ""))
    if not summary_path.is_file():
        return ["active feedback summary is missing"]
    if latest.get("summary_sha256") != sha256_file(summary_path):
        errors.append("active feedback summary hash is stale")
    summary = load_json(summary_path)
    feedback_manifest_path = summary_path.parent / "manifest.json"
    if not feedback_manifest_path.is_file():
        errors.append("active feedback run manifest is missing")
    else:
        feedback_manifest = load_json(feedback_manifest_path)
        snapshot = feedback_manifest.get("source_snapshot") or {}
        for key, relative in (
            ("manifest", "specgen/btree_set_stable_manifest.json"),
            ("seeds", "specgen/btree_set_seed_candidates.json"),
            ("contracts", "specgen/existing_contract_context.json"),
            (
                "spec_determinism_manifest",
                "verification/spec_determinism_harnesses/manifest.json",
            ),
        ):
            path = ROOT / relative
            if (
                snapshot.get(key) != relative
                or snapshot.get(f"{key}_sha256") != sha256_file(path)
            ):
                errors.append(f"feedback run has stale {key} input")
    if not summary.get("generated_spec_no_verify") or not summary.get(
        "generated_spec_actual_verus"
    ):
        errors.append("feedback run lacks both current generated-spec Verus modes")
    module_evidence = summary_path.parent / str(
        summary.get("module_spec_evidence", "")
    )
    for name in ("generated_spec_no_verify", "generated_spec_actual_verus"):
        record_path = module_evidence / f"{name}.json"
        if not record_path.is_file():
            errors.append(f"feedback run lacks module evidence {name}")
            continue
        record = load_json(record_path)
        source = ROOT / str(record.get("source", ""))
        if (
            record.get("passed") is not True
            or not source.is_file()
            or record.get("source_sha256") != sha256_file(source)
        ):
            errors.append(f"feedback module evidence is stale or failed: {name}")
    for field in ("expected_targets", "completed_targets", "typecheck_passed"):
        if summary.get(field) != expected:
            errors.append(f"feedback {field}={summary.get(field)} != {expected}")
    if summary.get("status") != "passed":
        errors.append("feedback determinism gate did not pass")
    for field in (
        "missing_targets",
        "extra_targets",
        "typecheck_failures",
        "checker_errors",
        "sat_targets",
        "unresolved_targets",
        "missing_round_results",
    ):
        if summary.get(field):
            errors.append(f"feedback has nonempty {field}")
    if set(summary.get("spec_determinism_proved_targets") or []) != set(
        adjudicated := summary.get("checker_capability_adjudicated_targets") or []
    ):
        errors.append(
            "feedback adjudications lack current-stage determinism proofs"
        )
    if summary.get("spec_determinism_failures"):
        errors.append("feedback specification determinism proofs failed")
    adjudication_path = ROOT / str(
        summary.get("checker_capability_adjudication", "")
    )
    if adjudicated:
        if not adjudication_path.is_file():
            errors.append("feedback checker-capability adjudication is missing")
        else:
            adjudication = load_json(adjudication_path)
            adjudication_rows = adjudication.get("rows") or []
            if adjudication.get("adjudicated_count") != len(adjudicated):
                errors.append("feedback adjudication count is stale")
            if {row.get("target") for row in adjudication_rows} != set(adjudicated):
                errors.append("feedback adjudication target set differs")
            for row in adjudication_rows:
                source = row.get("source") or {}
                if (
                    not row.get("contract_fingerprint")
                    or not row.get("principal_behavior")
                    or not source.get("sha256")
                    or row.get("feedback_acceptance_evidence") is not True
                    or row.get("required_followup") is not None
                ):
                    errors.append(
                        f"feedback adjudication is not target-specific: {row.get('target')}"
                    )
                if row.get("feedback_status") == "unsupported":
                    raw_error = ROOT / str(row.get("raw_error_evidence", ""))
                    if (
                        not raw_error.is_file()
                        or not narrowly_evidenced_checker_limitation(
                            row,
                            raw_error.read_text(encoding="utf-8"),
                        )
                    ):
                        errors.append(
                            "feedback unsupported adjudication is not narrowly "
                            f"evidenced: {row.get('target')}"
                        )
                proof = ROOT / str(row.get("spec_determinism_evidence", ""))
                target_row = by_target.get(str(row.get("target")))
                if not proof.is_file() or target_row is None:
                    errors.append(
                        "feedback adjudication lacks current determinism evidence: "
                        f"{row.get('target')}"
                    )
                    continue
                proof_record = load_json(proof)
                proof_source = ROOT / str(proof_record.get("source", ""))
                if (
                    proof_record.get("passed") is not True
                    or proof_record.get("contract_fingerprint")
                    != target_row["contract_fingerprint"]
                    or proof_record.get("accepted_requires_sha256")
                    != target_row["accepted_requires_sha256"]
                    or proof_record.get("accepted_clause_sha256")
                    != target_row["accepted_clause_sha256"]
                    or not proof_source.is_file()
                    or proof_record.get("source_sha256")
                    != sha256_file(proof_source)
                    or row.get("spec_determinism_source_sha256")
                    != proof_record.get("source_sha256")
                ):
                    errors.append(
                        "feedback adjudication determinism evidence is stale: "
                        f"{row.get('target')}"
                    )
    return errors


def verify_reviews(required_gates: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for gate in required_gates:
        path = ROOT / "reviews" / f"{gate}.json"
        if not path.is_file():
            errors.append(f"missing independent reviewer gate: {gate}")
            continue
        record = load_json(path)
        review = record.get("review") or {}
        if (
            record.get("producer_role") != "reviewer"
            or review.get("status") != "done"
            or record.get("independent") is not True
            or record.get("acceptance_eligible") is not True
        ):
            errors.append(f"reviewer gate is not accepted: {gate}")
        request = record.get("request") or {}
        request_path = ROOT / str(request.get("path", ""))
        if not request_path.is_file() or request.get("sha256") != sha256_file(
            request_path
        ):
            errors.append(f"reviewer gate request binding is stale: {gate}")
        handoff = record.get("canonical_handoff") or {}
        handoff_path = Path(str(handoff.get("path", "")))
        if not handoff_path.is_file() or handoff.get("sha256") != sha256_file(
            handoff_path
        ):
            errors.append(f"canonical reviewer handoff binding is stale: {gate}")
            continue
        handoff_payload = load_json(handoff_path)
        handoff_review = handoff_payload.get("review") or {}
        if (
            handoff_payload.get("producer_role") != "reviewer"
            or handoff_review.get("status") != "done"
        ):
            errors.append(f"canonical handoff is not a done Reviewer decision: {gate}")
    return errors


def verify_dynamic(required_gates: tuple[str, ...]) -> list[str]:
    if not INVENTORY.is_file():
        return ["missing inventory for dynamic verification"]
    rows = load_json(INVENTORY)["rows"]
    errors = verify_verus(rows)
    errors.extend(verify_feedback(rows, require_completeness=True))
    errors.extend(verify_reviews(required_gates))
    for name in (
        "proof_evidence_audit.json",
        "feedback_determinism_audit.json",
        "mutation_audit.json",
    ):
        path = ROOT / "verification/audits" / name
        if not path.is_file() or load_json(path).get("status") != "passed":
            errors.append(f"dynamic audit is not passed: {name}")
    aggregate = load_json(AGGREGATE)
    expected = len(rows)
    for field in (
        "stable_inventory_total",
        "selected_targets",
        "actual_verus_verified",
        "completeness_verified",
        "mutation_rejected",
    ):
        if aggregate.get(field) != expected:
            errors.append(f"aggregate {field}={aggregate.get(field)} != {expected}")
    checker_adjudicated = len(
        proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
    )
    for field, value in {
        "actual_verus_native_verified": expected - checker_adjudicated,
        "actual_verus_checker_adjudicated": checker_adjudicated,
        "mutation_native_rejected": expected - checker_adjudicated,
        "mutation_checker_adjudicated": checker_adjudicated,
    }.items():
        if aggregate.get(field) != value:
            errors.append(
                f"aggregate {field}={aggregate.get(field)} != {value}"
            )
    if aggregate.get("failed") != 0 or aggregate.get("pending") != 0:
        errors.append("aggregate has failed or pending proof targets")
    if aggregate.get("target_external_body") != 0:
        errors.append("aggregate reports target-level external bodies")
    live_rows = model.derive_inventory(model.load_rustdoc())[0]
    expected_literal_counts = (
        proof_model.aggregate_literal_external_body_counts(live_rows)
    )
    expected_external_bodies = expected_literal_counts["harness"]
    if (
        aggregate.get("harness_literal_external_body_occurrences")
        != expected_external_bodies
    ):
        errors.append("aggregate lower dependency external_body count is stale")
    aggregate_count_fields = {
        "target_external_body_occurrences": "target",
        "completeness_external_body_occurrences": "completeness",
        "dependency_external_body_occurrences": "dependency",
        "helper_external_body_occurrences": "helper",
        "harness_literal_external_body_occurrences": "harness",
    }
    if (
        aggregate.get("literal_external_body_occurrences_by_category")
        != expected_literal_counts
        or any(
            aggregate.get(field) != expected_literal_counts[category]
            for field, category in aggregate_count_fields.items()
        )
    ):
        errors.append(
            "aggregate category-specific external_body accounting is stale"
        )
    if aggregate.get("whole_contract_dependency") != 0:
        errors.append("aggregate reports whole-contract dependency proofs")
    shared_external_bodies = model.SHARED_VOCABULARY.count(
        "#[verifier::external_body]"
    )
    if (
        aggregate.get("shared_vocabulary_external_body_occurrences_per_harness")
        != shared_external_bodies
        or aggregate.get("compiled_harness_external_body_occurrences")
        != expected_external_bodies + len(rows) * shared_external_bodies
    ):
        errors.append("aggregate shared/compiled external_body accounting is stale")
    expected_adjudication_external_bodies = sum(
        proof_model.checker_adjudication_source(row).count(
            "#[verifier::external_body]"
        )
        + proof_model.checker_adjudication_source(
            row,
            mutation=True,
        ).count("#[verifier::external_body]")
        for row in model.derive_inventory(model.load_rustdoc())[0]
        if proof_model.requires_associated_item_air_adjudication(row)
    )
    if (
        aggregate.get(
            "checker_adjudication_literal_external_body_occurrences"
        )
        != expected_adjudication_external_bodies
    ):
        errors.append(
            "aggregate checker adjudication external_body count is stale"
        )
    return errors


def artifact_manifest(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(paths)
    ]


def seal() -> dict[str, Any]:
    inventory = load_json(INVENTORY)
    rows = inventory["rows"]
    aggregate = load_json(AGGREGATE)
    aggregate["evidence_status"] = "campaign_complete"
    aggregate["pending"] = 0
    aggregate["failed"] = 0
    atomic_json(AGGREGATE, aggregate)
    atomic_json(
        ROOT / "verification/audits/artifact_integrity_audit.json",
        {
            "schema_version": 1,
            "module": model.MODULE,
            "status": "passed",
            "checked_targets": len(rows),
            "mandatory_specs_interface": True,
            "one_harness_child_per_selected_target": True,
            "source_contract_evidence_hashes_current": True,
        },
    )
    pipeline_path = ROOT / "research/PIPELINE_STATE.json"
    pipeline = load_json(pipeline_path)
    pipeline["current_stage"] = "delivery"
    pipeline["stages"]["review"]["status"] = "done"
    pipeline["stages"]["delivery"] = {
        "status": "done",
        "pending": 0,
    }
    for stage_name, stage in pipeline["stages"].items():
        if stage.get("status") not in {"done", "accepted", "passed"}:
            raise CampaignError(
                f"hidden pending pipeline stage: {stage_name}={stage.get('status')}"
            )
        if stage.get("pending", 0) != 0:
            raise CampaignError(
                f"hidden pending pipeline rows: {stage_name}={stage.get('pending')}"
            )
    atomic_json(pipeline_path, pipeline)
    evidence_manifests = [
        ROOT / "verification/evidence/verus_matrix/latest_manifest.json",
        ROOT
        / "verification/evidence/btree_set_feedback_determinism/latest_manifest.json",
    ]
    review_paths = [
        ROOT / "reviews/inventory_specification.json",
        ROOT / "reviews/proof_completeness.json",
        ROOT / "reviews/final_aggregate.json",
    ]
    bound_paths = [
        SCHEMA,
        ROOT / "provenance/source_manifest.json",
        ROOT / "provenance/freeze_context.json",
        INVENTORY,
        EXACT_AUDIT,
        CATALOG,
        ROOT / "specs/generated_btree_set_specs.rs",
        ROOT / "specs/btree_set_shared_vocabulary.rs",
        AGGREGATE,
        pipeline_path,
        ROOT / "verification/audits/artifact_integrity_audit.json",
        ROOT / "aggregate/inventory_specification_artifact_index.json",
        ROOT / "aggregate/proof_completeness_artifact_index.json",
        ROOT / "aggregate/final_aggregate_artifact_index.json",
        *evidence_manifests,
        *review_paths,
    ]
    manifest = artifact_manifest(bound_paths)
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode()
    ).hexdigest()
    literal_external_body_counts = (
        proof_model.aggregate_literal_external_body_counts(
            model.derive_inventory(model.load_rustdoc())[0]
        )
    )
    certification = {
        "schema_version": 1,
        "module": model.MODULE,
        "certification_id": digest[:20],
        "status": "campaign_complete",
        "counts_source": "inventory/btree_set_exec_fn_inventory.json#rows",
        "counts": {
            **inventory["counts"],
            "selected_targets": len(rows),
            "actual_verus_verified": len(rows),
            "completeness_verified": len(rows),
            "mutation_rejected": len(rows),
            "failed": 0,
            "pending": 0,
        },
        "trust": {
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
            "harness_literal_external_body_occurrences": (
                literal_external_body_counts["harness"]
            ),
            "whole_contract_dependency": 0,
            "shared_vocabulary_external_body_occurrences_per_harness": (
                model.SHARED_VOCABULARY.count("#[verifier::external_body]")
            ),
            "compiled_harness_external_body_occurrences": (
                literal_external_body_counts["harness"]
                + len(rows)
                * model.SHARED_VOCABULARY.count("#[verifier::external_body]")
            ),
            "no_additional_boundary_targets": 0,
            "foundational_end_to_end_trust_free_targets": 0,
        },
        "review_gates": [
            "inventory_specification",
            "proof_completeness",
            "final_aggregate",
        ],
        "hidden_pending_rows": 0,
        "artifact_manifest": manifest,
        "artifact_manifest_sha256": digest,
    }
    final_path = (
        ROOT
        / "proof_inventory"
        / f"final_aggregate_certification_{certification['certification_id']}.json"
    )
    if final_path.exists() and load_json(final_path) != certification:
        raise CampaignError(f"immutable certification collision: {final_path}")
    atomic_json(final_path, certification)
    atomic_json(
        ROOT / "proof_inventory/active_aggregate_certification.json",
        {
            "schema_version": 1,
            "status": "campaign_complete",
            "active_certification_id": certification["certification_id"],
            "active_certification_relpath": str(final_path.relative_to(ROOT)),
            "active_certification_sha256": sha256_file(final_path),
        },
    )
    atomic_json(ROOT / "aggregate/final_report.json", certification)
    return certification


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--static-only", action="store_true")
    group.add_argument("--spec-review", action="store_true")
    group.add_argument("--proof-review", action="store_true")
    group.add_argument("--pre-final-review", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = verify_static(include_proofs=not args.spec_review)
    mode = "static"
    if args.spec_review:
        if INVENTORY.is_file():
            errors.extend(
                verify_feedback(
                    load_json(INVENTORY)["rows"],
                    require_completeness=False,
                )
            )
        else:
            errors.append("missing inventory for specification review")
        mode = "spec_review"
    elif not args.static_only:
        if args.proof_review:
            required = ("inventory_specification",)
            mode = "proof_review"
        elif args.pre_final_review:
            required = ("inventory_specification", "proof_completeness")
            mode = "pre_final_review"
        else:
            required = (
                "inventory_specification",
                "proof_completeness",
                "final_aggregate",
            )
            mode = "final"
        errors.extend(verify_dynamic(required))
    errors = sorted(set(errors))
    result: dict[str, Any] = {
        "schema_version": 1,
        "module": model.MODULE,
        "mode": mode,
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }
    if not errors and mode == "final":
        result["certification"] = seal()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
