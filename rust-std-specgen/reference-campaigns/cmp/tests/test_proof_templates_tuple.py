"""Tests for tools/proof_templates_tuple.py.

These tests exercise the module against the campaign's real, frozen
core::cmp inputs: the 96 ``core/src/tuple.rs`` rows from
``inventory/core_cmp_exec_fn_inventory.json`` and the matching accepted
contract text carved out of ``specs/generated_cmp_specs.rs`` (the same file
the ``tuple_short_circuit`` family's ``assume_specification`` blocks live
in). Representative renders are additionally fed to the real, pinned Verus
binary -- both as the renderer emits them and in the orchestrator-normalized
shape (``implementation_target``/``completeness_theorem``/``accepted_contract``
with completeness compiled standalone through an implementation module) -- so
the executable, non-external implementation and completeness proofs are
checked end to end rather than merely rendered.

The semantic properties the audit demanded are pinned explicitly:

* the rendered ``implementation`` ``ensures`` is the accepted contract's
  ``ensures`` block *verbatim*, so the frozen global
  ``cmp_tuple_observation_count`` and direct ``partial_cmp`` observations are
  the real obligation;
* no locally invented ``observation_count`` existential and no per-row
  uninterpreted chaining stand-in survives;
* the global observation count is established through exactly one narrow
  trace/count boundary whose ``ensures`` never mentions the target result;
* completeness compares two accepted-contract outcomes under the same
  component calls *and* the same exact global observation count.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools import build_implementation_proofs as builder
from tools import proof_templates_tuple as ptt
from tools import run_implementation_proofs as runner
from tools.proof_template_common import ProofTemplate

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
GENERATED_SPECS_PATH = ROOT / "specs" / "generated_cmp_specs.rs"
SHARED_VOCABULARY_PATH = ROOT / "specs" / "cmp_shared_vocabulary.rs"

SPEC_ROW_RE = re.compile(r"^// @spec-row (\S+) family=(\S+)\s*$")
VERIFICATION_RE = runner.VERIFICATION_RE

_ALLOWED_MUTATION_CATEGORIES = {
    "equality_ordering_distinction",
    "branch_reversal",
    "chaining_equal_continue",
    "chaining_non_equal_relation",
    "chaining_none_false",
}
_REQUIRED_BOUNDARY_KEYS = {
    "name",
    "function",
    "category",
    "level",
    "literal_external_body",
    "whole_target_outcome",
    "rationale",
}
_METHOD_OPERATION = {
    "eq": "Eq",
    "ne": "Ne",
    "cmp": "Cmp",
    "partial_cmp": "PartialCmp",
    "lt": "Lt",
    "le": "Le",
    "gt": "Gt",
    "ge": "Ge",
}


def _load_inventory_rows() -> list[dict[str, Any]]:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return list(payload["rows"])


def _load_tuple_rows() -> list[dict[str, Any]]:
    rows = _load_inventory_rows()
    return [row for row in rows if row.get("source_file") == ptt.SOURCE_FILE]


def _load_accepted_contracts() -> dict[str, tuple[str, str]]:
    """Return row_id -> (family, accepted_contract_text) parsed from the
    generated specs file's ``// @spec-row`` anchored assume_specification
    blocks (the same anchors the inventory's row_id values reference)."""

    text = GENERATED_SPECS_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    anchors: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = SPEC_ROW_RE.match(line)
        if match:
            anchors.append((index, match.group(1), match.group(2)))

    contracts: dict[str, tuple[str, str]] = {}
    for position, (line_index, row_id, family) in enumerate(anchors):
        start = line_index + 1
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        body = "\n".join(lines[start:end]).strip("\n")
        contracts[row_id] = (family, body)
    return contracts


def _accepted_ensures_block(accepted_contract_text: str) -> str:
    """The accepted ``assume_specification``'s ``ensures`` clause lines,
    verbatim (independently of the module under test)."""

    lines = accepted_contract_text.splitlines()
    start = lines.index("    ensures")
    end = next(
        index
        for index in range(start + 1, len(lines))
        if lines[index].strip() == ";"
    )
    return "\n".join(lines[start + 1:end])


TUPLE_ROWS = _load_tuple_rows()
ACCEPTED_CONTRACTS = _load_accepted_contracts()


class SupportsTests(unittest.TestCase):
    def test_supports_true_for_all_96_tuple_rows(self) -> None:
        self.assertEqual(len(TUPLE_ROWS), 96)
        for row in TUPLE_ROWS:
            with self.subTest(row_id=row["row_id"]):
                self.assertTrue(ptt.supports(row, ptt.CONTRACT_FAMILY))

    def test_supports_covers_exactly_the_expected_method_arity_grid(self) -> None:
        seen = {
            (row["method_name"], len(row["matching_shape"]["type_parameters"]))
            for row in TUPLE_ROWS
        }
        expected = {
            (method, arity)
            for method in (
                "eq",
                "ne",
                "partial_cmp",
                "cmp",
                "lt",
                "le",
                "gt",
                "ge",
            )
            for arity in range(1, 13)
        }
        self.assertEqual(seen, expected)

    def test_supports_false_for_wrong_contract_family(self) -> None:
        for row in TUPLE_ROWS[:5]:
            self.assertFalse(ptt.supports(row, "exact_vstd"))
            self.assertFalse(ptt.supports(row, ""))
            self.assertFalse(ptt.supports(row, "tuple_short_circuit_typo"))

    def test_supports_false_for_non_tuple_rows(self) -> None:
        non_tuple_rows = [
            row
            for row in _load_inventory_rows()
            if row.get("source_file") != ptt.SOURCE_FILE
        ]
        self.assertGreater(len(non_tuple_rows), 0)
        sample = non_tuple_rows[:: max(1, len(non_tuple_rows) // 40)]
        for row in sample:
            with self.subTest(row_id=row.get("row_id")):
                self.assertFalse(ptt.supports(row, ptt.CONTRACT_FAMILY))

    def test_supports_false_for_malformed_rows(self) -> None:
        self.assertFalse(ptt.supports({}, ptt.CONTRACT_FAMILY))
        self.assertFalse(ptt.supports(None, ptt.CONTRACT_FAMILY))  # type: ignore[arg-type]
        self.assertFalse(
            ptt.supports({"source_file": ptt.SOURCE_FILE}, ptt.CONTRACT_FAMILY)
        )
        base = dict(TUPLE_ROWS[0])
        base["method_name"] = "partial_ord_unknown"
        self.assertFalse(ptt.supports(base, ptt.CONTRACT_FAMILY))
        base2 = dict(TUPLE_ROWS[0])
        base2["matching_shape"] = dict(base2["matching_shape"])
        base2["matching_shape"]["type_parameters"] = [f"T{i}" for i in range(13)]
        self.assertFalse(ptt.supports(base2, ptt.CONTRACT_FAMILY))


class AcceptedContractFixtureTests(unittest.TestCase):
    """Sanity-check the accepted-contract fixture used by the render tests."""

    def test_every_tuple_row_id_has_an_accepted_contract(self) -> None:
        missing = [
            row["row_id"]
            for row in TUPLE_ROWS
            if row["row_id"] not in ACCEPTED_CONTRACTS
        ]
        self.assertEqual(missing, [])

    def test_every_tuple_accepted_contract_is_tagged_tuple_short_circuit(self) -> None:
        for row in TUPLE_ROWS:
            family, text = ACCEPTED_CONTRACTS[row["row_id"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertEqual(family, ptt.CONTRACT_FAMILY)
                self.assertIn(row["target"], text)

    def test_every_tuple_accepted_contract_observes_the_global_count(self) -> None:
        for row in TUPLE_ROWS:
            _, text = ACCEPTED_CONTRACTS[row["row_id"]]
            operation = _METHOD_OPERATION[row["method_name"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertIn(
                    f"cmp_tuple_observation_count(CmpOperation::{operation}, "
                    "left, right)",
                    text,
                )

    def test_parse_accepted_contract_rejects_malformed_text(self) -> None:
        with self.assertRaises(ptt.AcceptedContractError):
            ptt.parse_accepted_contract("no ensures here", "bool")
        with self.assertRaises(ptt.AcceptedContractError):
            ptt.parse_accepted_contract("    ensures\n        true,\n", "bool")


def _external_body_before(text: str, def_pattern: str) -> bool:
    """Return True if the exec/proof item matched by def_pattern is directly
    annotated with #[verifier::external_body] (allowing intervening blank
    lines/comments as Verus does)."""

    match = re.search(def_pattern, text)
    assert match is not None, f"pattern not found: {def_pattern}"
    prefix = text[: match.start()]
    tail = prefix.rstrip()
    # Walk backwards over any trailing attribute/comment lines immediately
    # preceding the definition to see whether external_body is among them.
    preceding_lines = tail.splitlines()
    for line in reversed(preceding_lines):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("//"):
            continue
        if stripped.startswith("#["):
            if "verifier::external_body" in stripped:
                return True
            continue
        break
    return False


def _definition_pattern(function_name: str) -> str:
    return rf"pub (?:proof )?fn {re.escape(function_name)}<"


def _declaration(text: str, function_name: str) -> str:
    """Everything from a function's `pub fn`/`pub proof fn` keyword up to the
    opening brace of its body."""

    match = re.search(_definition_pattern(function_name), text)
    assert match is not None, function_name
    opening = text.find("\n{", match.start())
    assert opening >= 0, function_name
    return text[match.start():opening + 1]


class RenderStructuralTests(unittest.TestCase):
    """Render all 96 rows and check the required structural properties
    without invoking Verus (fast, exhaustive)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.templates: dict[str, ProofTemplate] = {}
        for row in TUPLE_ROWS:
            _, accepted_contract_text = ACCEPTED_CONTRACTS[row["row_id"]]
            cls.templates[row["row_id"]] = ptt.render(
                row, ptt.CONTRACT_FAMILY, accepted_contract_text
            )

    def test_renders_all_96_rows(self) -> None:
        self.assertEqual(len(self.templates), 96)
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                self.assertIsInstance(template, ProofTemplate)
                self.assertEqual(template.proof_family, ptt.CONTRACT_FAMILY)
                self.assertTrue(
                    template.accepted_relation_name.endswith(
                        f"_{row_id.replace('-', '_')}_relation"
                    ),
                    template.accepted_relation_name,
                )
                self.assertIsInstance(template.implementation_proof, str)
                self.assertIsInstance(template.completeness_proof, str)
                self.assertTrue(template.implementation_proof.strip())
                self.assertTrue(template.completeness_proof.strip())

    def test_render_rejects_unsupported_row_or_family(self) -> None:
        row = TUPLE_ROWS[0]
        with self.assertRaises(ValueError):
            ptt.render(row, "not_a_real_family", "ignored")
        non_tuple = next(
            r
            for r in _load_inventory_rows()
            if r.get("source_file") != ptt.SOURCE_FILE
        )
        with self.assertRaises(ValueError):
            ptt.render(non_tuple, ptt.CONTRACT_FAMILY, "ignored")

    def test_implementation_target_is_executable_and_not_external(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                text = template.implementation_proof
                self.assertIn("pub fn implementation<", text)
                self.assertFalse(
                    _external_body_before(text, r"pub fn implementation<"),
                    "implementation target must not be external_body",
                )
                # The relation exposed to `ensures` must be a real, non-external
                # spec fn (the accepted, family-specific relation).
                self.assertIn("pub open spec fn", text)
                self.assertNotIn("external_body]\npub open spec fn", text)

    # -- accepted-contract fidelity ----------------------------------------

    def test_implementation_ensures_is_the_accepted_ensures_verbatim(self) -> None:
        """The target's obligation is the accepted contract as written -- not a
        paraphrase and not a locally invented relation."""

        for row in TUPLE_ROWS:
            row_id = row["row_id"]
            _, accepted_contract_text = ACCEPTED_CONTRACTS[row_id]
            expected = _accepted_ensures_block(accepted_contract_text)
            text = self.templates[row_id].implementation_proof
            declaration = _declaration(text, "implementation")
            with self.subTest(row_id=row_id):
                self.assertIn("\n    ensures\n" + expected + "\n", declaration)

    def test_accepted_relation_spec_fn_matches_the_accepted_contract(self) -> None:
        for row in TUPLE_ROWS:
            row_id = row["row_id"]
            _, accepted_contract_text = ACCEPTED_CONTRACTS[row_id]
            contract = ptt.parse_accepted_contract(
                accepted_contract_text, "bool"
            )
            text = self.templates[row_id].implementation_proof
            with self.subTest(row_id=row_id):
                self.assertIn(contract.relation_body, text)
                # Every accepted conjunct survives into the rendered relation.
                for clause in (
                    *contract.observations,
                    contract.count_conjunct,
                ):
                    self.assertIn(clause, text)

    def test_no_locally_invented_observation_count(self) -> None:
        """The audited defect: an existentially quantified, target-local
        `observation_count` that makes the accepted count conjunct vacuous."""

        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                for text in (
                    template.implementation_proof,
                    template.completeness_proof,
                ):
                    self.assertNotIn("observation_count: nat", text)
                    self.assertNotIn("exists|observation_count", text)

    def test_global_observation_count_component_is_the_obligation(self) -> None:
        for row in TUPLE_ROWS:
            operation = _METHOD_OPERATION[row["method_name"]]
            term = (
                f"cmp_tuple_observation_count(CmpOperation::{operation}, "
                "left, right)"
            )
            template = self.templates[row["row_id"]]
            declaration = _declaration(
                template.implementation_proof, "implementation"
            )
            with self.subTest(row_id=row["row_id"]):
                self.assertIn(term, declaration)
                self.assertIn(term, template.completeness_proof)

    def test_frozen_vocabulary_definitions_are_source_identical(self) -> None:
        frozen = SHARED_VOCABULARY_PATH.read_text(encoding="utf-8")
        for item in ptt.VOCABULARY_ITEMS:
            with self.subTest(item=item.splitlines()[0]):
                self.assertIn(item, frozen)
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                for item in ptt.VOCABULARY_ITEMS:
                    self.assertIn(item, template.implementation_proof)

    def test_only_frozen_vocabulary_functions_are_uninterpreted(self) -> None:
        """No per-row uninterpreted stand-in may be introduced; the only
        uninterpreted symbols are the frozen vocabulary components."""

        allowed = {
            "cmp_tuple_observation_count",
        }
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                for text in (
                    template.implementation_proof,
                    template.completeness_proof,
                ):
                    names = set(
                        re.findall(
                            r"uninterp spec fn ([A-Za-z0-9_]+)",
                            text,
                        )
                    )
                    self.assertTrue(
                        names <= allowed,
                        f"unexpected uninterpreted symbols: {sorted(names - allowed)}",
                    )

    def test_private_chaining_is_derived_from_partial_cmp(self) -> None:
        for row in TUPLE_ROWS:
            method = row["method_name"]
            arity = len(row["matching_shape"]["type_parameters"])
            if method not in ("lt", "le", "gt", "ge") or arity < 2:
                continue
            relation = f"CmpRelation::{_METHOD_OPERATION[method]}"
            template = self.templates[row["row_id"]]
            text = template.implementation_proof
            with self.subTest(row_id=row["row_id"]):
                self.assertNotIn("cmp_private_chaining_outcome", text)
                for index in range(arity - 1):
                    self.assertIn(
                        f"call_ensures(<"
                        f"{row['matching_shape']['type_parameters'][index]} "
                        "as PartialOrd>::partial_cmp, "
                        f"(&left.{index}, &right.{index}), outcome{index})",
                        text,
                    )
                self.assertIn(
                    "Some(core::cmp::Ordering::Equal) =>",
                    text,
                )
                self.assertIn("Some(order0) =>", text)
                self.assertIn("None =>", text)
                self.assertIn(
                    f"cmp_relation_holds({relation}, outcome0->0)",
                    text,
                )
                last = row["matching_shape"]["type_parameters"][-1]
                self.assertIn(f"<{last} as PartialOrd>::{method}", text)

    def test_observation_count_boundary_is_narrow_and_result_free(self) -> None:
        for row in TUPLE_ROWS:
            row_id = row["row_id"]
            template = self.templates[row_id]
            text = template.implementation_proof
            _, accepted_contract_text = ACCEPTED_CONTRACTS[row_id]
            contract = ptt.parse_accepted_contract(accepted_contract_text, "bool")
            count_boundaries = [
                boundary
                for boundary in template.boundaries
                if boundary["category"] == "observation_count_trace"
            ]
            with self.subTest(row_id=row_id):
                self.assertEqual(len(count_boundaries), 1)
                boundary = count_boundaries[0]
                declaration = _declaration(text, boundary["function"])
                self.assertTrue(
                    _external_body_before(
                        text, _definition_pattern(boundary["function"])
                    )
                )
                ensures = declaration.split("    ensures\n", 1)[1]
                # The boundary's ensures is *only* the accepted global count
                # equation: it must not carry the target's result.
                self.assertEqual(
                    ensures.strip(), contract.count_conjunct + ","
                )
                self.assertNotRegex(ensures, r"\bresult\b")
                # ... and its premises are the accepted observation conjuncts.
                for clause in contract.observations:
                    self.assertIn(clause, declaration)

    def test_completeness_compares_two_accepted_contract_outcomes(self) -> None:
        for row in TUPLE_ROWS:
            row_id = row["row_id"]
            template = self.templates[row_id]
            operation = _METHOD_OPERATION[row["method_name"]]
            term = (
                f"cmp_tuple_observation_count(CmpOperation::{operation}, "
                "left, right)"
            )
            declaration = _declaration(template.completeness_proof, "completeness")
            with self.subTest(row_id=row_id):
                self.assertEqual(
                    declaration.count("call_ensures(implementation_contract_link"),
                    2,
                )
                relation_name = template.accepted_relation_name
                self.assertIn(f"{relation_name}(left, right, left_result)", declaration)
                self.assertIn(
                    f"{relation_name}(left, right, right_result)", declaration
                )
                # Both compared observations share the same environment (the
                # same fixed component calls) ...
                self.assertGreater(declaration.count("environment."), 1)
                # ... and the same *exact* global observation count. Neither
                # side may pick its own free count witness.
                self.assertIn(f"left_count == {term}", declaration)
                self.assertIn(f"right_count == {term}", declaration)
                self.assertIn("left_result == right_result", declaration)
                self.assertIn("left_count == right_count", declaration)

    def test_completeness_theorem_is_proof_fn_and_not_external(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                text = template.completeness_proof
                self.assertIn("pub proof fn completeness<", text)
                self.assertFalse(
                    _external_body_before(text, r"pub proof fn completeness<"),
                    "completeness theorem must not be external_body",
                )
                self.assertNotIn("assume(", text)
                self.assertNotIn("admit()", text)

    def test_short_circuit_and_ordering_distinctions_are_preserved(self) -> None:
        expected_output_type = {
            "eq": "bool",
            "ne": "bool",
            "cmp": "core::cmp::Ordering",
            "partial_cmp": "Option<core::cmp::Ordering>",
            "lt": "bool",
            "le": "bool",
            "gt": "bool",
            "ge": "bool",
        }
        for row in TUPLE_ROWS:
            method = row["method_name"]
            template = self.templates[row["row_id"]]
            text = template.implementation_proof
            arity = len(row["matching_shape"]["type_parameters"])
            with self.subTest(row_id=row["row_id"]):
                self.assertIn(f"-> (result: {expected_output_type[method]})", text)
                if method == "eq" and arity > 1:
                    self.assertIn("true =>", text)
                if method == "ne" and arity > 1:
                    self.assertIn("false =>", text)
                if method == "cmp" and arity > 1:
                    self.assertIn("core::cmp::Ordering::Equal =>", text)
                if method == "partial_cmp" and arity > 1:
                    self.assertIn("Some(core::cmp::Ordering::Equal) =>", text)
                if method in ("lt", "le", "gt", "ge") and arity > 1:
                    self.assertIn(
                        "Option<core::cmp::Ordering>",
                        text,
                    )
                    self.assertIn(
                        "Some(core::cmp::Ordering::Equal) =>",
                        text,
                    )
                    self.assertIn("Some(order0) =>", text)
                    self.assertIn("None =>", text)
                    self.assertNotIn(
                        "cmp_private_chaining_outcome",
                        text,
                    )
                    self.assertIn(
                        f"<{row['matching_shape']['type_parameters'][-1]} "
                        f"as PartialOrd>::{method}",
                        text,
                    )

    def test_unrolled_components_reference_every_field_in_source_order(self) -> None:
        for row in TUPLE_ROWS:
            arity = len(row["matching_shape"]["type_parameters"])
            template = self.templates[row["row_id"]]
            text = template.implementation_proof
            with self.subTest(row_id=row["row_id"]):
                for index in range(arity):
                    self.assertIn(f"&left.{index}", text)
                    self.assertIn(f"&right.{index}", text)
                # No out-of-range field access.
                self.assertNotIn(f"&left.{arity}", text)
                # Components are dispatched in source order.
                positions = [
                    text.index(f"(&left.{index}, &right.{index});")
                    for index in range(arity)
                ]
                self.assertEqual(positions, sorted(positions))

    def test_source_shape_tokens_are_populated_and_reflect_the_row(self) -> None:
        for row in TUPLE_ROWS:
            template = self.templates[row["row_id"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertIsInstance(template.source_shape_tokens, tuple)
                self.assertGreater(len(template.source_shape_tokens), 0)
                self.assertIn(row["target"], template.source_shape_tokens)
                self.assertIn(
                    f"method:{row['method_name']}", template.source_shape_tokens
                )

    def test_boundaries_are_explicit_narrow_and_non_whole_target(self) -> None:
        for row in TUPLE_ROWS:
            template = self.templates[row["row_id"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertIsInstance(template.boundaries, tuple)
                self.assertGreater(len(template.boundaries), 0)
                for boundary in template.boundaries:
                    self.assertTrue(_REQUIRED_BOUNDARY_KEYS.issubset(boundary.keys()))
                    self.assertIs(boundary["literal_external_body"], True)
                    self.assertIs(boundary["whole_target_outcome"], False)
                    self.assertEqual(boundary["level"], "narrow")
                    self.assertTrue(boundary["name"])
                    self.assertTrue(boundary["function"])
                    self.assertTrue(boundary["rationale"])
                    # The boundary must actually correspond to a real
                    # external_body helper defined in the same file.
                    self.assertRegex(
                        template.implementation_proof,
                        _definition_pattern(boundary["function"]),
                    )
                    self.assertTrue(
                        _external_body_before(
                            template.implementation_proof,
                            _definition_pattern(boundary["function"]),
                        )
                    )

    def test_every_external_body_helper_is_a_declared_boundary(self) -> None:
        for row in TUPLE_ROWS:
            template = self.templates[row["row_id"]]
            declared = {boundary["function"] for boundary in template.boundaries}
            with self.subTest(row_id=row["row_id"]):
                for text in (
                    template.implementation_proof,
                    template.completeness_proof,
                ):
                    found = set(
                        re.findall(
                            r"#\[verifier::external_body\]\s*\n"
                            r"pub (?:proof )?fn ([A-Za-z0-9_]+)",
                            text,
                        )
                    )
                    self.assertEqual(found - declared, set())
                self.assertEqual(
                    len(declared),
                    template.implementation_proof.count(
                        "#[verifier::external_body]"
                    )
                    + template.completeness_proof.count(
                        "#[verifier::external_body]"
                    ),
                )

    def test_mutation_plans_are_well_formed_and_unique(self) -> None:
        impl_fragments: dict[str, str] = {}
        completeness_fragments: dict[str, str] = {}
        for row in TUPLE_ROWS:
            row_id = row["row_id"]
            template = self.templates[row_id]
            implementation_mutations = (
                template.implementation_mutations
                or (template.implementation_mutation,)
            )
            completeness_mutations = (
                template.completeness_mutations
                or (template.completeness_mutation,)
            )
            for proof_kind, mutations, text, fragments in (
                (
                    "implementation",
                    implementation_mutations,
                    template.implementation_proof,
                    impl_fragments,
                ),
                (
                    "completeness",
                    completeness_mutations,
                    template.completeness_proof,
                    completeness_fragments,
                ),
            ):
                for mutation in mutations:
                    with self.subTest(
                        row_id=row_id,
                        proof_kind=proof_kind,
                        mutation_id=mutation.get("id", "default"),
                    ):
                        self.assertIsInstance(mutation, dict)
                        for value in mutation.values():
                            self.assertIsInstance(value, str)
                        self.assertIn(
                            mutation["category"],
                            _ALLOWED_MUTATION_CATEGORIES,
                        )
                        fragment = mutation["fragment"]
                        replacement = mutation["replacement"]
                        self.assertNotEqual(fragment, replacement)
                        self.assertEqual(
                            text.count(fragment),
                            1,
                            f"fragment must occur exactly once for {row_id}",
                        )
                        mutated = text.replace(fragment, replacement)
                        self.assertEqual(mutated.count(replacement), 1)
                        self.assertNotEqual(mutated, text)
                        self.assertTrue(mutation["rationale"])
                        self.assertNotIn(fragment, fragments)
                        fragments[fragment] = row_id

            arity = len(row["matching_shape"]["type_parameters"])
            if (
                row["method_name"] in {"lt", "le", "gt", "ge"}
                and arity > 1
            ):
                self.assertEqual(
                    {
                        mutation["id"]
                        for mutation in implementation_mutations
                    },
                    {
                        "chaining_equal_continue",
                        "chaining_non_equal_relation",
                        "chaining_none_false",
                    },
                )
            else:
                self.assertEqual(len(implementation_mutations), 1)

        self.assertEqual(len(impl_fragments), 184)
        self.assertEqual(len(completeness_fragments), 96)

    def test_unique_anchors_across_all_96_renders(self) -> None:
        """Every generated identifier that could collide (relation names,
        environment struct names, external_body helper names) must be
        globally unique across all 96 standalone renders."""

        relation_names: set[str] = set()
        environment_names: set[str] = set()
        helper_names: set[str] = set()
        for row in TUPLE_ROWS:
            template = self.templates[row["row_id"]]
            relation_name = template.accepted_relation_name
            self.assertIn(
                f"pub open spec fn {relation_name}<",
                template.implementation_proof,
            )
            self.assertNotIn(relation_name, relation_names)
            relation_names.add(relation_name)

            environment_match = re.search(
                r"pub ghost struct (\S+?)<", template.completeness_proof
            )
            self.assertIsNotNone(environment_match)
            environment_name = environment_match.group(1)
            self.assertNotIn(environment_name, environment_names)
            environment_names.add(environment_name)

            for boundary in template.boundaries:
                name = boundary["function"]
                self.assertNotIn(name, helper_names)
                helper_names.add(name)

        self.assertEqual(len(relation_names), 96)
        self.assertEqual(len(environment_names), 96)

    def test_orchestrator_normalization_yields_the_expected_anchors(self) -> None:
        """The orchestrator renames the family relation/target/theorem; the
        render has to survive that rewrite with the accepted contract intact."""

        for row in TUPLE_ROWS[:: max(1, len(TUPLE_ROWS) // 12)]:
            row_id = row["row_id"]
            _, accepted_contract_text = ACCEPTED_CONTRACTS[row_id]
            normalized = builder.normalized_template(self.templates[row_id])
            expected = _accepted_ensures_block(accepted_contract_text)
            with self.subTest(row_id=row_id):
                self.assertEqual(
                    normalized.accepted_relation_name, "accepted_contract"
                )
                self.assertIn(
                    "pub open spec fn cmp_relation_holds(",
                    normalized.implementation_proof,
                )
                self.assertIn(
                    "pub fn implementation_target<", normalized.implementation_proof
                )
                self.assertIn(expected, normalized.implementation_proof)
                self.assertIn(
                    "pub proof fn completeness_theorem<",
                    normalized.completeness_proof,
                )
                self.assertIn(
                    "implementation_target(left, right)",
                    normalized.completeness_proof,
                )
                self.assertIn(
                    '#[path = "implementation_proof.rs"]',
                    normalized.completeness_proof,
                )
                declaration = _declaration(
                    normalized.completeness_proof, "completeness_theorem"
                )
                self.assertGreaterEqual(declaration.count("accepted_contract("), 2)


VERUS_BINARY = runner.DEFAULT_VERUS
Z3_BINARY = runner.DEFAULT_Z3
_VERUS_AVAILABLE = VERUS_BINARY.is_file() and Z3_BINARY.is_file()


def _run_verus(path: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["VERUS_Z3_PATH"] = str(Z3_BINARY)
    return subprocess.run(
        [str(VERUS_BINARY), "--crate-type=lib", "--triggers-mode", "silent", str(path)],
        capture_output=True,
        text=True,
        timeout=110,
        env=env,
    )


def _assert_clean_verification(
    test: unittest.TestCase, result: subprocess.CompletedProcess[str]
) -> None:
    match = VERIFICATION_RE.search(result.stdout)
    test.assertIsNotNone(
        match,
        f"Verus did not report a verification summary.\nstdout={result.stdout}\n"
        f"stderr={result.stderr}",
    )
    verified, errors = int(match.group(1)), int(match.group(2))
    test.assertEqual(
        errors,
        0,
        f"expected 0 errors, got {errors} verified={verified}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}",
    )
    test.assertGreater(verified, 0)


def _assert_rejected(
    test: unittest.TestCase, result: subprocess.CompletedProcess[str]
) -> None:
    match = VERIFICATION_RE.search(result.stdout)
    test.assertIsNotNone(
        match,
        "mutation must still typecheck so Verus reaches verification.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}",
    )
    test.assertNotEqual(int(match.group(2)), 0, result.stdout)


@unittest.skipUnless(
    _VERUS_AVAILABLE, "pinned Verus/Z3 binaries are not available in this environment"
)
class ActualVerusRepresentativeTests(unittest.TestCase):
    """Feed representative renders to the real, pinned Verus binary
    (0.2026.07.21) so the standalone implementation and completeness proofs
    are checked end to end, not merely rendered."""

    REPRESENTATIVE_METHODS = ("eq", "cmp", "partial_cmp", "lt")

    @classmethod
    def setUpClass(cls) -> None:
        cls.by_method_arity: dict[tuple[str, int], dict[str, Any]] = {}
        for row in TUPLE_ROWS:
            arity = len(row["matching_shape"]["type_parameters"])
            cls.by_method_arity[(row["method_name"], arity)] = row

    def _render(self, method: str, arity: int) -> ProofTemplate:
        row = self.by_method_arity[(method, arity)]
        _, accepted_contract_text = ACCEPTED_CONTRACTS[row["row_id"]]
        return ptt.render(row, ptt.CONTRACT_FAMILY, accepted_contract_text)

    def _write_harness(
        self,
        directory: Path,
        implementation: str,
        completeness: str,
    ) -> Path:
        (directory / "implementation_proof.rs").write_text(
            implementation, encoding="utf-8"
        )
        (directory / "completeness_proof.rs").write_text(
            completeness, encoding="utf-8"
        )
        harness = (
            '#[path = "implementation_proof.rs"]\n'
            "pub mod implementation_proof;\n"
            '#[path = "completeness_proof.rs"]\n'
            "pub mod completeness_proof;\n"
        )
        harness_path = directory / "harness.rs"
        harness_path.write_text(harness, encoding="utf-8")
        return harness_path

    def _check_full_harness(self, method: str, arity: int) -> None:
        template = self._render(method, arity)
        with tempfile.TemporaryDirectory() as tmp:
            harness_path = self._write_harness(
                Path(tmp), template.implementation_proof, template.completeness_proof
            )
            _assert_clean_verification(self, _run_verus(harness_path))

    def test_arity_1_representative_methods_verify(self) -> None:
        for method in self.REPRESENTATIVE_METHODS:
            with self.subTest(method=method, arity=1):
                self._check_full_harness(method, 1)

    def test_arity_2_representative_methods_verify(self) -> None:
        for method in self.REPRESENTATIVE_METHODS:
            with self.subTest(method=method, arity=2):
                self._check_full_harness(method, 2)

    def test_arity_12_representative_methods_verify(self) -> None:
        for method in self.REPRESENTATIVE_METHODS:
            with self.subTest(method=method, arity=12):
                self._check_full_harness(method, 12)

    def test_orchestrator_shape_verifies_standalone(self) -> None:
        """Exactly what the orchestrator retains: normalized names, the
        implementation proof compiled on its own, and completeness compiled
        standalone through the implementation module."""

        for method, arity in (("eq", 1), ("lt", 12)):
            template = builder.normalized_template(self._render(method, arity))
            with self.subTest(method=method, arity=arity):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    implementation_path = tmp_path / "implementation_proof.rs"
                    completeness_path = tmp_path / "completeness_proof.rs"
                    implementation_path.write_text(
                        template.implementation_proof, encoding="utf-8"
                    )
                    completeness_path.write_text(
                        template.completeness_proof, encoding="utf-8"
                    )
                    _assert_clean_verification(
                        self, _run_verus(implementation_path)
                    )
                    _assert_clean_verification(self, _run_verus(completeness_path))

    def test_representative_implementation_mutations_break_verification(self) -> None:
        for method, arity in (("eq", 1), ("eq", 12), ("lt", 12)):
            template = self._render(method, arity)
            mutations = (
                template.implementation_mutations
                or (template.implementation_mutation,)
            )
            for mutation in mutations:
                with self.subTest(
                    method=method,
                    arity=arity,
                    mutation_id=mutation.get("id", "default"),
                ):
                    self.assertEqual(
                        template.implementation_proof.count(
                            mutation["fragment"]
                        ),
                        1,
                    )
                    mutated = template.implementation_proof.replace(
                        mutation["fragment"], mutation["replacement"]
                    )
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / "implementation_proof.rs"
                        path.write_text(mutated, encoding="utf-8")
                        _assert_rejected(self, _run_verus(path))

    def test_representative_completeness_mutations_break_verification(self) -> None:
        for method, arity in (("eq", 1), ("lt", 12)):
            with self.subTest(method=method, arity=arity):
                template = self._render(method, arity)
                mutation = template.completeness_mutation
                self.assertEqual(
                    template.completeness_proof.count(mutation["fragment"]), 1
                )
                mutated_completeness = template.completeness_proof.replace(
                    mutation["fragment"], mutation["replacement"]
                )
                with tempfile.TemporaryDirectory() as tmp:
                    harness_path = self._write_harness(
                        Path(tmp),
                        template.implementation_proof,
                        mutated_completeness,
                    )
                    _assert_rejected(self, _run_verus(harness_path))

    def test_dropping_the_count_boundary_call_breaks_verification(self) -> None:
        """The accepted global observation count is a real obligation: without
        the narrow trace/count boundary the target cannot be proved, so the
        boundary is not decorative and the count conjunct is not vacuous."""

        for method, arity in (("eq", 2), ("lt", 2)):
            with self.subTest(method=method, arity=arity):
                template = self._render(method, arity)
                boundary = next(
                    entry
                    for entry in template.boundaries
                    if entry["category"] == "observation_count_trace"
                )
                stripped = re.sub(
                    rf"\n *{re.escape(boundary['function'])}\(left, right[^;]*\);",
                    "",
                    template.implementation_proof,
                )
                self.assertNotIn(
                    f"{boundary['function']}(left, right", stripped
                )
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "implementation_proof.rs"
                    path.write_text(stripped, encoding="utf-8")
                    _assert_rejected(self, _run_verus(path))


if __name__ == "__main__":
    unittest.main()
