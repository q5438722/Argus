"""Tests for tools.proof_templates_sequence.

Covers all 27 owned pending rows (core/src/array/equality.rs,
core/src/array/mod.rs, core/src/slice/cmp.rs) with structural
render/anchor checks -- in particular that the frozen
``cmp_shared_vocabulary`` is used verbatim, that the exact accepted
observation/dispatch/result conjuncts are discharged, and that no
whole-target passthrough external helper stubs a sibling target -- plus an
actual-Verus verification pass (one row per rendered shape) and an
actual-Verus mutation pass (one row per contract family).
"""

from __future__ import annotations

import atexit
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import proof_templates_sequence as templates
from tools.proof_template_common import ProofTemplate

INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
VERUS = ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
Z3 = ROOT.parent / "verus" / "source" / "z3"
VERUS_TIMEOUT_SECONDS = 110  # keeps every command comfortably under 2 minutes

_FORBIDDEN_TARGET_TOKENS = (
    "unimplemented!()",
    "todo!()",
    "loop {}",
    "assume(",
    "admit(",
)

# The 14 inventory rows the semantic audit flagged as whole-target passthrough
# external helpers (inventory indices 051-058, 118, 213-217). Every one of them
# must now delegate to its sibling target for real.
_FORWARDING_ROWS = {
    "rustdoc-10909-10907": "rustdoc-10903-10901",
    "rustdoc-10909-10908": "rustdoc-10903-10902",
    "rustdoc-10912-10910": "rustdoc-10906-10904",
    "rustdoc-10912-10911": "rustdoc-10906-10905",
    "rustdoc-10915-10913": "rustdoc-10903-10901",
    "rustdoc-10915-10914": "rustdoc-10903-10902",
    "rustdoc-10918-10916": "rustdoc-10906-10904",
    "rustdoc-10918-10917": "rustdoc-10906-10905",
    "rustdoc-11323-11322": "rustdoc-11363-11362",
    "rustdoc-11546-11541": "rustdoc-11610-11605",
    "rustdoc-11546-11542": "rustdoc-11610-11606",
    "rustdoc-11546-11543": "rustdoc-11610-11607",
    "rustdoc-11546-11544": "rustdoc-11610-11609",
    "rustdoc-11546-11545": "rustdoc-11610-11608",
}

# Slice targets proved in this same campaign; they must never be stubbed by an
# alpha-identical external helper inside an array row's proof.
_CAMPAIGN_PROVED_SIBLINGS = (
    "rustdoc-11363-11362",
    "rustdoc-11610-11605",
    "rustdoc-11610-11606",
    "rustdoc-11610-11607",
    "rustdoc-11610-11608",
    "rustdoc-11610-11609",
)

# Accepted global vocabulary the semantic audit requires these rows to use
# rather than local stand-ins.
_ACCEPTED_VOCABULARY = (
    "cmp_sequence_observation_count",
    "cmp_array_eq_dispatch",
    "cmp_slice_eq_dispatch",
    "cmp_array_order_dispatch",
    "cmp_slice_order_dispatch",
    "cmp_always_applicable_ord_dispatch",
    "cmp_bytewise_equal",
    "cmp_unsigned_bytewise_order",
    "cmp_array_slice_forwarding",
)

_EXTERNAL_FUNCTION_RE = re.compile(
    r"#\[verifier::external_body\]\n"
    r"pub (?:(?:open|closed)\s+)?(?:spec|proof|exec)?\s*fn\s+([A-Za-z0-9_]+)"
)


def _load_rows() -> dict[str, dict[str, Any]]:
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return {row["row_id"]: row for row in data["rows"]}


_ROWS = _load_rows()

# One representative row per contract family, used for the actual-Verus
# mutation pass.
_FAMILY_REPRESENTATIVES = {
    templates.FAMILY_ARRAY_EQUALITY: "rustdoc-10900-10898",
    templates.FAMILY_SLICE_EQUALITY: "rustdoc-11030-11029",
    templates.FAMILY_ARRAY_ORDER: "rustdoc-11323-11322",
    templates.FAMILY_SLICE_ORDER: "rustdoc-11610-11605",
}

