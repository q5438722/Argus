#!/usr/bin/env python3
"""Build, capture, and verify immutable inputs for the core::cmp campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = 1
EXPECTED_CAMPAIGN_NAME = "nanvix-rust-std-cmp-regeneration-20260901-v011-8798"
CAMPAIGN_MODULE = "core::cmp"
RUST_RELEASE = "1.96.0"
CAMPAIGN_SCOPE = (
    "stable executable APIs publicly reachable through core::cmp in Rust 1.96"
)
PRESERVATION_POLICY = {
    "canonical_checkouts": "read_only_git_state_binding",
    "negative_lessons_workspace": (
        "metadata_only_guard; workspace file contents are neither copied nor read"
    ),
}
CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
SURVEY_ROOT = CAMPAIGN_ROOT.parent
RUST_ROOT = SURVEY_ROOT / "rust-1.96"
VERUS_ROOT = SURVEY_ROOT / "verus"
NEGATIVE_LESSONS_ROOT = (
    SURVEY_ROOT / "nanvix-rust-std-next-six-modules-2026-08-25"
)
PROCESS_DOCUMENT = (
    Path.home()
    / ".argus-skill/workspaces/s-8d9b336f/research/rust-std-lib-specgen-process.md"
)
SLICE_VEC_TRUST_AUDIT = (
    SURVEY_ROOT
    / "nanvix-rust-std-slice-vec-implproof-2026-08-12/TRUST_BOUNDARY_AUDIT.md"
)
PROVENANCE_DIR = CAMPAIGN_ROOT / "provenance"
RUSTDOC_TARGET = PROVENANCE_DIR / "rustdoc-target"
RUSTDOC_JSON = RUSTDOC_TARGET / "doc" / "core.json"
RUSTDOC_BUILD_RESULT = PROVENANCE_DIR / "rustdoc_generation.json"
VERUS_BINARY = VERUS_ROOT / "source" / "target-verus" / "release" / "verus"
Z3_BINARY = VERUS_ROOT / "source" / "z3"
RUST_TOOLCHAIN_ROOT = (
    Path.home() / ".rustup/toolchains/1.96.0-x86_64-unknown-linux-gnu"
)
RUSTC_BINARY = RUST_TOOLCHAIN_ROOT / "bin" / "rustc"
CARGO_BINARY = RUST_TOOLCHAIN_ROOT / "bin" / "cargo"
RUSTDOC_BINARY = RUST_TOOLCHAIN_ROOT / "bin" / "rustdoc"
SOURCE_MANIFEST_JSON = PROVENANCE_DIR / "source_manifest.json"
SOURCE_MANIFEST_CSV = PROVENANCE_DIR / "source_manifest.csv"
PRESERVATION_MANIFEST = PROVENANCE_DIR / "preservation_baseline.json"
CAMPAIGN_MANIFEST = PROVENANCE_DIR / "campaign_provenance.json"
VALIDATION_RESULT = PROVENANCE_DIR / "validation" / "provenance_check.json"

GIT_EXECUTABLE_TEXT = shutil.which("git")
if GIT_EXECUTABLE_TEXT is None:
    raise RuntimeError("git is required to capture campaign provenance")
GIT_EXECUTABLE = Path(GIT_EXECUTABLE_TEXT).resolve()
CARGO_DRIVER_TEXT = shutil.which("cargo")
if CARGO_DRIVER_TEXT is None:
    raise RuntimeError("cargo is required to build the Rust 1.96 rustdoc inventory")
CARGO_DRIVER = Path(CARGO_DRIVER_TEXT)


class ProvenanceError(RuntimeError):
    """A provenance input, artifact, or command did not satisfy its contract."""


@dataclass(frozen=True)
class SourceInput:
    identifier: str
    role: str
    source_root: str
    source_path: Path
    source_relpath: str
    snapshot_relpath: str


@dataclass(frozen=True)
class HashedInput:
    identifier: str
    role: str
    path: Path


@dataclass(frozen=True)
class ToolInput:
    identifier: str
    path: Path
    version_args: tuple[str, ...]


def source_input(
    identifier: str,
    role: str,
    source_root: str,
    root: Path,
    relative_path: str,
) -> SourceInput:
    return SourceInput(
        identifier,
        role,
        source_root,
        root / relative_path,
        relative_path,
        f"provenance/snapshots/{source_root}/{relative_path}",
    )


SOURCE_INPUTS = (
    source_input(
        "rust_core_cmp_export",
        "canonical_core_cmp_public_export",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/lib.rs",
    ),
    source_input(
        "rust_std_cmp_reexport",
        "std_cmp_alias_collapse_evidence",
        "rust-1.96",
        RUST_ROOT,
        "library/std/src/lib.rs",
    ),
    source_input(
        "rust_core_prelude_cmp_reexports",
        "prelude_alias_collapse_evidence",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/prelude/v1.rs",
    ),
    source_input(
        "rust_core_cmp",
        "public_api_default_body_and_effective_impl_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/cmp.rs",
    ),
    source_input(
        "rust_core_cmp_bytewise",
        "bytewise_equality_and_ordering_specialization_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/cmp/bytewise.rs",
    ),
    source_input(
        "rust_core_slice_cmp",
        "generic_and_bytewise_slice_comparison_dispatch_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/slice/cmp.rs",
    ),
    source_input(
        "rust_core_array_equality",
        "array_comparison_forwarding_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/array/equality.rs",
    ),
    source_input(
        "rust_core_array_module",
        "array_ordering_forwarding_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/array/mod.rs",
    ),
    source_input(
        "rust_core_tuple",
        "tuple_comparison_effective_impl_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/tuple.rs",
    ),
    source_input(
        "rust_core_option",
        "option_comparison_effective_impl_source",
        "rust-1.96",
        RUST_ROOT,
        "library/core/src/option.rs",
    ),
    source_input(
        "vstd_cmp",
        "exact_vstd_cmp_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/cmp.rs",
    ),
    source_input(
        "vstd_ordering",
        "exact_vstd_ordering_contract_candidate_and_dirty_input",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/ordering.rs",
    ),
    source_input(
        "vstd_num",
        "primitive_comparison_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/num.rs",
    ),
    source_input(
        "vstd_option",
        "option_comparison_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/option.rs",
    ),
    source_input(
        "vstd_vec",
        "sequence_comparison_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/vec.rs",
    ),
    source_input(
        "vstd_raw_ptr",
        "pointer_comparison_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/raw_ptr.rs",
    ),
    source_input(
        "vstd_string",
        "string_comparison_contract_candidate_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/string.rs",
    ),
    source_input(
        "vstd_laws_cmp",
        "comparison_law_dependency_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/laws_cmp.rs",
    ),
    source_input(
        "vstd_laws_eq",
        "equality_law_dependency_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/laws_eq.rs",
    ),
    source_input(
        "vstd_std_specs_module",
        "vstd_contract_loading_and_dirty_state_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/std_specs/mod.rs",
    ),
    source_input(
        "vstd_root",
        "vstd_loading_and_dirty_state_source",
        "verus",
        VERUS_ROOT,
        "source/vstd/vstd.rs",
    ),
    source_input(
        "authoritative_process",
        "authoritative_campaign_process",
        "process",
        PROCESS_DOCUMENT.parent,
        PROCESS_DOCUMENT.name,
    ),
    source_input(
        "slice_vec_trust_audit",
        "reviewed_comparison_and_trust_accounting_methodology",
        "precedent",
        SLICE_VEC_TRUST_AUDIT.parent,
        SLICE_VEC_TRUST_AUDIT.name,
    ),
)

HASHED_INPUTS = (
    HashedInput(
        "rustdoc_core_json",
        "machine_readable_inventory_source",
        RUSTDOC_JSON,
    ),
)

TOOL_INPUTS = (
    ToolInput("rustc_1_96", RUSTC_BINARY, ("--version", "--verbose")),
    ToolInput("cargo_1_96", CARGO_BINARY, ("--version",)),
    ToolInput("rustdoc_1_96", RUSTDOC_BINARY, ("--version", "--verbose")),
    ToolInput("verus", VERUS_BINARY, ("--version",)),
    ToolInput("z3", Z3_BINARY, ("--version",)),
    ToolInput("git", GIT_EXECUTABLE, ("--version",)),
    ToolInput("python", Path(sys.executable).resolve(), ("--version",)),
)

CAMPAIGN_VALIDATION_SOURCES = (
    ".gitignore",
    "tools/__init__.py",
    "tools/provenance.py",
    "tests/__init__.py",
    "tests/test_provenance.py",
)

SOURCE_CSV_FIELDS = (
    "identifier",
    "role",
    "source_root",
    "source_path",
    "source_relpath",
    "snapshot_path",
    "captured_at_utc",
    "size_bytes",
    "sha256",
    "snapshot_size_bytes",
    "snapshot_sha256",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise ProvenanceError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_path = Path(stream.name)
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise ProvenanceError(f"cannot write {path}: {error}") from error


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json_bytes(value))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProvenanceError(f"cannot read valid JSON from {path}: {error}") from error


def run_command(command: Sequence[str], cwd: Path | None = None) -> bytes:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ProvenanceError(f"cannot execute {command!r}: {error}") from error
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(
            f"command failed with exit {result.returncode}: {command!r}: {stderr}"
        )
    return result.stdout


def rustdoc_command_contract() -> dict[str, dict[str, Any]]:
    manifest_path = RUST_ROOT / "library/Cargo.toml"
    return {
        "clean": {
            "argv": [
                str(CARGO_DRIVER),
                "+1.96.0",
                "clean",
                "--manifest-path",
                str(manifest_path),
                "-p",
                "core",
                "--target-dir",
                str(RUSTDOC_TARGET),
            ],
            "command": (
                "RUSTC_BOOTSTRAP=1 cargo +1.96.0 clean "
                f"--manifest-path {shlex.quote(str(manifest_path))} -p core "
                f"--target-dir {shlex.quote(str(RUSTDOC_TARGET))}"
            ),
            "environment_overrides": {"RUSTC_BOOTSTRAP": "1"},
            "working_directory": str(CAMPAIGN_ROOT),
        },
        "rustdoc": {
            "argv": [
                str(CARGO_DRIVER),
                "+1.96.0",
                "rustdoc",
                "--manifest-path",
                str(manifest_path),
                "-p",
                "core",
                "--lib",
                "--",
                "-Z",
                "unstable-options",
                "--output-format",
                "json",
            ],
            "command": (
                f"CARGO_TARGET_DIR={shlex.quote(str(RUSTDOC_TARGET))} "
                "RUSTC_BOOTSTRAP=1 cargo +1.96.0 rustdoc "
                f"--manifest-path {shlex.quote(str(manifest_path))} -p core --lib "
                "-- -Z unstable-options --output-format json"
            ),
            "environment_overrides": {
                "CARGO_TARGET_DIR": str(RUSTDOC_TARGET),
                "RUSTC_BOOTSTRAP": "1",
            },
            "working_directory": str(CAMPAIGN_ROOT),
        },
    }


def run_recorded_command(contract: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    started_at = utc_now()
    started_ns = time.monotonic_ns()
    environment = os.environ.copy()
    environment.update(contract["environment_overrides"])
    try:
        result = subprocess.run(
            contract["argv"],
            cwd=CAMPAIGN_ROOT,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        timed_out = False
        return_code: int | None = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        return_code = None
        stdout = error.stdout or b""
        stderr = error.stderr or b""
    except OSError as error:
        raise ProvenanceError(
            f"cannot execute rustdoc command {contract['command']!r}: {error}"
        ) from error
    completed_at = utc_now()
    return {
        **contract,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "duration_ms": (time.monotonic_ns() - started_ns) // 1_000_000,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "exit_code": return_code,
        "stdout": decode_command_output(stdout, "rustdoc command stdout"),
        "stderr": decode_command_output(stderr, "rustdoc command stderr"),
    }


def rustdoc_file_record() -> dict[str, Any]:
    if not RUSTDOC_JSON.is_file():
        raise ProvenanceError(f"generated rustdoc JSON is missing: {RUSTDOC_JSON}")
    return {
        "path": RUSTDOC_JSON.relative_to(CAMPAIGN_ROOT).as_posix(),
        "size_bytes": RUSTDOC_JSON.stat().st_size,
        "sha256": sha256_file(RUSTDOC_JSON),
    }


def build_rustdoc(refresh: bool, timeout_seconds: int) -> None:
    assert_layout()
    if (RUSTDOC_BUILD_RESULT.exists() or RUSTDOC_JSON.exists()) and not refresh:
        raise ProvenanceError(
            "rustdoc evidence already exists; use build-rustdoc --refresh only "
            "after an intentional rebuild"
        )

    contracts = rustdoc_command_contract()
    steps: dict[str, dict[str, Any]] = {}
    for name in ("clean", "rustdoc"):
        steps[name] = run_recorded_command(contracts[name], timeout_seconds)
        if steps[name]["exit_code"] != 0 or steps[name]["timed_out"]:
            result = {
                "schema_version": SCHEMA_VERSION,
                "status": "fail",
                "rust_release": RUST_RELEASE,
                "module": CAMPAIGN_MODULE,
                "steps": steps,
            }
            write_json(RUSTDOC_BUILD_RESULT, result)
            raise ProvenanceError(
                f"Rust 1.96 rustdoc {name} step did not complete successfully"
            )

    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "rust_release": RUST_RELEASE,
        "module": CAMPAIGN_MODULE,
        "steps": steps,
        "generated_core_json": rustdoc_file_record(),
    }
    write_json(RUSTDOC_BUILD_RESULT, result)
    print(
        "built Rust 1.96 core rustdoc JSON: "
        f"{result['generated_core_json']['size_bytes']} bytes, "
        f"sha256 {result['generated_core_json']['sha256']}"
    )


def validate_rustdoc_generation() -> dict[str, Any]:
    result = read_json(RUSTDOC_BUILD_RESULT)
    require_equal("rustdoc evidence schema", result.get("schema_version"), SCHEMA_VERSION)
    require_equal("rustdoc evidence status", result.get("status"), "pass")
    require_equal("rustdoc evidence Rust release", result.get("rust_release"), RUST_RELEASE)
    require_equal("rustdoc evidence module", result.get("module"), CAMPAIGN_MODULE)
    contracts = rustdoc_command_contract()
    steps = result.get("steps")
    if not isinstance(steps, dict):
        raise ProvenanceError("rustdoc evidence has no command steps")
    for name, contract in contracts.items():
        step = steps.get(name)
        if not isinstance(step, dict):
            raise ProvenanceError(f"rustdoc evidence has no {name} step")
        for field, expected in contract.items():
            require_equal(f"rustdoc {name} {field}", step.get(field), expected)
        require_equal(f"rustdoc {name} exit code", step.get("exit_code"), 0)
        require_equal(f"rustdoc {name} timeout status", step.get("timed_out"), False)
        if not isinstance(step.get("stdout"), str) or not isinstance(
            step.get("stderr"), str
        ):
            raise ProvenanceError(f"rustdoc {name} output is not retained as text")
    generated_record = rustdoc_file_record()
    require_equal(
        "generated rustdoc JSON",
        result.get("generated_core_json"),
        generated_record,
    )
    return generated_record


def run_optional_branch(root: Path) -> str | None:
    command = [
        str(GIT_EXECUTABLE),
        "-C",
        str(root),
        "symbolic-ref",
        "--short",
        "-q",
        "HEAD",
    ]
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(
            f"branch query failed with exit {result.returncode}: {stderr}"
        )
    return result.stdout.decode("utf-8").strip()


def decode_command_output(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProvenanceError(f"{label} produced non-UTF-8 output") from error


def git_output(root: Path, *arguments: str) -> bytes:
    return run_command(
        [str(GIT_EXECUTABLE), "-C", str(root), *arguments],
    )


def nul_paths(data: bytes, label: str) -> list[str]:
    paths: list[str] = []
    for raw_path in data.split(b"\0"):
        if not raw_path:
            continue
        try:
            paths.append(os.fsdecode(raw_path))
        except UnicodeDecodeError as error:
            raise ProvenanceError(f"{label} contains a non-decodable path") from error
    return paths


def filesystem_path_state(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return {"path": relative_path, "type": "missing"}
    mode = path_stat.st_mode
    base: dict[str, Any] = {
        "path": relative_path,
        "mode": f"{stat.S_IMODE(mode):04o}",
        "size_bytes": path_stat.st_size,
    }
    if stat.S_ISREG(mode):
        return {**base, "type": "regular", "sha256": sha256_file(path)}
    if stat.S_ISLNK(mode):
        target = os.readlink(path)
        return {
            **base,
            "type": "symlink",
            "target": target,
            "target_sha256": sha256_bytes(os.fsencode(target)),
        }
    if stat.S_ISDIR(mode):
        return {**base, "type": "directory"}
    return {**base, "type": "other"}


def git_state(identifier: str, root: Path) -> dict[str, Any]:
    status_text_bytes = git_output(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    status_z = git_output(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    changed = nul_paths(
        git_output(root, "diff", "--name-only", "-z", "HEAD", "--"),
        f"{identifier} changed paths",
    )
    untracked = nul_paths(
        git_output(root, "ls-files", "--others", "--exclude-standard", "-z"),
        f"{identifier} untracked paths",
    )
    dirty_paths = sorted(set(changed + untracked))
    status_text = decode_command_output(status_text_bytes, f"{identifier} git status")
    return {
        "identifier": identifier,
        "root": str(root),
        "head": decode_command_output(
            git_output(root, "rev-parse", "HEAD"),
            f"{identifier} HEAD",
        ).strip(),
        "head_tree": decode_command_output(
            git_output(root, "rev-parse", "HEAD^{tree}"),
            f"{identifier} HEAD tree",
        ).strip(),
        "head_commit_time": decode_command_output(
            git_output(root, "show", "-s", "--format=%cI", "HEAD"),
            f"{identifier} commit time",
        ).strip(),
        "branch": run_optional_branch(root),
        "describe": decode_command_output(
            git_output(root, "describe", "--always", "--dirty", "--broken"),
            f"{identifier} describe",
        ).strip(),
        "is_clean": not status_z,
        "status_porcelain_v1": status_text,
        "status_porcelain_v1_z_sha256": sha256_bytes(status_z),
        "head_diff_binary_sha256": sha256_bytes(
            git_output(root, "diff", "--binary", "HEAD", "--")
        ),
        "submodule_status_recursive": decode_command_output(
            git_output(root, "submodule", "status", "--recursive"),
            f"{identifier} submodule status",
        ),
        "dirty_paths": [
            filesystem_path_state(root, relative_path)
            for relative_path in dirty_paths
        ],
    }


def entry_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def metadata_tree_fingerprint(root: Path) -> dict[str, Any]:
    """Hash path/lstat metadata without reading protected file contents."""
    if not root.is_dir():
        raise ProvenanceError(f"protected root is not a directory: {root}")

    records: list[dict[str, Any]] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as error:
            raise ProvenanceError(
                f"cannot scan protected directory {directory}: {error}"
            ) from error
        for entry in entries:
            path = Path(entry.path)
            try:
                path_stat = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise ProvenanceError(
                    f"cannot stat protected entry {path}: {error}"
                ) from error
            relative_path = path.relative_to(root).as_posix()
            kind = entry_type(path_stat.st_mode)
            record: dict[str, Any] = {
                "path": relative_path,
                "type": kind,
                "mode": f"{stat.S_IMODE(path_stat.st_mode):04o}",
                "size_bytes": path_stat.st_size,
                "mtime_ns": path_stat.st_mtime_ns,
            }
            if kind == "symlink":
                record["target"] = os.readlink(path)
            records.append(record)
            if kind == "directory":
                pending.append(path)

    root_stat = root.lstat()
    records.append(
        {
            "path": ".",
            "type": "directory",
            "mode": f"{stat.S_IMODE(root_stat.st_mode):04o}",
            "size_bytes": root_stat.st_size,
            "mtime_ns": root_stat.st_mtime_ns,
        }
    )
    records.sort(key=lambda record: record["path"])

    digest = hashlib.sha256()
    counts = {"directory": 0, "regular": 0, "symlink": 0, "other": 0}
    total_regular_bytes = 0
    for record in records:
        digest.update(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
        counts[record["type"]] += 1
        if record["type"] == "regular":
            total_regular_bytes += record["size_bytes"]

    return {
        "root": str(root),
        "method": "sorted_relative_path_and_lstat_metadata_sha256_v1",
        "content_bytes_read": 0,
        "entry_count_including_root": len(records),
        "entry_type_counts": counts,
        "total_regular_bytes": total_regular_bytes,
        "metadata_sha256": digest.hexdigest(),
    }


def source_records(captured_at: str, write_snapshots: bool) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in SOURCE_INPUTS:
        try:
            source_bytes = source.source_path.read_bytes()
        except OSError as error:
            raise ProvenanceError(f"cannot read source input {source.source_path}: {error}") from error
        snapshot_path = CAMPAIGN_ROOT / source.snapshot_relpath
        if write_snapshots and (
            not snapshot_path.is_file()
            or snapshot_path.read_bytes() != source_bytes
        ):
            atomic_write(snapshot_path, source_bytes)
        if not snapshot_path.is_file():
            raise ProvenanceError(f"source snapshot is missing: {snapshot_path}")
        records.append(
            {
                "identifier": source.identifier,
                "role": source.role,
                "source_root": source.source_root,
                "source_path": str(source.source_path),
                "source_relpath": source.source_relpath,
                "snapshot_path": source.snapshot_relpath,
                "captured_at_utc": captured_at,
                "size_bytes": len(source_bytes),
                "sha256": sha256_bytes(source_bytes),
                "snapshot_size_bytes": snapshot_path.stat().st_size,
                "snapshot_sha256": sha256_file(snapshot_path),
            }
        )
    return records


def source_manifest_csv(records: Sequence[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=SOURCE_CSV_FIELDS,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


def hashed_input_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in HASHED_INPUTS:
        if not item.path.is_file():
            raise ProvenanceError(f"hashed input is missing: {item.path}")
        records.append(
            {
                "identifier": item.identifier,
                "role": item.role,
                "path": str(item.path),
                "size_bytes": item.path.stat().st_size,
                "sha256": sha256_file(item.path),
            }
        )
    return records


def tool_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for tool in TOOL_INPUTS:
        if not tool.path.is_file():
            raise ProvenanceError(f"tool binary is missing: {tool.path}")
        command = [str(tool.path), *tool.version_args]
        try:
            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise ProvenanceError(f"cannot execute tool {tool.identifier}: {error}") from error
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise ProvenanceError(
                f"{tool.identifier} version command failed with exit "
                f"{result.returncode}: {stderr}"
            )
        records.append(
            {
                "identifier": tool.identifier,
                "path": str(tool.path),
                "size_bytes": tool.path.stat().st_size,
                "sha256": sha256_file(tool.path),
                "version_command": command,
                "version_stdout": decode_command_output(
                    result.stdout, f"{tool.identifier} --version stdout"
                ),
                "version_stderr": decode_command_output(
                    result.stderr, f"{tool.identifier} --version stderr"
                ),
            }
        )
    return records


def environment_record() -> dict[str, Any]:
    selected_names = (
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "RUSTUP_TOOLCHAIN",
        "RUSTFLAGS",
        "SOURCE_DATE_EPOCH",
        "TZ",
        "VERUS_Z3_PATH",
    )
    return {
        "operating_system": platform.system(),
        "kernel_release": platform.release(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "byte_order": sys.byteorder,
        "required_working_directory": str(CAMPAIGN_ROOT),
        "selected_environment_variables": {
            name: os.environ.get(name) for name in selected_names
        },
    }


def expected_campaign_record() -> dict[str, str]:
    return {
        "module": CAMPAIGN_MODULE,
        "rust_release": RUST_RELEASE,
        "campaign_root": str(CAMPAIGN_ROOT),
        "scope": CAMPAIGN_SCOPE,
        "artifact_write_boundary": str(CAMPAIGN_ROOT),
    }


def expected_command_records() -> dict[str, Any]:
    return {
        "rustdoc_build": {
            "working_directory": str(CAMPAIGN_ROOT),
            "command": "python3 tools/provenance.py build-rustdoc --timeout 120",
        },
        "rustdoc_rebuild": {
            "working_directory": str(CAMPAIGN_ROOT),
            "command": (
                "python3 tools/provenance.py build-rustdoc --refresh --timeout 120"
            ),
        },
        "capture": {
            "working_directory": str(CAMPAIGN_ROOT),
            "command": "python3 tools/provenance.py capture",
            "resolved_python_argv": [
                str(Path(sys.executable).resolve()),
                "tools/provenance.py",
                "capture",
            ],
        },
        "intentional_refresh": {
            "working_directory": str(CAMPAIGN_ROOT),
            "command": "python3 tools/provenance.py capture --refresh",
        },
        "stale_input_check": {
            "working_directory": str(CAMPAIGN_ROOT),
            "command": "python3 tools/provenance.py check --record",
        },
    }


def campaign_file_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative_path in CAMPAIGN_VALIDATION_SOURCES:
        path = CAMPAIGN_ROOT / relative_path
        if not path.is_file():
            raise ProvenanceError(f"campaign validation source is missing: {path}")
        records.append(
            {
                "path": relative_path,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def relative_artifact_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(CAMPAIGN_ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def assert_layout() -> None:
    if CAMPAIGN_ROOT.name != EXPECTED_CAMPAIGN_NAME:
        raise ProvenanceError(
            f"collector is in {CAMPAIGN_ROOT.name!r}, expected "
            f"{EXPECTED_CAMPAIGN_NAME!r}"
        )
    if Path.cwd().resolve() != CAMPAIGN_ROOT:
        raise ProvenanceError(
            f"run from {CAMPAIGN_ROOT}, not {Path.cwd().resolve()}"
        )
    for root in (RUST_ROOT, VERUS_ROOT, NEGATIVE_LESSONS_ROOT):
        if not root.is_dir():
            raise ProvenanceError(f"required input directory is missing: {root}")
    for path in (PROCESS_DOCUMENT, SLICE_VEC_TRUST_AUDIT):
        if not path.is_file():
            raise ProvenanceError(f"required methodology input is missing: {path}")


def capture(refresh: bool) -> None:
    assert_layout()
    existing_manifests = [
        path
        for path in (
            SOURCE_MANIFEST_JSON,
            SOURCE_MANIFEST_CSV,
            PRESERVATION_MANIFEST,
            CAMPAIGN_MANIFEST,
        )
        if path.exists()
    ]
    if existing_manifests and not refresh:
        paths = ", ".join(str(path) for path in existing_manifests)
        raise ProvenanceError(
            f"provenance already exists ({paths}); use capture --refresh "
            "only after an intentional input change"
        )

    captured_at = utc_now()
    rustdoc_record = validate_rustdoc_generation()
    records = source_records(captured_at, write_snapshots=True)
    rust_state = git_state("rust-1.96", RUST_ROOT)
    verus_state = git_state("verus", VERUS_ROOT)
    negative_lessons_guard = metadata_tree_fingerprint(NEGATIVE_LESSONS_ROOT)
    tools = tool_records()
    hashed_inputs = hashed_input_records()
    validation_sources = campaign_file_records()

    source_json = {
        "schema_version": SCHEMA_VERSION,
        "module": CAMPAIGN_MODULE,
        "rust_release": RUST_RELEASE,
        "captured_at_utc": captured_at,
        "record_count": len(records),
        "records": records,
    }
    preservation = {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": captured_at,
        "policy": PRESERVATION_POLICY,
        "canonical_checkouts": {
            "rust-1.96": rust_state,
            "verus": verus_state,
        },
        "negative_lessons_workspace": negative_lessons_guard,
    }

    write_json(SOURCE_MANIFEST_JSON, source_json)
    atomic_write(SOURCE_MANIFEST_CSV, source_manifest_csv(records))
    write_json(PRESERVATION_MANIFEST, preservation)

    source_refs = [
        relative_artifact_record(SOURCE_MANIFEST_JSON),
        relative_artifact_record(SOURCE_MANIFEST_CSV),
    ]
    preservation_ref = relative_artifact_record(PRESERVATION_MANIFEST)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": captured_at,
        "campaign": expected_campaign_record(),
        "commands": expected_command_records(),
        "environment": environment_record(),
        "tools": tools,
        "hash_only_inputs": hashed_inputs,
        "rustdoc_generation": relative_artifact_record(RUSTDOC_BUILD_RESULT),
        "rustdoc_core_json": rustdoc_record,
        "source_manifests": source_refs,
        "preservation_manifest": preservation_ref,
        "checkouts": {
            "rust-1.96": {
                "root": str(RUST_ROOT),
                "head": rust_state["head"],
                "head_tree": rust_state["head_tree"],
                "is_clean": rust_state["is_clean"],
            },
            "verus": {
                "root": str(VERUS_ROOT),
                "head": verus_state["head"],
                "head_tree": verus_state["head_tree"],
                "is_clean": verus_state["is_clean"],
            },
        },
        "campaign_validation_sources": validation_sources,
        "hash_algorithm": "sha256",
    }
    write_json(CAMPAIGN_MANIFEST, manifest)

    print(
        "captured core::cmp provenance: "
        f"{len(records)} source snapshots, "
        f"Rust {rust_state['head']}, Verus {verus_state['head']}, "
        "negative-lessons metadata entries "
        f"{negative_lessons_guard['entry_count_including_root']}"
    )


def require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ProvenanceError(f"stale or inconsistent {label}")


def expected_snapshot_paths() -> set[str]:
    return {
        source.snapshot_relpath.removeprefix("provenance/snapshots/")
        for source in SOURCE_INPUTS
    }


def actual_snapshot_paths() -> set[str]:
    root = PROVENANCE_DIR / "snapshots"
    if not root.is_dir():
        raise ProvenanceError(f"snapshot directory is missing: {root}")
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def validate_static_manifest_contract(
    manifest: dict[str, Any],
    source_manifest: dict[str, Any],
    preservation: dict[str, Any],
) -> None:
    require_equal("campaign schema", manifest.get("schema_version"), SCHEMA_VERSION)
    require_equal("source schema", source_manifest.get("schema_version"), SCHEMA_VERSION)
    require_equal("preservation schema", preservation.get("schema_version"), SCHEMA_VERSION)
    require_equal("campaign identity and scope", manifest.get("campaign"), expected_campaign_record())
    require_equal("command mapping", manifest.get("commands"), expected_command_records())
    require_equal("hash algorithm", manifest.get("hash_algorithm"), "sha256")
    require_equal("source module", source_manifest.get("module"), CAMPAIGN_MODULE)
    require_equal(
        "source Rust release",
        source_manifest.get("rust_release"),
        RUST_RELEASE,
    )
    require_equal(
        "preservation policy",
        preservation.get("policy"),
        PRESERVATION_POLICY,
    )


def validate_source_records(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    captured_at = source_manifest.get("captured_at_utc")
    if not isinstance(captured_at, str) or not captured_at:
        raise ProvenanceError("source manifest has no capture timestamp")
    current_source_records = source_records(captured_at, write_snapshots=False)
    require_equal(
        "source record count",
        source_manifest.get("record_count"),
        len(current_source_records),
    )
    require_equal(
        "canonical sources or snapshots",
        source_manifest.get("records"),
        current_source_records,
    )
    return current_source_records


def check_provenance() -> dict[str, Any]:
    assert_layout()
    manifest = read_json(CAMPAIGN_MANIFEST)
    source_manifest = read_json(SOURCE_MANIFEST_JSON)
    preservation = read_json(PRESERVATION_MANIFEST)

    validate_static_manifest_contract(manifest, source_manifest, preservation)

    captured_at = source_manifest.get("captured_at_utc")
    require_equal("capture timestamps", manifest.get("captured_at_utc"), captured_at)
    require_equal("preservation capture timestamp", preservation.get("captured_at_utc"), captured_at)

    for reference in manifest.get("source_manifests", []):
        path = CAMPAIGN_ROOT / reference["path"]
        require_equal(
            f"artifact size for {reference['path']}",
            path.stat().st_size,
            reference["size_bytes"],
        )
        require_equal(
            f"artifact hash for {reference['path']}",
            sha256_file(path),
            reference["sha256"],
        )
    preservation_reference = manifest.get("preservation_manifest", {})
    preservation_path = CAMPAIGN_ROOT / preservation_reference["path"]
    require_equal(
        "preservation artifact size",
        preservation_path.stat().st_size,
        preservation_reference["size_bytes"],
    )
    require_equal(
        "preservation artifact hash",
        sha256_file(preservation_path),
        preservation_reference["sha256"],
    )

    current_source_records = validate_source_records(source_manifest)
    require_equal(
        "source CSV",
        SOURCE_MANIFEST_CSV.read_bytes(),
        source_manifest_csv(current_source_records),
    )
    require_equal("snapshot file set", actual_snapshot_paths(), expected_snapshot_paths())

    require_equal(
        "hash-only inputs",
        manifest.get("hash_only_inputs"),
        hashed_input_records(),
    )
    rustdoc_reference = manifest.get("rustdoc_generation", {})
    rustdoc_evidence_path = CAMPAIGN_ROOT / rustdoc_reference.get("path", "")
    if not rustdoc_evidence_path.is_file():
        raise ProvenanceError("rustdoc generation evidence is missing")
    require_equal(
        "rustdoc generation artifact",
        rustdoc_reference,
        relative_artifact_record(rustdoc_evidence_path),
    )
    require_equal(
        "rustdoc core JSON",
        manifest.get("rustdoc_core_json"),
        validate_rustdoc_generation(),
    )
    require_equal("tool binaries or versions", manifest.get("tools"), tool_records())
    require_equal("execution environment", manifest.get("environment"), environment_record())
    require_equal(
        "campaign validation sources",
        manifest.get("campaign_validation_sources"),
        campaign_file_records(),
    )

    current_rust_state = git_state("rust-1.96", RUST_ROOT)
    current_verus_state = git_state("verus", VERUS_ROOT)
    require_equal(
        "Rust checkout state",
        preservation.get("canonical_checkouts", {}).get("rust-1.96"),
        current_rust_state,
    )
    require_equal(
        "Verus checkout state",
        preservation.get("canonical_checkouts", {}).get("verus"),
        current_verus_state,
    )
    require_equal(
        "negative-lessons workspace metadata",
        preservation.get("negative_lessons_workspace"),
        metadata_tree_fingerprint(NEGATIVE_LESSONS_ROOT),
    )

    require_equal(
        "Rust checkout summary",
        manifest.get("checkouts", {}).get("rust-1.96"),
        {
            "root": str(RUST_ROOT),
            "head": current_rust_state["head"],
            "head_tree": current_rust_state["head_tree"],
            "is_clean": current_rust_state["is_clean"],
        },
    )
    require_equal(
        "Verus checkout summary",
        manifest.get("checkouts", {}).get("verus"),
        {
            "root": str(VERUS_ROOT),
            "head": current_verus_state["head"],
            "head_tree": current_verus_state["head_tree"],
            "is_clean": current_verus_state["is_clean"],
        },
    )

    return {
        "source_snapshot_count": len(current_source_records),
        "rust_head": current_rust_state["head"],
        "verus_head": current_verus_state["head"],
        "verus_dirty_path_count": len(current_verus_state["dirty_paths"]),
        "negative_lessons_metadata_entry_count": preservation[
            "negative_lessons_workspace"
        ][
            "entry_count_including_root"
        ],
        "rustdoc_core_json_sha256": manifest["rustdoc_core_json"]["sha256"],
    }


def check(record: bool) -> None:
    summary = check_provenance()
    if record:
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "pass",
            "checked_at_utc": utc_now(),
            "command": {
                "working_directory": str(CAMPAIGN_ROOT),
                "command": "python3 tools/provenance.py check --record",
                "resolved_python_argv": [
                    str(Path(sys.executable).resolve()),
                    "tools/provenance.py",
                    "check",
                    "--record",
                ],
            },
            "campaign_manifest": relative_artifact_record(CAMPAIGN_MANIFEST),
            "summary": summary,
        }
        write_json(VALIDATION_RESULT, result)
    print(
        "provenance check: PASS; "
        f"{summary['source_snapshot_count']} source snapshots, "
        f"{summary['verus_dirty_path_count']} pinned Verus dirty paths, "
        f"{summary['negative_lessons_metadata_entry_count']} "
        "negative-lessons metadata entries"
    )


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rustdoc_parser = subparsers.add_parser("build-rustdoc")
    rustdoc_parser.add_argument(
        "--refresh",
        action="store_true",
        help="replace existing rustdoc evidence after an intentional rebuild",
    )
    rustdoc_parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="maximum seconds allowed for each cargo step",
    )
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument(
        "--refresh",
        action="store_true",
        help="replace an existing baseline after an intentional input change",
    )
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument(
        "--record",
        action="store_true",
        help="write a successful check record under provenance/validation",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        if options.command == "build-rustdoc":
            if options.timeout <= 0:
                raise ProvenanceError("--timeout must be positive")
            build_rustdoc(options.refresh, options.timeout)
        elif options.command == "capture":
            capture(options.refresh)
        else:
            check(options.record)
    except (ProvenanceError, OSError) as error:
        print(f"provenance error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
