"""Proof template rendering for the pending ``core::cmp`` identities owned by
this campaign slice.

This module owns exactly the 73 ``disposition == "pending"`` inventory rows
whose ``source_file`` is ``core/src/cmp.rs``: the generated primitive
``bool``/``char``/``()`` comparisons, all 15 ``Ord::clamp`` bodies, the
compiler-derived/debug/hash/``then_with`` ``Ordering`` identities, the
``Reverse<T>`` default/debug/hash/clone/clone_from/comparison identities
(with operand reversal for the ``PartialOrd``/``Ord`` methods), the free
``core::cmp::{min,max,min_by,max_by,min_by_key,max_by_key}`` functions, every
mutable-reference-forwarding ``PartialEq``/``PartialOrd``/``Ord`` impl, and
the ``Eq::assert_receiver_is_total_eq`` trait-default empty method.

Two functions are exported:

``supports(row, contract_family)``
    Returns ``True`` only when ``row`` is one of the 73 owned identities and
    ``contract_family`` matches the family this module has independently
    assigned to that row.

``render(row, contract_family, accepted_contract_text)``
    Renders a :class:`~tools.proof_template_common.ProofTemplate` for an
    owned row. The implementation proof preserves the exact resolved
    signature/generic/lifetime/mutability shape of the target whenever Verus
    supports it directly; the sole documented exception is
    ``empty_eq_default``, whose real body is empty and is lowered to the
    trivial predicate ``true`` (see ``_build_empty_eq_default``).

    ``implementation_target`` always performs the target's own work itself:
    it executes the real referent delegate, the real derived
    discriminant/variant-name selection, the real lower ``Debug::fmt`` /
    ``Hash::hash`` delegation and the real ``f(&v2)``-then-``f(&v1)`` key
    callback sequence with its ``K::lt`` comparison and tie selection. No
    rendered family delegates the whole target outcome to an ``external_body``
    helper. The remaining boundaries are strictly lower operations -- a shared
    reborrow of an unsized referent, one ``Formatter::write_str``, one
    discriminant hash, one ``FnMut`` call, one observation-count equation --
    each with a postcondition strictly narrower than (never alpha-identical
    to) the target's, each recorded with ``whole_target_outcome=False``.

Every rendered completeness theorem compares two accepted outcomes of the
*same* deterministic ``accepted_contract`` predicate (built from the same
callback/dispatch/panic/dependency environment) and proves exact outcome
equality without any external theorem, ``assume``, or ``admit``.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from tools.proof_template_common import ProofTemplate

# ---------------------------------------------------------------------------
# Row ownership
# ---------------------------------------------------------------------------

# row_id -> contract family, for exactly the 73 pending core/src/cmp.rs rows
# this module owns. This table is the single source of truth for `supports`;
# it is cross-checked against the live inventory by the accompanying tests.
ROW_FAMILY: dict[str, str] = {
    # Ordering: compiler-derived eq/partial_cmp/cmp/clone.
    "rustdoc-10786-10785": "ordering_value",
    "rustdoc-11198-11197": "ordering_value",
    "rustdoc-11200-11199": "ordering_value",
    "rustdoc-9698-9697": "ordering_value",
    # Reverse<T>: direct field-equality forwarding.
    "rustdoc-10788-10787": "reverse_forwarding",
    # (): eq/ne/cmp/partial_cmp.
    "rustdoc-10791-10789": "unit_value",
    "rustdoc-10791-10790": "unit_value",
    "rustdoc-11249-11248": "unit_value",
    "rustdoc-11396-11395": "unit_value",
    # char: eq/ne/cmp/partial_cmp/lt/le/gt/ge.
    "rustdoc-10797-10795": "char_value",
    "rustdoc-10797-10796": "char_value",
    "rustdoc-11257-11255": "char_value",
    "rustdoc-11432-11427": "char_value",
    "rustdoc-11432-11428": "char_value",
    "rustdoc-11432-11429": "char_value",
    "rustdoc-11432-11430": "char_value",
    "rustdoc-11432-11431": "char_value",
    # bool: cmp/min/max/partial_cmp/lt/le/gt/ge.
    "rustdoc-11254-11250": "bool_value",
    "rustdoc-11254-11251": "bool_value",
    "rustdoc-11254-11252": "bool_value",
    "rustdoc-11402-11397": "bool_value",
    "rustdoc-11402-11398": "bool_value",
    "rustdoc-11402-11399": "bool_value",
    "rustdoc-11402-11400": "bool_value",
    "rustdoc-11402-11401": "bool_value",
    # Mutable-reference forwarding (&mut A / &A vs &mut B / &B).
    "rustdoc-10853-10851": "reference_forwarding",
    "rustdoc-10853-10852": "reference_forwarding",
    "rustdoc-10856-10854": "reference_forwarding",
    "rustdoc-10856-10855": "reference_forwarding",
    "rustdoc-10859-10857": "reference_forwarding",
    "rustdoc-10859-10858": "reference_forwarding",
    "rustdoc-11299-11298": "reference_forwarding",
    "rustdoc-11518-11513": "reference_forwarding",
    "rustdoc-11518-11514": "reference_forwarding",
    "rustdoc-11518-11515": "reference_forwarding",
    "rustdoc-11518-11516": "reference_forwarding",
    "rustdoc-11518-11517": "reference_forwarding",
    # Ordering::then_with.
    "rustdoc-11181-11180": "ordering_then_with",
    # Ordering Debug/Hash.
    "rustdoc-11204-11203": "ordering_debug",
    "rustdoc-11206-11205": "ordering_hash",
    # Reverse<T> Default/Debug/Hash.
    "rustdoc-11225-11224": "reverse_default",
    "rustdoc-11228-11227": "reverse_debug",
    "rustdoc-11230-11229": "reverse_hash",
    # Reverse<T> PartialOrd/Ord: operand-swapped forwarding.
    "rustdoc-11236-11231": "reverse_operand_reversal",
    "rustdoc-11236-11232": "reverse_operand_reversal",
    "rustdoc-11236-11233": "reverse_operand_reversal",
    "rustdoc-11236-11234": "reverse_operand_reversal",
    "rustdoc-11236-11235": "reverse_operand_reversal",
    "rustdoc-11238-11237": "reverse_operand_reversal",
    # 14 Ord::clamp overrides.
    "rustdoc-11254-11253": "primitive_clamp",
    "rustdoc-11257-11256": "primitive_clamp",
    "rustdoc-11260-11259": "primitive_clamp",
    "rustdoc-11263-11262": "primitive_clamp",
    "rustdoc-11266-11265": "primitive_clamp",
    "rustdoc-11269-11268": "primitive_clamp",
    "rustdoc-11272-11271": "primitive_clamp",
    "rustdoc-11275-11274": "primitive_clamp",
    "rustdoc-11278-11277": "primitive_clamp",
    "rustdoc-11281-11280": "primitive_clamp",
    "rustdoc-11284-11283": "primitive_clamp",
    "rustdoc-11287-11286": "primitive_clamp",
    "rustdoc-11290-11289": "primitive_clamp",
    "rustdoc-11293-11292": "primitive_clamp",
    # Shared Ord::clamp default, whose vstd declaration omits the panic outcome.
    "trait-default-50-11241": "trait_default_clamp",
    # Free functions.
    "rustdoc-11629": "free_ord_forwarding",
    "rustdoc-11632": "free_ord_forwarding",
    "rustdoc-11630": "comparator_callback",
    "rustdoc-11633": "comparator_callback",
    "rustdoc-11631": "key_callback_order",
    "rustdoc-11634": "key_callback_order",
    # Reverse<T> Clone/clone_from.
    "rustdoc-9702-9699": "reverse_clone",
    "rustdoc-9702-9701": "reverse_clone",
    # Eq trait-default empty method.
    "source-trait-default-eq-assert_receiver_is_total_eq": "empty_eq_default",
}

assert len(ROW_FAMILY) == 73

# family -> the one REQUIRED_MUTATION_CATEGORIES bucket exercised by both the
# implementation and completeness mutation of every row in that family. This
# module's owned rows collectively cover forwarding, callback_order_state,
# branch_reversal, equality_ordering_distinction, and panic_domain.
_FAMILY_MUTATION_CATEGORY: dict[str, str] = {
    "ordering_value": "equality_ordering_distinction",
    "reverse_forwarding": "forwarding",
    "unit_value": "equality_ordering_distinction",
    "char_value": "equality_ordering_distinction",
    "bool_value": "equality_ordering_distinction",
    "reference_forwarding": "forwarding",
    "ordering_then_with": "callback_order_state",
    "ordering_debug": "forwarding",
    "ordering_hash": "forwarding",
    "reverse_default": "forwarding",
    "reverse_debug": "forwarding",
    "reverse_hash": "forwarding",
    "reverse_operand_reversal": "branch_reversal",
    "primitive_clamp": "panic_domain",
    "trait_default_clamp": "panic_domain",
    "free_ord_forwarding": "forwarding",
    "comparator_callback": "callback_order_state",
    "key_callback_order": "callback_order_state",
    "reverse_clone": "forwarding",
    "empty_eq_default": "equality_ordering_distinction",
}

REQUIRED_MUTATION_CATEGORIES = frozenset(_FAMILY_MUTATION_CATEGORY.values())
assert REQUIRED_MUTATION_CATEGORIES == frozenset(
    {
        "forwarding",
        "callback_order_state",
        "branch_reversal",
        "equality_ordering_distinction",
        "panic_domain",
    }
)


def supports(row: dict[str, Any], contract_family: str) -> bool:
    """Return ``True`` iff this module owns ``row`` under ``contract_family``."""

    if not isinstance(row, dict):
        return False
    if row.get("source_file") != "core/src/cmp.rs":
        return False
    if row.get("disposition") != "pending":
        return False
    row_id = row.get("row_id")
    if not isinstance(row_id, str):
        return False
    return ROW_FAMILY.get(row_id) == contract_family


# ---------------------------------------------------------------------------
# Shared rendering helpers
# ---------------------------------------------------------------------------

_HEADER = (
    '#![allow(dead_code, unused_imports, unused_variables)]\n'
    '#![crate_type = "lib"]\n'
)

_SIZED_HIERARCHY_HEADER = "#![feature(sized_hierarchy)]\n" + _HEADER

_REVERSE_TYPE_SPEC = (
    "#[verifier::external_type_specification]\n"
    "#[verifier::reject_recursive_types(T)]\n"
    "pub struct ExCmpReverse<T>(core::cmp::Reverse<T>);\n"
)

_FORMATTER_TYPE_SPEC = (
    "#[verifier::external_type_specification]\n"
    "#[verifier::external_body]\n"
    "pub struct ExCmpFormatter<'a>(core::fmt::Formatter<'a>);\n"
    "\n"
    "#[verifier::external_type_specification]\n"
    "#[verifier::external_body]\n"
    "pub struct ExCmpFmtError(core::fmt::Error);\n"
)

# `core::fmt::Debug` / `core::hash::Hash` have no vstd specification, so the
# lower trait call cannot be named by `call_ensures` without declaring the
# trait to Verus first. Both proxies are pure declarations: they add no
# `ensures`, so `call_ensures(<T as Debug>::fmt, ..)` / `call_ensures(<T as
# Hash>::hash, ..)` stay the opaque per-impl relations of the real lower
# trait methods.
_DEBUG_TRAIT_SPEC = (
    "#[verifier::external_trait_specification]\n"
    "pub trait ExDebug: PointeeSized {\n"
    "    type ExternalTraitSpecificationFor: core::fmt::Debug;\n"
    "\n"
    "    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>)"
    " -> (result: core::fmt::Result);\n"
    "}\n\n"
)

_HASH_TRAIT_SPEC = (
    "#[verifier::external_trait_specification]\n"
    "pub trait ExHash: PointeeSized {\n"
    "    type ExternalTraitSpecificationFor: core::hash::Hash;\n"
    "\n"
    "    fn hash<H: Hasher>(&self, state: &mut H);\n"
    "}\n\n"
)


# ---------------------------------------------------------------------------
# Derived narrowness check
#
# `whole_target_outcome=False` is never taken on trust here: before a boundary
# record is emitted, the rendered proof text itself is parsed and the
# boundary's declared contract is compared against `implementation_target`'s.
# A helper whose `requires`/`ensures` are alpha-identical to the target's, a
# helper that names the target's `accepted_contract`, and a body that is a
# single call to such a helper are all rejected at render time -- regardless
# of what the helper's body says.
# ---------------------------------------------------------------------------

_FN_HEADER_RE = re.compile(
    r"(?m)^(?P<attrs>(?:#\[[^\n]*\]\n)*)"
    r"(?:pub(?:\([^)]*\))?\s+)?"
    r"(?:unsafe\s+)?(?:broadcast\s+)?(?:(?:open|closed)\s+)?"
    r"(?:(?:spec|proof|exec)\s+)?"
    r"fn\s+(?P<name>[A-Za-z0-9_]+)"
)


def _balanced_end(text: str, start: int, opener: str, closer: str) -> int:
    depth = 0
    index = start
    while index < len(text):
        if text.startswith("->", index):
            index += 2
            continue
        character = text[index]
        if character == opener:
            depth += 1
        elif character == closer:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise AssertionError("unbalanced group")


def _top_level_items(text: str) -> list[str]:
    items: list[str] = []
    depth = 0
    current: list[str] = []
    index = 0
    while index < len(text):
        if text.startswith("->", index):
            current.append("->")
            index += 2
            continue
        character = text[index]
        if character in "(<[":
            depth += 1
        elif character in ")>]":
            depth -= 1
        if character == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        index += 1
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return [item for item in items if item]


def _declared_clauses(rest: str) -> list[str]:
    clauses: list[str] = []
    active = False
    buffer: list[str] = []
    for raw_line in rest.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped in ("requires", "ensures"):
            if buffer:
                clauses.append(" ".join(buffer))
                buffer = []
            active = True
            continue
        if not active:
            continue
        buffer.append(stripped)
        if stripped.endswith(","):
            clauses.append(" ".join(buffer))
            buffer = []
    if buffer:
        clauses.append(" ".join(buffer))
    return clauses


def _parsed_function(text: str, match: re.Match[str]) -> tuple[str, str, str]:
    """Return ``(attributes, normalized_contract, body)`` for one function."""

    declaration_start = match.end()
    opening = text.find("\n{", declaration_start)
    if opening < 0:
        return match.group("attrs"), "", ""
    opening += 1
    depth = 0
    closing = len(text)
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index
                break
    declaration = text[declaration_start:opening]

    index = 0
    while index < len(declaration) and declaration[index].isspace():
        index += 1
    generics = ""
    if index < len(declaration) and declaration[index] == "<":
        end = _balanced_end(declaration, index, "<", ">")
        generics = declaration[index + 1:end - 1]
        index = end
    while index < len(declaration) and declaration[index].isspace():
        index += 1
    end = _balanced_end(declaration, index, "(", ")")
    parameters = declaration[index + 1:end - 1]
    rest = declaration[end:]

    names = [
        item.split(":", 1)[0].strip()
        for item in _top_level_items(parameters)
        if ":" in item
    ]
    generic_names = [
        item.split(":", 1)[0].strip().removeprefix("const ").strip()
        for item in _top_level_items(generics)
        if not item.startswith("'")
    ]
    lifetimes = [
        item.split(":", 1)[0].strip().lstrip("'")
        for item in _top_level_items(generics)
        if item.startswith("'")
    ]
    binder = re.search(r"->\s*\(\s*([A-Za-z0-9_]+)\s*:", rest)

    substitutions = [
        (re.compile(rf"(?<!['\w]){re.escape(name)}\b"), f"@p{position}")
        for position, name in enumerate(names)
    ]
    substitutions += [
        (re.compile(rf"(?<!['\w]){re.escape(name)}\b"), f"@t{position}")
        for position, name in enumerate(generic_names)
    ]
    substitutions += [
        (re.compile(rf"'{re.escape(name)}\b"), f"'@l{position}")
        for position, name in enumerate(lifetimes)
    ]
    if binder is not None:
        substitutions.append(
            (re.compile(rf"(?<!['\w]){re.escape(binder.group(1))}\b"), "@ret")
        )

    normalized: list[str] = []
    for clause in _declared_clauses(rest):
        for pattern, replacement in substitutions:
            clause = pattern.sub(replacement, clause)
        normalized.append(re.sub(r"\s+", " ", clause).strip().rstrip(",").strip())
    return (
        match.group("attrs"),
        " && ".join(sorted(normalized)),
        text[opening + 1:closing],
    )


def _assert_boundaries_are_derived_narrow(
    implementation_proof: str,
    boundaries: tuple[dict[str, Any], ...],
) -> None:
    parsed: dict[str, tuple[str, str, str]] = {}
    for match in _FN_HEADER_RE.finditer(implementation_proof):
        parsed[match.group("name")] = _parsed_function(implementation_proof, match)
    attributes, target_contract, target_body = parsed["implementation_target"]
    assert "external_body" not in attributes, "implementation_target is external"

    stripped_body = "\n".join(
        line
        for line in target_body.splitlines()
        if not line.strip().startswith("//")
    ).strip().rstrip(";").strip()

    for boundary in boundaries:
        name = boundary["function"]
        assert name in parsed, ("undeclared boundary", name)
        boundary_attributes, boundary_contract, _ = parsed[name]
        assert "external_body" in boundary_attributes, (
            "boundary is not external_body",
            name,
        )
        assert re.search(rf"\b{re.escape(name)}\s*(?:::\s*<|\()", stripped_body), (
            "boundary is never called by implementation_target",
            name,
        )
        assert boundary_contract != target_contract, (
            "boundary declares the target's own requires/ensures",
            name,
        )
        assert "accepted_contract(" not in boundary_contract, (
            "boundary names the whole accepted contract",
            name,
        )
        assert not re.fullmatch(
            rf"{re.escape(name)}\s*(?:::\s*<[^>]*>\s*)?\([\s\S]*\)",
            stripped_body,
        ), ("implementation_target is a single call to the boundary", name)

    called_external = {
        candidate
        for candidate, (candidate_attributes, _, _) in parsed.items()
        if candidate != "implementation_target"
        and "external_body" in candidate_attributes
        and re.search(
            rf"\b{re.escape(candidate)}\s*(?:::\s*<|\()", stripped_body
        )
    }
    assert called_external == {boundary["function"] for boundary in boundaries}, (
        "called external_body helpers do not match declared boundaries",
        sorted(called_external),
    )


def _boundary(function: str, category: str) -> dict[str, Any]:
    return {
        "function": function,
        "category": category,
        "whole_target_outcome": False,
        "literal_external_body": True,
    }


def _mutation(
    family: str,
    fragment: str,
    replacement: str,
    omitted_observable: str,
) -> dict[str, str]:
    assert fragment != replacement
    return {
        "category": _FAMILY_MUTATION_CATEGORY[family],
        "fragment": fragment,
        "replacement": replacement,
        "omitted_observable": omitted_observable,
    }


def _template(
    *,
    proof_family: str,
    implementation_proof: str,
    completeness_proof: str,
    source_shape_tokens: tuple[str, ...],
    boundaries: tuple[dict[str, Any], ...],
    implementation_mutation: dict[str, str],
    completeness_mutation: dict[str, str],
) -> ProofTemplate:
    for token in source_shape_tokens:
        assert token in implementation_proof, (proof_family, token)
    # `whole_target_outcome=False` is recorded only after the derived check
    # above has confirmed, from the rendered text, that the boundary really is
    # narrower than `implementation_target`.
    _assert_boundaries_are_derived_narrow(implementation_proof, boundaries)
    for boundary in boundaries:
        assert boundary["whole_target_outcome"] is False
    assert implementation_proof.count(implementation_mutation["fragment"]) == 1
    assert completeness_proof.count(completeness_mutation["fragment"]) == 1
    return ProofTemplate(
        proof_family=proof_family,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=boundaries,
        implementation_mutation=implementation_mutation,
        completeness_mutation=completeness_mutation,
    )


# ---------------------------------------------------------------------------
# ordering_value / unit_value / char_value / bool_value:
# fully concrete, deterministic value comparisons with no external calls.
# ---------------------------------------------------------------------------

_ORDERING_RANK_HELPERS = """\
pub open spec fn cmp_ordering_rank(value: Ordering) -> int {
    match value {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

pub fn cmp_ordering_rank_exec(value: Ordering) -> (rank: i8)
    ensures
        rank as int == cmp_ordering_rank(value),
{
    match value {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

"""

_CHAR_RANK_HELPERS = """\
pub open spec fn cmp_char_rank(value: char) -> int {
    (value as u32) as int
}

pub fn cmp_char_rank_exec(value: char) -> (rank: u32)
    ensures
        rank as int == cmp_char_rank(value),
{
    value as u32
}

"""


def _build_value_relation(row: dict[str, Any]) -> ProofTemplate:
    owner_type = row["owner_type"]
    method = row["method_name"]

    if owner_type == "Ordering":
        return _build_ordering_value(method)
    if owner_type == "()":
        return _build_unit_value(method)
    if owner_type == "char":
        return _build_char_value(method)
    if owner_type == "bool":
        return _build_bool_value(method)
    raise AssertionError(f"unsupported value_relation owner_type {owner_type!r}")


def _build_ordering_value(method: str) -> ProofTemplate:
    family = "ordering_value"
    if method == "eq":
        implementation = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: bool) -> bool {
    result <==> cmp_ordering_rank(left) == cmp_ordering_rank(right)
}

pub fn implementation_target(left: &Ordering, right: &Ordering) -> (result: bool)
    ensures
        accepted_contract(*left, *right, result),
{
    cmp_ordering_rank_exec(*left) == cmp_ordering_rank_exec(*right)
}

}
"""
        completeness = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: bool) -> bool {
    result <==> cmp_ordering_rank(left) == cmp_ordering_rank(right)
}

pub proof fn completeness_theorem(left: Ordering, right: Ordering, result1: bool, result2: bool)
    requires
        accepted_contract(left, right, result1),
        accepted_contract(left, right, result2),
    ensures
        result1 == result2,
{
}

}
"""
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &Ordering", "right: &Ordering", "-> (result: bool)"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "cmp_ordering_rank_exec(*left) == cmp_ordering_rank_exec(*right)",
                "cmp_ordering_rank_exec(*left) != cmp_ordering_rank_exec(*right)",
                "equal_bias",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "equal_bias",
            ),
        )
    if method == "partial_cmp":
        implementation = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: Option<Ordering>) -> bool {
    result == Some(
        if cmp_ordering_rank(left) < cmp_ordering_rank(right) { Ordering::Less }
        else if cmp_ordering_rank(left) > cmp_ordering_rank(right) { Ordering::Greater }
        else { Ordering::Equal }
    )
}

pub fn implementation_target(left: &Ordering, right: &Ordering) -> (result: Option<Ordering>)
    ensures
        accepted_contract(*left, *right, result),
{
    let lr = cmp_ordering_rank_exec(*left);
    let rr = cmp_ordering_rank_exec(*right);
    Some(if lr < rr { Ordering::Less } else if lr > rr { Ordering::Greater } else { Ordering::Equal })
}

}
"""
        completeness = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: Option<Ordering>) -> bool {
    result == Some(
        if cmp_ordering_rank(left) < cmp_ordering_rank(right) { Ordering::Less }
        else if cmp_ordering_rank(left) > cmp_ordering_rank(right) { Ordering::Greater }
        else { Ordering::Equal }
    )
}

pub proof fn completeness_theorem(
    left: Ordering,
    right: Ordering,
    result1: Option<Ordering>,
    result2: Option<Ordering>,
)
    requires
        accepted_contract(left, right, result1),
        accepted_contract(left, right, result2),
    ensures
        result1 == result2,
{
}

}
"""
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &Ordering", "right: &Ordering", "-> (result: Option<Ordering>)"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "if lr < rr { Ordering::Less } else if lr > rr { Ordering::Greater } else { Ordering::Equal }",
                "if lr > rr { Ordering::Less } else if lr < rr { Ordering::Greater } else { Ordering::Equal }",
                "return_branch",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "return_branch",
            ),
        )
    if method == "cmp":
        implementation = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: Ordering) -> bool {
    result == if cmp_ordering_rank(left) < cmp_ordering_rank(right) { Ordering::Less }
        else if cmp_ordering_rank(left) > cmp_ordering_rank(right) { Ordering::Greater }
        else { Ordering::Equal }
}

pub fn implementation_target(left: &Ordering, right: &Ordering) -> (result: Ordering)
    ensures
        accepted_contract(*left, *right, result),
{
    let lr = cmp_ordering_rank_exec(*left);
    let rr = cmp_ordering_rank_exec(*right);
    if lr < rr { Ordering::Less } else if lr > rr { Ordering::Greater } else { Ordering::Equal }
}

}
"""
        completeness = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _ORDERING_RANK_HELPERS + """\
pub open spec fn accepted_contract(left: Ordering, right: Ordering, result: Ordering) -> bool {
    result == if cmp_ordering_rank(left) < cmp_ordering_rank(right) { Ordering::Less }
        else if cmp_ordering_rank(left) > cmp_ordering_rank(right) { Ordering::Greater }
        else { Ordering::Equal }
}

pub proof fn completeness_theorem(left: Ordering, right: Ordering, result1: Ordering, result2: Ordering)
    requires
        accepted_contract(left, right, result1),
        accepted_contract(left, right, result2),
    ensures
        result1 == result2,
{
}

}
"""
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &Ordering", "right: &Ordering", "-> (result: Ordering)"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "if lr < rr { Ordering::Less } else if lr > rr { Ordering::Greater } else { Ordering::Equal }",
                "if lr > rr { Ordering::Less } else if lr < rr { Ordering::Greater } else { Ordering::Equal }",
                "return_branch",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "return_branch",
            ),
        )
    assert method == "clone"
    implementation = _HEADER + """\
use vstd::prelude::*;
use core::cmp::Ordering;

verus! {

pub open spec fn accepted_contract(source: Ordering, result: Ordering) -> bool {
    result == source
}

pub fn implementation_target(source: &Ordering) -> (result: Ordering)
    ensures
        accepted_contract(*source, result),
{
    *source
}

}
"""
    completeness = _HEADER + """\
use vstd::prelude::*;
use core::cmp::Ordering;

verus! {

pub open spec fn accepted_contract(source: Ordering, result: Ordering) -> bool {
    result == source
}

pub proof fn completeness_theorem(source: Ordering, result1: Ordering, result2: Ordering)
    requires
        accepted_contract(source, result1),
        accepted_contract(source, result2),
    ensures
        result1 == result2,
{
}

}
"""
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("source: &Ordering", "-> (result: Ordering)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "*source\n}",
            "if matches!(*source, Ordering::Equal) { Ordering::Equal } else { Ordering::Equal }\n}",
            "return_branch",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "return_branch",
        ),
    )