# One representative row per rendered shape, used for the actual-Verus
# verification pass (every distinct control shape this module emits).
_SHAPE_REPRESENTATIVES = {
    "array_eq_dispatch_base": "rustdoc-10900-10898",
    "array_eq_length_guard": "rustdoc-10903-10901",
    "array_eq_forward": "rustdoc-10915-10913",
    "slice_eq_dispatch": "rustdoc-11030-11029",
    "order_forward_cmp": "rustdoc-11323-11322",
    "order_forward_partial_cmp": "rustdoc-11546-11541",
    "order_forward_bool": "rustdoc-11546-11542",
    "order_dispatch_cmp": "rustdoc-11363-11362",
    "order_dispatch_partial_cmp": "rustdoc-11610-11605",
    "order_dispatch_bool": "rustdoc-11610-11606",
}


def _target_body(implementation_proof: str) -> str:
    start = implementation_proof.index("pub fn implementation_target")
    end = implementation_proof.index("\n}\n", start)
    return implementation_proof[start:end]


def _external_body_declarations(text: str) -> list[str]:
    """Every ``#[verifier::external_body]`` *function* declaration in ``text``."""
    declarations: list[str] = []
    for match in _EXTERNAL_FUNCTION_RE.finditer(text):
        opening = text.find("\n{", match.end())
        if opening < 0:
            continue
        declarations.append(text[match.start():opening])
    return declarations


def _accepted_contract_text(row_id: str) -> str:
    return f"accepted-contract-text-for-{row_id}"


class OwnershipAndSupportsTests(unittest.TestCase):
    def test_owns_exactly_27_rows(self) -> None:
        self.assertEqual(len(templates._ROW_PLAN), 27)

    def test_owned_rows_are_sourced_from_the_three_owned_files(self) -> None:
        owned_files = {
            templates._SOURCE_FILE_ARRAY_EQUALITY,
            templates._SOURCE_FILE_ARRAY_MOD,
            templates._SOURCE_FILE_SLICE_CMP,
        }
        for row_id in templates._ROW_PLAN:
            row = _ROWS[row_id]
            self.assertIn(row["source_file"], owned_files, row_id)
            self.assertEqual(row["disposition"], "pending", row_id)

    def test_family_counts_match_the_expected_partition(self) -> None:
        counts: dict[str, int] = {}
        for row_id in templates._ROW_PLAN:
            family = templates._classify(_ROWS[row_id])
            counts[family] = counts.get(family, 0) + 1
        self.assertEqual(
            counts,
            {
                templates.FAMILY_ARRAY_EQUALITY: 14,
                templates.FAMILY_SLICE_EQUALITY: 1,
                templates.FAMILY_ARRAY_ORDER: 6,
                templates.FAMILY_SLICE_ORDER: 6,
            },
        )

    def test_supports_true_for_every_owned_row_under_its_own_family(self) -> None:
        for row_id in templates._ROW_PLAN:
            row = _ROWS[row_id]
            family = templates._classify(row)
            with self.subTest(row_id=row_id):
                self.assertIsNotNone(family)
                self.assertTrue(templates.supports(row, family))

    def test_supports_false_for_mismatched_family(self) -> None:
        all_families = {
            templates.FAMILY_ARRAY_EQUALITY,
            templates.FAMILY_SLICE_EQUALITY,
            templates.FAMILY_ARRAY_ORDER,
            templates.FAMILY_SLICE_ORDER,
        }
        for row_id in templates._ROW_PLAN:
            row = _ROWS[row_id]
            own_family = templates._classify(row)
            for other_family in all_families - {own_family}:
                with self.subTest(row_id=row_id, other_family=other_family):
                    self.assertFalse(templates.supports(row, other_family))

    def test_supports_false_for_unowned_or_non_pending_rows(self) -> None:
        for row in _ROWS.values():
            if row["row_id"] in templates._ROW_PLAN:
                continue
            with self.subTest(row_id=row["row_id"]):
                self.assertFalse(
                    templates.supports(row, templates.FAMILY_ARRAY_EQUALITY)
                )
                self.assertFalse(
                    templates.supports(row, templates.FAMILY_SLICE_EQUALITY)
                )
                self.assertFalse(
                    templates.supports(row, templates.FAMILY_ARRAY_ORDER)
                )
                self.assertFalse(
                    templates.supports(row, templates.FAMILY_SLICE_ORDER)
                )

    def test_supports_false_when_disposition_is_not_pending(self) -> None:
        row = dict(_ROWS["rustdoc-10900-10898"])
        row["disposition"] = "exact_vstd"
        self.assertFalse(templates.supports(row, templates.FAMILY_ARRAY_EQUALITY))

    def test_every_shape_has_a_verus_representative(self) -> None:
        shapes = {plan["shape"] for plan in templates._ROW_PLAN.values()}
        self.assertEqual(shapes, set(_SHAPE_REPRESENTATIVES))
        for shape, row_id in _SHAPE_REPRESENTATIVES.items():
            self.assertEqual(templates._ROW_PLAN[row_id]["shape"], shape)


