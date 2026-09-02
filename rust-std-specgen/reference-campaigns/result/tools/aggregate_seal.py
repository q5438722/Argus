#!/usr/bin/env python3
"""Prepare, validate, and finalize the core::result aggregate seal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_ROOT))

import implementation  # noqa: E402
from tools import check_implementation_proofs as checker  # noqa: E402
from tools.review_provenance import implementation_review_basis  # noqa: E402


SCHEMA_VERSION = 2
PROOF_INVENTORY_ROOT = CAMPAIGN_ROOT / "proof_inventory"
ACTIVE_CERTIFICATION = (
    PROOF_INVENTORY_ROOT / "active_aggregate_certification.json"
)
CANONICAL_HANDOFF_SNAPSHOT_ROOT = (
    PROOF_INVENTORY_ROOT / "canonical_handoffs"
)
IMPLEMENTATION_REVIEW_REQUEST = (
    CAMPAIGN_ROOT / "reviews/implementation_completeness_review_request.json"
)
IMPLEMENTATION_REVIEW_RECORD = (
    CAMPAIGN_ROOT / "reviews/implementation_completeness_review.json"
)
FINAL_REVIEW_REQUEST = (
    CAMPAIGN_ROOT / "reviews/final_aggregate_review_request.json"
)
FINAL_REVIEW_RECORD = CAMPAIGN_ROOT / "reviews/final_aggregate_review.json"
FINAL_DELIVERY = PROOF_INVENTORY_ROOT / "final_delivery.json"
PRE_FINAL_VERIFICATION = (
    CAMPAIGN_ROOT / "verification/pre_final_certification.json"
)
AGGREGATE_SEAL_VERIFICATION = CAMPAIGN_ROOT / "verification/aggregate_seal.json"

HANDOFF_ROOT = Path(
    "/home/chentianyu/.argus-skill-v011-slice-conditional/"
    "projects/s-17ed5943/handoffs/e6b720a1979f"
)
MISSION_PATH = HANDOFF_ROOT / "mission.json"
CHECKPOINT_PATH = HANDOFF_ROOT / "CHECKPOINT.md"
LATEST_PATH = HANDOFF_ROOT / "latest.json"
MISSION_ID = HANDOFF_ROOT.name

TARGETS_PATH = PROOF_INVENTORY_ROOT / "targets.json"
GENERATION_SUMMARY_PATH = PROOF_INVENTORY_ROOT / "generation_summary.json"
DEPENDENCY_GRAPH_PATH = PROOF_INVENTORY_ROOT / "dependency_graph.json"
VERIFICATION_RUN_PATH = PROOF_INVENTORY_ROOT / "verification_run.json"
VERIFIED_TARGET_STATUS_PATH = (
    PROOF_INVENTORY_ROOT / "verified_target_status.json"
)
TRUST_AUDIT_PATH = CAMPAIGN_ROOT / "audits/trust_boundary_audit.json"
IMPLEMENTATION_CHECK_PATH = (
    CAMPAIGN_ROOT / "verification/implementation_proof_check.json"
)
AGGREGATE_COVERAGE_PATH = PROOF_INVENTORY_ROOT / "aggregate_coverage.json"
POST_BATCH_AUDITS = {
    "source_hash_fidelity": CAMPAIGN_ROOT / "audits/source_hash_fidelity.json",
    "artifact_integrity": CAMPAIGN_ROOT / "audits/artifact_integrity.json",
    "literal_trust_boundary": (
        CAMPAIGN_ROOT / "audits/literal_trust_boundary_audit.json"
    ),
    "semantic_trust_boundary": (
        CAMPAIGN_ROOT / "audits/semantic_trust_boundary_audit.json"
    ),
    "mutation": CAMPAIGN_ROOT / "audits/mutation_audit.json",
}
PROOF_STAGE_AUTHORIZATION = CAMPAIGN_ROOT / "proof_stage/authorization.json"
ACCEPTED_SPECIFICATION = CAMPAIGN_ROOT / "specs/all_result_specs.json"
ACCEPTED_SPECIFICATION_MANIFEST = (
    CAMPAIGN_ROOT / "specs/specification_package_manifest.json"
)

EXPECTED_COUNTS = {
    "selected_targets": 64,
    "generated_targets": 54,
    "exact_vstd_reference_only_targets": 10,
    "derive_expansion_rows": 9,
    "distinct_proof_templates": 60,
    "distinct_semantic_families": 40,
    "implementation_files": 64,
    "completeness_files": 64,
    "baseline_no_verify_obligations": 128,
    "baseline_actual_verus_obligations": 128,
    "syntax_valid_mutants": 128,
    "actual_verus_mutation_rejections": 128,
    "total_commands": 512,
    "target_level_external_bodies": 0,
    "completeness_external_bodies": 0,
    "assume_statements": 0,
    "failed": 0,
    "pending": 0,
}

TRUST_STATEMENT = (
    "Every one of the 86 lower-level external-body helpers and 31 "
    "uninterpreted representation helpers is individually enumerated against "
    "readable frozen source definitions, definition anchors, and target call "
    "sites. The FromIterator item equality is retained by one source-bound "
    "type-level bridge. This makes no foundational end-to-end trust-freedom "
    "claim."
)


def nearby_reason_pattern(left: str, right: str, distance: int = 140) -> str:
    between = rf"[\s\S]{{0,{distance}}}"
    return rf"(?:{left}{between}{right}|{right}{between}{left})"


IMPLEMENTATION_REASON_TERMS = (
    (nearby_reason_pattern(r"\b64\b", r"\bselected targets?\b"), "64 selected targets"),
    (nearby_reason_pattern(r"\b54\b", r"\bgenerated\b"), "54 generated targets"),
    (
        nearby_reason_pattern(r"\b10\b", r"\bexact[- ]vstd\b"),
        "10 exact-vstd reference-only targets",
    ),
    (nearby_reason_pattern(r"\b9\b", r"\bderive\b"), "9 derive rows"),
    (nearby_reason_pattern(r"\b60\b", r"\bproof templates?\b"), "60 proof templates"),
    (
        nearby_reason_pattern(r"\b40\b", r"\bsemantic families?\b"),
        "40 semantic families",
    ),
    (
        nearby_reason_pattern(r"\b64\b", r"\bimplementation (?:proof )?files?\b"),
        "64 implementation files",
    ),
    (
        nearby_reason_pattern(r"\b64\b", r"\bcompleteness (?:proof )?files?\b"),
        "64 completeness files",
    ),
    (
        nearby_reason_pattern(
            r"\b128\b", r"\bbaseline\b[\s\S]{0,40}\bno[- ]verify\b"
        ),
        "128 baseline no-verify obligations",
    ),
    (
        nearby_reason_pattern(
            r"\b128\b", r"\bbaseline\b[\s\S]{0,40}\bactual[- ]verus\b"
        ),
        "128 baseline actual-Verus obligations",
    ),
    (
        nearby_reason_pattern(r"\b128\b", r"\bsyntax[- ]valid mutants?\b"),
        "128 syntax-valid mutants",
    ),
    (
        nearby_reason_pattern(
            r"\b128\b", r"\bactual[- ]verus\b[\s\S]{0,40}\bmutation rejections?\b"
        ),
        "128 actual-Verus mutation rejections",
    ),
    (nearby_reason_pattern(r"\b512\b", r"\bcommands?\b"), "512 total commands"),
    (
        r"(?:\b(?:0|zero|no)\b[\s\S]{0,60}\btarget[- ]level external bodies?\b"
        r"|\btarget[- ]level external bodies?\b[\s\S]{0,60}\b(?:0|zero|none)\b)",
        "zero target-level external bodies",
    ),
    (
        r"(?:\b(?:0|zero|no)\b[\s\S]{0,60}\bassumes?\b"
        r"|\bassumes?\b[\s\S]{0,60}\b(?:0|zero|none)\b)",
        "zero assumes",
    ),
    (
        r"\breadable\b[\s\S]{0,80}\bsource\b[\s\S]{0,100}\bcontract\b"
        r"[\s\S]{0,120}\bdependenc(?:y|ies)\b",
        "readable source contract dependencies",
    ),
    (
        r"\brepresentative\b[\s\S]{0,80}\bproof bodies?\b",
        "representative proof bodies",
    ),
    (
        nearby_reason_pattern(
            r"\bnarrow(?:ly)?\b",
            r"\b(?:trust|dependenc|boundar)",
            distance=100,
        ),
        "narrow trust boundaries",
    ),
    (
        r"\bsource definitions?\b[\s\S]{0,120}\banchors?\b"
        r"[\s\S]{0,120}\bcall sites?\b",
        "source definitions anchors and call sites",
    ),
    (
        r"\bfresh\b[\s\S]{0,100}\bexecution\b[\s\S]{0,100}"
        r"\btimestamp(?:ed|s)?\b",
        "fresh timestamped execution evidence",
    ),
    (
        nearby_reason_pattern(
            r"\b86\b", r"\blower[- ]level external[- ]body helpers?\b"
        ),
        "86 lower-level external-body helpers",
    ),
    (
        nearby_reason_pattern(
            r"\b31\b", r"\buninterpreted (?:representation )?helpers?\b"
        ),
        "31 uninterpreted helpers",
    ),
    (
        r"\bFromIterator\b[\s\S]{0,120}\btype[- ]level bridge\b",
        "FromIterator type-level bridge",
    ),
    (
        r"\b(?:no|without|not)\b[\s\S]{0,80}\bfoundational\b"
        r"[\s\S]{0,60}\btrust(?:[- ]freedom)?\b",
        "no foundational trust-freedom claim",
    ),
    (
        nearby_reason_pattern(r"\b(?:0|zero|no)\b", r"\bfailed\b", 60),
        "zero failed",
    ),
    (
        nearby_reason_pattern(r"\b(?:0|zero|no)\b", r"\bpending\b", 60),
        "zero pending",
    ),
)

FINAL_REASON_TERMS = IMPLEMENTATION_REASON_TERMS + (
    (
        r"\bstructural\b[\s\S]{0,100}\b(?:pass(?:es|ed)?|accept(?:s|ed)?)\b",
        "structural gate",
    ),
    (
        r"\bevidence\b[\s\S]{0,100}\b(?:pass(?:es|ed)?|accept(?:s|ed)?)\b",
        "evidence gate",
    ),
    (
        r"\btrust\b[\s\S]{0,100}\b(?:pass(?:es|ed)?|accept(?:s|ed)?)\b",
        "trust gate",
    ),
    (
        r"\bverification[- ]run\b[\s\S]{0,100}"
        r"\b(?:pass(?:es|ed)?|complete|accept(?:s|ed)?)\b",
        "verification-run gate",
    ),
    (
        r"\bimplementation review\b[\s\S]{0,100}"
        r"\b(?:pass(?:es|ed)?|accept(?:s|ed)?)\b",
        "implementation-review gate",
    ),
    (
        r"\baggregate\b[\s\S]{0,100}\b(?:pass(?:es|ed)?|accept(?:s|ed)?)\b",
        "aggregate gate",
    ),
    (
        r"(?:\b(?:0|zero|no)\b[\s\S]{0,50}\bunresolved findings?\b"
        r"|\bunresolved findings?\b[\s\S]{0,50}\b(?:none|0|zero)\b)",
        "zero unresolved findings",
    ),
)


class AggregateSealError(RuntimeError):
    """Aggregate evidence cannot safely advance to the requested state."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp(value: Any, label: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError as error:
            raise AggregateSealError(f"{label} timestamp is invalid") from error
    raise AggregateSealError(f"{label} timestamp is missing")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AggregateSealError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise AggregateSealError(f"expected a JSON object in {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    """Publish immutable JSON without replacing an existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    )
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise AggregateSealError(
                f"refusing to overwrite immutable artifact: {path}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def write_bytes_exclusive(path: Path, value: bytes) -> None:
    """Publish immutable bytes without replacing an existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    )
    try:
        with temporary.open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise AggregateSealError(
                f"refusing to overwrite immutable artifact: {path}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AggregateSealError(message)


def require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise AggregateSealError(
            f"{label} mismatch: expected {expected!r}, found {actual!r}"
        )


def campaign_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(CAMPAIGN_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise AggregateSealError(f"path is outside the campaign: {path}") from error


def artifact_binding(path: Path) -> dict[str, str]:
    require(path.is_file(), f"artifact is missing: {path}")
    return {"path": campaign_relative(path), "sha256": sha256_file(path)}


def canonical_handoff_snapshot_path(expected_hash: str) -> Path:
    require(
        re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None,
        "canonical handoff snapshot SHA-256 is invalid",
    )
    return CANONICAL_HANDOFF_SNAPSHOT_ROOT / f"{expected_hash}.json"


def archive_canonical_handoff(path: Path, expected_hash: str) -> Path:
    require(path.is_file(), f"canonical handoff is missing: {path}")
    require_equal(
        "canonical handoff archive source SHA-256",
        sha256_file(path),
        expected_hash,
    )
    snapshot = canonical_handoff_snapshot_path(expected_hash)
    if snapshot.exists():
        require_equal(
            "canonical handoff snapshot SHA-256",
            sha256_file(snapshot),
            expected_hash,
        )
        return snapshot
    write_bytes_exclusive(snapshot, path.read_bytes())
    require_equal(
        "canonical handoff snapshot SHA-256",
        sha256_file(snapshot),
        expected_hash,
    )
    return snapshot


def validate_artifact_binding(
    record: dict[str, Any], label: str, *, expected_path: Path | None = None
) -> Path:
    require(isinstance(record, dict), f"{label} binding is not an object")
    relative = Path(str(record.get("path", "")))
    require(
        bool(str(relative)) and not relative.is_absolute(),
        f"{label} path must be campaign-relative",
    )
    path = (CAMPAIGN_ROOT / relative).resolve()
    campaign_relative(path)
    if expected_path is not None:
        require_equal(f"{label} path", path, expected_path.resolve())
    require(path.is_file(), f"{label} is missing: {path}")
    require_equal(f"{label} SHA-256", record.get("sha256"), sha256_file(path))
    return path


def build_pre_final_verification_projection(
    candidate_path: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    require_equal(
        "pre-final projection source status",
        candidate.get("status"),
        "implementation_reviewed_pending_final_review",
    )
    require_equal(
        "pre-final projection technical gate",
        candidate.get("technical_gate"),
        "pass",
    )
    require_equal(
        "pre-final projection counts",
        candidate.get("counts"),
        EXPECTED_COUNTS,
    )
    implementation_review = candidate.get("implementation_review", {})
    require(
        isinstance(implementation_review, dict)
        and implementation_review.get("review_status") == "done"
        and implementation_review.get("acceptance_eligible") is True,
        "pre-final projection source lacks accepted implementation review",
    )
    gate_bindings = candidate.get("gate_bindings", {})
    proof_inventory = (
        gate_bindings.get("proof_inventory", {})
        if isinstance(gate_bindings, dict)
        else {}
    )
    require(
        isinstance(proof_inventory, dict)
        and isinstance(proof_inventory.get("sha256"), str),
        "pre-final projection source lacks proof inventory binding",
    )
    timestamp(candidate.get("created_at_utc"), "pre-final projection source")
    return {
        "schema_version": SCHEMA_VERSION,
        "projection_kind": "canonical_pre_final_certification",
        "canonical_candidate": artifact_binding(candidate_path),
        "created_at_utc": candidate["created_at_utc"],
        "proof_inventory_sha256": proof_inventory["sha256"],
        "all_target_commands_complete": True,
        "independent_review_complete": True,
        "final_certified": False,
        "status": candidate["status"],
    }


def build_aggregate_seal_verification_projection(
    delivery_path: Path,
    delivery: dict[str, Any],
) -> dict[str, Any]:
    require_equal(
        "aggregate projection delivery status",
        delivery.get("status"),
        "accepted",
    )
    require_equal(
        "aggregate projection counts",
        delivery.get("counts"),
        EXPECTED_COUNTS,
    )
    require_equal(
        "aggregate projection unresolved findings",
        delivery.get("unresolved_findings"),
        [],
    )
    for label in ("implementation_review", "final_review"):
        review = delivery.get(label, {})
        require(
            isinstance(review, dict)
            and review.get("review_status") == "done"
            and review.get("acceptance_eligible") is True,
            f"aggregate projection source lacks accepted {label.replace('_', ' ')}",
        )
    certification = delivery.get("certification", {})
    require(
        isinstance(certification, dict),
        "aggregate projection source lacks certification binding",
    )
    timestamp(delivery.get("created_at_utc"), "aggregate projection source")
    return {
        "schema_version": SCHEMA_VERSION,
        "projection_kind": "canonical_final_delivery",
        "final_delivery": artifact_binding(delivery_path),
        "certification": certification,
        "created_at_utc": delivery["created_at_utc"],
        "delivery_status": delivery["status"],
        "structural_and_evidence_complete": True,
        "independent_review_complete": True,
        "final_certified": True,
        "errors": [],
        "status": "campaign_complete",
    }


def validate_pre_final_verification_projection(
    candidate_path: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    expected = build_pre_final_verification_projection(
        candidate_path,
        candidate,
    )
    projection = load_json(PRE_FINAL_VERIFICATION)
    require_equal("pre-final verification projection", projection, expected)
    return projection


def validate_aggregate_seal_verification_projection(
    delivery_path: Path,
    delivery: dict[str, Any],
) -> dict[str, Any]:
    expected = build_aggregate_seal_verification_projection(
        delivery_path,
        delivery,
    )
    projection = load_json(AGGREGATE_SEAL_VERIFICATION)
    require_equal("aggregate seal verification projection", projection, expected)
    return projection


def reason_coverage(
    reason: str, required_terms: Sequence[tuple[str, str]]
) -> dict[str, bool]:
    return {
        label: bool(re.search(pattern, reason, re.IGNORECASE))
        for pattern, label in required_terms
    }


def _review_request_created_at(request: dict[str, Any], label: str) -> float:
    return timestamp(
        request.get("created_at_utc", request.get("created_at")),
        f"{label} request",
    )


def canonical_review_binding(
    raw_binding: dict[str, Any],
    *,
    required_terms: Sequence[tuple[str, str]],
    request_created_at: float,
    label: str,
) -> dict[str, Any]:
    require(isinstance(raw_binding, dict), f"{label} has no canonical handoff")
    raw_path = Path(str(raw_binding.get("path", "")))
    require(raw_path.is_absolute(), f"{label} handoff path must be absolute")
    path = raw_path.resolve()
    require_equal(f"{label} handoff directory", path.parent, HANDOFF_ROOT.resolve())
    match = re.fullmatch(r"round-(\d{4})\.json", path.name)
    require(match is not None, f"{label} handoff filename is not canonical")
    review_round = int(match.group(1))
    try:
        recorded_round = int(
            raw_binding.get("round", raw_binding.get("review_round"))
        )
    except (TypeError, ValueError) as error:
        raise AggregateSealError(f"{label} review round is invalid") from error
    require_equal(f"{label} review round", recorded_round, review_round)
    require(path.is_file(), f"{label} handoff is missing: {path}")
    expected_hash = str(raw_binding.get("sha256", ""))
    require(
        re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None,
        f"{label} handoff SHA-256 is invalid",
    )
    handoff_source = path
    if sha256_file(path) != expected_hash:
        handoff_source = canonical_handoff_snapshot_path(expected_hash)
        require(
            handoff_source.is_file(),
            f"{label} handoff was superseded without a canonical snapshot",
        )
        require_equal(
            f"{label} handoff snapshot SHA-256",
            sha256_file(handoff_source),
            expected_hash,
        )

    handoff = load_json(handoff_source)
    require_equal(f"{label} handoff kind", handoff.get("kind"), "round_reviewed_handoff")
    require_equal(f"{label} mission id", handoff.get("mission_id"), MISSION_ID)
    require_equal(
        f"{label} mission context",
        Path(str(handoff.get("mission_context", ""))).resolve(),
        MISSION_PATH.resolve(),
    )
    require_equal(f"{label} producer role", handoff.get("producer_role"), "reviewer")
    require_equal(f"{label} handoff round", handoff.get("round"), review_round)
    require_equal(
        f"{label} checkpoint",
        Path(str(handoff.get("checkpoint", {}).get("path", ""))).resolve(),
        CHECKPOINT_PATH.resolve(),
    )
    review = handoff.get("review")
    require(isinstance(review, dict), f"{label} handoff has no review object")
    require_equal(f"{label} review status", review.get("status"), "done")
    reason = str(review.get("reason", ""))
    coverage = reason_coverage(reason, required_terms)
    missing = [name for name, present in coverage.items() if not present]
    require(not missing, f"{label} reason lacks: {', '.join(missing)}")
    created_at = timestamp(handoff.get("created_at"), f"{label} handoff")
    require(
        created_at >= request_created_at,
        f"{label} handoff predates its frozen request",
    )
    require_equal(
        f"{label} handoff post-read SHA-256",
        sha256_file(handoff_source),
        expected_hash,
    )
    return {
        "path": str(path),
        "sha256": expected_hash,
        "round": review_round,
        "producer_role": "reviewer",
        "created_at": created_at,
        "reason": reason,
        "explicit_reason_coverage": coverage,
    }


def validate_implementation_request() -> tuple[dict[str, Any], dict[str, str]]:
    request = load_json(IMPLEMENTATION_REVIEW_REQUEST)
    require_equal(
        "implementation request status",
        request.get("status"),
        "awaiting_independent_review",
    )
    require(
        request.get("acceptance_claim") is False,
        "implementation request must not claim acceptance",
    )
    require_equal(
        "implementation request readable review basis",
        request.get("review_basis"),
        implementation_review_basis(CAMPAIGN_ROOT),
    )
    review_basis = request.get("review_basis", {})
    require(
        isinstance(review_basis, dict),
        "implementation request review basis is not an object",
    )
    fresh_execution = review_basis.get("fresh_execution", {})
    require(
        isinstance(fresh_execution, dict),
        "implementation request fresh execution is not an object",
    )
    require_equal(
        "implementation request execution state",
        fresh_execution.get("state"),
        "completed",
    )
    require_equal(
        "implementation request execution commands",
        fresh_execution.get("commands_recorded"),
        EXPECTED_COUNTS["total_commands"],
    )
    require_equal(
        "implementation request mutation rejections",
        fresh_execution.get("mutation_rejections"),
        EXPECTED_COUNTS["actual_verus_mutation_rejections"],
    )
    generation_at = timestamp(
        fresh_execution.get("proof_generation_at_utc"),
        "implementation request proof generation",
    )
    verification_at = timestamp(
        fresh_execution.get("verification_bound_at_utc"),
        "implementation request verification binding",
    )
    require(
        verification_at >= generation_at,
        "implementation review evidence predates proof generation",
    )
    require(
        _review_request_created_at(request, "implementation") >= verification_at,
        "implementation request predates fresh execution evidence",
    )
    return request, artifact_binding(IMPLEMENTATION_REVIEW_REQUEST)


def implementation_reviewed_artifacts() -> dict[str, dict[str, str]]:
    """Return the exact technical roots submitted to implementation review."""
    return {
        "request": artifact_binding(IMPLEMENTATION_REVIEW_REQUEST),
        "proof_inventory": artifact_binding(TARGETS_PATH),
        "generation_summary": artifact_binding(GENERATION_SUMMARY_PATH),
        "dependency_graph": artifact_binding(DEPENDENCY_GRAPH_PATH),
        "verification_run": artifact_binding(VERIFICATION_RUN_PATH),
        "verified_target_status": artifact_binding(
            VERIFIED_TARGET_STATUS_PATH
        ),
        "trust_audit": artifact_binding(TRUST_AUDIT_PATH),
        "implementation_check": artifact_binding(IMPLEMENTATION_CHECK_PATH),
        "aggregate_coverage": artifact_binding(AGGREGATE_COVERAGE_PATH),
        **{
            f"{name}_audit": artifact_binding(path)
            for name, path in POST_BATCH_AUDITS.items()
        },
        "proof_stage_authorization": artifact_binding(
            PROOF_STAGE_AUTHORIZATION
        ),
        "accepted_specification": artifact_binding(ACCEPTED_SPECIFICATION),
        "accepted_specification_manifest": artifact_binding(
            ACCEPTED_SPECIFICATION_MANIFEST
        ),
        "implementation_checker": artifact_binding(
            Path(implementation.__file__)
        ),
        "evidence_trust_checker": artifact_binding(Path(checker.__file__)),
    }


def stage_implementation_request() -> dict[str, Any]:
    if IMPLEMENTATION_REVIEW_RECORD.exists():
        record = load_json(IMPLEMENTATION_REVIEW_RECORD)
        require(
            record.get("acceptance_eligible") is not True,
            "refusing to replace the request after implementation acceptance",
        )
    technical = derive_technical_gate()
    request = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "scope": (
            "64 core::result proof obligations, 512 commands and mutation "
            "evidence"
        ),
        "review_basis": implementation_review_basis(CAMPAIGN_ROOT),
        "status": "awaiting_independent_review",
        "acceptance_claim": False,
    }
    write_json_atomic(IMPLEMENTATION_REVIEW_REQUEST, request)
    validate_implementation_request()
    return {
        "status": request["status"],
        "technical_gate": technical["status"],
    }


def _validate_implementation_review_record(
    record: dict[str, Any],
    *,
    request: dict[str, Any],
    request_binding: dict[str, str],
    acceptance_eligible: bool,
    require_recorded_coverage: bool,
) -> dict[str, Any]:
    require_equal(
        "implementation review artifact role",
        record.get("artifact_role"),
        "independent_reviewer_decision",
    )
    require_equal("implementation review type", record.get("review_type"), "implementation")
    require_equal("implementation review status", record.get("review_status"), "done")
    if acceptance_eligible:
        require(
            record.get("acceptance_eligible") is True,
            "implementation review is not acceptance-eligible",
        )
    else:
        require(
            record.get("acceptance_eligible") is False,
            "implementation review is not a non-accepted done decision",
        )
    require_equal(
        "implementation review route",
        record.get("route"),
        {
            "TASK_SCOPE": "bounded",
            "TASK_STAGE_CLOSING": False,
            "TASK_REQUIRE_INDEPENDENT_REVIEW": True,
            "TASK_SKIP_STAGE_TRANSITION": True,
            "ROUTING_REQUIREMENT": "independent_review:required",
        },
    )
    require_equal("implementation review request", record.get("request"), request_binding)
    expected_artifacts = implementation_reviewed_artifacts()
    require_equal(
        "implementation reviewed artifact bindings",
        record.get("reviewed_artifacts"),
        expected_artifacts,
    )
    handoff = canonical_review_binding(
        record.get("canonical_handoff", {}),
        required_terms=IMPLEMENTATION_REASON_TERMS,
        request_created_at=_review_request_created_at(request, "implementation"),
        label="implementation review",
    )
    require_equal("implementation review reason", record.get("reason"), handoff["reason"])
    if require_recorded_coverage:
        require_equal(
            "implementation review reason coverage",
            record.get("explicit_reason_coverage"),
            handoff["explicit_reason_coverage"],
        )
    require(
        timestamp(record.get("completed_at"), "implementation review record")
        >= handoff["created_at"],
        "implementation review record predates its canonical handoff",
    )
    return handoff


def accepted_implementation_review() -> dict[str, Any]:
    request, request_binding = validate_implementation_request()
    require(
        IMPLEMENTATION_REVIEW_RECORD.is_file(),
        "accepted implementation review record is missing",
    )
    record = load_json(IMPLEMENTATION_REVIEW_RECORD)
    handoff = _validate_implementation_review_record(
        record,
        request=request,
        request_binding=request_binding,
        acceptance_eligible=True,
        require_recorded_coverage=True,
    )
    return {
        **record,
        "canonical_handoff": {
            key: handoff[key]
            for key in ("path", "sha256", "round", "producer_role")
        },
    }


def reconcile_implementation_review() -> dict[str, Any]:
    request, request_binding = validate_implementation_request()
    require(
        IMPLEMENTATION_REVIEW_RECORD.is_file(),
        "implementation review record is missing",
    )
    record = load_json(IMPLEMENTATION_REVIEW_RECORD)
    handoff = _validate_implementation_review_record(
        record,
        request=request,
        request_binding=request_binding,
        acceptance_eligible=False,
        require_recorded_coverage=False,
    )
    coverage = handoff["explicit_reason_coverage"]
    require(
        coverage.get("narrow trust boundaries") is True,
        "canonical implementation review lacks narrow trust-boundary coverage",
    )
    previous_coverage = dict(coverage)
    previous_coverage["narrow trust boundaries"] = False
    require_equal(
        "reconcilable implementation review reason coverage",
        record.get("explicit_reason_coverage"),
        previous_coverage,
    )
    reconciled = {
        **record,
        "acceptance_eligible": True,
        "explicit_reason_coverage": coverage,
    }
    _validate_implementation_review_record(
        reconciled,
        request=request,
        request_binding=request_binding,
        acceptance_eligible=True,
        require_recorded_coverage=True,
    )
    write_json_atomic(IMPLEMENTATION_REVIEW_RECORD, reconciled)
    return {"status": "implementation_review_accepted"}


def _inventory_counts(
    inventory: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, int]:
    targets = inventory.get("targets")
    require(isinstance(targets, list), "proof inventory targets are missing")
    target_dirs = [
        CAMPAIGN_ROOT / "proof_harnesses" / str(target.get("directory", ""))
        for target in targets
    ]
    manifest_rows = [
        load_json(path / "manifest.json") for path in target_dirs
    ]
    per_command = evidence.get("per_command_counts", {})
    return {
        "selected_targets": len(targets),
        "generated_targets": sum(
            target.get("disposition") == "generated" for target in targets
        ),
        "exact_vstd_reference_only_targets": sum(
            target.get("disposition") == "exact_vstd" for target in targets
        ),
        "derive_expansion_rows": sum(
            row.get("source", {}).get("kind") == "rustc_derive_expansion"
            for row in manifest_rows
        ),
        "distinct_proof_templates": len(
            {str(target.get("proof_template_id", "")) for target in targets}
        ),
        "distinct_semantic_families": len(
            {str(target.get("semantic_family", "")) for target in targets}
        ),
        "implementation_files": sum(
            (path / "implementation_proof.rs").is_file() for path in target_dirs
        ),
        "completeness_files": sum(
            (path / "completeness_proof.rs").is_file() for path in target_dirs
        ),
        "baseline_no_verify_obligations": sum(
            int(per_command.get(name, 0))
            for name in ("implementation_no_verify", "completeness_no_verify")
        ),
        "baseline_actual_verus_obligations": sum(
            int(per_command.get(name, 0))
            for name in ("implementation_actual", "completeness_actual")
        ),
        "syntax_valid_mutants": sum(
            int(per_command.get(name, 0))
            for name in (
                "implementation_mutant_no_verify",
                "completeness_mutant_no_verify",
            )
        ),
        "actual_verus_mutation_rejections": sum(
            int(per_command.get(name, 0))
            for name in (
                "implementation_mutant_actual",
                "completeness_mutant_actual",
            )
        ),
    }


def derive_technical_gate() -> dict[str, Any]:
    structural_errors = list(
        implementation.structural_errors(require_evidence=True)
    )
    trust = checker.trust_accounting()
    evidence = checker.evidence_accounting()
    evidence_errors = checker.evidence_errors(evidence)
    errors = structural_errors + evidence_errors

    trust_expectations = {
        "literal_target_external_bodies": 0,
        "literal_completeness_external_bodies": 0,
        "literal_assume_statements": 0,
        "public_implementation_targets": 64,
        "literal_lower_level_external_bodies": 86,
    }
    for field, expected in trust_expectations.items():
        if trust.get(field) != expected:
            errors.append(
                f"trust {field}={trust.get(field)!r} expected={expected!r}"
            )
    if not trust.get("narrow_external_boundaries"):
        errors.append("narrow dependency trust boundaries are not accounted")
    if sum(trust.get("uninterpreted_model_boundaries", {}).values()) != 31:
        errors.append(
            "the 31 uninterpreted helper occurrences are not fully accounted"
        )
    if sum(trust.get("associated_type_bridges", {}).values()) != 1:
        errors.append(
            "the FromIterator type-level bridge is not uniquely accounted"
        )
    if trust.get("unbound_local_helpers") != []:
        errors.append("at least one local trust helper is unbound")

    inventory = load_json(TARGETS_PATH)
    counts = _inventory_counts(inventory, evidence)
    counts.update(
        {
            "total_commands": int(evidence.get("commands_recorded", -1)),
            "target_level_external_bodies": int(
                trust.get("literal_target_external_bodies", -1)
            ),
            "completeness_external_bodies": int(
                trust.get("literal_completeness_external_bodies", -1)
            ),
            "assume_statements": int(
                trust.get("literal_assume_statements", -1)
            ),
            "failed": max(
                0,
                int(evidence.get("commands_recorded", 0))
                - int(evidence.get("expectations_met", 0)),
            ),
            "pending": max(
                0,
                EXPECTED_COUNTS["total_commands"]
                - int(evidence.get("commands_recorded", 0)),
            ),
        }
    )
    if counts != EXPECTED_COUNTS:
        errors.append(
            f"aggregate counts mismatch: expected {EXPECTED_COUNTS!r}, "
            f"found {counts!r}"
        )

    generation = load_json(GENERATION_SUMMARY_PATH)
    require_equal(
        "generation target count",
        generation.get("target_count"),
        EXPECTED_COUNTS["selected_targets"],
    )
    require_equal(
        "generation generated count",
        generation.get("generated"),
        EXPECTED_COUNTS["generated_targets"],
    )
    require_equal(
        "generation exact-vstd count",
        generation.get("exact_vstd"),
        EXPECTED_COUNTS["exact_vstd_reference_only_targets"],
    )
    require_equal(
        "generation derive count",
        generation.get("derive_bound"),
        EXPECTED_COUNTS["derive_expansion_rows"],
    )
    require_equal(
        "generation proof template count",
        generation.get("distinct_proof_templates"),
        EXPECTED_COUNTS["distinct_proof_templates"],
    )
    require_equal(
        "generation semantic family count",
        generation.get("distinct_semantic_families"),
        EXPECTED_COUNTS["distinct_semantic_families"],
    )
    trust_audit = load_json(TRUST_AUDIT_PATH)
    implementation_check = load_json(IMPLEMENTATION_CHECK_PATH)
    require_equal(
        "implementation check status",
        implementation_check.get("status"),
        "pass",
    )
    require_equal(
        "implementation check mode",
        implementation_check.get("mode"),
        "full",
    )
    require_equal(
        "implementation check error count",
        implementation_check.get("error_count"),
        0,
    )
    require_equal(
        "trust audit target external bodies",
        trust_audit.get("literal_target_external_bodies"),
        0,
    )
    require_equal(
        "trust audit completeness external theorems",
        trust_audit.get("literal_completeness_external_theorems"),
        0,
    )
    require_equal(
        "trust audit lower-level external helpers",
        trust_audit.get("lower_level_external_body_helpers"),
        86,
    )
    require_equal(
        "trust audit uninterpreted helpers",
        sum(
            trust_audit.get(
                "uninterpreted_model_boundaries", {}
            ).values()
        ),
        31,
    )
    require_equal(
        "trust audit associated-type bridges",
        sum(trust_audit.get("associated_type_bridges", {}).values()),
        1,
    )
    require_equal(
        "trust audit unbound helpers",
        trust_audit.get("unbound_local_helpers"),
        [],
    )
    require(
        isinstance(trust_audit.get("narrow_boundaries"), list)
        and bool(trust_audit["narrow_boundaries"]),
        "trust audit has no narrow dependency boundaries",
    )
    require_equal("trust audit status", trust_audit.get("status"), "pass")
    for name, path in POST_BATCH_AUDITS.items():
        audit = load_json(path)
        require_equal(f"{name} audit status", audit.get("status"), "pass")
    aggregate_coverage = load_json(AGGREGATE_COVERAGE_PATH)
    require_equal(
        "aggregate coverage status",
        aggregate_coverage.get("status"),
        "technical_gates_passed_pending_independent_review",
    )
    require(
        aggregate_coverage.get("acceptance_claim") is False
        and aggregate_coverage.get("independent_review_complete") is False,
        "pre-review aggregate coverage makes an acceptance claim",
    )
    run = load_json(VERIFICATION_RUN_PATH)
    verified_status = load_json(VERIFIED_TARGET_STATUS_PATH)
    require_equal("verification run state", run.get("state"), "completed")
    require_equal(
        "verification run commands",
        run.get("commands_recorded"),
        EXPECTED_COUNTS["total_commands"],
    )
    require_equal(
        "verification run mutation rejections",
        run.get("mutation_rejections"),
        EXPECTED_COUNTS["actual_verus_mutation_rejections"],
    )
    require(
        run.get("evidence_current") is True,
        "verification run evidence is not current",
    )
    require_equal(
        "verified-target overlay status",
        verified_status.get("status"),
        "pass",
    )
    require_equal(
        "verified-target overlay count",
        verified_status.get("target_count"),
        EXPECTED_COUNTS["selected_targets"],
    )
    require_equal("verified-target failed count", verified_status.get("failed"), 0)
    require_equal("verified-target pending count", verified_status.get("pending"), 0)
    require_equal(
        "verified-target base inventory",
        verified_status.get("base_inventory"),
        {
            "path": campaign_relative(TARGETS_PATH),
            "sha256": sha256_file(TARGETS_PATH),
            "size": TARGETS_PATH.stat().st_size,
        },
    )
    require(not errors, "technical gate failed: " + "; ".join(errors[:20]))

    binding_paths = {
        "proof_inventory": TARGETS_PATH,
        "generation_summary": GENERATION_SUMMARY_PATH,
        "dependency_graph": DEPENDENCY_GRAPH_PATH,
        "verification_run": VERIFICATION_RUN_PATH,
        "verified_target_status": VERIFIED_TARGET_STATUS_PATH,
        "trust_audit": TRUST_AUDIT_PATH,
        "implementation_check": IMPLEMENTATION_CHECK_PATH,
        "aggregate_coverage": AGGREGATE_COVERAGE_PATH,
        **{
            f"{name}_audit": path
            for name, path in POST_BATCH_AUDITS.items()
        },
        "proof_stage_authorization": PROOF_STAGE_AUTHORIZATION,
        "accepted_specification": ACCEPTED_SPECIFICATION,
        "accepted_specification_manifest": ACCEPTED_SPECIFICATION_MANIFEST,
        "implementation_checker": Path(implementation.__file__),
        "evidence_trust_checker": Path(checker.__file__),
    }
    return {
        "status": "pass",
        "counts": counts,
        "trust": {
            "lower_level_external_body_helpers": trust[
                "literal_lower_level_external_bodies"
            ],
            "narrow_external_boundaries": trust["narrow_external_boundaries"],
            "uninterpreted_model_boundaries": trust[
                "uninterpreted_model_boundaries"
            ],
            "associated_type_bridges": trust["associated_type_bridges"],
            "unbound_local_helpers": trust["unbound_local_helpers"],
            "foundational_end_to_end_trust_free": False,
            "statement": TRUST_STATEMENT,
        },
        "run": {
            "run_id": run.get("run_id"),
            "run_dir": run.get("run_dir"),
            "state": run.get("state"),
        },
        "gate_bindings": {
            name: artifact_binding(path)
            for name, path in binding_paths.items()
        },
    }


def certification_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{secrets.token_hex(8)}"


def certification_path(certification_identifier: str) -> Path:
    return (
        PROOF_INVENTORY_ROOT
        / f"final_aggregate_certification_{certification_identifier}.json"
    )


def _validate_certification_filename(path: Path) -> None:
    require(
        re.fullmatch(
            r"final_aggregate_certification_"
            r"\d{8}T\d{12}Z-[0-9a-f]{16}\.json",
            path.name,
        )
        is not None,
        "certification filename is not immutable unique-id format",
    )


def _implementation_review_binding(
    review: dict[str, Any],
) -> dict[str, Any]:
    return {
        **artifact_binding(IMPLEMENTATION_REVIEW_RECORD),
        "review_status": "done",
        "acceptance_eligible": True,
        "canonical_handoff": review["canonical_handoff"],
    }


def build_final_review_request(
    candidate_path: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": candidate["certification_id"],
        "review_type": "final_aggregate_acceptance",
        "module": "core::result",
        "routing": {
            "requirement": "independent_review:required",
            "task_scope": "bounded",
            "task_stage_closing": True,
            "task_require_independent_review": True,
            "task_skip_stage_transition": False,
        },
        "candidate_certification": artifact_binding(candidate_path),
        "implementation_review": candidate["implementation_review"],
        "counts": candidate["counts"],
        "technical_gate": candidate["technical_gate"],
        "gate_bindings": candidate["gate_bindings"],
        "trust": candidate["trust"],
        "review_requirements": [
            "Independently inspect readable source and contract content, dependency definitions, definition anchors, and target call sites.",
            "Inspect representative implementation and completeness proof bodies rather than trusting checker booleans or opaque integrity identifiers.",
            "Confirm the 512-command evidence is execution-attributed and timestamped after proof generation.",
            "Explicitly account for every frozen count and all technical/review gates.",
            "Require zero unresolved findings, zero failed or pending work, narrow trust-boundary language, and no foundational trust-freedom claim.",
        ],
        "created_at_utc": utc_now(),
    }


def prepare() -> dict[str, Any]:
    for path, label in (
        (ACTIVE_CERTIFICATION, "active aggregate certification"),
        (FINAL_REVIEW_REQUEST, "final aggregate review request"),
        (FINAL_REVIEW_RECORD, "final aggregate review record"),
        (FINAL_DELIVERY, "final delivery"),
    ):
        require(not path.exists(), f"refusing to replace existing {label}: {path}")

    technical = derive_technical_gate()
    implementation_review = accepted_implementation_review()
    seal_id = certification_id()
    candidate_path = certification_path(seal_id)
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "certification_id": seal_id,
        "status": "implementation_reviewed_pending_final_review",
        "module": "core::result",
        "technical_gate": technical["status"],
        "counts": technical["counts"],
        "trust": technical["trust"],
        "verification_run": technical["run"],
        "gate_bindings": technical["gate_bindings"],
        "implementation_review": _implementation_review_binding(
            implementation_review
        ),
        "pending_gates": ["independent final aggregate review"],
        "unresolved_findings": [],
        "created_at_utc": utc_now(),
    }
    write_json_exclusive(candidate_path, candidate)
    request = build_final_review_request(candidate_path, candidate)
    write_json_exclusive(FINAL_REVIEW_REQUEST, request)
    write_json_atomic(
        ACTIVE_CERTIFICATION,
        {
            "schema_version": SCHEMA_VERSION,
            "status": candidate["status"],
            "active_certification_id": seal_id,
            "active_certification": artifact_binding(candidate_path),
            "final_review_request": artifact_binding(FINAL_REVIEW_REQUEST),
        },
    )
    write_json_atomic(
        PRE_FINAL_VERIFICATION,
        build_pre_final_verification_projection(candidate_path, candidate),
    )
    validate_candidate_state(run_gate_checks=False)
    return candidate


def validate_candidate_state(
    *, run_gate_checks: bool
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    active = load_json(ACTIVE_CERTIFICATION)
    require_equal(
        "active certification status",
        active.get("status"),
        "implementation_reviewed_pending_final_review",
    )
    candidate_path = validate_artifact_binding(
        active.get("active_certification", {}), "active candidate certification"
    )
    _validate_certification_filename(candidate_path)
    candidate = load_json(candidate_path)
    require_equal(
        "candidate certification id",
        candidate.get("certification_id"),
        active.get("active_certification_id"),
    )
    require_equal(
        "candidate status",
        candidate.get("status"),
        "implementation_reviewed_pending_final_review",
    )
    require_equal("candidate counts", candidate.get("counts"), EXPECTED_COUNTS)
    require_equal("candidate pending gates", candidate.get("pending_gates"), [
        "independent final aggregate review"
    ])
    require_equal(
        "candidate unresolved findings", candidate.get("unresolved_findings"), []
    )
    implementation_review = accepted_implementation_review()
    require_equal(
        "candidate implementation review",
        candidate.get("implementation_review"),
        _implementation_review_binding(implementation_review),
    )
    request_path = validate_artifact_binding(
        active.get("final_review_request", {}),
        "active final review request",
        expected_path=FINAL_REVIEW_REQUEST,
    )
    request = load_json(request_path)
    require_equal(
        "final request type",
        request.get("review_type"),
        "final_aggregate_acceptance",
    )
    require_equal(
        "final request id", request.get("request_id"), candidate["certification_id"]
    )
    require_equal(
        "final request candidate",
        request.get("candidate_certification"),
        artifact_binding(candidate_path),
    )
    for key in (
        "counts",
        "technical_gate",
        "gate_bindings",
        "trust",
        "implementation_review",
    ):
        require_equal(
            f"final request {key}", request.get(key), candidate.get(key)
        )
    require(
        request.get("routing", {}).get("task_stage_closing") is True
        and request.get("routing", {}).get("task_skip_stage_transition") is False,
        "final request is not a stage-closing independent review",
    )
    require(
        _review_request_created_at(request, "final")
        >= timestamp(candidate.get("created_at_utc"), "candidate"),
        "final request predates the candidate certification",
    )
    require(
        timestamp(candidate.get("created_at_utc"), "candidate")
        >= timestamp(
            implementation_review.get("completed_at"),
            "implementation review record",
        ),
        "candidate certification predates the implementation review",
    )
    validate_pre_final_verification_projection(candidate_path, candidate)
    if run_gate_checks:
        technical = derive_technical_gate()
        require_equal(
            "candidate technical status",
            candidate.get("technical_gate"),
            technical["status"],
        )
        require_equal(
            "candidate gate bindings",
            candidate.get("gate_bindings"),
            technical["gate_bindings"],
        )
        require_equal(
            "candidate verification run",
            candidate.get("verification_run"),
            technical["run"],
        )
        require_equal(
            "candidate trust accounting",
            candidate.get("trust"),
            technical["trust"],
        )
    return active, candidate, request


def require_distinct_review_handoffs(
    implementation_handoff: dict[str, Any],
    final_handoff: dict[str, Any],
) -> None:
    for field in ("path", "sha256", "round"):
        require(
            implementation_handoff.get(field) != final_handoff.get(field),
            f"final review must use a distinct canonical handoff ({field})",
        )


def accepted_final_review(
    review_record_path: Path,
    request: dict[str, Any],
    implementation_review: dict[str, Any],
) -> dict[str, Any]:
    require_equal(
        "final review record path",
        review_record_path.resolve(),
        FINAL_REVIEW_RECORD.resolve(),
    )
    record = load_json(review_record_path)
    require_equal(
        "final review artifact role",
        record.get("artifact_role"),
        "independent_reviewer_decision",
    )
    require_equal("final review type", record.get("review_type"), "final")
    require_equal("final review status", record.get("review_status"), "done")
    require(
        record.get("acceptance_eligible") is True,
        "final review is not acceptance-eligible",
    )
    require_equal(
        "final review route",
        record.get("route"),
        {
            "TASK_SCOPE": "bounded",
            "TASK_STAGE_CLOSING": True,
            "TASK_REQUIRE_INDEPENDENT_REVIEW": True,
            "TASK_SKIP_STAGE_TRANSITION": False,
            "ROUTING_REQUIREMENT": "independent_review:required",
        },
    )
    request_binding = artifact_binding(FINAL_REVIEW_REQUEST)
    require_equal("final review request", record.get("request"), request_binding)
    expected_artifacts = {
        "request": request_binding,
        "candidate_certification": request["candidate_certification"],
    }
    require_equal(
        "final reviewed artifact bindings",
        record.get("reviewed_artifacts"),
        expected_artifacts,
    )
    handoff = canonical_review_binding(
        record.get("canonical_handoff", {}),
        required_terms=FINAL_REASON_TERMS,
        request_created_at=_review_request_created_at(request, "final"),
        label="final aggregate review",
    )
    require_equal("final review reason", record.get("reason"), handoff["reason"])
    require_equal(
        "final review reason coverage",
        record.get("explicit_reason_coverage"),
        handoff["explicit_reason_coverage"],
    )
    require(
        timestamp(record.get("completed_at"), "final review record")
        >= handoff["created_at"],
        "final review record predates its canonical handoff",
    )
    normalized = {
        key: handoff[key]
        for key in ("path", "sha256", "round", "producer_role")
    }
    require_distinct_review_handoffs(
        implementation_review["canonical_handoff"], normalized
    )
    return {**record, "canonical_handoff": normalized}


def finalize_accepted_review(review_record_path: Path) -> dict[str, Any]:
    require(
        not FINAL_DELIVERY.exists(),
        "refusing to replace an existing final delivery",
    )
    active, candidate, request = validate_candidate_state(run_gate_checks=True)
    implementation_review = accepted_implementation_review()
    final_review = accepted_final_review(
        review_record_path, request, implementation_review
    )
    candidate_path = validate_artifact_binding(
        active["active_certification"], "pre-final certification"
    )
    seal_id = certification_id()
    terminal_path = certification_path(seal_id)
    terminal = {
        **candidate,
        "certification_id": seal_id,
        "status": "campaign_complete",
        "pre_final_certification": artifact_binding(candidate_path),
        "final_review_request": artifact_binding(FINAL_REVIEW_REQUEST),
        "final_review": {
            **artifact_binding(review_record_path),
            "review_status": "done",
            "acceptance_eligible": True,
            "canonical_handoff": final_review["canonical_handoff"],
        },
        "pending_gates": [],
        "unresolved_findings": [],
        "created_at_utc": utc_now(),
    }
    delivery = {
        "schema_version": SCHEMA_VERSION,
        "status": "accepted",
        "module": "core::result",
        "counts": EXPECTED_COUNTS,
        "pre_final_certification": terminal["pre_final_certification"],
        "implementation_review": terminal["implementation_review"],
        "final_review_request": terminal["final_review_request"],
        "final_review": terminal["final_review"],
        "unresolved_findings": [],
        "created_at_utc": utc_now(),
    }
    write_json_exclusive(terminal_path, terminal)
    delivery["certification"] = artifact_binding(terminal_path)
    write_json_exclusive(FINAL_DELIVERY, delivery)
    write_json_atomic(
        ACTIVE_CERTIFICATION,
        {
            "schema_version": SCHEMA_VERSION,
            "status": "campaign_complete",
            "active_certification_id": seal_id,
            "active_certification": artifact_binding(terminal_path),
            "final_delivery": artifact_binding(FINAL_DELIVERY),
        },
    )
    write_json_atomic(
        AGGREGATE_SEAL_VERIFICATION,
        build_aggregate_seal_verification_projection(FINAL_DELIVERY, delivery),
    )
    validate_terminal_state(run_gate_checks=False)
    return terminal


def validate_terminal_state(
    *,
    run_gate_checks: bool,
    validate_verification_projections: bool = True,
) -> dict[str, Any]:
    active = load_json(ACTIVE_CERTIFICATION)
    require_equal("active terminal status", active.get("status"), "campaign_complete")
    terminal_path = validate_artifact_binding(
        active.get("active_certification", {}), "terminal certification"
    )
    _validate_certification_filename(terminal_path)
    terminal = load_json(terminal_path)
    require_equal(
        "terminal certification id",
        terminal.get("certification_id"),
        active.get("active_certification_id"),
    )
    require_equal("terminal status", terminal.get("status"), "campaign_complete")
    require_equal("terminal counts", terminal.get("counts"), EXPECTED_COUNTS)
    require_equal("terminal pending gates", terminal.get("pending_gates"), [])
    require_equal(
        "terminal unresolved findings", terminal.get("unresolved_findings"), []
    )
    candidate_path = validate_artifact_binding(
        terminal.get("pre_final_certification", {}), "pre-final certification"
    )
    candidate = load_json(candidate_path)
    require_equal(
        "pre-final status",
        candidate.get("status"),
        "implementation_reviewed_pending_final_review",
    )
    if validate_verification_projections:
        validate_pre_final_verification_projection(candidate_path, candidate)
    request_path = validate_artifact_binding(
        terminal.get("final_review_request", {}),
        "terminal final review request",
        expected_path=FINAL_REVIEW_REQUEST,
    )
    request = load_json(request_path)
    require_equal(
        "terminal request candidate binding",
        request.get("candidate_certification"),
        terminal.get("pre_final_certification"),
    )
    implementation_review = accepted_implementation_review()
    require_equal(
        "terminal implementation review",
        terminal.get("implementation_review"),
        _implementation_review_binding(implementation_review),
    )
    final_record_path = validate_artifact_binding(
        terminal.get("final_review", {}),
        "terminal final review",
        expected_path=FINAL_REVIEW_RECORD,
    )
    final_review = accepted_final_review(
        final_record_path, request, implementation_review
    )
    require_equal(
        "terminal final handoff",
        terminal.get("final_review", {}).get("canonical_handoff"),
        final_review["canonical_handoff"],
    )
    require(
        timestamp(terminal.get("created_at_utc"), "terminal certification")
        >= timestamp(
            load_json(final_record_path).get("completed_at"),
            "final review record",
        ),
        "terminal certification predates the final review",
    )
    delivery_path = validate_artifact_binding(
        active.get("final_delivery", {}),
        "final delivery",
        expected_path=FINAL_DELIVERY,
    )
    delivery = load_json(delivery_path)
    require_equal("final delivery status", delivery.get("status"), "accepted")
    require_equal("final delivery counts", delivery.get("counts"), EXPECTED_COUNTS)
    require_equal(
        "final delivery certification",
        delivery.get("certification"),
        artifact_binding(terminal_path),
    )
    for key in (
        "pre_final_certification",
        "implementation_review",
        "final_review_request",
        "final_review",
        "unresolved_findings",
    ):
        require_equal(
            f"final delivery {key}", delivery.get(key), terminal.get(key)
        )
    if validate_verification_projections:
        validate_aggregate_seal_verification_projection(
            delivery_path,
            delivery,
        )
    if run_gate_checks:
        technical = derive_technical_gate()
        require_equal(
            "terminal technical gate",
            terminal.get("technical_gate"),
            technical["status"],
        )
        require_equal(
            "terminal gate bindings",
            terminal.get("gate_bindings"),
            technical["gate_bindings"],
        )
        require_equal(
            "terminal verification run",
            terminal.get("verification_run"),
            technical["run"],
        )
        require_equal(
            "terminal trust accounting",
            terminal.get("trust"),
            technical["trust"],
        )
    return terminal


def regenerate_verification_projections() -> dict[str, Any]:
    terminal = validate_terminal_state(
        run_gate_checks=True,
        validate_verification_projections=False,
    )
    candidate_path = validate_artifact_binding(
        terminal.get("pre_final_certification", {}),
        "pre-final certification",
    )
    candidate = load_json(candidate_path)
    delivery = load_json(FINAL_DELIVERY)
    write_json_atomic(
        PRE_FINAL_VERIFICATION,
        build_pre_final_verification_projection(candidate_path, candidate),
    )
    write_json_atomic(
        AGGREGATE_SEAL_VERIFICATION,
        build_aggregate_seal_verification_projection(FINAL_DELIVERY, delivery),
    )
    return validate_terminal_state(run_gate_checks=False)


def check() -> dict[str, Any]:
    active = load_json(ACTIVE_CERTIFICATION)
    if active.get("status") == "campaign_complete":
        return validate_terminal_state(run_gate_checks=True)
    _, candidate, _ = validate_candidate_state(run_gate_checks=True)
    return candidate


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("stage-implementation-review")
    subparsers.add_parser("reconcile-implementation-review")
    subparsers.add_parser("prepare")
    subparsers.add_parser("regenerate-verification-projections")
    subparsers.add_parser("check")
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument(
        "--review-record",
        default=campaign_relative(FINAL_REVIEW_RECORD),
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        if options.command == "stage-implementation-review":
            result = stage_implementation_request()
        elif options.command == "reconcile-implementation-review":
            result = reconcile_implementation_review()
        elif options.command == "prepare":
            result = prepare()
        elif options.command == "regenerate-verification-projections":
            result = regenerate_verification_projections()
        elif options.command == "finalize":
            record = Path(options.review_record)
            if not record.is_absolute():
                record = CAMPAIGN_ROOT / record
            result = finalize_accepted_review(record)
        else:
            result = check()
    except (AggregateSealError, OSError, ValueError, KeyError) as error:
        print(f"aggregate seal error: {error}", file=sys.stderr)
        return 1
    output = {"status": result["status"]}
    if "certification_id" in result:
        output["certification_id"] = result["certification_id"]
    print(json.dumps(output, sort_keys=True))
    if options.command == "check" and result["status"] != "campaign_complete":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
