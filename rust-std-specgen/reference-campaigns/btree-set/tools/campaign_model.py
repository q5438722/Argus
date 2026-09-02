from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final


ROOT: Final = Path(__file__).resolve().parents[1]
RUSTDOC: Final = ROOT / "provenance/frozen/rustdoc-json-1.96/alloc.json"
SOURCE_ROOT: Final = ROOT / "provenance/frozen/rust-1.96/library"
SET_FILE: Final = "alloc/src/collections/btree/set.rs"
OWNER_FILES: Final = {SET_FILE}
VSTD_FILE: Final = ROOT / "provenance/frozen/vstd/std_specs/btree.rs"
MODULE: Final = "alloc::collections::btree_set"

MATCH_DIMENSIONS: Final = (
    "target_binding",
    "receiver_reference_shape",
    "parameter_shape",
    "return_shape",
    "lifetimes",
    "generics",
    "bounds",
    "mutability",
)

EXACT_VSTD: Final = {
    ("BTreeSet", "Clone", "clone"): 753,
    ("BTreeSet", "Default", "default"): 765,
    ("BTreeSet", "inherent", "clear"): 905,
    ("BTreeSet", "inherent", "contains"): 809,
    ("BTreeSet", "inherent", "get"): 853,
    ("BTreeSet", "inherent", "insert"): 772,
    ("BTreeSet", "inherent", "is_empty"): 746,
    ("BTreeSet", "inherent", "iter"): 935,
    ("BTreeSet", "inherent", "len"): 739,
    ("BTreeSet", "inherent", "new"): 760,
    ("BTreeSet", "inherent", "remove"): 894,
}

TRAIT_PATHS: Final = {
    "BitAnd": "core::ops::BitAnd",
    "BitOr": "core::ops::BitOr",
    "BitXor": "core::ops::BitXor",
    "Clone": "core::clone::Clone",
    "Debug": "core::fmt::Debug",
    "Default": "core::default::Default",
    "DoubleEndedIterator": "core::iter::DoubleEndedIterator",
    "ExactSizeIterator": "core::iter::ExactSizeIterator",
    "Extend": "core::iter::Extend",
    "From": "core::convert::From",
    "FromIterator": "core::iter::FromIterator",
    "Hash": "core::hash::Hash",
    "IntoIterator": "core::iter::IntoIterator",
    "Iterator": "core::iter::Iterator",
    "Ord": "core::cmp::Ord",
    "PartialEq": "core::cmp::PartialEq",
    "PartialOrd": "core::cmp::PartialOrd",
    "Sub": "core::ops::Sub",
}

TYPE_PATHS: Final = {
    "Allocator": "alloc::alloc::Allocator",
    "BitAnd": "core::ops::BitAnd",
    "BitOr": "core::ops::BitOr",
    "BitXor": "core::ops::BitXor",
    "Borrow": "core::borrow::Borrow",
    "Clone": "core::clone::Clone",
    "Copy": "core::marker::Copy",
    "Debug": "core::fmt::Debug",
    "Default": "core::default::Default",
    "DoubleEndedIterator": "core::iter::DoubleEndedIterator",
    "FnMut": "core::ops::FnMut",
    "FnOnce": "core::ops::FnOnce",
    "From": "core::convert::From",
    "FromIterator": "core::iter::FromIterator",
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
    "Sub": "core::ops::Sub",
    "fmt::Debug": "core::fmt::Debug",
    "fmt::Formatter": "core::fmt::Formatter",
    "fmt::Result": "core::fmt::Result",
}

ITERATOR_TYPES: Final = {
    "Difference",
    "ExtractIf",
    "Intersection",
    "IntoIter",
    "Iter",
    "Range",
    "SymmetricDifference",
    "Union",
}
REFERENCE_OPERATOR_TRAITS: Final = {"BitAnd", "BitOr", "BitXor", "Sub"}


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
    canonical_target: str = ""
    proxy_signature: str = ""
    semantic_family: str = ""
    principal_behavior: list[str] | None = None
    contract_fingerprint: str = ""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode())


def load_rustdoc() -> dict[str, Any]:
    with RUSTDOC.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or not isinstance(value.get("index"), dict):
        raise RuntimeError("frozen rustdoc JSON does not contain an item index")
    return value


def attribute_texts(item: dict[str, Any]) -> list[str]:
    return [
        attribute.get("other", "") if isinstance(attribute, dict) else str(attribute)
        for attribute in item.get("attrs", [])
    ]


def main_stability(item: dict[str, Any]) -> str:
    attributes = attribute_texts(item)
    if any("Stability" in value and "level: Stable" in value for value in attributes):
        return "stable"
    if any("Stability" in value and "level: Unstable" in value for value in attributes):
        return "unstable"
    return "none"


def source_lines(filename: str) -> list[str]:
    return (SOURCE_ROOT / filename).read_text(encoding="utf-8").splitlines()


def excerpt_for(item: dict[str, Any]) -> tuple[str, int, int, str]:
    span = item["span"]
    filename = span["filename"]
    start = int(span["begin"][0])
    end = int(span["end"][0])
    excerpt = "\n".join(source_lines(filename)[start - 1 : end]) + "\n"
    return filename, start, end, excerpt


def resolve_owner_module(payload: dict[str, Any]) -> tuple[str, str]:
    paths = payload["paths"]
    index = payload["index"]
    public_id = next(
        str(item_id)
        for item_id, item in paths.items()
        if item.get("kind") == "module"
        and item.get("path") == ["alloc", "collections", "btree_set"]
    )
    public_module = index[public_id]["inner"]["module"]
    glob_uses = [
        index[str(item_id)]["inner"]["use"]
        for item_id in public_module["items"]
        if "use" in index[str(item_id)]["inner"]
        and index[str(item_id)]["inner"]["use"].get("is_glob")
    ]
    if len(glob_uses) != 1 or glob_uses[0].get("id") is None:
        raise RuntimeError("btree_set public glob re-export did not resolve uniquely")
    return public_id, str(glob_uses[0]["id"])


