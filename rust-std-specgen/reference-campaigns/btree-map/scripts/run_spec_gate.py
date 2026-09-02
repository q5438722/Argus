#!/usr/bin/env python3
"""Capture hash-bound Verus evidence for the BTreeMap specification package."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
EVIDENCE = ROOT / "specs/evidence"
INPUTS = {
    "generated_source": ROOT / "specs/generated_btree_map_specs.rs",
    "shared_vocabulary": ROOT / "specs/btree_map_shared_vocabulary.rs",
    "all_specs_catalog": ROOT / "specs/all_btree_map_specs.json",
    "inventory": ROOT / "inventory/btree_map_exec_fn_inventory.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def run(name: str, *, no_verify: bool) -> bool:
    source = INPUTS["generated_source"]
    command = [
        str(VERUS),
        "--crate-type=lib",
        "--triggers-mode",
        "silent",
    ]
    if no_verify:
        command.append("--no-verify")
    command.append(str(source))
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    duration_ms = round((time.monotonic() - started) * 1000)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"{name}.command").write_text(shlex.join(command) + "\n")
    (EVIDENCE / f"{name}.stdout").write_text(completed.stdout)
    (EVIDENCE / f"{name}.stderr").write_text(completed.stderr)
    (EVIDENCE / f"{name}.rc").write_text(f"{completed.returncode}\n")
    inputs = {
        key: {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for key, path in INPUTS.items()
    }
    payload = {
        "schema_version": 2,
        "name": name,
        "command": command,
        "cwd": str(ROOT),
        "completed_at": now(),
        "duration_ms": duration_ms,
        "mode": "no_verify" if no_verify else "actual_verus",
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "inputs": inputs,
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
    }
    atomic_json(EVIDENCE / f"{name}.json", payload)
    return payload["passed"]


def main() -> int:
    no_verify = run("generated_spec_no_verify", no_verify=True)
    actual = run("generated_spec_actual_verus", no_verify=False)
    print(
        "BTreeMap specification Verus gate: "
        f"no_verify={'passed' if no_verify else 'failed'}, "
        f"actual_verus={'passed' if actual else 'failed'}"
    )
    return 0 if no_verify and actual else 1


if __name__ == "__main__":
    raise SystemExit(main())
