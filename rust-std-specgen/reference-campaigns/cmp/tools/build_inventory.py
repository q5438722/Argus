#!/usr/bin/env python3
"""Build and verify the Rust 1.96 core::cmp executable identity inventory."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
if str(CAMPAIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMPAIGN_ROOT))

from tools import provenance


SCHEMA_VERSION = 1
RUSTDOC_JSON = provenance.RUSTDOC_JSON
INVENTORY_DIR = CAMPAIGN_ROOT / "inventory"
AUDITS_DIR = CAMPAIGN_ROOT / "audits"
INVENTORY_JSON = INVENTORY_DIR / "core_cmp_exec_fn_inventory.json"
INVENTORY_CSV = INVENTORY_DIR / "core_cmp_exec_fn_inventory.csv"
EXCLUSIONS_JSON = INVENTORY_DIR / "core_cmp_exclusions.json"
EXCLUSIONS_CSV = INVENTORY_DIR / "core_cmp_exclusions.csv"
OWNERSHIP_JSON = INVENTORY_DIR / "trait_impl_ownership.json"
EXACT_VSTD_JSON = INVENTORY_DIR / "exact_vstd_audit.json"
RECONCILIATION_JSON = INVENTORY_DIR / "inventory_reconciliation.json"
INVENTORY_README = INVENTORY_DIR / "README.md"
DEFAULT_BINDING_AUDIT = AUDITS_DIR / "default_binding_audit.json"
SPECIALIZATION_AUDIT = AUDITS_DIR / "specialization_ownership_audit.json"
AMBIGUITY_AUDIT = AUDITS_DIR / "identity_ambiguity_audit.json"

RUST_SNAPSHOT_PREFIX = "provenance/snapshots/rust-1.96/library/"
VSTD_SNAPSHOT_PREFIX = "provenance/snapshots/verus/source/vstd/"
CMP_SOURCE = "core/src/cmp.rs"
CMP_TRAIT_SOURCE_FILES = {
    CMP_SOURCE,
    "core/src/slice/cmp.rs",
    "core/src/array/equality.rs",
    "core/src/array/mod.rs",
    "core/src/tuple.rs",
    "core/src/option.rs",
}
CMP_TRAITS = ("PartialEq", "Eq", "Ord", "PartialOrd")
CMP_TRAIT_METHODS = {
    "PartialEq": ("eq", "ne"),
    "Eq": ("assert_receiver_is_total_eq",),
    "Ord": ("cmp", "max", "min", "clamp"),
    "PartialOrd": ("partial_cmp", "lt", "le", "gt", "ge"),
}
CMP_DEFAULT_METHODS = {
    "PartialEq": ("ne",),
    "Eq": ("assert_receiver_is_total_eq",),
    "Ord": ("max", "min", "clamp"),
    "PartialOrd": ("lt", "le", "gt", "ge"),
}
PUBLIC_CMP_TYPES = ("Ordering", "Reverse")
TUPLE_PARAMETERS = ("E", "D", "C", "B", "A", "Z", "Y", "X", "W", "V", "U", "T")
INTEGER_TYPES = (
    "u8",
    "i8",
    "u16",
    "i16",
    "u32",
    "i32",
    "u64",
    "i64",
    "u128",
    "i128",
    "usize",
    "isize",
)
FLOAT_TYPES = ("f32", "f64")
DERIVED_IMPLS = {
    ("Ordering", "Clone"),
    ("Ordering", "Copy"),
    ("Ordering", "Debug"),
    ("Ordering", "Hash"),
    ("Ordering", "PartialEq"),
    ("Ordering", "Eq"),
    ("Ordering", "PartialOrd"),
    ("Ordering", "Ord"),
    ("Reverse<T>", "Copy"),
    ("Reverse<T>", "Debug"),
    ("Reverse<T>", "Hash"),
    ("Reverse<T>", "PartialEq"),
    ("Reverse<T>", "Eq"),
    ("Reverse<T>", "Default"),
}

INVENTORY_CSV_FIELDS = (
    "row_id",
    "target",
    "api_kind",
    "implementation_kind",
    "owner_type",
    "trait_name",
    "method_name",
    "rustdoc_item_id",
    "rustdoc_impl_id",
    "source_file",
    "source_begin_line",
    "source_end_line",
    "stable_since",
    "disposition",
    "vstd_provenance_class",
)
EXCLUSION_CSV_FIELDS = (
    "candidate_id",
    "target",
    "candidate_kind",
    "rustdoc_item_id",
    "rustdoc_impl_id",
    "source_file",
    "source_begin_line",
    "reason",
    "stability",
)


class InventoryError(RuntimeError):
    """The live inventory or one of its audits is inconsistent."""


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def attr_text(item: dict[str, Any]) -> Iterable[str]:
    for attribute in item.get("attrs", []):
        if isinstance(attribute, dict) and isinstance(attribute.get("other"), str):
            yield attribute["other"]


def main_stability(item: dict[str, Any]) -> dict[str, str | None]:
    for text in attr_text(item):
        if not text.startswith("#[attr = Stability "):
            continue
        if "level: Stable" in text:
            match = re.search(
                r"since: Version\(RustcVersion \{ major: (\d+), minor: (\d+), patch: (\d+) \}\)",
                text,
            )
            return {
                "state": "stable",
                "since": ".".join(match.groups()) if match else None,
                "attribute": text,
            }
        if "level: Unstable" in text:
            feature = re.search(r'feature: Symbol\("([^"]+)"\)', text)
            issue = re.search(r"issue: Some\((\d+)\)", text)
            return {
                "state": "unstable",
                "since": None,
                "feature": feature.group(1) if feature else None,
                "issue": issue.group(1) if issue else None,
                "attribute": text,
            }
    return {"state": "none", "since": None, "attribute": None}


def const_stability(item: dict[str, Any]) -> dict[str, str | None]:
    for text in attr_text(item):
        if not text.startswith("#[attr = RustcConstStability "):
            continue
        level = "unstable" if "level: Unstable" in text else "stable"
        feature = re.search(r'feature: Symbol\("([^"]+)"\)', text)
        issue = re.search(r"issue: Some\((\d+)\)", text)
        return {
            "state": level,
            "feature": feature.group(1) if feature else None,
            "issue": issue.group(1) if issue else None,
            "attribute": text,
        }
    return {"state": "none", "feature": None, "issue": None, "attribute": None}


def deprecation(item: dict[str, Any]) -> dict[str, str | None] | None:
    for text in attr_text(item):
        if not text.startswith("#[attr = Deprecation "):
            continue
        since = re.search(r'since: Some\(Symbol\("([^"]+)"\)\)', text)
        note = re.search(r'note: Some\(Symbol\("([^"]+)"\)\)', text)
        return {
            "since": since.group(1) if since else None,
            "note": note.group(1) if note else None,
            "attribute": text,
        }
    return None


def render_const(value: Any) -> str:
    if isinstance(value, dict):
        expression = value.get("expr")
        if isinstance(expression, str) and expression:
            return expression
        if value.get("is_literal"):
            return str(value.get("value"))
        return compact_json(value)
    return str(value)


def render_generic_args(arguments: Any, self_type: str | None = None) -> str:
    if not arguments:
        return ""
    if "angle_bracketed" in arguments:
        rendered: list[str] = []
        for argument in arguments["angle_bracketed"].get("args", []):
            if "type" in argument:
                rendered.append(render_type(argument["type"], self_type))
            elif "lifetime" in argument:
                rendered.append(argument["lifetime"])
            elif "const" in argument:
                rendered.append(render_const(argument["const"]))
            else:
                rendered.append(compact_json(argument))
        return f"<{', '.join(rendered)}>" if rendered else ""
    if "parenthesized" in arguments:
        data = arguments["parenthesized"]
        inputs = ", ".join(render_type(value, self_type) for value in data.get("inputs", []))
        output = data.get("output")
        suffix = f" -> {render_type(output, self_type)}" if output is not None else ""
        return f"({inputs}){suffix}"
    return compact_json(arguments)


def render_type(value: Any, self_type: str | None = None) -> str:
    if value is None:
        return "()"
    if not isinstance(value, dict) or len(value) != 1:
        return compact_json(value)
    kind, data = next(iter(value.items()))
    if kind == "primitive":
        return data
    if kind == "generic":
        return self_type if data == "Self" and self_type is not None else data
    if kind == "array":
        return f"[{render_type(data['type'], self_type)}; {render_const(data['len'])}]"
    if kind == "slice":
        return f"[{render_type(data, self_type)}]"
    if kind == "borrowed_ref":
        lifetime = f"{data['lifetime']} " if data.get("lifetime") else ""
        mutable = "mut " if data.get("is_mutable") else ""
        return f"&{lifetime}{mutable}{render_type(data['type'], self_type)}"
    if kind == "raw_pointer":
        mutable = "mut" if data.get("is_mutable") else "const"
        return f"*{mutable} {render_type(data['type'], self_type)}"
    if kind == "resolved_path":
        return f"{data['path']}{render_generic_args(data.get('args'), self_type)}"
    if kind == "qualified_path":
        trait = data.get("trait")
        trait_path = trait.get("path", "") if trait else ""
        return (
            f"<{render_type(data['self_type'], self_type)} as {trait_path}>::{data['name']}"
            f"{render_generic_args(data.get('args'), self_type)}"
        )
    if kind == "tuple":
        values = ", ".join(render_type(item, self_type) for item in data)
        if len(data) == 1:
            values += ","
        return f"({values})"
    if kind == "never":
        return "!"
    if kind == "infer":
        return "_"
    if kind == "function_pointer":
        signature = data["sig"]
        inputs = ", ".join(render_type(item[1], self_type) for item in signature["inputs"])
        return f"fn({inputs}) -> {render_type(signature['output'], self_type)}"
    return compact_json(value)


def normalize_lifetimes(value: str) -> str:
    return re.sub(r"&'(?:_[A-Za-z0-9]*|[A-Za-z][A-Za-z0-9_]*)\s+", "&", value)


def normalize_signature_type(value: str) -> str:
    normalized = normalize_lifetimes(value)
    for qualified, canonical in (
        ("core::cmp::Ordering", "Ordering"),
        ("cmp::Ordering", "Ordering"),
        ("core::option::Option", "Option"),
    ):
        normalized = normalized.replace(qualified, canonical)
    return normalized


def reference_mutability_shape(value: str) -> str:
    remaining = normalize_signature_type(value)
    layers: list[str] = []
    while remaining.startswith("&"):
        remaining = remaining[1:]
        if remaining.startswith("mut "):
            layers.append("mutable")
            remaining = remaining[4:]
        else:
            layers.append("shared")
    return ">".join(layers) if layers else "by_value"


def render_bound(bound: dict[str, Any], include_const: bool) -> str:
    trait_bound = bound.get("trait_bound")
    if isinstance(trait_bound, dict):
        trait = trait_bound["trait"]
        prefix = (
            "[const] "
            if include_const and trait_bound.get("modifier") == "maybe_const"
            else ""
        )
        return f"{prefix}{trait['path']}{render_generic_args(trait.get('args'))}"
    outlives = bound.get("outlives")
    if isinstance(outlives, str):
        return outlives
    return compact_json(bound)


def generic_shape(generics: dict[str, Any]) -> dict[str, Any]:
    type_parameters: list[str] = []
    const_parameters: list[str] = []
    lifetime_parameters: list[str] = []
    runtime_bounds: list[str] = []
    source_bounds: list[str] = []
    for parameter in generics.get("params", []):
        name = parameter["name"]
        kind = parameter.get("kind", {})
        type_data = kind.get("type")
        if isinstance(type_data, dict):
            type_parameters.append(name)
            for bound in type_data.get("bounds", []):
                runtime_bounds.append(f"{name}:{render_bound(bound, False)}")
                source_bounds.append(f"{name}:{render_bound(bound, True)}")
        elif "const" in kind:
            const_parameters.append(name)
        elif "lifetime" in kind:
            lifetime_parameters.append(name)
    for predicate in generics.get("where_predicates", []):
        bounded = predicate.get("bound_predicate")
        if isinstance(bounded, dict):
            left = render_type(bounded["type"])
            for bound in bounded.get("bounds", []):
                runtime_bounds.append(f"{left}:{render_bound(bound, False)}")
                source_bounds.append(f"{left}:{render_bound(bound, True)}")
            continue
        lifetime = predicate.get("lifetime_predicate")
        if isinstance(lifetime, dict):
            for outlives in lifetime.get("outlives", []):
                runtime_bounds.append(f"{lifetime['lifetime']}:{outlives}")
                source_bounds.append(f"{lifetime['lifetime']}:{outlives}")
    return {
        "type_parameters": type_parameters,
        "const_parameters": const_parameters,
        "lifetime_parameters": lifetime_parameters,
        "runtime_bounds": sorted(set(runtime_bounds)),
        "source_bounds": sorted(set(source_bounds)),
    }


def trait_context_shape(trait_item: dict[str, Any]) -> dict[str, Any]:
    trait = trait_item["inner"]["trait"]
    shape = generic_shape(trait["generics"])
    for bound in trait.get("bounds", []):
        shape["runtime_bounds"].append(f"Self:{render_bound(bound, False)}")
        shape["source_bounds"].append(f"Self:{render_bound(bound, True)}")
    shape["runtime_bounds"] = sorted(set(shape["runtime_bounds"]))
    shape["source_bounds"] = sorted(set(shape["source_bounds"]))
    return shape


def function_signature(
    function: dict[str, Any],
    *,
    self_type: str | None,
    owner_generics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signature = function["sig"]
    method_generics = generic_shape(function.get("generics", {}))
    owner_shape = owner_generics or {
        "type_parameters": [],
        "const_parameters": [],
        "lifetime_parameters": [],
        "runtime_bounds": [],
        "source_bounds": [],
    }
    declared_inputs = [
        {"name": name, "type": render_type(value)}
        for name, value in signature.get("inputs", [])
    ]
    resolved_inputs = [
        {"name": name, "type": render_type(value, self_type)}
        for name, value in signature.get("inputs", [])
    ]
    declared_output = render_type(signature.get("output"))
    resolved_output = render_type(signature.get("output"), self_type)
    return {
        "declared_inputs": declared_inputs,
        "resolved_inputs": resolved_inputs,
        "declared_output": declared_output,
        "resolved_output": resolved_output,
        "owner_generics": owner_shape,
        "method_generics": method_generics,
        "header": function.get("header", {}),
        "is_c_variadic": bool(signature.get("is_c_variadic")),
    }


def matching_shape(row: dict[str, Any]) -> dict[str, Any]:
    signature = row["signature"]
    owner = signature["owner_generics"]
    method = signature["method_generics"]
    return {
        "target": row["target"],
        "inputs": [
            normalize_signature_type(item["type"])
            for item in signature["resolved_inputs"]
        ],
        "output": normalize_signature_type(signature["resolved_output"]),
        "type_parameters": owner["type_parameters"] + method["type_parameters"],
        "const_parameters": owner["const_parameters"] + method["const_parameters"],
        "runtime_bounds": sorted(
            set(owner["runtime_bounds"] + method["runtime_bounds"])
        ),
        "receiver_and_argument_mutability": [
            reference_mutability_shape(item["type"])
            for item in signature["resolved_inputs"]
        ],
        "implementation_identity": row["implementation_kind"],
    }


def source_span(item: dict[str, Any]) -> tuple[str, int | None, int | None]:
    span = item.get("span") or {}
    begin = span.get("begin") or [None]
    end = span.get("end") or [None]
    return span.get("filename", ""), begin[0], end[0]


def effective_stability(
    index: dict[str, Any],
    impl_item: dict[str, Any],
    method_item: dict[str, Any],
) -> dict[str, str | None]:
    impl_state = main_stability(impl_item)
    if impl_state["state"] == "unstable":
        return impl_state
    own_state = main_stability(method_item)
    if own_state["state"] != "none":
        return own_state
    implementation = impl_item["inner"]["impl"]
    trait = implementation.get("trait")
    if trait is not None:
        trait_item = index[str(trait["id"])]
        for trait_member_id in trait_item["inner"]["trait"].get("items", []):
            trait_member = index[str(trait_member_id)]
            if (
                trait_member.get("name") == method_item.get("name")
                and "function" in trait_member["inner"]
            ):
                trait_state = main_stability(trait_member)
                if trait_state["state"] != "none":
                    return trait_state
    if impl_state["state"] != "none":
        return impl_state
    return {"state": "none", "since": None, "attribute": None}


def read_rustdoc() -> dict[str, Any]:
    try:
        document = json.loads(RUSTDOC_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InventoryError(f"cannot read rustdoc JSON: {error}") from error
    if document.get("format_version") != 57:
        raise InventoryError(
            f"unexpected rustdoc format: {document.get('format_version')!r}"
        )
    manifest = provenance.read_json(provenance.CAMPAIGN_MANIFEST)
    hashed_inputs = {
        record["identifier"]: record for record in manifest.get("hash_only_inputs", [])
    }
    expected = hashed_inputs.get("rustdoc_core_json")
    if expected is None:
        raise InventoryError("campaign provenance does not bind rustdoc_core_json")
    if RUSTDOC_JSON.stat().st_size != expected["size_bytes"]:
        raise InventoryError("rustdoc JSON size does not match provenance")
    if provenance.sha256_file(RUSTDOC_JSON) != expected["sha256"]:
        raise InventoryError("rustdoc JSON hash does not match provenance")
    return document


def source_manifest_records() -> dict[str, dict[str, Any]]:
    manifest = provenance.read_json(provenance.SOURCE_MANIFEST_JSON)
    return {record["snapshot_path"]: record for record in manifest["records"]}


def snapshot_relpath(source_file: str) -> str:
    if source_file.startswith("core/src/") or source_file.startswith("std/src/"):
        return f"{RUST_SNAPSHOT_PREFIX}{source_file}"
    raise InventoryError(f"source file is outside the captured Rust tree: {source_file}")


def line_hash(path: Path, begin: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if begin < 1 or end < begin or end > len(lines):
        raise InventoryError(f"invalid source span {path}:{begin}-{end}")
    return provenance.sha256_bytes("".join(lines[begin - 1 : end]).encode("utf-8"))


def source_evidence(
    records: dict[str, dict[str, Any]],
    source_file: str,
    begin: int,
    end: int,
) -> dict[str, Any]:
    relative = snapshot_relpath(source_file)
    record = records.get(relative)
    if record is None:
        raise InventoryError(f"source snapshot is not in manifest: {relative}")
    path = CAMPAIGN_ROOT / relative
    return {
        "snapshot_path": relative,
        "snapshot_sha256": record["snapshot_sha256"],
        "span_sha256": line_hash(path, begin, end),
    }


def exclusion(
    *,
    candidate_id: str,
    target: str,
    candidate_kind: str,
    reason: str,
    stability: str,
    source_file: str,
    source_begin_line: int | None,
    rustdoc_item_id: int | None = None,
    rustdoc_impl_id: int | None = None,
    details: str = "",
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "target": target,
        "candidate_kind": candidate_kind,
        "rustdoc_item_id": rustdoc_item_id,
        "rustdoc_impl_id": rustdoc_impl_id,
        "source_file": source_file,
        "source_begin_line": source_begin_line,
        "reason": reason,
        "details": details,
        "stability": stability,
    }


def canonical_trait_name(
    implementation: dict[str, Any],
    self_type: str,
) -> str:
    trait = implementation["trait"]
    name = trait["path"]
    arguments = render_generic_args(trait.get("args"), self_type)
    if name in ("PartialEq", "PartialOrd") and not arguments:
        arguments = f"<{self_type}>"
    return f"{name}{arguments}"


def implementation_kind(
    self_type: str,
    trait_name: str,
    source_file: str,
    begin_line: int | None,
) -> str:
    if (self_type, trait_name) in DERIVED_IMPLS:
        return "compiler_derived_concrete"
    if source_file == "core/src/tuple.rs":
        return "source_macro_expanded_concrete"
    if source_file == CMP_SOURCE and begin_line in {
        1897,
        1909,
        1987,
        1990,
        2079,
    }:
        return "source_macro_expanded_concrete"
    return "manual_concrete"


def make_row(
    *,
    row_id: str,
    target: str,
    api_kind: str,
    implementation_kind_value: str,
    owner_type: str,
    trait_name: str,
    method_name: str,
    rustdoc_item_id: int | None,
    rustdoc_impl_id: int | None,
    source_file: str,
    source_begin_line: int,
    source_end_line: int,
    stable_since: str | None,
    const_state: dict[str, Any],
    signature: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    visibility: str = "rustdoc_visible",
    deprecation_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "row_id": row_id,
        "identity_key": row_id,
        "target": target,
        "api_kind": api_kind,
        "implementation_kind": implementation_kind_value,
        "owner_type": owner_type,
        "trait_name": trait_name,
        "method_name": method_name,
        "rustdoc_item_id": rustdoc_item_id,
        "rustdoc_impl_id": rustdoc_impl_id,
        "source_file": source_file,
        "source_begin_line": source_begin_line,
        "source_end_line": source_end_line,
        "source_visibility": visibility,
        "stable_since": stable_since,
        "const_callability": const_state,
        "deprecation": deprecation_record,
        "signature": signature,
        "source_evidence": source_evidence(
            source_records,
            source_file,
            source_begin_line,
            source_end_line,
        ),
        "disposition": "pending",
        "vstd_binding_ids": [],
        "vstd_provenance_class": "",
    }
    row["matching_shape"] = matching_shape(row)
    return row


def source_line(path: Path, line_number: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    if line_number < 1 or line_number > len(lines):
        raise InventoryError(f"source line is absent: {path}:{line_number}")
    return lines[line_number - 1]


def require_source_line(path: Path, line_number: int, fragment: str) -> None:
    if fragment not in source_line(path, line_number):
        raise InventoryError(
            f"required source fragment is absent at {path}:{line_number}: {fragment!r}"
        )


def manual_function_signature(
    inputs: Sequence[tuple[str, str]],
    output: str,
    *,
    type_parameters: Sequence[str] = (),
    const_parameters: Sequence[str] = (),
    lifetime_parameters: Sequence[str] = (),
    runtime_bounds: Sequence[str] = (),
    source_bounds: Sequence[str] | None = None,
    is_const: bool = False,
    is_unsafe: bool = False,
) -> dict[str, Any]:
    owner = {
        "type_parameters": list(type_parameters),
        "const_parameters": list(const_parameters),
        "lifetime_parameters": list(lifetime_parameters),
        "runtime_bounds": sorted(set(runtime_bounds)),
        "source_bounds": sorted(set(source_bounds or runtime_bounds)),
    }
    return {
        "declared_inputs": [{"name": name, "type": value} for name, value in inputs],
        "resolved_inputs": [{"name": name, "type": value} for name, value in inputs],
        "declared_output": output,
        "resolved_output": output,
        "owner_generics": owner,
        "method_generics": {
            "type_parameters": [],
            "const_parameters": [],
            "lifetime_parameters": [],
            "runtime_bounds": [],
            "source_bounds": [],
        },
        "header": {
            "is_const": is_const,
            "is_unsafe": is_unsafe,
            "is_async": False,
            "abi": "Rust",
        },
        "is_c_variadic": False,
    }


def derive_path_and_default_rows(
    document: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, int],
    dict[tuple[str, str], str],
    dict[str, dict[str, Any]],
]:
    index = document["index"]
    module_ids = [
        str(identifier)
        for identifier, record in document["paths"].items()
        if record.get("path") == ["core", "cmp"] and record.get("kind") == "module"
    ]
    if len(module_ids) != 1:
        raise InventoryError(f"expected one core::cmp module, found {module_ids}")
    trait_ids: dict[str, int] = {}
    trait_items: dict[str, dict[str, Any]] = {}
    for name in CMP_TRAITS:
        matches = [
            int(identifier)
            for identifier, record in document["paths"].items()
            if record.get("path") == ["core", "cmp", name]
            and record.get("kind") == "trait"
        ]
        if len(matches) != 1:
            raise InventoryError(f"expected one core::cmp::{name} trait, found {matches}")
        trait_ids[name] = matches[0]
        trait_items[name] = index[str(matches[0])]

    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    default_rows: dict[tuple[str, str], str] = {}
    module = index[module_ids[0]]["inner"]["module"]
    for raw_item_id in module["items"]:
        item_id = int(raw_item_id)
        item = index[str(item_id)]
        kind = next(iter(item["inner"]))
        state = main_stability(item)
        source_file, begin, end = source_span(item)
        name = item.get("name") or f"item-{item_id}"
        if kind == "function" and item["inner"]["function"].get("has_body"):
            if state["state"] == "stable":
                rows.append(
                    make_row(
                        row_id=f"rustdoc-{item_id}",
                        target=f"core::cmp::{name}",
                        api_kind="free_function",
                        implementation_kind_value="module_function",
                        owner_type="core::cmp",
                        trait_name="",
                        method_name=name,
                        rustdoc_item_id=item_id,
                        rustdoc_impl_id=None,
                        source_file=source_file,
                        source_begin_line=begin,
                        source_end_line=end,
                        stable_since=state["since"],
                        const_state=const_stability(item),
                        signature=function_signature(
                            item["inner"]["function"],
                            self_type=None,
                        ),
                        source_records=source_records,
                    )
                )
            else:
                exclusions.append(
                    exclusion(
                        candidate_id=f"rustdoc-{item_id}",
                        target=f"core::cmp::{name}",
                        candidate_kind="module_function",
                        reason="unstable_main_stability",
                        stability=state["state"],
                        source_file=source_file,
                        source_begin_line=begin,
                        rustdoc_item_id=item_id,
                    )
                )
        else:
            reason = (
                "unstable_non_executable_declaration"
                if state["state"] == "unstable"
                else "non_executable_declaration"
            )
            exclusions.append(
                exclusion(
                    candidate_id=f"rustdoc-{item_id}",
                    target=f"core::cmp::{name}",
                    candidate_kind=f"module_{kind}",
                    reason=reason,
                    stability=state["state"],
                    source_file=source_file,
                    source_begin_line=begin,
                    rustdoc_item_id=item_id,
                    details=(
                        "traits and public types are expanded into executable body "
                        "identities; derive macros and value constructors are not functions"
                    ),
                )
            )

    for trait_name in ("PartialEq", "Ord", "PartialOrd"):
        trait_item = trait_items[trait_name]
        context = trait_context_shape(trait_item)
        for raw_member_id in trait_item["inner"]["trait"]["items"]:
            member_id = int(raw_member_id)
            member = index[str(member_id)]
            if "function" not in member["inner"]:
                continue
            state = main_stability(member)
            source_file, begin, end = source_span(member)
            method_name = member["name"]
            function = member["inner"]["function"]
            if state["state"] == "stable" and function.get("has_body"):
                row_id = f"trait-default-{trait_ids[trait_name]}-{member_id}"
                rows.append(
                    make_row(
                        row_id=row_id,
                        target=f"{trait_name}::{method_name}",
                        api_kind="trait_default_method",
                        implementation_kind_value="trait_default",
                        owner_type=trait_name,
                        trait_name=trait_name,
                        method_name=method_name,
                        rustdoc_item_id=member_id,
                        rustdoc_impl_id=None,
                        source_file=source_file,
                        source_begin_line=begin,
                        source_end_line=end,
                        stable_since=state["since"],
                        const_state=const_stability(member),
                        signature=function_signature(
                            function,
                            self_type=None,
                            owner_generics=context,
                        ),
                        source_records=source_records,
                    )
                )
                default_rows[(trait_name, method_name)] = row_id
            elif state["state"] == "stable":
                exclusions.append(
                    exclusion(
                        candidate_id=f"trait-declaration-{trait_ids[trait_name]}-{member_id}",
                        target=f"{trait_name}::{method_name}",
                        candidate_kind="abstract_trait_method",
                        reason="required_trait_declaration_has_no_executable_body",
                        stability="stable",
                        source_file=source_file,
                        source_begin_line=begin,
                        rustdoc_item_id=member_id,
                        details=(
                            "the callable path is retained in the path audit, but each "
                            "effective concrete implementation body is inventoried instead"
                        ),
                    )
                )

    cmp_snapshot = CAMPAIGN_ROOT / f"{RUST_SNAPSHOT_PREFIX}{CMP_SOURCE}"
    require_source_line(
        cmp_snapshot,
        348,
        "fn assert_receiver_is_total_eq(&self) {}",
    )
    require_source_line(cmp_snapshot, 355, "fn assert_fields_are_eq(&self) {}")
    eq_context = trait_context_shape(trait_items["Eq"])
    hidden_eq_row_id = "source-trait-default-eq-assert_receiver_is_total_eq"
    hidden_eq_signature = manual_function_signature(
        (("self", "&Self"),),
        "()",
        type_parameters=eq_context["type_parameters"],
        const_parameters=eq_context["const_parameters"],
        lifetime_parameters=eq_context["lifetime_parameters"],
        runtime_bounds=eq_context["runtime_bounds"],
        source_bounds=eq_context["source_bounds"],
    )
    rows.append(
        make_row(
            row_id=hidden_eq_row_id,
            target="Eq::assert_receiver_is_total_eq",
            api_kind="trait_default_method",
            implementation_kind_value="trait_default",
            owner_type="Eq",
            trait_name="Eq",
            method_name="assert_receiver_is_total_eq",
            rustdoc_item_id=None,
            rustdoc_impl_id=None,
            source_file=CMP_SOURCE,
            source_begin_line=348,
            source_end_line=348,
            stable_since="1.0.0",
            const_state={
                "state": "unstable",
                "feature": "const_cmp",
                "issue": "143800",
                "attribute": "inherited from Eq trait rustc_const_unstable",
            },
            signature=hidden_eq_signature,
            source_records=source_records,
            visibility="doc_hidden_but_public_and_stable",
            deprecation_record={
                "since": "1.95.0",
                "note": "implementation detail of #[derive(Eq)]",
                "attribute": "source-derived",
            },
        )
    )
    default_rows[("Eq", "assert_receiver_is_total_eq")] = hidden_eq_row_id
    exclusions.append(
        exclusion(
            candidate_id="source-eq-assert_fields_are_eq",
            target="Eq::assert_fields_are_eq",
            candidate_kind="source_hidden_trait_method",
            reason="unstable_main_stability",
            stability="unstable",
            source_file=CMP_SOURCE,
            source_begin_line=355,
            details="derive_eq_internals, issue none",
        )
    )
    for line, method_name in (
        (1478, "__chaining_lt"),
        (1486, "__chaining_le"),
        (1494, "__chaining_gt"),
        (1502, "__chaining_ge"),
    ):
        require_source_line(cmp_snapshot, line, f"fn {method_name}")
        exclusions.append(
            exclusion(
                candidate_id=f"source-partialord-{method_name}",
                target=f"PartialOrd::{method_name}",
                candidate_kind="source_hidden_trait_method",
                reason="doc_hidden_perma_unstable_internal_dispatch",
                stability="unstable",
                source_file=CMP_SOURCE,
                source_begin_line=line,
                details="partial_ord_chaining_methods has issue none",
            )
        )
    require_source_line(cmp_snapshot, 418, "const fn as_raw(self) -> i8")
    exclusions.append(
        exclusion(
            candidate_id="source-ordering-as_raw",
            target="Ordering::as_raw",
            candidate_kind="private_inherent_method",
            reason="private_non_public_method",
            stability="internal",
            source_file=CMP_SOURCE,
            source_begin_line=418,
        )
    )
    return rows, exclusions, trait_ids, default_rows, trait_items


def derive_impl_rows(
    document: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    trait_ids: dict[str, int],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    index = document["index"]
    cmp_trait_by_id = {value: key for key, value in trait_ids.items()}
    primitive_stability: dict[str, dict[str, Any]] = {}
    for item_id, item in index.items():
        if "primitive" not in item.get("inner", {}) or not item.get("name"):
            continue
        primitive_stability[item["name"]] = {
            "rustdoc_item_id": int(item_id),
            **main_stability(item),
        }
    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    cmp_impl_seeds: list[dict[str, Any]] = []
    included_member_ids: set[int] = set()
    out_of_scope_impl_counts: Counter[str] = Counter()
    out_of_scope_method_counts: Counter[str] = Counter()

    for raw_impl_id, impl_item in index.items():
        if "impl" not in impl_item.get("inner", {}):
            continue
        impl_id = int(raw_impl_id)
        implementation = impl_item["inner"]["impl"]
        trait = implementation.get("trait")
        trait_id = int(trait["id"]) if trait else None
        trait_name = trait["path"] if trait else ""
        source_file, impl_begin, impl_end = source_span(impl_item)
        self_type = render_type(implementation["for"])
        is_cmp_trait_impl = (
            source_file in CMP_TRAIT_SOURCE_FILES and trait_id in cmp_trait_by_id
        )
        is_public_cmp_type_impl = (
            source_file == CMP_SOURCE and self_type in PUBLIC_CMP_TYPES
        ) or (
            source_file == CMP_SOURCE and self_type == "Reverse<T>"
        )
        if (
            trait_id in cmp_trait_by_id
            and source_file not in CMP_TRAIT_SOURCE_FILES
            and not implementation.get("is_synthetic")
            and implementation.get("blanket_impl") is None
        ):
            out_of_scope_impl_counts[source_file or "<no-source-span>"] += 1
            out_of_scope_method_counts[source_file or "<no-source-span>"] += sum(
                "function" in index[str(member_id)]["inner"]
                for member_id in implementation.get("items", [])
            )
        if not is_cmp_trait_impl and not is_public_cmp_type_impl:
            continue
        if implementation.get("is_synthetic"):
            continue
        if implementation.get("blanket_impl") is not None:
            continue

        impl_state = main_stability(impl_item)
        self_type_state = primitive_stability.get(self_type)
        unstable_self_type = (
            self_type_state is not None
            and self_type_state["state"] == "unstable"
        )
        kind = implementation_kind(self_type, trait_name, source_file, impl_begin)
        impl_generics = generic_shape(implementation.get("generics", {}))
        method_decisions: list[dict[str, Any]] = []
        for raw_member_id in implementation.get("items", []):
            member_id = int(raw_member_id)
            member = index[str(member_id)]
            member_kind = next(iter(member["inner"]))
            member_name = member.get("name") or f"item-{member_id}"
            member_source, begin, end = source_span(member)
            effective = effective_stability(index, impl_item, member)
            if trait is None:
                target = f"{self_type}::{member_name}"
            else:
                target = (
                    f"<{self_type} as "
                    f"{canonical_trait_name(implementation, self_type)}>::{member_name}"
                )
            decision = "included"
            reason = "stable_source_owned_executable_body"
            if member_kind != "function":
                decision = "excluded"
                reason = "non_executable_associated_item"
            elif not member["inner"]["function"].get("has_body"):
                decision = "excluded"
                reason = "method_has_no_body"
            elif unstable_self_type:
                decision = "excluded"
                reason = "unstable_self_type"
            elif impl_state["state"] == "unstable":
                decision = "excluded"
                reason = "unstable_implementation"
            elif effective["state"] != "stable":
                decision = "excluded"
                reason = "unstable_or_non_public_effective_stability"

            method_decisions.append(
                {
                    "rustdoc_item_id": member_id,
                    "target": target,
                    "name": member_name,
                    "kind": member_kind,
                    "effective_stability": effective["state"],
                    "decision": decision,
                    "reason": reason,
                }
            )
            if decision == "included":
                if member_id in included_member_ids:
                    raise InventoryError(f"duplicate rustdoc member inclusion: {member_id}")
                included_member_ids.add(member_id)
                rows.append(
                    make_row(
                        row_id=f"rustdoc-{impl_id}-{member_id}",
                        target=target,
                        api_kind=(
                            "inherent_method" if trait is None else "trait_impl_method"
                        ),
                        implementation_kind_value=(
                            "inherent_concrete"
                            if trait is None
                            else implementation_kind(
                                self_type,
                                trait_name,
                                member_source or source_file,
                                begin,
                            )
                        ),
                        owner_type=self_type,
                        trait_name=trait_name,
                        method_name=member_name,
                        rustdoc_item_id=member_id,
                        rustdoc_impl_id=impl_id,
                        source_file=member_source or source_file,
                        source_begin_line=begin,
                        source_end_line=end,
                        stable_since=effective["since"],
                        const_state=const_stability(member),
                        signature=function_signature(
                            member["inner"]["function"],
                            self_type=self_type,
                            owner_generics=impl_generics,
                        ),
                        source_records=source_records,
                        deprecation_record=deprecation(member),
                    )
                )
            else:
                exclusions.append(
                    exclusion(
                        candidate_id=f"rustdoc-{impl_id}-{member_id}",
                        target=target,
                        candidate_kind=f"impl_{member_kind}",
                        reason=reason,
                        stability=(
                            "unstable" if unstable_self_type else effective["state"]
                        ),
                        source_file=member_source or source_file,
                        source_begin_line=begin,
                        rustdoc_item_id=member_id,
                        rustdoc_impl_id=impl_id,
                        details=(
                            f"self type rustdoc item {self_type_state['rustdoc_item_id']} "
                            "has unstable main stability"
                            if unstable_self_type
                            else ""
                        ),
                    )
                )

        seed = {
            "rustdoc_impl_id": impl_id,
            "trait_name": trait_name,
            "trait_id": trait_id,
            "self_type": self_type,
            "source_file": source_file,
            "source_begin_line": impl_begin,
            "source_end_line": impl_end,
            "main_stability": (
                {
                    **self_type_state,
                    "state": "unstable",
                    "reason": "unstable_self_type",
                }
                if unstable_self_type
                else impl_state
            ),
            "self_type_stability": self_type_state,
            "implementation_kind": kind,
            "impl_generics": impl_generics,
            "method_decisions": method_decisions,
            "source_visibility": "rustdoc_visible",
        }
        if is_cmp_trait_impl:
            cmp_impl_seeds.append(seed)

    public_type_impl_decisions: list[dict[str, Any]] = []
    for type_name in PUBLIC_CMP_TYPES:
        matches = [
            (str(identifier), record)
            for identifier, record in document["paths"].items()
            if record.get("path") == ["core", "cmp", type_name]
            and record.get("kind") in ("enum", "struct")
        ]
        if len(matches) != 1:
            raise InventoryError(f"cannot resolve core::cmp::{type_name}")
        item = index[matches[0][0]]
        item_kind = next(iter(item["inner"]))
        for raw_impl_id in item["inner"][item_kind]["impls"]:
            impl_id = int(raw_impl_id)
            impl_item = index[str(impl_id)]
            implementation = impl_item["inner"]["impl"]
            source_file, begin, end = source_span(impl_item)
            trait = implementation.get("trait")
            trait_name = trait["path"] if trait else ""
            if implementation.get("is_synthetic"):
                decision = "excluded_compiler_auto_trait"
            elif implementation.get("blanket_impl") is not None:
                decision = "excluded_externally_owned_blanket_impl"
            elif source_file != CMP_SOURCE:
                decision = "excluded_implementation_owned_outside_core_cmp"
            else:
                decision = "owned_by_core_cmp"
            public_type_impl_decisions.append(
                {
                    "associated_public_type": type_name,
                    "rustdoc_impl_id": impl_id,
                    "trait_name": trait_name,
                    "source_file": source_file,
                    "source_begin_line": begin,
                    "source_end_line": end,
                    "is_synthetic": bool(implementation.get("is_synthetic")),
                    "is_blanket": implementation.get("blanket_impl") is not None,
                    "decision": decision,
                    "explicit_item_count": len(implementation.get("items", [])),
                }
            )
    out_of_scope = {
        "rule": (
            "cmp-trait implementations declared outside the captured cmp, slice, "
            "array, tuple, and option ownership sources are not campaign identities"
        ),
        "impl_count": sum(out_of_scope_impl_counts.values()),
        "explicit_method_item_count": sum(out_of_scope_method_counts.values()),
        "impl_counts_by_source_file": dict(sorted(out_of_scope_impl_counts.items())),
        "method_counts_by_source_file": dict(
            sorted(out_of_scope_method_counts.items())
        ),
    }
    return (
        rows,
        exclusions,
        cmp_impl_seeds,
        public_type_impl_decisions,
        out_of_scope,
    )


def synthesize_hidden_tuple_rows(
    source_records: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tuple_source = "core/src/tuple.rs"
    path = CAMPAIGN_ROOT / f"{RUST_SNAPSHOT_PREFIX}{tuple_source}"
    require_source_line(
        path,
        238,
        "tuple_impls!(E D C B A Z Y X W V U T);",
    )
    text = path.read_text(encoding="utf-8")
    required_fragments = (
        "fn eq(&self, other: &($($T,)+)) -> bool",
        "fn ne(&self, other: &($($T,)+)) -> bool",
        "fn partial_cmp(&self, other: &($($T,)+)) -> Option<Ordering>",
        "fn lt(&self, other: &($($T,)+)) -> bool",
        "fn le(&self, other: &($($T,)+)) -> bool",
        "fn ge(&self, other: &($($T,)+)) -> bool",
        "fn gt(&self, other: &($($T,)+)) -> bool",
        "fn cmp(&self, other: &($($T,)+)) -> Ordering",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise InventoryError(f"tuple macro bodies are missing: {missing}")

    rows: list[dict[str, Any]] = []
    impl_seeds: list[dict[str, Any]] = []
    methods = {
        "PartialEq": (("eq", "bool"), ("ne", "bool")),
        "Eq": (),
        "PartialOrd": (
            ("partial_cmp", "Option<Ordering>"),
            ("lt", "bool"),
            ("le", "bool"),
            ("ge", "bool"),
            ("gt", "bool"),
        ),
        "Ord": (("cmp", "Ordering"),),
    }
    for arity in range(2, 13):
        parameters = TUPLE_PARAMETERS[-arity:]
        tuple_type = f"({', '.join(parameters)})"
        for trait_name in CMP_TRAITS:
            method_decisions: list[dict[str, Any]] = []
            row_ids: dict[str, str] = {}
            runtime_bounds = [f"{name}:{trait_name}" for name in parameters]
            source_bounds = [f"{name}:[const] {trait_name}" for name in parameters]
            for method_name, output in methods[trait_name]:
                row_id = (
                    f"source-tuple-arity-{arity:02d}-"
                    f"{trait_name.lower()}-{method_name}"
                )
                row_ids[method_name] = row_id
                target_trait = trait_name
                if trait_name in ("PartialEq", "PartialOrd"):
                    target_trait += f"<{tuple_type}>"
                signature = manual_function_signature(
                    (("self", f"&{tuple_type}"), ("other", f"&{tuple_type}")),
                    output,
                    type_parameters=parameters,
                    runtime_bounds=runtime_bounds,
                    source_bounds=source_bounds,
                    is_const=False,
                )
                rows.append(
                    make_row(
                        row_id=row_id,
                        target=f"<{tuple_type} as {target_trait}>::{method_name}",
                        api_kind="trait_impl_method",
                        implementation_kind_value="source_hidden_macro_expanded_concrete",
                        owner_type=tuple_type,
                        trait_name=trait_name,
                        method_name=method_name,
                        rustdoc_item_id=None,
                        rustdoc_impl_id=None,
                        source_file=tuple_source,
                        source_begin_line=238,
                        source_end_line=238,
                        stable_since="1.0.0",
                        const_state={
                            "state": "unstable",
                            "feature": "const_cmp",
                            "issue": "143800",
                            "attribute": "source-derived rustc_const_unstable",
                        },
                        signature=signature,
                        source_records=source_records,
                        visibility="doc_hidden_source_macro_expansion",
                    )
                )
                method_decisions.append(
                    {
                        "rustdoc_item_id": None,
                        "target": f"<{tuple_type} as {target_trait}>::{method_name}",
                        "name": method_name,
                        "kind": "function",
                        "effective_stability": "stable",
                        "decision": "included",
                        "reason": "stable_source_hidden_macro_expansion",
                        "row_id": row_id,
                    }
                )
            impl_seeds.append(
                {
                    "rustdoc_impl_id": None,
                    "source_identity": f"tuple-arity-{arity:02d}-{trait_name.lower()}",
                    "trait_name": trait_name,
                    "trait_id": None,
                    "self_type": tuple_type,
                    "source_file": tuple_source,
                    "source_begin_line": 238,
                    "source_end_line": 238,
                    "main_stability": {"state": "stable", "since": "1.0.0"},
                    "implementation_kind": "source_hidden_macro_expanded_concrete",
                    "impl_generics": {
                        "type_parameters": list(parameters),
                        "const_parameters": [],
                        "lifetime_parameters": [],
                        "runtime_bounds": sorted(runtime_bounds),
                        "source_bounds": sorted(source_bounds),
                    },
                    "method_decisions": method_decisions,
                    "source_visibility": "doc_hidden_source_macro_expansion",
                    "row_ids": row_ids,
                }
            )
    return rows, impl_seeds


def build_ownership(
    cmp_impl_seeds: list[dict[str, Any]],
    hidden_tuple_impl_seeds: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    default_rows: dict[tuple[str, str], str],
    public_type_impl_decisions: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    row_by_impl_method = {
        (row["rustdoc_impl_id"], row["method_name"]): row["row_id"]
        for row in rows
        if row["rustdoc_impl_id"] is not None and row["trait_name"] in CMP_TRAITS
    }
    ownership_records: list[dict[str, Any]] = []
    default_binding_records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    overlap: list[dict[str, Any]] = []

    for seed in [*cmp_impl_seeds, *hidden_tuple_impl_seeds]:
        trait_name = seed["trait_name"]
        stable = seed["main_stability"]["state"] != "unstable"
        explicit_names = {
            decision["name"]
            for decision in seed["method_decisions"]
            if decision["decision"] == "included"
        }
        bindings: list[dict[str, Any]] = []
        if stable:
            for method_name in CMP_TRAIT_METHODS[trait_name]:
                explicit_row_id = None
                if method_name in explicit_names:
                    if seed["rustdoc_impl_id"] is not None:
                        explicit_row_id = row_by_impl_method.get(
                            (seed["rustdoc_impl_id"], method_name)
                        )
                    else:
                        explicit_row_id = seed.get("row_ids", {}).get(method_name)
                    if explicit_row_id is None:
                        unresolved.append(
                            {
                                "implementation": seed.get(
                                    "source_identity",
                                    f"rustdoc-{seed['rustdoc_impl_id']}",
                                ),
                                "trait": trait_name,
                                "method": method_name,
                                "reason": "explicit method has no inventory row",
                            }
                        )
                        continue
                    owner_kind = "concrete_override"
                    owner_row_id = explicit_row_id
                else:
                    owner_row_id = default_rows.get((trait_name, method_name))
                    if owner_row_id is None:
                        unresolved.append(
                            {
                                "implementation": seed.get(
                                    "source_identity",
                                    f"rustdoc-{seed['rustdoc_impl_id']}",
                                ),
                                "trait": trait_name,
                                "method": method_name,
                                "reason": "required method has no explicit body",
                            }
                        )
                        continue
                    owner_kind = "inherited_trait_default"
                if explicit_row_id is not None and (trait_name, method_name) in default_rows:
                    if owner_row_id == default_rows[(trait_name, method_name)]:
                        overlap.append(
                            {
                                "implementation": seed.get(
                                    "source_identity",
                                    f"rustdoc-{seed['rustdoc_impl_id']}",
                                ),
                                "trait": trait_name,
                                "method": method_name,
                            }
                        )
                binding = {
                    "method": method_name,
                    "owner_kind": owner_kind,
                    "owner_row_id": owner_row_id,
                }
                bindings.append(binding)
                if method_name in CMP_DEFAULT_METHODS[trait_name]:
                    default_binding_records.append(
                        {
                            "implementation": seed.get(
                                "source_identity",
                                f"rustdoc-{seed['rustdoc_impl_id']}",
                            ),
                            "rustdoc_impl_id": seed["rustdoc_impl_id"],
                            "self_type": seed["self_type"],
                            "trait_name": trait_name,
                            "method_name": method_name,
                            "effective_owner": owner_kind,
                            "owner_row_id": owner_row_id,
                            "default_row_id": default_rows[(trait_name, method_name)],
                        }
                    )
        ownership_records.append(
            {
                **seed,
                "stable_runtime_implementation": stable,
                "explicit_method_names": sorted(explicit_names),
                "effective_method_bindings": bindings,
            }
        )

    stable_records = [
        record for record in ownership_records if record["stable_runtime_implementation"]
    ]
    per_trait_counts = Counter(record["trait_name"] for record in stable_records)
    owner_counts = Counter(
        record["effective_owner"] for record in default_binding_records
    )
    ownership = {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "ownership_rule": (
            "one row per stable executable body: a trait default is owned once; "
            "each explicit concrete, blanket, macro-expanded, or compiler-derived "
            "override is owned once; inherited defaults bind back to the shared "
            "default row; source-hidden tuple arities are expanded from the captured "
            "macro; private specialization bodies are audited separately"
        ),
        "rustdoc_visible_cmp_trait_impl_count": len(cmp_impl_seeds),
        "source_hidden_tuple_impl_count": len(hidden_tuple_impl_seeds),
        "adjudicated_cmp_trait_impl_count": len(ownership_records),
        "stable_cmp_trait_impl_count": len(stable_records),
        "unstable_cmp_trait_impl_count": len(ownership_records) - len(stable_records),
        "stable_impl_counts_by_trait": dict(sorted(per_trait_counts.items())),
        "public_type_impl_decisions": sorted(
            public_type_impl_decisions,
            key=lambda record: (
                record["associated_public_type"],
                record["rustdoc_impl_id"],
            ),
        ),
        "records": sorted(
            ownership_records,
            key=lambda record: (
                record["trait_name"],
                record["self_type"],
                record.get("source_identity", ""),
                record["rustdoc_impl_id"] or -1,
            ),
        ),
    }
    default_audit = {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "status": "pass" if not unresolved and not overlap else "fail",
        "default_body_identity_count": len(default_rows),
        "default_binding_slot_count": len(default_binding_records),
        "binding_owner_counts": dict(sorted(owner_counts.items())),
        "unresolved_binding_count": len(unresolved),
        "concrete_default_overlap_count": len(overlap),
        "unresolved_bindings": unresolved,
        "concrete_default_overlaps": overlap,
        "records": sorted(
            default_binding_records,
            key=lambda record: (
                record["trait_name"],
                record["method_name"],
                record["self_type"],
                record["implementation"],
            ),
        ),
    }
    if default_audit["status"] != "pass":
        raise InventoryError(
            "default implementation ownership is unresolved or overlapping"
        )
    return ownership, default_audit


def parse_marker_impls() -> list[dict[str, Any]]:
    bytewise_path = (
        CAMPAIGN_ROOT
        / f"{RUST_SNAPSHOT_PREFIX}core/src/cmp/bytewise.rs"
    )
    slice_path = (
        CAMPAIGN_ROOT
        / f"{RUST_SNAPSHOT_PREFIX}core/src/slice/cmp.rs"
    )
    bytewise_text = bytewise_path.read_text(encoding="utf-8")
    slice_text = slice_path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []

    calls = re.findall(
        r"is_bytewise_comparable!\(\s*(.*?)\s*\);",
        bytewise_text,
        flags=re.DOTALL,
    )
    if len(calls) != 4:
        raise InventoryError(f"expected four BytewiseEq macro calls, found {len(calls)}")
    bytewise_types: list[str] = []
    for call in calls:
        without_comments = re.sub(r"//.*", "", call)
        bytewise_types.extend(
            item.strip() for item in without_comments.split(",") if item.strip()
        )
    length_match = re.search(
        r"is_bytewise_comparable_array_length!\(([^)]+)\);",
        bytewise_text,
    )
    if length_match is None:
        raise InventoryError("BytewiseEq array-length marker invocation is absent")
    lengths = [
        item.strip() for item in length_match.group(1).split(",") if item.strip()
    ]
    for index, type_name in enumerate(bytewise_types, start=1):
        records.append(
            {
                "marker_id": f"bytewise-eq-{index:02d}",
                "marker_trait": "BytewiseEq",
                "target_type": type_name,
                "source_file": "core/src/cmp/bytewise.rs",
                "executable_body": False,
                "role": "specialization_eligibility_safety_assertion",
            }
        )
    for index, length in enumerate(lengths, start=1):
        records.append(
            {
                "marker_id": f"bytewise-eq-array-{index:02d}",
                "marker_trait": "BytewiseEq",
                "target_type": f"[T; {length}] as BytewiseEq<[U; {length}]>",
                "source_file": "core/src/cmp/bytewise.rs",
                "executable_body": False,
                "role": "specialization_eligibility_safety_assertion",
            }
        )

    always_match = re.search(
        r"always_applicable_ord!\s*\{\s*(.*?)\s*\}",
        slice_text,
        flags=re.DOTALL,
    )
    if always_match is None:
        raise InventoryError("AlwaysApplicableOrd marker invocation is absent")
    always_types = [
        match.group(1).strip()
        for match in re.finditer(
            r"\[[^\]]*\]\s*([^,]+),",
            always_match.group(1),
        )
    ]
    for index, type_name in enumerate(always_types, start=1):
        records.append(
            {
                "marker_id": f"always-applicable-ord-{index:02d}",
                "marker_trait": "AlwaysApplicableOrd",
                "target_type": type_name,
                "source_file": "core/src/slice/cmp.rs",
                "executable_body": False,
                "role": "specialization_eligibility_assertion",
            }
        )

    unsigned_types = re.findall(
        r"unsafe impl const UnsignedBytewiseOrd for ([^{]+) \{\}",
        slice_text,
    )
    for index, type_name in enumerate(unsigned_types, start=1):
        records.append(
            {
                "marker_id": f"unsigned-bytewise-ord-{index:02d}",
                "marker_trait": "UnsignedBytewiseOrd",
                "target_type": type_name.strip(),
                "source_file": "core/src/slice/cmp.rs",
                "executable_body": False,
                "role": "specialization_eligibility_safety_assertion",
            }
        )
    return records


def build_specialization_audit() -> dict[str, Any]:
    slice_path = (
        CAMPAIGN_ROOT
        / f"{RUST_SNAPSHOT_PREFIX}core/src/slice/cmp.rs"
    )
    array_path = (
        CAMPAIGN_ROOT
        / f"{RUST_SNAPSHOT_PREFIX}core/src/array/equality.rs"
    )
    slots = (
        (
            "slice_partial_eq_equal_same_length",
            "core/src/slice/cmp.rs",
            "SlicePartialEq",
            "equal_same_length",
            126,
            152,
            "BytewiseEq",
            ("<[T] as PartialEq<[U]>>::eq",),
        ),
        (
            "array_spec_eq",
            "core/src/array/equality.rs",
            "SpecArrayEq",
            "spec_eq",
            143,
            153,
            "BytewiseEq",
            ("<[T; N] as PartialEq<[U; N]>>::eq",),
        ),
        (
            "array_spec_ne",
            "core/src/array/equality.rs",
            "SpecArrayEq",
            "spec_ne",
            146,
            159,
            "BytewiseEq",
            ("<[T; N] as PartialEq<[U; N]>>::ne",),
        ),
        (
            "slice_partial_ord_partial_compare",
            "core/src/slice/cmp.rs",
            "SlicePartialOrd",
            "partial_compare",
            184,
            261,
            "AlwaysApplicableOrd",
            ("<[T] as PartialOrd<[T]>>::partial_cmp",),
        ),
        (
            "slice_chain_lt",
            "core/src/slice/cmp.rs",
            "SliceChain",
            "chaining_lt",
            207,
            369,
            "UnsignedBytewiseOrd",
            ("<[T] as PartialOrd<[T]>>::lt",),
        ),
        (
            "slice_chain_le",
            "core/src/slice/cmp.rs",
            "SliceChain",
            "chaining_le",
            210,
            376,
            "UnsignedBytewiseOrd",
            ("<[T] as PartialOrd<[T]>>::le",),
        ),
        (
            "slice_chain_gt",
            "core/src/slice/cmp.rs",
            "SliceChain",
            "chaining_gt",
            213,
            383,
            "UnsignedBytewiseOrd",
            ("<[T] as PartialOrd<[T]>>::gt",),
        ),
        (
            "slice_chain_ge",
            "core/src/slice/cmp.rs",
            "SliceChain",
            "chaining_ge",
            216,
            390,
            "UnsignedBytewiseOrd",
            ("<[T] as PartialOrd<[T]>>::ge",),
        ),
        (
            "slice_ord_compare",
            "core/src/slice/cmp.rs",
            "SliceOrd",
            "compare",
            295,
            342,
            "UnsignedBytewiseOrd",
            ("<[T] as Ord>::cmp",),
        ),
    )
    identities: list[dict[str, Any]] = []
    slot_records: list[dict[str, Any]] = []
    for (
        slot_id,
        source_file,
        trait_name,
        method_name,
        default_line,
        specialized_line,
        marker,
        callers,
    ) in slots:
        path = slice_path if "slice/" in source_file else array_path
        require_source_line(path, default_line, f"fn {method_name}")
        require_source_line(path, specialized_line, f"fn {method_name}")
        if "default " not in source_line(path, default_line):
            raise InventoryError(
                f"specialization default marker is absent at {source_file}:{default_line}"
            )
        identities.extend(
            (
                {
                    "identity_id": f"{slot_id}-default",
                    "slot_id": slot_id,
                    "implementation_kind": "specialization_default",
                    "trait_name": trait_name,
                    "method_name": method_name,
                    "source_file": source_file,
                    "source_begin_line": default_line,
                    "selection_predicate": "generic trait bound",
                    "public_callers": list(callers),
                },
                {
                    "identity_id": f"{slot_id}-specialized",
                    "slot_id": slot_id,
                    "implementation_kind": "specialized_override",
                    "trait_name": trait_name,
                    "method_name": method_name,
                    "source_file": source_file,
                    "source_begin_line": specialized_line,
                    "selection_predicate": marker,
                    "public_callers": list(callers),
                },
            )
        )
        slot_records.append(
            {
                "slot_id": slot_id,
                "trait_name": trait_name,
                "method_name": method_name,
                "default_identity": f"{slot_id}-default",
                "specialized_identities": [f"{slot_id}-specialized"],
                "selection_marker": marker,
                "incomparable_specialized_candidate_count": 0,
                "selection_is_unambiguous": True,
            }
        )

    slice_text = slice_path.read_text(encoding="utf-8")
    commented_start = slice_text.find(
        "// This is the impl that we would like to have. Unfortunately it's not sound."
    )
    commented_impl = slice_text.find("impl<A> SlicePartialOrd for A", commented_start)
    comment_close = slice_text.find("*/", commented_impl)
    if min(commented_start, commented_impl, comment_close) < 0:
        raise InventoryError("commented unsound SlicePartialOrd candidate is not preserved")
    for line_number, fragment in (
        (398, "trait SliceContains"),
        (406, "default fn slice_contains"),
        (411, "impl SliceContains for u8"),
        (418, "impl SliceContains for i8"),
        (455, "impl_slice_contains!("),
    ):
        require_source_line(slice_path, line_number, fragment)
    contains_types_match = re.search(
        r"impl_slice_contains!\(([^)]+)\);",
        slice_text,
    )
    if contains_types_match is None:
        raise InventoryError("SliceContains concrete specialization list is absent")
    contains_macro_types = [
        item.strip()
        for item in contains_types_match.group(1).split(",")
        if item.strip()
    ]
    marker_records = parse_marker_impls()
    marker_counts = Counter(record["marker_trait"] for record in marker_records)
    ambiguous_slots = [
        record for record in slot_records if not record["selection_is_unambiguous"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "status": "pass" if not ambiguous_slots else "fail",
        "public_inventory_includes_private_specialization_identities": False,
        "specialization_slot_count": len(slot_records),
        "specialization_executable_identity_count": len(identities),
        "marker_impl_count": len(marker_records),
        "marker_impl_counts_by_trait": dict(sorted(marker_counts.items())),
        "ambiguous_slot_count": len(ambiguous_slots),
        "slots": slot_records,
        "identities": identities,
        "marker_impls": marker_records,
        "nested_dispatch_paths": [
            {
                "public_target": "<[T] as PartialOrd<[T]>>::partial_cmp",
                "path": [
                    "SlicePartialOrd::partial_compare specialized by AlwaysApplicableOrd",
                    "SliceOrd::compare specialized independently by UnsignedBytewiseOrd",
                ],
                "ambiguity": False,
                "reason": "the markers select different trait slots in a nested call",
            },
            {
                "public_target": "<[T; N] as PartialEq<[U; N]>>::eq/ne",
                "path": [
                    "SpecArrayEq selects its own BytewiseEq override",
                    "the generic SpecArrayEq path delegates to slice equality",
                    "SlicePartialEq then performs its independent BytewiseEq selection",
                ],
                "ambiguity": False,
                "reason": "each dispatch point has one default and one strictly more specific impl",
            },
        ],
        "excluded_specialization_candidate": {
            "target": "SlicePartialOrd::partial_compare for A: Ord",
            "status": "commented_out",
            "reason": "captured source explicitly states that the candidate is unsound",
            "source_file": "core/src/slice/cmp.rs",
            "source_begin_line": 245,
            "source_end_line": 258,
        },
        "excluded_out_of_scope_specialization_families": [
            {
                "trait_name": "SliceContains",
                "method_name": "slice_contains",
                "source_file": "core/src/slice/cmp.rs",
                "source_begin_line": 398,
                "default_identity_count": 1,
                "concrete_override_count": 2 + len(contains_macro_types),
                "executable_identity_count": 3 + len(contains_macro_types),
                "macro_override_types": contains_macro_types,
                "reason": (
                    "dispatches from the slice inherent contains API, not from a "
                    "stable executable core::cmp identity"
                ),
            }
        ],
    }


def vstd_dirty_status() -> dict[str, str]:
    preservation = provenance.read_json(provenance.PRESERVATION_MANIFEST)
    status = preservation["canonical_checkouts"]["verus"]["status_porcelain_v1"]
    result: dict[str, str] = {}
    for line in status.splitlines():
        if len(line) >= 4:
            result[line[3:]] = line[:2]
    return result


def find_unique_line(path: Path, needle: str) -> int:
    matches = [
        index
        for index, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        )
        if needle in line
    ]
    if len(matches) != 1:
        raise InventoryError(
            f"expected one occurrence of {needle!r} in {path}, found {matches}"
        )
    return matches[0]


def assume_declaration_span(path: Path, start_line: int) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index in range(start_line - 1, len(lines)):
        stripped = lines[index].strip()
        if index == start_line - 1 and stripped.endswith(";"):
            return start_line, start_line
        if index > start_line - 1 and stripped == ";":
            return start_line, index + 1
    raise InventoryError(f"unterminated assume_specification at {path}:{start_line}")


def candidate_shape(
    target: str,
    inputs: Sequence[str],
    output: str,
    implementation_identity: str,
    *,
    type_parameters: Sequence[str] = (),
    const_parameters: Sequence[str] = (),
    runtime_bounds: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "target": target,
        "inputs": list(inputs),
        "output": output,
        "type_parameters": list(type_parameters),
        "const_parameters": list(const_parameters),
        "runtime_bounds": sorted(set(runtime_bounds)),
        "receiver_and_argument_mutability": [
            reference_mutability_shape(item) for item in inputs
        ],
        "implementation_identity": implementation_identity,
    }


def vstd_file_record(relative_path: str, dirty: dict[str, str]) -> dict[str, Any]:
    snapshot = f"{VSTD_SNAPSHOT_PREFIX}{relative_path}"
    path = CAMPAIGN_ROOT / snapshot
    checkout_path = f"source/vstd/{relative_path}"
    status_code = dirty.get(checkout_path, "")
    return {
        "snapshot_path": snapshot,
        "snapshot_sha256": provenance.sha256_file(path),
        "checkout_path": checkout_path,
        "git_status_code": status_code,
        "candidate_source_tracked_clean_at_head": not status_code,
        "candidate_source_untracked": status_code == "??",
    }


def exact_vstd_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_target: dict[str, dict[str, Any]] = {}
    for row in rows:
        target = row["target"]
        if target in row_by_target:
            raise InventoryError(f"duplicate inventory target before vstd matching: {target}")
        row_by_target[target] = row

    dirty = vstd_dirty_status()
    exact_records: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    exact_targets: set[str] = set()

    def add_exact(
        *,
        candidate_id: str,
        target: str,
        relative_path: str,
        needle: str,
        expected_shape: dict[str, Any],
        semantic_adequacy: str,
        declaration_fragments: Sequence[str] = (),
        context_fragments: Sequence[str] = (),
        declaration_span: tuple[int, int] | None = None,
        instantiation_needle: str | None = None,
        lifetime_evidence: dict[str, Any] | None = None,
        semantic_rejection_reason: str | None = None,
    ) -> None:
        row = row_by_target.get(target)
        if row is None:
            raise InventoryError(f"exact-vstd target is absent from inventory: {target}")
        snapshot = f"{VSTD_SNAPSHOT_PREFIX}{relative_path}"
        path = CAMPAIGN_ROOT / snapshot
        text = path.read_text(encoding="utf-8")
        if needle not in text:
            raise InventoryError(f"vstd target binding is absent: {needle!r} in {path}")
        if declaration_span is None:
            start = find_unique_line(path, needle)
            span = assume_declaration_span(path, start)
        else:
            span = declaration_span
            require_source_line(path, span[0], needle)
        lines = text.splitlines()
        declaration_text = " ".join(lines[span[0] - 1 : span[1]])
        normalized_declaration = re.sub(r"\s+", " ", declaration_text)
        missing_declaration = [
            fragment
            for fragment in declaration_fragments
            if re.sub(r"\s+", " ", fragment) not in normalized_declaration
        ]
        missing_context = [
            fragment
            for fragment in context_fragments
            if re.sub(r"\s+", " ", fragment)
            not in re.sub(r"\s+", " ", text)
        ]
        if missing_declaration or missing_context:
            raise InventoryError(
                f"vstd signature evidence is absent for {target}: "
                f"declaration={missing_declaration}, context={missing_context}"
            )
        instantiation_line = (
            find_unique_line(path, instantiation_needle)
            if instantiation_needle is not None
            else None
        )
        actual_shape = row["matching_shape"]
        comparisons = {
            key: {
                "inventory": actual_shape[key],
                "vstd": expected_shape[key],
                "matches": actual_shape[key] == expected_shape[key],
            }
            for key in expected_shape
        }
        mismatches = {
            key: value for key, value in comparisons.items() if not value["matches"]
        }
        if mismatches:
            raise InventoryError(
                f"exact-vstd signature mismatch for {target}: {compact_json(mismatches)}"
            )
        file_record = vstd_file_record(relative_path, dirty)
        canonical = file_record["candidate_source_tracked_clean_at_head"]
        provenance_class = (
            "tracked_clean_vstd"
            if canonical
            else "frozen_dirty_or_untracked_current_vstd"
        )
        lifetime_record = lifetime_evidence or {
            "status": "not_applicable_or_elided_equivalent",
            "alpha_equivalent": True,
        }
        full_shape_matches = all(
            comparison["matches"] for comparison in comparisons.values()
        ) and bool(lifetime_record["alpha_equivalent"])
        record = {
            "candidate_id": candidate_id,
            "row_id": row["row_id"],
            "target": target,
            "status": (
                "rejected_semantically_incomplete"
                if semantic_rejection_reason
                else "exact_match"
            ),
            "signature_comparison": comparisons,
            "full_signature_shape_matches": full_shape_matches,
            "implementation_identity_matches": comparisons[
                "implementation_identity"
            ]["matches"],
            "lifetime_comparison": lifetime_record,
            "evidence": {
                **file_record,
                "declaration_begin_line": span[0],
                "declaration_end_line": span[1],
                "declaration_sha256": line_hash(path, span[0], span[1]),
                "macro_instantiation_line": instantiation_line,
                "required_declaration_fragments": list(declaration_fragments),
                "required_context_fragments": list(context_fragments),
            },
            "semantic_adequacy": semantic_adequacy,
            "vstd_provenance_class": provenance_class,
            "canonical_upstream_binding": canonical,
            "current_snapshot_loaded": True,
            "independent_review_status": "pending",
        }
        candidate_records.append(record)
        if semantic_rejection_reason:
            record.update(
                {
                    "semantic_complete": False,
                    "rejection_reason": semantic_rejection_reason,
                    "mismatch_dimensions": [
                        "observable_result_semantics",
                        "nan_behavior",
                        "result_functionality",
                    ],
                }
            )
            rejected_records.append(record)
            row["specification_blocker"] = {
                "kind": "loaded_vstd_float_model_boundary",
                "evidence_path": (
                    "specification/float_model_boundary_audit.json"
                ),
                "candidate_id": candidate_id,
                "reason": semantic_rejection_reason,
                "review_status": "pending_independent_row_review",
            }
            return
        record["semantic_complete"] = True
        exact_records.append(record)
        if target in exact_targets:
            raise InventoryError(f"multiple exact-vstd candidates match {target}")
        exact_targets.add(target)
        row["disposition"] = "exact_vstd"
        row["vstd_binding_ids"].append(candidate_id)
        row["vstd_provenance_class"] = provenance_class

    default_configs = {
        "PartialEq::ne": (
            23,
            27,
            candidate_shape(
                "PartialEq::ne",
                ("&Self", "&Rhs"),
                "bool",
                "trait_default",
                type_parameters=("Rhs",),
                runtime_bounds=("Rhs:PointeeSized", "Self:PointeeSized"),
            ),
        ),
        "PartialOrd::lt": (
            53,
            63,
            candidate_shape(
                "PartialOrd::lt",
                ("&Self", "&Rhs"),
                "bool",
                "trait_default",
                type_parameters=("Rhs",),
                runtime_bounds=(
                    "Rhs:PointeeSized",
                    "Self:PartialEq<Rhs>",
                    "Self:PointeeSized",
                ),
            ),
        ),
        "PartialOrd::le": (
            65,
            81,
            candidate_shape(
                "PartialOrd::le",
                ("&Self", "&Rhs"),
                "bool",
                "trait_default",
                type_parameters=("Rhs",),
                runtime_bounds=(
                    "Rhs:PointeeSized",
                    "Self:PartialEq<Rhs>",
                    "Self:PointeeSized",
                ),
            ),
        ),
        "PartialOrd::gt": (
            83,
            93,
            candidate_shape(
                "PartialOrd::gt",
                ("&Self", "&Rhs"),
                "bool",
                "trait_default",
                type_parameters=("Rhs",),
                runtime_bounds=(
                    "Rhs:PointeeSized",
                    "Self:PartialEq<Rhs>",
                    "Self:PointeeSized",
                ),
            ),
        ),
        "PartialOrd::ge": (
            95,
            111,
            candidate_shape(
                "PartialOrd::ge",
                ("&Self", "&Rhs"),
                "bool",
                "trait_default",
                type_parameters=("Rhs",),
                runtime_bounds=(
                    "Rhs:PointeeSized",
                    "Self:PartialEq<Rhs>",
                    "Self:PointeeSized",
                ),
            ),
        ),
        "Ord::max": (
            127,
            141,
            candidate_shape(
                "Ord::max",
                ("Self", "Self"),
                "Self",
                "trait_default",
                runtime_bounds=(
                    "Self:Eq",
                    "Self:PartialOrd<Self>",
                    "Self:PointeeSized",
                    "Self:Sized",
                ),
            ),
        ),
        "Ord::min": (
            143,
            157,
            candidate_shape(
                "Ord::min",
                ("Self", "Self"),
                "Self",
                "trait_default",
                runtime_bounds=(
                    "Self:Eq",
                    "Self:PartialOrd<Self>",
                    "Self:PointeeSized",
                    "Self:Sized",
                ),
            ),
        ),
        "Ord::clamp": (
            159,
            185,
            candidate_shape(
                "Ord::clamp",
                ("Self", "Self", "Self"),
                "Self",
                "trait_default",
                runtime_bounds=(
                    "Self:Eq",
                    "Self:PartialOrd<Self>",
                    "Self:PointeeSized",
                    "Self:Sized",
                ),
            ),
        ),
    }
    default_context = {
        "PartialEq::ne": (
            "pub trait ExPartialEq<Rhs: PointeeSized = Self>: PointeeSized",
            "type ExternalTraitSpecificationFor: PartialEq<Rhs>",
        ),
        "PartialOrd::lt": (
            "pub trait ExPartialOrd<Rhs: PointeeSized = Self>: PartialEq<Rhs> + PointeeSized",
            "type ExternalTraitSpecificationFor: PartialOrd<Rhs>",
        ),
        "PartialOrd::le": (
            "pub trait ExPartialOrd<Rhs: PointeeSized = Self>: PartialEq<Rhs> + PointeeSized",
            "type ExternalTraitSpecificationFor: PartialOrd<Rhs>",
        ),
        "PartialOrd::gt": (
            "pub trait ExPartialOrd<Rhs: PointeeSized = Self>: PartialEq<Rhs> + PointeeSized",
            "type ExternalTraitSpecificationFor: PartialOrd<Rhs>",
        ),
        "PartialOrd::ge": (
            "pub trait ExPartialOrd<Rhs: PointeeSized = Self>: PartialEq<Rhs> + PointeeSized",
            "type ExternalTraitSpecificationFor: PartialOrd<Rhs>",
        ),
        "Ord::max": (
            "pub trait ExOrd: Eq + PartialOrd + PointeeSized",
            "type ExternalTraitSpecificationFor: Ord",
        ),
        "Ord::min": (
            "pub trait ExOrd: Eq + PartialOrd + PointeeSized",
            "type ExternalTraitSpecificationFor: Ord",
        ),
        "Ord::clamp": (
            "pub trait ExOrd: Eq + PartialOrd + PointeeSized",
            "type ExternalTraitSpecificationFor: Ord",
        ),
    }
    for target, (begin, end, shape) in default_configs.items():
        if target == "Ord::clamp":
            # The loaded vstd declaration requires min <= max and therefore
            # specifies only normal returns. Rust's default body also has the
            # observable min > max panic outcome, so this candidate is not an
            # exact semantic match and must receive a generated contract.
            continue
        method_name = target.split("::")[-1]
        if target.startswith("PartialEq"):
            method_signature_fragment = (
                f"fn {method_name}(&self, other: &Rhs) -> (r: bool)"
            )
        elif target.startswith("PartialOrd"):
            method_signature_fragment = (
                f"fn {method_name}(&self, other: &Rhs) -> (r: bool)"
            )
        elif method_name in ("max", "min"):
            method_signature_fragment = (
                f"fn {method_name}(self, other: Self) -> (r: Self)"
            )
        else:
            method_signature_fragment = (
                "fn clamp(self, min: Self, max: Self) -> (r: Self)"
            )
        add_exact(
            candidate_id=f"vstd-trait-default-{target.replace('::', '-').lower()}",
            target=target,
            relative_path="std_specs/cmp.rs",
            needle=f"fn {method_name}(",
            expected_shape=shape,
            semantic_adequacy="external_trait_default_ensures_matches_source_body",
            declaration_fragments=(
                method_signature_fragment,
                "default_ensures",
            ),
            context_fragments=default_context[target],
            declaration_span=(begin, end),
        )

    ordering_shapes = {
        "is_eq": (("Ordering",), "bool"),
        "is_ne": (("Ordering",), "bool"),
        "is_lt": (("Ordering",), "bool"),
        "is_gt": (("Ordering",), "bool"),
        "is_le": (("Ordering",), "bool"),
        "is_ge": (("Ordering",), "bool"),
        "reverse": (("Ordering",), "Ordering"),
        "then": (("Ordering", "Ordering"), "Ordering"),
    }
    for method_name, (inputs, output) in ordering_shapes.items():
        target = f"Ordering::{method_name}"
        add_exact(
            candidate_id=f"vstd-ordering-{method_name}",
            target=target,
            relative_path="std_specs/ordering.rs",
            needle=f"assume_specification[ Ordering::{method_name} ]",
            expected_shape=candidate_shape(
                target,
                inputs,
                output,
                "inherent_concrete",
            ),
            semantic_adequacy="direct_ordering_branch_contract",
            declaration_fragments=(
                (
                    "(ordering: Ordering, other: Ordering)"
                    if method_name == "then"
                    else "(ordering: Ordering)"
                ),
                f"-> (result: {output})",
                "ensures",
            ),
        )

    primitive_methods = {
        "eq": ("PartialEq", "bool"),
        "ne": ("PartialEq", "bool"),
        "cmp": ("Ord", "Ordering"),
        "partial_cmp": ("PartialOrd", "Option<Ordering>"),
        "lt": ("PartialOrd", "bool"),
        "le": ("PartialOrd", "bool"),
        "gt": ("PartialOrd", "bool"),
        "ge": ("PartialOrd", "bool"),
    }

    for method_name in ("eq", "ne"):
        trait_name, output = primitive_methods[method_name]
        target = f"<bool as {trait_name}<bool>>::{method_name}"
        add_exact(
            candidate_id=f"vstd-bool-{method_name}",
            target=target,
            relative_path="std_specs/cmp.rs",
            needle=f"<bool as PartialEq<bool>>::{method_name}",
            expected_shape=candidate_shape(
                target,
                ("&bool", "&bool"),
                output,
                "source_macro_expanded_concrete",
            ),
            semantic_adequacy="binding_plus_partial_eq_spec_impl_dependency",
            declaration_fragments=("(x: &bool, y: &bool) -> bool",),
            context_fragments=(
                "impl PartialEqSpecImpl for bool",
                "open spec fn obeys_eq_spec() -> bool",
                "open spec fn eq_spec(&self, other: &bool) -> bool",
            ),
        )

    for type_name in FLOAT_TYPES:
        for method_name in ("eq", "ne", "partial_cmp", "lt", "le", "gt", "ge"):
            trait_name, output = primitive_methods[method_name]
            target = f"<{type_name} as {trait_name}<{type_name}>>::{method_name}"
            add_exact(
                candidate_id=f"vstd-{type_name}-{method_name}",
                target=target,
                relative_path="std_specs/cmp.rs",
                needle=f"<{type_name} as {trait_name}<{type_name}>>::{method_name}",
                expected_shape=candidate_shape(
                    target,
                    (f"&{type_name}", f"&{type_name}"),
                    output,
                    "source_macro_expanded_concrete",
                ),
                semantic_adequacy=(
                    "signature_exact_but_result_semantics_uninterpreted"
                ),
                declaration_fragments=(
                    f"(x: &{type_name}, y: &{type_name})",
                    f"-> (o: {output})",
                    f"{method_name}_ensures::<{type_name}>"
                    if method_name not in ("partial_cmp",)
                    else f"partial_cmp_ensures::<{type_name}>",
                ),
                semantic_rejection_reason=(
                    "The loaded vstd declaration delegates the complete "
                    "observable result to an unconstrained predicate. It "
                    "does not expose Rust 1.96 ordering branches, None, or "
                    "NaN behavior and therefore is not exact semantic "
                    "coverage."
                ),
            )

    invocation_needles = {
        "u8": "num_specs!(u8, i8,",
        "i8": "num_specs!(u8, i8,",
        "u16": "num_specs!(u16, i16,",
        "i16": "num_specs!(u16, i16,",
        "u32": "num_specs!(u32, i32,",
        "i32": "num_specs!(u32, i32,",
        "u64": "num_specs!(u64, i64,",
        "i64": "num_specs!(u64, i64,",
        "u128": "u128_specs_tmp,",
        "i128": "i128_specs_tmp,",
        "usize": "usize_specs_tmp,",
        "isize": "isize_specs_tmp,",
    }
    for type_name in INTEGER_TYPES:
        template = "$uN" if type_name.startswith("u") else "$iN"
        if type_name == "usize":
            template = "$uN"
        if type_name == "isize":
            template = "$iN"
        for method_name, (trait_name, output) in primitive_methods.items():
            target = (
                f"<{type_name} as {trait_name}<{type_name}>>::{method_name}"
                if trait_name in ("PartialEq", "PartialOrd")
                else f"<{type_name} as {trait_name}>::{method_name}"
            )
            template_target = (
                f"<{template} as {trait_name}<{template}>>::{method_name}"
                if trait_name in ("PartialEq", "PartialOrd")
                else f"<{template} as {trait_name}>::{method_name}"
            )
            add_exact(
                candidate_id=f"vstd-{type_name}-{method_name}",
                target=target,
                relative_path="std_specs/num.rs",
                needle=f"assume_specification[{template_target}]",
                expected_shape=candidate_shape(
                    target,
                    (f"&{type_name}", f"&{type_name}"),
                    output,
                    "source_macro_expanded_concrete",
                ),
                semantic_adequacy="binding_plus_integer_spec_impl_dependency",
                declaration_fragments=(
                    f"(x: &{template}, y: &{template}) -> {output}",
                ),
                context_fragments=(
                    (
                        f"impl super::super::cmp::PartialEqSpecImpl for {template}"
                        if trait_name == "PartialEq"
                        else f"impl super::super::cmp::PartialOrdSpecImpl for {template}"
                        if trait_name == "PartialOrd"
                        else f"impl super::super::cmp::OrdSpecImpl for {template}"
                    ),
                    (
                        "open spec fn obeys_eq_spec() -> bool"
                        if trait_name == "PartialEq"
                        else "open spec fn obeys_partial_cmp_spec() -> bool"
                        if trait_name == "PartialOrd"
                        else "open spec fn obeys_cmp_spec() -> bool"
                    ),
                ),
                instantiation_needle=invocation_needles[type_name],
            )

    reference_methods = {
        "eq": ("PartialEq<&B>", "bool"),
        "ne": ("PartialEq<&B>", "bool"),
        "partial_cmp": ("PartialOrd<&B>", "Option<Ordering>"),
        "lt": ("PartialOrd<&B>", "bool"),
        "le": ("PartialOrd<&B>", "bool"),
        "gt": ("PartialOrd<&B>", "bool"),
        "ge": ("PartialOrd<&B>", "bool"),
    }
    for method_name, (trait_target, output) in reference_methods.items():
        target = f"<&A as {trait_target}>::{method_name}"
        bound_trait = "PartialEq<B>" if trait_target.startswith("PartialEq") else "PartialOrd<B>"
        vstd_output = (
            "Option<core::cmp::Ordering>"
            if output == "Option<Ordering>"
            else output
        )
        add_exact(
            candidate_id=f"vstd-shared-reference-{method_name}",
            target=target,
            relative_path="std_specs/cmp.rs",
            needle=f"as {trait_target.split('<')[0]}<&B>>::{method_name}",
            expected_shape=candidate_shape(
                target,
                ("&&A", "&&B"),
                output,
                "manual_concrete",
                type_parameters=("A", "B"),
                runtime_bounds=(
                    f"A:{bound_trait}",
                    "A:PointeeSized",
                    "B:PointeeSized",
                ),
            ),
            semantic_adequacy="exact_shared_reference_forwarding_contract",
            declaration_fragments=(
                "<'_0, 'a, A: PointeeSized, B: PointeeSized>",
                "a: &&'a A",
                "b: &&B",
                f"-> {vstd_output}",
                f"where A: {bound_trait}",
            ),
            context_fragments=(
                (
                    "PartialEqSpecImpl<&B> for &A"
                    if trait_target.startswith("PartialEq")
                    else "PartialOrdSpecImpl<&B> for &A"
                ),
                (
                    "open spec fn obeys_eq_spec() -> bool"
                    if trait_target.startswith("PartialEq")
                    else "open spec fn obeys_partial_cmp_spec() -> bool"
                ),
            ),
            lifetime_evidence={
                "inventory": "elided outer receiver and inner reference lifetimes",
                "vstd": "explicit '_0 and 'a binders",
                "alpha_equivalent": True,
                "mutability_matches": True,
            },
        )
    reference_ord_target = "<&A as Ord>::cmp"
    add_exact(
        candidate_id="vstd-shared-reference-cmp",
        target=reference_ord_target,
        relative_path="std_specs/cmp.rs",
        needle="as Ord>::cmp ]",
        expected_shape=candidate_shape(
            reference_ord_target,
            ("&&A", "&&A"),
            "Ordering",
            "manual_concrete",
            type_parameters=("A",),
            runtime_bounds=("A:Ord", "A:PointeeSized"),
        ),
        semantic_adequacy="exact_shared_reference_forwarding_contract",
        declaration_fragments=(
            "<'a, A: PointeeSized + Ord>",
            "a: &&'a A",
            "b: &&'a A",
            "-> core::cmp::Ordering",
        ),
        context_fragments=(
            "impl<A: PointeeSized + Ord> OrdSpecImpl for &A",
            "open spec fn obeys_cmp_spec() -> bool",
        ),
        lifetime_evidence={
            "inventory": "elided outer receiver and shared-reference lifetime",
            "vstd": "explicit 'a binder",
            "alpha_equivalent": True,
            "mutability_matches": True,
        },
    )

    option_methods = {
        "eq": ("PartialEq<Option<T>>", "bool", "PartialEq"),
        "partial_cmp": (
            "PartialOrd<Option<T>>",
            "Option<Ordering>",
            "PartialOrd",
        ),
        "cmp": ("Ord", "Ordering", "Ord"),
    }
    for method_name, (trait_target, output, bound_trait) in option_methods.items():
        target = f"<Option<T> as {trait_target}>::{method_name}"
        source_trait = trait_target.split("<")[0]
        add_exact(
            candidate_id=f"vstd-option-{method_name}",
            target=target,
            relative_path="std_specs/option.rs",
            needle=f"<Option<T> as {source_trait}>::{method_name}",
            expected_shape=candidate_shape(
                target,
                ("&Option<T>", "&Option<T>"),
                output,
                "manual_concrete",
                type_parameters=("T",),
                runtime_bounds=(f"T:{bound_trait}",),
            ),
            semantic_adequacy="exact_option_branch_contract",
            declaration_fragments=(
                f"<T: {bound_trait}>",
                "x: &Option<T>",
                "y: &Option<T>",
                (
                    "-> Option<core::cmp::Ordering>"
                    if output == "Option<Ordering>"
                    else f"-> core::cmp::Ordering"
                    if output == "Ordering"
                    else f"-> {output}"
                ),
            ),
            context_fragments=(
                (
                    "PartialEqSpecImpl for Option<T>"
                    if source_trait == "PartialEq"
                    else "PartialOrdSpecImpl for Option<T>"
                    if source_trait == "PartialOrd"
                    else "OrdSpecImpl for Option<T>"
                ),
                (
                    "open spec fn obeys_eq_spec() -> bool"
                    if source_trait == "PartialEq"
                    else "open spec fn obeys_partial_cmp_spec() -> bool"
                    if source_trait == "PartialOrd"
                    else "open spec fn obeys_cmp_spec() -> bool"
                ),
            ),
        )

    rejected_candidates = (
        {
            "candidate_id": "vstd-trait-default-ord-clamp",
            "target": "Ord::clamp",
            "path": "std_specs/cmp.rs",
            "line": 159,
            "status": "rejected_as_semantically_incomplete",
            "mismatch_dimensions": ["observable_outcome", "panic_domain"],
            "reason": (
                "the vstd declaration requires min <= max and models only a "
                "normal Self return, while the Rust default has an observable "
                "min > max panic/no-normal-return outcome"
            ),
        },
        {
            "candidate_id": "vstd-trait-required-partialeq-eq",
            "target": "PartialEq::eq",
            "path": "std_specs/cmp.rs",
            "line": 19,
            "reason": (
                "abstract required trait declaration has no executable body identity; "
                "the trait-level extension cannot be assigned to concrete overrides"
            ),
        },
        {
            "candidate_id": "vstd-trait-required-partialord-partial_cmp",
            "target": "PartialOrd::partial_cmp",
            "path": "std_specs/cmp.rs",
            "line": 49,
            "reason": (
                "abstract required trait declaration has no executable body identity; "
                "the trait-level extension cannot be assigned to concrete overrides"
            ),
        },
        {
            "candidate_id": "vstd-trait-required-ord-cmp",
            "target": "Ord::cmp",
            "path": "std_specs/cmp.rs",
            "line": 123,
            "reason": (
                "abstract required trait declaration has no executable body identity; "
                "the trait-level extension cannot be assigned to concrete overrides"
            ),
        },
        {
            "candidate_id": "vstd-vec-partialeq-eq",
            "target": "<Vec<T, A1> as PartialEq<Vec<U, A2>>>::eq",
            "path": "std_specs/vec.rs",
            "line": 343,
            "reason": "target implementation source is outside the captured core::cmp ownership scope",
        },
        {
            "candidate_id": "vstd-mut-pointer-partialeq-eq",
            "target": "<*mut T as PartialEq<*mut T>>::eq",
            "path": "raw_ptr.rs",
            "line": 198,
            "reason": "target implementation source is outside the captured core::cmp ownership scope",
        },
        {
            "candidate_id": "vstd-const-pointer-partialeq-eq",
            "target": "<*const T as PartialEq<*const T>>::eq",
            "path": "raw_ptr.rs",
            "line": 221,
            "reason": "target implementation source is outside the captured core::cmp ownership scope",
        },
        {
            "candidate_id": "vstd-string-partialeq-eq",
            "target": "<String as PartialEq<String>>::eq",
            "path": "string.rs",
            "line": 351,
            "reason": "alloc::string implementation source is outside the captured core::cmp ownership scope",
        },
    )
    for candidate in rejected_candidates:
        file_record = vstd_file_record(candidate["path"], dirty)
        path = CAMPAIGN_ROOT / file_record["snapshot_path"]
        if "fn " not in source_line(path, candidate["line"]) and "assume_specification" not in source_line(
            path, candidate["line"]
        ):
            raise InventoryError(
                f"rejected vstd candidate anchor is absent: {path}:{candidate['line']}"
            )
        record = {
            **candidate,
            "status": candidate.get(
                "status", "rejected_as_exact_implementation_match"
            ),
            "inventory_target_present": candidate["target"] in row_by_target,
            "mismatch_dimensions": candidate.get(
                "mismatch_dimensions",
                ["implementation_identity", "target_ownership"],
            ),
            "evidence": file_record,
        }
        rejected_records.append(record)
        candidate_records.append(record)

    exact_by_provenance = Counter(
        record["vstd_provenance_class"] for record in exact_records
    )
    dirty_loader_paths = {
        path: code
        for path, code in dirty.items()
        if path in {
            "source/vstd/std_specs/mod.rs",
            "source/vstd/std_specs/ordering.rs",
            "source/vstd/vstd.rs",
        }
    }
    std_specs_module = (
        CAMPAIGN_ROOT / f"{VSTD_SNAPSHOT_PREFIX}std_specs/mod.rs"
    ).read_text(encoding="utf-8")
    vstd_root = (
        CAMPAIGN_ROOT / f"{VSTD_SNAPSHOT_PREFIX}vstd.rs"
    ).read_text(encoding="utf-8")
    ordering_module_declared = "pub mod ordering;" in std_specs_module
    std_specs_loaded = (
        "#[cfg(verus_keep_ghost)]\npub mod std_specs;" in vstd_root
    )
    if not ordering_module_declared or not std_specs_loaded:
        raise InventoryError("captured current-vstd comparison modules are not loaded")
    unmatched_rows = [
        {
            "row_id": row["row_id"],
            "target": row["target"],
            "implementation_kind": row["implementation_kind"],
        }
        for row in rows
        if row["disposition"] == "pending"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "matching_rule": (
            "exact target, executable implementation identity, receiver/reference "
            "shape, parameter and return shape, lifetime alpha-equivalence, type and "
            "const generics, bounds, mutability, and every observable returned or "
            "panicked outcome must all match; trait-level extensions do not cover "
            "concrete overrides"
        ),
        "semantic_scope": (
            "exact_match certifies executable target/identity, full signature, and "
            "complete observable-outcome coverage; a declaration that excludes a "
            "source panic domain is rejected even when its normal-return signature "
            "matches"
        ),
        "candidate_count": len(candidate_records),
        "exact_match_count": len(exact_records),
        "exact_match_counts_by_provenance": dict(sorted(exact_by_provenance.items())),
        "canonical_upstream_exact_match_count": sum(
            record["canonical_upstream_binding"] for record in exact_records
        ),
        "frozen_dirty_or_untracked_exact_match_count": sum(
            not record["canonical_upstream_binding"] for record in exact_records
        ),
        "rejected_candidate_count": len(rejected_records),
        "unmatched_inventory_count": len(unmatched_rows),
        "candidate_sources": {
            relative: vstd_file_record(relative, dirty)
            for relative in (
                "std_specs/cmp.rs",
                "std_specs/ordering.rs",
                "std_specs/num.rs",
                "std_specs/option.rs",
                "std_specs/vec.rs",
                "raw_ptr.rs",
                "string.rs",
                "laws_cmp.rs",
                "laws_eq.rs",
                "std_specs/mod.rs",
                "vstd.rs",
            )
        },
        "loading_audit": {
            "std_specs_root_guard": "cfg(verus_keep_ghost)",
            "std_specs_loaded": std_specs_loaded,
            "ordering_module_declared": ordering_module_declared,
            "dirty_loading_paths": dirty_loader_paths,
            "ordering_coverage_is_canonical_upstream": False,
            "ordering_coverage_authority": "frozen current dirty checkout only",
            "loading_snapshot_authority": "frozen current checkout, not HEAD reconstruction",
        },
        "contract_dependencies": [
            {
                "path": "std_specs/cmp.rs",
                "construct": "ExPartialEq::{eq,ne} and PartialEqSpecImpl",
                "role": "postconditions for bare concrete PartialEq bindings",
                "identity_accounting": "dependency only; not a concrete implementation match",
            },
            {
                "path": "std_specs/cmp.rs",
                "construct": "ExPartialOrd methods and PartialOrdSpecImpl",
                "role": "postconditions for bare concrete PartialOrd bindings",
                "identity_accounting": "dependency only; required abstract declarations are not body rows",
            },
            {
                "path": "std_specs/cmp.rs",
                "construct": "ExOrd methods and OrdSpecImpl",
                "role": "postconditions for bare concrete Ord bindings",
                "identity_accounting": "dependency only; required abstract declarations are not body rows",
            },
        ],
        "non_binding_sources": [
            {
                "path": "std_specs/cmp.rs",
                "construct": "tuple_cmp_impl for arities 1 through 12",
                "classification": "spec-model implementations without executable assume_specification targets",
            },
            {
                "path": "std_specs/cmp.rs",
                "construct": "PartialEqIs and PartialOrdIs",
                "classification": "ghost helper traits, not executable target bindings",
            },
            {
                "path": "laws_cmp.rs",
                "construct": "comparison laws and broadcast lemmas",
                "classification": "proof/spec dependencies, not executable target bindings",
            },
            {
                "path": "laws_eq.rs",
                "construct": "equality laws and broadcast lemmas",
                "classification": "proof/spec dependencies, not executable target bindings",
            },
        ],
        "records": sorted(exact_records, key=lambda record: record["row_id"]),
        "rejected_candidates": rejected_records,
        "unmatched_inventory": sorted(unmatched_rows, key=lambda record: record["row_id"]),
    }


def build_ambiguity_audit(
    rows: list[dict[str, Any]],
    ownership: dict[str, Any],
    default_audit: dict[str, Any],
    specialization: dict[str, Any],
    exact_vstd: dict[str, Any],
) -> dict[str, Any]:
    row_id_counts = Counter(row["row_id"] for row in rows)
    target_counts = Counter(row["target"] for row in rows)
    duplicate_row_ids = sorted(
        row_id for row_id, count in row_id_counts.items() if count != 1
    )
    duplicate_targets = sorted(
        target for target, count in target_counts.items() if count != 1
    )
    span_groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for row in rows:
        span_groups[(row["source_file"], row["source_begin_line"])].append(
            row["row_id"]
        )
    shared_spans = [
        {
            "source_file": key[0],
            "source_begin_line": key[1],
            "row_count": len(row_ids),
            "row_ids": sorted(row_ids),
            "resolution": (
                "macro/derive call-site spans are not identity keys; rustdoc item/impl "
                "ids, canonical targets, and source-derived tuple arity keys remain unique"
            ),
        }
        for key, row_ids in sorted(span_groups.items())
        if len(row_ids) > 1
    ]
    exact_row_counts = Counter(
        record["row_id"] for record in exact_vstd["records"]
    )
    multiply_matched_exact_rows = sorted(
        row_id for row_id, count in exact_row_counts.items() if count != 1
    )
    failures = (
        len(duplicate_row_ids)
        + len(duplicate_targets)
        + default_audit["unresolved_binding_count"]
        + default_audit["concrete_default_overlap_count"]
        + specialization["ambiguous_slot_count"]
        + len(multiply_matched_exact_rows)
    )
    alias_sources = (
        (
            "core/src/lib.rs",
            285,
            "pub mod cmp;",
            "core::cmp canonical module export",
        ),
        (
            "core/src/prelude/v1.rs",
            35,
            "pub use crate::cmp::{Eq, Ord, PartialEq, PartialOrd};",
            "prelude trait reexports",
        ),
        (
            "std/src/lib.rs",
            497,
            "pub use core::cmp;",
            "std::cmp module reexport",
        ),
    )
    alias_evidence: list[dict[str, Any]] = []
    for source_file, line_number, fragment, role in alias_sources:
        path = CAMPAIGN_ROOT / f"{RUST_SNAPSHOT_PREFIX}{source_file}"
        require_source_line(path, line_number, fragment)
        alias_evidence.append(
            {
                "source_file": source_file,
                "source_line": line_number,
                "source_line_sha256": line_hash(path, line_number, line_number),
                "role": role,
                "resolution": "identity-preserving export; no body identity added",
                "verified": True,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "status": "pass" if failures == 0 else "fail",
        "duplicate_row_id_count": len(duplicate_row_ids),
        "duplicate_target_label_count": len(duplicate_targets),
        "duplicate_row_ids": duplicate_row_ids,
        "duplicate_target_labels": duplicate_targets,
        "shared_source_span_group_count": len(shared_spans),
        "shared_source_span_groups": shared_spans,
        "concrete_default_overlap_count": default_audit[
            "concrete_default_overlap_count"
        ],
        "unresolved_default_binding_count": default_audit[
            "unresolved_binding_count"
        ],
        "specialization_ambiguous_slot_count": specialization[
            "ambiguous_slot_count"
        ],
        "multiply_matched_exact_vstd_row_count": len(multiply_matched_exact_rows),
        "multiply_matched_exact_vstd_rows": multiply_matched_exact_rows,
        "source_hidden_tuple_arity_overlap_count": 0,
        "alias_duplicate_count": 0,
        "alias_evidence": alias_evidence,
        "stable_cmp_trait_impl_count": ownership["stable_cmp_trait_impl_count"],
    }


def derive_inventory(document: dict[str, Any]) -> dict[str, Any]:
    records = source_manifest_records()
    (
        path_rows,
        exclusions,
        trait_ids,
        default_rows,
        _trait_items,
    ) = derive_path_and_default_rows(document, records)
    (
        impl_rows,
        impl_exclusions,
        cmp_impl_seeds,
        public_type_impl_decisions,
        out_of_scope_cmp_impls,
    ) = derive_impl_rows(document, records, trait_ids)
    hidden_tuple_rows, hidden_tuple_impl_seeds = synthesize_hidden_tuple_rows(records)
    rows = [*path_rows, *impl_rows, *hidden_tuple_rows]
    exclusions.extend(impl_exclusions)
    ownership, default_audit = build_ownership(
        cmp_impl_seeds,
        hidden_tuple_impl_seeds,
        rows,
        default_rows,
        public_type_impl_decisions,
    )
    specialization = build_specialization_audit()
    exact_vstd = exact_vstd_audit(rows)
    ambiguity = build_ambiguity_audit(
        rows,
        ownership,
        default_audit,
        specialization,
        exact_vstd,
    )
    if ambiguity["status"] != "pass":
        raise InventoryError("identity ambiguity audit failed")

    rows.sort(key=lambda row: row["row_id"])
    exclusions.sort(key=lambda row: row["candidate_id"])
    disposition_counts = Counter(row["disposition"] for row in rows)
    api_kind_counts = Counter(row["api_kind"] for row in rows)
    implementation_kind_counts = Counter(row["implementation_kind"] for row in rows)
    source_counts = Counter(row["source_file"] for row in rows)
    stable_total = len(rows)
    reconciled_total = sum(disposition_counts.values())
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "rust_release": provenance.RUST_RELEASE,
        "rustdoc_format_version": document["format_version"],
        "rustdoc_sha256": provenance.sha256_file(RUSTDOC_JSON),
        "generator_sha256": provenance.sha256_file(Path(__file__)),
        "derivation_rule": (
            "stable executable free and inherent bodies owned by core::cmp; stable "
            "trait defaults owned once; stable explicit methods of core::cmp traits "
            "in the captured cmp, slice, array, tuple, and option implementation "
            "sources; stable explicit methods on Ordering and Reverse owned by "
            "core::cmp; source-hidden tuple arities expanded from the captured macro; "
            "abstract required declarations, inherited-default duplicates, unstable "
            "items, aliases, non-functions, and private specialization dependencies "
            "are not public inventory rows"
        ),
        "row_count": stable_total,
        "rows": rows,
    }
    exclusions_artifact = {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "record_count": len(exclusions),
        "records": exclusions,
    }
    reconciliation = {
        "schema_version": SCHEMA_VERSION,
        "module": "core::cmp",
        "stable_inventory_total": stable_total,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "api_kind_counts": dict(sorted(api_kind_counts.items())),
        "implementation_kind_counts": dict(sorted(implementation_kind_counts.items())),
        "source_file_counts": dict(sorted(source_counts.items())),
        "path_surface": {
            "rustdoc_visible_stable_path_rows_historical_cross_check": 26,
            "source_discovered_doc_hidden_stable_path_count": sum(
                row["source_visibility"] == "doc_hidden_but_public_and_stable"
                for row in rows
            ),
            "abstract_required_declaration_count": sum(
                record["reason"]
                == "required_trait_declaration_has_no_executable_body"
                for record in exclusions
            ),
            "historical_count_is_acceptance_input": False,
        },
        "ownership_boundary": out_of_scope_cmp_impls,
        "ownership": {
            "stable_cmp_trait_impl_count": ownership[
                "stable_cmp_trait_impl_count"
            ],
            "default_body_identity_count": default_audit[
                "default_body_identity_count"
            ],
            "private_specialization_executable_identity_count": specialization[
                "specialization_executable_identity_count"
            ],
            "private_specialization_marker_impl_count": specialization[
                "marker_impl_count"
            ],
        },
        "exact_vstd": {
            "exact_match_count": exact_vstd["exact_match_count"],
            "canonical_upstream_exact_match_count": exact_vstd[
                "canonical_upstream_exact_match_count"
            ],
            "frozen_dirty_or_untracked_exact_match_count": exact_vstd[
                "frozen_dirty_or_untracked_exact_match_count"
            ],
        },
        "excluded_candidate_count": len(exclusions),
        "equation": {
            "left": stable_total,
            "right": reconciled_total,
            "holds": stable_total == reconciled_total,
        },
        "hard_coded_acceptance_total": False,
        "all_audits_pass": (
            default_audit["status"] == "pass"
            and specialization["status"] == "pass"
            and ambiguity["status"] == "pass"
        ),
    }
    if not reconciliation["equation"]["holds"]:
        raise InventoryError("inventory disposition equation does not reconcile")
    return {
        "inventory": inventory,
        "exclusions": exclusions_artifact,
        "ownership": ownership,
        "exact_vstd": exact_vstd,
        "reconciliation": reconciliation,
        "default_audit": default_audit,
        "specialization_audit": specialization,
        "ambiguity_audit": ambiguity,
    }


def csv_bytes(records: Sequence[dict[str, Any]], fields: Sequence[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


def readme_bytes(derived: dict[str, Any]) -> bytes:
    reconciliation = derived["reconciliation"]
    dispositions = reconciliation["disposition_counts"]
    ownership = reconciliation["ownership"]
    exact = reconciliation["exact_vstd"]
    text = f"""# Rust 1.96 `core::cmp` identity inventory

