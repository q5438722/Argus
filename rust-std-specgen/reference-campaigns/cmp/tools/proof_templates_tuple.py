"""Independent implementation/completeness proof rendering for core::tuple's
``PartialEq``/``Eq``/``PartialOrd``/``Ord`` short-circuit family.

This module owns exactly the 96 ``core/src/tuple.rs`` rows produced by the
``tuple_impls!`` macro for arities 1..=12: ``eq``, ``ne``, ``partial_cmp``,
``cmp``, ``lt``, ``le``, ``gt`` and ``ge``. Every one of those methods walks
the tuple's fields from index zero, in source order, and stops at the first
component whose comparison already decides the outcome:

* ``eq``/``ne`` fold the fields with ``&&``/``||`` and stop at the first
  ``false``/``true`` component.
* ``cmp``/``partial_cmp`` stop at the first component whose ``Ordering`` (or
  ``Option<Ordering>``) is not ``Equal``/``Some(Equal)``.
* ``lt``/``le``/``gt``/``ge`` call ``partial_cmp`` once for every field but
  the last and implement the private ``__chaining_*`` mapping explicitly:
  ``Some(Equal)`` continues, ``Some(non-equal)`` applies the requested
  relation, and ``None`` returns ``false``. The last field uses the public
  relation directly.

The rendered proofs discharge the accepted generated contract *as written*:

* ``implementation``'s ``ensures`` is the accepted ``assume_specification``
  ``ensures`` block copied verbatim out of the accepted contract text, so the
  global ``cmp_tuple_observation_count`` and direct ``partial_cmp`` observations
  are the actual proof obligation. There is no locally invented
  ``observation_count`` and no uninterpreted chaining result.
* The only thing that cannot be derived from the executed Rust body is how
  many components the *global* observation counter attributes to the call.
  That single fact is supplied by one narrow trace/count boundary whose
  ``ensures`` is exactly the ``cmp_tuple_observation_count`` equation for the
  observed short-circuit prefix -- it never mentions, and never supplies, the
  target's result. It is a plain proof function rather than a broadcast
  axiom, so it is only ever applied to the outcomes the executed path really
  observed, in source order.
* Every other trusted surface is a single-component dispatch helper.

``render`` produces two *standalone* Verus source strings per row -- an
``implementation_proof.rs`` with an executable, non-external ``pub fn
implementation`` matching the resolved target signature (``self`` renamed to
``left``), and a ``completeness_proof.rs`` that proves two accepted-contract
observations sharing the same component-output environment and the same exact
global observation count must agree.
"""

from __future__ import annotations

import re
from typing import Any

from tools.proof_template_common import ProofTemplate

SOURCE_FILE = "core/src/tuple.rs"
CONTRACT_FAMILY = "tuple_short_circuit"
MIN_ARITY = 1
MAX_ARITY = 12

# method_name -> (kind, trait_name)
_METHOD_KIND: dict[str, str] = {
    "eq": "and_or",
    "ne": "and_or",
    "cmp": "ord",
    "partial_cmp": "partial_ord_value",
    "lt": "chain_bool",
    "le": "chain_bool",
    "gt": "chain_bool",
    "ge": "chain_bool",
}

_METHOD_TRAIT: dict[str, str] = {
    "eq": "PartialEq",
    "ne": "PartialEq",
    "cmp": "Ord",
    "partial_cmp": "PartialOrd",
    "lt": "PartialOrd",
    "le": "PartialOrd",
    "gt": "PartialOrd",
    "ge": "PartialOrd",
}

_METHOD_OPERATION: dict[str, str] = {
    "eq": "Eq",
    "ne": "Ne",
    "cmp": "Cmp",
    "partial_cmp": "PartialCmp",
    "lt": "Lt",
    "le": "Le",
    "gt": "Gt",
    "ge": "Ge",
}

_METHOD_OUTPUT: dict[str, str] = {
    "eq": "bool",
    "ne": "bool",
    "cmp": "core::cmp::Ordering",
    "partial_cmp": "Option<core::cmp::Ordering>",
    "lt": "bool",
    "le": "bool",
    "gt": "bool",
    "ge": "bool",
}

# The component outcome type each kind observes per field.
_KIND_COMPONENT_TYPE: dict[str, str] = {
    "and_or": "bool",
    "ord": "core::cmp::Ordering",
    "partial_ord_value": "Option<core::cmp::Ordering>",
}

_SUPPORTED_METHODS = frozenset(_METHOD_KIND)

# ---------------------------------------------------------------------------
# Frozen shared vocabulary
# ---------------------------------------------------------------------------
#
# Standalone Verus modules cannot `use` ``specs/cmp_shared_vocabulary.rs``
# (it is a bare ``verus!{}`` fragment, not a crate), so the exact components
# the accepted tuple contracts reference are reproduced here byte-identically
# to the frozen file. ``tests/test_proof_templates_tuple.py`` pins that
# byte-identity.

