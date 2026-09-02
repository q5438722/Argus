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


EXACT = load_tool("audit_exact_vstd")


def declarations() -> list[dict[str, object]]:
    return EXACT.loaded_declarations()


def inventory_rows() -> list[dict[str, object]]:
    payload = json.loads(EXACT.INVENTORY_PATH.read_text(encoding="utf-8"))
    return payload["rows"]


def row_for(target: str) -> dict[str, object]:
    matches = [row for row in inventory_rows() if row["target"] == target]
    assert len(matches) == 1
    return matches[0]


def declaration_for(
    method: str, self_type: str
) -> dict[str, object]:
    matches = [
        declaration
        for declaration in declarations()
        if declaration["shape"]["method"] == method
        and declaration["shape"]["self_type"] == self_type
    ]
    assert len(matches) == 1
    return matches[0]


def test_parser_finds_every_assume_specification_in_result_source() -> None:
    source = EXACT.VSTD_RESULT.read_text(encoding="utf-8")
    parsed = EXACT.parse_declarations(source, "result")
    assert len(parsed) == len(EXACT.ASSUME_SPECIFICATION.findall(source))
    assert len({row["declaration_id"] for row in parsed}) == len(parsed)


def test_map_matches_complete_signature() -> None:
    row = row_for("<core::result::Result<T, E>>::map")
    rust = EXACT.rust_signature(row)
    declaration = declaration_for("map", "Result<T,E>")
    mismatches, _ = EXACT.compare_signatures(rust, declaration)
    assert mismatches == []
    assert rust["bound_modifiers"] == [
        {"bound": "F:FnOnce(T)->U", "modifier": "maybe_const"}
    ]


def test_debug_bound_matches_complete_unwrap_signature() -> None:
    row = row_for("<core::result::Result<T, E>>::unwrap")
    rust = EXACT.rust_signature(row)
    declaration = declaration_for("unwrap", "Result<T,E>")
    mismatches, _ = EXACT.compare_signatures(rust, declaration)
    assert mismatches == []
    assert rust["shape"]["bounds"] == ["E:Debug"]


def test_signature_mutations_are_rejected() -> None:
    row = row_for("<core::result::Result<T, E>>::map")
    rust = EXACT.rust_signature(row)
    declaration = copy.deepcopy(
        declaration_for("map", "Result<T,E>")
    )
    declaration["shape"]["output"] = "Result<T,E>"
    declaration["shape"]["bounds"] = []
    mismatches, _ = EXACT.compare_signatures(rust, declaration)
    assert "output" in mismatches
    assert "bounds" in mismatches


def test_receiver_mutability_mutation_is_rejected() -> None:
    row = row_for("<core::result::Result<T, E>>::as_ref")
    rust = EXACT.rust_signature(row)
    declaration = copy.deepcopy(
        declaration_for("as_ref", "Result<T,E>")
    )
    declaration["shape"]["inputs"][0] = "&mutResult<T,E>"
    declaration["shape"]["receiver"] = "&mutResult<T,E>"
    mismatches, _ = EXACT.compare_signatures(rust, declaration)
    assert "inputs" in mismatches
    assert "receiver" in mismatches


def test_every_result_declaration_matches_one_live_row() -> None:
    result_declarations = [
        row
        for row in declarations()
        if str(row["source_path"]).endswith("std_specs/result.rs")
    ]
    uses = {row["declaration_id"]: [] for row in result_declarations}
    for inventory_row in inventory_rows():
        rust = EXACT.rust_signature(inventory_row)
        for declaration in result_declarations:
            if any(
                declaration["shape"][field] != rust["shape"][field]
                for field in ("method", "self_type", "trait")
            ):
                continue
            mismatches, _ = EXACT.compare_signatures(rust, declaration)
            if not mismatches:
                uses[declaration["declaration_id"]].append(
                    inventory_row["rustdoc_item_id"]
                )
    assert uses
    assert all(len(item_ids) == 1 for item_ids in uses.values())


def test_audit_covers_all_rows_and_adjudicates_language_items() -> None:
    report = json.loads(EXACT.OUTPUT_PATH.read_text(encoding="utf-8"))
    rows = inventory_rows()
    assert report["status"] == "passed"
    assert report["summary"]["audited_inventory_rows"] == len(rows)
    assert (
        report["summary"]["exact_vstd"]
        + report["summary"]["pending"]
        == len(rows)
    )
    out_of_scope = report["declaration_scope"][
        "out_of_scope_declarations"
    ]
    assert {row["reason"] for row in out_of_scope} == {
        "unstable_core_result_api_not_in_stable_inventory"
    }
    assert {row["exclusion_reason"] for row in out_of_scope} == {
        "unstable_api"
    }
    assert {row["target_binding"].split("::")[-1].strip() for row in out_of_scope} == {
        "branch",
        "from_residual",
    }
    assert all(row["exact_vstd_audit_status"] for row in rows)
