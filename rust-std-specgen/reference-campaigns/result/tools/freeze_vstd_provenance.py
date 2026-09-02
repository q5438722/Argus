#!/usr/bin/env python3
"""Freeze the complete readable vstd source closure and verifier runtime."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT.parent
VERUS_REPOSITORY = SURVEY / "verus"
VSTD_ROOT = VERUS_REPOSITORY / "source" / "vstd"
VSTD_ENTRYPOINT = VSTD_ROOT / "vstd.rs"
VSTD_MANIFEST = VSTD_ROOT / "Cargo.toml"
COPY_ROOT = (
    ROOT
    / "provenance"
    / "vstd-dependency-closure"
    / "source"
    / "vstd"
)
OUTPUT = ROOT / "provenance" / "vstd_dependency_closure.json"
TOOLCHAIN = ROOT / "provenance" / "toolchain.json"
VERUS_RELEASE = (
    VERUS_REPOSITORY / "source" / "target-verus" / "release"
)
Z3_BINARY = VERUS_REPOSITORY / "source" / "z3"

MODULE_RE = re.compile(
    r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?"
    r"(?:unsafe\s+)?mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;"
)
PATH_ATTRIBUTE_RE = re.compile(
    r'^#\s*\[\s*path\s*=\s*"([^"]+)"\s*\]\s*$'
)
INCLUDE_RE = re.compile(r'include!\s*\(\s*"([^"]+)"\s*\)')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode())


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run(
    argv: list[str],
    *,
    cwd: Path = VERUS_REPOSITORY,
    binary: bool = False,
) -> str | bytes:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (
            completed.stderr.decode(errors="replace")
            if binary
            else completed.stderr
        )
        raise RuntimeError(
            f"command failed ({completed.returncode}): {argv!r}\n{stderr}"
        )
    return completed.stdout


def relative_git_path(path: Path) -> str:
    return path.relative_to(VERUS_REPOSITORY).as_posix()


def parse_status(stdout: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in stdout.splitlines():
        if len(line) < 4 or line[2] != " ":
            raise ValueError(f"unsupported git status row: {line!r}")
        status = line[:2]
        path = line[3:]
        if path.startswith('"') or " -> " in path:
            raise ValueError(f"ambiguous git status path: {line!r}")
        if path in rows:
            raise ValueError(f"duplicate git status path: {path}")
        rows[path] = status
    return rows


def git_status(pathspec: str | None = None) -> tuple[list[str], str]:
    argv = [
        "git",
        "-c",
        "core.quotePath=false",
        "status",
        "--short",
        "--untracked-files=all",
        "--no-renames",
    ]
    if pathspec is not None:
        argv.extend(["--", pathspec])
    stdout = run(argv)
    assert isinstance(stdout, str)
    return argv, stdout


def tracked_paths() -> set[str]:
    stdout = run(["git", "ls-files", "--", "source/vstd"])
    assert isinstance(stdout, str)
    return {line for line in stdout.splitlines() if line}


def head_file_state(git_path: str) -> tuple[str | None, str | None]:
    oid = subprocess.run(
        ["git", "rev-parse", f"HEAD:{git_path}"],
        cwd=VERUS_REPOSITORY,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if oid.returncode != 0:
        return None, None
    blob = run(["git", "show", f"HEAD:{git_path}"], binary=True)
    assert isinstance(blob, bytes)
    return oid.stdout.strip(), sha256_bytes(blob)


def module_directory(source: Path) -> Path:
    if source == VSTD_ENTRYPOINT or source.name == "mod.rs":
        return source.parent
    return source.parent / source.stem


def source_declarations(source: Path) -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    attributes: list[str] = []
    for line_number, line in enumerate(
        source.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if stripped.startswith("#["):
            attributes.append(stripped)
            continue
        if not stripped or stripped.startswith("//"):
            continue

        module_match = MODULE_RE.match(line)
        if module_match is not None:
            path_attributes = [
                match.group(1)
                for attribute in attributes
                if (match := PATH_ATTRIBUTE_RE.match(attribute)) is not None
            ]
            if len(path_attributes) > 1:
                raise ValueError(
                    f"multiple path attributes at {source}:{line_number}"
                )
            declarations.append(
                {
                    "attributes": list(attributes),
                    "kind": "module",
                    "line": line_number,
                    "module": module_match.group(1),
                    "path_attribute": (
                        path_attributes[0] if path_attributes else None
                    ),
                }
            )

        for include_match in INCLUDE_RE.finditer(line):
            declarations.append(
                {
                    "attributes": list(attributes),
                    "include": include_match.group(1),
                    "kind": "include",
                    "line": line_number,
                }
            )
        attributes = []
    return declarations


def resolve_declaration(
    source: Path, declaration: dict[str, Any]
) -> Path:
    if declaration["kind"] == "include":
        candidate = source.parent / declaration["include"]
    elif declaration["path_attribute"] is not None:
        candidate = source.parent / declaration["path_attribute"]
    else:
        directory = module_directory(source)
        name = declaration["module"]
        candidates = [directory / f"{name}.rs", directory / name / "mod.rs"]
        existing = [candidate for candidate in candidates if candidate.is_file()]
        if len(existing) != 1:
            rendered = ", ".join(str(candidate) for candidate in candidates)
            raise ValueError(
                f"{source}:{declaration['line']} resolves to "
                f"{len(existing)} files ({rendered})"
            )
        candidate = existing[0]

    candidate = candidate.resolve()
    try:
        candidate.relative_to(VSTD_ROOT.resolve())
    except ValueError as error:
        raise ValueError(
            f"vstd dependency escapes source root: {candidate}"
        ) from error
    if not candidate.is_file():
        raise ValueError(f"missing vstd dependency: {candidate}")
    if candidate.is_symlink():
        raise ValueError(f"symlinked vstd dependency is not allowed: {candidate}")
    return candidate


def discover_closure() -> dict[Path, list[dict[str, Any]]]:
    if not VSTD_ENTRYPOINT.is_file():
        raise ValueError(f"missing vstd entrypoint: {VSTD_ENTRYPOINT}")

    reasons: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    entrypoint = VSTD_ENTRYPOINT.resolve()
    reasons[entrypoint].append(
        {"kind": "crate_entrypoint", "source": "source/vstd/Cargo.toml"}
    )
    queue: deque[Path] = deque([entrypoint])
    visited: set[Path] = set()

    while queue:
        source = queue.popleft()
        if source in visited:
            continue
        visited.add(source)
        for declaration in source_declarations(source):
            dependency = resolve_declaration(source, declaration)
            reason = {
                "attributes": declaration["attributes"],
                "kind": declaration["kind"],
                "line": declaration["line"],
                "source": relative_git_path(source),
            }
            if declaration["kind"] == "module":
                reason["module"] = declaration["module"]
            else:
                reason["include"] = declaration["include"]
            reasons[dependency].append(reason)
            if dependency not in visited:
                queue.append(dependency)

    return dict(reasons)


def sync_copies(sources: list[Path]) -> None:
    expected = {
        source.relative_to(VSTD_ROOT).as_posix() for source in sources
    }
    COPY_ROOT.mkdir(parents=True, exist_ok=True)

    for existing in sorted(COPY_ROOT.rglob("*"), reverse=True):
        if existing.is_file():
            relative = existing.relative_to(COPY_ROOT).as_posix()
            if relative not in expected:
                existing.unlink()
    for directory in sorted(COPY_ROOT.rglob("*"), reverse=True):
        if directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                pass

    for source in sources:
        destination = COPY_ROOT / source.relative_to(VSTD_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def runtime_artifacts() -> list[dict[str, Any]]:
    candidates = sorted(
        path for path in VERUS_RELEASE.iterdir() if path.is_file()
    )
    candidates.append(Z3_BINARY)
    rows = []
    for path in candidates:
        if not path.is_file():
            raise ValueError(f"missing verifier runtime input: {path}")
        rows.append(
            {
                "path": relative_git_path(path),
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )
    return rows


def expected_verus_head(toolchain: dict[str, Any]) -> str:
    try:
        return str(toolchain["pins"]["verus"]["commit"])
    except (KeyError, TypeError) as error:
        raise ValueError("toolchain lacks the canonical Verus commit") from error


def build_manifest(*, copy_sources: bool) -> dict[str, Any]:
    toolchain = load_json(TOOLCHAIN)
    expected_head = expected_verus_head(toolchain)
    head = run(["git", "rev-parse", "HEAD"])
    assert isinstance(head, str)
    head = head.strip()
    if head != expected_head:
        raise ValueError(
            f"Verus HEAD changed: expected {expected_head}, observed {head}"
        )

    closure = discover_closure()
    sources = sorted({*closure, VSTD_MANIFEST.resolve()})
    if copy_sources:
        sync_copies(sources)

    vstd_status_argv, vstd_status_stdout = git_status("source/vstd")
    global_status_argv, global_status_stdout = git_status()
    status_map = parse_status(vstd_status_stdout)
    tracked = tracked_paths()
    expected_git_paths = {relative_git_path(source) for source in sources}
    dirty_outside_closure = sorted(set(status_map) - expected_git_paths)
    if dirty_outside_closure:
        raise ValueError(
            "dirty vstd paths escape the frozen conservative closure: "
            + ", ".join(dirty_outside_closure)
        )

    rows = []
    for source in sources:
        relative = source.relative_to(VSTD_ROOT)
        git_path = relative_git_path(source)
        copied = COPY_ROOT / relative
        if not copied.is_file():
            raise ValueError(f"missing frozen vstd copy: {copied}")
        source_hash = sha256(source)
        copied_hash = sha256(copied)
        if copied_hash != source_hash:
            raise ValueError(f"frozen vstd copy differs: {copied}")
        is_tracked = git_path in tracked
        head_oid, head_hash = (
            head_file_state(git_path) if is_tracked else (None, None)
        )
        rows.append(
            {
                "copied_path": copied.relative_to(ROOT).as_posix(),
                "copied_sha256": copied_hash,
                "discovery": (
                    [{"kind": "crate_manifest"}]
                    if source == VSTD_MANIFEST.resolve()
                    else closure[source]
                ),
                "git_path": git_path,
                "git_status": status_map.get(git_path, "clean"),
                "head_git_blob": head_oid,
                "head_sha256": head_hash,
                "sha256": source_hash,
                "size": source.stat().st_size,
                "tracked": is_tracked,
            }
        )

    dirty_rows = [
        {"git_path": path, "git_status": status}
        for path, status in sorted(status_map.items())
    ]
    runtime_rows = runtime_artifacts()
    return {
        "closure": {
            "configuration_mode": "conservative_all_cfg_branches",
            "copy_root": COPY_ROOT.relative_to(ROOT).as_posix(),
            "dirty_file_count": len(dirty_rows),
            "dirty_paths": dirty_rows,
            "dirty_paths_outside_closure": dirty_outside_closure,
            "entrypoint": relative_git_path(VSTD_ENTRYPOINT),
            "file_count": len(rows),
            "files": rows,
            "tracked_file_count": sum(row["tracked"] for row in rows),
            "untracked_file_count": sum(
                not row["tracked"] for row in rows
            ),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "cfg_handling": (
                "Every file-backed module declaration is followed regardless "
                "of cfg attributes so inactive branches remain in the frozen "
                "verifier-source boundary."
            ),
            "copy_policy": (
                "Every reachable Rust source and the vstd Cargo manifest are "
                "copied byte-for-byte beneath the campaign provenance tree."
            ),
            "scope": (
                "Verifier dependency provenance for the core::result campaign; "
                "the closure does not transfer specification claims from any "
                "other Rust module."
            ),
        },
        "runtime": {
            "artifact_count": len(runtime_rows),
            "artifacts": runtime_rows,
            "release_directory": relative_git_path(VERUS_RELEASE),
        },
        "schema_version": 1,
        "status": "passed",
        "verus_repository": {
            "expected_head": expected_head,
            "global_status": {
                "argv": global_status_argv,
                "sha256": sha256_text(global_status_stdout),
                "stdout": global_status_stdout,
            },
            "head": head,
            "root": str(VERUS_REPOSITORY),
            "vstd_status": {
                "argv": vstd_status_argv,
                "sha256": sha256_text(vstd_status_stdout),
                "stdout": vstd_status_stdout,
            },
        },
    }


def main() -> None:
    manifest = build_manifest(copy_sources=True)
    write_json(OUTPUT, manifest)
    toolchain = load_json(TOOLCHAIN)
    toolchain["commands"]["vstd_dependency_freeze"] = [
        str(Path(__file__).resolve()),
    ]
    toolchain["input_policy"]["vstd_dependency_closure_status"] = (
        "frozen_pending_independent_audit"
    )
    write_json(TOOLCHAIN, toolchain)
    print(
        json.dumps(
            {
                "dirty_file_count": manifest["closure"][
                    "dirty_file_count"
                ],
                "file_count": manifest["closure"]["file_count"],
                "output": str(OUTPUT),
                "runtime_artifact_count": manifest["runtime"][
                    "artifact_count"
                ],
                "status": manifest["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