VOCABULARY_ITEMS: tuple[str, ...] = (
    """pub enum CmpOperation {
    Eq,
    Ne,
    PartialCmp,
    Cmp,
    Lt,
    Le,
    Gt,
    Ge,
}""",
    """pub enum CmpRelation {
    Lt,
    Le,
    Gt,
    Ge,
}""",
    """pub open spec fn cmp_relation_holds(
    relation: CmpRelation,
    ordering: core::cmp::Ordering,
) -> bool {
    match relation {
        CmpRelation::Lt => ordering == core::cmp::Ordering::Less,
        CmpRelation::Le => ordering != core::cmp::Ordering::Greater,
        CmpRelation::Gt => ordering == core::cmp::Ordering::Greater,
        CmpRelation::Ge => ordering != core::cmp::Ordering::Less,
    }
}""",
    """pub uninterp spec fn cmp_tuple_observation_count<L: ?Sized, R: ?Sized>(
    operation: CmpOperation,
    left: &L,
    right: &R,
) -> nat;""",
    """pub open spec fn cmp_tuple_chaining_trigger<T>(value: T) -> bool {
    true
}""",
)

_VOCABULARY_HEADER = (
    "// Frozen `specs/cmp_shared_vocabulary.rs` components used verbatim by the\n"
    "// accepted contract below. A standalone Verus module cannot `use` the\n"
    "// frozen fragment, so the source-identical definitions are reproduced.\n"
    "// `cmp_tuple_observation_count` stays uninterpreted here exactly as it is\n"
    "// in the frozen vocabulary."
)

VOCABULARY_BLOCK = _VOCABULARY_HEADER + "\n" + "\n\n".join(VOCABULARY_ITEMS)


def _matching_shape(row: dict[str, Any]) -> dict[str, Any]:
    shape = row.get("matching_shape")
    return shape if isinstance(shape, dict) else {}


def _type_parameters(row: dict[str, Any]) -> list[str]:
    params = _matching_shape(row).get("type_parameters")
    return list(params) if isinstance(params, list) else []


def supports(row: dict[str, Any], contract_family: str) -> bool:
    """Return True exactly for the 96 tuple short-circuit rows this module owns."""

    if contract_family != CONTRACT_FAMILY:
        return False
    if not isinstance(row, dict):
        return False
    if row.get("source_file") != SOURCE_FILE:
        return False
    method_name = row.get("method_name")
    if method_name not in _SUPPORTED_METHODS:
        return False
    type_params = _type_parameters(row)
    arity = len(type_params)
    if not (MIN_ARITY <= arity <= MAX_ARITY):
        return False
    if len(set(type_params)) != arity:
        return False
    target = row.get("target")
    if not isinstance(target, str) or not target:
        return False
    trait_name = row.get("trait_name")
    if trait_name is not None and trait_name != _METHOD_TRAIT[method_name]:
        return False
    return True


def _tuple_type(type_params: list[str]) -> str:
    if len(type_params) == 1:
        return f"({type_params[0]},)"
    return "(" + ", ".join(type_params) + ")"


def _generics(type_params: list[str], bound: str) -> str:
    return ", ".join(f"{name}: {bound}" for name in type_params)


def _row_slug(row: dict[str, Any], arity: int, method: str) -> str:
    row_id = str(row.get("row_id") or row.get("identity_key") or "row")
    safe = re.sub(r"[^0-9A-Za-z]+", "_", row_id).strip("_")
    return f"tuple_a{arity}_{method}_{safe}"


def _marker(tag: str, slug: str) -> str:
    return f"/* MUTATION::{tag}::{slug} */"


def _substitute(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(name) for name in mapping) + r")\b"
    )
    return pattern.sub(lambda match: mapping[match.group(1)], text)


# ---------------------------------------------------------------------------
# Accepted contract parsing
# ---------------------------------------------------------------------------


class AcceptedContractError(ValueError):
    """Raised when the accepted contract text cannot be parsed exactly."""


class _AcceptedContract:
    """The accepted ``assume_specification`` ensures block, split into the
    exact pieces the rendered proof has to discharge.

    Nothing here is re-derived or paraphrased: ``clause_block`` is copied
    verbatim into ``implementation``'s ``ensures`` and every other field is a
    verbatim slice of it (only the existential binder names of a contract that
    binds the *result* itself are alpha-renamed to ``last`` so they can be
    ordinary function parameters).
    """

    __slots__ = (
        "clause_block",
        "clause_lines",
        "binders",
        "observations",
        "result_equation",
        "count_conjunct",
        "relation_body",
    )

    def __init__(
        self,
        clause_lines: list[str],
        binders: list[tuple[str, str]],
        observations: list[str],
        result_equation: str,
        count_conjunct: str,
        relation_body: str,
    ) -> None:
        self.clause_lines = clause_lines
        self.clause_block = "\n".join(clause_lines)
        self.binders = binders
        self.observations = observations
        self.result_equation = result_equation
        self.count_conjunct = count_conjunct
        self.relation_body = relation_body

    @property
    def binder_names(self) -> list[str]:
        return [name for name, _ in self.binders]


def _split_binders(text: str) -> list[tuple[str, str]]:
    binders: list[tuple[str, str]] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, type_name = part.partition(":")
        if not type_name:
            raise AcceptedContractError(f"unparsable existential binder: {part!r}")
        binders.append((name.strip(), type_name.strip()))
    return binders


