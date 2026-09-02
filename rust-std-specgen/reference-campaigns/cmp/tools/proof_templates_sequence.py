"""Row-owned Verus proof template generation for core::cmp array/slice rows.

This module owns exactly the 27 pending ``core_cmp_exec_fn_inventory`` rows
sourced from ``core/src/array/equality.rs``, ``core/src/array/mod.rs`` and
``core/src/slice/cmp.rs``. Every owned row is rendered into a standalone,
Verus-checkable implementation/completeness proof pair that:

* inlines the **frozen** ``cmp_shared_vocabulary.rs`` verbatim, so every
  observation/dispatch predicate the accepted contract mentions
  (``cmp_sequence_observation_count``, ``cmp_array_eq_dispatch``,
  ``cmp_slice_eq_dispatch``, ``cmp_array_order_dispatch``,
  ``cmp_slice_order_dispatch``, ``cmp_always_applicable_ord_dispatch``,
  ``cmp_bytewise_equal``, ``cmp_unsigned_bytewise_order``,
  ``cmp_array_slice_forwarding``, and the ``cmp_lexicographic_*`` prefixes)
  is the accepted global symbol rather than a local stand-in;
* discharges the **exact** accepted ``ensures`` conjuncts of the row's
  frozen ``assume_specification`` block as the ``implementation_target``
  postcondition -- the clause text is copied verbatim out of
  ``generated_cmp_specs.rs``;
* preserves the row's exact resolved target signature (type parameters,
  lifetimes, const generics, trait bounds, parameter and result types) by
  copying it from the same accepted contract block;
* preserves the source-level control shape that the row's real Rust body
  exhibits -- the generic first-mismatch equality/order/chaining loops, the
  ``as_array::<N>()`` length guard and its ``None`` fallback, the runtime
  length guard of ``<[T] as PartialEq<[U]>>::eq``, the
  ``AlwaysApplicableOrd`` short-circuit, and the ``BytewiseEq``/
  ``UnsignedBytewiseOrd`` bytewise specializations;
* routes **only** narrow, source-backed lower-level facts through
  ``#[verifier::external_body]`` boundaries: specialization/dispatch
  selection, the ``raw_eq``/``compare_bytes`` bytewise primitives, the
  per-element ``partial_cmp`` call, the ``as_array`` length conversion, and
  the observation-count laws. No boundary produces a whole-target outcome;
* forwards **for real**: every array row whose source body delegates to a
  sibling slice/reference target calls that sibling directly, bound to the
  sibling's own accepted contract via ``pub assume_specification``, so the
  forwarded outcome is ``call_ensures`` of the sibling target instead of an
  alpha-identical ``external_body`` passthrough helper;
* proves a ``completeness_theorem`` that compares two ``accepted_contract``
  outcomes -- the exact accepted conjuncts, with every accepted existential
  witness pinned to the same explicit dispatch/trace ``environment`` -- and
  derives ``result1 == result2`` without any ``assume``/``admit``/external
  escape hatch.

``supports``/``render`` are the only public entry points, matching the
``tools.proof_template_common.ProofTemplate`` contract.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from tools.proof_template_common import ProofTemplate

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# Accepted inputs. Proof generation reads the current reviewer-bound specs and
# then freezes those exact bytes into the proof package. The prior frozen
# selection remains a fallback for standalone inspection.
# --------------------------------------------------------------------------
_FROZEN_DIR = ROOT / "frozen_inputs" / "selected_contracts"
_SPECS_DIR = ROOT / "specs"


def _frozen_file(name: str) -> Path:
    accepted = _SPECS_DIR / name
    if accepted.is_file():
        return accepted
    frozen = _FROZEN_DIR / name
    if frozen.is_file():
        return frozen
    raise FileNotFoundError(f"frozen input not available: {name}")


# --------------------------------------------------------------------------
# Contract families (mirrors specs/all_cmp_specs.json's per-row `family`).
# --------------------------------------------------------------------------
FAMILY_ARRAY_EQUALITY = "array_equality_dispatch"
FAMILY_SLICE_EQUALITY = "slice_equality_dispatch"
FAMILY_ARRAY_ORDER = "array_slice_order_forwarding"
FAMILY_SLICE_ORDER = "slice_order_dispatch"

_SOURCE_FILE_ARRAY_EQUALITY = "core/src/array/equality.rs"
_SOURCE_FILE_ARRAY_MOD = "core/src/array/mod.rs"
_SOURCE_FILE_SLICE_CMP = "core/src/slice/cmp.rs"

# --------------------------------------------------------------------------
# Mutation categories (subset of
# check_implementation_proofs.REQUIRED_MUTATION_CATEGORIES relevant here).
# --------------------------------------------------------------------------
MUTATION_FORWARDING = "forwarding"
MUTATION_BRANCH_REVERSAL = "branch_reversal"
MUTATION_SPECIALIZATION_DISPATCH = "specialization_dispatch"
MUTATION_EQUALITY_ORDERING_DISTINCTION = "equality_ordering_distinction"

# --------------------------------------------------------------------------
# Per-row generation recipe. ``sibling`` names the accepted contract row this
# row's real Rust body delegates to; it is bound with `assume_specification`
# and called directly (never stubbed by an external_body helper).
# --------------------------------------------------------------------------
_ROW_PLAN: dict[str, dict[str, str]] = {
    # core/src/array/equality.rs -- array_equality_dispatch (14 rows)
    "rustdoc-10900-10898": {
        "shape": "array_eq_dispatch_base", "method": "eq",
        "operation": "Eq",
        "mutation": MUTATION_SPECIALIZATION_DISPATCH,
    },
    "rustdoc-10900-10899": {
        "shape": "array_eq_dispatch_base", "method": "ne",
        "operation": "Ne",
        "mutation": MUTATION_SPECIALIZATION_DISPATCH,
    },
    "rustdoc-10903-10901": {
        "shape": "array_eq_length_guard", "method": "eq",
        "operation": "Eq",
        "guard_direction": "array_then_slice",
        "sibling": "rustdoc-10900-10898",
        "mutation": MUTATION_BRANCH_REVERSAL,
    },
    "rustdoc-10903-10902": {
        "shape": "array_eq_length_guard", "method": "ne",
        "operation": "Ne",
        "guard_direction": "array_then_slice",
        "sibling": "rustdoc-10900-10899",
        "mutation": MUTATION_BRANCH_REVERSAL,
    },
    "rustdoc-10906-10904": {
        "shape": "array_eq_length_guard", "method": "eq",
        "operation": "Eq",
        "guard_direction": "slice_then_array",
        "sibling": "rustdoc-10900-10898",
        "mutation": MUTATION_BRANCH_REVERSAL,
    },
    "rustdoc-10906-10905": {
        "shape": "array_eq_length_guard", "method": "ne",
        "operation": "Ne",
        "guard_direction": "slice_then_array",
        "sibling": "rustdoc-10900-10899",
        "mutation": MUTATION_BRANCH_REVERSAL,
    },
    "rustdoc-10909-10907": {
        "shape": "array_eq_forward", "method": "eq", "forward": "other_ref",
        "operation": "Eq",
        "sibling": "rustdoc-10903-10901",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10909-10908": {
        "shape": "array_eq_forward", "method": "ne", "forward": "other_ref",
        "operation": "Ne",
        "sibling": "rustdoc-10903-10902",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10912-10910": {
        "shape": "array_eq_forward", "method": "eq", "forward": "self_ref",
        "operation": "Eq",
        "sibling": "rustdoc-10906-10904",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10912-10911": {
        "shape": "array_eq_forward", "method": "ne", "forward": "self_ref",
        "operation": "Ne",
        "sibling": "rustdoc-10906-10905",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10915-10913": {
        "shape": "array_eq_forward", "method": "eq", "forward": "other_mut",
        "operation": "Eq",
        "sibling": "rustdoc-10903-10901",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10915-10914": {
        "shape": "array_eq_forward", "method": "ne", "forward": "other_mut",
        "operation": "Ne",
        "sibling": "rustdoc-10903-10902",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10918-10916": {
        "shape": "array_eq_forward", "method": "eq", "forward": "self_mut",
        "operation": "Eq",
        "sibling": "rustdoc-10906-10904",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-10918-10917": {
        "shape": "array_eq_forward", "method": "ne", "forward": "self_mut",
        "operation": "Ne",
        "sibling": "rustdoc-10906-10905",
        "mutation": MUTATION_FORWARDING,
    },
    # core/src/slice/cmp.rs PartialEq -- slice_equality_dispatch (1 row)
    "rustdoc-11030-11029": {
        "shape": "slice_eq_dispatch", "method": "eq",
        "operation": "Eq",
        "mutation": MUTATION_SPECIALIZATION_DISPATCH,
    },
    # core/src/array/mod.rs -- array_slice_order_forwarding (6 rows)
    "rustdoc-11323-11322": {
        "shape": "order_forward_cmp", "method": "cmp",
        "operation": "Cmp",
        "sibling": "rustdoc-11363-11362",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-11546-11541": {
        "shape": "order_forward_partial_cmp", "method": "partial_cmp",
        "operation": "PartialCmp",
        "sibling": "rustdoc-11610-11605",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-11546-11542": {
        "shape": "order_forward_bool", "method": "lt",
        "operation": "Lt", "relation": "Lt",
        "sibling": "rustdoc-11610-11606",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-11546-11543": {
        "shape": "order_forward_bool", "method": "le",
        "operation": "Le", "relation": "Le",
        "sibling": "rustdoc-11610-11607",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-11546-11544": {
        "shape": "order_forward_bool", "method": "ge",
        "operation": "Ge", "relation": "Ge",
        "sibling": "rustdoc-11610-11609",
        "mutation": MUTATION_FORWARDING,
    },
    "rustdoc-11546-11545": {
        "shape": "order_forward_bool", "method": "gt",
        "operation": "Gt", "relation": "Gt",
        "sibling": "rustdoc-11610-11608",
        "mutation": MUTATION_FORWARDING,
    },
    # core/src/slice/cmp.rs Ord/PartialOrd -- slice_order_dispatch (6 rows)
    "rustdoc-11363-11362": {
        "shape": "order_dispatch_cmp", "method": "cmp",
        "operation": "Cmp",
        "mutation": MUTATION_SPECIALIZATION_DISPATCH,
    },
    "rustdoc-11610-11605": {
        "shape": "order_dispatch_partial_cmp", "method": "partial_cmp",
        "operation": "PartialCmp",
        "mutation": MUTATION_EQUALITY_ORDERING_DISTINCTION,
    },
    "rustdoc-11610-11606": {
        "shape": "order_dispatch_bool", "method": "lt",
        "operation": "Lt", "relation": "Lt",
        "mutation": MUTATION_EQUALITY_ORDERING_DISTINCTION,
    },
    "rustdoc-11610-11607": {
        "shape": "order_dispatch_bool", "method": "le",
        "operation": "Le", "relation": "Le",
        "mutation": MUTATION_EQUALITY_ORDERING_DISTINCTION,
    },
    "rustdoc-11610-11608": {
        "shape": "order_dispatch_bool", "method": "gt",
        "operation": "Gt", "relation": "Gt",
        "mutation": MUTATION_EQUALITY_ORDERING_DISTINCTION,
    },
    "rustdoc-11610-11609": {
        "shape": "order_dispatch_bool", "method": "ge",
        "operation": "Ge", "relation": "Ge",
        "mutation": MUTATION_EQUALITY_ORDERING_DISTINCTION,
    },
}
assert len(_ROW_PLAN) == 27


# --------------------------------------------------------------------------
# Classification / supports().
# --------------------------------------------------------------------------
def _classify(row: dict[str, Any]) -> str | None:
    if row.get("disposition") != "pending":
        return None
    if row.get("row_id") not in _ROW_PLAN:
        return None
    source_file = row.get("source_file")
    if source_file == _SOURCE_FILE_ARRAY_EQUALITY:
        return FAMILY_ARRAY_EQUALITY
    if source_file == _SOURCE_FILE_ARRAY_MOD:
        return FAMILY_ARRAY_ORDER
    if source_file == _SOURCE_FILE_SLICE_CMP:
        if row.get("trait_name") == "PartialEq":
            return FAMILY_SLICE_EQUALITY
        return FAMILY_SLICE_ORDER
    return None


def supports(row: dict[str, Any], contract_family: str) -> bool:
    """True when this module owns ``row`` under exactly ``contract_family``."""
    return _classify(row) == contract_family and contract_family is not None


# --------------------------------------------------------------------------
# Frozen accepted contract block parsing.
# --------------------------------------------------------------------------
_CONTRACT_BLOCK_RE = re.compile(
    r"// @spec-row (?P<row_id>[A-Za-z0-9\-]+) family=(?P<family>\S+)\n"
    r"pub assume_specification(?P<generics>[^\[]*)\[\n"
    r"\s*(?P<target>[^\n]+)\n"
    r"\]\(\n(?P<params>.*?)\n\) -> \((?P<binding>\w+): (?P<result_type>[^\n]+)\)\n"
    r"    ensures\n(?P<ensures>.*?)\n;\n",
    re.DOTALL,
)


class _AcceptedContract:
    """One accepted ``assume_specification`` block, split into its parts."""

    __slots__ = (
        "row_id",
        "family",
        "generics",
        "target",
        "parameters",
        "binding",
        "result_type",
        "clauses",
        "text",
    )

    def __init__(self, match: re.Match[str]) -> None:
        self.row_id = match.group("row_id")
        self.family = match.group("family")
        self.generics = match.group("generics").strip()
        self.target = match.group("target").strip()
        self.parameters = tuple(
            line.strip().rstrip(",")
            for line in match.group("params").split("\n")
            if line.strip()
        )
        self.binding = match.group("binding")
        self.result_type = match.group("result_type").strip()
        clauses = []
        for line in match.group("ensures").split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.endswith(","):
                raise ValueError(
                    f"{self.row_id}: accepted ensures clause is not a single "
                    f"comma-terminated line: {stripped!r}"
                )
            clauses.append(stripped[:-1])
        if not clauses:
            raise ValueError(f"{self.row_id}: accepted contract has no ensures")
        self.clauses = tuple(clauses)
        self.text = match.group(0)

    @property
    def type_parameters(self) -> tuple[str, ...]:
        """Generic argument names (type + const), lifetimes excluded."""
        inner = self.generics[1:-1] if self.generics.startswith("<") else ""
        names: list[str] = []
        depth = 0
        current = ""
        for character in inner:
            if character in "<([":
                depth += 1
            elif character in ">)]":
                depth -= 1
            if character == "," and depth == 0:
                names.append(current)
                current = ""
            else:
                current += character
        if current.strip():
            names.append(current)
        arguments: list[str] = []
        for name in names:
            token = name.strip()
            if not token or token.startswith("'"):
                continue
            token = token.split(":", 1)[0].strip()
            if token.startswith("const "):
                token = token[len("const "):].strip()
            arguments.append(token)
        return tuple(arguments)

    @property
    def generics_without_lifetimes(self) -> str:
        if not self.generics.startswith("<"):
            return ""
        inner = self.generics[1:-1]
        kept = [
            part
            for part in _split_top_level(inner)
            if part.strip() and not part.strip().startswith("'")
        ]
        return "<" + ", ".join(part.strip() for part in kept) + ">" if kept else ""

    def parameter_block(self, indent: str = "    ") -> str:
        return "".join(f"{indent}{parameter},\n" for parameter in self.parameters)

    def ensures_block(self, indent: str = "        ") -> str:
        return "".join(f"{indent}{clause},\n" for clause in self.clauses)


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current = ""
    for character in value:
        if character in "<([":
            depth += 1
        elif character in ">)]":
            depth -= 1
        if character == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += character
    if current.strip():
        parts.append(current)
    return parts


_MATCH_CACHE: dict[str, re.Match[str]] | None = None
_CONTRACT_CACHE: dict[str, _AcceptedContract] = {}


def _contract_matches() -> dict[str, re.Match[str]]:
    global _MATCH_CACHE
    if _MATCH_CACHE is None:
        text = _frozen_file("generated_cmp_specs.rs").read_text(encoding="utf-8")
        _MATCH_CACHE = {
            match.group("row_id"): match
            for match in _CONTRACT_BLOCK_RE.finditer(text)
        }
    return _MATCH_CACHE


def _accepted(row_id: str) -> _AcceptedContract:
    if row_id not in _CONTRACT_CACHE:
        matches = _contract_matches()
        if row_id not in matches:
            raise ValueError(f"no accepted contract block for row {row_id!r}")
        _CONTRACT_CACHE[row_id] = _AcceptedContract(matches[row_id])
    return _CONTRACT_CACHE[row_id]


_VOCABULARY_CACHE: str | None = None


def _vocabulary() -> str:
    global _VOCABULARY_CACHE
    if _VOCABULARY_CACHE is None:
        _VOCABULARY_CACHE = _frozen_file("cmp_shared_vocabulary.rs").read_text(
            encoding="utf-8"
        )
    return _VOCABULARY_CACHE


def _vocabulary_digest() -> str:
    return hashlib.sha256(_vocabulary().encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Observed-operand normalization.
#
# The accepted clauses name the observed operand sequences through the exact
# expression that is legal in the target's own `ensures` (`left@`,
# `(*right)@`, `old(*left)@`, ...).  The completeness statement is expressed
# over the *observed operands themselves*, so those expressions are rewritten
# to the plain `left@`/`right@` of the observed slice/array operands.  This is
# a pure renaming of the observed operand; no conjunct is added, dropped or
# weakened.
# --------------------------------------------------------------------------
_OBSERVED_REWRITES = (
    ("old(*left)@", "left@"),
    ("old(*right)@", "right@"),
    ("(*left)@", "left@"),
    ("(*right)@", "right@"),
)


def _observed_clause(clause: str) -> str:
    for source, replacement in _OBSERVED_REWRITES:
        clause = clause.replace(source, replacement)
    return clause


def _observed_parameter(parameter: str) -> str:
    """The observed operand parameter matching an accepted target parameter."""
    name, _, declared = parameter.partition(": ")
    declared = declared.strip()
    if declared.startswith("&&mut "):
        declared = "&" + declared[len("&&mut "):]
    elif declared.startswith("&&"):
        declared = "&" + declared[len("&&"):]
    declared = re.sub(r"&'[A-Za-z0-9_]+ mut ", "&mut ", declared)
    declared = re.sub(r"&'[A-Za-z0-9_]+ ", "&", declared)
    if declared.startswith("&mut "):
        declared = "&" + declared[len("&mut "):]
    return f"{name.strip()}: {declared}"


# --------------------------------------------------------------------------
# Environment (dispatch + trace) derivation from the accepted clauses.
# --------------------------------------------------------------------------
_TRACE_FIELDS = {
    "Seq<bool>": "ne_outcomes",
    "Seq<Option<core::cmp::Ordering>>": "partial_cmp_outcomes",
    "Seq<core::cmp::Ordering>": "cmp_outcomes",
    "Seq<Option<bool>>": "chaining_outcomes",
    "core::cmp::Ordering": "decisive_order",
}

_DISPATCH_FIELDS = {
    "cmp_array_eq_dispatch": ("array_eq_dispatch", "CmpEqDispatch"),
    "cmp_slice_eq_dispatch": ("slice_eq_dispatch", "CmpEqDispatch"),
    "cmp_array_order_dispatch": ("array_order_dispatch", "CmpOrderDispatch"),
    "cmp_slice_order_dispatch": ("slice_order_dispatch", "CmpOrderDispatch"),
    "cmp_always_applicable_ord_dispatch": (
        "always_applicable_ord_dispatch",
        "CmpOrderDispatch",
    ),
}

_EXISTS_RE = re.compile(r"exists\|(?P<binders>[^|]*)\|\s*")


def _environment_plan(
    contract: _AcceptedContract,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Return the environment fields and the environment-instantiated clauses.

    Every accepted existential witness is replaced by a dedicated
    ``environment`` field, so both compared outcomes are evaluated under one
    identical dispatch/trace.  Every accepted dispatch selector observed by
    the clauses is additionally pinned to an environment field.
    """
    fields: list[tuple[str, str]] = []
    seen: set[str] = set()

    def register(name: str, declared: str) -> None:
        if name not in seen:
            seen.add(name)
            fields.append((name, declared))

    instantiated: list[str] = []
    for clause in contract.clauses:
        remaining = _observed_clause(clause)
        rendered = ""
        while True:
            match = _EXISTS_RE.search(remaining)
            if match is None:
                rendered += remaining
                break
            rendered += remaining[:match.start()]
            tail = remaining[match.end():]
            for binder in _split_top_level(match.group("binders")):
                binder_name, _, binder_type = binder.partition(":")
                binder_name = binder_name.strip()
                binder_type = binder_type.strip()
                field = _TRACE_FIELDS.get(binder_type)
                if field is None:
                    raise ValueError(
                        f"{contract.row_id}: unsupported accepted existential "
                        f"witness type {binder_type!r}"
                    )
                register(field, binder_type)
                tail = re.sub(
                    rf"\b{re.escape(binder_name)}\b",
                    f"environment.{field}",
                    tail,
                )
            remaining = tail
        instantiated.append(rendered)

    pinned: list[str] = []
    for selector, (field, declared) in _DISPATCH_FIELDS.items():
        call = re.search(
            rf"{selector}\((?P<arguments>[^()]*)\)",
            "\n".join(_observed_clause(clause) for clause in contract.clauses),
        )
        if call is None:
            continue
        register(field, declared)
        pinned.append(
            f"environment.{field} == {selector}({call.group('arguments')})"
        )
    return fields, pinned + instantiated


