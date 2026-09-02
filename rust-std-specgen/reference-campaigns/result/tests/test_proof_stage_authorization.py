from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_proof_stage_authorization as authorization  # noqa: E402


class ProofStageAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(
            authorization.AUTHORIZATION_PATH.read_text(encoding="utf-8")
        )

    def test_current_authorization_preserves_accepted_package(self) -> None:
        report = authorization.audit_authorization()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["counts"], authorization.EXPECTED_COUNTS)
        self.assertEqual(report["checked_frozen_inputs"], 7)
        self.assertGreater(report["checked_specification_artifacts"], 0)

        manifest = json.loads(
            (
                ROOT / "specs" / "specification_package_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(manifest["proof_harnesses_authorized"])
        self.assertEqual(
            self.payload["transition"]["proof_harnesses_creation"],
            "authorized",
        )
        self.assertNotIn(
            "remediation_reviewer_handoff", self.payload["authority"]
        )
        self.assertNotIn(
            "remediation_reviewer_handoff",
            {row["role"] for row in self.payload["frozen_inputs"]},
        )

    def test_reviewer_handoff_hash_cannot_be_rebound(self) -> None:
        mutant = copy.deepcopy(self.payload)
        reviewer = next(
            row
            for row in mutant["frozen_inputs"]
            if row["role"] == "canonical_reviewer_handoff"
        )
        reviewer["sha256"] = "0" * 64
        report = authorization.audit_authorization(mutant)
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "frozen_input_expected_hash_mismatch", report["errors"]
        )
        self.assertIn(
            "frozen_input_content_hash_mismatch", report["errors"]
        )

    def test_frozen_specification_cannot_be_made_mutable(self) -> None:
        mutant = copy.deepcopy(self.payload)
        mutant["transition"][
            "accepted_specification_package_mutation"
        ] = "allowed"
        report = authorization.audit_authorization(mutant)
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "proof_transition_field_mismatch", report["errors"]
        )

    def test_required_harness_pair_cannot_be_weakened(self) -> None:
        mutant = copy.deepcopy(self.payload)
        mutant["transition"]["required_files_per_target"] = [
            "implementation_proof.rs"
        ]
        report = authorization.audit_authorization(mutant)
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "proof_transition_field_mismatch", report["errors"]
        )


if __name__ == "__main__":
    unittest.main()