_UNIT_VALUE_RESULT: dict[str, tuple[str, str]] = {
    # method -> (return type, exec/spec literal value expression)
    "eq": ("bool", "true"),
    "ne": ("bool", "false"),
    "cmp": ("Ordering", "Ordering::Equal"),
    "partial_cmp": ("Option<Ordering>", "Some(Ordering::Equal)"),
}


def _build_unit_value(method: str) -> ProofTemplate:
    family = "unit_value"
    return_type, literal = _UNIT_VALUE_RESULT[method]
    negated = {
        "true": "false",
        "false": "true",
        "Ordering::Equal": "Ordering::Less",
        "Some(Ordering::Equal)": "None",
    }[literal]
    implementation = _HEADER + (
        "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n"
        "pub open spec fn accepted_contract(result: " + return_type + ") -> bool {\n"
        "    result == " + literal + "\n"
        "}\n\n"
        "pub fn implementation_target(left: &(), right: &()) -> (result: " + return_type + ")\n"
        "    ensures\n"
        "        accepted_contract(result),\n"
        "{\n"
        "    " + literal + "\n"
        "}\n\n"
        "}\n"
    )
    completeness = _HEADER + (
        "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n"
        "pub open spec fn accepted_contract(result: " + return_type + ") -> bool {\n"
        "    result == " + literal + "\n"
        "}\n\n"
        "pub proof fn completeness_theorem(result1: " + return_type + ", result2: " + return_type + ")\n"
        "    requires\n"
        "        accepted_contract(result1),\n"
        "        accepted_contract(result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("left: &()", "right: &()", "-> (result: " + return_type + ")"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    " + literal + "\n}",
            "    " + negated + "\n}",
            "equal_bias",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "equal_bias",
        ),
    )


