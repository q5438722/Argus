#!/usr/bin/env python3
"""Reject stale or incomplete frozen vstd dependency provenance."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "vstd_dependency_closure.json"
OUTPUT = ROOT / "provenance" / "vstd_dependency_closure_check.json"


def load_freezer() -> ModuleType:
    path = ROOT / "tools" / "freeze_vstd_provenance.py"
    spec = importlib.util.spec_from_file_location(
        "freeze_vstd_provenance_for_check", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FREEZER = load_freezer()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def compare(
    expected: Any,
    actual: Any,
    path: str,
    errors: list[str],
) -> None:
    if type(expected) is not type(actual):
        errors.append(f"{path}:type")
        return
    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            errors.append(f"{path}.{key}:missing")
        for key in sorted(actual_keys - expected_keys):
            errors.append(f"{path}.{key}:unexpected")
        for key in sorted(expected_keys & actual_keys):
            compare(expected[key], actual[key], f"{path}.{key}", errors)
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            errors.append(f"{path}:length")
            return
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=True)
        ):
            compare(
                expected_item,
                actual_item,
                f"{path}[{index}]",
                errors,
            )
        return
    if expected != actual:
        errors.append(f"{path}:value")


def validate(manifest: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest:not_object"]
    if manifest.get("schema_version") != 1:
        errors.append("manifest.schema_version:value")
    if manifest.get("status") != "passed":
        errors.append("manifest.status:value")
    if not isinstance(manifest.get("generated_at_utc"), str):
        errors.append("manifest.generated_at_utc:type")

    try:
        current = FREEZER.build_manifest(copy_sources=False)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        errors.append(f"current_snapshot:{type(error).__name__}:{error}")
        return errors

    expected_payload = {
        key: value
        for key, value in current.items()
        if key != "generated_at_utc"
    }
    actual_payload = {
        key: value
        for key, value in manifest.items()
        if key != "generated_at_utc"
    }
    compare(expected_payload, actual_payload, "manifest", errors)
    return sorted(set(errors))


def main() -> None:
    try:
        manifest = load_json(MANIFEST)
        errors = validate(manifest)
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
        manifest = {}
        errors = [f"manifest_load:{type(error).__name__}:{error}"]

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checker_sha256": FREEZER.sha256(Path(__file__)),
        "closure_file_count": manifest.get("closure", {}).get("file_count"),
        "dirty_file_count": manifest.get("closure", {}).get(
            "dirty_file_count"
        ),
        "errors": errors,
        "manifest_path": str(MANIFEST),
        "manifest_sha256": (
            FREEZER.sha256(MANIFEST) if MANIFEST.is_file() else None
        ),
        "runtime_artifact_count": manifest.get("runtime", {}).get(
            "artifact_count"
        ),
        "schema_version": 1,
        "status": "failed" if errors else "passed",
    }
    FREEZER.write_json(OUTPUT, result)
    print(json.dumps(result, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