class RenderAllOwnedRowsTests(unittest.TestCase):
    """Structural render/anchor checks for all 27 owned rows (no Verus)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.templates: dict[str, ProofTemplate] = {}
        for row_id in templates._ROW_PLAN:
            row = _ROWS[row_id]
            family = templates._classify(row)
            cls.templates[row_id] = templates.render(
                row, family, _accepted_contract_text(row_id)
            )

    def test_render_rejects_unowned_row(self) -> None:
        row = _ROWS["rustdoc-10786-10785"]  # <Ordering as PartialEq<Ordering>>::eq
        with self.assertRaises(ValueError):
            templates.render(row, templates.FAMILY_ARRAY_EQUALITY, "x")

    def test_render_rejects_mismatched_family(self) -> None:
        row = _ROWS["rustdoc-10900-10898"]
        with self.assertRaises(ValueError):
            templates.render(row, templates.FAMILY_SLICE_ORDER, "x")

    def test_proof_family_matches_contract_family(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                expected = templates._classify(_ROWS[row_id])
                self.assertEqual(template.proof_family, expected)

    # -- frozen shared vocabulary -----------------------------------------
    def test_frozen_shared_vocabulary_is_inlined_verbatim(self) -> None:
        vocabulary = templates._vocabulary().rstrip("\n")
        self.assertIn("cmp_sequence_observation_count", vocabulary)
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                self.assertIn(vocabulary, template.implementation_proof)
                self.assertIn(
                    templates._vocabulary_digest(), template.implementation_proof
                )
                self.assertIn(
                    templates._vocabulary_digest(), template.completeness_proof
                )

    def test_completeness_reuses_the_implementation_module_vocabulary(self) -> None:
        vocabulary = templates._vocabulary().rstrip("\n")
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                # The completeness proof imports the implementation module
                # instead of redeclaring the accepted vocabulary.
                self.assertIn(
                    "use super::implementation_proof::*;",
                    template.completeness_proof,
                )
                self.assertNotIn(vocabulary, template.completeness_proof)

    def test_accepted_vocabulary_is_never_redeclared_locally(self) -> None:
        vocabulary = templates._vocabulary()
        for row_id, template in self.templates.items():
            outside = template.implementation_proof.replace(
                vocabulary.rstrip("\n"), ""
            )
            for symbol in _ACCEPTED_VOCABULARY:
                with self.subTest(row_id=row_id, symbol=symbol):
                    # Declared exactly once, inside the frozen vocabulary.
                    self.assertEqual(
                        vocabulary.count(f"spec fn {symbol}"), 1, symbol
                    )
                    self.assertNotIn(f"spec fn {symbol}", outside)
                    self.assertNotIn(
                        f"spec fn {symbol}", template.completeness_proof
                    )

    def test_every_row_uses_the_accepted_vocabulary_it_is_specified_with(
        self,
    ) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            used = {
                symbol
                for symbol in _ACCEPTED_VOCABULARY
                if any(symbol in clause for clause in contract.clauses)
            }
            with self.subTest(row_id=row_id):
                self.assertTrue(used, row_id)
                for symbol in used:
                    self.assertIn(symbol, template.implementation_proof)
                    self.assertIn(symbol, template.completeness_proof)

    # -- exact accepted contract ------------------------------------------
    def test_implementation_target_ensures_the_exact_accepted_clauses(self) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            target = _target_body(template.implementation_proof)
            with self.subTest(row_id=row_id):
                self.assertIn("    ensures\n", target)
                for clause in contract.clauses:
                    self.assertIn(f"        {clause},\n", target, clause[:60])

    def test_implementation_target_signature_matches_the_accepted_contract(
        self,
    ) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            declaration = (
                f"pub fn implementation_target{contract.generics}(\n"
                + contract.parameter_block()
                + f") -> ({contract.binding}: {contract.result_type})\n"
            )
            with self.subTest(row_id=row_id):
                self.assertIn(declaration, template.implementation_proof)

    def test_implementation_target_is_executable_and_non_external(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                impl = template.implementation_proof
                self.assertIn("pub fn implementation_target", impl)
                marker = "pub fn implementation_target"
                index = impl.index(marker)
                preceding = impl[max(0, index - 80):index]
                self.assertNotIn("external_body", preceding)
                body = _target_body(impl)
                body = body[body.index("\n{"):]
                for token in _FORBIDDEN_TARGET_TOKENS:
                    self.assertNotIn(token, body, f"{row_id}: forbidden {token!r}")
                self.assertTrue(body.strip())

    def test_implementation_and_completeness_never_assume_or_admit(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                self.assertNotIn("assume(", template.implementation_proof)
                self.assertNotIn("admit(", template.implementation_proof)
                self.assertNotIn("assume(", template.completeness_proof)
                self.assertNotIn("admit(", template.completeness_proof)

    # -- forwarding without whole-target passthrough helpers ---------------
    def test_flagged_forwarding_rows_call_the_sibling_target_directly(self) -> None:
        for row_id, sibling_id in _FORWARDING_ROWS.items():
            template = self.templates[row_id]
            sibling = templates._accepted(sibling_id)
            with self.subTest(row_id=row_id, sibling=sibling_id):
                # The sibling is bound to its own accepted contract ...
                self.assertIn(sibling.text, template.implementation_proof)
                # ... and the delegating body is a real call of it.
                body = _target_body(template.implementation_proof)
                self.assertIn(f"{sibling.target}(", body)

    def test_no_external_helper_reproduces_a_whole_target_outcome(self) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            accepted_clauses = list(contract.clauses)
            plan = templates._ROW_PLAN[row_id]
            if "sibling" in plan:
                accepted_clauses += list(templates._accepted(plan["sibling"]).clauses)
            declarations = _external_body_declarations(
                template.implementation_proof
            ) + _external_body_declarations(template.completeness_proof)
            for declaration in declarations:
                for clause in accepted_clauses:
                    with self.subTest(row_id=row_id, clause=clause[:48]):
                        self.assertNotIn(clause, declaration)

    def test_campaign_proved_siblings_are_never_stubbed(self) -> None:
        stub_names = {
            "rust_1_96_slice_ord_cmp",
            "rust_1_96_slice_partial_ord_partial_cmp",
            "rust_1_96_slice_partial_ord_lt",
            "rust_1_96_slice_partial_ord_le",
            "rust_1_96_slice_partial_ord_gt",
            "rust_1_96_slice_partial_ord_ge",
            "rust_1_96_elementwise_eq_array",
            "rust_1_96_array_n_partial_eq_slice",
            "rust_1_96_array_n_partial_ne_slice",
            "rust_1_96_slice_partial_eq_array_n",
            "rust_1_96_slice_partial_ne_array_n",
        }
        for row_id, template in self.templates.items():
            declared = set(
                _EXTERNAL_FUNCTION_RE.findall(template.implementation_proof)
            ) | set(_EXTERNAL_FUNCTION_RE.findall(template.completeness_proof))
            with self.subTest(row_id=row_id):
                self.assertFalse(declared & stub_names, sorted(declared & stub_names))
        for sibling_id in _CAMPAIGN_PROVED_SIBLINGS:
            with self.subTest(sibling=sibling_id):
                self.assertIn(sibling_id, templates._ROW_PLAN)

    def test_generic_loop_and_bytewise_branches_are_preserved(self) -> None:
        loop_rows = {
            "rustdoc-10900-10898",
            "rustdoc-10900-10899",
            "rustdoc-11030-11029",
            "rustdoc-11363-11362",
            "rustdoc-11610-11605",
            "rustdoc-11610-11606",
            "rustdoc-11610-11607",
            "rustdoc-11610-11608",
            "rustdoc-11610-11609",
        }
        for row_id in loop_rows:
            body = _target_body(self.templates[row_id].implementation_proof)
            with self.subTest(row_id=row_id):
                self.assertIn("while index <", body)
                self.assertIn("invariant", body)
                self.assertIn("decreases", body)
                self.assertTrue(
                    "bytewise_equal" in body or "compare_bytes" in body,
                    f"{row_id}: bytewise specialization branch missing",
                )

    # -- completeness ------------------------------------------------------
    def test_completeness_theorem_compares_two_accepted_contract_outcomes(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                comp = template.completeness_proof
                self.assertIn("pub proof fn completeness_theorem", comp)
                self.assertNotIn(
                    "#[verifier::external_body]\npub proof fn completeness_theorem",
                    comp,
                )
                self.assertGreaterEqual(comp.count("accepted_contract("), 2)
                self.assertEqual(
                    comp.count("call_ensures(implementation_contract_link"), 2
                )
                self.assertIn("result1 == result2", comp)

    def test_completeness_uses_the_exact_accepted_conjuncts(self) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            _, clauses = templates._environment_plan(contract)
            with self.subTest(row_id=row_id):
                for clause in clauses:
                    self.assertIn(
                        f"    &&& {clause}\n", template.completeness_proof
                    )
                # The link function re-states the accepted ensures verbatim.
                for clause in contract.clauses:
                    self.assertIn(
                        f"        {clause},\n", template.completeness_proof
                    )

    def test_completeness_pins_every_accepted_existential_witness(self) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            fields, clauses = templates._environment_plan(contract)
            comp = template.completeness_proof
            with self.subTest(row_id=row_id):
                for name, declared in fields:
                    self.assertIn(f"    pub {name}: {declared},\n", comp)
                    self.assertIn(f"environment.{name}", comp)
                # No accepted existential survives inside accepted_contract.
                start = comp.index("pub open spec fn accepted_contract")
                end = comp.index("\n}\n", start)
                self.assertNotIn("exists|", comp[start:end])
                self.assertTrue(clauses)

    def test_completeness_pins_every_accepted_dispatch_selector(self) -> None:
        for row_id, template in self.templates.items():
            contract = templates._accepted(row_id)
            selectors = [
                selector
                for selector in templates._DISPATCH_FIELDS
                if any(selector in clause for clause in contract.clauses)
            ]
            with self.subTest(row_id=row_id):
                self.assertTrue(selectors, row_id)
                for selector in selectors:
                    field = templates._DISPATCH_FIELDS[selector][0]
                    self.assertIn(
                        f"    &&& environment.{field} == {selector}(",
                        template.completeness_proof,
                    )

    def test_source_shape_tokens_are_non_empty_and_present_in_implementation(
        self,
    ) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                self.assertTrue(template.source_shape_tokens)
                for token in template.source_shape_tokens:
                    self.assertIn(token, template.implementation_proof)

    def test_source_shape_tokens_expose_the_owned_source_control_shape(self) -> None:
        # Spot-check that representative rows preserve the specific source
        # constructs called out by the task: dispatch, length guard,
        # forwarding, and the AlwaysApplicableOrd/bytewise paths.
        expectations = {
            "rustdoc-10900-10898": "SpecArrayEq::spec_eq(self, other)",
            "rustdoc-10903-10901": "other.as_array::<N>()",
            "rustdoc-10909-10907": "*self == **other",
            "rustdoc-11030-11029": "SlicePartialEq::equal_same_length",
            "rustdoc-11323-11322": "Ord::cmp(&&self[..], &&other[..])",
            "rustdoc-11363-11362": "SliceOrd::compare(self, other)",
            "rustdoc-11610-11605": "SlicePartialOrd::partial_compare(self, other)",
        }
        for row_id, needle in expectations.items():
            with self.subTest(row_id=row_id):
                template = self.templates[row_id]
                joined = "\n".join(template.source_shape_tokens)
                self.assertIn(needle, joined)

    def test_boundaries_are_narrow_and_non_whole_target(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                for boundary in template.boundaries:
                    self.assertIs(boundary["whole_target_outcome"], False)
                    self.assertIs(boundary["literal_external_body"], True)
                    self.assertTrue(boundary["function"])
                    needles = (
                        "#[verifier::external_body]\npub fn "
                        + boundary["function"],
                        "#[verifier::external_body]\npub proof fn "
                        + boundary["function"],
                    )
                    self.assertTrue(
                        any(
                            needle in template.implementation_proof
                            or needle in template.completeness_proof
                            for needle in needles
                        ),
                        f"{row_id}: boundary {boundary['function']} not found "
                        "as an external_body function",
                    )

    def test_declared_boundaries_match_the_rendered_external_helpers(self) -> None:
        for row_id, template in self.templates.items():
            declared = sorted(
                boundary["function"] for boundary in template.boundaries
            )
            rendered = sorted(
                set(_EXTERNAL_FUNCTION_RE.findall(template.implementation_proof))
                | set(_EXTERNAL_FUNCTION_RE.findall(template.completeness_proof))
            )
            with self.subTest(row_id=row_id):
                self.assertEqual(declared, rendered)

    def test_pure_delegation_rows_declare_no_external_helper_at_all(self) -> None:
        for row_id, plan in templates._ROW_PLAN.items():
            if plan["shape"] != "array_eq_forward":
                continue
            template = self.templates[row_id]
            with self.subTest(row_id=row_id):
                self.assertEqual(template.boundaries, ())
                self.assertEqual(
                    _EXTERNAL_FUNCTION_RE.findall(template.implementation_proof),
                    [],
                )

    def test_implementation_mutation_is_unique_and_typed_as_strings(self) -> None:
        for row_id, template in self.templates.items():
            mutations = (
                template.implementation_mutations
                or (template.implementation_mutation,)
            )
            for mutation in mutations:
                with self.subTest(
                    row_id=row_id,
                    mutation_id=mutation.get("id", "default"),
                ):
                    for key in (
                        "fragment",
                        "replacement",
                        "category",
                        "omitted_observable",
                    ):
                        self.assertIn(key, mutation)
                        self.assertIsInstance(mutation[key], str)
                        self.assertTrue(mutation[key])
                    self.assertEqual(
                        template.implementation_proof.count(
                            mutation["fragment"]
                        ),
                        1,
                    )
                    self.assertNotEqual(
                        mutation["fragment"],
                        mutation["replacement"],
                    )
            if templates._ROW_PLAN[row_id]["shape"] == "order_dispatch_bool":
                self.assertEqual(
                    {mutation["id"] for mutation in mutations},
                    {
                        "bytewise_relation",
                        "chaining_equal_continue",
                        "chaining_non_equal_relation",
                        "chaining_none_false",
                    },
                )
            else:
                self.assertEqual(len(mutations), 1)

    def test_completeness_mutation_is_unique_and_typed_as_strings(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                mutation = template.completeness_mutation
                for key in ("fragment", "replacement", "category", "omitted_observable"):
                    self.assertIn(key, mutation)
                    self.assertIsInstance(mutation[key], str)
                    self.assertTrue(mutation[key])
                self.assertEqual(
                    template.completeness_proof.count(mutation["fragment"]), 1
                )
                self.assertNotEqual(mutation["fragment"], mutation["replacement"])

    def test_mutation_categories_cover_the_required_dimensions(self) -> None:
        categories = set()
        for template in self.templates.values():
            categories.update(
                mutation["category"]
                for mutation in (
                    template.implementation_mutations
                    or (template.implementation_mutation,)
                )
            )
            categories.update(
                mutation["category"]
                for mutation in (
                    template.completeness_mutations
                    or (template.completeness_mutation,)
                )
            )
        self.assertIn(templates.MUTATION_FORWARDING, categories)
        self.assertIn(templates.MUTATION_SPECIALIZATION_DISPATCH, categories)
        self.assertIn(templates.MUTATION_EQUALITY_ORDERING_DISTINCTION, categories)
        self.assertIn(templates.MUTATION_BRANCH_REVERSAL, categories)
        self.assertIn("chaining_equal_continue", categories)
        self.assertIn("chaining_non_equal_relation", categories)
        self.assertIn("chaining_none_false", categories)

    def test_slice_relations_derive_every_chaining_branch_from_partial_cmp(
        self,
    ) -> None:
        row_ids = [
            row_id
            for row_id, plan in templates._ROW_PLAN.items()
            if plan["shape"] == "order_dispatch_bool"
        ]
        self.assertEqual(len(row_ids), 4)
        for row_id in row_ids:
            text = self.templates[row_id].implementation_proof
            with self.subTest(row_id=row_id):
                self.assertIn(
                    "rust_1_96_partial_cmp_step",
                    text,
                )
                self.assertIn(
                    "call_ensures(\n"
                    "            <T as PartialOrd>::partial_cmp",
                    text,
                )
                self.assertIn(
                    "Some(core::cmp::Ordering::Equal) =>",
                    text,
                )
                self.assertIn("Some(order) =>", text)
                self.assertIn("None =>", text)
                self.assertIn(
                    "cmp_lexicographic_partial_cmp_prefix",
                    text,
                )
                self.assertNotIn(
                    "cmp_private_chaining_outcome",
                    text,
                )
                self.assertNotIn("cmp_slice_chaining_prefix", text)

    def test_every_row_implementation_mutation_matches_its_plan_category(self) -> None:
        for row_id, template in self.templates.items():
            with self.subTest(row_id=row_id):
                expected = templates._ROW_PLAN[row_id]["mutation"]
                self.assertEqual(
                    template.implementation_mutation["category"], expected
                )
                self.assertEqual(
                    template.completeness_mutation["category"], expected
                )

    def test_render_is_deterministic(self) -> None:
        for row_id in templates._ROW_PLAN:
            with self.subTest(row_id=row_id):
                row = _ROWS[row_id]
                family = templates._classify(row)
                again = templates.render(row, family, _accepted_contract_text(row_id))
                self.assertEqual(again, self.templates[row_id])

    def test_accepted_contract_text_is_bound_into_the_rendered_header(self) -> None:
        row = _ROWS["rustdoc-10900-10898"]
        family = templates._classify(row)
        first = templates.render(row, family, "alpha")
        second = templates.render(row, family, "beta")
        self.assertNotEqual(
            first.implementation_proof, second.implementation_proof
        )
        self.assertIn(
            templates._contract_digest("alpha"), first.implementation_proof
        )
        self.assertIn(
            templates._contract_digest("beta"), second.implementation_proof
        )


def _write_harness(directory: Path, implementation: str, completeness: str) -> Path:
    """Materialize the pair exactly the way build_implementation_proofs does.

    ``implementation_proof.rs`` is a standalone crate root; the completeness
    proof pulls it in as a ``#[path]`` module, which is how
    ``tools/run_implementation_proofs.py`` verifies each file.
    """
    (directory / "implementation_proof.rs").write_text(implementation, encoding="utf-8")
    (directory / "completeness_proof.rs").write_text(
        completeness.replace(
            "use super::implementation_proof::*;",
            '#[path = "implementation_proof.rs"]\n'
            "mod implementation_proof;\n"
            "use implementation_proof::*;",
            1,
        ),
        encoding="utf-8",
    )
    return directory / "completeness_proof.rs"


def _scratch_dir() -> tempfile.TemporaryDirectory:
    # Keep all scratch Verus inputs inside the repository tree rather than
    # the system temp directory.
    scratch_root = ROOT / ".pytest_verus_scratch"
    scratch_root.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(scratch_root))


atexit.register(
    shutil.rmtree, str(ROOT / ".pytest_verus_scratch"), True
)


def _run_verus(proof: Path, *, no_verify: bool) -> subprocess.CompletedProcess:
    command = [str(VERUS), "--crate-type=lib"]
    if no_verify:
        command.append("--no-verify")
    else:
        command.append("--triggers-mode")
        command.append("silent")
    command.append(proof.name)
    return subprocess.run(
        command,
        cwd=proof.parent,
        capture_output=True,
        text=True,
        timeout=VERUS_TIMEOUT_SECONDS,
    )


@unittest.skipUnless(VERUS.is_file(), "actual Verus binary is not available")
class ActualVerusRepresentativeTests(unittest.TestCase):
    """Runs the real Verus binary for one representative row per shape.

    Confirms both that the rendered proof pair actually verifies -- the
    implementation target discharging the exact accepted contract and the
    completeness theorem deriving exact result equality -- and that the
    implementation/completeness mutations are unique, type-check, and are
    rejected by actual Verus. Every invocation below completes in about a
    second, so each command stays far inside the two-minute budget.
    """

    def test_shape_representatives_verify(self) -> None:
        for shape, row_id in _SHAPE_REPRESENTATIVES.items():
            with self.subTest(shape=shape, row_id=row_id):
                row = _ROWS[row_id]
                family = templates._classify(row)
                template = templates.render(
                    row, family, _accepted_contract_text(row_id)
                )
                with _scratch_dir() as tmp:
                    completeness = _write_harness(
                        Path(tmp),
                        template.implementation_proof,
                        template.completeness_proof,
                    )
                    implementation = completeness.parent / "implementation_proof.rs"
                    for proof in (implementation, completeness):
                        result = _run_verus(proof, no_verify=False)
                        self.assertEqual(
                            result.returncode,
                            0,
                            msg=(
                                f"{row_id}/{proof.name} failed to verify:\n"
                                f"{result.stdout}\n{result.stderr}"
                            ),
                        )
                        self.assertIn("0 errors", result.stdout)

    def test_family_representative_mutations_typecheck_and_are_rejected(self) -> None:
        for family, row_id in _FAMILY_REPRESENTATIVES.items():
            row = _ROWS[row_id]
            template = templates.render(row, family, _accepted_contract_text(row_id))
            for proof_kind, mutation in (
                ("implementation", template.implementation_mutation),
                ("completeness", template.completeness_mutation),
            ):
                with self.subTest(family=family, row_id=row_id, proof_kind=proof_kind):
                    implementation = template.implementation_proof
                    completeness = template.completeness_proof
                    if proof_kind == "implementation":
                        self.assertEqual(
                            implementation.count(mutation["fragment"]), 1
                        )
                        implementation = implementation.replace(
                            mutation["fragment"], mutation["replacement"], 1
                        )
                    else:
                        self.assertEqual(
                            completeness.count(mutation["fragment"]), 1
                        )
                        completeness = completeness.replace(
                            mutation["fragment"], mutation["replacement"], 1
                        )
                    with _scratch_dir() as tmp:
                        proof = _write_harness(
                            Path(tmp), implementation, completeness
                        )
                        no_verify = _run_verus(proof, no_verify=True)
                        self.assertEqual(
                            no_verify.returncode,
                            0,
                            msg=(
                                f"{row_id}/{proof_kind} mutation failed to "
                                f"typecheck:\n{no_verify.stdout}\n{no_verify.stderr}"
                            ),
                        )
                        actual = _run_verus(proof, no_verify=False)
                        self.assertNotEqual(
                            actual.returncode,
                            0,
                            msg=(
                                f"{row_id}/{proof_kind} mutation was not "
                                f"rejected by actual Verus:\n{actual.stdout}"
                            ),
                        )

    def test_all_slice_chaining_branch_mutations_are_decisive(self) -> None:
        row_id = "rustdoc-11610-11606"
        row = _ROWS[row_id]
        family = templates._classify(row)
        template = templates.render(
            row, family, _accepted_contract_text(row_id)
        )
        mutations = [
            mutation
            for mutation in template.implementation_mutations
            if mutation["id"].startswith("chaining_")
        ]
        self.assertEqual(len(mutations), 3)
        for mutation in mutations:
            with self.subTest(mutation_id=mutation["id"]):
                implementation = template.implementation_proof.replace(
                    mutation["fragment"],
                    mutation["replacement"],
                    1,
                )
                with _scratch_dir() as tmp:
                    proof = _write_harness(
                        Path(tmp),
                        implementation,
                        template.completeness_proof,
                    )
                    no_verify = _run_verus(proof, no_verify=True)
                    self.assertEqual(
                        no_verify.returncode,
                        0,
                        msg=(
                            f"{mutation['id']} failed to typecheck:\n"
                            f"{no_verify.stdout}\n{no_verify.stderr}"
                        ),
                    )
                    actual = _run_verus(proof, no_verify=False)
                    self.assertNotEqual(
                        actual.returncode,
                        0,
                        msg=(
                            f"{mutation['id']} was not rejected:\n"
                            f"{actual.stdout}\n{actual.stderr}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