# --------------------------------------------------------------------------
# Source excerpt + header rendering.
# --------------------------------------------------------------------------
def _read_source_excerpt(row: dict[str, Any]) -> str:
    evidence = row["source_evidence"]
    path = ROOT / evidence["snapshot_path"]
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    begin = int(row["source_begin_line"])
    end = int(row["source_end_line"])
    return "".join(lines[begin - 1:end])


def _excerpt_tokens(excerpt: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for line in excerpt.splitlines():
        stripped = line.strip()
        if not stripped or stripped in ("{", "}"):
            continue
        if stripped not in tokens:
            tokens.append(stripped)
    return tuple(tokens)


def _contract_digest(accepted_contract_text: str) -> str:
    return hashlib.sha256(accepted_contract_text.encode("utf-8")).hexdigest()


def _comment_block(text: str, fallback: str) -> list[str]:
    lines = [f"// {line}" if line else "//" for line in text.splitlines()]
    return lines or [f"// {fallback}"]


def _header(
    row: dict[str, Any],
    contract_family: str,
    accepted_contract_text: str,
    proof_kind: str,
    excerpt: str,
    contract: _AcceptedContract,
) -> str:
    lines = [
        "#![feature(sized_hierarchy)]",
        "#![allow(dead_code, unused_imports, unused_variables, deprecated)]",
        f"// Standalone {proof_kind} proof for {row['target']}.",
        f"// Row: {row['row_id']}",
        f"// Contract family: {contract_family}",
        f"// Accepted contract sha256: {_contract_digest(accepted_contract_text)}",
        f"// Frozen cmp_shared_vocabulary.rs sha256: {_vocabulary_digest()}",
        "// Accepted contract block (frozen generated_cmp_specs.rs); every",
        "// ensures clause below is reproduced verbatim by this proof and by the",
        "// paired completeness proof's `accepted_contract` relation:",
        *_comment_block(contract.text, "(empty accepted contract)"),
        "// Source excerpt ({}:{}-{}):".format(
            row["source_file"], row["source_begin_line"], row["source_end_line"]
        ),
        *_comment_block(excerpt, "(empty source excerpt)"),
        "",
        "use vstd::prelude::*;",
        "",
    ]
    if proof_kind == "implementation":
        lines.extend(
            [
                "// The frozen accepted shared vocabulary is inlined verbatim so"
                " every",
                "// observation/dispatch symbol below is the accepted global"
                " symbol.",
                _vocabulary().rstrip("\n"),
                "",
            ]
        )
    else:
        lines.append("use super::implementation_proof::*;")
        lines.append("")
    lines.extend(["verus! {", ""])
    return "\n".join(lines) + "\n"


_FOOTER = "\n} // verus!\n"


def _boundary(function: str, category: str, role: str) -> dict[str, Any]:
    return {
        "function": function,
        "category": category,
        "role": role,
        "whole_target_outcome": False,
        "literal_external_body": True,
    }


def _completeness_mutation(category: str, observable: str) -> dict[str, str]:
    return {
        "fragment": "result1 == result2",
        "replacement": "result1 != result2",
        "category": category,
        "omitted_observable": observable,
    }


def _require_unique(text: str, fragment: str, row_id: str, label: str) -> None:
    count = text.count(fragment)
    if count != 1:
        raise ValueError(
            f"{row_id}: {label} mutation fragment occurs {count} times "
            f"(expected exactly 1): {fragment!r}"
        )


# --------------------------------------------------------------------------
# Narrow, source-backed law helpers (never a whole-target outcome).
# --------------------------------------------------------------------------
def _law_eq_dispatch_select(selector: str, generics: str, operands: str) -> str:
    return (
        "// Narrow source-backed law: `SpecArrayEq`/`SlicePartialEq`"
        " specialization\n"
        "// selection only. It reveals which branch the source takes, never the\n"
        "// comparison outcome.\n"
        "#[verifier::external_body]\n"
        f"pub fn rust_1_96_{selector}_select{generics}(\n"
        f"{operands}"
        ") -> (selected: CmpEqDispatch)\n"
        f"    ensures selected == cmp_{selector}(left@, right@),\n"
        "{\n    loop {}\n}\n"
    )


def _law_order_dispatch_select(
    name: str,
    selector: str,
    generics: str,
    operands: str,
    admissible: tuple[str, str],
    extra_requires: str = "",
) -> str:
    return (
        "// Narrow source-backed law: `SliceOrd`/`SlicePartialOrd`"
        " specialization\n"
        "// selection only. It reveals which branch the source takes, never the\n"
        "// comparison outcome.\n"
        "#[verifier::external_body]\n"
        f"pub fn {name}{generics}(\n"
        f"{operands}"
        ") -> (selected: CmpOrderDispatch)\n"
        f"{extra_requires}"
        f"    ensures\n"
        f"        selected == {selector}(left@, right@),\n"
        f"        selected == CmpOrderDispatch::{admissible[0]}"
        f" || selected == CmpOrderDispatch::{admissible[1]},\n"
        "{\n    loop {}\n}\n"
    )


_LAW_LENGTH_MISMATCH_COUNT = (
    "// Narrow source-backed law: a rejected length guard performs no element\n"
    "// observation at all.\n"
    "#[verifier::external_body]\n"
    "pub proof fn rust_1_96_length_mismatch_observation_count<T, U>(\n"
    "    operation: CmpOperation,\n"
    "    left: Seq<T>,\n"
    "    right: Seq<U>,\n"
    ")\n"
    "    requires left.len() != right.len(),\n"
    "    ensures cmp_sequence_observation_count(operation, left, right) == 0,\n"
    "{\n}\n"
)

_LAW_GENERIC_EQ_LOOP_COUNT = (
    "// Narrow source-backed law: the generic first-mismatch loop performs"
    " exactly\n"
    "// one `PartialEq::ne` observation per visited element and stops at the\n"
    "// first decisive one.\n"
    "#[verifier::external_body]\n"
    "pub proof fn rust_1_96_generic_eq_loop_observation_count<T: PartialEq<U>,"
    " U>(\n"
    "    operation: CmpOperation,\n"
    "    left: Seq<T>,\n"
    "    right: Seq<U>,\n"
    "    outcomes: Seq<bool>,\n"
    ")\n"
    "    requires\n"
    "        cmp_lexicographic_ne_prefix(left, right, outcomes),\n"
    "        outcomes.len() <= left.len(),\n"
    "        outcomes.len() < left.len() ==> outcomes.len() > 0"
    " && outcomes.last(),\n"
    "    ensures\n"
    "        cmp_sequence_observation_count(operation, left, right)"
    " == outcomes.len(),\n"
    "{\n}\n"
)


def _law_bytewise_equal(selector: str, generics: str, operands: str) -> str:
    return (
        "// Narrow source-backed law: the `BytewiseEq` specialization's single\n"
        "// `raw_eq`/`compare_bytes` primitive and its single observation.\n"
        "#[verifier::external_body]\n"
        f"pub fn rust_1_96_{selector}_bytewise_equal{generics}(\n"
        "    operation: CmpOperation,\n"
        f"{operands}"
        ") -> (equal: bool)\n"
        f"    requires cmp_{selector}(left@, right@) == CmpEqDispatch::Bytewise,\n"
        "    ensures\n"
        "        equal == cmp_bytewise_equal(left@, right@),\n"
        "        cmp_sequence_observation_count(operation, left@, right@) == 1,\n"
        "{\n    loop {}\n}\n"
    )


def _law_compare_bytes_order(
    name: str,
    selector: str,
    generics: str,
) -> str:
    return (
        "// Narrow source-backed law: the `UnsignedBytewiseOrd` specialization's\n"
        "// single `compare_bytes` primitive.\n"
        "#[verifier::external_body]\n"
        f"pub fn {name}{generics}(\n"
        "    left: &[T],\n"
        "    right: &[T],\n"
        ") -> (order: core::cmp::Ordering)\n"
        f"    requires {selector}(left@, right@)"
        " == CmpOrderDispatch::UnsignedBytewiseOrd,\n"
        "    ensures order == cmp_unsigned_bytewise_order(left@, right@),\n"
        "{\n    loop {}\n}\n"
    )


_LAW_SLICE_AS_ARRAY = (
    "// Narrow source-backed law: the `as_array::<N>()` checked length"
    " conversion.\n"
    "#[verifier::external_body]\n"
    "pub fn rust_1_96_slice_as_array<X, const N: usize>(\n"
    "    slice: &[X],\n"
    ") -> (converted: Option<&[X; N]>)\n"
    "    ensures\n"
    "        (slice@.len() == N) == converted.is_some(),\n"
    "        converted.is_some() ==> converted.unwrap()@ == slice@,\n"
    "{\n    loop {}\n}\n"
)

_LAW_HIDDEN_ORD_ELEMENT = (
    "// Narrow source-backed law: one per-element `Ord::cmp` observation taken\n"
    "// through the `AlwaysApplicableOrd` specialization, where the element's\n"
    "// `Ord` bound is not visible in this impl's signature.\n"
    "#[verifier::external_body]\n"
    "pub fn rust_1_96_hidden_ord_element_cmp<T: PartialOrd>(\n"
    "    left: &T,\n"
    "    right: &T,\n"
    ") -> (order: core::cmp::Ordering)\n"
    "    ensures cmp_hidden_ord_element_result(*left, *right, order),\n"
    "{\n    loop {}\n}\n"
)

_LAW_PARTIAL_CMP_STEP = (
    "// Narrow source-backed law: one per-element `PartialOrd::partial_cmp`\n"
    "// observation used by the private chaining machinery.\n"
    "#[verifier::external_body]\n"
    "pub fn rust_1_96_partial_cmp_step<T: PartialOrd>(\n"
    "    left: &T,\n"
    "    right: &T,\n"
    ") -> (outcome: Option<core::cmp::Ordering>)\n"
    "    ensures\n"
    "        call_ensures(\n"
    "            <T as PartialOrd>::partial_cmp,\n"
    "            (left, right),\n"
    "            outcome,\n"
    "        ),\n"
    "{\n    left.partial_cmp(right)\n}\n"
)

_LAW_ARRAY_SLICE_FORWARDING = (
    "// Narrow source-backed law: `[T; N]`'s `Ord`/`PartialOrd` impls have no\n"
    "// body of their own beyond `&self[..]` coercion, so the forwarding is\n"
    "// observed and the array-level dispatch selector *is* the slice-level\n"
    "// one. The law says nothing about the forwarded comparison outcome.\n"
    "#[verifier::external_body]\n"
    "pub proof fn rust_1_96_array_slice_order_forwarding<T>(\n"
    "    operation: CmpOperation,\n"
    "    left: Seq<T>,\n"
    "    right: Seq<T>,\n"
    ")\n"
    "    ensures\n"
    "        cmp_array_slice_forwarding(operation, left, right),\n"
    "        cmp_array_order_dispatch(left, right)"
    " == cmp_slice_order_dispatch(left, right),\n"
    "{\n}\n"
)

# --------------------------------------------------------------------------
# Shape builders. Each returns the implementation preamble (laws + sibling
# contracts), the executable target body, the declared boundaries, and the
# implementation mutation.
# --------------------------------------------------------------------------
def _sibling_block(plan: dict[str, str]) -> str:
    sibling = _accepted(plan["sibling"])
    return (
        "// The sibling target this row's real body delegates to, bound to its\n"
        "// own accepted campaign contract. The delegation below is a real call\n"
        "// whose outcome is `call_ensures` of that sibling target.\n"
        + sibling.text
    )


def _build_array_eq_dispatch_base(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    operation = plan["operation"]
    is_ne = plan["method"] == "ne"
    decisive = "true" if is_ne else "false"
    exhaustive = "false" if is_ne else "true"
    bytewise_call = (
        "rust_1_96_array_eq_dispatch_bytewise_equal::<T, U, N>("
        f"CmpOperation::{operation}, left, right)"
    )
    gate = "if matches!(dispatch, CmpEqDispatch::Bytewise) {"

    preamble = "".join(
        [
            _law_eq_dispatch_select(
                "array_eq_dispatch",
                "<T: PartialEq<U>, U, const N: usize>",
                "    left: &[T; N],\n    right: &[U; N],\n",
            ),
            "\n",
            _law_bytewise_equal(
                "array_eq_dispatch",
                "<T: PartialEq<U>, U, const N: usize>",
                "    left: &[T; N],\n    right: &[U; N],\n",
            ),
            "\n",
            _LAW_GENERIC_EQ_LOOP_COUNT,
        ]
    )

    body = (
        "    // `SpecArrayEq::spec_eq` dispatch: the `BytewiseEq` `raw_eq`\n"
        "    // specialization, or the generic first-mismatch element loop.\n"
        "    let dispatch = rust_1_96_array_eq_dispatch_select::<T, U, N>"
        "(left, right);\n"
        f"    {gate}\n"
        f"        {'!' if is_ne else ''}{bytewise_call}\n"
        "    } else {\n"
        "        let ghost mut outcomes: Seq<bool> = Seq::empty();\n"
        "        let mut index: usize = 0;\n"
        "        while index < N\n"
        "            invariant\n"
        "                cmp_array_eq_dispatch(left@, right@)"
        " == CmpEqDispatch::GenericElementLoop,\n"
        "                index <= N,\n"
        "                left@.len() == N,\n"
        "                right@.len() == N,\n"
        "                outcomes.len() == index,\n"
        "                cmp_lexicographic_ne_prefix(left@, right@, outcomes),\n"
        "                forall|slot: int| 0 <= slot < outcomes.len()"
        " ==> !outcomes[slot],\n"
        "            decreases N - index,\n"
        "        {\n"
        "            let step = <T as PartialEq<U>>::ne"
        "(&left[index], &right[index]);\n"
        "            proof {\n"
        "                outcomes = outcomes.push(step);\n"
        "            }\n"
        "            if step {\n"
        "                proof {\n"
        "                    rust_1_96_generic_eq_loop_observation_count"
        "::<T, U>(\n"
        f"                        CmpOperation::{operation}, left@, right@,"
        " outcomes,\n"
        "                    );\n"
        "                }\n"
        "                assert(cmp_lexicographic_ne_prefix"
        "(left@, right@, outcomes));\n"
        f"                return {decisive};\n"
        "            }\n"
        "            index += 1;\n"
        "        }\n"
        "        proof {\n"
        "            rust_1_96_generic_eq_loop_observation_count::<T, U>(\n"
        f"                CmpOperation::{operation}, left@, right@, outcomes,\n"
        "            );\n"
        "        }\n"
        "        assert(cmp_lexicographic_ne_prefix(left@, right@, outcomes));\n"
        f"        {exhaustive}\n"
        "    }\n"
    )

    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_array_eq_dispatch_select",
                "specialization_selection_dependency",
                "SpecArrayEq/BytewiseEq specialization selection only",
            ),
            _boundary(
                "rust_1_96_array_eq_dispatch_bytewise_equal",
                "bytewise_equality_dependency",
                "raw_eq bytewise primitive and its single observation",
            ),
            _boundary(
                "rust_1_96_generic_eq_loop_observation_count",
                "observation_count_law",
                "generic first-mismatch loop observation count law",
            ),
        ),
        "mutation": {
            "fragment": gate,
            "replacement": "if !matches!(dispatch, CmpEqDispatch::Bytewise) {",
            "category": MUTATION_SPECIALIZATION_DISPATCH,
            "omitted_observable": (
                "inverts the BytewiseEq specialization gate so the raw_eq path "
                "and the generic first-mismatch loop swap places, breaking both "
                "cmp_array_eq_dispatch branches of the accepted contract"
            ),
        },
    }


