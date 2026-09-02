#!/usr/bin/env python3
"""Generate the source-backed Rust 1.96 core::cmp specification package."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
RECONCILIATION = ROOT / "inventory" / "inventory_reconciliation.json"
EXACT_AUDIT = ROOT / "inventory" / "exact_vstd_audit.json"
VOCABULARY = ROOT / "specs" / "cmp_shared_vocabulary.rs"
GENERATED = ROOT / "specs" / "generated_cmp_specs.rs"
CATALOG = ROOT / "specs" / "all_cmp_specs.json"
EXISTING = ROOT / "specs" / "existing_vstd"
EXISTING_BINDINGS = EXISTING / "bindings.json"
EXISTING_README = EXISTING / "README.md"
README = ROOT / "specs" / "README.md"
SPECIFICATION = ROOT / "specification"
EQUIVALENCE = SPECIFICATION / "cmp_outcome_equivalence.json"
MANIFEST = SPECIFICATION / "cmp_specification_manifest.json"
REVIEW_REQUEST = ROOT / "reviews" / "specification_review_request.json"
HELPER_AUDIT = ROOT / "audits" / "specification_helper_boundary_audit.json"
FLOAT_MODEL_BOUNDARY = (
    SPECIFICATION / "float_model_boundary_audit.json"
)
FLOAT_MODEL_EVIDENCE_LATEST = (
    ROOT
    / "verification"
    / "evidence"
    / "float-model-boundary"
    / "latest.json"
)

FLOAT_TYPES = ("f32", "f64")
FLOAT_METHODS = ("eq", "ne", "partial_cmp", "lt", "le", "gt", "ge")

UNINTERPRETED_HELPERS = {
    "cmp_tuple_observation_count": (
        "call_count_observation",
        "Counts source-ordered tuple component observations; return branches are direct.",
    ),
    "cmp_shared_reborrow": (
        "verifier_representation_boundary",
        "Models the shared reborrow of an unsized PointeeSized referent that Verus cannot snapshot with old.",
    ),
    "cmp_sequence_observation_count": (
        "call_count_observation",
        "Counts source-ordered sequence element observations; return branches are direct.",
    ),
    "cmp_array_eq_dispatch": (
        "specialization_dispatch_observation",
        "Selects the source generic or bytewise equality path.",
    ),
    "cmp_slice_eq_dispatch": (
        "specialization_dispatch_observation",
        "Selects the source generic or bytewise slice equality path.",
    ),
    "cmp_array_order_dispatch": (
        "specialization_dispatch_observation",
        "Selects the source array ordering path.",
    ),
    "cmp_slice_order_dispatch": (
        "specialization_dispatch_observation",
        "Selects the source slice ordering path.",
    ),
    "cmp_always_applicable_ord_dispatch": (
        "specialization_dispatch_observation",
        "Records the hidden AlwaysApplicable Ord specialization selected by source.",
    ),
    "cmp_bytewise_equal": (
        "private_representation_dependency",
        "Models the lower bytewise equality dependency only inside an explicit dispatch branch.",
    ),
    "cmp_unsigned_bytewise_order": (
        "private_representation_dependency",
        "Models compare_bytes ordering only inside an explicit unsigned-byte dispatch branch.",
    ),
    "cmp_array_slice_forwarding": (
        "forwarding_path_observation",
        "Witnesses array-to-slice forwarding while direct element, length, and dispatch clauses determine the result.",
    ),
    "cmp_then_with_observation_count": (
        "callback_count_observation",
        "Counts then_with callback calls; the branch and callback result are direct.",
    ),
    "cmp_comparator_observation_count": (
        "callback_count_observation",
        "Counts comparator calls; arguments, result, and tie selection are direct.",
    ),
    "cmp_fn_mut_state_transition": (
        "callback_state_boundary",
        "Threads one FnMut call's initial and final closure states around a direct callback ensures relation.",
    ),
    "cmp_key_callback_observation_count": (
        "callback_count_observation",
        "Counts the explicit v2-then-v1 key-callback trace.",
    ),
    "cmp_clone_from_effect": (
        "dependency_post_state",
        "Models the wrapped T::clone_from state transition without selecting a public return value.",
    ),
    "cmp_ordering_debug_effect": (
        "formatter_dependency_effect",
        "Models the Debug formatter transition while the target and returned fmt::Result remain explicit.",
    ),
    "cmp_reverse_debug_effect": (
        "formatter_dependency_effect",
        "Models delegated wrapped-value Debug effects only.",
    ),
    "cmp_ordering_hash_effect": (
        "hasher_dependency_effect",
        "Models the derived discriminant hash state transition only.",
    ),
    "cmp_reverse_hash_effect": (
        "hasher_dependency_effect",
        "Models delegated wrapped-value Hash effects only.",
    ),
    "cmp_hidden_ord_element_result": (
        "private_specialization_dependency",
        "Models one hidden Ord element comparison inside the explicit lexicographic path.",
    ),
}


class SpecificationBuildError(RuntimeError):
    """The inventory cannot be converted into a complete specification package."""


@dataclass(frozen=True)
class Contract:
    row_id: str
    target: str
    family: str
    declaration: str
    semantic_summary: str
    dependencies: tuple[str, ...]
    observable_components: tuple[str, ...]
    panic_domain: str


def is_float_model_boundary(row: dict[str, Any]) -> bool:
    blocker = row.get("specification_blocker", {})
    return (
        row.get("owner_type") in FLOAT_TYPES
        and row.get("method_name") in FLOAT_METHODS
        and blocker.get("kind") == "loaded_vstd_float_model_boundary"
    )


def model_boundary_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [row for row in rows if is_float_model_boundary(row)]


def generated_candidate_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row["disposition"] == "pending"
        and not is_float_model_boundary(row)
    ]


def selected_specification_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row["disposition"] == "exact_vstd"
        or (
            row["disposition"] == "pending"
            and not is_float_model_boundary(row)
        )
    ]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_file() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def marker(row: dict[str, Any], family: str) -> str:
    return f"// @spec-row {row['row_id']} family={family}"


def declaration(
    row: dict[str, Any],
    family: str,
    generics: str,
    target: str,
    parameters: str,
    output: str | None,
    *,
    requires: list[str] | None = None,
    ensures: list[str] | None = None,
    where: str | None = None,
    attributes: tuple[str, ...] = (),
) -> str:
    lines = [marker(row, family), *attributes]
    generic_text = f"<{generics}>" if generics else ""
    lines.append(f"pub assume_specification{generic_text}[")
    lines.append(f"    {target}")
    lines.append("](")
    if parameters:
        for line in parameters.splitlines():
            lines.append(f"    {line}")
    lines.append(")" + (f" -> (result: {output})" if output else ""))
    if where:
        lines.append(f"    where {where}")
    if requires:
        lines.append("    requires")
        lines.extend(f"        {clause}," for clause in requires)
    if ensures:
        lines.append("    ensures")
        lines.extend(f"        {clause}," for clause in ensures)
    lines.append(";")
    return "\n".join(lines)


def nested_if(conditions: list[str], values: list[str], fallback: str) -> str:
    expression = fallback
    for condition, value in reversed(list(zip(conditions, values))):
        expression = f"if {condition} {{ {value} }} else {{ {expression} }}"
    return expression


def tuple_types(row: dict[str, Any]) -> list[str]:
    owner = row["owner_type"]
    if not owner.startswith("("):
        raise SpecificationBuildError(f"not a tuple owner: {owner}")
    return list(row["signature"]["owner_generics"]["type_parameters"])


def tuple_type(types: list[str]) -> str:
    return "(" + ", ".join(types) + ("," if len(types) == 1 else "") + ")"


def tuple_contract(row: dict[str, Any]) -> Contract:
    types = tuple_types(row)
    owner = tuple_type(types)
    method = row["method_name"]
    relation = {
        "lt": "Lt",
        "le": "Le",
        "gt": "Gt",
        "ge": "Ge",
    }.get(method)
    trait = {
        "eq": "PartialEq",
        "ne": "PartialEq",
        "partial_cmp": "PartialOrd",
        "lt": "PartialOrd",
        "le": "PartialOrd",
        "gt": "PartialOrd",
        "ge": "PartialOrd",
        "cmp": "Ord",
    }[method]
    generics = ", ".join(f"{name}: {trait}" for name in types)
    target_trait = (
        f"PartialEq<{owner}>" if trait == "PartialEq"
        else f"PartialOrd<{owner}>" if trait == "PartialOrd"
        else "Ord"
    )
    target = f"<{owner} as {target_trait}>::{method}"
    params = f"left: &{owner},\nright: &{owner},"
    output = {
        "eq": "bool",
        "ne": "bool",
        "partial_cmp": "Option<core::cmp::Ordering>",
        "lt": "bool",
        "le": "bool",
        "gt": "bool",
        "ge": "bool",
        "cmp": "core::cmp::Ordering",
    }[method]
    outcomes = [f"o{i}" for i in range(len(types))]

    if method in {"eq", "ne", "partial_cmp", "cmp"}:
        outcome_type = {
            "eq": "bool",
            "ne": "bool",
            "partial_cmp": "Option<core::cmp::Ordering>",
            "cmp": "core::cmp::Ordering",
        }[method]
        existential = ", ".join(f"{name}: {outcome_type}" for name in outcomes)
        call_trait = "PartialEq" if method in {"eq", "ne"} else trait
        calls: list[str] = []
        previous: list[str] = []
        for index, (type_name, outcome) in enumerate(zip(types, outcomes)):
            call = (
                f"call_ensures(<{type_name} as {call_trait}>::{method}, "
                f"(&left.{index}, &right.{index}), {outcome})"
            )
            if previous:
                calls.append(f"({' && '.join(previous)} ==> {call})")
            else:
                calls.append(call)
            if method == "eq":
                previous.append(outcome)
            elif method == "ne":
                previous.append(f"!{outcome}")
            else:
                previous.append(
                    f"{outcome} == "
                    + (
                        "Some(core::cmp::Ordering::Equal)"
                        if method == "partial_cmp"
                        else "core::cmp::Ordering::Equal"
                    )
                )
        if method == "eq":
            result_expression = " && ".join(outcomes)
            stop_conditions = [f"!{name}" for name in outcomes[:-1]]
        elif method == "ne":
            result_expression = " || ".join(outcomes)
            stop_conditions = outcomes[:-1]
        else:
            equal = (
                "Some(core::cmp::Ordering::Equal)"
                if method == "partial_cmp"
                else "core::cmp::Ordering::Equal"
            )
            result_expression = outcomes[-1]
            for outcome in reversed(outcomes[:-1]):
                result_expression = (
                    f"if {outcome} == {equal} "
                    f"{{ {result_expression} }} else {{ {outcome} }}"
                )
            stop_conditions = [
                f"{name} != {equal}" for name in outcomes[:-1]
            ]
        count_values = [
            f"{index + 1}nat" for index in range(len(stop_conditions))
        ]
        count_expression = nested_if(
            stop_conditions,
            count_values,
            f"{len(types)}nat",
        )
        body = " &&\n            ".join(
            [
                *calls,
                (
                    f"(result {'<==>' if method in {'eq', 'ne'} else '=='} "
                    f"({result_expression}))"
                ),
                (
                    "cmp_tuple_observation_count("
                    f"CmpOperation::{method_to_operation(method)}, left, right"
                    f") == {count_expression}"
                ),
            ]
        )
        ensures = [f"exists|{existential}|\n            {body}"]
        dependencies = (
            f"{trait}::{method} component calls in source order",
        )
    else:
        assert relation is not None
        if len(types) == 1:
            ensures = [
                (
                    f"call_ensures(<{types[0]} as PartialOrd>::{method}, "
                    "(&left.0, &right.0), result)"
                ),
                (
                    "cmp_tuple_observation_count("
                    f"CmpOperation::{method_to_operation(method)}, left, right"
                    ") == 1"
                ),
            ]
        else:
            outcome_names = [f"outcome{i}" for i in range(len(types) - 1)]
            conditions = [
                (
                    f"{name} != "
                    "Some(core::cmp::Ordering::Equal)"
                )
                for name in outcome_names
            ]
            values = [
                (
                    f"{name} is Some && "
                    f"cmp_relation_holds(CmpRelation::{relation}, {name}->0)"
                )
                for name in outcome_names
            ]
            final = "last"
            result_expression = nested_if(conditions, values, final)
            continue_prefix: list[str] = []
            trigger_values = ", ".join([*outcome_names, "last"])
            clauses: list[str] = [
                "#[trigger] cmp_tuple_chaining_trigger("
                f"({trigger_values}))"
            ]
            for index, (type_name, outcome) in enumerate(
                zip(types[:-1], outcome_names)
            ):
                observation = (
                    f"call_ensures(<{type_name} as PartialOrd>::partial_cmp, "
                    f"(&left.{index}, &right.{index}), {outcome})"
                )
                if continue_prefix:
                    clauses.append(
                        f"({' && '.join(continue_prefix)} ==> {observation})"
                    )
                else:
                    clauses.append(observation)
                continue_prefix.append(
                    f"{outcome} == Some(core::cmp::Ordering::Equal)"
                )
            last_index = len(types) - 1
            clauses.append(
                f"({' && '.join(continue_prefix)} ==> "
                f"call_ensures(<{types[-1]} as PartialOrd>::{method}, "
                f"(&left.{last_index}, &right.{last_index}), last))"
            )
            clauses.append(f"result == {result_expression}")
            count_expression = nested_if(
                conditions,
                [
                    f"{index + 1}nat"
                    for index in range(len(conditions))
                ],
                f"{len(types)}nat",
            )
            clauses.append(
                "cmp_tuple_observation_count("
                f"CmpOperation::{method_to_operation(method)}, left, right"
                f") == {count_expression}"
            )
            existential = ", ".join(
                [
                    *(
                        f"{name}: Option<core::cmp::Ordering>"
                        for name in outcome_names
                    ),
                    "last: bool",
                ]
            )
            ensures = [
                f"exists|{existential}|\n            "
                + " &&\n            ".join(clauses)
            ]
        dependencies = (
            (
                "PartialOrd::partial_cmp observations mapped by the source "
                "private chaining semantics for all non-final fields"
            ),
            f"PartialOrd::{method} for the final field",
        )
    text = declaration(
        row,
        "tuple_short_circuit",
        generics,
        target,
        params,
        output,
        ensures=ensures,
    )
    return Contract(
        row["row_id"],
        row["target"],
        "tuple_short_circuit",
        text,
        (
            f"Tuple {method} observes fields from index zero, stops at the "
            "first decisive outcome, and uses the public relation only for "
            "the final field."
        ),
        dependencies,
        ("return_value", "component_call_order", "component_call_count"),
        "inherits_component_unwind",
    )


def method_to_operation(method: str) -> str:
    return {
        "eq": "Eq",
        "ne": "Ne",
        "partial_cmp": "PartialCmp",
        "cmp": "Cmp",
        "lt": "Lt",
        "le": "Le",
        "gt": "Gt",
        "ge": "Ge",
    }[method]


ARRAY_EQ_SHAPES: dict[str, tuple[str, str, str, str, str]] = {
    "<[T; N] as PartialEq<[U; N]>>::": (
        "T: PartialEq<U>, U, const N: usize",
        "left: &[T; N],\nright: &[U; N],",
        "left@",
        "right@",
        "true",
    ),
    "<[T; N] as PartialEq<[U]>>::": (
        "T: PartialEq<U>, U, const N: usize",
        "left: &[T; N],\nright: &[U],",
        "left@",
        "right@",
        "right@.len() == N",
    ),
    "<[T] as PartialEq<[U; N]>>::": (
        "T: PartialEq<U>, U, const N: usize",
        "left: &[T],\nright: &[U; N],",
        "left@",
        "right@",
        "left@.len() == N",
    ),
    "<[T; N] as PartialEq<&[U]>>::": (
        "'a, T: PartialEq<U>, U, const N: usize",
        "left: &[T; N],\nright: &&[U],",
        "left@",
        "(*right)@",
        "(*right)@.len() == N",
    ),
    "<&[T] as PartialEq<[U; N]>>::": (
        "'a, T: PartialEq<U>, U, const N: usize",
        "left: &&'a [T],\nright: &[U; N],",
        "(*left)@",
        "right@",
        "(*left)@.len() == N",
    ),
    "<[T; N] as PartialEq<&mut [U]>>::": (
        "'a, T: PartialEq<U>, U, const N: usize",
        "left: &[T; N],\nright: &&mut [U],",
        "left@",
        "old(*right)@",
        "old(*right)@.len() == N",
    ),
    "<&mut [T] as PartialEq<[U; N]>>::": (
        "'a, T: PartialEq<U>, U, const N: usize",
        "left: &&'a mut [T],\nright: &[U; N],",
        "old(*left)@",
        "right@",
        "old(*left)@.len() == N",
    ),
}


def array_equality_contract(row: dict[str, Any]) -> Contract:
    target = row["target"]
    prefix = next((item for item in ARRAY_EQ_SHAPES if target.startswith(item)), None)
    if prefix is None:
        raise SpecificationBuildError(f"unknown array equality target: {target}")
    generics, params, left, right, equal_length = ARRAY_EQ_SHAPES[prefix]
    method = row["method_name"]
    if method not in {"eq", "ne"}:
        raise SpecificationBuildError(f"unknown array equality method: {target}")
    mismatch = (
        f"!({equal_length}) ==> {'!result' if method == 'eq' else 'result'}"
        if equal_length != "true"
        else None
    )
    generic_result = (
        "(result <==> outcomes.len() == N "
        "&& forall|i: int| 0 <= i < N ==> !outcomes[i]) "
        "&& (!result <==> outcomes.len() > 0 && outcomes.last())"
        if method == "eq"
        else "(!result <==> outcomes.len() == N "
        "&& forall|i: int| 0 <= i < N ==> !outcomes[i]) "
        "&& (result <==> outcomes.len() > 0 && outcomes.last())"
    )
    active_prefix = "" if equal_length == "true" else f"{equal_length} ==> "
    clauses = []
    if mismatch:
        clauses.append(mismatch)
        clauses.append(
            f"!({equal_length}) ==> "
            f"cmp_sequence_observation_count(CmpOperation::{method_to_operation(method)}, "
            f"{left}, {right}) == 0"
        )
    clauses.extend(
        [
            (
                f"{active_prefix}cmp_array_eq_dispatch({left}, {right}) "
                "== CmpEqDispatch::GenericElementLoop ==> "
                "exists|outcomes: Seq<bool>| "
                f"cmp_lexicographic_ne_prefix({left}, {right}, outcomes) "
                f"&& {generic_result} "
                "&& cmp_sequence_observation_count("
                f"CmpOperation::{method_to_operation(method)}, {left}, {right}) "
                "== outcomes.len()"
            ),
            (
                f"{active_prefix}cmp_array_eq_dispatch({left}, {right}) "
                "== CmpEqDispatch::Bytewise ==> "
                f"(result {'<==>' if method == 'eq' else '<==> !'} "
                f"cmp_bytewise_equal({left}, {right})) "
                "&& cmp_sequence_observation_count("
                f"CmpOperation::{method_to_operation(method)}, {left}, {right}) == 1"
            ),
        ]
    )
    rendered_target = target
    if prefix == "<[T; N] as PartialEq<&[U]>>::":
        rendered_target = target.replace("&[U]", "&'a [U]")
    elif prefix == "<[T; N] as PartialEq<&mut [U]>>::":
        rendered_target = target.replace("&mut [U]", "&'a mut [U]")
    text = declaration(
        row,
        "array_equality_dispatch",
        generics,
        rendered_target,
        params,
        "bool",
        ensures=clauses,
    )
    return Contract(
        row["row_id"],
        target,
        "array_equality_dispatch",
        text,
        (
            f"Array {method} checks length before delegation and distinguishes "
            "the generic first-mismatch loop from raw bytewise equality."
        ),
        ("SpecArrayEq", "SlicePartialEq", "BytewiseEq/raw_eq"),
        ("return_value", "element_or_bytewise_dispatch", "comparison_count"),
        "inherits_element_comparison_unwind",
    )


def lexicographic_partial_clauses(
    left: str,
    right: str,
    result: str,
    method: str,
    bound: str,
) -> list[str]:
    equal = "Some(core::cmp::Ordering::Equal)"
    less = "Some(core::cmp::Ordering::Less)"
    greater = "Some(core::cmp::Ordering::Greater)"
    if method == "partial_cmp":
        result_clause = (
            f"{result} == if outcomes.len() > 0 && outcomes.last() != {equal} "
            f"{{ outcomes.last() }} else {{ Some(cmp_length_order({left}.len(), {right}.len())) }}"
        )
    else:
        relation = method.capitalize()
        result_clause = (
            f"({result} <==> if outcomes.len() > 0 "
            f"&& outcomes.last() != {equal} "
            "{ outcomes.last() is Some "
            f"&& cmp_relation_holds(CmpRelation::{relation}, outcomes.last()->0) "
            "} else { "
            f"cmp_relation_holds(CmpRelation::{relation}, "
            f"cmp_length_order({left}.len(), {right}.len())) "
            "})"
        )
    return [
        f"cmp_lexicographic_partial_cmp_prefix({left}, {right}, outcomes)",
        f"outcomes.len() <= {bound}",
        f"({bound} == 0 ==> outcomes.len() == 0)",
        f"({bound} > 0 ==> outcomes.len() > 0)",
        f"(outcomes.len() < {bound} ==> outcomes.last() != {equal})",
        result_clause,
    ]


def lexicographic_cmp_clauses(
    left: str,
    right: str,
    result: str,
    bound: str,
    *,
    prefix_function: str = "cmp_lexicographic_cmp_prefix",
) -> list[str]:
    return [
        f"{prefix_function}({left}, {right}, outcomes)",
        f"outcomes.len() <= {bound}",
        f"({bound} == 0 ==> outcomes.len() == 0)",
        f"({bound} > 0 ==> outcomes.len() > 0)",
        (
            f"(outcomes.len() < {bound} ==> "
            "outcomes.last() != core::cmp::Ordering::Equal)"
        ),
        (
            f"{result} == if outcomes.len() > 0 "
            "&& outcomes.last() != core::cmp::Ordering::Equal "
            f"{{ outcomes.last() }} else {{ cmp_length_order({left}.len(), {right}.len()) }}"
        ),
    ]


def array_order_contract(row: dict[str, Any]) -> Contract:
    target = row["target"]
    method = row["method_name"]
    trait = "Ord" if method == "cmp" else "PartialOrd"
    generics = f"T: {trait}, const N: usize"
    output = (
        "core::cmp::Ordering"
        if method == "cmp"
        else "Option<core::cmp::Ordering>"
        if method == "partial_cmp"
        else "bool"
    )
    left, right, bound = "left@", "right@", "N"
    clauses = [
        (
            f"cmp_array_slice_forwarding(CmpOperation::{method_to_operation(method)}, "
            f"{left}, {right})"
        )
    ]
    if method == "cmp":
        generic = lexicographic_cmp_clauses(left, right, "result", bound)
        clauses.extend(
            [
                (
                    "cmp_array_order_dispatch(left@, right@) "
                    "== CmpOrderDispatch::GenericOrdLoop "
                    "|| cmp_array_order_dispatch(left@, right@) "
                    "== CmpOrderDispatch::UnsignedBytewiseOrd"
                ),
                (
                    "cmp_array_order_dispatch(left@, right@) "
                    "== CmpOrderDispatch::GenericOrdLoop ==> "
                    "exists|outcomes: Seq<core::cmp::Ordering>| "
                    + " && ".join(generic)
                ),
                (
                    "cmp_array_order_dispatch(left@, right@) "
                    "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                    "result == cmp_unsigned_bytewise_order(left@, right@)"
                ),
            ]
        )
    else:
        generic = lexicographic_partial_clauses(
            left, right, "result", method, bound
        )
        allowed = (
            "cmp_array_order_dispatch(left@, right@) "
            "== CmpOrderDispatch::GenericPartialOrdLoop "
            "|| cmp_array_order_dispatch(left@, right@) "
            "== CmpOrderDispatch::AlwaysApplicableOrd"
            if method == "partial_cmp"
            else
            "cmp_array_order_dispatch(left@, right@) "
            "== CmpOrderDispatch::GenericPartialOrdLoop "
            "|| cmp_array_order_dispatch(left@, right@) "
            "== CmpOrderDispatch::UnsignedBytewiseOrd"
        )
        clauses.extend(
            [
                f"({allowed})",
                (
                    "cmp_array_order_dispatch(left@, right@) "
                    "== CmpOrderDispatch::GenericPartialOrdLoop ==> "
                    "exists|outcomes: Seq<Option<core::cmp::Ordering>>| "
                    + " && ".join(generic)
                ),
            ]
        )
        if method == "partial_cmp":
            clauses.append(
                "cmp_array_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::AlwaysApplicableOrd ==> "
                "(cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop "
                "|| cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd) "
                "&& (cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop ==> "
                "exists|outcomes: Seq<core::cmp::Ordering>, "
                "order: core::cmp::Ordering| "
                + " && ".join(
                    lexicographic_cmp_clauses(
                        left,
                        right,
                        "order",
                        bound,
                        prefix_function=(
                            "cmp_hidden_ord_lexicographic_prefix"
                        ),
                    )
                )
                + " && result == Some(order)) "
                "&& (cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                "result == Some(cmp_unsigned_bytewise_order(left@, right@)))"
            )
        else:
            clauses.append(
                "cmp_array_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                f"(result <==> cmp_relation_holds(CmpRelation::{method.capitalize()}, "
                "cmp_unsigned_bytewise_order(left@, right@)))"
            )
    text = declaration(
        row,
        "array_slice_order_forwarding",
        generics,
        target,
        "left: &[T; N],\nright: &[T; N],",
        output,
        ensures=clauses,
    )
    return Contract(
        row["row_id"],
        target,
        "array_slice_order_forwarding",
        text,
        (
            f"Array {method} forwards both operands as slices and preserves "
            "generic, always-applicable Ord, and unsigned-bytewise outcomes."
        ),
        ("array-to-slice forwarding", "SlicePartialOrd/SliceChain/SliceOrd"),
        ("return_value", "forwarding_path", "comparison_dispatch"),
        "inherits_element_comparison_unwind",
    )


def slice_equality_contract(row: dict[str, Any]) -> Contract:
    target = row["target"]
    clauses = [
        "left@.len() != right@.len() ==> !result",
        (
            "left@.len() != right@.len() ==> "
            "cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 0"
        ),
        (
            "left@.len() == right@.len() "
            "&& cmp_slice_eq_dispatch(left@, right@) "
            "== CmpEqDispatch::GenericElementLoop ==> "
            "exists|outcomes: Seq<bool>| "
            "cmp_lexicographic_ne_prefix(left@, right@, outcomes) "
            "&& (result <==> outcomes.len() == left@.len() "
            "&& forall|i: int| 0 <= i < left@.len() ==> !outcomes[i]) "
            "&& (!result <==> outcomes.len() > 0 && outcomes.last()) "
            "&& cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) "
            "== outcomes.len()"
        ),
        (
            "left@.len() == right@.len() "
            "&& cmp_slice_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> "
            "(result <==> cmp_bytewise_equal(left@, right@)) "
            "&& cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 1"
        ),
    ]
    text = declaration(
        row,
        "slice_equality_dispatch",
        "T: PartialEq<U>, U",
        target,
        "left: &[T],\nright: &[U],",
        "bool",
        ensures=clauses,
    )
    return Contract(
        row["row_id"],
        target,
        "slice_equality_dispatch",
        text,
        "Slice equality checks length, then selects the generic first-mismatch loop or compare_bytes.",
        ("SlicePartialEq::equal_same_length", "BytewiseEq/compare_bytes"),
        ("return_value", "length_branch", "element_or_bytewise_dispatch"),
        "inherits_element_comparison_unwind",
    )


def slice_order_contract(row: dict[str, Any]) -> Contract:
    method = row["method_name"]
    target = row["target"]
    trait = "Ord" if method == "cmp" else "PartialOrd"
    output = (
        "core::cmp::Ordering"
        if method == "cmp"
        else "Option<core::cmp::Ordering>"
        if method == "partial_cmp"
        else "bool"
    )
    bound = "cmp_min_len(left@.len(), right@.len())"
    clauses: list[str] = []
    if method == "cmp":
        clauses = [
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop "
                "|| cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd"
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop ==> "
                "exists|outcomes: Seq<core::cmp::Ordering>| "
                + " && ".join(
                    lexicographic_cmp_clauses(
                        "left@", "right@", "result", bound
                    )
                )
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                "result == cmp_unsigned_bytewise_order(left@, right@)"
            ),
        ]
    elif method == "partial_cmp":
        clauses = [
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericPartialOrdLoop "
                "|| cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::AlwaysApplicableOrd"
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericPartialOrdLoop ==> "
                "exists|outcomes: Seq<Option<core::cmp::Ordering>>| "
                + " && ".join(
                    lexicographic_partial_clauses(
                        "left@", "right@", "result", method, bound
                    )
                )
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::AlwaysApplicableOrd ==> "
                "(cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop "
                "|| cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd) "
                "&& (cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericOrdLoop ==> "
                "exists|outcomes: Seq<core::cmp::Ordering>, "
                "order: core::cmp::Ordering| "
                + " && ".join(
                    lexicographic_cmp_clauses(
                        "left@",
                        "right@",
                        "order",
                        bound,
                        prefix_function=(
                            "cmp_hidden_ord_lexicographic_prefix"
                        ),
                    )
                )
                + " && result == Some(order)) "
                "&& (cmp_always_applicable_ord_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                "result == Some(cmp_unsigned_bytewise_order(left@, right@)))"
            ),
        ]
    else:
        relation = method.capitalize()
        clauses = [
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericPartialOrdLoop "
                "|| cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd"
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::GenericPartialOrdLoop ==> "
                "exists|outcomes: Seq<Option<core::cmp::Ordering>>| "
                "cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) "
                f"&& outcomes.len() <= {bound} "
                f"&& ({bound} == 0 ==> outcomes.len() == 0) "
                f"&& ({bound} > 0 ==> outcomes.len() > 0) "
                f"&& (outcomes.len() < {bound} ==> outcomes.last() "
                "!= Some(core::cmp::Ordering::Equal)) "
                "&& (result <==> if outcomes.len() > 0 "
                "&& outcomes.last() != Some(core::cmp::Ordering::Equal) "
                "{ outcomes.last() is Some && "
                f"cmp_relation_holds(CmpRelation::{relation}, outcomes.last()->0) "
                "} else { "
                f"cmp_relation_holds(CmpRelation::{relation}, "
                "cmp_length_order(left@.len(), right@.len())) })"
            ),
            (
                "cmp_slice_order_dispatch(left@, right@) "
                "== CmpOrderDispatch::UnsignedBytewiseOrd ==> "
                f"(result <==> cmp_relation_holds(CmpRelation::{relation}, "
                "cmp_unsigned_bytewise_order(left@, right@)))"
            ),
        ]
    text = declaration(
        row,
        "slice_order_dispatch",
        f"T: {trait}",
        target,
        "left: &[T],\nright: &[T],",
        output,
        ensures=clauses,
    )
    return Contract(
        row["row_id"],
        target,
        "slice_order_dispatch",
        text,
        (
            f"Slice {method} preserves first-decisive lexicographic behavior, "
            "length tie-breaking, private chaining, and unsigned bytewise dispatch."
        ),
        ("SlicePartialOrd", "SliceChain", "SliceOrd", "compare_bytes"),
        ("return_value", "element_call_prefix", "length_branch", "dispatch_path"),
        "inherits_element_comparison_unwind",
    )


def simple_contract(
    row: dict[str, Any],
    family: str,
    generics: str,
    target: str,
    parameters: str,
    output: str | None,
    ensures: list[str],
    summary: str,
    dependencies: tuple[str, ...] = (),
    components: tuple[str, ...] = ("return_value",),
    panic: str = "no_source_panic",
    *,
    requires: list[str] | None = None,
    attributes: tuple[str, ...] = (),
) -> Contract:
    return Contract(
        row["row_id"],
        row["target"],
        family,
        declaration(
            row,
            family,
            generics,
            target,
            parameters,
            output,
            requires=requires,
            ensures=ensures,
            attributes=attributes,
        ),
        summary,
        dependencies,
        components,
        panic,
    )


def cmp_source_contract(row: dict[str, Any]) -> Contract:
    target = row["target"]
    method = row["method_name"]
    allow_trait = ("#[verifier::allow(undeclared_external_trait)]",)
    if target == "Ord::clamp":
        text = "\n".join(
            [
                marker(row, "trait_default_clamp"),
                "pub open spec fn cmp_ord_clamp_contract<",
                "    Self_: Ord + PartialOrdSpec + OrdSpec,",
                ">(",
                "    value: Self_,",
                "    min: Self_,",
                "    max: Self_,",
                "    result: CmpCallOutcome<Self_>,",
                ") -> bool {",
                "    Self_::obeys_partial_cmp_spec() ==> (",
                "        result == if min.partial_cmp_spec(&max) == Some(Ordering::Greater) {",
                "            CmpCallOutcome::Panicked",
                "        } else {",
                "            CmpCallOutcome::Returned(",
                "                if value.partial_cmp_spec(&min) == Some(Ordering::Less) {",
                "                    min",
                "                } else if value.partial_cmp_spec(&max) == Some(Ordering::Greater) {",
                "                    max",
                "                } else {",
                "                    value",
                "                },",
                "            )",
                "        }",
                "    )",
                "}",
            ]
        )
        return Contract(
            row["row_id"],
            target,
            "trait_default_clamp",
            text,
            (
                "The shared Ord::clamp body returns the lower bound, upper "
                "bound, or receiver when min <= max and has the unique "
                "panicked/no-normal-return outcome when min > max."
            ),
            ("PartialOrdSpec", "Ord::lt", "Ord::gt"),
            ("return_value", "panic_domain", "lower_then_upper_branch"),
            "panics_iff_min_greater_than_max",
        )
    if target == "Eq::assert_receiver_is_total_eq":
        text = "\n".join(
            [
                marker(row, "empty_eq_default"),
                "#[allow(deprecated)]",
                "pub open spec fn cmp_eq_assert_receiver_is_total_eq_contract<",
                "    T: Eq + ?Sized,",
                ">(",
                "    receiver: &T,",
                ") -> bool {",
                "    true",
                "}",
            ]
        )
        return Contract(
            row["row_id"],
            target,
            "empty_eq_default",
            text,
            (
                "The deprecated shared Eq default has an empty body, a unit "
                "return, and no mutable post-state; true is its complete "
                "observable outcome relation."
            ),
            (),
            ("unit_return", "shared_receiver_unchanged"),
            "no_source_panic",
        )
    if target == "<Ordering as PartialEq<Ordering>>::eq":
        return simple_contract(
            row, "ordering_value", "", target,
            "left: &Ordering,\nright: &Ordering,", "bool",
            ["result <==> cmp_ordering_rank(*left) == cmp_ordering_rank(*right)"],
            "Ordering equality compares the three discriminant values.",
        )
    if target == "<Ordering as PartialOrd<Ordering>>::partial_cmp":
        return simple_contract(
            row, "ordering_value", "", target,
            "left: &Ordering,\nright: &Ordering,",
            "Option<Ordering>",
            ["result == Some(cmp_ordering_compare(*left, *right))"],
            "Ordering partial_cmp is total and returns the discriminant ordering.",
        )
    if target == "<Ordering as Ord>::cmp":
        return simple_contract(
            row, "ordering_value", "", target,
            "left: &Ordering,\nright: &Ordering,", "Ordering",
            ["result == cmp_ordering_compare(*left, *right)"],
            "Ordering cmp returns the discriminant ordering.",
        )
    if target == "<Ordering as Clone>::clone":
        return simple_contract(
            row, "ordering_value", "", target, "source: &Ordering,", "Ordering",
            ["result == *source"],
            "Ordering clone copies the enum value.",
        )
    if target == "<Ordering as Debug>::fmt":
        return simple_contract(
            row, "ordering_debug", "", target,
            "value: &Ordering,\nformatter: &mut core::fmt::Formatter<'_>,",
            "core::fmt::Result",
            ["cmp_ordering_debug_effect(*value, formatter, result)"],
            "Derived Ordering Debug selects the exact variant name and one formatter dependency result.",
            ("Formatter variant-name write",),
            ("return_value", "formatter_post_state", "variant_name"),
            "formatter_dependency_may_unwind",
            attributes=allow_trait,
        )
    if target == "<Ordering as Hash>::hash":
        return simple_contract(
            row, "ordering_hash", "H: core::hash::Hasher", target,
            "value: &Ordering,\nstate: &mut H,", None,
            ["cmp_ordering_hash_effect(*value, state)"],
            "Derived Ordering Hash observes the discriminant and resulting hasher state.",
            ("Hasher::write",),
            ("hasher_post_state", "ordering_discriminant"),
            "hasher_dependency_may_unwind",
            attributes=allow_trait,
        )
    if target == "Ordering::then_with":
        return simple_contract(
            row, "ordering_then_with", "F: FnOnce() -> Ordering",
            "Ordering::then_with::<F>",
            "ordering: Ordering,\ncallback: F,", "Ordering",
            [
                "ordering != Ordering::Equal ==> result == ordering",
                (
                    "ordering != Ordering::Equal ==> "
                    "cmp_then_with_observation_count(ordering, callback) == 0"
                ),
                "ordering == Ordering::Equal ==> callback.ensures((), result)",
                (
                    "ordering == Ordering::Equal ==> "
                    "cmp_then_with_observation_count(ordering, callback) == 1"
                ),
            ],
            "then_with invokes its FnOnce exactly once only for Equal and otherwise returns self.",
            ("FnOnce callback",),
            ("return_value", "callback_count", "callback_output"),
            "callback_may_unwind",
            requires=["ordering == Ordering::Equal ==> callback.requires(())"],
        )
    if target == "<Reverse<T> as PartialEq<Reverse<T>>>::eq":
        return simple_contract(
            row, "reverse_forwarding", "T: PartialEq", target,
            "left: &Reverse<T>,\nright: &Reverse<T>,", "bool",
            ["call_ensures(<T as PartialEq>::eq, (&left.0, &right.0), result)"],
            "Reverse equality preserves operand order and delegates to the wrapped values.",
            ("T::eq",),
        )
    if target == "<Reverse<T> as Default>::default":
        return simple_contract(
            row, "reverse_default", "T: Default", target, "", "Reverse<T>",
            [
                "exists|value: T| call_ensures(T::default, (), value) && result == Reverse(value)"
            ],
            "Reverse default wraps exactly one T::default result.",
            ("T::default",),
        )
    if target == "<Reverse<T> as Debug>::fmt":
        return simple_contract(
            row, "reverse_debug", "T: core::fmt::Debug", target,
            "value: &Reverse<T>,\nformatter: &mut core::fmt::Formatter<'_>,",
            "core::fmt::Result",
            ["cmp_reverse_debug_effect(&value.0, formatter, result)"],
            "Derived Reverse Debug emits the Reverse tuple-struct name and wrapped field.",
            ("Formatter debug-tuple operations", "T::fmt"),
            ("return_value", "formatter_post_state", "wrapper_name", "field_call"),
            "formatter_or_field_may_unwind",
            attributes=allow_trait,
        )
    if target == "<Reverse<T> as Hash>::hash":
        return simple_contract(
            row, "reverse_hash",
            "T: core::hash::Hash, H: core::hash::Hasher", target,
            "value: &Reverse<T>,\nstate: &mut H,", None,
            ["cmp_reverse_hash_effect(&value.0, state)"],
            "Derived Reverse Hash delegates once to the wrapped field without reversing it.",
            ("T::hash",),
            ("hasher_post_state", "wrapped_field_call"),
            "hasher_or_field_may_unwind",
            attributes=allow_trait,
        )
    reverse_partial = re.fullmatch(
        r"<Reverse<T> as PartialOrd<Reverse<T>>>::(partial_cmp|lt|le|gt|ge)",
        target,
    )
    if reverse_partial:
        name = reverse_partial.group(1)
        output = "Option<Ordering>" if name == "partial_cmp" else "bool"
        return simple_contract(
            row, "reverse_operand_reversal", "T: PartialOrd", target,
            "left: &Reverse<T>,\nright: &Reverse<T>,", output,
            [
                f"call_ensures(<T as PartialOrd>::{name}, "
                f"(&right.0, &left.0), result)"
            ],
            f"Reverse {name} swaps wrapped operands before invoking T::{name}.",
            (f"T::{name} with (right, left)",),
            ("return_value", "reversed_operand_order"),
            "inherits_wrapped_comparison_unwind",
        )
    if target == "<Reverse<T> as Ord>::cmp":
        return simple_contract(
            row, "reverse_operand_reversal", "T: Ord", target,
            "left: &Reverse<T>,\nright: &Reverse<T>,", "Ordering",
            ["call_ensures(<T as Ord>::cmp, (&right.0, &left.0), result)"],
            "Reverse cmp swaps wrapped operands rather than merely post-reversing an Ordering.",
            ("T::cmp with (right, left)",),
            ("return_value", "reversed_operand_order"),
            "inherits_wrapped_comparison_unwind",
        )
    if target == "<Reverse<T> as Clone>::clone":
        return simple_contract(
            row, "reverse_clone", "T: Clone", target,
            "source: &Reverse<T>,", "Reverse<T>",
            ["cloned::<T>(source.0, result.0)"],
            "Reverse clone wraps the Clone outcome for the sole field.",
            ("T::clone",),
        )
    if target == "<Reverse<T> as Clone>::clone_from":
        return simple_contract(
            row, "reverse_clone", "T: Clone", target,
            "target: &mut Reverse<T>,\nsource: &Reverse<T>,", None,
            ["cmp_clone_from_effect(old(target).0, source.0, final(target).0)"],
            "Reverse clone_from delegates the old, source, and final wrapped values to T::clone_from.",
            ("T::clone_from",),
            ("wrapped_field_post_state",),
            "clone_dependency_may_unwind",
        )
    if target in {"core::cmp::min", "core::cmp::max"}:
        name = target.rsplit("::", 1)[1]
        return simple_contract(
            row, "free_ord_forwarding", "T: Ord", f"core::cmp::{name}::<T>",
            "v1: T,\nv2: T,", "T",
            [
                f"call_ensures(<T as Ord>::{name}, (v1, v2), result)"
            ],
            f"core::cmp::{name} is an exact forwarding call to Ord::{name}, retaining that contract's equal-value bias.",
            (f"Ord::{name}",),
            ("return_value", "delegate_identity", "equal_value_bias"),
            "inherits_ord_method_unwind",
        )
    if target in {"core::cmp::min_by", "core::cmp::max_by"}:
        name = target.rsplit("::", 1)[1]
        choose_first = (
            "order == Ordering::Less || order == Ordering::Equal"
            if name == "min_by"
            else "order == Ordering::Greater"
        )
        return simple_contract(
            row, "comparator_callback",
            "T, F: FnOnce(&T, &T) -> Ordering",
            f"core::cmp::{name}::<T, F>",
            "v1: T,\nv2: T,\ncompare: F,", "T",
            [
                "exists|order: Ordering| compare.ensures((&v1, &v2), order) "
                f"&& result == if {choose_first} {{ v1 }} else {{ v2 }} "
                "&& cmp_comparator_observation_count(compare, &v1, &v2) == 1"
            ],
            f"{name} calls compare exactly once as (v1, v2) and preserves its documented tie selection.",
            ("FnOnce comparator",),
            ("return_value", "callback_order", "callback_count", "equal_value_bias"),
            "callback_may_unwind",
            requires=["compare.requires((&v1, &v2))"],
        )
    if target in {"core::cmp::min_by_key", "core::cmp::max_by_key"}:
        name = target.rsplit("::", 1)[1]
        selected = (
            "if second_is_less { v2 } else { v1 }"
            if name == "min_by_key"
            else "if second_is_less { v1 } else { v2 }"
        )
        return simple_contract(
            row, "key_callback_order",
            "T, F: FnMut(&T) -> K, K: Ord",
            f"core::cmp::{name}::<T, F, K>",
            "v1: T,\nv2: T,\ncallback: F,", "T",
            [
                "exists|key2: K, key1: K, callback_after_v2: F, "
                "callback_after_v1: F, second_is_less: bool| "
                "callback.ensures((&v2,), key2) "
                "&& cmp_fn_mut_state_transition("
                "callback, &v2, key2, callback_after_v2) "
                "&& callback_after_v2.ensures((&v1,), key1) "
                "&& cmp_fn_mut_state_transition("
                "callback_after_v2, &v1, key1, callback_after_v1) "
                "&& call_ensures(<K as PartialOrd>::lt, (&key2, &key1), second_is_less) "
                f"&& result == {selected} "
                "&& cmp_key_callback_observation_count(callback, &v2, &v1) == 2"
            ],
            f"{name} calls the key callback in source order v2 then v1, threads its mutable state through both calls, and applies its distinct tie bias.",
            ("FnMut key callback", "K::lt"),
            (
                "return_value",
                "callback_order_v2_then_v1",
                "callback_state_transition",
                "callback_final_state",
                "callback_count",
                "equal_value_bias",
            ),
            "callback_or_key_comparison_may_unwind",
            requires=[
                "callback.requires((&v2,))",
                "forall|key2: K, callback_after_v2: F| "
                "cmp_fn_mut_state_transition("
                "callback, &v2, key2, callback_after_v2) "
                "==> callback_after_v2.requires((&v1,))",
            ],
        )
    if target in {
        "<() as PartialEq<()>>::eq",
        "<() as PartialEq<()>>::ne",
        "<() as PartialOrd<()>>::partial_cmp",
        "<() as Ord>::cmp",
    }:
        output = (
            "bool"
            if method in {"eq", "ne"}
            else "Option<Ordering>"
            if method == "partial_cmp"
            else "Ordering"
        )
        value = {
            "eq": "result",
            "ne": "!result",
            "partial_cmp": "result == Some(Ordering::Equal)",
            "cmp": "result == Ordering::Equal",
        }[method]
        return simple_contract(
            row, "unit_value", "", target,
            "left: &(),\nright: &(),", output, [value],
            f"Unit {method} has the sole total equality/ordering outcome.",
        )
    if target in {
        "<char as PartialEq<char>>::eq",
        "<char as PartialEq<char>>::ne",
    }:
        relation_text = "==" if method == "eq" else "!="
        return simple_contract(
            row, "char_value", "", target,
            "left: &char,\nright: &char,", "bool",
            [f"result <==> cmp_char_rank(*left) {relation_text} cmp_char_rank(*right)"],
            f"char {method} compares Unicode scalar-value ranks.",
            ("char scalar-value representation",),
        )
    if target.startswith("<bool as PartialOrd<bool>>::"):
        expression = {
            "partial_cmp": "result == Some(cmp_bool_compare(*left, *right))",
            "lt": "result <==> !*left && *right",
            "le": "result <==> !*left || *right",
            "gt": "result <==> *left && !*right",
            "ge": "result <==> *left || !*right",
        }[method]
        output = "Option<Ordering>" if method == "partial_cmp" else "bool"
        return simple_contract(
            row, "bool_value", "", target,
            "left: &bool,\nright: &bool,", output, [expression],
            f"bool {method} directly exposes false-before-true ordering.",
        )
    if target == "<bool as Ord>::cmp":
        return simple_contract(
            row, "bool_value", "", target,
            "left: &bool,\nright: &bool,", "Ordering",
            ["result == cmp_bool_compare(*left, *right)"],
            "bool cmp maps the i8 difference to Less, Equal, or Greater.",
        )
    if target in {"<bool as Ord>::min", "<bool as Ord>::max"}:
        expression = "left && right" if method == "min" else "left || right"
        return simple_contract(
            row, "bool_value", "", target,
            "left: bool,\nright: bool,", "bool",
            [f"result == ({expression})"],
            f"bool {method} is the source bitwise boolean operation and retains tie behavior.",
        )
    if target == "<bool as Ord>::clamp":
        return simple_contract(
            row, "primitive_clamp", "", target,
            "value: bool,\nmin: bool,\nmax: bool,", "bool",
            [
                (
                    "(if min && !max { CmpCallOutcome::Panicked } else { "
                    "CmpCallOutcome::Returned("
                    "if !value && min { min } else if value && !max "
                    "{ max } else { value }) }) "
                    "== CmpCallOutcome::Returned(result)"
                )
            ],
            "bool clamp checks min <= max, then applies lower and upper branches.",
            components=("return_value", "panic_domain", "lower_then_upper_branch"),
            panic="panics_iff_min_greater_than_max",
        )
    if target.startswith("<char as PartialOrd<char>>::"):
        comparison = "cmp_char_compare(*left, *right)"
        expression = (
            f"result == Some({comparison})"
            if method == "partial_cmp"
            else f"result <==> cmp_relation_holds(CmpRelation::{method.capitalize()}, {comparison})"
        )
        output = "Option<Ordering>" if method == "partial_cmp" else "bool"
        return simple_contract(
            row, "char_value", "", target,
            "left: &char,\nright: &char,", output, [expression],
            f"char {method} follows Unicode scalar-value ordering.",
            ("char scalar-value representation",),
        )
    if target == "<char as Ord>::cmp":
        return simple_contract(
            row, "char_value", "", target,
            "left: &char,\nright: &char,", "Ordering",
            ["result == cmp_char_compare(*left, *right)"],
            "char cmp follows Unicode scalar-value ordering.",
            ("char scalar-value representation",),
        )
    clamp_match = re.fullmatch(r"<([^ ]+) as Ord>::clamp", target)
    if clamp_match:
        type_name = clamp_match.group(1)
        if type_name == "char":
            lower = "cmp_char_rank(value) < cmp_char_rank(min)"
            upper = "cmp_char_rank(value) > cmp_char_rank(max)"
            valid = "cmp_char_rank(min) <= cmp_char_rank(max)"
        else:
            lower = "value < min"
            upper = "value > max"
            valid = "min <= max"
        invalid = f"!({valid})"
        return simple_contract(
            row, "primitive_clamp", "", target,
            f"value: {type_name},\nmin: {type_name},\nmax: {type_name},",
            type_name,
            [
                (
                    f"(if {invalid} {{ CmpCallOutcome::Panicked }} else {{ "
                    "CmpCallOutcome::Returned("
                    f"if {lower} {{ min }} else if {upper} "
                    "{ max } else { value }) }) "
                    "== CmpCallOutcome::Returned(result)"
                )
            ],
            f"{type_name} clamp exposes the lower branch, upper branch, and in-range identity.",
            components=("return_value", "panic_domain", "lower_then_upper_branch"),
            panic="panics_iff_min_greater_than_max",
        )
    reference_partial_eq = re.fullmatch(
        r"<(&mut A|&A) as PartialEq<(&mut B|&B)>>::(eq|ne)", target
    )
    if reference_partial_eq:
        left_kind, right_kind, name = reference_partial_eq.groups()
        left_type = "&'a mut A" if left_kind == "&mut A" else "&'a A"
        right_type = "&mut B" if right_kind == "&mut B" else "&B"
        left_argument = (
            "cmp_shared_reborrow(left)" if left_kind == "&mut A" else "*left"
        )
        right_argument = (
            "cmp_shared_reborrow(right)" if right_kind == "&mut B" else "*right"
        )
        rendered_target = target.replace(
            left_kind,
            "&'a mut A" if left_kind == "&mut A" else "&'a A",
            1,
        )
        return simple_contract(
            row, "reference_forwarding",
            "'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized",
            rendered_target,
            f"left: &{left_type},\nright: &{right_type},", "bool",
            [
                f"call_ensures(<A as PartialEq<B>>::{name}, "
                f"({left_argument}, {right_argument}), result)"
            ],
            f"Reference {name} dereferences both operands exactly once and preserves their order.",
            (f"A::{name}",),
            ("return_value", "dereference_forwarding", "operand_order"),
            "inherits_referent_comparison_unwind",
            attributes=allow_trait,
        )
    reference_partial_ord = re.fullmatch(
        r"<&mut A as PartialOrd<&mut B>>::(partial_cmp|lt|le|gt|ge)", target
    )
    if reference_partial_ord:
        name = reference_partial_ord.group(1)
        output = "Option<Ordering>" if name == "partial_cmp" else "bool"
        return simple_contract(
            row, "reference_forwarding",
            "'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized",
            target.replace("&mut A", "&'a mut A", 1),
            "left: &&'a mut A,\nright: &&mut B,", output,
            [
                f"call_ensures(<A as PartialOrd<B>>::{name}, "
                "(cmp_shared_reborrow(left), "
                "cmp_shared_reborrow(right)), result)"
            ],
            f"Mutable-reference {name} dereferences both operands and preserves operand order.",
            (f"A::{name}",),
            ("return_value", "dereference_forwarding", "operand_order"),
            "inherits_referent_comparison_unwind",
            attributes=allow_trait,
        )
    if target == "<&mut A as Ord>::cmp":
        return simple_contract(
            row, "reference_forwarding",
            "'a, A: PointeeSized + Ord",
            target.replace("&mut A", "&'a mut A", 1),
            "left: &&'a mut A,\nright: &&'a mut A,", "Ordering",
            [
                "call_ensures(<A as Ord>::cmp, "
                "(cmp_shared_reborrow(left), "
                "cmp_shared_reborrow(right)), result)"
            ],
            "Mutable-reference cmp dereferences both operands and preserves operand order.",
            ("A::cmp",),
            ("return_value", "dereference_forwarding", "operand_order"),
            "inherits_referent_comparison_unwind",
            attributes=allow_trait,
        )
    raise SpecificationBuildError(f"unhandled cmp.rs pending target: {target}")


def build_contract(row: dict[str, Any]) -> Contract:
    source = row["source_file"]
    if source == "core/src/tuple.rs":
        return tuple_contract(row)
    if source == "core/src/array/equality.rs":
        return array_equality_contract(row)
    if source == "core/src/array/mod.rs":
        return array_order_contract(row)
    if source == "core/src/slice/cmp.rs":
        if row["method_name"] == "eq":
            return slice_equality_contract(row)
        return slice_order_contract(row)
    if source == "core/src/cmp.rs":
        return cmp_source_contract(row)
    raise SpecificationBuildError(
        f"pending identity has no specification renderer: {row['row_id']} {source}"
    )


def source_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_path": row["source_evidence"]["snapshot_path"],
        "snapshot_sha256": row["source_evidence"]["snapshot_sha256"],
        "span_sha256": row["source_evidence"]["span_sha256"],
        "start_line": row["source_begin_line"],
        "end_line": row["source_end_line"],
    }


def generated_source(contracts: list[Contract]) -> bytes:
    header = """#![feature(sized_hierarchy)]