def parse_accepted_contract(
    accepted_contract_text: str,
    output_type: str,
) -> _AcceptedContract:
    """Split the accepted contract's ``ensures`` block into its exact pieces."""

    lines = accepted_contract_text.splitlines()
    try:
        start = lines.index("    ensures")
    except ValueError as error:  # pragma: no cover - defensive
        raise AcceptedContractError("accepted contract has no ensures block") from error
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].strip() == ";"),
        None,
    )
    if end is None:
        raise AcceptedContractError("accepted contract ensures block is unterminated")
    clause_lines = lines[start + 1:end]
    if not clause_lines:
        raise AcceptedContractError("accepted contract ensures block is empty")

    head = clause_lines[0].strip()
    if head.startswith("exists|"):
        if not head.endswith("|"):
            raise AcceptedContractError(f"unparsable existential head: {head!r}")
        binders = _split_binders(head[len("exists|"):-1])
        conjuncts: list[str] = []
        for index, raw in enumerate(clause_lines[1:]):
            piece = raw.strip()
            last = index == len(clause_lines) - 2
            if last:
                if not piece.endswith(","):
                    raise AcceptedContractError(f"unterminated conjunct: {piece!r}")
                conjuncts.append(piece[:-1])
            else:
                if not piece.endswith(" &&"):
                    raise AcceptedContractError(f"unjoined conjunct: {piece!r}")
                conjuncts.append(piece[:-3])
        if len(conjuncts) < 3:
            raise AcceptedContractError("accepted contract has too few conjuncts")
        observations = conjuncts[:-2]
        result_equation = conjuncts[-2]
        count_conjunct = conjuncts[-1]
        relation_body = "\n".join(
            [f"    {head}"] + [f"        {line.strip()}" for line in clause_lines[1:]]
        ).rstrip()
        if relation_body.endswith(","):
            relation_body = relation_body[:-1]
    else:
        clauses = []
        for raw in clause_lines:
            piece = raw.strip()
            if not piece.endswith(","):
                raise AcceptedContractError(f"unterminated clause: {piece!r}")
            clauses.append(piece[:-1])
        if len(clauses) < 2:
            raise AcceptedContractError("accepted contract has too few clauses")
        # This shape binds the target's own `result` rather than an existential
        # witness; alpha-rename it to `last` so the same machinery applies.
        binders = [("last", output_type)]
        observations = [
            _substitute(clause, {"result": "last"}) for clause in clauses[:-1]
        ]
        result_equation = "result == last"
        count_conjunct = clauses[-1]
        relation_body = "\n    && ".join(
            f"({clause})" for clause in clauses
        )
        relation_body = "    " + relation_body

    if not count_conjunct.startswith("cmp_tuple_observation_count("):
        raise AcceptedContractError(
            "accepted contract does not end in a cmp_tuple_observation_count "
            f"conjunct: {count_conjunct!r}"
        )
    if not re.search(r"\bresult\b", result_equation):
        raise AcceptedContractError(
            f"accepted contract result conjunct does not bind result: {result_equation!r}"
        )
    return _AcceptedContract(
        clause_lines=clause_lines,
        binders=binders,
        observations=observations,
        result_equation=result_equation,
        count_conjunct=count_conjunct,
        relation_body=relation_body,
    )


# ---------------------------------------------------------------------------
# Kind-specific rendering
# ---------------------------------------------------------------------------


class _KindResult:
    __slots__ = (
        "helper_fns",
        "impl_body",
        "boundaries",
        "impl_mutation",
        "impl_mutations",
        "trigger_terms",
    )


def _count_boundary(
    slug: str,
    contract: _AcceptedContract,
    type_params: list[str],
    bound: str,
    method: str,
) -> tuple[str, str, dict[str, Any]]:
    """Render the single narrow trace/count boundary.

    Its ``ensures`` is *only* the accepted contract's
    ``cmp_tuple_observation_count`` equation for the observed short-circuit
    prefix -- it never mentions the target's result, so it cannot stand in for
    the whole target outcome.
    """

    name = f"{slug}_observation_count_boundary"
    tuple_ty = _tuple_type(type_params)
    parameters = "".join(
        f"    {binder}: {binder_type},\n" for binder, binder_type in contract.binders
    )
    requires = ",\n".join(f"        {clause}" for clause in contract.observations)
    text = (
        "#[verifier::external_body]\n"
        f"pub proof fn {name}<{_generics(type_params, bound)}>(\n"
        f"    left: &{tuple_ty},\n"
        f"    right: &{tuple_ty},\n"
        f"{parameters}"
        ")\n"
        "    requires\n"
        f"{requires},\n"
        "    ensures\n"
        f"        {contract.count_conjunct},\n"
        "{\n"
        "}"
    )
    record = {
        "name": name,
        "function": name,
        "category": "observation_count_trace",
        "level": "narrow",
        "literal_external_body": True,
        "whole_target_outcome": False,
        "rationale": (
            "Narrow trace/count boundary. It is a plain (non-broadcast) proof "
            "function, so it contributes nothing except at the one call site "
            "per executed path, where it is applied to the component outcomes "
            "the body actually observed in source order. Its ensures is only "
            "the accepted contract's frozen global "
            f"`cmp_tuple_observation_count(CmpOperation::{_METHOD_OPERATION[method]}, "
            "left, right)` equation for that observed short-circuit prefix; it "
            "never mentions the target's result, so it cannot stand in for the "
            "target outcome. How many components the global counter attributes "
            "to the call is the one fact the Rust body cannot expose to Verus."
        ),
    }
    return name, text, record