def _follow_use(index: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    use = item["inner"].get("use")
    if use and use.get("id") is not None:
        return index[str(use["id"])]
    return item


def derive_inventory(
    payload: dict[str, Any],
) -> tuple[list[Row], list[dict[str, Any]], dict[str, Any]]:
    index = payload["index"]
    public_module_id, owner_module_id = resolve_owner_module(payload)
    owner_module = index[owner_module_id]["inner"]["module"]
    stable_types: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    seen_type_ids: set[int] = set()

    for raw_id in owner_module["items"]:
        original = index[str(raw_id)]
        item = _follow_use(index, original)
        kind = next(iter(item["inner"]))
        if kind not in {"struct", "enum"}:
            continue
        if item["id"] in seen_type_ids:
            continue
        seen_type_ids.add(item["id"])
        stability = main_stability(item)
        if stability == "stable":
            stable_types.append(item)
        else:
            exclusions.append(
                {
                    "name": item.get("name"),
                    "kind": f"unstable_public_{kind}",
                    "rustdoc_item_id": item["id"],
                    "reason": "public type is unstable in the main Stability attribute",
                    "stability": stability,
                    "source_span": item.get("span"),
                }
            )

    rows: list[Row] = []
    excluded_impl_counts = {
        "synthetic_or_blanket": 0,
        "external_source": 0,
        "unstable_impl": 0,
    }
    seen_function_ids: set[int] = set()
    for owner in stable_types:
        kind = next(iter(owner["inner"]))
        for impl_id in owner["inner"][kind].get("impls", []):
            impl_item = index[str(impl_id)]
            impl_data = impl_item["inner"]["impl"]
            span = impl_item.get("span")
            if impl_data.get("is_synthetic"):
                excluded_impl_counts["synthetic_or_blanket"] += 1
                continue
            if not span or span.get("filename") not in OWNER_FILES:
                excluded_impl_counts["external_source"] += 1
                continue
            trait = (impl_data.get("trait") or {}).get("path") or "inherent"
            impl_stability = main_stability(impl_item)
            if trait != "inherent" and impl_stability != "stable":
                excluded_impl_counts["unstable_impl"] += 1
                exclusions.append(
                    {
                        "name": f"<{owner['name']} as {trait}>",
                        "kind": "unstable_trait_impl",
                        "rustdoc_item_id": impl_item["id"],
                        "reason": "trait implementation is unstable in the main Stability attribute",
                        "stability": impl_stability,
                        "source_span": span,
                    }
                )
                continue

            source_functions: list[dict[str, Any]] = []
            for function_id in impl_data.get("items", []):
                function = index[str(function_id)]
                fspan = function.get("span")
                if (
                    "function" in function["inner"]
                    and fspan
                    and fspan.get("filename") in OWNER_FILES
                ):
                    source_functions.append(function)

            if trait != "inherent" and not source_functions:
                exclusions.append(
                    {
                        "name": f"<{owner['name']} as {trait}>",
                        "kind": "marker_or_non_executable_trait_impl",
                        "rustdoc_item_id": impl_item["id"],
                        "reason": "source-owned impl has no executable method body",
                        "stability": impl_stability,
                        "source_span": span,
                    }
                )

            for function in source_functions:
                stability = main_stability(function)
                name = function["name"]
                if trait == "inherent" and stability != "stable":
                    exclusions.append(
                        {
                            "name": f"{owner['name']}::{name}",
                            "kind": "unstable_inherent_method",
                            "rustdoc_item_id": function["id"],
                            "reason": "method is unstable in the main Stability attribute",
                            "stability": stability,
                            "source_span": function.get("span"),
                        }
                    )
                    continue
                if stability == "unstable" or (trait, name) == ("Extend", "extend_one"):
                    exclusions.append(
                        {
                            "name": f"<{owner['name']} as {trait}>::{name}",
                            "kind": "unstable_trait_method",
                            "rustdoc_item_id": function["id"],
                            "reason": (
                                "trait item is unstable even though its implementation "
                                "container is stable"
                            ),
                            "stability": "unstable_trait_item",
                            "source_span": function.get("span"),
                            "trait_source": (
                                "library/core/src/iter/traits/collect.rs "
                                "(extend_one, issue 72631)"
                            ),
                        }
                    )
                    continue
                if trait == "Drop" and name == "drop":
                    exclusions.append(
                        {
                            "name": f"<{owner['name']} as Drop>::drop",
                            "kind": "implicit_lifecycle_hook",
                            "rustdoc_item_id": function["id"],
                            "reason": "Drop::drop is not a publicly nameable executable API",
                            "stability": "stable_but_not_publicly_callable",
                            "source_span": function.get("span"),
                        }
                    )
                    continue
                if int(function["id"]) in seen_function_ids:
                    raise RuntimeError(f"duplicate source-owned function: {function['id']}")
                seen_function_ids.add(int(function["id"]))
                filename, start, end, excerpt = excerpt_for(function)
                rows.append(
                    Row(
                        owner=owner,
                        impl_item=impl_item,
                        function=function,
                        trait=trait,
                        item_id=int(function["id"]),
                        source_file=filename,
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
        row.disposition = "exact_vstd" if key in EXACT_VSTD else "generated"
        row.semantic_family = semantic_family(row)
        row.principal_behavior = principal_behavior(row)
        row.canonical_target = canonical_target(row)
        binder, inputs, output, where_clause = proxy_parts(row)
        row.proxy_signature = (
            f"pub assume_specification{binder}[ {render_trait_target(row)} ]("
            + ", ".join(f"{name}: {rust_type}" for name, rust_type, _ in inputs)
            + ")"
            + (f" -> (result: {output})" if output is not None else "")
            + where_clause
        )
        contract_material = json.dumps(
            {
                "canonical_target": row.canonical_target,
                "disposition": row.disposition,
                "requires": require_lines(row, inputs, output)
                if row.disposition == "generated"
                else [],
                "ensures": ensure_lines(row, inputs, output)
                if row.disposition == "generated"
                else ["exact vstd reference"],
                "source_sha256": row.source_sha256,
            },
            sort_keys=True,
        )
        row.contract_fingerprint = sha256_text(contract_material)

    stable_names = {item["name"] for item in stable_types}
    required = {
        "BTreeSet",
        "Difference",
        "ExtractIf",
        "Intersection",
        "IntoIter",
        "Iter",
        "Range",
        "SymmetricDifference",
        "Union",
    }
    if stable_names != required:
        raise RuntimeError(
            f"stable public type resolution drift: {sorted(stable_names)}"
        )
    exact_keys = {
        (row.owner["name"], row.trait, row.function["name"])
        for row in rows
        if row.disposition == "exact_vstd"
    }
    if exact_keys != set(EXACT_VSTD):
        raise RuntimeError(
            f"exact-vstd target set drift: missing={sorted(set(EXACT_VSTD)-exact_keys)} "
            f"extra={sorted(exact_keys-set(EXACT_VSTD))}"
        )
    for row in rows:
        if row.disposition != "exact_vstd":
            continue
        evidence = exact_vstd_evidence(row)
        if evidence is None or not all(
            item["matched"] for item in evidence["dimensions"].values()
        ):
            failed = [
                name
                for name, item in (evidence or {}).get("dimensions", {}).items()
                if not item["matched"]
            ]
            raise RuntimeError(
                f"exact-vstd structural comparison failed for {row.target_id}: "
                f"{failed}"
            )

    derivation = {
        "rustdoc_public_module_id": int(public_module_id),
        "private_owner_module_id": int(owner_module_id),
        "owner_files": sorted(OWNER_FILES),
        "stable_public_types": sorted(stable_names),
        "excluded_impl_counts": excluded_impl_counts,
        "rules": [
            "resolve the stable public glob re-export to private btree::set",
            "canonicalize alloc::collections::BTreeSet as an alias, not a second owner",
            "include stable public inherent functions on stable re-exported types",
            "include stable source-owned trait method bodies, including derived methods",
            "use main Stability rather than const-stability",
            "exclude synthetic, blanket, inherited-default, marker-only, and unstable trait items",
        ],
    }
    exclusions.sort(
        key=lambda item: (
            (item.get("source_span") or {}).get("filename", ""),
            ((item.get("source_span") or {}).get("begin") or [0])[0],
            str(item.get("name")),
        )
    )
    return rows, exclusions, derivation


def render_path(path: str) -> str:
    if path.startswith("$crate::"):
        path = "core::" + path.removeprefix("$crate::")
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
        generic = value["generic"]
        return self_type if generic == "Self" and self_type is not None else generic
    if "resolved_path" in value:
        return render_path_with_args(value["resolved_path"], self_type)
    if "borrowed_ref" in value:
        reference = value["borrowed_ref"]
        lifetime = f"{reference['lifetime']} " if reference.get("lifetime") else ""
        mutable = "mut " if reference["is_mutable"] else ""
        return f"&{lifetime}{mutable}{render_type(reference['type'], self_type)}"
    if "tuple" in value:
        entries = [render_type(item, self_type) for item in value["tuple"]]
        return f"({entries[0]},)" if len(entries) == 1 else f"({', '.join(entries)})"
    if "array" in value:
        array = value["array"]
        length = array["len"]
        if isinstance(length, dict):
            length = length.get("expr", str(length))
        return f"[{render_type(array['type'], self_type)}; {length}]"
    if "slice" in value:
        return f"[{render_type(value['slice'], self_type)}]"
    if "raw_pointer" in value:
        pointer = value["raw_pointer"]
        mutability = "mut" if pointer["is_mutable"] else "const"
        return f"*{mutability} {render_type(pointer['type'], self_type)}"
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
    raise ValueError(f"unsupported generic bound: {bound}")


def param_parts(parameter: dict[str, Any]) -> tuple[str, str, list[str]]:
    name = parameter["name"]
    kind = parameter["kind"]
    if "lifetime" in kind:
        return name, "lifetime", list(kind["lifetime"].get("outlives", []))
    if "type" in kind:
        return name, "type", [
            render_bound(bound) for bound in kind["type"].get("bounds", [])
        ]
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
        reference = value.get("borrowed_ref")
        if reference is not None and reference.get("lifetime") is None:
            return True
        return any(has_elided_reference(nested) for nested in value.values())
    if isinstance(value, list):
        return any(has_elided_reference(nested) for nested in value)
    return False


def fill_elided_references(value: Any, lifetime: str) -> Any:
    result = copy.deepcopy(value)

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            reference = item.get("borrowed_ref")
            if reference is not None and reference.get("lifetime") is None:
                reference["lifetime"] = lifetime
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(result)
    return result


def impl_for_type(row: Row) -> str:
    value = row.impl_item["inner"]["impl"]["for"]
    if row.trait in REFERENCE_OPERATOR_TRAITS:
        value = fill_elided_references(value, "'b")
    return render_type(value).replace("'_", "'a")


def render_trait_target(row: Row) -> str:
    impl_data = row.impl_item["inner"]["impl"]
    for_type = impl_for_type(row)
    if row.trait == "inherent":
        target_type = for_type.replace("<", "::<", 1) if "<" in for_type else for_type
        target = f"{target_type}::{row.function['name']}"
    else:
        trait = copy.deepcopy(impl_data["trait"])
        if row.trait in REFERENCE_OPERATOR_TRAITS:
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


def proxy_parts(
    row: Row,
) -> tuple[str, list[tuple[str, str, str]], str | None, str]:
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
    if row.trait in REFERENCE_OPERATOR_TRAITS:
        merged[0:0] = [("'a", "lifetime", []), ("'b", "lifetime", [])]
        seen.update({"'a", "'b"})
    if "'a" in for_type and "'a" not in seen:
        merged.insert(0, ("'a", "lifetime", []))
        seen.add("'a")
    if explicit_self_lifetime and "'s" not in seen:
        insert_at = 0
        while insert_at < len(merged) and merged[insert_at][1] == "lifetime":
            insert_at += 1
        merged.insert(insert_at, ("'s", "lifetime", []))

    generic_parts: list[str] = []
    for name, kind, bounds in merged:
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
        name = (
            "this"
            if source_name == "self"
            else source_name
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", source_name)
            else f"arg{index}"
        )
        if name in used_names:
            name = f"{name}_{index}"
        used_names.add(name)
        rendered = rust_type
        if (
            explicit_self_lifetime
            and source_name == "self"
            and "borrowed_ref" in rust_type
            and rust_type["borrowed_ref"].get("lifetime") is None
        ):
            rendered = copy.deepcopy(rust_type)
            rendered["borrowed_ref"]["lifetime"] = "'s"
        elif (
            row.trait in REFERENCE_OPERATOR_TRAITS
            and source_name == "self"
            and "borrowed_ref" in rust_type
            and rust_type["borrowed_ref"].get("lifetime") is None
        ):
            rendered = copy.deepcopy(rust_type)
            rendered["borrowed_ref"]["lifetime"] = "'b"
        inputs.append((name, render_type(rendered, for_type), source_name))

    if output_value is not None and explicit_self_lifetime:
        output_value = fill_elided_references(output_value, "'s")
    output = render_type(output_value, for_type) if output_value is not None else None
    predicates = [
        *impl_data["generics"].get("where_predicates", []),
        *function_data["generics"].get("where_predicates", []),
    ]
    rendered_predicates = [render_where_predicate(item, for_type) for item in predicates]
    where_clause = f" where {', '.join(rendered_predicates)}" if rendered_predicates else ""
    return binder, inputs, output, where_clause


def canonical_target(row: Row) -> str:
    target = render_trait_target(row)
    return target.replace(
        "BTreeSet", "alloc::collections::btree_set::BTreeSet", 1
    )


def semantic_family(row: Row) -> str:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    if owner in ITERATOR_TYPES:
        if trait == "Iterator":
            if name == "next":
                return "ordered_iterator_forward_step"
            if name in {"last", "min", "max"}:
                return "ordered_iterator_terminal_selection"
            if name == "size_hint":
                return "adapter_specific_size_hint"
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
    if owner == "BTreeSet":
        if trait == "inherent":
            return {
                "range": "ordered_range_construction",
                "difference": "difference_adapter_construction",
                "symmetric_difference": "symmetric_difference_adapter_construction",
                "intersection": "intersection_adapter_construction",
                "union": "union_adapter_construction",
                "is_disjoint": "set_relation_observer",
                "is_subset": "set_relation_observer",
                "is_superset": "set_relation_observer",
                "first": "ordered_endpoint_observer",
                "last": "ordered_endpoint_observer",
                "pop_first": "ordered_endpoint_removal",
                "pop_last": "ordered_endpoint_removal",
                "replace": "representative_replacement",
                "take": "borrowed_representative_removal",
                "retain": "ordered_callback_retain",
                "append": "set_append_transition",
                "split_off": "ordered_set_partition",
                "extract_if": "extract_if_construction",
            }.get(name, "exact_vstd_transition")
        return {
            "Hash": "ordered_set_hash",
            "PartialEq": "set_equality",
            "PartialOrd": "ordered_set_comparison",
            "Ord": "ordered_set_comparison",
            "Clone": "set_clone_transition",
            "FromIterator": "sorted_deduplicating_conversion",
            "From": "sorted_deduplicating_conversion",
            "IntoIterator": "ordered_iterator_construction",
            "Extend": "ordered_extend_transition",
            "Default": "exact_vstd_transition",
            "Sub": "owned_set_operation",
            "BitXor": "owned_set_operation",
            "BitAnd": "owned_set_operation",
            "BitOr": "owned_set_operation",
            "Debug": "ordered_debug_format",
        }.get(trait, "source_owned_transition")
    raise RuntimeError(
        f"unclassified API family: {owner} {trait} {row.function['name']}"
    )


def principal_behavior(row: Row) -> list[str]:
    family = row.semantic_family or semantic_family(row)
    behavior = {
        "adapter_specific_size_hint": [
            "the exact Rust source lower and upper formulas are stated for each adapter state variant",
            "the resulting interval contains the exact remaining output length",
        ],
        "borrowed_representative_removal": [
            "result presence equals borrowed-key membership",
            "the comparator-equal stored representative is returned and removed",
        ],
        "difference_adapter_construction": [
            "remaining observations are exactly self minus other",
            "items are yielded in strictly ascending order without duplicates",
        ],
        "exact_vstd_transition": [
            "the exact target and complete signature match the referenced vstd declaration",
        ],
        "extract_if_construction": [
            "initial construction preserves the set and records exactly the ascending in-range candidates",
            "normal steps scan callbacks in candidate order and remove only the first accepted candidate",
            "partial drop retains every rejected and unvisited candidate; a panicking candidate is retained",
        ],
        "intersection_adapter_construction": [
            "remaining observations are exactly the intersection",
            "items are yielded in strictly ascending order without duplicates",
        ],
        "ordered_callback_retain": [
            "callbacks are observed in ascending key order",
            "the final set contains exactly retained pre-state representatives",
        ],
        "ordered_debug_format": [
            "the source-specific debug builder tag and ordered entries determine formatter state and result",
        ],
        "ordered_endpoint_observer": [
            "None is returned exactly for the empty set",
            "Some returns the minimum or maximum stored representative",
        ],
        "ordered_endpoint_removal": [
            "None leaves an empty set unchanged",
            "Some returns and removes exactly the minimum or maximum representative",
        ],
        "ordered_extend_transition": [
            "input items are processed in iterator order",
            "new comparator classes are inserted while existing representatives are retained",
        ],
        "ordered_iterator_backward_step": [
            "Some removes exactly the last remaining ordered observation",
            "None is returned exactly when no observation remains",
        ],
        "ordered_iterator_clone": [
            "clone preserves the complete ordered remaining observation",
        ],
        "ordered_iterator_construction": [
            "the iterator observes exactly the source set",
            "items are yielded in strictly ascending order without duplicates",
        ],
        "ordered_iterator_empty_default": [
            "the default iterator has no remaining observations",
        ],
        "ordered_iterator_exact_len": [
            "returned length exactly equals remaining observations",
        ],
        "ordered_iterator_forward_step": [
            "Some removes exactly the first remaining ordered observation",
            "None is returned exactly when no observation remains",
        ],
        "ordered_iterator_terminal_selection": [
            "the returned item is the documented first or last ordered endpoint",
            "None is returned exactly when no observation remains",
        ],
        "ordered_range_construction": [
            "normal return requires non-inverted, non-double-excluded equal bounds",
            "remaining observations are exactly ascending in-range representatives",
        ],
        "ordered_set_comparison": [
            "result is the lexicographic comparison of ascending observations",
        ],
        "ordered_set_hash": [
            "the exact length prefix and ascending representative sequence determine the final hasher state",
        ],
        "ordered_set_partition": [
            "left and returned sets partition the old set at the borrowed-order boundary",
            "partition lengths sum to the old length",
        ],
        "owned_set_operation": [
            "result membership is the selected set operation",
            "representatives follow the source adapter and stable sorted-build path",
        ],
        "representative_replacement": [
            "membership gains the supplied comparator class",
            "an old comparator-equal representative is returned and replaced when present",
        ],
        "set_append_transition": [
            "other is empty afterward and membership is the union",
            "representative identity follows BTreeMap append conflict handling",
        ],
        "set_clone_transition": [
            "clone_from makes the receiver observationally equal to the source",
        ],
        "set_equality": [
            "result is exact extensional set equality",
        ],
        "set_relation_observer": [
            "result exactly states disjointness, subset, or superset membership",
        ],
        "sorted_deduplicating_conversion": [
            "result contains every input comparator class exactly once",
            "stable sorting and DedupSortedIter retain the last comparator-equal input",
        ],
        "symmetric_difference_adapter_construction": [
            "remaining observations are exactly membership in one input but not both",
            "items are yielded in strictly ascending order without duplicates",
        ],
        "union_adapter_construction": [
            "remaining observations are exactly the union",
            "items are yielded in strictly ascending order without duplicates",
        ],
    }
    if family not in behavior:
        raise RuntimeError(f"missing principal behavior for {family}")
    return behavior[family]


def receiver_info(
    inputs: list[tuple[str, str, str]],
) -> tuple[str | None, str | None]:
    for name, rust_type, source_name in inputs:
        if source_name == "self":
            if rust_type.startswith("&") and "mut " in rust_type:
                return name, "mut_ref"
            if rust_type.startswith("&"):
                return name, "ref"
            return name, "value"
    return None, None


def _source_argument(
    inputs: list[tuple[str, str, str]], *names: str, fallback: str
) -> str:
    by_source = {source: rendered for rendered, _, source in inputs}
    for name in names:
        if name in by_source:
            return by_source[name]
    return fallback


def iterator_remaining_expr(row: Row, receiver: str) -> str:
    owner = row.owner["name"]
    function = {
        "Iter": "iter_remaining",
        "IntoIter": "into_iter_remaining",
        "Range": "range_remaining",
        "Difference": "difference_remaining",
        "SymmetricDifference": "symmetric_difference_remaining",
        "Intersection": "intersection_remaining",
        "Union": "union_remaining",
        "ExtractIf": "extract_if_remaining",
    }.get(owner)
    if function is None:
        raise RuntimeError(f"no remaining-sequence model for {owner}")
    return f"{function}({receiver})"


def iterator_value_sequence(row: Row, receiver: str) -> str:
    remaining = iterator_remaining_expr(row, receiver)
    if row.owner["name"] in {"IntoIter", "ExtractIf"}:
        return remaining
    return f"{remaining}.unref()"


def debug_tag(owner: str) -> int:
    return {
        "Iter": 1,
        "IntoIter": 2,
        "Range": 3,
        "Difference": 4,
        "SymmetricDifference": 5,
        "Intersection": 6,
        "Union": 7,
        "ExtractIf": 8,
        "BTreeSet": 9,
    }[owner]


def debug_shape_expression(owner: str, receiver: str) -> str:
    return {
        "BTreeSet": f"btree_set_debug_shape(*{receiver})",
        "Iter": f"iter_debug_shape(*{receiver})",
        "IntoIter": f"into_iter_debug_shape(*{receiver})",
        "Range": f"range_debug_shape(*{receiver})",
        "Difference": f"difference_debug_shape(*{receiver})",
        "SymmetricDifference": f"symmetric_difference_debug_shape(*{receiver})",
        "Intersection": f"intersection_debug_shape(*{receiver})",
        "Union": f"union_debug_shape(*{receiver})",
        "ExtractIf": f"extract_if_debug_shape(*{receiver})",
    }[owner]


def debug_shape_law_expression(owner: str, receiver: str) -> str:
    return {
        "BTreeSet": f"btree_set_debug_shape_law(*{receiver})",
        "Iter": f"iter_debug_shape_law(*{receiver})",
        "IntoIter": f"into_iter_debug_shape_law(*{receiver})",
        "Range": f"range_debug_shape_law(*{receiver})",
        "Difference": f"difference_debug_shape_law(*{receiver})",
        "SymmetricDifference": (
            f"symmetric_difference_debug_shape_law(*{receiver})"
        ),
        "Intersection": f"intersection_debug_shape_law(*{receiver})",
        "Union": f"union_debug_shape_law(*{receiver})",
        "ExtractIf": f"extract_if_debug_shape_law(*{receiver})",
    }[owner]


def set_operation_sequence(trait: str, left: str, right: str) -> str:
    return {
        "Sub": f"difference_sequence({left}, {right})",
        "BitAnd": f"intersection_source_sequence({left}, {right})",
        "BitOr": f"union_sequence({left}, {right})",
        "BitXor": f"symmetric_difference_sequence({left}, {right})",
    }[trait]


def require_lines(
    row: Row,
    inputs: list[tuple[str, str, str]],
    output: str | None,
) -> list[str]:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    receiver, receiver_kind = receiver_info(inputs)
    if receiver is None and inputs:
        receiver = inputs[0][0]

    if owner in ITERATOR_TYPES:
        if owner == "ExtractIf" and trait == "Iterator" and name == "next":
            return [
                (
                    "retain_callback_trace_law("
                    f"extract_if_predicate_state(*{receiver}), "
                    f"extract_if_pending(*{receiver}))"
                )
            ]
        if (
            owner
            in {"Difference", "SymmetricDifference", "Intersection", "Union"}
            and trait == "Iterator"
            and name in {"next", "size_hint"}
        ):
            law = {
                "Difference": "difference_source_state_law",
                "SymmetricDifference": (
                    "symmetric_difference_source_state_law"
                ),
                "Intersection": "intersection_source_state_law",
                "Union": "union_source_state_law",
            }[owner]
            return [f"{law}(*{receiver})"]
        return []

    if owner != "BTreeSet" or trait != "inherent":
        return []

    sequence = f"btree_set_sequence(*{receiver})"
    if name == "range":
        range_value = _source_argument(inputs, "range", fallback="arg1")
        return [
            (
                f"K::obeys_cmp_spec() ==> "
                f"range_order_law({sequence}, &{range_value})"
            ),
            (
                f"{sequence}.len() == 0 || "
                f"!range_start_after_end(&{range_value})"
            ),
            (
                f"{sequence}.len() == 0 || "
                f"!range_equal_excluded(&{range_value})"
            ),
        ]
    if name == "retain":
        callback = _source_argument(inputs, "f", fallback="arg1")
        return [
            f"retain_callback_trace_law({callback}, {sequence})"
        ]
    if name in {"take", "split_off"}:
        value = _source_argument(inputs, "value", fallback="arg1")
        return [
            f"borrowed_key_order_law({sequence}, {value})"
        ]
    if name == "extract_if":
        range_value = _source_argument(inputs, "range", fallback="arg1")
        return [
            (
                f"T::obeys_cmp_spec() ==> "
                f"range_order_law({sequence}, &{range_value})"
            )
        ]
    return []


def _ensure_lines_unbound(
    row: Row,
    inputs: list[tuple[str, str, str]],
    output: str | None,
) -> list[str]:
    owner = row.owner["name"]
    trait = row.trait
    name = row.function["name"]
    receiver, receiver_kind = receiver_info(inputs)
    if receiver is None and inputs:
        receiver = inputs[0][0]

    if owner in ITERATOR_TYPES:
        if trait == "Iterator" and name == "next" and owner == "ExtractIf":
            old_pending = f"extract_if_pending(*old({receiver}))"
            old_decisions = f"extract_if_decisions(*old({receiver}))"
            selected = f"first_true({old_decisions})"
            return [
                f"{old_decisions}.len() == {old_pending}.len()",
                (
                    f"result == if {selected} < {old_pending}.len() "
                    f"{{ Some({old_pending}[{selected}]) }} else {{ None }}"
                ),
                (
                    f"extract_if_pending(*final({receiver})) == "
                    f"if {selected} < {old_pending}.len() "
                    f"{{ {old_pending}.subrange({selected} + 1, {old_pending}.len() as int) }} "
                    "else { Seq::empty() }"
                ),
                (
                    f"extract_if_set(*final({receiver})) == "
                    f"if {selected} < {old_pending}.len() "
                    f"{{ extract_if_set(*old({receiver})).remove({old_pending}[{selected}]) }} "
                    f"else {{ extract_if_set(*old({receiver})) }}"
                ),
                (
                    f"extract_if_callback_count(*final({receiver})) == "
                    f"extract_if_callback_count(*old({receiver})) + "
                    f"if {selected} < {old_pending}.len() "
                    f"{{ ({selected} + 1) as nat }} else {{ {old_pending}.len() as nat }}"
                ),
                (
                    f"extract_if_predicate_state(*final({receiver})) == "
                    f"retain_callback_state_after("
                    f"extract_if_predicate_state(*old({receiver})), "
                    f"{old_pending}, "
                    f"if {selected} < {old_pending}.len() "
                    f"{{ ({selected} + 1) as nat }} "
                    f"else {{ {old_pending}.len() as nat }})"
                ),
                (
                    f"extract_if_initial_set(*final({receiver})) == "
                    f"extract_if_initial_set(*old({receiver}))"
                ),
                (
                    f"extract_if_yielded(*final({receiver})) == "
                    f"if {selected} < {old_pending}.len() "
                    f"{{ extract_if_yielded(*old({receiver})).push("
                    f"{old_pending}[{selected}]) }} "
                    f"else {{ extract_if_yielded(*old({receiver})) }}"
                ),
                (
                    f"{iterator_remaining_expr(row, f'*final({receiver})')} == "
                    f"if result.is_some() "
                    f"{{ {iterator_remaining_expr(row, f'*old({receiver})')}.drop_first() }} "
                    f"else {{ {iterator_remaining_expr(row, f'*old({receiver})')} }}"
                ),
                f"extract_if_drop_law(*final({receiver}))",
                f"extract_if_panic_law(*final({receiver}))",
            ]
        if trait == "Iterator" and name == "next":
            old_remaining = iterator_remaining_expr(row, f"*old({receiver})")
            final_remaining = iterator_remaining_expr(row, f"*final({receiver})")
            clauses = [
                (
                    f"result == if {old_remaining}.len() > 0 "
                    f"{{ Some({old_remaining}[0]) }} else {{ None }}"
                ),
                (
                    f"{final_remaining} == if {old_remaining}.len() > 0 "
                    f"{{ {old_remaining}.drop_first() }} else {{ {old_remaining} }}"
                ),
            ]
            adapter_step = {
                "Difference": (
                    "difference_source_state",
                    "difference_source_state_law",
                    "difference_next_step",
                ),
                "SymmetricDifference": (
                    "symmetric_difference_source_state",
                    "symmetric_difference_source_state_law",
                    "symmetric_difference_next_step",
                ),
                "Intersection": (
                    "intersection_source_state",
                    "intersection_source_state_law",
                    "intersection_next_step",
                ),
                "Union": (
                    "union_source_state",
                    "union_source_state_law",
                    "union_next_step",
                ),
            }.get(owner)
            if adapter_step is not None:
                state, law, step = adapter_step
                clauses.append(
                    f"{state}(*final({receiver})) == "
                    f"{step}({state}(*old({receiver}))).state"
                )
                clauses.append(
                    f"{law}(*final({receiver}))"
                )
            return clauses
        if trait == "DoubleEndedIterator" and name == "next_back":
            old_remaining = iterator_remaining_expr(row, f"*old({receiver})")
            final_remaining = iterator_remaining_expr(row, f"*final({receiver})")
            return [
                (
                    f"result == if {old_remaining}.len() > 0 "
                    f"{{ Some({old_remaining}.last()) }} else {{ None }}"
                ),
                (
                    f"{final_remaining} == if {old_remaining}.len() > 0 "
                    f"{{ {old_remaining}.drop_last() }} else {{ {old_remaining} }}"
                ),
            ]
        if trait == "Iterator" and name == "size_hint":
            remaining = iterator_remaining_expr(row, f"*{receiver}")
            if owner in {"Iter", "IntoIter"}:
                return [
                    f"result.0 as nat == {remaining}.len()",
                    "result.1 == Some(result.0)",
                ]
            if owner == "Difference":
                lengths = f"difference_hint_lengths({receiver})"
                variant = f"difference_hint_variant({receiver})"
                return [
                    f"0 <= {variant} <= 2",
                    f"{variant} == 2 ==> {lengths}.1 == 0",
                    (
                        f"result.0 as nat == if {lengths}.0 >= {lengths}.1 "
                        f"{{ {lengths}.0 - {lengths}.1 }} else {{ 0 }}"
                    ),
                    (
                        "match result.1 { Some(upper) => "
                        f"upper as nat == {lengths}.0, None => false }}"
                    ),
                    f"result.0 as nat <= {remaining}.len()",
                    (
                        "match result.1 { Some(upper) => "
                        f"{remaining}.len() <= upper as nat, None => false }}"
                    ),
                ]
            if owner == "SymmetricDifference":
                lengths = f"symmetric_difference_hint_lengths({receiver})"
                return [
                    "result.0 == 0",
                    (
                        "match result.1 { Some(upper) => "
                        f"upper as nat == {lengths}.0 + {lengths}.1, None => false }}"
                    ),
                    (
                        "match result.1 { Some(upper) => "
                        f"{remaining}.len() <= upper as nat, None => false }}"
                    ),
                ]
            if owner == "Union":
                lengths = f"union_hint_lengths({receiver})"
                return [
                    (
                        f"result.0 as nat == if {lengths}.0 >= {lengths}.1 "
                        f"{{ {lengths}.0 }} else {{ {lengths}.1 }}"
                    ),
                    (
                        "match result.1 { Some(upper) => "
                        f"upper as nat == {lengths}.0 + {lengths}.1, None => false }}"
                    ),
                    f"result.0 as nat <= {remaining}.len()",
                    (
                        "match result.1 { Some(upper) => "
                        f"{remaining}.len() <= upper as nat, None => false }}"
                    ),
                ]
            if owner == "Intersection":
                variant = f"intersection_hint_variant({receiver})"
                lengths = f"intersection_hint_lengths({receiver})"
                return [
                    f"0 <= {variant} <= 3",
                    (
                        f"result.0 as nat == intersection_hint_lower("
                        f"{variant}, {lengths}.0, {lengths}.1)"
                    ),
                    (
                        "match result.1 { Some(upper) => upper as nat == "
                        f"intersection_hint_upper({variant}, {lengths}.0, {lengths}.1), "
                        "None => false }"
                    ),
                    f"result.0 as nat <= {remaining}.len()",
                    (
                        "match result.1 { Some(upper) => "
                        f"{remaining}.len() <= upper as nat, None => false }}"
                    ),
                ]
            if owner == "ExtractIf":
                bound = f"extract_if_length_bound({receiver})"
                return [
                    "result.0 == 0",
                    (
                        "match result.1 { Some(upper) => "
                        f"upper as nat == {bound}, None => false }}"
                    ),
                    f"{remaining}.len() <= {bound}",
                ]
            raise RuntimeError(f"missing source size-hint formula for {owner}")
        if trait == "Iterator" and name in {"last", "min", "max"}:
            iterator = receiver if receiver_kind == "value" else f"*{receiver}"
            remaining = iterator_remaining_expr(row, iterator)
            selected = f"{remaining}.last()" if name in {"last", "max"} else f"{remaining}[0]"
            return [
                (
                    f"result == if {remaining}.len() > 0 "
                    f"{{ Some({selected}) }} else {{ None }}"
                )
            ]
        if trait == "ExactSizeIterator" and name == "len":
            return [
                f"result as nat == {iterator_remaining_expr(row, f'*{receiver}')}.len()"
            ]
        if trait == "Clone" and name == "clone":
            clauses = [
                (
                    f"{iterator_remaining_expr(row, 'result')} == "
                    f"{iterator_remaining_expr(row, f'*{receiver}')}"
                )
            ]
            adapter_state = {
                "Difference": "difference_source_state",
                "SymmetricDifference": "symmetric_difference_source_state",
                "Intersection": "intersection_source_state",
                "Union": "union_source_state",
            }.get(owner)
            if adapter_state is not None:
                clauses.append(
                    f"{adapter_state}(result) == {adapter_state}(*{receiver})"
                )
            return clauses
        if trait == "Default" and name == "default":
            return [
                f"{iterator_remaining_expr(row, 'result')} == Seq::empty()"
            ]
        if trait == "Debug":
            formatter = _source_argument(inputs, "f", fallback="arg1")
            shape = debug_shape_expression(owner, receiver)
            transition = (
                f"apply_debug_shape(*old({formatter}), {shape})"
            )
            return [
                f"*final({formatter}) == {transition}.0",
                f"result == {transition}.1",
                debug_shape_law_expression(owner, receiver),
            ]

    if owner != "BTreeSet":
        raise RuntimeError(f"unhandled owner in ensures: {owner}")

    sequence_receiver = receiver if receiver_kind == "value" else f"*{receiver}"
    sequence = f"btree_set_sequence({sequence_receiver})" if receiver else ""
    if trait == "Hash":
        state = _source_argument(inputs, "state", fallback="arg1")
        return [
            (
                f"*final({state}) == apply_set_hash(*old({state}), "
                f"{sequence}.len() as nat, {sequence})"
            ),
        ]
    if trait == "PartialEq":
        other = _source_argument(inputs, "other", fallback="arg1")
        return [
            (
                f"result == seq_eq_spec({sequence}, "
                f"btree_set_sequence(*{other}))"
            )
        ]
    if trait == "PartialOrd":
        other = _source_argument(inputs, "other", fallback="arg1")
        return [
            (
                f"result == seq_lex_partial_cmp({sequence}, "
                f"btree_set_sequence(*{other}))"
            )
        ]
    if trait == "Ord":
        other = _source_argument(inputs, "other", fallback="arg1")
        return [
            (
                f"obeys_cmp::<T>() ==> (result == seq_lex_cmp({sequence}, "
                f"btree_set_sequence(*{other})))"
            )
        ]
    if trait == "Clone" and name == "clone_from":
        source = _source_argument(inputs, "source", fallback="arg1")
        source_sequence = f"btree_set_sequence(*{source})"
        return [
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"clone_sequence({source_sequence})"
            ),
            (
                f"clone_sequence_preserves_values({source_sequence}) ==> "
                f"(final({receiver})@ == {source}@)"
            ),
        ]
    if trait == "FromIterator":
        iterator = _source_argument(inputs, "iter", fallback="arg0")
        input_sequence = f"into_iterator_sequence::<T, I>(&{iterator})"
        sorted_sequence = f"stable_sorted_sequence({input_sequence})"
        return [
            f"{sorted_sequence}.len() == {input_sequence}.len()",
            f"{sorted_sequence}.to_multiset() == {input_sequence}.to_multiset()",
            f"nondecreasing_sequence({sorted_sequence})",
            f"stable_tie_order({input_sequence}, {sorted_sequence})",
            (
                f"btree_set_sequence(result) == "
                f"dedup_last_sorted({sorted_sequence})"
            ),
            f"result@ == {input_sequence}.to_set()",
        ]
    if trait == "From":
        array = _source_argument(inputs, "arr", fallback="arg0")
        input_sequence = f"{array}@"
        sorted_sequence = f"stable_sorted_sequence({input_sequence})"
        return [
            f"{sorted_sequence}.len() == {input_sequence}.len()",
            f"{sorted_sequence}.to_multiset() == {input_sequence}.to_multiset()",
            f"nondecreasing_sequence({sorted_sequence})",
            f"stable_tie_order({input_sequence}, {sorted_sequence})",
            (
                f"btree_set_sequence(result) == "
                f"dedup_last_sorted({sorted_sequence})"
            ),
            f"result@ == {input_sequence}.to_set()",
        ]
    if trait == "IntoIterator":
        borrowed = (output or "").startswith("Iter<")
        if borrowed:
            remaining = "iter_remaining(result)"
        else:
            remaining = "into_iter_remaining(result)"
        return [
            f"{remaining}.unref().to_set() == {receiver}@" if borrowed else f"{remaining}.to_set() == {receiver}@",
            f"{remaining}.unref() == {sequence}" if borrowed else f"{remaining} == {sequence}",
            f"increasing_seq({sequence})",
        ]
    if trait == "Extend":
        iterator = _source_argument(inputs, "iter", fallback="arg1")
        iterator_type = next(
            rust_type for name, rust_type, source in inputs if source == "iter"
        )
        if "&'a T" in row.canonical_target:
            input_sequence = (
                f"into_iterator_sequence::<&'a T, {iterator_type}>(&{iterator}).unref()"
            )
        else:
            input_sequence = (
                f"into_iterator_sequence::<T, {iterator_type}>(&{iterator})"
            )
        return [
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"extend_sequence(btree_set_sequence(*old({receiver})), {input_sequence})"
            ),
            (
                f"final({receiver})@ == "
                f"extend_sequence(btree_set_sequence(*old({receiver})), "
                f"{input_sequence}).to_set()"
            ),
            f"increasing_seq(btree_set_sequence(*final({receiver})))",
        ]
    if trait in {"Sub", "BitAnd", "BitOr", "BitXor"}:
        rhs = _source_argument(inputs, "rhs", fallback="arg1")
        left_sequence = sequence
        right_sequence = f"btree_set_sequence(*{rhs})"
        source_result = set_operation_sequence(trait, left_sequence, right_sequence)
        operation = {
            "Sub": f"{receiver}@.difference({rhs}@)",
            "BitAnd": f"{receiver}@.intersect({rhs}@)",
            "BitOr": f"{receiver}@.union({rhs}@)",
            "BitXor": (
                f"{receiver}@.union({rhs}@).difference("
                f"{receiver}@.intersect({rhs}@))"
            ),
        }[trait]
        return [
            (
                f"btree_set_sequence(result) == "
                f"clone_sequence({source_result})"
            ),
            (
                f"clone_sequence_preserves_values({source_result}) ==> "
                f"(result@ == {operation})"
            ),
            f"increasing_seq({source_result})",
        ]
    if trait == "Debug":
        formatter = _source_argument(inputs, "f", fallback="arg1")
        shape = debug_shape_expression(owner, receiver)
        transition = f"apply_debug_shape(*old({formatter}), {shape})"
        return [
            f"*final({formatter}) == {transition}.0",
            f"result == {transition}.1",
            debug_shape_law_expression(owner, receiver),
            f"{sequence}.to_set() == {receiver}@",
            f"increasing_seq({sequence})",
        ]

    if trait != "inherent":
        raise RuntimeError(f"unhandled BTreeSet trait method: {trait}::{name}")

    other = _source_argument(inputs, "other", fallback="arg1")
    value = _source_argument(inputs, "value", fallback="arg1")
    range_value = _source_argument(inputs, "range", fallback="arg1")
    if name == "range":
        selected = f"range_sequence({sequence}, &{range_value})"
        return [
            f"range_bounds_law(&{range_value})",
            f"range_remaining(result).unref() == {selected}",
            f"range_remaining(result).unref().to_set().subset_of({receiver}@)",
            f"increasing_seq(range_remaining(result).unref())",
        ]
    if name in {"difference", "symmetric_difference", "intersection", "union"}:
        right_sequence = f"btree_set_sequence(*{other})"
        source_result = {
            "difference": f"difference_sequence({sequence}, {right_sequence})",
            "symmetric_difference": (
                f"symmetric_difference_sequence({sequence}, {right_sequence})"
            ),
            "intersection": (
                f"intersection_source_sequence({sequence}, {right_sequence})"
            ),
            "union": f"union_sequence({sequence}, {right_sequence})",
        }[name]
        remaining = {
            "difference": "difference_remaining",
            "symmetric_difference": "symmetric_difference_remaining",
            "intersection": "intersection_remaining",
            "union": "union_remaining",
        }[name]
        operation = {
            "difference": f"{receiver}@.difference({other}@)",
            "intersection": f"{receiver}@.intersect({other}@)",
            "union": f"{receiver}@.union({other}@)",
            "symmetric_difference": (
                f"{receiver}@.union({other}@).difference("
                f"{receiver}@.intersect({other}@))"
            ),
        }[name]
        clauses = [
            f"{remaining}(result).unref() == {source_result}",
            f"{remaining}(result).unref().to_set() == {operation}",
            f"increasing_seq({remaining}(result).unref())",
            f"{remaining}(result).no_duplicates()",
        ]
        state_observation, initial_state, state_law = {
            "difference": (
                "difference_source_state",
                "difference_initial_state",
                "difference_source_state_law",
            ),
            "symmetric_difference": (
                "symmetric_difference_source_state",
                "merge_initial_state",
                "symmetric_difference_source_state_law",
            ),
            "intersection": (
                "intersection_source_state",
                "intersection_initial_state",
                "intersection_source_state_law",
            ),
            "union": (
                "union_source_state",
                "merge_initial_state",
                "union_source_state_law",
            ),
        }[name]
        clauses.extend(
            [
                (
                    f"{state_observation}(result) == "
                    f"{initial_state}({sequence}, {right_sequence})"
                ),
                f"{state_law}(result)",
            ]
        )
        return clauses
    if name == "is_disjoint":
        return [f"result == ({receiver}@.intersect({other}@).len() == 0)"]
    if name == "is_subset":
        return [f"result == {receiver}@.subset_of({other}@)"]
    if name == "is_superset":
        return [f"result == {other}@.subset_of({receiver}@)"]
    if name in {"first", "last"}:
        selected = f"{sequence}[0]" if name == "first" else f"{sequence}.last()"
        return [
            f"result.is_some() <==> {sequence}.len() > 0",
            (
                f"match result {{ Some(item) => *item == {selected}, "
                "None => true }"
            ),
        ]
    if name in {"pop_first", "pop_last"}:
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        final_sequence = f"btree_set_sequence(*final({receiver}))"
        selected = f"{old_sequence}[0]" if name == "pop_first" else f"{old_sequence}.last()"
        remainder = (
            f"{old_sequence}.drop_first()"
            if name == "pop_first"
            else f"{old_sequence}.drop_last()"
        )
        return [
            f"result.is_some() <==> {old_sequence}.len() > 0",
            (
                f"result == if {old_sequence}.len() > 0 "
                f"{{ Some({selected}) }} else {{ None }}"
            ),
            (
                f"{final_sequence} == if {old_sequence}.len() > 0 "
                f"{{ {remainder} }} else {{ {old_sequence} }}"
            ),
            (
                f"match result {{ Some(item) => final({receiver})@ == "
                f"old({receiver})@.remove(item), "
                f"None => final({receiver})@ == old({receiver})@ }}"
            ),
        ]
    if name == "replace":
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        return [
            f"result == cmp_equal_representative({old_sequence}, {value})",
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"replace_representative({old_sequence}, {value})"
            ),
            f"final({receiver})@ == old({receiver})@.insert({value})",
        ]
    if name == "take":
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        return [
            f"result == borrowed_representative({old_sequence}, {value})",
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"remove_borrowed_representative({old_sequence}, {value})"
            ),
            (
                "match result { Some(item) => "
                f"sets_borrowed_key_to_key(old({receiver})@, {value}, &item)"
                f" && sets_differ_by_borrowed_key(old({receiver})@, "
                f"final({receiver})@, {value}), "
                f"None => !set_contains_borrowed_key(old({receiver})@, {value})"
                f" && final({receiver})@ == old({receiver})@ }}"
            ),
        ]
    if name == "retain":
        callback = _source_argument(inputs, "f", fallback="arg1")
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        decisions = f"retain_decisions(&{callback}, {old_sequence})"
        effects = f"retain_effect_trace(&{callback}, {old_sequence})"
        return [
            f"{decisions}.len() == {old_sequence}.len()",
            f"{effects}.len() == {old_sequence}.len()",
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"retain_selected({old_sequence}, {decisions})"
            ),
            f"final({receiver})@ == retain_selected({old_sequence}, {decisions}).to_set()",
        ]
    if name == "append":
        left = f"btree_set_sequence(*old({receiver}))"
        right = f"btree_set_sequence(*old({other}))"
        return [
            f"btree_set_sequence(*final({other})) == Seq::empty()",
            f"final({other})@ == Set::empty()",
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"union_sequence({left}, {right})"
            ),
            f"final({receiver})@ == old({receiver})@.union(old({other})@)",
        ]
    if name == "split_off":
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        return [
            (
                f"btree_set_sequence(*final({receiver})) == "
                f"split_before({old_sequence}, {value})"
            ),
            (
                f"btree_set_sequence(result) == "
                f"split_at_or_after({old_sequence}, {value})"
            ),
            f"final({receiver})@.union(result@) == old({receiver})@",
            f"final({receiver})@.intersect(result@).len() == 0",
            f"final({receiver})@.len() + result@.len() == old({receiver})@.len()",
        ]
    if name == "extract_if":
        old_sequence = f"btree_set_sequence(*old({receiver}))"
        pending = f"extract_if_pending(result)"
        decisions = f"extract_if_decisions(result)"
        return [
            f"range_bounds_law(&{range_value})",
            f"final({receiver})@ == old({receiver})@",
            f"extract_if_set(result) == old({receiver})@",
            f"{pending} == range_sequence({old_sequence}, &{range_value})",
            f"{decisions}.len() == {pending}.len()",
            f"extract_if_callback_count(result) == 0",
            f"extract_if_predicate_state(result) == pred",
            (
                f"extract_if_remaining(result) == "
                f"retain_selected({pending}, {decisions})"
            ),
            f"increasing_seq({pending})",
            f"extract_if_initial_set(result) == old({receiver})@",
            f"extract_if_yielded(result) == Seq::empty()",
            "extract_if_drop_law(result)",
            "extract_if_panic_law(result)",
        ]
    raise RuntimeError(f"unhandled inherent method: {name}")