def _build_array_eq_length_guard(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    operation = plan["operation"]
    method = plan["method"]
    is_ne = method == "ne"
    fallback = "true" if is_ne else "false"
    flipped = "false" if is_ne else "true"
    if plan["guard_direction"] == "array_then_slice":
        converted_type = "U"
        guarded = "right"
        call = f"<[T; N] as PartialEq<[U; N]>>::{method}(left, converted)"
        congruence = "assert(converted@ == right@);"
    else:
        converted_type = "T"
        guarded = "left"
        call = f"<[T; N] as PartialEq<[U; N]>>::{method}(converted, right)"
        congruence = "assert(converted@ == left@);"

    preamble = "".join(
        [
            _LAW_SLICE_AS_ARRAY,
            "\n",
            _LAW_LENGTH_MISMATCH_COUNT,
            "\n",
            _sibling_block(plan),
        ]
    )

    body = (
        f"    // `{guarded}.as_array::<N>()` length guard; `Some` delegates to the\n"
        "    // sibling array-vs-array target, `None` is the unequal-length"
        " fallback.\n"
        f"    match rust_1_96_slice_as_array::<{converted_type}, N>({guarded}) {{\n"
        "        Some(converted) => {\n"
        f"            {congruence}\n"
        f"            {call}\n"
        "        }\n"
        "        None => {\n"
        f"            let unequal_length_result: bool = {fallback};\n"
        "            proof {\n"
        "                rust_1_96_length_mismatch_observation_count::<T, U>(\n"
        f"                    CmpOperation::{operation}, left@, right@,\n"
        "                );\n"
        "            }\n"
        "            unequal_length_result\n"
        "        }\n"
        "    }\n"
    )

    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_slice_as_array",
                "length_conversion_dependency",
                "as_array::<N>() checked length conversion",
            ),
            _boundary(
                "rust_1_96_length_mismatch_observation_count",
                "observation_count_law",
                "rejected length guard observes no element",
            ),
        ),
        "mutation": {
            "fragment": f"let unequal_length_result: bool = {fallback};",
            "replacement": f"let unequal_length_result: bool = {flipped};",
            "category": MUTATION_BRANCH_REVERSAL,
            "omitted_observable": (
                "flips the as_array length-mismatch fallback so an "
                "unequal-length comparison returns the opposite of the "
                "accepted contract's None-arm result"
            ),
        },
    }