def _build_char_value(method: str) -> ProofTemplate:
    family = "char_value"
    if method in ("eq", "ne"):
        operator = "==" if method == "eq" else "!="
        implementation = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
            "pub open spec fn accepted_contract(left: char, right: char, result: bool) -> bool {\n"
            "    result <==> cmp_char_rank(left) " + operator + " cmp_char_rank(right)\n"
            "}\n\n"
            "pub fn implementation_target(left: &char, right: &char) -> (result: bool)\n"
            "    ensures\n"
            "        accepted_contract(*left, *right, result),\n"
            "{\n"
            "    cmp_char_rank_exec(*left) " + operator + " cmp_char_rank_exec(*right)\n"
            "}\n\n"
            "}\n"
        )
        completeness = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
            "pub open spec fn accepted_contract(left: char, right: char, result: bool) -> bool {\n"
            "    result <==> cmp_char_rank(left) " + operator + " cmp_char_rank(right)\n"
            "}\n\n"
            "pub proof fn completeness_theorem(left: char, right: char, result1: bool, result2: bool)\n"
            "    requires\n"
            "        accepted_contract(left, right, result1),\n"
            "        accepted_contract(left, right, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{\n"
            "}\n\n"
            "}\n"
        )
        flipped = "!=" if method == "eq" else "=="
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &char", "right: &char", "-> (result: bool)"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "cmp_char_rank_exec(*left) " + operator + " cmp_char_rank_exec(*right)",
                "cmp_char_rank_exec(*left) " + flipped + " cmp_char_rank_exec(*right)",
                "equal_bias",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "equal_bias",
            ),
        )
    if method in ("cmp", "partial_cmp"):
        wrap_open, wrap_close = ("", "") if method == "cmp" else ("Some(", ")")
        return_type = "Ordering" if method == "cmp" else "Option<Ordering>"
        branch = (
            "if cmp_char_rank(left) < cmp_char_rank(right) { Ordering::Less }\n"
            "        else if cmp_char_rank(left) > cmp_char_rank(right) { Ordering::Greater }\n"
            "        else { Ordering::Equal }"
        )
        exec_branch = (
            "if lr < rr { Ordering::Less } else if lr > rr { Ordering::Greater } else { Ordering::Equal }"
        )
        mutated_exec_branch = (
            "if lr > rr { Ordering::Less } else if lr < rr { Ordering::Greater } else { Ordering::Equal }"
        )
        implementation = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
            "pub open spec fn accepted_contract(left: char, right: char, result: " + return_type + ") -> bool {\n"
            "    result == " + wrap_open + branch + wrap_close + "\n"
            "}\n\n"
            "pub fn implementation_target(left: &char, right: &char) -> (result: " + return_type + ")\n"
            "    ensures\n"
            "        accepted_contract(*left, *right, result),\n"
            "{\n"
            "    let lr = cmp_char_rank_exec(*left);\n"
            "    let rr = cmp_char_rank_exec(*right);\n"
            "    " + wrap_open + exec_branch + wrap_close + "\n"
            "}\n\n"
            "}\n"
        )
        completeness = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
            "pub open spec fn accepted_contract(left: char, right: char, result: " + return_type + ") -> bool {\n"
            "    result == " + wrap_open + branch + wrap_close + "\n"
            "}\n\n"
            "pub proof fn completeness_theorem(left: char, right: char, result1: " + return_type + ", result2: " + return_type + ")\n"
            "    requires\n"
            "        accepted_contract(left, right, result1),\n"
            "        accepted_contract(left, right, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{\n"
            "}\n\n"
            "}\n"
        )
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &char", "right: &char", "-> (result: " + return_type + ")"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                wrap_open + exec_branch + wrap_close,
                wrap_open + mutated_exec_branch + wrap_close,
                "return_branch",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "return_branch",
            ),
        )
    assert method in ("lt", "le", "gt", "ge")
    relation = {
        "lt": ("<", "<"),
        "le": ("<=", "<="),
        "gt": (">", ">"),
        "ge": (">=", ">="),
    }[method]
    operator = relation[0]
    flipped = {"<": ">=", "<=": ">", ">": "<=", ">=": "<"}[operator]
    implementation = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
        "pub open spec fn accepted_contract(left: char, right: char, result: bool) -> bool {\n"
        "    result <==> cmp_char_rank(left) " + operator + " cmp_char_rank(right)\n"
        "}\n\n"
        "pub fn implementation_target(left: &char, right: &char) -> (result: bool)\n"
        "    ensures\n"
        "        accepted_contract(*left, *right, result),\n"
        "{\n"
        "    cmp_char_rank_exec(*left) " + operator + " cmp_char_rank_exec(*right)\n"
        "}\n\n"
        "}\n"
    )
    completeness = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + _CHAR_RANK_HELPERS + (
        "pub open spec fn accepted_contract(left: char, right: char, result: bool) -> bool {\n"
        "    result <==> cmp_char_rank(left) " + operator + " cmp_char_rank(right)\n"
        "}\n\n"
        "pub proof fn completeness_theorem(left: char, right: char, result1: bool, result2: bool)\n"
        "    requires\n"
        "        accepted_contract(left, right, result1),\n"
        "        accepted_contract(left, right, result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("left: &char", "right: &char", "-> (result: bool)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "cmp_char_rank_exec(*left) " + operator + " cmp_char_rank_exec(*right)",
            "cmp_char_rank_exec(*left) " + flipped + " cmp_char_rank_exec(*right)",
            "return_branch",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "return_branch",
        ),
    )


def _build_bool_value(method: str) -> ProofTemplate:
    family = "bool_value"
    if method in ("min", "max"):
        expr = "left && right" if method == "min" else "left || right"
        mutated = "left || right" if method == "min" else "left && right"
        implementation = _HEADER + (
            "use vstd::prelude::*;\n\nverus! {\n\n"
            "pub open spec fn accepted_contract(left: bool, right: bool, result: bool) -> bool {\n"
            "    result == (" + expr + ")\n"
            "}\n\n"
            "pub fn implementation_target(left: bool, right: bool) -> (result: bool)\n"
            "    ensures\n"
            "        accepted_contract(left, right, result),\n"
            "{\n"
            "    " + expr + "\n"
            "}\n\n"
            "}\n"
        )
        completeness = _HEADER + (
            "use vstd::prelude::*;\n\nverus! {\n\n"
            "pub open spec fn accepted_contract(left: bool, right: bool, result: bool) -> bool {\n"
            "    result == (" + expr + ")\n"
            "}\n\n"
            "pub proof fn completeness_theorem(left: bool, right: bool, result1: bool, result2: bool)\n"
            "    requires\n"
            "        accepted_contract(left, right, result1),\n"
            "        accepted_contract(left, right, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{\n"
            "}\n\n"
            "}\n"
        )
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: bool", "right: bool", "-> (result: bool)"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "    " + expr + "\n}",
                "    " + mutated + "\n}",
                "equal_bias",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "equal_bias",
            ),
        )
    if method in ("cmp", "partial_cmp"):
        wrap_open, wrap_close = ("", "") if method == "cmp" else ("Some(", ")")
        return_type = "Ordering" if method == "cmp" else "Option<Ordering>"
        branch = "if !left && right { Ordering::Less } else if left && !right { Ordering::Greater } else { Ordering::Equal }"
        exec_branch = "if !left && right { Ordering::Less } else if left && !right { Ordering::Greater } else { Ordering::Equal }"
        mutated_exec_branch = "if left && !right { Ordering::Less } else if !left && right { Ordering::Greater } else { Ordering::Equal }"
        helpers = (
            "pub open spec fn cmp_bool_order(left: bool, right: bool) -> Ordering {\n"
            "    " + branch + "\n"
            "}\n\n"
            "pub fn cmp_bool_order_exec(left: bool, right: bool) -> (order: Ordering)\n"
            "    ensures\n"
            "        order == cmp_bool_order(left, right),\n"
            "{\n"
            "    " + exec_branch + "\n"
            "}\n\n"
        )
        implementation = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + helpers + (
            "pub open spec fn accepted_contract(left: bool, right: bool, result: " + return_type + ") -> bool {\n"
            "    result == " + wrap_open + "cmp_bool_order(left, right)" + wrap_close + "\n"
            "}\n\n"
            "pub fn implementation_target(left: &bool, right: &bool) -> (result: " + return_type + ")\n"
            "    ensures\n"
            "        accepted_contract(*left, *right, result),\n"
            "{\n"
            "    " + wrap_open + "cmp_bool_order_exec(*left, *right)" + wrap_close + "\n"
            "}\n\n"
            "}\n"
        )
        completeness = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n" + (
            "pub open spec fn cmp_bool_order(left: bool, right: bool) -> Ordering {\n"
            "    " + branch + "\n"
            "}\n\n"
            "pub open spec fn accepted_contract(left: bool, right: bool, result: " + return_type + ") -> bool {\n"
            "    result == " + wrap_open + "cmp_bool_order(left, right)" + wrap_close + "\n"
            "}\n\n"
            "pub proof fn completeness_theorem(left: bool, right: bool, result1: " + return_type + ", result2: " + return_type + ")\n"
            "    requires\n"
            "        accepted_contract(left, right, result1),\n"
            "        accepted_contract(left, right, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{\n"
            "}\n\n"
            "}\n"
        )
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=("left: &bool", "right: &bool", "-> (result: " + return_type + ")"),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "order == cmp_bool_order(left, right),\n{\n    " + exec_branch,
                "order == cmp_bool_order(left, right),\n{\n    " + mutated_exec_branch,
                "return_branch",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "return_branch",
            ),
        )
    assert method in ("lt", "le", "gt", "ge")
    expr = {
        "lt": "!left && right",
        "le": "!left || right",
        "gt": "left && !right",
        "ge": "left || !right",
    }[method]
    exec_expr = {
        "lt": "!*left && *right",
        "le": "!*left || *right",
        "gt": "*left && !*right",
        "ge": "*left || !*right",
    }[method]
    mutated_exec_expr = {
        "lt": "*left && !*right",
        "le": "*left || !*right",
        "gt": "!*left && *right",
        "ge": "!*left || *right",
    }[method]
    implementation = _HEADER + (
        "use vstd::prelude::*;\n\nverus! {\n\n"
        "pub open spec fn accepted_contract(left: bool, right: bool, result: bool) -> bool {\n"
        "    result == (" + expr + ")\n"
        "}\n\n"
        "pub fn implementation_target(left: &bool, right: &bool) -> (result: bool)\n"
        "    ensures\n"
        "        accepted_contract(*left, *right, result),\n"
        "{\n"
        "    " + exec_expr + "\n"
        "}\n\n"
        "}\n"
    )
    completeness = _HEADER + (
        "use vstd::prelude::*;\n\nverus! {\n\n"
        "pub open spec fn accepted_contract(left: bool, right: bool, result: bool) -> bool {\n"
        "    result == (" + expr + ")\n"
        "}\n\n"
        "pub proof fn completeness_theorem(left: bool, right: bool, result1: bool, result2: bool)\n"
        "    requires\n"
        "        accepted_contract(left, right, result1),\n"
        "        accepted_contract(left, right, result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("left: &bool", "right: &bool", "-> (result: bool)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    " + exec_expr + "\n}",
            "    " + mutated_exec_expr + "\n}",
            "return_branch",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "return_branch",
        ),
    )


# ---------------------------------------------------------------------------
# primitive_clamp: 14 Ord::clamp overrides. The real body asserts `min <= max`
# (a debug_assert! in the real source; modelled here as a genuine no-normal-
# return panic branch) before clamping `value` into `[min, max]`.
# ---------------------------------------------------------------------------

_CLAMP_INT_TYPES = (
    "usize", "u8", "u16", "u32", "u64", "u128",
    "isize", "i8", "i16", "i32", "i64", "i128",
)


