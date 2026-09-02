#!/usr/bin/env python3
"""Fail-closed verification for the BTreeMap campaign provenance freeze."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = CAMPAIGN_ROOT / "provenance" / "source_manifest.json"
CSV_PATH = CAMPAIGN_ROOT / "provenance" / "source_manifest.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    count = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return count


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def run_command(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def verify_artifacts(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for artifact in manifest["artifacts"]:
        artifact_id = artifact["id"]
        if artifact_id in seen:
            errors.append(f"duplicate artifact id: {artifact_id}")
            continue
        seen.add(artifact_id)

        canonical = resolve_path(root, artifact["canonical_path"])
        if not canonical.is_file():
            errors.append(f"{artifact_id}: missing canonical file {canonical}")
            continue

        expected_size = artifact["size_bytes"]
        expected_hash = artifact["sha256"]
        expected_lines = artifact["line_count"]
        if canonical.stat().st_size != expected_size:
            errors.append(
                f"{artifact_id}: canonical size {canonical.stat().st_size} != {expected_size}"
            )
        if sha256_file(canonical) != expected_hash:
            errors.append(f"{artifact_id}: canonical SHA256 drift")
        if line_count(canonical) != expected_lines:
            errors.append(f"{artifact_id}: canonical line-count drift")

        frozen_value = artifact["frozen_path"]
        if frozen_value is None:
            if not artifact["scope_treatment"].startswith("hash_reference_only"):
                errors.append(f"{artifact_id}: missing frozen copy without reference-only policy")
            continue

        frozen = resolve_path(root, frozen_value)
        try:
            frozen.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{artifact_id}: frozen copy escapes campaign root")
            continue
        if not frozen.is_file():
            errors.append(f"{artifact_id}: missing frozen copy {frozen}")
            continue
        if frozen.stat().st_size != expected_size:
            errors.append(f"{artifact_id}: frozen size drift")
        if sha256_file(frozen) != expected_hash:
            errors.append(f"{artifact_id}: frozen SHA256 drift")
    return errors


def verify_repositories(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    for repository in manifest["repositories"]:
        repository_id = repository["id"]
        repository_root = resolve_path(root, repository["root"])
        if not repository_root.is_dir():
            errors.append(f"{repository_id}: missing repository root {repository_root}")
            continue

        head = run_command(["git", "rev-parse", "HEAD"], cwd=repository_root)
        if head.returncode != 0:
            errors.append(f"{repository_id}: git rev-parse failed: {head.stderr.strip()}")
            continue
        if head.stdout.strip() != repository["head"]:
            errors.append(f"{repository_id}: HEAD drift")

        exact_tag = repository["exact_tag"]
        if exact_tag is not None:
            tag = run_command(
                ["git", "describe", "--tags", "--exact-match", "HEAD"],
                cwd=repository_root,
            )
            if tag.returncode != 0 or tag.stdout.strip() != exact_tag:
                errors.append(f"{repository_id}: exact tag drift")

        describe = run_command(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=repository_root,
        )
        if describe.returncode != 0 or describe.stdout.strip() != repository["describe"]:
            errors.append(f"{repository_id}: describe/dirty state drift")

        status = run_command(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repository_root,
        )
        if status.returncode != 0:
            errors.append(f"{repository_id}: git status failed: {status.stderr.strip()}")
        elif status.stdout.splitlines() != repository["status_entries"]:
            errors.append(f"{repository_id}: full worktree status drift")

        clean_paths = run_command(
            ["git", "status", "--porcelain=v1", "--", *repository["required_clean_paths"]],
            cwd=repository_root,
        )
        if clean_paths.returncode != 0:
            errors.append(f"{repository_id}: scoped git status failed")
        elif clean_paths.stdout:
            errors.append(f"{repository_id}: required input path is dirty")
    return errors


def verify_tools(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    for tool in manifest["tools"]:
        tool_id = tool["id"]
        tool_path = resolve_path(root, tool["path"])
        if not tool_path.is_file():
            errors.append(f"{tool_id}: missing tool binary {tool_path}")
            continue
        if sha256_file(tool_path) != tool["sha256"]:
            errors.append(f"{tool_id}: binary SHA256 drift")
            continue
        result = run_command([str(tool_path), *tool["version_args"]])
        if result.returncode != 0:
            errors.append(f"{tool_id}: version command failed: {result.stderr.strip()}")
        elif result.stdout.splitlines() != tool["version_stdout"]:
            errors.append(f"{tool_id}: version output drift")
    return errors


def verify_csv_projection(manifest: dict[str, Any], path: Path = CSV_PATH) -> list[str]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    artifacts = manifest["artifacts"]
    if len(rows) != len(artifacts):
        return [f"CSV row count {len(rows)} != JSON artifact count {len(artifacts)}"]

    fields = [
        "id",
        "role",
        "canonical_path",
        "frozen_path",
        "sha256",
        "size_bytes",
        "line_count",
        "repository_id",
        "scope_treatment",
    ]
    for row, artifact in zip(rows, artifacts, strict=True):
        for field in fields:
            expected = artifact[field]
            rendered = "" if expected is None else str(expected)
            if row[field] != rendered:
                errors.append(f"CSV mismatch for {artifact['id']}.{field}")
    return errors


def verify_rustdoc(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    artifact = next(
        item for item in manifest["artifacts"] if item["id"] == manifest["rustdoc"]["artifact_id"]
    )
    path = resolve_path(root, artifact["frozen_path"])
    with path.open(encoding="utf-8") as stream:
        rustdoc = json.load(stream)

    expected = manifest["rustdoc"]
    scalar_fields = ("format_version", "crate_version", "includes_private")
    for field in scalar_fields:
        if rustdoc[field] != expected[field]:
            errors.append(f"rustdoc {field} drift")
    if rustdoc["root"] != expected["root_item_id"]:
        errors.append("rustdoc root item drift")

    matching_paths = [
        (item_id, item)
        for item_id, item in rustdoc["paths"].items()
        if "::".join(item["path"]) == manifest["ownership"]["rustdoc_module_path"]
    ]
    if len(matching_paths) != expected["btree_map_path_count"]:
        errors.append("rustdoc btree_map module path count drift")
    elif (
        matching_paths[0][0] != manifest["ownership"]["rustdoc_path_id"]
        or matching_paths[0][1]["kind"] != "module"
    ):
        errors.append("rustdoc btree_map module identity drift")
    return errors


def verify_ownership(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if manifest["module"] != "alloc::collections::btree_map":
        errors.append("campaign module is not alloc::collections::btree_map")
    if manifest["rust_release"] != "1.96.0":
        errors.append("Rust release is not 1.96.0")
    if manifest["cfg_assumptions"] != ["not(no_global_oom_handling)"]:
        errors.append("unexpected cfg assumptions")

    artifacts = {artifact["id"]: artifact for artifact in manifest["artifacts"]}
    entry = manifest["ownership"]["public_entry"]
    entry_path = resolve_path(root, artifacts[entry["artifact_id"]]["frozen_path"])
    entry_lines = entry_path.read_text(encoding="utf-8").splitlines()
    excerpt = "\n".join(entry_lines[entry["line_start"] - 1 : entry["line_end"]])
    for required in (
        "#[cfg(not(no_global_oom_handling))]",
        "pub mod btree_map",
        "pub use super::btree::map::*",
    ):
        if required not in excerpt:
            errors.append(f"public-entry excerpt missing {required}")

    map_path = resolve_path(root, artifacts["rust_btree_map"]["frozen_path"])
    entry_impl_path = resolve_path(root, artifacts["rust_btree_map_entry"]["frozen_path"])
    if "pub struct BTreeMap<" not in map_path.read_text(encoding="utf-8"):
        errors.append("map owner snapshot lacks BTreeMap")
    entry_text = entry_impl_path.read_text(encoding="utf-8")
    for required in ("pub enum Entry<", "pub struct VacantEntry<", "pub struct OccupiedEntry<"):
        if required not in entry_text:
            errors.append(f"entry owner snapshot lacks {required}")

    if (
        manifest["ownership"]["inventory_status"]
        != "complete_151_stable_executable_rows"
    ):
        errors.append("inventory completion status is missing or stale")
    if (
        manifest["ownership"]["exact_vstd_match_status"]
        != "complete_13_exact_vstd_rows"
    ):
        errors.append("exact-vstd completion status is missing or stale")
    return errors


def verify_manifest(
    manifest: dict[str, Any], root: Path = CAMPAIGN_ROOT
) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("unsupported source manifest schema")
        return errors
    errors.extend(verify_artifacts(manifest, root))
    errors.extend(verify_repositories(manifest, root))
    errors.extend(verify_tools(manifest, root))
    errors.extend(verify_csv_projection(manifest))
    errors.extend(verify_rustdoc(manifest, root))
    errors.extend(verify_ownership(manifest, root))
    return errors


def main() -> int:
    try:
        manifest = load_manifest()
        errors = verify_manifest(manifest)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"provenance verification error: {error}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"provenance verification failed: {len(errors)} error(s)", file=sys.stderr)
        return 1

    copied = sum(artifact["frozen_path"] is not None for artifact in manifest["artifacts"])
    referenced = len(manifest["artifacts"]) - copied
    dirty = sum(len(repository["status_entries"]) for repository in manifest["repositories"])
    print(
        "provenance verification passed: "
        f"{len(manifest['artifacts'])} inputs "
        f"({copied} copied, {referenced} hash-only), "
        f"{len(manifest['repositories'])} repositories, "
        f"{len(manifest['tools'])} tools, "
        f"{dirty} frozen unrelated dirty entries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