_FORWARD_CALLS = {
    "other_ref": (
        "",
        "<[T; N] as PartialEq<[U]>>::{method}(left, *right)",
    ),
    "other_mut": (
        "    let right_slice: &[U] = *right;\n",
        "<[T; N] as PartialEq<[U]>>::{method}(left, right_slice)",
    ),
    "self_ref": (
        "",
        "<[T] as PartialEq<[U; N]>>::{method}(*left, right)",
    ),
    "self_mut": (
        "    let left_slice: &[T] = *left;\n",
        "<[T] as PartialEq<[U; N]>>::{method}(left_slice, right)",
    ),
}


def _build_array_eq_forward(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    method = plan["method"]
    reborrow, call_template = _FORWARD_CALLS[plan["forward"]]
    call = call_template.format(method=method)

    body = (
        "    // `*self == **other` / `**self == *other`: dereference the wrapping\n"
        "    // reference and delegate to the sibling array/slice target.\n"
        f"{reborrow}"
        f"    {call}\n"
    )

    return {
        "preamble": _sibling_block(plan),
        "body": body,
        "boundaries": (),
        "mutation": {
            "fragment": f"    {call}\n",
            "replacement": f"    !{call}\n",
            "category": MUTATION_FORWARDING,
            "omitted_observable": (
                "negates the delegated sibling comparison so the "
                "reference-forwarding body no longer reports the sibling "
                "target's own accepted outcome"
            ),
        },
    }


def _build_slice_eq_dispatch(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    operation = plan["operation"]
    gate = "if matches!(dispatch, CmpEqDispatch::Bytewise) {"

    preamble = "".join(
        [
            _law_eq_dispatch_select(
                "slice_eq_dispatch",
                "<T: PartialEq<U>, U>",
                "    left: &[T],\n    right: &[U],\n",
            ),
            "\n",
            _law_bytewise_equal(
                "slice_eq_dispatch",
                "<T: PartialEq<U>, U>",
                "    left: &[T],\n    right: &[U],\n",
            ),
            "\n",
            _LAW_GENERIC_EQ_LOOP_COUNT,
            "\n",
            _LAW_LENGTH_MISMATCH_COUNT,
        ]
    )

    body = (
        "    // `let len = self.len(); if len == other.len() { ... } else { false }`\n"
        "    let len = left.len();\n"
        "    if len == right.len() {\n"
        "        // `SlicePartialEq::equal_same_length` dispatch: the `BytewiseEq`\n"
        "        // `compare_bytes` specialization, or the generic loop.\n"
        "        let dispatch = rust_1_96_slice_eq_dispatch_select::<T, U>"
        "(left, right);\n"
        f"        {gate}\n"
        "            rust_1_96_slice_eq_dispatch_bytewise_equal::<T, U>(\n"
        f"                CmpOperation::{operation}, left, right,\n"
        "            )\n"
        "        } else {\n"
        "            let ghost mut outcomes: Seq<bool> = Seq::empty();\n"
        "            let mut index: usize = 0;\n"
        "            while index < len\n"
        "                invariant\n"
        "                    cmp_slice_eq_dispatch(left@, right@)"
        " == CmpEqDispatch::GenericElementLoop,\n"
        "                    index <= len,\n"
        "                    len == left@.len(),\n"
        "                    len == right@.len(),\n"
        "                    outcomes.len() == index,\n"
        "                    cmp_lexicographic_ne_prefix"
        "(left@, right@, outcomes),\n"
        "                    forall|slot: int| 0 <= slot < outcomes.len()"
        " ==> !outcomes[slot],\n"
        "                decreases len - index,\n"
        "            {\n"
        "                let step = <T as PartialEq<U>>::ne"
        "(&left[index], &right[index]);\n"
        "                proof {\n"
        "                    outcomes = outcomes.push(step);\n"
        "                }\n"
        "                if step {\n"
        "                    proof {\n"
        "                        rust_1_96_generic_eq_loop_observation_count"
        "::<T, U>(\n"
        f"                            CmpOperation::{operation}, left@, right@,"
        " outcomes,\n"
        "                        );\n"
        "                    }\n"
        "                    assert(cmp_lexicographic_ne_prefix"
        "(left@, right@, outcomes));\n"
        "                    return false;\n"
        "                }\n"
        "                index += 1;\n"
        "            }\n"
        "            proof {\n"
        "                rust_1_96_generic_eq_loop_observation_count::<T, U>(\n"
        f"                    CmpOperation::{operation}, left@, right@,"
        " outcomes,\n"
        "                );\n"
        "            }\n"
        "            assert(cmp_lexicographic_ne_prefix"
        "(left@, right@, outcomes));\n"
        "            true\n"
        "        }\n"
        "    } else {\n"
        "        proof {\n"
        "            rust_1_96_length_mismatch_observation_count::<T, U>(\n"
        f"                CmpOperation::{operation}, left@, right@,\n"
        "            );\n"
        "        }\n"
        "        false\n"
        "    }\n"
    )

    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_slice_eq_dispatch_select",
                "specialization_selection_dependency",
                "SlicePartialEq/BytewiseEq specialization selection only",
            ),
            _boundary(
                "rust_1_96_slice_eq_dispatch_bytewise_equal",
                "bytewise_equality_dependency",
                "compare_bytes bytewise primitive and its single observation",
            ),
            _boundary(
                "rust_1_96_generic_eq_loop_observation_count",
                "observation_count_law",
                "generic first-mismatch loop observation count law",
            ),
            _boundary(
                "rust_1_96_length_mismatch_observation_count",
                "observation_count_law",
                "rejected length guard observes no element",
            ),
        ),
        "mutation": {
            "fragment": gate,
            "replacement": "if !matches!(dispatch, CmpEqDispatch::Bytewise) {",
            "category": MUTATION_SPECIALIZATION_DISPATCH,
            "omitted_observable": (
                "inverts the BytewiseEq specialization gate so the "
                "compare_bytes path and the generic first-mismatch loop swap "
                "places once the length guard has already passed"
            ),
        },
    }


