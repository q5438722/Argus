#!/usr/bin/env python3
"""Subtract loaded vstd declarations using complete semantic signatures."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    ROOT / "inventory" / "core_result_exec_fn_inventory.json"
)
INVENTORY_CSV_PATH = (
    ROOT / "inventory" / "core_result_exec_fn_inventory.csv"
)
EXCLUSIONS_PATH = ROOT / "inventory" / "core_result_exclusions.json"
SUMMARY_PATH = ROOT / "inventory" / "coverage_summary.json"
CLOSURE_ROOT = (
    ROOT
    / "provenance"
    / "vstd-dependency-closure"
    / "source"
    / "vstd"
)
VSTD_ENTRYPOINT = CLOSURE_ROOT / "vstd.rs"
VSTD_MODULE = CLOSURE_ROOT / "std_specs" / "mod.rs"
VSTD_RESULT = CLOSURE_ROOT / "std_specs" / "result.rs"
VSTD_CONTROL_FLOW = CLOSURE_ROOT / "std_specs" / "control_flow.rs"
CLOSURE_MANIFEST = ROOT / "provenance" / "vstd_dependency_closure.json"
CLOSURE_AUDIT = (
    ROOT / "provenance" / "vstd_dependency_closure_independent_audit.json"
)
OUTPUT_PATH = ROOT / "inventory" / "exact_vstd_audit.json"

ASSUME_SPECIFICATION = re.compile(r"\bpub\s+assume_specification\b")
PATH_ALIASES = {
    "$crate::": "core::",
    "core::clone::Clone": "Clone",
    "core::cmp::Ord": "Ord",
    "core::cmp::Ordering": "Ordering",
    "core::cmp::PartialEq": "PartialEq",
    "core::cmp::PartialOrd": "PartialOrd",
    "core::convert::Infallible": "Infallible",
    "core::fmt::Debug": "Debug",
    "core::hash::Hash": "Hash",
    "core::hash::Hasher": "Hasher",
    "core::option::Option": "Option",
    "core::ops::function::FnOnce": "FnOnce",
    "core::result::Result": "Result",
    "cmp::Ordering": "Ordering",
    "fmt::Debug": "Debug",
}
COMPARE_FIELDS = (
    "abi",
    "async",
    "bounds",
    "const_parameters",
    "inputs",
    "method",
    "output",
    "receiver",
    "self_type",
    "trait",
    "type_parameters",
    "unsafe",
    "variadic",
)
AUDIT_COLUMNS = (
    "exact_vstd_audit_status",
    "exact_vstd_declaration_id",
    "exact_vstd_declaration_start_line",
    "exact_vstd_signature_shape_sha256",
    "exact_vstd_source_path",
    "exact_vstd_source_sha256",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
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


def skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def matching_delimiter(
    text: str, start: int, opening: str, closing: str
) -> int:
    if start >= len(text) or text[start] != opening:
        raise ValueError(f"expected {opening!r} at source offset {start}")
    depth = 0
    for position in range(start, len(text)):
        character = text[position]
        if character == opening:
            depth += 1
        elif character == closing:
            if closing == ">" and position > 0 and text[position - 1] == "-":
                continue
            depth -= 1
            if depth == 0:
                return position
    raise ValueError(f"unterminated {opening!r} at source offset {start}")


def split_top_level(text: str, delimiter: str) -> list[str]:
    depths = {"(": 0, "[": 0, "{": 0, "<": 0}
    closing = {")": "(", "]": "[", "}": "{", ">": "<"}
    pieces: list[str] = []
    start = 0
    for position, character in enumerate(text):
        if character in depths:
            depths[character] += 1
        elif character in closing:
            if (
                character == ">"
                and position > 0
                and text[position - 1] == "-"
            ):
                continue
            key = closing[character]
            if depths[key] > 0:
                depths[key] -= 1
        elif character == delimiter and not any(depths.values()):
            pieces.append(text[start:position].strip())
            start = position + 1
    pieces.append(text[start:].strip())
    return pieces


def top_level_colon(text: str) -> int | None:
    depths = {"(": 0, "[": 0, "{": 0, "<": 0}
    closing = {")": "(", "]": "[", "}": "{", ">": "<"}
    for position, character in enumerate(text):
        if character in depths:
            depths[character] += 1
        elif character in closing:
            if (
                character == ">"
                and position > 0
                and text[position - 1] == "-"
            ):
                continue
            key = closing[character]
            if depths[key] > 0:
                depths[key] -= 1
        elif (
            character == ":"
            and not any(depths.values())
            and (position == 0 or text[position - 1] != ":")
            and (position + 1 == len(text) or text[position + 1] != ":")
        ):
            return position
    return None


def canonical_text(text: str, erase_lifetimes: bool = True) -> str:
    value = text.strip()
    for source, replacement in sorted(
        PATH_ALIASES.items(), key=lambda pair: len(pair[0]), reverse=True
    ):
        value = value.replace(source, replacement)
    value = re.sub(r"::\s*(?=<)", "", value)
    tokens = re.findall(
        r"'[A-Za-z_][A-Za-z0-9_]*|::|->|"
        r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\s]",
        value,
    )
    normalized: list[str] = []
    for token in tokens:
        if token.startswith("'") and token != "'static":
            if erase_lifetimes:
                continue
            token = "'_"
        normalized.append(token)
    result = "".join(normalized)
    if erase_lifetimes:
        previous = None
        while previous != result:
            previous = result
            result = (
                result.replace("<,", "<")
                .replace("(,", "(")
                .replace("[,", "[")
                .replace(",,", ",")
                .replace(",>", ">")
                .replace(",)", ")")
                .replace(",]", "]")
            )
        result = result.replace("<>", "")
    return result


def render_constant(value: Any, self_type: Any = None) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("expr", "value"):
            if isinstance(value.get(key), str):
                return value[key]
        if "type" in value:
            return render_rust_type(value["type"], self_type)
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_generic_argument(value: Any, self_type: Any = None) -> str:
    if not isinstance(value, dict):
        return str(value)
    if "lifetime" in value:
        return str(value["lifetime"])
    if "type" in value:
        return render_rust_type(value["type"], self_type)
    if "const" in value:
        return render_constant(value["const"], self_type)
    if "infer" in value:
        return "_"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_rust_bound(value: Any, self_type: Any = None) -> str:
    if not isinstance(value, dict):
        return str(value)
    if "trait_bound" in value:
        return render_rust_path(value["trait_bound"]["trait"], self_type)
    if "outlives" in value:
        return str(value["outlives"])
    if "use" in value:
        return "use<" + ",".join(map(str, value["use"])) + ">"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_generic_args(value: Any, self_type: Any = None) -> str:
    if value is None:
        return ""
    if "angle_bracketed" in value:
        body = value["angle_bracketed"]
        arguments = [
            render_generic_argument(argument, self_type)
            for argument in body.get("args", [])
        ]
        for constraint in body.get("constraints", []):
            name = constraint.get("name", "?")
            binding = constraint.get("binding", {})
            if "equality" in binding:
                equality = binding["equality"]
                rendered = (
                    render_rust_type(equality["type"], self_type)
                    if "type" in equality
                    else render_constant(equality.get("constant"), self_type)
                )
                arguments.append(f"{name}={rendered}")
            elif "constraint" in binding:
                bounds = binding["constraint"].get("bounds", [])
                rendered = "+".join(
                    render_rust_bound(bound, self_type) for bound in bounds
                )
                arguments.append(f"{name}:{rendered}")
        return "<" + ",".join(arguments) + ">" if arguments else ""
    if "parenthesized" in value:
        body = value["parenthesized"]
        inputs = ",".join(
            render_rust_type(argument, self_type)
            for argument in body.get("inputs", [])
        )
        output = body.get("output")
        suffix = (
            f"->{render_rust_type(output, self_type)}"
            if output is not None
            else ""
        )
        return f"({inputs}){suffix}"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def render_rust_path(value: Any, self_type: Any = None) -> str:
    if not isinstance(value, dict):
        return str(value)
    path = str(value.get("path", "?"))
    return path + render_generic_args(value.get("args"), self_type)


def render_rust_type(value: Any, self_type: Any = None) -> str:
    if value is None:
        return "()"
    if not isinstance(value, dict) or len(value) != 1:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    kind, body = next(iter(value.items()))
    if kind == "generic":
        if body == "Self" and self_type is not None:
            return render_rust_type(self_type)
        return str(body)
    if kind == "primitive":
        return str(body)
    if kind == "resolved_path":
        return render_rust_path(body, self_type)
    if kind == "borrowed_ref":
        lifetime = f"{body['lifetime']} " if body.get("lifetime") else ""
        mutable = "mut " if body.get("is_mutable") else ""
        return (
            f"&{lifetime}{mutable}"
            f"{render_rust_type(body['type'], self_type)}"
        )
    if kind == "raw_pointer":
        mutable = "mut" if body.get("is_mutable") else "const"
        return f"*{mutable} {render_rust_type(body['type'], self_type)}"
    if kind == "slice":
        return f"[{render_rust_type(body, self_type)}]"
    if kind == "array":
        return (
            f"[{render_rust_type(body['type'], self_type)};"
            f"{render_constant(body['len'], self_type)}]"
        )
    if kind == "tuple":
        rendered = [
            render_rust_type(item, self_type) for item in body
        ]
        suffix = "," if len(rendered) == 1 else ""
        return "(" + ",".join(rendered) + suffix + ")"
    if kind == "qualified_path":
        return (
            f"<{render_rust_type(body['self_type'], self_type)} as "
            f"{render_rust_path(body['trait'], self_type)}>::"
            f"{body['name']}"
            f"{render_generic_args(body.get('args'), self_type)}"
        )
    if kind == "impl_trait":
        return "impl " + "+".join(
            render_rust_bound(bound, self_type) for bound in body
        )
    if kind == "dyn_trait":
        traits = [
            render_rust_path(trait["trait"], self_type)
            for trait in body.get("traits", [])
        ]
        if body.get("lifetime"):
            traits.append(str(body["lifetime"]))
        return "dyn " + "+".join(traits)
    if kind == "function_pointer":
        signature = body.get("sig", {})
        inputs = ",".join(
            render_rust_type(item[1], self_type)
            for item in signature.get("inputs", [])
        )
        output = signature.get("output")
        suffix = (
            f"->{render_rust_type(output, self_type)}"
            if output is not None
            else ""
        )
        return f"fn({inputs}){suffix}"
    if kind == "pat":
        return render_rust_type(body["type"], self_type)
    if kind == "infer":
        return "_"
    if kind == "never":
        return "!"
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def rust_generic_shape(
    implementation_generics: dict[str, Any],
    function_generics: dict[str, Any],
    self_type: Any,
) -> dict[str, Any]:
    type_parameters: list[str] = []
    lifetime_parameters: list[str] = []
    const_parameters: list[str] = []
    bounds: list[str] = []
    bound_modifiers: list[dict[str, str]] = []
    for generic_set in (implementation_generics, function_generics):
        for parameter in generic_set.get("params", []):
            name = str(parameter.get("name"))
            kind = parameter.get("kind", {})
            if "type" in kind:
                if not kind["type"].get("is_synthetic", False):
                    type_parameters.append(name)
                for bound in kind["type"].get("bounds", []):
                    rendered = f"{name}:{render_rust_bound(bound, self_type)}"
                    bounds.append(rendered)
                    if "trait_bound" in bound:
                        bound_modifiers.append(
                            {
                                "bound": canonical_text(rendered),
                                "modifier": str(
                                    bound["trait_bound"].get("modifier")
                                ),
                            }
                        )
            elif "lifetime" in kind:
                lifetime_parameters.append(name)
                for outlives in kind["lifetime"].get("outlives", []):
                    bounds.append(f"{name}:{outlives}")
            elif "const" in kind:
                const_parameters.append(
                    f"{name}:"
                    f"{render_rust_type(kind['const']['type'], self_type)}"
                )
        for predicate in generic_set.get("where_predicates", []):
            if "bound_predicate" in predicate:
                body = predicate["bound_predicate"]
                target = render_rust_type(body["type"], self_type)
                for bound in body.get("bounds", []):
                    rendered = (
                        f"{target}:{render_rust_bound(bound, self_type)}"
                    )
                    bounds.append(rendered)
                    if "trait_bound" in bound:
                        bound_modifiers.append(
                            {
                                "bound": canonical_text(rendered),
                                "modifier": str(
                                    bound["trait_bound"].get("modifier")
                                ),
                            }
                        )
            elif "lifetime_predicate" in predicate:
                body = predicate["lifetime_predicate"]
                for outlives in body.get("outlives", []):
                    bounds.append(f"{body['lifetime']}:{outlives}")
            elif "eq_predicate" in predicate:
                body = predicate["eq_predicate"]
                bounds.append(
                    f"{render_rust_type(body['lhs'], self_type)}="
                    f"{render_rust_type(body['rhs'], self_type)}"
                )
    return {
        "bound_modifiers": sorted(
            bound_modifiers,
            key=lambda row: (row["bound"], row["modifier"]),
        ),
        "bounds": sorted({canonical_text(bound) for bound in bounds}),
        "const_parameters": [
            canonical_text(value) for value in const_parameters
        ],
        "lifetime_parameters": lifetime_parameters,
        "type_parameters": type_parameters,
    }


def rust_signature(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("signature_shape")
    if not isinstance(raw, dict):
        raise ValueError(
            f"inventory row lacks signature shape: {row.get('target')}"
        )
    function = raw["function"]
    self_type_raw = raw["self_type"]
    generics = rust_generic_shape(
        raw["implementation_generics"],
        function["generics"],
        self_type_raw,
    )
    self_type_text = render_rust_type(self_type_raw)
    trait_raw = raw.get("trait")
    trait_text = (
        canonical_text(render_rust_path(trait_raw))
        if trait_raw is not None
        else None
    )
    named_inputs = function["sig"].get("inputs", [])
    inputs_raw = [
        render_rust_type(value, self_type_raw)
        for _, value in named_inputs
    ]
    output_raw = render_rust_type(
        function["sig"].get("output"), self_type_raw
    )
    header = function["header"]
    receiver = (
        canonical_text(inputs_raw[0])
        if named_inputs and named_inputs[0][0] == "self"
        else None
    )
    shape = {
        "abi": header.get("abi"),
        "async": bool(header.get("is_async")),
        "bounds": generics["bounds"],
        "const_parameters": generics["const_parameters"],
        "inputs": [canonical_text(value) for value in inputs_raw],
        "lifetime_parameters": generics["lifetime_parameters"],
        "method": row.get("method_name"),
        "output": canonical_text(output_raw),
        "receiver": receiver,
        "self_type": canonical_text(self_type_text),
        "trait": trait_text,
        "type_parameters": generics["type_parameters"],
        "unsafe": bool(header.get("is_unsafe")),
        "variadic": bool(function["sig"].get("is_c_variadic")),
    }
    raw_types = [self_type_text, *inputs_raw, output_raw]
    return {
        "bound_modifiers": generics["bound_modifiers"],
        "const": bool(header.get("is_const")),
        "lifetime_occurrences": re.findall(
            r"'[A-Za-z_][A-Za-z0-9_]*", " ".join(raw_types)
        ),
        "raw_types": {
            "inputs": inputs_raw,
            "output": output_raw,
            "self_type": self_type_text,
        },
        "shape": shape,
    }


def parse_output_type(text: str) -> str:
    value = text.strip()
    if value.startswith("("):
        end = matching_delimiter(value, 0, "(", ")")
        if end == len(value) - 1:
            inner = value[1:end]
            colon = top_level_colon(inner)
            if colon is not None:
                return inner[colon + 1 :].strip()
    return value


def parse_parameters(text: str) -> list[dict[str, str]]:
    parameters: list[dict[str, str]] = []
    for piece in split_top_level(text, ","):
        if not piece:
            continue
        colon = top_level_colon(piece)
        if colon is None:
            raise ValueError(f"parameter has no top-level colon: {piece!r}")
        parameters.append(
            {
                "name": piece[:colon].strip(),
                "type": piece[colon + 1 :].strip(),
            }
        )
    return parameters


def parse_vstd_generics(text: str) -> dict[str, Any]:
    type_parameters: list[str] = []
    lifetime_parameters: list[str] = []
    const_parameters: list[str] = []
    bounds: list[str] = []
    for piece in split_top_level(text, ","):
        if not piece:
            continue
        if piece.startswith("'"):
            name, _, bound_text = piece.partition(":")
            lifetime_parameters.append(name.strip())
            if bound_text:
                for bound in split_top_level(bound_text, "+"):
                    bounds.append(f"{name.strip()}:{bound}")
            continue
        if piece.startswith("const "):
            body = piece[len("const ") :]
            colon = top_level_colon(body)
            if colon is None:
                raise ValueError(f"const generic has no type: {piece!r}")
            const_parameters.append(
                canonical_text(
                    f"{body[:colon].strip()}:"
                    f"{body[colon + 1:].strip()}"
                )
            )
            continue
        colon = top_level_colon(piece)
        if colon is None:
            type_parameters.append(piece.strip())
            continue
        name = piece[:colon].strip()
        type_parameters.append(name)
        for bound in split_top_level(piece[colon + 1 :], "+"):
            bounds.append(f"{name}:{bound}")
    return {
        "bounds": sorted({canonical_text(bound) for bound in bounds}),
        "const_parameters": const_parameters,
        "lifetime_parameters": lifetime_parameters,
        "type_parameters": type_parameters,
    }


def strip_receiver_reference(value: str) -> str:
    if value.startswith("&mut"):
        return value[len("&mut") :]
    if value.startswith("&"):
        return value[1:]
    return value


def parse_target(
    target: str, parameter_types: list[str]
) -> tuple[str, str | None, str]:
    trait_match = re.match(
        r"^\s*<(?P<self>.+)\s+as\s+(?P<trait>.+)>"
        r"\s*::\s*(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*$",
        target,
        re.DOTALL,
    )
    if trait_match is not None:
        return (
            canonical_text(trait_match.group("self")),
            canonical_text(trait_match.group("trait")),
            trait_match.group("method"),
        )
    inherent_match = re.match(
        r"^\s*(?P<self>.+)\s*::\s*"
        r"(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*$",
        target,
        re.DOTALL,
    )
    if inherent_match is None:
        raise ValueError(
            f"unparseable assume_specification target: {target!r}"
        )
    self_type = canonical_text(inherent_match.group("self"))
    if self_type == "Result":
        if not parameter_types:
            raise ValueError(f"cannot infer bare Result target: {target!r}")
        self_type = strip_receiver_reference(parameter_types[0])
    return self_type, None, inherent_match.group("method")


def receiver_for_vstd(
    self_type: str,
    trait: str | None,
    parameter_types: list[str],
) -> str | None:
    if trait is not None or not parameter_types:
        return None
    first = parameter_types[0]
    if strip_receiver_reference(first) == self_type:
        return first
    return None


def declaration_terminator(source: str, position: int) -> int:
    terminator = source.find(";", position)
    if terminator < 0:
        raise ValueError(
            f"assume_specification lacks terminator after offset {position}"
        )
    return terminator + 1


def parse_declaration(
    source: str,
    match: re.Match[str],
    source_label: str,
) -> dict[str, Any]:
    position = skip_space(source, match.end())
    generic_text = ""
    if position < len(source) and source[position] == "<":
        end = matching_delimiter(source, position, "<", ">")
        generic_text = source[position + 1 : end]
        position = skip_space(source, end + 1)
    if position >= len(source) or source[position] != "[":
        raise ValueError(
            f"assume_specification lacks target at offset {match.start()}"
        )
    target_end = matching_delimiter(source, position, "[", "]")
    target_text = source[position + 1 : target_end].strip()
    position = skip_space(source, target_end + 1)
    if position >= len(source) or source[position] != "(":
        raise ValueError(
            f"assume_specification lacks parameters at offset {match.start()}"
        )
    parameters_end = matching_delimiter(source, position, "(", ")")
    parameters_text = source[position + 1 : parameters_end]
    position = skip_space(source, parameters_end + 1)
    if not source.startswith("->", position):
        raise ValueError(
            f"assume_specification lacks output at offset {match.start()}"
        )
    position = skip_space(source, position + 2)
    output_start = position
    if position < len(source) and source[position] == "(":
        output_end = matching_delimiter(source, position, "(", ")") + 1
    else:
        output_end = position
        while output_end < len(source):
            if source[output_end] in ";\n":
                break
            output_end += 1
    output_text = source[output_start:output_end].strip()
    declaration_end = declaration_terminator(source, output_end)
    parameters = parse_parameters(parameters_text)
    parameter_types = [
        canonical_text(parameter["type"]) for parameter in parameters
    ]
    self_type, trait, method = parse_target(target_text, parameter_types)
    generics = parse_vstd_generics(generic_text)
    output_type = parse_output_type(output_text)
    header_text = source[match.start() : output_end]
    declaration_text = source[match.start() : declaration_end]
    shape = {
        "abi": "Rust",
        "async": False,
        "bounds": generics["bounds"],
        "const_parameters": generics["const_parameters"],
        "inputs": parameter_types,
        "lifetime_parameters": generics["lifetime_parameters"],
        "method": method,
        "output": canonical_text(output_type),
        "receiver": receiver_for_vstd(
            self_type, trait, parameter_types
        ),
        "self_type": self_type,
        "trait": trait,
        "type_parameters": generics["type_parameters"],
        "unsafe": bool(
            re.search(
                r"\bunsafe\b",
                header_text[: match.end() - match.start()],
            )
        ),
        "variadic": False,
    }
    start_line = source.count("\n", 0, match.start()) + 1
    end_line = source.count("\n", 0, declaration_end) + 1
    declaration_id = f"vstd-{source_label}-assume-" + object_sha256(
        {
            "shape": shape,
            "start_line": start_line,
            "target": canonical_text(target_text, erase_lifetimes=False),
        }
    )[:16]
    raw_types = [
        target_text,
        *(parameter["type"] for parameter in parameters),
        output_type,
    ]
    return {
        "declaration_id": declaration_id,
        "declaration_sha256": hashlib.sha256(
            declaration_text.encode()
        ).hexdigest(),
        "end_line": end_line,
        "header": " ".join(header_text.split()),
        "lifetime_occurrences": re.findall(
            r"'[A-Za-z_][A-Za-z0-9_]*", " ".join(raw_types)
        ),
        "raw_types": {
            "inputs": [parameter["type"] for parameter in parameters],
            "output": output_type,
            "self_type": target_text,
        },
        "shape": shape,
        "signature_shape_sha256": object_sha256(shape),
        "start_line": start_line,
        "target_binding": " ".join(target_text.split()),
    }


def parse_declarations(
    source: str, source_label: str
) -> list[dict[str, Any]]:
    return [
        parse_declaration(source, match, source_label)
        for match in ASSUME_SPECIFICATION.finditer(source)
    ]


def loaded_declarations() -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    for path, label in (
        (VSTD_RESULT, "result"),
        (VSTD_CONTROL_FLOW, "control-flow"),
    ):
        source = path.read_text(encoding="utf-8")
        parsed = parse_declarations(source, label)
        if path == VSTD_CONTROL_FLOW:
            parsed = [
                declaration
                for declaration in parsed
                if declaration["shape"]["self_type"].startswith("Result<")
            ]
        for declaration in parsed:
            declaration["source_path"] = str(path.relative_to(ROOT))
            declaration["source_sha256"] = sha256(path)
        declarations.extend(parsed)
    return declarations


def lifetime_match(
    rust: dict[str, Any], vstd: dict[str, Any]
) -> tuple[bool, str]:
    rust_shape = rust["shape"]
    vstd_shape = vstd["shape"]
    rust_static = rust["lifetime_occurrences"].count("'static")
    vstd_static = vstd["lifetime_occurrences"].count("'static")
    if rust_static != vstd_static:
        return False, "static_lifetime_mismatch"
    rust_lifetimes = rust_shape["lifetime_parameters"]
    vstd_lifetimes = vstd_shape["lifetime_parameters"]
    if len(rust_lifetimes) == len(vstd_lifetimes) and rust_lifetimes:
        return True, "alpha_normalized_declared_lifetimes"
    if rust_lifetimes == vstd_lifetimes:
        return True, "identical_or_absent"
    vstd_type_text = " ".join(
        [
            *vstd["raw_types"]["inputs"],
            vstd["raw_types"]["output"],
            vstd["raw_types"]["self_type"],
        ]
    )
    for lifetime in vstd_lifetimes:
        if not re.search(rf"&\s*{re.escape(lifetime)}\b", vstd_type_text):
            return False, "non_elidable_vstd_lifetime"
    if rust_lifetimes:
        return False, "generic_lifetime_parameter_mismatch"
    return True, "vstd_names_rust_elided_reference_lifetime"


def compare_signatures(
    rust: dict[str, Any], declaration: dict[str, Any]
) -> tuple[list[str], str]:
    mismatches = [
        field
        for field in COMPARE_FIELDS
        if rust["shape"].get(field) != declaration["shape"].get(field)
    ]
    lifetimes_equal, lifetime_mode = lifetime_match(rust, declaration)
    if not lifetimes_equal:
        mismatches.append("lifetimes")
    return mismatches, lifetime_mode


def write_inventory_csv(rows: list[dict[str, Any]]) -> None:
    with INVENTORY_CSV_PATH.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        existing_fields = next(reader)
    fields = existing_fields + [
        field for field in AUDIT_COLUMNS if field not in existing_fields
    ]
    temporary = INVENTORY_CSV_PATH.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(INVENTORY_CSV_PATH)


def add_error(
    errors: list[dict[str, Any]], code: str, **details: Any
) -> None:
    errors.append({"code": code, **details})


def closure_inputs_valid() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    try:
        manifest = load_object(CLOSURE_MANIFEST)
        audit = load_object(CLOSURE_AUDIT)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        return [
            {
                "code": "vstd_closure_evidence_unreadable",
                "message": str(error),
            }
        ]
    if manifest.get("status") != "passed":
        add_error(errors, "vstd_closure_manifest_not_passed")
    if audit.get("status") != "passed":
        add_error(errors, "vstd_closure_independent_audit_not_passed")
    manifest_rows = {
        row["copied_path"]: row
        for row in manifest.get("closure", {}).get("files", [])
    }
    for path in (VSTD_ENTRYPOINT, VSTD_MODULE, VSTD_RESULT, VSTD_CONTROL_FLOW):
        relative = str(path.relative_to(ROOT))
        row = manifest_rows.get(relative)
        if row is None:
            add_error(
                errors,
                "required_vstd_source_not_in_closure",
                path=relative,
            )
        elif sha256(path) != row.get("sha256"):
            add_error(
                errors,
                "required_vstd_source_hash_mismatch",
                path=relative,
            )
    return errors


def main() -> int:
    required = (
        INVENTORY_PATH,
        INVENTORY_CSV_PATH,
        EXCLUSIONS_PATH,
        SUMMARY_PATH,
        VSTD_ENTRYPOINT,
        VSTD_MODULE,
        VSTD_RESULT,
        VSTD_CONTROL_FLOW,
        CLOSURE_MANIFEST,
        CLOSURE_AUDIT,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing exact-vstd audit input: {missing}")

    inventory_payload = load_object(INVENTORY_PATH)
    rows = inventory_payload.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("inventory rows are not a list")
    exclusions_payload = load_object(EXCLUSIONS_PATH)
    exclusions = exclusions_payload.get("rows")
    if not isinstance(exclusions, list):
        raise SystemExit("exclusion rows are not a list")
    summary = load_object(SUMMARY_PATH)
    module_source = VSTD_MODULE.read_text(encoding="utf-8")
    entrypoint_source = VSTD_ENTRYPOINT.read_text(encoding="utf-8")
    pre_inventory_hash = sha256(INVENTORY_PATH)
    generated_at = datetime.now(timezone.utc).isoformat()
    errors = closure_inputs_valid()

    loaded_module_matches = {
        "pub mod std_specs;": len(
            re.findall(
                r"(?m)^pub mod std_specs;\s*$", entrypoint_source
            )
        ),
        "pub mod control_flow;": len(
            re.findall(
                r"(?m)^pub mod control_flow;\s*$", module_source
            )
        ),
        "pub mod result;": len(
            re.findall(r"(?m)^pub mod result;\s*$", module_source)
        ),
    }
    for declaration, count in loaded_module_matches.items():
        if count != 1:
            add_error(
                errors,
                "vstd_module_not_unconditionally_loaded_once",
                declaration=declaration,
                matches=count,
            )

    try:
        declarations = loaded_declarations()
    except ValueError as error:
        declarations = []
        add_error(errors, "vstd_declaration_parse_error", message=str(error))
    declaration_ids = [
        declaration["declaration_id"] for declaration in declarations
    ]
    if len(declaration_ids) != len(set(declaration_ids)):
        add_error(errors, "duplicate_vstd_declaration_id")

    row_audits: list[dict[str, Any]] = []
    exact_uses: dict[str, list[int]] = {}
    updated_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            add_error(errors, "inventory_row_not_object")
            continue
        rustdoc_item_id = row.get("rustdoc_item_id")
        rust = rust_signature(row)
        binding_candidates = [
            declaration
            for declaration in declarations
            if declaration["shape"]["method"] == rust["shape"]["method"]
            and declaration["shape"]["trait"] == rust["shape"]["trait"]
            and declaration["shape"]["self_type"]
            == rust["shape"]["self_type"]
        ]
        comparisons = []
        exact_candidates = []
        for declaration in binding_candidates:
            mismatches, lifetime_mode = compare_signatures(
                rust, declaration
            )
            comparisons.append(
                {
                    "declaration_id": declaration["declaration_id"],
                    "lifetime_mode": lifetime_mode,
                    "mismatched_signature_components": mismatches,
                }
            )
            if not mismatches:
                exact_candidates.append((declaration, lifetime_mode))
        if len(exact_candidates) > 1:
            add_error(
                errors,
                "multiple_exact_vstd_matches",
                declaration_ids=[
                    value[0]["declaration_id"]
                    for value in exact_candidates
                ],
                rustdoc_item_id=rustdoc_item_id,
            )

        updated = dict(row)
        if len(exact_candidates) == 1:
            declaration, lifetime_mode = exact_candidates[0]
            disposition = "exact_vstd"
            audit_status = "full_signature_exact"
            updated["disposition"] = disposition
            updated["pending_reason"] = ""
            updated["exact_vstd_declaration_id"] = declaration[
                "declaration_id"
            ]
            updated["exact_vstd_declaration_start_line"] = declaration[
                "start_line"
            ]
            updated["exact_vstd_signature_shape_sha256"] = declaration[
                "signature_shape_sha256"
            ]
            updated["exact_vstd_source_path"] = declaration["source_path"]
            updated["exact_vstd_source_sha256"] = declaration["source_sha256"]
            exact_uses.setdefault(
                declaration["declaration_id"], []
            ).append(int(rustdoc_item_id))
        else:
            disposition = str(updated.get("disposition"))
            if disposition in {"pending", "exact_vstd"}:
                disposition = "pending"
                updated["disposition"] = disposition
                updated["pending_reason"] = (
                    "no loaded vstd declaration matches the complete Rust "
                    "signature; generated contract required"
                )
            audit_status = (
                "signature_mismatch"
                if binding_candidates
                else "no_target_binding"
            )
            lifetime_mode = None
            for field in AUDIT_COLUMNS[1:]:
                updated.pop(field, None)
        updated["exact_vstd_audit_status"] = audit_status
        updated_rows.append(updated)
        row_audits.append(
            {
                "binding_candidate_count": len(binding_candidates),
                "comparisons": comparisons,
                "disposition": disposition,
                "exact_declaration_id": (
                    exact_candidates[0][0]["declaration_id"]
                    if len(exact_candidates) == 1
                    else None
                ),
                "lifetime_match_mode": lifetime_mode,
                "rust_signature": rust,
                "rustdoc_item_id": rustdoc_item_id,
                "target": row.get("target"),
            }
        )

    multiply_used = {
        declaration_id: item_ids
        for declaration_id, item_ids in exact_uses.items()
        if len(item_ids) != 1
    }
    if multiply_used:
        add_error(
            errors,
            "vstd_declaration_matches_multiple_inventory_rows",
            matches=multiply_used,
        )

    result_declaration_ids = {
        declaration["declaration_id"]
        for declaration in declarations
        if declaration["source_path"].endswith("std_specs/result.rs")
    }
    unmatched_result_declarations = sorted(
        result_declaration_ids - set(exact_uses)
    )
    if unmatched_result_declarations:
        add_error(
            errors,
            "loaded_result_vstd_declaration_not_exact_for_inventory",
            declaration_ids=unmatched_result_declarations,
        )

    out_of_scope_declarations = []
    for declaration in declarations:
        declaration_id = declaration["declaration_id"]
        if declaration_id in result_declaration_ids:
            continue
        exclusion_matches = [
            row
            for row in exclusions
            if row.get("method_name") == declaration["shape"]["method"]
            and canonical_text(str(row.get("self_type", "")))
            == declaration["shape"]["self_type"]
            and row.get("exclusion_reason") == "unstable_api"
        ]
        if len(exclusion_matches) > 1:
            input_types = [
                canonical_text(value)
                for value in declaration["raw_types"]["inputs"]
            ]
            exclusion_matches = [
                row
                for row in exclusion_matches
                if all(
                    input_type in canonical_text(str(row.get("target", "")))
                    for input_type in input_types
                )
            ]
        if len(exclusion_matches) != 1:
            add_error(
                errors,
                "out_of_scope_vstd_declaration_not_bound_to_one_exclusion",
                declaration_id=declaration_id,
                matches=len(exclusion_matches),
            )
        out_of_scope_declarations.append(
            {
                "declaration_id": declaration_id,
                "exclusion_reason": (
                    exclusion_matches[0]["exclusion_reason"]
                    if len(exclusion_matches) == 1
                    else None
                ),
                "exclusion_target": (
                    exclusion_matches[0]["target"]
                    if len(exclusion_matches) == 1
                    else None
                ),
                "reason": "unstable_core_result_api_not_in_stable_inventory",
                "target_binding": declaration["target_binding"],
            }
        )

    dispositions = {
        "exact_vstd": 0,
        "generated": 0,
        "genuinely_impossible": 0,
        "pending": 0,
    }
    for row in updated_rows:
        disposition = row.get("disposition")
        if disposition not in dispositions:
            add_error(
                errors,
                "unknown_inventory_disposition",
                disposition=disposition,
                rustdoc_item_id=row.get("rustdoc_item_id"),
            )
            continue
        dispositions[disposition] += 1
    if sum(dispositions.values()) != len(updated_rows):
        add_error(
            errors,
            "disposition_counts_do_not_reconcile",
            dispositions=dispositions,
            rows=len(updated_rows),
        )
    if len(row_audits) != len(rows):
        add_error(
            errors,
            "not_every_inventory_row_was_audited",
            audited=len(row_audits),
            inventory=len(rows),
        )

    post_inventory_hash: str | None = None
    post_summary_hash: str | None = None
    if not errors:
        summary.update(dispositions)
        summary["exact_vstd_audited_at_utc"] = generated_at
        summary["specified_total"] = (
            dispositions["exact_vstd"] + dispositions["generated"]
        )
        summary["stable_inventory_total"] = len(updated_rows)
        summary["strict_specification_coverage"] = (
            summary["specified_total"] / len(updated_rows)
            if updated_rows
            else 0.0
        )
        inventory_payload["rows"] = updated_rows
        inventory_payload["summary"] = summary
        inventory_payload["exact_vstd_subtraction"] = {
            "audit_path": str(OUTPUT_PATH.relative_to(ROOT)),
            "audited_at_utc": generated_at,
            "checker_path": str(Path(__file__).resolve()),
            "checker_sha256": sha256(Path(__file__)),
            "loaded_declaration_count": len(declarations),
            "module_loader_sha256": sha256(VSTD_MODULE),
            "source_files": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                }
                for path in (VSTD_RESULT, VSTD_CONTROL_FLOW)
            ],
        }
        write_json(INVENTORY_PATH, inventory_payload)
        write_json(SUMMARY_PATH, summary)
        write_inventory_csv(updated_rows)
        post_inventory_hash = sha256(INVENTORY_PATH)
        post_summary_hash = sha256(SUMMARY_PATH)

    error_codes = sorted({error["code"] for error in errors})
    report = {
        "audit": {
            "checked_at_utc": generated_at,
            "comparison_rule": (
                "Exact target binding plus receiver/reference, ordered "
                "parameters, result, generic type/const parameters, bounds, "
                "lifetime topology, mutability, safety, async, ABI, and "
                "variadic shape. Rust constness and internal bound modifiers "
                "are retained in each Rust row because assume_specification "
                "binds the resolved target rather than restating those target "
                "qualifiers. Rust lifetime elision is accepted only for "
                "reference lifetimes with otherwise identical erased types."
            ),
            "script_path": str(Path(__file__).resolve()),
            "script_sha256": sha256(Path(__file__)),
        },
        "declarations": declarations,
        "declaration_scope": {
            "exact_stable_declaration_ids": sorted(exact_uses),
            "out_of_scope_declarations": out_of_scope_declarations,
        },
        "error_details": errors,
        "errors": error_codes,
        "inputs": {
            "closure_independent_audit_path": str(CLOSURE_AUDIT),
            "closure_independent_audit_sha256": sha256(CLOSURE_AUDIT),
            "closure_manifest_path": str(CLOSURE_MANIFEST),
            "closure_manifest_sha256": sha256(CLOSURE_MANIFEST),
            "inventory_path": str(INVENTORY_PATH),
            "pre_subtraction_inventory_sha256": pre_inventory_hash,
            "vstd_module_loader_path": str(VSTD_MODULE),
            "vstd_module_loader_sha256": sha256(VSTD_MODULE),
            "loaded_source_files": [
                {
                    "path": str(path),
                    "sha256": sha256(path),
                }
                for path in (VSTD_RESULT, VSTD_CONTROL_FLOW)
            ],
        },
        "module_loading": {
            "declarations": loaded_module_matches,
            "all_required_modules_loaded_once": all(
                count == 1 for count in loaded_module_matches.values()
            ),
        },
        "outputs": {
            "inventory_sha256": post_inventory_hash,
            "summary_sha256": post_summary_hash,
        },
        "rows": row_audits,
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "summary": {
            **dispositions,
            "audited_inventory_rows": len(row_audits),
            "loaded_result_assume_specification_declarations": len(
                result_declaration_ids
            ),
            "loaded_result_language_item_declarations": len(
                out_of_scope_declarations
            ),
            "stable_inventory_total": len(updated_rows),
            "unmatched_loaded_result_declarations": len(
                unmatched_result_declarations
            ),
        },
    }
    write_json(OUTPUT_PATH, report)
    print(
        json.dumps(
            {
                "errors": error_codes,
                "status": report["status"],
                "summary": report["summary"],
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
