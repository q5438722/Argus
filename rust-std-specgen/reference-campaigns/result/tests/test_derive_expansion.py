from __future__ import annotations

import hashlib
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


CAPTURE = load_tool("capture_derive_expansion")


def manifest() -> dict[str, object]:
    value = json.loads(CAPTURE.MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def inventory_rows() -> list[dict[str, object]]:
    value = json.loads(CAPTURE.INVENTORY.read_text(encoding="utf-8"))
    return value["rows"]


def test_probe_uses_exact_result_derive_and_field_shapes() -> None:
    source = CAPTURE.SOURCE.read_text(encoding="utf-8")
    assert "#[derive(Copy, Debug, Hash)]" in source
    assert "#[derive_const(PartialEq, PartialOrd, Eq, Ord)]" in source
    assert "enum Result<T, E>" in source
    assert "struct Iter<'a, T: 'a>" in source
    assert "inner: Option<&'a T>" in source
    assert "struct IterMut<'a, T: 'a>" in source
    assert "inner: Option<&'a mut T>" in source
    assert "#[derive(Clone, Debug)]" in source
    assert "struct IntoIter<T>" in source


def test_manifest_binds_exactly_all_nine_derived_inventory_rows() -> None:
    payload = manifest()
    captures = payload["captures"]
    derived_rows = [
        row
        for row in inventory_rows()
        if row["source_body_kind"] == "rustc_derive_expansion_required"
    ]
    assert payload["status"] == "passed"
    assert len(captures) == len(derived_rows) == 9
    assert {row["target"] for row in captures} == {
        row["target"] for row in derived_rows
    }
    assert len({row["rustdoc_item_id"] for row in captures}) == 9
    assert all(payload["semantic_checks"].values())


def test_every_inventory_row_carries_its_exact_expansion_slice() -> None:
    payload = manifest()
    expanded = CAPTURE.EXPANDED.read_text(encoding="utf-8")
    capture_by_target = {
        capture["target"]: capture for capture in payload["captures"]
    }
    for row in inventory_rows():
        if row["source_body_kind"] != "rustc_derive_expansion_required":
            continue
        assert row["derive_expansion_status"] == "captured"
        capture = capture_by_target[row["target"]]
        method = capture["expanded_method"]
        excerpt = expanded[method["start_byte"] : method["end_byte"]]
        assert hashlib.sha256(excerpt.encode()).hexdigest() == method["sha256"]
        assert row["derive_expansion_method_sha256"] == method["sha256"]
        assert row["derive_expansion_method_start_byte"] == method["start_byte"]
        assert row["derive_expansion_method_end_byte"] == method["end_byte"]


def test_missing_derive_semantics_are_detected() -> None:
    expanded = CAPTURE.EXPANDED.read_text(encoding="utf-8")
    mutated = expanded.replace(
        "discriminant_value", "missing_discriminant"
    )
    derived_rows = [
        row
        for row in inventory_rows()
        if row["source_body_kind"] == "rustc_derive_expansion_required"
    ]
    _, semantic_checks = CAPTURE.capture_expansions(mutated, derived_rows)
    hash_target = (
        "<core::result::Result<T, E> as core::hash::Hash>::hash"
    )
    assert semantic_checks[hash_target] is False