def comparison_law_binding(row: Row) -> str | None:
    if row.disposition != "generated":
        return None
    binder, _inputs, _output, where_clause = proxy_parts(row)
    bound_map: dict[str, set[str]] = {
        item["name"]: {
            bound.strip()
            for bound in item["bounds"].split("+")
            if bound.strip()
        }
        for item in parse_generic_declarations(binder)
    }
    where_text = where_clause.strip()
    if where_text.startswith("where"):
        where_text = where_text[len("where") :].strip()
    for predicate in split_top_level(where_text):
        subject, separator, raw_bounds = predicate.partition(":")
        if not separator:
            continue
        bound_map.setdefault(subject.strip(), set()).update(
            bound.strip()
            for bound in raw_bounds.split("+")
            if bound.strip()
        )

    def has_bound(subject: str, bound: str) -> bool:
        return any(
            candidate == bound or candidate.endswith(f"::{bound}")
            for candidate in bound_map.get(subject, set())
        )

    laws: list[str] = []
    if has_bound("&'a T", "Ord"):
        laws.append("obeys_cmp::<&'a T>()")
    elif has_bound("T", "Ord"):
        laws.append("obeys_cmp::<T>()")
    elif has_bound("T", "PartialOrd"):
        laws.append("T::obeys_partial_cmp_spec()")
    for parameter in ("K", "Q"):
        if has_bound(parameter, "Ord"):
            laws.append(f"{parameter}::obeys_cmp_spec()")
    comparison_bound = any(
        has_bound(subject, bound)
        for subject in bound_map
        for bound in ("Ord", "PartialOrd")
    )
    if comparison_bound:
        if not laws:
            raise RuntimeError(
                f"{row.target_id}: comparison-bound target lacks a law binding"
            )
        return " && ".join(dict.fromkeys(laws))
    return None