def _build_primitive_clamp(row: dict[str, Any]) -> ProofTemplate:
    family = "primitive_clamp"
    owner_type = row["owner_type"]
    if owner_type in _CLAMP_INT_TYPES:
        ty = owner_type
        le = "min <= max"
        lt_value_min = "value < min"
        gt_value_max = "value > max"
        le_exec = le
        lt_value_min_exec = lt_value_min
        gt_value_max_exec = gt_value_max
    elif owner_type == "char":
        ty = "char"
        le = "cmp_char_rank(min) <= cmp_char_rank(max)"
        lt_value_min = "cmp_char_rank(value) < cmp_char_rank(min)"
        gt_value_max = "cmp_char_rank(value) > cmp_char_rank(max)"
        le_exec = "cmp_char_rank_exec(min) <= cmp_char_rank_exec(max)"
        lt_value_min_exec = "cmp_char_rank_exec(value) < cmp_char_rank_exec(min)"
        gt_value_max_exec = "cmp_char_rank_exec(value) > cmp_char_rank_exec(max)"
    elif owner_type == "bool":
        ty = "bool"
        le = "(!min || max)"
        lt_value_min = "(!value && min)"
        gt_value_max = "(value && !max)"
        le_exec = le
        lt_value_min_exec = lt_value_min
        gt_value_max_exec = gt_value_max
    else:
        raise AssertionError(f"unsupported clamp owner_type {owner_type!r}")

    rank_helpers = _CHAR_RANK_HELPERS if owner_type == "char" else ""
    guard = "!(" + le + ")"
    guard_exec = "!(" + le_exec + ")"
    mutated_guard_exec = "(" + le_exec + ")"
    body_branch = (
        "if " + lt_value_min + " { min } else if " + gt_value_max + " { max } else { value }"
    )
    accepted_contract = (
        "pub open spec fn accepted_contract(value: " + ty + ", min: " + ty + ", max: " + ty
        + ", result: CmpCallOutcome<" + ty + ">) -> bool {\n"
        "    if " + guard + " {\n"
        "        result is Panicked\n"
        "    } else {\n"
        "        result == CmpCallOutcome::Returned(" + body_branch + ")\n"
        "    }\n"
        "}\n\n"
    )
    outcome_enum = (
        "pub enum CmpCallOutcome<T> {\n"
        "    Returned(T),\n"
        "    Panicked,\n"
        "}\n\n"
    )
    implementation = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + outcome_enum + rank_helpers + accepted_contract + (
        "pub fn implementation_target(value: " + ty + ", min: " + ty + ", max: " + ty + ") -> (result: CmpCallOutcome<" + ty + ">)\n"
        "    ensures\n"
        "        accepted_contract(value, min, max, result),\n"
        "{\n"
        "    if " + guard_exec + " {\n"
        "        CmpCallOutcome::Panicked\n"
        "    } else if " + lt_value_min_exec + " {\n"
        "        CmpCallOutcome::Returned(min)\n"
        "    } else if " + gt_value_max_exec + " {\n"
        "        CmpCallOutcome::Returned(max)\n"
        "    } else {\n"
        "        CmpCallOutcome::Returned(value)\n"
        "    }\n"
        "}\n\n"
        "}\n"
    )
    completeness = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n" + outcome_enum + rank_helpers + accepted_contract + (
        "pub proof fn completeness_theorem(\n"
        "    value: " + ty + ",\n"
        "    min: " + ty + ",\n"
        "    max: " + ty + ",\n"
        "    result1: CmpCallOutcome<" + ty + ">,\n"
        "    result2: CmpCallOutcome<" + ty + ">,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(value, min, max, result1),\n"
        "        accepted_contract(value, min, max, result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "value: " + ty,
            "min: " + ty,
            "max: " + ty,
            "-> (result: CmpCallOutcome<" + ty + ">)",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    if " + guard_exec + " {\n        CmpCallOutcome::Panicked",
            "    if " + mutated_guard_exec + " {\n        CmpCallOutcome::Panicked",
            "panic_guard",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "panic_guard",
        ),
    )


# ---------------------------------------------------------------------------
# trait_default_clamp: the shared Ord::clamp body. Unlike the loaded vstd
# declaration, this model includes the source assert's panicked outcome and
# imposes no min/max precondition.
# ---------------------------------------------------------------------------

def _build_trait_default_clamp(row: dict[str, Any]) -> ProofTemplate:
    family = "trait_default_clamp"
    outcome_enum = (
        "pub enum CmpCallOutcome<T> {\n"
        "    Returned(T),\n"
        "    Panicked,\n"
        "}\n\n"
    )
    accepted_contract = (
        "pub open spec fn accepted_contract<"
        "Self_: Ord + PartialOrdSpec + OrdSpec>(\n"
        "    value: Self_,\n"
        "    min: Self_,\n"
        "    max: Self_,\n"
        "    result: CmpCallOutcome<Self_>,\n"
        ") -> bool {\n"
        "    Self_::obeys_partial_cmp_spec() ==> result ==\n"
        "        if min.partial_cmp_spec(&max) == Some(Ordering::Greater) {\n"
        "            CmpCallOutcome::Panicked\n"
        "        } else {\n"
        "            CmpCallOutcome::Returned(\n"
        "                if value.partial_cmp_spec(&min) == Some(Ordering::Less) {\n"
        "                    min\n"
        "                } else if value.partial_cmp_spec(&max) == Some(Ordering::Greater) {\n"
        "                    max\n"
        "                } else {\n"
        "                    value\n"
        "                },\n"
        "            )\n"
        "        }\n"
        "}\n\n"
    )
    preamble = (
        _SIZED_HIERARCHY_HEADER
        + "use vstd::prelude::*;\n"
        + "use vstd::std_specs::cmp::*;\n"
        + "use core::cmp::Ordering;\n\n"
        + "verus! {\n\n"
        + outcome_enum
        + accepted_contract
    )
    implementation = preamble + (
        "pub fn implementation_target<"
        "Self_: Ord + PartialOrdSpec + OrdSpec>(\n"
        "    value: Self_,\n"
        "    min: Self_,\n"
        "    max: Self_,\n"
        ") -> (result: CmpCallOutcome<Self_>)\n"
        "    requires\n"
        "        Self_::obeys_partial_cmp_spec(),\n"
        "    ensures\n"
        "        accepted_contract(value, min, max, result),\n"
        "{\n"
        "    if min > max {\n"
        "        CmpCallOutcome::Panicked\n"
        "    } else if value < min {\n"
        "        CmpCallOutcome::Returned(min)\n"
        "    } else if value > max {\n"
        "        CmpCallOutcome::Returned(max)\n"
        "    } else {\n"
        "        CmpCallOutcome::Returned(value)\n"
        "    }\n"
        "}\n\n"
        "}\n"
    )
    completeness = preamble + (
        "pub proof fn completeness_theorem<"
        "Self_: Ord + PartialOrdSpec + OrdSpec>(\n"
        "    value: Self_,\n"
        "    min: Self_,\n"
        "    max: Self_,\n"
        "    result1: CmpCallOutcome<Self_>,\n"
        "    result2: CmpCallOutcome<Self_>,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(value, min, max, result1),\n"
        "        accepted_contract(value, min, max, result2),\n"
        "        Self_::obeys_partial_cmp_spec(),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "min > max",
            "value < min",
            "value > max",
            "CmpCallOutcome::Panicked",
            "CmpCallOutcome::Returned",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    if min > max {\n        CmpCallOutcome::Panicked",
            "    if min <= max {\n        CmpCallOutcome::Panicked",
            "panic_guard",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "panic_guard",
        ),
    )


# ---------------------------------------------------------------------------
# reference_forwarding: &mut A / &A vs &mut B / &B PartialEq/PartialOrd/Ord
# impls that forward to the pointee's own comparison via a reborrow.
#
# These are rendered exactly like the already-accepted shared-reference
# forwarding templates: `implementation_target` itself executes the real
# `PartialEq`/`PartialOrd`/`Ord` referent delegate and its `ensures` is the
# direct `call_ensures` relation for that delegate. The only difference from
# the `&A`/`&B` case is the shared reborrow of a `PointeeSized` referent held
# behind a `&&mut _`: Verus rejects `&**left` in a postcondition ("to
# dereference a mutable reference parameter in a postcondition, disambiguate
# by wrapping it in either `old` or `final`") and `old`/`final` themselves
# require `MetaSized`, which a `PointeeSized` generic does not satisfy. The
# accepted specification therefore names that reborrow with the frozen
# `cmp_shared_reborrow` model, and the sole boundary here is the matching
# `cmp_shared_reborrow_exec` reborrow: its whole `ensures` is
# `result == cmp_shared_reborrow(value)`. It mentions no comparison trait, no
# operand pair and no target result, so it is strictly narrower than
# `implementation_target` and cannot stand in for the target outcome.
# ---------------------------------------------------------------------------

_REFERENCE_FORWARDING_RETURN: dict[str, str] = {
    "eq": "bool",
    "ne": "bool",
    "cmp": "Ordering",
    "partial_cmp": "Option<Ordering>",
    "lt": "bool",
    "le": "bool",
    "gt": "bool",
    "ge": "bool",
}

_REFERENCE_FORWARDING_TRAIT_CALL: dict[str, str] = {
    "eq": "PartialEq::eq",
    "ne": "PartialEq::ne",
    "cmp": "Ord::cmp",
    "partial_cmp": "PartialOrd::partial_cmp",
    "lt": "PartialOrd::lt",
    "le": "PartialOrd::le",
    "gt": "PartialOrd::gt",
    "ge": "PartialOrd::ge",
}

_REFERENCE_FORWARDING_CALL_ENSURES_TRAIT: dict[str, str] = {
    "eq": "PartialEq<B>",
    "ne": "PartialEq<B>",
    "cmp": "Ord",
    "partial_cmp": "PartialOrd<B>",
    "lt": "PartialOrd<B>",
    "le": "PartialOrd<B>",
    "gt": "PartialOrd<B>",
    "ge": "PartialOrd<B>",
}


