"""Proof-template renderer owning the accepted ``disposition=exact_vstd`` rows.

This module renders `ProofTemplate` objects (see
`tools/proof_template_common.py`) for every `core::cmp` inventory row whose
independent exact-vstd audit already certifies an identity-, signature-, and
semantics-preserving binding to a pre-existing vstd contract. Because the
vstd contract is already the accepted authority for these rows, the rendered
proofs never redeclare a competing `assume_specification` for the target
itself. Instead each rendered `accepted_contract` spec function *calls
through* to the already-declared vstd spec surface (`PartialEqSpec`,
`PartialOrdSpec`, `OrdSpec`, or the literal Ordering/Option `ensures`
relation copied from the frozen vstd snapshot) and the executable
implementation body is a direct, source-shaped reimplementation of the
frozen `core::cmp`/`core::option` source span (primitive operators,
`Ordering` matches, `Option` variant matches, or default-method bodies),
with any compiler-intrinsic dependency lowered to an explicit, narrow
boundary rather than independently re-derived.

Ownership is exactly the non-float rows with ``disposition == "exact_vstd"`` in
``inventory/core_cmp_exec_fn_inventory.json``, partitioned into five
structural families:

* ``primitive_scalar`` -- bool/integer `eq`/`ne`/partial-ordering/
  `Ord::cmp`.
* ``shared_reference_forwarding`` -- the blanket `&A` forwarding impls (8
  rows).
* ``ordering_inherent`` -- `Ordering`'s inherent `is_*`/`reverse`/`then`
  convenience methods (8 rows).
* ``option_relational`` -- `Option<T>`'s `eq`/`partial_cmp`/`cmp` (3 rows).
* ``trait_default`` -- the shared `PartialEq`/`PartialOrd`/`Ord` default
  method bodies with semantically exact vstd contracts (7 rows).

`supports(row, contract_family)` gates on both the row's own
``disposition`` and on the caller-supplied ``contract_family`` label (the
uniform ``"exact_vstd"`` value that
``tools/build_specification.py::equivalence_record`` assigns to every row
with no newly authored contract). `render(row, contract_family,
accepted_contract_text)` raises :class:`ValueError` for anything this
module does not own, and otherwise returns a `ProofTemplate` whose
``implementation_proof`` and ``completeness_proof`` are independently
self-contained Verus source files (each compiles with
``verus <file> --crate-type=lib``).
"""

from __future__ import annotations

from typing import Any

from tools.proof_template_common import ProofTemplate

# --------------------------------------------------------------------------
# Ownership classification
# --------------------------------------------------------------------------

FAMILY_PRIMITIVE_SCALAR = "primitive_scalar"
FAMILY_SHARED_REFERENCE_FORWARDING = "shared_reference_forwarding"
FAMILY_ORDERING_INHERENT = "ordering_inherent"
FAMILY_OPTION_RELATIONAL = "option_relational"
FAMILY_TRAIT_DEFAULT = "trait_default"

ALL_FAMILIES = (
    FAMILY_PRIMITIVE_SCALAR,
    FAMILY_SHARED_REFERENCE_FORWARDING,
    FAMILY_ORDERING_INHERENT,
    FAMILY_OPTION_RELATIONAL,
    FAMILY_TRAIT_DEFAULT,
)

INTEGER_TYPES = (
    "i8", "i16", "i32", "i64", "i128", "isize",
    "u8", "u16", "u32", "u64", "u128", "usize",
)
BOOL_TYPE = "bool"
SCALAR_TYPES = (BOOL_TYPE,) + INTEGER_TYPES

CONTRACT_FAMILY = "exact_vstd"

EQ_METHODS = ("eq", "ne")
ORD_METHODS = ("lt", "le", "gt", "ge")
TRAIT_DEFAULT_TARGETS = frozenset(
    (
        ("PartialEq", "ne"),
        ("PartialOrd", "lt"),
        ("PartialOrd", "le"),
        ("PartialOrd", "gt"),
        ("PartialOrd", "ge"),
        ("Ord", "max"),
        ("Ord", "min"),
    )
)


def _classify(row: dict[str, Any]) -> str | None:
    owner = row.get("owner_type")
    if owner in SCALAR_TYPES:
        return FAMILY_PRIMITIVE_SCALAR
    if owner == "&A":
        return FAMILY_SHARED_REFERENCE_FORWARDING
    if owner == "Ordering":
        return FAMILY_ORDERING_INHERENT
    if owner == "Option<T>":
        return FAMILY_OPTION_RELATIONAL
    if (
        row.get("implementation_kind") == "trait_default"
        and (owner, row.get("method_name")) in TRAIT_DEFAULT_TARGETS
    ):
        return FAMILY_TRAIT_DEFAULT
    return None


def supports(row: dict[str, Any], contract_family: str) -> bool:
    """Return whether this module owns ``row`` under ``contract_family``.

    Ownership requires all three of: the row is a mapping, the caller is
    asking under the uniform ``"exact_vstd"`` contract-family label used for
    every row lacking a newly authored contract, and the row's own
    ``disposition`` is ``"exact_vstd"`` with a recognized structural shape.
    """

    if not isinstance(row, dict):
        return False
    if contract_family != CONTRACT_FAMILY:
        return False
    if row.get("disposition") != "exact_vstd":
        return False
    return _classify(row) is not None


# --------------------------------------------------------------------------
# Shared rendering helpers
# --------------------------------------------------------------------------

