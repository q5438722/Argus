from __future__ import annotations

import re
import unittest

from tools import build_implementation_proofs as proofs
from tools import build_specification
from tools import check_implementation_proofs
from tools import check_specification


REQUIRED_TARGET_FILES = (
    "implementation_proof.rs",
    "completeness_proof.rs",
    "source_excerpt.rs",
    "accepted_contract.rs",
    "contract_equivalence.json",
    "source_body.json",
    "transformation_manifest.json",
    "dependency_assumptions.json",
    "trust_boundaries.json",
    "proof_manifest.json",
)

MIRRORED_MANIFEST_FILES = (
    "source_body.json",
    "transformation_manifest.json",
    "dependency_assumptions.json",
)

TARGET_SIGNATURE = re.compile(
    r"((?:#\[[^\n]*\]\s*\n\s*)*)pub fn implementation_target\b"
)
COMPLETENESS_SIGNATURE = re.compile(
    r"((?:#\[[^\n]*\]\s*\n\s*)*)(?:pub )?proof fn completeness_theorem\b"
)


class ImplementationGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        inventory_rows = proofs.load(build_specification.INVENTORY)["rows"]
        cls.catalog_rows = proofs.load(build_specification.CATALOG)["rows"]
        cls.catalog_by_id = {
            row["row_id"]: row for row in cls.catalog_rows
        }
        cls.rows = proofs.selected_proof_rows(
            inventory_rows,
            cls.catalog_rows,
        )
        cls.targets = proofs.load(proofs.TARGETS_JSON)["rows"]

    def test_every_selected_row_has_exactly_one_renderer(self) -> None:
        blocks = check_specification.contract_blocks(
            build_specification.GENERATED.read_text(encoding="utf-8")
        )
        for row in self.rows:
            family = (
                "exact_vstd"
                if row["disposition"] == "exact_vstd"
                else blocks[row["row_id"]][0]
            )
            with self.subTest(row_id=row["row_id"]):
                matches = [
                    module
                    for module in proofs.TEMPLATE_MODULES
                    if module.supports(row, family)
                ]
                self.assertEqual(len(matches), 1)

    def test_target_layout_is_inventory_derived_and_unique(self) -> None:
        self.assertEqual(
            {row["row_id"] for row in self.targets},
            {row["row_id"] for row in self.rows},
        )
        self.assertEqual(len(self.targets), len(self.rows))
        self.assertEqual(
            len({row["target_dir"] for row in self.targets}),
            len(self.rows),
        )
        children = {
            path.name
            for path in proofs.HARNESS_ROOT.iterdir()
            if path.is_dir()
        }
        self.assertEqual(children, {row["slug"] for row in self.targets})

    def test_generated_artifacts_are_byte_deterministic(self) -> None:
        payloads, _ = proofs.build_payloads()
        for path, expected in payloads.items():
            if path in {proofs.AGGREGATE_JSON, proofs.AGGREGATE_MD}:
                continue
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_bytes(), expected)

    def test_manifests_bind_current_proofs_sources_and_review(self) -> None:
        by_id = {row["row_id"]: row for row in self.rows}
        review_hash = proofs.sha256(
            check_specification.INDEPENDENT_REVIEW
        )
        for target in self.targets:
            row = by_id[target["row_id"]]
            directory = build_specification.ROOT / target["target_dir"]
            manifest = proofs.load(directory / "proof_manifest.json")
            with self.subTest(row_id=row["row_id"]):
                self.assertEqual(
                    manifest["inventory_signature_sha256"],
                    proofs.compact_hash(row["signature"]),
                )
                self.assertEqual(
                    manifest["source_span_sha256"],
                    row["source_evidence"]["span_sha256"],
                )
                self.assertEqual(
                    manifest["specification_review_sha256"],
                    review_hash,
                )
                for name in (
                    "implementation_proof",
                    "completeness_proof",
                    "accepted_contract",
                    "source_excerpt",
                ):
                    self.assertEqual(
                        manifest[f"{name}_sha256"],
                        proofs.sha256(directory / f"{name}.rs"),
                    )

    def test_every_target_colocates_the_required_proof_files(self) -> None:
        for target in self.targets:
            directory = build_specification.ROOT / target["target_dir"]
            mirror = proofs.MANIFEST_ROOT / target["slug"]
            with self.subTest(row_id=target["row_id"]):
                self.assertTrue(directory.is_dir())
                for name in REQUIRED_TARGET_FILES:
                    self.assertTrue(
                        (directory / name).is_file(),
                        f"{target['slug']} missing {name}",
                    )
                self.assertTrue((directory / "evidence").is_dir())
                for name in MIRRORED_MANIFEST_FILES:
                    self.assertTrue((mirror / name).is_file())
                    self.assertEqual(
                        (mirror / name).read_bytes(),
                        (directory / name).read_bytes(),
                    )

    def test_no_target_or_completeness_level_external_body(self) -> None:
        for target in self.targets:
            directory = build_specification.ROOT / target["target_dir"]
            implementation = (directory / "implementation_proof.rs").read_text(
                encoding="utf-8"
            )
            completeness = (directory / "completeness_proof.rs").read_text(
                encoding="utf-8"
            )
            trust = proofs.load(directory / "trust_boundaries.json")
            with self.subTest(row_id=target["row_id"]):
                target_match = TARGET_SIGNATURE.search(implementation)
                self.assertIsNotNone(
                    target_match,
                    f"{target['slug']} has no executable implementation_target",
                )
                self.assertNotIn("external", target_match.group(1))

                theorem = COMPLETENESS_SIGNATURE.search(completeness)
                self.assertIsNotNone(
                    theorem,
                    f"{target['slug']} has no completeness_theorem",
                )
                self.assertNotIn("external", theorem.group(1))
                self.assertNotRegex(
                    completeness[theorem.end():],
                    r"\bassume\s*\(",
                )

                self.assertIs(trust["target_external_body"], False)
                self.assertIs(trust["completeness_external_body"], False)

    def test_contract_provenance_matches_accepted_disposition(self) -> None:
        by_id = {row["row_id"]: row for row in self.rows}
        for target in self.targets:
            row = by_id[target["row_id"]]
            accepted = self.catalog_by_id[target["row_id"]]
            directory = build_specification.ROOT / target["target_dir"]
            manifest = proofs.load(directory / "proof_manifest.json")
            equivalence = proofs.load(directory / "contract_equivalence.json")
            with self.subTest(row_id=target["row_id"]):
                self.assertEqual(
                    manifest["contract_provenance"],
                    "generated"
                    if accepted["disposition"] == "generated"
                    else "exact_vstd_reference",
                )
                self.assertEqual(
                    equivalence["accepted_contract_sha256"],
                    proofs.sha256(directory / "accepted_contract.rs"),
                )

    def test_pre_evidence_structural_gate_passes(self) -> None:
        protected = {
            path: path.read_bytes()
            for path in (
                check_implementation_proofs.AGGREGATE_JSON,
                check_implementation_proofs.AGGREGATE_MD,
                check_implementation_proofs.REVIEW_REQUEST,
            )
        }
        errors = check_implementation_proofs.validate(
            require_results=False,
            require_mutations=False,
            require_review=False,
            write_artifacts=False,
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            {path: path.read_bytes() for path in protected},
            protected,
        )


if __name__ == "__main__":
    unittest.main()
