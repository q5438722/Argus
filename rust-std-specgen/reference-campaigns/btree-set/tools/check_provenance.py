#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shlex
import subprocess
import sys
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


class ProvenanceError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ProvenanceError(f"expected a JSON object: {path}")
    return value


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProvenanceError(message)


def validate(campaign_root: Path) -> dict[str, int]:
    survey_root = survey_root_from(campaign_root)
    manifest_path = campaign_root / "provenance/source_manifest.json"
    csv_path = campaign_root / "provenance/source_manifest.csv"
    commands_path = campaign_root / "provenance/commands.json"
    context_path = campaign_root / "provenance/freeze_context.json"
    for path in (manifest_path, csv_path, commands_path, context_path):
        require(path.is_file(), f"missing provenance artifact: {path}")

    manifest = load_json(manifest_path)
    require(manifest.get("schema_version") == 1, "unsupported source manifest schema")
    require(manifest.get("module") == MODULE, "source manifest module mismatch")
    require(manifest.get("rust_version") == RUST_VERSION, "Rust version mismatch")
    require(manifest.get("hash_algorithm") == "sha256", "hash algorithm mismatch")
    records = manifest.get("records")
    require(isinstance(records, list), "source manifest records must be a list")
    require(len(records) == len(INPUTS), "source manifest record count mismatch")
    require(manifest.get("record_count") == len(records), "declared record count mismatch")

    expected = {item.source_path: item for item in INPUTS}
    by_source: dict[str, dict[str, Any]] = {}
    for raw_record in records:
        require(isinstance(raw_record, dict), "source manifest record is not an object")
        record = raw_record
        source_path = record.get("source_path")
        require(isinstance(source_path, str), "source path is missing")
        require(source_path not in by_source, f"duplicate source record: {source_path}")
        by_source[source_path] = record
    require(set(by_source) == set(expected), "source manifest paths differ from freeze policy")

    expected_frozen_paths: set[str] = set()
    for source_path, item in expected.items():
        record = by_source[source_path]
        require(record.get("frozen_path") == item.frozen_path, f"frozen path mismatch: {source_path}")
        require(record.get("role") == item.role, f"role mismatch: {source_path}")
        require(record.get("ownership") == item.ownership, f"ownership mismatch: {source_path}")
        source = survey_root / source_path
        frozen = campaign_root / item.frozen_path
        require(source.is_file(), f"canonical input is missing: {source}")
        require(frozen.is_file(), f"frozen input is missing: {frozen}")
        source_size = source.stat().st_size
        source_hash = sha256_file(source)
        require(record.get("size_bytes") == source_size, f"size drift: {source_path}")
        require(record.get("sha256") == source_hash, f"canonical hash drift: {source_path}")
        require(sha256_file(frozen) == source_hash, f"frozen copy mismatch: {source_path}")
        expected_frozen_paths.add(item.frozen_path)

    frozen_root = campaign_root / "provenance/frozen"
    actual_frozen_paths = {
        path.relative_to(campaign_root).as_posix()
        for path in frozen_root.rglob("*")
        if path.is_file()
    }
    require(
        actual_frozen_paths == expected_frozen_paths,
        "unmanifested or missing files exist under provenance/frozen",
    )

    with csv_path.open(encoding="utf-8", newline="") as source:
        csv_records = list(csv.DictReader(source))
    normalized_json_records = [
        {
            **{key: str(value) for key, value in record.items()},
            "size_bytes": str(record["size_bytes"]),
        }
        for record in records
    ]
    require(csv_records == normalized_json_records, "CSV and JSON source manifests differ")

    commands = load_json(commands_path)
    require(commands.get("schema_version") == 1, "unsupported commands schema")
    require(commands.get("module") == MODULE, "commands module mismatch")
    require(commands.get("working_directory") == ".", "commands working directory mismatch")
    require(commands.get("commands") == list(COMMANDS), "frozen command definitions drifted")

    context = load_json(context_path)
    require(context.get("schema_version") == 1, "unsupported freeze context schema")
    require(context.get("module") == MODULE, "freeze context module mismatch")
    scope = context.get("scope")
    require(isinstance(scope, dict), "scope is missing")
    require(scope.get("public_module") == MODULE, "public module mismatch")
    require(
        scope.get("internal_owner") == "alloc::collections::btree::set",
        "internal target owner mismatch",
    )
    require(scope.get("cfg") == "not(no_global_oom_handling)", "target cfg mismatch")

    artifact_hashes = context.get("artifact_hashes")
    require(isinstance(artifact_hashes, dict), "artifact hashes are missing")
    for path in (manifest_path, csv_path, commands_path):
        relative = path.relative_to(campaign_root).as_posix()
        require(
            artifact_hashes.get(relative) == sha256_file(path),
            f"frozen artifact hash mismatch: {relative}",
        )

    rust_root = survey_root / "rust-1.96"
    verus_root = survey_root / "verus"
    checkouts = context.get("checkouts")
    require(isinstance(checkouts, dict), "checkout context is missing")
    rust_context = checkouts.get("rust")
    verus_context = checkouts.get("verus")
    require(isinstance(rust_context, dict), "Rust checkout context is missing")
    require(isinstance(verus_context, dict), "Verus checkout context is missing")
    rust_head = run(["git", "rev-parse", "HEAD"], rust_root)
    verus_head = run(["git", "rev-parse", "HEAD"], verus_root)
    require(rust_head == RUST_COMMIT == rust_context.get("commit"), "Rust commit drift")
    require(verus_head == VERUS_COMMIT == verus_context.get("commit"), "Verus commit drift")
    rust_status = run(
        ["git", "status", "--short", "--untracked-files=no"], rust_root
    ).splitlines()
    verus_status = run(
        ["git", "status", "--short", "--untracked-files=no"], verus_root
    ).splitlines()
    require(rust_status == rust_context.get("tracked_status"), "Rust tracked status drift")
    require(verus_status == verus_context.get("tracked_status"), "Verus tracked status drift")
    selected_vstd_status = run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=no",
            "--",
            "source/vstd/std_specs/btree.rs",
        ],
        verus_root,
    ).splitlines()
    require(
        selected_vstd_status == verus_context.get("selected_vstd_file_status") == [],
        "selected vstd baseline is modified",
    )

    tools = context.get("tools")
    require(isinstance(tools, dict), "tool context is missing")
    tool_commands = {
        "rustc": ["rustc", "+1.96.0", "--version", "--verbose"],
        "verus": [str(verus_root / "source/target-verus/release/verus"), "--version"],
        "z3": [str(verus_root / "source/target-verus/release/z3"), "--version"],
    }
    for name, command in tool_commands.items():
        frozen_tool = tools.get(name)
        require(isinstance(frozen_tool, dict), f"{name} tool context is missing")
        require(frozen_tool.get("command") == shlex.join(command), f"{name} command drift")
        require(frozen_tool.get("stdout") == run(command), f"{name} version drift")

    rustdoc_path = survey_root / "rustdoc-json-1.96/alloc.json"
    rustdoc_context = context.get("rustdoc")
    require(isinstance(rustdoc_context, dict), "rustdoc context is missing")
    with rustdoc_path.open(encoding="utf-8") as source:
        rustdoc = json.load(source)
    rustdoc_facts = {
        "format_version": rustdoc.get("format_version"),
        "root": rustdoc.get("root"),
        "crate_version": rustdoc.get("crate_version"),
        "includes_private": rustdoc.get("includes_private"),
        "index_items": len(rustdoc.get("index", {})),
        "path_items": len(rustdoc.get("paths", {})),
    }
    for key, value in rustdoc_facts.items():
        require(rustdoc_context.get(key) == value, f"rustdoc {key} drift")
    require(rustdoc_context.get("format_version") == 57, "unexpected rustdoc format")
    require(rustdoc_context.get("includes_private") is False, "rustdoc must exclude private items")

    dependencies = context.get("dependency_acceptance")
    require(isinstance(dependencies, dict), "dependency acceptance is missing")
    require(
        dependencies
        == {
            "alloc::collections::BTreeMap": "unaccepted_narrow_dependency",
            "core::cmp::Ord": "unaccepted_narrow_dependency",
            "core::option::Option": "unaccepted_narrow_dependency",
            "core::ops::RangeBounds": "unaccepted_narrow_dependency",
            "core::ops::FnMut": "unaccepted_narrow_dependency",
        },
        "dependency acceptance changed",
    )
    return {
        "inputs": len(records),
        "frozen_bytes": sum(int(record["size_bytes"]) for record in records),
        "rustdoc_items": rustdoc_facts["index_items"],
    }


def main() -> None:
    campaign_root = campaign_root_from(Path(__file__))
    summary = validate(campaign_root)
    print(
        "provenance check passed: "
        f"inputs={summary['inputs']} "
        f"frozen_bytes={summary['frozen_bytes']} "
        f"rustdoc_items={summary['rustdoc_items']}"
    )


if __name__ == "__main__":
    main()
