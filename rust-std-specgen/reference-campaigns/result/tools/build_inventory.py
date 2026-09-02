#!/usr/bin/env python3
"""Build the pinned Rust 1.96 core::result executable API inventory."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT.parent
RUST_ROOT = SURVEY / "rust-1.96"
VERUS_ROOT = SURVEY / "verus"
RUSTDOC_ORIGIN = SURVEY / "rustdoc-json-1.96" / "core.json"
RUSTDOC_JSON = ROOT / "provenance" / "rustdoc-target" / "doc" / "core.json"
RESULT_SOURCE = RUST_ROOT / "library" / "core" / "src" / "result.rs"
ACCUM_SOURCE = (
    RUST_ROOT
    / "library"
    / "core"
    / "src"
    / "iter"
    / "traits"
    / "accum.rs"
)
CORE_LIB_SOURCE = RUST_ROOT / "library" / "core" / "src" / "lib.rs"
CORE_PRELUDE_SOURCE = (
    RUST_ROOT / "library" / "core" / "src" / "prelude" / "v1.rs"
)
STD_LIB_SOURCE = RUST_ROOT / "library" / "std" / "src" / "lib.rs"
VSTD_RESULT = VERUS_ROOT / "source" / "vstd" / "std_specs" / "result.rs"
VSTD_MODULE = VERUS_ROOT / "source" / "vstd" / "std_specs" / "mod.rs"
VERUS_BINARY = VERUS_ROOT / "source" / "target-verus" / "release" / "verus"
Z3_BINARY = VERUS_ROOT / "source" / "z3"
PROCESS_DOCUMENT = Path(
    "/home/chentianyu/.argus-skill/workspaces/s-8d9b336f/research/"
    "rust-std-lib-specgen-process.md"
)
TRUST_AUDIT = (
    SURVEY
    / "nanvix-rust-std-slice-vec-implproof-2026-08-12"
    / "TRUST_BOUNDARY_AUDIT.md"
)

MODULE_PATH = ["core", "result"]
HISTORICAL_REPORTED_ROWS = 37
EXPECTED_RUST_COMMIT = "ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96"
EXPECTED_VERUS_COMMIT = "1beb0fad337b8f8a224cf8684162cb02d0c2fc01"
EXPECTED_HASHES = {
    "result_source": (
        RESULT_SOURCE,
        "fc9cedba2ca1bb3d07b07d0f15160ed0277ed9a9cbc91fa5045125a73cdacb1d",
    ),
    "accum_source": (
        ACCUM_SOURCE,
        "6555f677413d4f09131fb4544f8b4b9780cd9b8398c1495e10cf74be9b3c402b",
    ),
    "rustdoc_json": (
        RUSTDOC_ORIGIN,
        "0e5a02c4527d63beedb9d78f6ec055fa07c4d18353c023a8e015a315c702b62c",
    ),
    "vstd_result": (
        VSTD_RESULT,
        "c0d32562ba5b25d9d7a1d5425e9b0ef848c1ab800e1ebba47737d89868b456ff",
    ),
    "vstd_module": (
        VSTD_MODULE,
        "1d38c2e5903e8c1a77d7c2f2a8366ac20af7ed61e03ca3d3ce0025b6143ddb71",
    ),
    "verus_binary": (
        VERUS_BINARY,
        "53aa2cdd02e9172de6561f175fbc341e157c051d743ab69107513ceba2cd3141",
    ),
    "z3_binary": (
        Z3_BINARY,
        "260a93f9ad37363d880d251c79e3af07888ef3b2171eb8ec8d4d3808678a3e84",
    ),
    "process_document": (
        PROCESS_DOCUMENT,
        "b718e235187616459cd5e99eabc70cad9117f7ad6fbf03a2de5271c2baeccf0c",
    ),
    "trust_audit": (
        TRUST_AUDIT,
        "55f7aba92e27893c4b92ffff86d645addc58849156e2a0ad388e213503e4b5d0",
    ),
}
RUSTDOC_REPRODUCTION_COMMAND = (
    "RUSTC_BOOTSTRAP=1 cargo +1.96.0 clean "
    "--manifest-path ../rust-1.96/library/Cargo.toml -p core "
    '--target-dir "$PWD/provenance/rustdoc-target" && '
    'CARGO_TARGET_DIR="$PWD/provenance/rustdoc-target" '
    "RUSTC_BOOTSTRAP=1 cargo +1.96.0 rustdoc "
    "--manifest-path ../rust-1.96/library/Cargo.toml -p core --lib -- "
    "-Z unstable-options --output-format json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(
    path: Path, rows: list[dict[str, Any]], fields: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def run(argv: list[str], cwd: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "stderr": completed.stderr,
        "stdout": completed.stdout,
    }


def require_success(result: dict[str, Any], label: str) -> None:
    if result["returncode"] != 0:
        raise ValueError(
            f"{label} failed with rc={result['returncode']}: "
            f"{result['stderr']}"
        )


def copy_input(
    source: Path, destination: Path, role: str
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "copied_path": str(destination.relative_to(ROOT)),
        "role": role,
        "sha256": sha256(destination),
        "size": destination.stat().st_size,
        "source_path": str(source),
        "source_sha256": sha256(source),
    }


def inner_kind(item: dict[str, Any]) -> str:
    inner = item.get("inner")
    if not isinstance(inner, dict) or len(inner) != 1:
        raise ValueError(
            f"rustdoc item {item.get('id')} has malformed inner data"
        )
    return next(iter(inner))


def item_for(document: dict[str, Any], item_id: int) -> dict[str, Any]:
    item = document["index"].get(str(item_id))
    if not isinstance(item, dict):
        raise ValueError(f"rustdoc index lacks item {item_id}")
    return item


def path_for_id(
    document: dict[str, Any], item_id: int, fallback: str
) -> str:
    path = document["paths"].get(str(item_id))
    parts = path.get("path") if isinstance(path, dict) else None
    if isinstance(parts, list) and all(
        isinstance(part, str) for part in parts
    ):
        return "::".join(parts)
    return fallback


def render_constant(value: Any, document: dict[str, Any]) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("expr", "value"):
            if isinstance(value.get(key), str):
                return value[key]
        if "type" in value:
            return render_type(value["type"], document)
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_generic_argument(
    value: Any, document: dict[str, Any]
) -> str:
    if not isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    if "lifetime" in value:
        return str(value["lifetime"])
    if "type" in value:
        return render_type(value["type"], document)
    if "const" in value:
        return render_constant(value["const"], document)
    if "infer" in value:
        return "_"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_bound(value: Any, document: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        return str(value)
    if "trait_bound" in value:
        bound = value["trait_bound"]
        prefix = "?" if bound.get("modifier") == "maybe" else ""
        return prefix + render_path(bound["trait"], document)
    if "outlives" in value:
        return str(value["outlives"])
    if "use" in value:
        return "use<" + ", ".join(map(str, value["use"])) + ">"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_generic_args(value: Any, document: dict[str, Any]) -> str:
    if value is None:
        return ""
    if not isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    if "angle_bracketed" in value:
        angle = value["angle_bracketed"]
        arguments = [
            render_generic_argument(argument, document)
            for argument in angle.get("args", [])
        ]
        for constraint in angle.get("constraints", []):
            name = constraint.get("name", "?")
            binding = constraint.get("binding", {})
            if "equality" in binding:
                equality = binding["equality"]
                rendered = (
                    render_type(equality["type"], document)
                    if "type" in equality
                    else render_constant(equality.get("constant"), document)
                )
                arguments.append(f"{name} = {rendered}")
            elif "constraint" in binding:
                rendered = " + ".join(
                    render_bound(bound, document)
                    for bound in binding["constraint"].get("bounds", [])
                )
                arguments.append(f"{name}: {rendered}")
        return "<" + ", ".join(arguments) + ">" if arguments else ""
    if "parenthesized" in value:
        parenthesized = value["parenthesized"]
        inputs = ", ".join(
            render_type(item, document)
            for item in parenthesized.get("inputs", [])
        )
        output = parenthesized.get("output")
        suffix = (
            f" -> {render_type(output, document)}"
            if output is not None
            else ""
        )
        return f"({inputs}){suffix}"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_path(value: Any, document: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        return str(value)
    fallback = (
        value.get("path") if isinstance(value.get("path"), str) else "?"
    )
    item_id = value.get("id")
    path = (
        path_for_id(document, item_id, fallback)
        if isinstance(item_id, int)
        else fallback
    )
    return path + render_generic_args(value.get("args"), document)


def render_type(value: Any, document: dict[str, Any]) -> str:
    if value is None:
        return "()"
    if not isinstance(value, dict) or len(value) != 1:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    kind, body = next(iter(value.items()))
    if kind in {"generic", "primitive"}:
        return str(body)
    if kind == "resolved_path":
        return render_path(body, document)
    if kind == "borrowed_ref":
        lifetime = f"{body['lifetime']} " if body.get("lifetime") else ""
        mutable = "mut " if body.get("is_mutable") else ""
        return f"&{lifetime}{mutable}{render_type(body['type'], document)}"
    if kind == "raw_pointer":
        mutable = "mut" if body.get("is_mutable") else "const"
        return f"*{mutable} {render_type(body['type'], document)}"
    if kind == "slice":
        return f"[{render_type(body, document)}]"
    if kind == "array":
        return (
            f"[{render_type(body['type'], document)}; "
            f"{render_constant(body['len'], document)}]"
        )
    if kind == "tuple":
        rendered = [render_type(item, document) for item in body]
        suffix = "," if len(rendered) == 1 else ""
        return "(" + ", ".join(rendered) + suffix + ")"
    if kind == "qualified_path":
        self_type = render_type(body["self_type"], document)
        trait = render_path(body["trait"], document)
        args = render_generic_args(body.get("args"), document)
        return f"<{self_type} as {trait}>::{body['name']}{args}"
    if kind == "impl_trait":
        return "impl " + " + ".join(
            render_bound(bound, document) for bound in body
        )
    if kind == "dyn_trait":
        traits = [
            render_path(trait["trait"], document)
            for trait in body.get("traits", [])
        ]
        if body.get("lifetime"):
            traits.append(str(body["lifetime"]))
        return "dyn " + " + ".join(traits)
    if kind == "function_pointer":
        signature = body.get("sig", {})
        inputs = ", ".join(
            render_type(item[1], document)
            for item in signature.get("inputs", [])
        )
        output = signature.get("output")
        suffix = (
            f" -> {render_type(output, document)}"
            if output is not None
            else ""
        )
        return f"fn({inputs}){suffix}"
    if kind == "pat":
        return render_type(body["type"], document)
    if kind == "infer":
        return "_"
    if kind == "never":
        return "!"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def generic_parameter_names(generics: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for parameter in generics.get("params", []):
        name = parameter.get("name")
        kind = parameter.get("kind", {})
        is_synthetic = (
            isinstance(kind, dict)
            and isinstance(kind.get("type"), dict)
            and kind["type"].get("is_synthetic", False)
        )
        if isinstance(name, str) and not is_synthetic:
            names.append(name)
    return names


def render_signature(
    item: dict[str, Any], document: dict[str, Any]
) -> str:
    function = item["inner"]["function"]
    header = function["header"]
    qualifiers: list[str] = []
    if item.get("visibility") == "public":
        qualifiers.append("pub")
    if header.get("is_const"):
        qualifiers.append("const")
    if header.get("is_async"):
        qualifiers.append("async")
    if header.get("is_unsafe"):
        qualifiers.append("unsafe")
    qualifiers.append("fn")
    generics = generic_parameter_names(function["generics"])
    generic_text = "<" + ", ".join(generics) + ">" if generics else ""
    inputs = ", ".join(
        f"{name}: {render_type(input_type, document)}"
        for name, input_type in function["sig"].get("inputs", [])
    )
    output = function["sig"].get("output")
    output_text = (
        f" -> {render_type(output, document)}"
        if output is not None
        else ""
    )
    return (
        " ".join(qualifiers)
        + f" {item['name']}{generic_text}({inputs}){output_text}"
    )


STABILITY_PATTERN = re.compile(
    r"level: (?P<level>Stable|Unstable)"
    r"(?: \{since: Version\(RustcVersion \{ major: (?P<major>\d+), "
    r"minor: (?P<minor>\d+), patch: (?P<patch>\d+) \}\)\}| \{[^}]*\})"
    r".*?feature: \"(?P<feature>[^\"]+)\"",
    re.DOTALL,
)


def own_stability(item: dict[str, Any]) -> dict[str, Any] | None:
    for attribute in item.get("attrs", []):
        text = (
            attribute.get("other")
            if isinstance(attribute, dict)
            else None
        )
        if not isinstance(text, str) or not text.startswith(
            "#[attr = Stability {"
        ):
            continue
        match = STABILITY_PATTERN.search(text)
        if match is None:
            raise ValueError(
                "cannot parse main Stability attribute on "
                f"item {item.get('id')}"
            )
        since = None
        if match.group("major") is not None:
            since = ".".join(
                [
                    match.group("major"),
                    match.group("minor"),
                    match.group("patch"),
                ]
            )
        return {
            "attribute": text,
            "feature": match.group("feature"),
            "level": match.group("level").casefold(),
            "since": since,
        }
    return None


def effective_stability(
    parent: dict[str, Any],
    implementation: dict[str, Any],
    associated: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scopes = [
        ("parent_item", own_stability(parent)),
        ("implementation", own_stability(implementation)),
    ]
    if associated is not None:
        scopes.append(("function", own_stability(associated)))
    for basis, stability in scopes:
        if stability is not None and stability["level"] == "unstable":
            return {**stability, "basis": basis}
    for basis, stability in reversed(scopes):
        if stability is not None:
            return {**stability, "basis": basis}
    return {
        "attribute": None,
        "basis": "no_main_stability_attribute",
        "feature": None,
        "level": "unknown",
        "since": None,
    }


def automatically_derived(item: dict[str, Any]) -> bool:
    return any(attribute == "automatically_derived" for attribute in item.get("attrs", []))


def canonical_source_path(span: dict[str, Any]) -> Path:
    filename = span.get("filename")
    if not isinstance(filename, str):
        raise ValueError("rustdoc source span lacks filename")
    path = RUST_ROOT / "library" / filename
    if not path.is_file():
        raise ValueError(f"rustdoc source path does not exist: {path}")
    return path


def frozen_source_path(path: Path) -> Path:
    relative = path.relative_to(RUST_ROOT / "library")
    return ROOT / "provenance" / "rust-source" / "library" / relative


def source_excerpt(path: Path, span: dict[str, Any]) -> str:
    begin = span.get("begin")
    end = span.get("end")
    if (
        not isinstance(begin, list)
        or not isinstance(end, list)
        or len(begin) != 2
        or len(end) != 2
    ):
        raise ValueError("rustdoc source span lacks begin/end coordinates")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start_line, start_column = begin
    end_line, end_column = end
    selected = lines[start_line - 1 : end_line]
    if not selected:
        raise ValueError(f"empty source span in {path}: {begin}-{end}")
    if start_line == end_line:
        return selected[0][start_column - 1 : end_column - 1]
    selected[0] = selected[0][start_column - 1 :]
    selected[-1] = selected[-1][: end_column - 1]
    return "".join(selected)


def impl_ids(parent: dict[str, Any]) -> list[int]:
    body = parent["inner"][inner_kind(parent)]
    return [
        value for value in body.get("impls", []) if isinstance(value, int)
    ]


def impl_identity(
    implementation: dict[str, Any], document: dict[str, Any]
) -> tuple[str, str | None, str]:
    body = implementation["inner"]["impl"]
    self_type = render_type(body["for"], document)
    trait_value = body.get("trait")
    if trait_value is None:
        return "inherent", None, self_type
    return "trait", render_path(trait_value, document), self_type


def impl_target(
    implementation: dict[str, Any], document: dict[str, Any]
) -> str:
    impl_kind, trait, self_type = impl_identity(implementation, document)
    if impl_kind == "inherent":
        return f"<{self_type}>"
    return f"<{self_type} as {trait}>"


def canonical_target(
    implementation: dict[str, Any],
    function_item: dict[str, Any],
    document: dict[str, Any],
) -> str:
    return (
        f"{impl_target(implementation, document)}::"
        f"{function_item['name']}"
    )


def substitute_generic_type(
    value: Any, generic_name: str, replacement: Any
) -> Any:
    if (
        isinstance(value, dict)
        and len(value) == 1
        and value.get("generic") == generic_name
    ):
        return copy.deepcopy(replacement)
    if isinstance(value, dict):
        return {
            key: substitute_generic_type(item, generic_name, replacement)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            substitute_generic_type(item, generic_name, replacement)
            for item in value
        ]
    return value


def apply_blanket_effective_identity(
    row: dict[str, Any],
    implementation: dict[str, Any],
    function_item: dict[str, Any],
    document: dict[str, Any],
) -> None:
    impl_body = implementation["inner"]["impl"]
    blanket_self = impl_body.get("blanket_impl")
    if blanket_self is None:
        return
    if (
        not isinstance(blanket_self, dict)
        or len(blanket_self) != 1
        or not isinstance(blanket_self.get("generic"), str)
    ):
        raise ValueError(
            "unsupported blanket impl identity on "
            f"item {implementation['id']}"
        )
    trait_value = impl_body.get("trait")
    if not isinstance(trait_value, dict):
        raise ValueError(
            f"blanket impl {implementation['id']} has no trait"
        )

    generic_name = blanket_self["generic"]
    effective_self = impl_body["for"]
    effective_trait = substitute_generic_type(
        trait_value, generic_name, effective_self
    )
    effective_function = substitute_generic_type(
        function_item["inner"]["function"],
        generic_name,
        effective_self,
    )
    implementation_generics = impl_body["generics"]
    effective_generics = {
        **implementation_generics,
        "params": [
            parameter
            for parameter in implementation_generics.get("params", [])
            if parameter.get("name") != generic_name
        ],
        "where_predicates": substitute_generic_type(
            implementation_generics.get("where_predicates", []),
            generic_name,
            effective_self,
        ),
    }
    implementation_shape = {
        "function": function_item["inner"]["function"],
        "implementation_generics": implementation_generics,
        "self_type": blanket_self,
        "trait": trait_value,
    }
    effective_shape = {
        "function": effective_function,
        "implementation_generics": effective_generics,
        "self_type": effective_self,
        "trait": effective_trait,
    }
    effective_item = copy.deepcopy(function_item)
    effective_item["inner"]["function"] = effective_function
    implementation_self_type = render_type(blanket_self, document)
    implementation_trait = render_path(trait_value, document)
    effective_self_type = render_type(effective_self, document)
    effective_trait_name = render_path(effective_trait, document)
    method_name = str(function_item["name"])
    row.update(
        {
            "blanket_implementation_self_type": implementation_self_type,
            "blanket_implementation_signature": row["signature"],
            "blanket_implementation_signature_shape_sha256": json_sha256(
                implementation_shape
            ),
            "blanket_implementation_target": (
                f"<{implementation_self_type} as "
                f"{implementation_trait}>::{method_name}"
            ),
            "blanket_implementation_trait": implementation_trait,
            "signature": render_signature(effective_item, document),
            "signature_shape": effective_shape,
            "signature_shape_sha256": json_sha256(effective_shape),
            "target": (
                f"<{effective_self_type} as "
                f"{effective_trait_name}>::{method_name}"
            ),
            "trait": effective_trait_name,
        }
    )


def function_row(
    parent: dict[str, Any],
    implementation: dict[str, Any],
    function_item: dict[str, Any],
    document: dict[str, Any],
    rustdoc_hash: str,
) -> dict[str, Any]:
    function = function_item["inner"]["function"]
    span = function_item.get("span")
    if not isinstance(span, dict):
        raise ValueError(f"function {function_item['id']} lacks a span")
    source_path = canonical_source_path(span)
    excerpt = source_excerpt(source_path, span)
    stability = effective_stability(parent, implementation, function_item)
    impl_kind, trait, self_type = impl_identity(
        implementation, document
    )
    derived = automatically_derived(implementation)
    shape = {
        "function": function,
        "implementation_generics": implementation["inner"]["impl"][
            "generics"
        ],
        "self_type": implementation["inner"]["impl"]["for"],
        "trait": implementation["inner"]["impl"].get("trait"),
    }
    return {
        "api_owner": path_for_id(
            document,
            parent["id"],
            f"core::result::{parent['name']}",
        ),
        "derive_expansion_status": (
            "required_pending" if derived else "not_applicable"
        ),
        "disposition": "pending",
        "frozen_source_path": str(
            frozen_source_path(source_path).relative_to(ROOT)
        ),
        "impl_kind": impl_kind,
        "implementation_rustdoc_id": implementation["id"],
        "is_async": function["header"]["is_async"],
        "is_const": function["header"]["is_const"],
        "is_unsafe": function["header"]["is_unsafe"],
        "method_name": function_item["name"],
        "parent_rustdoc_id": parent["id"],
        "pending_reason": (
            "exact-vstd full-signature audit and generated-contract work "
            "not started"
        ),
        "rustdoc_item_id": function_item["id"],
        "rustdoc_json_sha256": rustdoc_hash,
        "self_type": self_type,
        "signature": render_signature(function_item, document),
        "signature_shape": shape,
        "signature_shape_sha256": json_sha256(shape),
        "source_body_kind": (
            "rustc_derive_expansion_required"
            if derived
            else "exact_rust_source_body"
        ),
        "source_end_column": span["end"][1],
        "source_end_line": span["end"][0],
        "source_excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
        "source_file_sha256": sha256(source_path),
        "source_path": str(source_path),
        "source_start_column": span["begin"][1],
        "source_start_line": span["begin"][0],
        "stability": stability["level"],
        "stability_attribute": stability["attribute"],
        "stability_basis": stability["basis"],
        "stability_feature": stability["feature"],
        "stability_since": stability["since"],
        "target": canonical_target(
            implementation, function_item, document
        ),
        "trait": trait,
    }


def exclusion_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    reason = row.get("exclusion_reason")
    if reason == "inherited_default_trait_method_owned_by_defining_trait":
        return (
            "inherited_default",
            row.get("implementation_rustdoc_id"),
            row.get("method_name"),
        )
    if row.get("item_kind") == "implementation":
        return ("implementation", row.get("implementation_rustdoc_id"))
    implementation_id = row.get("implementation_rustdoc_id")
    if isinstance(implementation_id, int):
        return (
            "implementation_item",
            implementation_id,
            row.get("rustdoc_item_id"),
            row.get("method_name"),
            row.get("signature_shape_sha256"),
        )
    return (
        "rustdoc_item",
        row.get("rustdoc_item_id"),
        reason,
    )


def inventory_partition_errors(
    inventory: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    stable_targets = [row.get("target") for row in inventory]
    exclusion_targets = [row.get("target") for row in exclusions]
    stable_ids = [
        row.get("rustdoc_item_id")
        for row in inventory
        if isinstance(row.get("rustdoc_item_id"), int)
    ]
    identities = [exclusion_identity(row) for row in exclusions]
    if any(
        not isinstance(target, str) or not target
        for target in stable_targets
    ):
        errors.append("stable inventory contains an invalid target")
    if any(
        not isinstance(target, str) or not target
        for target in exclusion_targets
    ):
        errors.append("exclusion ledger contains an invalid target")
    if any(count > 1 for count in Counter(stable_targets).values()):
        errors.append("duplicate canonical stable targets")
    if any(count > 1 for count in Counter(stable_ids).values()):
        errors.append("duplicate stable executable rustdoc item ids")
    if any(count > 1 for count in Counter(exclusion_targets).values()):
        errors.append("duplicate canonical exclusion targets")
    if any(count > 1 for count in Counter(identities).values()):
        errors.append("duplicate exclusion identities")
    if set(stable_targets) & set(exclusion_targets):
        errors.append("stable and excluded target sets overlap")
    return errors


def collect_inventory(
    document: dict[str, Any], rustdoc_hash: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    module_ids = [
        int(item_id)
        for item_id, path in document["paths"].items()
        if path.get("path") == MODULE_PATH and path.get("kind") == "module"
    ]
    if len(module_ids) != 1:
        raise ValueError(
            f"expected one core::result module, found {module_ids}"
        )
    module = item_for(document, module_ids[0])
    parent_ids = module["inner"]["module"]["items"]
    inventory: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    counters = {
        "attached_function_bodies": 0,
        "blanket_impl_function_exclusions": 0,
        "declaration_exclusions": 0,
        "implementation_declaration_exclusions": 0,
        "inherited_default_method_exclusions": 0,
        "non_executable_associated_item_exclusions": 0,
        "non_public_inherent_method_exclusions": 0,
        "synthetic_impl_function_exclusions": 0,
        "unstable_function_exclusions": 0,
        "unknown_stability_function_exclusions": 0,
    }

    for parent_id in parent_ids:
        parent = item_for(document, parent_id)
        parent_path = path_for_id(
            document, parent_id, f"core::result::{parent.get('name')}"
        )
        parent_stability = own_stability(parent)
        exclusions.append(
            {
                "api_owner": parent_path,
                "exclusion_reason": (
                    "unstable_non_executable_declaration"
                    if parent_stability
                    and parent_stability["level"] == "unstable"
                    else "non_executable_declaration"
                ),
                "item_kind": inner_kind(parent),
                "rustdoc_item_id": parent_id,
                "source_path": str(canonical_source_path(parent["span"])),
                "source_start_line": parent["span"]["begin"][0],
                "target": parent_path,
            }
        )
        counters["declaration_exclusions"] += 1

        if inner_kind(parent) == "enum":
            for variant_id in parent["inner"]["enum"].get("variants", []):
                variant = item_for(document, variant_id)
                exclusions.append(
                    {
                        "api_owner": parent_path,
                        "exclusion_reason": (
                            "enum_variant_constructor_has_no_independent_"
                            "function_body"
                        ),
                        "item_kind": "variant",
                        "rustdoc_item_id": variant_id,
                        "source_path": str(
                            canonical_source_path(variant["span"])
                        ),
                        "source_start_line": variant["span"]["begin"][0],
                        "target": f"{parent_path}::{variant['name']}",
                    }
                )
                counters["declaration_exclusions"] += 1

        for implementation_id in impl_ids(parent):
            implementation = item_for(document, implementation_id)
            impl_body = implementation["inner"]["impl"]
            impl_kind, trait, self_type = impl_identity(
                implementation, document
            )
            exclusion_prefix = {
                "api_owner": parent_path,
                "impl_kind": impl_kind,
                "implementation_rustdoc_id": implementation_id,
                "self_type": self_type,
                "trait": trait,
            }
            associated_ids = impl_body.get("items", [])
            function_ids = [
                associated_id
                for associated_id in associated_ids
                if inner_kind(item_for(document, associated_id))
                == "function"
            ]
            if not function_ids:
                stability = effective_stability(parent, implementation)
                if impl_body.get("is_synthetic"):
                    reason = "synthetic_auto_trait_impl_declaration"
                elif stability["level"] == "unstable":
                    reason = "unstable_non_executable_impl_declaration"
                elif impl_body.get("blanket_impl") is not None:
                    reason = (
                        "blanket_impl_declaration_owned_outside_core_result"
                    )
                else:
                    reason = "non_executable_impl_declaration"
                span = implementation.get("span")
                exclusions.append(
                    {
                        **exclusion_prefix,
                        "exclusion_reason": reason,
                        "item_kind": "implementation",
                        "rustdoc_item_id": "",
                        "source_path": (
                            str(canonical_source_path(span))
                            if isinstance(span, dict)
                            else ""
                        ),
                        "source_start_line": (
                            span["begin"][0]
                            if isinstance(span, dict)
                            else ""
                        ),
                        "stability": stability["level"],
                        "stability_basis": stability["basis"],
                        "stability_feature": stability["feature"],
                        "target": impl_target(implementation, document),
                    }
                )
                counters["implementation_declaration_exclusions"] += 1

            concrete_method_names = {
                associated.get("name")
                for associated_id in associated_ids
                for associated in [item_for(document, associated_id)]
                if inner_kind(associated) == "function"
            }
            for provided_name in impl_body.get(
                "provided_trait_methods", []
            ):
                if provided_name in concrete_method_names:
                    continue
                exclusions.append(
                    {
                        **exclusion_prefix,
                        "exclusion_reason": (
                            "inherited_default_trait_method_owned_by_"
                            "defining_trait"
                        ),
                        "item_kind": "provided_trait_method",
                        "method_name": provided_name,
                        "rustdoc_item_id": "",
                        "source_path": "",
                        "source_start_line": "",
                        "target": (
                            f"{impl_target(implementation, document)}::"
                            f"{provided_name}"
                        ),
                    }
                )
                counters["inherited_default_method_exclusions"] += 1

            for associated_id in associated_ids:
                associated = item_for(document, associated_id)
                if inner_kind(associated) != "function":
                    target = (
                        f"{impl_target(implementation, document)}::"
                        f"{associated.get('name')}"
                    )
                    exclusions.append(
                        {
                            **exclusion_prefix,
                            "exclusion_reason": (
                                "non_executable_associated_item"
                            ),
                            "item_kind": inner_kind(associated),
                            "method_name": associated.get("name"),
                            "rustdoc_item_id": associated_id,
                            "source_path": (
                                str(
                                    canonical_source_path(
                                        associated["span"]
                                    )
                                )
                                if associated.get("span")
                                else ""
                            ),
                            "source_start_line": (
                                associated["span"]["begin"][0]
                                if associated.get("span")
                                else ""
                            ),
                            "target": target,
                        }
                    )
                    counters[
                        "non_executable_associated_item_exclusions"
                    ] += 1
                    continue

                counters["attached_function_bodies"] += 1
                row = function_row(
                    parent,
                    implementation,
                    associated,
                    document,
                    rustdoc_hash,
                )
                apply_blanket_effective_identity(
                    row, implementation, associated, document
                )
                reason = None
                if impl_body.get("is_synthetic"):
                    reason = "synthetic_impl_method"
                    counters[
                        "synthetic_impl_function_exclusions"
                    ] += 1
                elif impl_body.get("blanket_impl") is not None:
                    reason = (
                        "blanket_impl_method_owned_outside_core_result"
                    )
                    counters["blanket_impl_function_exclusions"] += 1
                elif not associated["inner"]["function"].get("has_body"):
                    reason = "non_executable_trait_declaration"
                elif (
                    impl_kind == "inherent"
                    and associated.get("visibility") != "public"
                ):
                    reason = "non_public_inherent_method"
                    counters["non_public_inherent_method_exclusions"] += 1
                elif row["stability"] == "unstable":
                    reason = "unstable_api"
                    counters["unstable_function_exclusions"] += 1
                elif row["stability"] != "stable":
                    reason = "unknown_stability"
                    counters[
                        "unknown_stability_function_exclusions"
                    ] += 1

                if reason is None:
                    inventory.append(row)
                else:
                    exclusions.append(
                        {
                            **{
                                key: value
                                for key, value in row.items()
                                if key != "signature_shape"
                            },
                            "disposition": "excluded",
                            "exclusion_reason": reason,
                            "item_kind": "function",
                        }
                    )

    inventory.sort(
        key=lambda row: (
            row["source_path"],
            row["source_start_line"],
            row["target"],
            row["rustdoc_item_id"],
        )
    )
    exclusions.sort(
        key=lambda row: (
            str(row.get("source_path", "")),
            str(row.get("source_start_line", "")),
            row["target"],
            str(row.get("rustdoc_item_id", "")),
        )
    )
    return inventory, exclusions, counters


def validate_pins() -> dict[str, Any]:
    missing = [
        str(path)
        for path, _ in EXPECTED_HASHES.values()
        if not path.is_file()
    ]
    if missing:
        raise ValueError(f"missing pinned inputs: {missing}")
    observed_hashes = {
        name: {
            "expected_sha256": expected,
            "observed_sha256": sha256(path),
            "path": str(path),
        }
        for name, (path, expected) in EXPECTED_HASHES.items()
    }
    mismatches = [
        name
        for name, values in observed_hashes.items()
        if values["observed_sha256"] != values["expected_sha256"]
    ]
    if mismatches:
        raise ValueError(f"pinned input hash mismatch: {mismatches}")

    rust_head = run(["git", "rev-parse", "HEAD"], RUST_ROOT)
    rust_status = run(["git", "status", "--short"], RUST_ROOT)
    verus_head = run(["git", "rev-parse", "HEAD"], VERUS_ROOT)
    verus_status = run(["git", "status", "--short"], VERUS_ROOT)
    rustc = run(["rustc", "+1.96.0", "--version", "--verbose"])
    cargo = run(["cargo", "+1.96.0", "--version"])
    verus = run([str(VERUS_BINARY), "--version"])
    z3 = run([str(Z3_BINARY), "--version"])
    for label, result in (
        ("Rust HEAD", rust_head),
        ("Rust status", rust_status),
        ("Verus HEAD", verus_head),
        ("Verus status", verus_status),
        ("rustc", rustc),
        ("cargo", cargo),
        ("Verus", verus),
        ("Z3", z3),
    ):
        require_success(result, label)

    if rust_head["stdout"].strip() != EXPECTED_RUST_COMMIT:
        raise ValueError("canonical Rust commit does not match the pin")
    if rust_status["stdout"]:
        raise ValueError("canonical Rust 1.96 checkout is not clean")
    if verus_head["stdout"].strip() != EXPECTED_VERUS_COMMIT:
        raise ValueError("canonical Verus commit does not match the pin")
    rustc_commit = re.search(
        r"^commit-hash:\s*(\w+)$", rustc["stdout"], re.MULTILINE
    )
    if (
        rustc_commit is None
        or rustc_commit.group(1) != EXPECTED_RUST_COMMIT
    ):
        raise ValueError("Rust source and rustc 1.96.0 do not match")
    if not cargo["stdout"].startswith("cargo 1.96.0 "):
        raise ValueError("cargo 1.96.0 is not active")
    if "0.2026.07.21.1beb0fa.dirty" not in verus["stdout"]:
        raise ValueError("Verus version does not match the campaign pin")
    if "Z3 version 4.12.5" not in z3["stdout"]:
        raise ValueError("Z3 version does not match the campaign pin")
    return {
        "cargo": cargo,
        "hashes": observed_hashes,
        "rust": {
            "commit": rust_head["stdout"].strip(),
            "status": rust_status,
        },
        "rustc": rustc,
        "verus": {
            "commit": verus_head["stdout"].strip(),
            "status": verus_status,
            "version": verus,
        },
        "z3": z3,
    }


def main() -> int:
    pins = validate_pins()
    generated_at = datetime.now(timezone.utc).isoformat()
    source_inputs = [
        copy_input(
            RESULT_SOURCE,
            ROOT
            / "provenance"
            / "rust-source"
            / "library"
            / "core"
            / "src"
            / "result.rs",
            "authoritative_rust_1_96_module_source",
        ),
        copy_input(
            ACCUM_SOURCE,
            ROOT
            / "provenance"
            / "rust-source"
            / "library"
            / "core"
            / "src"
            / "iter"
            / "traits"
            / "accum.rs",
            "authoritative_rust_1_96_external_result_impl_source",
        ),
        copy_input(
            CORE_LIB_SOURCE,
            ROOT
            / "provenance"
            / "rust-source"
            / "library"
            / "core"
            / "src"
            / "lib.rs",
            "core_result_module_reachability_source",
        ),
        copy_input(
            CORE_PRELUDE_SOURCE,
            ROOT
            / "provenance"
            / "rust-source"
            / "library"
            / "core"
            / "src"
            / "prelude"
            / "v1.rs",
            "core_result_prelude_reexport_source",
        ),
        copy_input(
            STD_LIB_SOURCE,
            ROOT
            / "provenance"
            / "rust-source"
            / "library"
            / "std"
            / "src"
            / "lib.rs",
            "std_result_reexport_source",
        ),
        copy_input(
            RUSTDOC_ORIGIN,
            RUSTDOC_JSON,
            "authoritative_rust_1_96_rustdoc_json",
        ),
        copy_input(
            VSTD_RESULT,
            ROOT / "provenance" / "vstd" / "std_specs" / "result.rs",
            "current_vstd_result_exact_contract_audit_input",
        ),
        copy_input(
            VSTD_MODULE,
            ROOT / "provenance" / "vstd" / "std_specs" / "mod.rs",
            "current_vstd_module_loading_evidence",
        ),
        copy_input(
            PROCESS_DOCUMENT,
            ROOT
            / "provenance"
            / "methodology"
            / "rust-std-lib-specgen-process.md",
            "authoritative_specgen_process",
        ),
        copy_input(
            TRUST_AUDIT,
            ROOT
            / "provenance"
            / "methodology"
            / "TRUST_BOUNDARY_AUDIT.md",
            "authoritative_trust_accounting_methodology",
        ),
    ]
    source_inputs.sort(key=lambda row: row["copied_path"])

    document = load_json(RUSTDOC_JSON)
    if not isinstance(document, dict):
        raise ValueError("rustdoc JSON is not an object")
    if document.get("format_version") != 57:
        raise ValueError(
            f"unexpected rustdoc format: {document.get('format_version')}"
        )
    rustdoc_hash = sha256(RUSTDOC_JSON)
    inventory, exclusions, counters = collect_inventory(
        document, rustdoc_hash
    )
    errors = inventory_partition_errors(inventory, exclusions)
    if errors:
        raise ValueError("; ".join(errors))
    if any(row["stability"] != "stable" for row in inventory):
        raise ValueError("non-stable row entered the stable inventory")

    by_impl_kind = Counter(row["impl_kind"] for row in inventory)
    by_source_kind = Counter(
        row["source_body_kind"] for row in inventory
    )
    live_total = len(inventory)
    inherent_total = by_impl_kind["inherent"]
    trait_total = by_impl_kind["trait"]
    historical_reconciliation = {
        "difference_from_older_reported_count": (
            live_total - HISTORICAL_REPORTED_ROWS
        ),
        "live_concrete_trait_method_rows": trait_total,
        "live_inherent_method_rows": inherent_total,
        "live_inventory_total": live_total,
        "numeric_relationship": (
            "The older reported count numerically matches the freshly "
            "derived inherent-method subtotal; the current inventory also "
            "accounts for every stable concrete trait method attached to "
            "Result and its public helper iterator types."
            if inherent_total == HISTORICAL_REPORTED_ROWS
            else "The older reported count does not match the freshly "
            "derived inherent-method subtotal."
        ),
        "older_campaign_artifacts_imported": False,
        "older_campaign_reported_rows": HISTORICAL_REPORTED_ROWS,
        "older_count_used_as_acceptance_criterion": False,
        "trait_rows_accounting_for_numeric_difference": [
            row["target"]
            for row in inventory
            if row["impl_kind"] == "trait"
        ],
    }
    summary = {
        **counters,
        "derived_body_rows": by_source_kind[
            "rustc_derive_expansion_required"
        ],
        "exact_rust_source_body_rows": by_source_kind[
            "exact_rust_source_body"
        ],
        "exact_vstd": 0,
        "excluded_rows_total": len(exclusions),
        "generated": 0,
        "generated_at_utc": generated_at,
        "genuinely_impossible": 0,
        "historical_reconciliation": historical_reconciliation,
        "module": "core::result",
        "pending": live_total,
        "specified_total": 0,
        "stable_inherent_method_rows": inherent_total,
        "stable_inventory_total": live_total,
        "stable_trait_method_rows": trait_total,
        "strict_specification_coverage": 0.0,
    }
    inventory_payload = {
        "derivation": {
            "blanket_implementations": (
                "Effective signatures are rendered against each Result "
                "type, then excluded because the executable body is owned "
                "by the defining blanket implementation outside "
                "core::result."
            ),
            "default_trait_methods": (
                "Inherited defaults are excluded as APIs owned by their "
                "defining traits; concrete overrides supplied by a "
                "Result-owned implementation remain selected."
            ),
            "derived_methods": (
                "Stable executable methods from compiler-generated impls "
                "are selected and marked as requiring pinned derive "
                "expansion before implementation-proof work."
            ),
            "enum_variants": (
                "Ok and Err are datatype variant constructors without "
                "independent function bodies; they are recorded in the "
                "exclusion ledger and remain part of the Result datatype "
                "semantic model."
            ),
            "executable_rule": (
                "A Rustdoc function item with has_body=true in a "
                "non-synthetic, non-blanket implementation attached to a "
                "direct public core::result type, stable under main "
                "Stability metadata."
            ),
            "scope_rule": (
                "Direct public children of the core::result rustdoc module, "
                "including inherent methods, concrete trait methods, "
                "public helper iterators, derived methods, and Sum/Product "
                "bodies located in core::iter::traits::accum."
            ),
            "stability_rule": (
                "Main Stability metadata inherited through parent type and "
                "implementation controls inclusion; const-stability does "
                "not alter API stability."
            ),
        },
        "reexport_surface": [
            "core::result",
            "core prelude Result/Ok/Err",
            "std::result",
            "std prelude Result/Ok/Err",
        ],
        "rows": inventory,
        "schema_version": 1,
        "summary": summary,
    }
    exclusion_payload = {
        "rows": exclusions,
        "schema_version": 1,
        "summary": {"count": len(exclusions), **counters},
    }
    toolchain = {
        "commands": {
            "inventory_generation": [
                sys.executable,
                "tools/build_inventory.py",
            ],
            "rustdoc_reproduction": {
                "command": RUSTDOC_REPRODUCTION_COMMAND,
                "executed_this_increment": False,
                "input_used": str(RUSTDOC_ORIGIN),
            },
        },
        "environment": {
            "cwd": str(ROOT),
            "locale": os.environ.get("LC_ALL")
            or os.environ.get("LANG", ""),
            "machine": platform.machine(),
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "generated_at_utc": generated_at,
        "input_policy": {
            "inventory_count_derived_from": (
                "pinned Rust 1.96 rustdoc JSON, main Stability metadata, "
                "and exact source spans"
            ),
            "older_campaign_artifacts_used": [],
            "vstd_dependency_closure_status": (
                "pending independent exact-vstd closure audit"
            ),
        },
        "pins": pins,
        "rustdoc": {
            "format_version": document["format_version"],
            "frozen_path": str(RUSTDOC_JSON.relative_to(ROOT)),
            "origin_path": str(RUSTDOC_ORIGIN),
            "sha256": rustdoc_hash,
            "size": RUSTDOC_JSON.stat().st_size,
        },
        "schema_version": 1,
        "status": "passed",
    }

    inventory_fields = [
        "target",
        "disposition",
        "pending_reason",
        "api_owner",
        "impl_kind",
        "trait",
        "self_type",
        "method_name",
        "signature",
        "stability",
        "stability_since",
        "stability_feature",
        "stability_basis",
        "is_const",
        "is_unsafe",
        "is_async",
        "source_body_kind",
        "derive_expansion_status",
        "source_path",
        "frozen_source_path",
        "source_start_line",
        "source_start_column",
        "source_end_line",
        "source_end_column",
        "source_file_sha256",
        "source_excerpt_sha256",
        "parent_rustdoc_id",
        "implementation_rustdoc_id",
        "rustdoc_item_id",
        "signature_shape_sha256",
        "rustdoc_json_sha256",
    ]
    exclusion_fields = [
        "target",
        "exclusion_reason",
        "item_kind",
        "api_owner",
        "impl_kind",
        "trait",
        "self_type",
        "method_name",
        "blanket_implementation_target",
        "blanket_implementation_self_type",
        "blanket_implementation_trait",
        "blanket_implementation_signature",
        "blanket_implementation_signature_shape_sha256",
        "stability",
        "stability_feature",
        "stability_basis",
        "source_path",
        "source_start_line",
        "parent_rustdoc_id",
        "implementation_rustdoc_id",
        "rustdoc_item_id",
    ]
    manifest_fields = [
        "source_path",
        "copied_path",
        "role",
        "size",
        "sha256",
        "source_sha256",
    ]
    write_json(
        ROOT / "inventory" / "core_result_exec_fn_inventory.json",
        inventory_payload,
    )
    write_csv(
        ROOT / "inventory" / "core_result_exec_fn_inventory.csv",
        inventory,
        inventory_fields,
    )
    write_json(
        ROOT / "inventory" / "core_result_exclusions.json",
        exclusion_payload,
    )
    write_csv(
        ROOT / "inventory" / "core_result_exclusions.csv",
        exclusions,
        exclusion_fields,
    )
    write_json(ROOT / "inventory" / "coverage_summary.json", summary)
    write_json(ROOT / "provenance" / "toolchain.json", toolchain)
    write_json(
        ROOT / "provenance" / "source_manifest.json",
        {
            "generated_at_utc": generated_at,
            "rows": source_inputs,
            "schema_version": 1,
        },
    )
    write_csv(
        ROOT / "provenance" / "source_manifest.csv",
        source_inputs,
        manifest_fields,
    )
    print(
        json.dumps(
            {
                "excluded": len(exclusions),
                "inherent": inherent_total,
                "module": "core::result",
                "stable_inventory_total": live_total,
                "status": "passed",
                "trait": trait_total,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