def _boundary_call(name: str, contract: _AcceptedContract, indent: str) -> str:
    arguments = ", ".join(["left", "right", *contract.binder_names])
    return f"{indent}{name}({arguments});"


def _proof_block(
    indent: str,
    boundary_name: str,
    contract: _AcceptedContract,
    trigger_terms: list[tuple[str, str]],
    observed_binders: set[str],
    witnesses: dict[str, str] | None = None,
    result_expression: str | None = None,
) -> list[str]:
    witnesses = witnesses or {}
    lines = [f"{indent}proof {{"]
    for binder, binder_type in contract.binders:
        if binder in observed_binders:
            continue
        # Unobserved components are unconstrained by the accepted contract on
        # this path. Reusing a single shared witness (rather than a fresh
        # `arbitrary()` per slot) keeps the existential's multi-pattern from
        # exploding combinatorially over interchangeable ground terms.
        witness = witnesses.get(binder, "arbitrary()")
        lines.append(f"{indent}    let {binder}: {binder_type} = {witness};")
    for label, term in trigger_terms:
        lines.append(f"{indent}    let {label} = {term};")
    lines.append(_boundary_call(boundary_name, contract, indent + "    "))
    if result_expression is not None:
        local_clauses = [
            *contract.observations,
            _substitute(
                contract.result_equation,
                {"result": f"({result_expression})"},
            ),
            contract.count_conjunct,
        ]
        local_assertion = (
            "(\n"
            + f"{indent}        "
            + f" &&\n{indent}        ".join(
                f"({clause})" for clause in local_clauses
            )
            + f"\n{indent}    )"
        )
        lines.append(f"{indent}    assert{local_assertion};")
        relation = _substitute(
            contract.relation_body.strip(),
            {"result": f"({result_expression})"},
        )
        witness_mapping = {
            name: f"{name}_witness"
            for name in contract.binder_names
        }
        witness_binders = ", ".join(
            f"{witness_mapping[name]}: {binder_type}"
            for name, binder_type in contract.binders
        )
        witness_clauses = [
            *(
                f"{witness_mapping[name]} == {name}"
                for name in contract.binder_names
            ),
            *(
                _substitute(clause, witness_mapping)
                for clause in local_clauses
            ),
        ]
        strong_witness = (
            f"exists|{witness_binders}| "
            + " && ".join(
                f"({clause})" for clause in witness_clauses
            )
        )
        witness_assertion = (
            "(\n"
            + f"{indent}        "
            + f" &&\n{indent}        ".join(
                f"({clause})" for clause in witness_clauses
            )
            + f"\n{indent}    )"
        )
        lines.append(f"{indent}    assert({strong_witness}) by {{")
        for name in contract.binder_names:
            lines.append(
                f"{indent}        let {witness_mapping[name]} = {name};"
            )
        lines.append(f"{indent}        assert{witness_assertion};")
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}    assert({relation});")
    lines.append(f"{indent}}}")
    return lines