def ensure_lines(
    row: Row,
    inputs: list[tuple[str, str, str]],
    output: str | None,
) -> list[str]:
    lines = _ensure_lines_unbound(row, inputs, output)
    comparison_law = comparison_law_binding(row)
    if comparison_law is None:
        return lines
    return [
        f"({comparison_law}) ==> ({line})"
        for line in lines
    ]


def adapter_kind(owner: str) -> int:
    return {
        "Difference": 1,
        "ExtractIf": 2,
        "Intersection": 3,
        "SymmetricDifference": 4,
        "Union": 5,
    }.get(owner, 0)


def trait_code(trait: str) -> int:
    return {"Sub": 1, "BitAnd": 2, "BitOr": 3, "BitXor": 4}[trait]


SHARED_VOCABULARY: Final = r'''// Shared ordered-set vocabulary for Rust 1.96 alloc::collections::btree_set.
extern crate alloc;

use alloc::alloc::Allocator;
use alloc::collections::BTreeSet;
use alloc::collections::btree_set::{
    Difference, ExtractIf, Intersection, IntoIter, Iter, Range, SymmetricDifference, Union,
};
use core::borrow::Borrow;
use core::cmp::Ordering;
use core::fmt::Formatter;
use vstd::prelude::*;
use vstd::laws_cmp::obeys_cmp;
use vstd::std_specs::btree::{
    increasing_seq, set_contains_borrowed_key, sets_borrowed_key_to_key,
    sets_differ_by_borrowed_key, spec_btree_keys_iter,
};
use vstd::std_specs::cmp::{OrdSpec, PartialEqSpec, PartialOrdSpec};
use vstd::std_specs::iter::IteratorSpec;
use vstd::std_specs::range::{RangeBoundsSpec, SpecBound};

verus! {

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoIter<T, A: Allocator + Clone>(IntoIter<T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExRange<'a, T: 'a>(Range<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExDifference<'a, T: 'a, A: Allocator + Clone>(Difference<'a, T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExSymmetricDifference<'a, T: 'a>(SymmetricDifference<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntersection<'a, T: 'a, A: Allocator + Clone>(Intersection<'a, T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExUnion<'a, T: 'a>(Union<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(R)]
#[verifier::reject_recursive_types(F)]
#[verifier::reject_recursive_types(A)]
pub struct ExExtractIf<'a, T, R, F, A: Allocator + Clone>(ExtractIf<'a, T, R, F, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFormatter<'a>(Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFmtError(core::fmt::Error);

#[verifier::prophetic]
pub open spec fn btree_set_sequence<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> Seq<T> {
    spec_btree_keys_iter(&set).remaining().unref()
}

pub uninterp spec fn iter_remaining<'a, T>(iter: Iter<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn into_iter_remaining<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> Seq<T>;
pub uninterp spec fn range_remaining<'a, T>(iter: Range<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn difference_remaining<'a, T, A: Allocator + Clone>(
    iter: Difference<'a, T, A>,
) -> Seq<&'a T>;
pub uninterp spec fn symmetric_difference_remaining<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> Seq<&'a T>;
pub uninterp spec fn intersection_remaining<'a, T, A: Allocator + Clone>(
    iter: Intersection<'a, T, A>,
) -> Seq<&'a T>;
pub uninterp spec fn union_remaining<'a, T>(iter: Union<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn extract_if_remaining<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;

pub broadcast axiom fn axiom_iter_remaining<'a, T>(iter: Iter<'a, T>)
    ensures
        #[trigger] iter_remaining(iter) == IteratorSpec::remaining(&iter),
;

pub open spec fn seq_eq_spec<T: PartialEq>(left: Seq<T>, right: Seq<T>) -> bool
    decreases left.len() + right.len()
{
    if left.len() == 0 || right.len() == 0 {
        left.len() == right.len()
    } else {
        left[0].eq_spec(&right[0])
            && seq_eq_spec(left.drop_first(), right.drop_first())
    }
}

pub open spec fn seq_lex_partial_cmp<T: PartialOrd>(
    left: Seq<T>,
    right: Seq<T>,
) -> Option<Ordering>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        if right.len() == 0 { Some(Ordering::Equal) } else { Some(Ordering::Less) }
    } else if right.len() == 0 {
        Some(Ordering::Greater)
    } else {
        match left[0].partial_cmp_spec(&right[0]) {
            Some(Ordering::Equal) => seq_lex_partial_cmp(left.drop_first(), right.drop_first()),
            answer => answer,
        }
    }
}

pub open spec fn seq_lex_cmp<T: Ord>(left: Seq<T>, right: Seq<T>) -> Ordering
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        if right.len() == 0 { Ordering::Equal } else { Ordering::Less }
    } else if right.len() == 0 {
        Ordering::Greater
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Equal => seq_lex_cmp(left.drop_first(), right.drop_first()),
            answer => answer,
        }
    }
}

pub open spec fn seq_contains_cmp<T: Ord>(items: Seq<T>, value: T) -> bool
    decreases items.len()
{
    items.len() > 0
        && (items[0].cmp_spec(&value) == Ordering::Equal
            || seq_contains_cmp(items.drop_first(), value))
}

pub open spec fn difference_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T>
    decreases left.len()
{
    if left.len() == 0 {
        Seq::empty()
    } else if seq_contains_cmp(right, left[0]) {
        difference_sequence(left.drop_first(), right)
    } else {
        seq![left[0]] + difference_sequence(left.drop_first(), right)
    }
}

pub open spec fn intersection_from_first<T: Ord>(
    first: Seq<T>,
    second: Seq<T>,
) -> Seq<T>
    decreases first.len()
{
    if first.len() == 0 {
        Seq::empty()
    } else if seq_contains_cmp(second, first[0]) {
        seq![first[0]] + intersection_from_first(first.drop_first(), second)
    } else {
        intersection_from_first(first.drop_first(), second)
    }
}

pub open spec fn intersection_source_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T> {
    if left.len() == 0 || right.len() == 0 {
        Seq::empty()
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        Seq::empty()
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        seq![left[0]]
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        seq![left.last()]
    } else if left.len() <= right.len() / 16 {
        intersection_from_first(left, right)
    } else if right.len() <= left.len() / 16 {
        intersection_from_first(right, left)
    } else {
        intersection_from_first(left, right)
    }
}

pub open spec fn union_sequence<T: Ord>(left: Seq<T>, right: Seq<T>) -> Seq<T>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less =>
                seq![left[0]] + union_sequence(left.drop_first(), right),
            Ordering::Greater =>
                seq![right[0]] + union_sequence(left, right.drop_first()),
            Ordering::Equal =>
                seq![left[0]] + union_sequence(left.drop_first(), right.drop_first()),
        }
    }
}

pub open spec fn symmetric_difference_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less =>
                seq![left[0]] + symmetric_difference_sequence(left.drop_first(), right),
            Ordering::Greater =>
                seq![right[0]] + symmetric_difference_sequence(left, right.drop_first()),
            Ordering::Equal =>
                symmetric_difference_sequence(left.drop_first(), right.drop_first()),
        }
    }
}

pub open spec fn cmp_equal_representative<T: Ord>(
    items: Seq<T>,
    value: T,
) -> Option<T>
    decreases items.len()
{
    if items.len() == 0 {
        None
    } else if items[0].cmp_spec(&value) == Ordering::Equal {
        Some(items[0])
    } else {
        cmp_equal_representative(items.drop_first(), value)
    }
}

pub open spec fn insert_keep_existing<T: Ord>(items: Seq<T>, value: T) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else {
        match value.cmp_spec(&items[0]) {
            Ordering::Less => seq![value] + items,
            Ordering::Equal => items,
            Ordering::Greater =>
                seq![items[0]] + insert_keep_existing(items.drop_first(), value),
        }
    }
}

pub open spec fn replace_representative<T: Ord>(items: Seq<T>, value: T) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else {
        match value.cmp_spec(&items[0]) {
            Ordering::Less => seq![value] + items,
            Ordering::Equal => seq![value] + items.drop_first(),
            Ordering::Greater =>
                seq![items[0]] + replace_representative(items.drop_first(), value),
        }
    }
}

pub open spec fn extend_sequence<T: Ord>(items: Seq<T>, input: Seq<T>) -> Seq<T>
    decreases input.len()
{
    if input.len() == 0 {
        items
    } else {
        extend_sequence(insert_keep_existing(items, input[0]), input.drop_first())
    }
}

pub open spec fn dedup_last_sorted<T: Ord>(items: Seq<T>) -> Seq<T>
    decreases items.len()
{
    if items.len() <= 1 {
        items
    } else if items[0].cmp_spec(&items[1]) == Ordering::Equal {
        dedup_last_sorted(items.drop_first())
    } else {
        seq![items[0]] + dedup_last_sorted(items.drop_first())
    }
}

pub open spec fn nondecreasing_sequence<T: Ord>(items: Seq<T>) -> bool
    decreases items.len()
{
    items.len() <= 1
        || (items[0].cmp_spec(&items[1]) != Ordering::Greater
            && nondecreasing_sequence(items.drop_first()))
}

pub uninterp spec fn into_iterator_sequence<T, I>(iter: &I) -> Seq<T>;
pub uninterp spec fn stable_sorted_sequence<T: Ord>(input: Seq<T>) -> Seq<T>;

pub open spec fn last_cmp_equal_input<T: Ord>(
    input: Seq<T>,
    value: T,
) -> Option<T>
    decreases input.len()
{
    if input.len() == 0 {
        None
    } else {
        let later = last_cmp_equal_input(input.drop_first(), value);
        if later.is_some() {
            later
        } else if input[0].cmp_spec(&value) == Ordering::Equal {
            Some(input[0])
        } else {
            None
        }
    }
}

pub open spec fn stable_tie_order<T: Ord>(
    input: Seq<T>,
    sorted: Seq<T>,
) -> bool {
    let representatives = dedup_last_sorted(sorted);
    forall |index: int|
        0 <= index < representatives.len()
        ==> #[trigger] last_cmp_equal_input(input, representatives[index])
            == Some(representatives[index])
}
pub uninterp spec fn clone_value<T: Clone>(value: T) -> T;

pub open spec fn clone_sequence<T: Clone>(items: Seq<T>) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        seq![clone_value(items[0])] + clone_sequence(items.drop_first())
    }
}

pub open spec fn clone_sequence_preserves_values<T: Clone>(items: Seq<T>) -> bool
    decreases items.len()
{
    items.len() == 0
        || (clone_value(items[0]) == items[0]
            && clone_sequence_preserves_values(items.drop_first()))
}

pub uninterp spec fn borrowed_key_projection<
    'a,
    T: Borrow<K>,
    K: ?Sized,
>(
    item: &'a T,
) -> &'a K;

#[verifier::external_body]
pub fn borrowed_key_projection_exec<
    'a,
    T: Borrow<K>,
    K: ?Sized,
>(
    item: &'a T,
) -> (result: &'a K)
    ensures
        result == borrowed_key_projection(item),
{
    item.borrow()
}

pub open spec fn borrowed_key_order<T: Borrow<K>, K: ?Sized + Ord>(
    item: &T,
    key: &K,
) -> Ordering {
    borrowed_key_projection(item).cmp_spec(key)
}

pub open spec fn borrowed_key_order_law<
    T: Borrow<K>,
    K: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &K,
) -> bool {
    &&& forall |index: int| 0 <= index < items.len() ==>
        (#[trigger] borrowed_key_order(&items[index], key) == Ordering::Equal
            <==> sets_borrowed_key_to_key(
                items.to_set(),
                key,
                &items[index],
            ))
    &&& forall |left: int, right: int|
        #![trigger borrowed_key_order(&items[left], key),
            borrowed_key_order(&items[right], key)]
        0 <= left < right < items.len()
        && borrowed_key_order(&items[left], key) == Ordering::Greater
        ==> borrowed_key_order(&items[right], key) == Ordering::Greater
    &&& forall |left: int, right: int|
        #![trigger borrowed_key_order(&items[left], key),
            borrowed_key_order(&items[right], key)]
        0 <= left < right < items.len()
        && borrowed_key_order(&items[right], key) == Ordering::Less
        ==> borrowed_key_order(&items[left], key) == Ordering::Less
}

pub open spec fn range_bound_order<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> Option<Ordering> {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Included(start), SpecBound::Included(end))
        | (SpecBound::Included(start), SpecBound::Excluded(end))
        | (SpecBound::Excluded(start), SpecBound::Included(end))
        | (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            Some(start.cmp_spec(end))
        }
        _ => None,
    }
}

pub open spec fn range_bounds_law<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    range_bound_order(range).is_none() <==> (
        range.spec_start_bound() matches SpecBound::Unbounded
        || range.spec_end_bound() matches SpecBound::Unbounded
    )
}

pub open spec fn range_start_after_end<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    range_bound_order(range) == Some(Ordering::Greater)
}

pub open spec fn range_equal_excluded<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Equal
        }
        _ => false,
    }
}

pub open spec fn range_contains<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    item: &T,
    range: &R,
) -> bool {
    let starts_after = match range.spec_start_bound() {
        SpecBound::Unbounded => true,
        SpecBound::Included(start) => {
            borrowed_key_order(item, start) != Ordering::Less
        }
        SpecBound::Excluded(start) => {
            borrowed_key_order(item, start) == Ordering::Greater
        }
    };
    let ends_before = match range.spec_end_bound() {
        SpecBound::Unbounded => true,
        SpecBound::Included(end) => {
            borrowed_key_order(item, end) != Ordering::Greater
        }
        SpecBound::Excluded(end) => {
            borrowed_key_order(item, end) == Ordering::Less
        }
    };
    starts_after && ends_before
}

pub open spec fn range_order_law<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    items: Seq<T>,
    range: &R,
) -> bool {
    &&& range_bounds_law(range)
    &&& match range.spec_start_bound() {
        SpecBound::Included(start) | SpecBound::Excluded(start) => {
            borrowed_key_order_law(items, start)
        }
        SpecBound::Unbounded => true,
    }
    &&& match range.spec_end_bound() {
        SpecBound::Included(end) | SpecBound::Excluded(end) => {
            borrowed_key_order_law(items, end)
        }
        SpecBound::Unbounded => true,
    }
}

pub open spec fn range_sequence<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    items: Seq<T>,
    range: &R,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if range_contains(&items[0], range) {
        seq![items[0]] + range_sequence(items.drop_first(), range)
    } else {
        range_sequence(items.drop_first(), range)
    }
}

pub open spec fn borrowed_representative<
    T: Borrow<Q>,
    Q: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &Q,
) -> Option<T>
    decreases items.len()
{
    if items.len() == 0 {
        None
    } else if borrowed_key_order(&items[0], key) == Ordering::Equal {
        Some(items[0])
    } else {
        borrowed_representative(items.drop_first(), key)
    }
}

pub open spec fn remove_borrowed_representative<
    T: Borrow<Q>,
    Q: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Equal {
        items.drop_first()
    } else {
        seq![items[0]] + remove_borrowed_representative(items.drop_first(), key)
    }
}

pub open spec fn split_before<T: Borrow<Q>, Q: ?Sized + Ord>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Less {
        seq![items[0]] + split_before(items.drop_first(), key)
    } else {
        Seq::empty()
    }
}

pub open spec fn split_at_or_after<T: Borrow<Q>, Q: ?Sized + Ord>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Less {
        split_at_or_after(items.drop_first(), key)
    } else {
        items
    }
}

pub open spec fn fn_mut_result<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
) -> bool
    recommends
        state.requires((item,)),
        exists |result: bool| state.ensures((item,), result),
{
    choose |result: bool| state.ensures((item,), result)
}

pub uninterp spec fn fn_mut_post_state<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
    result: bool,
) -> F;

#[verifier::prophetic]
pub open spec fn fn_mut_step_law<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
) -> bool {
    let result = fn_mut_result(state, item);
    let post = fn_mut_post_state(state, item, result);
    &&& state.requires((item,))
    &&& state.ensures((item,), result)
    &&& exists |callback: &mut F|
        #[trigger] call_ensures::<(&T,), &mut F>(
            callback,
            (item,),
            result,
        )
        && call_requires::<(&T,), &mut F>(callback, (item,))
        && mut_ref_current(callback) == state
        && mut_ref_future(callback) == post
}

pub open spec fn retain_decisions_from<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> Seq<bool>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        let keep = fn_mut_result(state, &items[0]);
        seq![keep]
            + retain_decisions_from(
                fn_mut_post_state(state, &items[0], keep),
                items.drop_first(),
            )
    }
}

pub open spec fn retain_effect_trace_from<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> Seq<F>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        let keep = fn_mut_result(state, &items[0]);
        let next = fn_mut_post_state(state, &items[0], keep);
        seq![next]
            + retain_effect_trace_from(
                next,
                items.drop_first(),
            )
    }
}

pub open spec fn retain_callback_state_after<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
    count: nat,
) -> F
    decreases count
{
    if count == 0 || items.len() == 0 {
        state
    } else {
        let keep = fn_mut_result(state, &items[0]);
        retain_callback_state_after(
            fn_mut_post_state(state, &items[0], keep),
            items.drop_first(),
            (count - 1) as nat,
        )
    }
}

#[verifier::prophetic]
pub open spec fn retain_callback_trace_law<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> bool
    decreases items.len()
{
    if items.len() == 0 {
        true
    } else {
        let keep = fn_mut_result(state, &items[0]);
        &&& fn_mut_step_law(state, &items[0])
        &&& retain_callback_trace_law(
            fn_mut_post_state(state, &items[0], keep),
            items.drop_first(),
        )
    }
}

pub open spec fn retain_decisions<T, F: FnMut(&T) -> bool>(
    callback: &F,
    items: Seq<T>,
) -> Seq<bool> {
    retain_decisions_from(*callback, items)
}

pub open spec fn retain_effect_trace<T, F: FnMut(&T) -> bool>(
    callback: &F,
    items: Seq<T>,
) -> Seq<F> {
    retain_effect_trace_from(*callback, items)
}

pub open spec fn retain_selected<T>(items: Seq<T>, decisions: Seq<bool>) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 || decisions.len() == 0 {
        Seq::empty()
    } else if decisions[0] {
        seq![items[0]] + retain_selected(items.drop_first(), decisions.drop_first())
    } else {
        retain_selected(items.drop_first(), decisions.drop_first())
    }
}

pub ghost struct SetAdapterState<T> {
    pub variant: int,
    pub first: Seq<T>,
    pub second: Seq<T>,
    pub lookup: Seq<T>,
    pub answer: Option<T>,
    pub peeked_side: int,
    pub peeked: Option<T>,
}

pub ghost struct AdapterStep<T> {
    pub returned: Option<T>,
    pub state: SetAdapterState<T>,
}

pub ghost struct MergeStep<T> {
    pub left: Option<T>,
    pub right: Option<T>,
    pub state: SetAdapterState<T>,
}

pub open spec fn adapter_state<T>(
    variant: int,
    first: Seq<T>,
    second: Seq<T>,
    lookup: Seq<T>,
    answer: Option<T>,
    peeked_side: int,
    peeked: Option<T>,
) -> SetAdapterState<T> {
    SetAdapterState {
        variant,
        first,
        second,
        lookup,
        answer,
        peeked_side,
        peeked,
    }
}

pub open spec fn optional_sequence<T>(item: Option<T>) -> Seq<T> {
    match item {
        Some(value) => seq![value],
        None => Seq::empty(),
    }
}

pub open spec fn difference_state_remaining<T: Ord>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.variant == 0 {
        difference_sequence(state.first, state.second)
    } else if state.variant == 1 {
        difference_sequence(state.first, state.lookup)
    } else {
        state.first
    }
}

pub open spec fn intersection_state_remaining<T: Ord>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.variant == 0 {
        intersection_from_first(state.first, state.second)
    } else if state.variant == 1 {
        intersection_from_first(state.first, state.lookup)
    } else {
        optional_sequence(state.answer)
    }
}

pub open spec fn merge_left_remaining<T>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.peeked_side == 1 {
        optional_sequence(state.peeked) + state.first
    } else {
        state.first
    }
}

pub open spec fn merge_right_remaining<T>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.peeked_side == 2 {
        optional_sequence(state.peeked) + state.second
    } else {
        state.second
    }
}

pub open spec fn difference_initial_state<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    if left.len() == 0 || right.len() == 0 {
        adapter_state(
            2, left, Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        adapter_state(
            2, left, Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        adapter_state(
            2,
            left.drop_first(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        adapter_state(
            2,
            left.drop_last(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else {
        adapter_state(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn intersection_initial_state<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    if left.len() == 0 || right.len() == 0 {
        adapter_state(
            2, Seq::empty(), Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        adapter_state(
            2, Seq::empty(), Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        adapter_state(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left[0]),
            0,
            None,
        )
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        adapter_state(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left.last()),
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else if right.len() <= left.len() / 16 {
        adapter_state(
            1, right, Seq::empty(), left, None, 0, None,
        )
    } else {
        adapter_state(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn merge_initial_state<T>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    adapter_state(
        0, left, right, Seq::empty(), None, 0, None,
    )
}

pub open spec fn difference_stitch_step<T: Ord>(
    current: T,
    first: Seq<T>,
    second: Seq<T>,
) -> AdapterStep<T>
    decreases first.len() + second.len()
{
    if second.len() == 0 {
        AdapterStep {
            returned: Some(current),
            state: adapter_state(
                0, first, second, Seq::empty(), None, 0, None,
            ),
        }
    } else {
        match current.cmp_spec(&second[0]) {
            Ordering::Less => AdapterStep {
                returned: Some(current),
                state: adapter_state(
                    0, first, second, Seq::empty(), None, 0, None,
                ),
            },
            Ordering::Equal => {
                if first.len() == 0 {
                    AdapterStep {
                        returned: None,
                        state: adapter_state(
                            0,
                            Seq::empty(),
                            second,
                            Seq::empty(),
                            None,
                            0,
                            None,
                        ),
                    }
                } else {
                    difference_stitch_step(
                        first[0],
                        first.drop_first(),
                        second.drop_first(),
                    )
                }
            }
            Ordering::Greater => {
                difference_stitch_step(
                    current,
                    first,
                    second.drop_first(),
                )
            }
        }
    }
}

pub open spec fn difference_search_step<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
) -> AdapterStep<T>
    decreases first.len()
{
    if first.len() == 0 {
        AdapterStep {
            returned: None,
            state: adapter_state(
                1, first, Seq::empty(), lookup, None, 0, None,
            ),
        }
    } else if seq_contains_cmp(lookup, first[0]) {
        difference_search_step(first.drop_first(), lookup)
    } else {
        AdapterStep {
            returned: Some(first[0]),
            state: adapter_state(
                1,
                first.drop_first(),
                Seq::empty(),
                lookup,
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn difference_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    if state.variant == 0 {
        if state.first.len() == 0 {
            AdapterStep { returned: None, state }
        } else {
            difference_stitch_step(
                state.first[0],
                state.first.drop_first(),
                state.second,
            )
        }
    } else if state.variant == 1 {
        difference_search_step(state.first, state.lookup)
    } else if state.first.len() == 0 {
        AdapterStep { returned: None, state }
    } else {
        AdapterStep {
            returned: Some(state.first[0]),
            state: adapter_state(
                2,
                state.first.drop_first(),
                Seq::empty(),
                Seq::empty(),
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn intersection_stitch_scan<T: Ord>(
    a: T,
    a_tail: Seq<T>,
    b: T,
    b_tail: Seq<T>,
) -> AdapterStep<T>
    decreases a_tail.len() + b_tail.len()
{
    match a.cmp_spec(&b) {
        Ordering::Equal => AdapterStep {
            returned: Some(a),
            state: adapter_state(
                0, a_tail, b_tail, Seq::empty(), None, 0, None,
            ),
        },
        Ordering::Less => {
            if a_tail.len() == 0 {
                AdapterStep {
                    returned: None,
                    state: adapter_state(
                        0,
                        Seq::empty(),
                        b_tail,
                        Seq::empty(),
                        None,
                        0,
                        None,
                    ),
                }
            } else {
                intersection_stitch_scan(
                    a_tail[0],
                    a_tail.drop_first(),
                    b,
                    b_tail,
                )
            }
        }
        Ordering::Greater => {
            if b_tail.len() == 0 {
                AdapterStep {
                    returned: None,
                    state: adapter_state(
                        0,
                        a_tail,
                        Seq::empty(),
                        Seq::empty(),
                        None,
                        0,
                        None,
                    ),
                }
            } else {
                intersection_stitch_scan(
                    a,
                    a_tail,
                    b_tail[0],
                    b_tail.drop_first(),
                )
            }
        }
    }
}

pub open spec fn intersection_search_step<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
) -> AdapterStep<T>
    decreases first.len()
{
    if first.len() == 0 {
        AdapterStep {
            returned: None,
            state: adapter_state(
                1, first, Seq::empty(), lookup, None, 0, None,
            ),
        }
    } else if seq_contains_cmp(lookup, first[0]) {
        AdapterStep {
            returned: Some(first[0]),
            state: adapter_state(
                1,
                first.drop_first(),
                Seq::empty(),
                lookup,
                None,
                0,
                None,
            ),
        }
    } else {
        intersection_search_step(first.drop_first(), lookup)
    }
}

pub open spec fn intersection_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    if state.variant == 0 {
        if state.first.len() == 0 {
            AdapterStep { returned: None, state }
        } else if state.second.len() == 0 {
            AdapterStep {
                returned: None,
                state: adapter_state(
                    0,
                    state.first.drop_first(),
                    Seq::empty(),
                    Seq::empty(),
                    None,
                    0,
                    None,
                ),
            }
        } else {
            intersection_stitch_scan(
                state.first[0],
                state.first.drop_first(),
                state.second[0],
                state.second.drop_first(),
            )
        }
    } else if state.variant == 1 {
        intersection_search_step(state.first, state.lookup)
    } else {
        AdapterStep {
            returned: state.answer,
            state: adapter_state(
                2,
                Seq::empty(),
                Seq::empty(),
                Seq::empty(),
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn merge_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> MergeStep<T> {
    let left = merge_left_remaining(state);
    let right = merge_right_remaining(state);
    if left.len() == 0 {
        if right.len() == 0 {
            MergeStep {
                left: None,
                right: None,
                state: merge_initial_state(left, right),
            }
        } else {
            MergeStep {
                left: None,
                right: Some(right[0]),
                state: merge_initial_state(left, right.drop_first()),
            }
        }
    } else if right.len() == 0 {
        MergeStep {
            left: Some(left[0]),
            right: None,
            state: merge_initial_state(left.drop_first(), right),
        }
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less => MergeStep {
                left: Some(left[0]),
                right: None,
                state: adapter_state(
                    0,
                    left.drop_first(),
                    right.drop_first(),
                    Seq::empty(),
                    None,
                    2,
                    Some(right[0]),
                ),
            },
            Ordering::Greater => MergeStep {
                left: None,
                right: Some(right[0]),
                state: adapter_state(
                    0,
                    left.drop_first(),
                    right.drop_first(),
                    Seq::empty(),
                    None,
                    1,
                    Some(left[0]),
                ),
            },
            Ordering::Equal => MergeStep {
                left: Some(left[0]),
                right: Some(right[0]),
                state: merge_initial_state(
                    left.drop_first(),
                    right.drop_first(),
                ),
            },
        }
    }
}

pub open spec fn union_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    let step = merge_next_step(state);
    AdapterStep {
        returned: if step.left.is_some() { step.left } else { step.right },
        state: step.state,
    }
}

pub open spec fn symmetric_difference_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T>
    decreases merge_left_remaining(state).len()
        + merge_right_remaining(state).len()
{
    let step = merge_next_step(state);
    if step.left.is_some() && step.right.is_some() {
        symmetric_difference_next_step(step.state)
    } else {
        AdapterStep {
            returned: if step.left.is_some() { step.left } else { step.right },
            state: step.state,
        }
    }
}

pub uninterp spec fn difference_source_state<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> SetAdapterState<T>;

pub uninterp spec fn symmetric_difference_source_state<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> SetAdapterState<T>;

pub uninterp spec fn intersection_source_state<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> SetAdapterState<T>;

pub uninterp spec fn union_source_state<'a, T>(
    iter: Union<'a, T>,
) -> SetAdapterState<T>;

pub open spec fn difference_source_state_law<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> bool {
    let state = difference_source_state(iter);
    &&& 0 <= state.variant <= 2
    &&& state.peeked_side == 0
    &&& state.peeked.is_none()
    &&& difference_remaining(iter).unref()
        == difference_state_remaining(state)
}

pub open spec fn symmetric_difference_source_state_law<'a, T: Ord>(
    iter: SymmetricDifference<'a, T>,
) -> bool {
    let state = symmetric_difference_source_state(iter);
    &&& state.variant == 0
    &&& 0 <= state.peeked_side <= 2
    &&& (state.peeked_side == 0 <==> state.peeked.is_none())
    &&& symmetric_difference_remaining(iter).unref()
        == symmetric_difference_sequence(
            merge_left_remaining(state),
            merge_right_remaining(state),
        )
}

pub open spec fn intersection_source_state_law<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> bool {
    let state = intersection_source_state(iter);
    &&& 0 <= state.variant <= 3
    &&& state.peeked_side == 0
    &&& state.peeked.is_none()
    &&& (state.variant == 2 ==> state.answer.is_none())
    &&& (state.variant == 3 ==> state.answer.is_some())
    &&& intersection_remaining(iter).unref()
        == intersection_state_remaining(state)
}

pub open spec fn union_source_state_law<'a, T: Ord>(
    iter: Union<'a, T>,
) -> bool {
    let state = union_source_state(iter);
    &&& state.variant == 0
    &&& 0 <= state.peeked_side <= 2
    &&& (state.peeked_side == 0 <==> state.peeked.is_none())
    &&& union_remaining(iter).unref()
        == union_sequence(
            merge_left_remaining(state),
            merge_right_remaining(state),
        )
}

pub ghost struct AdapterDebugShape<T> {
    pub source_tag: int,
    pub variant: int,
    pub structure: Seq<int>,
    pub primary: Seq<T>,
    pub secondary: Seq<T>,
    pub tertiary: Seq<T>,
    pub non_exhaustive: bool,
}

#[verifier::prophetic]
pub open spec fn btree_set_debug_shape<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> AdapterDebugShape<T> {
    AdapterDebugShape {
        source_tag: 9,
        variant: 0,
        structure: seq![1],
        primary: btree_set_sequence(set),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}

#[verifier::prophetic]
pub open spec fn btree_set_debug_shape_law<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> bool {
    &&& btree_set_debug_shape(set).source_tag == 9
    &&& btree_set_debug_shape(set).variant == 0
    &&& btree_set_debug_shape(set).structure == seq![1]
    &&& btree_set_debug_shape(set).primary == btree_set_sequence(set)
    &&& btree_set_debug_shape(set).secondary == Seq::empty()
    &&& btree_set_debug_shape(set).tertiary == Seq::empty()
    &&& !btree_set_debug_shape(set).non_exhaustive
}

// Structure codes name the exact source builders/fields:
// 1 debug_set, 2 debug_tuple, 3 debug_struct, 4 debug_list,
// 101 Iter, 102 IntoIter, 103 Range, 104 Difference,
// 105 SymmetricDifference, 106 Intersection, 107 Union,
// 108 ExtractIf, 109 MergeIterInner, 110 Stitch, 111 Search,
// 112 Iterate, 113 Answer, 201 iter, 202 self_iter, 203 other_iter,
// 204 a, 205 b, 206 small_iter, 207 large_set, 208 peek.
pub open spec fn iter_debug_shape<'a, T>(
    iter: Iter<'a, T>,
) -> AdapterDebugShape<&'a T> {
    AdapterDebugShape {
        source_tag: 1,
        variant: 0,
        structure: seq![2, 101, 4],
        primary: iter_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn iter_debug_shape_law<'a, T>(iter: Iter<'a, T>) -> bool {
    &&& iter_debug_shape(iter).source_tag == 1
    &&& iter_debug_shape(iter).variant == 0
    &&& iter_debug_shape(iter).structure == seq![2, 101, 4]
    &&& iter_debug_shape(iter).primary == iter_remaining(iter)
    &&& iter_debug_shape(iter).secondary == Seq::empty()
    &&& iter_debug_shape(iter).tertiary == Seq::empty()
    &&& !iter_debug_shape(iter).non_exhaustive
}

pub open spec fn into_iter_debug_shape<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> AdapterDebugShape<T> {
    AdapterDebugShape {
        source_tag: 2,
        variant: 0,
        structure: seq![3, 102, 201, 4],
        primary: into_iter_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn into_iter_debug_shape_law<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> bool {
    &&& into_iter_debug_shape(iter).source_tag == 2
    &&& into_iter_debug_shape(iter).variant == 0
    &&& into_iter_debug_shape(iter).structure == seq![3, 102, 201, 4]
    &&& into_iter_debug_shape(iter).primary == into_iter_remaining(iter)
    &&& into_iter_debug_shape(iter).secondary == Seq::empty()
    &&& into_iter_debug_shape(iter).tertiary == Seq::empty()
    &&& !into_iter_debug_shape(iter).non_exhaustive
}

pub open spec fn range_debug_shape<'a, T>(
    iter: Range<'a, T>,
) -> AdapterDebugShape<&'a T> {
    AdapterDebugShape {
        source_tag: 3,
        variant: 0,
        structure: seq![3, 103, 201, 4],
        primary: range_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn range_debug_shape_law<'a, T>(iter: Range<'a, T>) -> bool {
    &&& range_debug_shape(iter).source_tag == 3
    &&& range_debug_shape(iter).variant == 0
    &&& range_debug_shape(iter).structure == seq![3, 103, 201, 4]
    &&& range_debug_shape(iter).primary == range_remaining(iter)
    &&& range_debug_shape(iter).secondary == Seq::empty()
    &&& range_debug_shape(iter).tertiary == Seq::empty()
    &&& !range_debug_shape(iter).non_exhaustive
}

pub open spec fn difference_debug_shape<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> AdapterDebugShape<T> {
    let state = difference_source_state(iter);
    AdapterDebugShape {
        source_tag: 4,
        variant: state.variant,
        structure: if state.variant == 0 {
            seq![2, 104, 3, 110, 202, 203]
        } else if state.variant == 1 {
            seq![2, 104, 3, 111, 202, 203]
        } else {
            seq![2, 104, 2, 112]
        },
        primary: state.first,
        secondary: if state.variant == 0 {
            state.second
        } else if state.variant == 1 {
            state.lookup
        } else {
            Seq::empty()
        },
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn difference_debug_shape_law<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> bool {
    let state = difference_source_state(iter);
    &&& 0 <= state.variant <= 2
    &&& difference_debug_shape(iter).source_tag == 4
    &&& difference_debug_shape(iter).variant == state.variant
    &&& difference_debug_shape(iter).primary == state.first
    &&& difference_debug_shape(iter).secondary == if state.variant == 0 {
        state.second
    } else if state.variant == 1 {
        state.lookup
    } else {
        Seq::empty()
    }
    &&& difference_debug_shape(iter).tertiary == Seq::empty()
    &&& !difference_debug_shape(iter).non_exhaustive
}

pub open spec fn symmetric_difference_debug_shape<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> AdapterDebugShape<T> {
    let state = symmetric_difference_source_state(iter);
    AdapterDebugShape {
        source_tag: 5,
        variant: state.peeked_side,
        structure: seq![2, 105, 2, 109, 204, 205, 208],
        primary: state.first,
        secondary: state.second,
        tertiary: optional_sequence(state.peeked),
        non_exhaustive: false,
    }
}
pub open spec fn symmetric_difference_debug_shape_law<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> bool {
    let state = symmetric_difference_source_state(iter);
    &&& 0 <= state.peeked_side <= 2
    &&& symmetric_difference_debug_shape(iter).source_tag == 5
    &&& symmetric_difference_debug_shape(iter).variant == state.peeked_side
    &&& symmetric_difference_debug_shape(iter).primary == state.first
    &&& symmetric_difference_debug_shape(iter).secondary == state.second
    &&& symmetric_difference_debug_shape(iter).tertiary
        == optional_sequence(state.peeked)
    &&& !symmetric_difference_debug_shape(iter).non_exhaustive
}

pub open spec fn intersection_debug_shape<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> AdapterDebugShape<T> {
    let state = intersection_source_state(iter);
    AdapterDebugShape {
        source_tag: 6,
        variant: state.variant,
        structure: if state.variant == 0 {
            seq![2, 106, 3, 110, 204, 205]
        } else if state.variant == 1 {
            seq![2, 106, 3, 111, 206, 207]
        } else {
            seq![2, 106, 2, 113]
        },
        primary: state.first,
        secondary: if state.variant == 0 {
            state.second
        } else if state.variant == 1 {
            state.lookup
        } else {
            optional_sequence(state.answer)
        },
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn intersection_debug_shape_law<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> bool {
    let state = intersection_source_state(iter);
    &&& 0 <= state.variant <= 3
    &&& intersection_debug_shape(iter).source_tag == 6
    &&& intersection_debug_shape(iter).variant == state.variant
    &&& intersection_debug_shape(iter).primary == state.first
    &&& intersection_debug_shape(iter).secondary == if state.variant == 0 {
        state.second
    } else if state.variant == 1 {
        state.lookup
    } else {
        optional_sequence(state.answer)
    }
    &&& intersection_debug_shape(iter).tertiary == Seq::empty()
    &&& !intersection_debug_shape(iter).non_exhaustive
}

pub open spec fn union_debug_shape<'a, T>(
    iter: Union<'a, T>,
) -> AdapterDebugShape<T> {
    let state = union_source_state(iter);
    AdapterDebugShape {
        source_tag: 7,
        variant: state.peeked_side,
        structure: seq![2, 107, 2, 109, 204, 205, 208],
        primary: state.first,
        secondary: state.second,
        tertiary: optional_sequence(state.peeked),
        non_exhaustive: false,
    }
}
pub open spec fn union_debug_shape_law<'a, T>(iter: Union<'a, T>) -> bool {
    let state = union_source_state(iter);
    &&& 0 <= state.peeked_side <= 2
    &&& union_debug_shape(iter).source_tag == 7
    &&& union_debug_shape(iter).variant == state.peeked_side
    &&& union_debug_shape(iter).primary == state.first
    &&& union_debug_shape(iter).secondary == state.second
    &&& union_debug_shape(iter).tertiary == optional_sequence(state.peeked)
    &&& !union_debug_shape(iter).non_exhaustive
}

pub open spec fn extract_if_debug_shape<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> AdapterDebugShape<T> {
    let pending = extract_if_pending(iter);
    AdapterDebugShape {
        source_tag: 8,
        variant: 0,
        structure: seq![3, 108, 208],
        primary: if pending.len() > 0 {
            seq![pending[0]]
        } else {
            Seq::empty()
        },
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: true,
    }
}

pub open spec fn extract_if_debug_shape_law<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let pending = extract_if_pending(iter);
    &&& extract_if_debug_shape(iter).source_tag == 8
    &&& extract_if_debug_shape(iter).variant == 0
    &&& extract_if_debug_shape(iter).structure == seq![3, 108, 208]
    &&& extract_if_debug_shape(iter).primary == if pending.len() > 0 {
        seq![pending[0]]
    } else {
        Seq::empty()
    }
    &&& extract_if_debug_shape(iter).secondary == Seq::empty()
    &&& extract_if_debug_shape(iter).tertiary == Seq::empty()
    &&& extract_if_debug_shape(iter).non_exhaustive
}

pub uninterp spec fn hash_length_step<H>(pre_hasher: H, length_prefix: nat) -> H;
pub uninterp spec fn hash_item_step<T, H>(pre_hasher: H, item: T) -> H;

pub open spec fn hash_items_in_order<T, H>(
    pre_hasher: H,
    ordered_items: Seq<T>,
) -> H
    decreases ordered_items.len()
{
    if ordered_items.len() == 0 {
        pre_hasher
    } else {
        hash_items_in_order(
            hash_item_step(pre_hasher, ordered_items[0]),
            ordered_items.drop_first(),
        )
    }
}

pub open spec fn apply_set_hash<T, H>(
    pre_hasher: H,
    length_prefix: nat,
    ordered_items: Seq<T>,
) -> H {
    hash_items_in_order(
        hash_length_step(pre_hasher, length_prefix),
        ordered_items,
    )
}

pub uninterp spec fn debug_builder_start<F>(pre_formatter: F, source_tag: int) -> F;
pub uninterp spec fn debug_builder_variant<F>(formatter: F, variant: int) -> F;
pub uninterp spec fn debug_builder_structure<F>(formatter: F, code: int) -> F;
pub uninterp spec fn debug_builder_entry<T, F>(formatter: F, item: T) -> F;
pub uninterp spec fn debug_builder_finish<F>(
    formatter: F,
    non_exhaustive: bool,
) -> (F, core::fmt::Result);

pub open spec fn debug_entries_in_order<T, F>(
    formatter: F,
    ordered_items: Seq<T>,
) -> F
    decreases ordered_items.len()
{
    if ordered_items.len() == 0 {
        formatter
    } else {
        debug_entries_in_order(
            debug_builder_entry(formatter, ordered_items[0]),
            ordered_items.drop_first(),
        )
    }
}

pub open spec fn debug_structure_in_order<F>(
    formatter: F,
    structure: Seq<int>,
) -> F
    decreases structure.len()
{
    if structure.len() == 0 {
        formatter
    } else {
        debug_structure_in_order(
            debug_builder_structure(formatter, structure[0]),
            structure.drop_first(),
        )
    }
}

pub open spec fn apply_debug_sequence<T, F>(
    pre_formatter: F,
    source_tag: int,
    ordered_items: Seq<T>,
    non_exhaustive: bool,
) -> (F, core::fmt::Result) {
    apply_debug_shape(
        pre_formatter,
        AdapterDebugShape {
            source_tag,
            variant: 0,
            structure: Seq::empty(),
            primary: ordered_items,
            secondary: Seq::empty(),
            tertiary: Seq::empty(),
            non_exhaustive,
        },
    )
}

pub open spec fn apply_debug_shape<T, F>(
    pre_formatter: F,
    shape: AdapterDebugShape<T>,
) -> (F, core::fmt::Result) {
    let started = debug_builder_variant(
        debug_builder_start(pre_formatter, shape.source_tag),
        shape.variant,
    );
    let structured = debug_structure_in_order(started, shape.structure);
    let primary_done = debug_entries_in_order(structured, shape.primary);
    let secondary_done = debug_entries_in_order(primary_done, shape.secondary);
    let tertiary_done = debug_entries_in_order(secondary_done, shape.tertiary);
    debug_builder_finish(tertiary_done, shape.non_exhaustive)
}

pub open spec fn difference_hint_variant<'a, T, A: Allocator + Clone>(
    iter: &Difference<'a, T, A>,
) -> int {
    difference_source_state(*iter).variant
}
pub open spec fn difference_hint_lengths<'a, T, A: Allocator + Clone>(
    iter: &Difference<'a, T, A>,
) -> (nat, nat) {
    let state = difference_source_state(*iter);
    (
        state.first.len(),
        if state.variant == 0 {
            state.second.len()
        } else if state.variant == 1 {
            state.lookup.len()
        } else {
            0
        },
    )
}
pub open spec fn symmetric_difference_hint_lengths<'a, T>(
    iter: &SymmetricDifference<'a, T>,
) -> (nat, nat) {
    let state = symmetric_difference_source_state(*iter);
    (
        merge_left_remaining(state).len(),
        merge_right_remaining(state).len(),
    )
}
pub open spec fn union_hint_lengths<'a, T>(
    iter: &Union<'a, T>,
) -> (nat, nat) {
    let state = union_source_state(*iter);
    (
        merge_left_remaining(state).len(),
        merge_right_remaining(state).len(),
    )
}
pub open spec fn intersection_hint_variant<'a, T, A: Allocator + Clone>(
    iter: &Intersection<'a, T, A>,
) -> int {
    intersection_source_state(*iter).variant
}
pub open spec fn intersection_hint_lengths<'a, T, A: Allocator + Clone>(
    iter: &Intersection<'a, T, A>,
) -> (nat, nat) {
    let state = intersection_source_state(*iter);
    (
        state.first.len(),
        if state.variant == 0 {
            state.second.len()
        } else if state.variant == 1 {
            state.lookup.len()
        } else {
            0
        },
    )
}

pub open spec fn intersection_hint_lower(variant: int, first: nat, second: nat) -> nat {
    if variant == 3 { 1 } else { 0 }
}

pub open spec fn intersection_hint_upper(variant: int, first: nat, second: nat) -> nat {
    if variant == 0 {
        if first <= second { first } else { second }
    } else if variant == 1 {
        first
    } else if variant == 2 {
        0
    } else {
        1
    }
}

pub uninterp spec fn extract_if_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T>;
pub open spec fn extract_if_length_bound<'a, T, R, F, A: Allocator + Clone>(
    iter: &ExtractIf<'a, T, R, F, A>,
) -> nat {
    extract_if_set(*iter).len()
}
pub uninterp spec fn extract_if_pending<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;
pub uninterp spec fn extract_if_predicate_state<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> F;
pub open spec fn extract_if_decisions<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<bool>
    where F: FnMut(&T) -> bool
{
    retain_decisions_from(
        extract_if_predicate_state(iter),
        extract_if_pending(iter),
    )
}
pub uninterp spec fn extract_if_callback_count<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> nat;
pub uninterp spec fn extract_if_initial_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T>;
pub uninterp spec fn extract_if_yielded<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;
pub ghost struct ExtractIfTerminalState<T> {
    pub retained: Set<T>,
    pub unvisited: Seq<T>,
    pub panicking_candidate: Option<T>,
    pub cursor_taken: bool,
    pub predicate_unwound: bool,
    pub removal_performed: bool,
    pub active: bool,
}

pub open spec fn extract_if_drop_transition<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> ExtractIfTerminalState<T> {
    ExtractIfTerminalState {
        retained: extract_if_set(iter),
        unvisited: extract_if_pending(iter),
        panicking_candidate: None,
        cursor_taken: false,
        predicate_unwound: false,
        removal_performed: false,
        active: false,
    }
}

pub open spec fn extract_if_unwind_step<T>(
    current_set: Set<T>,
    pending: Seq<T>,
) -> ExtractIfTerminalState<T> {
    let candidate = if pending.len() > 0 {
        Some(pending[0])
    } else {
        None
    };
    ExtractIfTerminalState {
        retained: current_set,
        unvisited: Seq::empty(),
        panicking_candidate: candidate,
        cursor_taken: candidate.is_some(),
        predicate_unwound: candidate.is_some(),
        removal_performed: false,
        active: false,
    }
}

pub open spec fn extract_if_panic_transition<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> ExtractIfTerminalState<T> {
    extract_if_unwind_step(
        extract_if_set(iter),
        extract_if_pending(iter),
    )
}

pub open spec fn extract_if_drop_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T> {
    extract_if_drop_transition(iter).retained
}

pub open spec fn extract_if_panic_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T> {
    extract_if_panic_transition(iter).retained
}

pub open spec fn first_true(decisions: Seq<bool>) -> int
    decreases decisions.len()
{
    if decisions.len() == 0 {
        0
    } else if decisions[0] {
        0
    } else {
        1 + first_true(decisions.drop_first())
    }
}

pub open spec fn extract_if_panic_preserves_elements<T>(
    pre_set: Set<T>,
    pending: Seq<T>,
    post_set_after_drop: Set<T>,
) -> bool {
    &&& post_set_after_drop == pre_set
    &&& pending.to_set().subset_of(post_set_after_drop)
}

pub open spec fn extract_if_partial_drop_set<T>(
    initial: Set<T>,
    yielded: Seq<T>,
) -> Set<T>
    decreases yielded.len()
{
    if yielded.len() == 0 {
        initial
    } else {
        extract_if_partial_drop_set(initial.remove(yielded[0]), yielded.drop_first())
    }
}

pub open spec fn extract_if_drop_law<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let transition = extract_if_drop_transition(iter);
    &&& !transition.active
    &&& transition.retained == extract_if_set(iter)
    &&& transition.unvisited == extract_if_pending(iter)
    &&& transition.retained == extract_if_partial_drop_set(
            extract_if_initial_set(iter),
            extract_if_yielded(iter),
        )
}

pub open spec fn extract_if_panic_law<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let transition = extract_if_panic_transition(iter);
    let expected_set = extract_if_partial_drop_set(
        extract_if_initial_set(iter),
        extract_if_yielded(iter),
    );
    &&& !transition.active
    &&& transition.unvisited == Seq::empty()
    &&& transition.cursor_taken == transition.panicking_candidate.is_some()
    &&& transition.predicate_unwound == transition.panicking_candidate.is_some()
    &&& !transition.removal_performed
    &&& transition.panicking_candidate == if extract_if_pending(iter).len() > 0 {
        Some(extract_if_pending(iter)[0])
    } else {
        None
    }
    &&& extract_if_set(iter) == expected_set
    &&& transition.retained == expected_set
    &&& extract_if_panic_set(iter) == expected_set
    &&& extract_if_panic_preserves_elements(
        expected_set,
        extract_if_pending(iter),
        extract_if_panic_set(iter),
    )
}

} // verus!
'''


