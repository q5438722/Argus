#!/usr/bin/env python3
"""Run and retain the aggregate Verus contract typecheck."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


VERUS_BIN = (
    support.ROOT.parent
    / "verus"
    / "source"
    / "target-verus"
    / "release"
    / "verus"
)
Z3_PATH = support.ROOT.parent / "verus" / "source" / "z3"
OUTPUT_PATH = support.VERIFICATION_ROOT / "verus_typecheck.json"
STDOUT_PATH = support.VERIFICATION_ROOT / "verus_typecheck.stdout.log"
STDERR_PATH = support.VERIFICATION_ROOT / "verus_typecheck.stderr.log"


def main() -> int:
    if not VERUS_BIN.is_file() or not Z3_PATH.is_file():
        raise SystemExit("pinned Verus or Z3 binary is missing")
    command = [
        str(VERUS_BIN),
        "--crate-type=lib",
        "--triggers-mode",
        "silent",
        "--no-verify",
        str(support.CONTRACT_PATH),
    ]
    environment = dict(os.environ)
    environment["VERUS_Z3_PATH"] = str(Z3_PATH)
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=support.ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=110,
            check=False,
        )
    except subprocess.TimeoutExpired as exception:
        timed_out = True
        result = subprocess.CompletedProcess(
            command,
            124,
            stdout=exception.stdout or "",
            stderr=exception.stderr or "",
        )
    duration_ms = int((time.monotonic() - started) * 1000)
    STDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STDOUT_PATH.write_text(str(result.stdout), encoding="utf-8")
    STDERR_PATH.write_text(str(result.stderr), encoding="utf-8")
    verus_version = subprocess.check_output(
        [str(VERUS_BIN), "--version"], text=True
    ).strip()
    z3_version = subprocess.check_output(
        [str(Z3_PATH), "--version"], text=True
    ).strip()
    passed = result.returncode == 0 and not timed_out
    payload = {
        "command": command,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "environment": {"VERUS_Z3_PATH": str(Z3_PATH)},
        "exit_code": result.returncode,
        "inputs": {
            "catalog_sha256": support.sha256(support.CATALOG_PATH),
            "contracts_sha256": support.sha256(support.CONTRACT_PATH),
            "inventory_sha256": support.sha256(support.INVENTORY_PATH),
            "vocabulary_sha256": support.sha256(
                support.VOCABULARY_PATH
            ),
        },
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": support.sha256(Path(__file__)),
        "schema_version": 1,
        "started_at_utc": started_at,
        "status": "passed" if passed else "failed",
        "stderr_path": str(STDERR_PATH.relative_to(support.ROOT)),
        "stderr_sha256": support.sha256(STDERR_PATH),
        "stdout_path": str(STDOUT_PATH.relative_to(support.ROOT)),
        "stdout_sha256": support.sha256(STDOUT_PATH),
        "timed_out": timed_out,
        "tools": {
            "verus_binary": str(VERUS_BIN),
            "verus_binary_sha256": support.sha256(VERUS_BIN),
            "verus_version": verus_version,
            "z3_binary": str(Z3_PATH),
            "z3_binary_sha256": support.sha256(Z3_PATH),
            "z3_version": z3_version,
        },
    }
    support.write_json(OUTPUT_PATH, payload)
    print(
        json.dumps(
            {
                "duration_ms": duration_ms,
                "exit_code": result.returncode,
                "status": payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