This inventory is regenerated by `python3 tools/build_inventory.py generate`
from the frozen rustdoc JSON and captured Rust/vstd source snapshots. It uses
executable body identity rather than historical path labels.

| Measure | Derived count |
| --- | ---: |
| Stable public executable identities | {reconciliation["stable_inventory_total"]} |
| Exact current-vstd matches | {exact["exact_match_count"]} |
| Canonical tracked exact-vstd matches | {exact["canonical_upstream_exact_match_count"]} |
| Frozen dirty/untracked exact-vstd matches | {exact["frozen_dirty_or_untracked_exact_match_count"]} |
| Pending identities | {dispositions.get("pending", 0)} |
| Stable cmp-trait impl identities | {ownership["stable_cmp_trait_impl_count"]} |
| Shared trait-default body identities | {ownership["default_body_identity_count"]} |
| Private specialization executable identities | {ownership["private_specialization_executable_identity_count"]} |
| Private specialization marker impls | {ownership["private_specialization_marker_impl_count"]} |
| Rustdoc cmp-trait impls outside the captured ownership sources | {reconciliation["ownership_boundary"]["impl_count"]} |

`Eq::assert_receiver_is_total_eq` is included because it remains stable,
publicly callable, and executable despite being doc-hidden and deprecated.
Required trait declarations without bodies are retained in the exclusions/path
audit and replaced by their effective concrete implementation identities.
Inherited defaults bind to one shared default body rather than creating a row
per implementing type.