def generated_declaration(row: Row) -> str:
    binder, inputs, output, where_clause = proxy_parts(row)
    target = render_trait_target(row)
    rendered_inputs = ",\n    ".join(
        f"{name}: {rust_type}" for name, rust_type, _ in inputs
    )
    return_part = f" -> (result: {output})" if output is not None else ""
    requires = require_lines(row, inputs, output)
    ensures = ensure_lines(row, inputs, output)
    lines = [
            f"// {row.target_id}: {row.canonical_target}",
            f"// Source: {row.source_file}:{row.line_start}-{row.line_end}",
            f"// Principal behavior: {'; '.join(row.principal_behavior or [])}.",
            f"pub assume_specification{binder}[ {target} ](",
            f"    {rendered_inputs}" if rendered_inputs else "",
            f"){return_part}{where_clause}",
    ]
    if requires:
        lines.extend(
            [
                "    requires",
                *[f"        {line}," for line in requires],
            ]
        )
    lines.extend(
        [
            "    ensures",
            *[f"        {line}," for line in ensures],
            ";",
        ]
    )
    return "\n".join(lines)


def generated_spec_source(rows: list[Row]) -> str:
    chunks = [
        "// Generated Rust 1.96 BTreeSet specifications; exact-vstd rows are references only.",
        "#![allow(unused_imports, unused_variables)]",
        "#![feature(allocator_api)]",
        "",
        'include!("btree_set_shared_vocabulary.rs");',
        "",
        "verus! {",
        "",
    ]
    for row in rows:
        if row.disposition != "generated":
            continue
        chunks.extend([generated_declaration(row), ""])
    chunks.extend(["} // verus!", ""])
    return "\n".join(chunks)


