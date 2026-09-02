#!/usr/bin/env python3
"""Independently reconstruct and hash the readable vstd source closure."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT.parent / "verus" / "source" / "vstd"
COPIED = ROOT / "provenance" / "vstd-dependency-closure" / "source" / "vstd"
RETAINED = ROOT / "provenance" / "vstd_dependency_closure.json"
OUTPUT = (
    ROOT / "provenance" / "vstd_dependency_closure_independent_audit.json"
)
TOOLCHAIN = ROOT / "provenance" / "toolchain.json"

MODULE = re.compile(
    r"(?m)^[ \t]*"
    r"(?:#\[path[ \t]*=[ \t]*\"([^\"]+)\"\][ \t]*\n[ \t]*)?"
    r"(?:pub(?:\([^)]*\))?[ \t]+)?"
    r"(?:unsafe[ \t]+)?mod[ \t]+([A-Za-z_]\w*)[ \t]*;"
)
LITERAL_INCLUDE = re.compile(
    r"\binclude!\s*\(\s*\"([^\"]+\.rs)\"\s*\)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def relative_files(root: Path) -> set[Path]:
    files = {
        path.relative_to(root)
        for path in root.rglob("*.rs")
        if path.name != "build.rs"
    }
    files.add(Path("Cargo.toml"))
    return files


def module_target(
    path: Path, path_attr: str | None, name: str
) -> Path | None:
    if path_attr is not None:
        candidate = (path.parent / path_attr).resolve()
        return candidate if candidate.is_file() else None
    base = (
        path.parent
        if path.name in {"lib.rs", "main.rs", "mod.rs", "vstd.rs"}
        else path.parent / path.stem
    )
    candidates = (base / f"{name}.rs", base / name / "mod.rs")
    existing = [candidate for candidate in candidates if candidate.is_file()]
    return existing[0] if len(existing) == 1 else None


def graph_closure(
) -> tuple[set[Path], list[dict[str, Any]], list[dict[str, Any]]]:
    entry = CANONICAL / "vstd.rs"
    queue = deque([entry])
    visited: set[Path] = set()
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    while queue:
        path = queue.popleft().resolve()
        if path in visited:
            continue
        visited.add(path)
        source = path.read_text(encoding="utf-8")
        for match in MODULE.finditer(source):
            target = module_target(path, match.group(1), match.group(2))
            line = source.count("\n", 0, match.start()) + 1
            if target is None:
                unresolved.append(
                    {
                        "kind": "module",
                        "line": line,
                        "module": match.group(2),
                        "source": str(path.relative_to(CANONICAL)),
                    }
                )
                continue
            target = target.resolve()
            edges.append(
                {
                    "kind": "module",
                    "line": line,
                    "source": str(path.relative_to(CANONICAL)),
                    "target": str(target.relative_to(CANONICAL)),
                }
            )
            queue.append(target)
        for match in LITERAL_INCLUDE.finditer(source):
            target = (path.parent / match.group(1)).resolve()
            line = source.count("\n", 0, match.start()) + 1
            if not target.is_file():
                unresolved.append(
                    {
                        "include": match.group(1),
                        "kind": "include",
                        "line": line,
                        "source": str(path.relative_to(CANONICAL)),
                    }
                )
                continue
            edges.append(
                {
                    "kind": "include",
                    "line": line,
                    "source": str(path.relative_to(CANONICAL)),
                    "target": str(target.relative_to(CANONICAL)),
                }
            )
            queue.append(target)
    return (
        {path.relative_to(CANONICAL) for path in visited},
        edges,
        unresolved,
    )


def main() -> int:
    retained = json.loads(RETAINED.read_text(encoding="utf-8"))
    retained_files = {
        Path(row["git_path"]).relative_to("source/vstd")
        for row in retained["closure"]["files"]
    }
    canonical_files = relative_files(CANONICAL)
    copied_files = relative_files(COPIED)
    graph_files, edges, unresolved = graph_closure()
    expected_rust = {
        path for path in canonical_files if path.suffix == ".rs"
    }
    hash_mismatches = []
    for relative in sorted(canonical_files & copied_files):
        canonical_hash = sha256(CANONICAL / relative)
        copied_hash = sha256(COPIED / relative)
        if canonical_hash != copied_hash:
            hash_mismatches.append(
                {
                    "canonical_sha256": canonical_hash,
                    "copied_sha256": copied_hash,
                    "path": str(relative),
                }
            )
    errors = []
    if canonical_files != copied_files:
        errors.append("canonical_copy_file_set_mismatch")
    if canonical_files != retained_files:
        errors.append("retained_manifest_file_set_mismatch")
    if graph_files != expected_rust:
        errors.append("module_include_graph_not_complete")
    if unresolved:
        errors.append("unresolved_module_or_include")
    if hash_mismatches:
        errors.append("canonical_copy_hash_mismatch")
    report = {
        "audit": {
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "implementation_independent_from_freezer": True,
            "method": (
                "Independent filesystem set comparison, byte hashing, and "
                "conservative mod/include traversal from vstd.rs."
            ),
            "script_path": str(Path(__file__).resolve()),
            "script_sha256": sha256(Path(__file__)),
        },
        "errors": errors,
        "graph": {
            "edge_count": len(edges),
            "edges": edges,
            "entrypoint": "vstd.rs",
            "reached_rust_files": len(graph_files),
            "unresolved": unresolved,
            "unreached": sorted(
                str(path) for path in expected_rust - graph_files
            ),
        },
        "hash_mismatches": hash_mismatches,
        "inputs": {
            "retained_manifest_path": str(RETAINED),
            "retained_manifest_sha256": sha256(RETAINED),
        },
        "reconciliation": {
            "canonical_file_count": len(canonical_files),
            "copied_file_count": len(copied_files),
            "retained_file_count": len(retained_files),
            "rust_file_count": len(expected_rust),
        },
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
    }
    write_json(OUTPUT, report)
    if not errors:
        toolchain = json.loads(TOOLCHAIN.read_text(encoding="utf-8"))
        toolchain["commands"]["vstd_dependency_independent_audit"] = [
            str(Path(__file__).resolve()),
        ]
        toolchain["input_policy"]["vstd_dependency_closure_status"] = (
            "passed_conservative_all_cfg_freeze_and_independent_graph_audit"
        )
        write_json(TOOLCHAIN, toolchain)
    print(
        json.dumps(
            {
                "errors": errors,
                "reconciliation": report["reconciliation"],
                "status": report["status"],
                "unreached": len(report["graph"]["unreached"]),
                "unresolved": len(unresolved),
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