def _component_kind(
    method: str,
    kind_name: str,
    type_params: list[str],
    slug: str,
    contract: _AcceptedContract,
) -> _KindResult:
    """``eq``/``ne`` (``and_or``), ``cmp`` (``ord``) and ``partial_cmp``."""

    n = len(type_params)
    trait_name = _METHOD_TRAIT[method]
    component_type = _KIND_COMPONENT_TYPE[kind_name]

    if kind_name == "and_or":
        continue_pattern = "true" if method == "eq" else "false"
        decisive_pattern = "false" if method == "eq" else "true"
        helper_expression = "a == b" if method == "eq" else "a != b"
    elif kind_name == "ord":
        continue_pattern = "core::cmp::Ordering::Equal"
        decisive_pattern = "_"
        helper_expression = "a.cmp(b)"
    else:
        continue_pattern = "Some(core::cmp::Ordering::Equal)"
        decisive_pattern = "_"
        helper_expression = "a.partial_cmp(b)"

    helper_name = f"{slug}_component"
    helper_fn = (
        "#[verifier::external_body]\n"
        f"pub fn {helper_name}<X: {trait_name}>(a: &X, b: &X) -> (result: {component_type})\n"
        "    ensures\n"
        f"        call_ensures(<X as {trait_name}>::{method}, (a, b), result),\n"
        "{\n"
        f"    {helper_expression}\n"
        "}"
    )

    boundary_name, boundary_fn, boundary_record = _count_boundary(
        slug, contract, type_params, trait_name, method
    )

    trigger_terms = [
        (
            f"_observed{index}",
            f"call_ensures(<{type_params[index]} as {trait_name}>::{method}, "
            f"(&left.{index}, &right.{index}), o{index})",
        )
        for index in range(n)
    ]

    marker = _marker("IMPL", slug)

    def build(index: int, indent: str) -> list[str]:
        prefix = marker if index == 0 else ""
        lines = [
            f"{indent}{prefix}let o{index} = {helper_name}(&left.{index}, &right.{index});"
        ]
        observed = {f"o{i}" for i in range(index + 1)}
        if index == n - 1:
            lines.extend(
                _proof_block(indent, boundary_name, contract, trigger_terms, observed)
            )
            lines.append(f"{indent}o{index}")
            return lines
        lines.append(f"{indent}match o{index} {{")
        lines.append(f"{indent}    {continue_pattern} => {{")
        lines.extend(build(index + 1, indent + "        "))
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}    {decisive_pattern} => {{")
        lines.extend(
            _proof_block(
                indent + "        ", boundary_name, contract, trigger_terms, observed
            )
        )
        lines.append(f"{indent}        o{index}")
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}}}")
        return lines

    if kind_name == "and_or":
        mutation_replacement = f"{marker}let o0 = !{helper_name}(&left.0, &right.0);"
        mutation_rationale = (
            "Negating the first component's actual comparison outcome still "
            "typechecks (bool negation) but makes the observed short-circuit "
            f"prefix disagree with the accepted `{method}` component call, so "
            "actual Verus must reject it."
        )
    elif kind_name == "ord":
        mutation_replacement = (
            f"{marker}let o0 = {helper_name}(&left.0, &right.0).reverse();"
        )
        mutation_rationale = (
            "Reversing the first component's actual `cmp` outcome still "
            "typechecks (`Ordering::reverse` composes) but conflates the "
            "equality/ordering distinction the accepted lexicographic contract "
            "depends on, so actual Verus must reject it."
        )
    else:
        mutation_replacement = (
            f"{marker}let o0 = {helper_name}(&left.0, &right.0)"
            ".map(|value| value.reverse());"
        )
        mutation_rationale = (
            "Reversing the first component's actual `partial_cmp` outcome still "
            "typechecks (`Option::map` with `Ordering::reverse` composes) but "
            "conflates the equality/ordering distinction the accepted "
            "lexicographic contract depends on, so actual Verus must reject it."
        )

    result = _KindResult()
    result.helper_fns = [helper_fn, boundary_fn]
    result.impl_body = "\n".join(build(0, "    "))
    result.trigger_terms = trigger_terms
    result.boundaries = [
        {
            "name": helper_name,
            "function": helper_name,
            "category": "component_dispatch",
            "level": "narrow",
            "literal_external_body": True,
            "whole_target_outcome": False,
            "rationale": (
                f"Wraps the single generic-component `{method}` call so the tuple "
                "short-circuit chain never assumes a whole-target outcome; the "
                "trusted surface is exactly one field comparison per call."
            ),
        },
        boundary_record,
    ]
    result.impl_mutation = {
        "category": "equality_ordering_distinction",
        "fragment": f"{marker}let o0 = {helper_name}(&left.0, &right.0);",
        "replacement": mutation_replacement,
        "rationale": mutation_rationale,
    }
    result.impl_mutations = [result.impl_mutation]
    return result