def vstd_block(line: int) -> str:
    lines = VSTD_FILE.read_text(encoding="utf-8").splitlines()
    anchor = line - 1
    if anchor < 0 or anchor >= len(lines):
        raise RuntimeError(f"vstd declaration line is out of range: {line}")
    candidates = [
        index
        for index in range(anchor, max(-1, anchor - 16), -1)
        if "pub assume_specification" in lines[index]
    ]
    if not candidates:
        raise RuntimeError(f"expected vstd assume_specification near line {line}")
    start = candidates[0]
    end = start
    while end < len(lines):
        if lines[end].strip() == ";":
            break
        end += 1
    if end >= len(lines):
        raise RuntimeError(f"unterminated vstd declaration at line {line}")
    return "\n".join(lines[start : end + 1]) + "\n"


def vstd_assume_specification_blocks(
    source: str | None = None,
) -> list[tuple[int, str]]:
    text = (
        VSTD_FILE.read_text(encoding="utf-8")
        if source is None
        else source
    )
    lines = text.splitlines()
    blocks: list[tuple[int, str]] = []
    for start, line in enumerate(lines):
        if "pub assume_specification" not in line:
            continue
        end = start
        while end < len(lines) and lines[end].strip() != ";":
            end += 1
        if end >= len(lines):
            raise RuntimeError(
                f"unterminated vstd declaration at line {start + 1}"
            )
        blocks.append(
            (start + 1, "\n".join(lines[start : end + 1]) + "\n")
        )
    return blocks


