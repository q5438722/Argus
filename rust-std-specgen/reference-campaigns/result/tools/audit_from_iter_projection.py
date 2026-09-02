#!/usr/bin/env python3
"""Adjudicate the FromIterator feedback projection failure."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


RUSTDOC_ITEM_ID = 26942


def main() -> int:
    feedback = support.load_json(support.FEEDBACK_SUMMARY_PATH)
    inventory = support.inventory_by_id()
    row = inventory[RUSTDOC_ITEM_ID]
    candidates = [
        candidate
        for candidate in feedback.get("final_candidates", [])
        if candidate.get("target") == row["target"]
    ]
    if len(candidates) != 1:
        raise SystemExit(
            "expected exactly one FromIterator feedback candidate"
        )
    candidate = candidates[0]
    safe_name = support.safe_name(str(row["target"]))
    target_root = support.FEEDBACK_ROOT / "targets" / safe_name
    target_summary = target_root / "summary.json"
    stderr = target_root / "round_00" / "det_stderr.txt"
    probe = support.load_json(support.FROM_ITER_PROBE_REPORT_PATH)
    seed = support.load_json(support.FEEDBACK_SEED_PATH)[
        str(row["target"])
    ]
    equivalence = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
    equivalence_record = next(
        record
        for record in equivalence["records"]
        if int(record["rustdoc_item_id"]) == RUSTDOC_ITEM_ID
    )
    equivalence_binding = support.outcome_equivalence_binding(
        equivalence_record, equivalence
    )
    relation_capability = support.load_json(
        support.FEEDBACK_RELATION_CAPABILITY_PATH
    )
    relation_evaluation = (
        support.feedback_relation_target_classification(
            equivalence_binding,
            relation_capability,
        )
    )
    stderr_text = stderr.read_text(encoding="utf-8")
    required_contract_fragments = (
        "result_all_ok",
        "into_iter_remaining::<Result<A, E>, I>(iter)",
        "result_ok_payloads_match",
        "result_collect_output",
        "FromIteratorSpec::from_iter_ensures",
        "result_short_circuit_trace",
        "ResultShortCircuitOperation::FromIterator",
        ").len() == stop + 1",
        "forall|prior: int|",
        "result == Err(",
    )
    negative_mutants = probe.get("negative_mutants", {})
    checks = {
        "aggregate_contract_typechecked": (
            candidate.get("typecheck_status") == "pass"
        ),
        "candidate_is_add_spec": candidate.get("decision") == "add_spec",
        "candidate_equivalence_version_bound": (
            candidate.get("outcome_equivalence")
            == equivalence_binding
        ),
        "candidate_selected_relation_classified_unsupported": (
            candidate.get("selected_relation_evaluation")
            == relation_evaluation
        ),
        "contract_retains_full_collector_and_first_err_laws": all(
            fragment in seed["contract_code"]
            for fragment in required_contract_fragments
        ),
        "exact_projection_failure_observed": (
            candidate.get("det_status") == "verus_error"
            and "internal error: generated ill-typed AIR code" in stderr_text
            and "proj%%core!iter.traits.collect.IntoIterator./Item"
            in stderr_text
        ),
        "projection_erased_exactness_proved": (
            probe.get("status") == "passed"
        ),
        "projection_probe_err_mutant_rejected": (
            negative_mutants.get("err_payload", {}).get(
                "rejected_as_expected"
            )
            is True
        ),
        "projection_probe_ok_mutant_rejected": (
            negative_mutants.get("ok_payload", {}).get(
                "rejected_as_expected"
            )
            is True
        ),
        "projection_probe_eager_consumption_mutant_rejected": (
            negative_mutants.get("consumes_after_err", {}).get(
                "rejected_as_expected"
            )
            is True
        ),
        "raw_target_summary_present": target_summary.is_file(),
    }
    passed = all(checks.values())
    report = {
        "adjudication": (
            "unsupported_projection_lowering"
            if passed
            else "unresolved_verus_error"
        ),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "dependency_boundary": (
            "The target output is exact relative to the explicit collector "
            "law over all Ok payloads, the exact first-Err law, and the "
            "source-item trace ending at that first Err. The raw "
            "IntoIterator::Item projection error is confined to the generic "
            "feedback harness."
        ),
        "feedback_batch_path": str(
            support.FEEDBACK_SUMMARY_PATH.relative_to(support.ROOT)
        ),
        "feedback_batch_sha256": support.sha256(
            support.FEEDBACK_SUMMARY_PATH
        ),
        "outcome_equivalence": equivalence_binding,
        "selected_relation_evaluation": relation_evaluation,
        "projection_probe_path": str(
            support.FROM_ITER_PROBE_REPORT_PATH.relative_to(support.ROOT)
        ),
        "projection_probe_sha256": support.sha256(
            support.FROM_ITER_PROBE_REPORT_PATH
        ),
        "raw_feedback_status": candidate.get("det_status"),
        "raw_stderr_path": str(stderr.relative_to(support.ROOT)),
        "raw_stderr_sha256": support.sha256(stderr),
        "raw_target_summary_path": str(
            target_summary.relative_to(support.ROOT)
        ),
        "raw_target_summary_sha256": support.sha256(target_summary),
        "rustdoc_item_id": RUSTDOC_ITEM_ID,
        "schema_version": 2,
        "status": "passed" if passed else "failed",
        "target": row["target"],
    }
    support.write_json(support.FROM_ITER_ADJUDICATION_PATH, report)
    print(
        json.dumps(
            {
                "adjudication": report["adjudication"],
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
