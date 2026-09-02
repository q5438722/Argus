#!/usr/bin/env python3
"""Route BTreeSet campaign gates through the canonical independent Reviewer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIFE_ROOT = Path(
    "/home/chentianyu/.argus-skill-v011-slice-conditional/projects/s-fb203e1c"
)
HANDOFF_ROOT = LIFE_ROOT / "handoffs/77b0f688faf9"
MISSION_PATH = HANDOFF_ROOT / "mission.json"
CHECKPOINT_PATH = HANDOFF_ROOT / "CHECKPOINT.md"
LATEST_PATH = HANDOFF_ROOT / "latest.json"
MISSION_ID = "77b0f688faf9"

STAGES = {
    "inventory_specification": {
        "checker_args": ["--spec-review"],
        "request": "reviews/inventory_specification_review_request.json",
        "record": "reviews/inventory_specification.json",
        "stage_closing": False,
    },
    "proof_completeness": {
        "checker_args": ["--proof-review"],
        "request": "reviews/proof_completeness_review_request.json",
        "record": "reviews/proof_completeness.json",
        "stage_closing": False,
    },
    "final_aggregate": {
        "checker_args": ["--pre-final-review"],
        "request": "reviews/final_aggregate_review_request.json",
        "record": "reviews/final_aggregate.json",
        "stage_closing": True,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_progress(path: Path, event: str, **fields: Any) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"event": event, "timestamp": time.time(), **fields}, sort_keys=True)
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def latest_round() -> int:
    latest = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    handoff_path = Path(str(latest.get("handoff", {}).get("path", "")))
    match = re.fullmatch(r"round-(\d{4})(?:-engineer)?\.json", handoff_path.name)
    if match is None:
        raise RuntimeError(f"canonical latest handoff is malformed: {handoff_path}")
    return int(match.group(1))


def next_review_round() -> int:
    candidate = latest_round() + 1
    while (
        (HANDOFF_ROOT / f"round-{candidate:04d}.json").exists()
        or (HANDOFF_ROOT / f"round-{candidate:04d}-engineer.json").exists()
    ):
        candidate += 1
    return candidate


def counts() -> dict[str, int]:
    inventory = json.loads(
        (ROOT / "inventory/btree_set_exec_fn_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    aggregate = json.loads(
        (ROOT / "proof_inventory/aggregate_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        **inventory["counts"],
        "selected": len(inventory["rows"]),
        "actual_verus": aggregate["actual_verus_verified"],
        "actual_verus_native": aggregate.get(
            "actual_verus_native_verified",
            0,
        ),
        "actual_verus_checker_adjudicated": aggregate.get(
            "actual_verus_checker_adjudicated",
            0,
        ),
        "completeness": aggregate["completeness_verified"],
        "mutations": aggregate["mutation_rejected"],
        "mutations_native": aggregate.get(
            "mutation_native_rejected",
            0,
        ),
        "mutations_checker_adjudicated": aggregate.get(
            "mutation_checker_adjudicated",
            0,
        ),
        "failed": aggregate["failed"],
        "proof_pending": aggregate["pending"],
    }


def required_reason_statement(stage: str, values: dict[str, int]) -> str:
    facts = [
        f"stable inventory {values['stable_inventory_total']}",
        f"exact-vstd rows {values['exact_vstd']}",
        f"generated rows {values['generated']}",
    ]
    if stage != "inventory_specification":
        facts.extend(
            [
                f"selected proof targets {values['selected']}",
                (
                    "actual Verus implementation proofs "
                    f"{values['actual_verus']}"
                ),
                f"completeness proofs {values['completeness']}",
                f"semantic mutations rejected {values['mutations']}",
                "BTreeMap delegation or merge-iterator dependency retained",
                "zero failed",
            ]
        )
    facts.append("zero pending")
    if stage == "final_aggregate":
        facts.extend(
            [
                "all gates pass",
                "zero unresolved findings",
                (
                    "accepted semantic boundaries do not imply "
                    "foundational trust freedom"
                ),
            ]
        )
    return f"Accepted {stage} coverage: " + "; ".join(facts) + "."


def reason_output_contract(stage: str, values: dict[str, int]) -> str:
    statement = required_reason_statement(stage, values)
    return (
        "The final Reviewer reason is a machine-checked acceptance record. "
        "Before returning status done, independently verify every fact and include "
        "this complete statement verbatim in the reason: "
        f'"{statement}" Omission of any fact makes the review acceptance-ineligible; '
        "return continue instead if any fact cannot be verified."
    )


def objective(stage: str, values: dict[str, int]) -> str:
    common = (
        f"The authoritative inventory has {values['stable_inventory_total']} stable "
        f"executable BTreeSet-owned rows, reconciled as {values['exact_vstd']} exact-vstd, "
        f"{values['generated']} generated, {values['genuinely_impossible']} impossible, "
        f"and {values['pending']} specification-pending. There are "
        f"{values['selected']} selected proof targets."
    )
    if stage == "inventory_specification":
        detail = (
            "Independently review the complete stable public inherent, trait, iterator, "
            "range, set-operation, and ExtractIf inventory; the unstable entry/cursor/"
            "allocator exclusions; exact eight-dimension signature-level vstd "
            "subtraction; direct non-vacuous ordered-set contracts; range panic, "
            "callback, representative, and ordered-adapter semantics; generated "
            "no-verify and seeded feedback evidence. Return done only if this "
            "inventory/specification gate is accepted with zero pending rows."
        )
    elif stage == "proof_completeness":
        detail = (
            f"Independently review all {values['selected']} colocated source-shaped "
            "implementation and exact-observation completeness harnesses. Confirm the "
            "real BTreeSet-to-BTreeMap or merge-iterator dependency path is retained, "
            f"actual Verus succeeds for {values['actual_verus']} implementation and "
            f"{values['completeness']} completeness proofs, all {values['mutations']} "
            "negative mutations are rejected, with "
            f"{values['actual_verus_native']} native exact-signature proofs and "
            f"{values['actual_verus_checker_adjudicated']} narrowly evidenced "
            "IntoIterator associated-item checker adjudications, no public target "
            "uses external_body, "
            "source/contract/hash/trust audits pass, and failed/pending are zero. "
            "Reject a postcondition-restatement or assumed-target campaign."
        )
    else:
        detail = (
            "Perform a fresh final aggregate review. Explicitly state the inventory, "
            "exact-vstd, specification, no-verify, actual-Verus, implementation, "
            "completeness, mutation, source/hash, provenance, trust, artifact-layout, "
            "and aggregate gates all pass; state all row/proof counts, zero failed and "
            "zero pending, zero unresolved findings, and that accepted semantic "
            "boundaries do not imply foundational trust-freedom."
        )
    return "\n".join(
        (
            "ROUTING_REQUIREMENT=independent_review:required",
            "TASK_SCOPE=bounded",
            f"TASK_STAGE_CLOSING={'true' if stage == 'final_aggregate' else 'false'}",
            "TASK_REQUIRE_INDEPENDENT_REVIEW=true",
            f"TASK_SKIP_STAGE_TRANSITION={'false' if stage == 'final_aggregate' else 'true'}",
            "",
            common,
            detail,
            "",
            "Start with the stage review request. Inspect exact referenced artifacts "
            "and run the cheapest decisive campaign-local checks. Do not trust "
            "Engineer-authored pass fields without checking proof bodies, hashes, and "
            "raw result evidence. The successful verification matrix named by "
            "verification/evidence/verus_matrix/latest_manifest.json is immutable "
            "review evidence: do not invoke tools/run_verus_matrix.py or generate a "
            "replacement matrix during review. Return continue with a precise "
            "corrective next action for any defect.",
            "",
            reason_output_contract(stage, values),
        )
    )


def required_coverage(stage: str, reason: str, values: dict[str, int]) -> dict[str, bool]:
    terms = {
        "stable inventory count": rf"\b{values['stable_inventory_total']}\b",
        "exact-vstd count": rf"\b{values['exact_vstd']}\b",
        "generated count": rf"\b{values['generated']}\b",
        "zero pending": r"\b(?:zero|0|no)\b.{0,32}\bpending\b|\bpending\b.{0,32}\b(?:zero|0|none)\b",
        "explicit acceptance": r"\b(?:accept|pass|done)\w*\b",
    }
    if stage != "inventory_specification":
        terms.update(
            {
                "selected proof count": rf"\b{values['selected']}\b",
                "actual Verus": r"\bactual[- ]?verus\b",
                "completeness": r"\bcompleteness\b",
                "mutations": r"\bmutations?\b",
                "BTreeMap delegation": r"\bbtreemap\b.{0,48}\bdelegat|\bdelegat\w*\b.{0,48}\bbtreemap\b",
                "zero failed": r"\b(?:zero|0|no)\b.{0,32}\bfailed\b|\bfailed\b.{0,32}\b(?:zero|0|none)\b",
            }
        )
    if stage == "final_aggregate":
        terms.update(
            {
                "all gates": r"\bgates?\b.{0,48}\bpass",
                "zero unresolved": r"\b(?:zero|0|no)\b.{0,32}\bunresolved\b|\bunresolved\b.{0,32}\b(?:zero|0|none)\b",
                "no foundational trust freedom": r"\b(?:no|not|without)\b.{0,80}\bfoundational\b.{0,48}\btrust",
            }
        )
    return {
        label: bool(re.search(pattern, reason, re.IGNORECASE | re.DOTALL))
        for label, pattern in terms.items()
    }


def acceptance_eligible(
    stage: str,
    status: str,
    reason: str,
    values: dict[str, int],
) -> bool:
    return status == "done" and all(required_coverage(stage, reason, values).values())


def stage_artifacts(stage: str) -> list[Path]:
    common = [
        ROOT / "aggregate/schema.json",
        ROOT / "provenance/source_manifest.json",
        ROOT / "provenance/freeze_context.json",
        ROOT / "inventory/btree_set_exec_fn_inventory.json",
        ROOT / "inventory/unstable_non_executable_exclusions.json",
        ROOT / "inventory/exact_vstd_audit.json",
        ROOT / "inventory/inventory_reconciliation.json",
        ROOT / "specs/all_btree_set_specs.json",
        ROOT / "specs/README.md",
        ROOT / "specs/generated_btree_set_specs.rs",
        ROOT / "specs/btree_set_shared_vocabulary.rs",
        ROOT / "verification/spec_determinism_harnesses/manifest.json",
        ROOT
        / "verification/evidence/btree_set_feedback_determinism/latest_manifest.json",
        ROOT / "verification/audits/feedback_determinism_audit.json",
    ]
    if stage == "inventory_specification":
        return common
    proof = [
        ROOT / "proof_inventory/targets.json",
        ROOT / "proof_inventory/aggregate_coverage.json",
        ROOT / "TRUST_BOUNDARY_AUDIT.md",
        ROOT / "verification/evidence/verus_matrix/latest_manifest.json",
        ROOT / "verification/audits/proof_evidence_audit.json",
        ROOT / "verification/audits/mutation_audit.json",
        ROOT / "reviews/inventory_specification.json",
    ]
    if stage == "proof_completeness":
        return [*common, *proof]
    return [
        *common,
        *proof,
        ROOT / "reviews/proof_completeness.json",
        ROOT / "proof_inventory/aggregate_coverage.md",
    ]


def build_artifact_index(stage: str) -> Path:
    files: list[Path] = []
    for path in stage_artifacts(stage):
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append(path)
    feedback_latest = json.loads(
        (
            ROOT
            / "verification/evidence/btree_set_feedback_determinism/latest_manifest.json"
        ).read_text(encoding="utf-8")
    )
    feedback_summary = ROOT / str(feedback_latest["summary"])
    files.extend(
        [
            feedback_summary,
            feedback_summary.parent / "manifest.json",
            feedback_summary.parent / "module_evidence/generated_spec_no_verify.json",
            feedback_summary.parent / "module_evidence/generated_spec_actual_verus.json",
            feedback_summary.parent / "checker_capability_adjudications.json",
        ]
    )
    files.extend(
        sorted(
            (ROOT / "verification/spec_determinism_harnesses").glob("*.rs")
        )
    )
    files.extend(
        sorted(
            (feedback_summary.parent / "spec_determinism").glob("*.json")
        )
    )
    if stage != "inventory_specification":
        files.extend(
            sorted(
                path
                for path in (ROOT / "proof_harnesses").glob("*/*")
                if path.is_file()
                and path.name
                in {
                    "implementation_proof.rs",
                    "completeness_proof.rs",
                    "mutation_proof.rs",
                    "checker_adjudication_proof.rs",
                    "checker_adjudication_mutation.rs",
                    "checker_adjudication.json",
                    "source_excerpt.rs",
                    "contract_binding.json",
                    "contract_equivalence.json",
                    "transformation_manifest.json",
                    "dependency_assumptions.json",
                    "trust_boundaries.json",
                    "mutation_manifest.json",
                    "summary.json",
                }
            )
        )
        files.extend(
            sorted(
                path
                for path in (ROOT / "proof_harnesses").glob("*/evidence/*")
                if path.is_file()
                and path.suffix in {".json", ".rc"}
            )
        )
        for adjudication in sorted(
            (ROOT / "proof_harnesses").glob(
                "*/checker_adjudication.json"
            )
        ):
            evidence = adjudication.parent / "evidence"
            for stem in (
                "implementation_actual_verus",
                (
                    "implementation_actual_verus"
                    "_checker_adjudication"
                ),
                "mutation_actual_verus",
                "mutation_actual_verus_checker_adjudication",
            ):
                files.extend(
                    path
                    for suffix in (
                        ".command",
                        ".stdout",
                        ".stderr",
                        ".rc",
                    )
                    if (path := evidence / f"{stem}{suffix}").is_file()
                )
        verus_latest = json.loads(
            (
                ROOT / "verification/evidence/verus_matrix/latest_manifest.json"
            ).read_text(encoding="utf-8")
        )
        verus_summary = ROOT / str(verus_latest["summary"])
        files.extend(
            [
                verus_summary,
                verus_summary.parent / "manifest.json",
                verus_summary.parent / "versions.json",
            ]
        )
    files = sorted(set(files))
    index_path = ROOT / "aggregate" / f"{stage}_artifact_index.json"
    atomic_json(
        index_path,
        {
            "schema_version": 1,
            "stage": stage,
            "artifact_count": len(files),
            "artifacts": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in files
            ],
        },
    )
    return index_path


def run_gate(stage: str, run_dir: Path) -> dict[str, Any]:
    config = STAGES[stage]
    command = [sys.executable, "tools/check_campaign.py", *config["checker_args"]]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    gate_root = run_dir / "gate"
    gate_root.mkdir(parents=True, exist_ok=True)
    (gate_root / "command").write_text(" ".join(command) + "\n", encoding="utf-8")
    (gate_root / "stdout").write_text(result.stdout, encoding="utf-8")
    (gate_root / "stderr").write_text(result.stderr, encoding="utf-8")
    (gate_root / "rc").write_text(f"{result.returncode}\n", encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(
            f"campaign gate failed before independent review: {result.stdout}"
        )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
    }


def main() -> int:
    from argus_skill.adapters.agent_cli_backend import AgentCliBackend
    from argus_skill.life.context_packet import record_reviewed_handoff
    from argus_skill.reviewer import Reviewer, ReviewerConfig

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    stage = args.stage
    config = STAGES[stage]
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    stop_path = run_dir / "STOP"
    if stop_path.exists():
        raise RuntimeError(f"refusing stale cancellation flag: {stop_path}")
    status_path = run_dir / "status.json"
    progress_path = run_dir / "progress.jsonl"
    progress_path.touch(exist_ok=True)
    started = time.time()
    status: dict[str, Any] = {
        "schema_version": 1,
        "task_id": args.task_id,
        "stage": stage,
        "state": "running",
        "started_at": started,
        "updated_at": started,
        "stream_events": 0,
    }
    atomic_json(status_path, status)
    append_progress(progress_path, "run_started", task_id=args.task_id, stage=stage)

    gate = run_gate(stage, run_dir)
    artifact_index = build_artifact_index(stage)
    values = counts()
    request_path = ROOT / config["request"]
    questions = [
        "Are inventory counts independently derived from Rustdoc/source rather than hard-coded?",
        "Does exact-vstd subtraction match target and all eight signature dimensions?",
        "Do contracts state principal range, iterator, callback, size-hint, representative, formatting/hash, and ExtractIf normal/panic/partial-drop behavior directly or through defined law-constrained vocabulary?",
        "Do both current module Verus modes and per-generated-target feedback evidence bind the reviewed contract hashes?",
        "Does the checker fail closed on opaque whole-behavior helpers, pending rows, stale evidence, and stage order?",
    ]
    if stage != "inventory_specification":
        questions.extend(
            [
                "Does each selected row have exactly one source/hash/contract-bound executable proof harness regenerated after specification acceptance?",
                "Are BTreeMap operations and return shapes narrower than the public target while BTreeSet projection and control flow remain executable?",
                "Does completeness conjoin the actual hashed accepted clauses without a surrogate or whole-outcome dependency?",
                "Are current two-mode and mutation records complete, and are trust boundaries explicit without a whole-target assumption?",
                "For exactly the three IntoIterator::Item AIR failures, do exact-signature --no-verify and raw checker evidence pair with actual-Verus success and mutation rejection for an otherwise identical body whose only erased precondition strengthens the proof domain?",
            ]
        )
    request = {
        "schema_version": 1,
        "module": "alloc::collections::btree_set",
        "review_type": stage,
        "independent_review": "required",
        "route": {
            "ROUTING_REQUIREMENT": "independent_review:required",
            "TASK_SCOPE": "bounded",
            "TASK_STAGE_CLOSING": config["stage_closing"],
            "TASK_REQUIRE_INDEPENDENT_REVIEW": True,
            "TASK_SKIP_STAGE_TRANSITION": not config["stage_closing"],
        },
        "counts": values,
        "artifact_index": {
            "path": str(artifact_index.relative_to(ROOT)),
            "sha256": sha256_file(artifact_index),
        },
        "campaign_gate": gate,
        "questions": questions,
        "output_contract": {
            "done_requires_complete_reason_coverage": True,
            "required_reason_statement": required_reason_statement(stage, values),
            "omission_is_acceptance_ineligible": True,
        },
    }
    atomic_json(request_path, request)

    manifest = {
        "schema_version": 1,
        "task_id": args.task_id,
        "stage": stage,
        "objective": objective(stage, values),
        "route": request["route"],
        "request": {
            "path": str(request_path.relative_to(ROOT)),
            "sha256": sha256_file(request_path),
        },
        "created_at": started,
    }
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists() and json.loads(
        manifest_path.read_text(encoding="utf-8")
    ) != manifest:
        raise RuntimeError(f"refusing to overwrite different manifest: {manifest_path}")
    atomic_json(manifest_path, manifest)
    last_heartbeat = 0.0

    def interrupt_reason() -> str | None:
        return "supervised STOP requested" if stop_path.exists() else None

    def stream_event(stream_name: str, _line: str) -> None:
        nonlocal last_heartbeat
        status["stream_events"] = int(status["stream_events"]) + 1
        now_value = time.time()
        if now_value - last_heartbeat < 20:
            return
        last_heartbeat = now_value
        status.update(
            {
                "updated_at": now_value,
                "last_stream": stream_name,
                "elapsed_seconds": round(now_value - started, 1),
            }
        )
        atomic_json(status_path, status)
        append_progress(
            progress_path,
            "heartbeat",
            elapsed_seconds=status["elapsed_seconds"],
            stream_events=status["stream_events"],
        )

    backend = AgentCliBackend(
        backend="copilot",
        runner_bin="/home/chentianyu/.local/bin/copilot",
        default_interrupt_reason_provider=interrupt_reason,
        event_callback=stream_event,
    )
    reviewer = Reviewer(backend, memory_maintenance_enabled=False)
    review_objective = objective(stage, values)
    decision = reviewer.evaluate(
        objective=review_objective,
        original_objective=review_objective,
        operator_messages=[
            (
                f"Route the BTreeSet {stage} gate through "
                "independent_review:required. "
                f"{reason_output_contract(stage, values)}"
            )
        ],
        round_index=max(1, latest_round()),
        round_max=1,
        session_id=MISSION_ID,
        main_summary=(
            f"Engineering submits the bounded BTreeSet {stage} request with "
            f"{values['selected']} selected rows and inventory-derived checks."
        ),
        main_error=None,
        config=ReviewerConfig(
            model="gpt-5.6-sol",
            reasoning_effort="max",
            skip_git_repo_check=True,
            dangerous_yolo=True,
            working_dir=str(ROOT),
        ),
        planner_review_instruction=(
            f"This is the bounded independent {stage} gate. Review scientific "
            "validity and source-shaped proof evidence, not file presence alone. "
            "Audit the persisted successful matrix and never invoke "
            "tools/run_verus_matrix.py from this review. "
            f"{reason_output_contract(stage, values)}"
        ),
        raw_evidence=str(request_path.relative_to(ROOT)),
        scope="bounded",
        checkpoint_path=str(CHECKPOINT_PATH),
        background_context=(
            "BTreeMap and core::cmp remain explicit unaccepted narrow dependencies. "
            "No acceptance may imply foundational trust freedom."
        ),
        engineer_log_path=str(LIFE_ROOT / "events.jsonl"),
    )
    coverage = required_coverage(stage, decision.reason, values)
    eligible = acceptance_eligible(stage, decision.status, decision.reason, values)
    review_round = next_review_round()
    handoff_path = record_reviewed_handoff(
        mission_context_path=MISSION_PATH,
        round_index=review_round,
        engineer_summary=f"Bounded BTreeSet {stage} review packet submitted.",
        review=decision,
        checkpoint_path=CHECKPOINT_PATH,
    )
    if handoff_path is None:
        raise RuntimeError("Reviewer handoff was not recorded")
    completed = time.time()
    record = {
        "schema_version": 1,
        "artifact_role": "independent_reviewer_decision",
        "producer_role": "reviewer",
        "independent": True,
        "review_type": stage,
        "review": asdict(decision),
        "explicit_reason_coverage": coverage,
        "acceptance_eligible": eligible,
        "request": manifest["request"],
        "canonical_handoff": {
            "path": str(handoff_path),
            "round": review_round,
            "sha256": sha256_file(handoff_path),
        },
        "completed_at": completed,
    }
    atomic_json(ROOT / config["record"], record)
    atomic_json(run_dir / "result.json", record)
    pipeline_path = ROOT / "research/PIPELINE_STATE.json"
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    review_state = pipeline["stages"]["review"]
    accepted = set(review_state.get("accepted_gates", []))
    if record["acceptance_eligible"]:
        accepted.add(stage)
    review_state.update(
        {
            "status": (
                "done"
                if accepted
                == {
                    "inventory_specification",
                    "proof_completeness",
                    "final_aggregate",
                }
                else "in_progress"
            ),
            "accepted_gates": sorted(accepted),
            "last_gate": stage,
            "last_review_status": decision.status,
        }
    )
    if record["acceptance_eligible"] and stage == "inventory_specification":
        pipeline["stages"]["specification"]["status"] = "accepted"
        pipeline["stages"]["specification"]["review_gate"] = stage
    if record["acceptance_eligible"] and stage == "proof_completeness":
        pipeline["stages"]["implementation_completeness"]["status"] = "accepted"
        pipeline["stages"]["implementation_completeness"]["review_gate"] = stage
    atomic_json(pipeline_path, pipeline)
    status.update(
        {
            "state": "completed",
            "updated_at": completed,
            "completed_at": completed,
            "review_status": decision.status,
            "acceptance_eligible": record["acceptance_eligible"],
            "canonical_handoff": record["canonical_handoff"],
        }
    )
    atomic_json(status_path, status)
    append_progress(
        progress_path,
        "run_completed",
        review_status=decision.status,
        acceptance_eligible=record["acceptance_eligible"],
    )
    print(
        json.dumps(
            {
                "review_status": decision.status,
                "acceptance_eligible": record["acceptance_eligible"],
                "canonical_handoff": str(handoff_path),
            },
            sort_keys=True,
        )
    )
    return 0 if record["acceptance_eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
