from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import aggregate_seal


COMPLETE_REASON = (
    "The 64 selected targets comprise 54 generated targets and 10 exact-vstd "
    "reference-only targets, including 9 derive rows, 60 proof templates, and "
    "40 semantic families. I inspected all 64 implementation proof files and "
    "64 completeness proof files. Evidence establishes 128 successful baseline "
    "--no-verify obligations, 128 successful baseline actual-Verus obligations, "
    "128 syntax-valid mutants, 128 actual-Verus mutation rejections, and 512 "
    "total commands, with zero target-level external bodies and zero assumes, "
    "zero failed work, and zero pending work. I independently inspected readable "
    "source and contract content, dependency definitions, source definitions, "
    "anchors, call sites, and representative proof bodies. The 512-command "
    "evidence is fresh execution evidence timestamped after repaired proof "
    "generation and attributed to its recorded run. The narrow dependency trust "
    "boundaries remain, tied to readable frozen source definitions, anchors, and "
    "call sites, with all 86 lower-level external-body helpers and all 31 "
    "uninterpreted representation helpers enumerated. The FromIterator item "
    "equality uses a type-level bridge; this makes no foundational end-to-end "
    "trust-freedom claim. The structural gate passes, "
    "the evidence gate passes, the trust gate passes, the verification-run "
    "gate is complete, the implementation review gate passes, and the aggregate "
    "gate passes with zero unresolved findings."
)