def _chain_bool_kind(
    method: str,
    type_params: list[str],
    slug: str,
    contract: _AcceptedContract,
) -> _KindResult:
    n = len(type_params)
    relation_variant = f"CmpRelation::{_METHOD_OPERATION[method]}"
    last_type = type_params[-1]

    final_helper_name = f"{slug}_final"
    final_helper_fn = (
        "#[verifier::external_body]\n"
        f"pub fn {final_helper_name}<X: PartialOrd>(a: &X, b: &X) -> (result: bool)\n"
        "    ensures\n"
        f"        call_ensures(<X as PartialOrd>::{method}, (a, b), result),\n"
        "{\n"
        f"    a.{method}(b)\n"
        "}"
    )

    boundary_name, boundary_fn, boundary_record = _count_boundary(
        slug, contract, type_params, "PartialOrd", method
    )

    marker = _marker("IMPL", slug)

    if n == 1:
        impl_lines = [
            f"    {marker}let last = {final_helper_name}(&left.0, &right.0);"
        ]
        impl_lines.extend(
            _proof_block("    ", boundary_name, contract, [], {"last"})
        )
        impl_lines.append("    last")

        result = _KindResult()
        result.helper_fns = [final_helper_fn, boundary_fn]
        result.impl_body = "\n".join(impl_lines)
        result.trigger_terms = []
        result.boundaries = [
            {
                "name": final_helper_name,
                "function": final_helper_name,
                "category": "component_dispatch",
                "level": "narrow",
                "literal_external_body": True,
                "whole_target_outcome": False,
                "rationale": (
                    f"Wraps the single generic-component direct `{method}` call; "
                    "the source macro's one-field base case forwards straight to "
                    "the public relation, so no private chaining step exists."
                ),
            },
            boundary_record,
        ]
        result.impl_mutation = {
            "category": "branch_reversal",
            "fragment": f"{marker}let last = {final_helper_name}(&left.0, &right.0);",
            "replacement": f"{marker}let last = !{final_helper_name}(&left.0, &right.0);",
            "rationale": (
                "Negating the single component's direct relation call still "
                "typechecks (bool negation) but reverses the accepted one-field "
                f"`{method}` outcome, so actual Verus must reject it."
            ),
        }
        result.impl_mutations = [result.impl_mutation]
        return result

    chain_helper_name = f"{slug}_chain_component"
    chain_helper_fn = (
        "#[verifier::external_body]\n"
        f"pub fn {chain_helper_name}<X: PartialOrd>(a: &X, b: &X) "
        "-> (result: Option<core::cmp::Ordering>)\n"
        "    ensures\n"
        "        call_ensures(<X as PartialOrd>::partial_cmp, (a, b), result),\n"
        "{\n"
        "    a.partial_cmp(b)\n"
        "}"
    )

    trigger_terms: list[tuple[str, str]] = []
    for index in range(n - 1):
        trigger_terms.extend(
            [
                (
                f"_observed{index}",
                f"call_ensures(<{type_params[index]} as PartialOrd>::partial_cmp, "
                f"(&left.{index}, &right.{index}), outcome{index})",
                ),
                (f"_value{index}", f"outcome{index}->0"),
                (
                    f"_relation{index}",
                    f"cmp_relation_holds("
                    f"{relation_variant}, outcome{index}->0)",
                ),
            ]
        )
    trigger_terms.append(
        (
            "_observed_last",
            f"call_ensures(<{last_type} as PartialOrd>::{method}, "
            f"(&left.{n - 1}, &right.{n - 1}), last)",
        )
    )
    # A decisive current outcome makes every later observation implication
    # vacuous. Reuse one equal witness for those unobserved slots instead of
    # introducing interchangeable arbitrary ground terms.
    witnesses = {
        f"outcome{index}": "Some(core::cmp::Ordering::Equal)"
        for index in range(n - 1)
    }
    decisive_variant = (
        "core::cmp::Ordering::Less"
        if method in {"lt", "le"}
        else "core::cmp::Ordering::Greater"
    )

    def build(index: int, indent: str) -> list[str]:
        if index == n - 1:
            lines = [
                f"{indent}let last = {final_helper_name}(&left.{index}, &right.{index});"
            ]
            observed = {f"outcome{i}" for i in range(n - 1)} | {"last"}
            lines.extend(
                _proof_block(
                    indent,
                    boundary_name,
                    contract,
                    trigger_terms,
                    observed,
                    witnesses,
                    "last",
                )
            )
            lines.append(f"{indent}last")
            return lines
        prefix = marker if index == 0 else ""
        lines = [
            f"{indent}{prefix}let outcome{index} = "
            f"{chain_helper_name}(&left.{index}, &right.{index});"
        ]
        observed = {f"outcome{i}" for i in range(index + 1)}
        equal_marker = _marker("CHAIN_EQUAL", slug) if index == 0 else ""
        lines.append(f"{indent}match outcome{index} {{")
        lines.append(
            f"{indent}    {equal_marker}"
            "Some(core::cmp::Ordering::Equal) => {"
        )
        lines.append(
            f"{indent}        proof {{ assert(outcome{index} "
            "== Some(core::cmp::Ordering::Equal)); }"
        )
        lines.extend(build(index + 1, indent + "        "))
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}    Some(order{index}) => {{")
        lines.append(
            f"{indent}        proof {{\n"
            f"{indent}            assert(outcome{index} == Some(order{index}));\n"
            f"{indent}            assert(order{index} "
            "!= core::cmp::Ordering::Equal);\n"
            f"{indent}        }}"
        )
        non_equal_expression = (
            f"matches!(order{index}, {decisive_variant})"
        )
        lines.extend(
            _proof_block(
                indent + "        ",
                boundary_name,
                contract,
                trigger_terms,
                observed,
                witnesses,
                non_equal_expression,
            )
        )
        non_equal_marker = (
            _marker("CHAIN_NON_EQUAL", slug) if index == 0 else ""
        )
        lines.append(
            f"{indent}        {non_equal_marker}{non_equal_expression}"
        )
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}    None => {{")
        lines.append(
            f"{indent}        proof {{ assert(outcome{index} is None); }}"
        )
        lines.extend(
            _proof_block(
                indent + "        ",
                boundary_name,
                contract,
                trigger_terms,
                observed,
                witnesses,
                "false",
            )
        )
        none_marker = _marker("CHAIN_NONE", slug) if index == 0 else ""
        lines.append(f"{indent}        {none_marker}false")
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}}}")
        return lines

    result = _KindResult()
    result.helper_fns = [chain_helper_fn, final_helper_fn, boundary_fn]
    result.impl_body = "\n".join(build(0, "    "))
    result.trigger_terms = trigger_terms
    result.boundaries = [
        {
            "name": chain_helper_name,
            "function": chain_helper_name,
            "category": "component_dispatch",
            "level": "narrow",
            "literal_external_body": True,
            "whole_target_outcome": False,
            "rationale": (
                "Wraps exactly one component `PartialOrd::partial_cmp` call. "
                f"The executable proof body, not this boundary, maps `{relation_variant}` "
                "over Some(non-equal), continues on Some(Equal), and returns "
                "false on None."
            ),
        },
        {
            "name": final_helper_name,
            "function": final_helper_name,
            "category": "component_dispatch",
            "level": "narrow",
            "literal_external_body": True,
            "whole_target_outcome": False,
            "rationale": (
                f"Wraps the single generic-component direct `{method}` call used "
                "only for the last field, matching the source macro's base case."
            ),
        },
        boundary_record,
    ]
    equal_marker = _marker("CHAIN_EQUAL", slug)
    non_equal_marker = _marker("CHAIN_NON_EQUAL", slug)
    none_marker = _marker("CHAIN_NONE", slug)
    result.impl_mutations = [
        {
            "id": "chaining_equal_continue",
            "category": "chaining_equal_continue",
            "fragment": (
                f"{equal_marker}Some(core::cmp::Ordering::Equal)"
            ),
            "replacement": (
                f"{equal_marker}Some(core::cmp::Ordering::Less)"
            ),
            "omitted_observable": (
                "continues on Some(Less) instead of Some(Equal), so equality "
                "no longer reaches the next tuple field"
            ),
            "rationale": (
                "Changing the continuation discriminator remains exhaustive "
                "because the catch-all Some(order) arm survives, but actual "
                "Verus must reject the missing Some(Equal) continuation."
            ),
        },
        {
            "id": "chaining_non_equal_relation",
            "category": "chaining_non_equal_relation",
            "fragment": (
                f"{non_equal_marker}matches!(order0, {decisive_variant})"
            ),
            "replacement": (
                f"{non_equal_marker}!matches!(order0, {decisive_variant})"
            ),
            "omitted_observable": (
                "reverses the requested relation selected by a non-equal "
                "partial_cmp outcome"
            ),
            "rationale": (
                "The mutation keeps the same non-equal partial_cmp observation "
                "but returns the opposite relation; actual Verus must reject it."
            ),
        },
        {
            "id": "chaining_none_false",
            "category": "chaining_none_false",
            "fragment": f"{none_marker}false",
            "replacement": f"{none_marker}true",
            "omitted_observable": (
                "changes the source-defined None branch from false to true"
            ),
            "rationale": (
                "The mutation keeps the same None partial_cmp observation but "
                "returns true; actual Verus must reject it."
            ),
        },
    ]
    result.impl_mutation = result.impl_mutations[0]
    return result


