from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_builder() -> ModuleType:
    path = ROOT / "tools" / "build_inventory.py"
    spec = importlib.util.spec_from_file_location("build_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load_builder()


def load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_generated_inventory_matches_frozen_rustdoc() -> None:
    document = load_object(BUILD.RUSTDOC_JSON)
    expected_rows, expected_exclusions, _ = BUILD.collect_inventory(
        document, BUILD.sha256(BUILD.RUSTDOC_JSON)
    )
    inventory = load_object(
        ROOT / "inventory" / "core_result_exec_fn_inventory.json"
    )
    exclusions = load_object(
        ROOT / "inventory" / "core_result_exclusions.json"
    )
    actual_rows = inventory["rows"]
    assert len(actual_rows) == len(expected_rows)
    for actual, expected in zip(actual_rows, expected_rows, strict=True):
        projected = {key: actual[key] for key in expected}
        for enriched_field in (
            "derive_expansion_status",
            "disposition",
            "pending_reason",
        ):
            projected[enriched_field] = expected[enriched_field]
        assert projected == expected
    assert exclusions["rows"] == expected_exclusions
    assert BUILD.inventory_partition_errors(
        expected_rows, expected_exclusions
    ) == []


def test_inventory_is_stable_executable_and_exact_vstd_audited() -> None:
    payload = load_object(
        ROOT / "inventory" / "core_result_exec_fn_inventory.json"
    )
    rows = payload["rows"]
    assert isinstance(rows, list)
    assert rows
    assert all(row["stability"] == "stable" for row in rows)
    assert {row["disposition"] for row in rows} <= {
        "exact_vstd",
        "pending",
    }
    assert all(row["exact_vstd_audit_status"] for row in rows)
    assert all(
        not row["pending_reason"]
        if row["disposition"] == "exact_vstd"
        else bool(row["pending_reason"])
        for row in rows
    )
    assert len({row["target"] for row in rows}) == len(rows)
    assert len({row["rustdoc_item_id"] for row in rows}) == len(rows)


def test_high_risk_result_surfaces_are_selected() -> None:
    payload = load_object(
        ROOT / "inventory" / "core_result_exec_fn_inventory.json"
    )
    targets = {row["target"] for row in payload["rows"]}
    required_suffixes = {
        ">::flatten",
        ">::unwrap_unchecked",
        ">::unwrap_err_unchecked",
        ">::from_iter",
        ">::sum",
        ">::product",
        ">::clone_from",
        ">::into_iter",
        ">::next",
        ">::next_back",
        ">::size_hint",
    }
    for suffix in required_suffixes:
        assert any(target.endswith(suffix) for target in targets), suffix


def test_unstable_and_non_executable_items_are_adjudicated() -> None:
    payload = load_object(
        ROOT / "inventory" / "core_result_exclusions.json"
    )
    rows = payload["rows"]
    unstable_methods = {
        row.get("method_name")
        for row in rows
        if row.get("exclusion_reason") == "unstable_api"
    }
    assert {"map_or_default", "into_ok", "into_err"}.issubset(
        unstable_methods
    )
    assert {"branch", "from_output", "from_residual"}.issubset(
        unstable_methods
    )
    assert any(
        row.get("trait") == "core::iter::traits::marker::TrustedLen"
        and row.get("exclusion_reason")
        == "unstable_non_executable_impl_declaration"
        for row in rows
    )
    variant_rows = [
        row for row in rows if row.get("item_kind") == "variant"
    ]
    assert {row["target"].rsplit("::", 1)[-1] for row in variant_rows} == {
        "Ok",
        "Err",
    }


def test_derived_methods_have_bound_compiler_expansions() -> None:
    payload = load_object(
        ROOT / "inventory" / "core_result_exec_fn_inventory.json"
    )
    rows = payload["rows"]
    derived = [
        row
        for row in rows
        if row["source_body_kind"] == "rustc_derive_expansion_required"
    ]
    assert derived
    assert all(
        row["derive_expansion_status"] == "captured"
        for row in derived
    )
    assert all(row["derive_expansion_method_sha256"] for row in derived)
    assert {
        row["trait"]
        for row in derived
    } == {
        "core::clone::Clone",
        "core::cmp::Ord",
        "core::cmp::PartialEq",
        "core::cmp::PartialOrd",
        "core::fmt::Debug",
        "core::hash::Hash",
    }


def test_historical_count_is_annotation_not_acceptance_rule() -> None:
    summary = load_object(
        ROOT / "inventory" / "coverage_summary.json"
    )
    reconciliation = summary["historical_reconciliation"]
    assert (
        reconciliation["older_count_used_as_acceptance_criterion"] is False
    )
    assert reconciliation["older_campaign_artifacts_imported"] is False
    assert summary["stable_inventory_total"] == (
        summary["stable_inherent_method_rows"]
        + summary["stable_trait_method_rows"]
    )
    assert reconciliation["difference_from_older_reported_count"] == (
        summary["stable_inventory_total"]
        - reconciliation["older_campaign_reported_rows"]
    )
    assert len(
        reconciliation["trait_rows_accounting_for_numeric_difference"]
    ) == summary["stable_trait_method_rows"]
    if (
        reconciliation["live_inherent_method_rows"]
        == reconciliation["older_campaign_reported_rows"]
    ):
        assert (
            reconciliation["difference_from_older_reported_count"]
            == reconciliation["live_concrete_trait_method_rows"]
        )


def test_source_files_and_toolchain_are_pinned() -> None:
    manifest = load_object(
        ROOT / "provenance" / "source_manifest.json"
    )
    rows = manifest["rows"]
    roles = Counter(row["role"] for row in rows)
    assert roles["authoritative_rust_1_96_module_source"] == 1
    assert roles["authoritative_rust_1_96_rustdoc_json"] == 1
    assert roles["current_vstd_result_exact_contract_audit_input"] == 1
    for row in rows:
        copied = ROOT / row["copied_path"]
        source = Path(row["source_path"])
        assert copied.is_file()
        assert BUILD.sha256(copied) == row["sha256"]
        assert BUILD.sha256(source) == row["source_sha256"]
        assert copied.read_bytes() == source.read_bytes()

    toolchain = load_object(ROOT / "provenance" / "toolchain.json")
    assert toolchain["status"] == "passed"
    assert toolchain["rustdoc"]["format_version"] == 57
    assert (
        toolchain["input_policy"]["older_campaign_artifacts_used"] == []
    )
    assert (
        toolchain["commands"]["rustdoc_reproduction"][
            "executed_this_increment"
        ]
        is False
    )