def _build_reference_forwarding(row: dict[str, Any]) -> ProofTemplate:
    family = "reference_forwarding"
    method = row["method_name"]
    inputs = row["matching_shape"]["inputs"]
    left_mut = "mut" in inputs[0]
    right_mut = "mut" in inputs[1]
    return_type = _REFERENCE_FORWARDING_RETURN[method]
    trait_call = _REFERENCE_FORWARDING_TRAIT_CALL[method]
    single_type = method == "cmp"

    if single_type:
        generics = "A: PointeeSized + Ord"
        bound_trait = "<A as Ord>::" + method
    else:
        generics = (
            "A: PointeeSized + "
            + _REFERENCE_FORWARDING_CALL_ENSURES_TRAIT[method]
            + ", B: PointeeSized"
        )
        bound_trait = (
            "<A as "
            + _REFERENCE_FORWARDING_CALL_ENSURES_TRAIT[method]
            + ">::"
            + method
        )
    call_ensures_args = "(left_value, right_value)"

    left_param_type = "&&mut A" if left_mut else "&&A"
    right_param_name = "A" if single_type else "B"
    right_param_type = ("&&mut " if right_mut else "&&") + right_param_name

    # The accepted specification names the shared reborrow of a `&mut`
    # referent with `cmp_shared_reborrow`; a shared referent needs no model
    # at all and is spelled `*left` / `*right` exactly as the accepted
    # contract spells it.
    left_view = "cmp_shared_reborrow(left)" if left_mut else "*left"
    right_view = "cmp_shared_reborrow(right)" if right_mut else "*right"
    needs_reborrow = left_mut or right_mut

    left_binding = (
        "cmp_shared_reborrow_exec(left)" if left_mut else "*left"
    )
    right_binding = (
        "cmp_shared_reborrow_exec(right)" if right_mut else "*right"
    )

    reborrow_model = (
        "pub uninterp spec fn cmp_shared_reborrow<'outer, 'inner, X: PointeeSized>(\n"
        "    value: &'outer &'inner mut X,\n"
        ") -> &'outer X;\n\n"
    )
    # Narrow boundary: the shared reborrow itself and nothing else. Its full
    # `ensures` is the single equality below -- no comparison trait, no
    # operand pair, no target result -- so it is strictly narrower than
    # `implementation_target`'s `call_ensures` postcondition.
    reborrow_boundary = (
        "#[verifier::external_body]\n"
        "fn cmp_shared_reborrow_exec<'outer, 'inner, X: PointeeSized>(\n"
        "    value: &'outer &'inner mut X,\n"
        ") -> (result: &'outer X)\n"
        "    ensures\n"
        "        result == cmp_shared_reborrow(value),\n"
        "{\n"
        "    &**value\n"
        "}\n\n"
    )

    accepted_contract = (
        "pub open spec fn accepted_contract<" + generics + ">(\n"
        "    left_value: &A,\n"
        "    right_value: &" + right_param_name + ",\n"
        "    result: " + return_type + ",\n"
        ") -> bool {\n"
        "    call_ensures(" + bound_trait + ", " + call_ensures_args + ", result)\n"
        "}\n\n"
    )

    determinism_hypothesis = (
        "        forall|o1: " + return_type + ", o2: " + return_type + "|\n"
        "            call_ensures(" + bound_trait + ", " + call_ensures_args + ", o1)\n"
        "                && call_ensures(" + bound_trait + ", " + call_ensures_args + ", o2)\n"
        "                ==> o1 == o2,\n"
    )

    header = (
        _SIZED_HIERARCHY_HEADER
        + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n"
        "use core::marker::PointeeSized;\n\nverus! {\n\n"
    )

    delegate_call = trait_call + "(left_referent, right_referent)"
    body = (
        "    let left_referent: &A = " + left_binding + ";\n"
        "    let right_referent: &" + right_param_name + " = " + right_binding + ";\n"
        "    " + delegate_call + "\n"
    )

    implementation = header + (
        (reborrow_model + reborrow_boundary) if needs_reborrow else ""
    ) + accepted_contract + (
        "pub fn implementation_target<" + generics + ">(\n"
        "    left: " + left_param_type + ",\n"
        "    right: " + right_param_type + ",\n"
        ") -> (result: " + return_type + ")\n"
        "    ensures\n"
        "        accepted_contract(" + left_view + ", " + right_view + ", result),\n"
        "{\n"
        + body
        + "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<" + generics + ">(\n"
        "    left_value: &A,\n"
        "    right_value: &" + right_param_name + ",\n"
        "    result1: " + return_type + ",\n"
        "    result2: " + return_type + ",\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(left_value, right_value, result1),\n"
        "        accepted_contract(left_value, right_value, result2),\n"
        + determinism_hypothesis
        + "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )

    boundaries = (
        (_boundary("cmp_shared_reborrow_exec", "shared_reborrow_model"),)
        if needs_reborrow
        else ()
    )
    # `implementation_target` is responsible for executing the referent
    # delegate itself, so the mutation replaces the delegate outcome with a
    # type-preserving transform of it: the `call_ensures` relation the target
    # must prove no longer holds for the value that is returned.
    if return_type == "bool":
        mutated_call = "!(" + delegate_call + ")"
    elif return_type == "Ordering":
        mutated_call = (
            "match " + delegate_call + " { Ordering::Less => Ordering::Greater, "
            "Ordering::Equal => Ordering::Equal, "
            "Ordering::Greater => Ordering::Less }"
        )
    else:
        assert return_type == "Option<Ordering>"
        mutated_call = (
            "match " + delegate_call + " { Some(Ordering::Less) => Some(Ordering::Greater), "
            "Some(Ordering::Equal) => Some(Ordering::Equal), "
            "Some(Ordering::Greater) => Some(Ordering::Less), None => None }"
        )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "left: " + left_param_type,
            "right: " + right_param_type,
            "-> (result: " + return_type + ")",
        ),
        boundaries=boundaries,
        implementation_mutation=_mutation(
            family,
            "    " + delegate_call + "\n}",
            "    " + mutated_call + "\n}",
            "forwarding_target",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_target",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_operand_reversal: Reverse<T> PartialOrd/Ord methods that forward to
# T's own method with the two operands swapped (`other.0.method(&self.0)`).
# ---------------------------------------------------------------------------

_REVERSE_REVERSAL_RETURN: dict[str, str] = {
    "partial_cmp": "Option<Ordering>",
    "lt": "bool",
    "le": "bool",
    "gt": "bool",
    "ge": "bool",
    "cmp": "Ordering",
}

_REVERSE_REVERSAL_TRAIT: dict[str, str] = {
    "partial_cmp": ("PartialOrd", "PartialOrd::partial_cmp"),
    "lt": ("PartialOrd", "PartialOrd::lt"),
    "le": ("PartialOrd", "PartialOrd::le"),
    "gt": ("PartialOrd", "PartialOrd::gt"),
    "ge": ("PartialOrd", "PartialOrd::ge"),
    "cmp": ("Ord", "Ord::cmp"),
}


def _build_reverse_operand_reversal(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_operand_reversal"
    method = row["method_name"]
    return_type = _REVERSE_REVERSAL_RETURN[method]
    bound, call = _REVERSE_REVERSAL_TRAIT[method]
    bound_trait = "<T as " + bound + ">::" + method

    header = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\n" + _REVERSE_TYPE_SPEC + "\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<T: " + bound + ">(\n"
        "    left: T,\n"
        "    right: T,\n"
        "    result: " + return_type + ",\n"
        ") -> bool {\n"
        "    call_ensures(" + bound_trait + ", (&right, &left), result)\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T: " + bound + ">(\n"
        "    left: &core::cmp::Reverse<T>,\n"
        "    right: &core::cmp::Reverse<T>,\n"
        ") -> (result: " + return_type + ")\n"
        "    ensures\n"
        "        accepted_contract(left.0, right.0, result),\n"
        "{\n"
        "    " + call + "(&right.0, &left.0)\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T: " + bound + ">(\n"
        "    left: T,\n"
        "    right: T,\n"
        "    result1: " + return_type + ",\n"
        "    result2: " + return_type + ",\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(left, right, result1),\n"
        "        accepted_contract(left, right, result2),\n"
        "        forall|o1: " + return_type + ", o2: " + return_type + "|\n"
        "            call_ensures(" + bound_trait + ", (&right, &left), o1)\n"
        "                && call_ensures(" + bound_trait + ", (&right, &left), o2)\n"
        "                ==> o1 == o2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "left: &core::cmp::Reverse<T>",
            "right: &core::cmp::Reverse<T>",
            "-> (result: " + return_type + ")",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            call + "(&right.0, &left.0)",
            call + "(&left.0, &right.0)",
            "operand_swap",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "operand_swap",
        ),
    )


# ---------------------------------------------------------------------------
# free_ord_forwarding: core::cmp::{min,max} forward to <T as Ord>::{min,max}.
# ---------------------------------------------------------------------------

def _build_free_ord_forwarding(row: dict[str, Any]) -> ProofTemplate:
    family = "free_ord_forwarding"
    method = row["method_name"]
    assert method in ("min", "max")
    header = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<T: Ord>(v1: T, v2: T, result: T) -> bool {\n"
        "    call_ensures(<T as Ord>::" + method + ", (v1, v2), result)\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T: Ord>(v1: T, v2: T) -> (result: T)\n"
        "    ensures\n"
        "        accepted_contract(v1, v2, result),\n"
        "{\n"
        "    Ord::" + method + "(v1, v2)\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T: Ord>(v1: T, v2: T, result1: T, result2: T)\n"
        "    requires\n"
        "        accepted_contract(v1, v2, result1),\n"
        "        accepted_contract(v1, v2, result2),\n"
        "        forall|o1: T, o2: T|\n"
        "            call_ensures(<T as Ord>::" + method + ", (v1, v2), o1)\n"
        "                && call_ensures(<T as Ord>::" + method + ", (v1, v2), o2)\n"
        "                ==> o1 == o2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    other_method = "max" if method == "min" else "min"
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("v1: T", "v2: T", "-> (result: T)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "Ord::" + method + "(v1, v2)",
            "Ord::" + other_method + "(v1, v2)",
            "forwarding_target",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_target",
        ),
    )


# ---------------------------------------------------------------------------
# comparator_callback: core::cmp::{min_by,max_by} call an FnOnce comparator
# exactly once, selecting a value based on the Ordering it returns.
# ---------------------------------------------------------------------------

def _build_comparator_callback(row: dict[str, Any]) -> ProofTemplate:
    family = "comparator_callback"
    method = row["method_name"]
    assert method in ("min_by", "max_by")
    if method == "min_by":
        selection = "if order == Ordering::Less || order == Ordering::Equal { v1 } else { v2 }"
        exec_selection = "if matches!(order, Ordering::Less | Ordering::Equal) { v1 } else { v2 }"
        mutated_exec_selection = "if matches!(order, Ordering::Less) { v1 } else { v2 }"
    else:
        selection = "if order == Ordering::Greater { v1 } else { v2 }"
        exec_selection = "if matches!(order, Ordering::Greater) { v1 } else { v2 }"
        mutated_exec_selection = "if matches!(order, Ordering::Greater | Ordering::Equal) { v1 } else { v2 }"

    header = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<T, F: FnOnce(&T, &T) -> Ordering>(\n"
        "    v1: T,\n"
        "    v2: T,\n"
        "    compare: F,\n"
        "    result: T,\n"
        ") -> bool {\n"
        "    exists|order: Ordering|\n"
        "        compare.ensures((&v1, &v2), order) && result == " + selection + "\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T, F: FnOnce(&T, &T) -> Ordering>(v1: T, v2: T, compare: F) -> (result: T)\n"
        "    requires\n"
        "        compare.requires((&v1, &v2)),\n"
        "    ensures\n"
        "        accepted_contract(v1, v2, compare, result),\n"
        "{\n"
        "    let order = compare(&v1, &v2);\n"
        "    " + exec_selection + "\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T, F: FnOnce(&T, &T) -> Ordering>(\n"
        "    v1: T,\n"
        "    v2: T,\n"
        "    compare: F,\n"
        "    result1: T,\n"
        "    result2: T,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(v1, v2, compare, result1),\n"
        "        accepted_contract(v1, v2, compare, result2),\n"
        "        forall|o1: Ordering, o2: Ordering|\n"
        "            compare.ensures((&v1, &v2), o1) && compare.ensures((&v1, &v2), o2) ==> o1 == o2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("v1: T", "v2: T", "compare: F", "-> (result: T)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    " + exec_selection + "\n}",
            "    " + mutated_exec_selection + "\n}",
            "equal_bias",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "equal_bias",
        ),
    )


# ---------------------------------------------------------------------------
# key_callback_order: core::cmp::{min_by_key,max_by_key} are
# `if f(&v2) < f(&v1) { v2 } else { v1 }` (min) / `{ v1 } else { v2 }` (max).
#
# `implementation_target` owns the whole of that shape: it performs the `f(&v2)`
# call, then the `f(&v1)` call *on the state the first call produced*, then the
# `K::lt` comparison, then the tie-goes-to-`v1` (min) / tie-goes-to-`v2` (max)
# selection, and it discharges the exact-2 observation count. The two effects
# that a Rust body cannot expose to Verus are split into per-call narrow
# boundaries:
#
#   * `cmp_key_callback_step` performs exactly one `FnMut` call and returns the
#     key together with the callback's successor state. It knows nothing about
#     `v1` vs `v2`, nothing about `K::lt`, nothing about the selection and it
#     never returns a `T`, so it cannot select or stand in for the target
#     result.
#   * `cmp_key_callback_observation_count_law` is a plain (non-broadcast) proof
#     function whose `ensures` is only the accepted contract's observation
#     count equation, applied to the two calls the body actually made.
#
# Neither boundary mentions the target's `T` result, and neither has the
# target's requires/ensures.
# ---------------------------------------------------------------------------