def _build_order_forward_cmp(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    call = "<[T] as Ord>::cmp(left_slice, right_slice)"
    body = (
        "    // `Ord::cmp(&&self[..], &&other[..])`: coerce both arrays to slices\n"
        "    // and delegate to the sibling `<[T] as Ord>::cmp` target.\n"
        "    let left_slice: &[T] = left;\n"
        "    let right_slice: &[T] = right;\n"
        "    proof {\n"
        "        rust_1_96_array_slice_order_forwarding::<T>(\n"
        "            CmpOperation::Cmp, left@, right@,\n"
        "        );\n"
        "    }\n"
        f"    {call}\n"
    )
    return {
        "preamble": _LAW_ARRAY_SLICE_FORWARDING + "\n" + _sibling_block(plan),
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_array_slice_order_forwarding",
                "forwarding_observation_law",
                "array-to-slice forwarding observation and dispatch identity",
            ),
        ),
        "mutation": {
            "fragment": f"    {call}\n",
            "replacement": "    <[T] as Ord>::cmp(right_slice, left_slice)\n",
            "category": MUTATION_FORWARDING,
            "omitted_observable": (
                "swaps the delegated operand order so the array-to-slice "
                "forwarding reports cmp(right, left) instead of cmp(left, right)"
            ),
        },
    }


def _build_order_forward_partial_cmp(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    call = "<[T] as PartialOrd<[T]>>::partial_cmp(left_slice, right_slice)"
    body = (
        "    // `PartialOrd::partial_cmp(&&self[..], &&other[..])`: coerce both\n"
        "    // arrays to slices and delegate to the sibling slice target.\n"
        "    let left_slice: &[T] = left;\n"
        "    let right_slice: &[T] = right;\n"
        "    proof {\n"
        "        rust_1_96_array_slice_order_forwarding::<T>(\n"
        "            CmpOperation::PartialCmp, left@, right@,\n"
        "        );\n"
        "    }\n"
        f"    {call}\n"
    )
    return {
        "preamble": _LAW_ARRAY_SLICE_FORWARDING + "\n" + _sibling_block(plan),
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_array_slice_order_forwarding",
                "forwarding_observation_law",
                "array-to-slice forwarding observation and dispatch identity",
            ),
        ),
        "mutation": {
            "fragment": f"    {call}\n",
            "replacement": (
                "    <[T] as PartialOrd<[T]>>::partial_cmp"
                "(right_slice, left_slice)\n"
            ),
            "category": MUTATION_FORWARDING,
            "omitted_observable": (
                "swaps the delegated operand order so the array-to-slice "
                "forwarding reports partial_cmp(right, left) instead of "
                "partial_cmp(left, right)"
            ),
        },
    }


