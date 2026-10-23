"""Project-level storage preflight; delegates unchanged arguments to pinned specdet."""

from __future__ import annotations

import argparse
from dataclasses import replace
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Any


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    expected = {"schema_version", "specdet_version", "max_input_mib", "min_free_gib"}
    if set(policy) != expected or policy["schema_version"] != 1:
        raise ValueError("Unsupported storage policy schema")
    for key in ("max_input_mib", "min_free_gib"):
        if type(policy[key]) is not int or policy[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if not isinstance(policy["specdet_version"], str) or not policy["specdet_version"]:
        raise ValueError("Storage policy must pin a specdet version")
    return policy


def fail_walk(error: OSError) -> None:
    raise error


def snapshot_inputs(config: Any, ignored_dirs: set[str]) -> dict[str, Path]:
    """Mirror prepare_project's file selection, not targets.include discovery."""
    root = config.project_root.resolve()
    selected: dict[str, Path] = {}
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=fail_walk):
        base = Path(directory)
        kept = []
        for name in sorted(dirs):
            candidate = base / name
            relative = candidate.relative_to(root).as_posix()
            if name in ignored_dirs or candidate.resolve() == config.output_dir:
                continue
            if any(fnmatch.fnmatchcase(relative + "/", rule) for rule in config.exclude):
                continue
            if candidate.is_symlink():
                raise ValueError(f"symlink_input: {relative}")
            kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            candidate = base / name
            relative = candidate.relative_to(root).as_posix()
            if any(fnmatch.fnmatchcase(relative, rule) for rule in config.exclude):
                continue
            if candidate.is_symlink() or not stat.S_ISREG(candidate.stat().st_mode):
                raise ValueError(f"unsupported_input: {relative}")
            selected[relative] = candidate
    if not selected:
        raise ValueError("empty_input: no files would be snapshotted")
    return selected


def check_storage(config: Any, policy: dict[str, Any], ignored_dirs: set[str]) -> dict[str, Any]:
    config.validate()
    files = snapshot_inputs(config, ignored_dirs)
    sizes = {name: path.stat().st_size for name, path in files.items()}
    logical = sum(sizes.values())
    allocations = {name: path.stat().st_blocks * 512 for name, path in files.items()}
    allocated = sum(allocations.values())
    directories = {Path(".")}
    for name in files:
        directories.update(Path(name).parents)
    directory_bytes = sum(
        max(4096, (config.project_root / relative).stat().st_blocks * 512)
        for relative in directories
    )
    projected = directory_bytes + sum(
        max((sizes[name] + 4095) // 4096 * 4096, allocations[name])
        for name in files
    )
    limit = policy["max_input_mib"] * 2**20
    if projected > limit:
        largest = sorted(sizes, key=sizes.__getitem__, reverse=True)[:8]
        raise ValueError(
            f"input_budget_exceeded: logical={logical}, allocated={allocated}, "
            f"projected={projected}, limit={limit}; "
            f"largest={[(name, sizes[name]) for name in largest]}; "
            "targets.include does not limit snapshots; preserve the full dependency closure"
        )
    for name, path in files.items():
        if path.name == "snapshot.json":
            artifact = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(artifact, dict) and artifact.get("kind") == "source_snapshot":
                raise ValueError(f"previous_run_in_input: exclude historical outputs: {name}")
    root = config.project_root.resolve()
    for name in (config.build.entrypoint, config.build.injection_file, *config.type_sources):
        if name:
            required = (root / name).resolve()
            if not required.is_relative_to(root) or required.relative_to(root).as_posix() not in files:
                raise ValueError(f"required_input_missing_or_excluded: {name}")
    candidates = set()
    for pattern in config.include:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ValueError(f"Input glob escapes project: {pattern}")
        candidates.update(path.relative_to(root).as_posix() for path in root.glob(pattern)
                          if path.is_file() and path.relative_to(root).as_posix() in files)
    if not candidates:
        raise ValueError("empty_target_inputs: include/exclude selects no files")
    output = config.output_dir.resolve()
    ancestor = output
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ValueError(f"Output ancestor is not a directory: {ancestor}")
    free = shutil.disk_usage(ancestor).free
    minimum = policy["min_free_gib"] * 2**30
    if free < minimum:
        raise ValueError(f"free_space_below_minimum: free={free}, minimum={minimum}, filesystem={ancestor}")
    manifest = {}
    for name, path in files.items():
        with path.open("rb") as stream:
            manifest[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"preflight_only": True, "source_root": str(root), "output_dir": str(output),
            "input_files": len(files), "logical_bytes": logical, "allocated_bytes": allocated,
            "directory_bytes": directory_bytes, "projected_bytes": projected,
            "max_input_bytes": limit, "free_bytes": free, "min_free_bytes": minimum,
            "target_inputs": sorted(candidates), "files": manifest}


def effective_config(cli: Any, args: argparse.Namespace) -> Any:
    if args.command in {"replay", "assist"}:
        config = cli._restore_config(args.run, args.config)
        if args.out:
            config = replace(config, output_dir=args.out.expanduser().resolve())
        if args.verus:
            config = replace(config, toolchain=replace(
                config.toolchain, executable=str(Path(args.verus).expanduser().resolve())
            ))
        return config
    return cli._config(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-policy", type=Path, required=True)
    parser.add_argument("--storage-check-only", action="store_true")
    parser.add_argument("checker_args", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    arguments = options.checker_args
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    try:
        from specdet import __version__
        from specdet.cli import main as cli
        from specdet.storage.workspace import _IGNORED_DIRS

        policy = load_policy(options.storage_policy)
        if __version__ != policy["specdet_version"]:
            raise ValueError(
                f"Unreviewed checker version {__version__}; expected {policy['specdet_version']}"
            )
        args = cli._parser().parse_args(arguments)
        copies_inputs = args.command in {"discover", "analyze", "assist"} or (
            args.command == "replay" and args.reexecute
        )
        if copies_inputs:
            report = check_storage(effective_config(cli, args), policy, _IGNORED_DIRS)
            if options.storage_check_only:
                print(json.dumps(report, indent=2))
                return 0
            print("specdet-storage: " + json.dumps(
                {key: value for key, value in report.items() if key not in {"files", "target_inputs"}}
            ), file=sys.stderr)
        elif options.storage_check_only:
            raise ValueError("Storage check-only requires discover, analyze, assist, or replay --reexecute")
        return cli.main(arguments)
    except (OSError, ValueError) as error:
        print(f"specdet-storage: BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