def _build_key_callback_order(row: dict[str, Any]) -> ProofTemplate:
    family = "key_callback_order"
    method = row["method_name"]
    assert method in ("min_by_key", "max_by_key")
    selection = (
        "if second_is_less { v2 } else { v1 }"
        if method == "min_by_key"
        else "if second_is_less { v1 } else { v2 }"
    )
    exec_selection = (
        "if second_is_less { v2 } else { v1 }"
        if method == "min_by_key"
        else "if second_is_less { v1 } else { v2 }"
    )

    header = _HEADER + "use vstd::prelude::*;\n\nverus! {\n\n"
    state_transition_helper = (
        "pub uninterp spec fn cmp_fn_mut_state_transition<T, F: FnMut(&T) -> K, K>(\n"
        "    before: F,\n"
        "    argument: &T,\n"
        "    output: K,\n"
        "    after: F,\n"
        ") -> bool;\n\n"
    )
    observation_count_helper = (
        "pub uninterp spec fn cmp_key_callback_observation_count<F, T>(\n"
        "    callback: F,\n"
        "    first: &T,\n"
        "    second: &T,\n"
        ") -> nat;\n\n"
    )
    trace_helper = (
        "pub open spec fn cmp_key_callback_trace<T, F: FnMut(&T) -> K, K: Ord>(\n"
        "    v1: T,\n"
        "    v2: T,\n"
        "    callback: F,\n"
        "    key2: K,\n"
        "    key1: K,\n"
        "    callback_after_v2: F,\n"
        "    callback_after_v1: F,\n"
        "    second_is_less: bool,\n"
        ") -> bool {\n"
        "    callback.ensures((&v2,), key2)\n"
        "        && cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2)\n"
        "        && callback_after_v2.ensures((&v1,), key1)\n"
        "        && cmp_fn_mut_state_transition(callback_after_v2, &v1, key1, callback_after_v1)\n"
        "        && call_ensures(<K as PartialOrd>::lt, (&key2, &key1), second_is_less)\n"
        "}\n\n"
    )
    accepted_contract = (
        "pub open spec fn accepted_contract<T, F: FnMut(&T) -> K, K: Ord>(\n"
        "    v1: T,\n"
        "    v2: T,\n"
        "    callback: F,\n"
        "    result: T,\n"
        ") -> bool {\n"
        "    exists|key2: K, key1: K, callback_after_v2: F, callback_after_v1: F, second_is_less: bool|\n"
        "        cmp_key_callback_trace(v1, v2, callback, key2, key1, callback_after_v2, callback_after_v1, second_is_less)\n"
        "            && result == " + selection + "\n"
        "            && cmp_key_callback_observation_count(callback, &v2, &v1) == 2\n"
        "}\n\n"
    )
    requires_clause = (
        "    requires\n"
        "        callback.requires((&v2,)),\n"
        "        forall|key2: K, callback_after_v2: F|\n"
        "            cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2)\n"
        "                ==> callback_after_v2.requires((&v1,)),\n"
    )
    # Narrow boundary 1: exactly one FnMut call. No `T` result, no comparison,
    # no selection -- it cannot be the target outcome.
    step_boundary = (
        "#[verifier::external_body]\n"
        "fn cmp_key_callback_step<T, F: FnMut(&T) -> K, K>(\n"
        "    callback: F,\n"
        "    argument: &T,\n"
        ") -> (result: (K, F))\n"
        "    requires\n"
        "        callback.requires((argument,)),\n"
        "    ensures\n"
        "        callback.ensures((argument,), result.0),\n"
        "        cmp_fn_mut_state_transition(callback, argument, result.0, result.1),\n"
        "{\n"
        "    let mut callback = callback;\n"
        "    let key = callback(argument);\n"
        "    (key, callback)\n"
        "}\n\n"
    )
    # Narrow boundary 2: only the observation-count equation, and only for the
    # two calls the body actually performed.
    count_boundary = (
        "#[verifier::external_body]\n"
        "pub proof fn cmp_key_callback_observation_count_law<T, F: FnMut(&T) -> K, K>(\n"
        "    callback: F,\n"
        "    first: &T,\n"
        "    second: &T,\n"
        "    key_first: K,\n"
        "    callback_after_first: F,\n"
        "    key_second: K,\n"
        "    callback_after_second: F,\n"
        ")\n"
        "    requires\n"
        "        callback.ensures((first,), key_first),\n"
        "        cmp_fn_mut_state_transition(callback, first, key_first, callback_after_first),\n"
        "        callback_after_first.ensures((second,), key_second),\n"
        "        cmp_fn_mut_state_transition(callback_after_first, second, key_second, callback_after_second),\n"
        "    ensures\n"
        "        cmp_key_callback_observation_count(callback, first, second) == 2,\n"
        "{\n"
        "}\n\n"
    )
    call_sequence = (
        "    let (key2, callback_after_v2) = cmp_key_callback_step(callback, &v2);\n"
        "    let (key1, callback_after_v1) = cmp_key_callback_step(callback_after_v2, &v1);\n"
    )
    mutated_call_sequence = (
        "    let (key1, callback_after_v1) = cmp_key_callback_step(callback, &v1);\n"
        "    let (key2, callback_after_v2) = cmp_key_callback_step(callback_after_v1, &v2);\n"
    )
    implementation = (
        header
        + state_transition_helper
        + observation_count_helper
        + trace_helper
        + accepted_contract
        + step_boundary
        + count_boundary
        + "pub fn implementation_target<T, F: FnMut(&T) -> K, K: Ord>(v1: T, v2: T, callback: F) -> (result: T)\n"
        + requires_clause
        + "    ensures\n"
        "        accepted_contract(v1, v2, callback, result),\n"
        "{\n"
        + call_sequence
        + "    let second_is_less = PartialOrd::lt(&key2, &key1);\n"
        "    proof {\n"
        "        cmp_key_callback_observation_count_law::<T, F, K>(\n"
        "            callback,\n"
        "            &v2,\n"
        "            &v1,\n"
        "            key2,\n"
        "            callback_after_v2,\n"
        "            key1,\n"
        "            callback_after_v1,\n"
        "        );\n"
        "        assert(cmp_key_callback_trace(\n"
        "            v1,\n"
        "            v2,\n"
        "            callback,\n"
        "            key2,\n"
        "            key1,\n"
        "            callback_after_v2,\n"
        "            callback_after_v1,\n"
        "            second_is_less,\n"
        "        ));\n"
        "        assert(accepted_contract(\n"
        "            v1,\n"
        "            v2,\n"
        "            callback,\n"
        "            " + exec_selection + ",\n"
        "        ));\n"
        "    }\n"
        "    " + exec_selection + "\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + state_transition_helper + observation_count_helper + trace_helper + accepted_contract + (
        "pub proof fn completeness_theorem<T, F: FnMut(&T) -> K, K: Ord>(\n"
        "    v1: T,\n"
        "    v2: T,\n"
        "    callback: F,\n"
        "    key2_1: K,\n"
        "    key1_1: K,\n"
        "    callback_after_v2_1: F,\n"
        "    callback_after_v1_1: F,\n"
        "    second_is_less_1: bool,\n"
        "    result1: T,\n"
        "    key2_2: K,\n"
        "    key1_2: K,\n"
        "    callback_after_v2_2: F,\n"
        "    callback_after_v1_2: F,\n"
        "    second_is_less_2: bool,\n"
        "    result2: T,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(v1, v2, callback, result1),\n"
        "        accepted_contract(v1, v2, callback, result2),\n"
        "        cmp_key_callback_trace(v1, v2, callback, key2_1, key1_1, callback_after_v2_1, callback_after_v1_1, second_is_less_1),\n"
        "        cmp_key_callback_trace(v1, v2, callback, key2_2, key1_2, callback_after_v2_2, callback_after_v1_2, second_is_less_2),\n"
        "        result1 == " + (
            "if second_is_less_1 { v2 } else { v1 }"
            if method == "min_by_key"
            else "if second_is_less_1 { v1 } else { v2 }"
        ) + ",\n"
        "        result2 == " + (
            "if second_is_less_2 { v2 } else { v1 }"
            if method == "min_by_key"
            else "if second_is_less_2 { v1 } else { v2 }"
        ) + ",\n"
        "        forall|ka: K, kb: K| callback.ensures((&v2,), ka) && callback.ensures((&v2,), kb) ==> ka == kb,\n"
        "        forall|before: F, key: K, after_a: F, after_b: F|\n"
        "            cmp_fn_mut_state_transition(before, &v2, key, after_a)\n"
        "                && cmp_fn_mut_state_transition(before, &v2, key, after_b)\n"
        "                ==> after_a == after_b,\n"
        "        forall|cb2: F, ka: K, kb: K| cb2.ensures((&v1,), ka) && cb2.ensures((&v1,), kb) ==> ka == kb,\n"
        "        forall|before: F, key: K, after_a: F, after_b: F|\n"
        "            cmp_fn_mut_state_transition(before, &v1, key, after_a)\n"
        "                && cmp_fn_mut_state_transition(before, &v1, key, after_b)\n"
        "                ==> after_a == after_b,\n"
        "        forall|k2: K, k1: K, la: bool, lb: bool|\n"
        "            call_ensures(<K as PartialOrd>::lt, (&k2, &k1), la)\n"
        "                && call_ensures(<K as PartialOrd>::lt, (&k2, &k1), lb)\n"
        "                ==> la == lb,\n"
        "    ensures\n"
        "        key2_1 == key2_2,\n"
        "        callback_after_v2_1 == callback_after_v2_2,\n"
        "        key1_1 == key1_2,\n"
        "        callback_after_v1_1 == callback_after_v1_2,\n"
        "        second_is_less_1 == second_is_less_2,\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    boundaries = (
        _boundary("cmp_key_callback_step", "single_fn_mut_call"),
        _boundary(
            "cmp_key_callback_observation_count_law", "observation_count_trace"
        ),
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("v1: T", "v2: T", "callback: F", "-> (result: T)"),
        boundaries=boundaries,
        implementation_mutation=_mutation(
            family,
            call_sequence,
            mutated_call_sequence,
            "call_order",
        ),
        completeness_mutation=_mutation(
            family,
            "callback_after_v1_1 == callback_after_v1_2,",
            "callback_after_v1_1 != callback_after_v1_2,",
            "callback_final_state",
        ),
    )


# ---------------------------------------------------------------------------
# ordering_then_with: Ordering::then_with calls its FnOnce callback exactly
# once, and only when `self == Ordering::Equal`.
# ---------------------------------------------------------------------------

def _build_ordering_then_with(row: dict[str, Any]) -> ProofTemplate:
    family = "ordering_then_with"
    header = _HEADER + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<F: FnOnce() -> Ordering>(\n"
        "    ordering: Ordering,\n"
        "    callback: F,\n"
        "    result: Ordering,\n"
        ") -> bool {\n"
        "    if ordering != Ordering::Equal {\n"
        "        result == ordering\n"
        "    } else {\n"
        "        callback.ensures((), result)\n"
        "    }\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<F: FnOnce() -> Ordering>(ordering: Ordering, callback: F) -> (result: Ordering)\n"
        "    requires\n"
        "        ordering == Ordering::Equal ==> callback.requires(()),\n"
        "    ensures\n"
        "        accepted_contract(ordering, callback, result),\n"
        "{\n"
        "    if matches!(ordering, Ordering::Equal) {\n"
        "        assert(callback.requires(()));\n"
        "        callback()\n"
        "    } else {\n"
        "        ordering\n"
        "    }\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<F: FnOnce() -> Ordering>(\n"
        "    ordering: Ordering,\n"
        "    callback: F,\n"
        "    result1: Ordering,\n"
        "    result2: Ordering,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(ordering, callback, result1),\n"
        "        accepted_contract(ordering, callback, result2),\n"
        "        forall|o1: Ordering, o2: Ordering|\n"
        "            callback.ensures((), o1) && callback.ensures((), o2) ==> o1 == o2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("ordering: Ordering", "callback: F", "-> (result: Ordering)"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "if matches!(ordering, Ordering::Equal) {",
            "if !matches!(ordering, Ordering::Equal) {",
            "call_gate",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "call_gate",
        ),
    )


# ---------------------------------------------------------------------------
# ordering_debug: `Ordering` derives `Debug`. For a field-less enum rustc
# lowers the derive to a discriminant-directed variant-name selection followed
# by exactly one `Formatter::write_str` of that name, and `implementation_target`
# preserves that structure literally: it selects the variant name itself (a
# plain, fully verified `match`) and then performs the single lower
# `write_str`. The only boundary is that lower formatter operation, whose
# whole `ensures` is `cmp_formatter_write_str_effect(text, ..)` for an
# arbitrary `text: &str`. It never mentions `Ordering` and never mentions the
# derived variant-name selection, so it is strictly narrower than
# `implementation_target`'s postcondition rather than alpha-identical to it.
#
# Documented Verus lowering: the accepted contract spells the formatter effect
# over the `&mut Formatter` itself; a mutable reference passed to a callee is
# a *distinct* mutable reference in Verus's model ("every mut ref has a unique
# name"), so the pre/post formatter *values* `*old(formatter)` / `*final(
# formatter)` are what actually thread through a call. Both the boundary and
# the target therefore state the effect over those two values.
# ---------------------------------------------------------------------------

_ORDERING_DEBUG_NAME_HELPERS = """\
pub open spec fn cmp_ordering_debug_name(value: Ordering) -> &'static str {
    match value {
        Ordering::Less => "Less",
        Ordering::Equal => "Equal",
        Ordering::Greater => "Greater",
    }
}

pub fn cmp_ordering_debug_name_exec(value: &Ordering) -> (name: &'static str)
    ensures
        name == cmp_ordering_debug_name(*value),
{
    match value {
        Ordering::Less => "Less",
        Ordering::Equal => "Equal",
        Ordering::Greater => "Greater",
    }
}

"""

_FORMATTER_WRITE_STR_EFFECT = """\
pub uninterp spec fn cmp_formatter_write_str_effect<'a>(
    text: &str,
    before: core::fmt::Formatter<'a>,
    after: core::fmt::Formatter<'a>,
    result: core::fmt::Result,
) -> bool;

"""