def _exists_body(clause: str, declared_type: str, rename: str) -> str:
    """The body of the accepted ``exists`` witness, with its binder renamed."""
    match = re.search(
        rf"exists\|\s*(?P<name>[A-Za-z0-9_]+)\s*:\s*{re.escape(declared_type)}\s*\|\s*",
        clause,
    )
    if match is None:
        raise ValueError(
            f"no accepted existential of type {declared_type!r} in clause"
        )
    body = clause[match.end():]
    return re.sub(rf"\b{re.escape(match.group('name'))}\b", rename, body)


def _build_order_forward_bool(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    method = plan["method"]
    operation = plan["operation"]
    sibling = _accepted(plan["sibling"])
    witness = _exists_body(
        next(
            clause
            for clause in sibling.clauses
            if "Seq<Option<core::cmp::Ordering>>|" in clause
        ),
        "Seq<Option<core::cmp::Ordering>>",
        "outcomes",
    )
    array_witness = _exists_body(
        next(
            clause
            for clause in contract.clauses
            if "Seq<Option<core::cmp::Ordering>>|" in clause
        ),
        "Seq<Option<core::cmp::Ordering>>",
        "outcomes",
    )

    call = f"<[T] as PartialOrd<[T]>>::{method}(left_slice, right_slice)"
    body = (
        f"    // `PartialOrd::{method}(&&self[..], &&other[..])`: coerce both\n"
        "    // arrays to slices and delegate to the sibling slice target.\n"
        "    let left_slice: &[T] = left;\n"
        "    let right_slice: &[T] = right;\n"
        "    proof {\n"
        "        rust_1_96_array_slice_order_forwarding::<T>(\n"
        f"            CmpOperation::{operation}, left@, right@,\n"
        "        );\n"
        "    }\n"
        f"    let result = {call};\n"
        "    proof {\n"
        "        // The sibling and array contracts expose the same source-order\n"
        "        // partial_cmp element trace.\n"
        "        if cmp_slice_order_dispatch(left@, right@)\n"
        "            == CmpOrderDispatch::GenericPartialOrdLoop\n"
        "        {\n"
        "            let outcomes = choose|outcomes: "
        f"Seq<Option<core::cmp::Ordering>>| {witness};\n"
        f"            assert({witness});\n"
        f"            assert({array_witness});\n"
        "        }\n"
        "    }\n"
        "    result\n"
    )

    return {
        "preamble": (
            _LAW_ARRAY_SLICE_FORWARDING
            + "\n"
            + _sibling_block(plan)
        ),
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_array_slice_order_forwarding",
                "forwarding_observation_law",
                "array-to-slice forwarding observation and dispatch identity",
            ),
        ),
        "mutation": {
            "fragment": f"    let result = {call};\n",
            "replacement": f"    let result = !{call};\n",
            "category": MUTATION_FORWARDING,
            "omitted_observable": (
                f"negates the delegated sibling PartialOrd::{method} outcome so "
                "the array-to-slice forwarding no longer reports the sibling "
                "target's own accepted outcome"
            ),
        },
    }


def _build_order_dispatch_cmp(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    gate = "if matches!(dispatch, CmpOrderDispatch::UnsignedBytewiseOrd) {"
    preamble = "".join(
        [
            _law_order_dispatch_select(
                "rust_1_96_slice_ord_dispatch_select",
                "cmp_slice_order_dispatch",
                "<T: Ord>",
                "    left: &[T],\n    right: &[T],\n",
                ("GenericOrdLoop", "UnsignedBytewiseOrd"),
            ),
            "\n",
            _law_compare_bytes_order(
                "rust_1_96_slice_ord_compare_bytes",
                "cmp_slice_order_dispatch",
                "<T: Ord>",
            ),
        ]
    )
    body = (
        "    // `SliceOrd::compare(self, other)` dispatch: the\n"
        "    // `UnsignedBytewiseOrd` `compare_bytes` specialization, or the\n"
        "    // generic first-mismatch loop with a length tie-break.\n"
        "    let dispatch = rust_1_96_slice_ord_dispatch_select::<T>(left, right);\n"
        f"    {gate}\n"
        "        rust_1_96_slice_ord_compare_bytes::<T>(left, right)\n"
        "    } else {\n"
        "        let shortest: usize = if left.len() < right.len()"
        " { left.len() } else { right.len() };\n"
        "        let ghost mut outcomes: Seq<core::cmp::Ordering> ="
        " Seq::empty();\n"
        "        let mut index: usize = 0;\n"
        "        while index < shortest\n"
        "            invariant\n"
        "                cmp_slice_order_dispatch(left@, right@)"
        " == CmpOrderDispatch::GenericOrdLoop,\n"
        "                index <= shortest,\n"
        "                shortest == cmp_min_len(left@.len(), right@.len()),\n"
        "                outcomes.len() == index,\n"
        "                cmp_lexicographic_cmp_prefix(left@, right@, outcomes),\n"
        "                forall|slot: int| 0 <= slot < outcomes.len() ==>\n"
        "                    outcomes[slot] == core::cmp::Ordering::Equal,\n"
        "            decreases shortest - index,\n"
        "        {\n"
        "            let step = <T as Ord>::cmp(&left[index], &right[index]);\n"
        "            proof {\n"
        "                outcomes = outcomes.push(step);\n"
        "            }\n"
        "            if !matches!(step, core::cmp::Ordering::Equal) {\n"
        "                assert(cmp_lexicographic_cmp_prefix"
        "(left@, right@, outcomes));\n"
        "                return step;\n"
        "            }\n"
        "            index += 1;\n"
        "        }\n"
        "        assert(cmp_lexicographic_cmp_prefix(left@, right@, outcomes));\n"
        "        if left.len() < right.len() {\n"
        "            core::cmp::Ordering::Less\n"
        "        } else if left.len() > right.len() {\n"
        "            core::cmp::Ordering::Greater\n"
        "        } else {\n"
        "            core::cmp::Ordering::Equal\n"
        "        }\n"
        "    }\n"
    )
    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_slice_ord_dispatch_select",
                "specialization_selection_dependency",
                "SliceOrd/UnsignedBytewiseOrd specialization selection only",
            ),
            _boundary(
                "rust_1_96_slice_ord_compare_bytes",
                "bytewise_comparison_dependency",
                "compare_bytes bytewise ordering primitive",
            ),
        ),
        "mutation": {
            "fragment": gate,
            "replacement": (
                "if !matches!(dispatch, CmpOrderDispatch::UnsignedBytewiseOrd) {"
            ),
            "category": MUTATION_SPECIALIZATION_DISPATCH,
            "omitted_observable": (
                "inverts the UnsignedBytewiseOrd specialization gate so the "
                "compare_bytes path and the generic first-mismatch loop swap "
                "places"
            ),
        },
    }


