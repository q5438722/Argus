#!/usr/bin/env python3
"""Fail-closed checker for the core::result implementation-conformance gate.

The checker re-derives every claim from the artifacts on disk.  No self-authored
boolean in a generated manifest is trusted: hashes are recomputed, proof text is
re-read, mutation anchors are re-located, and evidence outcomes are re-counted
from the per-command records written by
``tools/run_implementation_proofs.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import implementation  # noqa: E402

HARNESS_ROOT = ROOT / "proof_harnesses"
MANIFEST_ROOT = ROOT / "proof_manifests"
LIVE_RUNS = ROOT / "verification/live_runs"
RUN_BINDING = ROOT / "proof_inventory/verification_run.json"
VERIFICATION_RE = re.compile(
    r"verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors"
)
EXTERNAL_HELPER_RE = re.compile(
    r"#\[verifier::external_body\]"
    r"(?:\s*#\[[^\]]+\])*\s*"
    r"pub\s+(?:proof\s+)?(?:unsafe\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)"
)
UNINTERPRETED_HELPER_RE = re.compile(
    r"pub\s+uninterp\s+spec\s+fn\s+([A-Za-z_][A-Za-z0-9_]*)"
)

MUTANT_REJECTION_NAMES = (
    "implementation_mutant_actual",
    "completeness_mutant_actual",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_load(path: Path) -> Any:
    return json.loads(path.read_text())


def proof_closure_paths(target: Path) -> dict[str, Path]:
    proof_manifest = MANIFEST_ROOT / target.name
    return {
        "implementation_proof.rs": target / "implementation_proof.rs",
        "completeness_proof.rs": target / "completeness_proof.rs",
        "mutations/implementation_mutant.rs": (
            target / "mutations/implementation_mutant.rs"
        ),
        "mutations/completeness_mutant.rs": (
            target / "mutations/completeness_mutant.rs"
        ),
        "accepted_contract.rs": target / "accepted_contract.rs",
        "source_excerpt.rs": target / "source_excerpt.rs",
        "contract_equivalence.json": target / "contract_equivalence.json",
        "transformation_manifest.json": target / "transformation_manifest.json",
        "dependency_assumptions.json": target / "dependency_assumptions.json",
        "trust_boundaries.json": target / "trust_boundaries.json",
        "manifest.json": target / "manifest.json",
        "proof_manifests/source_body.json": proof_manifest / "source_body.json",
        "proof_manifests/transformation_manifest.json": (
            proof_manifest / "transformation_manifest.json"
        ),
        "proof_manifests/dependency_assumption_manifest.json": (
            proof_manifest / "dependency_assumption_manifest.json"
        ),
        "proof_manifests/proof_manifest.json": (
            proof_manifest / "proof_manifest.json"
        ),
        "frozen_inputs/source_dependency_manifest.json": (
            ROOT / "frozen_inputs/source_dependency_manifest.json"
        ),
        "specs/result_shared_vocabulary.rs": (
            ROOT / "specs/result_shared_vocabulary.rs"
        ),
        "specs/all_result_specs.json": ROOT / "specs/all_result_specs.json",
        "implementation.py": ROOT / "implementation.py",
        "proofgen/families.py": ROOT / "proofgen/families.py",
        "proofgen/model.py": ROOT / "proofgen/model.py",
        "proofgen/render.py": ROOT / "proofgen/render.py",
        "tools/run_implementation_proofs.py": (
            ROOT / "tools/run_implementation_proofs.py"
        ),
        "tools/check_implementation_proofs.py": Path(__file__).resolve(),
    }


def trust_accounting() -> dict[str, Any]:
    """Re-derive literal and semantic trust accounting from the proof text."""

    literal_target_external = 0
    literal_completeness_external = 0
    literal_assume = 0
    literal_lower_level_external = 0
    external_boundaries: dict[str, int] = {}
    uninterpreted_boundaries: dict[str, int] = {}
    type_bridges: dict[str, int] = {}
    frozen_datatypes: dict[str, int] = {}
    source_bound_dependencies: dict[str, int] = {}
    helper_occurrences: list[dict[str, Any]] = []
    unbound_helpers: list[dict[str, Any]] = []
    target_symbols = 0
    unsafe_targets = 0
    for target_dir in sorted(path for path in HARNESS_ROOT.iterdir() if path.is_dir()):
        implementation_text = (target_dir / "implementation_proof.rs").read_text()
        completeness_text = (target_dir / "completeness_proof.rs").read_text()
        if re.search(
            r"#\[verifier::external_body\]\s*(?:#\[[^\]]*\]\s*)*pub (?:unsafe )?fn implementation_target",
            implementation_text,
        ):
            literal_target_external += 1
        literal_lower_level_external += implementation_text.count(
            "#[verifier::external_body]"
        )
        literal_completeness_external += completeness_text.count("#[verifier::external_body]")
        literal_assume += implementation_text.count("assume(") + completeness_text.count("assume(")
        if "pub fn implementation_target" in implementation_text:
            target_symbols += 1
        if "pub unsafe fn implementation_target" in implementation_text:
            target_symbols += 1
            unsafe_targets += 1
        dependency_manifest = json_load(
            target_dir / "dependency_assumptions.json"
        )
        dependencies = dependency_manifest["dependencies"]
        for dependency in dependencies:
            source_bound_dependencies[dependency["name"]] = (
                source_bound_dependencies.get(dependency["name"], 0) + 1
            )
            if dependency["kind"] == "frozen_source_datatype":
                frozen_datatypes[dependency["name"]] = (
                    frozen_datatypes.get(dependency["name"], 0) + 1
                )

        declarations: list[tuple[int, str, str]] = []
        for declaration_kind, pattern in (
            ("external_body", EXTERNAL_HELPER_RE),
            ("uninterpreted_spec", UNINTERPRETED_HELPER_RE),
        ):
            declarations.extend(
                (
                    implementation_text.count("\n", 0, match.start()) + 1,
                    declaration_kind,
                    match.group(1),
                )
                for match in pattern.finditer(implementation_text)
            )
        for dependency in dependencies:
            if dependency["kind"] != "associated_type_bridge":
                continue
            symbol = dependency["proof_symbol"]
            match = re.search(
                rf"\bpub\s+trait\s+{re.escape(symbol)}\b",
                implementation_text,
            )
            if match is not None:
                declarations.append(
                    (
                        implementation_text.count("\n", 0, match.start()) + 1,
                        "associated_type_bridge",
                        symbol,
                    )
                )

        for source_line, declaration_kind, symbol in sorted(declarations):
            matches = [
                dependency
                for dependency in dependencies
                if symbol
                in dependency.get(
                    "proof_symbols", [dependency["proof_symbol"]]
                )
            ]
            record = {
                "target": target_dir.name,
                "source_line": source_line,
                "declaration_kind": declaration_kind,
                "symbol": symbol,
                "dependency": matches[0]["name"] if len(matches) == 1 else None,
            }
            helper_occurrences.append(record)
            if len(matches) != 1:
                unbound_helpers.append(record)
                continue
            dependency_name = matches[0]["name"]
            destination = {
                "external_body": external_boundaries,
                "uninterpreted_spec": uninterpreted_boundaries,
                "associated_type_bridge": type_bridges,
            }[declaration_kind]
            destination[dependency_name] = destination.get(dependency_name, 0) + 1
    return {
        "targets": len(list(HARNESS_ROOT.iterdir())),
        "public_implementation_targets": target_symbols,
        "unsafe_implementation_targets": unsafe_targets,
        "literal_target_external_bodies": literal_target_external,
        "literal_lower_level_external_bodies": literal_lower_level_external,
        "literal_completeness_external_bodies": literal_completeness_external,
        "literal_assume_statements": literal_assume,
        "narrow_external_boundaries": dict(sorted(external_boundaries.items())),
        "uninterpreted_model_boundaries": dict(
            sorted(uninterpreted_boundaries.items())
        ),
        "associated_type_bridges": dict(sorted(type_bridges.items())),
        "non_external_frozen_datatypes": dict(sorted(frozen_datatypes.items())),
        "source_bound_dependencies": dict(
            sorted(source_bound_dependencies.items())
        ),
        "local_boundary_helper_occurrences": helper_occurrences,
        "unbound_local_helpers": unbound_helpers,
        "semantic_boundary_count": len(
            set(external_boundaries)
            | set(uninterpreted_boundaries)
            | set(type_bridges)
        ),
    }


def evidence_accounting() -> dict[str, Any]:
    """Re-count every recorded command outcome from the per-command records."""

    total = 0
    met = 0
    mutation_rejections = 0
    per_name: dict[str, int] = {}
    run_ids: set[str] = set()
    stale_inputs: list[str] = []
    unbound: list[str] = []
    invalid_records: list[str] = []
    stale_sidecars: list[str] = []
    stale_closures: list[str] = []
    stale_tools: list[str] = []
    targets_complete = 0
    for target_dir in sorted(path for path in HARNESS_ROOT.iterdir() if path.is_dir()):
        present = 0
        for name in implementation.EVIDENCE_NAMES:
            record_path = target_dir / "evidence" / f"{name}.json"
            if not record_path.is_file():
                continue
            record = json_load(record_path)
            present += 1
            total += 1
            per_name[name] = per_name.get(name, 0) + 1
            label = f"{target_dir.name}/{name}"
            if (
                record.get("name") != name
                or record.get("target_directory") != target_dir.name
            ):
                invalid_records.append(label)
            sidecars: dict[str, Path] = {
                "command": target_dir / "evidence" / f"{name}.command.txt",
                "stdout": target_dir / "evidence" / f"{name}.stdout.txt",
                "stderr": target_dir / "evidence" / f"{name}.stderr.txt",
                "rc": target_dir / "evidence" / f"{name}.rc.txt",
            }
            if not all(path.is_file() for path in sidecars.values()):
                stale_sidecars.append(label)
                continue
            try:
                sidecar_rc = int(sidecars["rc"].read_text().strip())
            except ValueError:
                stale_sidecars.append(label)
                continue
            stdout = sidecars["stdout"].read_text()
            stderr = sidecars["stderr"].read_text()
            expected_sidecar_values = {
                "return_code": sidecar_rc,
                "command_text": sidecars["command"].read_text().rstrip("\n"),
                "command_sha256": sha256_file(sidecars["command"]),
                "stdout_sha256": sha256_file(sidecars["stdout"]),
                "stderr_sha256": sha256_file(sidecars["stderr"]),
                "rc_sha256": sha256_file(sidecars["rc"]),
            }
            if any(
                record.get(field) != expected
                for field, expected in expected_sidecar_values.items()
            ):
                stale_sidecars.append(label)
            mutant_actual = name in MUTANT_REJECTION_NAMES
            no_verify = name.endswith("_no_verify")
            if mutant_actual:
                derived_expectation = (
                    sidecar_rc != 0
                    and record.get("timed_out") is False
                    and any(
                        marker in stderr
                        for marker in (
                            "postcondition not satisfied",
                            "precondition not satisfied",
                            "assertion failed",
                        )
                    )
                )
            else:
                derived_expectation = (
                    sidecar_rc == 0 and record.get("timed_out") is False
                )
                if not no_verify:
                    match = VERIFICATION_RE.search(stdout + "\n" + stderr)
                    derived_expectation = (
                        derived_expectation
                        and match is not None
                        and int(match.group(1)) > 0
                        and int(match.group(2)) == 0
                    )
            if (
                record.get("expectation_met") is not derived_expectation
                or record.get("success") is not derived_expectation
                or not derived_expectation
            ):
                invalid_records.append(label)
            if derived_expectation:
                met += 1
            if mutant_actual and derived_expectation:
                mutation_rejections += 1
            run_id = record.get("run_id")
            if not run_id:
                unbound.append(f"{target_dir.name}/{name}")
            else:
                run_ids.add(run_id)
            input_path = ROOT / record.get("input_path", "")
            if not input_path.is_file() or sha256_file(input_path) != record.get("input_sha256"):
                stale_inputs.append(label)
            closure_paths = proof_closure_paths(target_dir)
            closure = record.get("proof_closure_sha256", {})
            if set(closure) != set(closure_paths) or any(
                not path.is_file() or closure.get(relative) != sha256_file(path)
                for relative, path in closure_paths.items()
            ):
                stale_closures.append(label)
            tools = record.get("tools", {})
            if (
                tools.get("verus_binary_sha256")
                != sha256_file(ROOT.parent / "verus/source/target-verus/release/verus")
                or tools.get("z3_binary_sha256")
                != sha256_file(ROOT.parent / "verus/source/z3")
                or "Toolchain: 1.96.0-" not in str(tools.get("verus_version", ""))
                or "rustc 1.96.0" not in str(tools.get("rustc_version", ""))
                or "Z3 version 4.12.5" not in str(tools.get("z3_version", ""))
            ):
                stale_tools.append(label)
        if present == len(implementation.EVIDENCE_NAMES):
            targets_complete += 1
    known_runs = {path.name.split(".summary.json")[0] for path in LIVE_RUNS.glob("*.summary.json")}
    return {
        "commands_recorded": total,
        "commands_expected_for_full_batch": 512,
        "expectations_met": met,
        "targets_with_complete_matrices": targets_complete,
        "mutation_rejections_observed": mutation_rejections,
        "mutation_rejections_required": 128,
        "per_command_counts": dict(sorted(per_name.items())),
        "run_ids": sorted(run_ids),
        "run_ids_without_summary": sorted(run_ids - known_runs),
        "evidence_not_bound_to_run": sorted(unbound),
        "stale_evidence_inputs": sorted(stale_inputs),
        "invalid_or_failed_records": sorted(set(invalid_records)),
        "stale_evidence_sidecars": sorted(set(stale_sidecars)),
        "stale_proof_closures": sorted(set(stale_closures)),
        "stale_tool_identities": sorted(set(stale_tools)),
    }


def evidence_errors(accounting: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if accounting["commands_recorded"] != 512:
        errors.append(
            f"commands_recorded={accounting['commands_recorded']} expected=512 "
            "(all 64 targets x 8 commands)"
        )
    if accounting["targets_with_complete_matrices"] != 64:
        errors.append(
            f"targets_with_complete_matrices="
            f"{accounting['targets_with_complete_matrices']} expected=64"
        )
    if accounting["expectations_met"] != accounting["commands_recorded"]:
        errors.append("not every recorded command met its expectation")
    if accounting["mutation_rejections_observed"] != 128:
        errors.append(
            f"mutation_rejections_observed={accounting['mutation_rejections_observed']} "
            "expected=128 (64 implementation mutants + 64 completeness mutants)"
        )
    errors.extend(f"evidence not bound to a run id: {name}" for name in accounting["evidence_not_bound_to_run"])
    errors.extend(f"evidence run id has no durable summary: {run}" for run in accounting["run_ids_without_summary"])
    errors.extend(f"stale evidence input: {name}" for name in accounting["stale_evidence_inputs"])
    errors.extend(
        f"invalid or failed evidence record: {name}"
        for name in accounting["invalid_or_failed_records"]
    )
    errors.extend(
        f"stale evidence sidecar: {name}"
        for name in accounting["stale_evidence_sidecars"]
    )
    errors.extend(
        f"stale proof closure: {name}"
        for name in accounting["stale_proof_closures"]
    )
    errors.extend(
        f"stale tool identity: {name}"
        for name in accounting["stale_tool_identities"]
    )
    if len(accounting["run_ids"]) != 1:
        errors.append(
            f"full evidence must come from exactly one run id, found "
            f"{accounting['run_ids']}"
        )
    errors.extend(run_binding_errors(accounting))
    return errors


def run_binding_errors(accounting: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not RUN_BINDING.is_file():
        return ["proof_inventory/verification_run.json is missing"]
    binding = json_load(RUN_BINDING)
    run_ids = accounting["run_ids"]
    if len(run_ids) != 1 or binding.get("run_id") != run_ids[0]:
        errors.append("verification run binding does not name the sole evidence run")
        return errors
    if (
        binding.get("state") != "completed"
        or binding.get("target_count") != 64
        or binding.get("commands_recorded") != 512
        or binding.get("mutation_rejections") != 128
        or binding.get("evidence_current") is not True
        or binding.get("proof_inventory_sha256")
        != sha256_file(ROOT / "proof_inventory/targets.json")
    ):
        errors.append("verification run binding has stale or incomplete totals")
    run_dir = ROOT / str(binding.get("run_dir", ""))
    if not run_dir.is_dir():
        errors.append("verification run directory is missing")
        return errors
    artifacts = binding.get("artifacts", {})
    for label in ("manifest", "status", "progress", "results", "summary"):
        record = artifacts.get(label, {})
        path = ROOT / str(record.get("path", ""))
        if (
            not path.is_file()
            or record.get("sha256") != sha256_file(path)
            or record.get("size") != path.stat().st_size
        ):
            errors.append(f"verification run {label} binding is stale")
    manifest_path = run_dir / "manifest.json"
    status_path = run_dir / "status.json"
    summary_path = run_dir / "summary.json"
    results_path = run_dir / "results.jsonl"
    if all(path.is_file() for path in (manifest_path, status_path, summary_path, results_path)):
        manifest = json_load(manifest_path)
        status = json_load(status_path)
        summary = json_load(summary_path)
        result_rows = [
            line for line in results_path.read_text().splitlines() if line.strip()
        ]
        if (
            manifest.get("run_id") != binding.get("run_id")
            or manifest.get("full_batch") is not True
            or manifest.get("target_count") != 64
            or manifest.get("expected_commands") != 512
            or manifest.get("inputs", {}).get("proof_inventory")
            != sha256_file(ROOT / "proof_inventory/targets.json")
            or manifest.get("inputs", {}).get("accepted_catalog")
            != sha256_file(ROOT / "specs/all_result_specs.json")
            or manifest.get("inputs", {}).get("accepted_manifest")
            != sha256_file(ROOT / "specs/specification_package_manifest.json")
            or manifest.get("inputs", {}).get("proof_stage_authorization")
            != sha256_file(ROOT / "proof_stage/authorization.json")
            or manifest.get("inputs", {}).get("source_dependency_manifest")
            != sha256_file(ROOT / "frozen_inputs/source_dependency_manifest.json")
            or manifest.get("inputs", {}).get("implementation_generator")
            != sha256_file(ROOT / "implementation.py")
            or manifest.get("inputs", {}).get("family_templates")
            != sha256_file(ROOT / "proofgen/families.py")
            or manifest.get("inputs", {}).get("proof_model")
            != sha256_file(ROOT / "proofgen/model.py")
            or manifest.get("inputs", {}).get("proof_renderer")
            != sha256_file(ROOT / "proofgen/render.py")
            or manifest.get("inputs", {}).get("runner")
            != sha256_file(ROOT / "tools/run_implementation_proofs.py")
            or manifest.get("inputs", {}).get("checker")
            != sha256_file(ROOT / "tools/check_implementation_proofs.py")
        ):
            errors.append("verification run manifest is stale")
        if (
            status.get("state") != "completed"
            or status.get("commands_done") != 512
            or status.get("commands_total") != 512
            or status.get("evidence_current") is not True
        ):
            errors.append("verification run status is not terminal and complete")
        if (
            summary.get("full_64_target_batch_run") is not True
            or summary.get("evidence_current") is not True
            or summary.get("commands_recorded") != 512
            or summary.get("successful_expectations") != 512
            or summary.get("failed_expectations") != []
        ):
            errors.append("verification run summary is not a complete success")
        if len(result_rows) != 512:
            errors.append(
                f"verification run results row count={len(result_rows)} expected=512"
            )
    return errors


def artifact_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def write_audit(path: Path, payload: dict[str, Any]) -> None:
    value = {
        "schema_version": implementation.SCHEMA,
        "generated_at_utc": implementation.utc_now(),
        **payload,
    }
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_post_batch_audits(
    result: dict[str, Any],
    trust: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    audit_root = ROOT / "audits"
    audit_root.mkdir(parents=True, exist_ok=True)
    inventory = json_load(ROOT / "proof_inventory/targets.json")
    source_rows = []
    mutation_rows = []
    for target in inventory["targets"]:
        directory = HARNESS_ROOT / target["directory"]
        manifest = json_load(directory / "manifest.json")
        dependency = json_load(directory / "dependency_assumptions.json")
        source_rows.append(
            {
                "rustdoc_item_id": target["rustdoc_item_id"],
                "target": target["target"],
                "source_excerpt_sha256": manifest["source"][
                    "excerpt_sha256"
                ],
                "accepted_contract_segment_sha256": manifest["contract"][
                    "accepted_segment_sha256"
                ],
                "accepted_contract_copy_sha256": sha256_file(
                    directory / "accepted_contract.rs"
                ),
                "dependency_count": len(dependency["dependencies"]),
                "local_boundary_helper_count": len(
                    dependency["local_boundary_helpers"]
                ),
                "local_boundary_helpers": dependency[
                    "local_boundary_helpers"
                ],
                "dependency_hashes": {
                    row["name"]: row["sha256"]
                    for row in dependency["dependencies"]
                },
                "status": "pass",
            }
        )
        mutation_rows.append(
            {
                "rustdoc_item_id": target["rustdoc_item_id"],
                "target": target["target"],
                "implementation_no_verify": artifact_record(
                    directory
                    / "evidence/implementation_mutant_no_verify.json"
                ),
                "implementation_actual_rejection": artifact_record(
                    directory / "evidence/implementation_mutant_actual.json"
                ),
                "completeness_no_verify": artifact_record(
                    directory
                    / "evidence/completeness_mutant_no_verify.json"
                ),
                "completeness_actual_rejection": artifact_record(
                    directory / "evidence/completeness_mutant_actual.json"
                ),
            }
        )

    accepted_records = implementation.verify_accepted_inputs()
    verified_status_path = (
        ROOT / "proof_inventory/verified_target_status.json"
    )
    verified_status_path.write_text(
        json.dumps(
            {
                "schema_version": implementation.SCHEMA,
                "generated_at_utc": implementation.utc_now(),
                "base_inventory": artifact_record(
                    ROOT / "proof_inventory/targets.json"
                ),
                "verification_run": artifact_record(RUN_BINDING),
                "base_inventory_status_semantics": (
                    "The evidence_status field in targets.json is the "
                    "generation-time state frozen as an input to the supervised "
                    "run. This overlay is the post-run status source."
                ),
                "target_count": len(inventory["targets"]),
                "targets": [
                    {
                        "rustdoc_item_id": target["rustdoc_item_id"],
                        "directory": target["directory"],
                        "status": "actual_verus_verified",
                        "baseline_no_verify": 2,
                        "baseline_actual_verus": 2,
                        "syntax_valid_mutants": 2,
                        "actual_verus_mutation_rejections": 2,
                    }
                    for target in inventory["targets"]
                ],
                "failed": 0,
                "pending": 0,
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    write_audit(
        audit_root / "source_hash_fidelity.json",
        {
            "audit": "source_and_hash_fidelity",
            "accepted_input_count": len(accepted_records),
            "accepted_inputs": accepted_records,
            "target_count": len(source_rows),
            "targets": source_rows,
            "status": "pass",
        },
    )
    write_audit(
        audit_root / "artifact_integrity.json",
        {
            "audit": "artifact_integrity",
            "target_directories": len(
                [path for path in HARNESS_ROOT.iterdir() if path.is_dir()]
            ),
            "proof_manifest_directories": len(
                [path for path in MANIFEST_ROOT.iterdir() if path.is_dir()]
            ),
            "commands_recorded": evidence["commands_recorded"],
            "targets_with_complete_matrices": evidence[
                "targets_with_complete_matrices"
            ],
            "proof_inventory": artifact_record(
                ROOT / "proof_inventory/targets.json"
            ),
            "verification_run": artifact_record(RUN_BINDING),
            "verified_target_status": artifact_record(
                verified_status_path
            ),
            "status": "pass",
        },
    )
    write_audit(
        audit_root / "literal_trust_boundary_audit.json",
        {
            "audit": "literal_trust_boundary",
            "target_count": trust["targets"],
            "target_external_bodies": trust[
                "literal_target_external_bodies"
            ],
            "completeness_external_bodies": trust[
                "literal_completeness_external_bodies"
            ],
            "lower_level_external_body_helpers": trust[
                "literal_lower_level_external_bodies"
            ],
            "assume_statements": trust["literal_assume_statements"],
            "narrow_external_boundaries": trust[
                "narrow_external_boundaries"
            ],
            "uninterpreted_model_boundaries": trust[
                "uninterpreted_model_boundaries"
            ],
            "associated_type_bridges": trust[
                "associated_type_bridges"
            ],
            "local_boundary_helper_occurrences": trust[
                "local_boundary_helper_occurrences"
            ],
            "unbound_local_helpers": trust["unbound_local_helpers"],
            "status": "pass",
        },
    )
    write_audit(
        audit_root / "semantic_trust_boundary_audit.json",
        {
            "audit": "semantic_trust_boundary",
            "target_count": trust["targets"],
            "narrow_source_bound_dependencies": trust[
                "source_bound_dependencies"
            ],
            "external_body_helpers_by_dependency": trust[
                "narrow_external_boundaries"
            ],
            "uninterpreted_helpers_by_dependency": trust[
                "uninterpreted_model_boundaries"
            ],
            "associated_type_bridges": trust[
                "associated_type_bridges"
            ],
            "non_external_frozen_datatypes": trust[
                "non_external_frozen_datatypes"
            ],
            "local_boundary_helper_occurrences": trust[
                "local_boundary_helper_occurrences"
            ],
            "unbound_local_helpers": trust["unbound_local_helpers"],
            "foundational_end_to_end_trust_free": False,
            "language": (
                "No target-level or completeness-level implementation "
                "assumption is present. Narrow source-hash-bound dependency "
                "models remain; this is not a foundational trust-freedom claim."
            ),
            "status": "pass",
        },
    )
    write_audit(
        audit_root / "mutation_audit.json",
        {
            "audit": "implementation_and_completeness_mutations",
            "target_count": len(mutation_rows),
            "syntax_valid_mutants": (
                evidence["per_command_counts"][
                    "implementation_mutant_no_verify"
                ]
                + evidence["per_command_counts"][
                    "completeness_mutant_no_verify"
                ]
            ),
            "actual_verus_rejections": evidence[
                "mutation_rejections_observed"
            ],
            "targets": mutation_rows,
            "status": "pass",
        },
    )
    aggregate = {
        "schema_version": implementation.SCHEMA,
        "generated_at_utc": implementation.utc_now(),
        "module": "core::result",
        "status": "technical_gates_passed_pending_independent_review",
        "counts": {
            "selected": 64,
            "generated": 54,
            "exact_vstd": 10,
            "derive_expansion": 9,
            "implementation_proofs": 64,
            "completeness_proofs": 64,
            "commands": 512,
            "actual_verus_baselines": 128,
            "mutation_rejections": 128,
            "failed": 0,
            "pending": 0,
        },
        "trust": {
            "lower_level_external_body_helpers": trust[
                "literal_lower_level_external_bodies"
            ],
            "uninterpreted_helpers": sum(
                trust["uninterpreted_model_boundaries"].values()
            ),
            "associated_type_bridges": sum(
                trust["associated_type_bridges"].values()
            ),
            "unbound_local_helpers": trust["unbound_local_helpers"],
        },
        "checker": artifact_record(
            ROOT / "verification/implementation_proof_check.json"
        ),
        "verified_target_status": artifact_record(verified_status_path),
        "audits": {
            name: artifact_record(audit_root / f"{name}.json")
            for name in (
                "source_hash_fidelity",
                "artifact_integrity",
                "literal_trust_boundary_audit",
                "semantic_trust_boundary_audit",
                "mutation_audit",
            )
        },
        "independent_review_complete": False,
        "acceptance_claim": False,
    }
    path = ROOT / "proof_inventory/aggregate_coverage.json"
    path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
    trust_audit_path = audit_root / "trust_boundary_audit.json"
    trust_audit = json_load(trust_audit_path)
    trust_audit.update(
        {
            "status": "pass",
            "lower_level_external_body_helpers": trust[
                "literal_lower_level_external_bodies"
            ],
            "narrow_external_boundaries": trust[
                "narrow_external_boundaries"
            ],
            "uninterpreted_model_boundaries": trust[
                "uninterpreted_model_boundaries"
            ],
            "associated_type_bridges": trust[
                "associated_type_bridges"
            ],
            "local_boundary_helper_occurrences": trust[
                "local_boundary_helper_occurrences"
            ],
            "unbound_local_helpers": trust["unbound_local_helpers"],
            "literal_audit": artifact_record(
                audit_root / "literal_trust_boundary_audit.json"
            ),
            "semantic_audit": artifact_record(
                audit_root / "semantic_trust_boundary_audit.json"
            ),
            "verification_run": artifact_record(RUN_BINDING),
        }
    )
    trust_audit_path.write_text(
        json.dumps(trust_audit, indent=2, sort_keys=True) + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structural-only", action="store_true")
    parser.add_argument("--stage-review", action="store_true")
    args = parser.parse_args()

    errors = implementation.structural_errors(not args.structural_only)
    trust = trust_accounting()
    evidence = evidence_accounting()

    if trust["literal_target_external_bodies"] != 0:
        errors.append("at least one implementation_target is declared external_body")
    if trust["literal_completeness_external_bodies"] != 0:
        errors.append("at least one completeness proof declares an external body")
    if trust["literal_assume_statements"] != 0:
        errors.append("at least one proof uses `assume`")
    if trust["literal_lower_level_external_bodies"] != sum(
        trust["narrow_external_boundaries"].values()
    ):
        errors.append(
            "not every lower-level external body is bound to one frozen "
            "source dependency"
        )
    if trust["unbound_local_helpers"]:
        errors.append(
            "at least one external-body, uninterpreted, or type-bridge helper "
            "is not bound to exactly one frozen source dependency"
        )
    if sum(trust["associated_type_bridges"].values()) != 1:
        errors.append(
            "the FromIterator associated-item equality must have exactly one "
            "source-bound type bridge"
        )
    if trust["public_implementation_targets"] != 64:
        errors.append(
            f"public implementation targets={trust['public_implementation_targets']} expected=64"
        )
    if trust["unsafe_implementation_targets"] != 2:
        errors.append(
            f"unsafe implementation targets={trust['unsafe_implementation_targets']} expected=2"
        )

    if not args.structural_only:
        errors.extend(evidence_errors(evidence))

    inventory = json_load(ROOT / "proof_inventory/targets.json")
    result = {
        "schema_version": implementation.SCHEMA,
        "checked_at_utc": implementation.utc_now(),
        "mode": "structural" if args.structural_only else "full",
        "inventory": {
            "targets": len(inventory["targets"]),
            "exact_vstd": sum(t["disposition"] == "exact_vstd" for t in inventory["targets"]),
            "generated": sum(t["disposition"] == "generated" for t in inventory["targets"]),
            "derive_expansion_rows": sum(
                json_load(HARNESS_ROOT / t["directory"] / "manifest.json")["source"]["kind"]
                == "rustc_derive_expansion"
                for t in inventory["targets"]
            ),
            "distinct_proof_templates": len({t["proof_template_id"] for t in inventory["targets"]}),
            "distinct_semantic_families": len({t["semantic_family"] for t in inventory["targets"]}),
            "proof_manifest_directories": len(
                [path for path in MANIFEST_ROOT.iterdir() if path.is_dir()]
            ),
        },
        "trust_accounting": trust,
        "evidence_accounting": evidence,
        "error_count": len(errors),
        "errors": errors,
        "status": "pass" if not errors else "fail",
    }
    path = ROOT / "verification/implementation_proof_check.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not errors and args.stage_review and not args.structural_only:
        write_post_batch_audits(result, trust, evidence)
        implementation.emit_post_batch_surfaces()
    console_result = {
        key: value
        for key, value in result.items()
        if key not in {"errors", "trust_accounting", "evidence_accounting"}
    }
    console_result["evidence_accounting"] = {
        key: value
        for key, value in evidence.items()
        if not isinstance(value, list) or key == "run_ids"
    }
    console_result["trust_accounting"] = {
        key: value
        for key, value in trust.items()
        if key != "local_boundary_helper_occurrences"
    }
    print(json.dumps(console_result, sort_keys=True))
    for error in errors[:40]:
        print(f"  error: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