The exact-vstd audit compares target and implementation identity, receiver and
argument reference/mutability shape, output, generics, lifetimes, bounds, and
complete observable-result semantics. The 14 `f32`/`f64` comparison bindings
are signature matches but not semantic matches: their unconstrained result
predicates omit Rust's ordering branches, `None`, and NaN behavior. They remain
non-exact rows with a target-specific verifier-model boundary.
Bare concrete declarations retain their checked `*SpecImpl` and external-trait
postcondition dependencies in `exact_vstd_audit.json`.
The eight `Ordering` convenience-method matches come from the frozen untracked
`std_specs/ordering.rs` plus dirty loader edits; they are explicitly not
reported as canonical upstream coverage.
"""
    return text.encode("utf-8")


def artifact_payloads(derived: dict[str, Any]) -> dict[Path, bytes]:
    return {
        INVENTORY_JSON: provenance.json_bytes(derived["inventory"]),
        INVENTORY_CSV: csv_bytes(
            derived["inventory"]["rows"],
            INVENTORY_CSV_FIELDS,
        ),
        EXCLUSIONS_JSON: provenance.json_bytes(derived["exclusions"]),
        EXCLUSIONS_CSV: csv_bytes(
            derived["exclusions"]["records"],
            EXCLUSION_CSV_FIELDS,
        ),
        OWNERSHIP_JSON: provenance.json_bytes(derived["ownership"]),
        EXACT_VSTD_JSON: provenance.json_bytes(derived["exact_vstd"]),
        RECONCILIATION_JSON: provenance.json_bytes(derived["reconciliation"]),
        DEFAULT_BINDING_AUDIT: provenance.json_bytes(derived["default_audit"]),
        SPECIALIZATION_AUDIT: provenance.json_bytes(
            derived["specialization_audit"]
        ),
        AMBIGUITY_AUDIT: provenance.json_bytes(derived["ambiguity_audit"]),
        INVENTORY_README: readme_bytes(derived),
    }


def generate() -> None:
    provenance.check_provenance()
    derived = derive_inventory(read_rustdoc())
    for path, payload in artifact_payloads(derived).items():
        provenance.atomic_write(path, payload)
    reconciliation = derived["reconciliation"]
    print(
        "core::cmp inventory generated: "
        f"{reconciliation['stable_inventory_total']} stable executable identities, "
        f"{reconciliation['exact_vstd']['exact_match_count']} exact-vstd matches, "
        f"{reconciliation['ownership']['stable_cmp_trait_impl_count']} stable cmp impls"
    )


def check() -> None:
    provenance.check_provenance()
    derived = derive_inventory(read_rustdoc())
    for path, expected in artifact_payloads(derived).items():
        if not path.is_file():
            raise InventoryError(f"inventory artifact is missing: {path}")
        if path.read_bytes() != expected:
            raise InventoryError(f"stale inventory artifact: {path}")
    reconciliation = derived["reconciliation"]
    if not reconciliation["all_audits_pass"]:
        raise InventoryError("one or more inventory audits failed")
    print(
        "core::cmp inventory check: PASS; "
        f"{reconciliation['stable_inventory_total']} rows reconcile, "
        f"{reconciliation['exact_vstd']['canonical_upstream_exact_match_count']} "
        "canonical exact-vstd plus "
        f"{reconciliation['exact_vstd']['frozen_dirty_or_untracked_exact_match_count']} "
        "frozen dirty exact-vstd"
    )


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        if options.command == "generate":
            generate()
        else:
            check()
    except (InventoryError, provenance.ProvenanceError, OSError) as error:
        print(f"core::cmp inventory error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