def _format_accepted_contract_comment(accepted_contract_text: str) -> str:
    lines = ["// Accepted contract text (verbatim, for traceability):"]
    for line in accepted_contract_text.splitlines() or [""]:
        lines.append(f"// {line}" if line else "//")
    return "\n".join(lines)


def _environment_premise(
    contract: _AcceptedContract,
    side: str,
    count_term: str,
) -> str:
    mapping = {name: f"environment.{name}" for name in contract.binder_names}
    clauses = [_substitute(clause, mapping) for clause in contract.observations]
    clauses.append(
        _substitute(
            _substitute(contract.result_equation, mapping),
            {"result": f"{side}_result"},
        )
    )
    clauses.append(_substitute(contract.count_conjunct, mapping))
    # The compared observation counts are the *exact* global vocabulary
    # observation, not a free existential witness.
    clauses.append(f"{side}_count == {count_term}")
    return "\n            && ".join(f"({clause})" for clause in clauses)


def render(
    row: dict[str, Any],
    contract_family: str,
    accepted_contract_text: str,
) -> ProofTemplate:
    if not supports(row, contract_family):
        raise ValueError(
            "proof_templates_tuple.render called with an unsupported row/"
            f"contract_family pair: {row.get('row_id')!r} / {contract_family!r}"
        )

    method = row["method_name"]
    type_params = _type_parameters(row)
    arity = len(type_params)
    target = row["target"]
    row_id = str(row.get("row_id") or row.get("identity_key") or "unknown-row")
    slug = _row_slug(row, arity, method)
    kind_name = _METHOD_KIND[method]
    trait_name = _METHOD_TRAIT[method]
    bound = trait_name
    output_type = _METHOD_OUTPUT[method]
    operation = _METHOD_OPERATION[method]
    count_term = f"cmp_tuple_observation_count(CmpOperation::{operation}, left, right)"

    contract = parse_accepted_contract(accepted_contract_text, output_type)
    if count_term not in contract.count_conjunct:
        raise AcceptedContractError(
            f"accepted contract for {row_id} does not observe {count_term}"
        )

    if kind_name == "chain_bool":
        kind = _chain_bool_kind(method, type_params, slug, contract)
    else:
        kind = _component_kind(method, kind_name, type_params, slug, contract)

    tuple_ty = _tuple_type(type_params)
    generics = _generics(type_params, bound)

    header_comment = (
        "#![allow(dead_code, unused_imports, unused_variables)]\n"
        f"// Source-shaped implementation proof for {target}.\n"
        f"// Row: {row_id} (contract_family={contract_family}, arity={arity}).\n"
        "// The exact Rust body performs a source-order, short-circuiting "
        "component-wise\n"
        "// comparison. `implementation`'s ensures below is the accepted "
        "contract's\n"
        "// ensures block copied verbatim, so the frozen global\n"
        f"// {count_term}\n"
        "// component is the real proof obligation; only single-component "
        "dispatch and\n"
        "// one narrow trace/count boundary are trusted.\n"
        f"{_format_accepted_contract_comment(accepted_contract_text)}"
    )

    relation_name = f"{slug}_relation"
    relation_fn = (
        f"pub open spec fn {relation_name}<{generics}>(\n"
        f"    left: &{tuple_ty},\n"
        f"    right: &{tuple_ty},\n"
        f"    result: {output_type},\n"
        f") -> bool {{\n"
        f"{contract.relation_body}\n"
        f"}}"
    )

    helper_fns_text = "\n\n".join(kind.helper_fns)

    implementation_fn = (
        f"pub fn implementation<{generics}>(\n"
        f"    left: &{tuple_ty},\n"
        f"    right: &{tuple_ty},\n"
        f") -> (result: {output_type})\n"
        f"    ensures\n"
        f"{contract.clause_block}\n"
        f"        {relation_name}(left, right, result),\n"
        f"{{\n"
        f"{kind.impl_body}\n"
        f"}}"
    )

    implementation_proof = (
        f"{header_comment}\n\n"
        "use vstd::prelude::*;\n\n"
        "verus! {\n\n"
        f"{VOCABULARY_BLOCK}\n\n"
        f"{relation_fn}\n\n"
        f"{helper_fns_text}\n\n"
        f"{implementation_fn}\n\n"
        "}\n"
    )

    # -- completeness proof -------------------------------------------------
    environment_name = f"{slug}_Environment"
    environment_fields_text = "\n".join(
        f"    pub {name}: {binder_type}," for name, binder_type in contract.binders
    )

    link_fn = (
        f"pub fn implementation_contract_link<{generics}>(\n"
        f"    left: &{tuple_ty},\n"
        f"    right: &{tuple_ty},\n"
        f") -> (result: {output_type})\n"
        f"    ensures\n"
        f"        {relation_name}(left, right, result),\n"
        f"{{\n"
        f"    implementation(left, right)\n"
        f"}}"
    )

    left_premise = _environment_premise(contract, "left", count_term)
    right_premise = _environment_premise(contract, "right", count_term)

    completeness_fn = (
        f"pub proof fn completeness<{generics}>(\n"
        f"    left: &{tuple_ty},\n"
        f"    right: &{tuple_ty},\n"
        f"    environment: {environment_name}<{', '.join(type_params)}>,\n"
        f"    left_result: {output_type},\n"
        f"    left_count: nat,\n"
        f"    right_result: {output_type},\n"
        f"    right_count: nat,\n"
        f")\n"
        f"    requires\n"
        f"        call_ensures(implementation_contract_link, (left, right), left_result),\n"
        f"        call_ensures(implementation_contract_link, (left, right), right_result),\n"
        f"        {relation_name}(left, right, left_result),\n"
        f"        {relation_name}(left, right, right_result),\n"
        f"        {left_premise},\n"
        f"        {right_premise},\n"
        f"    ensures\n"
        f"        {_marker('COMPLETE', slug)}left_result == right_result,\n"
        f"        left_count == right_count,\n"
        f"{{\n"
        f"}}"
    )

    # Ghost struct is parameterised over the same tuple's type parameters so
    # every distinct row gets its own, non-colliding environment type.
    environment_struct = (
        f"pub ghost struct {environment_name}<{', '.join(type_params)}> {{\n"
        f"{environment_fields_text}\n"
        f"    pub _marker: core::marker::PhantomData<({', '.join(type_params)})>,\n"
        f"}}"
    )

    completeness_header = (
        "#![allow(dead_code, unused_imports, unused_variables)]\n"
        f"// Target/family-specific exact completeness proof for {target}.\n"
        f"// Row: {row_id} (contract_family={contract_family}, arity={arity}).\n"
        "// Both compared observations are the *same* accepted contract, taken\n"
        "// under the same fixed per-component calls (the environment) and the\n"
        "// same exact global observation\n"
        f"// {count_term};\n"
        "// neither side is free to invent its own observation count.\n"
        f"{_format_accepted_contract_comment(accepted_contract_text)}"
    )

    completeness_proof = (
        f"{completeness_header}\n\n"
        "use vstd::prelude::*;\n"
        "use super::implementation_proof::*;\n\n"
        "verus! {\n\n"
        f"{environment_struct}\n\n"
        f"{link_fn}\n\n"
        f"{completeness_fn}\n\n"
        "}\n"
    )

    source_shape_tokens: tuple[str, ...] = (
        target,
        f"method:{method}",
        f"trait:{trait_name}",
        f"arity:{arity}",
        "kind:short_circuit",
        f"contract_family:{contract_family}",
        *(f"component[{i}]:{type_params[i]}" for i in range(arity)),
    )

    boundaries = tuple(
        {**boundary, "row_id": row_id} for boundary in kind.boundaries
    )

    implementation_mutation = dict(kind.impl_mutation)
    completeness_mutation = {
        "category": "equality_ordering_distinction",
        "fragment": f"{_marker('COMPLETE', slug)}left_result == right_result,",
        "replacement": f"{_marker('COMPLETE', slug)}left_result != right_result,",
        "rationale": (
            "Flipping the proved equality to a disequality still typechecks "
            "(both sides keep the same comparable type) but asserts the "
            "opposite of what the shared component-output environment and the "
            "shared exact global observation count actually establish, so "
            "actual Verus must reject the mutated completeness theorem."
        ),
    }

    return ProofTemplate(
        proof_family=CONTRACT_FAMILY,
        accepted_relation_name=relation_name,
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=boundaries,
        implementation_mutation=implementation_mutation,
        completeness_mutation=completeness_mutation,
        implementation_mutations=tuple(kind.impl_mutations),
        completeness_mutations=(completeness_mutation,),
    )
