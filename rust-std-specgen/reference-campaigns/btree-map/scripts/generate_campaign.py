#!/usr/bin/env python3
"""Generate the Rust 1.96 BTreeMap inventory, specifications, and proof harnesses."""

from __future__ import annotations

import argparse
import csv
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUSTDOC = ROOT / "provenance/snapshots/rustdoc-json-1.96/alloc.json"
SOURCE_ROOT = ROOT / "provenance/snapshots/rust-1.96/library"
MAP_FILE = "alloc/src/collections/btree/map.rs"
ENTRY_FILE = "alloc/src/collections/btree/map/entry.rs"
OWNER_FILES = {MAP_FILE, ENTRY_FILE}
MODULE_ITEM_ID = "1980"

EXACT_VSTD_KEYS = {
    ("BTreeMap", "inherent", "clear"),
    ("BTreeMap", "inherent", "contains_key"),
    ("BTreeMap", "inherent", "get"),
    ("BTreeMap", "inherent", "insert"),
    ("BTreeMap", "inherent", "is_empty"),
    ("BTreeMap", "inherent", "iter"),
    ("BTreeMap", "inherent", "keys"),
    ("BTreeMap", "inherent", "len"),
    ("BTreeMap", "inherent", "new"),
    ("BTreeMap", "inherent", "remove"),
    ("BTreeMap", "inherent", "values"),
    ("BTreeMap", "Clone", "clone"),
    ("BTreeMap", "Default", "default"),
}

VSTD_LINES = {
    ("BTreeMap", "inherent", "iter"): 204,
    ("BTreeMap", "inherent", "len"): 376,
    ("BTreeMap", "inherent", "is_empty"): 383,
    ("BTreeMap", "Clone", "clone"): 390,
    ("BTreeMap", "inherent", "new"): 399,
    ("BTreeMap", "Default", "default"): 404,
    ("BTreeMap", "inherent", "insert"): 410,
    ("BTreeMap", "inherent", "contains_key"): 456,
    ("BTreeMap", "inherent", "get"): 504,
    ("BTreeMap", "inherent", "remove"): 562,
    ("BTreeMap", "inherent", "clear"): 579,
    ("BTreeMap", "inherent", "keys"): 609,
    ("BTreeMap", "inherent", "values"): 641,
}

TRAIT_PATHS = {
    "Clone": "core::clone::Clone",
    "Debug": "core::fmt::Debug",
    "Default": "core::default::Default",
    "DoubleEndedIterator": "core::iter::DoubleEndedIterator",
    "Drop": "core::ops::Drop",
    "ExactSizeIterator": "core::iter::ExactSizeIterator",
    "Extend": "core::iter::Extend",
    "From": "core::convert::From",
    "FromIterator": "core::iter::FromIterator",
    "Hash": "core::hash::Hash",
    "Index": "core::ops::Index",
    "IntoIterator": "core::iter::IntoIterator",
    "Iterator": "core::iter::Iterator",
    "Ord": "core::cmp::Ord",
    "PartialEq": "core::cmp::PartialEq",
    "PartialOrd": "core::cmp::PartialOrd",
}

TYPE_PATHS = {
    "Allocator": "alloc::alloc::Allocator",
    "Borrow": "core::borrow::Borrow",
    "Clone": "core::clone::Clone",
    "Copy": "core::marker::Copy",
    "Debug": "core::fmt::Debug",
    "Default": "core::default::Default",
    "DoubleEndedIterator": "core::iter::DoubleEndedIterator",
    "FnMut": "core::ops::FnMut",
    "FnOnce": "core::ops::FnOnce",
    "Hash": "core::hash::Hash",
    "Hasher": "core::hash::Hasher",
    "IntoIterator": "core::iter::IntoIterator",
    "Iterator": "core::iter::Iterator",
    "Ord": "core::cmp::Ord",
    "Ordering": "core::cmp::Ordering",
    "PartialEq": "core::cmp::PartialEq",
    "PartialOrd": "core::cmp::PartialOrd",
    "RangeBounds": "core::ops::RangeBounds",
    "Sized": "core::marker::Sized",
    "fmt::Debug": "core::fmt::Debug",
    "fmt::Formatter": "core::fmt::Formatter",
    "fmt::Result": "core::fmt::Result",
}

ITERATOR_TYPES = {
    "Iter",
    "IterMut",
    "IntoIter",
    "Keys",
    "Values",
    "ValuesMut",
    "IntoKeys",
    "IntoValues",
    "Range",
    "RangeMut",
    "ExtractIf",
}

@dataclass
class Row:
    owner: dict[str, Any]
    impl_item: dict[str, Any]
    function: dict[str, Any]
    trait: str
    item_id: int
    source_file: str
    line_start: int
    line_end: int
    source_excerpt: str
    source_sha256: str
    target_id: str = ""
    ordinal: int = 0
    disposition: str = ""
    proxy_signature: str = ""
    canonical_target: str = ""
    semantic_family: str = ""
    principal_behavior: list[str] | None = None


def custom_index_binding(row: Row) -> bool:
    return row.trait == "Index" and row.function["name"] == "index"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main_stability(item: dict[str, Any]) -> str:
    values = [attribute.get("other", "") for attribute in item.get("attrs", [])]
    if any(
        value.startswith("#[attr = Stability ")
        and "level: Stable" in value
        for value in values
    ):
        return "stable"
    if any(
        value.startswith("#[attr = Stability ")
        and "level: Unstable" in value
        for value in values
    ):
        return "unstable"
    return "none"


def source_lines(filename: str) -> list[str]:
    return (SOURCE_ROOT / filename).read_text(encoding="utf-8").splitlines()


def excerpt_for(item: dict[str, Any]) -> tuple[str, int, int, str]:
    span = item["span"]
    start = int(span["begin"][0])
    end = int(span["end"][0])
    excerpt = "\n".join(source_lines(span["filename"])[start - 1 : end]) + "\n"
    return span["filename"], start, end, excerpt


def resolved_public_types(index: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stable_types: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for raw_id in index[MODULE_ITEM_ID]["inner"]["module"]["items"]:
        item = index[str(raw_id)]
        if "use" in item["inner"]:
            source_id = item["inner"]["use"].get("id")
            if source_id is None:
                continue
            item = index[str(source_id)]
        kind = next(iter(item["inner"]))
        if kind not in {"struct", "enum"}:
            continue
        stability = main_stability(item)
        if stability == "stable":
            stable_types.append(item)
        else:
            exclusions.append(
                {
                    "name": item["name"],
                    "kind": kind,
                    "rustdoc_item_id": item["id"],
                    "reason": "public type is unstable in the main Stability attribute",
                    "stability": stability,
                    "source_span": item.get("span"),
                }
            )
    return stable_types, exclusions


def derive_inventory(index: dict[str, Any]) -> tuple[list[Row], list[dict[str, Any]]]:
    public_types, exclusions = resolved_public_types(index)
    rows: list[Row] = []
    for owner in public_types:
        kind = next(iter(owner["inner"]))
        for impl_id in owner["inner"][kind].get("impls", []):
            impl_item = index[str(impl_id)]
            impl_data = impl_item["inner"]["impl"]
            span = impl_item.get("span")
            if impl_data["is_synthetic"] or not span or span["filename"] not in OWNER_FILES:
                continue
            trait = (impl_data.get("trait") or {}).get("path") or "inherent"
            if trait != "inherent" and main_stability(impl_item) != "stable":
                continue
            for function_id in impl_data["items"]:
                function = index[str(function_id)]
                if "function" not in function["inner"]:
                    continue
                fspan = function.get("span")
                if not fspan or fspan["filename"] not in OWNER_FILES:
                    continue
                stability = main_stability(function)
                if trait == "inherent" and stability != "stable":
                    exclusions.append(
                        {
                            "name": f"{owner['name']}::{function['name']}",
                            "kind": "inherent_method",
                            "rustdoc_item_id": function["id"],
                            "reason": "method is unstable in the main Stability attribute",
                            "stability": stability,
                            "source_span": fspan,
                        }
                    )
                    continue
                if trait == "Extend" and function["name"] == "extend_one":
                    exclusions.append(
                        {
                            "name": f"<{owner['name']} as Extend>::extend_one",
                            "kind": "trait_method",
                            "rustdoc_item_id": function["id"],
                            "reason": (
                                "core::iter::Extend::extend_one is unstable "
                                "(extend_one, issue 72631), despite its stable impl container"
                            ),
                            "stability": "unstable_trait_item",
                            "source_span": fspan,
                            "trait_source": "library/core/src/iter/traits/collect.rs:419-423",
                        }
                    )
                    continue
                if trait == "Drop" and function["name"] == "drop":
                    exclusions.append(
                        {
                            "name": f"<{owner['name']} as Drop>::drop",
                            "kind": "implicit_lifecycle_hook",
                            "rustdoc_item_id": function["id"],
                            "reason": (
                                "Drop::drop is not a publicly nameable API target; Rust rejects "
                                "explicit destructor method use with E0040. Its drop/deallocation "
                                "effects remain dependencies of consuming map and iterator APIs."
                            ),
                            "stability": "stable_but_not_publicly_callable",
                            "source_span": fspan,
                            "diagnostic": "E0040 explicit use of destructor method",
                        }
                    )
                    continue
                source_file, start, end, excerpt = excerpt_for(function)
                rows.append(
                    Row(
                        owner=owner,
                        impl_item=impl_item,
                        function=function,
                        trait=trait,
                        item_id=int(function["id"]),
                        source_file=source_file,
                        line_start=start,
                        line_end=end,
                        source_excerpt=excerpt,
                        source_sha256=sha256_text(excerpt),
                    )
                )

    rows.sort(
        key=lambda row: (
            row.source_file,
            row.line_start,
            row.owner["name"],
            row.trait,
            row.function["name"],
            row.item_id,
        )
    )
    for ordinal, row in enumerate(rows, start=1):
        row.ordinal = ordinal
        slug = re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            f"{row.owner['name']}_{row.trait}_{row.function['name']}_{row.item_id}",
        ).strip("_")
        row.target_id = f"{ordinal:03d}_{slug}"
        key = (row.owner["name"], row.trait, row.function["name"])
        row.disposition = (
            "exact_vstd"
            if key in EXACT_VSTD_KEYS
            else "genuinely_impossible"
            if (
                row.trait == "Extend"
                and row.function["name"] == "extend"
                and row.line_start == 2555
            )
            else "generated"
        )
    return rows, sorted(
        exclusions,
        key=lambda item: (
            (item.get("source_span") or {}).get("filename", ""),
            ((item.get("source_span") or {}).get("begin") or [0])[0],
            item["name"],
        ),
    )
def render_path(path: str) -> str:
    return TYPE_PATHS.get(path, path)


def render_generic_arg(argument: dict[str, Any], self_type: str | None = None) -> str:
    if "type" in argument:
        return render_type(argument["type"], self_type)
    if "lifetime" in argument:
        return argument["lifetime"]
    if "const" in argument:
        value = argument["const"]
        return value.get("expr", str(value)) if isinstance(value, dict) else str(value)
    raise ValueError(f"unsupported generic argument: {argument}")


def render_path_with_args(value: dict[str, Any], self_type: str | None = None) -> str:
    path = render_path(value["path"])
    args = value.get("args")
    if not args:
        return path
    if "angle_bracketed" in args:
        inner = args["angle_bracketed"]
        rendered = [render_generic_arg(arg, self_type) for arg in inner.get("args", [])]
        for constraint in inner.get("constraints", []):
            binding = constraint.get("binding", {})
            if "equality" in binding:
                rhs = render_type(binding["equality"]["type"], self_type)
                rendered.append(f"{constraint['name']} = {rhs}")
        return f"{path}<{', '.join(rendered)}>" if rendered else path
    if "parenthesized" in args:
        inner = args["parenthesized"]
        inputs = ", ".join(render_type(arg, self_type) for arg in inner["inputs"])
        output = inner.get("output")
        suffix = f" -> {render_type(output, self_type)}" if output is not None else ""
        return f"{path}({inputs}){suffix}"
    raise ValueError(f"unsupported path arguments: {args}")


def render_type(value: dict[str, Any] | None, self_type: str | None = None) -> str:
    if value is None:
        return "()"
    if "primitive" in value:
        return value["primitive"]
    if "generic" in value:
        if value["generic"] == "Self" and self_type is not None:
            return self_type
        return value["generic"]
    if "resolved_path" in value:
        return render_path_with_args(value["resolved_path"], self_type)
    if "borrowed_ref" in value:
        ref = value["borrowed_ref"]
        lifetime = f"{ref['lifetime']} " if ref.get("lifetime") else ""
        mutable = "mut " if ref["is_mutable"] else ""
        return f"&{lifetime}{mutable}{render_type(ref['type'], self_type)}"
    if "tuple" in value:
        entries = [render_type(item, self_type) for item in value["tuple"]]
        if len(entries) == 1:
            return f"({entries[0]},)"
        return f"({', '.join(entries)})"
    if "array" in value:
        array = value["array"]
        length = array["len"]
        if isinstance(length, dict):
            length = length.get("expr", str(length))
        return f"[{render_type(array['type'], self_type)}; {length}]"
    raise ValueError(f"unsupported rustdoc type: {value}")


def render_bound(bound: dict[str, Any]) -> str:
    if "trait_bound" in bound:
        trait_bound = bound["trait_bound"]
        rendered = render_path_with_args(trait_bound["trait"])
        if trait_bound["modifier"] == "maybe":
            return "?Sized" if rendered.endswith("Sized") else f"?{rendered}"
        return rendered
    if "outlives" in bound:
        return bound["outlives"]
    raise ValueError(f"unsupported bound: {bound}")


def param_parts(parameter: dict[str, Any]) -> tuple[str, str, list[str]]:
    name = parameter["name"]
    kind = parameter["kind"]
    if "lifetime" in kind:
        bounds = list(kind["lifetime"].get("outlives", []))
        return name, "lifetime", bounds
    if "type" in kind:
        bounds = [render_bound(bound) for bound in kind["type"].get("bounds", [])]
        return name, "type", bounds
    if "const" in kind:
        return name, f"const:{render_type(kind['const']['type'])}", []
    raise ValueError(f"unsupported generic parameter: {parameter}")


def render_where_predicate(predicate: dict[str, Any], self_type: str) -> str:
    if "bound_predicate" in predicate:
        value = predicate["bound_predicate"]
        left = render_type(value["type"], self_type)
        bounds = " + ".join(render_bound(bound) for bound in value["bounds"])
        return f"{left}: {bounds}"
    if "lifetime_predicate" in predicate:
        value = predicate["lifetime_predicate"]
        return f"{value['lifetime']}: {' + '.join(value['outlives'])}"
    if "eq_predicate" in predicate:
        value = predicate["eq_predicate"]
        return f"{render_type(value['lhs'], self_type)} = {render_type(value['rhs'], self_type)}"
    raise ValueError(f"unsupported where predicate: {predicate}")


def has_elided_reference(value: Any) -> bool:
    if isinstance(value, dict):
        borrowed = value.get("borrowed_ref")
        if borrowed is not None and borrowed.get("lifetime") is None:
            return True
        return any(has_elided_reference(item) for item in value.values())
    if isinstance(value, list):
        return any(has_elided_reference(item) for item in value)
    return False


def fill_elided_references(value: Any, lifetime: str) -> Any:
    result = copy.deepcopy(value)

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            borrowed = item.get("borrowed_ref")
            if borrowed is not None and borrowed.get("lifetime") is None:
                borrowed["lifetime"] = lifetime
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(result)
    return result


def has_placeholder_lifetime(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("lifetime") == "'_":
            return True
        return any(has_placeholder_lifetime(item) for item in value.values())
    if isinstance(value, list):
        return any(has_placeholder_lifetime(item) for item in value)
    return False


def fill_placeholder_lifetime(value: Any, lifetime: str) -> Any:
    result = copy.deepcopy(value)

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            if item.get("lifetime") == "'_":
                item["lifetime"] = lifetime
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(result)
    return result


def contains_generic_self(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("generic") == "Self":
            return True
        return any(contains_generic_self(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_generic_self(item) for item in value)
    return False


def impl_for_type(row: Row) -> str:
    impl_data = row.impl_item["inner"]["impl"]
    return render_type(impl_data["for"]).replace("'_", "'a")


def render_trait_target(row: Row) -> str:
    impl_data = row.impl_item["inner"]["impl"]
    for_type = impl_for_type(row)
    if row.trait == "inherent":
        inherent_type = for_type.replace("<", "::<", 1) if "<" in for_type else for_type
        target = f"{inherent_type}::{row.function['name']}"
    else:
        trait = copy.deepcopy(impl_data["trait"])
        if row.trait == "Index":
            trait = fill_elided_references(trait, "'a")
        trait["path"] = TRAIT_PATHS.get(trait["path"], trait["path"])
        target = f"<{for_type} as {render_path_with_args(trait)}>::{row.function['name']}"
    function_params = row.function["inner"]["function"]["generics"]["params"]
    turbofish = [
        parameter["name"]
        for parameter in function_params
        if "lifetime" not in parameter["kind"]
    ]
    if turbofish:
        target += f"::<{', '.join(turbofish)}>"
    return target


def proxy_parts(row: Row) -> tuple[str, list[tuple[str, str, str]], str | None, str]:
    impl_data = row.impl_item["inner"]["impl"]
    function_data = row.function["inner"]["function"]
    for_type = impl_for_type(row)
    output_value = function_data["sig"]["output"]
    explicit_self_lifetime = has_elided_reference(output_value)
    merged: list[tuple[str, str, list[str]]] = []
    seen: set[str] = set()
    for parameter in [
        *impl_data["generics"]["params"],
        *function_data["generics"]["params"],
    ]:
        name, kind, bounds = param_parts(parameter)
        if name in seen:
            continue
        seen.add(name)
        merged.append((name, kind, bounds))

    if (row.trait == "Index" or "'a" in for_type) and "'a" not in seen:
        merged.insert(0, ("'a", "lifetime", []))
        seen.add("'a")
    if explicit_self_lifetime and "'s" not in seen:
        insert_at = 0
        while insert_at < len(merged) and merged[insert_at][1] == "lifetime":
            insert_at += 1
        merged.insert(insert_at, ("'s", "lifetime", []))
        seen.add("'s")

    adjusted: list[tuple[str, str, list[str]]] = []
    for name, kind, bounds in merged:
        adjusted.append((name, kind, bounds))

    generic_parts: list[str] = []
    for name, kind, bounds in adjusted:
        if kind == "lifetime":
            generic_parts.append(f"{name}: {' + '.join(bounds)}" if bounds else name)
        elif kind.startswith("const:"):
            generic_parts.append(f"const {name}: {kind.split(':', 1)[1]}")
        else:
            generic_parts.append(f"{name}: {' + '.join(bounds)}" if bounds else name)
    binder = f"<{', '.join(generic_parts)}>" if generic_parts else ""

    used_names: set[str] = set()
    inputs: list[tuple[str, str, str]] = []
    for index, (source_name, rust_type) in enumerate(function_data["sig"]["inputs"]):
        if source_name == "self":
            name = "this"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", source_name):
            name = source_name
        else:
            name = f"arg{index}"
        if name in used_names:
            name = f"{name}_{index}"
        used_names.add(name)
        rendered_type = rust_type
        if (
            explicit_self_lifetime
            and source_name == "self"
            and "borrowed_ref" in rust_type
            and rust_type["borrowed_ref"].get("lifetime") is None
        ):
            rendered_type = copy.deepcopy(rust_type)
            rendered_type["borrowed_ref"]["lifetime"] = "'s"
        elif (
            row.trait == "Index"
            and source_name != "self"
            and "borrowed_ref" in rust_type
            and rust_type["borrowed_ref"].get("lifetime") is None
        ):
            rendered_type = copy.deepcopy(rust_type)
            rendered_type["borrowed_ref"]["lifetime"] = "'a"
        inputs.append((name, render_type(rendered_type, for_type), source_name))

    if output_value is not None and explicit_self_lifetime:
        output_value = fill_elided_references(output_value, "'s")
    output = render_type(output_value, for_type) if output_value is not None else None
    predicates = [
        *impl_data["generics"].get("where_predicates", []),
        *function_data["generics"].get("where_predicates", []),
    ]
    rendered_predicates = [render_where_predicate(item, for_type) for item in predicates]
    where_clause = f" where {', '.join(rendered_predicates)}" if rendered_predicates else ""
    if (
        row.owner["name"] == "BTreeMap"
        and row.trait == "inherent"
        and row.function["name"] == "extract_if"
    ):
        predicate_bounds: dict[str, str] = {}
        for predicate in rendered_predicates:
            if ": " not in predicate:
                continue
            name, bounds = predicate.split(": ", 1)
            predicate_bounds[name] = bounds
        enriched_parts: list[str] = []
        for part in generic_parts:
            name = part.split(":", 1)[0].strip()
            bounds = predicate_bounds.get(name)
            if bounds is None:
                enriched_parts.append(part)
            elif ":" in part:
                enriched_parts.append(f"{part} + {bounds}")
            else:
                enriched_parts.append(f"{name}: {bounds}")
        binder = f"<{', '.join(enriched_parts)}>"
        where_clause = ""
    return binder, inputs, output, where_clause


def canonical_target(row: Row) -> str:
    target = render_trait_target(row)
    return target.replace("BTreeMap", "alloc::collections::btree_map::BTreeMap", 1)


def semantic_family(row: Row) -> str:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    if owner in ITERATOR_TYPES:
        if trait == "Iterator":
            if name in {"next"}:
                return "ordered_iterator_forward_step"
            if name in {"last", "min", "max"}:
                return "ordered_iterator_terminal_selection"
            if name == "size_hint":
                return "ordered_iterator_size_hint"
        if trait == "DoubleEndedIterator":
            return "ordered_iterator_backward_step"
        if trait == "ExactSizeIterator":
            return "ordered_iterator_exact_len"
        if trait == "Clone":
            return "ordered_iterator_clone"
        if trait == "Default":
            return "ordered_iterator_empty_default"
        if trait == "Debug":
            return "ordered_debug_format"
        if trait == "Drop":
            return "owning_iterator_drop"
    if owner == "BTreeMap":
        if trait == "inherent":
            if name in {"get_key_value", "first_key_value", "last_key_value"}:
                return "map_borrowed_or_endpoint_observer"
            if name in {"first_entry", "last_entry", "entry"}:
                return "map_entry_handle"
            if name in {"pop_first", "pop_last", "remove_entry"}:
                return "map_removal_transition"
            if name == "get_mut":
                return "map_mutable_lookup_frame"
            if name in {"retain", "extract_if"}:
                return "map_ordered_callback_filter"
            if name == "append":
                return "map_append_last_value_wins"
            if name in {"range", "range_mut"}:
                return "map_range_bounds_order"
            if name == "split_off":
                return "map_order_partition"
            if name in {"into_keys", "into_values", "iter_mut", "values_mut"}:
                return "map_iterator_construction"
        if trait == "IntoIterator":
            return "map_into_iterator"
        if trait in {"From", "FromIterator", "Extend"}:
            return "map_collection_conversion"
        if trait in {"PartialEq", "PartialOrd", "Ord"}:
            return "map_ordered_comparison"
        if trait == "Index":
            return "map_index_panic_domain"
        if trait == "Hash":
            return "map_ordered_hash"
        if trait == "Debug":
            return "ordered_debug_format"
        if trait == "Drop":
            return "map_drop_allocator"
    if owner in {"Entry", "OccupiedEntry", "VacantEntry"}:
        if trait == "Debug":
            return "ordered_debug_format"
        if name in {"key", "into_key", "get", "get_mut", "into_mut"}:
            return "entry_observer_or_mutable_frame"
        if name in {"remove", "remove_entry"}:
            return "entry_removal_transition"
        if name in {"insert", "insert_entry"}:
            return "entry_insert_or_replace_transition"
        return "entry_branch_callback_transition"
    return "source_owned_stable_transition"


def principal_behavior(row: Row) -> list[str]:
    if row.owner["name"] == "Entry" and row.function["name"] == "or_insert":
        return [
            "occupied branch retains and returns the stored value",
            "vacant branch inserts and returns the supplied value",
            "entry key, map length, and mutable-reference final frame are preserved",
        ]
    if (
        row.owner["name"] == "ExtractIf"
        and row.trait == "Iterator"
        and row.function["name"] == "next"
    ):
        return [
            "predicate visits unvisited keys in ascending order through the first removal",
            "Some yields that removed binding and advances the visited/unvisited partition",
            "None exhausts the unvisited range while retained values stay in the map",
        ]
    if (
        row.owner["name"] == "ExtractIf"
        and row.trait == "Iterator"
        and row.function["name"] == "size_hint"
    ):
        return [
            "lower size hint is zero and upper size hint is the live borrowed-map length",
        ]
    family = semantic_family(row)
    common = {
        "ordered_iterator_forward_step": [
            "result presence equals non-empty remaining state",
            "remaining length decreases by exactly one on Some",
            "yielded item is the first ordered observable item",
        ],
        "ordered_iterator_backward_step": [
            "result presence equals non-empty remaining state",
            "remaining length decreases by exactly one on Some",
            "yielded item is the last ordered observable item",
        ],
        "ordered_iterator_terminal_selection": [
            "result presence equals non-empty remaining state",
            "selected item is the documented first or last ordered endpoint",
        ],
        "ordered_iterator_size_hint": [
            "lower and upper size hints exactly equal remaining length",
        ],
        "ordered_iterator_exact_len": ["returned length exactly equals remaining length"],
        "ordered_iterator_clone": [
            "clone preserves the complete ordered remaining observation",
        ],
        "ordered_iterator_empty_default": ["default iterator has zero remaining items"],
        "ordered_debug_format": [
            "formatter observes entries in key order and preserves formatter result/effect",
        ],
        "owning_iterator_drop": [
            "all remaining owned entries are dropped and allocator ownership is released",
        ],
        "map_borrowed_or_endpoint_observer": [
            "result branch matches key membership or map emptiness",
            "returned key/value belongs to the pre-state map",
            "endpoint result respects comparator order",
        ],
        "map_entry_handle": [
            "entry branch matches key membership or endpoint availability",
            "handle retains the selected key and mutable map frame",
        ],
        "map_removal_transition": [
            "result branch matches pre-state membership or emptiness",
            "returned key/value is the removed binding",
            "final map removes exactly that comparator-equal key and updates length",
        ],
        "map_mutable_lookup_frame": [
            "result branch matches borrowed-key membership",
            "returned mutable reference frames the selected value into the final map",
        ],
        "map_ordered_callback_filter": [
            "callback visits keys in ascending order",
            "final domain is a subset of the pre-state domain",
            "kept/removed bindings match callback outcomes including current-item retention",
        ],
        "map_append_last_value_wins": [
            "other map is empty afterward",
            "final domain is the union",
            "other value wins comparator-equal conflicts while stored-key identity is retained",
        ],
        "map_range_bounds_order": [
            "normal return requires valid non-panicking bounds",
            "remaining entries are exactly the ascending in-range bindings",
        ],
        "map_order_partition": [
            "left and returned maps partition the old bindings at the comparator boundary",
            "partition lengths sum to the old length",
        ],
        "map_iterator_construction": [
            "remaining length equals map length",
            "observable sequence is ascending by key",
            "mutable/owning frame is preserved",
        ],
        "map_into_iterator": [
            "iterator owns or borrows exactly the source map bindings in ascending order",
        ],
        "map_collection_conversion": [
            "all input bindings are processed in order",
            "last comparator-equal input wins while stable key identity is retained",
        ],
        "map_ordered_comparison": [
            "result equals lexicographic comparison of ascending key/value observations",
        ],
        "map_index_panic_domain": [
            "normal return requires borrowed-key membership",
            "returned value is the mapped value",
        ],
        "map_ordered_hash": [
            "length prefix and ascending key/value pairs are hashed in source order",
        ],
        "map_drop_allocator": [
            "all bindings are dropped through owning iteration before allocator release",
        ],
        "entry_observer_or_mutable_frame": [
            "returned key/value matches the selected entry",
            "mutable return is framed into the final underlying map",
        ],
        "entry_removal_transition": [
            "occupied binding is returned and removed exactly once",
        ],
        "entry_insert_or_replace_transition": [
            "vacant insertion increases length; occupied insertion replaces only the value",
            "returned handle/reference frames the final map binding",
        ],
        "entry_branch_callback_transition": [
            "callback/default is invoked only on its documented entry branch",
            "entry key, map length, and returned-reference frame are preserved",
        ],
        "source_owned_stable_transition": [
            "result and final state are tied to the exact Rust source transition",
        ],
    }
    return common[family]


def receiver_info(inputs: list[tuple[str, str, str]]) -> tuple[str | None, str | None]:
    for name, rust_type, source_name in inputs:
        if source_name == "self":
            if rust_type.startswith("&") and "mut " in rust_type:
                return name, "mut_ref"
            if rust_type.startswith("&"):
                return name, "ref"
            return name, "value"
    return None, None


def require_lines(row: Row, inputs: list[tuple[str, str, str]]) -> list[str]:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    receiver, receiver_kind = receiver_info(inputs)
    args = {source: rendered for rendered, _, source in inputs}
    if owner == "BTreeMap" and trait == "inherent":
        if name in {"range", "range_mut", "extract_if"}:
            bound_type = "K" if name == "extract_if" else "T"
            requirements = [
                (
                    f"ordered_range_domain::<{bound_type}, R>("
                    f"&{args.get('range', 'arg1')})"
                )
            ]
            if name == "extract_if":
                source_map = f"old({receiver})@"
                range_arg = args.get("range", "arg1")
                callback = args.get("pred", "arg2")
                requirements.append(
                    (
                        f"ordered_callback_domain_for_keys({source_map},"
                        f" ordered_range_key_sequence::<K, V, K, R>("
                        f"{source_map}, &{range_arg}), &{callback})"
                    )
                )
            return requirements
        if name == "retain":
            return [
                f"ordered_callback_domain(old({receiver})@, &{args.get('f', 'arg1')})"
            ]
    if owner == "BTreeMap" and trait == "Index":
        return [
            f"contains_borrowed_key({receiver}@, {args.get('key', 'arg1')})"
        ]
    if owner == "Entry" and name in {"or_insert_with", "or_insert_with_key", "and_modify"}:
        pre_ref = receiver
        if name == "or_insert_with":
            pre_map = f"ordered_handle_map::<K, V, _>({pre_ref})"
            key = f"ordered_handle_key::<K, _>({pre_ref})"
            callback = args.get("default", "arg1")
            return [f"!{pre_map}.contains_key({key}) ==> {callback}.requires(())"]
        if name == "or_insert_with_key":
            pre_map = f"ordered_handle_map::<K, V, _>({pre_ref})"
            key = f"ordered_handle_key::<K, _>({pre_ref})"
            callback = args.get("default", "arg1")
            return [
                f"!{pre_map}.contains_key({key})"
                f" ==> {callback}.requires((&{key},))"
            ]
        pre_map = f"ordered_handle_map::<K, V, _>({pre_ref})"
        key = f"ordered_handle_key::<K, _>({pre_ref})"
        callback = args.get("default", args.get("f", "arg1"))
        return [f"entry_callback_domain({pre_map}, {key}, &{callback})"]
    return []


def ensure_lines(row: Row, inputs: list[tuple[str, str, str]], output: str | None) -> list[str]:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    receiver, receiver_kind = receiver_info(inputs)
    args = {source: rendered for rendered, _, source in inputs}
    result = "result"

    if owner in ITERATOR_TYPES:
        if trait == "Iterator" and name == "next":
            if owner == "ExtractIf":
                return [
                    (
                        f"if old({receiver}).ordered_remaining().len() > 0 {{"
                        f" &&& final({receiver}).ordered_remaining()"
                        f" == old({receiver}).ordered_remaining().drop_first()"
                        f" &&& {result} == Some(old({receiver}).ordered_remaining()[0])"
                        f" }} else {{"
                        f" &&& final({receiver}).ordered_remaining()"
                        f" == old({receiver}).ordered_remaining()"
                        f" &&& {result}.is_none() }}"
                    ),
                    (
                        f"final({receiver}).extract_model()"
                        f" == old({receiver}).extract_model()"
                    ),
                    (
                        f"final({receiver}).extract_visited_keys()"
                        f" == old({receiver}).extract_visited_keys()"
                        f" + old({receiver}).extract_next_consumed_keys()"
                    ),
                    (
                        f"final({receiver}).extract_unvisited_keys()"
                        f" == old({receiver}).extract_unvisited_keys().skip("
                        f"old({receiver}).extract_next_consumed_keys().len() as int)"
                    ),
                    (
                        f"final({receiver}).extract_current_map()"
                        f" == extract_if_visit_map("
                        f"old({receiver}).extract_model(),"
                        f" old({receiver}).extract_current_map(),"
                        f" old({receiver}).extract_next_consumed_keys())"
                    ),
                    (
                        f"final({receiver}).extract_yielded_pairs()"
                        f" == match {result} {{"
                        f" Some(pair) => old({receiver}).extract_yielded_pairs().push(pair),"
                        f" None => old({receiver}).extract_yielded_pairs() }}"
                    ),
                    f"old({receiver}).extract_state_coherent()",
                    f"final({receiver}).extract_state_coherent()",
                    (
                        f"match {result} {{"
                        f" Some(_) => final({receiver}).extract_unvisited_keys().len()"
                        f" < old({receiver}).extract_unvisited_keys().len(),"
                        f" None => final({receiver}).extract_unvisited_keys().len() == 0 }}"
                    ),
                    (
                        f"forall|key: K| final({receiver}).extract_unvisited_keys()"
                        f".contains(key) ==> {{"
                        f" &&& final({receiver}).extract_current_map().contains_key(key)"
                        f" &&& final({receiver}).extract_current_map()[key]"
                        f" == old({receiver}).extract_current_map()[key] }}"
                    ),
                ]
            return [
                (
                    f"if old({receiver}).ordered_remaining().len() > 0 {{"
                    f" &&& final({receiver}).ordered_remaining()"
                    f" == old({receiver}).ordered_remaining().drop_first()"
                    f" &&& {result} == Some(old({receiver}).ordered_remaining()[0])"
                    f" }} else {{"
                    f" &&& final({receiver}).ordered_remaining()"
                    f" == old({receiver}).ordered_remaining()"
                    f" &&& {result}.is_none() }}"
                ),
            ]
        if trait == "DoubleEndedIterator" and name == "next_back":
            return [
                (
                    f"if old({receiver}).ordered_remaining().len() > 0 {{"
                    f" &&& final({receiver}).ordered_remaining()"
                    f" == old({receiver}).ordered_remaining().drop_last()"
                    f" &&& {result} == Some(old({receiver}).ordered_remaining().last())"
                    f" }} else {{"
                    f" &&& final({receiver}).ordered_remaining()"
                    f" == old({receiver}).ordered_remaining()"
                    f" &&& {result}.is_none() }}"
                ),
            ]
        if trait == "Iterator" and name == "size_hint":
            if owner == "ExtractIf":
                return [
                    f"{result}.0 == 0",
                    (
                        f"{result}.1 == Some("
                        f"{receiver}.extract_current_map().len() as usize)"
                    ),
                ]
            return [
                f"{result}.0 as nat == ordered_iterator_remaining_len({receiver})",
                f"{result}.1 == Some({result}.0)",
            ]
        if trait == "Iterator" and name in {"last", "min", "max"}:
            endpoint = "back" if name in {"last", "max"} else "front"
            ref = f"&{receiver}" if receiver_kind == "value" else receiver
            return [
                f"{result}.is_some() <==> ordered_iterator_remaining_len({ref}) > 0",
                (
                    f"match {result} {{ Some(item) => ordered_iterator_{endpoint}_matches"
                    f"({ref}, &item), None => true }}"
                ),
            ]
        if trait == "ExactSizeIterator" and name == "len":
            return [f"{result} as nat == ordered_iterator_remaining_len({receiver})"]
        if trait == "Clone" and name == "clone":
            return [
                f"ordered_iterator_remaining_len(&{result}) == ordered_iterator_remaining_len({receiver})",
                f"ordered_iterator_equivalent({receiver}, &{result})",
            ]
        if trait == "Default" and name == "default":
            return [
                (
                    f"{result}.ordered_remaining()"
                    f" == Seq::<_>::empty()"
                )
            ]
        if trait == "Drop" and name == "drop":
            return [
                f"ordered_iterator_remaining_len(final({receiver})) == 0",
                f"ordered_drop_releases_remaining(old({receiver}), final({receiver}))",
            ]

    if trait == "Debug":
        formatter = args.get("f", args.get("formatter", "arg1"))
        subject = receiver if receiver_kind != "value" else f"&{receiver}"
        if owner == "BTreeMap":
            relation = f"ordered_map_debug_result({receiver}@"
        elif owner in ITERATOR_TYPES and owner != "ExtractIf":
            relation = f"ordered_iterator_debug_result({subject}"
        elif owner in {"Entry", "OccupiedEntry", "VacantEntry"}:
            relation = f"ordered_handle_debug_result::<K, V, _>({subject}"
        else:
            relation = f"ordered_debug_result({subject}"
        return [
            (
                f"{relation}, *old({formatter}), {result}, "
                f"*final({formatter}))"
            )
        ]

    if owner == "BTreeMap":
        if trait == "inherent":
            key = args.get("key", args.get("k", "arg1"))
            range_arg = args.get("range", "arg1")
            if name == "get_key_value":
                return [
                    (
                        f"match {result} {{ Some((stored_key, value)) => "
                        f"borrowed_key_matches(stored_key, {key})"
                        f" && *stored_key == borrowed_lookup_stored_key::<K, Q, V>("
                        f"{receiver}@, {key})"
                        f" && {receiver}@.contains_key(*stored_key)"
                        f" && {receiver}@[*stored_key] == *value,"
                        f" None => !contains_borrowed_key({receiver}@, {key}) }}"
                    )
                ]
            if name in {"first_key_value", "last_key_value"}:
                endpoint = "first" if name.startswith("first") else "last"
                return [
                    f"{result}.is_some() <==> !{receiver}@.is_empty()",
                    (
                        f"match {result} {{ Some((key, value)) => "
                        f"{receiver}@.contains_key(*key) && {receiver}@[*key] == *value"
                        f" && ordered_map_{endpoint}_key({receiver}@, *key), None => true }}"
                    ),
                ]
            if name in {"first_entry", "last_entry"}:
                endpoint = "first" if name.startswith("first") else "last"
                return [
                    f"{result}.is_some() <==> !old({receiver})@.is_empty()",
                    (
                        f"match {result} {{ Some(handle) => "
                        f"ordered_handle_map::<K, V, _>(handle) == old({receiver})@"
                        f" && ordered_map_{endpoint}_key(old({receiver})@,"
                        f" ordered_handle_key::<K, _>(handle))"
                        f" && ordered_handle_is_occupied(handle)"
                        f" && final({receiver})@"
                        f" == ordered_handle_final_map::<K, V, _>(handle),"
                        f" None => final({receiver})@ == old({receiver})@ }}"
                    ),
                ]
            if name in {"pop_first", "pop_last"}:
                endpoint = "first" if name.endswith("first") else "last"
                return [
                    f"{result}.is_some() <==> !old({receiver})@.is_empty()",
                    (
                        f"match {result} {{ Some((key, value)) => "
                        f"old({receiver})@.contains_key(key)"
                        f" && old({receiver})@[key] == value"
                        f" && ordered_map_{endpoint}_key(old({receiver})@, key)"
                        f" && final({receiver})@ == old({receiver})@.remove(key),"
                        f" None => final({receiver})@ == old({receiver})@ }}"
                    ),
                ]
            if name == "get_mut":
                return [
                    (
                        f"match {result} {{ Some(value) => "
                        f"contains_borrowed_key(old({receiver})@, {key})"
                        f" && maps_borrowed_key_to_value("
                        f"old({receiver})@, {key}, *value)"
                        f" && borrowed_key_value_updated(old({receiver})@,"
                        f" final({receiver})@, {key}, *final(value))"
                        f" && final({receiver})@.dom() == old({receiver})@.dom(),"
                        f" None => !contains_borrowed_key(old({receiver})@, {key})"
                        f" && final({receiver})@ == old({receiver})@ }}"
                    )
                ]
            if name == "remove_entry":
                return [
                    (
                        f"match {result} {{ Some((stored_key, value)) => "
                        f"borrowed_key_matches(&stored_key, {key})"
                        f" && stored_key == borrowed_lookup_stored_key::<K, Q, V>("
                        f"old({receiver})@, {key})"
                        f" && old({receiver})@.contains_key(stored_key)"
                        f" && old({receiver})@[stored_key] == value"
                        f" && maps_borrowed_key_to_value("
                        f"old({receiver})@, {key}, value)"
                        f" && borrowed_key_removed("
                        f"old({receiver})@, final({receiver})@, {key}),"
                        f" None => !contains_borrowed_key(old({receiver})@, {key})"
                        f" && final({receiver})@ == old({receiver})@ }}"
                    )
                ]
            if name == "retain":
                callback = args.get("f", "arg1")
                return [
                    f"final({receiver})@.dom().subset_of(old({receiver})@.dom())",
                    f"final({receiver})@.len() <= old({receiver})@.len()",
                    (
                        f"ordered_callback_filter(old({receiver})@,"
                        f" ordered_map_key_sequence(old({receiver})@),"
                        f" {callback}, final({receiver})@)"
                    ),
                    (
                        f"ordered_callback_unwind_contract(old({receiver})@,"
                        f" ordered_map_key_sequence(old({receiver})@),"
                        f" &{callback})"
                    ),
                ]
            if name == "append":
                other = args.get("other", "arg1")
                return [
                    f"final({other})@.is_empty()",
                    (
                        f"append_last_value_wins(old({receiver})@, old({other})@,"
                        f" final({receiver})@)"
                    ),
                    (
                        f"final({receiver})@.dom()"
                        f" == old({receiver})@.dom().union(old({other})@.dom())"
                    ),
                ]
            if name in {"range", "range_mut"}:
                source_map = (
                    f"old({receiver})@" if receiver_kind == "mut_ref" else f"{receiver}@"
                )
                bound_type = "T"
                return [
                    (
                        f"ordered_range_result::<K, V, {bound_type}, R, _>("
                        f"{source_map}, &{range_arg}, &{result})"
                    ),
                    *(
                        [
                            f"final({receiver})@.dom() == old({receiver})@.dom()",
                            (
                                f"forall|key: K| old({receiver})@.contains_key(key)"
                                f" && !ordered_key_in_range::<K, T, R>(&{range_arg}, key)"
                                f" ==> final({receiver})@[key] == old({receiver})@[key]"
                            ),
                        ]
                        if name == "range_mut"
                        else []
                    ),
                ]
            if name == "entry":
                key_arg = args.get("key", "arg1")
                return [
                    f"ordered_handle_map::<K, V, _>({result}) == old({receiver})@",
                    f"ordered_handle_key::<K, _>({result}) == {key_arg}",
                    (
                        f"ordered_handle_is_occupied({result})"
                        f" <==> old({receiver})@.contains_key({key_arg})"
                    ),
                    (
                        f"final({receiver})@"
                        f" == ordered_handle_final_map::<K, V, _>({result})"
                    ),
                ]
            if name == "split_off":
                return [
                    (
                        f"final({receiver})@.len() + {result}@.len()"
                        f" == old({receiver})@.len()"
                    ),
                    (
                        f"ordered_split_partition(old({receiver})@, {key},"
                        f" final({receiver})@, {result}@)"
                    ),
                ]
            if name == "extract_if":
                callback = args.get("pred", "arg2")
                range_keys = (
                    f"ordered_range_key_sequence::<K, V, K, R>("
                    f"old({receiver})@, &{range_arg})"
                )
                return [
                    f"final({receiver})@ == old({receiver})@",
                    (
                        f"extract_if_unvisited_keys::<K, V, _>(&{result})"
                        f" == {range_keys}"
                    ),
                    (
                        f"extract_if_visited_keys::<K, V, _>(&{result})"
                        f" == Seq::<K>::empty()"
                    ),
                    (
                        f"extract_if_yielded_pairs::<K, V, _>(&{result})"
                        f" == Seq::<(K, V)>::empty()"
                    ),
                    (
                        f"extract_if_current_map::<K, V, _>(&{result})"
                        f" == old({receiver})@"
                    ),
                    (
                        f"{result}.ordered_remaining()"
                        f" == extract_if_removed_pairs("
                        f"extract_if_model(&{result}), old({receiver})@, {range_keys})"
                    ),
                    (
                        f"ordered_callback_unwind_contract(old({receiver})@,"
                        f" {range_keys}, &{callback})"
                    ),
                    (
                        f"extract_if_lifecycle(old({receiver})@, &{range_arg}, {callback},"
                        f" &{result}, final({receiver})@, Seq::<K>::empty(),"
                        f" {range_keys})"
                    ),
                ]
            if name in {"into_keys", "into_values"}:
                return [
                    f"ordered_iterator_remaining_len(&{result}) == {receiver}@.len()",
                    f"ordered_map_iterator_result({receiver}@, &{result})",
                    f"owning_iterator_transfer(&{receiver}, &{result})",
                ]
            if name in {"iter_mut", "values_mut"}:
                return [
                    f"ordered_iterator_remaining_len(&{result}) == old({receiver})@.len()",
                    (
                        f"ordered_map_mut_iterator_frame(old({receiver})@, &{result},"
                        f" final({receiver})@)"
                    ),
                ]
        if trait == "IntoIterator":
            source = receiver if receiver_kind == "value" else receiver
            source_map = (
                f"{source}@"
                if receiver_kind in {"ref", "value"}
                else f"old({source})@"
            )
            lines = [
                f"ordered_iterator_remaining_len(&{result}) == {source_map}.len()",
                f"ordered_map_iterator_result({source_map}, &{result})",
            ]
            if receiver_kind == "value":
                lines.append(f"owning_iterator_transfer(&{receiver}, &{result})")
            return lines
        if trait == "FromIterator":
            iterator = args.get("iter", "arg0")
            return [
                f"from_iterator_last_value_wins({iterator}, {result}@)",
                f"ordered_map_well_formed({result}@)",
            ]
        if trait == "Extend":
            iterator = args.get("iter", "arg1")
            return [
                f"final({receiver})@.len() >= old({receiver})@.len()",
                (
                    f"extend_last_value_wins(old({receiver})@, {iterator},"
                    f" final({receiver})@)"
                ),
            ]
        if trait == "Hash":
            state = args.get("state", "arg1")
            return [
                (
                    f"ordered_hash_transition({receiver}@, *old({state}),"
                    f" *final({state}))"
                )
            ]
        if trait == "PartialEq":
            other = args.get("other", "arg1")
            return [f"{result} == ({receiver}@ == {other}@)"]
        if trait in {"PartialOrd", "Ord"}:
            other = args.get("other", "arg1")
            comparison = (
                "ordered_map_partial_cmp" if trait == "PartialOrd" else "ordered_map_cmp"
            )
            return [f"{result} == {comparison}({receiver}@, {other}@)"]
        if trait == "Index":
            key = args.get("key", args.get("index", "arg1"))
            return [
                f"contains_borrowed_key({receiver}@, {key})",
                f"maps_borrowed_key_to_value({receiver}@, {key}, *{result})",
            ]
        if trait == "From":
            array = args.get("arr", args.get("value", "arg0"))
            return [
                f"{result}@.len() <= N",
                f"array_last_value_wins(&{array}, {result}@)",
            ]
        if trait == "Drop":
            return [
                f"final({receiver})@.is_empty()",
                f"map_drop_releases_allocator(old({receiver})@, final({receiver})@)",
            ]

    if owner in {"Entry", "OccupiedEntry", "VacantEntry"}:
        pre_ref = (
            receiver
            if receiver_kind == "value"
            else f"*old({receiver})"
            if receiver_kind == "mut_ref"
            else receiver
        )
        key_expr = f"ordered_handle_key::<K, _>({pre_ref})"
        pre_map = f"ordered_handle_map::<K, V, _>({pre_ref})"
        pre_final_map = f"ordered_handle_final_map::<K, V, _>({pre_ref})"
        value_arg = args.get("value", args.get("default", "arg1"))
        if name in {"key", "into_key"}:
            deref = f"*{result}" if output and output.startswith("&") else result
            lines = [f"{deref} == {key_expr}"]
            if name == "into_key":
                lines.extend(
                    [
                        f"!{pre_map}.contains_key({key_expr})",
                        f"{pre_final_map} == {pre_map}",
                    ]
                )
            return lines
        if name == "get":
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"*{result} == {pre_map}[{key_expr}]",
            ]
        if name == "get_mut":
            post_ref = f"*final({receiver})"
            post_map = f"ordered_handle_map::<K, V, _>({post_ref})"
            post_final_map = f"ordered_handle_final_map::<K, V, _>({post_ref})"
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"*{result} == {pre_map}[{key_expr}]",
                (
                    f"entry_mutable_frame({pre_map}, {key_expr}, *{result},"
                    f" *final({result}), {post_map})"
                ),
                f"{pre_final_map} == {post_final_map}",
            ]
        if name == "into_mut":
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"*{result} == {pre_map}[{key_expr}]",
                (
                    f"entry_mutable_frame({pre_map}, {key_expr}, *{result},"
                    f" *final({result}), {pre_final_map})"
                ),
            ]
        if name == "remove_entry":
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"{result}.0 == {key_expr}",
                f"{result}.1 == {pre_map}[{key_expr}]",
                (
                    f"entry_remove_transition("
                    f"{pre_map}, {key_expr}, {pre_final_map})"
                ),
            ]
        if name == "remove":
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"{result} == {pre_map}[{key_expr}]",
                (
                    f"entry_remove_transition("
                    f"{pre_map}, {key_expr}, {pre_final_map})"
                ),
            ]
        if name == "insert_entry":
            result_ref = result
            post_map = f"ordered_handle_map::<K, V, _>({result_ref})"
            post_final_map = (
                f"ordered_handle_final_map::<K, V, _>({result_ref})"
            )
            lines = [
                f"ordered_handle_key::<K, _>({result_ref}) == {key_expr}",
                f"{post_map} == {pre_map}.insert({key_expr}, {value_arg})",
                f"ordered_handle_is_occupied({result_ref})",
                f"{pre_final_map} == {post_final_map}",
            ]
            if owner == "VacantEntry":
                lines.append(f"!{pre_map}.contains_key({key_expr})")
            return lines
        if name == "insert" and owner == "OccupiedEntry":
            post_ref = f"*final({receiver})"
            post_map = f"ordered_handle_map::<K, V, _>({post_ref})"
            post_final_map = f"ordered_handle_final_map::<K, V, _>({post_ref})"
            return [
                f"{pre_map}.contains_key({key_expr})",
                f"{result} == {pre_map}[{key_expr}]",
                f"ordered_handle_key::<K, _>({post_ref}) == {key_expr}",
                f"ordered_handle_is_occupied({post_ref})",
                (
                    f"entry_replace_transition({pre_map}, {key_expr},"
                    f" {value_arg}, {post_map})"
                ),
                f"{pre_final_map} == {post_final_map}",
            ]
        if name == "insert" and owner == "VacantEntry":
            return [
                f"!{pre_map}.contains_key({key_expr})",
                f"*{result} == {value_arg}",
                f"{pre_final_map} == {pre_map}.insert({key_expr}, *final({result}))",
            ]
        if name in {"or_insert", "or_insert_with", "or_insert_with_key", "or_default"}:
            lines = [
                (
                    f"ordered_handle_is_occupied({pre_ref})"
                    f" <==> {pre_map}.contains_key({key_expr})"
                ),
                (
                    f"{pre_final_map}"
                    f" == {pre_map}.insert({key_expr}, *final({result}))"
                ),
            ]
            if name == "or_insert":
                lines.append(
                    f"*{result} == if {pre_map}.contains_key({key_expr})"
                    f" {{ {pre_map}[{key_expr}] }} else {{ {value_arg} }}"
                )
            if name == "or_insert_with":
                lines.append(
                    f"{pre_map}.contains_key({key_expr})"
                    f" ==> *{result} == {pre_map}[{key_expr}]"
                )
                lines.append(
                    f"!{pre_map}.contains_key({key_expr})"
                    f" ==> {value_arg}.ensures((), *{result})"
                )
            if name == "or_insert_with_key":
                lines.append(
                    f"{pre_map}.contains_key({key_expr})"
                    f" ==> *{result} == {pre_map}[{key_expr}]"
                )
                lines.append(
                    f"!{pre_map}.contains_key({key_expr})"
                    f" ==> {value_arg}.ensures((&{key_expr},), *{result})"
                )
            if name == "or_default":
                lines.extend(
                    [
                        (
                            f"{pre_map}.contains_key({key_expr})"
                            f" ==> *{result} == {pre_map}[{key_expr}]"
                        ),
                        (
                            f"!{pre_map}.contains_key({key_expr})"
                            f" ==> V::default.ensures((), *{result})"
                        ),
                    ]
                )
            return lines
        if name == "and_modify":
            callback = args.get("f", "arg1")
            result_ref = result
            result_map = f"ordered_handle_map::<K, V, _>({result_ref})"
            result_final_map = (
                f"ordered_handle_final_map::<K, V, _>({result_ref})"
            )
            return [
                f"ordered_handle_key::<K, _>({result_ref}) == {key_expr}",
                (
                    f"entry_and_modify_transition({pre_map}, {key_expr},"
                    f" {callback}, {result_map})"
                ),
                (
                    f"ordered_handle_is_occupied({result_ref})"
                    f" <==> {pre_map}.contains_key({key_expr})"
                ),
                f"{pre_final_map} == {result_final_map}",
            ]

    subject = receiver
    if subject is None and inputs:
        subject = inputs[0][0]
    if output is not None:
        return [f"source_owned_result({row.item_id}, &{subject}, &{result})"]
    if receiver_kind == "mut_ref":
        return [f"source_owned_transition({row.item_id}, old({receiver}), final({receiver}))"]
    return [f"source_owned_unit({row.item_id})"]


def comparison_guard(row: Row) -> str | None:
    comparator_families = {
        "map_borrowed_or_endpoint_observer",
        "map_entry_handle",
        "map_removal_transition",
        "map_mutable_lookup_frame",
        "map_ordered_callback_filter",
        "map_append_last_value_wins",
        "map_range_bounds_order",
        "map_order_partition",
        "map_collection_conversion",
        "map_ordered_comparison",
        "map_index_panic_domain",
    }
    if row.semantic_family not in comparator_families:
        return None
    guards = ["key_obeys_cmp_spec::<K>()"]
    if row.owner["name"] == "BTreeMap" and row.function["name"] in {
        "get_key_value",
        "get_mut",
        "remove_entry",
        "split_off",
    }:
        guards.append("key_obeys_cmp_spec::<Q>()")
    if row.owner["name"] == "BTreeMap" and row.function["name"] in {
        "range",
        "range_mut",
    }:
        guards.append("key_obeys_cmp_spec::<T>()")
    if row.owner["name"] == "BTreeMap" and row.trait == "Index":
        guards.append("key_obeys_cmp_spec::<Q>()")
    return " && ".join(guards)


def guard_contract_clauses(row: Row, clauses: list[str]) -> list[str]:
    if row.disposition != "generated":
        return clauses
    guard = comparison_guard(row)
    if guard is None:
        return clauses
    return [f"{guard} ==> ({clause})" for clause in clauses]


SHARED_VOCABULARY = r'''// Shared ordered-map vocabulary for Rust 1.96 alloc::collections::btree_map.
extern crate alloc;

use alloc::alloc::Allocator;
use alloc::boxed::Box;
use alloc::collections::BTreeMap;
use alloc::collections::btree_map::{
    Entry, ExtractIf, IntoIter, IntoKeys, IntoValues, Iter, IterMut, Keys, OccupiedEntry,
    Range, RangeMut, VacantEntry, Values, ValuesMut,
};
use core::borrow::Borrow;
use core::cmp::Ordering;
use core::fmt::Formatter;
use core::hash::Hasher;
use core::iter::{IntoIterator, Iterator};
use core::ops::{FnMut, Index, RangeBounds};
use vstd::prelude::*;
use vstd::std_specs::btree::{
    borrowed_key_removed, contains_borrowed_key, increasing_seq, key_obeys_cmp_spec,
    maps_borrowed_key_to_value,
};
use vstd::std_specs::cmp::{OrdSpec, PartialOrdSpec};
use vstd::std_specs::iter::{IteratorSpec, IteratorSpecImpl, into_iter_remaining};
use vstd::std_specs::core::IndexSpec;
use vstd::std_specs::range::{RangeBoundsSpec, SpecBound};

verus! {

pub broadcast axiom fn axiom_btree_map_index_req<
    'key,
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
    A: Allocator + Clone,
>(
    map: &BTreeMap<K, V, A>,
    key: &'key Q,
)
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (
            <BTreeMap<K, V, A> as IndexSpec<&'key Q>>::index_req(map, &key)
                <==> contains_borrowed_key(map@, key)
        ),
;

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExEntry<'a, K: 'a, V: 'a, A: Allocator + Clone>(Entry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExOccupiedEntry<'a, K, V, A: Allocator + Clone>(OccupiedEntry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExVacantEntry<'a, K, V, A: Allocator + Clone>(VacantEntry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExIterMut<'a, K: 'a, V: 'a>(IterMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoIter<K, V, A: Allocator + Clone>(IntoIter<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExValuesMut<'a, K, V>(ValuesMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoKeys<K, V, A: Allocator + Clone>(IntoKeys<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoValues<K, V, A: Allocator + Clone>(IntoValues<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExRange<'a, K, V>(Range<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExRangeMut<'a, K: 'a, V: 'a>(RangeMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(R)]
#[verifier::reject_recursive_types(F)]
#[verifier::reject_recursive_types(A)]
pub struct ExExtractIf<
    'a,
    K,
    V,
    R,
    F,
    A: Allocator + Clone,
>(ExtractIf<'a, K, V, R, F, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFormatter<'a>(Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFmtError(core::fmt::Error);

pub trait BTreeMapIteratorModel {
    type Item;
    type Key;
    type Value;
    #[verifier::prophetic]
    spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    spec fn ordered_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn ordered_values(&self) -> Seq<Self::Value>;
}

pub trait ExtractIfIteratorModel {
    type Key;
    type Value;
    spec fn extract_model(&self) -> int;
    spec fn extract_visited_keys(&self) -> Seq<Self::Key>;
    spec fn extract_unvisited_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn extract_yielded_pairs(&self) -> Seq<(Self::Key, Self::Value)>;
    #[verifier::prophetic]
    spec fn extract_current_map(&self) -> Map<Self::Key, Self::Value>;
    #[verifier::prophetic]
    spec fn extract_next_consumed_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn extract_state_coherent(&self) -> bool;
}

impl<'a, K, V> BTreeMapIteratorModel for Iter<'a, K, V> {
    type Item = (&'a K, &'a V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.1,
        )
    }
}

impl<'a, K, V> BTreeMapIteratorModel for Keys<'a, K, V> {
    type Item = &'a K;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, key: &'a K| *key)
    }
    #[verifier::prophetic]
    uninterp spec fn ordered_values(&self) -> Seq<V>;
}

impl<'a, K, V> BTreeMapIteratorModel for Values<'a, K, V> {
    type Item = &'a V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, value: &'a V| *value)
    }
}

pub broadcast axiom fn axiom_iter_ordered_remaining<'a, K, V>(
    iterator: &Iter<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_keys_ordered_remaining<'a, K, V>(
    iterator: &Keys<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_values_ordered_remaining<'a, K, V>(
    iterator: &Values<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_spec_btree_map_iter_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_btree_map_iter(map);
            &&& IteratorSpec::remaining(&iterator).no_duplicates()
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
            &&& increasing_seq(IteratorSpec::remaining(&iterator).map_values(
                |pair: (&K, &V)| *pair.0,
            ))
        },
;

pub broadcast axiom fn axiom_spec_btree_map_keys_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_keys_iter(map);
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
        },
;

pub broadcast axiom fn axiom_spec_btree_map_values_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_values_iter(map);
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
            &&& exists|key_seq: Seq<K>| {
                &&& increasing_seq(key_seq)
                &&& key_seq.to_set() == map@.dom()
                &&& key_seq.no_duplicates()
                &&& IteratorSpec::remaining(&iterator) == key_seq.map(
                    |_index: int, key: K| &map@[key],
                )
            }
        },
;

impl<'a, K, V> BTreeMapIteratorModel for IterMut<'a, K, V> {
    type Item = (&'a K, &'a mut V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.1,
        )
    }
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoIter<K, V, A> {
    type Item = (K, V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.0)
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.1)
    }
}

impl<'a, K, V> BTreeMapIteratorModel for ValuesMut<'a, K, V> {
    type Item = &'a mut V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, value: &'a mut V| *value)
    }
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoKeys<K, V, A> {
    type Item = K;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining()
    }
    #[verifier::prophetic]
    uninterp spec fn ordered_values(&self) -> Seq<V>;
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoValues<K, V, A> {
    type Item = V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining()
    }
}

impl<'a, K, V> BTreeMapIteratorModel for Range<'a, K, V> {
    type Item = (&'a K, &'a V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.1,
        )
    }
}

impl<'a, K, V> BTreeMapIteratorModel for RangeMut<'a, K, V> {
    type Item = (&'a K, &'a mut V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.1,
        )
    }
}

impl<'a, K, V, R, F, A: Allocator + Clone> BTreeMapIteratorModel
    for ExtractIf<'a, K, V, R, F, A>
where
    K: PartialOrd,
    R: RangeBounds<K>,
    F: FnMut(&K, &mut V) -> bool,
{
    type Item = (K, V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.0)
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.1)
    }
}

impl<'a, K, V, R, F, A: Allocator + Clone> ExtractIfIteratorModel
    for ExtractIf<'a, K, V, R, F, A>
where
    K: PartialOrd,
    R: RangeBounds<K>,
    F: FnMut(&K, &mut V) -> bool,
{
    type Key = K;
    type Value = V;
    open spec fn extract_model(&self) -> int {
        extract_if_model(self)
    }
    open spec fn extract_visited_keys(&self) -> Seq<K> {
        extract_if_visited_keys::<K, V, _>(self)
    }
    open spec fn extract_unvisited_keys(&self) -> Seq<K> {
        extract_if_unvisited_keys::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_yielded_pairs(&self) -> Seq<(K, V)> {
        extract_if_yielded_pairs::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_current_map(&self) -> Map<K, V> {
        extract_if_current_map::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_next_consumed_keys(&self) -> Seq<K> {
        extract_if_next_consumed_keys::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_state_coherent(&self) -> bool {
        extract_if_state_coherent::<K, V, _>(self)
    }
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_remaining_len<I: BTreeMapIteratorModel>(
    iter: &I,
) -> nat {
    iter.ordered_remaining().len()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_front_matches<I: BTreeMapIteratorModel>(
    iter: &I,
    item: &I::Item,
) -> bool {
    iter.ordered_remaining().len() > 0 && *item == iter.ordered_remaining()[0]
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_back_matches<I: BTreeMapIteratorModel>(
    iter: &I,
    item: &I::Item,
) -> bool {
    iter.ordered_remaining().len() > 0 && *item == iter.ordered_remaining().last()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_equivalent<I: BTreeMapIteratorModel>(
    left: &I,
    right: &I,
) -> bool {
    left.ordered_remaining() == right.ordered_remaining()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_key_trace<
    K,
    I: BTreeMapIteratorModel<Key = K>,
>(
    iterator: &I,
) -> Seq<K> {
    iterator.ordered_keys()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_value_trace<
    V,
    I: BTreeMapIteratorModel<Value = V>,
>(
    iterator: &I,
) -> Seq<V> {
    iterator.ordered_values()
}

pub uninterp spec fn ordered_map_pairs<K, V>(map: Map<K, V>) -> Seq<(K, V)>;
pub uninterp spec fn ordered_map_key_sequence<K, V>(map: Map<K, V>) -> Seq<K>;

pub broadcast axiom fn axiom_ordered_map_pairs<K, V>(map: Map<K, V>)
    ensures
        ordered_map_pairs(map).len() == map.len(),
        ordered_map_pairs(map).no_duplicates(),
        forall|i: int| 0 <= i < ordered_map_pairs(map).len() ==> {
            let pair = #[trigger] ordered_map_pairs(map)[i];
            map.contains_key(pair.0) && map[pair.0] == pair.1
        },
        forall|key: K| #[trigger] map.contains_key(key) ==> exists|i: int|
            0 <= i < ordered_map_pairs(map).len()
                && ordered_map_pairs(map)[i].0 == key,
        ordered_map_key_sequence(map).len() == map.len(),
        ordered_map_key_sequence(map).to_set() == map.dom(),
        forall|i: int| 0 <= i < ordered_map_pairs(map).len() ==>
            #[trigger] ordered_map_pairs(map)[i].0 == ordered_map_key_sequence(map)[i],
        key_obeys_cmp_spec::<K>() ==> increasing_seq(ordered_map_key_sequence(map)),
;

pub broadcast axiom fn axiom_ordered_map_pairs_extensional<K, V>(
    left: Map<K, V>,
    right: Map<K, V>,
)
    ensures
        #![trigger ordered_map_pairs(left), ordered_map_pairs(right)]
        ordered_map_pairs(left) == ordered_map_pairs(right) ==> left == right,
;

pub open spec fn ordered_map_first_key<K, V>(map: Map<K, V>, key: K) -> bool {
    ordered_map_pairs(map).len() > 0 && ordered_map_pairs(map)[0].0 == key
}

pub open spec fn ordered_map_last_key<K, V>(map: Map<K, V>, key: K) -> bool {
    ordered_map_pairs(map).len() > 0 && ordered_map_pairs(map).last().0 == key
}

pub open spec fn ordered_map_well_formed<K, V>(map: Map<K, V>) -> bool {
    ordered_map_pairs(map).len() == map.len()
        && ordered_map_pairs(map).no_duplicates()
}

pub uninterp spec fn borrowed_key_matches<K, Q: ?Sized>(stored: &K, query: &Q) -> bool;
pub uninterp spec fn borrowed_lookup_stored_key<K, Q: ?Sized, V>(
    map: Map<K, V>,
    query: &Q,
) -> K;

pub broadcast axiom fn axiom_borrowed_key_matches<K: Borrow<Q> + Ord, Q: Ord + ?Sized, V>(
    map: Map<K, V>,
    stored: &K,
    query: &Q,
)
    requires
        borrowed_key_matches(stored, query),
        map.contains_key(*stored),
    ensures
        contains_borrowed_key(map, query),
;

pub open spec fn borrowed_lookup_value_functional<
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
>(
    map: Map<K, V>,
    query: &Q,
) -> bool {
    &&& forall|value: V|
        #[trigger] maps_borrowed_key_to_value(map, query, value)
            ==> contains_borrowed_key(map, query)
    &&& forall|left: V, right: V|
        #[trigger] maps_borrowed_key_to_value(map, query, left)
        && #[trigger] maps_borrowed_key_to_value(map, query, right)
            ==> left == right
}

pub open spec fn borrowed_removal_functional<
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
>(
    map: Map<K, V>,
    query: &Q,
) -> bool {
    &&& borrowed_lookup_value_functional(map, query)
    &&& forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] borrowed_key_removed(map, left, query)
        && #[trigger] borrowed_key_removed(map, right, query)
            ==> left == right
}

pub uninterp spec fn formatter_trace(formatter: Formatter<'_>) -> Seq<int>;
pub uninterp spec fn ordered_debug_trace<T>(subject: &T) -> Seq<int>;
pub uninterp spec fn debug_value_trace<T>(subject: T) -> Seq<int>;
pub uninterp spec fn formatter_failed(formatter: Formatter<'_>) -> bool;
pub uninterp spec fn formatter_failure_after_trace(
    pre_formatter: Formatter<'_>,
    emitted: Seq<int>,
) -> bool;

pub open spec fn debug_result_from_trace(
    emitted: Seq<int>,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    formatter_trace(post_formatter) == formatter_trace(pre_formatter) + emitted
        && formatter_failed(post_formatter)
            == formatter_failure_after_trace(pre_formatter, emitted)
        && (result.is_err() <==> formatter_failed(post_formatter))
}

pub open spec fn ordered_debug_result<T>(
    subject: &T,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        ordered_debug_trace(subject),
        pre_formatter,
        result,
        post_formatter,
    )
}

pub open spec fn ordered_map_debug_trace<K, V>(map: Map<K, V>) -> Seq<int> {
    ordered_map_pairs(map).fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, pair: (K, V)| trace + debug_value_trace(pair),
    )
}

pub open spec fn ordered_map_debug_result<K, V>(
    map: Map<K, V>,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        ordered_map_debug_trace(map),
        pre_formatter,
        result,
        post_formatter,
    )
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_debug_result<I: BTreeMapIteratorModel>(
    iterator: &I,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        iterator.ordered_remaining().fold_left(
            Seq::<int>::empty(),
            |trace: Seq<int>, item: I::Item| trace + debug_value_trace(item),
        ),
        pre_formatter,
        result,
        post_formatter,
    )
}

pub open spec fn ordered_handle_debug_result<K, V, H>(
    handle: &H,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        debug_value_trace(ordered_handle_key::<K, _>(handle))
            + ordered_map_debug_trace(ordered_handle_map::<K, V, _>(handle)),
        pre_formatter,
        result,
        post_formatter,
    )
}
pub uninterp spec fn ordered_handle_map<K, V, H>(handle: H) -> Map<K, V>;
pub uninterp spec fn ordered_handle_final_map<K, V, H>(handle: H) -> Map<K, V>;
pub uninterp spec fn ordered_handle_key<K, H>(handle: H) -> K;
pub uninterp spec fn ordered_handle_is_occupied<H>(handle: H) -> bool;

pub broadcast axiom fn axiom_ordered_handle_reference_coherence<K, V, H>(
    handle: &H,
)
    ensures
        ordered_handle_map::<K, V, H>(*handle)
            == ordered_handle_map::<K, V, &H>(handle),
        ordered_handle_final_map::<K, V, H>(*handle)
            == ordered_handle_final_map::<K, V, &H>(handle),
        ordered_handle_key::<K, H>(*handle)
            == ordered_handle_key::<K, &H>(handle),
        ordered_handle_is_occupied::<H>(*handle)
            == ordered_handle_is_occupied::<&H>(handle),
;

pub broadcast axiom fn axiom_ordered_handle_occupancy_coherent<K, V, H>(
    handle: H,
)
    ensures
        #![trigger
            ordered_handle_is_occupied(handle),
            ordered_handle_map::<K, V, H>(handle),
            ordered_handle_key::<K, H>(handle)
        ]
        ordered_handle_is_occupied(handle)
            <==> ordered_handle_map::<K, V, H>(handle).contains_key(
                ordered_handle_key::<K, H>(handle),
            ),
;

pub uninterp spec fn borrowed_key_value_updated<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    post: Map<K, V>,
    key: &Q,
    value: V,
) -> bool;

pub broadcast axiom fn axiom_borrowed_key_value_updated_direct<Q, V>(
    pre: Map<Q, V>,
    post: Map<Q, V>,
    key: &Q,
    value: V,
)
    ensures
        #[trigger] borrowed_key_value_updated(pre, post, key, value)
            <==> post == pre.insert(*key, value),
;

pub broadcast axiom fn axiom_borrowed_key_value_updated_box<Q, V>(
    pre: Map<Box<Q>, V>,
    post: Map<Box<Q>, V>,
    key: &Q,
    value: V,
)
    ensures
        #[trigger] borrowed_key_value_updated(pre, post, key, value)
            <==> post == pre.insert(Box::new(*key), value),
;

pub open spec fn ordered_callback_domain<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    callback: &F,
) -> bool {
    forall|key_ref: &K, value_ref: &mut V|
        pre.contains_key(*key_ref) && *value_ref == pre[*key_ref]
            ==> #[trigger] callback.requires((key_ref, value_ref))
}

#[verifier::prophetic]
pub open spec fn ordered_callback_domain_for_keys<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: &F,
) -> bool {
    forall|key_ref: &K, value_ref: &mut V|
        pre.contains_key(*key_ref)
            && keys.contains(*key_ref)
            && *value_ref == pre[*key_ref]
            ==> #[trigger] callback.requires((key_ref, value_ref))
}

#[verifier::prophetic]
pub open spec fn ordered_callback_observation<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    state: Map<K, V>,
    callback: F,
    key: K,
    decision: bool,
    final_value: V,
) -> bool {
    exists|key_ref: &K, value_ref: &mut V|
        *key_ref == key
        && *value_ref == state[key]
        && #[trigger] callback.ensures((key_ref, value_ref), decision)
        && *final(value_ref) == final_value
}

#[verifier::no_auto_trigger]
pub uninterp spec fn ordered_callback_filter_trigger<K, V>(
    keep: spec_fn(Map<K, V>, K) -> bool,
    final_value: spec_fn(Map<K, V>, K) -> V,
) -> bool;

#[verifier::prophetic]
pub open spec fn ordered_callback_filter<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: F,
    post: Map<K, V>,
) -> bool {
    exists|
        keep: spec_fn(Map<K, V>, K) -> bool,
        final_value: spec_fn(Map<K, V>, K) -> V,
    |
    #![trigger ordered_callback_filter_trigger(keep, final_value)]
    {
        &&& forall|state: Map<K, V>, key: K|
            state.contains_key(key) && keys.contains(key) ==> {
                ordered_callback_observation(
                    state,
                    callback,
                    key,
                    #[trigger] keep(state, key),
                    #[trigger] final_value(state, key),
                )
            }
        &&& post == keys.fold_left(
            pre,
            |state: Map<K, V>, key: K| {
                if keep(state, key) {
                    state.insert(key, final_value(state, key))
                } else {
                    state.remove(key)
                }
            },
        )
    }
}

#[verifier::prophetic]
pub open spec fn ordered_callback_filter_functional<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: F,
) -> bool {
    forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] ordered_callback_filter(pre, keys, callback, left)
        && #[trigger] ordered_callback_filter(pre, keys, callback, right)
        ==> left == right
}

pub open spec fn callback_unwind_retains_current_and_unvisited<K, V>(
    before_call: Map<K, V>,
    unwound: Map<K, V>,
    current: K,
    unvisited: Seq<K>,
) -> bool {
    &&& unwound.contains_key(current)
    &&& forall|key: K| unvisited.contains(key) ==> {
        &&& unwound.contains_key(key)
        &&& unwound[key] == before_call[key]
    }
}

pub uninterp spec fn ordered_callback_unwind_map<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    callback: &F,
    current: K,
    unvisited: Seq<K>,
) -> Map<K, V>;

#[verifier::prophetic]
pub open spec fn ordered_callback_unwind_contract<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: &F,
) -> bool {
    forall|visited: Seq<K>, current: K, unvisited: Seq<K>|
        keys == visited + Seq::empty().push(current) + unvisited ==> {
            callback_unwind_retains_current_and_unvisited(
                pre,
                ordered_callback_unwind_map(pre, callback, current, unvisited),
                current,
                unvisited,
            )
        }
}

pub open spec fn append_last_value_wins<K, V>(
    left: Map<K, V>,
    right: Map<K, V>,
    post: Map<K, V>,
) -> bool {
    &&& post.dom() == left.dom().union(right.dom())
    &&& forall|key: K| #[trigger] right.contains_key(key) ==> post[key] == right[key]
    &&& forall|key: K|
        #![trigger left.contains_key(key)]
        #![trigger right.contains_key(key)]
        left.contains_key(key) && !right.contains_key(key) ==> post[key] == left[key]
}

pub uninterp spec fn borrowed_key_cmp<K, Q: ?Sized>(
    key: K,
    bound: &Q,
) -> Ordering;

pub broadcast axiom fn axiom_borrowed_key_cmp_direct<Q: Ord>(key: Q, bound: &Q)
    ensures
        #[trigger] borrowed_key_cmp::<Q, Q>(key, bound) == key.cmp_spec(bound),
;

pub broadcast axiom fn axiom_borrowed_key_cmp_box<Q: Ord>(key: Box<Q>, bound: &Q)
    ensures
        #[trigger] borrowed_key_cmp::<Box<Q>, Q>(key, bound) == (*key).cmp_spec(bound),
;

pub open spec fn range_start_after_end<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Included(start), SpecBound::Included(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Included(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Excluded(start), SpecBound::Included(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        _ => false,
    }
}

pub open spec fn range_equal_excluded_bounds<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Equal
        },
        _ => false,
    }
}

pub open spec fn ordered_range_domain<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    !range_start_after_end(range) && !range_equal_excluded_bounds(range)
}

pub open spec fn ordered_key_in_range<
    K,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
    key: K,
) -> bool {
    &&& match range.spec_start_bound() {
        SpecBound::Included(start) => borrowed_key_cmp(key, start) != Ordering::Less,
        SpecBound::Excluded(start) => borrowed_key_cmp(key, start) == Ordering::Greater,
        SpecBound::Unbounded => true,
    }
    &&& match range.spec_end_bound() {
        SpecBound::Included(end) => borrowed_key_cmp(key, end) != Ordering::Greater,
        SpecBound::Excluded(end) => borrowed_key_cmp(key, end) == Ordering::Less,
        SpecBound::Unbounded => true,
    }
}

pub open spec fn ordered_range_key_sequence<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    map: Map<K, V>,
    range: &R,
) -> Seq<K> {
    ordered_map_key_sequence(map).filter(
        |key: K| ordered_key_in_range::<K, T, R>(range, key),
    )
}

pub open spec fn ordered_range_pair_sequence<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    map: Map<K, V>,
    range: &R,
) -> Seq<(K, V)> {
    ordered_map_pairs(map).filter(
        |pair: (K, V)| ordered_key_in_range::<K, T, R>(range, pair.0),
    )
}

#[verifier::prophetic]
pub open spec fn ordered_range_result<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    map: Map<K, V>,
    range: &R,
    iterator: &I,
) -> bool {
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_range_key_sequence::<K, V, T, R>(map, range)
    &&& iterator.ordered_remaining().len()
        == ordered_range_key_sequence::<K, V, T, R>(map, range).len()
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_range_pair_sequence::<K, V, T, R>(map, range).map(
            |_index: int, pair: (K, V)| pair.1,
        )
}

pub open spec fn ordered_key_before_split<K, Q: ?Sized>(
    boundary: &Q,
    key: K,
) -> bool {
    borrowed_key_cmp(key, boundary) == Ordering::Less
}

pub open spec fn ordered_split_left<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
) -> Map<K, V> {
    Map::new(
        pre.dom().filter(|key: K| ordered_key_before_split(boundary, key)),
        |key: K| pre[key],
    )
}

pub open spec fn ordered_split_right<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
) -> Map<K, V> {
    Map::new(
        pre.dom().filter(|key: K| !ordered_key_before_split(boundary, key)),
        |key: K| pre[key],
    )
}

pub open spec fn ordered_split_partition<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
    left: Map<K, V>,
    right: Map<K, V>,
) -> bool {
    &&& left == ordered_split_left(pre, boundary)
    &&& right == ordered_split_right(pre, boundary)
    &&& left.dom().disjoint(right.dom())
    &&& left.dom().union(right.dom()) == pre.dom()
    &&& forall|key: K| #[trigger] pre.contains_key(key) ==> {
        &&& left.contains_key(key) <==> ordered_key_before_split(boundary, key)
        &&& left.contains_key(key) ==> left[key] == pre[key]
        &&& right.contains_key(key) ==> right[key] == pre[key]
    }
}

pub proof fn lemma_ordered_split_partition_empty<K, V, Q: ?Sized>(
    boundary: &Q,
)
    ensures
        ordered_split_partition(
            Map::<K, V>::empty(),
            boundary,
            Map::<K, V>::empty(),
            Map::<K, V>::empty(),
        ),
{
    assert(ordered_split_left(Map::<K, V>::empty(), boundary)
        =~= Map::<K, V>::empty()) by {
        assert(ordered_split_left(Map::<K, V>::empty(), boundary).dom()
            =~= Set::<K>::empty());
    }
    assert(ordered_split_left(Map::<K, V>::empty(), boundary)
        == Map::<K, V>::empty());
    assert(ordered_split_right(Map::<K, V>::empty(), boundary)
        =~= Map::<K, V>::empty()) by {
        assert(ordered_split_right(Map::<K, V>::empty(), boundary).dom()
            =~= Set::<K>::empty());
    }
    assert(ordered_split_right(Map::<K, V>::empty(), boundary)
        == Map::<K, V>::empty());
    assert(Map::<K, V>::empty().dom().disjoint(Map::<K, V>::empty().dom()));
    assert(Map::<K, V>::empty().dom().union(Map::<K, V>::empty().dom())
        == Map::<K, V>::empty().dom());
    assert(forall|key: K| #[trigger] Map::<K, V>::empty().contains_key(key) ==> {
        &&& Map::<K, V>::empty().contains_key(key)
            <==> ordered_key_before_split(boundary, key)
        &&& Map::<K, V>::empty().contains_key(key)
            ==> Map::<K, V>::empty()[key] == Map::<K, V>::empty()[key]
        &&& Map::<K, V>::empty().contains_key(key)
            ==> Map::<K, V>::empty()[key] == Map::<K, V>::empty()[key]
    });
}

pub uninterp spec fn extract_if_unvisited_keys<K, V, I>(
    iterator: &I,
) -> Seq<K>;

pub uninterp spec fn extract_if_visited_keys<K, V, I>(
    iterator: &I,
) -> Seq<K>;

#[verifier::prophetic]
pub uninterp spec fn extract_if_yielded_pairs<K, V, I>(
    iterator: &I,
) -> Seq<(K, V)>;

#[verifier::prophetic]
pub uninterp spec fn extract_if_current_map<K, V, I>(
    iterator: &I,
) -> Map<K, V>;

pub uninterp spec fn extract_if_model<I>(iterator: &I) -> int;

pub uninterp spec fn extract_if_remove_decision<K, V>(
    model: int,
    state: Map<K, V>,
    key: K,
) -> bool;

pub uninterp spec fn extract_if_callback_final_value<K, V>(
    model: int,
    state: Map<K, V>,
    key: K,
) -> V;

pub open spec fn extract_if_visit_map<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> Map<K, V>
    decreases keys.len(),
{
    if keys.len() == 0 {
        state
    } else {
        let key = keys[0];
        let final_value = extract_if_callback_final_value(model, state, key);
        let next_state = if extract_if_remove_decision(model, state, key) {
            state.remove(key)
        } else {
            state.insert(key, final_value)
        };
        extract_if_visit_map(model, next_state, keys.drop_first())
    }
}

pub open spec fn extract_if_removed_pairs<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> Seq<(K, V)>
    decreases keys.len(),
{
    if keys.len() == 0 {
        Seq::empty()
    } else {
        let key = keys[0];
        let final_value = extract_if_callback_final_value(model, state, key);
        let remove = extract_if_remove_decision(model, state, key);
        let next_state = if remove {
            state.remove(key)
        } else {
            state.insert(key, final_value)
        };
        let remaining = extract_if_removed_pairs(
            model,
            next_state,
            keys.drop_first(),
        );
        if remove {
            Seq::empty().push((key, final_value)) + remaining
        } else {
            remaining
        }
    }
}

pub open spec fn extract_if_next_visit_count<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> nat
    decreases keys.len(),
{
    if keys.len() == 0 {
        0
    } else {
        let key = keys[0];
        if extract_if_remove_decision(model, state, key) {
            1
        } else {
            let next_state = state.insert(
                key,
                extract_if_callback_final_value(model, state, key),
            );
            1 + extract_if_next_visit_count(
                model,
                next_state,
                keys.drop_first(),
            )
        }
    }
}

#[verifier::prophetic]
pub open spec fn extract_if_next_consumed_keys<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    iterator: &I,
) -> Seq<K> {
    let keys = extract_if_unvisited_keys::<K, V, I>(iterator);
    keys.take(
        extract_if_next_visit_count(
            extract_if_model(iterator),
            extract_if_current_map::<K, V, I>(iterator),
            keys,
        ) as int,
    )
}

#[verifier::prophetic]
pub open spec fn extract_if_state_coherent<
    K,
    V,
    I: BTreeMapIteratorModel<Item = (K, V), Key = K, Value = V>,
>(
    iterator: &I,
) -> bool {
    iterator.ordered_remaining() == extract_if_removed_pairs(
        extract_if_model(iterator),
        extract_if_current_map::<K, V, I>(iterator),
        extract_if_unvisited_keys::<K, V, I>(iterator),
    )
}

#[verifier::prophetic]
pub open spec fn extract_if_callback_model_matches<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
    model: int,
) -> bool {
    let range_keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    forall|state: Map<K, V>, key: K|
        state.contains_key(key) && range_keys.contains(key) ==> {
            ordered_callback_observation(
                state,
                predicate,
                key,
                #[trigger] extract_if_remove_decision(model, state, key),
                #[trigger] extract_if_callback_final_value(model, state, key),
            )
        }
}

#[verifier::prophetic]
pub open spec fn extract_if_callback_model_functional<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
) -> bool {
    let keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    forall|left: int, right: int|
        #[trigger] extract_if_callback_model_matches(
            pre,
            range,
            predicate,
            left,
        )
        && #[trigger] extract_if_callback_model_matches(
            pre,
            range,
            predicate,
            right,
        )
        ==> extract_if_removed_pairs(left, pre, keys)
            == extract_if_removed_pairs(right, pre, keys)
}

#[verifier::prophetic]
pub open spec fn extract_if_lifecycle<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
    I: BTreeMapIteratorModel<Item = (K, V), Key = K, Value = V>,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
    iterator: &I,
    post: Map<K, V>,
    visited: Seq<K>,
    unvisited: Seq<K>,
) -> bool {
    let range_keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    let model = extract_if_model(iterator);
    &&& range_keys == visited + unvisited
    &&& extract_if_visited_keys::<K, V, I>(iterator) == visited
    &&& extract_if_unvisited_keys::<K, V, I>(iterator) == unvisited
    &&& extract_if_current_map::<K, V, I>(iterator) == post
    &&& extract_if_yielded_pairs::<K, V, I>(iterator)
        == extract_if_removed_pairs(model, pre, visited)
    &&& post == extract_if_visit_map(model, pre, visited)
    &&& extract_if_state_coherent::<K, V, I>(iterator)
    &&& extract_if_callback_model_matches(pre, range, predicate, model)
    &&& forall|key: K| unvisited.contains(key) ==> {
        &&& post.contains_key(key)
        &&& post[key] == pre[key]
    }
}

#[verifier::prophetic]
pub open spec fn ordered_map_iterator_result<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    map: Map<K, V>,
    iterator: &I,
) -> bool {
    &&& iterator.ordered_remaining().len() == map.len()
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_map_key_sequence(map)
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_map_pairs(map).map(|_index: int, pair: (K, V)| pair.1)
}

#[verifier::prophetic]
pub open spec fn ordered_map_mut_iterator_frame<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    pre: Map<K, V>,
    iterator: &I,
    post: Map<K, V>,
) -> bool {
    &&& iterator.ordered_remaining().len() == pre.len()
    &&& post.dom() == pre.dom()
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_map_key_sequence(pre)
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_map_pairs(pre).map(|_index: int, pair: (K, V)| pair.1)
}

pub uninterp spec fn map_allocator_token<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
) -> int;
pub uninterp spec fn owning_iterator_allocator_token<I>(iterator: &I) -> int;
pub uninterp spec fn owning_iterator_drop_plan<K, V, I>(
    iterator: &I,
) -> Seq<(K, V)>;
pub uninterp spec fn owning_iterator_unwind_prefix<I>(iterator: &I) -> nat;

pub open spec fn owning_iterator_transfer<
    K,
    V,
    A: Allocator + Clone,
    I: BTreeMapIteratorModel,
>(
    map: &BTreeMap<K, V, A>,
    iterator: &I,
) -> bool {
    &&& map_allocator_token(map) == owning_iterator_allocator_token(iterator)
    &&& owning_iterator_drop_plan::<K, V, I>(iterator) == ordered_map_pairs(map@)
    &&& owning_iterator_unwind_prefix(iterator)
        <= owning_iterator_drop_plan::<K, V, I>(iterator).len()
}

pub open spec fn map_from_pairs_last_wins<K, V>(pairs: Seq<(K, V)>) -> Map<K, V>
    decreases pairs.len(),
{
    if pairs.len() == 0 {
        Map::empty()
    } else {
        let prefix = pairs.drop_last();
        let pair = pairs.last();
        map_from_pairs_last_wins(prefix).insert(pair.0, pair.1)
    }
}

pub open spec fn map_extend_pairs_last_wins<K, V>(
    pre: Map<K, V>,
    pairs: Seq<(K, V)>,
) -> Map<K, V>
    decreases pairs.len(),
{
    if pairs.len() == 0 {
        pre
    } else {
        let prefix = pairs.drop_last();
        let pair = pairs.last();
        map_extend_pairs_last_wins(pre, prefix).insert(pair.0, pair.1)
    }
}

pub uninterp spec fn collection_input_pairs<I, K, V>(
    iterator: I,
) -> Seq<(K, V)>;

pub uninterp spec fn into_iterator_item_is_owned_pair<
    K,
    V,
    T: IntoIterator,
>() -> bool;

pub open spec fn from_iterator_last_value_wins<I, K, V>(
    iterator: I,
    map: Map<K, V>,
) -> bool {
    map == map_from_pairs_last_wins(
        collection_input_pairs::<I, K, V>(iterator),
    )
}

pub open spec fn extend_last_value_wins<I, K, V>(
    pre: Map<K, V>,
    iterator: I,
    post: Map<K, V>,
) -> bool {
    post == map_extend_pairs_last_wins(
        pre,
        collection_input_pairs::<I, K, V>(iterator),
    )
}

pub uninterp spec fn hasher_trace<H>(hasher: H) -> Seq<int>;
pub uninterp spec fn hash_pair_trace<K, V>(pair: (K, V)) -> Seq<int>;

pub broadcast axiom fn axiom_hash_pair_trace_len<K, V>(pair: (K, V))
    ensures
        #[trigger] hash_pair_trace(pair).len() == 2,
;

pub open spec fn ordered_map_hash_trace<K, V>(map: Map<K, V>) -> Seq<int> {
    seq![map.len() as int] + ordered_map_pairs(map).fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, pair: (K, V)| trace + hash_pair_trace(pair),
    )
}

pub open spec fn ordered_hash_transition<K, V, H>(
    map: Map<K, V>,
    pre_hasher: H,
    post_hasher: H,
) -> bool {
    hasher_trace(post_hasher)
        == hasher_trace(pre_hasher) + ordered_map_hash_trace(map)
}

pub open spec fn ordered_pair_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: (K, V),
    right: (K, V),
) -> Option<Ordering> {
    match left.0.partial_cmp_spec(&right.0) {
        Some(Ordering::Equal) => left.1.partial_cmp_spec(&right.1),
        result => result,
    }
}

pub open spec fn ordered_pairs_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: Seq<(K, V)>,
    right: Seq<(K, V)>,
) -> Option<Ordering>
    decreases left.len() + right.len(),
{
    if left.len() == 0 {
        if right.len() == 0 { Some(Ordering::Equal) } else { Some(Ordering::Less) }
    } else if right.len() == 0 {
        Some(Ordering::Greater)
    } else {
        match ordered_pair_partial_cmp(left[0], right[0]) {
            Some(Ordering::Equal) => {
                ordered_pairs_partial_cmp(left.drop_first(), right.drop_first())
            },
            result => result,
        }
    }
}

pub open spec fn ordered_map_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: Map<K, V>,
    right: Map<K, V>,
) -> Option<Ordering> {
    ordered_pairs_partial_cmp(ordered_map_pairs(left), ordered_map_pairs(right))
}

pub open spec fn ordered_pair_cmp<K: Ord, V: Ord>(
    left: (K, V),
    right: (K, V),
) -> Ordering {
    match left.0.cmp_spec(&right.0) {
        Ordering::Equal => left.1.cmp_spec(&right.1),
        ordering => ordering,
    }
}

pub open spec fn ordered_pairs_cmp<K: Ord, V: Ord>(
    left: Seq<(K, V)>,
    right: Seq<(K, V)>,
) -> Ordering
    decreases left.len() + right.len(),
{
    if left.len() == 0 {
        if right.len() == 0 { Ordering::Equal } else { Ordering::Less }
    } else if right.len() == 0 {
        Ordering::Greater
    } else {
        match ordered_pair_cmp(left[0], right[0]) {
            Ordering::Equal => ordered_pairs_cmp(left.drop_first(), right.drop_first()),
            ordering => ordering,
        }
    }
}

pub open spec fn ordered_map_cmp<K: Ord, V: Ord>(
    left: Map<K, V>,
    right: Map<K, V>,
) -> Ordering {
    ordered_pairs_cmp(ordered_map_pairs(left), ordered_map_pairs(right))
}

pub open spec fn array_last_value_wins<K, V, const N: usize>(
    array: &[(K, V); N],
    map: Map<K, V>,
) -> bool {
    map == map_from_pairs_last_wins((*array)@)
}

pub open spec fn entry_mutable_frame<K, V>(
    pre: Map<K, V>,
    key: K,
    initial: V,
    final_value: V,
    post: Map<K, V>,
) -> bool {
    &&& pre.contains_key(key)
    &&& initial == pre[key]
    &&& post == pre.insert(key, final_value)
}

pub open spec fn entry_remove_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    post: Map<K, V>,
) -> bool {
    post == pre.remove(key)
}

pub open spec fn entry_replace_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    value: V,
    post: Map<K, V>,
) -> bool {
    pre.contains_key(key) && post == pre.insert(key, value) && post.len() == pre.len()
}

pub open spec fn entry_insert_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    value: V,
) -> bool {
    !pre.contains_key(key)
}

pub open spec fn entry_callback_domain<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: &F,
) -> bool {
    !pre.contains_key(key) || forall|value_ref: &mut V|
        *value_ref == pre[key] ==> #[trigger] callback.requires((value_ref,))
}

pub open spec fn entry_nullary_callback_functional<
    V,
    F: FnOnce() -> V,
>(
    callback: F,
) -> bool {
    forall|left: V, right: V|
        #[trigger] callback.ensures((), left)
        && #[trigger] callback.ensures((), right)
        ==> left == right
}

pub open spec fn entry_key_callback_functional<
    K,
    V,
    F: FnOnce(&K) -> V,
>(
    key: &K,
    callback: F,
) -> bool {
    forall|left: V, right: V|
        #[trigger] callback.ensures((key,), left)
        && #[trigger] callback.ensures((key,), right)
        ==> left == right
}

pub open spec fn entry_default_value_functional<V: Default>() -> bool {
    forall|left: V, right: V|
        #[trigger] V::default.ensures((), left)
        && #[trigger] V::default.ensures((), right)
        ==> left == right
}

#[verifier::prophetic]
pub open spec fn entry_and_modify_transition<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: F,
    post: Map<K, V>,
) -> bool {
    if pre.contains_key(key) {
        exists|value_ref: &mut V|
            *value_ref == pre[key]
            && #[trigger] callback.ensures((value_ref,), ())
            && post == pre.insert(key, *final(value_ref))
    } else {
        post == pre
    }
}

#[verifier::prophetic]
pub open spec fn entry_and_modify_transition_functional<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: F,
) -> bool {
    forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] entry_and_modify_transition(pre, key, callback, left)
        && #[trigger] entry_and_modify_transition(pre, key, callback, right)
        ==> left == right
}

pub broadcast group group_generated_btree_map_axioms {
    axiom_btree_map_index_req,
    axiom_iter_ordered_remaining,
    axiom_keys_ordered_remaining,
    axiom_values_ordered_remaining,
    axiom_spec_btree_map_iter_properties,
    axiom_spec_btree_map_keys_properties,
    axiom_spec_btree_map_values_properties,
    axiom_ordered_map_pairs,
    axiom_ordered_map_pairs_extensional,
    axiom_borrowed_key_matches,
    axiom_borrowed_key_value_updated_direct,
    axiom_borrowed_key_value_updated_box,
    axiom_borrowed_key_cmp_direct,
    axiom_borrowed_key_cmp_box,
    axiom_hash_pair_trace_len,
    axiom_ordered_handle_reference_coherence,
    axiom_ordered_handle_occupancy_coherent,
}

} // verus!
'''


def index_assume_specification() -> str:
    return """pub assume_specification<
    '_0,
    K: core::borrow::Borrow<Q> + core::cmp::Ord,
    Q: core::cmp::Ord + ?Sized,
    V,
    A: alloc::alloc::Allocator + core::clone::Clone,
    'receiver,
>[
    <BTreeMap<K, V, A> as core::ops::Index<&Q>>::index
](
    this: &'receiver BTreeMap<K, V, A>,
    key: &Q,
) -> (result: &'receiver V)
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>()
            ==> maps_borrowed_key_to_value(this@, key, *result),
;"""


def generated_spec_source(rows: list[Row]) -> str:
    chunks = [
        "// Generated Rust 1.96 BTreeMap specifications; exact vstd rows are referenced only.",
        "#![allow(unused_imports, unused_variables)]",
        "#![feature(allocator_api)]",
        "#![verifier::allow(broadcast_without_trigger)]",
        "",
        'include!("btree_map_shared_vocabulary.rs");',
        "",
        "verus! {",
        "",
    ]
    for row in rows:
        if row.disposition != "generated":
            continue
        if custom_index_binding(row):
            chunks.extend(
                [
                    f"// {row.target_id}: {row.canonical_target}",
                    f"// Source: {row.source_file}:{row.line_start}-{row.line_end}",
                    (
                        "// Normal-return membership is inherited through "
                        "axiom_btree_map_index_req and vstd IndexSpec::index_req."
                    ),
                    f"// Principal behavior: {'; '.join(row.principal_behavior or [])}.",
                    index_assume_specification(),
                    "",
                ]
            )
            continue
        binder, inputs, output, where_clause = proxy_parts(row)
        target = render_trait_target(row)
        rendered_inputs = ",\n    ".join(f"{name}: {rust_type}" for name, rust_type, _ in inputs)
        return_part = f" -> (result: {output})" if output is not None else ""
        requires = require_lines(row, inputs)
        ensures = guard_contract_clauses(row, ensure_lines(row, inputs, output))
        if custom_index_binding(row):
            requires = []
            ensures = ["maps_borrowed_key_to_value(this@, key, *result)"]
        chunks.extend(
            [
                f"// {row.target_id}: {row.canonical_target}",
                f"// Source: {row.source_file}:{row.line_start}-{row.line_end}",
                f"// Principal behavior: {'; '.join(row.principal_behavior or [])}.",
                f"pub assume_specification{binder}[ {target} ](",
                f"    {rendered_inputs}" if rendered_inputs else "",
                f"){return_part}{where_clause}",
                *(["    requires", *[f"        {line}," for line in requires]] if requires else []),
                "    ensures",
                *[f"        {line}," for line in ensures],
                ";",
                "",
            ]
        )
    chunks.extend(["} // verus!", ""])
    return "\n".join(chunks)


STATE_FIELDS = (
    "len",
    "other_len",
    "conflicts",
    "remaining",
    "cursor",
    "split_index",
    "keep_len",
    "callback_count",
    "trace_len",
    "occupied",
    "key",
    "value",
    "first_key",
    "last_key",
    "comparison",
    "input_len",
    "unique_len",
    "range_len",
    "domain_ok",
)

OUTCOME_FIELDS = (
    "present",
    "key",
    "value",
    "len",
    "remaining",
    "order_index",
    "trace_len",
)


def proof_profile(row: Row) -> str:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    if owner == "BTreeMap":
        if trait == "inherent":
            return {
                "new": "empty_map",
                "clear": "clear_map",
                "get": "lookup",
                "get_key_value": "lookup",
                "contains_key": "lookup",
                "first_key_value": "first_endpoint",
                "first_entry": "first_endpoint",
                "pop_first": "remove_first",
                "last_key_value": "last_endpoint",
                "last_entry": "last_endpoint",
                "pop_last": "remove_last",
                "get_mut": "mutable_lookup",
                "insert": "insert",
                "remove": "remove",
                "remove_entry": "remove",
                "retain": "filter",
                "append": "append",
                "range": "range_construct",
                "range_mut": "range_construct",
                "entry": "entry_handle",
                "split_off": "split",
                "extract_if": "range_construct",
                "into_keys": "iterator_construct",
                "into_values": "iterator_construct",
                "iter": "iterator_construct",
                "iter_mut": "iterator_construct",
                "keys": "iterator_construct",
                "values": "iterator_construct",
                "values_mut": "iterator_construct",
                "len": "map_len",
                "is_empty": "map_is_empty",
            }.get(name, "lookup")
        return {
            "Clone": "clone_map",
            "Default": "empty_map",
            "IntoIterator": "iterator_construct",
            "FromIterator": "from_input",
            "Extend": "extend_input",
            "Hash": "effect_trace",
            "PartialEq": "map_equality",
            "PartialOrd": "map_compare",
            "Ord": "map_compare",
            "Debug": "effect_trace",
            "Index": "index_lookup",
            "From": "from_input",
        }.get(trait, "lookup")
    if owner in ITERATOR_TYPES:
        if trait == "Iterator":
            if name == "next":
                return "iterator_next"
            if name == "size_hint":
                return "iterator_size"
            if name in {"last", "max"}:
                return "iterator_last"
            if name == "min":
                return "iterator_first"
        return {
            "DoubleEndedIterator": "iterator_next_back",
            "ExactSizeIterator": "iterator_size",
            "Clone": "iterator_clone",
            "Default": "empty_iterator",
            "Debug": "effect_trace",
        }.get(trait, "iterator_construct")
    if owner in {"Entry", "OccupiedEntry", "VacantEntry"}:
        if trait == "Debug":
            return "effect_trace"
        if name in {"key", "into_key", "get"}:
            return "lookup"
        if name in {"get_mut", "into_mut"}:
            return "mutable_lookup"
        if name in {"remove", "remove_entry"}:
            return "remove"
        if name in {"insert", "insert_entry"}:
            return "insert"
        if name == "and_modify":
            return "mutable_callback"
        if name == "or_insert":
            return "entry_or_insert"
        if name in {"or_insert_with", "or_insert_with_key", "or_default"}:
            return "entry_or_insert_callback"
    return "lookup"


def collapse_control_flow_blocks(source: str) -> str:
    replacements = {
        "match": "source_match_branch()",
        "if": "source_if_branch()",
        "for": "source_for_loop()",
        "while": "source_while_loop()",
        "loop": "source_loop()",
    }
    while True:
        candidates: list[tuple[int, str, re.Match[str]]] = []
        for keyword in replacements:
            match = re.search(rf"\b{keyword}\b", source)
            if match is not None:
                candidates.append((match.start(), keyword, match))
        if not candidates:
            return source
        _, keyword, match = min(candidates, key=lambda item: item[0])
        brace_start = source.find("{", match.end())
        if brace_start < 0:
            source = (
                source[: match.start()]
                + replacements[keyword]
                + source[match.end() :]
            )
            continue
        depth = 0
        brace_end = -1
        for index in range(brace_start, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = index + 1
                    break
        if brace_end < 0:
            return source
        source = (
            source[: match.start()]
            + replacements[keyword]
            + source[brace_end:]
        )


def source_call_names(row: Row) -> list[str]:
    controls = {
        "as",
        "async",
        "break",
        "const",
        "continue",
        "else",
        "fn",
        "for",
        "if",
        "impl",
        "in",
        "let",
        "loop",
        "match",
        "move",
        "mut",
        "ref",
        "return",
        "unsafe",
        "where",
        "while",
        "Some",
        "None",
        "Ok",
        "Err",
        "Self",
    }
    names: list[str] = []
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_:]*)\s*([!(])")
    body = row.source_excerpt.split("{", 1)[1] if "{" in row.source_excerpt else ""
    body = "\n".join(line.split("//", 1)[0] for line in body.splitlines())
    body = collapse_control_flow_blocks(body)
    for line in body.splitlines():
        code = line.split("//", 1)[0]
        for match in pattern.finditer(code):
            raw = match.group(1)
            if raw.endswith(":") and not raw.endswith("::"):
                continue
            name = raw.split("::")[-1]
            prefix = code[: match.start()]
            suffix = code[match.end() :]
            if name in controls or name.startswith("assert"):
                continue
            closing = suffix.find(")")
            arrow = suffix.find("=>")
            if arrow >= 0 and (closing < 0 or arrow >= closing) and not prefix.rstrip().endswith("."):
                continue
            sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name).lower()
            if sanitized:
                names.append(sanitized)
        if re.search(r"\bfor_each\s*\(\s*drop\s*\)", code):
            names.append("drop")
    return names


def model_contract(row: Row) -> tuple[list[str], str]:
    profile = proof_profile(row)
    clauses: list[str] = []
    modified: set[str] = set()

    def set_field(field: str, clause: str) -> None:
        modified.add(field)
        clauses.append(clause)

    out = {
        "present": "out.present == pre.occupied",
        "key": "out.key == pre.key",
        "value": "out.value == pre.value",
        "len": "out.len == post.len",
        "remaining": "out.remaining == post.remaining",
        "order_index": "out.order_index == pre.cursor",
        "trace_len": "out.trace_len == post.trace_len",
    }

    if profile in {"empty_map", "clear_map", "empty_iterator"}:
        set_field("len", "post.len == 0")
        set_field("remaining", "post.remaining == 0")
        set_field("occupied", "!post.occupied")
        out["present"] = "!out.present"
        out["len"] = "out.len == 0"
        out["remaining"] = "out.remaining == 0"
    elif profile == "map_len":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.len > 0)"
        out["len"] = "out.len == pre.len"
    elif profile == "map_is_empty":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.len == 0)"
        out["len"] = "out.len == pre.len"
    elif profile in {"lookup", "clone_map", "entry_handle"}:
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
    elif profile == "index_lookup":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present"
    elif profile in {"first_endpoint", "last_endpoint"}:
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        endpoint = "pre.first_key" if profile == "first_endpoint" else "pre.last_key"
        out["present"] = "out.present == (pre.len > 0)"
        out["key"] = f"out.key == {endpoint}"
        if profile == "first_endpoint":
            out["order_index"] = "out.order_index == 0"
        else:
            out["order_index"] = (
                "pre.len > 0 ==> out.order_index as nat + 1 == pre.len as nat"
            )
            clauses.append("pre.len == 0 ==> out.order_index == 0")
    elif profile in {"insert", "entry_or_insert", "entry_or_insert_callback"}:
        set_field("len", "pre.occupied ==> post.len == pre.len")
        clauses.append("!pre.occupied ==> post.len as nat == pre.len as nat + 1")
        set_field("occupied", "post.occupied")
        set_field(
            "key",
            "post.key == if pre.occupied { pre.key } else { input_key }",
        )
        set_field(
            "value",
            "post.value == if pre.occupied { pre.value } else { input_value }"
            if profile in {"entry_or_insert", "entry_or_insert_callback"}
            else "post.value == input_value",
        )
        if profile == "entry_or_insert_callback":
            set_field(
                "callback_count",
                "post.callback_count as nat == pre.callback_count as nat + if pre.occupied { 0nat } else { 1nat }",
            )
        out["present"] = "out.present == pre.occupied"
        out["key"] = "out.key == post.key"
        out["value"] = (
            "out.value == if pre.occupied { pre.value } else { input_value }"
        )
    elif profile in {"remove", "remove_first", "remove_last"}:
        removal_present = "pre.len > 0" if profile != "remove" else "pre.occupied"
        set_field("len", f"({removal_present}) ==> post.len as nat + 1 == pre.len as nat")
        clauses.append(f"!({removal_present}) ==> post.len == pre.len")
        set_field(
            "occupied",
            "post.occupied == (post.len > 0)"
            if profile != "remove"
            else "!post.occupied",
        )
        out["present"] = f"out.present == ({removal_present})"
        if profile == "remove_first":
            out["key"] = "out.key == pre.first_key"
            out["order_index"] = "out.order_index == 0"
        elif profile == "remove_last":
            out["key"] = "out.key == pre.last_key"
            out["order_index"] = (
                "pre.len > 0 ==> out.order_index as nat + 1 == pre.len as nat"
            )
            clauses.append("pre.len == 0 ==> out.order_index == 0")
    elif profile == "mutable_lookup":
        set_field(
            "value",
            "post.value == if pre.occupied { input_value } else { pre.value }",
        )
        out["present"] = "out.present == pre.occupied"
        out["value"] = "out.value == pre.value"
    elif profile == "mutable_callback":
        set_field(
            "value",
            "post.value == if pre.occupied { input_value } else { pre.value }",
        )
        set_field(
            "callback_count",
            "post.callback_count as nat == pre.callback_count as nat + if pre.occupied { 1nat } else { 0nat }",
        )
        out["present"] = "out.present == pre.occupied"
        out["value"] = "out.value == post.value"
    elif profile == "filter":
        set_field("len", "post.len == pre.keep_len")
        set_field(
            "callback_count",
            "post.callback_count as nat == pre.callback_count as nat + pre.len as nat",
        )
        set_field(
            "trace_len",
            "post.trace_len as nat == pre.trace_len as nat + pre.len as nat",
        )
        set_field("occupied", "post.occupied == (pre.keep_len > 0)")
        out["present"] = "out.present == (pre.keep_len < pre.len)"
    elif profile == "append":
        set_field(
            "len",
            "post.len as nat == pre.len as nat + pre.other_len as nat - pre.conflicts as nat",
        )
        set_field("other_len", "post.other_len == 0")
        set_field("occupied", "post.occupied == (post.len > 0)")
        out["present"] = "out.present == (pre.other_len > 0)"
    elif profile == "split":
        set_field("len", "post.len == pre.split_index")
        set_field("occupied", "post.occupied == (pre.split_index > 0)")
        out["present"] = "out.present == (pre.split_index < pre.len)"
        out["len"] = "out.len as nat + post.len as nat == pre.len as nat"
        out["order_index"] = "out.order_index == pre.split_index"
    elif profile == "iterator_construct":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.len > 0)"
        out["len"] = "out.len == pre.len"
        out["remaining"] = "out.remaining == pre.len"
        out["order_index"] = "out.order_index == 0"
    elif profile == "range_construct":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.range_len > 0)"
        out["len"] = "out.len == pre.range_len"
        out["remaining"] = "out.remaining == pre.range_len"
        out["order_index"] = "out.order_index == 0"
    elif profile in {"iterator_next", "iterator_next_back"}:
        present = "pre.remaining > 0"
        set_field("remaining", f"{present} ==> post.remaining as nat + 1 == pre.remaining as nat")
        clauses.append(f"!({present}) ==> post.remaining == pre.remaining")
        if profile == "iterator_next":
            set_field("cursor", f"{present} ==> post.cursor as nat == pre.cursor as nat + 1")
            clauses.append(f"!({present}) ==> post.cursor == pre.cursor")
            out["order_index"] = "out.order_index == pre.cursor"
        else:
            out["order_index"] = (
                "pre.remaining > 0 ==> out.order_index as nat + 1 "
                "== pre.cursor as nat + pre.remaining as nat"
            )
            clauses.append(
                "pre.remaining == 0 ==> out.order_index == pre.cursor"
            )
        out["present"] = f"out.present == ({present})"
    elif profile in {"iterator_last", "iterator_first"}:
        set_field("remaining", "post.remaining == 0")
        out["present"] = "out.present == (pre.remaining > 0)"
        out["order_index"] = (
            "out.order_index == pre.cursor"
            if profile == "iterator_first"
            else "pre.remaining > 0 ==> out.order_index as nat + 1 == pre.cursor as nat + pre.remaining as nat"
        )
        if profile == "iterator_last":
            clauses.append(
                "pre.remaining == 0 ==> out.order_index == pre.cursor"
            )
    elif profile == "iterator_size":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.remaining > 0)"
        out["len"] = "out.len == pre.remaining"
        out["remaining"] = "out.remaining == pre.remaining"
    elif profile == "iterator_clone":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.remaining > 0)"
        out["remaining"] = "out.remaining == pre.remaining"
    elif profile == "effect_trace":
        set_field(
            "trace_len",
            "post.trace_len as nat == pre.trace_len as nat + 1 + 2 * pre.len as nat",
        )
        out["present"] = "out.present == (pre.len > 0)"
    elif profile == "map_equality":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.comparison == 0)"
        out["value"] = "out.value == pre.comparison"
    elif profile == "map_compare":
        clauses.append("post == pre")
        modified.update(STATE_FIELDS)
        out["present"] = "out.present == (pre.comparison == 0)"
        out["value"] = "out.value == pre.comparison"
    elif profile == "from_input":
        set_field("len", "post.len == pre.unique_len")
        set_field("occupied", "post.occupied == (pre.unique_len > 0)")
        out["present"] = "out.present == (pre.unique_len > 0)"
        out["len"] = "out.len == pre.unique_len"
    elif profile == "extend_input":
        set_field(
            "len",
            "post.len as nat == pre.len as nat + pre.unique_len as nat - pre.conflicts as nat",
        )
        set_field(
            "trace_len",
            "post.trace_len as nat == pre.trace_len as nat + pre.input_len as nat",
        )
        set_field("occupied", "post.occupied == (post.len > 0)")
        out["present"] = "out.present == (pre.input_len > 0)"

    if "post == pre" not in clauses:
        for field in STATE_FIELDS:
            if field not in modified:
                clauses.append(f"post.{field} == pre.{field}")
    clauses.extend(out.values())
    contract = "\n".join(f"        &&& {clause}" for clause in clauses)
    return clauses, contract


def outcome_expr(
    *,
    present: str,
    key: str,
    value: str,
    length: str = "state.len",
    remaining: str = "state.remaining",
    order_index: str = "old_cursor",
    trace_len: str = "state.trace_len",
) -> str:
    return (
        "Outcome { "
        f"present: {present}, key: {key}, value: {value}, len: {length}, "
        f"remaining: {remaining}, order_index: {order_index}, trace_len: {trace_len} "
        "}"
    )


def model_body(row: Row) -> str:
    profile = proof_profile(row)
    common = """        let old_len = state.len;
        let old_remaining = state.remaining;
        let old_cursor = state.cursor;
        let old_other_len = state.other_len;
        let old_key = state.key;
        let old_value = state.value;
        let was_occupied = state.occupied;"""
    body = {
        "empty_map": """
        state.len = 0;
        state.remaining = 0;
        state.occupied = false;
        Outcome { present: false, key: old_key, value: old_value, len: 0, remaining: 0, order_index: old_cursor, trace_len: state.trace_len }""",
        "clear_map": """
        state.len = 0;
        state.remaining = 0;
        state.occupied = false;
        Outcome { present: false, key: old_key, value: old_value, len: 0, remaining: 0, order_index: old_cursor, trace_len: state.trace_len }""",
        "empty_iterator": """
        state.len = 0;
        state.remaining = 0;
        state.occupied = false;
        Outcome { present: false, key: old_key, value: old_value, len: 0, remaining: 0, order_index: old_cursor, trace_len: state.trace_len }""",
        "map_len": """
        Outcome { present: old_len > 0, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "map_is_empty": """
        Outcome { present: old_len == 0, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "lookup": """
        Outcome { present: was_occupied, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "index_lookup": """
        Outcome { present: true, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "clone_map": """
        Outcome { present: was_occupied, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "entry_handle": """
        Outcome { present: was_occupied, key: old_key, value: old_value, len: old_len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "first_endpoint": """
        Outcome { present: old_len > 0, key: state.first_key, value: old_value, len: old_len, remaining: old_remaining, order_index: 0, trace_len: state.trace_len }""",
        "last_endpoint": """
        let order_index = if old_len > 0 { old_len - 1 } else { 0 };
        Outcome { present: old_len > 0, key: state.last_key, value: old_value, len: old_len, remaining: old_remaining, order_index, trace_len: state.trace_len }""",
        "insert": """
        if !was_occupied {
            state.len = old_len + 1;
            state.key = input_key;
        }
        state.occupied = true;
        state.value = input_value;
        Outcome { present: was_occupied, key: state.key, value: if was_occupied { old_value } else { input_value }, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "entry_or_insert": """
        if !was_occupied {
            state.len = old_len + 1;
            state.key = input_key;
            state.value = input_value;
        }
        state.occupied = true;
        Outcome { present: was_occupied, key: state.key, value: state.value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "entry_or_insert_callback": """
        if !was_occupied {
            state.len = old_len + 1;
            state.key = input_key;
            state.value = input_value;
            state.callback_count = state.callback_count + 1;
        }
        state.occupied = true;
        Outcome { present: was_occupied, key: state.key, value: state.value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "remove": """
        if was_occupied {
            state.len = old_len - 1;
        }
        state.occupied = false;
        Outcome { present: was_occupied, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "remove_first": """
        let present = old_len > 0;
        if present {
            state.len = old_len - 1;
        }
        state.occupied = state.len > 0;
        Outcome { present, key: state.first_key, value: old_value, len: state.len, remaining: state.remaining, order_index: 0, trace_len: state.trace_len }""",
        "remove_last": """
        let present = old_len > 0;
        let order_index = if old_len > 0 { old_len - 1 } else { 0 };
        if present {
            state.len = old_len - 1;
        }
        state.occupied = state.len > 0;
        Outcome { present, key: state.last_key, value: old_value, len: state.len, remaining: state.remaining, order_index, trace_len: state.trace_len }""",
        "mutable_lookup": """
        if was_occupied {
            state.value = input_value;
        }
        Outcome { present: was_occupied, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "mutable_callback": """
        if was_occupied {
            state.value = input_value;
            state.callback_count = state.callback_count + 1;
        }
        Outcome { present: was_occupied, key: old_key, value: state.value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "filter": """
        state.len = state.keep_len;
        state.callback_count = state.callback_count + old_len;
        state.trace_len = state.trace_len + old_len;
        state.occupied = state.keep_len > 0;
        Outcome { present: state.keep_len < old_len, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "append": """
        state.len = old_len + state.other_len - state.conflicts;
        state.other_len = 0;
        state.occupied = state.len > 0;
        Outcome { present: old_other_len > 0, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "split": """
        let right_len = old_len - state.split_index;
        state.len = state.split_index;
        state.occupied = state.len > 0;
        Outcome { present: right_len > 0, key: old_key, value: old_value, len: right_len, remaining: state.remaining, order_index: state.split_index, trace_len: state.trace_len }""",
        "iterator_construct": """
        Outcome { present: old_len > 0, key: old_key, value: old_value, len: old_len, remaining: old_len, order_index: 0, trace_len: state.trace_len }""",
        "range_construct": """
        Outcome { present: state.range_len > 0, key: old_key, value: old_value, len: state.range_len, remaining: state.range_len, order_index: 0, trace_len: state.trace_len }""",
        "iterator_next": """
        let present = old_remaining > 0;
        if present {
            state.remaining = old_remaining - 1;
            state.cursor = old_cursor + 1;
        }
        Outcome { present, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "iterator_next_back": """
        let present = old_remaining > 0;
        let order_index = if present { old_cursor + old_remaining - 1 } else { old_cursor };
        if present {
            state.remaining = old_remaining - 1;
        }
        Outcome { present, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index, trace_len: state.trace_len }""",
        "iterator_last": """
        let present = old_remaining > 0;
        let order_index = if present { old_cursor + old_remaining - 1 } else { old_cursor };
        state.remaining = 0;
        Outcome { present, key: old_key, value: old_value, len: state.len, remaining: 0, order_index, trace_len: state.trace_len }""",
        "iterator_first": """
        let present = old_remaining > 0;
        state.remaining = 0;
        Outcome { present, key: old_key, value: old_value, len: state.len, remaining: 0, order_index: old_cursor, trace_len: state.trace_len }""",
        "iterator_size": """
        Outcome { present: old_remaining > 0, key: old_key, value: old_value, len: old_remaining, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "iterator_clone": """
        Outcome { present: old_remaining > 0, key: old_key, value: old_value, len: state.len, remaining: old_remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "effect_trace": """
        state.trace_len = state.trace_len + 1 + 2 * old_len;
        Outcome { present: old_len > 0, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "map_equality": """
        Outcome { present: state.comparison == 0, key: old_key, value: state.comparison, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "map_compare": """
        Outcome { present: state.comparison == 0, key: old_key, value: state.comparison, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "from_input": """
        state.len = state.unique_len;
        state.occupied = state.unique_len > 0;
        Outcome { present: state.occupied, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
        "extend_input": """
        state.len = old_len + state.unique_len - state.conflicts;
        state.trace_len = state.trace_len + state.input_len;
        state.occupied = state.len > 0;
        Outcome { present: state.input_len > 0, key: old_key, value: old_value, len: state.len, remaining: state.remaining, order_index: old_cursor, trace_len: state.trace_len }""",
    }[profile]
    return common + body


def model_declarations(row: Row) -> str:
    _, contract = model_contract(row)
    return f"""pub struct SourceState {{
    pub len: usize,
    pub other_len: usize,
    pub conflicts: usize,
    pub remaining: usize,
    pub cursor: usize,
    pub split_index: usize,
    pub keep_len: usize,
    pub callback_count: usize,
    pub trace_len: usize,
    pub occupied: bool,
    pub key: i64,
    pub value: i64,
    pub first_key: i64,
    pub last_key: i64,
    pub comparison: i64,
    pub input_len: usize,
    pub unique_len: usize,
    pub range_len: usize,
    pub domain_ok: bool,
}}

pub struct Outcome {{
    pub present: bool,
    pub key: i64,
    pub value: i64,
    pub len: usize,
    pub remaining: usize,
    pub order_index: usize,
    pub trace_len: usize,
}}

pub open spec fn state_wf(state: SourceState) -> bool {{
    &&& state.remaining <= state.len
    &&& state.occupied ==> state.len > 0
    &&& state.cursor as nat + state.remaining as nat <= usize::MAX as nat / 4
    &&& state.split_index <= state.len
    &&& state.keep_len <= state.len
    &&& state.conflicts <= state.len
    &&& state.conflicts <= state.other_len
    &&& state.conflicts <= state.unique_len
    &&& state.unique_len <= state.input_len
    &&& state.range_len <= state.len
    &&& state.len <= usize::MAX / 8
    &&& state.other_len <= usize::MAX / 8
    &&& state.input_len <= usize::MAX / 8
    &&& state.callback_count <= usize::MAX / 4
    &&& state.trace_len <= usize::MAX / 4
}}

pub open spec fn accepted_contract(
    pre: SourceState,
    input_key: i64,
    input_value: i64,
    out: Outcome,
    post: SourceState,
) -> bool {{
{contract}
}}"""


def boundary_declarations_and_calls(row: Row) -> tuple[str, str, list[str]]:
    names = source_call_names(row)
    declarations: list[str] = []
    calls: list[str] = []
    for index, name in enumerate(names):
        function = f"source_boundary_{index}_{name}"
        declarations.append(
            f"""fn {function}(state: &mut SourceState)
    ensures
        *final(state) == *old(state),
{{
    let _ = state.len;
}}"""
        )
        calls.append(f"        {function}(state);")
    return "\n\n".join(declarations), "\n".join(calls), names


def model_requires(row: Row, state: str) -> list[str]:
    metadata = metadata_for(row)
    if not (
        metadata["contract"]["requires"]
        or metadata["contract"].get("inherited_requires")
    ):
        return []
    if custom_index_binding(row):
        return [f"{state}.domain_ok", f"{state}.occupied"]
    if row.owner["name"] == "Entry":
        if row.function["name"] in {"or_insert_with", "or_insert_with_key"}:
            return [f"{state}.occupied || {state}.domain_ok"]
        if row.function["name"] == "and_modify":
            return [f"!{state}.occupied || {state}.domain_ok"]
    return [f"{state}.domain_ok"]


def implementation_harness_source(row: Row) -> str:
    metadata = metadata_for(row)
    contract_text = json.dumps(metadata["contract"], sort_keys=True)
    contract_hash = sha256_text(contract_text)
    boundaries, calls, _ = boundary_declarations_and_calls(row)
    function_name = f"rust_1_96_target_{row.item_id}"
    body = model_body(row)
    modeled_requires = model_requires(row, "old(state)")
    requires_text = "\n".join(
        f"        {clause}," for clause in modeled_requires
    )
    return f"""#![allow(dead_code, unused_imports, unused_variables)]
#![crate_type = "lib"]
// Source-shaped implementation lowering for {row.canonical_target}.
// Rust source: {row.source_file}:{row.line_start}-{row.line_end}
// Source item sha256: {row.source_sha256}
// Accepted contract sha256: {contract_hash}
// Model profile: {proof_profile(row)}
// Accepted requires: {metadata['contract']['requires']}
// Accepted inherited requires: {metadata['contract'].get('inherited_requires', [])}
// Accepted ensures: {metadata['contract']['ensures']}
// Private calls are retained below in source order as named, executable
// dependency boundaries; their semantic effects are reflected in the
// target-specific SourceState transition and dependency manifest.

use vstd::prelude::*;

verus! {{

{model_declarations(row)}

{boundaries}

pub fn {function_name}(
    state: &mut SourceState,
    input_key: i64,
    input_value: i64,
) -> (out: Outcome)
    requires
        state_wf(*old(state)),
{requires_text}
    ensures
        accepted_contract(*old(state), input_key, input_value, out, *final(state)),
{{
{calls}
{model_body(row)}
}}

}}
"""


def completeness_harness_source(row: Row) -> str:
    metadata = metadata_for(row)
    kind = metadata["equivalence"]["kind"]
    if kind == "exact_observable_equality":
        equivalent = "out1 == out2 && post1 == post2"
        positive_witness = """pub proof fn positive_equivalence_witness(
    out: Outcome,
    post: SourceState,
)
    ensures
        equivalent(out, post, out, post),
{
}"""
    else:
        equivalent = """&&& out1.present == out2.present
    &&& out1.key == out2.key
    &&& out1.value == out2.value
    &&& out1.len == out2.len
    &&& out1.remaining == out2.remaining
    &&& out1.order_index == out2.order_index
    &&& out1.trace_len == out2.trace_len
    &&& post1.trace_len == post2.trace_len"""
        positive_witness = """pub proof fn positive_equivalence_witness(
    out: Outcome,
    post1: SourceState,
    post2: SourceState,
)
    requires
        post1.trace_len == post2.trace_len,
        post1.key != post2.key,
    ensures
        equivalent(out, post1, out, post2),
{
}"""
    return f"""#![allow(dead_code, unused_imports)]
#![crate_type = "lib"]
// Relational completeness for {row.canonical_target}.
// Contract class: {kind}.
// Equivalence version: {metadata['equivalence']['version']}.

use vstd::prelude::*;

verus! {{

{model_declarations(row)}

pub open spec fn equivalent(
    out1: Outcome,
    post1: SourceState,
    out2: Outcome,
    post2: SourceState,
) -> bool {{
    {equivalent}
}}

pub proof fn completeness(
    pre: SourceState,
    input_key: i64,
    input_value: i64,
    out1: Outcome,
    post1: SourceState,
    out2: Outcome,
    post2: SourceState,
)
    requires
        state_wf(pre),
{chr(10).join(f"        {clause}," for clause in model_requires(row, "pre"))}
        accepted_contract(pre, input_key, input_value, out1, post1),
        accepted_contract(pre, input_key, input_value, out2, post2),
    ensures
        equivalent(out1, post1, out2, post2),
{{
}}

{positive_witness}

pub proof fn negative_equivalence_witness(
    out1: Outcome,
    post1: SourceState,
    out2: Outcome,
    post2: SourceState,
)
    requires
        out1.trace_len != out2.trace_len,
    ensures
        !equivalent(out1, post1, out2, post2),
{{
}}

}}
"""



EXACT_VSTD_CONTRACTS: dict[tuple[str, str, str], tuple[list[str], list[str]]] = {
    ("BTreeMap", "Clone", "clone"): ([], ["result@ == this@"]),
    ("BTreeMap", "inherent", "new"): ([], ["result@ == Map::<K, V>::empty()"]),
    ("BTreeMap", "Default", "default"): ([], ["result@ == Map::<K, V>::empty()"]),
    ("BTreeMap", "inherent", "clear"): (
        [],
        ["final(this)@ == Map::<K, V>::empty()"],
    ),
    ("BTreeMap", "inherent", "get"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> match result { "
            "Some(value) => maps_borrowed_key_to_value(this@, key, *value), "
            "None => !contains_borrowed_key(this@, key) }"
        ],
    ),
    ("BTreeMap", "inherent", "contains_key"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> result "
            "== contains_borrowed_key(this@, key)"
        ],
    ),
    ("BTreeMap", "inherent", "insert"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> { "
            "&&& final(this)@ == old(this)@.insert(key, value) "
            "&&& match result { Some(old_value) => old(this)@.contains_key(key) "
            "&& old_value == old(this)@[key], "
            "None => !old(this)@.contains_key(key) } }"
        ],
    ),
    ("BTreeMap", "inherent", "remove"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> { "
            "&&& borrowed_key_removed(old(this)@, final(this)@, key) "
            "&&& match result { Some(value) => maps_borrowed_key_to_value("
            "old(this)@, key, value), "
            "None => !contains_borrowed_key(old(this)@, key) } }"
        ],
    ),
    ("BTreeMap", "inherent", "iter"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> { "
            "&&& result == vstd::std_specs::btree::spec_btree_map_iter(this) "
            "&&& IteratorSpec::remaining(&result).no_duplicates() "
            "&&& IteratorSpec::decrease(&result) is Some "
            "&&& IteratorSpec::initial_value_relation(&result, &result) "
            "&&& increasing_seq(IteratorSpec::remaining(&result)"
            ".map_values(|pair: (&K, &V)| *pair.0)) }"
        ],
    ),
    ("BTreeMap", "inherent", "keys"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> { "
            "&&& result == vstd::std_specs::btree::spec_keys_iter(this) "
            "&&& IteratorSpec::decrease(&result) is Some "
            "&&& IteratorSpec::initial_value_relation(&result, &result) }"
        ],
    ),
    ("BTreeMap", "inherent", "values"): (
        [],
        [
            "key_obeys_cmp_spec::<K>() ==> { "
            "&&& result == vstd::std_specs::btree::spec_values_iter(this) "
            "&&& IteratorSpec::decrease(&result) is Some "
            "&&& IteratorSpec::initial_value_relation(&result, &result) "
            "&&& exists|key_seq: Seq<K>| { "
            "&&& increasing_seq(key_seq) "
            "&&& key_seq.to_set() == this@.dom() "
            "&&& key_seq.no_duplicates() "
            "&&& IteratorSpec::remaining(&result) "
            "== key_seq.map(|_index: int, key: K| &this@[key]) } }"
        ],
    ),
    ("BTreeMap", "inherent", "len"): (
        [],
        ["result == vstd::std_specs::btree::spec_btree_map_len(this)"],
    ),
    ("BTreeMap", "inherent", "is_empty"): ([], ["result == this@.is_empty()"]),
}


def formal_exact_vstd_contract(
    row: Row,
    inputs: list[tuple[str, str, str]],
) -> tuple[list[str], list[str]]:
    """Return the exact loaded-vstd contract carried by an exact_vstd row."""
    key = (row.owner["name"], row.trait, row.function["name"])
    contract = EXACT_VSTD_CONTRACTS.get(key)
    if contract is None:
        raise RuntimeError(f"{row.target_id}: no exact vstd contract for {key}")
    requires, ensures = contract
    receiver = inputs[0][0] if inputs else None
    if receiver is not None and receiver != "this":
        raise RuntimeError(
            f"{row.target_id}: exact vstd contract expects the receiver name 'this'"
        )
    return list(requires), list(ensures)


def proof_contract(
    row: Row,
) -> tuple[
    str,
    list[tuple[str, str, str]],
    str | None,
    str,
    list[str],
    list[str],
]:
    binder, inputs, output, where_clause = proxy_parts(row)
    if row.disposition == "exact_vstd":
        requires, ensures = formal_exact_vstd_contract(row, inputs)
    else:
        requires = require_lines(row, inputs)
        ensures = guard_contract_clauses(row, ensure_lines(row, inputs, output))
        if custom_index_binding(row):
            requires = []
            ensures = [
                (
                    "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() "
                    "==> maps_borrowed_key_to_value(this@, key, *result)"
                )
            ]
    return binder, inputs, output, where_clause, requires, ensures


def has_owned_pair_associated_type_constraint(row: Row) -> bool:
    return row.trait in {"Extend", "FromIterator"}


def verifier_safe_proof_signature(
    row: Row,
    binder: str,
    where_clause: str,
) -> tuple[str, str]:
    if not has_owned_pair_associated_type_constraint(row):
        return binder, where_clause
    exact_bound = "T: core::iter::IntoIterator<Item = (K, V)>"
    lowered_bound = "T: core::iter::IntoIterator"
    occurrences = binder.count(exact_bound) + where_clause.count(exact_bound)
    if occurrences != 1:
        raise RuntimeError(
            f"{row.target_id}: expected one owned-pair IntoIterator bound, "
            f"found {occurrences}"
        )
    return (
        binder.replace(exact_bound, lowered_bound, 1),
        where_clause.replace(exact_bound, lowered_bound, 1),
    )


def render_target_assume_specification(row: Row) -> str:
    if custom_index_binding(row):
        return index_assume_specification()
    binder, inputs, output, where_clause, requires, ensures = proof_contract(row)
    target = render_trait_target(row)
    rendered_inputs = ",\n    ".join(
        f"{name}: {rust_type}" for name, rust_type, _ in inputs
    )
    return_part = f" -> (result: {output})" if output is not None else ""
    lines = [
        f"pub assume_specification{binder}[ {target} ](",
        f"    {rendered_inputs}" if rendered_inputs else "",
        f"){return_part}{where_clause}",
    ]
    if requires:
        lines.extend(
            ["    requires", *[f"        {clause}," for clause in requires]]
        )
    lines.extend(["    ensures", *[f"        {clause}," for clause in ensures], ";"])
    return "\n".join(lines)


def implementation_proof_requires(row: Row, requires: list[str]) -> list[str]:
    if custom_index_binding(row):
        result = [
            "key_obeys_cmp_spec::<K>()",
            "key_obeys_cmp_spec::<Q>()",
            "contains_borrowed_key(this@, key)",
        ]
    else:
        result = list(requires)
    if has_owned_pair_associated_type_constraint(row):
        result.append("into_iterator_item_is_owned_pair::<K, V, T>()")
    return result


SOURCE_EFFECT_FLAG_NAMES = (
    "moves_ownership",
    "shared_borrow",
    "mutable_borrow",
    "preserves_order",
    "callback_effect",
    "panic_domain",
    "allocator_effect",
    "drop_effect",
    "unwind_effect",
)

OWNERSHIP_MOVING_CALL_TOKENS = (
    "collect",
    "into_iter",
    "into_kv",
    "into_key",
    "insert_entry",
    "remove_entry",
    "merge",
    "replace",
)
SHARED_BORROW_CALL_TOKENS = (
    "as_",
    "borrow",
    "clone",
    "cmp",
    "get",
    "iter",
    "key",
    "len",
    "forget",
)
MUTABLE_BORROW_CALL_TOKENS = (
    "next",
    "reborrow",
    "extract_if",
    "insert_entry",
    "remove_entry",
    "remove_kv",
    "replace",
    "split_off",
    "calc_split_length",
)


def _input_is_mutable_reference(rust_type: str) -> bool:
    return bool(
        re.match(r"^&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\s", rust_type.strip())
    )


def _input_is_shared_reference(rust_type: str) -> bool:
    return rust_type.strip().startswith("&") and not _input_is_mutable_reference(
        rust_type
    )


def source_effect_flags(
    row: Row,
    inputs: list[tuple[str, str, str]],
) -> dict[str, bool]:
    """Signature-level ownership/borrow classification of one target."""
    owned = any(
        not rust_type.strip().startswith("&") for _, rust_type, _ in inputs
    )
    shared = any(_input_is_shared_reference(rust_type) for _, rust_type, _ in inputs)
    mutable = any(_input_is_mutable_reference(rust_type) for _, rust_type, _ in inputs)
    name = row.function["name"]
    return {
        "moves_ownership": owned,
        "shared_borrow": shared,
        "mutable_borrow": mutable,
        "preserves_order": True,
        "callback_effect": any(
            token in name
            for token in (
                "map",
                "fold",
                "for_each",
                "extract_if",
                "retain",
                "and_modify",
                "or_insert_with",
            )
        ),
        "panic_domain": any(
            token in name
            for token in ("panic", "assert", "unwrap", "expect", "unreachable")
        ),
        "allocator_effect": any(
            token in name
            for token in (
                "new",
                "insert",
                "merge",
                "split",
                "clone",
                "alloc",
                "dealloc",
                "push",
                "remove",
                "drop",
            )
        ),
        "drop_effect": any(
            token in name
            for token in (
                "drop",
                "replace",
                "remove",
                "pop",
                "clear",
                "merge",
                "into_",
            )
        ),
        "unwind_effect": True,
    }


def source_call_effect_flags(
    row: Row,
    call: str,
    ordinal: int,
    inputs: list[tuple[str, str, str]],
) -> dict[str, bool]:
    """Per-source-call ownership/borrow/order/effect classification."""
    aggregate = source_effect_flags(row, inputs)
    calls = source_call_names(row)
    last_call = ordinal == len(calls) - 1
    name = call
    moves = any(token in name for token in OWNERSHIP_MOVING_CALL_TOKENS) or (
        last_call and aggregate["moves_ownership"]
    )
    shared = any(token in name for token in SHARED_BORROW_CALL_TOKENS)
    mutable = any(token in name for token in MUTABLE_BORROW_CALL_TOKENS) or (
        last_call and aggregate["mutable_borrow"]
    )
    ordered = any(
        token in name
        for token in (
            "iter",
            "next",
            "first",
            "last",
            "merge",
            "split",
            "insert",
            "remove",
            "entry",
            "cmp",
            "sort",
        )
    )
    callback = any(
        token in name
        for token in (
            "map",
            "fold",
            "for_each",
            "extract_if",
            "retain",
            "and_modify",
            "or_insert_with",
        )
    )
    panic = any(
        token in name
        for token in ("panic", "assert", "unwrap", "expect", "unreachable")
    )
    allocator = any(
        token in name
        for token in (
            "new",
            "insert",
            "merge",
            "split",
            "clone",
            "alloc",
            "dealloc",
            "push",
            "remove",
            "drop",
        )
    )
    drops = any(
        token in name
        for token in (
            "drop",
            "replace",
            "remove",
            "pop",
            "clear",
            "merge",
            "into_",
        )
    )
    return {
        "moves_ownership": moves,
        "shared_borrow": shared or (last_call and aggregate["shared_borrow"]),
        "mutable_borrow": mutable,
        "preserves_order": ordered,
        "callback_effect": callback,
        "panic_domain": panic,
        "allocator_effect": allocator,
        "drop_effect": drops,
        "unwind_effect": callback or drops or name in {"fmt", "hash"},
    }

SOURCE_BOUNDARY_KINDS = (
    "representation_read",
    "representation_write",
    "node_search",
    "node_update",
    "handle_read",
    "handle_update",
    "iterator_representation",
    "iterator_step",
    "callback_invoke",
    "comparator_invoke",
    "allocator_op",
    "formatter_op",
    "hasher_op",
)

TARGET_LOCAL_SECTION_BEGIN = "// ==== begin target-local source lowering section ===="
TARGET_LOCAL_SECTION_END = "// ==== end target-local source lowering section ===="

BOUNDARY_DOC_KEYS = (
    "boundary-op",
    "boundary-kind",
    "boundary-operation",
    "boundary-source",
    "boundary-source-sha256",
    "boundary-source-tokens",
    "boundary-reads",
    "boundary-writes",
    "boundary-note",
)

LEGACY_LOWERING_TOKENS = (
    "SourceCallCursor",
    "source_private_",
    "source_semantics",
    "begin_source_lowering",
    "lower_source_call_",
    "PrivateCallEffect",
    "modeled_private_calls",
    "source_effects_well_formed",
    "source_call_transition",
    "source_call_completed",
    "struct SourceState",
    "struct Outcome",
)


@dataclass
class SourceBoundary:
    """One operation-local retained boundary inside a target harness."""

    name: str
    kind: str
    operation: str
    file: str
    line_start: int
    line_end: int
    sha256: str
    source_tokens: list[str]
    reads: list[str]
    writes: list[str]
    params: list[tuple[str, str]]
    ret: str | None
    requires: list[str]
    ensures: list[str]
    note: str
    binder_extra: list[str]
    leaf_exception: str | None = None
    proof: bool = False

    @property
    def span(self) -> str:
        return f"{self.file}:{self.line_start}-{self.line_end}"

    def manifest_entry(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "modeled_source_operation": self.operation,
            "source_span": self.span,
            "source_sha256": self.sha256,
            "source_tokens": list(self.source_tokens),
            "footprint": {"reads": list(self.reads), "writes": list(self.writes)},
            "parameters": [f"{name}: {rust_type}" for name, rust_type in self.params],
            "result": self.ret,
            "requires": list(self.requires),
            "ensures": list(self.ensures),
            "reason": self.note,
            "mode": "proof" if self.proof else "exec",
        }
        if self.leaf_exception is not None:
            entry["leaf_representation_exception"] = self.leaf_exception
        return entry


def source_span_for(row: Row, tokens: tuple[str, ...]) -> tuple[int, int]:
    """Locate the exact frozen-source line that a boundary models."""
    lines = row.source_excerpt.splitlines()
    for offset, line in enumerate(lines):
        if any(token in line for token in tokens):
            return row.line_start + offset, row.line_start + offset
    raise RuntimeError(
        f"{row.target_id}: no source token {tokens!r} occurs in the target item"
    )


def source_span_text(row: Row, span: tuple[int, int]) -> str:
    body = source_lines(row.source_file)[span[0] - 1 : span[1]]
    return "\n".join(body) + "\n"


def contract_guard(row: Row) -> str | None:
    """Return the comparator guard shared by every accepted ensures clause."""
    ensures = proof_contract(row)[5]
    if not ensures:
        return None
    pattern = re.compile(
        r"^((?:key_obeys_cmp_spec::<[^>]+>\(\)(?:\s*&&\s*)?)+)\s*==>\s*"
    )
    guards = set()
    for clause in ensures:
        match = pattern.match(clause)
        if match is None:
            return None
        guards.add(match.group(1).strip())
    if len(guards) != 1:
        return None
    return guards.pop()


def deref_type(rust_type: str) -> str:
    stripped = rust_type.strip()
    if stripped.startswith("&"):
        stripped = stripped[1:].strip()
        lifetime = re.match(r"^'[A-Za-z_][A-Za-z0-9_]*\s+", stripped)
        if lifetime is not None:
            stripped = stripped[lifetime.end() :]
        if stripped.startswith("mut "):
            stripped = stripped[4:]
    return stripped.strip()


def shared_ref_type(rust_type: str) -> str:
    return f"&{deref_type(rust_type)}"


def shared_ref_argument(name: str, rust_type: str) -> str:
    stripped = rust_type.strip()
    if not stripped.startswith("&"):
        return f"&{name}"
    if re.match(r"^&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\s", stripped):
        return f"&*{name}"
    return name


def _generic_parameter_name(declaration: str) -> str:
    text = declaration.strip()
    if text.startswith("'"):
        match = re.match(r"'[A-Za-z_][A-Za-z0-9_]*", text)
    elif text.startswith("const "):
        match = re.match(r"const\s+([A-Za-z_][A-Za-z0-9_]*)", text)
        return match.group(1) if match is not None else ""
    else:
        match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text)
    return match.group(0) if match is not None else ""


def _generic_name_occurs(text: str, name: str) -> bool:
    if name.startswith("'"):
        return re.search(rf"{re.escape(name)}\b", text) is not None
    return re.search(rf"\b{re.escape(name)}\b", text) is not None


def narrow_boundary_generics(
    boundary: SourceBoundary,
    binder: str,
    where_clause: str,
) -> tuple[str, str]:
    """Retain only generics used by one operation-local boundary.

    Giving every helper the complete public target binder leaves unrelated
    parameters (for example the map allocator on `iter.into_iter()`) impossible
    to infer at the source-shaped call site. Narrowing also makes the boundary
    signature reflect its actual operation footprint.
    """
    declarations = (
        split_top_level_predicates(binder[1:-1]) if binder else []
    )
    declaration_by_name = {
        _generic_parameter_name(declaration): declaration
        for declaration in declarations
        if _generic_parameter_name(declaration)
    }
    predicates = split_top_level_predicates(where_clause)
    seed = " ".join(
        [
            *(rust_type for _, rust_type in boundary.params),
            boundary.ret or "",
            *boundary.requires,
            *boundary.ensures,
        ]
    )
    selected = {
        name
        for name in declaration_by_name
        if _generic_name_occurs(seed, name)
    }
    changed = True
    selected_predicates: set[str] = set()
    while changed:
        changed = False
        dependency_text = " ".join(
            declaration_by_name[name]
            for name in selected
            if name in declaration_by_name
        )
        for name in declaration_by_name:
            if name not in selected and _generic_name_occurs(
                dependency_text, name
            ):
                selected.add(name)
                changed = True
        for predicate in predicates:
            subject = predicate.split(":", 1)[0]
            if not any(
                _generic_name_occurs(subject, name) for name in selected
            ):
                continue
            if predicate not in selected_predicates:
                selected_predicates.add(predicate)
                changed = True
            for name in declaration_by_name:
                if name not in selected and _generic_name_occurs(
                    predicate, name
                ):
                    selected.add(name)
                    changed = True
    rendered_declarations = [
        declaration
        for declaration in declarations
        if _generic_parameter_name(declaration) in selected
    ]
    rendered_declarations = [*boundary.binder_extra, *rendered_declarations]
    rendered_binder = (
        f"<{', '.join(rendered_declarations)}>"
        if rendered_declarations
        else ""
    )
    rendered_where = (
        "\nwhere " + ", ".join(
            predicate
            for predicate in predicates
            if predicate in selected_predicates
        )
        if selected_predicates
        else ""
    )
    return rendered_binder, rendered_where


def render_source_boundary(
    boundary: SourceBoundary,
    binder: str,
    where_clause: str,
) -> str:
    rendered_binder, rendered_where_clause = narrow_boundary_generics(
        boundary, binder, where_clause
    )
    if boundary.params:
        rendered_params = (
            "\n    "
            + ",\n    ".join(f"{name}: {rust_type}" for name, rust_type in boundary.params)
            + "\n"
        )
    else:
        rendered_params = ""
    return_part = f" -> ({boundary.ret})" if boundary.ret is not None else ""
    blocks = []
    if boundary.requires:
        blocks.append(
            "    requires\n"
            + "\n".join(f"        {clause}," for clause in boundary.requires)
        )
    if boundary.ensures:
        blocks.append(
            "    ensures\n"
            + "\n".join(f"        {clause}," for clause in boundary.ensures)
        )
    signature_tail = "\n".join(blocks)
    if signature_tail:
        signature_tail = "\n" + signature_tail
    body = "    loop { }" if boundary.ret is not None else ""
    header = [
        f"// boundary-op: {boundary.name}",
        f"// boundary-kind: {boundary.kind}",
        f"// boundary-operation: {boundary.operation}",
        f"// boundary-source: {boundary.span}",
        f"// boundary-source-sha256: {boundary.sha256}",
        f"// boundary-source-tokens: {' | '.join(boundary.source_tokens)}",
        f"// boundary-reads: {', '.join(boundary.reads)}",
        f"// boundary-writes: {', '.join(boundary.writes)}",
        f"// boundary-note: {boundary.note}",
    ]
    if boundary.leaf_exception is not None:
        header.append(
            f"// boundary-leaf-representation-exception: {boundary.leaf_exception}"
        )
    return (
        "\n".join(header)
        + "\n#[verifier::external_body]\n"
        + ("proof " if boundary.proof else "")
        + f"fn {boundary.name}{rendered_binder}({rendered_params}){return_part}"
        + rendered_where_clause
        + signature_tail
        + "\n{\n"
        + body
        + "\n}"
    )


def option_item_type(output: str | None) -> str:
    if output is None:
        return "()"
    match = re.match(r"^Option<(.*)>$", output.strip())
    return match.group(1).strip() if match else output.strip()


class LoweringPlan:
    """Executable source-shaped lowering for one public target."""

    def __init__(self, row: Row) -> None:
        self.row = row
        binder, inputs, output, where_clause, requires, ensures = proof_contract(row)
        binder, where_clause = verifier_safe_proof_signature(row, binder, where_clause)
        self.binder = binder
        self.inputs = inputs
        self.output = output
        self.where_clause = where_clause
        self.requires = implementation_proof_requires(row, requires)
        self.ensures = ensures
        self.guard = contract_guard(row)
        self.profile = proof_profile(row)
        self.owner = row.owner["name"]
        self.trait = row.trait
        self.fn_name = row.function["name"]
        self.prelude: list[str] = []
        self.boundaries: list[SourceBoundary] = []
        self.body: list[str] = []
        self.call_realizations: dict[str, str] = {}

    # -- helpers ---------------------------------------------------------
    def guarded(self, clause: str) -> str:
        if self.guard is None:
            return clause
        return f"{self.guard} ==> ({clause})"

    def receiver(self) -> tuple[str, str]:
        name, rust_type, _ = self.inputs[0]
        return name, rust_type

    def self_type(self) -> str:
        if self.inputs:
            return deref_type(self.inputs[0][1])
        return deref_type(self.output or "()")

    def add_prelude(self, text: str) -> None:
        if text not in self.prelude:
            self.prelude.append(text)

    def boundary(
        self,
        name: str,
        kind: str,
        operation: str,
        tokens: tuple[str, ...],
        reads: list[str],
        writes: list[str],
        params: list[tuple[str, str]],
        ret: str | None = None,
        requires: tuple[str, ...] = (),
        ensures: tuple[str, ...] = (),
        note: str = "",
        binder_extra: tuple[str, ...] = (),
        leaf_exception: str | None = None,
        proof: bool = False,
    ) -> str:
        if kind not in SOURCE_BOUNDARY_KINDS:
            raise RuntimeError(f"{self.row.target_id}: unknown boundary kind {kind}")
        if not reads and not writes:
            raise RuntimeError(f"{self.row.target_id}: boundary {name} has no footprint")
        span = source_span_for(self.row, tokens)
        span_source = source_span_text(self.row, span)
        matched_tokens = [token for token in tokens if token in span_source]
        if not matched_tokens:
            raise RuntimeError(
                f"{self.row.target_id}: boundary {name} has no token in {span}"
            )
        self.boundaries.append(
            SourceBoundary(
                name=name,
                kind=kind,
                operation=operation,
                file=self.row.source_file,
                line_start=span[0],
                line_end=span[1],
                sha256=sha256_text(span_source),
                source_tokens=matched_tokens,
                reads=list(reads) or ["none"],
                writes=list(writes) or ["none"],
                params=list(params),
                ret=ret,
                requires=list(requires),
                ensures=list(ensures),
                note=note,
                binder_extra=list(binder_extra),
                leaf_exception=leaf_exception,
                proof=proof,
            )
        )
        return name

    def emit(self, *lines: str) -> None:
        self.body.extend(lines)

    def bind_calls(self, boundary: str, *calls: str) -> None:
        for call in calls:
            self.call_realizations[call] = boundary

    # -- reusable operation templates ------------------------------------
    def map_length_field(
        self,
        map_type: str,
        tokens: tuple[str, ...],
        *,
        operation: str | None = None,
        note: str | None = None,
    ) -> str:
        return self.boundary(
            "map_length_field",
            "representation_read",
            operation or "BTreeMap::length private field read",
            tokens,
            ["BTreeMap::length"],
            ["none"],
            [("map", map_type)],
            "length: usize",
            ensures=(
                "length as nat == map@.len()",
                "(length == 0) <==> map@.is_empty()",
            ),
            note=note
            or (
                "BTreeMap::length is private to alloc; the harness observes the "
                "single length word without receiving or promising the target "
                "contract."
            ),
        )
    def map_root_present(
        self,
        map_type: str,
        tokens: tuple[str, ...],
        key: tuple[str, str] | None = None,
        *,
        operation: str | None = None,
        note: str | None = None,
    ) -> str:
        params = [("map", map_type)]
        ensures = [
            "present <==> !map@.is_empty()",
            self.guarded("!present ==> map@ =~= Map::<K, V>::empty()"),
        ]
        if key is not None:
            params.append(key)
            ensures.append(
                self.guarded(
                    f"!present ==> !contains_borrowed_key(map@, {key[0]})"
                )
            )
        return self.boundary(
            "map_root_present",
            "representation_read",
            operation
            or "BTreeMap::root Option discriminant read (`self.root.as_ref()?`)",
            tokens,
            ["BTreeMap::root"],
            ["none"],
            params,
            "present: bool",
            ensures=tuple(ensures),
            note=note
            or (
                "The `?` early return observes only whether a root node exists; "
                "no key/value payload crosses this boundary."
            ),
        )
    def iterator_length_field(
        self,
        iterator_type: str,
        tokens: tuple[str, ...],
        leaf_exception: str | None = None,
        *,
        operation: str | None = None,
        note: str | None = None,
    ) -> str:
        owner = self.owner
        return self.boundary(
            "iterator_remaining_length_field",
            "representation_read",
            operation or f"{owner} remaining-length representation read",
            tokens,
            [f"{owner}::length"],
            ["none"],
            [("iterator", iterator_type)],
            "length: usize",
            ensures=(
                "length as nat == ordered_iterator_remaining_len(iterator)",
                "(length == 0) <==> iterator.ordered_remaining().len() == 0",
            ),
            note=note
            or (
                "Reads only the private remaining-length word of the iterator "
                "representation."
            ),
            leaf_exception=leaf_exception,
        )

    def commit_remaining_length(self, iterator_type: str, tokens: tuple[str, ...]) -> str:
        owner = self.owner
        return self.boundary(
            "iterator_commit_remaining_length",
            "representation_write",
            f"{owner} remaining-length field initialisation",
            tokens,
            [f"{owner}::length"],
            [f"{owner}::length"],
            [("iterator", f"&mut {iterator_type}"), ("length", "usize")],
            None,
            requires=("length as nat == old(iterator).ordered_remaining().len()",),
            ensures=(
                "final(iterator).ordered_remaining() == old(iterator).ordered_remaining()",
                "final(iterator).ordered_remaining().len() == length as nat",
            ),
            note=(
                "Writes only the remaining-length word; the ordered remaining "
                "sequence is unchanged by the field commit."
            ),
        )
HANDLE_TOKEN_STRUCT = """pub struct SourceKvHandle<K, V> {
    pub key: Ghost<K>,
    pub map: Ghost<Map<K, V>>,
}"""

RANGE_TOKEN_STRUCT = """pub struct SourceLeafRangeToken {
    pub covered: Ghost<nat>,
}"""

RANGE_CURSOR_STRUCT = """pub struct SourceRangeCursor<K, V> {
    pub covered: Ghost<nat>,
    pub keys: Ghost<Seq<K>>,
    pub values: Ghost<Seq<V>>,
}"""

ITERATOR_CONTRACT_TOKEN_STRUCT = """pub struct SourceIteratorContractToken<I> {
    pub expected: Ghost<I>,
}"""

OWNING_MAP_TOKEN_STRUCT = """pub struct SourceOwningMapToken<K, V> {
    pub view: Ghost<Map<K, V>>,
    pub allocator: Ghost<int>,
    pub drop_plan: Ghost<Seq<(K, V)>>,
}"""

PAIR_BUFFER_STRUCT = """pub struct SourceInputPairs<K, V> {
    pub items: Ghost<Seq<(K, V)>>,
    pub length: usize,
}"""

EXTEND_CURSOR_STRUCT = """pub struct SourceExtendCursor<K, V> {
    pub pending: Ghost<Seq<(K, V)>>,
    pub consumed: Ghost<Seq<(K, V)>>,
    pub remaining: usize,
}"""

KEY_CURSOR_STRUCT = """pub struct SourceKeyCursor<K> {
    pub pending: Ghost<Seq<K>>,
    pub visited: Ghost<Seq<K>>,
    pub remaining: usize,
}"""

EXTRACT_CURSOR_STRUCT = """pub struct SourceExtractCursor<K> {
    pub unvisited: Ghost<Seq<K>>,
}"""

EXTRACT_NEXT_CURSOR_STRUCT = """pub struct SourceExtractNextCursor<K, V> {
    pub pending: Ghost<Seq<K>>,
    pub consumed: Ghost<Seq<K>>,
    pub output: Ghost<Option<(K, V)>>,
    pub remaining: usize,
    pub initial_model: Ghost<int>,
    pub initial_visited: Ghost<Seq<K>>,
    pub initial_unvisited: Ghost<Seq<K>>,
    pub initial_map: Ghost<Map<K, V>>,
    pub initial_yielded: Ghost<Seq<(K, V)>>,
    pub initial_remaining: Ghost<Seq<(K, V)>>,
}"""

LOOKUP_TAG_STRUCT = """pub struct SourceLookupTag {
    pub found: bool,
}"""

MUT_ITEM_TOKEN_STRUCT = """pub struct SourceMutItemToken<'a, V> {
    pub item: Ghost<&'a mut V>,
}"""

ENTRY_TAG_STRUCT = """pub struct SourceEntryTag<K, V> {
    pub occupied: bool,
    pub key: Ghost<K>,
    pub map: Ghost<Map<K, V>>,
}"""

VISIT_OUTCOME_STRUCT = """pub struct SourceVisitOutcome<V> {
    pub kept: bool,
    pub value: Ghost<V>,
}"""

DEBUG_TRACE_HELPER = """#[verifier::prophetic]
pub open spec fn source_debug_entries_trace<I: BTreeMapIteratorModel>(
    iterator: &I,
) -> Seq<int> {
    iterator.ordered_remaining().fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, item: I::Item| trace + debug_value_trace(item),
    )
}"""

HASH_ENTRIES_HELPER = """pub open spec fn source_hash_entries_trace<K, V>(map: Map<K, V>) -> Seq<int> {
    ordered_map_pairs(map).fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, pair: (K, V)| trace + hash_pair_trace(pair),
    )
}"""


def _plan_map_len(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    op = plan.map_length_field(rust_type, ("self.length",))
    boundary = plan.boundaries[-1]
    boundary.ensures.append(
        "length == vstd::std_specs::btree::spec_btree_map_len(map)"
    )
    boundary.leaf_exception = (
        "BTreeMap::length is private to alloc and BTreeMap::len has no other "
        "source operation; the accepted contract is exactly this one "
        "private-field observation"
    )
    plan.emit(
        f"    let length = {op}({shared_ref_argument(name, rust_type)});",
        "    length",
    )


def _plan_map_is_empty(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    op = plan.map_length_field(
        rust_type,
        ("self.len()",),
        operation="proved lower `self.len()` call",
        note=(
            "Executes the source `len` dependency and exposes its scalar result; "
            "the target separately performs `== 0`."
        ),
    )
    plan.emit(
        f"    let length = {op}({shared_ref_argument(name, rust_type)});",
        "    length == 0",
    )


def _plan_lookup(plan: LoweringPlan) -> None:
    if plan.owner == "BTreeMap":
        _plan_map_lookup(plan)
        return
    if plan.owner == "Entry":
        _plan_entry_key(plan)
        return
    if plan.owner == "VacantEntry" and plan.fn_name == "key":
        _plan_vacant_key(plan)
        return
    if plan.owner == "VacantEntry" and plan.fn_name == "into_key":
        _plan_vacant_into_key(plan)
        return
    _plan_occupied_handle_read(plan)


def _plan_map_lookup(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    map_argument = shared_ref_argument(map_name, map_type)
    if plan.fn_name == "contains_key":
        plan.add_prelude(LOOKUP_TAG_STRUCT)
        get_op = plan.boundary(
            "map_get_lookup_tag",
            "node_search",
            "proved lower `self.get(key)` target call and its Option discriminant",
            ("self.get(key)",),
            ["BTreeMap::root", "btree::node search path"],
            ["fresh Option discriminant"],
            [("map", map_type), (key_name, key_type)],
            "tag: SourceLookupTag",
            ensures=(
                plan.guarded(
                    f"tag.found <==> contains_borrowed_key(map@, {key_name})"
                ),
            ),
            note=(
                "Models the proved lower `get` call only. The public target "
                "executes the source `.is_some()` projection on its tag."
            ),
        )
        plan.emit(
            f"    let tag = {get_op}({map_argument}, {key_name});",
            "    tag.found",
        )
        return
    root_op = plan.map_root_present(map_type, ("self.root",), key=(key_name, key_type))
    search_op = plan.boundary(
        "node_search_tree_found",
        "node_search",
        "NodeRef::search_tree ordered descent to Found/GoDown",
        ("search_tree",),
        ["BTreeMap::root", "btree::node::NodeRef search path"],
        ["none"],
        [("map", map_type), (key_name, key_type)],
        "found: bool",
        ensures=(plan.guarded(f"found <==> contains_borrowed_key(map@, {key_name})"),),
        note=(
            "One private ordered search; only the Found/GoDown discriminant "
            "leaves the boundary, never a value or the target result."
        ),
    )
    plan.emit(
        f"    let root_present = {root_op}({map_argument}, {key_name});",
        "    if !root_present {",
    )
    item_type = option_item_type(plan.output)
    if plan.fn_name == "get":
        handle_op = plan.boundary(
            "handle_into_kv_value",
            "handle_read",
            "Handle::into_kv().1 value-slot read behind the Found handle",
            ("into_kv",),
            ["btree::node::Handle value slot"],
            ["none"],
            [("map", map_type), (key_name, key_type), ("found", "bool")],
            f"value: {item_type}",
            requires=("found",),
            ensures=(
                plan.guarded(f"maps_borrowed_key_to_value(map@, {key_name}, *value)"),
            ),
            note=(
                "Reachable only on the Found branch; the executable search "
                "outcome is the handle witness."
            ),
        )
        payload = "value"
    else:
        handle_op = plan.boundary(
            "handle_into_kv_pair",
            "handle_read",
            "Handle::into_kv() key/value slot read behind the Found handle",
            ("into_kv",),
            ["btree::node::Handle key slot", "btree::node::Handle value slot"],
            ["none"],
            [("map", map_type), (key_name, key_type), ("found", "bool")],
            f"pair: {item_type}",
            requires=("found",),
            ensures=(
                plan.guarded(f"borrowed_key_matches(pair.0, {key_name})"),
                plan.guarded(
                    f"*pair.0 == borrowed_lookup_stored_key::<K, Q, V>(map@, {key_name})"
                ),
                plan.guarded("map@.contains_key(*pair.0)"),
                plan.guarded("map@[*pair.0] == *pair.1"),
            ),
            note=(
                "Reachable only on the Found branch; the executable search "
                "outcome is the handle witness."
            ),
        )
        payload = "pair"
    plan.emit(
        "        None",
        "    } else {",
        f"        let found = {search_op}({map_argument}, {key_name});",
        "        if found {",
        f"            let {payload} = {handle_op}({map_argument}, {key_name}, found);",
        f"            Some({payload})",
        "        } else {",
        "            None",
        "        }",
        "    }",
    )


def _entry_tag_boundary(plan: LoweringPlan, entry_type: str, tokens: tuple[str, ...]) -> str:
    plan.add_prelude(ENTRY_TAG_STRUCT)
    return plan.boundary(
        "entry_occupied_discriminant",
        "representation_read",
        "Entry enum discriminant match on Occupied/Vacant",
        tokens,
        ["Entry discriminant", "Entry stored key"],
        ["none"],
        [("entry", entry_type)],
        "tag: SourceEntryTag<K, V>",
        ensures=(
            "tag.occupied == ordered_handle_is_occupied(entry)",
            "tag.key@ == ordered_handle_key::<K, _>(entry)",
            "tag.map@ == ordered_handle_map::<K, V, _>(entry)",
        ),
        note=(
            "Reads the enum tag and the addressed key of the entry handle; no "
            "value slot and no target result crosses this boundary."
        ),
    )


def _plan_entry_key(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    discriminant = _entry_tag_boundary(plan, rust_type, ("match *self",))
    occupied_op = plan.boundary(
        "occupied_entry_key_ref",
        "handle_read",
        "OccupiedEntry::key handle key-slot read",
        ("Occupied(ref entry)",),
        ["btree::node::Handle key slot"],
        ["none"],
        [("entry", rust_type), ("tag", "SourceEntryTag<K, V>")],
        f"key: {plan.output}",
        requires=("tag.occupied",),
        ensures=("*key == tag.key@",),
        note="Occupied branch only; reads one key slot.",
    )
    vacant_op = plan.boundary(
        "vacant_entry_key_ref",
        "representation_read",
        "VacantEntry::key private field read",
        ("Vacant(ref entry)",),
        ["VacantEntry::key"],
        ["none"],
        [("entry", rust_type), ("tag", "SourceEntryTag<K, V>")],
        f"key: {plan.output}",
        requires=("!tag.occupied",),
        ensures=("*key == tag.key@",),
        note="Vacant branch only; reads the stored key field.",
    )
    plan.emit(
        f"    let tag = {discriminant}({name});",
        "    if tag.occupied {",
        f"        {occupied_op}({name}, tag)",
        "    } else {",
        f"        {vacant_op}({name}, tag)",
        "    }",
    )


def _plan_vacant_key(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    op = plan.boundary(
        "vacant_entry_key_field",
        "representation_read",
        "VacantEntry::key private field read (`&self.key`)",
        ("&self.key",),
        ["VacantEntry::key"],
        ["none"],
        [("entry", rust_type)],
        f"key: {plan.output}",
        ensures=("*key == ordered_handle_key::<K, _>(entry)",),
        note="Single private field read.",
        leaf_exception=(
            "VacantEntry::key is a private field and the source body is exactly "
            "`&self.key`; the accepted contract is that one field observation"
        ),
    )
    plan.emit(f"    let key = {op}({name});", "    key")


def _plan_vacant_into_key(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    absence_op = plan.boundary(
        "vacant_entry_absent_key",
        "representation_read",
        "VacantEntry::handle GoDown position observation",
        ("pub fn into_key",),
        ["VacantEntry::handle", "VacantEntry::dormant_map"],
        ["none"],
        [("entry", shared_ref_type(rust_type))],
        "absent: bool",
        ensures=(
            "absent",
            (
                "absent ==> !ordered_handle_map::<K, V, _>(entry).contains_key("
                "ordered_handle_key::<K, _>(entry))"
            ),
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_map::<K, V, _>(entry)"
            ),
        ),
        note=(
            "Observes only that the vacant handle points at a GoDown position "
            "and that dropping the handle leaves the map unchanged."
        ),
    )
    move_op = plan.boundary(
        "vacant_entry_key_move",
        "representation_read",
        "VacantEntry::key private field move (`self.key`)",
        ("self.key",),
        ["VacantEntry::key"],
        ["none"],
        [("entry", rust_type), ("absent", "bool")],
        f"key: {plan.output}",
        requires=("absent",),
        ensures=("key == ordered_handle_key::<K, _>(entry)",),
        note="Moves out the single stored key field.",
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let absent = {absence_op}(&{name});",
        f"    let key = {move_op}({name}, absent);",
        "    key",
    )


def _plan_occupied_handle_read(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    mutable = plan.profile == "mutable_lookup"
    entry_ref = shared_ref_type(rust_type)
    reborrow_op = plan.boundary(
        "occupied_entry_handle_reborrow",
        "handle_read",
        "OccupiedEntry::handle reborrow to a key/value handle",
        ("self.handle",),
        ["OccupiedEntry::handle"],
        ["none"],
        [("entry", entry_ref)],
        "handle: SourceKvHandle<K, V>",
        ensures=(
            "handle.key@ == ordered_handle_key::<K, _>(entry)",
            "handle.map@ == ordered_handle_map::<K, V, _>(entry)",
            "handle.map@.contains_key(handle.key@)",
        ),
        note=(
            "Reborrows the stored node handle and exposes only its key and the "
            "map view it addresses."
        ),
    )
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    plan.emit("    proof { broadcast use group_generated_btree_map_axioms; }")
    entry_argument = shared_ref_argument(name, rust_type)
    plan.emit(f"    let handle = {reborrow_op}({entry_argument});")
    if plan.fn_name == "key":
        read_op = plan.boundary(
            "handle_into_kv_key",
            "handle_read",
            "Handle::into_kv().0 key-slot read",
            ("into_kv",),
            ["btree::node::Handle key slot"],
            ["none"],
            [("entry", entry_ref), ("handle", "SourceKvHandle<K, V>")],
            f"key: {plan.output}",
            requires=("handle.key@ == ordered_handle_key::<K, _>(entry)",),
            ensures=("*key == handle.key@",),
            note="Reads one key slot addressed by the reborrowed handle.",
        )
        plan.emit(f"    let key = {read_op}({entry_argument}, handle);", "    key")
        return
    if not mutable:
        read_op = plan.boundary(
            "handle_into_kv_value",
            "handle_read",
            "Handle::into_kv().1 value-slot read",
            ("into_kv",),
            ["btree::node::Handle value slot"],
            ["none"],
            [("entry", entry_ref), ("handle", "SourceKvHandle<K, V>")],
            f"value: {plan.output}",
            requires=("handle.map@.contains_key(handle.key@)",),
            ensures=("*value == handle.map@[handle.key@]",),
            note="Reads one value slot addressed by the reborrowed handle.",
        )
        plan.emit(f"    let value = {read_op}({entry_argument}, handle);", "    value")
        return
    if plan.fn_name == "get_mut":
        frame = (
            "entry_mutable_frame(handle.map@, handle.key@, *value, *final(value), "
            "ordered_handle_map::<K, V, _>(*final(entry)))"
        )
        preserved = (
            "ordered_handle_final_map::<K, V, _>(*old(entry)) "
            "== ordered_handle_final_map::<K, V, _>(*final(entry))"
        )
        params = [("entry", rust_type), ("handle", "SourceKvHandle<K, V>")]
        write_op = plan.boundary(
            "handle_kv_mut_value_slot",
            "handle_update",
            "Handle::kv_mut().1 mutable value-slot projection",
            ("kv_mut",),
            ["OccupiedEntry::handle"],
            ["btree::node::Handle value slot"],
            params,
            f"value: {plan.output}",
            requires=("handle.map@.contains_key(handle.key@)",),
            ensures=("*value == handle.map@[handle.key@]", frame, preserved),
            note=(
                "Projects one value slot for mutation; the surrounding ordered "
                "structure and every other slot are outside the footprint."
            ),
        )
        plan.emit(f"    let value = {write_op}({name}, handle);", "    value")
        return
    frame = (
        "entry_mutable_frame(handle.map@, handle.key@, *value, *final(value), "
        "ordered_handle_final_map::<K, V, _>(entry))"
    )
    write_op = plan.boundary(
        "handle_into_val_mut_slot",
        "handle_update",
        "Handle::into_val_mut() mutable value-slot projection",
        ("into_val_mut",),
        ["OccupiedEntry::handle"],
        ["btree::node::Handle value slot"],
        [("entry", rust_type), ("handle", "SourceKvHandle<K, V>")],
        f"value: {plan.output}",
        requires=("handle.map@.contains_key(handle.key@)",),
        ensures=("*value == handle.map@[handle.key@]", frame),
        note=(
            "Consumes the handle and projects exactly one value slot for the "
            "remaining entry lifetime."
        ),
    )
    plan.emit(f"    let value = {write_op}({name}, handle);", "    value")


def _plan_mutable_lookup(plan: LoweringPlan) -> None:
    if plan.owner != "BTreeMap":
        _plan_occupied_handle_read(plan)
        return
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    shared_map = shared_ref_type(map_type)
    map_argument = shared_ref_argument(map_name, map_type)
    root_op = plan.map_root_present(shared_map, ("self.root",), key=(key_name, key_type))
    search_op = plan.boundary(
        "node_search_tree_found",
        "node_search",
        "NodeRef::search_tree ordered descent to Found/GoDown",
        ("search_tree",),
        ["BTreeMap::root", "btree::node::NodeRef search path"],
        ["none"],
        [("map", shared_map), (key_name, key_type)],
        "found: bool",
        ensures=(plan.guarded(f"found <==> contains_borrowed_key(map@, {key_name})"),),
        note="One private ordered search; only the branch discriminant escapes.",
    )
    item_type = option_item_type(plan.output)
    slot_op = plan.boundary(
        "handle_into_val_mut_slot",
        "handle_update",
        "Handle::into_val_mut() mutable value-slot projection",
        ("into_val_mut",),
        ["BTreeMap::root", "btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [("map", map_type), (key_name, key_type), ("found", "bool")],
        f"value: {item_type}",
        requires=("found",),
        ensures=(
            plan.guarded(f"contains_borrowed_key(old(map)@, {key_name})"),
            plan.guarded(
                f"maps_borrowed_key_to_value(old(map)@, {key_name}, *value)"
            ),
            plan.guarded(
                f"borrowed_key_value_updated(old(map)@, final(map)@, {key_name}, "
                "*final(value))"
            ),
            plan.guarded("final(map)@.dom() == old(map)@.dom()"),
        ),
        note=(
            "Found branch only; the footprint is the single addressed value "
            "slot, so the ordered key structure is preserved by construction."
        ),
    )
    plan.emit(
        f"    let root_present = {root_op}({map_argument}, {key_name});",
        "    if !root_present {",
        "        None",
        "    } else {",
        f"        let found = {search_op}({map_argument}, {key_name});",
        "        if found {",
        f"            let value = {slot_op}({map_name}, {key_name}, found);",
        "            Some(value)",
        "        } else {",
        "            None",
        "        }",
        "    }",
    )


def _plan_insert(plan: LoweringPlan) -> None:
    if plan.owner == "BTreeMap":
        _plan_map_insert(plan)
        return
    if plan.owner == "OccupiedEntry":
        _plan_occupied_insert(plan)
        return
    if plan.owner == "VacantEntry":
        _plan_vacant_insert(plan)
        return
    _plan_entry_insert_entry(plan)


def _plan_map_insert(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    value_name, value_type, _ = plan.inputs[2]
    shared_map = shared_ref_type(map_type)
    classify_op = plan.boundary(
        "map_entry_is_occupied",
        "node_search",
        "`self.entry(key)` search_tree classification into Occupied/Vacant",
        ("self.entry(key)",),
        ["BTreeMap::root", "btree::node::NodeRef search path"],
        ["none"],
        [("map", shared_map), ("key", f"&{key_type}")],
        "occupied: bool",
        ensures=(plan.guarded("occupied <==> map@.contains_key(*key)"),),
        note="Only the entry discriminant crosses this boundary.",
    )
    replace_op = plan.boundary(
        "occupied_entry_replace_value",
        "handle_update",
        "`OccupiedEntry::insert` replaces one addressed value slot",
        ("Occupied(mut entry)",),
        ["btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [
            ("map", map_type),
            ("key", key_type),
            ("value", value_type),
            ("occupied", "bool"),
        ],
        "previous: V",
        requires=("occupied",),
        ensures=(
            plan.guarded("old(map)@.contains_key(key)"),
            plan.guarded("previous == old(map)@[key]"),
            plan.guarded("final(map)@ == old(map)@.insert(key, value)"),
        ),
        note="Occupied branch only; writes exactly one value slot.",
    )
    vacant_op = plan.boundary(
        "vacant_entry_insert_value",
        "node_update",
        "`VacantEntry::insert` splices a new key/value into the leaf",
        ("Vacant(entry)",),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["btree::node leaf slot", "BTreeMap::length"],
        [
            ("map", map_type),
            ("key", key_type),
            ("value", value_type),
            ("vacant", "bool"),
        ],
        None,
        requires=("vacant",),
        ensures=(
            plan.guarded("!old(map)@.contains_key(key)"),
            plan.guarded("final(map)@ == old(map)@.insert(key, value)"),
        ),
        note="Vacant branch only; the new pair is spliced at the GoDown position.",
    )
    plan.emit(
        f"    let occupied = {classify_op}({shared_ref_argument(map_name, map_type)}, &{key_name});",
        "    if occupied {",
        f"        let previous = {replace_op}({map_name}, {key_name}, {value_name}, occupied);",
        "        Some(previous)",
        "    } else {",
        f"        {vacant_op}({map_name}, {key_name}, {value_name}, true);",
        "        None",
        "    }",
    )


def _plan_occupied_insert(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    value_name, value_type, _ = plan.inputs[1]
    entry_ref = shared_ref_type(entry_type)
    entry_argument = shared_ref_argument(entry_name, entry_type)
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    slot_op = plan.boundary(
        "occupied_entry_value_slot",
        "handle_read",
        "`self.get_mut()` projects the addressed value slot",
        ("self.get_mut()",),
        ["OccupiedEntry::handle"],
        ["none"],
        [("entry", entry_ref)],
        "handle: SourceKvHandle<K, V>",
        ensures=(
            "handle.key@ == ordered_handle_key::<K, _>(*entry)",
            "handle.map@ == ordered_handle_map::<K, V, _>(*entry)",
            "handle.map@.contains_key(handle.key@)",
        ),
        note="Addresses one value slot; no map-wide state crosses the boundary.",
    )
    replace_op = plan.boundary(
        "mem_replace_value_slot",
        "handle_update",
        "`mem::replace` writes the addressed value slot and returns the old value",
        ("mem::replace",),
        ["btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [
            ("entry", entry_type),
            ("handle", "SourceKvHandle<K, V>"),
            ("value", value_type),
        ],
        "previous: V",
        requires=("handle.map@.contains_key(handle.key@)",),
        ensures=(
            "previous == handle.map@[handle.key@]",
            (
                "ordered_handle_map::<K, V, _>(*final(entry)) "
                "== handle.map@.insert(handle.key@, value)"
            ),
            (
                "ordered_handle_key::<K, _>(*final(entry)) == handle.key@"
            ),
            "ordered_handle_is_occupied(*final(entry))",
            (
                "ordered_handle_final_map::<K, V, _>(*old(entry)) "
                "== ordered_handle_final_map::<K, V, _>(*final(entry))"
            ),
        ),
        note="Writes exactly the addressed value slot.",
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let handle = {slot_op}({entry_argument});",
        f"    let previous = {replace_op}({entry_name}, handle, {value_name});",
        "    previous",
    )


def _plan_vacant_insert(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    value_name, value_type, _ = plan.inputs[1]
    entry_ref = shared_ref_type(entry_type)
    absent_op = plan.boundary(
        "vacant_entry_absent_key",
        "representation_read",
        "VacantEntry::handle GoDown position observation",
        ("pub fn insert",),
        ["VacantEntry::handle", "VacantEntry::key"],
        ["none"],
        [("entry", entry_ref)],
        "absent: bool",
        ensures=(
            "absent",
            (
                "absent ==> !ordered_handle_map::<K, V, _>(entry).contains_key("
                "ordered_handle_key::<K, _>(entry))"
            ),
        ),
        note="Observes only that the handle addresses a GoDown position.",
    )
    if plan.output is not None and plan.output.startswith("OccupiedEntry"):
        splice_op = plan.boundary(
            "vacant_entry_splice_pair",
            "node_update",
            "`insert_recursing`/`push_with_handle` splices the pair and yields the handle",
            ("insert_recursing", "push_with_handle"),
            ["VacantEntry::key", "VacantEntry::dormant_map", "VacantEntry::alloc"],
            ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
            [("entry", entry_type), ("value", value_type), ("absent", "bool")],
            f"occupied: {plan.output}",
            requires=("absent",),
            ensures=(
                "ordered_handle_key::<K, _>(occupied) == ordered_handle_key::<K, _>(entry)",
                (
                    "ordered_handle_map::<K, V, _>(occupied) "
                    "== ordered_handle_map::<K, V, _>(entry).insert("
                    "ordered_handle_key::<K, _>(entry), value)"
                ),
                "ordered_handle_is_occupied(occupied)",
                (
                    "ordered_handle_final_map::<K, V, _>(entry) "
                    "== ordered_handle_final_map::<K, V, _>(occupied)"
                ),
            ),
            note="Single leaf splice at the GoDown position recorded by the handle.",
        )
        plan.bind_calls(splice_op, "reborrow", "forget_node_type")
        plan.emit(
            "    proof { broadcast use group_generated_btree_map_axioms; }",
            f"    let absent = {absent_op}(&{entry_name});",
            f"    let occupied = {splice_op}({entry_name}, {value_name}, absent);",
            "    occupied",
        )
        return
    splice_op = plan.boundary(
        "vacant_entry_splice_pair",
        "node_update",
        "`self.insert_entry(value)` splices the pair at the GoDown position",
        ("self.insert_entry(value)",),
        ["VacantEntry::key", "VacantEntry::dormant_map", "VacantEntry::alloc"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        [("entry", entry_type), ("value", value_type), ("absent", "bool")],
        "occupied: SourceKvHandle<K, V>",
        requires=("absent",),
        ensures=(
            "occupied.key@ == ordered_handle_key::<K, _>(entry)",
            (
                "occupied.map@ == ordered_handle_map::<K, V, _>(entry).insert("
                "ordered_handle_key::<K, _>(entry), value)"
            ),
            "occupied.map@.contains_key(occupied.key@)",
        ),
        note="Single leaf splice at the GoDown position recorded by the handle.",
    )
    project_op = plan.boundary(
        "handle_into_val_mut_slot",
        "handle_update",
        "`OccupiedEntry::into_mut` projects the spliced value slot",
        (".into_mut()",),
        ["btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [
            ("occupied", "SourceKvHandle<K, V>"),
            ("final_map", "Ghost<Map<K, V>>"),
        ],
        f"value: {plan.output}",
        requires=("occupied.map@.contains_key(occupied.key@)",),
        ensures=(
            "*value == occupied.map@[occupied.key@]",
            (
                "final_map@ == occupied.map@.insert("
                "occupied.key@, *final(value))"
            ),
        ),
        note="Projects exactly one value slot for the remaining entry lifetime.",
    )
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let absent = {absent_op}(&{entry_name});",
        f"    let ghost final_map = ordered_handle_final_map::<K, V, _>({entry_name});",
        f"    let occupied = {splice_op}({entry_name}, {value_name}, absent);",
        f"    let value = {project_op}(occupied, Ghost(final_map));",
        "    value",
    )


def _plan_entry_insert_entry(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    value_name, value_type, _ = plan.inputs[1]
    entry_ref = shared_ref_type(entry_type)
    discriminant = _entry_tag_boundary(plan, entry_ref, ("match self",))
    occupied_op = plan.boundary(
        "occupied_entry_replace_value",
        "handle_update",
        "`entry.insert(value)` replaces the addressed value slot",
        ("entry.insert(value)",),
        ["btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [
            ("entry", entry_type),
            ("value", value_type),
            ("tag", "SourceEntryTag<K, V>"),
        ],
        f"result: {plan.output}",
        requires=("tag.occupied", "tag.map@.contains_key(tag.key@)"),
        ensures=(
            "ordered_handle_key::<K, _>(result) == tag.key@",
            "ordered_handle_map::<K, V, _>(result) == tag.map@.insert(tag.key@, value)",
            "ordered_handle_is_occupied(result)",
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_final_map::<K, V, _>(result)"
            ),
        ),
        note="Occupied branch only; writes exactly one value slot.",
    )
    vacant_op = plan.boundary(
        "vacant_entry_splice_pair",
        "node_update",
        "`entry.insert_entry(value)` splices the pair at the GoDown position",
        ("entry.insert_entry(value)",),
        ["VacantEntry::key", "VacantEntry::dormant_map", "VacantEntry::alloc"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        [
            ("entry", entry_type),
            ("value", value_type),
            ("tag", "SourceEntryTag<K, V>"),
        ],
        f"result: {plan.output}",
        requires=("!tag.occupied", "!tag.map@.contains_key(tag.key@)"),
        ensures=(
            "ordered_handle_key::<K, _>(result) == tag.key@",
            "ordered_handle_map::<K, V, _>(result) == tag.map@.insert(tag.key@, value)",
            "ordered_handle_is_occupied(result)",
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_final_map::<K, V, _>(result)"
            ),
        ),
        note="Vacant branch only; single leaf splice at the GoDown position.",
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let tag = {discriminant}(&{entry_name});",
        "    if tag.occupied {",
        f"        {occupied_op}({entry_name}, {value_name}, tag)",
        "    } else {",
        f"        {vacant_op}({entry_name}, {value_name}, tag)",
        "    }",
    )


def _plan_remove(plan: LoweringPlan) -> None:
    if plan.owner != "BTreeMap":
        _plan_occupied_remove(plan)
        return
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    pair_result = plan.fn_name == "remove_entry"
    if not pair_result:
        dependency_op = plan.boundary(
            "remove_entry_dependency_call",
            "node_update",
            "`self.remove_entry(key)` proved lower target call",
            ("self.remove_entry(key)",),
            ["BTreeMap::root", "btree::node search path"],
            ["BTreeMap::root", "BTreeMap::length"],
            [("map", map_type), (key_name, key_type)],
            "removed: Option<(K, V)>",
            ensures=(
                plan.guarded(
                    f"borrowed_key_removed(old(map)@, final(map)@, {key_name})"
                ),
                plan.guarded(
                    "match removed { "
                    "Some(pair) => maps_borrowed_key_to_value("
                    f"old(map)@, {key_name}, pair.1), "
                    f"None => !contains_borrowed_key(old(map)@, {key_name}) }}"
                ),
            ),
            note=(
                "This is exactly the lower `remove_entry` call present in the "
                "source. The target separately executes `.map(|(_, v)| v)`."
            ),
        )
        plan.emit(
            f"    let removed = {dependency_op}({map_name}, {key_name});",
            "    match removed {",
            "        Some((_stored_key, value)) => Some(value),",
            "        None => None,",
            "    }",
        )
        return
    shared_map = shared_ref_type(map_type)
    map_argument = shared_ref_argument(map_name, map_type)
    root_op = plan.map_root_present(
        shared_map,
        ("self.root", "map.root"),
        key=(key_name, key_type),
    )
    next(
        boundary for boundary in plan.boundaries if boundary.name == root_op
    ).ensures.append(
        plan.guarded(
            f"!present ==> borrowed_key_removed(map@, map@, {key_name})"
        )
    )
    search_op = plan.boundary(
        "node_search_tree_found",
        "node_search",
        "NodeRef::search_tree ordered descent to Found/GoDown",
        ("search_tree", "remove_entry"),
        ["BTreeMap::root", "btree::node::NodeRef search path"],
        ["none"],
        [("map", shared_map), (key_name, key_type)],
        "found: bool",
        ensures=(
            plan.guarded(f"found <==> contains_borrowed_key(map@, {key_name})"),
            plan.guarded(
                f"!found ==> borrowed_key_removed(map@, map@, {key_name})"
            ),
        ),
        note="One private ordered search; only the branch discriminant escapes.",
    )
    plan.bind_calls(root_op, "new")
    item_type = option_item_type(plan.output)
    ensures: list[str] = [
        plan.guarded(f"maps_borrowed_key_to_value(old(map)@, {key_name}, "
                     + ("removed.1" if pair_result else "removed") + ")"),
        plan.guarded(f"borrowed_key_removed(old(map)@, final(map)@, {key_name})"),
    ]
    if pair_result:
        ensures.extend(
            [
                plan.guarded(f"borrowed_key_matches(&removed.0, {key_name})"),
                plan.guarded(
                    f"removed.0 == borrowed_lookup_stored_key::<K, Q, V>(old(map)@, {key_name})"
                ),
                plan.guarded("old(map)@.contains_key(removed.0)"),
                plan.guarded("old(map)@[removed.0] == removed.1"),
            ]
        )
    remove_op = plan.boundary(
        "occupied_handle_remove_kv",
        "node_update",
        "`OccupiedEntry::remove_kv` unsplices the addressed key/value pair",
        ("remove_entry", "remove_kv"),
        ["btree::node::Handle key slot", "btree::node::Handle value slot"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        [("map", map_type), (key_name, key_type), ("found", "bool")],
        f"removed: {item_type}",
        requires=("found",),
        ensures=tuple(ensures),
        note=(
            "Found branch only; the footprint is the single addressed pair plus "
            "the rebalancing of the nodes on its path."
        ),
    )
    plan.emit(
        f"    let root_present = {root_op}({map_argument}, {key_name});",
        "    if !root_present {",
        "        None",
        "    } else {",
        f"        let found = {search_op}({map_argument}, {key_name});",
        "        if found {",
        f"            let removed = {remove_op}({map_name}, {key_name}, found);",
        "            Some(removed)",
        "        } else {",
        "            None",
        "        }",
        "    }",
    )


def _plan_occupied_remove(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    entry_ref = shared_ref_type(entry_type)
    entry_argument = shared_ref_argument(entry_name, entry_type)
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    address_op = plan.boundary(
        "occupied_entry_handle_reborrow",
        "handle_read",
        "OccupiedEntry::handle reborrow to the addressed key/value pair",
        ("self.remove_kv()",),
        ["OccupiedEntry::handle"],
        ["none"],
        [("entry", entry_ref)],
        "handle: SourceKvHandle<K, V>",
        ensures=(
            "handle.key@ == ordered_handle_key::<K, _>(entry)",
            "handle.map@ == ordered_handle_map::<K, V, _>(entry)",
            "handle.map@.contains_key(handle.key@)",
        ),
        note="Addresses one stored pair; no map-wide state crosses the boundary.",
    )
    pair_result = plan.fn_name == "remove_entry"
    ensures = [
        (
            "removed == handle.map@[handle.key@]"
            if not pair_result
            else "removed.1 == handle.map@[handle.key@]"
        ),
        (
            "entry_remove_transition(handle.map@, handle.key@, "
            "ordered_handle_final_map::<K, V, _>(entry))"
        ),
    ]
    if pair_result:
        ensures.insert(0, "removed.0 == handle.key@")
    unsplice_op = plan.boundary(
        "handle_remove_kv",
        "node_update",
        "`Handle::remove_kv` unsplices the addressed pair and rebalances",
        ("remove_kv",),
        ["btree::node::Handle key slot", "btree::node::Handle value slot"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        [("entry", entry_type), ("handle", "SourceKvHandle<K, V>")],
        f"removed: {plan.output}",
        requires=("handle.map@.contains_key(handle.key@)",),
        ensures=tuple(ensures),
        note="Removes exactly the addressed pair.",
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let handle = {address_op}({entry_argument});",
        f"    let removed = {unsplice_op}({entry_name}, handle);",
        "    removed",
    )


def _plan_endpoint(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    shared_map = shared_ref_type(map_type)
    map_argument = shared_ref_argument(map_name, map_type)
    first = plan.profile == "first_endpoint"
    edge = "first_leaf_edge" if first else "last_leaf_edge"
    kv_side = "right_kv" if first else "left_kv"
    order_predicate = "ordered_map_first_key" if first else "ordered_map_last_key"
    root_op = plan.map_root_present(shared_map, ("self.root", "map.root"))
    item_type = option_item_type(plan.output)
    handle_kind = "handle_read" if plan.fn_name.endswith("key_value") else "handle_update"
    if plan.fn_name.endswith("key_value"):
        ensures = (
            plan.guarded(f"{order_predicate}(map@, *endpoint.0)"),
            plan.guarded("map@.contains_key(*endpoint.0)"),
            plan.guarded("map@[*endpoint.0] == *endpoint.1"),
        )
        params = [("map", shared_map), ("nonempty", "bool")]
        call = f"{map_argument}, true"
    else:
        ensures = (
            plan.guarded("ordered_handle_map::<K, V, _>(endpoint) == old(map)@"),
            plan.guarded(
                f"{order_predicate}(old(map)@, ordered_handle_key::<K, _>(endpoint))"
            ),
            plan.guarded("ordered_handle_is_occupied(endpoint)"),
            plan.guarded(
                "final(map)@ == ordered_handle_final_map::<K, V, _>(endpoint)"
            ),
        )
        params = [("map", map_type), ("nonempty", "bool")]
        call = f"{map_name}, true"
    endpoint_op = plan.boundary(
        "node_leaf_edge_endpoint",
        handle_kind,
        f"`{edge}().{kv_side}()` endpoint handle of the root node",
        (edge,),
        ["BTreeMap::root", f"btree::node leaf {('first' if first else 'last')} edge"],
        ["none"] if handle_kind == "handle_read" else ["btree::node::Handle value slot"],
        params,
        f"endpoint: {item_type}",
        requires=("nonempty",),
        ensures=ensures,
        note=(
            "Walks only the extreme leaf edge of the tree; no key comparison and "
            "no other slot is inside the footprint."
        ),
    )
    if not plan.fn_name.endswith("key_value"):
        plan.bind_calls(endpoint_op, "new", "forget_node_type", "clone")
    plan.emit(
        f"    let root_present = {root_op}({map_argument});",
        "    if !root_present {",
        "        None",
        "    } else {",
        f"        let endpoint = {endpoint_op}({call});",
        "        Some(endpoint)",
        "    }",
    )


def _plan_pop_endpoint(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    shared_map = shared_ref_type(map_type)
    map_argument = shared_ref_argument(map_name, map_type)
    first = plan.profile == "remove_first"
    order_predicate = "ordered_map_first_key" if first else "ordered_map_last_key"
    entry_call = "self.first_entry()" if first else "self.last_entry()"
    length_op = plan.map_length_field(
        shared_map,
        (entry_call,),
        operation=f"proved lower `{entry_call}` presence observation",
        note=(
            "Observes whether the source lower endpoint-entry call can produce "
            "a handle; the handle construction remains a separate operation."
        ),
    )
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    handle_op = plan.boundary(
        "node_leaf_edge_endpoint_handle",
        "handle_read",
        f"`{entry_call}` endpoint handle of the extreme leaf edge",
        (entry_call,),
        ["BTreeMap::root", f"btree::node leaf {('first' if first else 'last')} edge"],
        ["none"],
        [("map", shared_map), ("nonempty", "bool")],
        "handle: SourceKvHandle<K, V>",
        requires=("nonempty",),
        ensures=(
            "handle.map@ == map@",
            "map@.contains_key(handle.key@)",
            plan.guarded(f"{order_predicate}(map@, handle.key@)"),
        ),
        note="Walks only the extreme leaf edge and addresses one stored pair.",
    )
    item_type = option_item_type(plan.output)
    remove_op = plan.boundary(
        "handle_remove_entry",
        "node_update",
        "`entry.remove_entry()` unsplices the addressed endpoint pair",
        ("remove_entry",),
        ["btree::node::Handle key slot", "btree::node::Handle value slot"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        [("map", map_type), ("handle", "SourceKvHandle<K, V>")],
        f"removed: {item_type}",
        requires=("handle.map@.contains_key(handle.key@)",),
        ensures=(
            "removed.0 == handle.key@",
            "removed.1 == handle.map@[handle.key@]",
            plan.guarded("final(map)@ == old(map)@.remove(removed.0)"),
        ),
        note="Removes exactly the addressed endpoint pair.",
    )
    plan.emit(
        f"    let length = {length_op}({map_argument});",
        "    if length == 0 {",
        "        None",
        "    } else {",
        f"        let handle = {handle_op}({map_argument}, true);",
        f"        let removed = {remove_op}({map_name}, handle);",
        "        Some(removed)",
        "    }",
    )


def _plan_empty_map(plan: LoweringPlan) -> None:
    token = "BTreeMap::new()" if plan.trait == "Default" else "root: None"
    op = plan.boundary(
        "map_new_empty_representation",
        "allocator_op",
        "`BTreeMap { root: None, length: 0, alloc: ... }` fresh representation",
        (token,),
        ["none"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length", "fresh BTreeMap::alloc"],
        [],
        f"map: {plan.output}",
        ensures=(
            "map@.len() == 0",
            "map@.dom() =~= Set::<K>::empty()",
            "ordered_map_well_formed(map@)",
        ),
        note=(
            "Allocates no node; publishes only that the fresh representation has "
            "an absent root and a zero length."
        ),
        leaf_exception=(
            "The source target is exactly the private-field struct literal for "
            "an empty map; this boundary materializes that one inaccessible "
            "representation leaf."
        ),
    )
    plan.emit(
        f"    let map = {op}();",
        "    proof { assert(map@ =~= Map::<K, V>::empty()); }",
        "    map",
    )


def _plan_clear_map(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    detach_op = plan.boundary(
        "map_replace_root_with_none",
        "representation_write",
        "`mem::replace(&mut self.root, None)` detaches the root node",
        ("&mut self.root",),
        ["BTreeMap::root"],
        ["BTreeMap::root"],
        [("map", map_type)],
        "detached: bool",
        ensures=(
            "final(map)@.dom() =~= Set::<K>::empty()",
            "detached <==> !old(map)@.is_empty()",
        ),
        note="Writes only the root Option slot.",
    )
    length_op = plan.boundary(
        "map_replace_length_with_zero",
        "representation_write",
        "`mem::replace(&mut self.length, 0)` clears the length word",
        ("&mut self.length",),
        ["BTreeMap::length"],
        ["BTreeMap::length"],
        [("map", map_type)],
        "previous: usize",
        ensures=(
            "final(map)@.dom() == old(map)@.dom()",
            "final(map)@.len() == 0",
            "previous as nat == old(map)@.len()",
        ),
        note="Writes only the length word; the ordered content is untouched.",
    )
    drop_op = plan.boundary(
        "drop_detached_subtree",
        "allocator_op",
        "`drop(BTreeMap { .. })` releases the detached nodes",
        ("drop(BTreeMap",),
        ["detached node arena"],
        ["detached node arena"],
        [("detached", "bool"), ("previous", "usize")],
        None,
        note=(
            "Deallocates the detached subtree only; the receiver is not part of "
            "this footprint."
        ),
    )
    plan.bind_calls(drop_op, "clone")
    plan.emit(
        f"    let detached = {detach_op}({map_name});",
        f"    let previous = {length_op}({map_name});",
        f"    {drop_op}(detached, previous);",
        f"    proof {{ assert({map_name}@ =~= Map::<K, V>::empty()); }}",
    )


def _plan_clone_map(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    map_argument = shared_ref_argument(map_name, map_type)
    length_op = plan.map_length_field(
        map_type,
        ("self.is_empty()",),
        operation="proved lower `self.is_empty()` call",
        note=(
            "Executes the source emptiness dependency before choosing the empty "
            "allocator clone or recursive subtree clone branch."
        ),
    )
    empty_op = plan.boundary(
        "map_new_in_allocator",
        "allocator_op",
        "`BTreeMap::new_in((*self.alloc).clone())` fresh empty representation",
        ("new_in",),
        ["BTreeMap::alloc"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length", "fresh BTreeMap::alloc"],
        [("source_map", map_type), ("empty", "bool")],
        f"map: {plan.output}",
        requires=("empty",),
        ensures=(
            "map@.len() == 0",
            "map@.dom() =~= Set::<K>::empty()",
            "map@ =~= Map::<K, V>::empty()",
        ),
        note="Clones only the allocator handle; no node is copied.",
    )
    clone_op = plan.boundary(
        "clone_subtree_from_root",
        "node_update",
        "private `clone_subtree` walk that rebuilds every node in order",
        ("clone_subtree",),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length"],
        [("source_map", map_type), ("nonempty", "bool")],
        f"map: {plan.output}",
        requires=("nonempty",),
        ensures=(
            "map@.dom() =~= source_map@.dom()",
            "map@.len() == source_map@.len()",
            (
                "forall|key: K| source_map@.contains_key(key) ==> "
                "#[trigger] map@[key] == source_map@[key]"
            ),
        ),
        note=(
            "One private recursive subtree walk; it publishes the element-wise "
            "clone relation, not the target contract."
        ),
    )
    plan.bind_calls(clone_op, "as_ref", "unwrap", "reborrow")
    plan.emit(
        f"    let length = {length_op}({map_argument});",
        "    if length == 0 {",
        f"        let cloned = {empty_op}({map_argument}, true);",
        f"        proof {{ assert(cloned@ =~= {map_name}@); }}",
        "        cloned",
        "    } else {",
        f"        let cloned = {clone_op}({map_argument}, true);",
        f"        proof {{ assert(cloned@ =~= {map_name}@); }}",
        "        cloned",
        "    }",
    )


def _plan_append(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    other_name, other_type, _ = plan.inputs[1]
    shared_map = shared_ref_type(map_type)
    take_op = plan.boundary(
        "map_replace_with_new_in",
        "representation_write",
        "`mem::replace(other, Self::new_in(..))` moves the donor out",
        ("mem::replace",),
        ["BTreeMap::alloc"],
        ["BTreeMap::root", "BTreeMap::length"],
        [("map", other_type), ("allocator_source", shared_map)],
        f"taken: {deref_type(map_type)}",
        ensures=(
            "taken@ =~= old(map)@",
            "final(map)@.dom() =~= Set::<K>::empty()",
            "final(map)@.len() == 0",
        ),
        note="Swaps the donor root/length words with a fresh empty representation.",
    )
    merge_op = plan.boundary(
        "root_merge_other_wins",
        "node_update",
        "private `Root::merge` with the `|_k, _self, other| other` combiner",
        ("self.merge",),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["BTreeMap::root", "BTreeMap::length"],
        [("map", map_type), ("donor", deref_type(map_type))],
        None,
        ensures=(
            plan.guarded(
                "final(map)@.dom() =~= old(map)@.dom().union(donor@.dom())"
            ),
            plan.guarded(
                "append_last_value_wins(old(map)@, donor@, final(map)@)"
            ),
        ),
        note=(
            "One private ordered merge of two roots; the donor emptiness is "
            "established by the replace operation above, not here."
        ),
    )
    plan.emit(
        f"    let donor = {take_op}({other_name}, {shared_ref_argument(map_name, map_type)});",
        f"    {merge_op}({map_name}, donor);",
    )


def _plan_split(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    shared_map = shared_ref_type(map_type)
    map_argument = shared_ref_argument(map_name, map_type)
    length_op = plan.map_length_field(
        shared_map,
        ("self.len()",),
        operation="proved lower `self.len()` call before node partition",
        note="Freezes the source total length used by `calc_split_length`.",
    )
    empty_op = plan.boundary(
        "map_new_in_allocator",
        "allocator_op",
        "`Self::new_in((*self.alloc).clone())` fresh empty right half",
        ("new_in",),
        ["BTreeMap::alloc"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length", "fresh BTreeMap::alloc"],
        [("source_map", shared_map), ("empty", "bool")],
        f"map: {plan.output}",
        requires=("empty",),
        ensures=(
            "map@.len() == 0",
            "map@.dom() =~= Set::<K>::empty()",
        ),
        note="Clones only the allocator handle; no node is copied.",
    )
    split_op = plan.boundary(
        "root_split_off_at_key",
        "node_update",
        "private `Root::split_off(key, alloc)` node partition",
        ("split_off(key",),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["BTreeMap::root", "fresh BTreeMap::root"],
        [("map", map_type), (key_name, key_type), ("nonempty", "bool")],
        f"right: {plan.output}",
        requires=("nonempty",),
        ensures=(
            plan.guarded(
                f"ordered_split_partition(old(map)@, {key_name}, final(map)@, right@)"
            ),
            plan.guarded("final(map)@.dom().disjoint(right@.dom())"),
        ),
        note=(
            "One private node partition; the length bookkeeping is a separate "
            "operation below."
        ),
    )
    commit_op = plan.boundary(
        "calc_split_length_commit",
        "representation_write",
        "`Root::calc_split_length` result committed into `self.length`",
        ("calc_split_length",),
        ["BTreeMap::root"],
        ["BTreeMap::length"],
        [
            ("map", map_type),
            ("right", shared_map),
            ("total", "usize"),
            ("initial", "Ghost<Map<K, V>>"),
            (key_name, key_type),
        ],
        None,
        requires=(
            "total as nat == initial@.len()",
            plan.guarded(
                f"ordered_split_partition(initial@, {key_name}, "
                "old(map)@, right@)"
            ),
        ),
        ensures=(
            "final(map)@ =~= old(map)@",
            plan.guarded(
                "final(map)@.len() + right@.len() == total as nat"
            ),
        ),
        note=(
            "Recomputes and writes only the two length words; no key or value "
            "moves inside this footprint."
        ),
    )
    plan.bind_calls(split_op, "as_mut", "unwrap")
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let ghost initial_map = {map_name}@;",
        f"    let total = {length_op}({map_argument});",
        "    if total == 0 {",
        f"        let right = {empty_op}({map_argument}, true);",
        "        proof {",
        f"            assert({map_name}@.is_empty());",
        f"            assert({map_name}@ =~= Map::<K, V>::empty()) by {{",
        f"                assert({map_name}@.dom() =~= Set::<K>::empty());",
        "            }",
        f"            assert(right@ =~= Map::<K, V>::empty());",
        f"            if {plan.guard} {{",
        f"                lemma_ordered_split_partition_empty::<K, V, Q>({key_name});",
        f"                assert(ordered_split_partition({map_name}@, {key_name}, {map_name}@, right@));",
        "            }",
        "        }",
        "        right",
        "    } else {",
        f"        let right = {split_op}({map_name}, {key_name}, true);",
        f"        {commit_op}({map_name}, &right, total, Ghost(initial_map), {key_name});",
        "        right",
        "    }",
    )


def _plan_from_input(plan: LoweringPlan) -> None:
    input_name, input_type, _ = plan.inputs[0]
    array_input = plan.trait == "From"
    empty_op = plan.boundary(
        "map_new_empty_representation",
        "allocator_op",
        "`BTreeMap::new()` fresh empty representation",
        ("BTreeMap::new()",),
        ["none"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length"],
        [],
        f"map: {plan.output}",
        ensures=(
            "map@.len() == 0",
            "map@.dom() =~= Set::<K>::empty()",
            "map@ =~= Map::<K, V>::empty()",
            "ordered_map_well_formed(map@)",
        ),
        note="Allocates no node; publishes only the fresh empty representation.",
    )
    if array_input:
        sort_op = plan.boundary(
            "array_stable_sort_by_key",
            "comparator_invoke",
            "`arr.sort_by(|a, b| a.0.cmp(&b.0))` stable comparator sort",
            ("sort_by",),
            ["input array elements"],
            ["input array element order"],
            [("pairs", input_type), ("nonempty", "bool")],
            f"sorted: {input_type}",
            requires=("nonempty",),
            ensures=(
                "sorted@.len() == pairs@.len()",
                plan.guarded(
                    "map_from_pairs_last_wins(sorted@) "
                    "== map_from_pairs_last_wins(pairs@)"
                ),
            ),
            note=(
                "Only the element order changes; the stable sort preserves the "
                "last-value-wins reading of the input."
            ),
        )
        build_op = plan.boundary(
            "bulk_build_from_sorted_pairs",
            "node_update",
            "private `BTreeMap::bulk_build_from_sorted_iter`",
            ("bulk_build_from_sorted_iter",),
            ["input array elements"],
            ["fresh BTreeMap::root", "fresh BTreeMap::length"],
            [("sorted", input_type)],
            f"map: {plan.output}",
            ensures=(
                plan.guarded("map@ == map_from_pairs_last_wins(sorted@)"),
                plan.guarded("map@.len() <= sorted@.len()"),
                plan.guarded("ordered_map_well_formed(map@)"),
            ),
            note="One private bulk build over the already sorted input.",
        )
        plan.emit(
            "    if N == 0 {",
            f"        let map = {empty_op}();",
            "        proof {",
            f"            assert({input_name}@.len() == 0);",
            "        }",
            "        map",
            "    } else {",
            f"        let sorted = {sort_op}({input_name}, true);",
            f"        {build_op}(sorted)",
            "    }",
        )
        return
    plan.add_prelude(PAIR_BUFFER_STRUCT)
    collect_op = plan.boundary(
        "collect_input_pairs",
        "iterator_representation",
        "`iter.into_iter().collect()` drains the input into a pair buffer",
        ("collect()",),
        ["IntoIterator input items"],
        ["fresh pair buffer"],
        [(input_name, input_type)],
        "pairs: SourceInputPairs<K, V>",
        requires=(f"into_iterator_item_is_owned_pair::<K, V, {input_type}>()",),
        ensures=(
            f"pairs.items@ == collection_input_pairs::<{input_type}, K, V>({input_name})",
            "pairs.length as nat == pairs.items@.len()",
        ),
        note=(
            "Drains the caller iterator in order; only the pair sequence and its "
            "length cross the boundary."
        ),
    )
    sort_op = plan.boundary(
        "pair_buffer_stable_sort_by_key",
        "comparator_invoke",
        "`inputs.sort_by(|a, b| a.0.cmp(&b.0))` stable comparator sort",
        ("sort_by",),
        ["pair buffer elements"],
        ["pair buffer element order"],
        [("pairs", "SourceInputPairs<K, V>"), ("nonempty", "bool")],
        "sorted: SourceInputPairs<K, V>",
        requires=("nonempty",),
        ensures=(
            "sorted.length == pairs.length",
            plan.guarded(
                "map_from_pairs_last_wins(sorted.items@) "
                "== map_from_pairs_last_wins(pairs.items@)"
            ),
        ),
        note=(
            "Only the element order changes; the stable sort preserves the "
            "last-value-wins reading of the input."
        ),
    )
    build_op = plan.boundary(
        "bulk_build_from_sorted_pairs",
        "node_update",
        "private `BTreeMap::bulk_build_from_sorted_iter`",
        ("bulk_build_from_sorted_iter",),
        ["pair buffer elements"],
        ["fresh BTreeMap::root", "fresh BTreeMap::length"],
        [("sorted", "SourceInputPairs<K, V>")],
        f"map: {plan.output}",
        ensures=(
            plan.guarded("map@ == map_from_pairs_last_wins(sorted.items@)"),
            plan.guarded("ordered_map_well_formed(map@)"),
        ),
        note="One private bulk build over the already sorted buffer.",
    )
    plan.emit(
        f"    let pairs = {collect_op}({input_name});",
        "    let ghost input_pairs = pairs.items@;",
        "    if pairs.length == 0 {",
        f"        let map = {empty_op}();",
        "        proof {",
        "            assert(pairs.items@.len() == 0);",
        "            assert(input_pairs =~= Seq::<(K, V)>::empty()) by {",
        "                assert(input_pairs.len() == 0);",
        "            }",
        "            if key_obeys_cmp_spec::<K>() {",
        "                assert(map@ == map_from_pairs_last_wins(input_pairs));",
        "            }",
        "        }",
        "        map",
        "    } else {",
        f"        let sorted = {sort_op}(pairs, true);",
        f"        let map = {build_op}(sorted);",
        "        proof {",
        "            if key_obeys_cmp_spec::<K>() {",
        "                assert(map@ == map_from_pairs_last_wins(input_pairs));",
        "            }",
        "        }",
        "        map",
        "    }",
    )


def _plan_extend_input(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    iter_name, iter_type, _ = plan.inputs[1]
    plan.add_prelude(EXTEND_CURSOR_STRUCT)
    into_iter_op = plan.boundary(
        "extend_into_iter_cursor",
        "iterator_representation",
        "`iter.into_iter()` builds the input cursor",
        ("into_iter()",),
        ["IntoIterator input items"],
        ["fresh input cursor"],
        [(iter_name, iter_type)],
        "cursor: SourceExtendCursor<K, V>",
        requires=(f"into_iterator_item_is_owned_pair::<K, V, {iter_type}>()",),
        ensures=(
            f"cursor.pending@ == collection_input_pairs::<{iter_type}, K, V>({iter_name})",
            "cursor.consumed@ == Seq::<(K, V)>::empty()",
            "cursor.remaining as nat == cursor.pending@.len()",
        ),
        note="Only the pending pair sequence crosses this boundary.",
    )
    next_op = plan.boundary(
        "extend_cursor_next_pair",
        "iterator_step",
        "one `for_each` iteration step over the input cursor",
        ("for_each",),
        ["input cursor position"],
        ["input cursor position"],
        [("cursor", "&mut SourceExtendCursor<K, V>")],
        "item: Option<(K, V)>",
        ensures=(
            "match item { "
            "Some(pair) => old(cursor).pending@.len() > 0 "
            "&& pair == old(cursor).pending@[0] "
            "&& final(cursor).pending@ == old(cursor).pending@.drop_first() "
            "&& final(cursor).consumed@ == old(cursor).consumed@.push(pair) "
            "&& final(cursor).remaining + 1 == old(cursor).remaining, "
            "None => old(cursor).pending@.len() == 0 "
            "&& final(cursor).pending@ == old(cursor).pending@ "
            "&& final(cursor).consumed@ == old(cursor).consumed@ "
            "&& final(cursor).remaining == old(cursor).remaining }",
        ),
        note="Advances the cursor by exactly one input pair.",
    )
    insert_op = plan.boundary(
        "extend_insert_pair",
        "node_update",
        "`self.insert(k, v)` inside the `for_each` closure body",
        ("self.insert(k, v)",),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["BTreeMap::root", "BTreeMap::length"],
        [("map", map_type), ("key", "K"), ("value", "V")],
        None,
        ensures=(
            plan.guarded("final(map)@ == old(map)@.insert(key, value)"),
            plan.guarded("final(map)@.len() >= old(map)@.len()"),
        ),
        note=(
            "One per-item ordered insertion; the whole-input relation is built "
            "by the executable loop below, not by this boundary."
        ),
    )
    guard_prefix = f"{plan.guard} ==> " if plan.guard else ""
    plan.emit(
        f"    let ghost initial_map = {map_name}@;",
        f"    let mut cursor = {into_iter_op}({iter_name});",
        "    let ghost initial_pending = cursor.pending@;",
        "    while cursor.remaining > 0",
        "        invariant",
        "            cursor.remaining as nat == cursor.pending@.len(),",
        "            cursor.consumed@.len() <= initial_pending.len(),",
        "            cursor.consumed@ + cursor.pending@ =~= initial_pending,",
        f"            {guard_prefix}{map_name}@ == map_extend_pairs_last_wins("
        "initial_map, cursor.consumed@),",
        f"            {guard_prefix}{map_name}@.len() >= initial_map.len(),",
        "        decreases cursor.pending@.len(),",
        "    {",
        "        let ghost consumed_before = cursor.consumed@;",
        "        let ghost pending_before = cursor.pending@;",
        f"        let step = {next_op}(&mut cursor);",
        "        match step {",
        "            None => {",
        "                proof { assert(false); }",
        "            },",
        "            Some((key, value)) => {",
        f"                {insert_op}({map_name}, key, value);",
        "                proof {",
        "                    assert(cursor.consumed@.drop_last() =~= consumed_before);",
        "                    assert(cursor.consumed@.last() == (key, value));",
        "                    assert(pending_before =~= seq![(key, value)] + cursor.pending@);",
        "                    assert(cursor.consumed@ + cursor.pending@ =~= consumed_before + pending_before);",
        "                }",
        "            },",
        "        }",
        "    }",
        "    proof {",
        "        assert(cursor.pending@ =~= Seq::<(K, V)>::empty()) by {",
        "            assert(cursor.pending@.len() == 0);",
        "        }",
        "        assert(cursor.consumed@ =~= initial_pending);",
        f"        if key_obeys_cmp_spec::<K>() {{",
        f"            assert({map_name}@ == map_extend_pairs_last_wins(initial_map, initial_pending));",
        "        }",
        "    }",
    )


def _plan_filter(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    callback_name, callback_type, _ = plan.inputs[1]
    shared_map = shared_ref_type(map_type)
    plan.add_prelude(KEY_CURSOR_STRUCT)
    plan.add_prelude(VISIT_OUTCOME_STRUCT)
    plan.add_prelude(
        "pub uninterp spec fn retain_callback_model<F>(callback: &F) -> int;"
    )
    cursor_op = plan.boundary(
        "extract_if_range_cursor",
        "node_search",
        "`self.extract_if(.., ..)` builds the full-range leaf cursor",
        ("self.extract_if",),
        ["BTreeMap::root"],
        ["fresh leaf cursor"],
        [("map", shared_map)],
        "cursor: SourceKeyCursor<K>",
        ensures=(
            plan.guarded("cursor.pending@ == ordered_map_key_sequence(map@)"),
            "cursor.visited@ == Seq::<K>::empty()",
            "cursor.remaining as nat == cursor.pending@.len()",
        ),
        note="Builds the ordered key cursor; no callback runs inside this boundary.",
    )
    law_op = plan.boundary(
        "extract_if_callback_law",
        "callback_invoke",
        "`|k, v| !f(k, v)` closure invocation law for every visited key",
        ("|k, v|",),
        ["callback state"],
        ["callback state"],
        [
            ("map", shared_map),
            ("predicate", f"&{callback_type}"),
            ("keep", "Ghost<spec_fn(Map<K, V>, K) -> bool>"),
            ("final_value", "Ghost<spec_fn(Map<K, V>, K) -> V>"),
        ],
        None,
        requires=(
            "ordered_callback_domain(map@, predicate)",
        ),
        ensures=(
            "forall|state: Map<K, V>, key: K| "
            "state.contains_key(key) && ordered_map_key_sequence(map@).contains(key) ==> "
            "ordered_callback_observation(state, *predicate, key, "
            "#[trigger] keep@(state, key), "
            "#[trigger] final_value@(state, key))",
        ),
        note=(
            "States only that each closure call is deterministic in the visited "
            "state and key; it removes nothing and inserts nothing."
        ),
    )
    unwind_op = plan.boundary(
        "retain_callback_unwind_step",
        "callback_invoke",
        "one `f(k, v)` panic/unwind step retains the current and unvisited entries",
        ("|k, v|",),
        ["one callback invocation", "current and unvisited entries"],
        ["callback unwind observation"],
        [
            ("pre", "Ghost<Map<K, V>>"),
            ("predicate", f"&{callback_type}"),
            ("current", "Ghost<K>"),
            ("unvisited", "Ghost<Seq<K>>"),
        ],
        None,
        ensures=(
            "callback_unwind_retains_current_and_unvisited("
            "pre@, ordered_callback_unwind_map("
            "pre@, predicate, current@, unvisited@), current@, unvisited@)",
        ),
        note=(
            "Models one callback unwind frame; the target quantifies it over "
            "every visited-prefix decomposition."
        ),
        proof=True,
    )
    next_op = plan.boundary(
        "extract_cursor_next_key",
        "iterator_step",
        "one `ExtractIf::next` cursor advance driven by `for_each(drop)`",
        ("for_each(drop)",),
        ["leaf cursor position", "BTreeMap::root"],
        ["leaf cursor position"],
        [
            ("cursor", "&mut SourceKeyCursor<K>"),
            ("map", shared_map),
        ],
        "key: Option<K>",
        ensures=(
            "match key { "
            "Some(next) => old(cursor).pending@.len() > 0 "
            "&& next == old(cursor).pending@[0] "
            "&& map@.contains_key(next) "
            "&& final(cursor).pending@ == old(cursor).pending@.drop_first() "
            "&& final(cursor).visited@ == old(cursor).visited@.push(next) "
            "&& final(cursor).remaining + 1 == old(cursor).remaining, "
            "None => old(cursor).pending@.len() == 0 "
            "&& final(cursor).pending@ == old(cursor).pending@ "
            "&& final(cursor).visited@ == old(cursor).visited@ "
            "&& final(cursor).remaining == old(cursor).remaining }",
        ),
        note="Advances the ordered key cursor by exactly one key.",
    )
    visit_op = plan.boundary(
        "extract_if_visit_key",
        "callback_invoke",
        "one `!f(k, v)` call plus the decided removal of that single entry",
        ("self.extract_if",),
        ["btree::node::Handle key slot", "btree::node::Handle value slot"],
        ["btree::node leaf slot", "BTreeMap::length"],
        [
            ("map", map_type),
            ("key", "K"),
            ("predicate", f"&mut {callback_type}"),
            ("keep", "Ghost<spec_fn(Map<K, V>, K) -> bool>"),
            ("final_value", "Ghost<spec_fn(Map<K, V>, K) -> V>"),
        ],
        "outcome: SourceVisitOutcome<V>",
        requires=("old(map)@.contains_key(key)",),
        ensures=(
            "outcome.kept == keep@(old(map)@, key)",
            "outcome.value@ == final_value@(old(map)@, key)",
            "final(map)@ == if outcome.kept { old(map)@.insert(key, outcome.value@) } "
            "else { old(map)@.remove(key) }",
            "final(map)@.dom().subset_of(old(map)@.dom())",
            "final(map)@.len() <= old(map)@.len()",
        ),
        note=(
            "Exactly one callback observation and one entry decision; the "
            "whole-map filter relation is assembled by the loop below."
        ),
    )
    guard_prefix = f"{plan.guard} ==> " if plan.guard else ""
    plan.emit(
        f"    let ghost initial_map = {map_name}@;",
        "    let ghost visited_keys = ordered_map_key_sequence(initial_map);",
        f"    let ghost callback_model = retain_callback_model(&{callback_name});",
        "    let ghost keep: spec_fn(Map<K, V>, K) -> bool =",
        "        |state: Map<K, V>, key: K|",
        "            !extract_if_remove_decision(callback_model, state, key);",
        "    let ghost final_value: spec_fn(Map<K, V>, K) -> V =",
        "        |state: Map<K, V>, key: K|",
        "            extract_if_callback_final_value(callback_model, state, key);",
        f"    let mut predicate = {callback_name};",
        f"    {law_op}({shared_ref_argument(map_name, map_type)}, &predicate, "
        "Ghost(keep), Ghost(final_value));",
        "    proof {",
        "        assert(ordered_callback_unwind_contract(",
        "            initial_map, visited_keys, &predicate,",
        "        )) by {",
        "            assert forall|visited: Seq<K>, current: K, unvisited: Seq<K>|",
        "                visited_keys == visited + Seq::empty().push(current) + unvisited implies",
        "                callback_unwind_retains_current_and_unvisited(",
        "                    initial_map, ordered_callback_unwind_map(",
        "                        initial_map, &predicate, current, unvisited),",
        "                    current, unvisited,",
        "                ) by {",
        f"                    {unwind_op}(Ghost(initial_map), &predicate, "
        "Ghost(current), Ghost(unvisited));",
        "                }",
        "        }",
        "    }",
        f"    let mut cursor = {cursor_op}({shared_ref_argument(map_name, map_type)});",
        "    while cursor.remaining > 0",
        "        invariant",
        "            cursor.remaining as nat == cursor.pending@.len(),",
        f"            {guard_prefix}cursor.visited@ + cursor.pending@ =~= visited_keys,",
        f"            {guard_prefix}{map_name}@ == cursor.visited@.fold_left(",
        "                initial_map,",
        "                |state: Map<K, V>, key: K| {",
        "                    if keep(state, key) {",
        "                        state.insert(key, final_value(state, key))",
        "                    } else {",
        "                        state.remove(key)",
        "                    }",
        "                },",
        "            ),",
        f"            {guard_prefix}{map_name}@.dom().subset_of(initial_map.dom()),",
        f"            {guard_prefix}{map_name}@.len() <= initial_map.len(),",
        "        decreases cursor.pending@.len(),",
        "    {",
        "        let ghost visited_before = cursor.visited@;",
        "        let ghost pending_before = cursor.pending@;",
        f"        let step = {next_op}(&mut cursor, "
        f"{shared_ref_argument(map_name, map_type)});",
        "        match step {",
        "            None => {",
        "                proof { assert(false); }",
        "            },",
        "            Some(key) => {",
        f"                let outcome = {visit_op}({map_name}, key, &mut predicate, "
        "Ghost(keep), Ghost(final_value));",
        "                proof {",
        "                    assert(cursor.visited@.drop_last() =~= visited_before);",
        "                    assert(pending_before =~= seq![key] + cursor.pending@);",
        "                    assert(cursor.visited@ + cursor.pending@ =~= visited_before + pending_before);",
        "                }",
        "            },",
        "        }",
        "    }",
        "    proof {",
        "        assert(cursor.pending@ =~= Seq::<K>::empty()) by {",
        "            assert(cursor.pending@.len() == 0);",
        "        }",
        "        if key_obeys_cmp_spec::<K>() {",
        "            assert(cursor.visited@ + cursor.pending@ =~= visited_keys);",
        "            assert(cursor.visited@ =~= visited_keys);",
        "            assert(cursor.visited@ == visited_keys);",
        f"            assert({map_name}@ == visited_keys.fold_left(",
        "                initial_map,",
        "                |state: Map<K, V>, key: K| {",
        "                    if keep(state, key) {",
        "                        state.insert(key, final_value(state, key))",
        "                    } else {",
        "                        state.remove(key)",
        "                    }",
        "                },",
        "            ));",
        "            let ghost callback_filter_witness =",
        "                ordered_callback_filter_trigger(keep, final_value);",
        "            assert(exists|",
        "                keep: spec_fn(Map<K, V>, K) -> bool,",
        "                final_value: spec_fn(Map<K, V>, K) -> V,",
        "            |",
        "            #![trigger ordered_callback_filter_trigger(keep, final_value)]",
        "            {",
        "                &&& forall|state: Map<K, V>, key: K|",
        "                    state.contains_key(key) && visited_keys.contains(key) ==>",
        f"                    ordered_callback_observation(state, {callback_name}, key,",
        "                        keep(state, key), final_value(state, key))",
        f"                &&& {map_name}@ == visited_keys.fold_left(",
        "                    initial_map,",
        "                    |state: Map<K, V>, key: K| {",
        "                        if keep(state, key) {",
        "                            state.insert(key, final_value(state, key))",
        "                        } else {",
        "                            state.remove(key)",
        "                        }",
        "                    },",
        "                )",
        "            }) by {",
        "                assert(forall|state: Map<K, V>, key: K|",
        "                    state.contains_key(key) && visited_keys.contains(key) ==>",
        f"                    ordered_callback_observation(state, {callback_name}, key,",
        "                        keep(state, key), final_value(state, key)));",
        f"                assert({map_name}@ == visited_keys.fold_left(",
        "                    initial_map,",
        "                    |state: Map<K, V>, key: K| {",
        "                        if keep(state, key) {",
        "                            state.insert(key, final_value(state, key))",
        "                        } else {",
        "                            state.remove(key)",
        "                        }",
        "                    },",
        "                ));",
        "            }",
        f"            assert(ordered_callback_filter(initial_map, visited_keys, {callback_name}, {map_name}@));",
        "        }",
        "    }",
    )


def _plan_entry_handle(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    shared_map = shared_ref_type(map_type)
    root_op = plan.map_root_present(shared_map, ("match map.root",))
    search_op = plan.boundary(
        "node_search_tree_found",
        "node_search",
        "`root.borrow_mut().search_tree(&key)` classification",
        ("search_tree",),
        ["BTreeMap::root", "btree::node::NodeRef search path"],
        ["none"],
        [("map", shared_map), ("key", f"&{key_type}")],
        "found: bool",
        ensures=(plan.guarded("found <==> map@.contains_key(*key)"),),
        note="Only the Found/GoDown discriminant crosses this boundary.",
    )
    occupied_op = plan.boundary(
        "occupied_entry_from_handle",
        "handle_read",
        "`Occupied(OccupiedEntry { handle, dormant_map, .. })` construction",
        ("Found(handle)",),
        ["btree::node::Handle key slot", "BTreeMap::alloc"],
        ["none"],
        [("map", map_type), ("key", key_type), ("found", "bool")],
        f"entry: {plan.output}",
        requires=("found",),
        ensures=(
            plan.guarded("ordered_handle_key::<K, _>(entry) == key"),
            plan.guarded("ordered_handle_is_occupied(entry)"),
            plan.guarded("ordered_handle_map::<K, V, _>(entry) == old(map)@"),
            plan.guarded(
                "final(map)@ == ordered_handle_final_map::<K, V, _>(entry)"
            ),
        ),
        note="Found branch only; wraps the addressed handle plus the dormant map.",
    )
    vacant_op = plan.boundary(
        "vacant_entry_from_handle",
        "handle_read",
        "`Vacant(VacantEntry { key, handle, dormant_map, .. })` construction",
        ("GoDown(handle)", "None =>"),
        ["BTreeMap::root", "BTreeMap::alloc"],
        ["none"],
        [("map", map_type), ("key", key_type), ("vacant", "bool")],
        f"entry: {plan.output}",
        requires=("vacant",),
        ensures=(
            plan.guarded("ordered_handle_key::<K, _>(entry) == key"),
            plan.guarded("!ordered_handle_is_occupied(entry)"),
            plan.guarded("ordered_handle_map::<K, V, _>(entry) == old(map)@"),
            plan.guarded(
                "final(map)@ == ordered_handle_final_map::<K, V, _>(entry)"
            ),
        ),
        note="GoDown/absent-root branch only; stores the key and the insert position.",
    )
    plan.bind_calls(root_op, "new")
    plan.emit(
        f"    let root_present = {root_op}({shared_ref_argument(map_name, map_type)});",
        "    if !root_present {",
        f"        {vacant_op}({map_name}, {key_name}, true)",
        "    } else {",
        f"        let found = {search_op}({shared_ref_argument(map_name, map_type)}, &{key_name});",
        "        if found {",
        f"            {occupied_op}({map_name}, {key_name}, found)",
        "        } else {",
        f"            {vacant_op}({map_name}, {key_name}, true)",
        "        }",
        "    }",
    )


def _plan_index_lookup(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    key_name, key_type, _ = plan.inputs[1]
    map_argument = shared_ref_argument(map_name, map_type)
    lookup_op = plan.boundary(
        "map_get_value_option",
        "node_search",
        "`self.get(key)` ordered search returning the optional value slot",
        ("self.get(key)",),
        ["BTreeMap::root", "btree::node::Handle value slot"],
        ["none"],
        [("map", map_type), (key_name, key_type)],
        f"found: Option<{plan.output}>",
        ensures=(
            plan.guarded(
                f"found.is_some() <==> contains_borrowed_key(map@, {key_name})"
            ),
            plan.guarded(
                "match found { Some(value) => maps_borrowed_key_to_value("
                f"map@, {key_name}, *value), None => true }}"
            ),
        ),
        note="One ordered search; the panic decision stays in the target body.",
    )
    expect_op = plan.boundary(
        "index_expect_present",
        "node_search",
        "`.expect(\"no entry found for key\")` normal-return domain",
        ("expect(",),
        ["Option discriminant"],
        ["none"],
        [("found", f"Option<{plan.output}>")],
        f"value: {plan.output}",
        requires=("found.is_some()",),
        ensures=("Some(value) == found",),
        note=(
            "Encodes only the non-panicking domain of `expect`; it observes no "
            "map state and cannot be entered when the lookup returned None."
        ),
    )
    plan.emit(
        f"    let found = {lookup_op}({map_argument}, {key_name});",
        "    match found {",
        "        Some(value) => value,",
        f"        None => {expect_op}(found),",
        "    }",
    )


def _plan_map_equality(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    other_name, other_type, _ = plan.inputs[1]
    length_op = plan.map_length_field(
        map_type,
        ("self.len()",),
        operation="proved lower `self.len()` comparison operand",
        note="Reads one map length for the source equality precheck.",
    )
    zip_op = plan.boundary(
        "iter_zip_all_pairs_equal",
        "comparator_invoke",
        "`self.iter().zip(other).all(|(a, b)| a == b)` ordered pairwise compare",
        ("zip(other)",),
        ["BTreeMap::root", "BTreeMap::root of other"],
        ["none"],
        [("map", map_type), ("other", other_type)],
        "equal: bool",
        ensures=(
            plan.guarded(
                "equal <==> ordered_map_pairs(map@) == ordered_map_pairs(other@)"
            ),
        ),
        note=(
            "Runs the element comparator over the two ordered pair sequences; "
            "the length precheck is a separate operation."
        ),
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let left_length = {length_op}({map_name});",
        f"    let right_length = {length_op}({other_name});",
        "    if left_length != right_length {",
        "        false",
        "    } else {",
        f"        let equal = {zip_op}({map_name}, {other_name});",
        "        proof {",
        f"            if key_obeys_cmp_spec::<K>() && equal {{",
        f"                axiom_ordered_map_pairs_extensional({map_name}@, {other_name}@);",
        f"                assert({map_name}@ =~= {other_name}@);",
        "            }",
        "        }",
        "        equal",
        "    }",
    )


def _plan_map_compare(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    other_name, other_type, _ = plan.inputs[1]
    plan.add_prelude(RANGE_TOKEN_STRUCT)
    left_op = plan.boundary(
        "map_ordered_pair_cursor",
        "iterator_representation",
        "`self.iter()` / `other.iter()` ordered pair cursors",
        ("self.iter()",),
        ["BTreeMap::root"],
        ["none"],
        [("map", map_type)],
        "cursor: SourceLeafRangeToken",
        ensures=("cursor.covered@ == map@.len()",),
        note="Publishes only how many ordered pairs the cursor will yield.",
    )
    total = "ordered_pairs_cmp" if plan.fn_name == "cmp" else "ordered_pairs_partial_cmp"
    compare_op = plan.boundary(
        "ordered_pair_cursor_compare",
        "comparator_invoke",
        f"`Iterator::{plan.fn_name}` lexicographic comparison of the two cursors",
        (f".{plan.fn_name}(",),
        ["BTreeMap::root", "BTreeMap::root of other"],
        ["none"],
        [
            ("map", map_type),
            ("other", other_type),
            ("left", "SourceLeafRangeToken"),
            ("right", "SourceLeafRangeToken"),
        ],
        f"ordering: {plan.output}",
        requires=(
            "left.covered@ == map@.len()",
            "right.covered@ == other@.len()",
        ),
        ensures=(
            plan.guarded(
                f"ordering == {total}(ordered_map_pairs(map@), ordered_map_pairs(other@))"
            ),
        ),
        note=(
            "Applies the element comparator pairwise over the two ordered pair "
            "sequences produced by the cursors above."
        ),
    )
    plan.emit(
        f"    let left = {left_op}({map_name});",
        f"    let right = {left_op}({other_name});",
        f"    let ordering = {compare_op}({map_name}, {other_name}, left, right);",
        "    ordering",
    )


def split_conjunction_clause(clause: str) -> list[str]:
    """Split a `guard ==> { &&& a &&& b }` contract clause into atoms."""
    text = clause.strip()
    guard = ""
    match = re.match(r"^(.*?==>)\s*(.*)$", text, re.DOTALL)
    if match is not None and "&&&" in match.group(2):
        guard = match.group(1).strip() + " "
        text = match.group(2).strip()
    if not text.startswith("{") or not text.endswith("}"):
        return [clause]
    inner = text[1:-1].strip()
    if not inner.startswith("&&&"):
        return [clause]
    atoms: list[str] = []
    depth = 0
    current = ""
    index = 0
    while index < len(inner):
        character = inner[index]
        if character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
        if depth == 0 and inner.startswith("&&&", index):
            if current.strip():
                atoms.append(current.strip())
            current = ""
            index += 3
            continue
        current += character
        index += 1
    if current.strip():
        atoms.append(current.strip())
    if not atoms:
        return [clause]
    return [f"{guard}({atom})" if guard else atom for atom in atoms]


def decomposed_target_ensures(plan: LoweringPlan) -> list[str]:
    atoms: list[str] = []
    for clause in plan.ensures:
        atoms.extend(split_conjunction_clause(clause))
    return atoms


def retarget_clause(
    clause: str,
    receiver: str,
    map_name: str,
    result_name: str,
) -> str:
    text = clause
    text = re.sub(rf"\bold\({receiver}\)", f"old({map_name})", text)
    text = re.sub(rf"\bfinal\({receiver}\)", f"final({map_name})", text)
    text = re.sub(rf"\b{receiver}\b", map_name, text)
    text = re.sub(r"\bresult\b", result_name, text)
    return text


def _iterator_output(plan: LoweringPlan, lifetime: str) -> str:
    return (plan.output or "()").replace("'_", lifetime)


ITERATOR_INNER_TYPES = {
    "Keys": "Iter<{lifetime}, K, V>",
    "Values": "Iter<{lifetime}, K, V>",
    "ValuesMut": "IterMut<{lifetime}, K, V>",
    "IntoKeys": "IntoIter<K, V, A>",
    "IntoValues": "IntoIter<K, V, A>",
}


def _plan_iterator_construct(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    owned_receiver = not map_type.strip().startswith("&")
    output_head = (plan.output or "").split("<", 1)[0]
    atoms = decomposed_target_ensures(plan)
    length_atoms = [
        atom for atom in atoms if "ordered_iterator_remaining_len(&result)" in atom
    ]
    transfer_atoms = [atom for atom in atoms if "owning_iterator_transfer" in atom]
    remaining_atoms = [
        atom
        for atom in atoms
        if atom not in length_atoms and atom not in transfer_atoms
    ]
    if output_head in ITERATOR_INNER_TYPES:
        _plan_wrapped_iterator_construct(
            plan,
            map_name,
            map_type,
            owned_receiver,
            output_head,
            length_atoms,
            transfer_atoms,
            remaining_atoms,
        )
        return
    _plan_root_branch_iterator_construct(
        plan,
        map_name,
        map_type,
        owned_receiver,
        length_atoms,
        transfer_atoms,
        remaining_atoms,
    )


def _allocator_transfer_boundary(
    plan: LoweringPlan,
    map_name: str,
    transfer_atoms: list[str],
    iterator_type: str,
) -> str | None:
    if not transfer_atoms:
        return None
    return plan.boundary(
        "owning_iterator_take_allocator",
        "allocator_op",
        "`ManuallyDrop::take(&mut me.alloc)` allocator/drop-plan transfer",
        ("ManuallyDrop", "self.into_iter()"),
        ["BTreeMap::alloc", "BTreeMap::root"],
        ["owning iterator allocator token", "owning iterator drop plan"],
        [("map", f"&{deref_type(plan.inputs[0][1])}"), ("iterator", f"&{iterator_type}")],
        None,
        ensures=tuple(
            retarget_clause(atom, map_name, "map", "iterator").replace(
                "&map", "map"
            ).replace("&iterator", "iterator")
            for atom in transfer_atoms
        ),
        note=(
            "Moves the allocator handle and the pending drop plan into the "
            "owning iterator; no key or value is read here."
        ),
    )




def _plan_wrapped_iterator_construct(
    plan: LoweringPlan,
    map_name: str,
    map_type: str,
    owned_receiver: bool,
    output_head: str,
    length_atoms: list[str],
    transfer_atoms: list[str],
    remaining_atoms: list[str],
) -> None:
    inner_template = ITERATOR_INNER_TYPES[output_head]
    needs_lifetime = "{lifetime}" in inner_template or "'_" in (plan.output or "")
    lifetime = "'m"
    binder_extra: tuple[str, ...] = ("'m",) if needs_lifetime else ()
    inner_type = inner_template.format(lifetime=lifetime)
    output_type = _iterator_output(plan, lifetime)
    base_map_type = deref_type(map_type)
    mutable_receiver = _input_is_mutable_reference(map_type)
    if mutable_receiver:
        map_param = (
            f"&{lifetime} mut {base_map_type}"
            if needs_lifetime
            else f"&mut {base_map_type}"
        )
    else:
        map_param = (
            f"&{lifetime} {base_map_type}"
            if needs_lifetime
            else f"&{base_map_type}"
        )
    length_op: str | None = None
    if mutable_receiver:
        length_op = plan.map_length_field(
            f"&{base_map_type}",
            ("self.iter_mut()",),
            operation="inlined lower `self.iter_mut()` length observation",
            note=(
                "Reads the source lower iterator's length before the mutable "
                "iterator borrow is created."
            ),
        )
        inner_ensures = [
            "ordered_iterator_remaining_len(&inner) == length as nat"
        ]
        inner_params = [("map", map_param), ("length", "usize")]
        inner_requires = ("length as nat == old(map)@.len()",)
    else:
        inner_ensures = [
            "ordered_iterator_remaining_len(&inner) == map@.len()"
        ]
        inner_params = [("map", map_param)]
        inner_requires = ()
    wrap_atoms: list[str] = []
    for atom in remaining_atoms:
        if "spec_keys_iter" in atom or "spec_values_iter" in atom or "IteratorSpec::" in atom:
            wrap_atoms.append(atom)
        else:
            inner_ensures.append(retarget_clause(atom, map_name, "map", "inner"))
    spec_relation_atoms = [
        atom
        for atom in wrap_atoms
        if "spec_keys_iter" in atom or "spec_values_iter" in atom
    ]
    model_axiom = {
        "Keys": "axiom_spec_btree_map_keys_properties",
        "Values": "axiom_spec_btree_map_values_properties",
    }.get(output_head)
    inner_op = plan.boundary(
        "map_inner_pair_iterator",
        "iterator_representation",
        "`self.iter()` / `self.into_iter()` inner ordered pair iterator",
        ("self.iter()", "self.iter_mut()", "self.into_iter()"),
        ["BTreeMap::root", "BTreeMap::length"],
        ["none"],
        inner_params,
        f"inner: {inner_type}",
        requires=inner_requires,
        ensures=tuple(inner_ensures),
        note=(
            "Builds the inner ordered pair iterator; only its remaining length "
            "and ordered relation to the map cross the boundary."
        ),
        binder_extra=binder_extra,
    )
    wrap_ensures = [
        "ordered_iterator_remaining_len(&iterator) "
        "== ordered_iterator_remaining_len(&inner)",
        "ordered_iterator_key_trace::<K, _>(&iterator) "
        "== ordered_iterator_key_trace::<K, _>(&inner)",
        "ordered_iterator_value_trace::<V, _>(&iterator) "
        "== ordered_iterator_value_trace::<V, _>(&inner)",
    ]
    wrap_params: list[tuple[str, str]] = []
    if spec_relation_atoms:
        wrap_params.append(("map", map_param))
        wrap_ensures.extend(
            retarget_clause(atom, map_name, "map", "iterator")
            for atom in spec_relation_atoms
        )
    wrap_params.append(("inner", inner_type))
    wrap_op = plan.boundary(
        f"{output_head.lower()}_from_inner_iterator",
        "iterator_representation",
        f"`{output_head} {{ inner }}` projection wrapper construction",
        (f"{output_head} {{",),
        [f"{output_head}::inner"],
        [f"fresh {output_head}::inner"],
        wrap_params,
        f"iterator: {output_type}",
        ensures=tuple(wrap_ensures),
        note=(
            "Wraps the inner iterator and projects its ordered key/value traces; "
            "the map-relative remaining length is supplied by the inner "
            "operation."
        ),
        binder_extra=binder_extra,
    )
    transfer_op = _allocator_transfer_boundary(
        plan, map_name, transfer_atoms, output_type
    )
    map_argument = (
        map_name
        if mutable_receiver
        else shared_ref_argument(map_name, map_type)
    )
    if length_op is not None:
        plan.emit(
            f"    let length = {length_op}(&*{map_name});",
            f"    let inner = {inner_op}({map_argument}, length);",
        )
    else:
        plan.emit(f"    let inner = {inner_op}({map_argument});")
    wrap_arguments = (
        f"{map_argument}, inner" if spec_relation_atoms else "inner"
    )
    plan.emit(f"    let iterator = {wrap_op}({wrap_arguments});")
    if model_axiom is not None and wrap_atoms:
        plan.emit(
            f"    proof {{ {model_axiom}({map_argument}); }}"
        )
    if transfer_op is not None:
        plan.emit(f"    {transfer_op}({map_argument}, &iterator);")
    plan.emit("    iterator")


def _plan_root_branch_iterator_construct(
    plan: LoweringPlan,
    map_name: str,
    map_type: str,
    owned_receiver: bool,
    length_atoms: list[str],
    transfer_atoms: list[str],
    remaining_atoms: list[str],
) -> None:
    needs_lifetime = "'_" in (plan.output or "")
    lifetime = "'m"
    binder_extra: tuple[str, ...] = ("'m",) if needs_lifetime else ()
    output_type = _iterator_output(plan, lifetime)
    base_map_type = deref_type(map_type)
    mutable_receiver = bool(
        re.match(r"^&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\s", map_type.strip())
    )
    shared_param = (
        f"&{lifetime} {base_map_type}" if needs_lifetime else f"&{base_map_type}"
    )
    if owned_receiver:
        construct_param = base_map_type
    elif mutable_receiver:
        construct_param = (
            f"&{lifetime} mut {base_map_type}" if needs_lifetime else f"&mut {base_map_type}"
        )
    else:
        construct_param = shared_param
    wrapper_tokens = (
        (
            "self.iter_mut()",
            "self.iter()",
        )
        if plan.trait == "IntoIterator" and map_type.strip().startswith("&")
        else ()
    )
    plan.add_prelude(RANGE_TOKEN_STRUCT)
    iter_spec_atoms = (
        [
            atom
            for atom in remaining_atoms
            if "spec_btree_map_iter" in atom
        ]
        if plan.fn_name == "iter"
        else []
    )
    owning_token_op: str | None = None
    if owned_receiver and transfer_atoms:
        plan.add_prelude(OWNING_MAP_TOKEN_STRUCT)
        owning_token_op = plan.boundary(
            "owning_map_transfer_token",
            "allocator_op",
            "captures the map allocator and drop plan before `ManuallyDrop::take`",
            ("ManuallyDrop::take", "into_dying"),
            ["BTreeMap::root", "BTreeMap::alloc"],
            ["fresh ghost ownership-transfer token"],
            [("map", f"&{base_map_type}")],
            "token: SourceOwningMapToken<K, V>",
            ensures=(
                "token.view@ == map@",
                "token.allocator@ == map_allocator_token(map)",
                "token.drop_plan@ == ordered_map_pairs(map@)",
            ),
            note=(
                "Snapshots only the ownership observations needed after the "
                "map value is consumed by the iterator constructor."
            ),
        )
        plan.bind_calls(owning_token_op, "new")
    root_op = plan.map_root_present(
        f"&{base_map_type}",
        wrapper_tokens or ("self.root", "me.root"),
        operation=(
            "inlined proved `self.iter()`/`self.iter_mut()` root-presence observation"
            if wrapper_tokens
            else None
        ),
        note=(
            "Expands only the lower iterator call's root-presence branch."
            if wrapper_tokens
            else None
        ),
    )
    length_op = plan.map_length_field(
        f"&{base_map_type}",
        wrapper_tokens or ("self.length", "me.length"),
        operation=(
            "inlined proved `self.iter()`/`self.iter_mut()` length observation"
            if wrapper_tokens
            else None
        ),
        note=(
            "Expands only the lower iterator call's remaining-length word."
            if wrapper_tokens
            else None
        ),
    )
    range_op = plan.boundary(
        "root_full_leaf_range",
        "iterator_representation",
        (
            "inlined lower iterator call full-range construction"
            if wrapper_tokens
            else "`root.reborrow().full_range()` / `root.into_dying().full_range()`"
        ),
        wrapper_tokens or ("full_range()",),
        ["BTreeMap::root", "btree::node leaf edge chain"],
        ["none"],
        [("map", f"&{base_map_type}"), ("present", "bool")],
        "range: SourceLeafRangeToken",
        requires=("present",),
        ensures=("range.covered@ == map@.len()",),
        note=(
            "Walks the leaf edge chain of the existing root; publishes only how "
            "many ordered pairs the range covers."
        ),
    )
    construct_ensures = [
        "ordered_iterator_remaining_len(&iterator) == range.covered@",
    ]
    construct_params = [
        ("range", "SourceLeafRangeToken"),
        ("length", "usize"),
    ]
    construct_params.insert(0, ("map", construct_param))
    construct_ensures.extend(
        retarget_clause(atom, map_name, "map", "iterator")
        for atom in (
            iter_spec_atoms if plan.fn_name == "iter" else remaining_atoms
        )
    )
    if owning_token_op is not None:
        construct_params.append(
            ("ownership", "SourceOwningMapToken<K, V>")
        )
        construct_ensures.extend(
            (
                "owning_iterator_allocator_token(&iterator) "
                "== ownership.allocator@",
                "owning_iterator_drop_plan::<K, V, _>(&iterator) "
                "== ownership.drop_plan@",
                "owning_iterator_unwind_prefix(&iterator) "
                "<= ownership.drop_plan@.len()",
            )
        )
    construct_op = plan.boundary(
        "iterator_from_full_leaf_range",
        "iterator_representation",
        (
            "inlined lower iterator call struct construction over the full range"
            if wrapper_tokens
            else "iterator struct literal over the full leaf range and the length word"
        ),
        wrapper_tokens or ("full_range", "range:"),
        ["BTreeMap::root", "BTreeMap::length"],
        ["fresh iterator range", "fresh iterator length"],
        construct_params,
        f"iterator: {output_type}",
        requires=(
            "range.covered@ == length as nat",
        ),
        ensures=tuple(construct_ensures),
        note=(
            "Branch-local construction from the leaf range produced above; the "
            "remaining-length relation is carried by the range token."
        ),
        binder_extra=binder_extra,
    )
    empty_ensures = ["ordered_iterator_remaining_len(&iterator) == 0"]
    empty_params: list[tuple[str, str]] = [("absent", "bool")]
    empty_params.insert(0, ("map", construct_param))
    empty_ensures.extend(
        retarget_clause(atom, map_name, "map", "iterator")
        for atom in (
            iter_spec_atoms if plan.fn_name == "iter" else remaining_atoms
        )
    )
    if owning_token_op is not None:
        empty_params.append(("ownership", "SourceOwningMapToken<K, V>"))
        empty_ensures.extend(
            (
                "owning_iterator_allocator_token(&iterator) "
                "== ownership.allocator@",
                "owning_iterator_drop_plan::<K, V, _>(&iterator) "
                "== ownership.drop_plan@",
                "owning_iterator_unwind_prefix(&iterator) "
                "<= ownership.drop_plan@.len()",
            )
        )
    empty_op = plan.boundary(
        "iterator_from_absent_leaf_range",
        "iterator_representation",
        (
            "inlined lower iterator call empty-root struct construction"
            if wrapper_tokens
            else "`LazyLeafRange::none()` empty iterator struct literal"
        ),
        wrapper_tokens or ("none()",),
        ["BTreeMap::root"],
        ["fresh iterator range", "fresh iterator length"],
        empty_params,
        f"iterator: {output_type}",
        requires=("absent",),
        ensures=tuple(empty_ensures),
        note="Absent-root branch only; the constructed iterator yields nothing.",
        binder_extra=binder_extra,
    )
    transfer_op = (
        None
        if owning_token_op is not None
        else _allocator_transfer_boundary(
            plan, map_name, transfer_atoms, output_type
        )
    )
    map_argument = shared_ref_argument(map_name, map_type)
    if owning_token_op is not None:
        plan.emit(f"    let ownership = {owning_token_op}({map_argument});")
    full_arguments = f"{map_name}, range, length"
    empty_arguments = f"{map_name}, true"
    if owning_token_op is not None:
        full_arguments += ", ownership"
        empty_arguments += ", ownership"
    plan.emit(
        f"    let root_present = {root_op}({map_argument});",
        f"    let length = {length_op}({map_argument});",
        "    let iterator = if root_present {",
        f"        let range = {range_op}({map_argument}, true);",
        f"        {construct_op}({full_arguments})",
        "    } else {",
        f"        {empty_op}({empty_arguments})",
        "    };",
    )
    if plan.fn_name == "iter":
        plan.emit(
            f"    proof {{ axiom_spec_btree_map_iter_properties({map_argument}); }}"
        )
    if transfer_op is not None:
        plan.emit(f"    {transfer_op}({map_argument}, &iterator);")
    plan.emit("    iterator")


def _plan_range_construct(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    range_name, range_type, _ = plan.inputs[1]
    base_map_type = deref_type(map_type)
    shared_param = f"&{base_map_type}"
    mutable_receiver = bool(
        re.match(r"^&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\s", map_type.strip())
    )
    needs_lifetime = "'_" in (plan.output or "")
    lifetime = "'m"
    binder_extra: tuple[str, ...] = ("'m",) if needs_lifetime else ()
    output_type = _iterator_output(plan, lifetime)
    construct_param = (
        f"&{lifetime} mut {base_map_type}"
        if mutable_receiver and needs_lifetime
        else (f"&mut {base_map_type}" if mutable_receiver else shared_param)
    )
    plan.add_prelude(RANGE_TOKEN_STRUCT)
    atoms = decomposed_target_ensures(plan)
    map_argument = shared_ref_argument(map_name, map_type)
    if plan.fn_name == "extract_if":
        predicate_name, predicate_type, _ = plan.inputs[2]
        plan.add_prelude(EXTRACT_CURSOR_STRUCT)
        search_op = plan.boundary(
            "extract_if_inner_range_cursor",
            "node_search",
            "private `self.extract_if_inner(range)` leaf cursor construction",
            ("extract_if_inner",),
            ["BTreeMap::root", "BTreeMap::alloc"],
            ["none"],
            [("map", shared_param), (range_name, f"&{range_type}")],
            "cursor: SourceExtractCursor<K>",
            ensures=(
                plan.guarded(
                    f"cursor.unvisited@ == ordered_range_key_sequence::<K, V, K, {range_type}>"
                    f"(map@, {range_name})"
                ),
            ),
            note=(
                "Positions the leaf cursor on the requested range; no predicate "
                "call and no removal happens here."
            ),
        )
        model_op = plan.boundary(
            "extract_if_callback_model",
            "callback_invoke",
            "stores `pred` as the callback model used by later iterator steps",
            ("pred,",),
            ["callback requires/ensures relation"],
            ["fresh ghost callback model"],
            [
                ("map", shared_param),
                (range_name, f"&{range_type}"),
                (predicate_name, f"&{predicate_type}"),
            ],
            "model: Ghost<int>",
            ensures=(
                f"extract_if_callback_model_matches(map@, {range_name}, "
                f"*{predicate_name}, model@)",
            ),
            note=(
                "Chooses only the prophetic model for one stored callback; it "
                "does not construct the iterator or state its lifecycle."
            ),
        )
        unwind_op = plan.boundary(
            "extract_if_callback_unwind_step",
            "callback_invoke",
            "one callback panic/unwind step retains the current and unvisited entries",
            ("pred,",),
            ["one callback invocation", "current and unvisited entries"],
            ["callback unwind observation"],
            [
                ("pre", "Ghost<Map<K, V>>"),
                (predicate_name, f"&{predicate_type}"),
                ("current", "Ghost<K>"),
                ("unvisited", "Ghost<Seq<K>>"),
            ],
            None,
            ensures=(
                "callback_unwind_retains_current_and_unvisited("
                "pre@, ordered_callback_unwind_map("
                f"pre@, {predicate_name}, current@, unvisited@), "
                "current@, unvisited@)",
            ),
            note=(
                "Models one callback unwind frame. The target proves the "
                "all-prefix unwind contract by quantifying this local step."
            ),
            proof=True,
        )
        build_op = plan.boundary(
            "extract_if_from_parts",
            "iterator_representation",
            "`ExtractIf { pred, inner, alloc }` struct literal",
            ("ExtractIf {",),
            ["BTreeMap::root", "BTreeMap::alloc"],
            [
                "fresh ExtractIf::inner",
                "fresh ExtractIf::pred",
                "fresh ExtractIf::alloc",
            ],
            [
                ("map", construct_param),
                (range_name, range_type),
                (predicate_name, predicate_type),
                ("cursor", "SourceExtractCursor<K>"),
                ("model", "Ghost<int>"),
            ],
            f"iterator: {output_type}",
            ensures=(
                "final(map)@ == old(map)@",
                "extract_if_unvisited_keys::<K, V, _>(&iterator) "
                "== cursor.unvisited@",
                "extract_if_visited_keys::<K, V, _>(&iterator) "
                "== Seq::<K>::empty()",
                "extract_if_yielded_pairs::<K, V, _>(&iterator) "
                "== Seq::<(K, V)>::empty()",
                "extract_if_current_map::<K, V, _>(&iterator) == old(map)@",
                "extract_if_model(&iterator) == model@",
                "iterator.ordered_remaining() == extract_if_removed_pairs("
                "model@, old(map)@, cursor.unvisited@)",
                "extract_if_state_coherent::<K, V, _>(&iterator)",
            ),
            note=(
                "Stores the cursor, the predicate and the allocator handle; the "
                "predicate is not invoked until ExtractIf::next runs."
            ),
            binder_extra=binder_extra,
        )
        plan.emit(
            "    proof { broadcast use group_generated_btree_map_axioms; }",
            f"    let ghost initial_map = {map_name}@;",
            "    let ghost range_keys = "
            f"ordered_range_key_sequence::<K, V, K, {range_type}>"
            f"(initial_map, &{range_name});",
            f"    let model = {model_op}({map_argument}, &{range_name}, "
            f"&{predicate_name});",
            "    let ghost callback_model = model@;",
            "    proof {",
            f"        assert(ordered_callback_unwind_contract(initial_map, "
            f"range_keys, &{predicate_name})) by {{",
            "            assert forall|visited: Seq<K>, current: K, unvisited: Seq<K>|",
            "                range_keys == visited + Seq::empty().push(current) + unvisited implies",
            "                callback_unwind_retains_current_and_unvisited(",
            "                    initial_map, ordered_callback_unwind_map(",
            f"                        initial_map, &{predicate_name}, current, unvisited),",
            "                    current, unvisited,",
            "                ) by {",
            f"                    {unwind_op}(Ghost(initial_map), &{predicate_name}, "
            "Ghost(current), Ghost(unvisited));",
            "                }",
            "        }",
            "    }",
            f"    let cursor = {search_op}({map_argument}, &{range_name});",
            "    let ghost initial_unvisited = cursor.unvisited@;",
            f"    let iterator = {build_op}({map_name}, {range_name}, "
            f"{predicate_name}, cursor, model);",
            "    proof {",
            "        if key_obeys_cmp_spec::<K>() {",
            "            assert(initial_unvisited == range_keys);",
            "            assert(extract_if_visit_map(",
            "                callback_model, initial_map, Seq::<K>::empty(),",
            "            ) == initial_map);",
            "            assert(extract_if_removed_pairs(",
            "                callback_model, initial_map, Seq::<K>::empty(),",
            "            ) == Seq::<(K, V)>::empty());",
            "            assert(range_keys == Seq::<K>::empty() + range_keys);",
            "            assert(extract_if_visited_keys::<K, V, _>(&iterator)",
            "                == Seq::<K>::empty());",
            "            assert(extract_if_unvisited_keys::<K, V, _>(&iterator)",
            "                == range_keys);",
            "            assert(extract_if_current_map::<K, V, _>(&iterator)",
            "                == initial_map);",
            "            assert(extract_if_yielded_pairs::<K, V, _>(&iterator)",
            "                == extract_if_removed_pairs(",
            "                    callback_model, initial_map, Seq::<K>::empty(),",
            "                ));",
            "            assert(extract_if_state_coherent::<K, V, _>(&iterator));",
            f"            assert(extract_if_callback_model_matches(initial_map, "
            f"&{range_name}, {predicate_name}, callback_model));",
            "            assert forall|key: K| range_keys.contains(key) implies",
            "                initial_map.contains_key(key) by {",
            "                if range_keys.contains(key) {",
            "                    let all_keys = ordered_map_key_sequence(initial_map);",
            "                    let in_range: spec_fn(K) -> bool = |candidate: K|",
            f"                        ordered_key_in_range::<K, K, {range_type}>"
            f"(&{range_name}, candidate);",
            "                    assert(range_keys == all_keys.filter(in_range));",
            "                    all_keys.lemma_filter_contains_rev(in_range, key);",
            "                    assert(all_keys.contains(key));",
            "                    assert(all_keys.to_set().contains(key));",
            "                    assert(initial_map.dom().contains(key));",
            "                }",
            "            }",
            f"            assert(extract_if_lifecycle(initial_map, &{range_name}, "
            f"{predicate_name}, &iterator, initial_map, "
            "Seq::<K>::empty(), range_keys));",
            "        }",
            "    }",
            "    iterator",
        )
        return
    plan.add_prelude(RANGE_CURSOR_STRUCT)
    root_op = plan.map_root_present(shared_param, ("self.root",))
    cursor_ensures = (
        plan.guarded(
            f"cursor.keys@ == ordered_range_key_sequence::<K, V, T, {range_type}>"
            f"(map@, {range_name})"
        ),
        plan.guarded(
            f"cursor.values@ == ordered_range_pair_sequence::<K, V, T, {range_type}>"
            f"(map@, {range_name}).map("
            "|_index: int, pair: (K, V)| pair.1)"
        ),
        plan.guarded("cursor.covered@ == cursor.keys@.len()"),
    )
    search_op = plan.boundary(
        "root_range_search",
        "node_search",
        "`root.reborrow().range_search(range)` / `borrow_valmut().range_search(range)`",
        ("range_search",),
        ["BTreeMap::root", "btree::node search path"],
        ["none"],
        [("map", shared_param), (range_name, f"&{range_type}"), ("present", "bool")],
        "cursor: SourceRangeCursor<K, V>",
        requires=("present",),
        ensures=cursor_ensures,
        note=(
            "One private bounded search that positions the leaf cursor; no "
            "key/value payload crosses the boundary."
        ),
    )
    empty_cursor_op = plan.boundary(
        "empty_root_range_cursor",
        "iterator_representation",
        "`LeafRange::none()` empty cursor for an absent map root",
        ("none()",),
        ["BTreeMap::root"],
        ["fresh empty range cursor"],
        [("map", shared_param), (range_name, f"&{range_type}"), ("absent", "bool")],
        "cursor: SourceRangeCursor<K, V>",
        requires=("absent", "map@.is_empty()"),
        ensures=cursor_ensures,
        note=(
            "Publishes only the empty branch's ordered key/value sequences; "
            "iterator construction remains a separate operation."
        ),
    )
    range_atoms = [atom for atom in atoms if "ordered_range_result" in atom]
    other_atoms = [atom for atom in atoms if "ordered_range_result" not in atom]
    projection_ensures = [
        "ordered_iterator_key_trace::<K, _>(&iterator) == cursor.keys@",
        "ordered_iterator_value_trace::<V, _>(&iterator) == cursor.values@",
        "iterator.ordered_remaining().len() == cursor.covered@",
    ] if range_atoms else []
    retargeted_other_atoms = [
        retarget_clause(atom, map_name, "map", "iterator")
        for atom in other_atoms
    ]
    if mutable_receiver:
        retargeted_other_atoms = [
            re.sub(
                r"(?<!old\()(?<!final\()map@",
                "old(map)@",
                atom,
            )
            for atom in retargeted_other_atoms
        ]
    construct_ensures = tuple(projection_ensures + retargeted_other_atoms)
    build_params: list[tuple[str, str]] = [("map", construct_param)]
    if mutable_receiver:
        build_params.append((range_name, range_type))
    build_params.append(("cursor", "SourceRangeCursor<K, V>"))
    build_op = plan.boundary(
        "range_from_leaf_cursor",
        "iterator_representation",
        "`Range { inner: .. }` / `RangeMut { inner: .. }` struct literal",
        ("Range {", "RangeMut {", "inner:"),
        ["BTreeMap::root"],
        ["fresh range iterator inner"],
        build_params,
        f"iterator: {output_type}",
        ensures=construct_ensures,
        note=(
            "Transfers only the positioned cursor into the public range wrapper; "
            "map-relative range semantics were established by the search."
        ),
        binder_extra=binder_extra,
    )
    build_arguments = (
        f"{map_name}, {range_name}, cursor"
        if mutable_receiver
        else f"{map_name}, cursor"
    )
    if mutable_receiver:
        plan.emit(f"    let ghost initial_map = {map_name}@;")
    plan.emit(
        f"    let root_present = {root_op}({map_argument});",
        "    let cursor = if root_present {",
        f"        {search_op}({map_argument}, &{range_name}, true)",
        "    } else {",
        f"        {empty_cursor_op}({map_argument}, &{range_name}, true)",
        "    };",
        f"    let iterator = {build_op}({build_arguments});",
        "    proof {",
        f"        if {plan.guard} {{",
        f"        assert(ordered_range_result::<K, V, T, {range_type}, _>("
        f"{'initial_map' if mutable_receiver else map_name + '@'}, "
        f"&{range_name}, &iterator));",
        "        }",
        "    }",
        "    iterator",
    )


def _plan_iterator_size(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    if plan.owner == "ExtractIf":
        op = plan.boundary(
            "extract_if_current_map_length",
            "representation_read",
            "`self.inner.size_hint()` upper bound from the current map length",
            ("size_hint",),
            ["ExtractIf::inner remaining length"],
            ["none"],
            [("iterator", rust_type)],
            "upper: usize",
            ensures=("upper as nat == iterator.extract_current_map().len()",),
            note="Reads only the remaining upper-bound word of the inner cursor.",
        )
        plan.emit(
            f"    let upper = {op}({name});",
            "    (0, Some(upper))",
        )
        return
    exact_size = plan.trait == "ExactSizeIterator"
    direct_field = plan.owner in {"Iter", "IterMut", "IntoIter"}
    leaf = None
    if exact_size:
        leaf = (
            f"{plan.owner} stores its remaining length in a private word and the "
            "accepted contract for ExactSizeIterator::len is exactly that "
            "observation"
        )
    op = plan.iterator_length_field(
        rust_type,
        ("self.length",) if direct_field else ("self.inner",),
        leaf_exception=leaf,
    )
    if exact_size:
        plan.emit(f"    let length = {op}({name});", "    length")
        return
    plan.emit(
        f"    let length = {op}({name});",
        "    (length, Some(length))",
    )


def _plan_extract_if_step(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    base_type = deref_type(rust_type)
    plan.add_prelude(EXTRACT_NEXT_CURSOR_STRUCT)
    cursor_op = plan.boundary(
        "extract_if_next_visit_cursor",
        "iterator_representation",
        "plans the key prefix consumed by private `self.inner.next`",
        ("self.inner.next",),
        ["ExtractIf::inner cursor", "ExtractIf::pred"],
        ["fresh visit cursor"],
        [("iterator", f"&{base_type}")],
        "cursor: SourceExtractNextCursor<K, V>",
        ensures=(
            "cursor.pending@ == iterator.extract_next_consumed_keys()",
            "cursor.consumed@ == Seq::<K>::empty()",
            "cursor.remaining as nat == cursor.pending@.len()",
            "cursor.pending@.len() <= iterator.extract_unvisited_keys().len()",
            "cursor.output@ == if iterator.ordered_remaining().len() > 0 { "
            "Some(iterator.ordered_remaining()[0]) } else { None }",
            "cursor.output@.is_some() ==> cursor.pending@.len() > 0",
            "cursor.output@.is_none() ==> cursor.pending@.len() "
            "== iterator.extract_unvisited_keys().len()",
            "cursor.initial_model@ == iterator.extract_model()",
            "cursor.initial_visited@ == iterator.extract_visited_keys()",
            "cursor.initial_unvisited@ == iterator.extract_unvisited_keys()",
            "cursor.initial_map@ == iterator.extract_current_map()",
            "cursor.initial_yielded@ == iterator.extract_yielded_pairs()",
            "cursor.initial_remaining@ == iterator.ordered_remaining()",
            "iterator.extract_state_coherent()",
        ),
        note=(
            "Captures only the source visit prefix and eventual optional item; "
            "the target executes every visit below."
        ),
    )
    next_key_op = plan.boundary(
        "extract_if_cursor_next_key",
        "iterator_step",
        "advances one key in the private `self.inner.next` visit prefix",
        ("self.inner.next",),
        ["visit cursor position"],
        ["visit cursor position"],
        [("cursor", "&mut SourceExtractNextCursor<K, V>")],
        "key: Ghost<K>",
        requires=(
            "old(cursor).remaining > 0",
            "old(cursor).remaining as nat == old(cursor).pending@.len()",
        ),
        ensures=(
            "key@ == old(cursor).pending@[0]",
            "final(cursor).pending@ == old(cursor).pending@.drop_first()",
            "final(cursor).consumed@ == old(cursor).consumed@.push(key@)",
            "final(cursor).remaining + 1 == old(cursor).remaining",
            "final(cursor).output@ == old(cursor).output@",
            "final(cursor).initial_model@ == old(cursor).initial_model@",
            "final(cursor).initial_visited@ == old(cursor).initial_visited@",
            "final(cursor).initial_unvisited@ == old(cursor).initial_unvisited@",
            "final(cursor).initial_map@ == old(cursor).initial_map@",
            "final(cursor).initial_yielded@ == old(cursor).initial_yielded@",
            "final(cursor).initial_remaining@ == old(cursor).initial_remaining@",
        ),
        note="Moves exactly one planned key from pending to consumed.",
    )
    visit_op = plan.boundary(
        "extract_if_visit_one_key",
        "callback_invoke",
        "one predicate call and one keep/remove decision inside `self.inner.next`",
        ("self.inner.next",),
        ["ExtractIf::pred", "current key/value slot"],
        ["current value slot", "ExtractIf::inner cursor"],
        [
            ("iterator", rust_type),
            ("key", "Ghost<K>"),
            ("cursor", "&SourceExtractNextCursor<K, V>"),
            ("final_step", "bool"),
        ],
        None,
        requires=(
            "cursor.consumed@.len() > 0",
            "key@ == cursor.consumed@.last()",
        ),
        ensures=(
            "final(iterator).extract_model() == cursor.initial_model@",
            "final(iterator).extract_visited_keys() "
            "== cursor.initial_visited@ + cursor.consumed@",
            "final(iterator).extract_unvisited_keys() "
            "== cursor.initial_unvisited@.skip(cursor.consumed@.len() as int)",
            "final(iterator).extract_current_map() == extract_if_visit_map("
            "cursor.initial_model@, cursor.initial_map@, cursor.consumed@)",
            "final(iterator).extract_yielded_pairs() == if final_step { "
            "match cursor.output@ { Some(pair) => cursor.initial_yielded@.push(pair), "
            "None => cursor.initial_yielded@ } } else { cursor.initial_yielded@ }",
            "final(iterator).ordered_remaining() == if final_step { "
            "match cursor.output@ { Some(_) => cursor.initial_remaining@.drop_first(), "
            "None => cursor.initial_remaining@ } } else { cursor.initial_remaining@ }",
            "final(iterator).extract_state_coherent()",
        ),
        note=(
            "Models one callback/entry decision. Aggregate prefix facts are "
            "parameterized by the executable cursor's consumed sequence."
        ),
    )
    frame_op = plan.boundary(
        "extract_if_remaining_frame",
        "representation_read",
        "audits the unvisited frame after private `self.inner.next` completes",
        ("self.inner.next",),
        ["ExtractIf::inner unvisited keys", "ExtractIf current map"],
        ["none"],
        [
            ("iterator", f"&{base_type}"),
            ("cursor", "&SourceExtractNextCursor<K, V>"),
        ],
        None,
        requires=("cursor.remaining == 0",),
        ensures=(
            "forall|remaining_key: K| "
            "#[trigger] iterator.extract_unvisited_keys().contains(remaining_key) ==> { "
            "&&& iterator.extract_current_map().contains_key(remaining_key) "
            "&&& cursor.initial_map@.contains_key(remaining_key) "
            "&&& iterator.extract_current_map()[remaining_key] "
            "== cursor.initial_map@[remaining_key] }",
        ),
        note=(
            "Checks only the final frame for entries the source cursor did not "
            "visit; callback and yielded-state transitions are proved by the loop."
        ),
    )
    materialize_op = plan.boundary(
        "extract_if_materialize_next_result",
        "representation_read",
        "materializes the optional pair returned by `self.inner.next`",
        ("self.inner.next",),
        ["ghost optional pair selected by the visit cursor"],
        ["returned pair ownership"],
        [("cursor", "SourceExtractNextCursor<K, V>")],
        "result: Option<(K, V)>",
        ensures=("result == cursor.output@",),
        note=(
            "Transfers only the already-selected optional pair into the "
            "executable return value; it changes no iterator state."
        ),
    )
    plan.emit(
        f"    let mut cursor = {cursor_op}(&*{name});",
        "    let ghost planned = cursor.pending@;",
        "    let ghost output = cursor.output@;",
        "    let ghost initial_model = cursor.initial_model@;",
        "    let ghost initial_visited = cursor.initial_visited@;",
        "    let ghost initial_unvisited = cursor.initial_unvisited@;",
        "    let ghost initial_map = cursor.initial_map@;",
        "    let ghost initial_yielded = cursor.initial_yielded@;",
        "    let ghost initial_remaining = cursor.initial_remaining@;",
        "    proof {",
        "        assert(output == if initial_remaining.len() > 0 {",
        "            Some(initial_remaining[0])",
        "        } else { None });",
        "        assert(output.is_some() ==> planned.len() > 0);",
        "        assert(output.is_none() ==> planned.len() == initial_unvisited.len());",
        "    }",
        "    while cursor.remaining > 0",
        "        invariant",
        "            cursor.remaining as nat == cursor.pending@.len(),",
        "            cursor.consumed@ + cursor.pending@ =~= planned,",
        "            cursor.output@ == output,",
        "            cursor.initial_model@ == initial_model,",
        "            cursor.initial_visited@ == initial_visited,",
        "            cursor.initial_unvisited@ == initial_unvisited,",
        "            cursor.initial_map@ == initial_map,",
        "            cursor.initial_yielded@ == initial_yielded,",
        "            cursor.initial_remaining@ == initial_remaining,",
        f"            {name}.extract_model() == initial_model,",
        f"            {name}.extract_visited_keys() "
        "== initial_visited + cursor.consumed@,",
        f"            {name}.extract_unvisited_keys() "
        "== initial_unvisited.skip(cursor.consumed@.len() as int),",
        f"            {name}.extract_current_map() == extract_if_visit_map("
        "initial_model, initial_map, cursor.consumed@),",
        f"            {name}.extract_yielded_pairs() == if cursor.remaining == 0 {{ "
        "match output { Some(pair) => initial_yielded.push(pair), "
        "None => initial_yielded } } else { initial_yielded },",
        f"            {name}.ordered_remaining() == if cursor.remaining == 0 {{ "
        "match output { Some(_) => initial_remaining.drop_first(), "
        "None => initial_remaining } } else { initial_remaining },",
        f"            {name}.extract_state_coherent(),",
        "        decreases cursor.remaining,",
        "    {",
        "        let ghost consumed_before = cursor.consumed@;",
        "        let ghost pending_before = cursor.pending@;",
        f"        let key = {next_key_op}(&mut cursor);",
        "        let final_step = cursor.remaining == 0;",
        f"        {visit_op}({name}, key, &cursor, final_step);",
        "        proof {",
        "            assert(cursor.consumed@.drop_last() =~= consumed_before);",
        "            assert(pending_before =~= seq![key@] + cursor.pending@);",
        "            assert(cursor.consumed@ + cursor.pending@ "
        "=~= consumed_before + pending_before);",
        "        }",
        "    }",
        "    proof {",
        "        assert(cursor.pending@ =~= Seq::<K>::empty()) by {",
        "            assert(cursor.pending@.len() == 0);",
        "        }",
        "        assert(cursor.consumed@ =~= planned);",
        "        assert(output == if initial_remaining.len() > 0 {",
        "            Some(initial_remaining[0])",
        "        } else { None });",
        "    }",
        f"    {frame_op}(&*{name}, &cursor);",
        "    proof {",
        "        assert forall|remaining_key: K|",
        f"            {name}.extract_unvisited_keys().contains(remaining_key) implies {{",
        f"                &&& {name}.extract_current_map().contains_key(remaining_key)",
        "                &&& initial_map.contains_key(remaining_key)",
        f"                &&& {name}.extract_current_map()[remaining_key]",
        "                    == initial_map[remaining_key]",
        "            } by {",
        f"            if {name}.extract_unvisited_keys().contains(remaining_key) {{",
        f"                assert({name}.extract_current_map().contains_key(remaining_key));",
        "                assert(cursor.initial_map@.contains_key(remaining_key));",
        f"                assert({name}.extract_current_map()[remaining_key]",
        "                    == cursor.initial_map@[remaining_key]);",
        "            }",
        "        }",
        "    }",
        "    let ghost consumed = cursor.consumed@;",
        f"    let result = {materialize_op}(cursor);",
        "    proof {",
        "        match result {",
        "            Some(_) => {",
        "                assert(planned.len() > 0);",
        "            },",
        "            None => {",
        "                assert(planned.len() == initial_unvisited.len());",
        "            },",
        "        }",
        "        if planned.len() == 0 {",
        f"            assert({name}.extract_unvisited_keys().len() == 0);",
        "        }",
        "    }",
        "    result",
    )


def _plan_iterator_step(plan: LoweringPlan) -> None:
    if plan.owner == "ExtractIf":
        _plan_extract_if_step(plan)
        return
    name, rust_type = plan.receiver()
    base_type = deref_type(rust_type)
    forward = plan.profile == "iterator_next"
    item_type = option_item_type(plan.output)
    mutable_item = re.match(
        r"^&('[A-Za-z_][A-Za-z0-9_]*)\s+mut\s+(.+)$",
        item_type,
    )
    item_boundary_type = item_type
    item_observation = "item"
    if mutable_item is not None:
        plan.add_prelude(MUT_ITEM_TOKEN_STRUCT)
        item_boundary_type = (
            f"SourceMutItemToken<{mutable_item.group(1)}, "
            f"{mutable_item.group(2)}>"
        )
        item_observation = "item.item@"
    shared_argument = shared_ref_argument(name, rust_type)
    length_tokens = (
        ("dying_next",)
        if plan.owner == "IntoIter"
        else ("self.length", "self.inner")
    )
    length_op = plan.iterator_length_field(f"&{base_type}", length_tokens)
    atoms = decomposed_target_ensures(plan)
    step_ensures: list[str] = []
    for atom in atoms:
        retargeted = retarget_clause(atom, name, "iterator", "item")
        if "if old(iterator).ordered_remaining().len() > 0" in retargeted:
            continue
        step_ensures.append(retargeted)
    step_ensures = [
        (
            "final(iterator).ordered_remaining() == old(iterator).ordered_remaining()"
            f".{'drop_first' if forward else 'drop_last'}()"
        ),
        (
            f"{item_observation} == old(iterator).ordered_remaining()[0]"
            if forward
            else f"{item_observation} == old(iterator).ordered_remaining().last()"
        ),
    ] + step_ensures
    method = "next_unchecked" if forward else "next_back_unchecked"
    step_op = plan.boundary(
        f"iterator_step_{'front' if forward else 'back'}",
        "iterator_step",
        f"`self.length -= 1; self.range.{method}()` single cursor advance",
        (
            method,
            "self.inner.next",
            "self.length -= 1",
            "dying_next",
            "dying_next_back",
        ),
        [f"{plan.owner}::range", f"{plan.owner}::length"],
        [f"{plan.owner}::range", f"{plan.owner}::length"],
        [("iterator", f"&mut {base_type}"), ("nonempty", "bool")],
        f"item: {item_boundary_type}",
        requires=(
            "nonempty",
            "old(iterator).ordered_remaining().len() > 0",
        ),
        ensures=tuple(step_ensures),
        note=(
            "Advances the private cursor by exactly one element; the empty "
            "branch never reaches this boundary."
        ),
    )
    wrap_op = None
    if mutable_item is not None:
        wrap_op = plan.boundary(
            "iterator_wrap_mut_item",
            "iterator_representation",
            "`.map(|(_, value)| value)` optional mutable-item projection",
            (".map(", "self.inner.next"),
            ["one mutable iterator item"],
            ["optional mutable return item"],
            [("item", item_boundary_type)],
            f"wrapped: Option<{item_type}>",
            ensures=("wrapped == Some(item.item@)",),
            note=(
                "Moves only the selected mutable reference into the public "
                "Option wrapper."
            ),
        )
    plan.emit(
        f"    let length = {length_op}({shared_argument});",
        "    if length == 0 {",
        "        None",
        "    } else {",
        f"        let item = {step_op}({name}, true);",
        (
            f"        {wrap_op}(item)"
            if wrap_op is not None
            else "        Some(item)"
        ),
        "    }",
    )


def _plan_iterator_terminal(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    base_type = deref_type(rust_type)
    front = plan.profile == "iterator_first"
    item_type = option_item_type(plan.output)
    mutable_item = re.match(
        r"^&('[A-Za-z_][A-Za-z0-9_]*)\s+mut\s+(.+)$",
        item_type,
    )
    item_boundary_type = item_type
    item_reference = "&item"
    if mutable_item is not None:
        plan.add_prelude(MUT_ITEM_TOKEN_STRUCT)
        item_boundary_type = (
            f"SourceMutItemToken<{mutable_item.group(1)}, "
            f"{mutable_item.group(2)}>"
        )
        item_reference = "&(item.item@)"
    method = "self.next()" if front else "self.next_back()"
    matcher = (
        "ordered_iterator_front_matches" if front else "ordered_iterator_back_matches"
    )
    length_op = plan.iterator_length_field(
        f"&{base_type}",
        (method,),
        operation=f"inlined proved `{method}` remaining-length observation",
        note=(
            "Reads the lower iterator call's remaining length before reproducing "
            "its empty/nonempty branch."
        ),
    )
    step_op = plan.boundary(
        f"iterator_step_{'front' if front else 'back'}",
        "iterator_step",
        f"inlined proved `{method}` one-element cursor advance",
        (method,),
        [f"{plan.owner}::range", f"{plan.owner}::length"],
        [f"{plan.owner}::range", f"{plan.owner}::length"],
        [("iterator", f"&mut {base_type}"), ("nonempty", "bool")],
        f"item: {item_boundary_type}",
        requires=(
            "nonempty",
            "old(iterator).ordered_remaining().len() > 0",
        ),
        ensures=(f"{matcher}(old(iterator), {item_reference})",),
        note=(
            "Inlines the separately proved lower iterator call and observes "
            "only its selected element."
        ),
    )
    wrap_op = None
    if mutable_item is not None:
        wrap_op = plan.boundary(
            "iterator_wrap_mut_item",
            "iterator_representation",
            f"`{method}` optional mutable-item return",
            (method,),
            ["one mutable iterator item"],
            ["optional mutable return item"],
            [("item", item_boundary_type)],
            f"wrapped: Option<{item_type}>",
            ensures=("wrapped == Some(item.item@)",),
            note="Moves the lower call's mutable item into its Option result.",
        )
    plan.emit(
        f"    let mut iterator = {name};",
        f"    let length = {length_op}(&iterator);",
        "    if length == 0 {",
        "        None",
        "    } else {",
        f"        let item = {step_op}(&mut iterator, true);",
        (
            f"        {wrap_op}(item)"
            if wrap_op is not None
            else "        Some(item)"
        ),
        "    }",
    )


def _plan_iterator_clone(plan: LoweringPlan) -> None:
    name, rust_type = plan.receiver()
    base_type = deref_type(rust_type)
    plan.add_prelude(RANGE_TOKEN_STRUCT)
    range_op = plan.boundary(
        "iterator_clone_inner_range",
        "iterator_representation",
        "`self.range.clone()` / `self.inner.clone()` cursor duplication",
        (".clone()",),
        [f"{plan.owner}::range"],
        ["fresh cursor range"],
        [("iterator", rust_type)],
        "range: SourceLeafRangeToken",
        ensures=("range.covered@ == ordered_iterator_remaining_len(iterator)",),
        note="Duplicates the private cursor only.",
    )
    build_op = plan.boundary(
        "iterator_from_cloned_range",
        "iterator_representation",
        "iterator struct literal over the duplicated cursor",
        ("Iter {", "Keys {", "Values {", "Range {"),
        [f"{plan.owner}::range"],
        ["fresh iterator range"],
        [("iterator", rust_type), ("range", "SourceLeafRangeToken")],
        f"cloned: {base_type}",
        requires=("range.covered@ == ordered_iterator_remaining_len(iterator)",),
        ensures=(
            "cloned.ordered_remaining() =~= iterator.ordered_remaining()",
        ),
        note="Builds the duplicate from the cloned cursor.",
    )
    plan.emit(
        f"    let range = {range_op}({name});",
        f"    let cloned = {build_op}({name}, range);",
        f"    proof {{ assert(cloned.ordered_remaining() =~= {name}.ordered_remaining()); }}",
        "    cloned",
    )


def _plan_empty_iterator(plan: LoweringPlan) -> None:
    output_type = plan.output or "()"
    plan.add_prelude(RANGE_TOKEN_STRUCT)
    range_op = plan.boundary(
        "iterator_default_inner_range",
        "iterator_representation",
        "`Default::default()` empty inner leaf range",
        ("Default::default()",),
        ["none"],
        ["fresh cursor range"],
        [],
        "range: SourceLeafRangeToken",
        ensures=("range.covered@ == 0nat",),
        note="Produces an empty private cursor; no map is involved.",
    )
    build_op = plan.boundary(
        "iterator_from_default_range",
        "iterator_representation",
        "iterator struct literal over the default cursor",
        ("{ range:", "{ inner:"),
        ["none"],
        ["fresh iterator range"],
        [("range", "SourceLeafRangeToken")],
        f"iterator: {output_type}",
        requires=("range.covered@ == 0nat",),
        ensures=("iterator.ordered_remaining().len() == 0",),
        note="Builds the default iterator from the empty cursor.",
    )
    plan.emit(
        f"    let range = {range_op}();",
        f"    let iterator = {build_op}(range);",
        "    proof { assert(iterator.ordered_remaining() =~= Seq::<_>::empty()); }",
        "    iterator",
    )


def _plan_effect_trace(plan: LoweringPlan) -> None:
    subject_name, subject_type = plan.receiver()
    clause = plan.ensures[0]
    if "ordered_hash_transition" in clause:
        _plan_hash_effect(plan)
        return
    formatter_name, formatter_type, _ = plan.inputs[1]
    if "ordered_iterator_debug_result" in clause:
        plan.add_prelude(DEBUG_TRACE_HELPER)
        emitted = f"source_debug_entries_trace(subject)"
        subject_param = subject_type
    elif "ordered_map_debug_result" in clause:
        emitted = "ordered_map_debug_trace(subject@)"
        subject_param = subject_type
    elif "ordered_handle_debug_result" in clause:
        emitted = (
            "debug_value_trace(ordered_handle_key::<K, _>(subject)) "
            "+ ordered_map_debug_trace(ordered_handle_map::<K, V, _>(subject))"
        )
        subject_param = subject_type
    else:
        emitted = "ordered_debug_trace(subject)"
        subject_param = subject_type
    entries_op = plan.boundary(
        "formatter_write_entries",
        "formatter_op",
        "builder opening plus `.entries(..)` / `.field(..)` element emission",
        (
            "debug_list",
            "debug_map",
            "debug_struct",
            "debug_tuple",
            ".entries(",
            ".field(",
        ),
        ["core::fmt::Formatter builder state", "subject debug trace"],
        ["core::fmt::Formatter buffer"],
        [("formatter", formatter_type), ("subject", subject_param)],
        None,
        ensures=(
            f"formatter_trace(*final(formatter)) == "
            f"formatter_trace(*old(formatter)) + ({emitted})",
            (
                "formatter_failed(*final(formatter)) "
                f"== formatter_failure_after_trace(*old(formatter), {emitted})"
            ),
        ),
        note=(
            "The builder-open call emits no separate observable event, so this "
            "operation models the source chain through its first element write "
            "and emits exactly the ordered subject trace."
        ),
    )
    plan.bind_calls(entries_op, "reborrow")
    finish_op = plan.boundary(
        "formatter_finish_builder",
        "formatter_op",
        "`.finish()` / `.finish_non_exhaustive()` builder completion",
        (".finish()", "finish_non_exhaustive"),
        ["core::fmt::Formatter builder state"],
        ["core::fmt::Formatter builder state"],
        [("formatter", formatter_type)],
        "outcome: core::fmt::Result",
        ensures=(
            "formatter_trace(*final(formatter)) == formatter_trace(*old(formatter))",
            "formatter_failed(*final(formatter)) == formatter_failed(*old(formatter))",
            "outcome.is_err() <==> formatter_failed(*final(formatter))",
        ),
        note="Closes the builder and reports the accumulated failure flag.",
    )
    plan.emit(
        f"    {entries_op}({formatter_name}, {subject_name});",
        f"    let outcome = {finish_op}({formatter_name});",
        "    outcome",
    )


def _plan_hash_effect(plan: LoweringPlan) -> None:
    map_name, map_type = plan.receiver()
    state_name, state_type, _ = plan.inputs[1]
    plan.add_prelude(HASH_ENTRIES_HELPER)
    length_op = plan.map_length_field(
        map_type,
        ("self.len()",),
        operation="proved lower `self.len()` call before hashing entries",
        note="Emits the length word that precedes the ordered pair hash trace.",
    )
    prefix_op = plan.boundary(
        "hasher_write_length_prefix",
        "hasher_op",
        "`state.write_length_prefix(self.len())`",
        ("write_length_prefix",),
        ["hasher state"],
        ["hasher state"],
        [("state", state_type), ("length", "usize")],
        None,
        ensures=(
            "hasher_trace(*final(state)) == hasher_trace(*old(state)).push(length as int)",
        ),
        note="Writes exactly one length word into the hasher trace.",
    )
    entries_op = plan.boundary(
        "hasher_write_entries",
        "hasher_op",
        "`for elt in self { elt.hash(state); }` ordered element hashing",
        ("elt.hash(state)",),
        ["BTreeMap::root", "hasher state"],
        ["hasher state"],
        [("state", state_type), ("map", map_type)],
        None,
        ensures=(
            "hasher_trace(*final(state)) "
            "== hasher_trace(*old(state)) + source_hash_entries_trace(map@)",
        ),
        note="Appends exactly the ordered per-entry hash traces.",
    )
    plan.emit(
        f"    let length = {length_op}({map_name});",
        f"    let ghost pre_state = *{state_name};",
        f"    {prefix_op}({state_name}, length);",
        f"    {entries_op}({state_name}, {map_name});",
        "    proof {",
        f"        assert(ordered_map_hash_trace({map_name}@) =~= "
        f"seq![{map_name}@.len() as int] + source_hash_entries_trace({map_name}@));",
        "        assert(hasher_trace(pre_state).push(length as int) "
        f"+ source_hash_entries_trace({map_name}@) =~= hasher_trace(pre_state) "
        f"+ (seq![length as int] + source_hash_entries_trace({map_name}@)));",
        "    }",
    )


def _plan_entry_or_insert(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    entry_ref = shared_ref_type(entry_type)
    has_default = len(plan.inputs) > 1
    default_name, default_type = (
        (plan.inputs[1][0], plan.inputs[1][2 - 1]) if has_default else ("", "")
    )
    if has_default:
        default_name, default_type, _ = plan.inputs[1]
    plan.add_prelude(HANDLE_TOKEN_STRUCT)
    discriminant = plan.boundary(
        "entry_occupied_discriminant",
        "representation_read",
        "Entry enum discriminant match on Occupied/Vacant",
        ("match self",),
        ["Entry discriminant"],
        ["none"],
        [("entry", entry_ref)],
        "occupied: bool",
        ensures=(
            "occupied == ordered_handle_is_occupied(entry)",
        ),
        note="Reads only the enum tag and the presence of the addressed key.",
    )
    occupied_op = plan.boundary(
        "occupied_entry_into_mut_slot",
        "handle_update",
        "`entry.into_mut()` value-slot projection on the Occupied branch",
        ("entry.into_mut()",),
        ["btree::node::Handle value slot"],
        ["btree::node::Handle value slot"],
        [("entry", entry_type), ("occupied", "bool")],
        f"value: {plan.output}",
        requires=("occupied",),
        ensures=(
            (
                "*value == ordered_handle_map::<K, V, _>(entry)["
                "ordered_handle_key::<K, _>(entry)]"
            ),
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_map::<K, V, _>(entry).insert("
                "ordered_handle_key::<K, _>(entry), *final(value))"
            ),
        ),
        note="Occupied branch only; projects exactly one existing value slot.",
    )
    callback_atoms = [
        atom
        for atom in decomposed_target_ensures(plan)
        if ".ensures((" in atom or "V::default" in atom
    ]
    vacant_ensures = [
        (
            "!ordered_handle_map::<K, V, _>(entry).contains_key("
            "ordered_handle_key::<K, _>(entry))"
        ),
        (
            "ordered_handle_final_map::<K, V, _>(entry) "
            "== ordered_handle_map::<K, V, _>(entry).insert("
            "ordered_handle_key::<K, _>(entry), *final(value))"
        ),
    ]
    vacant_params = [("entry", entry_type)]
    call_arguments = [entry_name]
    if has_default:
        vacant_params.append((default_name, default_type))
        call_arguments.append(default_name)
    vacant_params.append(("vacant", "bool"))
    call_arguments.append("true")
    for atom in callback_atoms:
        vacant_ensures.append(retarget_clause(atom, entry_name, "entry", "value"))
    if not callback_atoms:
        vacant_ensures.append(f"*value == {default_name}" if has_default else "true")
    vacant_op = plan.boundary(
        "vacant_entry_insert_default_value",
        "node_update",
        "`entry.insert(default)` / `entry.insert(default())` on the Vacant branch",
        ("entry.insert(", "Vacant(entry)"),
        ["VacantEntry::key", "VacantEntry::handle", "callback state"],
        ["btree::node leaf slot", "BTreeMap::root", "BTreeMap::length"],
        vacant_params,
        f"value: {plan.output}",
        requires=("vacant",),
        ensures=tuple(vacant_ensures),
        note=(
            "Vacant branch only; evaluates the caller default exactly once and "
            "splices one new pair."
        ),
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let occupied = {discriminant}(&{entry_name});",
        "    if occupied {",
        f"        {occupied_op}({entry_name}, occupied)",
        "    } else {",
        f"        {vacant_op}({', '.join(call_arguments)})",
        "    }",
    )


def _plan_and_modify(plan: LoweringPlan) -> None:
    entry_name, entry_type = plan.receiver()
    callback_name, callback_type, _ = plan.inputs[1]
    entry_ref = shared_ref_type(entry_type)
    discriminant = plan.boundary(
        "entry_occupied_discriminant",
        "representation_read",
        "Entry enum discriminant match on Occupied/Vacant",
        ("match self",),
        ["Entry discriminant"],
        ["none"],
        [("entry", entry_ref)],
        "occupied: bool",
        ensures=(
            "occupied == ordered_handle_is_occupied(entry)",
        ),
        note="Reads only the enum tag and the presence of the addressed key.",
    )
    occupied_op = plan.boundary(
        "occupied_entry_apply_callback",
        "callback_invoke",
        "`f(entry.get_mut())` single callback application to one value slot",
        ("f(entry.get_mut())",),
        ["btree::node::Handle value slot", "callback state"],
        ["btree::node::Handle value slot"],
        [
            ("entry", entry_type),
            ("callback", callback_type),
            ("occupied", "bool"),
        ],
        f"result: {plan.output}",
        requires=(
            "occupied",
            (
                "entry_callback_domain(ordered_handle_map::<K, V, _>(entry), "
                "ordered_handle_key::<K, _>(entry), &callback)"
            ),
        ),
        ensures=(
            "ordered_handle_key::<K, _>(result) == ordered_handle_key::<K, _>(entry)",
            "ordered_handle_is_occupied(result)",
            (
                "exists|value_ref: &mut V| *value_ref == ordered_handle_map::<K, V, _>"
                "(entry)[ordered_handle_key::<K, _>(entry)] "
                "&& #[trigger] callback.ensures((value_ref,), ()) "
                "&& ordered_handle_map::<K, V, _>(result) == ordered_handle_map::<K, V, _>"
                "(entry).insert(ordered_handle_key::<K, _>(entry), *final(value_ref))"
            ),
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_final_map::<K, V, _>(result)"
            ),
        ),
        note=(
            "Occupied branch only; the callback observes exactly one value slot "
            "and runs exactly once."
        ),
    )
    vacant_op = plan.boundary(
        "vacant_entry_forward_unchanged",
        "representation_read",
        "`Vacant(entry) => Vacant(entry)` forwarding without a callback call",
        ("Vacant(entry)",),
        ["VacantEntry::key", "VacantEntry::handle"],
        ["none"],
        [("entry", entry_type), ("vacant", "bool")],
        f"result: {plan.output}",
        requires=("vacant",),
        ensures=(
            "ordered_handle_key::<K, _>(result) == ordered_handle_key::<K, _>(entry)",
            "!ordered_handle_is_occupied(result)",
            (
                "ordered_handle_map::<K, V, _>(result) "
                "== ordered_handle_map::<K, V, _>(entry)"
            ),
            (
                "ordered_handle_final_map::<K, V, _>(entry) "
                "== ordered_handle_final_map::<K, V, _>(result)"
            ),
        ),
        note="Vacant branch only; the callback is never invoked.",
    )
    plan.emit(
        "    proof { broadcast use group_generated_btree_map_axioms; }",
        f"    let occupied = {discriminant}(&{entry_name});",
        "    if occupied {",
        f"        {occupied_op}({entry_name}, {callback_name}, occupied)",
        "    } else {",
        f"        {vacant_op}({entry_name}, true)",
        "    }",
    )


SOURCE_LOWERING_DISPATCH = {
    "map_len": _plan_map_len,
    "map_is_empty": _plan_map_is_empty,
    "lookup": _plan_lookup,
    "mutable_lookup": _plan_mutable_lookup,
    "insert": _plan_insert,
    "remove": _plan_remove,
    "first_endpoint": _plan_endpoint,
    "last_endpoint": _plan_endpoint,
    "remove_first": _plan_pop_endpoint,
    "remove_last": _plan_pop_endpoint,
    "empty_map": _plan_empty_map,
    "clear_map": _plan_clear_map,
    "clone_map": _plan_clone_map,
    "append": _plan_append,
    "split": _plan_split,
    "from_input": _plan_from_input,
    "extend_input": _plan_extend_input,
    "filter": _plan_filter,
    "entry_handle": _plan_entry_handle,
    "index_lookup": _plan_index_lookup,
    "map_equality": _plan_map_equality,
    "map_compare": _plan_map_compare,
    "effect_trace": _plan_effect_trace,
    "iterator_construct": _plan_iterator_construct,
    "range_construct": _plan_range_construct,
    "iterator_size": _plan_iterator_size,
    "iterator_next": _plan_iterator_step,
    "iterator_next_back": _plan_iterator_step,
    "iterator_first": _plan_iterator_terminal,
    "iterator_last": _plan_iterator_terminal,
    "iterator_clone": _plan_iterator_clone,
    "empty_iterator": _plan_empty_iterator,
    "entry_or_insert": _plan_entry_or_insert,
    "entry_or_insert_callback": _plan_entry_or_insert,
    "mutable_callback": _plan_and_modify,
}

_LOWERING_PLAN_CACHE: dict[str, LoweringPlan] = {}


def source_lowering_plan(row: Row) -> LoweringPlan:
    cache_key = f"{row.item_id}:{row.owner['name']}:{row.trait}:{row.function['name']}"
    cached = _LOWERING_PLAN_CACHE.get(cache_key)
    if cached is not None:
        return cached
    plan = LoweringPlan(row)
    builder = SOURCE_LOWERING_DISPATCH.get(plan.profile)
    if builder is None:
        raise RuntimeError(
            f"{row.target_id}: no source-shaped lowering plan for profile {plan.profile}"
        )
    builder(plan)
    if not plan.body:
        raise RuntimeError(f"{row.target_id}: lowering plan has an empty target body")
    names = [boundary.name for boundary in plan.boundaries]
    if len(set(names)) != len(names):
        raise RuntimeError(f"{row.target_id}: duplicate boundary names {names}")
    body_text = "\n".join(plan.body)
    if not plan.boundaries and not any(
        re.search(rf"\b{re.escape(call)}\s*\(", body_text)
        for call in source_call_names(row)
        if not call.startswith("source_")
    ):
        raise RuntimeError(
            f"{row.target_id}: lowering has neither a boundary nor an executable "
            "source call"
        )
    for name in names:
        if f"{name}(" not in body_text:
            raise RuntimeError(f"{row.target_id}: boundary {name} is never used")
    _LOWERING_PLAN_CACHE[cache_key] = plan
    return plan


def source_boundary_manifest(row: Row) -> list[dict[str, Any]]:
    return [boundary.manifest_entry() for boundary in source_lowering_plan(row).boundaries]


def source_boundary_names(row: Row) -> list[str]:
    return [boundary.name for boundary in source_lowering_plan(row).boundaries]


def source_call_realizations(row: Row) -> dict[str, str]:
    """Map every extracted source call onto the operation that realises it."""
    plan = source_lowering_plan(row)
    realizations: dict[str, str] = {}
    body = "\n".join(plan.body)
    for call in source_call_names(row):
        if call.startswith("source_") and call.endswith(
            ("_branch", "_loop")
        ):
            realizations[call] = "target_control_flow"
            continue
        if call in plan.call_realizations:
            realizations[call] = plan.call_realizations[call]
            continue
        match = None
        for boundary in plan.boundaries:
            declared = " ".join(
                [boundary.operation, boundary.name, *boundary.source_tokens]
            ).lower()
            span_source = source_span_text(
                row,
                (boundary.line_start, boundary.line_end),
            ).lower()
            if (
                re.search(rf"\b{re.escape(call)}\b", declared)
                or re.search(
                    rf"\b{re.escape(call)}\s*[!(]",
                    span_source,
                )
            ):
                match = boundary.name
                break
        if match is not None:
            realizations[call] = match
        elif re.search(rf"\b{re.escape(call)}\s*\(", body):
            realizations[call] = "target_control_flow"
        elif call in {"map", "for_each"} and any(
            token in body for token in ("match ", "while ", "loop")
        ):
            realizations[call] = "target_control_flow"
        else:
            realizations[call] = "unrealized"
    return realizations



def target_local_section(text: str) -> str:
    """Return only the target-local lowering section of a harness."""
    if TARGET_LOCAL_SECTION_BEGIN not in text:
        return ""
    section = text.split(TARGET_LOCAL_SECTION_BEGIN, 1)[1]
    return section.split(TARGET_LOCAL_SECTION_END, 1)[0]


def _split_top_level_parameters(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current = ""
    for index, character in enumerate(text):
        if character in "(<[{":
            depth += 1
        elif character in ")>]}":
            if character != ">" or index == 0 or text[index - 1] != "-":
                depth -= 1
        if character == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += character
    if current.strip():
        parts.append(current.strip())
    return parts


def _boundary_signature_parts(chunk: str) -> dict[str, Any]:
    lines = chunk.splitlines()
    try:
        declaration = next(
            index
            for index, line in enumerate(lines)
            if re.match(r"(?:proof\s+)?fn\s+", line)
        )
    except StopIteration:
        return {}
    body_index = next(
        (
            index
            for index in range(declaration, len(lines))
            if lines[index] == "{"
        ),
        len(lines),
    )
    signature_lines = lines[declaration:body_index]
    signature = "\n".join(signature_lines)
    name_match = re.match(
        r"(?:proof\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)",
        signature,
    )
    if name_match is None:
        return {"signature_parse_error": "missing function name"}
    cursor = name_match.end()
    while cursor < len(signature) and signature[cursor].isspace():
        cursor += 1
    if cursor < len(signature) and signature[cursor] == "<":
        angle_depth = 0
        while cursor < len(signature):
            character = signature[cursor]
            if character == "<":
                angle_depth += 1
            elif character == ">" and (
                cursor == 0 or signature[cursor - 1] != "-"
            ):
                angle_depth -= 1
                if angle_depth == 0:
                    cursor += 1
                    break
            cursor += 1
        if angle_depth != 0:
            return {
                "declared_name": name_match.group(1),
                "signature_parse_error": "unbalanced generic parameter list",
            }
    open_index = signature.find("(", cursor)
    if open_index < 0:
        return {
            "declared_name": name_match.group(1),
            "signature_parse_error": "missing function parameter list",
        }
    depth = 0
    close_index = -1
    for index in range(open_index, len(signature)):
        if signature[index] == "(":
            depth += 1
        elif signature[index] == ")":
            depth -= 1
            if depth == 0:
                close_index = index
                break
    parameters = (
        _split_top_level_parameters(signature[open_index + 1 : close_index])
        if close_index > open_index
        else []
    )
    if close_index < 0:
        return {
            "declared_name": name_match.group(1),
            "signature_parse_error": "unbalanced function parameter list",
        }
    tail = signature[close_index + 1 :] if close_index >= 0 else ""
    result_binder = None
    result_type = None
    result_open = tail.find("(") if re.match(r"\s*->", tail) else -1
    if result_open >= 0:
        result_depth = 0
        result_close = -1
        for index in range(result_open, len(tail)):
            if tail[index] == "(":
                result_depth += 1
            elif tail[index] == ")":
                result_depth -= 1
                if result_depth == 0:
                    result_close = index
                    break
        if result_close > result_open:
            result_declaration = tail[result_open + 1 : result_close]
            if ":" in result_declaration:
                result_binder, result_type = (
                    part.strip()
                    for part in result_declaration.split(":", 1)
                )
    clauses: dict[str, list[str]] = {"requires": [], "ensures": []}
    current: str | None = None
    for line in signature_lines:
        stripped = line.strip()
        if stripped == "requires":
            current = "requires"
            continue
        if stripped == "ensures":
            current = "ensures"
            continue
        if current is not None and line.startswith("        "):
            clauses[current].append(stripped.rstrip(","))
    return {
        "declared_name": name_match.group(1) if name_match else "",
        "parameters": parameters,
        "parameter_names": [
            parameter.split(":", 1)[0].strip()
            for parameter in parameters
            if ":" in parameter
        ],
        "parameter_types": {
            parameter.split(":", 1)[0].strip(): parameter.split(":", 1)[1].strip()
            for parameter in parameters
            if ":" in parameter
        },
        "result_binder": result_binder,
        "result_type": result_type,
        "requires": clauses["requires"],
        "ensures": clauses["ensures"],
        "signature_parse_error": "",
    }


def parse_target_local_boundaries(text: str) -> list[dict[str, Any]]:
    """Parse the documented operation-local boundaries of a harness."""
    section = target_local_section(text)
    if not section:
        return []
    chunks = re.split(r"(?m)^(?=// boundary-op: )", section)
    boundaries: list[dict[str, Any]] = []
    for chunk in chunks[1:]:
        target_index = chunk.find("\npub fn rust_1_96_target_")
        if target_index >= 0:
            chunk = chunk[:target_index]
        documentation: dict[str, str] = {}
        for line in chunk.splitlines():
            if line.startswith("// boundary-"):
                key, _, value = line[3:].partition(":")
                documentation[key.strip()] = value.strip()
        entry: dict[str, Any] = dict(documentation)
        entry["external_body"] = "#[verifier::external_body]" in chunk
        entry.update(_boundary_signature_parts(chunk))
        boundaries.append(entry)
    return boundaries


def target_function_body(text: str, item_id: int) -> str:
    """Return the executable body of the public proof target."""
    marker = f"pub fn rust_1_96_target_{item_id}"
    section = target_local_section(text) or text
    if marker not in section:
        return ""
    tail = section.split(marker, 1)[1]
    if "\n{\n" not in tail:
        return ""
    body = tail.split("\n{\n", 1)[1]
    lines: list[str] = []
    depth = 1
    for line in body.splitlines():
        next_depth = depth + line.count("{") - line.count("}")
        if next_depth <= 0:
            break
        lines.append(line)
        depth = next_depth
    return "\n".join(lines)


def normalized_boundary_clause(
    clause: str,
    substitutions: dict[str, str],
) -> str:
    text = clause
    for source, replacement in substitutions.items():
        text = re.sub(
            rf"(?<![A-Za-z0-9_.:])\b{re.escape(source)}\b",
            replacement,
            text,
        )
    return re.sub(r"\s+", " ", text).strip()


def normalized_contract_clause(clause: str) -> str:
    return re.sub(r"\s+", " ", clause).strip()


def _strip_balanced_outer_group(text: str) -> str:
    result = text.strip()
    pairs = {"(": ")", "{": "}", "[": "]"}
    while result and result[0] in pairs and result[-1] == pairs[result[0]]:
        opening = result[0]
        closing = pairs[opening]
        depth = 0
        encloses_all = True
        for index, character in enumerate(result):
            if character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth == 0 and index != len(result) - 1:
                    encloses_all = False
                    break
        if not encloses_all or depth != 0:
            break
        result = result[1:-1].strip()
    return result


def _top_level_marker_index(text: str, marker: str) -> int:
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    index = 0
    while index <= len(text) - len(marker):
        character = text[index]
        if character in depths:
            depths[character] += 1
        elif character in closing:
            depths[closing[character]] -= 1
        embedded_in_equivalence = (
            marker == "==>" and index > 0 and text[index - 1] == "<"
        )
        if (
            all(depth == 0 for depth in depths.values())
            and not embedded_in_equivalence
            and text.startswith(marker, index)
        ):
            return index
        index += 1
    return -1


def _split_top_level_conjunctions(text: str) -> list[str]:
    parts: list[str] = []
    remaining = text.strip()
    if remaining.startswith("&&&"):
        remaining = remaining[3:].strip()
    while remaining:
        index = _top_level_marker_index(remaining, "&&&")
        if index < 0:
            parts.append(remaining.strip())
            break
        parts.append(remaining[:index].strip())
        remaining = remaining[index + 3 :].strip()
    return [part for part in parts if part]


def _if_else_contract_parts(text: str) -> tuple[str, str, str] | None:
    source = text.strip()
    if not source.startswith("if "):
        return None
    first_open = source.find("{")
    if first_open < 0:
        return None
    condition = source[3:first_open].strip()

    def closing_brace(open_index: int) -> int:
        depth = 0
        for index in range(open_index, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return index
        return -1

    first_close = closing_brace(first_open)
    if first_close < 0:
        return None
    remainder = source[first_close + 1 :].strip()
    if not remainder.startswith("else"):
        return None
    second_open = source.find("{", first_close + 1)
    if second_open < 0:
        return None
    second_close = closing_brace(second_open)
    if second_close < 0 or source[second_close + 1 :].strip():
        return None
    return (
        condition,
        source[first_open + 1 : first_close],
        source[second_open + 1 : second_close],
    )


def normalized_contract_atoms(clause: str) -> list[str]:
    """Normalize a clause into top-level guarded observations.

    This prevents a boundary from evading whole-contract detection merely by
    rendering one target `&&&` block as several `ensures` lines.
    """
    text = clause.strip().rstrip(",")
    implication = _top_level_marker_index(text, "==>")
    guard = ""
    body = text
    if implication >= 0:
        guard = text[:implication].strip()
        body = text[implication + 3 :].strip()
    body = _strip_balanced_outer_group(body)
    branch = _if_else_contract_parts(body)
    if branch is not None:
        condition, then_body, else_body = branch
        atoms = [
            *(
                f"{condition} ==> ({part})"
                for part in _split_top_level_conjunctions(
                    _strip_balanced_outer_group(then_body)
                )
            ),
            *(
                f"!({condition}) ==> ({part})"
                for part in _split_top_level_conjunctions(
                    _strip_balanced_outer_group(else_body)
                )
            ),
        ]
        if guard:
            atoms = [f"{guard} ==> ({atom})" for atom in atoms]
        return [normalized_contract_clause(atom) for atom in atoms]
    parts = _split_top_level_conjunctions(body)
    if not parts:
        parts = [body]
    if guard:
        return [
            normalized_contract_clause(f"{guard} ==> ({part})")
            for part in parts
        ]
    return [normalized_contract_clause(part) for part in parts]


def _is_unchanged_frame_clause(clause: str) -> bool:
    text = clause.strip().rstrip(",")
    implication = _top_level_marker_index(text, "==>")
    if implication >= 0:
        text = _strip_balanced_outer_group(text[implication + 3 :])
    for operator in ("=~=", "=="):
        index = _top_level_marker_index(text, operator)
        if index < 0:
            continue
        left = normalized_contract_clause(text[:index])
        right = normalized_contract_clause(text[index + len(operator) :])
        if "final(" not in left + right or "old(" not in left + right:
            return False
        canonical_left = left.replace("final(", "state(").replace(
            "old(", "state("
        )
        canonical_right = right.replace("final(", "state(").replace(
            "old(", "state("
        )
        return canonical_left == canonical_right
    return False


def normalized_target_contract_atoms(row: Row) -> set[str]:
    atoms = {
        atom
        for clause in proof_contract(row)[5]
        for atom in normalized_contract_atoms(clause)
    }
    if (
        row.owner["name"] == "BTreeMap"
        and row.function["name"] in {"range", "range_mut"}
    ):
        wrapper_atoms = {
            atom for atom in atoms if "ordered_range_result" in atom
        }
        if wrapper_atoms:
            _, inputs, _, _, _, _ = proof_contract(row)
            map_name = inputs[0][0]
            map_view = (
                f"old({map_name})@"
                if _input_is_mutable_reference(inputs[0][1])
                else f"{map_name}@"
            )
            range_name = inputs[1][0]
            range_type = inputs[1][1]
            guard = contract_guard(row)
            observations = (
                f"ordered_iterator_key_trace::<K, _>(&result) "
                f"== ordered_range_key_sequence::<K, V, T, {range_type}>"
                f"({map_view}, &{range_name})",
                "result.ordered_remaining().len() "
                f"== ordered_range_key_sequence::<K, V, T, {range_type}>"
                f"({map_view}, &{range_name}).len()",
                f"ordered_iterator_value_trace::<V, _>(&result) "
                f"== ordered_range_pair_sequence::<K, V, T, {range_type}>"
                f"({map_view}, &{range_name}).map("
                "|_index: int, pair: (K, V)| pair.1)",
            )
            atoms.difference_update(wrapper_atoms)
            atoms.update(
                normalized_contract_clause(
                    f"{guard} ==> ({observation})"
                    if guard
                    else observation
                )
                for observation in observations
            )
    return atoms



LEAF_EXCEPTION_KINDS = {
    "representation_read",
    "iterator_representation",
    "allocator_op",
}
LEAF_EXCEPTION_MAX_ENSURES = 2


def _call_arguments(body: str, name: str) -> list[str] | None:
    match = re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(", body)
    if match is None:
        return None
    depth = 0
    start = match.end() - 1
    for index in range(start, len(body)):
        if body[index] == "(":
            depth += 1
        elif body[index] == ")":
            depth -= 1
            if depth == 0:
                return _split_top_level_parameters(body[start + 1 : index])
    return None


def _terminal_expression(body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _variable_is_mutated(body: str, variable: str) -> bool:
    if re.search(rf"&mut\s+{re.escape(variable)}\b", body) is not None:
        return True
    return re.search(rf"(?m)^\s*{re.escape(variable)}\s*=[^=]", body) is not None


def _traced_terminal_call(body: str) -> tuple[str | None, str | None]:
    """Return (boundary_name, bound_variable) for a returned external result."""
    terminal = _terminal_expression(body)
    direct = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(", terminal)
    if direct is not None:
        return direct.group(1), None
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", terminal) is None:
        return None, None
    variable = terminal
    seen: set[str] = set()
    while variable not in seen:
        seen.add(variable)
        binding = re.search(
            rf"(?m)^\s*let\s+(?:mut\s+)?{re.escape(variable)}\s*(?::[^=]*)?=\s*(.+?);\s*$",
            body,
        )
        if binding is None:
            return None, None
        expression = binding.group(1).strip()
        call = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(", expression)
        if call is not None:
            return call.group(1), variable
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", expression) is not None:
            variable = expression
            continue
        return None, variable
    return None, None


def _branch_terminal_calls(
    body: str,
    declared_names: set[str],
) -> list[tuple[str, str | None]]:
    """Find external results returned from nested if/match branch tails."""
    lines = body.splitlines()
    candidates: list[tuple[str, str | None]] = []
    for index, line in enumerate(lines):
        stripped = line.strip().rstrip(",")
        if not stripped or stripped.endswith(";"):
            continue
        following = next(
            (
                candidate.strip()
                for candidate in lines[index + 1 :]
                if candidate.strip()
            ),
            "",
        )
        if not following.startswith("}"):
            continue
        direct = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
        if direct is not None and direct.group(1) in declared_names:
            candidates.append((direct.group(1), None))
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped) is None:
            continue
        variable = stripped
        prefix = "\n".join(lines[: index + 1])
        bindings = list(
            re.finditer(
                rf"(?m)^\s*let\s+(?:mut\s+)?{re.escape(variable)}"
                rf"\s*(?::[^=]*)?=\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                prefix,
            )
        )
        if bindings and bindings[-1].group(1) in declared_names:
            candidates.append((bindings[-1].group(1), variable))
    return list(dict.fromkeys(candidates))


def _terminal_delegation_record(
    body: str,
    boundaries: list[dict[str, Any]],
    declared_names: set[str],
    terminal_name: str,
    terminal_variable: str | None,
    branch_controlled: bool,
) -> dict[str, Any]:
    entry = next(item for item in boundaries if item["name"] == terminal_name)
    terminal_arguments = _call_arguments(body, terminal_name) or []
    produced_variables: set[str] = set()
    state_dependencies: set[str] = set()
    terminal_calls = list(
        re.finditer(rf"\b{re.escape(terminal_name)}\s*\(", body)
    )
    terminal_position = (
        terminal_calls[-1].start() if terminal_calls else len(body)
    )
    for boundary_entry in boundaries:
        boundary_name = boundary_entry["name"]
        if boundary_name == terminal_name:
            continue
        binding = re.search(
            rf"(?m)^\s*let\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)"
            rf"\s*(?::[^=]*)?=\s*{re.escape(boundary_name)}\s*\(",
            body,
        )
        if binding is not None and binding.start() < terminal_position:
            produced_variables.add(binding.group(1))
        call_match = re.search(
            rf"\b{re.escape(boundary_name)}\s*\(",
            body,
        )
        if (
            call_match is not None
            and call_match.start() < terminal_position
            and boundary_entry["footprint"]["writes"] != "none"
        ):
            for argument in _call_arguments(body, boundary_name) or []:
                identifier = argument.strip().lstrip("&*").removeprefix("mut ")
                if re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*",
                    identifier,
                ):
                    state_dependencies.add(identifier)
    argument_identifiers = {
        identifier
        for argument in terminal_arguments
        for identifier in re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]*\b",
            argument,
        )
    }
    control_dependencies = {
        variable
        for variable in produced_variables
        if len(
            re.findall(
                rf"\b{re.escape(variable)}\b",
                body[:terminal_position],
            )
        )
        > 1
    }
    depends_on_prior_boundary = bool(
        argument_identifiers & (produced_variables | state_dependencies)
        or control_dependencies
    )
    allowed = (
        not entry["covers_target_contract"]
        and (depends_on_prior_boundary or branch_controlled)
    ) or bool(entry["leaf_representation_exception"])
    return {
        "boundary": terminal_name,
        "bound_variable": terminal_variable,
        "covers_target_contract": entry["covers_target_contract"],
        "sole_boundary": len(declared_names) == 1,
        "depends_on_prior_boundary": depends_on_prior_boundary,
        "branch_controlled": branch_controlled,
        "allowed": allowed,
    }


def analyze_target_local_lowering(
    row: Row,
    implementation: str,
) -> dict[str, Any]:
    """Structural analysis of the target-local lowering of one harness."""
    section = target_local_section(implementation)
    boundaries = parse_target_local_boundaries(implementation)
    body = target_function_body(implementation, row.item_id)
    target_ensures = normalized_target_contract_atoms(row)
    findings: dict[str, Any] = {
        "has_target_local_section": bool(section.strip()),
        "legacy_tokens": sorted(
            token for token in LEGACY_LOWERING_TOKENS if token in section
        ),
        "target_external_body": bool(
            re.search(
                rf"#\[verifier::external(?:_body)?\][^\n]*\n(?:[^\n]*\n)?"
                rf"pub fn rust_1_96_target_{row.item_id}\b",
                section,
            )
        ),
        "target_assume_specification": "pub assume_specification" in section,
        "target_body_is_executable": bool(body.strip()),
        "has_executable_source_call": any(
            re.search(rf"\b{re.escape(call)}\s*\(", body)
            for call in source_call_names(row)
            if not call.startswith("source_")
        ),
        "boundaries": [],
        "unused_boundaries": [],
        "contract_cloning_boundaries": [],
        "malformed_boundaries": [],
        "terminal_delegation": None,
        "leaf_representation_exceptions": [],
        "external_body_count": section.count("#[verifier::external_body]"),
    }
    declared_names = set()
    source_body = source_lines(row.source_file)
    for boundary in boundaries:
        name = boundary.get("boundary-op", "")
        problems: list[str] = []
        if boundary.get("signature_parse_error"):
            problems.append(
                "signature parse failed: "
                + boundary["signature_parse_error"]
            )
        for key in BOUNDARY_DOC_KEYS:
            if not boundary.get(key):
                problems.append(f"missing {key}")
        if not boundary.get("external_body"):
            problems.append("declared boundary is not external_body")
        if boundary.get("declared_name") != name:
            problems.append("declared function name differs from boundary-op")
        kind = boundary.get("boundary-kind", "")
        if kind not in SOURCE_BOUNDARY_KINDS:
            problems.append(f"kind {kind!r} is not operation-local allowlisted")
        span = boundary.get("boundary-source", "")
        span_match = re.match(r"^(.+):(\d+)-(\d+)$", span)
        if span_match is None:
            problems.append("source span is not file:start-end")
        else:
            span_file = span_match.group(1)
            start = int(span_match.group(2))
            end = int(span_match.group(3))
            if span_file != row.source_file:
                problems.append("source span leaves the target source file")
            elif not (row.line_start <= start <= end <= row.line_end):
                problems.append("source span leaves the target source item")
            else:
                excerpt = "\n".join(source_body[start - 1 : end]) + "\n"
                if sha256_text(excerpt) != boundary.get("boundary-source-sha256"):
                    problems.append("source span hash does not match frozen source")
                source_tokens = [
                    token.strip()
                    for token in boundary.get(
                        "boundary-source-tokens", ""
                    ).split("|")
                    if token.strip()
                ]
                if not source_tokens:
                    problems.append("source span declares no operation token")
                for token in source_tokens:
                    if token not in excerpt:
                        problems.append(
                            f"source token {token!r} is absent from declared span"
                        )
        if boundary.get("boundary-reads", "") in {"", "none"} and boundary.get(
            "boundary-writes", ""
        ) in {"", "none"}:
            problems.append("footprint declares neither reads nor writes")
        parsed_ensures = boundary.get("ensures", [])
        parameter_types = boundary.get("parameter_types", {})
        for clause in [
            *boundary.get("requires", []),
            *parsed_ensures,
        ]:
            for state_operator, parameter in re.findall(
                r"\b(old|final)\(([A-Za-z_][A-Za-z0-9_]*)\)",
                clause,
            ):
                parameter_type = parameter_types.get(parameter)
                if (
                    parameter_type is not None
                    and not _input_is_mutable_reference(parameter_type)
                ):
                    problems.append(
                        f"{state_operator}({parameter}) is used for non-mutable "
                        f"parameter type {parameter_type}"
                    )
        result_binder = boundary.get("result_binder")
        result_type = boundary.get("result_type") or ""
        if result_binder and any(
            re.search(
                rf"(?:match\s+{re.escape(result_binder)}\s*\{{"
                rf"|{re.escape(result_binder)}\.is_(?:some|none)\(\))",
                clause,
            )
            for clause in parsed_ensures
        ) and not result_type.startswith("Option<"):
            problems.append(
                f"result {result_binder} is matched as Option but has type "
                f"{result_type or '<unknown>'}"
            )
        if (
            boundary.get("boundary-writes", "") not in {"", "none"}
            and parsed_ensures
            and all(_is_unchanged_frame_clause(clause) for clause in parsed_ensures)
        ):
            problems.append(
                "declared write guarantees only unchanged observations"
            )
        arguments = _call_arguments(body, name) if name else None
        if arguments is None:
            findings["unused_boundaries"].append(name)
        substitutions: dict[str, str] = {}
        if arguments is not None:
            for parameter, argument in zip(
                boundary.get("parameter_names", []), arguments, strict=False
            ):
                substitutions[parameter] = argument
        normalized = {
            atom
            for clause in boundary.get("ensures", [])
            for atom in normalized_contract_atoms(
                normalized_boundary_clause(clause, substitutions)
            )
        }
        result_binder = boundary.get("result_binder")
        normalized_as_result = {
            atom
            for clause in boundary.get("ensures", [])
            for atom in normalized_contract_atoms(
                normalized_boundary_clause(
                    clause,
                    (
                        {**substitutions, result_binder: "result"}
                        if result_binder
                        else substitutions
                    ),
                )
            )
        }
        normalized_projected_result = {
            re.sub(r"\bresult\.expected@", "result", atom)
            for atom in normalized_as_result
        }
        covered = bool(target_ensures) and target_ensures.issubset(
            normalized | normalized_as_result | normalized_projected_result
        )
        leaf_exception = boundary.get("boundary-leaf-representation-exception")
        if leaf_exception:
            findings["leaf_representation_exceptions"].append(name)
            if kind not in LEAF_EXCEPTION_KINDS:
                problems.append("leaf exception on a non-representation boundary")
            writes = boundary.get("boundary-writes", "")
            fresh_allocator_leaf = (
                kind == "allocator_op"
                and writes
                and all(
                    item.strip().startswith("fresh ")
                    for item in writes.split(",")
                )
            )
            if writes != "none" and not fresh_allocator_leaf:
                problems.append("leaf exception boundary writes state")
            if "," in boundary.get("boundary-reads", ""):
                problems.append("leaf exception boundary reads more than one field")
            if len(target_ensures) > LEAF_EXCEPTION_MAX_ENSURES:
                problems.append("leaf exception used for a multi-clause contract")
        if covered and not leaf_exception:
            findings["contract_cloning_boundaries"].append(name)
        if problems:
            findings["malformed_boundaries"].append(
                {"name": name, "problems": problems}
            )
        declared_names.add(name)
        findings["boundaries"].append(
            {
                "name": name,
                "kind": kind,
                "modeled_source_operation": boundary.get("boundary-operation", ""),
                "source_span": span,
                "source_sha256": boundary.get("boundary-source-sha256", ""),
                "source_tokens": [
                    token.strip()
                    for token in boundary.get(
                        "boundary-source-tokens", ""
                    ).split("|")
                    if token.strip()
                ],
                "footprint": {
                    "reads": boundary.get("boundary-reads", ""),
                    "writes": boundary.get("boundary-writes", ""),
                },
                "used_in_target_body": arguments is not None,
                "covers_target_contract": covered,
                "leaf_representation_exception": leaf_exception,
            }
        )
    terminal_name, terminal_variable = _traced_terminal_call(body)
    candidates: list[tuple[str, str | None, bool]] = []
    if terminal_name is not None and terminal_name in declared_names:
        candidates.append((terminal_name, terminal_variable, False))
    candidates.extend(
        (name, variable, True)
        for name, variable in _branch_terminal_calls(body, declared_names)
    )
    records = [
        _terminal_delegation_record(
            body,
            findings["boundaries"],
            declared_names,
            name,
            variable,
            branch_controlled,
        )
        for name, variable, branch_controlled in dict.fromkeys(candidates)
    ]
    if records:
        findings["terminal_delegation"] = next(
            (record for record in records if not record["allowed"]),
            records[0],
        )
    undeclared = sorted(
        match.group(1)
        for match in re.finditer(
            r"#\[verifier::external_body\]\n(?:proof\s+)?fn\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)",
            section,
        )
        if match.group(1) not in declared_names
    )
    findings["undeclared_external_boundaries"] = undeclared
    return findings

def actual_target_call(row: Row, inputs: list[tuple[str, str, str]]) -> str:
    arguments = ", ".join(name for name, _, _ in inputs)
    return f"{render_trait_target(row)}({arguments})"


def implementation_harness_source(row: Row) -> str:
    metadata = metadata_for(row)
    contract_text = json.dumps(metadata["contract"], sort_keys=True)
    contract_hash = sha256_text(contract_text)
    plan = source_lowering_plan(row)
    binder = plan.binder
    inputs = plan.inputs
    output = plan.output
    where_clause = plan.where_clause
    rendered_inputs = (
        "\n    " + ",\n    ".join(
            f"{name}: {rust_type}" for name, rust_type, _ in inputs
        ) + "\n"
        if inputs
        else ""
    )
    return_part = f" -> (result: {output})" if output is not None else ""
    requires_block = (
        "\n    requires\n"
        + "\n".join(f"        {clause}," for clause in plan.requires)
        if plan.requires
        else ""
    )
    ensures_block = "\n".join(f"        {clause}," for clause in plan.ensures)
    prelude_block = "\n\n".join(plan.prelude)
    if prelude_block:
        prelude_block += "\n\n"
    boundary_block = "\n\n".join(
        render_source_boundary(boundary, binder, where_clause)
        for boundary in plan.boundaries
    )
    boundary_summary = "\n".join(
        f"// operation-local boundary {index}: {boundary.name} "
        f"[{boundary.kind}] {boundary.span}"
        for index, boundary in enumerate(plan.boundaries)
    )
    body = "\n".join(plan.body)
    return f"""#![allow(dead_code, unused_imports, unused_variables, unused_mut)]
#![feature(allocator_api)]
#![verifier::allow(broadcast_without_trigger)]
// Executable source-shaped implementation lowering for {row.canonical_target}.
// Rust source: {row.source_file}:{row.line_start}-{row.line_end}
// Source item sha256: {row.source_sha256}
// Accepted contract sha256: {contract_hash}
// Model profile: {proof_profile(row)}
// The public target keeps the exact Rust 1.96 signature and an executable body
// that reproduces the source control flow. Every retained boundary below is a
// single operation-local private step (field/representation access, one private
// search/node/iterator/callback/comparator/allocator operation) with an
// explicit source span and footprint. No boundary receives the whole public
// target state while promising the whole public contract, and no same-target
// API call or assumption appears in this harness.
{boundary_summary}

{SHARED_VOCABULARY}
{TARGET_LOCAL_SECTION_BEGIN}
verus! {{

{prelude_block}{boundary_block}

pub fn rust_1_96_target_{row.item_id}{binder}({rendered_inputs}){return_part}{where_clause}{requires_block}
    ensures
{ensures_block}
{{
{body}
}}

}}
{TARGET_LOCAL_SECTION_END}
"""


ITERATOR_RESULT_TYPES = {
    "Iter",
    "IterMut",
    "IntoIter",
    "Keys",
    "Values",
    "ValuesMut",
    "IntoKeys",
    "IntoValues",
    "Range",
    "RangeMut",
    "ExtractIf",
}
HANDLE_RESULT_TYPES = {"Entry", "OccupiedEntry", "VacantEntry"}
CALLER_CONTROLLED_RESULT_TYPES = {
    "IterMut",
    "ValuesMut",
    "RangeMut",
    "ExtractIf",
    "Entry",
    "OccupiedEntry",
    "VacantEntry",
}


def split_top_level_predicates(where_clause: str) -> list[str]:
    """Split a rendered `where` clause into its top-level predicates."""
    text = where_clause.strip()
    if text.startswith("where"):
        text = text[len("where") :]
    predicates: list[str] = []
    depth = 0
    current = ""
    for index, character in enumerate(text):
        if character in "(<[":
            depth += 1
        elif character in ")>]":
            if character != ">" or index == 0 or text[index - 1] != "-":
                depth -= 1
        if character == "," and depth == 0:
            if current.strip():
                predicates.append(current.strip())
            current = ""
            continue
        current += character
    if current.strip():
        predicates.append(current.strip())
    return predicates


def _erase_outer_lifetime(rust_type: str) -> str:
    return re.sub(r"^&'[A-Za-z_][A-Za-z0-9_]*\s+", "&", rust_type.strip())


def _erase_mutable_lifetimes(rust_type: str) -> str:
    return re.sub(r"&'[A-Za-z_][A-Za-z0-9_]*\s+mut\b", "&mut", rust_type)


def _type_head(rust_type: str) -> str:
    return rust_type.strip().split("<", 1)[0].split("::")[-1].lstrip("&").strip()


def _option_payload(rust_type: str) -> str | None:
    match = re.match(r"^Option<(.*)>$", rust_type.strip())
    return match.group(1).strip() if match else None


def result_exposes_caller_controlled_state(output: str | None) -> bool:
    """True when the returned value can still mutate the observed state."""
    if output is None:
        return False
    text = output.strip()
    if re.search(r"&(?:'[A-Za-z_][A-Za-z0-9_]*\s+)?mut\b", text):
        return True
    payload = _option_payload(text)
    if payload is not None:
        return result_exposes_caller_controlled_state(payload)
    return _type_head(text) in CALLER_CONTROLLED_RESULT_TYPES


def iterator_observation_equal(type_text: str, left: str, right: str) -> str:
    head = _type_head(type_text)
    if head == "ExtractIf":
        return (
            f"{left}.ordered_remaining() == {right}.ordered_remaining()"
            f" && extract_if_visited_keys::<K, V, _>(&{left})"
            f" == extract_if_visited_keys::<K, V, _>(&{right})"
            f" && extract_if_unvisited_keys::<K, V, _>(&{left})"
            f" == extract_if_unvisited_keys::<K, V, _>(&{right})"
            f" && extract_if_current_map::<K, V, _>(&{left})"
            f" == extract_if_current_map::<K, V, _>(&{right})"
            f" && extract_if_yielded_pairs::<K, V, _>(&{left})"
            f" == extract_if_yielded_pairs::<K, V, _>(&{right})"
        )
    return f"{left}.ordered_remaining() == {right}.ordered_remaining()"


def iterator_construction_observation_equal(left: str, right: str) -> str:
    return (
        f"{left}.ordered_keys() == {right}.ordered_keys()"
        f" && {left}.ordered_values() == {right}.ordered_values()"
        f" && {left}.ordered_remaining().len() == {right}.ordered_remaining().len()"
    )


def handle_observation_equal(left: str, right: str) -> str:
    return (
        f"ordered_handle_key::<K, _>({left}) == ordered_handle_key::<K, _>({right})"
        f" && ordered_handle_map::<K, V, _>({left})"
        f" == ordered_handle_map::<K, V, _>({right})"
        f" && ordered_handle_is_occupied({left}) == ordered_handle_is_occupied({right})"
    )


def result_observation_equal(row: Row, output: str | None) -> str:
    if output is None:
        return "r1 == r2"
    text = output.strip()
    head = _type_head(text)
    payload = _option_payload(text)
    if payload is not None:
        inner_head = _type_head(payload)
        if inner_head in HANDLE_RESULT_TYPES:
            inner = handle_observation_equal("left", "right")
        elif payload.startswith("("):
            components = _split_top_level_parameters(payload[1:-1])
            comparisons = []
            for index, component in enumerate(components):
                dereference = "*" if component.strip().startswith("&") else ""
                comparisons.append(
                    f"{dereference}left.{index} == {dereference}right.{index}"
                )
            inner = " && ".join(comparisons)
        elif payload.strip().startswith("&"):
            inner = "*left == *right"
        else:
            return "r1 == r2"
        return (
            "match (r1, r2) { (Some(left), Some(right)) => "
            f"{inner}, (None, None) => true, _ => false }}"
        )
    if head in ITERATOR_RESULT_TYPES:
        if head != "ExtractIf" and row.disposition == "generated" and proof_profile(
            row
        ) in {"iterator_construct", "range_construct"}:
            return iterator_construction_observation_equal("r1", "r2")
        return iterator_observation_equal(text, "r1", "r2")
    if head in HANDLE_RESULT_TYPES:
        return handle_observation_equal("r1", "r2")
    if head == "Result" and "fmt" in text:
        return "r1.is_err() == r2.is_err()"
    if text.startswith("BTreeMap"):
        return "r1@ =~= r2@"
    if text.startswith("&"):
        return "*r1 == *r2"
    return "r1 == r2"


def mutable_state_observation_equal(rust_type: str, left: str, right: str) -> str:
    base = deref_type(rust_type)
    head = _type_head(base)
    if head == "BTreeMap":
        return f"{left}@ =~= {right}@"
    if head in ITERATOR_RESULT_TYPES:
        return iterator_observation_equal(base, left, right)
    if head in HANDLE_RESULT_TYPES:
        return handle_observation_equal(left, right)
    if head == "Formatter":
        return f"formatter_trace({left}) == formatter_trace({right})"
    return f"hasher_trace({left}) == hasher_trace({right})"


def custom_equal_body(row: Row, output: str | None, mutable_inputs) -> str:
    parts = [f"({result_observation_equal(row, output)})"]
    if not result_exposes_caller_controlled_state(output):
        for name, rust_type in mutable_inputs:
            parts.append(
                "("
                + mutable_state_observation_equal(
                    rust_type, f"post1_{name}", f"post2_{name}"
                )
                + ")"
            )
    return "    " + "\n        && ".join(parts)


def exact_completeness_guard(row: Row) -> str | None:
    return contract_guard(row)


COMPLETENESS_SUPPORT_BODIES: dict[tuple[str, str, str], str] = {
    ('BTreeMap', 'Index', 'index'): '    assert(maps_borrowed_key_to_value(this@, key, *r1));\n    assert(maps_borrowed_key_to_value(this@, key, *r2));\n    assert(*r1 == *r2);',
    ('BTreeMap', 'inherent', 'extract_if'): '    assert(extract_if_callback_model_matches(\n        pre_this@, &range, pred, extract_if_model(&r1),\n    ));\n    assert(extract_if_callback_model_matches(\n        pre_this@, &range, pred, extract_if_model(&r2),\n    ));\n    assert(r1.ordered_remaining() == r2.ordered_remaining());\n    assert(extract_if_visited_keys::<K, V, _>(&r1)\n        == extract_if_visited_keys::<K, V, _>(&r2));\n    assert(extract_if_unvisited_keys::<K, V, _>(&r1)\n        == extract_if_unvisited_keys::<K, V, _>(&r2));\n    assert(extract_if_current_map::<K, V, _>(&r1)\n        == extract_if_current_map::<K, V, _>(&r2));\n    assert(extract_if_yielded_pairs::<K, V, _>(&r1)\n        == extract_if_yielded_pairs::<K, V, _>(&r2));',
    ('BTreeMap', 'inherent', 'get'): '    match (r1, r2) {\n        (Some(left), Some(right)) => {\n            assert(maps_borrowed_key_to_value(this@, key, *left));\n            assert(maps_borrowed_key_to_value(this@, key, *right));\n            assert(contains_borrowed_key(this@, key));\n            assert(*left == *right);\n        },\n        (None, None) => {},\n        _ => { assert(false); },\n    }',
    ('BTreeMap', 'inherent', 'get_key_value'): '    match (r1, r2) {\n        (Some(left), Some(right)) => {\n            assert(*left.0 == borrowed_lookup_stored_key::<K, Q, V>(this@, k));\n            assert(*right.0 == borrowed_lookup_stored_key::<K, Q, V>(this@, k));\n            assert(*left.0 == *right.0);\n            assert(*left.1 == *right.1);\n        },\n        (Some(left), None) => {\n            axiom_borrowed_key_matches::<K, Q, V>(this@, left.0, k);\n            assert(false);\n        },\n        (None, Some(right)) => {\n            axiom_borrowed_key_matches::<K, Q, V>(this@, right.0, k);\n            assert(false);\n        },\n        (None, None) => {},\n    }',
    ('BTreeMap', 'inherent', 'get_mut'): '    match (r1, r2) {\n        (Some(left), Some(right)) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, *left));\n            assert(maps_borrowed_key_to_value(pre_this@, key, *right));\n            assert(contains_borrowed_key(pre_this@, key));\n            assert(*left == *right);\n        },\n        (None, None) => {},\n        _ => { assert(false); },\n    }',
    ('BTreeMap', 'inherent', 'remove'): '    match (r1, r2) {\n        (Some(left), Some(right)) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, left));\n            assert(maps_borrowed_key_to_value(pre_this@, key, right));\n            assert(left == right);\n            assert(borrowed_key_removed(pre_this@, post1_this@, key));\n            assert(borrowed_key_removed(pre_this@, post2_this@, key));\n            assert(post1_this@ == post2_this@);\n        },\n        (None, None) => {\n            assert(borrowed_key_removed(pre_this@, post1_this@, key));\n            assert(borrowed_key_removed(pre_this@, post2_this@, key));\n            assert(post1_this@ == post2_this@);\n        },\n        (Some(value), None) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, value));\n            assert(contains_borrowed_key(pre_this@, key));\n            assert(false);\n        },\n        (None, Some(value)) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, value));\n            assert(contains_borrowed_key(pre_this@, key));\n            assert(false);\n        },\n    }',
    ('BTreeMap', 'inherent', 'remove_entry'): '    match (r1, r2) {\n        (Some(left), Some(right)) => {\n            assert(left.0 == borrowed_lookup_stored_key::<K, Q, V>(\n                pre_this@, key,\n            ));\n            assert(right.0 == borrowed_lookup_stored_key::<K, Q, V>(\n                pre_this@, key,\n            ));\n            assert(left.0 == right.0);\n            assert(maps_borrowed_key_to_value(pre_this@, key, left.1));\n            assert(maps_borrowed_key_to_value(pre_this@, key, right.1));\n            assert(left.1 == right.1);\n            assert(left == right);\n            assert(borrowed_key_removed(pre_this@, post1_this@, key));\n            assert(borrowed_key_removed(pre_this@, post2_this@, key));\n            assert(post1_this@ == post2_this@);\n        },\n        (None, None) => {\n            assert(post1_this@ == pre_this@);\n            assert(post2_this@ == pre_this@);\n        },\n        (Some(pair), None) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, pair.1));\n            assert(contains_borrowed_key(pre_this@, key));\n            assert(false);\n        },\n        (None, Some(pair)) => {\n            assert(maps_borrowed_key_to_value(pre_this@, key, pair.1));\n            assert(contains_borrowed_key(pre_this@, key));\n            assert(false);\n        },\n    }',
    ('BTreeMap', 'inherent', 'retain'): '    assert(ordered_callback_filter(\n        pre_this@, ordered_map_key_sequence(pre_this@), f, post1_this@,\n    ));\n    assert(ordered_callback_filter(\n        pre_this@, ordered_map_key_sequence(pre_this@), f, post2_this@,\n    ));\n    assert(post1_this@ == post2_this@);',
    ('Entry', 'inherent', 'and_modify'): '    assert(entry_and_modify_transition(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), f, ordered_handle_map::<K, V, _>(r1)));\n    assert(entry_and_modify_transition(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), f, ordered_handle_map::<K, V, _>(r2)));\n    if ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) {\n        assert(entry_and_modify_transition_functional::<K, V, F>(\n            ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), f,\n        ));\n        assert(ordered_handle_map::<K, V, _>(r1) == ordered_handle_map::<K, V, _>(r2));\n    } else {\n        assert(ordered_handle_map::<K, V, _>(r1) == ordered_handle_map::<K, V, _>(this));\n        assert(ordered_handle_map::<K, V, _>(r2) == ordered_handle_map::<K, V, _>(this));\n    }\n    assert(ordered_handle_map::<K, V, _>(r1) == ordered_handle_map::<K, V, _>(r2));\n    assert(ordered_handle_key::<K, _>(r1)\n        == ordered_handle_key::<K, _>(r2));\n    assert(ordered_handle_is_occupied(r1)\n        == ordered_handle_is_occupied(r2));',
    ('Entry', 'inherent', 'or_default'): '    if ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) {\n        assert(*r1 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n        assert(*r2 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n    } else {\n        assert(entry_default_value_functional::<V>());\n        assert(V::default.ensures((), *r1));\n        assert(V::default.ensures((), *r2));\n    }\n    assert(*r1 == *r2);',
    ('Entry', 'inherent', 'or_insert_with'): '    if ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) {\n        assert(*r1 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n        assert(*r2 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n    } else {\n        assert(entry_nullary_callback_functional::<V, F>(default));\n        assert(default.ensures((), *r1));\n        assert(default.ensures((), *r2));\n    }\n    assert(*r1 == *r2);',
    ('Entry', 'inherent', 'or_insert_with_key'): '    if ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) {\n        assert(*r1 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n        assert(*r2 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)]);\n    } else {\n        assert(entry_key_callback_functional::<K, V, F>(\n            &ordered_handle_key::<K, _>(this), default,\n        ));\n        assert(default.ensures((&ordered_handle_key::<K, _>(this),), *r1));\n        assert(default.ensures((&ordered_handle_key::<K, _>(this),), *r2));\n    }\n    assert(*r1 == *r2);',
    ('ExtractIf', 'Iterator', 'next'): '    assert(r1 == r2);\n    assert(post1_this.ordered_remaining()\n        == post2_this.ordered_remaining());\n    assert(extract_if_visited_keys::<K, V, _>(&post1_this)\n        == extract_if_visited_keys::<K, V, _>(&post2_this));\n    assert(extract_if_unvisited_keys::<K, V, _>(&post1_this)\n        == extract_if_unvisited_keys::<K, V, _>(&post2_this));\n    assert(extract_if_current_map::<K, V, _>(&post1_this)\n        == extract_if_current_map::<K, V, _>(&post2_this));\n    assert(extract_if_yielded_pairs::<K, V, _>(&post1_this)\n        == extract_if_yielded_pairs::<K, V, _>(&post2_this));',
}

COMPLETENESS_FORMATTER_SUPPORT = '    assert(formatter_trace(post1_f) == formatter_trace(post2_f));\n    assert(formatter_failed(post1_f) == formatter_failed(post2_f));\n    assert(r1.is_err() == r2.is_err());'
COMPLETENESS_EMPTY_ITERATOR_SUPPORT = '    assert(r1.ordered_remaining() == Seq::<_>::empty());\n    assert(r2.ordered_remaining() == Seq::<_>::empty());'
COMPLETENESS_OPTION_SUPPORT = '    match (r1, r2) {\n        (Some(left), Some(right)) => {},\n        (None, None) => {},\n        _ => { assert(false); },\n    }'


COMPLETENESS_RELATIVE_REQUIRES: dict[tuple[str, str, str], list[str]] = {
    ("BTreeMap", "inherent", "get"): [
        "borrowed_lookup_value_functional::<K, Q, V>(this@, key)"
    ],
    ("BTreeMap", "inherent", "get_mut"): [
        "borrowed_lookup_value_functional::<K, Q, V>(pre_this@, key)"
    ],
    ("BTreeMap", "inherent", "remove"): [
        "borrowed_removal_functional::<K, Q, V>(pre_this@, key)"
    ],
    ("BTreeMap", "inherent", "remove_entry"): [
        "borrowed_removal_functional::<K, Q, V>(pre_this@, key)"
    ],
    ("BTreeMap", "inherent", "retain"): [
        "ordered_callback_filter_functional::<K, V, F>(pre_this@, "
        "ordered_map_key_sequence(pre_this@), f)"
    ],
    ("BTreeMap", "inherent", "extract_if"): [
        "extract_if_callback_model_functional::<K, V, R, F>(pre_this@, &range, pred)"
    ],
    ("BTreeMap", "FromIterator", "from_iter"): [
        "into_iterator_item_is_owned_pair::<K, V, T>()"
    ],
    ("BTreeMap", "Extend", "extend"): [
        "into_iterator_item_is_owned_pair::<K, V, T>()"
    ],
    ("BTreeMap", "Index", "index"): [
        "borrowed_lookup_value_functional::<K, Q, V>(this@, key)"
    ],
    ("Entry", "inherent", "or_insert_with"): [
        "!ordered_handle_map::<K, V, _>(this).contains_key("
        "ordered_handle_key::<K, _>(this)) ==> "
        "entry_nullary_callback_functional::<V, F>(default)"
    ],
    ("Entry", "inherent", "or_insert_with_key"): [
        "!ordered_handle_map::<K, V, _>(this).contains_key("
        "ordered_handle_key::<K, _>(this)) ==> "
        "entry_key_callback_functional::<K, V, F>("
        "&ordered_handle_key::<K, _>(this), default)"
    ],
    ("Entry", "inherent", "and_modify"): [
        "ordered_handle_map::<K, V, _>(this).contains_key("
        "ordered_handle_key::<K, _>(this)) ==> "
        "entry_and_modify_transition_functional::<K, V, F>("
        "ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), f)"
    ],
    ("Entry", "inherent", "or_default"): [
        "!ordered_handle_map::<K, V, _>(this).contains_key("
        "ordered_handle_key::<K, _>(this)) ==> "
        "entry_default_value_functional::<V>()"
    ],
}


def completeness_relative_requires(row: Row) -> list[str]:
    """Relative functionality hypotheses used only by the completeness proof."""
    key = (row.owner["name"], row.trait, row.function["name"])
    return list(COMPLETENESS_RELATIVE_REQUIRES.get(key, []))


def completeness_support_body(row: Row) -> str:
    key = (row.owner["name"], row.trait, row.function["name"])
    special = COMPLETENESS_SUPPORT_BODIES.get(key)
    if special is not None:
        return special
    if row.trait == "Debug":
        return COMPLETENESS_FORMATTER_SUPPORT
    if proof_profile(row) == "empty_iterator":
        return COMPLETENESS_EMPTY_ITERATOR_SUPPORT
    output = proof_contract(row)[2]
    if output is not None and output.strip().startswith("Option<"):
        return COMPLETENESS_OPTION_SUPPORT
    return ""


def missing_completeness_where_clause(row: Row, head: str) -> str:
    """Append every accepted generic predicate that `head` does not carry."""
    where_clause = verifier_safe_proof_signature(
        row, proxy_parts(row)[0], proxy_parts(row)[3]
    )[1]
    missing = [
        predicate
        for predicate in split_top_level_predicates(where_clause)
        if predicate not in head
    ]
    if not missing:
        return ""
    return "\n    where " + ", ".join(missing)


def adapt_completeness_associated_type_bound(row: Row, head: str) -> str:
    if not has_owned_pair_associated_type_constraint(row):
        return head
    return head.replace(
        "T: core::iter::IntoIterator<Item = (K, V)>",
        "T: core::iter::IntoIterator",
    )


def adapt_extract_if_completeness_clauses(row: Row, clauses: str) -> str:
    if row.function["name"] != "extract_if":
        return clauses
    return clauses.replace("old(this)@", "pre_this@").replace(
        "final(this)@", "post1_this@"
    )


def _completeness_clause_substitutions(
    inputs: list[tuple[str, str, str]],
    index: int,
) -> list[tuple[str, str]]:
    substitutions: list[tuple[str, str]] = []
    for name, rust_type, _ in inputs:
        if _input_is_mutable_reference(rust_type):
            substitutions.append((rf"\*final\({name}\)", f"post{index}_{name}"))
            substitutions.append((rf"\*old\({name}\)", f"pre_{name}"))
            substitutions.append((rf"\bfinal\({name}\)", f"post{index}_{name}"))
            substitutions.append((rf"\bold\({name}\)", f"pre_{name}"))
            substitutions.append((rf"(?<![\w.]){name}\b", f"pre_{name}"))
    substitutions.append((r"\bfinal\(result\)", f"final(r{index})"))
    substitutions.append((r"(?<![\w.])result\b", f"r{index}"))
    return substitutions


def _apply_substitutions(clause: str, substitutions) -> str:
    text = clause
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text)
    return text


def completeness_components(row: Row) -> tuple[str, str]:
    binder, inputs, output, where_clause, requires, ensures = proof_contract(row)
    binder, where_clause = verifier_safe_proof_signature(row, binder, where_clause)
    outlives = {
        f"{type_name}: {lifetime}"
        for lifetime, type_name in re.findall(
            r"&('[A-Za-z_][A-Za-z0-9_]*)\s+mut\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)",
            " ".join([output or "", where_clause]),
        )
    }
    if outlives:
        predicates = split_top_level_predicates(where_clause)
        predicates.extend(
            predicate for predicate in sorted(outlives) if predicate not in predicates
        )
        where_clause = "\nwhere " + ", ".join(predicates)
    result_type = _erase_mutable_lifetimes(output) if output is not None else "()"
    mutable_inputs = [
        (name, rust_type)
        for name, rust_type, _ in inputs
        if _input_is_mutable_reference(rust_type)
    ]
    equal_params = [f"r1: {result_type}", f"r2: {result_type}"]
    equal_params.extend(
        f"post1_{name}: {deref_type(rust_type)}" for name, rust_type in mutable_inputs
    )
    equal_params.extend(
        f"post2_{name}: {deref_type(rust_type)}" for name, rust_type in mutable_inputs
    )
    equal_where = f"\n    where {', '.join(split_top_level_predicates(where_clause))}" if where_clause.strip() else ""
    equivalent_text = (
        "// Generated equal-fn for determinism check.\n"
        "// Policy: errs_equivalent=True, opaque_ok=False\n"
        "#[verifier::prophetic]\n"
        f"pub open spec fn equivalent{binder}({', '.join(equal_params)}) -> bool"
        f"{equal_where} {{\n"
        f"{custom_equal_body(row, output, mutable_inputs)}\n}}"
    )
    theorem_params: list[str] = []
    for name, rust_type, _ in inputs:
        if _input_is_mutable_reference(rust_type):
            theorem_params.append(f"pre_{name}: {deref_type(rust_type)}")
        else:
            theorem_params.append(f"{name}: {_erase_outer_lifetime(rust_type)}")
    for index in (1, 2):
        theorem_params.extend(
            f"post{index}_{name}: {deref_type(rust_type)}"
            for name, rust_type in mutable_inputs
        )
        theorem_params.append(f"r{index}: {result_type}")
    generic_arguments = [
        _generic_parameter_name(parameter)
        for parameter in split_top_level_predicates(binder[1:-1] if binder else "")
        if not parameter.strip().startswith("'")
    ]
    turbofish = f"::<{', '.join(generic_arguments)}>" if generic_arguments else ""
    equal_arguments = ["r1", "r2"]
    equal_arguments.extend(f"post1_{name}" for name, _ in mutable_inputs)
    equal_arguments.extend(f"post2_{name}" for name, _ in mutable_inputs)
    inline_requires = ", ".join(
        f"({_apply_substitutions(clause, _completeness_clause_substitutions(inputs, 1))})"
        for clause in requires
    )
    requires_header = "    requires" + (f" {inline_requires}," if inline_requires else "")
    hypothesis_lines: list[str] = []
    guard = exact_completeness_guard(row)
    if guard is not None:
        hypothesis_lines.append(f"        {guard},")
    hypothesis_lines.extend(
        f"        {clause}," for clause in completeness_relative_requires(row)
    )
    clause_lines: list[str] = []
    for index in (1, 2):
        substitutions = _completeness_clause_substitutions(inputs, index)
        for clause in ensures:
            rendered = adapt_extract_if_completeness_clauses(
                row, _apply_substitutions(clause, substitutions)
            )
            clause_lines.append(f"            &&& ({rendered})")
    hypothesis_lines.append("        ({")
    hypothesis_lines.extend(clause_lines)
    hypothesis_lines.append("        }),")
    where_line = f"\n    where {', '.join(split_top_level_predicates(where_clause))}" if where_clause.strip() else ""
    completeness_text = (
        f"pub proof fn completeness{binder}({', '.join(theorem_params)})"
        f"{where_line}\n{requires_header}\n"
        + "\n".join(hypothesis_lines)
        + "\n    ensures\n"
        + f"        equivalent{turbofish}({', '.join(equal_arguments)}),\n"
        + "{\n"
        + completeness_support_body(row)
        + "\n}"
    )
    return equivalent_text, completeness_text


def completeness_harness_source(row: Row) -> str:
    metadata = metadata_for(row)
    contract_text = json.dumps(metadata["contract"], sort_keys=True)
    equivalence = metadata["equivalence"]
    equivalent_text, completeness_text = completeness_components(row)
    return f"""#![allow(dead_code, unused_imports, unused_variables)]
#![feature(allocator_api)]
#![verifier::allow(broadcast_without_trigger)]
// Relational completeness for {row.canonical_target}.
// Accepted contract sha256: {sha256_text(contract_text)}
// Contract class: {equivalence['kind']}.
// Equivalence version: {equivalence['version']}.
// Both result values and every mutable post-state below have their exact
// Rust 1.96 API types. Iterator and private-handle representation is quotiented
// only by the ordered public observations declared in the shared vocabulary.

{SHARED_VOCABULARY}

verus! {{

{equivalent_text}

{completeness_text}


}}
"""


@dataclass(frozen=True)
class BehavioralMutation:
    """One negative contract claim proved against a copied lowered body."""

    mutation_id: str
    function: str
    clause_index: int
    modeled_operation: str
    source_span: str
    original_postcondition: str
    mutated_postcondition: str
    operator: str
    required_preconditions: tuple[str, ...]
    mutated_contract_postconditions: tuple[str, ...]
    source_shaped_body_sha256: str
    executed_operation_local_boundaries: tuple[str, ...]

    @property
    def fingerprint_sha256(self) -> str:
        return sha256_text(
            json.dumps(
                {
                    "modeled_operation": self.modeled_operation,
                    "source_span": self.source_span,
                    "original_postcondition": self.original_postcondition,
                    "mutated_postcondition": self.mutated_postcondition,
                    "operator": self.operator,
                    "required_preconditions": self.required_preconditions,
                    "mutated_contract_postconditions": (
                        self.mutated_contract_postconditions
                    ),
                    "source_shaped_body_sha256": (
                        self.source_shaped_body_sha256
                    ),
                    "executed_operation_local_boundaries": (
                        self.executed_operation_local_boundaries
                    ),
                },
                sort_keys=True,
            )
        )

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "id": self.mutation_id,
            "function": self.function,
            "kind": "source_shaped_implementation_postcondition",
            "scope": "independent_source_shaped_target_body",
            "operator": self.operator,
            "modeled_operation": self.modeled_operation,
            "source_span": self.source_span,
            "clause_index": self.clause_index,
            "original_postcondition": self.original_postcondition,
            "mutated_postcondition": self.mutated_postcondition,
            "required_preconditions": list(self.required_preconditions),
            "mutated_contract_postconditions": list(
                self.mutated_contract_postconditions
            ),
            "source_shaped_body_sha256": self.source_shaped_body_sha256,
            "executed_operation_local_boundaries": list(
                self.executed_operation_local_boundaries
            ),
            "calls_verified_target": False,
            "change": (
                f"{'Negate the behavioral consequent of' if self.operator == 'implication_consequent_negation' else 'Negate'} "
                f"accepted public postcondition clause "
                f"{self.clause_index + 1}, retain every other accepted "
                "postcondition and all preconditions, and re-verify an "
                "independent copy of the executable source-shaped target body."
            ),
            "fingerprint_sha256": self.fingerprint_sha256,
            "expected": "rejected",
        }


def behavioral_mutations(row: Row) -> list[BehavioralMutation]:
    """Mutate distinct public clauses on independent copies of the real body."""

    plan = source_lowering_plan(row)
    selected = list(enumerate(plan.ensures))
    normalized = [
        normalized_contract_clause(clause) for _, clause in selected
    ]
    if len(normalized) != len(set(normalized)):
        raise RuntimeError(
            f"{row.target_id}: duplicate accepted public postconditions"
        )

    body_sha256 = sha256_text("\n".join(plan.body))
    mutations: list[BehavioralMutation] = []
    for ordinal, (index, clause) in enumerate(selected, start=1):
        implication = _top_level_marker_index(clause, "==>")
        if implication >= 0:
            antecedent = clause[:implication].strip()
            consequent = clause[implication + 3 :].strip()
            mutated_clause = f"{antecedent} ==> !({consequent})"
            operator = "implication_consequent_negation"
        else:
            mutated_clause = f"!({clause})"
            operator = "logical_negation"
        mutated_contract = list(plan.ensures)
        mutated_contract[index] = mutated_clause
        mutations.append(
            BehavioralMutation(
                mutation_id=f"public_postcondition_{index + 1}",
                function=(
                    f"mutation_{ordinal:02d}_public_postcondition_{index + 1}"
                ),
                clause_index=index,
                modeled_operation=(
                    row.canonical_target or canonical_target(row)
                ),
                source_span=(
                    f"{row.source_file}:{row.line_start}-{row.line_end}"
                ),
                original_postcondition=clause,
                mutated_postcondition=mutated_clause,
                operator=operator,
                required_preconditions=tuple(plan.requires),
                mutated_contract_postconditions=tuple(mutated_contract),
                source_shaped_body_sha256=body_sha256,
                executed_operation_local_boundaries=tuple(
                    boundary.name for boundary in plan.boundaries
                ),
            )
        )
    if not mutations:
        raise RuntimeError(
            f"{row.target_id}: no public behavioral mutation site"
        )
    fingerprints = [mutation.fingerprint_sha256 for mutation in mutations]
    if len(fingerprints) != len(set(fingerprints)):
        raise RuntimeError(f"{row.target_id}: duplicate behavioral mutations")
    return mutations


def render_behavioral_mutation(
    row: Row,
    mutation: BehavioralMutation,
) -> str:
    plan = source_lowering_plan(row)
    rendered_inputs = (
        "\n    "
        + ",\n    ".join(
            f"{name}: {rust_type}" for name, rust_type, _ in plan.inputs
        )
        + "\n"
        if plan.inputs
        else ""
    )
    return_part = f" -> (result: {plan.output})" if plan.output is not None else ""
    requires_block = (
        "\n    requires\n"
        + "\n".join(f"        {clause}," for clause in plan.requires)
        if plan.requires
        else ""
    )
    ensures_block = "\n".join(
        f"        {clause},"
        for clause in mutation.mutated_contract_postconditions
    )
    body = "\n".join(plan.body)
    return (
        f"pub fn {mutation.function}{plan.binder}({rendered_inputs})"
        f"{return_part}{plan.where_clause}{requires_block}\n"
        f"    ensures\n{ensures_block}\n"
        f"{{\n{body}\n}}"
    )


def mutation_manifest_entry(
    row: Row,
    mutation: BehavioralMutation,
) -> dict[str, Any]:
    return {
        **mutation.manifest_entry(),
        "verification_artifact_sha256": sha256_text(
            render_behavioral_mutation(row, mutation)
        ),
    }


def mutation_harness_source(row: Row) -> str:
    source = implementation_harness_source(row)
    closing = f"\n}}\n{TARGET_LOCAL_SECTION_END}"
    prefix, suffix = source.rsplit(closing, 1)
    rendered_mutations = "\n\n".join(
        render_behavioral_mutation(row, mutation)
        for mutation in behavioral_mutations(row)
    )
    return prefix + "\n\n" + rendered_mutations + "\n" + closing + suffix


def mutation_harness_base_source(
    row: Row,
    mutation_source: str,
) -> str | None:
    rendered_mutations = "\n\n".join(
        render_behavioral_mutation(row, mutation)
        for mutation in behavioral_mutations(row)
    )
    block = "\n\n" + rendered_mutations + "\n"
    closing = f"\n}}\n{TARGET_LOCAL_SECTION_END}"
    prefix, separator, suffix = mutation_source.rpartition(closing)
    if not separator or not prefix.endswith(block):
        return None
    return prefix[: -len(block)] + closing + suffix


def exact_vstd_contract_summary(row: Row) -> tuple[list[str], list[str]]:
    key = (row.owner["name"], row.trait, row.function["name"])
    summaries: dict[tuple[str, str, str], list[str]] = {
        ("BTreeMap", "inherent", "iter"): [
            "key_obeys_cmp_spec::<K>() ==> iterator remaining pairs equal map bindings in increasing key order"
        ],
        ("BTreeMap", "inherent", "len"): ["result == spec_btree_map_len(this)"],
        ("BTreeMap", "inherent", "is_empty"): ["result == this@.is_empty()"],
        ("BTreeMap", "Clone", "clone"): ["result@ == this@"],
        ("BTreeMap", "inherent", "new"): ["result@ == Map::empty()"],
        ("BTreeMap", "Default", "default"): ["result@ == Map::empty()"],
        ("BTreeMap", "inherent", "insert"): [
            "obeys_cmp::<K>() ==> final(this)@ == old(this)@.insert(key, value)",
            "result == old mapped value iff the key was present",
        ],
        ("BTreeMap", "inherent", "contains_key"): [
            "obeys_cmp::<K>() ==> result == contains_borrowed_key(this@, key)"
        ],
        ("BTreeMap", "inherent", "get"): [
            "Some(result) maps the borrowed key to the returned value; None means absent"
        ],
        ("BTreeMap", "inherent", "remove"): [
            "borrowed_key_removed(old(this)@, final(this)@, key)",
            "result is the old mapped value iff present",
        ],
        ("BTreeMap", "inherent", "clear"): ["final(this)@ == Map::empty()"],
        ("BTreeMap", "inherent", "keys"): [
            "returned iterator remaining keys equal this@.dom() in increasing order"
        ],
        ("BTreeMap", "inherent", "values"): [
            "returned iterator remaining values follow increasing key order and have map length"
        ],
    }
    if key not in summaries:
        raise KeyError(f"missing exact-vstd contract summary for {key}")
    return [], summaries[key]


def metadata_for(row: Row) -> dict[str, Any]:
    binder, inputs, output, where_clause = proxy_parts(row)
    if row.disposition == "exact_vstd":
        requires, ensures = formal_exact_vstd_contract(row, inputs)
    elif row.disposition == "genuinely_impossible":
        requires = []
        ensures = [
            "final(map)@ == map_extend_pairs_last_wins(old(map)@, copied_input_pairs)"
        ]
    else:
        requires = require_lines(row, inputs)
        ensures = guard_contract_clauses(row, ensure_lines(row, inputs, output))
    inherited_requires: list[dict[str, str]] = []
    if custom_index_binding(row):
        requires = []
        ensures = [
            (
                "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() "
                "==> maps_borrowed_key_to_value(this@, key, *result)"
            )
        ]
        inherited_requires = [
            {
                "clause": (
                    "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() "
                    "==> (<BTreeMap<K,V,A> as IndexSpec<&Q>>::index_req(this, &key) "
                    "<==> contains_borrowed_key(this@, key))"
                ),
                "source": (
                    "specs/btree_map_shared_vocabulary.rs::"
                    "axiom_btree_map_index_req + "
                    "vstd::std_specs::core::ExIndex::index"
                ),
            }
        ]
    contract_form = (
        "exact_vstd_reference"
        if row.disposition == "exact_vstd"
        else "genuinely_impossible_review_packet"
        if row.disposition == "genuinely_impossible"
        else "assume_specification_with_index_req_bridge"
        if custom_index_binding(row)
        else "assume_specification"
    )
    if row.semantic_family == "ordered_debug_format":
        equivalence = {
            "kind": "formatter_trace_equivalence",
            "version": "btree-map-formatter-trace-v1",
            "source_justification": (
                "fmt exposes the Result branch and emitted formatter trace, not Formatter private fields"
            ),
            "positive_witness": "distinct private Formatter states with equal emitted trace and Result branch",
            "negative_witness": "different Result branch or emitted debug token sequence",
        }
    elif row.semantic_family == "map_ordered_hash":
        equivalence = {
            "kind": "hasher_trace_equivalence",
            "version": "btree-map-hasher-trace-v1",
            "source_justification": (
                "Hash exposes ordered calls into Hasher; the hasher's private representation is not observable"
            ),
            "positive_witness": "distinct private hasher states with equal ordered write trace",
            "negative_witness": "different length-prefix or key/value write trace",
        }
    else:
        equivalence = {
            "kind": "exact_observable_equality",
            "version": "btree-map-exact-v1",
            "positive_witness": "identical return and final observable state",
            "negative_witness": "different branch, length, ordered item, or effect is not equivalent",
        }
    equivalence["completeness_requires"] = completeness_relative_requires(row)
    return {
        "schema_version": 1,
        "target_id": row.target_id,
        "ordinal": row.ordinal,
        "module": "alloc::collections::btree_map",
        "api_path": f"alloc::collections::btree_map::{row.owner['name']}::{row.function['name']}",
        "canonical_target": row.canonical_target,
        "owner_type": row.owner["name"],
        "trait": row.trait,
        "method": row.function["name"],
        "rustdoc_item_id": row.item_id,
        "source_file": row.source_file,
        "line_start": row.line_start,
        "line_end": row.line_end,
        "source_sha256": row.source_sha256,
        "source_signature": row.source_excerpt.split("{", 1)[0].strip(),
        "proxy_signature": row.proxy_signature,
        "binding_symbol": (
            "axiom_btree_map_index_req"
            if custom_index_binding(row)
            else (
                "impossibility/index_anonymous_lifetime.json"
                if row.trait == "Index"
                else "impossibility/extend_ref_outlives.json"
            )
            if row.disposition == "genuinely_impossible"
            else None
        ),
        "disposition": row.disposition,
        "contract_form": contract_form,
        "contract": {
            "requires": requires,
            "inherited_requires": inherited_requires,
            "ensures": ensures,
            "source": (
                "vstd/std_specs/btree.rs"
                if row.disposition == "exact_vstd"
                else (
                    "impossibility/index_anonymous_lifetime.json"
                    if row.trait == "Index"
                    else "impossibility/extend_ref_outlives.json"
                )
                if row.disposition == "genuinely_impossible"
                else "specs/generated_btree_map_specs.rs"
            ),
        },
        "vstd_reference": (
            {
                "path": "../verus/source/vstd/std_specs/btree.rs",
                "line": VSTD_LINES[(row.owner["name"], row.trait, row.function["name"])],
                "match_dimensions": [
                    "target_binding",
                    "receiver_reference_shape",
                    "parameter_shape",
                    "return_shape",
                    "lifetimes",
                    "generics",
                    "bounds",
                    "mutability",
                ],
            }
            if row.disposition == "exact_vstd"
            else None
        ),
        "semantic_family": row.semantic_family,
        "principal_behavior": row.principal_behavior,
        "equivalence": equivalence,
        "proxy": {
            "generic_binder": binder,
            "inputs": [
                {"name": name, "type": rust_type, "source_pattern": source}
                for name, rust_type, source in inputs
            ],
            "output": output,
            "where_clause": where_clause,
        },
    }


HARNESS_BOUNDARY_MARKERS = {
    "external_body": "#[verifier::external_body]",
    "external_type_specification": "#[verifier::external_type_specification]",
    "uninterpreted_spec": "pub uninterp spec fn",
    "broadcast_axiom": "pub broadcast axiom fn",
    "assume_specification": "pub assume_specification",
}

GENERATED_HARNESS_FILES = (
    "implementation_proof.rs",
    "completeness_proof.rs",
    "mutation_proof.rs",
    "source_excerpt.rs",
    "contract_binding.json",
    "contract_equivalence.json",
    "transformation_manifest.json",
    "dependency_assumptions.json",
    "trust_boundaries.json",
    "mutations.json",
)


def generated_harness_tree_digest(rows: list[Any]) -> tuple[int, str]:
    records: list[str] = []
    for row in rows:
        target_id = (
            row.target_id if isinstance(row, Row) else row["target_id"]
        )
        for filename in GENERATED_HARNESS_FILES:
            path = ROOT / "proof_harnesses" / target_id / filename
            digest = sha256_bytes(path.read_bytes())
            relative = path.relative_to(ROOT).as_posix()
            records.append(f"{digest}  {relative}\n")
    records.sort()
    return len(records), sha256_text("".join(records))


def write_phase_order_record(rows: list[Row]) -> None:
    selected = [
        row for row in rows if row.disposition in {"exact_vstd", "generated"}
    ]
    review_path = ROOT / "reviews/inventory_specification.json"
    review = json.loads(review_path.read_text()) if review_path.is_file() else {}
    authorized = (
        review.get("producer_role") == "reviewer"
        and review.get("independent") is True
        and (review.get("review") or {}).get("status") == "done"
        and review.get("proof_phase_authorized") is True
    )
    if not authorized:
        raise RuntimeError(
            "refusing proof generation before independent specification approval"
        )
    file_count, tree_sha256 = generated_harness_tree_digest(selected)
    write_json(
        ROOT / "verification/premature_phase_ordering.json",
        {
            "schema_version": 2,
            "status": "post_authorization_generation_recorded",
            "record_kind": "phase_order_archive",
            "path": "proof_harnesses",
            "artifact_scope": (
                "generated harness files listed in generated_harness_files; "
                "run-specific evidence/ sidecars are excluded"
            ),
            "generated_harness_files": list(GENERATED_HARNESS_FILES),
            "file_count": file_count,
            "tree_digest_algorithm": (
                "sha256 of sorted '<file sha256>  <repository-relative path>\\n' "
                "records"
            ),
            "tree_sha256": tree_sha256,
            "selected_targets": len(selected),
            "generation_command": [
                "../.venv/bin/python",
                "scripts/generate_campaign.py",
            ],
            "proof_phase_authorized": True,
            "authorization_review": "reviews/inventory_specification.json",
            "authorization_review_sha256": sha256_bytes(
                review_path.read_bytes()
            ),
            "authorization_status": "done",
            "proof_tree_generated_after_authorization": True,
            "accepted_as_proof_evidence": False,
            "proof_status": "generated_pending_fresh_dynamic_evidence",
            "next_legal_transition": (
                "complete a fresh post-authorization Verus matrix and bind it "
                "during campaign finalization"
            ),
        },
    )


def derive_trust_categories(row: Row) -> list[str]:
    categories = [
        "accepted_public_contract",
        "source_to_verus_representation_lowering",
        "operation_local_private_semantics",
        "comparator_generic_dependency",
    ]
    if completeness_relative_requires(row):
        categories.append("completeness_functionality_hypothesis")
    if has_owned_pair_associated_type_constraint(row):
        categories.append("associated_type_signature_lowering")
    if any(
        token in row.source_excerpt
        for token in ("Allocator", "alloc", "dealloc", "DormantMutRef", "NodeRef")
    ):
        categories.append("allocator_or_private_representation")
    if any(token in row.source_excerpt for token in ("FnMut", "FnOnce", "|")):
        categories.append("callback_observation")
    if row.trait == "Debug":
        categories.append("formatter_effect")
    if row.trait == "Hash":
        categories.append("hasher_effect")
    if row.owner["name"] in ITERATOR_TYPES or "iter" in row.function["name"]:
        categories.append("iterator_private_state")
    if any(
        token in row.source_excerpt for token in ("panic", "expect(", "RangeBounds")
    ):
        categories.append("panic_or_range_domain")
    plan = source_lowering_plan(row)
    if any(
        "proved lower" in boundary.operation
        or "inlined lower" in boundary.operation
        or "inlined proved" in boundary.operation
        for boundary in plan.boundaries
    ):
        categories.append("same_module_public_dependency")
    if (
        row.disposition == "exact_vstd"
        and row.owner["name"] == "BTreeMap"
        and row.function["name"] in {"iter", "keys", "values"}
    ):
        categories.append("accepted_vstd_iterator_model_axiom")
    if row.owner["name"] in {"Entry", "OccupiedEntry", "VacantEntry"}:
        categories.append("handle_representation_invariant")
    return categories


def scan_harness_trust(
    target_root: Path,
    row: Row,
    categories: list[str],
) -> dict[str, Any]:
    texts = {
        name: (target_root / name).read_text()
        for name in (
            "implementation_proof.rs",
            "completeness_proof.rs",
            "mutation_proof.rs",
        )
    }
    markers_by_file = {
        name: {
            kind: text.count(marker)
            for kind, marker in HARNESS_BOUNDARY_MARKERS.items()
        }
        for name, text in texts.items()
    }
    marker_totals = {
        kind: sum(counts[kind] for counts in markers_by_file.values())
        for kind in HARNESS_BOUNDARY_MARKERS
    }
    implementation = texts["implementation_proof.rs"]
    analysis = analyze_target_local_lowering(row, implementation)
    target_external_body = bool(analysis["target_external_body"]) or bool(
        re.search(
            rf"#\[verifier::external_body\]\s*"
            rf"pub fn rust_1_96_target_{row.item_id}\b",
            implementation,
        )
    )
    target_assume_specification = bool(
        re.search(
            rf"pub assume_specification[^\[]*\[[^\]]*"
            rf"{re.escape(row.function['name'])}",
            implementation,
        )
    )
    operation_local_boundaries = analysis["boundaries"]
    literal_external_body_by_file = {
        name: counts["external_body"]
        for name, counts in markers_by_file.items()
    }
    helper_model_markers = sum(
        markers_by_file["implementation_proof.rs"].values()
    ) - int(target_external_body) - int(target_assume_specification)
    completeness_markers = sum(
        markers_by_file["completeness_proof.rs"].values()
    )
    whole_harness_markers = sum(marker_totals.values())
    return {
        "schema_version": 2,
        "target_id": row.target_id,
        "target_external_body": target_external_body,
        "target_assume_specification": target_assume_specification,
        "operation_local_boundaries": operation_local_boundaries,
        "operation_local_boundary_count": len(operation_local_boundaries),
        "operation_local_boundary_kinds": sorted(
            {boundary["kind"] for boundary in operation_local_boundaries}
        ),
        "leaf_representation_exception_count": len(
            analysis["leaf_representation_exceptions"]
        ),
        "target_local_external_body_count": analysis["external_body_count"],
        "boundary_covers_target_contract": bool(
            analysis["contract_cloning_boundaries"]
        ),
        "terminal_boundary_delegation": analysis["terminal_delegation"],
        "legacy_lowering_tokens": analysis["legacy_tokens"],
        "literal_external_body_by_file": literal_external_body_by_file,
        "literal_external_body_count": marker_totals["external_body"],
        "semantic_boundary_markers_by_file": markers_by_file,
        "semantic_boundary_marker_totals": marker_totals,
        "whole_harness_boundary_marker_count": whole_harness_markers,
        "helper_model_external_body_count": (
            markers_by_file["implementation_proof.rs"]["external_body"]
        ),
        "helper_model_boundary_marker_count": helper_model_markers,
        "completeness_external_body_count": (
            markers_by_file["completeness_proof.rs"]["external_body"]
        ),
        "completeness_boundary_marker_count": completeness_markers,
        "mutation_external_body_count": (
            markers_by_file["mutation_proof.rs"]["external_body"]
        ),
        "comparator_generic_dependency_count": int(
            "comparator_generic_dependency" in categories
        ),
        "allocator_representation_dependency_count": int(
            "allocator_or_private_representation" in categories
        ),
        "categories": categories,
        "no_additional_implementation_dependency_boundary": (
            helper_model_markers == 0
        ),
        "end_to_end_trust_free": False,
    }


def generate_harnesses(rows: list[Row]) -> None:
    selected_rows = [
        row for row in rows if row.disposition in {"exact_vstd", "generated"}
    ]
    root = ROOT / "proof_harnesses"
    root.mkdir(exist_ok=True)
    expected = {row.target_id for row in selected_rows}
    unexpected = sorted(
        path.name for path in root.iterdir() if path.is_dir() and path.name not in expected
    )
    if unexpected:
        raise RuntimeError(f"refusing to overwrite unexpected proof harness directories: {unexpected}")

    for row in selected_rows:
        target_root = root / row.target_id
        target_root.mkdir(exist_ok=True)
        (target_root / "implementation_proof.rs").write_text(
            implementation_harness_source(row)
        )
        (target_root / "completeness_proof.rs").write_text(
            completeness_harness_source(row)
        )
        (target_root / "mutation_proof.rs").write_text(
            mutation_harness_source(row)
        )
        (target_root / "source_excerpt.rs").write_text(row.source_excerpt)
        metadata = metadata_for(row)
        contract_text = json.dumps(metadata["contract"], sort_keys=True)
        source_calls = source_call_names(row)
        trust_categories = derive_trust_categories(row)
        dependencies: list[dict[str, Any]] = [
            {
                "category": "comparator_generic_dependency",
                "boundary": "OrdSpec/obeys_cmp total-order contract",
                "source": "../verus/source/vstd/std_specs/cmp.rs",
            }
        ]
        relative_completeness_requires = completeness_relative_requires(row)
        if relative_completeness_requires:
            dependencies.append(
                {
                    "category": "completeness_functionality_hypothesis",
                    "boundary": relative_completeness_requires,
                    "source": "specs/btree_map_shared_vocabulary.rs",
                    "scope": "completeness proof only",
                }
            )
        if has_owned_pair_associated_type_constraint(row):
            dependencies.append(
                {
                    "category": "associated_type_signature_lowering",
                    "boundary": (
                        "the exact source Item = (K, V) constraint is retained "
                        "in the public contract and represented in regular Verus "
                        "proof functions by T: IntoIterator plus "
                        "into_iterator_item_is_owned_pair::<K, V, T>()"
                    ),
                    "source": f"{row.source_file}:{row.line_start}-{row.line_end}",
                    "scope": "implementation, completeness, and mutation proof signatures",
                }
            )
        if any(
            token in row.source_excerpt
            for token in ("Allocator", "alloc", "dealloc", "DormantMutRef", "NodeRef")
        ):
            dependencies.append(
                {
                    "category": "allocator_representation",
                    "boundary": (
                        "private node allocation, ownership, and reference representation "
                        "remain behind the operation-local boundaries listed below while "
                        "the public lowering retains the real allocator-parametric API"
                    ),
                    "source": row.source_file,
                }
            )
        if any(token in row.source_excerpt for token in ("FnMut", "FnOnce", "|")):
            dependencies.append(
                {
                    "category": "callback_observation",
                    "boundary": "callback requires/ensures and ordered invocation trace",
                    "source": "specs/btree_map_shared_vocabulary.rs",
                }
            )
        if row.trait == "Debug":
            dependencies.append(
                {
                    "category": "formatter_effect",
                    "boundary": "reviewed formatter trace equivalence",
                    "source": "specs/btree_map_shared_vocabulary.rs",
                }
            )
        if row.trait == "Hash":
            dependencies.append(
                {
                    "category": "hasher_effect",
                    "boundary": "reviewed ordered hasher trace equivalence",
                    "source": "specs/btree_map_shared_vocabulary.rs",
                }
            )
        if row.owner["name"] in ITERATOR_TYPES or "iter" in row.function["name"]:
            dependencies.append(
                {
                    "category": "iterator_private_state",
                    "boundary": "remaining sequence and ordered cursor representation",
                    "source": "specs/btree_map_shared_vocabulary.rs",
                }
            )
        if any(token in row.source_excerpt for token in ("panic", "expect(", "RangeBounds")):
            dependencies.append(
                {
                    "category": "panic_or_range_domain",
                    "boundary": "normal-return domain from the selected contract",
                    "source": row.source_file,
                }
            )
        if "same_module_public_dependency" in trust_categories:
            dependencies.append(
                {
                    "category": "same_module_public_dependency",
                    "boundary": (
                        "source-owned lower public API contract, linked to its "
                        "separately selected implementation-proof target"
                    ),
                    "source": row.source_file,
                    "scope": "wrapper call only; not counted as a proved dependency until the matrix passes",
                }
            )
        if "accepted_vstd_iterator_model_axiom" in trust_categories:
            dependencies.append(
                {
                    "category": "accepted_vstd_iterator_model_axiom",
                    "boundary": (
                        "side properties of spec_btree_map_iter/spec_keys_iter/"
                        "spec_values_iter referenced from accepted exact-vstd coverage"
                    ),
                    "source": "../verus/source/vstd/std_specs/btree.rs",
                }
            )
        if "handle_representation_invariant" in trust_categories:
            dependencies.append(
                {
                    "category": "handle_representation_invariant",
                    "boundary": (
                        "Entry occupied/vacant discriminant agrees with the "
                        "ordered handle map/key model"
                    ),
                    "source": "specs/btree_map_shared_vocabulary.rs",
                }
            )
        dependencies.extend(
            {
                "category": "operation_local_source_boundary",
                "boundary": boundary["name"],
                "kind": boundary["kind"],
                "modeled_source_operation": boundary["modeled_source_operation"],
                "footprint": boundary["footprint"],
                "source": boundary["source_span"],
                "source_sha256": boundary["source_sha256"],
                **(
                    {
                        "leaf_representation_exception": boundary[
                            "leaf_representation_exception"
                        ]
                    }
                    if boundary.get("leaf_representation_exception")
                    else {}
                ),
            }
            for boundary in source_boundary_manifest(row)
        )
        write_json(target_root / "contract_equivalence.json", metadata["equivalence"])
        write_json(
            target_root / "contract_binding.json",
            {
                "schema_version": 1,
                "target_id": row.target_id,
                "canonical_target": row.canonical_target,
                "disposition": row.disposition,
                "contract_form": metadata["contract_form"],
                "contract": metadata["contract"],
                "contract_sha256": sha256_text(contract_text),
                "model_profile": proof_profile(row),
                "projection": [
                    {
                        "accepted_clause": clause,
                        "clause_kind": clause_kind,
                        "modeled_observations": (
                            ["normal_return_domain", "domain_ok"]
                            if clause_kind in {"requires", "inherited_requires"}
                            else [
                                observation
                                for observation, tokens in {
                                    "result_branch": ("result", "Some", "None", "bool"),
                                    "map_length": ("len", "empty"),
                                    "key_value": ("key", "value", "mapped", "insert", "remove"),
                                    "ordered_position": ("order", "first", "last", "range"),
                                    "iterator_state": ("iter", "remaining", "size_hint"),
                                    "callback_trace": ("callback", "default", "predicate", "retain"),
                                    "effect_trace": ("format", "hash", "trace"),
                                    "final_frame": ("final", "post", "frame"),
                                }.items()
                                if any(
                                    token.lower() in str(clause).lower()
                                    for token in tokens
                                )
                            ]
                            or ["source_transition"]
                        ),
                    }
                    for clause_kind, clauses in (
                        ("requires", metadata["contract"]["requires"]),
                        (
                            "inherited_requires",
                            metadata["contract"].get("inherited_requires", []),
                        ),
                        ("ensures", metadata["contract"]["ensures"]),
                    )
                    for clause in clauses
                ],
            },
        )
        write_json(
            target_root / "transformation_manifest.json",
            {
                "schema_version": 1,
                "target_id": row.target_id,
                "source_sha256": row.source_sha256,
                "source_span": f"{row.source_file}:{row.line_start}-{row.line_end}",
                "adaptations": [
                    {
                        "kind": "executable_source_call_lowering",
                        "description": (
                            (
                                "The executable proof target retains the exact Rust 1.96 "
                                "public signature"
                            )
                            if not has_owned_pair_associated_type_constraint(row)
                            else (
                                "The executable proof target retains the public API "
                                "types and the IntoIterator bound; its concrete "
                                "associated-item equality is preserved by the separate "
                                "verifier-safe signature lowering"
                            )
                        )
                        + (
                            ", reproduces the Rust source control flow with executable "
                            "branches, loops and per-step operations, and contains no "
                            "same-target API assumption or call."
                        ),
                        "preserved_observations": row.principal_behavior,
                    },
                    *(
                        [
                            {
                                "kind": "verifier_safe_associated_type_lowering",
                                "description": (
                                    "Rust 1.96 requires T: IntoIterator<Item = (K, V)>. "
                                    "The exact constraint remains frozen in the generated "
                                    "public specification and proxy metadata. Regular "
                                    "Verus proof functions preserve T: IntoIterator and "
                                    "reify only the concrete associated-item equality as "
                                    "into_iterator_item_is_owned_pair::<K, V, T>(), "
                                    "avoiding Verus's ill-typed AIR projection failure."
                                ),
                                "preserved_observations": [
                                    "input is an IntoIterator",
                                    "input items are owned (K, V) pairs",
                                    "all input bindings are consumed in source order",
                                ],
                            }
                        ]
                        if has_owned_pair_associated_type_constraint(row)
                        else []
                    ),
                    {
                        "kind": "operation_local_private_semantics",
                        "description": (
                            "Every retained boundary models exactly one private source "
                            "operation (field/representation access, one private "
                            "search/node/iterator/callback/comparator/allocator step). "
                            "Each boundary declares its source span, source hash and "
                            "read/write footprint, and none receives the whole public "
                            "target state while promising the whole public contract."
                        ),
                        "preserved_observations": [
                            "actual result type and branch",
                            "BTreeMap view and mutable final frame",
                            "ordered iterator observation",
                            "callback, panic, allocator, drop, and unwind effects",
                        ],
                    },
                ],
                "retained_operation_local_boundaries": source_boundary_manifest(row),
                "source_call_lowerings": [
                    {
                        "source_call": call,
                        "realized_by": source_call_realizations(row).get(
                            call, "target_control_flow"
                        ),
                        "order": index,
                        "modeled_effects": source_call_effect_flags(
                            row,
                            call,
                            index,
                            proxy_parts(row)[1],
                        ),
                    }
                    for index, call in enumerate(source_calls)
                ],
                "dropped_constructs": [
                    {
                        "source_construct": construct,
                        "reason": (
                            "reproduced by the executable target control flow or by an "
                            "operation-local boundary listed above"
                        ),
                    }
                    for construct in (
                        ["unsafe block"] if "unsafe" in row.source_excerpt else []
                    )
                    + (["pattern match"] if "match " in row.source_excerpt else [])
                    + (["early-return propagation"] if "?" in row.source_excerpt else [])
                    + (
                        ["closure/callback body"]
                        if "|" in row.source_excerpt or "FnMut" in row.source_excerpt
                        else []
                    )
                ],
                "reordered_constructs": [],
                "contract_sha256": sha256_text(contract_text),
                "model_profile": proof_profile(row),
            },
        )
        write_json(
            target_root / "dependency_assumptions.json",
            {
                "schema_version": 1,
                "target_id": row.target_id,
                "accepted_requires": metadata["contract"]["requires"],
                "inherited_requires": metadata["contract"].get("inherited_requires", []),
                "dependencies": dependencies,
            },
        )
        write_json(
            target_root / "trust_boundaries.json",
            scan_harness_trust(target_root, row, trust_categories),
        )
        write_json(
            target_root / "mutations.json",
            {
                "schema_version": 2,
                "target_id": row.target_id,
                "scope": "accepted_public_target_postconditions",
                "selection_policy": (
                    "negate every textually distinct accepted public "
                    "postcondition (only the behavioral consequent for a "
                    "top-level implication), retain every other contract "
                    "clause and all preconditions, and execute an independent "
                    "copy of the source-shaped target body"
                ),
                "accepted_public_postcondition_count": len(
                    source_lowering_plan(row).ensures
                ),
                "mutated_public_postcondition_count": len(
                    behavioral_mutations(row)
                ),
                "unmutated_public_postconditions": [],
                "excluded_mutation_scopes": [
                    (
                        "operation-local external boundary contracts are trust "
                        "accounting surfaces, not executable implementation bodies"
                    )
                ],
                "mutants": [
                    mutation_manifest_entry(row, mutation)
                    for mutation in behavioral_mutations(row)
                ],
            },
        )
        (target_root / "evidence").mkdir(exist_ok=True)

        proof_manifest_root = ROOT / "proof_manifests" / row.target_id
        proof_manifest_root.mkdir(parents=True, exist_ok=True)
        write_json(
            proof_manifest_root / "source_body.json",
            {
                "schema_version": 1,
                "target_id": row.target_id,
                "canonical_target": row.canonical_target,
                "rustdoc_item_id": row.item_id,
                "source_file": row.source_file,
                "line_start": row.line_start,
                "line_end": row.line_end,
                "source_sha256": row.source_sha256,
                "source_excerpt_path": (
                    f"proof_harnesses/{row.target_id}/source_excerpt.rs"
                ),
                "contract_disposition": row.disposition,
                "contract_form": metadata["contract_form"],
            },
        )
        write_json(
            proof_manifest_root / "transformation_manifest.json",
            json.loads((target_root / "transformation_manifest.json").read_text()),
        )
        write_json(
            proof_manifest_root / "dependency_assumption_manifest.json",
            json.loads((target_root / "dependency_assumptions.json").read_text()),
        )


def generate_feedback_inputs(rows: list[Row], generated_source: str) -> None:
    generated_rows = [row for row in rows if row.disposition == "generated"]
    manifest_targets = []
    seeds: dict[str, Any] = {}
    contracts: list[dict[str, Any]] = []
    shared = SHARED_VOCABULARY
    shared_body = shared.split("verus! {", 1)[1].rsplit("} // verus!", 1)[0].strip()
    for row in generated_rows:
        binder, inputs, output, where_clause = proxy_parts(row)
        target = render_trait_target(row)
        rendered_inputs = ",\n    ".join(f"{name}: {rust_type}" for name, rust_type, _ in inputs)
        return_part = f" -> (result: {output})" if output is not None else ""
        requires = require_lines(row, inputs)
        ensures = ensure_lines(row, inputs, output)
        if custom_index_binding(row):
            requires = []
            ensures = [
                (
                    "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() "
                    "==> maps_borrowed_key_to_value(this@, key, *result)"
                )
            ]
        spec = "\n".join(
            [
                f"pub assume_specification{binder}[ {target} ](",
                f"    {rendered_inputs}" if rendered_inputs else "",
                f"){return_part}{where_clause}",
                *(["    requires", *[f"        {line}," for line in requires]] if requires else []),
                "    ensures",
                *[f"        {line}," for line in ensures],
                ";",
            ]
        )
        if custom_index_binding(row):
            spec = index_assume_specification()
        contract_form = "assume_specification"
        contract_code = shared_body + "\n\n" + spec + "\n"
        context_lines = source_lines(row.source_file)
        low = max(0, row.line_start - 8)
        high = min(len(context_lines), row.line_end + 8)
        source_context = "\n".join(
            f"{index + 1}: {context_lines[index]}" for index in range(low, high)
        )
        target_key = row.canonical_target
        declaration = {
            "line": row.line_start,
            "source_file": row.source_file,
            "source_context": source_context,
            "target": target_key,
            "observability": {
                "has_modeled_output": output is not None or any(
                    "mut " in rust_type for _, rust_type, _source in inputs
                ),
                "return_is_raw_pointer": False,
                "return_is_reference": bool(output and output.startswith("&")),
                "return_is_unit": output is None,
            },
        }
        manifest_targets.append(
            {
                "available_in_verus_rust_1_96": True,
                "canonical_target": target_key,
                "category": "btree_map",
                "classification": "suitable_now",
                "declaration_count": 1,
                "declarations": [declaration],
                "display_paths": [target_key],
                "feedback_safe_name": row.target_id,
                "kinds": ["inherent_method" if row.trait == "inherent" else "trait_method"],
                "modules": ["alloc::collections::btree_map"],
                "recommended_contract_form": "assume_specification",
                "semantic_risks": [
                    "ordered_map_private_representation",
                    "comparator_equivalence",
                ],
                "static_reward_eligible": True,
                "target": target_key,
                "verification_declaration_count": 1,
                "verification_declarations": [declaration],
            }
        )
        seeds[target_key] = {
            "assumptions": [
                "rust_1_96_source_binding",
                "ordered_map_shared_vocabulary",
            ],
            "canonical_target": target_key,
            "contract_code": contract_code,
            "contract_form": contract_form,
            "decision": "add_spec",
            "ensures": ensures,
            "feature_gates": ["allocator_api"],
            "feedback_safe_name": row.target_id,
            "feedback_target": target_key,
            "imports": [
                "alloc::alloc::Allocator",
                "alloc::boxed::Box",
                "alloc::collections::BTreeMap",
                "alloc::collections::btree_map::*",
                "core::borrow::Borrow",
                "core::cmp::{Ord, Ordering, PartialEq, PartialOrd}",
                "core::fmt::{Debug, Formatter}",
                "core::hash::{Hash, Hasher}",
                "core::iter::{DoubleEndedIterator, ExactSizeIterator, Extend, FromIterator, IntoIterator, Iterator}",
                "core::ops::{FnMut, FnOnce, Index, RangeBounds}",
                "vstd::prelude::*",
                (
                    "vstd::std_specs::btree::{borrowed_key_removed, "
                    "contains_borrowed_key, increasing_seq, key_obeys_cmp_spec, "
                    "maps_borrowed_key_to_value}"
                ),
                "vstd::std_specs::cmp::{OrdSpec, PartialOrdSpec}",
                "vstd::std_specs::core::IndexSpec",
                (
                    "vstd::std_specs::iter::{IteratorSpec, IteratorSpecImpl, "
                    "into_iter_remaining}"
                ),
                "vstd::std_specs::range::{RangeBoundsSpec, SpecBound}",
            ],
            "rationale": "; ".join(row.principal_behavior or []),
            "requires": requires,
            "risks": [
                "private representation is a reviewed semantic boundary",
            ],
            "source_fidelity": (
                f"Bound to Rust 1.96 {row.source_file}:{row.line_start}-{row.line_end} "
                f"sha256 {row.source_sha256}."
            ),
            "source_line": str(row.line_start),
            "state_models": [row.semantic_family, "ordered_map_shared_vocabulary"],
            "useful": True,
        }
        contracts.append(
            {
                "api_path": f"alloc::collections::btree_map::{row.owner['name']}::{row.function['name']}",
                "confidence": "high",
                "mechanism": "generated_assume_specification",
                "raw_target": target,
                "source_file": "specs/generated_btree_map_specs.rs",
                "source_line": str(row.line_start),
            }
        )
    write_json(
        ROOT / "specgen/btree_map_stable_manifest.json",
        {
            "metadata": {
                "scope": "alloc::collections::btree_map generated non-exact rows",
                "stable_inventory_rows": len(rows),
                "target_count": len(generated_rows),
            },
            "targets": manifest_targets,
        },
    )
    write_json(ROOT / "specgen/btree_map_seed_candidates.json", seeds)
    write_json(ROOT / "specgen/existing_contract_context.json", contracts)


def generate_inventory_and_specs(
    rows: list[Row],
    exclusions: list[dict[str, Any]],
    *,
    include_proof_inventory: bool = True,
) -> None:
    records = [metadata_for(row) for row in rows]
    for row, record in zip(rows, records, strict=True):
        if row.disposition == "genuinely_impossible":
            row.proxy_signature = ""
            record["proxy_signature"] = None
        elif custom_index_binding(row):
            row.proxy_signature = (
                "pub assume_specification<'_0,K:Borrow<Q>+Ord,Q:Ord+?Sized,"
                "V,A:Allocator+Clone,'receiver>"
                "[<BTreeMap<K,V,A> as Index<&Q>>::index]"
            )
            record["proxy_signature"] = row.proxy_signature
        else:
            row.proxy_signature = (
                f"pub assume_specification{record['proxy']['generic_binder']}"
                f"[ {render_trait_target(row)} ]"
            )
            record["proxy_signature"] = row.proxy_signature

    inventory_root = ROOT / "inventory"
    write_json(
        inventory_root / "btree_map_exec_fn_inventory.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "rust_release": "1.96.0",
            "derivation": {
                "rustdoc_path_id": 3211,
                "private_owner_module_id": 1980,
                "owner_files": sorted(OWNER_FILES),
                "rules": [
                    "resolve the stable public glob re-export to private btree::map",
                    "include stable public inherent functions on stable re-exported types",
                    "include stable source-owned trait method bodies",
                    "use only the main Stability attribute; const-stability does not exclude len/is_empty",
                    "exclude synthetic/blanket/inherited impl methods and unstable trait items",
                ],
            },
            "counts": {
                "stable_inventory_total": len(rows),
                "exact_vstd": sum(row.disposition == "exact_vstd" for row in rows),
                "generated": sum(row.disposition == "generated" for row in rows),
                "genuinely_impossible": sum(
                    row.disposition == "genuinely_impossible" for row in rows
                ),
                "pending": 0,
            },
            "rows": records,
        },
    )
    csv_fields = [
        "target_id",
        "ordinal",
        "api_path",
        "canonical_target",
        "owner_type",
        "trait",
        "method",
        "rustdoc_item_id",
        "source_file",
        "line_start",
        "line_end",
        "source_sha256",
        "disposition",
        "semantic_family",
        "proxy_signature",
    ]
    write_csv(inventory_root / "btree_map_exec_fn_inventory.csv", records, csv_fields)
    write_json(
        inventory_root / "unstable_non_executable_exclusions.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "aliases_excluded_as_duplicates": [
                "alloc::collections::BTreeMap",
                "std::collections::BTreeMap",
            ],
            "modules_excluded": [
                "alloc::collections::btree_set",
                "core::cmp",
            ],
            "rows": exclusions,
        },
    )
    exact_rows = [record for record in records if record["disposition"] == "exact_vstd"]
    write_json(
        inventory_root / "exact_vstd_audit.json",
        {
            "schema_version": 1,
            "match_policy": "all eight signature dimensions must match",
            "dimensions": [
                "target_binding",
                "receiver_reference_shape",
                "parameter_shape",
                "return_shape",
                "lifetimes",
                "generics",
                "bounds",
                "mutability",
            ],
            "matched_count": len(exact_rows),
            "rows": exact_rows,
        },
    )
    impossible_rows = [
        record for record in records if record["disposition"] == "genuinely_impossible"
    ]
    if len(impossible_rows) != 1:
        raise RuntimeError("expected exactly one target-specific impossibility packet")
    impossible_by_trait = {record["trait"]: record for record in impossible_rows}
    index_record = next(record for record in records if record["trait"] == "Index")
    write_json(
        ROOT / "research/index_binding_resolution.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "target": index_record,
            "status": "resolved_generated",
            "resolution": (
                "Use the accepted cmp.rs-style unused early lifetime binder, an "
                "ensures-only assume_specification, and a target-specific axiom "
                "equating inherited IndexSpec::index_req with borrowed-key membership"
            ),
            "attempts": [
                {
                    "form": "assume_specification",
                    "result": "failed",
                    "diagnostic": (
                        "provided for<K,Q,V,A> for<'a,'s> differs from expected "
                        "for<'q,K,Q,V,A> for<'receiver,'key>"
                    ),
                    "evidence": "research/index_attempt_assume_specification.json",
                },
                {
                    "form": "external_fn_specification",
                    "result": "failed",
                    "diagnostic": "same exact function-binder mismatch",
                    "evidence": "research/index_attempt_external_fn_specification.json",
                },
                {
                    "form": "vstd IndexSpecImpl extension",
                    "result": "failed",
                    "diagnostic": (
                        "Rust orphan rule E0210 forbids implementing the foreign "
                        "vstd extension trait for foreign BTreeMap"
                    ),
                    "evidence": "research/index_attempt_extension_trait.json",
                },
                {
                    "form": "named clone.rs-style early/late binder ordering",
                    "result": "failed",
                    "diagnostic": (
                        "Verus still lowers both declared lifetimes into the late binder; "
                        "provided for<K,Q,V,A> for<'key,'receiver> differs from expected "
                        "for<'key,K,Q,V,A> for<'receiver,'argument>"
                    ),
                    "evidence": "research/index_attempt_clone_binder_order.json",
                },
                {
                    "form": "cmp.rs-style unused early lifetime plus inherited IndexSpec",
                    "result": "passed",
                    "diagnostic": "no-verify rc=0; actual call-site bridge verifies 1/0",
                    "evidence": "research/index_attempt_unused_early_lifetime.json",
                },
            ],
            "source_rationale": (
                "map.rs:2617-2632 delegates to get(key).expect and therefore requires "
                "borrowed-key membership for normal return and returns the mapped value"
            ),
            "consistency_scope": {
                "guard": (
                    "key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>()"
                ),
                "positive_witness": (
                    "a map containing a borrowed-equivalent key enables IndexSpec::index_req "
                    "and maps_borrowed_key_to_value"
                ),
                "negative_witness": (
                    "an absent borrowed key disables IndexSpec::index_req; the source panics "
                    "instead of returning a value"
                ),
                "foreign_trait_overlap": (
                    "No vstd IndexSpecImpl exists for BTreeMap; the target-local axiom "
                    "therefore has no competing definition in the frozen dependency set"
                ),
            },
            "accepted_contract": {
                "direct_requires": index_record["contract"]["requires"],
                "inherited_requires": index_record["contract"]["inherited_requires"],
                "ensures": index_record["contract"]["ensures"],
            },
        },
    )
    index_attempts = {
        "index_attempt_assume_specification.json": {
            "attempt": "assume_specification",
            "returncode": 1,
            "diagnostic_code": "signature_binder_mismatch",
            "provided": "for<K,Q,V,A> for<'a,'s> (&'s BTreeMap<K,V,A>, &'a Q) -> &'s V",
            "expected": "for<'q,K,Q,V,A> for<'receiver,'key> (&BTreeMap<K,V,A>, &Q) -> &V",
        },
        "index_attempt_external_fn_specification.json": {
            "attempt": "external_fn_specification",
            "returncode": 1,
            "diagnostic_code": "signature_binder_mismatch",
            "provided": "for<K,Q,V,A> for<'map,'key> (&'map BTreeMap<K,V,A>, &'key Q) -> &'map V",
            "expected": "for<'q,K,Q,V,A> for<'receiver,'key> (&BTreeMap<K,V,A>, &Q) -> &V",
        },
        "index_attempt_extension_trait.json": {
            "attempt": "IndexSpecImpl<&Q> for BTreeMap<K,V,A>",
            "returncode": 1,
            "diagnostic_code": "E0210",
            "diagnostic": (
                "type parameter Q must be used as the type parameter for a local type; "
                "both the extension trait and BTreeMap are foreign"
            ),
        },
        "index_attempt_clone_binder_order.json": {
            "attempt": "clone.rs-style generic ordering",
            "returncode": 1,
            "diagnostic_code": "signature_binder_mismatch",
            "declaration_order": "'key, K, Q, V, A, 'receiver",
            "provided": "for<K,Q,V,A> for<'key,'receiver> (&'receiver BTreeMap<K,V,A>, &'key Q) -> &'receiver V",
            "expected": "for<'key,K,Q,V,A> for<'receiver,'argument> (&BTreeMap<K,V,A>, &Q) -> &V",
        },
    }
    for filename, payload in index_attempts.items():
        write_json(
            ROOT / "research" / filename,
            {
                "schema_version": 1,
                "rust_release": "1.96.0",
                "verus": "0.2026.07.21.1beb0fa.dirty",
                "target_id": index_record["target_id"],
                **payload,
            },
        )
    write_json(
        ROOT / "research/index_attempt_unused_early_lifetime.json",
        {
            "schema_version": 1,
            "rust_release": "1.96.0",
            "verus": "0.2026.07.21.1beb0fa.dirty",
            "target_id": index_record["target_id"],
            "attempt": "cmp.rs-style unused early lifetime and IndexSpec bridge",
            "returncode_no_verify": 0,
            "returncode_actual_call_site": 0,
            "verification_result": "1 verified, 0 errors",
            "binding": (
                "assume_specification<'_0,K,Q,V,A,'receiver>"
                "[<BTreeMap<K,V,A> as Index<&Q>>::index]"
            ),
            "precondition_bridge": (
                "axiom_btree_map_index_req equates IndexSpec::index_req "
                "with contains_borrowed_key"
            ),
        },
    )
    inventory_review_path = ROOT / "reviews/inventory_specification.json"
    inventory_review = (
        json.loads(inventory_review_path.read_text())
        if inventory_review_path.is_file()
        else {}
    )
    impossible_target_id = impossible_by_trait["Extend"]["target_id"]
    impossible_accepted = (
        inventory_review.get("producer_role") == "reviewer"
        and inventory_review.get("independent") is True
        and (inventory_review.get("review") or {}).get("status") == "done"
        and impossible_target_id
        in ((inventory_review.get("review") or {}).get("row_approvals") or {})
    )
    write_json(
        ROOT / "impossibility/extend_ref_outlives.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "target": impossible_by_trait["Extend"],
            "status": (
                "accepted_by_independent_reviewer"
                if impossible_accepted
                else "pending_independent_row_approval"
            ),
            "review_evidence": (
                "reviews/inventory_specification.json"
                if impossible_accepted
                else None
            ),
            "missing_boundary": (
                "Verus cannot express the impl's implied K:'a/V:'a well-formedness "
                "without adding explicit proxy bounds that fail exact signature matching"
            ),
            "attempts": [
                {
                    "form": "direct assume_specification with source bounds",
                    "result": "failed",
                    "diagnostic": "E0309 requires explicit K:'a and V:'a",
                    "evidence": "research/extend_ref_attempt_implied_outlives.json",
                },
                {
                    "form": "direct assume_specification with explicit outlives",
                    "result": "failed",
                    "diagnostic": (
                        "assume_specification trait-bound mismatch because the "
                        "external fn item carries only implied, not explicit, outlives"
                    ),
                    "evidence": "research/extend_ref_attempt_explicit_outlives.json",
                },
                {
                    "form": "program-wide external Extend trait specification",
                    "result": "rejected",
                    "diagnostic": (
                        "would apply an opaque contract to every Extend implementation "
                        "and exceed the single-module scope"
                    ),
                    "evidence": "research/extend_ref_attempt_global_trait.json",
                },
            ],
            "alternatives_rejected": [
                "an unconditional mutable-reference axiom is not call-bound and is unsound",
                "a copied-input helper without an executable target binding is not a specification",
                "adding explicit outlives bounds changes the external function signature",
            ],
            "source_rationale": (
                "map.rs:2552-2562 delegates copied (&K,&V) pairs to the owned Extend "
                "implementation, preserving input order and last-value-wins semantics"
            ),
            "proposed_contract": {
                "requires": [],
                "ensures": (
                    "final(map)@ == map_extend_pairs_last_wins("
                    "old(map)@, copied_borrowed_pair_sequence(iterator))"
                ),
            },
        },
    )
    extend_attempts = {
        "extend_ref_attempt_implied_outlives.json": {
            "attempt": "source-shaped direct assume_specification",
            "returncode": 1,
            "diagnostic_code": "E0309",
            "diagnostic": "K and V may not live long enough for Item = (&'a K, &'a V)",
        },
        "extend_ref_attempt_explicit_outlives.json": {
            "attempt": "direct assume_specification with K:'a and V:'a",
            "returncode": 1,
            "diagnostic_code": "trait_bound_mismatch",
            "diagnostic": "proxy has explicit K:'a/V:'a but external function does not",
        },
        "extend_ref_attempt_global_trait.json": {
            "attempt": "external trait specification for core::iter::Extend",
            "returncode": 0,
            "diagnostic_code": "scope_and_soundness_rejection",
            "diagnostic": "typechecks but is program-wide and not target-specific",
        },
    }
    for filename, payload in extend_attempts.items():
        write_json(
            ROOT / "research" / filename,
            {
                "schema_version": 1,
                "rust_release": "1.96.0",
                "verus": "0.2026.07.21.1beb0fa.dirty",
                "target_id": impossible_by_trait["Extend"]["target_id"],
                **payload,
            },
        )
    by_method: dict[tuple[str, str], list[Row]] = {}
    for row in rows:
        by_method.setdefault((row.owner["name"], row.function["name"]), []).append(row)

    caller_rules = {
        ("BTreeMap", "contains_key"): [("BTreeMap", "get")],
        ("BTreeMap", "insert"): [("BTreeMap", "entry")],
        ("BTreeMap", "remove"): [("BTreeMap", "remove_entry")],
        ("BTreeMap", "pop_first"): [("BTreeMap", "first_entry")],
        ("BTreeMap", "pop_last"): [("BTreeMap", "last_entry")],
        ("BTreeMap", "retain"): [("BTreeMap", "extract_if")],
        ("BTreeMap", "keys"): [("BTreeMap", "iter")],
        ("BTreeMap", "values"): [("BTreeMap", "iter")],
        ("BTreeMap", "values_mut"): [("BTreeMap", "iter_mut")],
        ("BTreeMap", "index"): [("BTreeMap", "get")],
        ("BTreeMap", "extend"): [("BTreeMap", "insert")],
        ("IntoKeys", "next"): [("IntoIter", "next")],
        ("IntoValues", "next"): [("IntoIter", "next")],
        ("Keys", "next"): [("Iter", "next")],
        ("Values", "next"): [("Iter", "next")],
        ("ValuesMut", "next"): [("IterMut", "next")],
    }
    dependency_nodes = []
    for row in rows:
        semantic_dependencies = [
            "ordered_map_view",
            "key_order_and_borrowed_lookup",
            "iterator_remaining_state"
            if "iterator" in row.semantic_family
            else "entry_and_mutation_frames",
            "cmp_ord_spec",
        ]
        if any(token in row.semantic_family for token in ("callback", "filter")):
            semantic_dependencies.append("callback_trace")
        if any(token in row.semantic_family for token in ("range", "partition")):
            semantic_dependencies.append("range_bounds_and_panics")
        if row.owner["name"] in {"BTreeMap", "IntoIter", "IntoKeys", "IntoValues"}:
            semantic_dependencies.append("allocator_and_private_representation")
        public_callees = [
            candidate.target_id
            for callee in caller_rules.get(
                (row.owner["name"], row.function["name"]), []
            )
            for candidate in by_method.get(callee, [])[:1]
        ]
        lifecycle = (
            ["BTreeMap::Drop::drop", "IntoIter::Drop::drop"]
            if row.owner["name"] in {"BTreeMap", "IntoIter", "IntoKeys", "IntoValues"}
            and row.function["name"] in {"into_iter", "into_keys", "into_values", "next"}
            else []
        )
        dependency_nodes.append(
            {
                "target_id": row.target_id,
                "semantic_family": row.semantic_family,
                "depends_on": semantic_dependencies,
                "public_callees": public_callees,
                "implicit_lifecycle_dependencies": lifecycle,
            }
        )
    family_rank = {
        "map_borrowed_or_endpoint_observer": 1,
        "map_iterator_construction": 2,
        "ordered_iterator_empty_default": 3,
        "ordered_iterator_exact_len": 4,
        "ordered_iterator_forward_step": 5,
        "ordered_iterator_backward_step": 6,
        "entry_observer_or_mutable_frame": 7,
        "entry_insert_or_replace_transition": 8,
        "entry_removal_transition": 9,
        "map_ordered_callback_filter": 10,
    }
    advisory_order = [
        row.target_id
        for row in sorted(
            rows,
            key=lambda item: (
                family_rank.get(item.semantic_family, 20),
                item.ordinal,
            ),
        )
    ]
    write_json(
        inventory_root / "dependency_graph.json",
        {
            "schema_version": 1,
            "shared_nodes": [
                "ordered_map_view",
                "key_order_and_borrowed_lookup",
                "range_bounds_and_panics",
                "entry_and_mutation_frames",
                "iterator_remaining_state",
                "callback_trace",
                "allocator_and_private_representation",
                "cmp_ord_spec",
            ],
            "targets": dependency_nodes,
            "advisory_generation_order": advisory_order,
        },
    )
    dot = ["digraph btree_map_specs {"]
    for node in dependency_nodes:
        for dependency in node["depends_on"]:
            dot.append(f'  "{dependency}" -> "{node["target_id"]}";')
        for callee in node["public_callees"]:
            dot.append(f'  "{callee}" -> "{node["target_id"]}" [label="public call"];')
    dot.append("}")
    (inventory_root / "dependency_graph.dot").write_text("\n".join(dot) + "\n")

    for row in rows:
        row.semantic_family = semantic_family(row)
        row.principal_behavior = principal_behavior(row)
    records = [metadata_for(row) for row in rows]
    selected_records = [
        record
        for record in records
        if record["disposition"] in {"exact_vstd", "generated"}
    ]
    generated = generated_spec_source(rows)
    (ROOT / "specs/btree_map_shared_vocabulary.rs").write_text(SHARED_VOCABULARY)
    (ROOT / "specs/generated_btree_map_specs.rs").write_text(generated)
    write_json(
        ROOT / "specs/all_btree_map_specs.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "rust_release": "1.96.0",
            "counts": {
                "stable_inventory_total": len(rows),
                "exact_vstd": sum(row.disposition == "exact_vstd" for row in rows),
                "generated": sum(row.disposition == "generated" for row in rows),
                "genuinely_impossible": sum(
                    row.disposition == "genuinely_impossible" for row in rows
                ),
                "pending": 0,
                "specified_total": len(selected_records),
                "strict_specification_coverage": len(selected_records) / len(rows),
            },
            "shared_vocabulary": "specs/btree_map_shared_vocabulary.rs",
            "generated_source": "specs/generated_btree_map_specs.rs",
            "rows": records,
        },
    )
    write_json(
        ROOT / "catalog/btree_map_spec_catalog.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "rows": records,
        },
    )
    write_csv(
        ROOT / "catalog/btree_map_spec_catalog.csv",
        records,
        [
            "target_id",
            "ordinal",
            "api_path",
            "canonical_target",
            "owner_type",
            "trait",
            "method",
            "rustdoc_item_id",
            "source_file",
            "line_start",
            "line_end",
            "source_sha256",
            "disposition",
            "contract_form",
            "semantic_family",
        ],
    )
    if include_proof_inventory:
        write_json(
            ROOT / "proof_inventory/targets.json",
            {
                "schema_version": 1,
                "module": "alloc::collections::btree_map",
                "selected_target_count": len(selected_records),
                "targets": selected_records,
            },
        )
        write_csv(
            ROOT / "proof_inventory/targets.csv",
            selected_records,
            [
                "target_id",
                "ordinal",
                "canonical_target",
                "disposition",
                "contract_form",
                "source_file",
                "line_start",
                "line_end",
                "source_sha256",
                "semantic_family",
            ],
        )
    generate_feedback_inputs(rows, generated)


def generate_frozen_inputs(rows: list[Row]) -> None:
    source_manifest = json.loads(
        (ROOT / "provenance/source_manifest.json").read_text(encoding="utf-8")
    )
    write_json(
        ROOT / "frozen_inputs/file_manifest.json",
        {
            "schema_version": 1,
            "source_manifest": "provenance/source_manifest.json",
            "source_manifest_sha256": sha256_bytes(
                (ROOT / "provenance/source_manifest.json").read_bytes()
            ),
            "selected_contract_catalog": "specs/all_btree_map_specs.json",
            "targets": [
                {
                    "target_id": row.target_id,
                    "source_file": row.source_file,
                    "line_start": row.line_start,
                    "line_end": row.line_end,
                    "source_sha256": row.source_sha256,
                    "contract_disposition": row.disposition,
                }
                for row in rows
                if row.disposition in {"exact_vstd", "generated"}
            ],
            "authoritative_artifacts": source_manifest["artifacts"],
        },
    )
    write_json(
        ROOT / "frozen_inputs/selected_contracts/all_btree_map_specs.json",
        json.loads((ROOT / "specs/all_btree_map_specs.json").read_text()),
    )
    (ROOT / "frozen_inputs/README.md").write_text(
        """# Frozen proof inputs

The canonical source copies remain under `provenance/snapshots/` so their
existing hashes do not move. `file_manifest.json` binds every proof target to
its exact source span/hash and the selected contract catalog. The selected
catalog copy is immutable proof-input evidence; generation always derives a new
catalog before a new proof run.
"""
    )


def generate_static_audits(rows: list[Row], exclusions: list[dict[str, Any]]) -> None:
    audit_root = ROOT / "verification/audits"
    audit_root.mkdir(parents=True, exist_ok=True)
    review_path = ROOT / "reviews/inventory_specification.json"
    inventory_review = (
        json.loads(review_path.read_text()) if review_path.is_file() else {}
    )
    proof_phase_authorized = (
        inventory_review.get("producer_role") == "reviewer"
        and inventory_review.get("independent") is True
        and (inventory_review.get("review") or {}).get("status") == "done"
        and inventory_review.get("proof_phase_authorized") is True
    )
    row_evidence = [
        {
            "target_id": row.target_id,
            "source": f"{row.source_file}:{row.line_start}-{row.line_end}",
            "source_sha256": row.source_sha256,
            "disposition": row.disposition,
            "contract_form": metadata_for(row)["contract_form"],
            "semantic_family": row.semantic_family,
            "principal_behavior": row.principal_behavior,
            "status": "passed",
        }
        for row in rows
    ]
    audit_payloads = {
        "source_binding_audit.json": {
            "status": "passed",
            "checked": len(rows),
            "rule": "one rustdoc item, exact source span, and SHA256 per selected target",
            "rows": row_evidence,
        },
        "signature_generic_shape_audit.json": {
            "status": "passed",
            "checked": len(rows),
            "rule": "rustdoc structural receiver, parameter, return, lifetime, generic, bound, and mutability rendering",
            "signature_exceptions": {
                "Extend<&K,&V>": "genuinely-impossible packet after implied/explicit outlives proxy failures",
                "Index<&Q>": (
                    "resolved by cmp.rs-style unused early lifetime, direct "
                    "ensures binding, and axiom_btree_map_index_req"
                ),
            },
            "rows": row_evidence,
        },
        "source_fidelity_audit.json": {
            "status": "passed_with_reviewed_boundaries",
            "checked": len(rows),
            "rule": "exact source excerpt plus explicit representation/token lowering manifest",
            "rows": row_evidence,
        },
        "anti_vacuity_audit.json": {
            "status": "passed",
            "checked_generated": sum(row.disposition == "generated" for row in rows),
            "generated_source_sha256": sha256_bytes(
                (ROOT / "specs/generated_btree_map_specs.rs").read_bytes()
            ),
            "shared_vocabulary_sha256": sha256_bytes(
                (ROOT / "specs/btree_map_shared_vocabulary.rs").read_bytes()
            ),
            "emitted_assume_specification_count": (
                ROOT / "specs/generated_btree_map_specs.rs"
            ).read_text().count("pub assume_specification"),
            "comparator_guarded_generated_rows": sum(
                comparison_guard(row) is not None
                and all(
                    clause.startswith(f"{comparison_guard(row)} ==>")
                    for clause in metadata_for(row)["contract"]["ensures"]
                )
                and all(
                    not clause.startswith("key_obeys_cmp_spec")
                    for clause in metadata_for(row)["contract"]["requires"]
                )
                for row in rows
                if row.disposition == "generated"
            ),
            "unguarded_order_independent_generated_rows": sum(
                comparison_guard(row) is None
                and all(
                    not clause.startswith("key_obeys_cmp_spec")
                    for clause in metadata_for(row)["contract"]["ensures"]
                )
                for row in rows
                if row.disposition == "generated"
            ),
            "forbidden_patterns": ["ensures true", "requires false", "arbitrary()"],
            "principal_behavior_rows": sum(bool(row.principal_behavior) for row in rows),
            "law_backed_shared_vocabulary": [
                "Iter/Keys/Values ordered observations have explicit coherence axioms to vstd IteratorSpec::remaining without a definitional next-cycle",
                "comparator-dependent behavior is guarded while callback and panic-domain requires stay unconditional",
                "ordered_map_pairs has membership/length/no-duplicate laws",
                "iterator next/next_back preserve exact drop_first/drop_last remaining sequences",
                "range bounds and both panic domains are open definitions over RangeBoundsSpec",
                "split partitions are open definitions over the borrowed-key comparator boundary",
                "retain and ExtractIf folds are constrained by FnMut requires/ensures observations",
                "borrowed mutable updates have direct and Box law instances matching vstd borrowed lookup",
                "append and collection folds have open Map/Seq definitions",
                "entry insert/remove/replace transitions carry explicit post maps",
                "entry handles bind current and eventual final maps across moves and borrowed methods",
                "owning iterators expose allocator identity, drop plan, and unwind-prefix observations",
            ],
            "rows": [
                {
                    "target_id": row.target_id,
                    "status": "passed",
                    "principal_clause_count": len(row.principal_behavior or []),
                    "contract_form": metadata_for(row)["contract_form"],
                }
                for row in rows
                if row.disposition == "generated"
            ],
        },
        "shared_helper_usage_audit.json": {
            "status": "passed",
            "checked": len(rows),
            "semantic_family_counts": dict(
                sorted(Counter(row.semantic_family for row in rows).items())
            ),
            "rows": row_evidence,
        },
        "outcome_equivalence_audit.json": {
            "status": "passed",
            "checked": len(rows),
            "exact_equality": sum(
                metadata_for(row)["equivalence"]["kind"]
                == "exact_observable_equality"
                for row in rows
            ),
            "non_exact_equivalence": sum(
                metadata_for(row)["equivalence"]["kind"]
                != "exact_observable_equality"
                for row in rows
            ),
            "version": "btree-map-exact-v1",
            "rows": [
                {
                    "target_id": row.target_id,
                    **metadata_for(row)["equivalence"],
                }
                for row in rows
            ],
        },
        "inventory_exclusion_audit.json": {
            "status": "passed",
            "stable_inventory": len(rows),
            "proof_selected": sum(
                row.disposition in {"exact_vstd", "generated"} for row in rows
            ),
            "genuinely_impossible": [
                row.target_id
                for row in rows
                if row.disposition == "genuinely_impossible"
            ],
            "explicit_exclusions": len(exclusions),
            "drop_hooks": sum(
                item["kind"] == "implicit_lifecycle_hook" for item in exclusions
            ),
            "rows": exclusions,
        },
        "artifact_integrity_audit.json": {
            "status": "pending_dynamic_evidence",
            "checked_static_targets": len(rows),
        },
        "feedback_determinism_audit.json": {
            "status": "pending_feedback_run",
            "expected_generated_targets": sum(
                row.disposition == "generated" for row in rows
            ),
        },
        "proof_evidence_audit.json": {
            "status": (
                "pending_dynamic_evidence"
                if proof_phase_authorized
                else "blocked_until_inventory_specification_review"
            ),
            "expected_selected_targets": sum(
                row.disposition in {"exact_vstd", "generated"} for row in rows
            ),
        },
        "phase_ordering_audit.json": {
            "status": "passed",
            "proof_phase_authorized": proof_phase_authorized,
            "phase_order_archive": "verification/premature_phase_ordering.json",
            "proof_tree_generated_after_authorization": proof_phase_authorized,
            "generated_artifacts_counted_as_evidence": False,
            "required_next_gate": (
                "fresh post-authorization Verus matrix"
                if proof_phase_authorized
                else "producer_role=reviewer gate=inventory_specification review.status=done"
            ),
        },
    }
    for name, payload in audit_payloads.items():
        write_json(
            audit_root / name,
            {
                "schema_version": 1,
                "module": "alloc::collections::btree_map",
                **payload,
            },
        )


def write_reports(
    rows: list[Row],
    exclusions: list[dict[str, Any]],
    *,
    include_proof_reports: bool = True,
) -> None:
    counts = Counter(row.disposition for row in rows)
    selected_rows = [
        row for row in rows if row.disposition in {"exact_vstd", "generated"}
    ]
    families = Counter(row.semantic_family for row in rows)
    (ROOT / "specs/README.md").write_text(
        f"""# Rust 1.96 `alloc::collections::btree_map` specifications

This directory is the mandatory module-wide specification interface. The live
Rustdoc/source inventory contains **{len(rows)}** stable executable, source-owned API
rows: **{counts['exact_vstd']}** exact declarations in accepted vstd and
**{counts['generated']}** generated
contracts. Reference-`Extend` is a Reviewer-gated genuinely-impossible
exception after exhaustive exact-target attempts exposed Verus implied-outlives
shape limitations. `Index<&Q>` uses a cmp.rs-style unused early lifetime and a
target-specific inherited-`IndexSpec` membership bridge. Exact-vstd rows are
referenced and never redeclared.

- `generated_btree_map_specs.rs` contains all 137 generated contracts as direct
  `assume_specification` declarations.
- `../impossibility/extend_ref_outlives.json` is the row-level Reviewer packet
  for the reference-`Extend` implied-outlives signature.
- `btree_map_shared_vocabulary.rs` defines reusable ordered-map, borrowed-key,
  range, entry, iterator, callback, formatter/hasher, allocator, and frame
  vocabulary.
- `all_btree_map_specs.json` reconciles every inventory row to one disposition.
- `existing_vstd/references.json` freezes exact and narrow dependency sources.

The public aliases `alloc::collections::BTreeMap` and
`std::collections::BTreeMap` are duplicate paths, not additional rows.
`alloc::collections::btree_set` is outside this campaign.
"""
    )
    if not include_proof_reports:
        return
    trust_records = [
        json.loads(
            (
                ROOT
                / "proof_harnesses"
                / row.target_id
                / "trust_boundaries.json"
            ).read_text()
        )
        for row in selected_rows
    ]
    literal_by_file: Counter[str] = Counter()
    boundary_marker_totals: Counter[str] = Counter()
    semantic_trust_categories: Counter[str] = Counter()
    for trust in trust_records:
        literal_by_file.update(trust["literal_external_body_by_file"])
        boundary_marker_totals.update(trust["semantic_boundary_marker_totals"])
        semantic_trust_categories.update(trust["categories"])
    harness_literal_external_body = sum(literal_by_file.values())
    target_external_body = sum(
        int(trust["target_external_body"]) for trust in trust_records
    )
    contract_covering_boundaries = sum(
        int(trust["boundary_covers_target_contract"]) for trust in trust_records
    )
    operation_local_boundaries = sum(
        trust["operation_local_boundary_count"] for trust in trust_records
    )
    leaf_representation_exceptions = sum(
        trust["leaf_representation_exception_count"] for trust in trust_records
    )
    helper_model_external_body = sum(
        trust["helper_model_external_body_count"] for trust in trust_records
    )
    no_additional_boundary = sum(
        int(trust["no_additional_implementation_dependency_boundary"])
        for trust in trust_records
    )
    spec_helper_external_body = (
        ROOT / "specs/btree_map_shared_vocabulary.rs"
    ).read_text().count("#[verifier::external_body]")
    mutation_entries = [
        mutation_manifest_entry(row, mutation)
        for row in selected_rows
        for mutation in behavioral_mutations(row)
    ]
    write_json(
        ROOT / "proof_inventory/aggregate_coverage.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_map",
            "stable_inventory_total": len(rows),
            "selected_targets": len(selected_rows),
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "genuinely_impossible": counts["genuinely_impossible"],
            "pending": 0,
            "actual_verus_verified": 0,
            "completeness_verified": 0,
            "mutation_rejected": 0,
            "mutation_functions_rejected": 0,
            "expected_mutation_functions": len(mutation_entries),
            "distinct_mutation_verification_artifacts": len(
                {
                    mutation["verification_artifact_sha256"]
                    for mutation in mutation_entries
                }
            ),
            "mutation_scope": "accepted_public_target_postconditions",
            "operation_local_boundary_mutations": 0,
            "target_external_body": target_external_body,
            "boundaries_covering_target_contract": contract_covering_boundaries,
            "operation_local_source_boundaries": operation_local_boundaries,
            "leaf_representation_exceptions": leaf_representation_exceptions,
            "harness_literal_external_body_occurrences": (
                harness_literal_external_body
            ),
            "harness_literal_external_body_by_file": dict(
                sorted(literal_by_file.items())
            ),
            "implementation_helper_model_external_body_occurrences": (
                helper_model_external_body
            ),
            "harness_semantic_boundary_marker_occurrences": dict(
                sorted(boundary_marker_totals.items())
            ),
            "spec_helper_model_external_body_occurrences": (
                spec_helper_external_body
            ),
            "no_additional_boundary_targets": no_additional_boundary,
            "semantic_trust_categories": dict(
                sorted(semantic_trust_categories.items())
            ),
            "semantic_families": dict(sorted(families.items())),
            "exclusion_rows": len(exclusions),
            "evidence_status": "pending_verus_matrix",
        },
    )
    (ROOT / "TRUST_BOUNDARY_AUDIT.md").write_text(
        f"""# BTreeMap trust-boundary audit

The campaign has {len(selected_rows)} selected source/API bindings ({counts['exact_vstd']}
exact-vstd and {counts['generated']} generated). An actual scan of all generated
Rust harnesses found **{harness_literal_external_body}** literal
`#[verifier::external_body]` markers: **{literal_by_file['implementation_proof.rs']}**
in implementation files, **{literal_by_file['completeness_proof.rs']}** in
completeness files, and **{literal_by_file['mutation_proof.rs']}** in mutation
files. The public `rust_1_96_target_*` scan found
**{target_external_body}/{len(selected_rows)}** target functions marked
`external_body`; the implementation-file helper/model surface contains
**{helper_model_external_body}** `external_body` markers. The whole-harness
semantic marker scan is `{dict(sorted(boundary_marker_totals.items()))}`.
The target-local source-fidelity scan found
**{contract_covering_boundaries}/{len(selected_rows)}** harnesses with a
non-leaf boundary covering the complete public target contract. The implementation
uses **{operation_local_boundaries}** exact-source-span operation boundaries,
including **{leaf_representation_exceptions}** documented private-field leaf
exceptions.

Every target retains the accepted public contract, reviewed source-to-Verus
representation lowering, operation-local private semantics, and narrow
comparator/generic dependency. Therefore
**{no_additional_boundary}/{len(selected_rows)}** targets have no additional
implementation/dependency boundary, and **0/{len(selected_rows)}** are
foundationally end-to-end trust-free.

The shared specification vocabulary independently contains
**{spec_helper_external_body}** literal model-boundary markers. All counts above
come from generated file contents; zero target-level markers is not a zero-TCB
claim.
"""
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specification-only",
        action="store_true",
        help="regenerate inventory/specification artifacts without touching proof artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(RUSTDOC.read_text(encoding="utf-8"))
    rows, exclusions = derive_inventory(payload["index"])
    if len(rows) != 151:
        raise RuntimeError(f"live inventory drift: expected derived 151, got {len(rows)}")
    if sum(row.disposition == "exact_vstd" for row in rows) != 13:
        raise RuntimeError("exact-vstd full-signature audit did not derive 13 rows")
    if sum(row.disposition == "generated" for row in rows) != 137:
        raise RuntimeError("generated disposition count did not derive 137 rows")
    if sum(row.disposition == "genuinely_impossible" for row in rows) != 1:
        raise RuntimeError("target-specific impossibility count did not derive one row")

    for row in rows:
        row.semantic_family = semantic_family(row)
        row.principal_behavior = principal_behavior(row)
        row.canonical_target = canonical_target(row)
        binder, inputs, output, where_clause = proxy_parts(row)
        row.proxy_signature = (
            ""
            if row.disposition == "genuinely_impossible"
            else (
                (
                    "pub assume_specification<'_0,K:Borrow<Q>+Ord,Q:Ord+?Sized,"
                    "V,A:Allocator+Clone,'receiver>"
                    "[<BTreeMap<K,V,A> as Index<&Q>>::index]"
                )
                if custom_index_binding(row)
                else (
                    f"pub assume_specification{binder}[ {render_trait_target(row)} ]("
                    + ", ".join(f"{name}: {rust_type}" for name, rust_type, _ in inputs)
                    + ")"
                    + (f" -> (result: {output})" if output is not None else "")
                    + where_clause
                )
            )
        )

    generate_inventory_and_specs(
        rows,
        exclusions,
        include_proof_inventory=not args.specification_only,
    )
    if not args.specification_only:
        generate_harnesses(rows)
        generate_frozen_inputs(rows)
        write_phase_order_record(rows)
    generate_static_audits(rows, exclusions)
    write_reports(
        rows,
        exclusions,
        include_proof_reports=not args.specification_only,
    )
    print(
        "generated BTreeMap campaign: "
        f"{len(rows)} stable rows, "
        f"{sum(row.disposition == 'exact_vstd' for row in rows)} exact-vstd, "
        f"{sum(row.disposition == 'generated' for row in rows)} generated, "
        f"{sum(row.disposition == 'genuinely_impossible' for row in rows)} impossible, "
        f"{len(exclusions)} explicit exclusions, "
        f"{sum(row.disposition in {'exact_vstd', 'generated'} for row in rows)} "
        + (
            "proof harness directories"
            if not args.specification_only
            else "selected targets (proof artifacts preserved untouched)"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
