import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from argus.skills.builtins import seed_context_skills, vertical_skill_source_path


SCRIPT = "spec_storage_scripts/specdet_storage.py"
SOURCE = vertical_skill_source_path("software") / SCRIPT
SPEC = importlib.util.spec_from_file_location("specdet_storage", SOURCE)
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)
POLICY = {"schema_version": 1, "specdet_version": "0.3.0", "max_input_mib": 10, "min_free_gib": 50}
IGNORED = {".git", ".venv", "__pycache__", ".pytest_cache", "target", "backups"}


@pytest.fixture
def config(tmp_path, monkeypatch):
    root = tmp_path / "input"
    root.mkdir()
    (root / "lib.rs").write_text("fn main() {}\n")
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _path: SimpleNamespace(free=100 * 2**30))
    return SimpleNamespace(
        project_root=root, output_dir=tmp_path / "output", include=("*.rs",), exclude=(),
        type_sources=(), build=SimpleNamespace(entrypoint="", injection_file=""),
        validate=lambda: None,
    )


def test_snapshot_selection_counts_non_target_files(config):
    extra = config.project_root / "unrelated.xml"
    extra.write_bytes(b"x")
    result = storage.check_storage(config, POLICY, IGNORED)
    assert result["input_files"] == 2
    assert result["target_inputs"] == ["lib.rs"]
    assert "unrelated.xml" in result["files"]


def test_input_over_ten_mib_is_blocked_before_any_output(config):
    with (config.project_root / "large.xml").open("wb") as stream:
        stream.truncate(10 * 2**20)
    with pytest.raises(ValueError, match="input_budget_exceeded"):
        storage.check_storage(config, POLICY, IGNORED)
    assert not config.output_dir.exists()


def test_input_at_limit_is_allowed(config):
    with (config.project_root / "lib.rs").open("wb") as stream:
        stream.truncate(10 * 2**20 - 4096)
    assert storage.check_storage(config, POLICY, IGNORED)["projected_bytes"] == 10 * 2**20


def test_directory_allocation_counts_towards_input_limit(config):
    with (config.project_root / "lib.rs").open("wb") as stream:
        stream.truncate(10 * 2**20 - 4095)
    with pytest.raises(ValueError, match="input_budget_exceeded"):
        storage.check_storage(config, POLICY, IGNORED)


@pytest.mark.parametrize("free,blocked", [(50 * 2**30 - 1, True), (50 * 2**30, False)])
def test_free_space_boundary(config, monkeypatch, free, blocked):
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _path: SimpleNamespace(free=free))
    if blocked:
        with pytest.raises(ValueError, match="free_space_below_minimum"):
            storage.check_storage(config, POLICY, IGNORED)
    else:
        storage.check_storage(config, POLICY, IGNORED)


@pytest.mark.parametrize("is_directory", [False, True])
def test_symlink_is_refused(config, is_directory):
    target = config.project_root if is_directory else config.project_root / "lib.rs"
    (config.project_root / "alias").symlink_to(target)
    with pytest.raises(ValueError, match="symlink_input|unsupported_input"):
        storage.check_storage(config, POLICY, IGNORED)


def test_current_output_is_not_snapshotted(config):
    config.output_dir = config.project_root / "out"
    config.output_dir.mkdir()
    (config.output_dir / "old.rs").write_text("old")
    assert storage.check_storage(config, POLICY, IGNORED)["input_files"] == 1


def test_old_output_requires_explicit_exclusion(config):
    old = config.project_root / "old-output"
    old.mkdir()
    (old / "snapshot.json").write_text(json.dumps({"kind": "source_snapshot"}))
    with pytest.raises(ValueError, match="previous_run_in_input"):
        storage.check_storage(config, POLICY, IGNORED)
    config.exclude = ("old-output/**",)
    assert storage.check_storage(config, POLICY, IGNORED)["input_files"] == 1


@pytest.mark.parametrize("field", ["entrypoint", "injection_file", "type_sources"])
def test_required_dependency_must_exist_and_not_be_excluded(config, field):
    if field == "type_sources":
        config.type_sources = ("missing.rs",)
    else:
        setattr(config.build, field, "missing.rs")
    with pytest.raises(ValueError, match="required_input_missing_or_excluded"):
        storage.check_storage(config, POLICY, IGNORED)


def test_empty_target_selection_is_not_success(config):
    config.include = ("absent/*.rs",)
    with pytest.raises(ValueError, match="empty_target_inputs"):
        storage.check_storage(config, POLICY, IGNORED)


def test_storage_script_seeds_verbatim(tmp_path):
    seed_context_skills(tmp_path, "software")
    assert (tmp_path / SCRIPT).read_bytes() == SOURCE.read_bytes()