_CONCRETE_PREAMBLE = (
    "use vstd::prelude::*;\n"
    "use vstd::std_specs::cmp::*;\n"
    "use core::cmp::Ordering;\n"
    "\n"
    "verus! {\n"
)
_GENERIC_PREAMBLE = (
    "#![feature(sized_hierarchy)]\n"
    "use vstd::prelude::*;\n"
    "use vstd::std_specs::cmp::*;\n"
    "use core::cmp::Ordering;\n"
    "use core::marker::PointeeSized;\n"
    "\n"
    "verus! {\n"
)
_POSTAMBLE = "\n} // verus!\n"


def _quote_reference(row: dict[str, Any], accepted_contract_text: str) -> str:
    """Render ``accepted_contract_text`` as a traceable doc-comment block.

    This is the literal referenced vstd/source text supplied by the caller;
    embedding it verbatim (rather than re-deriving it) is what keeps the
    exact-vstd contract *referenced* instead of redeclared.
    """

    header = (
        f"// referenced target: {row.get('target')}\n"
        f"// referenced vstd binding(s): {row.get('vstd_binding_ids')}\n"
        "// referenced contract text (verbatim, for traceability only):\n"
    )
    body_lines = accepted_contract_text.rstrip("\n").splitlines() or [""]
    quoted = "\n".join(
        f"// {line}" if line.strip() else "//" for line in body_lines
    )
    return header + quoted + "\n"


def _normalize_type(rust_type: str) -> str:
    return rust_type.replace("cmp::Ordering", "Ordering")


def _self_param(rust_type: str) -> str:
    """Rename the reserved ``Self`` placeholder to the ``Self_`` type param.

    Trait-default rows resolve their signature generically over ``Self``;
    ``Self`` cannot be declared as a free-function generic-parameter name in
    Rust, so every occurrence of the whole word ``Self`` is renamed to
    ``Self_`` when building the trait-default templates.
    """

    tokens = []
    current = ""
    for char in rust_type:
        if char.isalnum() or char == "_":
            current += char
        else:
            tokens.append(current)
            tokens.append(char)
            current = ""
    tokens.append(current)
    return "".join("Self_" if token == "Self" else token for token in tokens)


def _wrap(
    preamble: str,
    row: dict[str, Any],
    accepted_contract_text: str,
    accepted_contract_block: str,
    body_block: str,
) -> str:
    return (
        preamble
        + _quote_reference(row, accepted_contract_text)
        + "\n"
        + accepted_contract_block.strip("\n")
        + "\n\n"
        + body_block.strip("\n")
        + "\n"
        + _POSTAMBLE
    )


def _rename_param(name: str) -> str:
    # ``self`` is a reserved keyword and cannot be used as a free-function
    # parameter name; every other resolved-signature parameter name is
    # already a plain identifier and is preserved verbatim.
    return "x" if name == "self" else ("y" if name == "other" else name)


def _resolved_params(row: dict[str, Any]) -> list[tuple[str, str]]:
    inputs = row["signature"]["resolved_inputs"]
    return [
        (_rename_param(entry["name"]), _normalize_type(entry["type"]))
        for entry in inputs
    ]


def _resolved_output(row: dict[str, Any]) -> str:
    return _normalize_type(row["signature"]["resolved_output"])


# --------------------------------------------------------------------------
# Family: primitive_scalar
# --------------------------------------------------------------------------

def _three_way_compare_helper(type_name: str) -> str:
    # A narrow, executable, independently-verified stand-in for the real
    # source's unstable `crate::intrinsics::three_way_compare` compiler
    # intrinsic. Its ensures clause is the same deterministic expression
    # vstd's own `OrdSpecImpl`/`PartialOrdSpecImpl` use for concrete integer
    # types, so it is a faithful (not merely convenient) lowering.
    return (
        f"pub fn __three_way_compare(x: {type_name}, y: {type_name}) -> (r: Ordering)\n"
        "    ensures\n"
        "        r == if x < y { Ordering::Less } else if x > y "
        "{ Ordering::Greater } else { Ordering::Equal },\n"
        "{\n"
        "    if x < y {\n"
        "        Ordering::Less\n"
        "    } else if x > y {\n"
        "        Ordering::Greater\n"
        "    } else {\n"
        "        Ordering::Equal\n"
        "    }\n"
        "}\n"
    )


