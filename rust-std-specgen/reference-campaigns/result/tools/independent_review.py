#!/usr/bin/env python3
"""Route core::result proof gates through the canonical independent Reviewer."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_ROOT))

from tools import aggregate_seal  # noqa: E402


HEARTBEAT_INTERVAL_SECONDS = 20.0

STAGES = {
    "implementation": {
        "request": aggregate_seal.IMPLEMENTATION_REVIEW_REQUEST,
        "record": aggregate_seal.IMPLEMENTATION_REVIEW_RECORD,
        "required_terms": aggregate_seal.IMPLEMENTATION_REASON_TERMS,
        "summary": (
            "Engineering submits the 64-target core::result implementation "
            "and completeness proof package for independent scientific review."
        ),
        "objective": (
            "Independently inspect the complete core::result implementation "
            "and completeness proof package. Do not trust aggregate checker "
            "booleans, engineer-authored status fields, or opaque integrity "
            "identifiers as scientific evidence. Read and cross-check the "
            "source excerpts, accepted contracts, dependency definitions, "
            "definition anchors, target call sites, manifests, proof bodies, "
            "inventory, and evidence. Confirm from recorded attribution and "
            "timestamps that the 512-command execution followed the repaired "
            "proof generation. Return continue for any defect. A done "
            "reason must explicitly account for all of these facts: 64 selected "
            "targets; 54 generated and 10 exact-vstd reference-only targets; 9 "
            "derive rows; 60 proof templates spanning 40 semantic families; 64 "
            "implementation proof files and 64 completeness proof files; 128 "
            "successful baseline --no-verify obligations; 128 successful "
            "baseline actual-Verus obligations; 128 syntax-valid mutants; 128 "
            "actual-Verus mutation rejections; 512 total commands; zero "
            "target-level external bodies and zero assumes; zero failed and zero "
            "pending work. State precisely that retained dependency boundaries "
            "are narrow and tied to readable frozen source definitions, "
            "definition anchors, and target call sites; independently account "
            "for all 86 lower-level external-body helpers, all 31 uninterpreted "
            "representation helpers, and the one source-bound FromIterator "
            "type-level bridge; and state that acceptance makes no foundational "
            "end-to-end trust-freedom claim."
        ),
        "acceptance_language": (
            "The acceptance reason is matched fail-closed. If and only if the "
            "fresh inspection substantiates them, include these exact sentences: "
            "\"There are zero target-level external bodies and zero assumes.\" "
            "\"I independently inspected readable source and contract content, "
            "dependency definitions, source definitions, anchors, call sites, "
            "and representative proof bodies.\" \"The 512-command evidence is "
            "fresh execution evidence timestamped after the repaired proof "
            "generation and attributed to its recorded run.\" Otherwise return "
            "continue."
        ),
    },
    "final": {
        "request": aggregate_seal.FINAL_REVIEW_REQUEST,
        "record": aggregate_seal.FINAL_REVIEW_RECORD,
        "required_terms": aggregate_seal.FINAL_REASON_TERMS,
        "summary": (
            "Engineering submits the immutable core::result pre-final "
            "certification for a fresh final independent decision."
        ),
        "objective": (
            "Perform a fresh, independent final aggregate review of the exact "
            "immutable core::result candidate and frozen final request. Read "
            "their content and the distinct accepted implementation Reviewer "
            "handoff; independently inspect representative proof bodies, "
            "source and contract content, dependency definitions, definition "
            "anchors, target call sites, and execution timestamps. Do not trust "
            "checker booleans or opaque integrity identifiers as scientific "
            "evidence. The decision reason must explicitly account for every "
            "implementation total: 64 selected, 54 generated, 10 exact-vstd "
            "reference-only, 9 derive rows, 60 proof templates, 40 semantic "
            "families, 64 implementation and 64 completeness proof files, 128 "
            "successful baseline --no-verify obligations, 128 successful "
            "baseline actual-Verus obligations, 128 syntax-valid mutants, 128 "
            "actual-Verus mutation rejections, and 512 commands, with zero "
            "target-level external bodies, zero assumes, zero failed, and zero "
            "pending. Explicitly disposition the structural, evidence, trust, "
            "verification-run, implementation-review, and aggregate gates; "
            "require zero unresolved findings; describe dependency trust as "
            "narrow and tied to readable frozen source definitions, definition "
            "anchors, and target call sites; account for all 86 lower-level "
            "external-body helpers, all 31 uninterpreted representation helpers, "
            "and the one source-bound FromIterator type-level bridge; and make "
            "no foundational end-to-end trust-freedom claim. Return continue if "
            "any defect or unresolved finding exists."
        ),
        "acceptance_language": (
            "The acceptance reason is matched fail-closed. If and only if the "
            "fresh inspection substantiates them, include these exact sentences: "
            "\"There are zero target-level external bodies and zero assumes.\" "
            "\"I independently inspected readable source and contract content, "
            "dependency definitions, source definitions, anchors, call sites, "
            "and representative proof bodies.\" \"The 512-command evidence is "
            "fresh execution evidence timestamped after the repaired proof "
            "generation and attributed to its recorded run.\" \"The structural "
            "gate passes, the "
            "evidence gate passes, the trust gate passes, the verification-run "
            "gate is complete, the implementation review gate passes, and the "
            "aggregate gate passes with zero unresolved findings.\" Otherwise "
            "return continue."
        ),
    },
}


def _load_reviewer_components() -> tuple[Any, Any, Any, Any]:
    from argus_skill.adapters.agent_cli_backend import AgentCliBackend
    from argus_skill.life.context_packet import record_reviewed_handoff
    from argus_skill.reviewer import Reviewer, ReviewerConfig

    return AgentCliBackend, Reviewer, ReviewerConfig, record_reviewed_handoff


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_progress(path: Path, event: str, **fields: Any) -> None:
    record = {"event": event, "timestamp": time.time(), **fields}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def latest_round() -> int:
    latest = aggregate_seal.load_json(aggregate_seal.LATEST_PATH)
    handoff_path = Path(str(latest.get("handoff", {}).get("path", "")))
    require_current_handoff_root(handoff_path)
    match = re.fullmatch(
        r"round-(\d{4})(?:-engineer)?\.json", handoff_path.name
    )
    if match is None:
        raise RuntimeError(f"canonical latest handoff is malformed: {handoff_path}")
    return int(match.group(1))


def require_current_handoff_root(path: Path) -> None:
    if path.resolve().parent != aggregate_seal.HANDOFF_ROOT.resolve():
        raise RuntimeError(
            f"handoff is outside the current mission: {path.resolve()}"
        )


def next_review_round() -> int:
    candidate = latest_round() + 1
    while (
        (aggregate_seal.HANDOFF_ROOT / f"round-{candidate:04d}.json").exists()
        or (
            aggregate_seal.HANDOFF_ROOT
            / f"round-{candidate:04d}-engineer.json"
        ).exists()
    ):
        candidate += 1
    return candidate


def reviewed_artifacts(stage: str) -> dict[str, dict[str, str]]:
    if stage == "final":
        request = aggregate_seal.load_json(aggregate_seal.FINAL_REVIEW_REQUEST)
        candidate = request.get("candidate_certification")
        aggregate_seal.validate_artifact_binding(
            candidate, "final review candidate certification"
        )
        return {
            "request": aggregate_seal.artifact_binding(
                aggregate_seal.FINAL_REVIEW_REQUEST
            ),
            "candidate_certification": candidate,
        }
    return aggregate_seal.implementation_reviewed_artifacts()


def _stage_preconditions(stage: str) -> dict[str, dict[str, str]]:
    record_path = Path(STAGES[stage]["record"])
    if record_path.exists():
        existing = aggregate_seal.load_json(record_path)
        if existing.get("acceptance_eligible") is True:
            raise RuntimeError(
                f"refusing to replace accepted review record: {record_path}"
            )
    if stage == "final":
        if aggregate_seal.FINAL_DELIVERY.exists():
            raise RuntimeError("the core::result campaign already has a final delivery")
        aggregate_seal.validate_candidate_state(run_gate_checks=True)
    else:
        aggregate_seal.validate_implementation_request()
        aggregate_seal.derive_technical_gate()
    return reviewed_artifacts(stage)


def _write_terminal_protocol(
    *,
    status_path: Path,
    result_path: Path,
    progress_path: Path,
    status: dict[str, Any],
    result: dict[str, Any],
    event: str,
) -> None:
    now = time.time()
    result.setdefault("completed_at", now)
    status.update(
        {
            "state": result["state"],
            "updated_at": now,
            "completed_at": now,
            "result_path": str(result_path),
            "worker_alive": False,
        }
    )
    for field in (
        "review_status",
        "acceptance_eligible",
        "canonical_handoff",
        "error",
    ):
        if field in result:
            status[field] = result[field]
    write_json_atomic(result_path, result)
    write_json_atomic(status_path, status)
    append_progress(progress_path, event, state=result["state"])


class _ReviewRunProtocol:
    def __init__(
        self,
        *,
        stop_path: Path,
        status_path: Path,
        result_path: Path,
        progress_path: Path,
        status: dict[str, Any],
        started_at: float,
        heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        self._stop_path = stop_path
        self._status_path = status_path
        self._result_path = result_path
        self._progress_path = progress_path
        self._status = status
        self._started_at = started_at
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._last_heartbeat_at: float | None = None
        self._closed = False

    def _observe_stop_locked(self) -> bool:
        if self._stop_path.exists():
            self._stop_requested.set()
            return True
        return self._stop_requested.is_set()

    def stop_requested(self) -> bool:
        with self._lock:
            return self._observe_stop_locked()

    def interrupt_reason(self) -> str | None:
        return "supervised STOP requested" if self.stop_requested() else None

    def _heartbeat_locked(
        self,
        *,
        source: str,
        worker_idle_seconds: float | None = None,
        last_stream: str | None = None,
    ) -> None:
        monotonic_now = time.monotonic()
        if (
            self._last_heartbeat_at is not None
            and monotonic_now - self._last_heartbeat_at
            < self._heartbeat_interval_seconds
        ):
            return
        self._last_heartbeat_at = monotonic_now
        now = time.time()
        elapsed_seconds = round(now - self._started_at, 1)
        fields: dict[str, Any] = {
            "heartbeat_source": source,
            "updated_at": now,
            "worker_alive": True,
            "elapsed_seconds": elapsed_seconds,
        }
        progress_fields: dict[str, Any] = {
            "source": source,
            "worker_alive": True,
            "elapsed_seconds": elapsed_seconds,
            "stream_events": self._status["stream_events"],
        }
        if last_stream is not None:
            fields["last_stream"] = last_stream
        if worker_idle_seconds is not None:
            rounded_idle = round(worker_idle_seconds, 1)
            fields["worker_idle_seconds"] = rounded_idle
            progress_fields["worker_idle_seconds"] = rounded_idle
        self._status.update(fields)
        write_json_atomic(self._status_path, self._status)
        append_progress(
            self._progress_path,
            "heartbeat",
            **progress_fields,
        )

    def stream_event(self, stream_name: str, _line: str) -> None:
        with self._lock:
            if self._closed or self._observe_stop_locked():
                return
            self._status["stream_events"] = (
                int(self._status["stream_events"]) + 1
            )
            self._heartbeat_locked(
                source="stream",
                last_stream=stream_name,
            )

    def process_liveness(self, snapshot: Any) -> None:
        # The runner invokes this hook only after confirming its worker is alive.
        with self._lock:
            if self._closed or self._observe_stop_locked():
                return
            idle_seconds = float(getattr(snapshot, "idle_seconds", 0.0) or 0.0)
            self._heartbeat_locked(
                source="process_liveness",
                worker_idle_seconds=idle_seconds,
            )

    def write_terminal(
        self,
        *,
        result: dict[str, Any],
        event: str,
    ) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("review protocol is already terminal")
            _write_terminal_protocol(
                status_path=self._status_path,
                result_path=self._result_path,
                progress_path=self._progress_path,
                status=self._status,
                result=result,
                event=event,
            )
            self._closed = True


class _LivenessBackend:
    def __init__(
        self,
        backend: Any,
        *,
        inactivity_callback: Any,
        heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        self._backend = backend
        self._inactivity_callback = inactivity_callback
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    def run_exec(
        self,
        *,
        prompt: str,
        options: Any,
        run_label: str,
        resume_thread_id: str | None = None,
    ) -> Any:
        previous_callback = getattr(options, "inactivity_callback", None)

        def inactivity_callback(snapshot: Any) -> str | None:
            self._inactivity_callback(snapshot)
            if previous_callback is not None:
                return previous_callback(snapshot)
            return None

        requested_interval = getattr(
            options, "watchdog_soft_idle_seconds", None
        )
        effective_interval = self._heartbeat_interval_seconds
        if requested_interval is not None and float(requested_interval) > 0:
            effective_interval = min(
                effective_interval, float(requested_interval)
            )
        liveness_options = replace(
            options,
            inactivity_callback=inactivity_callback,
            watchdog_soft_idle_seconds=effective_interval,
        )
        return self._backend.run_exec(
            prompt=prompt,
            options=liveness_options,
            run_label=run_label,
            resume_thread_id=resume_thread_id,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)

    stage = STAGES[args.stage]
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    stop_path = run_dir / "STOP"
    manifest_path = run_dir / "manifest.json"
    status_path = run_dir / "status.json"
    progress_path = run_dir / "progress.jsonl"
    result_path = run_dir / "result.json"
    for path in (manifest_path, status_path, progress_path, result_path):
        if path.exists():
            raise RuntimeError(f"refusing to reuse protocol artifact: {path}")

    started_at = time.time()
    status: dict[str, Any] = {
        "schema_version": 1,
        "task_id": args.task_id,
        "stage": args.stage,
        "state": "running",
        "started_at": started_at,
        "updated_at": started_at,
        "stream_events": 0,
    }
    write_json_atomic(status_path, status)
    progress_path.touch(exist_ok=False)
    append_progress(progress_path, "run_started", task_id=args.task_id)
    protocol = _ReviewRunProtocol(
        stop_path=stop_path,
        status_path=status_path,
        result_path=result_path,
        progress_path=progress_path,
        status=status,
        started_at=started_at,
    )

    request_path = Path(stage["request"])
    route = {
        "TASK_SCOPE": "bounded",
        "TASK_STAGE_CLOSING": args.stage == "final",
        "TASK_REQUIRE_INDEPENDENT_REVIEW": True,
        "TASK_SKIP_STAGE_TRANSITION": args.stage != "final",
        "ROUTING_REQUIREMENT": "independent_review:required",
    }
    try:
        request_binding = aggregate_seal.artifact_binding(request_path)
    except (aggregate_seal.AggregateSealError, OSError) as error:
        request_binding = {
            "path": aggregate_seal.campaign_relative(request_path),
            "sha256": None,
        }
        manifest = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "objective": stage["objective"],
            "route": route,
            "request": request_binding,
            "reviewed_artifacts": {},
            "preflight_error": str(error),
            "created_at": started_at,
        }
        aggregate_seal.write_json_exclusive(manifest_path, manifest)
        result = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "state": "failed",
            "error": str(error),
            "acceptance_eligible": False,
            "started_at": started_at,
        }
        protocol.write_terminal(
            result=result,
            event="run_failed",
        )
        print(f"independent review error: {error}", file=sys.stderr)
        return 1

    if protocol.stop_requested():
        manifest = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "objective": stage["objective"],
            "route": route,
            "request": request_binding,
            "reviewed_artifacts": {},
            "created_at": started_at,
        }
        aggregate_seal.write_json_exclusive(manifest_path, manifest)
        result = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "state": "stopped",
            "error": "supervised STOP requested before Reviewer launch",
            "acceptance_eligible": False,
            "started_at": started_at,
        }
        protocol.write_terminal(
            result=result,
            event="run_stopped",
        )
        return 130

    try:
        reviewed = _stage_preconditions(args.stage)
    except (aggregate_seal.AggregateSealError, OSError, RuntimeError) as error:
        manifest = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "objective": stage["objective"],
            "route": route,
            "request": request_binding,
            "reviewed_artifacts": {},
            "preflight_error": str(error),
            "created_at": started_at,
        }
        aggregate_seal.write_json_exclusive(manifest_path, manifest)
        result = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "state": "failed",
            "error": str(error),
            "acceptance_eligible": False,
            "started_at": started_at,
        }
        protocol.write_terminal(
            result=result,
            event="run_failed",
        )
        print(f"independent review error: {error}", file=sys.stderr)
        return 1

    manifest = {
        "schema_version": 1,
        "task_id": args.task_id,
        "stage": args.stage,
        "objective": stage["objective"],
        "route": route,
        "request": request_binding,
        "reviewed_artifacts": reviewed,
        "created_at": started_at,
    }
    aggregate_seal.write_json_exclusive(manifest_path, manifest)

    try:
        (
            AgentCliBackend,
            Reviewer,
            ReviewerConfig,
            record_reviewed_handoff,
        ) = _load_reviewer_components()
        backend = _LivenessBackend(
            AgentCliBackend(
                backend="copilot",
                runner_bin="/home/chentianyu/.local/bin/copilot",
                default_interrupt_reason_provider=protocol.interrupt_reason,
                event_callback=protocol.stream_event,
            ),
            inactivity_callback=protocol.process_liveness,
        )
        reviewer = Reviewer(backend, memory_maintenance_enabled=False)
        objective = "\n".join(
            (
                "ROUTING_REQUIREMENT=independent_review:required",
                "TASK_SCOPE=bounded",
                f"TASK_STAGE_CLOSING={'true' if args.stage == 'final' else 'false'}",
                "TASK_REQUIRE_INDEPENDENT_REVIEW=true",
                f"TASK_SKIP_STAGE_TRANSITION={'false' if args.stage == 'final' else 'true'}",
                "",
                str(stage["objective"]),
                str(stage["acceptance_language"]),
                "",
                f"Begin with the exact frozen request {request_binding['path']}. "
                "Use its readable artifact paths and fresh-execution timestamps "
                "as the review provenance. Work only within "
                f"{CAMPAIGN_ROOT}. Do not modify campaign artifacts or run proof "
                "generation. Make a fresh scientific decision from the exact "
                "readable evidence. Local validators enforce artifact integrity; "
                "do not use opaque integrity identifiers as Reviewer evidence. "
                "Return done only if every required fact is explicitly stated "
                "in the reason.",
            )
        )
        decision = reviewer.evaluate(
            objective=objective,
            original_objective=objective,
            operator_messages=[
                (
                    f"Route the core::result {args.stage} gate through the "
                    "canonical independent Reviewer."
                )
            ],
            round_index=max(1, latest_round()),
            round_max=1,
            session_id=aggregate_seal.MISSION_ID,
            main_summary=str(stage["summary"]),
            main_error=None,
            config=ReviewerConfig(
                model="gpt-5.6-sol",
                reasoning_effort="max",
                skip_git_repo_check=True,
                dangerous_yolo=True,
                working_dir=str(CAMPAIGN_ROOT),
            ),
            planner_review_instruction=(
                f"This is the bounded independent {args.stage} gate. Inspect "
                "scientific validity and proof bodies, not merely file presence "
                "or checker status."
            ),
            raw_evidence=request_binding["path"],
            scope="bounded",
            checkpoint_path=str(aggregate_seal.CHECKPOINT_PATH),
            background_context=(
                "The accepted specification Reviewer belongs to a different "
                "mission and is historical input only. Record this decision as "
                "a new handoff in the current implementation mission."
            ),
            engineer_log_path=str(
                aggregate_seal.HANDOFF_ROOT.parent.parent / "events.jsonl"
            ),
        )
        if protocol.stop_requested():
            raise InterruptedError("supervised STOP requested")
        if aggregate_seal.artifact_binding(request_path) != request_binding:
            raise RuntimeError("frozen review request changed during review")
        if reviewed_artifacts(args.stage) != reviewed:
            raise RuntimeError("reviewed artifact hashes changed during review")

        coverage = aggregate_seal.reason_coverage(
            decision.reason, stage["required_terms"]
        )
        review_round = next_review_round()
        handoff_path = record_reviewed_handoff(
            mission_context_path=aggregate_seal.MISSION_PATH,
            round_index=review_round,
            engineer_summary=str(stage["summary"]),
            review=decision,
            checkpoint_path=aggregate_seal.CHECKPOINT_PATH,
        )
        if handoff_path is None:
            raise RuntimeError("Reviewer handoff was not recorded")
        handoff_path = Path(handoff_path).resolve()
        require_current_handoff_root(handoff_path)
        if handoff_path.name != f"round-{review_round:04d}.json":
            raise RuntimeError(f"Reviewer handoff path is not canonical: {handoff_path}")
        handoff_binding = {
            "path": str(handoff_path),
            "round": review_round,
            "sha256": aggregate_seal.sha256_file(handoff_path),
            "producer_role": "reviewer",
        }
        aggregate_seal.archive_canonical_handoff(
            handoff_path,
            handoff_binding["sha256"],
        )
        acceptance_eligible = (
            decision.status == "done" and all(coverage.values())
        )
        completed_at = time.time()
        review_record = {
            "schema_version": aggregate_seal.SCHEMA_VERSION,
            "artifact_role": "independent_reviewer_decision",
            "review_type": args.stage,
            "review_status": decision.status,
            "acceptance_eligible": acceptance_eligible,
            "reason": decision.reason,
            "explicit_reason_coverage": coverage,
            "route": manifest["route"],
            "request": request_binding,
            "reviewed_artifacts": reviewed,
            "canonical_handoff": handoff_binding,
            "completed_at": completed_at,
        }
        review_record_path = Path(stage["record"])
        if review_record_path.exists():
            write_json_atomic(review_record_path, review_record)
        else:
            aggregate_seal.write_json_exclusive(
                review_record_path, review_record
            )
        result = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "state": "completed",
            "route": manifest["route"],
            "review": asdict(decision),
            "explicit_reason_coverage": coverage,
            "acceptance_eligible": acceptance_eligible,
            "canonical_handoff": handoff_binding,
            "started_at": started_at,
            "completed_at": completed_at,
            "elapsed_seconds": round(completed_at - started_at, 1),
        }
        if args.stage == "final" and acceptance_eligible:
            terminal = aggregate_seal.finalize_accepted_review(
                Path(stage["record"])
            )
            result["terminal_certification"] = {
                "certification_id": terminal["certification_id"],
                "path": aggregate_seal.campaign_relative(
                    aggregate_seal.certification_path(
                        terminal["certification_id"]
                    )
                ),
            }
        protocol.write_terminal(
            result=result,
            event="run_completed",
        )
        print(
            json.dumps(
                {
                    "review_status": decision.status,
                    "acceptance_eligible": acceptance_eligible,
                    "canonical_handoff": str(handoff_path),
                },
                sort_keys=True,
            )
        )
        return 0 if acceptance_eligible else 2
    except Exception as error:
        stopped = isinstance(error, InterruptedError) or protocol.stop_requested()
        result = {
            "schema_version": 1,
            "task_id": args.task_id,
            "stage": args.stage,
            "state": "stopped" if stopped else "failed",
            "error": str(error),
            "acceptance_eligible": False,
            "started_at": started_at,
        }
        protocol.write_terminal(
            result=result,
            event="run_stopped" if stopped else "run_failed",
        )
        print(f"independent review error: {error}", file=sys.stderr)
        return 130 if stopped else 1


if __name__ == "__main__":
    raise SystemExit(main())
