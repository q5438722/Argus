from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name: str) -> ModuleType:
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FREEZER = load_tool("freeze_vstd_provenance")
CHECKER = load_tool("check_vstd_provenance")


def manifest() -> dict[str, object]:
    value = json.loads(CHECKER.MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_conservative_closure_reaches_result_and_loader() -> None:
    payload = manifest()
    git_paths = {
        row["git_path"]
        for row in payload["closure"]["files"]
    }
    assert "source/vstd/vstd.rs" in git_paths
    assert "source/vstd/std_specs/mod.rs" in git_paths
    assert "source/vstd/std_specs/result.rs" in git_paths
    assert payload["closure"]["dirty_paths_outside_closure"] == []


def test_frozen_manifest_matches_current_sources_and_runtime() -> None:
    assert CHECKER.validate(manifest()) == []


def test_source_hash_mutation_is_rejected() -> None:
    mutated = copy.deepcopy(manifest())
    mutated["closure"]["files"][0]["sha256"] = "0" * 64
    errors = CHECKER.validate(mutated)
    assert any(error.endswith(".sha256:value") for error in errors)


def test_dirty_state_mutation_is_rejected() -> None:
    mutated = copy.deepcopy(manifest())
    mutated["verus_repository"]["vstd_status"]["stdout"] = ""
    errors = CHECKER.validate(mutated)
    assert "manifest.verus_repository.vstd_status.stdout:value" in errors


def test_independent_graph_audit_reaches_every_rust_source() -> None:
    path = (
        ROOT
        / "provenance"
        / "vstd_dependency_closure_independent_audit.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["graph"]["unresolved"] == []
    assert payload["graph"]["unreached"] == []
    assert (
        payload["graph"]["reached_rust_files"]
        == payload["reconciliation"]["rust_file_count"]
    )
    source = (
        ROOT / "tools" / "audit_vstd_closure_independent.py"
    ).read_text(encoding="utf-8")
    assert "freeze_vstd_provenance" not in source
