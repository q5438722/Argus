#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.provenance_common import (
    COMMANDS,
    INPUTS,
    MODULE,
    RUST_COMMIT,
    RUST_VERSION,
    VERUS_COMMIT,
    campaign_root_from,
    survey_root_from,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)


def run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout.rstrip()


def command_record(command: list[str], cwd: Path | None = None) -> dict[str, str]:
    return {
        "command": shlex.join(command),
        "stdout": run(command, cwd),
    }


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    fields = (
        "source_path",
        "frozen_path",
        "role",
        "ownership",
        "size_bytes",
        "sha256",
    )
    with temporary.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    os.replace(temporary, path)


def main() -> None:
    campaign_root = campaign_root_from(Path(__file__))
    survey_root = survey_root_from(campaign_root)
    records: list[dict[str, Any]] = []

    for item in INPUTS:
        source = survey_root / item.source_path
        destination = campaign_root / item.frozen_path
        if not source.is_file():
            raise FileNotFoundError(f"required provenance input is missing: {source}")
        atomic_copy(source, destination)
        records.append(
            {
                "source_path": item.source_path,
                "frozen_path": item.frozen_path,
                "role": item.role,
                "ownership": item.ownership,
                "size_bytes": source.stat().st_size,
                "sha256": sha256_file(source),
            }
        )

    frozen_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    role_counts = dict(sorted(Counter(row["role"] for row in records).items()))
    manifest = {
        "schema_version": 1,
        "module": MODULE,
        "rust_version": RUST_VERSION,
        "frozen_at": frozen_at,
        "hash_algorithm": "sha256",
        "record_count": len(records),
        "role_counts": role_counts,
        "records": records,
    }
    manifest_json = campaign_root / "provenance/source_manifest.json"
    manifest_csv = campaign_root / "provenance/source_manifest.csv"
    commands_json = campaign_root / "provenance/commands.json"
    atomic_write(manifest_json, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_csv(manifest_csv, records)
    atomic_write(
        commands_json,
        json.dumps(
            {
                "schema_version": 1,
                "module": MODULE,
                "working_directory": ".",
                "commands": COMMANDS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    rust_root = survey_root / "rust-1.96"
    verus_root = survey_root / "verus"
    rustdoc_path = survey_root / "rustdoc-json-1.96/alloc.json"
    with rustdoc_path.open(encoding="utf-8") as rustdoc_input:
        rustdoc = json.load(rustdoc_input)

    rust_head = run(["git", "rev-parse", "HEAD"], rust_root)
    verus_head = run(["git", "rev-parse", "HEAD"], verus_root)
    if rust_head != RUST_COMMIT:
        raise RuntimeError(f"unexpected Rust commit: {rust_head}")
    if verus_head != VERUS_COMMIT:
        raise RuntimeError(f"unexpected Verus commit: {verus_head}")

    context = {
        "schema_version": 1,
        "module": MODULE,
        "frozen_at": frozen_at,
        "scope": {
            "public_module": MODULE,
            "public_alias": "alloc::collections::BTreeSet",
            "internal_owner": "alloc::collections::btree::set",
            "allocator_api": "unstable and excluded unless a stable signature exposes A",
            "entry_api": "unstable btree_set_entry exclusion evidence only",
            "cfg": "not(no_global_oom_handling)",
        },
        "target_resolution": [
            {
                "source": "rust-1.96/library/alloc/src/collections/mod.rs:25-31",
                "fact": "alloc::collections::btree_set glob re-exports the private btree::set module",
            },
            {
                "source": "rust-1.96/library/alloc/src/collections/mod.rs:47-51",
                "fact": "alloc::collections::BTreeSet is a second alias of btree_set::BTreeSet",
            },
            {
                "source": "rust-1.96/library/alloc/src/collections/btree/mod.rs:12",
                "fact": "the internal owner module is btree::set",
            },
        ],
        "checkouts": {
            "rust": {
                "root": "rust-1.96",
                "commit": rust_head,
                "tracked_status": run(
                    ["git", "status", "--short", "--untracked-files=no"], rust_root
                ).splitlines(),
            },
            "verus": {
                "root": "verus",
                "commit": verus_head,
                "tracked_status": run(
                    ["git", "status", "--short", "--untracked-files=no"], verus_root
                ).splitlines(),
                "selected_vstd_file_status": run(
                    [
                        "git",
                        "status",
                        "--short",
                        "--untracked-files=no",
                        "--",
                        "source/vstd/std_specs/btree.rs",
                    ],
                    verus_root,
                ).splitlines(),
            },
        },
        "tools": {
            "rustc": command_record(["rustc", "+1.96.0", "--version", "--verbose"]),
            "verus": command_record(
                [
                    str(verus_root / "source/target-verus/release/verus"),
                    "--version",
                ]
            ),
            "z3": command_record(
                [str(verus_root / "source/target-verus/release/z3"), "--version"]
            ),
        },
        "rustdoc": {
            "source_path": "rustdoc-json-1.96/alloc.json",
            "format_version": rustdoc.get("format_version"),
            "root": rustdoc.get("root"),
            "crate_version": rustdoc.get("crate_version"),
            "includes_private": rustdoc.get("includes_private"),
            "index_items": len(rustdoc.get("index", {})),
            "path_items": len(rustdoc.get("paths", {})),
            "target_assumption": "x86_64-unknown-linux-gnu host from the frozen rustc toolchain",
        },
        "dependency_acceptance": {
            "alloc::collections::BTreeMap": "unaccepted_narrow_dependency",
            "core::cmp::Ord": "unaccepted_narrow_dependency",
            "core::option::Option": "unaccepted_narrow_dependency",
            "core::ops::RangeBounds": "unaccepted_narrow_dependency",
            "core::ops::FnMut": "unaccepted_narrow_dependency",
        },
        "artifact_hashes": {
            path.relative_to(campaign_root).as_posix(): sha256_file(path)
            for path in (manifest_json, manifest_csv, commands_json)
        },
    }
    atomic_write(
        campaign_root / "provenance/freeze_context.json",
        json.dumps(context, indent=2, sort_keys=True) + "\n",
    )
    print(
        f"frozen {len(records)} inputs for {MODULE}; "
        f"rustdoc_items={context['rustdoc']['index_items']}"
    )


if __name__ == "__main__":
    main()