class AggregateSealTests(unittest.TestCase):
    def projection_fixture(
        self, root: Path
    ) -> tuple[Path, dict[str, object], Path, dict[str, object]]:
        candidate_path = (
            root
            / "proof_inventory"
            / "final_aggregate_certification_20260902T010203000000Z-aaaaaaaaaaaaaaaa.json"
        )
        candidate: dict[str, object] = {
            "schema_version": aggregate_seal.SCHEMA_VERSION,
            "status": "implementation_reviewed_pending_final_review",
            "technical_gate": "pass",
            "counts": aggregate_seal.EXPECTED_COUNTS,
            "implementation_review": {
                "review_status": "done",
                "acceptance_eligible": True,
            },
            "gate_bindings": {
                "proof_inventory": {
                    "path": "proof_inventory/targets.json",
                    "sha256": "a" * 64,
                },
            },
            "created_at_utc": "2026-09-02T01:02:03Z",
        }
        aggregate_seal.write_json_atomic(candidate_path, candidate)
        delivery_path = root / "proof_inventory/final_delivery.json"
        delivery: dict[str, object] = {
            "schema_version": aggregate_seal.SCHEMA_VERSION,
            "status": "accepted",
            "counts": aggregate_seal.EXPECTED_COUNTS,
            "implementation_review": {
                "review_status": "done",
                "acceptance_eligible": True,
            },
            "final_review": {
                "review_status": "done",
                "acceptance_eligible": True,
            },
            "certification": {
                "path": "proof_inventory/final_aggregate_certification.json",
                "sha256": "b" * 64,
            },
            "unresolved_findings": [],
            "created_at_utc": "2026-09-02T01:04:05Z",
        }
        aggregate_seal.write_json_atomic(delivery_path, delivery)
        return candidate_path, candidate, delivery_path, delivery

    def test_immutable_json_cannot_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "seal.json"
            aggregate_seal.write_json_exclusive(path, {"version": 1})

            with self.assertRaises(aggregate_seal.AggregateSealError):
                aggregate_seal.write_json_exclusive(path, {"version": 2})

            self.assertEqual(aggregate_seal.load_json(path), {"version": 1})

    def test_canonical_handoff_snapshot_survives_round_slot_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            handoff_root = root / "handoffs/mission"
            handoff_path = handoff_root / "round-0002.json"
            mission_path = handoff_root / "mission.json"
            checkpoint_path = handoff_root / "CHECKPOINT.md"
            accepted = {
                "schema_version": 2,
                "kind": "round_reviewed_handoff",
                "mission_id": "mission",
                "mission_context": str(mission_path),
                "checkpoint": {"path": str(checkpoint_path)},
                "producer_role": "reviewer",
                "round": 2,
                "created_at": 2.0,
                "review": {
                    "status": "done",
                    "reason": "accepted",
                    "next_action": "",
                    "operator_question": "",
                },
            }
            aggregate_seal.write_json_atomic(handoff_path, accepted)
            expected_hash = aggregate_seal.sha256_file(handoff_path)
            with mock.patch.multiple(
                aggregate_seal,
                HANDOFF_ROOT=handoff_root,
                MISSION_PATH=mission_path,
                CHECKPOINT_PATH=checkpoint_path,
                MISSION_ID="mission",
                CANONICAL_HANDOFF_SNAPSHOT_ROOT=(
                    root / "proof_inventory/canonical_handoffs"
                ),
            ):
                snapshot = aggregate_seal.archive_canonical_handoff(
                    handoff_path,
                    expected_hash,
                )
                aggregate_seal.write_json_atomic(
                    handoff_path,
                    {
                        **accepted,
                        "review": {
                            **accepted["review"],
                            "status": "continue",
                        },
                    },
                )
                binding = aggregate_seal.canonical_review_binding(
                    {
                        "path": str(handoff_path),
                        "round": 2,
                        "sha256": expected_hash,
                    },
                    required_terms=(),
                    request_created_at=1.0,
                    label="test review",
                )

            self.assertEqual(binding["sha256"], expected_hash)
            self.assertEqual(
                aggregate_seal.sha256_file(snapshot),
                expected_hash,
            )

    def test_verification_projections_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            candidate_path, candidate, delivery_path, delivery = (
                self.projection_fixture(root)
            )
            with mock.patch.object(aggregate_seal, "CAMPAIGN_ROOT", root):
                pre_final = (
                    aggregate_seal.build_pre_final_verification_projection(
                        candidate_path,
                        candidate,
                    )
                )
                aggregate = (
                    aggregate_seal.build_aggregate_seal_verification_projection(
                        delivery_path,
                        delivery,
                    )
                )
                self.assertEqual(
                    pre_final,
                    aggregate_seal.build_pre_final_verification_projection(
                        candidate_path,
                        candidate,
                    ),
                )
                self.assertEqual(
                    aggregate,
                    aggregate_seal.build_aggregate_seal_verification_projection(
                        delivery_path,
                        delivery,
                    ),
                )

            self.assertEqual(
                pre_final["created_at_utc"],
                candidate["created_at_utc"],
            )
            self.assertEqual(
                aggregate["created_at_utc"],
                delivery["created_at_utc"],
            )

    def test_blocked_verification_projections_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            candidate_path, candidate, delivery_path, delivery = (
                self.projection_fixture(root)
            )
            pre_final_path = root / "verification/pre_final_certification.json"
            aggregate_path = root / "verification/aggregate_seal.json"
            with mock.patch.multiple(
                aggregate_seal,
                CAMPAIGN_ROOT=root,
                PRE_FINAL_VERIFICATION=pre_final_path,
                AGGREGATE_SEAL_VERIFICATION=aggregate_path,
            ):
                pre_final = (
                    aggregate_seal.build_pre_final_verification_projection(
                        candidate_path,
                        candidate,
                    )
                )
                aggregate = (
                    aggregate_seal.build_aggregate_seal_verification_projection(
                        delivery_path,
                        delivery,
                    )
                )
                for path, projection, blocked_status, validator in (
                    (
                        pre_final_path,
                        pre_final,
                        "blocked_pending_independent_review",
                        lambda: aggregate_seal.validate_pre_final_verification_projection(
                            candidate_path,
                            candidate,
                        ),
                    ),
                    (
                        aggregate_path,
                        aggregate,
                        "blocked_incomplete_evidence",
                        lambda: aggregate_seal.validate_aggregate_seal_verification_projection(
                            delivery_path,
                            delivery,
                        ),
                    ),
                ):
                    with self.subTest(path=path.name):
                        blocked = {**projection, "status": blocked_status}
                        aggregate_seal.write_json_atomic(path, blocked)
                        with self.assertRaisesRegex(
                            aggregate_seal.AggregateSealError,
                            "verification projection.*mismatch",
                        ):
                            validator()

    def test_stale_verification_projection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            candidate_path, candidate, delivery_path, delivery = (
                self.projection_fixture(root)
            )
            pre_final_path = root / "verification/pre_final_certification.json"
            aggregate_path = root / "verification/aggregate_seal.json"
            with mock.patch.multiple(
                aggregate_seal,
                CAMPAIGN_ROOT=root,
                PRE_FINAL_VERIFICATION=pre_final_path,
                AGGREGATE_SEAL_VERIFICATION=aggregate_path,
            ):
                pre_final = (
                    aggregate_seal.build_pre_final_verification_projection(
                        candidate_path,
                        candidate,
                    )
                )
                aggregate = (
                    aggregate_seal.build_aggregate_seal_verification_projection(
                        delivery_path,
                        delivery,
                    )
                )
                pre_final["canonical_candidate"]["sha256"] = "0" * 64
                aggregate["final_delivery"]["sha256"] = "0" * 64
                for path, projection, validator in (
                    (
                        pre_final_path,
                        pre_final,
                        lambda: aggregate_seal.validate_pre_final_verification_projection(
                            candidate_path,
                            candidate,
                        ),
                    ),
                    (
                        aggregate_path,
                        aggregate,
                        lambda: aggregate_seal.validate_aggregate_seal_verification_projection(
                            delivery_path,
                            delivery,
                        ),
                    ),
                ):
                    with self.subTest(path=path.name):
                        aggregate_seal.write_json_atomic(path, projection)
                        with self.assertRaisesRegex(
                            aggregate_seal.AggregateSealError,
                            "verification projection.*mismatch",
                        ):
                            validator()

    def test_reason_coverage_is_fail_closed(self) -> None:
        incomplete = aggregate_seal.reason_coverage(
            "64 selected targets and 512 commands pass.",
            aggregate_seal.IMPLEMENTATION_REASON_TERMS,
        )
        complete = aggregate_seal.reason_coverage(
            COMPLETE_REASON,
            aggregate_seal.IMPLEMENTATION_REASON_TERMS,
        )

        self.assertFalse(all(incomplete.values()))
        self.assertFalse(incomplete["128 actual-Verus mutation rejections"])
        self.assertFalse(incomplete["representative proof bodies"])
        self.assertFalse(incomplete["no foundational trust-freedom claim"])
        self.assertTrue(all(complete.values()), complete)

    def test_narrow_boundary_coverage_accepts_canonical_word_order(self) -> None:
        coverage = aggregate_seal.reason_coverage(
            "The retained dependency boundaries are narrow and tied to readable "
            "frozen source definitions, definition anchors, and target call sites.",
            aggregate_seal.IMPLEMENTATION_REASON_TERMS,
        )

        self.assertTrue(coverage["narrow trust boundaries"])

    def test_reconcile_promotes_only_the_canonical_coverage_correction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            record_path = Path(temporary_directory) / "implementation_review.json"
            route = {
                "TASK_SCOPE": "bounded",
                "TASK_STAGE_CLOSING": False,
                "TASK_REQUIRE_INDEPENDENT_REVIEW": True,
                "TASK_SKIP_STAGE_TRANSITION": True,
                "ROUTING_REQUIREMENT": "independent_review:required",
            }
            request_binding = {
                "path": "reviews/implementation_request.json",
                "sha256": "a" * 64,
            }
            reviewed_artifacts = {
                "request": request_binding,
                "proof_inventory": {
                    "path": "proof_inventory/targets.json",
                    "sha256": "b" * 64,
                },
            }
            handoff = {
                "path": "/mission/round-0031.json",
                "sha256": "c" * 64,
                "round": 31,
                "producer_role": "reviewer",
                "created_at": 2.0,
                "reason": "The retained dependency boundaries are narrow.",
                "explicit_reason_coverage": {
                    "narrow trust boundaries": True,
                },
            }
            original = {
                "schema_version": aggregate_seal.SCHEMA_VERSION,
                "artifact_role": "independent_reviewer_decision",
                "review_type": "implementation",
                "review_status": "done",
                "acceptance_eligible": False,
                "reason": handoff["reason"],
                "explicit_reason_coverage": {
                    "narrow trust boundaries": False,
                },
                "route": route,
                "request": request_binding,
                "reviewed_artifacts": reviewed_artifacts,
                "canonical_handoff": {
                    key: handoff[key]
                    for key in ("path", "sha256", "round", "producer_role")
                },
                "completed_at": 3.0,
            }
            aggregate_seal.write_json_atomic(record_path, original)

            with (
                mock.patch.object(
                    aggregate_seal,
                    "IMPLEMENTATION_REVIEW_RECORD",
                    record_path,
                ),
                mock.patch.object(
                    aggregate_seal,
                    "validate_implementation_request",
                    return_value=(
                        {"created_at_utc": "1970-01-01T00:00:01Z"},
                        request_binding,
                    ),
                ),
                mock.patch.object(
                    aggregate_seal,
                    "implementation_reviewed_artifacts",
                    return_value=reviewed_artifacts,
                ),
                mock.patch.object(
                    aggregate_seal,
                    "canonical_review_binding",
                    return_value=handoff,
                ),
            ):
                result = aggregate_seal.reconcile_implementation_review()

            reconciled = aggregate_seal.load_json(record_path)
            self.assertEqual(
                result["status"], "implementation_review_accepted"
            )
            self.assertTrue(reconciled["acceptance_eligible"])
            self.assertTrue(
                reconciled["explicit_reason_coverage"][
                    "narrow trust boundaries"
                ]
            )
            self.assertEqual(reconciled["completed_at"], original["completed_at"])
            self.assertEqual(
                reconciled["canonical_handoff"], original["canonical_handoff"]
            )

    def test_final_reason_requires_all_gate_dispositions(self) -> None:
        implementation_only = aggregate_seal.reason_coverage(
            COMPLETE_REASON.split("The structural gate", 1)[0],
            aggregate_seal.FINAL_REASON_TERMS,
        )
        complete = aggregate_seal.reason_coverage(
            COMPLETE_REASON,
            aggregate_seal.FINAL_REASON_TERMS,
        )

        self.assertFalse(all(implementation_only.values()))
        self.assertFalse(implementation_only["structural gate"])
        self.assertFalse(implementation_only["zero unresolved findings"])
        self.assertTrue(all(complete.values()), complete)

    def test_missing_implementation_review_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            inventory = root / "proof_inventory/targets.json"
            request = root / "reviews/implementation_request.json"
            record = root / "reviews/implementation_review.json"
            review_basis = {
                "readable_artifacts": ["proof_inventory/targets.json"],
                "fresh_execution": {
                    "proof_generation_at_utc": "2026-09-01T16:00:00Z",
                    "verification_bound_at_utc": "2026-09-01T17:00:00Z",
                    "run_id": "fresh-run",
                    "run_dir": "verification/live_runs/fresh-run",
                    "state": "completed",
                    "commands_recorded": 512,
                    "mutation_rejections": 128,
                },
            }
            aggregate_seal.write_json_atomic(inventory, {"targets": []})
            aggregate_seal.write_json_atomic(
                request,
                {
                    "status": "awaiting_independent_review",
                    "acceptance_claim": False,
                    "created_at_utc": "2026-09-01T18:00:00Z",
                    "review_basis": review_basis,
                },
            )

            with (
                mock.patch.multiple(
                    aggregate_seal,
                    CAMPAIGN_ROOT=root,
                    TARGETS_PATH=inventory,
                    IMPLEMENTATION_REVIEW_REQUEST=request,
                    IMPLEMENTATION_REVIEW_RECORD=record,
                ),
                mock.patch.object(
                    aggregate_seal,
                    "implementation_review_basis",
                    return_value=review_basis,
                ),
            ):
                with self.assertRaisesRegex(
                    aggregate_seal.AggregateSealError,
                    "accepted implementation review record is missing",
                ):
                    aggregate_seal.accepted_implementation_review()

    def test_implementation_request_must_follow_fresh_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            request = root / "reviews/implementation_request.json"
            review_basis = {
                "readable_artifacts": ["proof_inventory/targets.json"],
                "fresh_execution": {
                    "proof_generation_at_utc": "2026-09-01T16:00:00Z",
                    "verification_bound_at_utc": "2026-09-01T18:00:00Z",
                    "run_id": "fresh-run",
                    "run_dir": "verification/live_runs/fresh-run",
                    "state": "completed",
                    "commands_recorded": 512,
                    "mutation_rejections": 128,
                },
            }
            aggregate_seal.write_json_atomic(
                request,
                {
                    "status": "awaiting_independent_review",
                    "acceptance_claim": False,
                    "created_at_utc": "2026-09-01T17:00:00Z",
                    "review_basis": review_basis,
                },
            )

            with (
                mock.patch.object(
                    aggregate_seal,
                    "IMPLEMENTATION_REVIEW_REQUEST",
                    request,
                ),
                mock.patch.object(
                    aggregate_seal,
                    "implementation_review_basis",
                    return_value=review_basis,
                ),
            ):
                with self.assertRaisesRegex(
                    aggregate_seal.AggregateSealError,
                    "predates fresh execution evidence",
                ):
                    aggregate_seal.validate_implementation_request()

    def test_final_review_handoff_must_be_distinct(self) -> None:
        implementation_handoff = {
            "path": "/mission/round-0002.json",
            "sha256": "a" * 64,
            "round": 2,
        }
        for field, final_handoff in (
            (
                "path",
                {
                    "path": implementation_handoff["path"],
                    "sha256": "b" * 64,
                    "round": 3,
                },
            ),
            (
                "sha256",
                {
                    "path": "/mission/round-0003.json",
                    "sha256": implementation_handoff["sha256"],
                    "round": 3,
                },
            ),
            (
                "round",
                {
                    "path": "/mission/round-0003.json",
                    "sha256": "b" * 64,
                    "round": 2,
                },
            ),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    aggregate_seal.AggregateSealError, field
                ):
                    aggregate_seal.require_distinct_review_handoffs(
                        implementation_handoff, final_handoff
                    )

        aggregate_seal.require_distinct_review_handoffs(
            implementation_handoff,
            {
                "path": "/mission/round-0003.json",
                "sha256": "b" * 64,
                "round": 3,
            },
        )

    def test_candidate_validation_precedes_terminal_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            final_delivery = root / "proof_inventory/final_delivery.json"
            with (
                mock.patch.multiple(
                    aggregate_seal,
                    CAMPAIGN_ROOT=root,
                    PROOF_INVENTORY_ROOT=root / "proof_inventory",
                    FINAL_DELIVERY=final_delivery,
                ),
                mock.patch.object(
                    aggregate_seal,
                    "validate_candidate_state",
                    side_effect=aggregate_seal.AggregateSealError(
                        "candidate is stale"
                    ),
                ),
                mock.patch.object(
                    aggregate_seal, "accepted_final_review"
                ) as accepted_review,
                mock.patch.object(
                    aggregate_seal, "write_json_exclusive"
                ) as publish,
            ):
                with self.assertRaisesRegex(
                    aggregate_seal.AggregateSealError, "candidate is stale"
                ):
                    aggregate_seal.finalize_accepted_review(
                        root / "reviews/final_aggregate_review.json"
                    )

            accepted_review.assert_not_called()
            publish.assert_not_called()
            self.assertFalse(final_delivery.exists())

    def test_candidate_check_is_nonterminal(self) -> None:
        with mock.patch.object(
            aggregate_seal,
            "check",
            return_value={
                "certification_id": "candidate",
                "status": "implementation_reviewed_pending_final_review",
            },
        ):
            self.assertEqual(aggregate_seal.main(["check"]), 2)


if __name__ == "__main__":
    unittest.main()