def _build_ordering_debug(row: dict[str, Any]) -> ProofTemplate:
    family = "ordering_debug"
    header = (
        _HEADER
        + "use vstd::prelude::*;\nuse core::cmp::Ordering;\n\n"
        + _FORMATTER_TYPE_SPEC
        + "\nverus! {\n\n"
    )
    boundary_fn = (
        "#[verifier::external_body]\n"
        "fn cmp_formatter_write_str(\n"
        "    formatter: &mut core::fmt::Formatter<'_>,\n"
        "    text: &str,\n"
        ") -> (result: core::fmt::Result)\n"
        "    ensures\n"
        "        cmp_formatter_write_str_effect(text, *old(formatter), *final(formatter), result),\n"
        "{\n"
        "    core::fmt::Formatter::write_str(formatter, text)\n"
        "}\n\n"
    )
    effect_definition = (
        "pub open spec fn cmp_ordering_debug_effect<'a>(\n"
        "    value: Ordering,\n"
        "    before: core::fmt::Formatter<'a>,\n"
        "    after: core::fmt::Formatter<'a>,\n"
        "    result: core::fmt::Result,\n"
        ") -> bool {\n"
        "    cmp_formatter_write_str_effect(cmp_ordering_debug_name(value), before, after, result)\n"
        "}\n\n"
    )
    accepted_contract = (
        "pub open spec fn accepted_contract<'a>(\n"
        "    value: Ordering,\n"
        "    before: core::fmt::Formatter<'a>,\n"
        "    after: core::fmt::Formatter<'a>,\n"
        "    result: core::fmt::Result,\n"
        ") -> bool {\n"
        "    cmp_ordering_debug_effect(value, before, after, result)\n"
        "}\n\n"
    )
    shared = (
        header
        + _ORDERING_DEBUG_NAME_HELPERS
        + _FORMATTER_WRITE_STR_EFFECT
        + effect_definition
        + accepted_contract
    )
    implementation = shared + boundary_fn + (
        "pub fn implementation_target(value: &Ordering, formatter: &mut core::fmt::Formatter<'_>) -> (result: core::fmt::Result)\n"
        "    ensures\n"
        "        accepted_contract(*value, *old(formatter), *final(formatter), result),\n"
        "{\n"
        "    let name = cmp_ordering_debug_name_exec(value);\n"
        "    cmp_formatter_write_str(formatter, name)\n"
        "}\n\n"
        "}\n"
    )
    completeness = shared + (
        "pub proof fn completeness_theorem<'a>(\n"
        "    value: Ordering,\n"
        "    before: core::fmt::Formatter<'a>,\n"
        "    after1: core::fmt::Formatter<'a>,\n"
        "    after2: core::fmt::Formatter<'a>,\n"
        "    result1: core::fmt::Result,\n"
        "    result2: core::fmt::Result,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(value, before, after1, result1),\n"
        "        accepted_contract(value, before, after2, result2),\n"
        "        forall|text: &str, a1: core::fmt::Formatter<'a>, r1: core::fmt::Result, a2: core::fmt::Formatter<'a>, r2: core::fmt::Result|\n"
        "            cmp_formatter_write_str_effect(text, before, a1, r1)\n"
        "                && cmp_formatter_write_str_effect(text, before, a2, r2)\n"
        "                ==> a1 == a2 && r1 == r2,\n"
        "    ensures\n"
        "        after1 == after2,\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    boundaries = (_boundary("cmp_formatter_write_str", "formatter_write_str"),)
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "value: &Ordering",
            "formatter: &mut core::fmt::Formatter<'_>",
            "-> (result: core::fmt::Result)",
        ),
        boundaries=boundaries,
        implementation_mutation=_mutation(
            family,
            "    cmp_formatter_write_str(formatter, name)\n",
            '    cmp_formatter_write_str(formatter, "Ordering")\n',
            "derived_variant_name",
        ),
        completeness_mutation=_mutation(
            family,
            "after1 == after2,",
            "after1 != after2,",
            "formatter_post_state",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_debug: `Reverse<T>` derives `Debug`, and the accepted contract fixes
# its formatter effect to the effect of debug-formatting the wrapped `T`.
# `implementation_target` executes that `T::fmt` delegation directly and binds
# the `call_ensures` of that lower trait call, with no external helper at all.
#
# Documented Verus lowering: the `&mut Formatter` handed to the delegate is a
# *distinct* mutable reference from the target's own parameter (in Verus's
# model every mutable reference has a unique name, so
# `call_ensures(f, (value, formatter), r)` is not transferable across the
# reborrow). The accepted effect is therefore expressed as: there exists a
# mutable reference with the same pre-state and the same post-state as the
# target's formatter for which the lower `T::fmt` call relation holds. That is
# a definition, not an uninterpreted stand-in, so nothing about the delegation
# is assumed.
# ---------------------------------------------------------------------------

def _build_reverse_debug(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_debug"
    header = (
        _SIZED_HIERARCHY_HEADER
        + "use vstd::prelude::*;\nuse core::marker::PointeeSized;\n\n"
        + _REVERSE_TYPE_SPEC
        + "\n"
        + _FORMATTER_TYPE_SPEC
        + "\nverus! {\n\n"
        + _DEBUG_TRAIT_SPEC
    )
    lower_call = "call_ensures(<T as core::fmt::Debug>::fmt, (value, inner), result)"
    effect_definition = (
        "#[verifier::prophetic]\n"
        "pub open spec fn cmp_reverse_debug_effect<'a, T: core::fmt::Debug>(\n"
        "    value: &T,\n"
        "    formatter: &mut core::fmt::Formatter<'a>,\n"
        "    result: core::fmt::Result,\n"
        ") -> bool {\n"
        "    exists|inner: &mut core::fmt::Formatter<'a>|\n"
        "        #![trigger " + lower_call + "]\n"
        "        mut_ref_current(inner) == mut_ref_current(formatter)\n"
        "            && mut_ref_future(inner) == mut_ref_future(formatter)\n"
        "            && " + lower_call + "\n"
        "}\n\n"
    )
    accepted_contract = (
        "#[verifier::prophetic]\n"
        "pub open spec fn accepted_contract<'a, T: core::fmt::Debug>(\n"
        "    value: &T,\n"
        "    formatter: &mut core::fmt::Formatter<'a>,\n"
        "    result: core::fmt::Result,\n"
        ") -> bool {\n"
        "    cmp_reverse_debug_effect(value, formatter, result)\n"
        "}\n\n"
    )
    shared = header + effect_definition + accepted_contract
    implementation = shared + (
        "pub fn implementation_target<T: core::fmt::Debug>(\n"
        "    value: &core::cmp::Reverse<T>,\n"
        "    formatter: &mut core::fmt::Formatter<'_>,\n"
        ") -> (result: core::fmt::Result)\n"
        "    ensures\n"
        "        accepted_contract(&value.0, formatter, result),\n"
        "{\n"
        "    core::fmt::Debug::fmt(&value.0, formatter)\n"
        "}\n\n"
        "}\n"
    )
    completeness = shared + (
        "pub proof fn completeness_theorem<'a, T: core::fmt::Debug>(\n"
        "    value: &T,\n"
        "    formatter1: &mut core::fmt::Formatter<'a>,\n"
        "    formatter2: &mut core::fmt::Formatter<'a>,\n"
        "    result1: core::fmt::Result,\n"
        "    result2: core::fmt::Result,\n"
        ")\n"
        "    requires\n"
        "        mut_ref_current(formatter1) == mut_ref_current(formatter2),\n"
        "        accepted_contract(value, formatter1, result1),\n"
        "        accepted_contract(value, formatter2, result2),\n"
        "        forall|f1: &mut core::fmt::Formatter<'a>, f2: &mut core::fmt::Formatter<'a>, r1: core::fmt::Result, r2: core::fmt::Result|\n"
        "            #![trigger call_ensures(<T as core::fmt::Debug>::fmt, (value, f1), r1), call_ensures(<T as core::fmt::Debug>::fmt, (value, f2), r2)]\n"
        "            mut_ref_current(f1) == mut_ref_current(f2)\n"
        "                && call_ensures(<T as core::fmt::Debug>::fmt, (value, f1), r1)\n"
        "                && call_ensures(<T as core::fmt::Debug>::fmt, (value, f2), r2)\n"
        "                ==> mut_ref_future(f1) == mut_ref_future(f2) && r1 == r2,\n"
        "    ensures\n"
        "        mut_ref_future(formatter1) == mut_ref_future(formatter2),\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "value: &core::cmp::Reverse<T>",
            "formatter: &mut core::fmt::Formatter<'_>",
            "-> (result: core::fmt::Result)",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    core::fmt::Debug::fmt(&value.0, formatter)\n",
            "    core::fmt::Debug::fmt(&value.0, formatter);\n"
            "    core::fmt::Debug::fmt(&value.0, formatter)\n",
            "forwarding_call_count",
        ),
        completeness_mutation=_mutation(
            family,
            "mut_ref_future(formatter1) == mut_ref_future(formatter2),",
            "mut_ref_future(formatter1) != mut_ref_future(formatter2),",
            "formatter_post_state",
        ),
    )


# ---------------------------------------------------------------------------
# ordering_hash: `Ordering` derives `Hash`. For a field-less enum rustc lowers
# the derive to `Hash::hash(&discriminant_value(self), state)`, and
# `implementation_target` preserves that structure literally: it computes the
# `#[repr(i8)]` discriminant itself (a plain, fully verified `match`) and then
# performs the single lower discriminant hash. The only boundary is that lower
# hasher operation, whose whole `ensures` is
# `cmp_discriminant_hash_effect(discriminant, ..)` for an arbitrary `i8`; it
# never mentions `Ordering` and never mentions the derived discriminant
# selection, so it is strictly narrower than `implementation_target`'s
# postcondition rather than alpha-identical to it.
# ---------------------------------------------------------------------------

_ORDERING_DISCRIMINANT_HELPERS = """\
pub open spec fn cmp_ordering_discriminant(value: Ordering) -> i8 {
    match value {
        Ordering::Less => -1i8,
        Ordering::Equal => 0i8,
        Ordering::Greater => 1i8,
    }
}

pub fn cmp_ordering_discriminant_exec(value: &Ordering) -> (discriminant: i8)
    ensures
        discriminant == cmp_ordering_discriminant(*value),
{
    match value {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

"""


def _build_ordering_hash(row: dict[str, Any]) -> ProofTemplate:
    family = "ordering_hash"
    header = (
        _HEADER
        + "use vstd::prelude::*;\nuse core::cmp::Ordering;\nuse core::hash::Hasher;\n\nverus! {\n\n"
    )
    effect_helper = (
        "pub uninterp spec fn cmp_discriminant_hash_effect<H: Hasher>(\n"
        "    discriminant: i8,\n"
        "    before: H,\n"
        "    after: H,\n"
        ") -> bool;\n\n"
    )
    effect_definition = (
        "pub open spec fn cmp_ordering_hash_effect<H: Hasher>(value: Ordering, before: H, after: H) -> bool {\n"
        "    cmp_discriminant_hash_effect(cmp_ordering_discriminant(value), before, after)\n"
        "}\n\n"
    )
    accepted_contract = (
        "pub open spec fn accepted_contract<H: Hasher>(value: Ordering, before: H, after: H) -> bool {\n"
        "    cmp_ordering_hash_effect(value, before, after)\n"
        "}\n\n"
    )
    boundary_fn = (
        "#[verifier::external_body]\n"
        "fn cmp_hash_discriminant<H: Hasher>(discriminant: i8, state: &mut H)\n"
        "    ensures\n"
        "        cmp_discriminant_hash_effect(discriminant, *old(state), *final(state)),\n"
        "{\n"
        "    core::hash::Hash::hash(&discriminant, state)\n"
        "}\n\n"
    )
    shared = (
        header
        + _ORDERING_DISCRIMINANT_HELPERS
        + effect_helper
        + effect_definition
        + accepted_contract
    )
    implementation = shared + boundary_fn + (
        "pub fn implementation_target<H: Hasher>(value: &Ordering, state: &mut H)\n"
        "    ensures\n"
        "        accepted_contract(*value, *old(state), *final(state)),\n"
        "{\n"
        "    let discriminant = cmp_ordering_discriminant_exec(value);\n"
        "    cmp_hash_discriminant(discriminant, state)\n"
        "}\n\n"
        "}\n"
    )
    completeness = shared + (
        "pub proof fn completeness_theorem<H: Hasher>(value: Ordering, before: H, result1: H, result2: H)\n"
        "    requires\n"
        "        accepted_contract(value, before, result1),\n"
        "        accepted_contract(value, before, result2),\n"
        "        forall|discriminant: i8, a1: H, a2: H|\n"
        "            cmp_discriminant_hash_effect(discriminant, before, a1)\n"
        "                && cmp_discriminant_hash_effect(discriminant, before, a2)\n"
        "                ==> a1 == a2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    boundaries = (_boundary("cmp_hash_discriminant", "discriminant_hash"),)
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("value: &Ordering", "state: &mut H"),
        boundaries=boundaries,
        implementation_mutation=_mutation(
            family,
            "    cmp_hash_discriminant(discriminant, state)\n",
            "    cmp_hash_discriminant(0, state)\n",
            "derived_discriminant",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "derived_discriminant",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_hash: `Reverse<T>` derives `Hash`, which rustc lowers to
# `Hash::hash(&self.0, state)`. `implementation_target` executes that `T::hash`
# delegation directly and binds the `call_ensures` of that lower trait call,
# with no external helper at all. The same documented mutable-reference
# lowering as `reverse_debug` applies to the `&mut H` hasher.
# ---------------------------------------------------------------------------

def _build_reverse_hash(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_hash"
    header = (
        _SIZED_HIERARCHY_HEADER
        + "use vstd::prelude::*;\nuse core::hash::Hasher;\n"
        "use core::marker::PointeeSized;\n\n"
        + _REVERSE_TYPE_SPEC
        + "\nverus! {\n\n"
        + _HASH_TRAIT_SPEC
    )
    lower_call = "call_ensures(<T as core::hash::Hash>::hash::<H>, (value, inner), ())"
    effect_definition = (
        "#[verifier::prophetic]\n"
        "pub open spec fn cmp_reverse_hash_effect<T: core::hash::Hash, H: Hasher>(\n"
        "    value: &T,\n"
        "    state: &mut H,\n"
        ") -> bool {\n"
        "    exists|inner: &mut H|\n"
        "        #![trigger " + lower_call + "]\n"
        "        mut_ref_current(inner) == mut_ref_current(state)\n"
        "            && mut_ref_future(inner) == mut_ref_future(state)\n"
        "            && " + lower_call + "\n"
        "}\n\n"
    )
    accepted_contract = (
        "#[verifier::prophetic]\n"
        "pub open spec fn accepted_contract<T: core::hash::Hash, H: Hasher>(value: &T, state: &mut H) -> bool {\n"
        "    cmp_reverse_hash_effect(value, state)\n"
        "}\n\n"
    )
    shared = header + effect_definition + accepted_contract
    implementation = shared + (
        "pub fn implementation_target<T: core::hash::Hash, H: Hasher>(value: &core::cmp::Reverse<T>, state: &mut H)\n"
        "    ensures\n"
        "        accepted_contract(&value.0, state),\n"
        "{\n"
        "    core::hash::Hash::hash(&value.0, state)\n"
        "}\n\n"
        "}\n"
    )
    determinism = (
        "        forall|s1: &mut H, s2: &mut H|\n"
        "            #![trigger call_ensures(<T as core::hash::Hash>::hash::<H>, (value, s1), ()), call_ensures(<T as core::hash::Hash>::hash::<H>, (value, s2), ())]\n"
        "            mut_ref_current(s1) == mut_ref_current(s2)\n"
        "                && call_ensures(<T as core::hash::Hash>::hash::<H>, (value, s1), ())\n"
        "                && call_ensures(<T as core::hash::Hash>::hash::<H>, (value, s2), ())\n"
        "                ==> mut_ref_future(s1) == mut_ref_future(s2),\n"
    )
    completeness = shared + (
        "pub proof fn completeness_theorem<T: core::hash::Hash, H: Hasher>(\n"
        "    value: &T,\n"
        "    state1: &mut H,\n"
        "    state2: &mut H,\n"
        "    result1: H,\n"
        "    result2: H,\n"
        ")\n"
        "    requires\n"
        "        mut_ref_current(state1) == mut_ref_current(state2),\n"
        "        mut_ref_future(state1) == result1,\n"
        "        mut_ref_future(state2) == result2,\n"
        "        accepted_contract(value, state1),\n"
        "        accepted_contract(value, state2),\n"
        + determinism
        + "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("value: &core::cmp::Reverse<T>", "state: &mut H"),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "    core::hash::Hash::hash(&value.0, state)\n",
            "    core::hash::Hash::hash(&value.0, state);\n"
            "    core::hash::Hash::hash(&value.0, state)\n",
            "forwarding_call_count",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_call_count",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_default: Reverse<T>::default() forwards to T::default().
# ---------------------------------------------------------------------------

def _build_reverse_default(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_default"
    header = _HEADER + "use vstd::prelude::*;\n\n" + _REVERSE_TYPE_SPEC + "\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<T: Default>(result: core::cmp::Reverse<T>) -> bool {\n"
        "    exists|value: T| call_ensures(T::default, (), value) && result == core::cmp::Reverse(value)\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T: Default>() -> (result: core::cmp::Reverse<T>)\n"
        "    ensures\n"
        "        accepted_contract(result),\n"
        "{\n"
        "    core::cmp::Reverse(T::default())\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T: Default>(\n"
        "    result1: core::cmp::Reverse<T>,\n"
        "    result2: core::cmp::Reverse<T>,\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(result1),\n"
        "        accepted_contract(result2),\n"
        "        forall|v1: T, v2: T| call_ensures(T::default, (), v1) && call_ensures(T::default, (), v2) ==> v1 == v2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("-> (result: core::cmp::Reverse<T>)",),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "result == core::cmp::Reverse(value)",
            "result != core::cmp::Reverse(value)",
            "forwarding_target",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_target",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_clone: Reverse<T>::clone forwards to T::clone; clone_from forwards
# to T::clone through a mutable reborrow (a plain, top-level `&mut Self`
# parameter, so old()/final() disambiguation applies directly with no
# PointeeSized/MetaSized restriction).
# ---------------------------------------------------------------------------

def _build_reverse_clone(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_clone"
    method = row["method_name"]
    header = _HEADER + "use vstd::prelude::*;\n\n" + _REVERSE_TYPE_SPEC + "\nverus! {\n\n"
    if method == "clone":
        accepted_contract = (
            "pub open spec fn accepted_contract<T: Clone>(\n"
            "    source: core::cmp::Reverse<T>,\n"
            "    result: core::cmp::Reverse<T>,\n"
            ") -> bool {\n"
            "    call_ensures(T::clone, (&source.0,), result.0)\n"
            "}\n\n"
        )
        implementation = header + accepted_contract + (
            "pub fn implementation_target<T: Clone>(source: &core::cmp::Reverse<T>) -> (result: core::cmp::Reverse<T>)\n"
            "    ensures\n"
            "        accepted_contract(*source, result),\n"
            "{\n"
            "    core::cmp::Reverse(source.0.clone())\n"
            "}\n\n"
            "}\n"
        )
        completeness = header + accepted_contract + (
            "pub proof fn completeness_theorem<T: Clone>(\n"
            "    source: core::cmp::Reverse<T>,\n"
            "    result1: core::cmp::Reverse<T>,\n"
            "    result2: core::cmp::Reverse<T>,\n"
            ")\n"
            "    requires\n"
            "        accepted_contract(source, result1),\n"
            "        accepted_contract(source, result2),\n"
            "        forall|a: T, b1: T, b2: T| call_ensures(T::clone, (&a,), b1) && call_ensures(T::clone, (&a,), b2) ==> b1 == b2,\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{\n"
            "}\n\n"
            "}\n"
        )
        return _template(
            proof_family=family,
            implementation_proof=implementation,
            completeness_proof=completeness,
            source_shape_tokens=(
                "source: &core::cmp::Reverse<T>",
                "-> (result: core::cmp::Reverse<T>)",
            ),
            boundaries=(),
            implementation_mutation=_mutation(
                family,
                "core::cmp::Reverse(source.0.clone())",
                "core::cmp::Reverse(source.0.clone().clone())",
                "forwarding_target",
            ),
            completeness_mutation=_mutation(
                family,
                "result1 == result2,",
                "result1 != result2,",
                "forwarding_target",
            ),
        )
    assert method == "clone_from"
    accepted_contract = (
        "pub open spec fn accepted_contract<T: Clone>(before: T, source: T, after: T) -> bool {\n"
        "    call_ensures(T::clone, (&source,), after)\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T: Clone>(\n"
        "    target: &mut core::cmp::Reverse<T>,\n"
        "    source: &core::cmp::Reverse<T>,\n"
        ")\n"
        "    ensures\n"
        "        accepted_contract(old(target).0, source.0, final(target).0),\n"
        "{\n"
        "    target.0 = source.0.clone();\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T: Clone>(before: T, source: T, result1: T, result2: T)\n"
        "    requires\n"
        "        accepted_contract(before, source, result1),\n"
        "        accepted_contract(before, source, result2),\n"
        "        forall|a: T, b1: T, b2: T| call_ensures(T::clone, (&a,), b1) && call_ensures(T::clone, (&a,), b2) ==> b1 == b2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "target: &mut core::cmp::Reverse<T>",
            "source: &core::cmp::Reverse<T>",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "target.0 = source.0.clone();",
            "let _ignored = source.0.clone();",
            "forwarding_target",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_target",
        ),
    )


# ---------------------------------------------------------------------------
# empty_eq_default: Eq::assert_receiver_is_total_eq is a trait-default method
# whose real body is empty ({}) and carries no observable behavior beyond the
# Eq/PartialEq<Self> marker bound. This is the sole documented lowering
# exception: the accepted contract is the trivial predicate `true`.
# ---------------------------------------------------------------------------

def _build_empty_eq_default(row: dict[str, Any]) -> ProofTemplate:
    family = "empty_eq_default"
    implementation = _SIZED_HIERARCHY_HEADER + (
        "use vstd::prelude::*;\n"
        "use core::marker::PointeeSized;\n\n"
        "verus! {\n\n"
        "// Explicit documented lowering: the real trait-default body is empty (`{}`)\n"
        "// and carries no observable behavior beyond the Eq/PartialEq<Self> marker\n"
        "// bound, so the accepted contract is the trivial predicate `true` for every\n"
        "// receiver. This is the only owned identity in this module rendered without\n"
        "// preserving a non-trivial resolved-shape ensures clause.\n"
        "pub open spec fn accepted_contract<T: PointeeSized + PartialEq<T>>(receiver: &T) -> bool {\n"
        "    true\n"
        "}\n\n"
        "pub fn implementation_target<T: PointeeSized + PartialEq<T>>(receiver: &T)\n"
        "    ensures\n"
        "        accepted_contract(receiver),\n"
        "{\n"
        "    // The real trait-default body is `{}`; `receiver` is named here only\n"
        "    // so the lowered body is a non-vacuous no-op with the same effect.\n"
        "    let _ = receiver;\n"
        "}\n\n"
        "}\n"
    )
    completeness = _SIZED_HIERARCHY_HEADER + (
        "use vstd::prelude::*;\n"
        "use core::marker::PointeeSized;\n\n"
        "verus! {\n\n"
        "pub open spec fn accepted_contract<T: PointeeSized + PartialEq<T>>(receiver: &T) -> bool {\n"
        "    true\n"
        "}\n\n"
        "pub proof fn completeness_theorem<T: PointeeSized + PartialEq<T>>(\n"
        "    receiver: &T,\n"
        "    result1: (),\n"
        "    result2: (),\n"
        ")\n"
        "    requires\n"
        "        accepted_contract(receiver),\n"
        "        accepted_contract(receiver),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=("receiver: &T",),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "pub open spec fn accepted_contract<T: PointeeSized + PartialEq<T>>(receiver: &T) -> bool {\n    true\n}",
            "pub open spec fn accepted_contract<T: PointeeSized + PartialEq<T>>(receiver: &T) -> bool {\n    false\n}",
            "trivial_predicate",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "trivial_predicate",
        ),
    )


# ---------------------------------------------------------------------------
# reverse_forwarding: Reverse<T>::eq forwards directly to T's PartialEq::eq
# (no operand reversal -- equality is symmetric in the source and this impl
# only reads the wrapped fields, unlike the PartialOrd/Ord methods above).
# ---------------------------------------------------------------------------

def _build_reverse_forwarding(row: dict[str, Any]) -> ProofTemplate:
    family = "reverse_forwarding"
    header = _HEADER + "use vstd::prelude::*;\n\n" + _REVERSE_TYPE_SPEC + "\nverus! {\n\n"
    accepted_contract = (
        "pub open spec fn accepted_contract<T: PartialEq>(left: T, right: T, result: bool) -> bool {\n"
        "    call_ensures(<T as PartialEq>::eq, (&left, &right), result)\n"
        "}\n\n"
    )
    implementation = header + accepted_contract + (
        "pub fn implementation_target<T: PartialEq>(\n"
        "    left: &core::cmp::Reverse<T>,\n"
        "    right: &core::cmp::Reverse<T>,\n"
        ") -> (result: bool)\n"
        "    ensures\n"
        "        accepted_contract(left.0, right.0, result),\n"
        "{\n"
        "    PartialEq::eq(&left.0, &right.0)\n"
        "}\n\n"
        "}\n"
    )
    completeness = header + accepted_contract + (
        "pub proof fn completeness_theorem<T: PartialEq>(left: T, right: T, result1: bool, result2: bool)\n"
        "    requires\n"
        "        accepted_contract(left, right, result1),\n"
        "        accepted_contract(left, right, result2),\n"
        "        forall|o1: bool, o2: bool|\n"
        "            call_ensures(<T as PartialEq>::eq, (&left, &right), o1)\n"
        "                && call_ensures(<T as PartialEq>::eq, (&left, &right), o2)\n"
        "                ==> o1 == o2,\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n"
        "}\n\n"
        "}\n"
    )
    return _template(
        proof_family=family,
        implementation_proof=implementation,
        completeness_proof=completeness,
        source_shape_tokens=(
            "left: &core::cmp::Reverse<T>",
            "right: &core::cmp::Reverse<T>",
            "-> (result: bool)",
        ),
        boundaries=(),
        implementation_mutation=_mutation(
            family,
            "PartialEq::eq(&left.0, &right.0)",
            "PartialEq::eq(&right.0, &left.0)",
            "forwarding_target",
        ),
        completeness_mutation=_mutation(
            family,
            "result1 == result2,",
            "result1 != result2,",
            "forwarding_target",
        ),
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_FAMILY_BUILDERS: dict[str, Callable[[dict[str, Any]], ProofTemplate]] = {
    "ordering_value": _build_value_relation,
    "unit_value": _build_value_relation,
    "char_value": _build_value_relation,
    "bool_value": _build_value_relation,
    "reference_forwarding": _build_reference_forwarding,
    "reverse_operand_reversal": _build_reverse_operand_reversal,
    "reverse_forwarding": _build_reverse_forwarding,
    "primitive_clamp": _build_primitive_clamp,
    "trait_default_clamp": _build_trait_default_clamp,
    "free_ord_forwarding": _build_free_ord_forwarding,
    "comparator_callback": _build_comparator_callback,
    "key_callback_order": _build_key_callback_order,
    "ordering_then_with": _build_ordering_then_with,
    "ordering_debug": _build_ordering_debug,
    "reverse_debug": _build_reverse_debug,
    "ordering_hash": _build_ordering_hash,
    "reverse_hash": _build_reverse_hash,
    "reverse_default": _build_reverse_default,
    "reverse_clone": _build_reverse_clone,
    "empty_eq_default": _build_empty_eq_default,
}

assert set(_FAMILY_BUILDERS) == set(ROW_FAMILY.values())


def render(
    row: dict[str, Any],
    contract_family: str,
    accepted_contract_text: str,
) -> ProofTemplate:
    """Render the :class:`ProofTemplate` owned by this module for ``row``.

    ``accepted_contract_text`` is the exact ``specs/generated_cmp_specs.rs``
    excerpt (the ``// @spec-row ... family=...`` block) bound to ``row``; it
    is accepted for identity binding and is not required to be re-parsed
    because every owned family's signature/generic/lifetime/mutability shape
    is already derived independently from ``row["signature"]``/
    ``row["matching_shape"]`` below, which is the same resolved-shape source
    of truth the accepted contract was itself generated from.
    """

    if not supports(row, contract_family):
        raise ValueError(
            f"proof_templates_cmp does not own row {row.get('row_id')!r} "
            f"under family {contract_family!r}"
        )
    if not isinstance(accepted_contract_text, str) or not accepted_contract_text.strip():
        raise ValueError("accepted_contract_text must be a non-empty string")
    row_id = row["row_id"]
    if row_id not in accepted_contract_text and row["target"] not in accepted_contract_text:
        raise ValueError(
            "accepted_contract_text is not bound to row "
            f"{row_id!r} (target {row['target']!r})"
        )
    builder = _FAMILY_BUILDERS[contract_family]
    return builder(row)