def _primitive_scalar_deterministic(
    row: dict[str, Any], accepted_contract_text: str
) -> ProofTemplate:
    type_name = row["owner_type"]
    method = row["method_name"]
    params = _resolved_params(row)
    output = _resolved_output(row)
    (x_name, x_type), (y_name, y_type) = params
    dx, dy = f"*{x_name}", f"*{y_name}"

    helper_block = ""
    helper_mutation_fragment = None
    helper_mutation_replacement = None
    source_shape_tokens: tuple[str, ...] = ()
    boundaries: tuple[dict[str, Any], ...] = ()

    if method == "eq":
        accepted_expr = (
            f"r == <{type_name} as PartialEqSpec>::eq_spec(&{x_name}, &{y_name})"
        )
        body_expr = f"{dx} == {dy}"
        mutated_body_expr = f"{dx} != {dy}"
        source_shape_tokens = ("==",)
    elif method == "ne":
        accepted_expr = (
            f"r == !<{type_name} as PartialEqSpec>::eq_spec(&{x_name}, &{y_name})"
        )
        body_expr = f"{dx} != {dy}"
        mutated_body_expr = f"{dx} == {dy}"
        source_shape_tokens = ("!=",)
    elif method == "lt":
        accepted_expr = (
            f"r == (<{type_name} as PartialOrdSpec>::partial_cmp_spec"
            f"(&{x_name}, &{y_name}) == Some(Ordering::Less))"
        )
        body_expr = f"{dx} < {dy}"
        mutated_body_expr = f"{dx} > {dy}"
        source_shape_tokens = ("<",)
    elif method == "gt":
        accepted_expr = (
            f"r == (<{type_name} as PartialOrdSpec>::partial_cmp_spec"
            f"(&{x_name}, &{y_name}) == Some(Ordering::Greater))"
        )
        body_expr = f"{dx} > {dy}"
        mutated_body_expr = f"{dx} < {dy}"
        source_shape_tokens = (">",)
    elif method == "le":
        accepted_expr = (
            f"r == matches!(<{type_name} as PartialOrdSpec>::partial_cmp_spec"
            f"(&{x_name}, &{y_name}), Some(Ordering::Less | Ordering::Equal))"
        )
        body_expr = f"{dx} <= {dy}"
        mutated_body_expr = f"{dx} >= {dy}"
        source_shape_tokens = ("<=",)
    elif method == "ge":
        accepted_expr = (
            f"r == matches!(<{type_name} as PartialOrdSpec>::partial_cmp_spec"
            f"(&{x_name}, &{y_name}), Some(Ordering::Greater | Ordering::Equal))"
        )
        body_expr = f"{dx} >= {dy}"
        mutated_body_expr = f"{dx} <= {dy}"
        source_shape_tokens = (">=",)
    elif method == "partial_cmp":
        accepted_expr = (
            f"r == <{type_name} as PartialOrdSpec>::partial_cmp_spec"
            f"(&{x_name}, &{y_name})"
        )
        body_expr = f"Some(__three_way_compare({dx}, {dy}))"
        mutated_body_expr = body_expr
        helper_block = _three_way_compare_helper(type_name)
        helper_mutation_fragment = (
            "    if x < y {\n"
            "        Ordering::Less\n"
            "    } else if x > y {\n"
            "        Ordering::Greater\n"
            "    } else {\n"
            "        Ordering::Equal\n"
            "    }\n"
            "}\n"
        )
        helper_mutation_replacement = (
            "    if x < y {\n"
            "        Ordering::Greater\n"
            "    } else if x > y {\n"
            "        Ordering::Less\n"
            "    } else {\n"
            "        Ordering::Equal\n"
            "    }\n"
            "}\n"
        )
        source_shape_tokens = ("<", ">", "three_way_compare")
        boundaries = (
            {
                "name": "three_way_compare_narrow_helper",
                "description": (
                    "Lowers the frozen source's unstable "
                    "`crate::intrinsics::three_way_compare` compiler "
                    "intrinsic to a narrow, independently-verified "
                    "executable helper with an identical deterministic "
                    "ensures clause; not claimed as the whole target "
                    "outcome."
                ),
                "whole_target_outcome": False,
            },
        )
    elif method == "cmp":
        accepted_expr = (
            f"r == <{type_name} as OrdSpec>::cmp_spec(&{x_name}, &{y_name})"
        )
        body_expr = f"__three_way_compare({dx}, {dy})"
        mutated_body_expr = body_expr
        helper_block = _three_way_compare_helper(type_name)
        helper_mutation_fragment = (
            "    if x < y {\n"
            "        Ordering::Less\n"
            "    } else if x > y {\n"
            "        Ordering::Greater\n"
            "    } else {\n"
            "        Ordering::Equal\n"
            "    }\n"
            "}\n"
        )
        helper_mutation_replacement = (
            "    if x < y {\n"
            "        Ordering::Greater\n"
            "    } else if x > y {\n"
            "        Ordering::Less\n"
            "    } else {\n"
            "        Ordering::Equal\n"
            "    }\n"
            "}\n"
        )
        source_shape_tokens = ("<", ">", "three_way_compare")
        boundaries = (
            {
                "name": "three_way_compare_narrow_helper",
                "description": (
                    "Lowers the frozen source's unstable "
                    "`crate::intrinsics::three_way_compare` compiler "
                    "intrinsic to a narrow, independently-verified "
                    "executable helper with an identical deterministic "
                    "ensures clause; not claimed as the whole target "
                    "outcome."
                ),
                "whole_target_outcome": False,
            },
        )
    else:
        raise AssertionError(f"unhandled primitive_scalar method {method!r}")

    accepted_block = (
        f"pub open spec fn accepted_contract({x_name}: {type_name}, "
        f"{y_name}: {type_name}, r: {output}) -> bool {{\n"
        f"    {accepted_expr}\n"
        "}\n"
    )
    impl_fn = (
        f"pub fn implementation_target({x_name}: {x_type}, {y_name}: {y_type})"
        f" -> (r: {output})\n"
        f"    ensures accepted_contract({dx}, {dy}, r)\n"
        "{\n"
        f"    {body_expr}\n"
        "}\n"
    )
    completeness_fn = (
        f"pub proof fn completeness_theorem({x_name}: {type_name}, "
        f"{y_name}: {type_name}, result1: {output}, result2: {output})\n"
        "    requires\n"
        f"        accepted_contract({x_name}, {y_name}, result1),\n"
        f"        accepted_contract({x_name}, {y_name}, result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{}\n"
    )

    implementation_proof = _wrap(
        _CONCRETE_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        (helper_block + "\n" + impl_fn) if helper_block else impl_fn,
    )
    completeness_proof = _wrap(
        _CONCRETE_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        completeness_fn,
    )

    if helper_mutation_fragment is not None:
        implementation_mutation = {
            "category": "equality_ordering_distinction",
            "fragment": helper_mutation_fragment,
            "replacement": helper_mutation_replacement,
        }
    else:
        body_fragment = "{\n    " + body_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_body_expr + "\n}\n"
        implementation_mutation = {
            "category": "equality_ordering_distinction",
            "fragment": body_fragment,
            "replacement": body_replacement,
        }
    completeness_mutation = {
        "category": "equality_ordering_distinction",
        "fragment": "result1 == result2",
        "replacement": "result1 != result2",
    }

    return ProofTemplate(
        proof_family=FAMILY_PRIMITIVE_SCALAR,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=boundaries,
        implementation_mutation=implementation_mutation,
        completeness_mutation=completeness_mutation,
    )