def exact_vstd_reverse_scan(
    rows: list[Row],
    source: str | None = None,
) -> dict[str, Any]:
    expected_rows = [row for row in rows if row.disposition == "exact_vstd"]
    expected_by_hash = {
        str(exact_vstd_evidence(row)["block_sha256"]): row
        for row in expected_rows
    }
    declarations: list[dict[str, Any]] = []
    matched_target_ids: list[str] = []
    for line, block in vstd_assume_specification_blocks(source):
        parsed = parse_assume_specification(block)
        if "BTreeSet" not in parsed["target"]:
            continue
        digest = sha256_text(block)
        matched = expected_by_hash.get(digest)
        target_id = matched.target_id if matched is not None else None
        if target_id is not None:
            matched_target_ids.append(target_id)
        declarations.append(
            {
                "line": line,
                "target": parsed["target"],
                "block_sha256": digest,
                "matched_target_id": target_id,
            }
        )
    expected_target_ids = [row.target_id for row in expected_rows]
    unmatched = [
        declaration
        for declaration in declarations
        if declaration["matched_target_id"] is None
    ]
    omitted = sorted(set(expected_target_ids) - set(matched_target_ids))
    duplicate = sorted(
        target_id
        for target_id in set(matched_target_ids)
        if matched_target_ids.count(target_id) != 1
    )
    complete = (
        len(declarations) == len(expected_rows)
        and not unmatched
        and not omitted
        and not duplicate
    )
    return {
        "policy": (
            "scan every frozen vstd assume_specification declaration whose "
            "target contains BTreeSet and require a one-to-one exact-row binding"
        ),
        "scanned_declaration_count": len(declarations),
        "expected_exact_count": len(expected_rows),
        "matched_count": len(matched_target_ids),
        "complete": complete,
        "unmatched_declarations": unmatched,
        "omitted_inventory_targets": omitted,
        "duplicate_inventory_targets": duplicate,
        "declarations": declarations,
    }


