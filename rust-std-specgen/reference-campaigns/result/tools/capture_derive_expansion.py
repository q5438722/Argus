#!/usr/bin/env python3
"""Freeze and bind Rust 1.96 expansions for nine Result derive methods."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "provenance" / "result_derive_expansion_input.rs"
EXPANDED = ROOT / "provenance" / "result_derive_expansion.rs"
STDERR = ROOT / "provenance" / "result_derive_expansion.stderr.log"
MANIFEST = ROOT / "provenance" / "result_derive_expansion.json"
INVENTORY = ROOT / "inventory" / "core_result_exec_fn_inventory.json"
INVENTORY_CSV = ROOT / "inventory" / "core_result_exec_fn_inventory.csv"
SUMMARY = ROOT / "inventory" / "coverage_summary.json"
RUST_RESULT = (
    ROOT
    / "provenance"
    / "rust-source"
    / "library"
    / "core"
    / "src"
    / "result.rs"
)
TOOLCHAIN = ROOT / "provenance" / "toolchain.json"

DERIVE_COLUMNS = (
    "derive_expansion_method_end_byte",
    "derive_expansion_method_end_line",
    "derive_expansion_method_sha256",
    "derive_expansion_method_start_byte",
    "derive_expansion_method_start_line",
    "derive_expansion_path",
)
EXPECTED_BINDINGS = {
    "<core::result::Result<T, E> as core::fmt::Debug>::fmt": {
        "derive_site_line": 552,
        "method": "fmt",
        "probe_type": "Result",
        "semantic_markers": [
            '"Ok"',
            '"Err"',
            "debug_tuple_field1_finish",
        ],
        "trait": "core::fmt::Debug",
    },
    "<core::result::Result<T, E> as core::hash::Hash>::hash": {
        "derive_site_line": 552,
        "method": "hash",
        "probe_type": "Result",
        "semantic_markers": [
            "discriminant_value",
            "Hash::hash",
            "Result::Ok",
            "Result::Err",
        ],
        "trait": "core::hash::Hash",
    },
    "<core::result::Result<T, E> as core::cmp::Ord>::cmp": {
        "derive_site_line": 553,
        "method": "cmp",
        "probe_type": "Result",
        "semantic_markers": [
            "Ord::cmp",
            "Result::Ok",
            "Result::Err",
        ],
        "trait": "core::cmp::Ord",
    },
    "<core::result::Result<T, E> as core::cmp::PartialEq>::eq": {
        "derive_site_line": 553,
        "method": "eq",
        "probe_type": "Result",
        "semantic_markers": [
            "__self_0 == __arg1_0",
            "discriminant_value",
            "Result::Ok",
            "Result::Err",
        ],
        "trait": "core::cmp::PartialEq",
    },
    "<core::result::Result<T, E> as core::cmp::PartialOrd>::partial_cmp": {
        "derive_site_line": 553,
        "method": "partial_cmp",
        "probe_type": "Result",
        "semantic_markers": [
            "PartialOrd::partial_cmp",
            "Result::Ok",
            "Result::Err",
        ],
        "trait": "core::cmp::PartialOrd",
    },
    "<core::result::Iter<'a, T> as core::fmt::Debug>::fmt": {
        "derive_site_line": 1973,
        "method": "fmt",
        "probe_type": "Iter",
        "semantic_markers": ['"Iter"', '"inner"', "self.inner"],
        "trait": "core::fmt::Debug",
    },
    "<core::result::IterMut<'a, T> as core::fmt::Debug>::fmt": {
        "derive_site_line": 2022,
        "method": "fmt",
        "probe_type": "IterMut",
        "semantic_markers": ['"IterMut"', '"inner"', "self.inner"],
        "trait": "core::fmt::Debug",
    },
    "<core::result::IntoIter<T> as core::clone::Clone>::clone": {
        "derive_site_line": 2068,
        "method": "clone",
        "probe_type": "IntoIter",
        "semantic_markers": ["Clone::clone", "self.inner"],
        "trait": "core::clone::Clone",
    },
    "<core::result::IntoIter<T> as core::fmt::Debug>::fmt": {
        "derive_site_line": 2068,
        "method": "fmt",
        "probe_type": "IntoIter",
        "semantic_markers": ['"IntoIter"', '"inner"', "self.inner"],
        "trait": "core::fmt::Debug",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def matching_brace(text: str, opening: int) -> int:
    if opening >= len(text) or text[opening] != "{":
        raise ValueError(f"expected opening brace at {opening}")
    depth = 0
    for position in range(opening, len(text)):
        character = text[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return position
    raise ValueError(f"unterminated brace at {opening}")


def automatically_derived_impls(expanded: str) -> list[dict[str, Any]]:
    rows = []
    pattern = re.compile(r"#\[automatically_derived\]\s*impl\b")
    for match in pattern.finditer(expanded):
        opening = expanded.find("{", match.end())
        if opening < 0:
            raise ValueError(
                f"derived impl at {match.start()} lacks an opening brace"
            )
        closing = matching_brace(expanded, opening)
        rows.append(
            {
                "end": closing + 1,
                "header": expanded[match.start() : opening],
                "start": match.start(),
                "text": expanded[match.start() : closing + 1],
            }
        )
    return rows


def type_header_pattern(probe_type: str) -> re.Pattern[str]:
    return re.compile(
        rf"\bfor\s+{re.escape(probe_type)}\s*(?:<|\{{)",
        re.DOTALL,
    )


def method_slice(
    expanded: str,
    implementation: dict[str, Any],
    method: str,
) -> dict[str, Any]:
    implementation_text = implementation["text"]
    match = re.search(rf"\bfn\s+{re.escape(method)}\b", implementation_text)
    if match is None:
        raise ValueError(
            f"derived impl has no method {method}: "
            f"{implementation['header']!r}"
        )
    global_start = implementation["start"] + match.start()
    opening = expanded.find("{", global_start)
    if opening < 0 or opening >= implementation["end"]:
        raise ValueError(f"derived method {method} has no body")
    global_end = matching_brace(expanded, opening) + 1
    if global_end > implementation["end"]:
        raise ValueError(f"derived method {method} escapes its impl")
    text = expanded[global_start:global_end]
    return {
        "end_byte": global_end,
        "end_line": expanded.count("\n", 0, global_end) + 1,
        "sha256": sha256_text(text),
        "start_byte": global_start,
        "start_line": expanded.count("\n", 0, global_start) + 1,
        "text": text,
    }


def capture_expansions(
    expanded: str,
    derived_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    targets = {str(row["target"]) for row in derived_rows}
    expected_targets = set(EXPECTED_BINDINGS)
    if targets != expected_targets:
        raise ValueError(
            "derived inventory targets differ from the required bindings: "
            f"missing={sorted(expected_targets - targets)}, "
            f"extra={sorted(targets - expected_targets)}"
        )
    by_target = {str(row["target"]): row for row in derived_rows}
    implementations = automatically_derived_impls(expanded)
    captures: list[dict[str, Any]] = []
    semantic_checks: dict[str, bool] = {}
    for target, binding in EXPECTED_BINDINGS.items():
        trait_fragment = f"::{binding['trait']}"
        type_pattern = type_header_pattern(binding["probe_type"])
        matching_impls = [
            implementation
            for implementation in implementations
            if trait_fragment in implementation["header"]
            and type_pattern.search(implementation["header"])
            and re.search(
                rf"\bfn\s+{re.escape(binding['method'])}\b",
                implementation["text"],
            )
        ]
        if len(matching_impls) != 1:
            raise ValueError(
                f"{target} resolved to {len(matching_impls)} derive impls"
            )
        method = method_slice(
            expanded, matching_impls[0], binding["method"]
        )
        marker_results = {
            marker: marker in method["text"]
            for marker in binding["semantic_markers"]
        }
        semantic_checks[target] = all(marker_results.values())
        inventory_row = by_target[target]
        if inventory_row["source_start_line"] != binding["derive_site_line"]:
            raise ValueError(
                f"{target} moved from derive site "
                f"{binding['derive_site_line']} to "
                f"{inventory_row['source_start_line']}"
            )
        captures.append(
            {
                "derive_site": {
                    "end_column": inventory_row["source_end_column"],
                    "end_line": inventory_row["source_end_line"],
                    "excerpt_sha256": inventory_row[
                        "source_excerpt_sha256"
                    ],
                    "path": inventory_row["frozen_source_path"],
                    "start_column": inventory_row["source_start_column"],
                    "start_line": inventory_row["source_start_line"],
                },
                "expanded_impl_header": " ".join(
                    matching_impls[0]["header"].split()
                ),
                "expanded_method": {
                    key: value
                    for key, value in method.items()
                    if key != "text"
                },
                "method": binding["method"],
                "probe_type": binding["probe_type"],
                "rust_signature": inventory_row["signature"],
                "rustdoc_item_id": inventory_row["rustdoc_item_id"],
                "semantic_markers": marker_results,
                "target": target,
                "trait": binding["trait"],
            }
        )
    captures.sort(key=lambda row: int(row["rustdoc_item_id"]))
    return captures, semantic_checks


def write_inventory_csv(rows: list[dict[str, Any]]) -> None:
    with INVENTORY_CSV.open(newline="", encoding="utf-8") as stream:
        existing_fields = next(csv.reader(stream))
    fields = existing_fields + [
        field for field in DERIVE_COLUMNS if field not in existing_fields
    ]
    temporary = INVENTORY_CSV.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(INVENTORY_CSV)


def update_inventory(
    inventory: dict[str, Any],
    captures: list[dict[str, Any]],
) -> None:
    by_target = {capture["target"]: capture for capture in captures}
    rows = inventory["rows"]
    for row in rows:
        if row["source_body_kind"] != "rustc_derive_expansion_required":
            continue
        capture = by_target[row["target"]]
        method = capture["expanded_method"]
        row.update(
            {
                "derive_expansion_method_end_byte": method["end_byte"],
                "derive_expansion_method_end_line": method["end_line"],
                "derive_expansion_method_sha256": method["sha256"],
                "derive_expansion_method_start_byte": method["start_byte"],
                "derive_expansion_method_start_line": method["start_line"],
                "derive_expansion_path": str(
                    EXPANDED.relative_to(ROOT)
                ),
                "derive_expansion_status": "captured",
            }
        )
    write_json(INVENTORY, inventory)
    write_inventory_csv(rows)


def main() -> int:
    command = [
        "rustc",
        "+1.96.0",
        str(SOURCE),
        "--crate-name",
        "result_derive_expansion",
        "--crate-type=lib",
        "-Zunpretty=expanded",
    ]
    environment = dict(os.environ)
    environment["RUSTC_BOOTSTRAP"] = "1"
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=110,
        check=False,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    EXPANDED.write_text(result.stdout, encoding="utf-8")
    STDERR.write_text(result.stderr, encoding="utf-8")
    rustc_version = subprocess.check_output(
        ["rustc", "+1.96.0", "--version", "--verbose"],
        text=True,
    )
    inventory = load_json(INVENTORY)
    rows = inventory.get("rows")
    if not isinstance(rows, list):
        raise ValueError("inventory rows are not a list")
    derived_rows = [
        row
        for row in rows
        if row.get("source_body_kind")
        == "rustc_derive_expansion_required"
    ]
    pre_inventory_sha256 = sha256(INVENTORY)
    errors: list[str] = []
    captures: list[dict[str, Any]] = []
    semantic_checks: dict[str, bool] = {}
    if result.returncode != 0:
        errors.append("rustc_expansion_failed")
    else:
        try:
            captures, semantic_checks = capture_expansions(
                result.stdout, derived_rows
            )
        except ValueError as error:
            errors.append(str(error))
    if semantic_checks and not all(semantic_checks.values()):
        errors.append("derive_semantic_marker_check_failed")
    if len(captures) != len(EXPECTED_BINDINGS):
        errors.append("not_all_nine_derive_methods_were_captured")

    expected_rust_commit = load_json(TOOLCHAIN)["pins"]["rust"]["commit"]
    if f"commit-hash: {expected_rust_commit}" not in rustc_version:
        errors.append("rustc_version_does_not_match_rust_source")
    if not errors:
        update_inventory(inventory, captures)
        summary = load_json(SUMMARY)
        summary["derive_expansion_captured_rows"] = len(captures)
        summary["derive_expansion_pending_rows"] = 0
        write_json(SUMMARY, summary)
    post_inventory_sha256 = (
        sha256(INVENTORY) if not errors else pre_inventory_sha256
    )
    manifest = {
        "captures": captures,
        "command": command,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "environment": {"RUSTC_BOOTSTRAP": "1"},
        "errors": errors,
        "exit_code": result.returncode,
        "expanded_path": str(EXPANDED.relative_to(ROOT)),
        "expanded_sha256": sha256(EXPANDED),
        "input_path": str(SOURCE.relative_to(ROOT)),
        "input_sha256": sha256(SOURCE),
        "inventory": {
            "derived_row_count": len(derived_rows),
            "path": str(INVENTORY.relative_to(ROOT)),
            "post_capture_sha256": post_inventory_sha256,
            "pre_capture_sha256": pre_inventory_sha256,
        },
        "runner_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "rust_1_96_source_binding": {
            "path": str(RUST_RESULT.relative_to(ROOT)),
            "sha256": sha256(RUST_RESULT),
            "sites": [
                "result.rs:552",
                "result.rs:553",
                "result.rs:1973",
                "result.rs:2022",
                "result.rs:2068",
            ],
        },
        "rustc_version": rustc_version,
        "schema_version": 1,
        "semantic_checks": semantic_checks,
        "started_at_utc": started_at,
        "status": "passed" if not errors else "failed",
        "stderr_path": str(STDERR.relative_to(ROOT)),
        "stderr_sha256": sha256(STDERR),
    }
    write_json(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "captured_methods": len(captures),
                "duration_ms": duration_ms,
                "errors": errors,
                "exit_code": result.returncode,
                "status": manifest["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
