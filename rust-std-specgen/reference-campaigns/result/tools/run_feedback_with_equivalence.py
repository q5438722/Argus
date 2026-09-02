#!/usr/bin/env python3
"""Run canonical feedback and bind selected-relation capability honestly."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--vstd-root", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--z3-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed-candidates", type=Path, required=True)
    parser.add_argument("--outcome-equivalence", type=Path, required=True)
    parser.add_argument("--relation-capability", type=Path, required=True)
    parser.add_argument("--feedback-rounds", type=int, required=True)
    parser.add_argument("--jobs", type=int, required=True)
    parser.add_argument("--check-timeout", type=int, required=True)
    parser.add_argument("--rlimit", type=float, required=True)
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(message)


def target_bindings(
    payload: dict[str, Any],
    path: Path,
) -> dict[str, dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list):
        fail("outcome-equivalence records are malformed")
    return {
        str(record["target"]): support.outcome_equivalence_binding(
            record, payload, path
        )
        for record in records
        if isinstance(record, dict)
    }


def main() -> int:
    args = parse_args()
    equivalence = support.load_json(args.outcome_equivalence)
    common_binding = support.outcome_equivalence_artifact_binding(
        equivalence, args.outcome_equivalence
    )
    bindings = target_bindings(equivalence, args.outcome_equivalence)
    relation_capability = support.load_json(args.relation_capability)
    expected_capability = support.feedback_relation_capability_payload(
        equivalence
    )
    if relation_capability != expected_capability:
        fail("selected-relation capability classification is stale")
    canonical_runner = relation_capability.get("canonical_runner", {})
    if (
        not isinstance(canonical_runner, dict)
        or args.runner.resolve()
        != Path(str(canonical_runner.get("path"))).resolve()
        or support.sha256(args.runner)
        != canonical_runner.get("sha256")
    ):
        fail(
            "feedback runner does not match the relation-capability "
            "classification"
        )
    common_relation_capability = (
        support.feedback_relation_capability_binding(
            relation_capability,
            args.relation_capability,
        )
    )
    manifest = support.load_json(args.manifest)
    seeds = support.load_json(args.seed_candidates)
    targets = manifest.get("targets")
    if not isinstance(targets, list):
        fail("feedback manifest targets are malformed")
    manifest_targets = {
        str(target.get("target")): target
        for target in targets
        if isinstance(target, dict)
    }
    if len(manifest_targets) != len(targets):
        fail("feedback manifest contains duplicate or malformed targets")
    if manifest.get("metadata", {}).get("outcome_equivalence") != (
        common_binding
    ):
        fail("feedback manifest lacks the current equivalence-version set")
    if manifest.get("metadata", {}).get(
        "selected_relation_evaluation"
    ) != common_relation_capability:
        fail("feedback manifest lacks the relation capability binding")
    for target, entry in manifest_targets.items():
        expected = bindings.get(target)
        if expected is None:
            fail(f"feedback target lacks an equivalence record: {target}")
        if entry.get("outcome_equivalence") != expected:
            fail(f"feedback target has a stale equivalence binding: {target}")
        expected_relation = (
            support.feedback_relation_target_classification(
                expected,
                relation_capability,
                args.relation_capability,
            )
        )
        if entry.get("selected_relation_evaluation") != expected_relation:
            fail(
                "feedback target has a stale selected-relation "
                f"classification: {target}"
            )
        seed = seeds.get(target)
        if not isinstance(seed, dict):
            fail(f"feedback target lacks a seed candidate: {target}")
        if seed.get("outcome_equivalence") != expected:
            fail(f"seed candidate has a stale equivalence binding: {target}")
        if seed.get("selected_relation_evaluation") != expected_relation:
            fail(
                "seed candidate has a stale selected-relation "
                f"classification: {target}"
            )

    command = [
        sys.executable,
        str(args.runner),
        "--manifest",
        str(args.manifest),
        "--contracts",
        str(args.contracts),
        "--vstd-root",
        str(args.vstd_root),
        "--verus-bin",
        str(args.verus_bin),
        "--z3-path",
        str(args.z3_path),
        "--out",
        str(args.out),
        "--seed-candidates",
        str(args.seed_candidates),
        "--feedback-rounds",
        str(args.feedback_rounds),
        "--jobs",
        str(args.jobs),
        "--check-timeout",
        str(args.check_timeout),
        "--rlimit",
        str(args.rlimit),
    ]
    completed = subprocess.run(
        command,
        cwd=support.ROOT,
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode

    summary_path = args.out / "batch_summary.json"
    summary = support.load_json(summary_path)
    raw_finals = summary.get("final_candidates")
    raw_results = summary.get("results")
    if not isinstance(raw_finals, list) or not isinstance(raw_results, list):
        fail("canonical feedback summary is malformed")
    finals = {
        str(candidate.get("target")): candidate
        for candidate in raw_finals
        if isinstance(candidate, dict)
    }
    results = {
        str(result.get("target")): result
        for result in raw_results
        if isinstance(result, dict)
    }
    if (
        len(finals) != len(raw_finals)
        or len(results) != len(raw_results)
        or set(finals) != set(manifest_targets)
        or set(results) != set(manifest_targets)
    ):
        fail("feedback output target set does not match the manifest")

    for target in sorted(manifest_targets):
        expected = bindings[target]
        expected_relation = (
            support.feedback_relation_target_classification(
                expected,
                relation_capability,
                args.relation_capability,
            )
        )
        result = results[target]
        final = result.get("final")
        if not isinstance(final, dict):
            fail(f"feedback result lacks a final record: {target}")
        candidate = final.get("candidate")
        if (
            not isinstance(candidate, dict)
            or candidate.get("outcome_equivalence") != expected
        ):
            fail(
                "canonical feedback did not preserve the seed equivalence "
                f"binding: {target}"
            )
        candidate["selected_relation_evaluation"] = expected_relation
        for history in result.get("history", []):
            history_candidate = (
                history.get("candidate")
                if isinstance(history, dict)
                else None
            )
            if (
                isinstance(history_candidate, dict)
                and history_candidate.get("outcome_equivalence") != expected
            ):
                fail(f"feedback history has a stale binding: {target}")
            if isinstance(history_candidate, dict):
                history_candidate[
                    "selected_relation_evaluation"
                ] = expected_relation
        target_dir = (
            args.out / "targets" / support.safe_name(target)
        )
        raw_target = support.load_json(target_dir / "target.json")
        if raw_target.get("outcome_equivalence") != expected:
            fail(f"raw feedback target has a stale binding: {target}")
        raw_target["selected_relation_evaluation"] = expected_relation
        support.write_json(
            target_dir / "target.json",
            raw_target,
        )
        round_dirs = sorted(
            path
            for path in target_dir.glob("round_*")
            if path.is_dir()
        )
        if not round_dirs:
            fail(f"feedback target has no round directory: {target}")
        for round_dir in round_dirs:
            raw_candidate_path = round_dir / "candidate.json"
            raw_candidate = support.load_json(raw_candidate_path)
            if raw_candidate.get("outcome_equivalence") != expected:
                fail(
                    "raw feedback candidate has a stale binding: "
                    f"{target} {round_dir.name}"
                )
            raw_candidate[
                "selected_relation_evaluation"
            ] = expected_relation
            support.write_json(raw_candidate_path, raw_candidate)

            round_result_path = round_dir / "round_result.json"
            if round_result_path.is_file():
                round_result = support.load_json(round_result_path)
                round_candidate = round_result.get("candidate")
                if (
                    not isinstance(round_candidate, dict)
                    or round_candidate.get("outcome_equivalence")
                    != expected
                ):
                    fail(
                        "round result has a stale equivalence binding: "
                        f"{target} {round_dir.name}"
                    )
                round_candidate[
                    "selected_relation_evaluation"
                ] = expected_relation
                round_result["canonical_evidence_role"] = (
                    "diagnostic_only"
                )
                round_result["selected_relation_evaluation"] = (
                    expected_relation
                )
                support.write_json(round_result_path, round_result)

            diagnostic_binding = (
                support.feedback_round_diagnostic_binding(
                    target,
                    round_dir,
                    expected,
                    expected_relation,
                )
            )
            support.write_json(
                round_dir
                / support.FEEDBACK_DIAGNOSTIC_BINDING_FILENAME,
                diagnostic_binding,
            )

        target_summary_path = target_dir / "summary.json"
        target_summary = support.load_json(target_summary_path)
        target_final = target_summary.get("final")
        target_final_candidate = (
            target_final.get("candidate")
            if isinstance(target_final, dict)
            else None
        )
        if (
            not isinstance(target_final_candidate, dict)
            or target_final_candidate.get("outcome_equivalence")
            != expected
        ):
            fail(f"raw target summary lacks final candidate: {target}")
        target_final_candidate[
            "selected_relation_evaluation"
        ] = expected_relation
        for target_history in target_summary.get("history", []):
            target_history_candidate = (
                target_history.get("candidate")
                if isinstance(target_history, dict)
                else None
            )
            if isinstance(target_history_candidate, dict):
                if (
                    target_history_candidate.get("outcome_equivalence")
                    != expected
                ):
                    fail(
                        "target summary history has a stale equivalence "
                        f"binding: {target}"
                    )
                target_history_candidate[
                    "selected_relation_evaluation"
                ] = expected_relation
        target_summary[
            "selected_relation_evaluation"
        ] = expected_relation
        support.write_json(target_summary_path, target_summary)
        finals[target]["outcome_equivalence"] = expected
        finals[target]["selected_relation_evaluation"] = expected_relation

    diagnostic_bindings = support.feedback_diagnostic_binding_set(
        args.out
    )
    metadata = summary.get("metadata")
    counts = summary.get("counts")
    if not isinstance(metadata, dict) or not isinstance(counts, dict):
        fail("feedback summary metadata or counts are malformed")
    metadata["outcome_equivalence"] = common_binding
    metadata[
        "selected_relation_evaluation"
    ] = common_relation_capability
    metadata["canonical_diagnostic_bindings"] = diagnostic_bindings
    counts["equivalence_bound_targets"] = len(bindings.keys() & finals.keys())
    counts["selected_relation_evaluated_targets"] = 0
    counts["selected_relation_unsupported_targets"] = len(
        bindings.keys() & finals.keys()
    )
    counts["diagnostic_only_rounds"] = diagnostic_bindings[
        "binding_count"
    ]
    summary["outcome_equivalence"] = common_binding
    summary[
        "selected_relation_evaluation"
    ] = common_relation_capability
    summary["canonical_diagnostic_bindings"] = diagnostic_bindings
    support.write_json(summary_path, summary)
    print(
        json.dumps(
            {
                "equivalence_bound_targets": counts[
                    "equivalence_bound_targets"
                ],
                "diagnostic_only_rounds": counts[
                    "diagnostic_only_rounds"
                ],
                "selected_relation_evaluated_targets": counts[
                    "selected_relation_evaluated_targets"
                ],
                "selected_relation_unsupported_targets": counts[
                    "selected_relation_unsupported_targets"
                ],
                "version_set_sha256": common_binding[
                    "version_set_sha256"
                ],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