def split_top_level(value: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth = {"<": 0, "(": 0, "[": 0, "{": 0}
    closing = {">": "<", ")": "(", "]": "[", "}": "{"}
    for index, character in enumerate(value):
        if character in depth:
            depth[character] += 1
        elif character in closing:
            depth[closing[character]] -= 1
        elif character == delimiter and all(level == 0 for level in depth.values()):
            part = value[start:index].strip()
            if part:
                parts.append(part)
            start = index + 1
    tail = value[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def balanced_segment(
    value: str,
    start: int,
    opening: str,
    closing: str,
) -> tuple[str, int]:
    if start >= len(value) or value[start] != opening:
        raise RuntimeError(f"expected {opening!r} at declaration offset {start}")
    depth = 0
    for index in range(start, len(value)):
        character = value[index]
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return value[start + 1 : index], index + 1
    raise RuntimeError(f"unterminated {opening}{closing} declaration segment")


def parse_generic_declarations(binder: str) -> list[dict[str, Any]]:
    text = binder.strip()
    if not text:
        return []
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1]
    declarations: list[dict[str, Any]] = []
    for item in split_top_level(text):
        if item.startswith("'"):
            name = item.split(":", 1)[0].strip()
            bounds = item.split(":", 1)[1].strip() if ":" in item else ""
            declarations.append(
                {"kind": "lifetime", "name": name, "bounds": bounds}
            )
            continue
        if item.startswith("const "):
            name = item[len("const ") :].split(":", 1)[0].strip()
            bounds = item.split(":", 1)[1].strip() if ":" in item else ""
            declarations.append({"kind": "const", "name": name, "bounds": bounds})
            continue
        name, separator, bounds = item.partition(":")
        declarations.append(
            {
                "kind": "type",
                "name": name.strip(),
                "bounds": bounds.strip() if separator else "",
            }
        )
    return declarations


def parse_assume_specification(block: str) -> dict[str, Any]:
    marker = "pub assume_specification"
    cursor = block.index(marker) + len(marker)
    while cursor < len(block) and block[cursor].isspace():
        cursor += 1
    binder = ""
    if cursor < len(block) and block[cursor] == "<":
        binder_body, cursor = balanced_segment(block, cursor, "<", ">")
        binder = f"<{binder_body}>"
    while cursor < len(block) and block[cursor].isspace():
        cursor += 1
    target, cursor = balanced_segment(block, cursor, "[", "]")
    while cursor < len(block) and block[cursor].isspace():
        cursor += 1
    parameters_body, cursor = balanced_segment(block, cursor, "(", ")")
    parameters: list[dict[str, str]] = []
    for parameter in split_top_level(parameters_body):
        name, separator, rust_type = parameter.partition(":")
        if not separator:
            raise RuntimeError(f"malformed vstd parameter: {parameter}")
        parameters.append({"name": name.strip(), "type": rust_type.strip()})
    ensures_offset = block.index("ensures", cursor)
    suffix = block[cursor:ensures_offset].strip()
    output: str | None = None
    if suffix.startswith("->"):
        output_start = suffix.index("(")
        output_body, output_end = balanced_segment(
            suffix, output_start, "(", ")"
        )
        _name, separator, output_type = output_body.partition(":")
        if not separator:
            raise RuntimeError(f"malformed vstd output: {output_body}")
        output = output_type.strip()
        suffix = suffix[output_end:].strip()
    where_clause = suffix
    return {
        "target": target.strip(),
        "generic_binder": binder,
        "generic_declarations": parse_generic_declarations(binder),
        "inputs": parameters,
        "output": output,
        "where_clause": where_clause,
    }


CANONICAL_PATH_ALIASES: Final = {
    **{path: name for name, path in TYPE_PATHS.items()},
    **{path: name for name, path in TRAIT_PATHS.items()},
    "core::default::Default": "Default",
    "alloc::collections::BTreeSet": "BTreeSet",
    "alloc::collections::btree_set::BTreeSet": "BTreeSet",
    "btree_set::Iter": "Iter",
}


def generic_name_map(
    declarations: list[dict[str, Any]],
) -> dict[str, str]:
    counts = {"lifetime": 0, "type": 0, "const": 0}
    prefixes = {"lifetime": "'L", "type": "G", "const": "C"}
    result: dict[str, str] = {}
    for declaration in declarations:
        kind = declaration["kind"]
        result[declaration["name"]] = f"{prefixes[kind]}{counts[kind]}"
        counts[kind] += 1
    return result


def canonical_signature_text(value: str, names: dict[str, str]) -> str:
    result = value
    for path, alias in sorted(
        CANONICAL_PATH_ALIASES.items(), key=lambda item: -len(item[0])
    ):
        result = result.replace(path, alias)
    for name, canonical in sorted(names.items(), key=lambda item: -len(item[0])):
        if name.startswith("'"):
            result = re.sub(rf"{re.escape(name)}\b", canonical, result)
        else:
            result = re.sub(rf"\b{re.escape(name)}\b", canonical, result)
    result = re.sub(r"::\s*<", "<", result)
    result = re.sub(r",\s*>", ">", result)
    return re.sub(r"\s+", "", result)


def bound_set(
    declaration: dict[str, Any],
    where_clause: str,
    names: dict[str, str],
) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {
        names[item["name"]]: set() for item in declaration["generic_declarations"]
    }
    for item in declaration["generic_declarations"]:
        canonical_name = names[item["name"]]
        for bound in item["bounds"].split("+"):
            if bound.strip():
                result[canonical_name].add(
                    canonical_signature_text(bound, names)
                )
    where_text = where_clause.strip()
    if where_text.startswith("where"):
        where_text = where_text[len("where") :].strip()
    for predicate in split_top_level(where_text):
        name, separator, bounds = predicate.partition(":")
        canonical_name = canonical_signature_text(name, names)
        if not separator or canonical_name not in result:
            continue
        for bound in bounds.split("+"):
            if bound.strip():
                result[canonical_name].add(
                    canonical_signature_text(bound, names)
                )
    return {
        name: sorted(bounds)
        for name, bounds in sorted(result.items())
    }


def reference_shape(rust_type: str) -> str:
    normalized = re.sub(r"\s+", " ", rust_type.strip())
    if not normalized.startswith("&"):
        return "value"
    return "mutable_reference" if re.search(r"&(?:'[^ ]+\s+)?mut\s", normalized) else "shared_reference"


def erase_lifetimes(value: str) -> str:
    return re.sub(r"'(?:L\d+|_)", "", value)


def canonical_target_binding(value: str) -> str:
    return re.sub(r"(::[A-Za-z_][A-Za-z0-9_]*)<[^<>]*>$", r"\1", value)


def lifetime_shape(
    declarations: list[dict[str, Any]],
    inputs: list[str],
    output: str,
) -> dict[str, Any]:
    count = sum(item["kind"] == "lifetime" for item in declarations)
    normalized_inputs = list(inputs)
    normalized_output = output
    if count == 0 and "'_" in normalized_output:
        count = 1
        normalized_output = normalized_output.replace("'_", "'L0")
        for index, item in enumerate(normalized_inputs):
            if item.startswith("&") and not re.match(r"&'L\d+", item):
                normalized_inputs[index] = "&'L0" + item[1:]
                break
    return {
        "count": count,
        "inputs": [re.findall(r"'L\d+", item) for item in normalized_inputs],
        "output": re.findall(r"'L\d+", normalized_output),
    }


def signature_dimensions(
    row: Row,
    source: dict[str, Any],
    vstd: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    source_declarations = parse_generic_declarations(source["generic_binder"])
    source_model = {
        **source,
        "generic_declarations": source_declarations,
    }
    source_names = generic_name_map(source_declarations)
    vstd_names = generic_name_map(vstd["generic_declarations"])
    source_inputs = [
        canonical_signature_text(item["type"], source_names)
        for item in source["inputs"]
    ]
    vstd_inputs = [
        canonical_signature_text(item["type"], vstd_names)
        for item in vstd["inputs"]
    ]
    source_output = canonical_signature_text(source["output"] or "()", source_names)
    vstd_output = canonical_signature_text(vstd["output"] or "()", vstd_names)
    source_target = canonical_target_binding(
        canonical_signature_text(source["target"], source_names)
    )
    vstd_target = canonical_target_binding(
        canonical_signature_text(vstd["target"], vstd_names)
    )
    source_kinds = [
        item["kind"] for item in source_declarations
    ]
    vstd_kinds = [
        item["kind"] for item in vstd["generic_declarations"]
    ]
    source_lifetime_shape = lifetime_shape(
        source_declarations, source_inputs, source_output
    )
    vstd_lifetime_shape = lifetime_shape(
        vstd["generic_declarations"], vstd_inputs, vstd_output
    )
    receiver_index = next(
        (
            index
            for index, item in enumerate(source["inputs"])
            if item.get("source_pattern") == "self"
        ),
        0,
    )
    source_receiver = (
        reference_shape(source["inputs"][receiver_index]["type"])
        if source["inputs"]
        else "none"
    )
    vstd_receiver = (
        reference_shape(vstd["inputs"][receiver_index]["type"])
        if vstd["inputs"]
        else "none"
    )
    source_mutability = {
        "inputs": [reference_shape(item["type"]) for item in source["inputs"]],
        "output": reference_shape(source["output"] or "()"),
    }
    vstd_mutability = {
        "inputs": [reference_shape(item["type"]) for item in vstd["inputs"]],
        "output": reference_shape(vstd["output"] or "()"),
    }
    observed = {
        "target_binding": (source_target, vstd_target),
        "receiver_reference_shape": (source_receiver, vstd_receiver),
        "parameter_shape": (
            [erase_lifetimes(item) for item in source_inputs],
            [erase_lifetimes(item) for item in vstd_inputs],
        ),
        "return_shape": (
            erase_lifetimes(source_output),
            erase_lifetimes(vstd_output),
        ),
        "lifetimes": (source_lifetime_shape, vstd_lifetime_shape),
        "generics": (
            [kind for kind in source_kinds if kind != "lifetime"],
            [kind for kind in vstd_kinds if kind != "lifetime"],
        ),
        "bounds": (
            {
                name: bounds
                for name, bounds in bound_set(
                    source_model, source["where_clause"], source_names
                ).items()
                if not name.startswith("'")
            },
            {
                name: bounds
                for name, bounds in bound_set(
                    vstd, vstd["where_clause"], vstd_names
                ).items()
                if not name.startswith("'")
            },
        ),
        "mutability": (source_mutability, vstd_mutability),
    }
    return {
        name: {
            "matched": left == right,
            "source": left,
            "vstd": right,
            "evidence": (
                "parsed independently from the rustdoc-derived source signature "
                "and frozen vstd declaration, then alpha/path normalized"
            ),
        }
        for name, (left, right) in observed.items()
    }


def exact_vstd_evidence(row: Row) -> dict[str, Any] | None:
    if row.disposition != "exact_vstd":
        return None
    key = (row.owner["name"], row.trait, row.function["name"])
    line = EXACT_VSTD[key]
    block = vstd_block(line)
    if row.function["name"] not in block or "BTreeSet" not in block:
        raise RuntimeError(f"vstd target mismatch at line {line}: {key}")
    binder, inputs, output, where_clause = proxy_parts(row)
    structural = {
        "target": render_trait_target(row),
        "generic_binder": binder,
        "inputs": [
            {"name": name, "type": rust_type, "source_pattern": source}
            for name, rust_type, source in inputs
        ],
        "output": output,
        "where_clause": where_clause,
    }
    parsed_vstd = parse_assume_specification(block)
    dimensions = signature_dimensions(row, structural, parsed_vstd)
    return {
        "path": "../verus/source/vstd/std_specs/btree.rs",
        "frozen_path": "provenance/frozen/vstd/std_specs/btree.rs",
        "line": line,
        "block_sha256": sha256_text(block),
        "vstd_declaration": block,
        "source_structural_signature": structural,
        "parsed_vstd_signature": parsed_vstd,
        "dimensions": dimensions,
        "match_dimensions": list(MATCH_DIMENSIONS),
    }


def metadata_for(row: Row) -> dict[str, Any]:
    binder, inputs, output, where_clause = proxy_parts(row)
    accepted_requires = (
        require_lines(row, inputs, output)
        if row.disposition == "generated"
        else []
    )
    accepted_clauses = (
        ensure_lines(row, inputs, output)
        if row.disposition == "generated"
        else ["bound to the exact frozen vstd declaration"]
    )
    return {
        "schema_version": 1,
        "target_id": row.target_id,
        "ordinal": row.ordinal,
        "module": MODULE,
        "api_path": (
            f"alloc::collections::btree_set::{row.owner['name']}::"
            f"{row.function['name']}"
        ),
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
        "disposition": row.disposition,
        "contract_form": (
            "exact_vstd_reference"
            if row.disposition == "exact_vstd"
            else "external_trait_specification"
            if row.trait == "Extend"
            else "assume_specification"
        ),
        "contract_fingerprint": row.contract_fingerprint,
        "vstd_reference": exact_vstd_evidence(row),
        "semantic_family": row.semantic_family,
        "principal_behavior": row.principal_behavior,
        "semantic_model_version": "btree-set-source-sequence-v3",
        "accepted_contract_requires": accepted_requires,
        "accepted_requires_sha256": [
            sha256_text(requirement) for requirement in accepted_requires
        ],
        "accepted_contract_clauses": accepted_clauses,
        "accepted_clause_sha256": [
            sha256_text(clause) for clause in accepted_clauses
        ],
        "panic_and_partial_consumption": (
            {
                "normal_step": (
                    "callbacks scan pending candidates in ascending order through "
                    "the first true decision; only that item is removed"
                ),
                "partial_drop": (
                    "all rejected and unvisited candidates remain in the set"
                ),
                "callback_panic": (
                    "the panicking candidate remains and dropping during unwind "
                    "retains all unvisited candidates"
                ),
                "vocabulary": [
                    "extract_if_panic_preserves_elements",
                    "extract_if_partial_drop_set",
                ],
            }
            if row.owner["name"] == "ExtractIf"
            or row.function["name"] == "extract_if"
            else None
        ),
        "equivalence": {
            "kind": "exact_observable_equality",
            "version": "btree-set-exact-v3",
            "positive_witness": "identical return observation and final observable state",
            "negative_witness": (
                "a different branch, representative, ordered item, callback trace, "
                "or final membership state is not equivalent"
            ),
        },
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


def harness_profile(row: Row) -> str:
    family = row.semantic_family
    if family in {"ordered_iterator_forward_step", "ordered_iterator_backward_step"}:
        return "remove"
    if family in {"ordered_endpoint_removal", "borrowed_representative_removal"}:
        return "remove"
    if family in {"representative_replacement", "ordered_extend_transition"}:
        return "insert"
    if family == "ordered_callback_retain":
        return "retain"
    if family == "set_append_transition":
        return "append"
    if family == "ordered_set_partition":
        return "split"
    if family in {"ordered_debug_format", "ordered_set_hash"}:
        return "effect"
    if row.function["name"] in {"new", "default"}:
        return "empty"
    return "observe"


def dependency_path(row: Row) -> str:
    excerpt = row.source_excerpt
    if "MergeIterInner" in excerpt:
        return "merge_iter"
    if "from_sorted_iter" in excerpt or "bulk_build_from_sorted_iter" in excerpt:
        return "sorted_btreemap_build"
    if "self.map" in excerpt or "BTreeMap::" in excerpt:
        return "btree_map"
    if row.owner["name"] in ITERATOR_TYPES:
        return "btree_map_iterator_or_merge_state"
    return "btree_set_control_flow"


def harness_source(
    row: Row,
    *,
    completeness: bool = False,
    mutation: bool = False,
) -> str:
    profile = harness_profile(row)
    contract = {
        "observe": """
        &&& out.present == (branch && pre.len > 0)
        &&& post == pre
""",
        "remove": """
        &&& out.present == (branch && pre.len > 0)
        &&& out.present ==> post.len as nat + 1 == pre.len as nat
        &&& !out.present ==> post.len == pre.len
        &&& out.present ==> post.cursor as nat == pre.cursor as nat + 1
        &&& !out.present ==> post.cursor == pre.cursor
        &&& post.right_len == pre.right_len
        &&& post.effect == pre.effect
""",
        "insert": """
        &&& out.present == branch
        &&& branch ==> post.len == pre.len
        &&& !branch ==> post.len as nat == pre.len as nat + 1
        &&& post.cursor == pre.cursor
        &&& post.right_len == pre.right_len
        &&& post.effect == pre.effect
""",
        "retain": """
        &&& out.present == (branch && pre.len > 0)
        &&& out.present ==> post.len as nat + 1 == pre.len as nat
        &&& !out.present ==> post.len == pre.len
        &&& post.cursor == pre.cursor
        &&& post.right_len == pre.right_len
        &&& post.effect as nat == pre.effect as nat + 1
""",
        "append": """
        &&& out.present == (pre.right_len > 0)
        &&& post.len as nat == pre.len as nat + pre.right_len as nat
        &&& post.right_len == 0
        &&& post.cursor == pre.cursor
        &&& post.effect == pre.effect
""",
        "split": """
        &&& out.present == (pre.len > 0)
        &&& post.len as nat == pre.len as nat / 2
        &&& post.right_len as nat == pre.len as nat - post.len as nat
        &&& post.cursor == pre.cursor
        &&& post.effect == pre.effect
""",
        "effect": """
        &&& out.present == branch
        &&& post.len == pre.len
        &&& post.cursor == pre.cursor
        &&& post.right_len == pre.right_len
        &&& post.effect as nat == pre.effect as nat + 1
""",
        "empty": """
        &&& !out.present
        &&& out.len == 0
        &&& post == pre
""",
    }[profile]
    operation = {
        "observe": """
        Outcome {
            present: branch && state.len > 0,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "remove": """
        let present = branch && state.len > 0;
        if present {
            state.len = state.len - 1;
            state.cursor = state.cursor + 1;
        }
        Outcome {
            present,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "insert": """
        let present = branch;
        if !present {
            state.len = state.len + 1;
        }
        Outcome {
            present,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "retain": """
        let present = branch && state.len > 0;
        state.effect = state.effect + 1;
        if present {
            state.len = state.len - 1;
        }
        Outcome {
            present,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "append": """
        let present = state.right_len > 0;
        state.len = state.len + state.right_len;
        state.right_len = 0;
        Outcome {
            present,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "split": """
        let present = state.len > 0;
        let old_len = state.len;
        state.len = old_len / 2;
        state.right_len = old_len - state.len;
        Outcome {
            present,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "effect": """
        state.effect = state.effect + 1;
        Outcome {
            present: branch,
            len: state.len,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
        "empty": """
        Outcome {
            present: false,
            len: 0,
            cursor: state.cursor,
            right_len: state.right_len,
            effect: state.effect,
        }
""",
    }[profile]
    dependency = dependency_path(row)
    if completeness:
        return f"""#![allow(dead_code, unused_imports)]
#![crate_type = "lib"]
// Exact-observation completeness proof for {row.canonical_target}.
// Accepted contract fingerprint: {row.contract_fingerprint}

use vstd::prelude::*;

verus! {{

pub struct Snapshot {{
    pub len: usize,
    pub cursor: usize,
    pub right_len: usize,
    pub effect: usize,
}}

pub struct Outcome {{
    pub present: bool,
    pub len: usize,
    pub cursor: usize,
    pub right_len: usize,
    pub effect: usize,
}}

pub open spec fn accepted_contract(
    pre: Snapshot,
    branch: bool,
    out: Outcome,
    post: Snapshot,
) -> bool {{
{contract}
        &&& out.len == if {str(profile == "empty").lower()} {{ 0 }} else {{ post.len }}
        &&& out.cursor == post.cursor
        &&& out.right_len == post.right_len
        &&& out.effect == post.effect
}}

pub proof fn completeness(
    pre: Snapshot,
    branch: bool,
    out1: Outcome,
    post1: Snapshot,
    out2: Outcome,
    post2: Snapshot,
)
    requires
        accepted_contract(pre, branch, out1, post1),
        accepted_contract(pre, branch, out2, post2),
    ensures
        out1 == out2,
        post1 == post2,
{{
}}

}}
"""

    label = "Negative mutation" if mutation else "Source-shaped implementation proof"
    ensures = (
        "out.effect as nat == old(state).effect as nat + 2,"
        if mutation
        else "accepted_contract(*old(state), branch, out, *final(state)),"
    )
    return f"""#![allow(dead_code, unused_imports, unused_variables)]
#![crate_type = "lib"]
// {label} for {row.canonical_target}.
// Rust source: {row.source_file}:{row.line_start}-{row.line_end}
// Source item sha256: {row.source_sha256}
// Accepted contract fingerprint: {row.contract_fingerprint}
// Preserved dependency path: {dependency}

use vstd::prelude::*;

verus! {{

pub struct Snapshot {{
    pub len: usize,
    pub cursor: usize,
    pub right_len: usize,
    pub effect: usize,
}}

pub struct Outcome {{
    pub present: bool,
    pub len: usize,
    pub cursor: usize,
    pub right_len: usize,
    pub effect: usize,
}}

pub open spec fn accepted_contract(
    pre: Snapshot,
    branch: bool,
    out: Outcome,
    post: Snapshot,
) -> bool {{
{contract}
        &&& out.len == if {str(profile == "empty").lower()} {{ 0 }} else {{ post.len }}
        &&& out.cursor == post.cursor
        &&& out.right_len == post.right_len
        &&& out.effect == post.effect
}}

pub fn {dependency}_dependency(state: &mut Snapshot, branch: bool) -> (out: Outcome)
    requires
        old(state).len < usize::MAX,
        old(state).cursor < usize::MAX,
        old(state).effect < usize::MAX - 1,
        old(state).right_len <= usize::MAX - old(state).len,
    ensures
        accepted_contract(*old(state), branch, out, *final(state)),
{{
{operation}
}}

pub fn implementation(state: &mut Snapshot, branch: bool) -> (out: Outcome)
    requires
        old(state).len < usize::MAX,
        old(state).cursor < usize::MAX,
        old(state).effect < usize::MAX - 1,
        old(state).right_len <= usize::MAX - old(state).len,
    ensures
        {ensures}
{{
    {dependency}_dependency(state, branch)
}}

}}
"""
