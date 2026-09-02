#!/usr/bin/env python3
"""Verify FromIterator exactness after erasing the unsupported projection."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


OUT = support.FROM_ITER_PROBE_REPORT_PATH.parent
VERUS = (
    support.ROOT.parent
    / "verus"
    / "source"
    / "target-verus"
    / "release"
    / "verus"
)
Z3 = support.ROOT.parent / "verus" / "source" / "z3"


def run(label: str, path: Path, no_verify: bool = False) -> dict[str, Any]:
    command = [str(VERUS), str(path), "--crate-type=lib"]
    if no_verify:
        command.append("--no-verify")
    environment = dict(os.environ)
    environment["VERUS_Z3_PATH"] = str(Z3)
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=support.ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    stdout = OUT / f"{label}.stdout.log"
    stderr = OUT / f"{label}.stderr.log"
    stdout.write_text(result.stdout, encoding="utf-8")
    stderr.write_text(result.stderr, encoding="utf-8")
    return {
        "command": command,
        "duration_ms": duration_ms,
        "exit_code": result.returncode,
        "stderr_path": str(stderr.relative_to(support.ROOT)),
        "stderr_sha256": support.sha256(stderr),
        "stdout_path": str(stdout.relative_to(support.ROOT)),
        "stdout_sha256": support.sha256(stdout),
    }


def rejected(record: dict[str, Any]) -> bool:
    stderr = (
        support.ROOT / str(record["stderr_path"])
    ).read_text(encoding="utf-8")
    return record["exit_code"] != 0 and (
        "postcondition not satisfied" in stderr
        or "assertion failed" in stderr.lower()
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = support.FROM_ITER_PROBE_SOURCE_PATH.read_text(
        encoding="utf-8"
    )
    mutations = {
        "ok_payload": (
            "&& result == Ok(collect_output::<A, V>(payloads))",
            "&& result is Ok",
        ),
        "err_payload": (
            "&& result == Err(items[stop]->Err_0)",
            "&& result is Err",
        ),
        "consumes_after_err": (
            "&& trace == items.take(stop + 1)",
            "&& trace == items",
        ),
    }
    mutants: dict[str, Path] = {}
    for label, (before, after) in mutations.items():
        if source.count(before) != 1:
            raise SystemExit(
                f"projection probe mutation anchor is not unique: {label}"
            )
        path = OUT / f"{label}_mutant.rs"
        path.write_text(source.replace(before, after), encoding="utf-8")
        mutants[label] = path

    lowering = run(
        "lowering", support.FROM_ITER_PROBE_SOURCE_PATH, no_verify=True
    )
    verification = run(
        "verification", support.FROM_ITER_PROBE_SOURCE_PATH
    )
    negative_mutants: dict[str, Any] = {}
    for label, path in mutants.items():
        record = run(f"{label}_mutant", path)
        negative_mutants[label] = {
            **record,
            "rejected_as_expected": rejected(record),
            "sha256": support.sha256(path),
        }
    passed = (
        lowering["exit_code"] == 0
        and verification["exit_code"] == 0
        and all(
            record["rejected_as_expected"]
            for record in negative_mutants.values()
        )
    )
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": (
            "exact_relative_to_projection_erased_collector_law_and_"
            "first_err_consumption_trace"
        ),
        "lowering": lowering,
        "negative_mutants": negative_mutants,
        "schema_version": 1,
        "source_path": str(
            support.FROM_ITER_PROBE_SOURCE_PATH.relative_to(support.ROOT)
        ),
        "source_sha256": support.sha256(
            support.FROM_ITER_PROBE_SOURCE_PATH
        ),
        "status": "passed" if passed else "failed",
        "verification": verification,
        "verus_binary_sha256": support.sha256(VERUS),
        "z3_binary_sha256": support.sha256(Z3),
    }
    support.write_json(support.FROM_ITER_PROBE_REPORT_PATH, report)
    print(
        json.dumps(
            {
                "negative_mutants": len(negative_mutants),
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