def _build_order_dispatch_partial_cmp(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    decisive_gate = "if !matches!(step, Some(core::cmp::Ordering::Equal)) {"
    preamble = "".join(
        [
            _law_order_dispatch_select(
                "rust_1_96_slice_partial_ord_dispatch_select",
                "cmp_slice_order_dispatch",
                "<T: PartialOrd>",
                "    left: &[T],\n    right: &[T],\n",
                ("GenericPartialOrdLoop", "AlwaysApplicableOrd"),
            ),
            "\n",
            _law_order_dispatch_select(
                "rust_1_96_always_applicable_ord_dispatch_select",
                "cmp_always_applicable_ord_dispatch",
                "<T: PartialOrd>",
                "    left: &[T],\n    right: &[T],\n",
                ("GenericOrdLoop", "UnsignedBytewiseOrd"),
                extra_requires=(
                    "    requires cmp_slice_order_dispatch(left@, right@)\n"
                    "        == CmpOrderDispatch::AlwaysApplicableOrd,\n"
                ),
            ),
            "\n",
            _law_compare_bytes_order(
                "rust_1_96_always_applicable_compare_bytes",
                "cmp_always_applicable_ord_dispatch",
                "<T: PartialOrd>",
            ),
            "\n",
            _LAW_HIDDEN_ORD_ELEMENT,
        ]
    )
    body = (
        "    // `SlicePartialOrd::partial_compare(self, other)` dispatch: the\n"
        "    // `AlwaysApplicableOrd` short-circuit to `Some(SliceOrd::compare)`,\n"
        "    // or the generic first-mismatch `partial_cmp` chaining loop.\n"
        "    let dispatch = rust_1_96_slice_partial_ord_dispatch_select::<T>"
        "(left, right);\n"
        "    if matches!(dispatch, CmpOrderDispatch::AlwaysApplicableOrd) {\n"
        "        let hidden = rust_1_96_always_applicable_ord_dispatch_select"
        "::<T>(left, right);\n"
        "        if matches!(hidden, CmpOrderDispatch::UnsignedBytewiseOrd) {\n"
        "            Some(rust_1_96_always_applicable_compare_bytes::<T>"
        "(left, right))\n"
        "        } else {\n"
        "            let shortest: usize = if left.len() < right.len()"
        " { left.len() } else { right.len() };\n"
        "            let ghost mut outcomes: Seq<core::cmp::Ordering> ="
        " Seq::empty();\n"
        "            let mut index: usize = 0;\n"
        "            while index < shortest\n"
        "                invariant\n"
        "                    cmp_slice_order_dispatch(left@, right@)"
        " == CmpOrderDispatch::AlwaysApplicableOrd,\n"
        "                    cmp_always_applicable_ord_dispatch(left@, right@)"
        " == CmpOrderDispatch::GenericOrdLoop,\n"
        "                    index <= shortest,\n"
        "                    shortest == cmp_min_len(left@.len(), right@.len()),\n"
        "                    outcomes.len() == index,\n"
        "                    cmp_hidden_ord_lexicographic_prefix"
        "(left@, right@, outcomes),\n"
        "                    forall|slot: int| 0 <= slot < outcomes.len() ==>\n"
        "                        outcomes[slot] == core::cmp::Ordering::Equal,\n"
        "                decreases shortest - index,\n"
        "            {\n"
        "                let step = rust_1_96_hidden_ord_element_cmp::<T>"
        "(&left[index], &right[index]);\n"
        "                proof {\n"
        "                    outcomes = outcomes.push(step);\n"
        "                }\n"
        "                if !matches!(step, core::cmp::Ordering::Equal) {\n"
        "                    assert(cmp_hidden_ord_lexicographic_prefix"
        "(left@, right@, outcomes));\n"
        "                    return Some(step);\n"
        "                }\n"
        "                index += 1;\n"
        "            }\n"
        "            assert(cmp_hidden_ord_lexicographic_prefix"
        "(left@, right@, outcomes));\n"
        "            if left.len() < right.len() {\n"
        "                Some(core::cmp::Ordering::Less)\n"
        "            } else if left.len() > right.len() {\n"
        "                Some(core::cmp::Ordering::Greater)\n"
        "            } else {\n"
        "                Some(core::cmp::Ordering::Equal)\n"
        "            }\n"
        "        }\n"
        "    } else {\n"
        "        let shortest: usize = if left.len() < right.len()"
        " { left.len() } else { right.len() };\n"
        "        let ghost mut outcomes: Seq<Option<core::cmp::Ordering>> ="
        " Seq::empty();\n"
        "        let mut index: usize = 0;\n"
        "        while index < shortest\n"
        "            invariant\n"
        "                cmp_slice_order_dispatch(left@, right@)"
        " == CmpOrderDispatch::GenericPartialOrdLoop,\n"
        "                index <= shortest,\n"
        "                shortest == cmp_min_len(left@.len(), right@.len()),\n"
        "                outcomes.len() == index,\n"
        "                cmp_lexicographic_partial_cmp_prefix"
        "(left@, right@, outcomes),\n"
        "                forall|slot: int| 0 <= slot < outcomes.len() ==>\n"
        "                    outcomes[slot] == Some(core::cmp::Ordering::Equal),\n"
        "            decreases shortest - index,\n"
        "        {\n"
        "            let step = <T as PartialOrd>::partial_cmp"
        "(&left[index], &right[index]);\n"
        "            proof {\n"
        "                outcomes = outcomes.push(step);\n"
        "            }\n"
        f"            {decisive_gate}\n"
        "                assert(cmp_lexicographic_partial_cmp_prefix"
        "(left@, right@, outcomes));\n"
        "                return step;\n"
        "            }\n"
        "            index += 1;\n"
        "        }\n"
        "        assert(cmp_lexicographic_partial_cmp_prefix"
        "(left@, right@, outcomes));\n"
        "        if left.len() < right.len() {\n"
        "            Some(core::cmp::Ordering::Less)\n"
        "        } else if left.len() > right.len() {\n"
        "            Some(core::cmp::Ordering::Greater)\n"
        "        } else {\n"
        "            Some(core::cmp::Ordering::Equal)\n"
        "        }\n"
        "    }\n"
    )
    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_slice_partial_ord_dispatch_select",
                "specialization_selection_dependency",
                "SlicePartialOrd/AlwaysApplicableOrd selection only",
            ),
            _boundary(
                "rust_1_96_always_applicable_ord_dispatch_select",
                "specialization_selection_dependency",
                "nested SliceOrd/UnsignedBytewiseOrd selection only",
            ),
            _boundary(
                "rust_1_96_always_applicable_compare_bytes",
                "bytewise_comparison_dependency",
                "compare_bytes bytewise ordering primitive",
            ),
            _boundary(
                "rust_1_96_hidden_ord_element_cmp",
                "element_comparison_dependency",
                "per-element Ord::cmp reached through AlwaysApplicableOrd",
            ),
        ),
        "mutation": {
            "fragment": decisive_gate,
            "replacement": "if !matches!(step, Some(core::cmp::Ordering::Less)) {",
            "category": MUTATION_EQUALITY_ORDERING_DISTINCTION,
            "omitted_observable": (
                "treats element equality as element ordering: the generic "
                "chaining loop stops on the first non-Less element instead of "
                "the first non-Equal one"
            ),
        },
    }


_RELATION_EXEC = {
    "Lt": ("matches!(order, core::cmp::Ordering::Less)", "left.len() < right.len()"),
    "Le": (
        "!matches!(order, core::cmp::Ordering::Greater)",
        "left.len() <= right.len()",
    ),
    "Gt": (
        "matches!(order, core::cmp::Ordering::Greater)",
        "left.len() > right.len()",
    ),
    "Ge": ("!matches!(order, core::cmp::Ordering::Less)", "left.len() >= right.len()"),
}

_RELATION_MUTATION = {
    "Lt": "!matches!(order, core::cmp::Ordering::Greater)",
    "Le": "matches!(order, core::cmp::Ordering::Less)",
    "Gt": "!matches!(order, core::cmp::Ordering::Less)",
    "Ge": "matches!(order, core::cmp::Ordering::Greater)",
}

_CHAIN_NON_EQUAL_EXEC = {
    "Lt": "matches!(order, core::cmp::Ordering::Less)",
    "Le": "matches!(order, core::cmp::Ordering::Less)",
    "Gt": "matches!(order, core::cmp::Ordering::Greater)",
    "Ge": "matches!(order, core::cmp::Ordering::Greater)",
}


def _build_order_dispatch_bool(
    contract: _AcceptedContract,
    plan: dict[str, str],
) -> dict[str, Any]:
    relation = plan["relation"]
    decided, tie_break = _RELATION_EXEC[relation]
    non_equal_decided = _CHAIN_NON_EQUAL_EXEC[relation]
    equal_marker = f"/* MUTATION::CHAIN_EQUAL::{relation} */"
    non_equal_marker = f"/* MUTATION::CHAIN_NON_EQUAL::{relation} */"
    none_marker = f"/* MUTATION::CHAIN_NONE::{relation} */"
    preamble = "".join(
        [
            _law_order_dispatch_select(
                "rust_1_96_slice_relation_dispatch_select",
                "cmp_slice_order_dispatch",
                "<T: PartialOrd>",
                "    left: &[T],\n    right: &[T],\n",
                ("GenericPartialOrdLoop", "UnsignedBytewiseOrd"),
            ),
            "\n",
            _law_compare_bytes_order(
                "rust_1_96_slice_relation_compare_bytes",
                "cmp_slice_order_dispatch",
                "<T: PartialOrd>",
            ),
            "\n",
            _LAW_PARTIAL_CMP_STEP,
        ]
    )
    body = (
        f"    // `as_underlying(self.__chaining_{plan['method']}(other)) == 1`"
        " dispatch:\n"
        "    // the `UnsignedBytewiseOrd` `compare_bytes` specialization, or the\n"
        "    // generic private-chaining loop with a length tie-break.\n"
        "    let dispatch = rust_1_96_slice_relation_dispatch_select::<T>"
        "(left, right);\n"
        "    if matches!(dispatch, CmpOrderDispatch::UnsignedBytewiseOrd) {\n"
        "        let order = rust_1_96_slice_relation_compare_bytes::<T>"
        "(left, right);\n"
        f"        {decided}\n"
        "    } else {\n"
        "        let shortest: usize = if left.len() < right.len()"
        " { left.len() } else { right.len() };\n"
        "        let ghost mut outcomes: "
        "Seq<Option<core::cmp::Ordering>> = Seq::empty();\n"
        "        let mut index: usize = 0;\n"
        "        while index < shortest\n"
        "            invariant\n"
        "                cmp_slice_order_dispatch(left@, right@)"
        " == CmpOrderDispatch::GenericPartialOrdLoop,\n"
        "                index <= shortest,\n"
        "                shortest == cmp_min_len(left@.len(), right@.len()),\n"
        "                outcomes.len() == index,\n"
        "                cmp_lexicographic_partial_cmp_prefix("
        "left@, right@, outcomes),\n"
        "                forall|slot: int| 0 <= slot < outcomes.len() ==>"
        " outcomes[slot] == Some(core::cmp::Ordering::Equal),\n"
        "            decreases shortest - index,\n"
        "        {\n"
        "            let outcome = rust_1_96_partial_cmp_step::<T>(\n"
        "                &left[index], &right[index],\n"
        "            );\n"
        "            proof {\n"
        "                outcomes = outcomes.push(outcome);\n"
        "            }\n"
        "            match outcome {\n"
        "                Some(core::cmp::Ordering::Equal) => { "
        f"{equal_marker} }}\n"
        "                Some(order) => {\n"
        "                    assert(cmp_lexicographic_partial_cmp_prefix("
        "left@, right@, outcomes));\n"
        f"                    return {non_equal_marker}{non_equal_decided};\n"
        "                }\n"
        "                None => {\n"
        "                    assert(cmp_lexicographic_partial_cmp_prefix("
        "left@, right@, outcomes));\n"
        f"                    return {none_marker}false;\n"
        "                }\n"
        "            }\n"
        "            index += 1;\n"
        "        }\n"
        "        assert(cmp_lexicographic_partial_cmp_prefix("
        "left@, right@, outcomes));\n"
        f"        {tie_break}\n"
        "    }\n"
    )
    bytewise_mutation = {
        "id": "bytewise_relation",
        "fragment": f"        {decided}\n",
        "replacement": f"        {_RELATION_MUTATION[relation]}\n",
        "category": MUTATION_EQUALITY_ORDERING_DISTINCTION,
        "omitted_observable": (
            f"replaces the strict/non-strict {plan['method']} relation used "
            "on the bytewise ordering with its equality-including "
            "counterpart, conflating equality with strict ordering"
        ),
    }
    chaining_mutations = [
        {
            "id": "chaining_equal_continue",
            "fragment": (
                "                Some(core::cmp::Ordering::Equal) => { "
                f"{equal_marker} }}\n"
            ),
            "replacement": (
                "                Some(core::cmp::Ordering::Equal) => { "
                f"{equal_marker} return false; }}\n"
            ),
            "category": "chaining_equal_continue",
            "omitted_observable": (
                "returns from the generic loop on Some(Equal) instead of "
                "continuing to the next element"
            ),
        },
        {
            "id": "chaining_non_equal_relation",
            "fragment": f"{non_equal_marker}{non_equal_decided}",
            "replacement": f"{non_equal_marker}!({non_equal_decided})",
            "category": "chaining_non_equal_relation",
            "omitted_observable": (
                "returns the opposite requested relation for a non-equal "
                "partial_cmp outcome"
            ),
        },
        {
            "id": "chaining_none_false",
            "fragment": f"{none_marker}false",
            "replacement": f"{none_marker}true",
            "category": "chaining_none_false",
            "omitted_observable": (
                "returns true for a None partial_cmp outcome instead of false"
            ),
        },
    ]
    return {
        "preamble": preamble,
        "body": body,
        "boundaries": (
            _boundary(
                "rust_1_96_slice_relation_dispatch_select",
                "specialization_selection_dependency",
                "SlicePartialOrd/UnsignedBytewiseOrd selection only",
            ),
            _boundary(
                "rust_1_96_slice_relation_compare_bytes",
                "bytewise_comparison_dependency",
                "compare_bytes bytewise ordering primitive",
            ),
            _boundary(
                "rust_1_96_partial_cmp_step",
                "element_comparison_dependency",
                "one PartialOrd::partial_cmp observation per element",
            ),
        ),
        "mutation": bytewise_mutation,
        "mutations": [bytewise_mutation, *chaining_mutations],
    }


