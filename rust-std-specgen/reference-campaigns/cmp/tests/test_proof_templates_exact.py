"""Tests for `tools/proof_templates_exact.py`.

These tests own two responsibilities mirroring the module's own scope:

1. Render every ``disposition == "exact_vstd"`` inventory
   rows and check the rendered `ProofTemplate` objects are structurally
   sound (own exactly this row set, embed no `assume`/`admit`/
   `external_body`, declare a unique `completeness_theorem`, and expose
   mutation fragments that are anchored exactly once in their own file),
   and that the three required mutation categories
   (``forwarding``/``branch_reversal``/``equality_ordering_distinction``)
   are represented across the owned rows.
2. Compile and verify a representative row per structural family (plus a
   panic-domain edge case) with the real, locally built Verus
   binary: the unmutated `implementation_proof`/`completeness_proof` must
   verify, and every mutated variant must be rejected by Verus with a
   recognizable soundness-violation diagnostic. Every subprocess call is
   bounded well under two minutes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from tools import proof_templates_exact as templates
from tools.proof_template_common import ProofTemplate

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
EXACT_VSTD_AUDIT = ROOT / "inventory" / "exact_vstd_audit.json"

# Mirrors tools/run_implementation_proofs.py's DEFAULT_VERUS/DEFAULT_Z3
# resolution: a sibling checkout of the Verus repository built in release
# mode next to this campaign's own repository root.
DEFAULT_VERUS = ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
DEFAULT_Z3 = ROOT.parent / "verus" / "source" / "z3"

VERUS_TIMEOUT_SECONDS = 100  # comfortably under the two-minute budget
SCRATCH_DIR = ROOT / ".pytest_cache" / "proof_templates_exact_verus_scratch"

REQUIRED_MUTATION_CATEGORIES = frozenset(
    (
        "forwarding",
        "branch_reversal",
        "equality_ordering_distinction",
    )
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _accepted_contract_text_index() -> dict[str, str]:
    """Build ``row_id -> literal referenced vstd contract text``.

    Sourced from the independent exact-vstd audit's own evidence span
    (`snapshot_path`, `declaration_begin_line`, `declaration_end_line`),
    which is exactly the declaration this module's rendered proofs must
    reference rather than redeclare.
    """

    audit = _load(EXACT_VSTD_AUDIT)
    index: dict[str, str] = {}
    cache: dict[str, list[str]] = {}
    for record in audit["records"]:
        evidence = record["evidence"]
        snapshot_path = evidence["snapshot_path"]
        if snapshot_path not in cache:
            cache[snapshot_path] = (ROOT / snapshot_path).read_text(
                encoding="utf-8"
            ).splitlines(keepends=True)
        lines = cache[snapshot_path]
        begin = int(evidence["declaration_begin_line"])
        end = int(evidence["declaration_end_line"])
        index[record["row_id"]] = "".join(lines[begin - 1:end])
    return index


class ProofTemplatesExactOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = _load(INVENTORY)
        cls.rows = cls.inventory["rows"]
        cls.exact_rows = [
            row for row in cls.rows if row["disposition"] == "exact_vstd"
        ]
        cls.non_exact_rows = [
            row for row in cls.rows if row["disposition"] != "exact_vstd"
        ]
        cls.accepted_contract_text = _accepted_contract_text_index()

    def test_exact_vstd_rows_exclude_float_model_boundaries(self) -> None:
        self.assertEqual(len(self.exact_rows), 124)
        self.assertFalse(any(
            row["owner_type"] in {"f32", "f64"}
            for row in self.exact_rows
        ))

    def test_supports_owns_all_and_only_exact_vstd_rows(self) -> None:
        owned_ids = {
            row["row_id"]
            for row in self.rows
            if templates.supports(row, "exact_vstd")
        }
        exact_ids = {row["row_id"] for row in self.exact_rows}
        self.assertEqual(owned_ids, exact_ids)
        self.assertEqual(len(owned_ids), len(self.exact_rows))

    def test_supports_rejects_non_exact_vstd_rows(self) -> None:
        for row in self.non_exact_rows:
            with self.subTest(row_id=row["row_id"]):
                self.assertFalse(templates.supports(row, "exact_vstd"))

    def test_supports_rejects_foreign_contract_family_labels(self) -> None:
        for row in self.exact_rows:
            with self.subTest(row_id=row["row_id"]):
                self.assertFalse(templates.supports(row, "not_exact_vstd"))
                self.assertFalse(templates.supports(row, ""))
                self.assertFalse(templates.supports(row, "exact_vstd "))

    def test_supports_rejects_non_mapping_rows(self) -> None:
        self.assertFalse(templates.supports(None, "exact_vstd"))  # type: ignore[arg-type]
        self.assertFalse(templates.supports("not-a-row", "exact_vstd"))  # type: ignore[arg-type]
        self.assertFalse(templates.supports(["not", "a", "row"], "exact_vstd"))  # type: ignore[arg-type]

    def test_render_rejects_unowned_rows(self) -> None:
        foreign_row = self.non_exact_rows[0]
        with self.assertRaises(ValueError):
            templates.render(foreign_row, "exact_vstd", "// text")

    def test_render_rejects_wrong_contract_family(self) -> None:
        row = self.exact_rows[0]
        text = self.accepted_contract_text[row["row_id"]]
        with self.assertRaises(ValueError):
            templates.render(row, "some_other_family", text)

    def test_render_rejects_empty_accepted_contract_text(self) -> None:
        row = self.exact_rows[0]
        with self.assertRaises(ValueError):
            templates.render(row, "exact_vstd", "")
        with self.assertRaises(ValueError):
            templates.render(row, "exact_vstd", "   \n  ")


class ProofTemplatesExactRenderAllTests(unittest.TestCase):
    """Renders and structurally validates every owned row."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = _load(INVENTORY)
        cls.exact_rows = [
            row
            for row in cls.inventory["rows"]
            if row["disposition"] == "exact_vstd"
        ]
        cls.accepted_contract_text = _accepted_contract_text_index()
        cls.rendered: dict[str, ProofTemplate] = {}
        for row in cls.exact_rows:
            text = cls.accepted_contract_text[row["row_id"]]
            cls.rendered[row["row_id"]] = templates.render(
                row, "exact_vstd", text
            )

    def test_every_owned_row_renders_a_proof_template(self) -> None:
        self.assertEqual(len(self.rendered), len(self.exact_rows))
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertIsInstance(template, ProofTemplate)
                self.assertIn(template.proof_family, templates.ALL_FAMILIES)

    def test_no_external_body_assume_or_admit_anywhere(self) -> None:
        for row_id, template in self.rendered.items():
            for label, text in (
                ("implementation_proof", template.implementation_proof),
                ("completeness_proof", template.completeness_proof),
            ):
                with self.subTest(row_id=row_id, text=label):
                    self.assertNotIn("external_body", text)
                    self.assertNotIn("assume(", text)
                    self.assertNotIn("admit(", text)

    @staticmethod
    def _non_comment_code(text: str) -> str:
        # The quoted, traceability-only `accepted_contract_text` block is
        # prefixed with `// ` on every line and may itself legitimately
        # contain the literal string `assume_specification` (it is often a
        # verbatim copy of the referenced vstd `assume_specification`
        # declaration). Only non-comment lines constitute actual rendered
        # code that must not redeclare it.
        return "\n".join(
            line
            for line in text.splitlines()
            if not line.lstrip().startswith("//")
        )

    def test_accepted_contract_is_referenced_not_redeclared(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                # The proof-local wrapper is always literally named
                # `accepted_contract`; it must appear in both proofs, and
                # the file's actual *code* (excluding the traceability
                # comment quoting the referenced vstd declaration) must not
                # declare a competing `assume_specification` for the row's
                # own target (that remains solely vstd's).
                self.assertIn(
                    "pub open spec fn accepted_contract",
                    template.implementation_proof,
                )
                self.assertIn(
                    "pub open spec fn accepted_contract",
                    template.completeness_proof,
                )
                self.assertNotIn(
                    "assume_specification",
                    self._non_comment_code(template.implementation_proof),
                )
                self.assertNotIn(
                    "assume_specification",
                    self._non_comment_code(template.completeness_proof),
                )

    def test_accepted_contract_text_is_embedded_for_traceability(self) -> None:
        row = self.exact_rows[0]
        template = self.rendered[row["row_id"]]
        reference_text = self.accepted_contract_text[row["row_id"]]
        first_reference_line = reference_text.splitlines()[0]
        self.assertIn(first_reference_line, template.implementation_proof)

    def test_completeness_theorem_is_present_and_scoped(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertIn(
                    "pub proof fn completeness_theorem",
                    template.completeness_proof,
                )
                self.assertGreaterEqual(
                    template.completeness_proof.count("accepted_contract("),
                    2,
                )

    def test_whole_target_outcome_is_always_false_when_boundaries_exist(
        self,
    ) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                for boundary in template.boundaries:
                    self.assertIs(boundary["whole_target_outcome"], False)

    def test_mutation_fragments_are_uniquely_anchored(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                impl_fragment = template.implementation_mutation["fragment"]
                comp_fragment = template.completeness_mutation["fragment"]
                self.assertEqual(
                    template.implementation_proof.count(impl_fragment), 1
                )
                self.assertEqual(
                    template.completeness_proof.count(comp_fragment), 1
                )

    def test_mutations_actually_change_the_text(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                im = template.implementation_mutation
                cm = template.completeness_mutation
                self.assertNotEqual(im["fragment"], im["replacement"])
                self.assertNotEqual(cm["fragment"], cm["replacement"])

    def test_mutation_categories_are_from_the_allowed_vocabulary(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertIn(
                    template.implementation_mutation["category"],
                    REQUIRED_MUTATION_CATEGORIES,
                )
                self.assertIn(
                    template.completeness_mutation["category"],
                    REQUIRED_MUTATION_CATEGORIES,
                )

    def test_all_three_mutation_categories_are_covered_across_owned_rows(
        self,
    ) -> None:
        seen = {
            template.implementation_mutation["category"]
            for template in self.rendered.values()
        }
        self.assertEqual(seen, REQUIRED_MUTATION_CATEGORIES)

    def test_forwarding_category_is_exactly_the_shared_reference_family(
        self,
    ) -> None:
        forwarding_rows = {
            row_id
            for row_id, template in self.rendered.items()
            if template.implementation_mutation["category"] == "forwarding"
        }
        shared_reference_rows = {
            row_id
            for row_id, template in self.rendered.items()
            if template.proof_family
            == templates.FAMILY_SHARED_REFERENCE_FORWARDING
        }
        self.assertEqual(forwarding_rows, shared_reference_rows)
        self.assertEqual(len(forwarding_rows), 8)

    def test_family_row_counts_match_the_inventory_partition(self) -> None:
        counts: dict[str, int] = {}
        for template in self.rendered.values():
            counts[template.proof_family] = counts.get(template.proof_family, 0) + 1
        self.assertEqual(
            counts,
            {
                templates.FAMILY_PRIMITIVE_SCALAR: 98,
                templates.FAMILY_SHARED_REFERENCE_FORWARDING: 8,
                templates.FAMILY_ORDERING_INHERENT: 8,
                templates.FAMILY_OPTION_RELATIONAL: 3,
                templates.FAMILY_TRAIT_DEFAULT: 7,
            },
        )

    def test_source_shape_tokens_are_present_when_declared(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                for token in template.source_shape_tokens:
                    self.assertIsInstance(token, str)
                    self.assertTrue(token)

    def test_render_is_deterministic(self) -> None:
        row = self.exact_rows[0]
        text = self.accepted_contract_text[row["row_id"]]
        first = templates.render(row, "exact_vstd", text)
        second = templates.render(row, "exact_vstd", text)
        self.assertEqual(first, second)


def _verus_available() -> bool:
    return DEFAULT_VERUS.is_file() and DEFAULT_Z3.is_file()


@unittest.skipUnless(
    _verus_available(),
    "actual Verus binary/z3 not available in this environment",
)
class ProofTemplatesExactActualVerusTests(unittest.TestCase):
    """Runs the real, locally built Verus binary over representative rows.

    One representative is selected per structural family.
    Every unmutated proof must verify; every mutated proof must be
    rejected with a recognizable soundness-violation diagnostic. Each
    `verus` invocation is bounded by `VERUS_TIMEOUT_SECONDS` (100s), well
    under the two-minute budget.
    """

    REPRESENTATIVES = {
        "primitive_scalar_int": "rustdoc-10827-10825",  # <i32 as PartialEq>::eq
        "primitive_scalar_int_cmp": "rustdoc-11287-11285",  # <i32 as Ord>::cmp
        "shared_reference_forwarding": "rustdoc-10850-10848",  # <&A as PartialEq<&B>>::eq
        "ordering_inherent": "rustdoc-11181-11178",  # Ordering::reverse
        "option_relational": "rustdoc-10997-10996",  # <Option<T> as PartialEq>::eq
        "trait_default_max": "trait-default-50-11239",  # Ord::max default
    }

    EXPECTED_REJECTION_SUBSTRINGS = (
        "postcondition not satisfied",
        "assertion failed",
        "precondition not satisfied",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = _load(INVENTORY)
        cls.rows = {row["row_id"]: row for row in cls.inventory["rows"]}
        cls.accepted_contract_text = _accepted_contract_text_index()
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(SCRATCH_DIR, ignore_errors=True)

    def _run_verus(self, path: Path) -> subprocess.CompletedProcess[str]:
        import os

        environment = os.environ.copy()
        environment["VERUS_Z3_PATH"] = str(DEFAULT_Z3)
        return subprocess.run(
            [str(DEFAULT_VERUS), str(path), "--crate-type=lib"],
            cwd=path.parent,
            env=environment,
            capture_output=True,
            text=True,
            timeout=VERUS_TIMEOUT_SECONDS,
        )

    def _write(self, name: str, text: str) -> Path:
        path = SCRATCH_DIR / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_representatives_verify_and_their_mutations_are_rejected(
        self,
    ) -> None:
        for label, row_id in self.REPRESENTATIVES.items():
            with self.subTest(representative=label, row_id=row_id):
                row = self.rows[row_id]
                text = self.accepted_contract_text[row_id]
                template = templates.render(row, "exact_vstd", text)

                # --- unmutated implementation_proof must verify ---
                impl_path = self._write(
                    f"{label}_implementation_proof.rs",
                    template.implementation_proof,
                )
                impl_result = self._run_verus(impl_path)
                self.assertEqual(
                    impl_result.returncode,
                    0,
                    msg=(
                        f"{label} implementation_proof failed to verify:\n"
                        f"{impl_result.stdout}\n{impl_result.stderr}"
                    ),
                )
                self.assertIn(
                    "verified", impl_result.stdout + impl_result.stderr
                )

                # --- unmutated completeness_proof must verify ---
                comp_path = self._write(
                    f"{label}_completeness_proof.rs",
                    template.completeness_proof,
                )
                comp_result = self._run_verus(comp_path)
                self.assertEqual(
                    comp_result.returncode,
                    0,
                    msg=(
                        f"{label} completeness_proof failed to verify:\n"
                        f"{comp_result.stdout}\n{comp_result.stderr}"
                    ),
                )

                # --- mutated implementation_proof must be rejected ---
                im = template.implementation_mutation
                self.assertEqual(
                    template.implementation_proof.count(im["fragment"]), 1
                )
                mutated_impl_text = template.implementation_proof.replace(
                    im["fragment"], im["replacement"], 1
                )
                mutated_impl_path = self._write(
                    f"{label}_implementation_proof_MUTATED.rs",
                    mutated_impl_text,
                )
                mutated_impl_result = self._run_verus(mutated_impl_path)
                self.assertNotEqual(mutated_impl_result.returncode, 0)
                combined = (
                    mutated_impl_result.stdout + mutated_impl_result.stderr
                )
                self.assertTrue(
                    any(
                        needle in combined
                        for needle in self.EXPECTED_REJECTION_SUBSTRINGS
                    ),
                    msg=f"{label} mutation was not rejected as expected:\n{combined}",
                )

                # --- mutated completeness_proof must be rejected ---
                cm = template.completeness_mutation
                self.assertEqual(
                    template.completeness_proof.count(cm["fragment"]), 1
                )
                mutated_comp_text = template.completeness_proof.replace(
                    cm["fragment"], cm["replacement"], 1
                )
                mutated_comp_path = self._write(
                    f"{label}_completeness_proof_MUTATED.rs",
                    mutated_comp_text,
                )
                mutated_comp_result = self._run_verus(mutated_comp_path)
                self.assertNotEqual(mutated_comp_result.returncode, 0)
                combined = (
                    mutated_comp_result.stdout + mutated_comp_result.stderr
                )
                self.assertTrue(
                    any(
                        needle in combined
                        for needle in self.EXPECTED_REJECTION_SUBSTRINGS
                    ),
                    msg=f"{label} completeness mutation was not rejected as expected:\n{combined}",
                )


if __name__ == "__main__":
    unittest.main()