#![allow(unused_imports, dead_code, deprecated)]

use core::cmp::{Eq, Ord, Ordering, PartialEq, PartialOrd, Reverse};
use core::clone::Clone;
use core::default::Default;
use core::fmt::Debug;
use core::hash::Hash;
use core::marker::PointeeSized;
use vstd::prelude::*;
use vstd::std_specs::cmp::{OrdSpec, PartialOrdSpec};

include!("cmp_shared_vocabulary.rs");

verus! {

"""
    body = "\n\n".join(contract.declaration for contract in contracts)
    return (header + body + "\n\n} // verus!\n").encode()


def exact_records(
    rows: list[dict[str, Any]],
    audit: dict[str, Any],
) -> list[dict[str, Any]]:
    by_candidate = {
        record["candidate_id"]: record
        for record in audit["records"]
        if record["status"] == "exact_match"
    }
    result = []
    for row in rows:
        if row["disposition"] != "exact_vstd":
            continue
        bindings = []
        for candidate_id in row["vstd_binding_ids"]:
            candidate = by_candidate.get(candidate_id)
            if candidate is None:
                raise SpecificationBuildError(
                    f"missing exact binding {candidate_id} for {row['row_id']}"
                )
            bindings.append(
                {
                    "candidate_id": candidate_id,
                    "canonical_upstream_binding": candidate[
                        "canonical_upstream_binding"
                    ],
                    "current_snapshot_loaded": candidate[
                        "current_snapshot_loaded"
                    ],
                    "evidence": candidate["evidence"],
                    "semantic_adequacy": candidate["semantic_adequacy"],
                    "vstd_provenance_class": candidate[
                        "vstd_provenance_class"
                    ],
                }
            )
        result.append(
            {
                "row_id": row["row_id"],
                "target": row["target"],
                "vstd_provenance_class": row["vstd_provenance_class"],
                "canonical_upstream_binding": all(
                    binding["canonical_upstream_binding"]
                    for binding in bindings
                ),
                "bindings": bindings,
            }
        )
    return result


def equivalence_record(
    row: dict[str, Any],
    contract: Contract | None,
    *,
    genuinely_impossible: bool = False,
) -> dict[str, Any]:
    if genuinely_impossible:
        components = [
            "required_direct_return_value",
            "nan_branch",
            "ordering_or_boolean_branch",
        ]
    else:
        components = (
            list(contract.observable_components)
            if contract
            else ["loaded_contract_return_and_post_state"]
        )
    if "panic_domain" not in components:
        components.append("panic_domain")
    return {
        "row_id": row["row_id"],
        "target": row["target"],
        "kind": "exact_observable_outcome_equality",
        "accepted_outcome_components": components,
        "contract_family": (
            "genuinely_impossible"
            if genuinely_impossible
            else contract.family if contract else "exact_vstd"
        ),
        "equivalence_rule": (
            "Two accepted-contract outcomes are equivalent exactly when every "
            "listed return, post-state, callback observation, dispatch-path "
            "observation, and panic-domain component is equal."
        ),
        "quotient_used": False,
        "positive_and_negative_witnesses_required": False,
        "review_status": "pending_independent_specification_review",
        "accepted_contract_available": not genuinely_impossible,
        "source_evidence": source_evidence(row),
    }


def helper_audit_payload(vocabulary: bytes) -> bytes:
    text = vocabulary.decode()
    uninterpreted = set(
        re.findall(r"pub uninterp spec fn (cmp_[A-Za-z0-9_]+)", text)
    )
    expected = set(UNINTERPRETED_HELPERS)
    if uninterpreted != expected:
        missing = sorted(expected - uninterpreted)
        extra = sorted(uninterpreted - expected)
        raise SpecificationBuildError(
            f"helper audit classification mismatch: missing={missing} extra={extra}"
        )
    open_defined = sorted(
        set(re.findall(r"pub open spec fn (cmp_[A-Za-z0-9_]+)", text))
    )
    records = [
        {
            "name": name,
            "definition_kind": "open_source_defined",
            "semantic_boundary": False,
            "whole_target_outcome": False,
            "permitted_role": "shared_defined_relation",
            "rationale": "The helper body is visible and source-shaped.",
        }
        for name in open_defined
    ]
    records.extend(
        {
            "name": name,
            "definition_kind": "uninterpreted_narrow_boundary",
            "semantic_boundary": True,
            "whole_target_outcome": False,
            "permitted_role": category,
            "rationale": rationale,
        }
        for name, (category, rationale) in sorted(
            UNINTERPRETED_HELPERS.items()
        )
    )
    return json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "passed",
            "vocabulary_sha256": sha256_bytes(vocabulary),
            "rule": (
                "No shared helper may encode a whole public target outcome. "
                "Uninterpreted helpers are restricted to call counts, private "
                "dependencies, dispatch observations, or state/effect boundaries."
            ),
            "prohibited_whole_target_helpers": [
                "cmp_reference_forward_result",
            ],
            "prohibited_helpers_absent": (
                "cmp_reference_forward_result" not in text
            ),
            "counts": {
                "total": len(records),
                "open_source_defined": len(open_defined),
                "uninterpreted_narrow_boundary": len(uninterpreted),
                "semantic_boundary": len(uninterpreted),
                "whole_target_outcome": 0,
            },
            "records": records,
        }
    )


def float_probe_binding() -> dict[str, Any]:
    if not FLOAT_MODEL_EVIDENCE_LATEST.is_file():
        raise SpecificationBuildError(
            "float model-boundary probe evidence is missing"
        )
    latest = load(FLOAT_MODEL_EVIDENCE_LATEST)
    run_dir = (ROOT / str(latest.get("run_dir", ""))).resolve()
    evidence_root = (
        ROOT / "verification" / "evidence" / "float-model-boundary"
    ).resolve()
    if not run_dir.is_relative_to(evidence_root):
        raise SpecificationBuildError(
            "float model-boundary evidence escapes its evidence root"
        )
    manifest = run_dir / "manifest.json"
    result_path = run_dir / "result.json"
    if not manifest.is_file() or not result_path.is_file():
        raise SpecificationBuildError(
            "float model-boundary evidence is incomplete"
        )
    result = load(result_path)
    if (
        latest.get("status") != "passed"
        or result.get("status") != "passed"
        or result.get("trial_count") != 2
        or result.get("passed_trial_count") != 2
        or latest.get("manifest_sha256") != sha256(manifest)
        or latest.get("result_sha256") != sha256(result_path)
    ):
        raise SpecificationBuildError(
            "float model-boundary evidence did not pass"
        )
    trial_bindings = []
    for trial in result.get("trials", []):
        path = (ROOT / str(trial.get("path", ""))).resolve()
        if not path.is_relative_to(run_dir) or not path.is_file():
            raise SpecificationBuildError(
                "float model-boundary trial path is invalid"
            )
        record = load(path)
        if (
            trial.get("sha256") != sha256(path)
            or record.get("status") != "passed"
            or record.get("expected_rejection") is not True
            or record.get("expected_fragment_observed") is not True
            or record.get("exit_code") == 0
        ):
            raise SpecificationBuildError(
                "float model-boundary trial is not decisive"
            )
        source = ROOT / str(record.get("source_path", ""))
        if (
            not source.is_file()
            or record.get("source_sha256") != sha256(source)
        ):
            raise SpecificationBuildError(
                "float model-boundary trial source is stale"
            )
        trial_bindings.append(
            {
                "name": record["trial"],
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "exit_code": record["exit_code"],
                "expected_fragment": record["expected_fragment"],
                "source_path": record["source_path"],
                "source_sha256": record["source_sha256"],
            }
        )
    return {
        "run_id": result["run_id"],
        "latest": {
            "path": str(FLOAT_MODEL_EVIDENCE_LATEST.relative_to(ROOT)),
            "sha256": sha256(FLOAT_MODEL_EVIDENCE_LATEST),
        },
        "manifest": {
            "path": str(manifest.relative_to(ROOT)),
            "sha256": sha256(manifest),
        },
        "result": {
            "path": str(result_path.relative_to(ROOT)),
            "sha256": sha256(result_path),
        },
        "trials": trial_bindings,
    }


def float_source_semantics(method: str) -> dict[str, Any]:
    if method == "eq":
        return {
            "result": (
                "false when either operand is NaN; otherwise IEEE numeric "
                "equality, including +0.0 == -0.0"
            ),
            "nan_result": False,
            "source_shape": "*self == *other",
        }
    if method == "ne":
        return {
            "result": (
                "true when either operand is NaN; otherwise the negation of "
                "IEEE numeric equality"
            ),
            "nan_result": True,
            "source_shape": "*self != *other",
        }
    if method == "partial_cmp":
        return {
            "result": (
                "match (left <= right, left >= right): "
                "(false,false) => None, (false,true) => Some(Greater), "
                "(true,false) => Some(Less), (true,true) => Some(Equal)"
            ),
            "nan_result": "None",
            "source_shape": "match (*self <= *other, *self >= *other)",
        }
    operator = {
        "lt": "<",
        "le": "<=",
        "gt": ">",
        "ge": ">=",
    }[method]
    return {
        "result": (
            f"the direct IEEE `{operator}` result; false when either "
            "operand is NaN"
        ),
        "nan_result": False,
        "source_shape": f"*self {operator} *other",
    }


def float_semantic_mutations(method: str) -> list[dict[str, str]]:
    if method == "eq":
        return [
            {
                "id": "nan_true",
                "mutation": "return true when either operand is NaN",
            },
            {
                "id": "signed_zero_distinct",
                "mutation": "treat +0.0 and -0.0 as unequal",
            },
        ]
    if method == "ne":
        return [
            {
                "id": "nan_false",
                "mutation": "return false when either operand is NaN",
            },
            {
                "id": "signed_zero_distinct",
                "mutation": "treat +0.0 and -0.0 as unequal",
            },
        ]
    if method == "partial_cmp":
        return [
            {
                "id": "none_to_equal",
                "mutation": "map (false, false) to Some(Equal)",
            },
            {
                "id": "reverse_ordering",
                "mutation": "swap the Some(Less) and Some(Greater) branches",
            },
        ]
    return [
        {
            "id": "nan_true",
            "mutation": "return true when either operand is NaN",
        },
        {
            "id": "relation_reversal",
            "mutation": "replace the primitive relation with its converse",
        },
    ]


def float_model_boundary_payload(
    rows: list[dict[str, Any]],
    exact_audit: dict[str, Any],
) -> bytes:
    expected_targets = {
        f"<{type_name} as {trait_name}<{type_name}>>::{method}"
        for type_name in FLOAT_TYPES
        for method, trait_name in (
            ("eq", "PartialEq"),
            ("ne", "PartialEq"),
            ("partial_cmp", "PartialOrd"),
            ("lt", "PartialOrd"),
            ("le", "PartialOrd"),
            ("gt", "PartialOrd"),
            ("ge", "PartialOrd"),
        )
    }
    if {row["target"] for row in rows} != expected_targets:
        raise SpecificationBuildError(
            "float model-boundary identity set is not the 14 Rust targets"
        )
    candidates = {
        record["row_id"]: record
        for record in exact_audit["records"] + exact_audit["rejected_candidates"]
        if record.get("row_id") in {row["row_id"] for row in rows}
    }
    if set(candidates) != {row["row_id"] for row in rows}:
        raise SpecificationBuildError(
            "float model-boundary vstd candidate set is incomplete"
        )
    probe = float_probe_binding()
    records = []
    for row in sorted(rows, key=lambda value: value["row_id"]):
        candidate = candidates[row["row_id"]]
        if candidate.get("status") != "rejected_semantically_incomplete":
            raise SpecificationBuildError(
                f"float candidate was not rejected: {row['row_id']}"
            )
        method = row["method_name"]
        ensures_name = (
            "partial_cmp_ensures"
            if method == "partial_cmp"
            else f"{method}_ensures"
        )
        records.append(
            {
                "row_id": row["row_id"],
                "target": row["target"],
                "owner_type": row["owner_type"],
                "method": method,
                "disposition": "genuinely_impossible",
                "counts_as_specification_coverage": False,
                "review_status": "pending_independent_row_approval",
                "source_evidence": source_evidence(row),
                "required_direct_source_semantics": float_source_semantics(
                    method
                ),
                "required_outcome_equivalence": (
                    "exact observable result equality; no quotient is "
                    "source- or documentation-justified"
                ),
                "loaded_vstd_candidate": {
                    "candidate_id": candidate["candidate_id"],
                    "status": candidate["status"],
                    "declaration_evidence": candidate["evidence"],
                    "semantic_adequacy": candidate["semantic_adequacy"],
                    "rejection_reason": candidate["rejection_reason"],
                },
                "missing_model_boundary": {
                    "name": (
                        f"loaded_vstd_{row['owner_type']}_{method}_"
                        "result_predicate"
                    ),
                    "predicate": ensures_name,
                    "semantic_boundary": True,
                    "whole_target_outcome": True,
                    "accepted_for_contract_or_proof": False,
                    "reason": (
                        "The predicate is the only loaded postcondition for "
                        "the target and places no source-backed constraint on "
                        "its complete return value."
                    ),
                },
                "attempts": [
                    {
                        "approach": "reuse_loaded_exact_vstd_binding",
                        "result": "rejected_semantically_incomplete",
                        "reason": (
                            "The return is hidden behind an unconstrained "
                            f"{ensures_name} predicate."
                        ),
                    },
                    {
                        "approach": (
                            "derive_functionality_and_nan_behavior_from_"
                            "loaded_predicate"
                        ),
                        "result": "actual_verus_rejected",
                        "evidence_run_id": probe["run_id"],
                        "reason": (
                            "Actual Verus cannot derive either unique output "
                            "or the required NaN branch from the predicate."
                        ),
                    },
                    {
                        "approach": (
                            "install_local_source_backed_assume_specification"
                        ),
                        "result": "verus_duplicate_specification_error",
                        "evidence_run_id": probe["run_id"],
                        "reason": (
                            "The loaded vstd binding already owns this exact "
                            "target and Verus rejects a stronger local binding."
                        ),
                    },
                    {
                        "approach": (
                            "axiomatize_predicate_or_use_whole_target_"
                            "external_body"
                        ),
                        "result": "rejected_as_unsound",
                        "reason": (
                            "Either alternative assumes the principal result "
                            "and recreates the whole-target trust boundary "
                            "forbidden by the mission."
                        ),
                    },
                ],
                "semantic_mutations": float_semantic_mutations(method),
                "mutation_status": (
                    "not_claimed: no sound target-bound baseline exists; "
                    "claiming rejection would reuse the missing model"
                ),
                "probe_evidence": probe,
            }
        )
    return json_bytes(
        {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "pending_independent_row_approval",
            "classification": "genuinely_impossible",
            "record_count": len(records),
            "identity_set_sha256": hashlib.sha256(
                json.dumps(
                    sorted(record["row_id"] for record in records),
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "strict_coverage_credit": 0,
            "probe_evidence": probe,
            "records": records,
        }
    )


def build_payloads() -> dict[Path, bytes]:
    inventory = load(INVENTORY)
    reconciliation = load(RECONCILIATION)
    audit = load(EXACT_AUDIT)
    rows = inventory["rows"]
    pending = generated_candidate_rows(rows)
    impossible = model_boundary_rows(rows)
    exact = [row for row in rows if row["disposition"] == "exact_vstd"]
    contracts = [build_contract(row) for row in pending]
    if len(contracts) != len(pending):
        raise SpecificationBuildError("not every pending row generated a contract")
    if len({contract.row_id for contract in contracts}) != len(contracts):
        raise SpecificationBuildError("duplicate generated contract row id")
    if {contract.row_id for contract in contracts} != {
        row["row_id"] for row in pending
    }:
        raise SpecificationBuildError("generated contract identity set mismatch")

    generated = generated_source(contracts)
    vocabulary_data = VOCABULARY.read_bytes()
    helper_audit_data = helper_audit_payload(vocabulary_data)
    float_boundary_data = float_model_boundary_payload(
        impossible,
        audit,
    )
    float_boundary = json.loads(float_boundary_data)
    contract_by_id = {contract.row_id: contract for contract in contracts}
    impossible_by_id = {
        record["row_id"]: record
        for record in float_boundary["records"]
    }
    exact_binding_records = exact_records(rows, audit)
    exact_by_id = {record["row_id"]: record for record in exact_binding_records}
    equivalence_records = [
        equivalence_record(
            row,
            contract_by_id.get(row["row_id"]),
            genuinely_impossible=row["row_id"] in impossible_by_id,
        )
        for row in rows
    ]
    equivalence = {
        "schema_version": 1,
        "module": "core::cmp",
        "default": "exact equality of every accepted observable outcome component",
        "non_exact_equivalence_count": 0,
        "record_count": len(equivalence_records),
        "review_status": "pending_independent_specification_review",
        "records": equivalence_records,
    }
    equivalence_data = json_bytes(equivalence)
    equivalence_hash = sha256_bytes(equivalence_data)
    catalog_rows = []
    for row in rows:
        contract = contract_by_id.get(row["row_id"])
        base = {
            "row_id": row["row_id"],
            "target": row["target"],
            "api_kind": row["api_kind"],
            "implementation_kind": row["implementation_kind"],
            "source": source_evidence(row),
            "equivalence": {
                "kind": "exact_observable_outcome_equality",
                "path": "specification/cmp_outcome_equivalence.json",
                "package_sha256": equivalence_hash,
                "review_status": "pending_independent_specification_review",
            },
        }
        if row["row_id"] in impossible_by_id:
            boundary = impossible_by_id[row["row_id"]]
            base.update(
                {
                    "disposition": "genuinely_impossible",
                    "contract": None,
                    "model_boundary": {
                        "path": str(
                            FLOAT_MODEL_BOUNDARY.relative_to(ROOT)
                        ),
                        "package_sha256": sha256_bytes(
                            float_boundary_data
                        ),
                        "review_status": boundary["review_status"],
                        "missing_model_boundary": boundary[
                            "missing_model_boundary"
                        ],
                        "required_direct_source_semantics": boundary[
                            "required_direct_source_semantics"
                        ],
                        "required_outcome_equivalence": boundary[
                            "required_outcome_equivalence"
                        ],
                        "attempt_count": len(boundary["attempts"]),
                        "semantic_mutations": boundary[
                            "semantic_mutations"
                        ],
                        "mutation_status": boundary["mutation_status"],
                        "probe_run_id": boundary["probe_evidence"][
                            "run_id"
                        ],
                    },
                }
            )
        elif contract:
            declaration_hash = sha256_bytes(
                (contract.declaration + "\n").encode()
            )
            base.update(
                {
                    "disposition": "generated",
                    "contract": {
                        "path": "specs/generated_cmp_specs.rs",
                        "marker": row["row_id"],
                        "binding_kind": (
                            "shared_trait_default_contract"
                            if contract.family
                            in {"empty_eq_default", "trait_default_clamp"}
                            else "assume_specification"
                        ),
                        "declaration_sha256": declaration_hash,
                        "family": contract.family,
                        "semantic_summary": contract.semantic_summary,
                        "dependencies": list(contract.dependencies),
                        "observable_components": list(
                            contract.observable_components
                        ),
                        "panic_domain": contract.panic_domain,
                    },
                }
            )
        else:
            binding = exact_by_id[row["row_id"]]
            base.update(
                {
                    "disposition": "exact_vstd",
                    "contract": {
                        "path": "specs/existing_vstd/bindings.json",
                        "canonical_upstream_binding": binding[
                            "canonical_upstream_binding"
                        ],
                        "vstd_provenance_class": binding[
                            "vstd_provenance_class"
                        ],
                        "binding_ids": [
                            item["candidate_id"]
                            for item in binding["bindings"]
                        ],
                        "semantic_dependencies": [
                            item["semantic_adequacy"]
                            for item in binding["bindings"]
                        ],
                    },
                }
            )
        catalog_rows.append(base)
    catalog = {
        "schema_version": 1,
        "module": "core::cmp",
        "inventory_sha256": sha256(INVENTORY),
        "generated_contract_sha256": sha256_bytes(generated),
        "shared_vocabulary_sha256": sha256(VOCABULARY),
        "outcome_equivalence_sha256": equivalence_hash,
        "counts": {
            "stable_inventory_total": len(rows),
            "generated": len(pending),
            "exact_vstd": len(exact),
            "specified_total": len(pending) + len(exact),
            "genuinely_impossible": len(impossible),
            "canonical_upstream_exact_vstd": sum(
                row["vstd_provenance_class"] == "tracked_clean_vstd"
                for row in exact
            ),
            "frozen_noncanonical_exact_vstd": sum(
                row["vstd_provenance_class"]
                == "frozen_dirty_or_untracked_current_vstd"
                for row in exact
            ),
            "pending": 0,
            "strict_specification_coverage": (
                (len(pending) + len(exact)) / len(rows)
                if rows
                else 1.0
            ),
            "review_adjusted_accounting_complete": False,
        },
        "rows": catalog_rows,
    }
    catalog_data = json_bytes(catalog)
    bindings = {
        "schema_version": 1,
        "module": "core::cmp",
        "rule": (
            "These are references to frozen vstd bindings, not regenerated "
            "contracts. canonical_upstream_binding=false is current dirty or "
            "untracked checkout coverage and is never reported as upstream."
        ),
        "counts": {
            "exact_vstd": len(exact_binding_records),
            "canonical_upstream": sum(
                record["canonical_upstream_binding"]
                for record in exact_binding_records
            ),
            "frozen_dirty_or_untracked": sum(
                not record["canonical_upstream_binding"]
                for record in exact_binding_records
            ),
        },
        "records": exact_binding_records,
    }
    bindings_data = json_bytes(bindings)
    readme = f"""# Rust 1.96 `core::cmp` specifications

This is the mandatory module-level browsing package. Its counts are regenerated
from `inventory/core_cmp_exec_fn_inventory.json`, never used as acceptance
constants.

- `generated_cmp_specs.rs` contains one source-backed declaration for each of
  the {len(pending)} inventory identities not exactly bound by vstd and not
  blocked by the loaded float model.
- `all_cmp_specs.json` accounts for all {len(rows)} stable executable
  identities and binds every row to source and exact outcome equivalence.
- `cmp_shared_vocabulary.rs` contains only shared observations and narrow
  dependency models; target return branches remain in direct `ensures`.
- `existing_vstd/bindings.json` retains the {len(exact)} exact bindings:
  {bindings['counts']['canonical_upstream']} tracked-clean upstream bindings and
  {bindings['counts']['frozen_dirty_or_untracked']} frozen current-checkout
  bindings that are explicitly noncanonical.
- `../specification/float_model_boundary_audit.json` records the
  {len(impossible)} `f32`/`f64` comparison identities that cannot receive a
  sound target-bound contract while vstd's unconstrained bindings are loaded.
  They receive no strict coverage credit and require independent row approval
  as `genuinely_impossible`.

Proof harness generation remains unauthorized until the independent
specification review is accepted.
""".encode()
    existing_readme = f"""# Existing vstd references

`bindings.json` records all {len(exact)} exact identity/signature bindings and
their frozen source hashes. The files below are relative symbolic references to
the campaign's immutable vstd snapshots.

The {bindings['counts']['frozen_dirty_or_untracked']} `Ordering` convenience
bindings from `std_specs/ordering.rs` have
`canonical_upstream_binding: false`; they depend on the frozen untracked module
and dirty loader edits and must not be described as canonical upstream vstd.
""".encode()
    manifest_stub = {
        "schema_version": 1,
        "module": "core::cmp",
        "implementation_proofs_authorized": False,
        "counts": catalog["counts"],
        "source_contract_family_count": len(
            {contract.family for contract in contracts}
        ),
        "all_generatable_identities_have_contracts": (
            len(contracts) == len(pending)
        ),
        "genuinely_impossible_candidate_count": len(impossible),
        "genuinely_impossible_rows_require_independent_approval": True,
        "all_identities_have_exact_outcome_equivalence": (
            len(equivalence_records) == len(rows)
            and all(not record["quotient_used"] for record in equivalence_records)
        ),
        "independent_specification_review": {
            "status": "pending",
            "request": "reviews/specification_review_request.json",
        },
        "artifacts": [],
    }
    base_payloads = {
        GENERATED: generated,
        CATALOG: catalog_data,
        EXISTING_BINDINGS: bindings_data,
        README: readme,
        EXISTING_README: existing_readme,
        EQUIVALENCE: equivalence_data,
        HELPER_AUDIT: helper_audit_data,
        FLOAT_MODEL_BOUNDARY: float_boundary_data,
    }
    manifest_stub["artifacts"] = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256_bytes(data),
        }
        for path, data in sorted(
            base_payloads.items(), key=lambda item: str(item[0])
        )
    ] + [
        {
            "path": str(VOCABULARY.relative_to(ROOT)),
            "sha256": sha256(VOCABULARY),
        }
    ]
    manifest_data = json_bytes(manifest_stub)
    review_request = {
        "schema_version": 1,
        "review_type": "bounded_inventory_and_specification",
        "module": "core::cmp",
        "scope": (
            "all stable executable Rust 1.96 identities publicly reachable "
            "through core::cmp"
        ),
        "implementation_proofs_authorized": False,
        "counts": catalog["counts"],
        "required_verdict": {
            "independent": True,
            "canonical_acceptance_requires": (
                "a sealed handoff with producer_role=reviewer and review.status=done"
            ),
        },
        "artifacts": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_bytes(data),
            }
            for path, data in [
                (GENERATED, generated),
                (VOCABULARY, vocabulary_data),
                (CATALOG, catalog_data),
                (EXISTING_BINDINGS, bindings_data),
                (EQUIVALENCE, equivalence_data),
                (MANIFEST, manifest_data),
                (HELPER_AUDIT, helper_audit_data),
                (FLOAT_MODEL_BOUNDARY, float_boundary_data),
            ]
        ],
        "review_questions": [
            (
                "Does every generatable inventory identity have exactly one "
                "target-bound declaration?"
            ),
            (
                f"Are all {len(impossible)} float identities correctly "
                "rejected as exact-vstd coverage, backed by target-specific "
                "attempts, and eligible for genuinely_impossible approval?"
            ),
            (
                "Does the float boundary audit state the direct Rust 1.96 "
                "NaN, None, equality, and ordering branches without treating "
                "the loaded predicates as narrow or functional?"
            ),
            (
                f"Are {bindings['counts']['canonical_upstream']} tracked-clean "
                f"and {bindings['counts']['frozen_dirty_or_untracked']} "
                "dirty/untracked exact-vstd bindings kept distinct?"
            ),
            "Do tuple and slice contracts preserve first-decisive call order and count?",
            "Do Reverse contracts swap operands at the call rather than only reverse a result?",
            "Do min/max comparator and key forms preserve callback order and equal-value bias?",
            "Do slice and array contracts distinguish generic, always-applicable, and bytewise paths?",
            "Are clamp successful outcomes and the min > max panic domain both explicit?",
            "Does exact outcome equality include return, post-state, callback, dispatch, and panic observations?",
            "Are any whole target outcomes hidden behind uninterpreted helpers?",
            "Does the helper-boundary audit classify every shared helper and report zero whole-target helpers?",
            "Does Verus --no-verify bind the exact generated source and vocabulary hashes?",
        ],
    }
    return {
        **base_payloads,
        MANIFEST: manifest_data,
        REVIEW_REQUEST: json_bytes(review_request),
    }


def refresh_symlinks(audit: dict[str, Any]) -> None:
    source_paths = sorted(
        {
            record["evidence"]["snapshot_path"]
            for record in audit["records"]
            if record["status"] == "exact_match"
        }
    )
    for source in source_paths:
        snapshot = ROOT / source
        prefix = "provenance/snapshots/verus/source/vstd/"
        if not source.startswith(prefix):
            raise SpecificationBuildError(f"unexpected vstd snapshot: {source}")
        relative = source[len(prefix):]
        link = EXISTING / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        desired = os.path.relpath(snapshot, link.parent)
        if link.is_symlink() and os.readlink(link) == desired:
            continue
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(desired)


def main() -> int:
    payloads = build_payloads()
    for path, data in payloads.items():
        write_if_changed(path, data)
    refresh_symlinks(load(EXACT_AUDIT))
    inventory = load(INVENTORY)
    rows = inventory["rows"]
    generated = len(generated_candidate_rows(rows))
    impossible = len(model_boundary_rows(rows))
    exact = sum(
        row["disposition"] == "exact_vstd" for row in rows
    )
    print(
        json.dumps(
            {
                "exact_vstd_references": exact,
                "generated_contracts": generated,
                "genuinely_impossible": impossible,
                "status": "built",
                "total": len(rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