_SHAPE_BUILDERS = {
    "array_eq_dispatch_base": _build_array_eq_dispatch_base,
    "array_eq_length_guard": _build_array_eq_length_guard,
    "array_eq_forward": _build_array_eq_forward,
    "slice_eq_dispatch": _build_slice_eq_dispatch,
    "order_forward_cmp": _build_order_forward_cmp,
    "order_forward_partial_cmp": _build_order_forward_partial_cmp,
    "order_forward_bool": _build_order_forward_bool,
    "order_dispatch_cmp": _build_order_dispatch_cmp,
    "order_dispatch_partial_cmp": _build_order_dispatch_partial_cmp,
    "order_dispatch_bool": _build_order_dispatch_bool,
}


# --------------------------------------------------------------------------
# Assembly.
# --------------------------------------------------------------------------
def _implementation_target(contract: _AcceptedContract, body: str) -> str:
    return (
        "// The executable target. Its postcondition is the accepted contract's\n"
        "// ensures block, reproduced verbatim, so every accepted observation,\n"
        "// dispatch and result conjunct is discharged here.\n"
        f"pub fn implementation_target{contract.generics}(\n"
        f"{contract.parameter_block()}"
        f") -> ({contract.binding}: {contract.result_type})\n"
        "    ensures\n"
        f"{contract.ensures_block()}"
        "{\n"
        f"{body}"
        "}\n"
    )


def _completeness_body(contract: _AcceptedContract) -> str:
    fields, clauses = _environment_plan(contract)
    observed = [_observed_parameter(parameter) for parameter in contract.parameters]
    observed_names = [parameter.split(":", 1)[0].strip() for parameter in observed]
    generics = contract.generics_without_lifetimes

    environment = (
        "// The dispatch/trace environment: every accepted existential witness\n"
        "// and every accepted dispatch selector is pinned here, so both compared\n"
        "// outcomes are evaluated under one identical dispatch/trace.\n"
        "pub ghost struct EnvironmentState {\n"
        + "".join(f"    pub {name}: {declared},\n" for name, declared in fields)
        + "}\n"
    )

    accepted = (
        "// The accepted contract, conjunct for conjunct, instantiated at the\n"
        "// environment's dispatch/trace.\n"
        f"pub open spec fn accepted_contract{generics}(\n"
        + "".join(f"    {parameter},\n" for parameter in observed)
        + "    environment: EnvironmentState,\n"
        f"    {contract.binding}: {contract.result_type},\n"
        ") -> bool {\n"
        + "".join(f"    &&& {clause}\n" for clause in clauses)
        + "}\n"
    )

    link = (
        "// A real call of the proved target, so the compared outcomes are the\n"
        "// target's own accepted outcomes rather than free values.\n"
        f"pub fn implementation_contract_link{contract.generics}(\n"
        f"{contract.parameter_block()}"
        f") -> ({contract.binding}: {contract.result_type})\n"
        "    ensures\n"
        f"{contract.ensures_block()}"
        "{\n"
        "    implementation_target("
        + ", ".join(
            parameter.split(":", 1)[0].strip() for parameter in contract.parameters
        )
        + ")\n"
        "}\n"
    )

    theorem = (
        f"pub proof fn completeness_theorem{contract.generics}(\n"
        f"{contract.parameter_block()}"
        + "".join(
            f"    {name}_observed{parameter[len(name):]},\n"
            for name, parameter in zip(observed_names, observed)
        )
        + "    environment: EnvironmentState,\n"
        "    result1: " + contract.result_type + ",\n"
        "    result2: " + contract.result_type + ",\n"
        ")\n"
        "    requires\n"
        "        call_ensures(implementation_contract_link, ("
        + ", ".join(
            parameter.split(":", 1)[0].strip() for parameter in contract.parameters
        )
        + "), result1),\n"
        "        call_ensures(implementation_contract_link, ("
        + ", ".join(
            parameter.split(":", 1)[0].strip() for parameter in contract.parameters
        )
        + "), result2),\n"
        "        accepted_contract("
        + ", ".join(f"{name}_observed" for name in observed_names)
        + ", environment, result1),\n"
        "        accepted_contract("
        + ", ".join(f"{name}_observed" for name in observed_names)
        + ", environment, result2),\n"
        "    ensures\n"
        "        result1 == result2,\n"
        "{\n}\n"
    )

    return "\n".join([environment, accepted, link, theorem])


def render(
    row: dict[str, Any],
    contract_family: str,
    accepted_contract_text: str,
) -> ProofTemplate:
    """Render the standalone implementation/completeness proof pair for ``row``.

    Raises ``ValueError`` if this module does not own ``row`` under
    ``contract_family`` (callers should check ``supports`` first).
    """
    row_id = row.get("row_id")
    plan = _ROW_PLAN.get(row_id)
    family = _classify(row)
    if plan is None or family != contract_family:
        raise ValueError(
            f"proof_templates_sequence does not own row {row_id!r} under "
            f"contract_family={contract_family!r}"
        )

    contract = _accepted(row_id)
    if contract.family != contract_family:
        raise ValueError(
            f"{row_id}: accepted contract family {contract.family!r} does not "
            f"match {contract_family!r}"
        )

    excerpt = _read_source_excerpt(row)
    shape = _SHAPE_BUILDERS[plan["shape"]](contract, plan)

    header_impl = _header(
        row, contract_family, accepted_contract_text, "implementation",
        excerpt, contract,
    )
    header_comp = _header(
        row, contract_family, accepted_contract_text, "completeness",
        excerpt, contract,
    )
    implementation_proof = (
        header_impl
        + shape["preamble"]
        + "\n"
        + _implementation_target(contract, shape["body"])
        + _FOOTER
    )
    completeness_proof = header_comp + _completeness_body(contract) + _FOOTER

    implementation_mutation = shape["mutation"]
    implementation_mutations = tuple(
        shape.get("mutations", [implementation_mutation])
    )
    completeness_mutation = _completeness_mutation(
        plan["mutation"],
        "drops the exact result equality the accepted contract forces on two "
        "outcomes taken under one identical dispatch/trace environment",
    )

    for mutation in implementation_mutations:
        _require_unique(
            implementation_proof,
            mutation["fragment"],
            row_id,
            f"implementation/{mutation.get('id', 'default')}",
        )
    _require_unique(
        completeness_proof,
        completeness_mutation["fragment"],
        row_id,
        "completeness",
    )

    source_shape_tokens = _excerpt_tokens(excerpt)
    for token in source_shape_tokens:
        if token not in implementation_proof:
            raise ValueError(
                f"{row_id}: source shape token missing from implementation "
                f"proof text: {token!r}"
            )
    for clause in contract.clauses:
        if clause not in implementation_proof:
            raise ValueError(
                f"{row_id}: accepted ensures clause missing from the "
                f"implementation target: {clause!r}"
            )

    return ProofTemplate(
        proof_family=contract_family,
        accepted_relation_name="accepted_contract",
        implementation_proof=implementation_proof,
        completeness_proof=completeness_proof,
        source_shape_tokens=source_shape_tokens,
        boundaries=shape["boundaries"],
        implementation_mutation=implementation_mutation,
        completeness_mutation=completeness_mutation,
        implementation_mutations=implementation_mutations,
        completeness_mutations=(completeness_mutation,),
    )