def _primitive_scalar(row: dict[str, Any], accepted_contract_text: str) -> ProofTemplate:
    return _primitive_scalar_deterministic(row, accepted_contract_text)


# --------------------------------------------------------------------------
# Family: shared_reference_forwarding
# --------------------------------------------------------------------------

_REF_EQ_LIKE = {
    "eq": ("obeys_eq_spec", "x.eq_spec(y)", "true"),
    "ne": ("obeys_eq_spec", "!x.eq_spec(y)", "false"),
}
_REF_ORD_LIKE = {
    "lt": (
        "obeys_partial_cmp_spec",
        "(x.partial_cmp_spec(y) == Some(Ordering::Less))",
        "false",
    ),
    "gt": (
        "obeys_partial_cmp_spec",
        "(x.partial_cmp_spec(y) == Some(Ordering::Greater))",
        "false",
    ),
    "le": (
        "obeys_partial_cmp_spec",
        "matches!(x.partial_cmp_spec(y), Some(Ordering::Less | Ordering::Equal))",
        "true",
    ),
    "ge": (
        "obeys_partial_cmp_spec",
        "matches!(x.partial_cmp_spec(y), Some(Ordering::Greater | Ordering::Equal))",
        "true",
    ),
}


def _shared_reference_forwarding(
    row: dict[str, Any], accepted_contract_text: str
) -> ProofTemplate:
    method = row["method_name"]
    params = _resolved_params(row)
    output = _resolved_output(row)
    (x_name, x_type), (y_name, y_type) = params
    dx, dy = f"*{x_name}", f"*{y_name}"
    has_b = method != "cmp"

    if method in _REF_EQ_LIKE:
        obeys, spec_expr, stub = _REF_EQ_LIKE[method]
        bound_trait, spec_trait = "PartialEq", "PartialEqSpec"
        body_expr = {"eq": f"{dx} == {dy}", "ne": f"{dx} != {dy}"}[method]
    elif method in _REF_ORD_LIKE:
        obeys, spec_expr, stub = _REF_ORD_LIKE[method]
        bound_trait, spec_trait = "PartialOrd", "PartialOrdSpec"
        body_expr = {
            "lt": f"{dx} < {dy}",
            "gt": f"{dx} > {dy}",
            "le": f"{dx} <= {dy}",
            "ge": f"{dx} >= {dy}",
        }[method]
    elif method == "partial_cmp":
        obeys, spec_expr, stub = "obeys_partial_cmp_spec", "x.partial_cmp_spec(y)", "None"
        bound_trait, spec_trait = "PartialOrd", "PartialOrdSpec"
        body_expr = f"({dx}).partial_cmp({dy})"
    elif method == "cmp":
        obeys, spec_expr, stub = "obeys_cmp_spec", "x.cmp_spec(y)", "Ordering::Equal"
        bound_trait, spec_trait = "Ord", "OrdSpec"
        body_expr = f"({dx}).cmp({dy})"
    else:
        raise AssertionError(f"unhandled shared_reference_forwarding method {method!r}")

    if has_b:
        generics = (
            f"A: PointeeSized + {bound_trait}<B> + {spec_trait}<B>, B: PointeeSized"
        )
        accepted_params = f"x: &A, y: &B, r: {output}"
    else:
        generics = f"A: PointeeSized + {bound_trait} + {spec_trait}"
        accepted_params = f"x: &A, y: &A, r: {output}"

    accepted_block = (
        f"pub open spec fn accepted_contract<{generics}>({accepted_params}) -> bool {{\n"
        f"    A::{obeys}() ==> r == {spec_expr}\n"
        "}\n"
    )
    impl_fn = (
        f"pub fn implementation_target<{generics}>({x_name}: {x_type}, "
        f"{y_name}: {y_type}) -> (r: {output})\n"
        f"    ensures accepted_contract({dx}, {dy}, r)\n"
        "{\n"
        f"    {body_expr}\n"
        "}\n"
    )
    completeness_fn = (
        f"pub proof fn completeness_theorem<{generics}>(x: &A, y: &"
        f"{'B' if has_b else 'A'}, result1: {output}, result2: {output})\n"
        "    requires\n"
        "        accepted_contract(x, y, result1),\n"
        "        accepted_contract(x, y, result2),\n"
        f"        A::{obeys}(),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{}\n"
    )

    implementation_proof = _wrap(
        _GENERIC_PREAMBLE, row, accepted_contract_text, accepted_block, impl_fn
    )
    completeness_proof = _wrap(
        _GENERIC_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        completeness_fn,
    )

    body_fragment = "{\n    " + body_expr + "\n}\n"
    body_replacement = "{\n    " + stub + "\n}\n"

    boundaries = (
        {
            "name": "reference_forwarding_delegation",
            "description": (
                "Delegates entirely to the wrapped type A's own "
                f"{spec_trait} relation through the blanket `&A` "
                "PartialEq/PartialOrd/Ord impl; no independent semantics "
                "are asserted beyond forwarding. Not claimed as the whole "
                "target outcome."
            ),
            "whole_target_outcome": False,
        },
    )

    return ProofTemplate(
        proof_family=FAMILY_SHARED_REFERENCE_FORWARDING,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=(body_expr.strip(),),
        boundaries=boundaries,
        implementation_mutation={
            "category": "forwarding",
            "fragment": body_fragment,
            "replacement": body_replacement,
        },
        completeness_mutation={
            "category": "forwarding",
            "fragment": "result1 == result2",
            "replacement": "result1 != result2",
        },
    )


