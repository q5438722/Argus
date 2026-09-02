from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import build_specification
from tools import check_aggregate
from tools import check_implementation_proofs
from tools import check_specification
from tools import run_implementation_proofs
from tools import run_mutation_probes


class ProofToolingTests(unittest.TestCase):
    def test_run_ids_and_descendants_fail_closed(self) -> None:
        self.assertTrue(run_implementation_proofs.valid_run_id("cmp-final_01"))
        self.assertFalse(run_implementation_proofs.valid_run_id("../escape"))
        self.assertFalse(run_implementation_proofs.valid_run_id(""))
        with self.assertRaises(ValueError):
            run_implementation_proofs.checked_descendant(
                Path("/tmp"),
                build_specification.ROOT,
                "test path",
            )

    def test_external_body_scan_covers_private_and_spec_helpers(self) -> None:
        text = """
#[verifier::external_body]
fn private_dependency() {}

#[verifier::external_body]
pub(crate) open spec fn model_dependency() -> bool { true }

#[verifier::external_body]
pub proof fn proof_dependency() {}

#[verifier :: external_body]
fn spaced_dependency() {}
"""
        self.assertEqual(
            check_implementation_proofs.external_functions(text),
            [
                "private_dependency",
                "model_dependency",
                "proof_dependency",
                "spaced_dependency",
            ],
        )
        self.assertEqual(
            check_implementation_proofs.external_body_count(text),
            4,
        )

    def test_completeness_declaration_is_scoped_to_the_theorem(self) -> None:
        text = """
pub proof fn decoy()
    requires accepted_contract(x, result1),
    ensures result1 == result2,
{}

pub proof fn completeness_theorem(result1: int, result2: int)
    requires
        accepted_contract(x, result1),
        accepted_contract(x, result2),
    ensures
        result1 == result2,
{}
"""
        declaration = check_implementation_proofs.function_declaration(
            text,
            "completeness_theorem",
        )
        self.assertIsNotNone(declaration)
        assert declaration is not None
        self.assertEqual(declaration.count("accepted_contract("), 2)
        self.assertIn("result1 == result2", declaration)

    def test_mutation_plan_schema_aliases_are_explicit(self) -> None:
        direct = {"implementation_mutation": {"fragment": "a"}}
        nested = {"mutations": {"completeness": {"fragment": "b"}}}
        plural = {
            "implementation_mutations": [
                {"id": "first", "fragment": "c"},
                {"id": "second", "fragment": "d"},
            ]
        }
        self.assertEqual(
            run_mutation_probes.mutation_plan(direct, "implementation"),
            {"fragment": "a"},
        )
        self.assertEqual(
            run_mutation_probes.mutation_plan(nested, "completeness"),
            {"fragment": "b"},
        )
        self.assertEqual(
            run_mutation_probes.mutation_plans(
                plural, "implementation"
            ),
            plural["implementation_mutations"],
        )
        self.assertEqual(
            run_mutation_probes.mutation_plan(
                plural, "implementation"
            ),
            plural["implementation_mutations"][0],
        )
        self.assertEqual(
            [
                run_mutation_probes.mutation_id(plan, index, 2)
                for index, plan in enumerate(
                    plural["implementation_mutations"]
                )
            ],
            ["first", "second"],
        )
        self.assertEqual(
            run_mutation_probes.mutation_id(
                {"fragment": "single"}, 0, 1
            ),
            "default",
        )

    def test_implementation_review_schema_mutations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / "request.json"
            review = root / "review.json"
            handoff = root / "handoff.json"
            questions = ["Does the proof review pass?"]
            request.write_text(
                json.dumps(
                    {
                        "artifacts": [],
                        "review_questions": questions,
                    }
                ),
                encoding="utf-8",
            )
            inventory_rows = check_implementation_proofs.load(
                build_specification.INVENTORY
            )["rows"]
            row_count = len(
                build_specification.selected_specification_rows(
                    inventory_rows
                )
            )
            impossible_count = len(inventory_rows) - row_count
            valid: dict[str, object] = {
                "schema_version": 1,
                "module": "core::cmp",
                "review_type": "implementation_and_completeness",
                "producer_role": "reviewer",
                "independence": {
                    "independent": True,
                    "artifacts_modified_by_reviewer": [],
                },
                "review_request": {
                    "path": request.name,
                    "sha256": check_implementation_proofs.sha256(request),
                },
                "artifact_bindings": [],
                "canonical_handoff": {
                    "path": handoff.name,
                    "sha256": "",
                },
                "review": {
                    "status": "done",
                    "implementation_completeness_accepted": True,
                    "unresolved_findings": [],
                    "accepted_target_count": row_count,
                    "approved_genuinely_impossible_count": (
                        impossible_count
                    ),
                    "question_verdicts": [
                        {
                            "question": questions[0],
                            "verdict": "satisfied",
                        }
                    ],
                },
            }
            handoff.write_text(
                json.dumps(
                    {
                        "producer_role": "reviewer",
                        "review_request": {
                            "path": request.name,
                            "sha256": check_implementation_proofs.sha256(
                                request
                            ),
                        },
                        "artifact_bindings": [],
                        "mission": {
                            "path": str(
                                check_specification.MISSION_PATH
                            ),
                            "sha256": check_implementation_proofs.sha256(
                                check_specification.MISSION_PATH
                            ),
                        },
                        "review": {
                            "status": "done",
                            "next_action": "",
                            "implementation_completeness_accepted": True,
                            "approved_genuinely_impossible_count": (
                                impossible_count
                            ),
                            "unresolved_findings": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            canonical = valid["canonical_handoff"]
            assert isinstance(canonical, dict)
            canonical["sha256"] = check_implementation_proofs.sha256(
                handoff
            )
            patches = (
                mock.patch.object(
                    check_implementation_proofs,
                    "ROOT",
                    root,
                ),
                mock.patch.object(
                    check_implementation_proofs,
                    "REVIEW_REQUEST",
                    request,
                ),
                mock.patch.object(
                    check_implementation_proofs,
                    "REVIEW",
                    review,
                ),
                mock.patch.object(
                    check_implementation_proofs,
                    "CANONICAL_REVIEW_HANDOFF",
                    handoff,
                ),
            )
            with patches[0], patches[1], patches[2], patches[3]:
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertEqual(
                    check_implementation_proofs.review_errors(),
                    [],
                )
                valid["producer_role"] = "independent_reviewer"
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertIn(
                    "implementation_reviewer_role_invalid",
                    {
                        error["code"]
                        for error in check_implementation_proofs.review_errors()
                    },
                )

                valid["producer_role"] = "reviewer"
                decision = valid["review"]
                assert isinstance(decision, dict)
                decision["status"] = "accepted"
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertIn(
                    "implementation_review_status_not_done",
                    {
                        error["code"]
                        for error in check_implementation_proofs.review_errors()
                    },
                )
                decision["status"] = "done"
                decision["implementation_completeness_accepted"] = False
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertIn(
                    "implementation_completeness_not_accepted",
                    {
                        error["code"]
                        for error in check_implementation_proofs.review_errors()
                    },
                )
                decision["implementation_completeness_accepted"] = True
                decision["approved_genuinely_impossible_count"] = 0
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertIn(
                    "implementation_review_impossible_count_mismatch",
                    {
                        error["code"]
                        for error in check_implementation_proofs.review_errors()
                    },
                )
                decision["approved_genuinely_impossible_count"] = (
                    impossible_count
                )
                bindings = valid["artifact_bindings"]
                assert isinstance(bindings, list)
                bindings.append("ignored malformed binding")
                review.write_text(json.dumps(valid), encoding="utf-8")
                self.assertIn(
                    "implementation_review_artifact_bindings_schema_invalid",
                    {
                        error["code"]
                        for error in check_implementation_proofs.review_errors()
                    },
                )

    def test_final_review_status_literal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / "final-request.json"
            review = root / "final-review.json"
            handoff = root / "final-handoff.json"
            inventory_rows = check_implementation_proofs.load(
                build_specification.INVENTORY
            )["rows"]
            selected = len(
                build_specification.selected_specification_rows(
                    inventory_rows
                )
            )
            impossible_count = len(inventory_rows) - selected
            request.write_text(
                json.dumps(
                    {
                        "artifacts": [],
                        "counts": {
                            "selected": selected,
                            "genuinely_impossible": impossible_count,
                        },
                        "review_questions": [],
                    }
                ),
                encoding="utf-8",
            )
            handoff.write_text(
                json.dumps(
                    {
                        "producer_role": "reviewer",
                        "review_request": {
                            "path": request.name,
                            "sha256": check_aggregate.sha256(request),
                        },
                        "artifact_bindings": [],
                        "mission": {
                            "path": str(check_specification.MISSION_PATH),
                            "sha256": check_aggregate.sha256(
                                check_specification.MISSION_PATH
                            ),
                        },
                        "review": {
                            "status": "done",
                            "next_action": "",
                            "final_aggregate_accepted": True,
                            "approved_genuinely_impossible_count": (
                                impossible_count
                            ),
                            "unresolved_findings": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            payload = {
                "schema_version": 1,
                "module": "core::cmp",
                "review_type": "final_aggregate",
                "producer_role": "reviewer",
                "independence": {
                    "independent": True,
                    "artifacts_modified_by_reviewer": [],
                },
                "review_request": {
                    "path": request.name,
                    "sha256": check_aggregate.sha256(request),
                },
                "artifact_bindings": [],
                "canonical_handoff": {
                    "path": handoff.name,
                    "sha256": check_aggregate.sha256(handoff),
                },
                "review": {
                    "status": "accepted",
                    "unresolved_findings": [],
                    "final_aggregate_accepted": True,
                    "accepted_target_count": selected,
                    "actual_verus_verified": selected,
                    "pending": 0,
                    "failed": 0,
                    "approved_genuinely_impossible_count": (
                        impossible_count
                    ),
                    "question_verdicts": [],
                },
            }
            review.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(
                check_aggregate,
                "ROOT",
                root,
            ), mock.patch.object(
                check_aggregate,
                "FINAL_REQUEST",
                request,
            ), mock.patch.object(
                check_aggregate,
                "FINAL_REVIEW",
                review,
            ), mock.patch.object(
                check_aggregate,
                "FINAL_REVIEW_HANDOFF",
                handoff,
            ):
                self.assertIn(
                    "final_review_status_not_done",
                    {
                        error["code"]
                        for error in check_aggregate.final_review_errors()
                    },
                )
                decision = payload["review"]
                assert isinstance(decision, dict)
                decision["status"] = "done"
                bindings = payload["artifact_bindings"]
                assert isinstance(bindings, list)
                bindings.append("ignored malformed binding")
                review.write_text(json.dumps(payload), encoding="utf-8")
                self.assertIn(
                    "final_review_artifact_bindings_schema_invalid",
                    {
                        error["code"]
                        for error in check_aggregate.final_review_errors()
                    },
                )

    def test_failed_aggregate_invalidates_stale_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            delivery = Path(temporary) / "final_delivery.json"
            delivery.write_text('{"status":"accepted"}\n', encoding="utf-8")
            with mock.patch.object(
                check_aggregate,
                "FINAL_DELIVERY",
                delivery,
            ), mock.patch.object(
                check_aggregate,
                "layout_errors",
                return_value=[{"code": "forced_layout_failure"}],
            ), mock.patch.object(
                check_aggregate.proofs,
                "validate",
                return_value=[],
            ), mock.patch.object(
                check_aggregate.proofs,
                "atomic_json",
            ), mock.patch.object(
                check_aggregate.provenance,
                "check_provenance",
            ), mock.patch.object(
                check_aggregate.build_inventory,
                "check",
            ):
                errors = check_aggregate.validate(
                    require_final_review=False
                )
            self.assertFalse(delivery.exists())
            self.assertIn(
                "forced_layout_failure",
                {error["code"] for error in errors},
            )


if __name__ == "__main__":
    unittest.main()
