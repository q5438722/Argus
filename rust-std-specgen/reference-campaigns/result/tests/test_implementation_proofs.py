"""Fail-closed tests for the core::result implementation-conformance gate.

These tests re-derive everything they assert from the artifacts on disk and
include negative cases: tampering with a proof, a manifest hash, a mutation
anchor, or the accepted-contract copy must make the checker fail.
"""

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import implementation  # noqa: E402

HARNESS_ROOT = ROOT / "proof_harnesses"
MANIFEST_ROOT = ROOT / "proof_manifests"
UNRELATED_AUTHORIZATION_ERROR = "unrelated authorization failure"


def load(path: Path):
    return json.loads(path.read_text())


def structural_errors_with_unhealthy_authorization():
    with mock.patch.object(
        implementation,
        "verify_accepted_inputs",
        side_effect=ValueError(UNRELATED_AUTHORIZATION_ERROR),
    ):
        return implementation.structural_errors(require_evidence=False)


class GeneratedPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "proof_inventory/targets.json").is_file():
            implementation.generate()
        cls.inventory = load(ROOT / "proof_inventory/targets.json")
        cls.rows = {int(r["rustdoc_item_id"]): r for r in implementation.accepted_rows()}
        cls.manifests = {
            path.parent.name: load(path) for path in HARNESS_ROOT.glob("*/manifest.json")
        }

    # -- inventory facts ------------------------------------------------
    def test_exact_authorized_inventory_counts(self):
        rows = implementation.accepted_rows()
        self.assertEqual(64, len(rows))
        self.assertEqual(10, sum(r["disposition"] == "exact_vstd" for r in rows))
        self.assertEqual(54, sum(r["disposition"] == "generated" for r in rows))
        self.assertEqual(64, len(self.inventory["targets"]))
        self.assertEqual(
            9,
            sum(
                manifest["source"]["kind"] == "rustc_derive_expansion"
                for manifest in self.manifests.values()
            ),
        )

    def test_proof_manifest_directories_mirror_harnesses(self):
        harness = sorted(p.name for p in HARNESS_ROOT.iterdir() if p.is_dir())
        manifests = sorted(p.name for p in MANIFEST_ROOT.iterdir() if p.is_dir())
        self.assertEqual(64, len(manifests))
        self.assertEqual(harness, manifests)
        for name in manifests:
            for required in implementation.REQUIRED_PROOF_MANIFEST_FILES:
                self.assertTrue((MANIFEST_ROOT / name / required).is_file(), f"{name}/{required}")

    def test_proof_manifest_hash_closure_is_exact(self):
        for directory in MANIFEST_ROOT.iterdir():
            manifest = load(directory / "proof_manifest.json")
            self.assertGreaterEqual(len(manifest["files"]), 15)
            for relative, digest in manifest["files"].items():
                path = ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertEqual(digest, implementation.sha256_file(path), relative)

    # -- architecture ---------------------------------------------------
    def test_no_generic_postcondition_restatement_architecture(self):
        for directory in HARNESS_ROOT.iterdir():
            text = (directory / "implementation_proof.rs").read_text()
            completeness = (directory / "completeness_proof.rs").read_text()
            for marker in implementation.FORBIDDEN_GENERIC_MARKERS:
                self.assertNotIn(marker, text, f"{directory.name}: {marker}")
                self.assertNotIn(marker, completeness, f"{directory.name}: {marker}")

    def test_targets_are_public_non_external_and_family_specific(self):
        bodies = {}
        for directory in HARNESS_ROOT.iterdir():
            text = (directory / "implementation_proof.rs").read_text()
            self.assertRegex(text, r"pub (?:unsafe )?fn implementation_target")
            self.assertNotRegex(
                text,
                r"#\[verifier::external_body\]\s*(?:#\[[^\]]*\]\s*)*pub (?:unsafe )?fn implementation_target",
            )
            self.assertNotIn("assume(", text)
            body = text.split("pub fn implementation_target", 1)[-1]
            bodies[directory.name] = body
        # the 64 targets must not collapse into one shared body
        self.assertGreater(len(set(bodies.values())), 40)

    def test_distinct_templates_and_families(self):
        templates = {t["proof_template_id"] for t in self.inventory["targets"]}
        families = {t["semantic_family"] for t in self.inventory["targets"]}
        self.assertGreaterEqual(len(templates), 40)
        self.assertGreaterEqual(len(families), 20)

    def test_required_family_markers_present(self):
        expectations = {
            26760: ["source_try_process", "ResultShortCircuitOperation::Sum"],
            26882: ["ResultShortCircuitOperation::Product"],
            26942: [
                "ResultShortCircuitOperation::FromIterator",
                "FromIteratorSpec::from_iter_ensures",
                "pub trait SourceIntoResultIterator",
                "type IntoIter: Iterator<Item = Result<A, E>>;",
                "iter.source_into_result_iter()",
            ],
            29279: ["source_invoke_fn_once", "f.ensures((input->Ok_0,), result)"],
            29285: ["result_mut_ref_identity", "source_ok_payload_mut"],
            29295: ["source_iter_from_inner", "result_iter_values"],
            27283: ["source_iter_inner_take", "drop_first"],
            27284: ["(n, Some(n))"],
            10005: ["source_clone_from", "source_clone"],
            11356: ["Ordering::Less", "Ordering::Greater"],
            29329: ["ResultFormatLiteral::OkName", "ResultFormatLiteral::ErrName"],
            29331: ["source_hash_discriminant(0u8, state);"],
            29300: ["source_unwrap_failed"],
            29308: ["pub unsafe fn implementation_target", "source_unreachable_unchecked"],
            29309: ["pub unsafe fn implementation_target"],
            29317: ["Ok(Some(value)) => Some(Ok(value)),"],
            29319: ["Ok(inner) => inner,"],
        }
        by_id = {
            int(manifest["rustdoc_item_id"]): directory
            for directory, manifest in self.manifests.items()
        }
        for item_id, markers in expectations.items():
            text = (HARNESS_ROOT / by_id[item_id] / "implementation_proof.rs").read_text()
            for marker in markers:
                self.assertIn(marker, text, f"rustdoc-{item_id}: {marker}")

    def test_completeness_links_and_compares(self):
        for directory in HARNESS_ROOT.iterdir():
            text = (directory / "completeness_proof.rs").read_text()
            self.assertIn("pub open spec fn accepted_contract", text)
            self.assertIn("pub fn implementation_contract_link", text)
            self.assertIn("pub proof fn completeness_theorem", text)
            self.assertIn("pub open spec fn outcomes_equivalent", text)
            self.assertRegex(text, r"implementation_target(::<[^>]*>)?\s*\(")
            accepted = text.split("pub open spec fn accepted_contract", 1)[-1].split("}\n", 1)[0]
            self.assertNotIn("implementation_target", accepted)

    def test_iter_mut_completeness_compares_final_identity_sequences(self):
        by_id = {
            int(manifest["rustdoc_item_id"]): directory
            for directory, manifest in self.manifests.items()
        }
        identity_equality = (
            "    &&& left_identities_after == right_identities_after"
        )
        identity_transition = (
            "    &&& identities_after == if identities_before.len() > 0 "
            "{ identities_before.drop_first() } else { identities_before }"
        )
        outcome_call = (
            "outcomes_equivalent(left, left_values_after, "
            "left_identities_after, right, right_values_after, "
            "right_identities_after)"
        )
        for item_id in (27287, 27049):
            directory = HARNESS_ROOT / by_id[item_id]
            completeness = (directory / "completeness_proof.rs").read_text()
            mutant = (
                directory / "mutations/completeness_mutant.rs"
            ).read_text()
            manifest = load(directory / "manifest.json")

            self.assertIn(identity_equality, completeness)
            self.assertIn(identity_transition, completeness)
            self.assertIn(outcome_call, completeness)
            self.assertIn(
                "assert(left_identities_after =~= right_identities_after);",
                completeness,
            )
            self.assertIn(identity_equality, mutant)
            self.assertNotIn(identity_transition, mutant)
            self.assertEqual(
                "omitted_final_mutable_identity_transition_equality",
                manifest["mutation_plan"]["completeness"]["kind"],
            )
            self.assertEqual(
                (
                    "identities_after == if identities_before.len() > 0 "
                    "{ identities_before.drop_first() } else "
                    "{ identities_before }"
                ),
                manifest["mutation_plan"]["completeness"]["observable"],
            )

    def test_exact_vstd_rows_reference_only(self):
        exact = [m for m in self.manifests.values() if m["disposition"] == "exact_vstd"]
        self.assertEqual(10, len(exact))
        for manifest in exact:
            self.assertEqual("reference_only", manifest["contract"]["mode"])
            text = (HARNESS_ROOT / manifest["directory"] / "implementation_proof.rs").read_text()
            self.assertNotIn("assume_specification", text)
            transformation = load(
                HARNESS_ROOT / manifest["directory"] / "transformation_manifest.json"
            )
            self.assertTrue(transformation["exact_vstd_references"])

    # -- provenance -----------------------------------------------------
    def test_accepted_contract_and_equivalence_hashes(self):
        for directory, manifest in self.manifests.items():
            row = self.rows[int(manifest["rustdoc_item_id"])]
            self.assertEqual(
                implementation.accepted_contract_sha(row),
                manifest["contract"]["accepted_segment_sha256"],
            )
            local = HARNESS_ROOT / directory / "accepted_contract.rs"
            self.assertEqual(
                implementation.sha256_file(local), manifest["contract"]["local_sha256"]
            )
            equivalence = load(HARNESS_ROOT / directory / "contract_equivalence.json")
            self.assertEqual(
                row["outcome_equivalence"]["record_sha256"],
                equivalence["accepted_outcome_equivalence"]["record_sha256"],
            )
            self.assertGreaterEqual(
                len(equivalence["proof_binding"]["clause_bindings"]),
                len(row["contract"].get("direct_ensures") or []),
            )

    def test_derive_bindings_are_exact(self):
        derived = [
            m for m in self.manifests.values() if m["source"]["kind"] == "rustc_derive_expansion"
        ]
        self.assertEqual(9, len(derived))
        for manifest in derived:
            capture = manifest["source"]["derive_capture"]
            self.assertEqual(
                capture["expanded_method"]["sha256"], manifest["source"]["excerpt_sha256"]
            )

    def test_dependency_freeze_is_per_target_and_exact(self):
        manifest = load(ROOT / "frozen_inputs/source_dependency_manifest.json")
        self.assertGreaterEqual(len(manifest["records"]), 15)
        for record in manifest["records"]:
            self.assertEqual(record["sha256"], record["snapshot_sha256"])
            self.assertIn("definition", record)
            self.assertTrue(record["definition"]["anchor_text"].strip())
        for directory in HARNESS_ROOT.iterdir():
            dependency_manifest = load(
                directory / "dependency_assumptions.json"
            )
            dependencies = dependency_manifest["dependencies"]
            self.assertTrue(dependencies)
            dependency_by_name = {
                dependency["name"]: dependency
                for dependency in dependencies
            }
            for helper in dependency_manifest["local_boundary_helpers"]:
                dependency = dependency_by_name[helper["dependency"]]
                self.assertIn(helper["symbol"], dependency["proof_symbols"])
                self.assertEqual(
                    helper["source_sha256"], dependency["sha256"]
                )
            excerpt = (directory / "source_excerpt.rs").read_text()
            row = self.rows[int(load(directory / "manifest.json")["rustdoc_item_id"])]
            for dependency in dependencies:
                call_site = dependency["target_call_site"]
                self.assertIn(
                    call_site["located_in"],
                    {"source_excerpt", "accepted_signature", "accepted_target_path"},
                )
                haystack = {
                    "source_excerpt": excerpt,
                    "accepted_signature": row["signature"],
                    "accepted_target_path": row["target"],
                }[call_site["located_in"]]
                self.assertIn(call_site["spelling"], haystack, dependency["name"])
                snapshot = ROOT / dependency["snapshot_path"]
                self.assertTrue(snapshot.is_file())
                lines = snapshot.read_text().splitlines()
                anchor = dependency["definition"]
                self.assertEqual(lines[anchor["anchor_line"] - 1], anchor["anchor_text"])

    def test_local_trust_helper_inventory_is_exact(self):
        external = 0
        uninterpreted = 0
        bridges = 0
        for directory in HARNESS_ROOT.iterdir():
            dependency = load(directory / "dependency_assumptions.json")
            trust = load(directory / "trust_boundaries.json")
            self.assertEqual(
                dependency["local_boundary_helpers"],
                trust["local_boundary_helpers"],
            )
            external += len(trust["external_body_helpers"])
            uninterpreted += len(trust["uninterpreted_spec_helpers"])
            bridges += len(trust["associated_type_bridges"])
        self.assertEqual(86, external)
        self.assertEqual(31, uninterpreted)
        self.assertEqual(1, bridges)

    def test_from_iter_uses_type_bridge_not_unconstrained_predicate(self):
        directory = next(
            directory
            for directory, manifest in self.manifests.items()
            if int(manifest["rustdoc_item_id"]) == 26942
        )
        text = (HARNESS_ROOT / directory / "implementation_proof.rs").read_text()
        self.assertNotIn("source_into_iterator_item_is_result", text)
        self.assertIn(
            "type IntoIter: Iterator<Item = Result<A, E>>;",
            text,
        )
        dependency = load(
            HARNESS_ROOT / directory / "dependency_assumptions.json"
        )
        bridge = [
            helper
            for helper in dependency["local_boundary_helpers"]
            if helper["declaration_kind"] == "associated_type_bridge"
        ]
        self.assertEqual(["SourceIntoResultIterator"], [row["symbol"] for row in bridge])

    # -- mutation plans -------------------------------------------------
    def test_mutation_plans_are_family_specific_and_anchored(self):
        implementation_kinds = set()
        completeness_kinds = set()
        for directory, manifest in self.manifests.items():
            plan = manifest["mutation_plan"]
            implementation_kinds.add(plan["implementation"]["kind"])
            completeness_kinds.add(plan["completeness"]["kind"])
            baseline = (HARNESS_ROOT / directory / "implementation_proof.rs").read_text()
            completeness = (HARNESS_ROOT / directory / "completeness_proof.rs").read_text()
            self.assertIn(plan["implementation"]["anchor"], baseline, directory)
            self.assertIn(plan["completeness"]["anchor"], completeness, directory)
            mutant = (
                HARNESS_ROOT / directory / "mutations/implementation_mutant.rs"
            ).read_text()
            completeness_mutant = (
                HARNESS_ROOT / directory / "mutations/completeness_mutant.rs"
            ).read_text()
            self.assertNotEqual(baseline, mutant)
            self.assertNotEqual(completeness, completeness_mutant)
            self.assertIn('#[path = "../implementation_proof.rs"]', completeness_mutant)
        self.assertGreaterEqual(len(implementation_kinds), 12)
        self.assertGreaterEqual(len(completeness_kinds), 12)
        self.assertNotEqual({"omitted_exact_outcome_equality_observable"}, completeness_kinds)

    # -- fail-closed behaviour -----------------------------------------
    def test_checker_accepts_complete_evidence(self):
        self.assertEqual([], implementation.structural_errors(require_evidence=False))
        self.assertEqual([], implementation.structural_errors(require_evidence=True))

    def test_checker_rejects_tampered_proof(self):
        directory = sorted(HARNESS_ROOT.iterdir())[0]
        path = directory / "implementation_proof.rs"
        backup = path.read_text()
        try:
            path.write_text(backup + "\n// tampered\n")
            errors = structural_errors_with_unhealthy_authorization()
            self.assertIn(UNRELATED_AUTHORIZATION_ERROR, errors)
            self.assertTrue(any("stale file hash" in error for error in errors))
        finally:
            path.write_text(backup)

    def test_checker_rejects_generic_restatement_architecture(self):
        directory = sorted(HARNESS_ROOT.iterdir())[3]
        path = directory / "implementation_proof.rs"
        backup = path.read_text()
        try:
            path.write_text(
                backup.replace(
                    "verus! {",
                    "verus! {\n\npub open spec fn accepted_lowering(x: int) -> int { x }\n",
                    1,
                )
            )
            errors = structural_errors_with_unhealthy_authorization()
            self.assertIn(UNRELATED_AUTHORIZATION_ERROR, errors)
            self.assertTrue(
                any("generic postcondition-restatement" in error for error in errors)
            )
        finally:
            path.write_text(backup)

    def test_checker_rejects_missing_proof_manifest(self):
        directory = sorted(MANIFEST_ROOT.iterdir())[5]
        path = directory / "proof_manifest.json"
        backup = path.read_text()
        try:
            path.unlink()
            errors = structural_errors_with_unhealthy_authorization()
            self.assertIn(UNRELATED_AUTHORIZATION_ERROR, errors)
            self.assertTrue(any("missing" in error for error in errors))
        finally:
            path.write_text(backup)

    def test_checker_rejects_accepted_contract_tampering(self):
        directory = sorted(HARNESS_ROOT.iterdir())[9]
        path = directory / "accepted_contract.rs"
        backup = path.read_text()
        try:
            path.write_text(backup.replace("ensures", "ensures // tampered", 1))
            errors = structural_errors_with_unhealthy_authorization()
            self.assertIn(UNRELATED_AUTHORIZATION_ERROR, errors)
            self.assertTrue(
                any(
                    "accepted contract copy hash drifted" in error
                    for error in errors
                )
            )
        finally:
            path.write_text(backup)

    def test_runner_requires_run_id_and_run_dir(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/run_implementation_proofs.py"), "--all"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("--run-id", completed.stderr)

    def test_full_checker_reports_complete_evidence_accounting(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/check_implementation_proofs.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = load(ROOT / "verification/implementation_proof_check.json")
        self.assertEqual("pass", report["status"])
        self.assertEqual(128, report["evidence_accounting"]["mutation_rejections_required"])
        self.assertEqual(512, report["evidence_accounting"]["commands_expected_for_full_batch"])
        self.assertEqual(512, report["evidence_accounting"]["commands_recorded"])
        self.assertEqual(0, report["trust_accounting"]["literal_target_external_bodies"])
        self.assertEqual(86, report["trust_accounting"]["literal_lower_level_external_bodies"])
        self.assertEqual([], report["trust_accounting"]["unbound_local_helpers"])
        self.assertEqual(64, report["trust_accounting"]["public_implementation_targets"])
        self.assertEqual(2, report["trust_accounting"]["unsafe_implementation_targets"])


if __name__ == "__main__":
    unittest.main()