# --------------------------------------------------------------------------
# Family: ordering_inherent
# --------------------------------------------------------------------------

# method -> (accepted/body boolean expression, mutated boolean expression)
_ORDERING_IS_METHODS = {
    "is_eq": ("matches!(x, Ordering::Equal)", "matches!(x, Ordering::Less)"),
    "is_ne": ("!matches!(x, Ordering::Equal)", "!matches!(x, Ordering::Less)"),
    "is_lt": ("matches!(x, Ordering::Less)", "matches!(x, Ordering::Greater)"),
    "is_gt": ("matches!(x, Ordering::Greater)", "matches!(x, Ordering::Less)"),
    "is_le": ("!matches!(x, Ordering::Greater)", "!matches!(x, Ordering::Less)"),
    "is_ge": ("!matches!(x, Ordering::Less)", "!matches!(x, Ordering::Greater)"),
}


def _ordering_inherent(row: dict[str, Any], accepted_contract_text: str) -> ProofTemplate:
    method = row["method_name"]
    params = _resolved_params(row)
    output = _resolved_output(row)

    if method in _ORDERING_IS_METHODS:
        (x_name, x_type), = params
        expr, mutated_expr = _ORDERING_IS_METHODS[method]
        accepted_block = (
            f"pub open spec fn accepted_contract({x_name}: Ordering, r: {output})"
            " -> bool {\n"
            f"    r == {expr}\n"
            "}\n"
        )
        impl_fn = (
            f"pub fn implementation_target({x_name}: {x_type}) -> (r: {output})\n"
            f"    ensures accepted_contract({x_name}, r)\n"
            "{\n"
            f"    {expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem({x_name}: Ordering, "
            f"result1: {output}, result2: {output})\n"
            "    requires\n"
            f"        accepted_contract({x_name}, result1),\n"
            f"        accepted_contract({x_name}, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        body_fragment = "{\n    " + expr + "\n}\n"
        body_replacement = "{\n    " + mutated_expr + "\n}\n"
        source_shape_tokens = (expr,)
    elif method == "reverse":
        (x_name, x_type), = params
        match_expr = (
            f"match {x_name} {{\n"
            "        Ordering::Less => Ordering::Greater,\n"
            "        Ordering::Equal => Ordering::Equal,\n"
            "        Ordering::Greater => Ordering::Less,\n"
            "    }"
        )
        mutated_match_expr = (
            f"match {x_name} {{\n"
            "        Ordering::Less => Ordering::Less,\n"
            "        Ordering::Equal => Ordering::Equal,\n"
            "        Ordering::Greater => Ordering::Greater,\n"
            "    }"
        )
        accepted_block = (
            f"pub open spec fn accepted_contract({x_name}: Ordering, r: {output})"
            " -> bool {\n"
            f"    r == {match_expr}\n"
            "}\n"
        )
        impl_fn = (
            f"pub fn implementation_target({x_name}: {x_type}) -> (r: {output})\n"
            f"    ensures accepted_contract({x_name}, r)\n"
            "{\n"
            f"    {match_expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem({x_name}: Ordering, "
            f"result1: {output}, result2: {output})\n"
            "    requires\n"
            f"        accepted_contract({x_name}, result1),\n"
            f"        accepted_contract({x_name}, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        body_fragment = "{\n    " + match_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_match_expr + "\n}\n"
        source_shape_tokens = ("match",)
    elif method == "then":
        (x_name, x_type), (y_name, y_type) = params
        match_expr = (
            f"match {x_name} {{\n"
            f"        Ordering::Equal => {y_name},\n"
            f"        _ => {x_name},\n"
            "    }"
        )
        mutated_match_expr = (
            f"match {x_name} {{\n"
            f"        Ordering::Equal => {x_name},\n"
            f"        _ => {y_name},\n"
            "    }"
        )
        accepted_expr = (
            f"if matches!({x_name}, Ordering::Equal) {{ {y_name} }} else {{ {x_name} }}"
        )
        accepted_block = (
            f"pub open spec fn accepted_contract({x_name}: Ordering, "
            f"{y_name}: Ordering, r: {output}) -> bool {{\n"
            f"    r == {accepted_expr}\n"
            "}\n"
        )
        impl_fn = (
            f"pub fn implementation_target({x_name}: {x_type}, {y_name}: {y_type})"
            f" -> (r: {output})\n"
            f"    ensures accepted_contract({x_name}, {y_name}, r)\n"
            "{\n"
            f"    {match_expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem({x_name}: Ordering, "
            f"{y_name}: Ordering, result1: {output}, result2: {output})\n"
            "    requires\n"
            f"        accepted_contract({x_name}, {y_name}, result1),\n"
            f"        accepted_contract({x_name}, {y_name}, result2),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        body_fragment = "{\n    " + match_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_match_expr + "\n}\n"
        source_shape_tokens = ("match",)
    else:
        raise AssertionError(f"unhandled ordering_inherent method {method!r}")

    implementation_proof = _wrap(
        _CONCRETE_PREAMBLE, row, accepted_contract_text, accepted_block, impl_fn
    )
    completeness_proof = _wrap(
        _CONCRETE_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        completeness_fn,
    )

    return ProofTemplate(
        proof_family=FAMILY_ORDERING_INHERENT,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=(),
        implementation_mutation={
            "category": "branch_reversal",
            "fragment": body_fragment,
            "replacement": body_replacement,
        },
        completeness_mutation={
            "category": "branch_reversal",
            "fragment": "result1 == result2",
            "replacement": "result1 != result2",
        },
    )


# --------------------------------------------------------------------------
# Family: option_relational
# --------------------------------------------------------------------------

def _option_relational(row: dict[str, Any], accepted_contract_text: str) -> ProofTemplate:
    method = row["method_name"]
    params = _resolved_params(row)
    output = _resolved_output(row)
    (x_name, x_type), (y_name, y_type) = params

    if method == "eq":
        bound_trait, spec_trait, obeys = "PartialEq", "PartialEqSpec", "obeys_eq_spec"
        none_none, some_some = "true", "a.eq_spec(&b)"
        none_some = some_none = "false"
        exec_none_some = exec_some_none = "false"
        exec_some_some = "a.eq(b)"
        exec_none_none = "true"
    elif method == "partial_cmp":
        bound_trait, spec_trait, obeys = "PartialOrd", "PartialOrdSpec", "obeys_partial_cmp_spec"
        none_none = "Some(Ordering::Equal)"
        none_some = "Some(Ordering::Less)"
        some_none = "Some(Ordering::Greater)"
        some_some = "a.partial_cmp_spec(&b)"
        exec_none_none = "Some(Ordering::Equal)"
        exec_none_some = "Some(Ordering::Less)"
        exec_some_none = "Some(Ordering::Greater)"
        exec_some_some = "a.partial_cmp(b)"
    elif method == "cmp":
        bound_trait, spec_trait, obeys = "Ord", "OrdSpec", "obeys_cmp_spec"
        none_none = "Ordering::Equal"
        none_some = "Ordering::Less"
        some_none = "Ordering::Greater"
        some_some = "a.cmp_spec(&b)"
        exec_none_none = "Ordering::Equal"
        exec_none_some = "Ordering::Less"
        exec_some_none = "Ordering::Greater"
        exec_some_some = "a.cmp(b)"
    else:
        raise AssertionError(f"unhandled option_relational method {method!r}")

    accepted_match = (
        f"match ({x_name}, {y_name}) {{\n"
        f"        (Option::None, Option::None) => {none_none},\n"
        f"        (Option::None, Option::Some(_)) => {none_some},\n"
        f"        (Option::Some(_), Option::None) => {some_none},\n"
        f"        (Option::Some(a), Option::Some(b)) => {some_some},\n"
        "    }"
    )
    accepted_block = (
        f"pub open spec fn accepted_contract<T: {bound_trait} + {spec_trait}>"
        f"({x_name}: Option<T>, {y_name}: Option<T>, r: {output}) -> bool {{\n"
        f"    T::{obeys}() ==> r == {accepted_match}\n"
        "}\n"
    )
    exec_match = (
        f"match ({x_name}, {y_name}) {{\n"
        f"        (None, None) => {exec_none_none},\n"
        f"        (None, Some(_)) => {exec_none_some},\n"
        f"        (Some(_), None) => {exec_some_none},\n"
        f"        (Some(a), Some(b)) => {exec_some_some},\n"
        "    }"
    )
    impl_fn = (
        f"pub fn implementation_target<T: {bound_trait} + {spec_trait}>"
        f"({x_name}: {x_type}, {y_name}: {y_type}) -> (r: {output})\n"
        f"    ensures accepted_contract(*{x_name}, *{y_name}, r)\n"
        "{\n"
        f"    {exec_match}\n"
        "}\n"
    )
    completeness_fn = (
        f"pub proof fn completeness_theorem<T: {bound_trait} + {spec_trait}>"
        f"({x_name}: Option<T>, {y_name}: Option<T>, result1: {output}, "
        f"result2: {output})\n"
        "    requires\n"
        f"        accepted_contract({x_name}, {y_name}, result1),\n"
        f"        accepted_contract({x_name}, {y_name}, result2),\n"
        f"        T::{obeys}(),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{}\n"
    )

    implementation_proof = _wrap(
        _CONCRETE_PREAMBLE, row, accepted_contract_text, accepted_block, impl_fn
    )
    completeness_proof = _wrap(
        _CONCRETE_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        completeness_fn,
    )

    # branch_reversal: for `partial_cmp`/`cmp`, swap the (None, Some) /
    # (Some, None) cross arms, which is the precise place the real source
    # encodes "None is smaller". For `eq` those two cross arms both already
    # produce `false`, so instead reverse the (None, None) base case, which
    # is the analogous branch-selection bug for a two-valued relation.
    if method == "eq":
        mutated_exec_match = (
            f"match ({x_name}, {y_name}) {{\n"
            f"        (None, None) => false,\n"
            f"        (None, Some(_)) => {exec_none_some},\n"
            f"        (Some(_), None) => {exec_some_none},\n"
            f"        (Some(a), Some(b)) => {exec_some_some},\n"
            "    }"
        )
    else:
        mutated_exec_match = (
            f"match ({x_name}, {y_name}) {{\n"
            f"        (None, None) => {exec_none_none},\n"
            f"        (None, Some(_)) => {exec_some_none},\n"
            f"        (Some(_), None) => {exec_none_some},\n"
            f"        (Some(a), Some(b)) => {exec_some_some},\n"
            "    }"
        )
    body_fragment = "{\n    " + exec_match + "\n}\n"
    body_replacement = "{\n    " + mutated_exec_match + "\n}\n"

    return ProofTemplate(
        proof_family=FAMILY_OPTION_RELATIONAL,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=("match", "None", "Some"),
        boundaries=(),
        implementation_mutation={
            "category": "branch_reversal",
            "fragment": body_fragment,
            "replacement": body_replacement,
        },
        completeness_mutation={
            "category": "branch_reversal",
            "fragment": "result1 == result2",
            "replacement": "result1 != result2",
        },
    )


# --------------------------------------------------------------------------
# Family: trait_default
# --------------------------------------------------------------------------

_DEFAULT_PARTIAL_ORD_METHODS = {
    "lt": ("Some(Ordering::Less)", False, "is_lt", "is_gt"),
    "gt": ("Some(Ordering::Greater)", False, "is_gt", "is_lt"),
    "le": ("Some(Ordering::Less | Ordering::Equal)", True, "is_le", "is_ge"),
    "ge": ("Some(Ordering::Greater | Ordering::Equal)", True, "is_ge", "is_le"),
}


def _trait_default_params(row: dict[str, Any]) -> list[tuple[str, str]]:
    raw = row["signature"]["resolved_inputs"]
    return [
        (_rename_param(entry["name"]), _self_param(_normalize_type(entry["type"])))
        for entry in raw
    ]


def _trait_default(row: dict[str, Any], accepted_contract_text: str) -> ProofTemplate:
    trait_name = row["trait_name"]
    method = row["method_name"]
    params = _trait_default_params(row)
    output = _self_param(_normalize_type(row["signature"]["resolved_output"]))

    if trait_name == "PartialEq":
        # PartialEq::ne default: `!self.eq(other)`.
        (x_name, x_type), (y_name, y_type) = params
        generics = (
            "Self_: PointeeSized + PartialEq<Rhs> + PartialEqSpec<Rhs>, Rhs: PointeeSized"
        )
        accepted_expr = f"!{x_name}.eq_spec({y_name})"
        accepted_block = (
            f"pub open spec fn accepted_contract<{generics}>({x_name}: &Self_, "
            f"{y_name}: &Rhs, r: bool) -> bool {{\n"
            f"    Self_::obeys_eq_spec() ==> r == {accepted_expr}\n"
            "}\n"
        )
        body_expr = f"!{x_name}.eq({y_name})"
        mutated_body_expr = f"{x_name}.eq({y_name})"
        impl_fn = (
            f"pub fn implementation_target<{generics}>({x_name}: {x_type}, "
            f"{y_name}: {y_type}) -> (r: bool)\n"
            f"    ensures accepted_contract({x_name}, {y_name}, r)\n"
            "{\n"
            f"    {body_expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem<{generics}>({x_name}: &Self_, "
            f"{y_name}: &Rhs, result1: bool, result2: bool)\n"
            "    requires\n"
            f"        accepted_contract({x_name}, {y_name}, result1),\n"
            f"        accepted_contract({x_name}, {y_name}, result2),\n"
            "        Self_::obeys_eq_spec(),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        category = "equality_ordering_distinction"
        body_fragment = "{\n    " + body_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_body_expr + "\n}\n"
        source_shape_tokens = ("!", ".eq(")
        boundaries: tuple[dict[str, Any], ...] = ()
    elif trait_name == "PartialOrd":
        (x_name, x_type), (y_name, y_type) = params
        generics = (
            "Self_: PointeeSized + PartialOrd<Rhs> + PartialOrdSpec<Rhs>, "
            "Rhs: PointeeSized"
        )
        target, use_matches, is_method, mutated_is_method = (
            _DEFAULT_PARTIAL_ORD_METHODS[method]
        )
        if use_matches:
            accepted_expr = f"matches!({x_name}.partial_cmp_spec({y_name}), {target})"
        else:
            accepted_expr = f"({x_name}.partial_cmp_spec({y_name}) == {target})"
        accepted_block = (
            f"pub open spec fn accepted_contract<{generics}>({x_name}: &Self_, "
            f"{y_name}: &Rhs, r: bool) -> bool {{\n"
            f"    Self_::obeys_partial_cmp_spec() ==> r == {accepted_expr}\n"
            "}\n"
        )
        body_expr = (
            f"match {x_name}.partial_cmp({y_name}) {{\n"
            f"        Some(o) => o.{is_method}(),\n"
            "        None => false,\n"
            "    }"
        )
        mutated_body_expr = (
            f"match {x_name}.partial_cmp({y_name}) {{\n"
            f"        Some(o) => o.{mutated_is_method}(),\n"
            "        None => false,\n"
            "    }"
        )
        impl_fn = (
            f"pub fn implementation_target<{generics}>({x_name}: {x_type}, "
            f"{y_name}: {y_type}) -> (r: bool)\n"
            f"    ensures accepted_contract({x_name}, {y_name}, r)\n"
            "{\n"
            f"    {body_expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem<{generics}>({x_name}: &Self_, "
            f"{y_name}: &Rhs, result1: bool, result2: bool)\n"
            "    requires\n"
            f"        accepted_contract({x_name}, {y_name}, result1),\n"
            f"        accepted_contract({x_name}, {y_name}, result2),\n"
            "        Self_::obeys_partial_cmp_spec(),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        category = "equality_ordering_distinction"
        body_fragment = "{\n    " + body_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_body_expr + "\n}\n"
        source_shape_tokens = ("partial_cmp", is_method)
        boundaries = ()
    elif method in ("max", "min"):
        (x_name, x_type), (y_name, y_type) = params
        generics = "Self_: Ord + PartialOrdSpec + OrdSpec"
        less_branch, else_branch = (
            (x_name, y_name) if method == "max" else (y_name, x_name)
        )
        accepted_expr = (
            f"if {y_name}.partial_cmp_spec(&{x_name}) == Some(Ordering::Less) "
            f"{{ {less_branch} }} else {{ {else_branch} }}"
        )
        accepted_block = (
            f"pub open spec fn accepted_contract<{generics}>({x_name}: Self_, "
            f"{y_name}: Self_, r: Self_) -> bool {{\n"
            f"    Self_::obeys_partial_cmp_spec() ==> r == {accepted_expr}\n"
            "}\n"
        )
        body_expr = f"if {y_name} < {x_name} {{ {less_branch} }} else {{ {else_branch} }}"
        mutated_body_expr = (
            f"if {y_name} < {x_name} {{ {else_branch} }} else {{ {less_branch} }}"
        )
        impl_fn = (
            f"pub fn implementation_target<{generics}>({x_name}: {x_type}, "
            f"{y_name}: {y_type}) -> (r: Self_)\n"
            f"    ensures accepted_contract({x_name}, {y_name}, r)\n"
            "{\n"
            f"    {body_expr}\n"
            "}\n"
        )
        completeness_fn = (
            f"pub proof fn completeness_theorem<{generics}>({x_name}: Self_, "
            f"{y_name}: Self_, result1: Self_, result2: Self_)\n"
            "    requires\n"
            f"        accepted_contract({x_name}, {y_name}, result1),\n"
            f"        accepted_contract({x_name}, {y_name}, result2),\n"
            "        Self_::obeys_partial_cmp_spec(),\n"
            "    ensures\n"
            "        result1 == result2,\n"
            "{}\n"
        )
        category = "branch_reversal"
        body_fragment = "{\n    " + body_expr + "\n}\n"
        body_replacement = "{\n    " + mutated_body_expr + "\n}\n"
        source_shape_tokens = ("<", "if", "else")
        boundaries = ()
    else:
        raise AssertionError(
            f"unhandled trait_default target {trait_name!r}::{method!r}"
        )

    implementation_proof = _wrap(
        _GENERIC_PREAMBLE, row, accepted_contract_text, accepted_block, impl_fn
    )
    completeness_proof = _wrap(
        _GENERIC_PREAMBLE,
        row,
        accepted_contract_text,
        accepted_block,
        completeness_fn,
    )

    return ProofTemplate(
        proof_family=FAMILY_TRAIT_DEFAULT,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=boundaries,
        implementation_mutation={
            "category": category,
            "fragment": body_fragment,
            "replacement": body_replacement,
        },
        completeness_mutation={
            "category": category,
            "fragment": "result1 == result2",
            "replacement": "result1 != result2",
        },
    )


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

_BUILDERS = {
    FAMILY_PRIMITIVE_SCALAR: _primitive_scalar,
    FAMILY_SHARED_REFERENCE_FORWARDING: _shared_reference_forwarding,
    FAMILY_ORDERING_INHERENT: _ordering_inherent,
    FAMILY_OPTION_RELATIONAL: _option_relational,
    FAMILY_TRAIT_DEFAULT: _trait_default,
}


def render(
    row: dict[str, Any],
    contract_family: str,
    accepted_contract_text: str,
) -> ProofTemplate:
    """Render the `ProofTemplate` for an owned exact-vstd row.

    Raises :class:`ValueError` if this module does not own ``row`` under
    ``contract_family`` (see `supports`), or if ``accepted_contract_text``
    is not a non-empty string.
    """

    if not supports(row, contract_family):
        raise ValueError(
            "tools.proof_templates_exact does not own row "
            f"{row.get('row_id') if isinstance(row, dict) else row!r} "
            f"under contract_family {contract_family!r}"
        )
    if not isinstance(accepted_contract_text, str) or not accepted_contract_text.strip():
        raise ValueError(
            "accepted_contract_text must be a non-empty string containing "
            "the literal referenced vstd/source contract text"
        )
    family = _classify(row)
    assert family is not None  # guaranteed by supports() above
    return _BUILDERS[family](row, accepted_contract_text)
