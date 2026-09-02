#!/usr/bin/env python3
"""Shared parsers and source-backed metadata for the Result spec package."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT.parent
INVENTORY_PATH = ROOT / "inventory" / "core_result_exec_fn_inventory.json"
EXACT_AUDIT_PATH = ROOT / "inventory" / "exact_vstd_audit.json"
DERIVE_AUDIT_PATH = ROOT / "provenance" / "result_derive_expansion.json"
DERIVE_SOURCE_PATH = ROOT / "provenance" / "result_derive_expansion.rs"
CONTRACT_PATH = ROOT / "specs" / "generated_result_specs.rs"
VOCABULARY_PATH = ROOT / "specs" / "result_shared_vocabulary.rs"
CATALOG_PATH = ROOT / "specs" / "all_result_specs.json"
EXACT_REFERENCES_PATH = (
    ROOT / "specs" / "existing_vstd" / "exact_result_references.json"
)
HELPER_USAGE_PATH = ROOT / "specs" / "result_helper_usage.json"
OUTCOME_EQUIVALENCE_PATH = (
    ROOT / "specs" / "result_outcome_equivalence.json"
)
PACKAGE_MANIFEST_PATH = ROOT / "specs" / "specification_package_manifest.json"
SPECGEN_ROOT = ROOT / "specgen"
FEEDBACK_MANIFEST_PATH = SPECGEN_ROOT / "result_stable_manifest.json"
FEEDBACK_SEED_PATH = SPECGEN_ROOT / "result_seed_candidates.json"
FEEDBACK_RELATION_CAPABILITY_PATH = (
    SPECGEN_ROOT / "result_feedback_relation_capability.json"
)
VSTD_CONTRACTS_PATH = ROOT / "provenance" / "vstd_contracts.json"
VERIFICATION_ROOT = ROOT / "verification"
AUDIT_ROOT = VERIFICATION_ROOT / "audits"
FEEDBACK_ROOT = VERIFICATION_ROOT / "feedback_determinism" / "final"
FEEDBACK_SUMMARY_PATH = FEEDBACK_ROOT / "batch_summary.json"
FEEDBACK_RUN_BINDING_PATH = FEEDBACK_ROOT / "run_binding.json"
FEEDBACK_ADAPTER_PATH = ROOT / "tools" / "run_feedback_with_equivalence.py"
FEEDBACK_DIAGNOSTIC_BINDING_FILENAME = (
    "selected_relation_diagnostic_binding.json"
)
FROM_ITER_PROBE_SOURCE_PATH = (
    VERIFICATION_ROOT
    / "feedback_probes"
    / "from_iter_projection_determinism.rs"
)
FROM_ITER_PROBE_REPORT_PATH = (
    VERIFICATION_ROOT
    / "feedback_determinism"
    / "from_iter_projection_probe"
    / "result.json"
)
FROM_ITER_ADJUDICATION_PATH = (
    VERIFICATION_ROOT
    / "feedback_determinism"
    / "from_iter_projection_adjudication.json"
)


@dataclass(frozen=True)
class ContractBlock:
    rustdoc_item_id: int
    text: str
    start_line: int
    end_line: int


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value, ensure_ascii=True, indent=2, sort_keys=True
    ) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def object_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def inventory_rows() -> list[dict[str, Any]]:
    rows = load_json(INVENTORY_PATH).get("rows")
    if not isinstance(rows, list):
        raise ValueError("inventory rows are missing")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("inventory contains a non-object row")
    return rows


def inventory_by_id() -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in inventory_rows():
        item_id = int(row["rustdoc_item_id"])
        if item_id in result:
            raise ValueError(f"duplicate inventory rustdoc id {item_id}")
        result[item_id] = row
    return result


def disposition_ids(disposition: str) -> set[int]:
    return {
        int(row["rustdoc_item_id"])
        for row in inventory_rows()
        if row.get("disposition") == disposition
    }


def generated_ids() -> set[int]:
    return disposition_ids("pending")


def exact_ids() -> set[int]:
    return disposition_ids("exact_vstd")


def contract_blocks(text: str | None = None) -> dict[int, ContractBlock]:
    source = CONTRACT_PATH.read_text(encoding="utf-8") if text is None else text
    marker = re.compile(r"(?m)^// @spec-row rustdoc-(\d+)\s*$")
    matches = list(marker.finditer(source))
    blocks: dict[int, ContractBlock] = {}
    wrapper_end = source.rfind("} // verus!")
    if wrapper_end < 0:
        raise ValueError("generated contract wrapper terminator is missing")
    for index, match in enumerate(matches):
        item_id = int(match.group(1))
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else wrapper_end
        )
        if item_id in blocks:
            raise ValueError(f"duplicate contract marker for {item_id}")
        text_value = source[match.start() : end].rstrip() + "\n"
        blocks[item_id] = ContractBlock(
            rustdoc_item_id=item_id,
            text=text_value,
            start_line=source.count("\n", 0, match.start()) + 1,
            end_line=source.count("\n", 0, end),
        )
    return blocks


def binding_text(block: ContractBlock) -> str:
    match = re.search(
        r"pub\s+assume_specification.*?\[\s*(.*?)\s*\]\s*\(",
        block.text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(
            f"rustdoc-{block.rustdoc_item_id} has no target binding"
        )
    return squash(match.group(1))


_FEEDBACK_MODULE: ModuleType | None = None


def feedback_module() -> ModuleType:
    global _FEEDBACK_MODULE
    if _FEEDBACK_MODULE is not None:
        return _FEEDBACK_MODULE
    path = SURVEY / "run_rust_std_spec_feedback.py"
    spec = importlib.util.spec_from_file_location(
        "result_feedback_schema", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import feedback parser from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _FEEDBACK_MODULE = module
    return module


def structured_clauses(
    contract_code: str,
) -> tuple[list[str], list[str]]:
    module = feedback_module()
    synthetic = module.assume_to_synthetic(contract_code)
    parsed = module.extract_spec(
        synthetic,
        "__rust_std_candidate",
        type_sources=[synthetic],
    )
    return list(parsed.requires), list(parsed.ensures)


def source_excerpt(path: Path, row: dict[str, Any]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start_line = int(row["source_start_line"])
    end_line = int(row["source_end_line"])
    start_column = int(row["source_start_column"])
    end_column = int(row["source_end_column"])
    selected = lines[start_line - 1 : end_line]
    if not selected:
        raise ValueError(f"empty source span for {row['target']}")
    if start_line == end_line:
        return selected[0][start_column - 1 : end_column - 1]
    selected[0] = selected[0][start_column - 1 :]
    selected[-1] = selected[-1][: end_column - 1]
    return "".join(selected)


def frozen_source_for(row: dict[str, Any]) -> Path:
    source_path = str(row["source_path"])
    marker = "/library/"
    if marker not in source_path:
        raise ValueError(f"source is outside Rust library: {source_path}")
    relative = source_path.split(marker, 1)[1]
    path = ROOT / "provenance" / "rust-source" / "library" / relative
    if not path.is_file():
        raise ValueError(f"frozen source is missing: {path}")
    return path


def extract_lines(path: Path, start_line: int, end_line: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(lines[start_line - 1 : end_line])


DERIVED_IDS = {
    10010,
    11011,
    11356,
    11599,
    29329,
    29331,
    29343,
    29354,
    29366,
}

SHORT_CIRCUIT_IDS = {26760, 26882, 26942}
CALLBACK_IDS = {
    29279,
    29281,
    29287,
    29288,
    29291,
    29292,
    29298,
    29304,
    29306,
}
UNSAFE_IDS = {29308, 29309}
MUTABLE_PROJECTION_IDS = {26996, 27287, 27049, 29285, 29294, 29296}
ITERATOR_TRANSITION_IDS = {
    27047,
    27049,
    27051,
    27283,
    27287,
    27291,
}
ITERATOR_STATE_IDS = {
    10007,
    10010,
    26988,
    26992,
    26996,
    27047,
    27049,
    27051,
    27283,
    27284,
    27287,
    27288,
    27291,
    27292,
    29295,
    29296,
    29343,
    29354,
    29366,
}

LINKED_ITERATOR_PROJECTION_HELPERS = {
    "result_into_iter_value_values",
    "result_iter_mut_value_identities",
    "result_iter_mut_value_values",
    "result_iter_value_identities",
    "result_iter_value_values",
}
DEFINED_MATHEMATICAL_HELPERS = {
    "result_all_ok",
    "result_ok_payloads_match",
}
SHORT_CIRCUIT_TRACE_HELPERS = {"result_short_circuit_trace"}
ITERATOR_PROJECTION_HELPERS = {
    "result_into_iter_values",
    "result_iter_identities",
    "result_iter_mut_identities",
    "result_iter_mut_values",
    "result_iter_values",
    *LINKED_ITERATOR_PROJECTION_HELPERS,
}
REFERENCE_IDENTITY_HELPERS = {
    "result_deref_mut_identity",
    "result_err_payload_identity",
    "result_err_value_identity",
    "result_mut_ref_identity",
    "result_ok_payload_identity",
    "result_ok_value_identity",
    "result_shared_ref_identity",
}
MUTABLE_STATE_HELPERS = {
    "result_deref_mut_state",
    "result_mut_ref_final_state",
    "result_mut_ref_initial_state",
}
FORMATTER_STATE_HELPERS = {"result_formatter_state"}

PROJECTED_EXACT_OBSERVATION_SCHEMAS: dict[int, str] = {
    29284: "shared_reference",
    29293: "shared_reference",
    29285: "mutable_reference_frame",
    29294: "mutable_reference_frame",
    10007: "iterator_state",
    10010: "iterator_state",
    26988: "iterator_state",
    26992: "iterator_state",
    26996: "iterator_state",
    29295: "iterator_state",
    29296: "iterator_state",
    27047: "iterator_transition",
    27049: "iterator_transition",
    27051: "iterator_transition",
    27283: "iterator_transition",
    27287: "iterator_transition",
    27291: "iterator_transition",
    29329: "formatter_effect",
    29343: "formatter_effect",
    29354: "formatter_effect",
    29366: "formatter_effect",
    29331: "hasher_effect",
}

TARGET_OBSERVATION_COMPONENTS: dict[int, tuple[str, ...]] = {
    29284: (
        "Result branch",
        "referenced payload value",
    ),
    29293: (
        "Result branch",
        "referenced payload value",
        "source-bound shared reference identity",
    ),
    29285: (
        "Result branch",
        "initial referred payload value",
        "source-bound mutable reference identity",
        "final referred payload state",
        "enclosing Result post-state",
    ),
    29294: (
        "Result branch",
        "initial referred payload value",
        "source-bound mutable reference identity",
        "final referred payload state",
        "enclosing Result post-state",
    ),
    10007: (
        "remaining payload sequence",
        "remaining shared reference-identity sequence",
    ),
    10010: ("remaining owned payload sequence",),
    26988: ("remaining owned payload sequence",),
    26992: (
        "remaining payload sequence",
        "remaining shared reference-identity sequence",
    ),
    26996: (
        "remaining payload sequence",
        "remaining mutable reference-identity sequence",
        "aliased Result post-state",
    ),
    29295: (
        "remaining payload sequence",
        "remaining shared reference-identity sequence",
    ),
    29296: (
        "remaining payload sequence",
        "remaining mutable reference-identity sequence",
        "aliased Result post-state",
    ),
    27047: (
        "returned Option branch and referred payload value",
        "returned shared reference identity",
        "final remaining payload sequence",
        "final shared reference-identity sequence",
    ),
    27283: (
        "returned Option branch and referred payload value",
        "returned shared reference identity",
        "final remaining payload sequence",
        "final shared reference-identity sequence",
    ),
    27049: (
        "returned Option branch and referred payload value",
        "returned mutable reference identity",
        "final remaining payload sequence",
        "final mutable reference-identity sequence",
    ),
    27287: (
        "returned Option branch and referred payload value",
        "returned mutable reference identity",
        "final remaining payload sequence",
        "final mutable reference-identity sequence",
    ),
    27051: (
        "returned Option value",
        "final remaining owned payload sequence",
    ),
    27291: (
        "returned Option value",
        "final remaining owned payload sequence",
    ),
    29329: ("core::fmt::Result", "final formatter-state projection"),
    29343: ("core::fmt::Result", "final formatter-state projection"),
    29354: ("core::fmt::Result", "final formatter-state projection"),
    29366: ("core::fmt::Result", "final formatter-state projection"),
    29331: ("final hasher state",),
}

TARGET_OBSERVATION_BINDINGS: dict[int, dict[str, tuple[str, ...]]] = {
    29284: {
        "Result branch": (
            "r is Ok <==> result is Ok",
            "r is Err <==> result is Err",
        ),
        "referenced payload value": (
            "result->Ok_0 == r->Ok_0",
            "result->Err_0 == r->Err_0",
        ),
    },
    29293: {
        "Result branch": (
            "*input is Ok ==> result is Ok",
            "*input is Err ==> result is Err",
        ),
        "referenced payload value": (
            "result->Ok_0 == result_deref_shared",
            "*result->Err_0 == input->Err_0",
        ),
        "source-bound shared reference identity": (
            "result_shared_ref_identity(result->Ok_0)",
            "result_shared_ref_identity(result->Err_0)",
        ),
    },
    29285: {
        "Result branch": (
            "*old(input) is Ok ==> result is Ok",
            "*old(input) is Err ==> result is Err",
        ),
        "initial referred payload value": (
            "*result->Ok_0 == (*old(input))->Ok_0",
            "*result->Err_0 == (*old(input))->Err_0",
        ),
        "source-bound mutable reference identity": (
            "result_ok_value_identity(*final(input))",
            "result_err_value_identity(*final(input))",
        ),
        "final referred payload state": (
            "*final(result->Ok_0)",
            "*final(result->Err_0)",
        ),
        "enclosing Result post-state": ("*final(input) ==",),
    },
    29294: {
        "Result branch": (
            "*old(input) is Ok ==> result is Ok",
            "*old(input) is Err ==> result is Err",
        ),
        "initial referred payload value": (
            "result_mut_ref_initial_state",
            "*result->Err_0 == (*old(input))->Err_0",
        ),
        "source-bound mutable reference identity": (
            "result_deref_mut_identity",
            "result_err_value_identity(*final(input))",
        ),
        "final referred payload state": (
            "result_mut_ref_final_state",
            "*final(result->Err_0)",
        ),
        "enclosing Result post-state": (
            "*final(input) is Ok",
            "*final(input) == Err",
        ),
    },
    10007: {
        "remaining payload sequence": ("result_iter_values(&result)",),
        "remaining shared reference-identity sequence": (
            "result_iter_identities(&result)",
        ),
    },
    10010: {
        "remaining owned payload sequence": (
            "result_into_iter_values(&result)",
            "result_clone_output",
        ),
    },
    26988: {
        "remaining owned payload sequence": (
            "result_into_iter_values(&result)",
        ),
    },
    26992: {
        "remaining payload sequence": ("result_iter_values(&result)",),
        "remaining shared reference-identity sequence": (
            "result_iter_identities(&result)",
        ),
    },
    26996: {
        "remaining payload sequence": (
            "result_iter_mut_values(&result)",
        ),
        "remaining mutable reference-identity sequence": (
            "result_iter_mut_identities(&result)",
        ),
        "aliased Result post-state": ("*final(input)",),
    },
    29295: {
        "remaining payload sequence": ("result_iter_values(&result)",),
        "remaining shared reference-identity sequence": (
            "result_iter_identities(&result)",
        ),
    },
    29296: {
        "remaining payload sequence": (
            "result_iter_mut_values(&result)",
        ),
        "remaining mutable reference-identity sequence": (
            "result_iter_mut_identities(&result)",
        ),
        "aliased Result post-state": ("*final(input)",),
    },
    27047: {
        "returned Option branch and referred payload value": (
            "result is None",
            "result is Some",
        ),
        "returned shared reference identity": (
            "result_shared_ref_identity(result->0)",
        ),
        "final remaining payload sequence": (
            "result_iter_value_values(*final(iter))",
        ),
        "final shared reference-identity sequence": (
            "result_iter_value_identities(*final(iter))",
        ),
    },
    27283: {
        "returned Option branch and referred payload value": (
            "result is None",
            "result is Some",
        ),
        "returned shared reference identity": (
            "result_shared_ref_identity(result->0)",
        ),
        "final remaining payload sequence": (
            "result_iter_value_values(*final(iter))",
        ),
        "final shared reference-identity sequence": (
            "result_iter_value_identities(*final(iter))",
        ),
    },
    27049: {
        "returned Option branch and referred payload value": (
            "result is None",
            "result is Some",
        ),
        "returned mutable reference identity": (
            "result_mut_ref_identity(result->0)",
        ),
        "final remaining payload sequence": (
            "result_iter_mut_value_values(*final(iter))",
        ),
        "final mutable reference-identity sequence": (
            "result_iter_mut_value_identities(*final(iter))",
        ),
    },
    27287: {
        "returned Option branch and referred payload value": (
            "result is None",
            "result is Some",
        ),
        "returned mutable reference identity": (
            "result_mut_ref_identity(result->0)",
        ),
        "final remaining payload sequence": (
            "result_iter_mut_value_values(*final(iter))",
        ),
        "final mutable reference-identity sequence": (
            "result_iter_mut_value_identities(*final(iter))",
        ),
    },
    27051: {
        "returned Option value": ("result == Some(", "result is None"),
        "final remaining owned payload sequence": (
            "result_into_iter_value_values(*final(iter))",
        ),
    },
    27291: {
        "returned Option value": ("result == Some(", "result is None"),
        "final remaining owned payload sequence": (
            "result_into_iter_value_values(*final(iter))",
        ),
    },
    29329: {
        "core::fmt::Result": (
            "result == result_formatter_debug_tuple_result",
        ),
        "final formatter-state projection": (
            "result_formatter_state(*final(formatter))",
        ),
    },
    29343: {
        "core::fmt::Result": (
            "result == result_formatter_debug_struct_result",
        ),
        "final formatter-state projection": (
            "result_formatter_state(*final(formatter))",
        ),
    },
    29354: {
        "core::fmt::Result": (
            "result == result_formatter_debug_struct_result",
        ),
        "final formatter-state projection": (
            "result_formatter_state(*final(formatter))",
        ),
    },
    29366: {
        "core::fmt::Result": (
            "result == result_formatter_debug_struct_result",
        ),
        "final formatter-state projection": (
            "result_formatter_state(*final(formatter))",
        ),
    },
    29331: {
        "final hasher state": ("*final(state) ==",),
    },
}

OBSERVATION_SCHEMA_SOURCE_BASIS: dict[str, str] = {
    "shared_reference": (
        "The contract observes the Result branch, referred payload value, "
        "and source-bound reference identity exposed by the returned shared "
        "reference."
    ),
    "mutable_reference_frame": (
        "The contract observes the Result branch, source-bound mutable "
        "reference identity, initial and final referred states, and the "
        "enclosing Result post-state."
    ),
    "iterator_state": (
        "The contract observes the constructor-visible remaining payload "
        "sequence, applicable reference identities, and any aliased Result "
        "post-state."
    ),
    "iterator_transition": (
        "The contract observes the returned Option value and applicable "
        "reference identity together with the complete final iterator-state "
        "projection."
    ),
    "formatter_effect": (
        "The contract observes core::fmt::Result and the complete modeled "
        "formatter-state transition caused by the source formatting call."
    ),
    "hasher_effect": (
        "The contract observes the complete modeled final hasher state after "
        "the source discriminant and payload hash calls."
    ),
}

OBSERVATION_EXAMPLES: dict[str, tuple[Any, Any]] = {
    "Result branch": ("Ok", "Err"),
    "referenced payload value": (7, 8),
    "source-bound shared reference identity": (17, 23),
    "source-bound mutable reference identity": (17, 23),
    "initial referred payload value": (7, 8),
    "final referred payload state": ({"value": 9}, {"value": 10}),
    "enclosing Result post-state": (
        {"payload": {"value": 9}, "variant": "Ok"},
        {"payload": {"value": 10}, "variant": "Ok"},
    ),
    "remaining payload sequence": ([7], [8]),
    "remaining shared reference-identity sequence": ([17], [23]),
    "remaining mutable reference-identity sequence": ([17], [23]),
    "remaining owned payload sequence": ([7], [8]),
    "aliased Result post-state": (
        {"payload": 7, "variant": "Ok"},
        {"payload": 8, "variant": "Ok"},
    ),
    "returned Option branch and referred payload value": (
        {"payload": 7, "variant": "Some"},
        {"variant": "None"},
    ),
    "returned Option value": (
        {"payload": 7, "variant": "Some"},
        {"variant": "None"},
    ),
    "returned shared reference identity": (17, 23),
    "returned mutable reference identity": (17, 23),
    "final remaining payload sequence": ([], [8]),
    "final shared reference-identity sequence": ([], [23]),
    "final mutable reference-identity sequence": ([], [23]),
    "final remaining owned payload sequence": ([], [8]),
    "core::fmt::Result": ("Ok(())", "Err(core::fmt::Error)"),
    "final formatter-state projection": (
        {"rendered": "Ok(7)"},
        {"rendered": "Err(7)"},
    ),
    "final hasher state": (
        {"written_words": [0, 7]},
        {"written_words": [1, 7]},
    ),
}

TARGET_OBSERVATION_EXAMPLE_OVERRIDES: dict[
    int, dict[str, tuple[Any, Any]]
] = {
    29329: {
        "final formatter-state projection": (
            {"rendered": "Ok(7)"},
            {"rendered": "Err(7)"},
        ),
    },
    29343: {
        "final formatter-state projection": (
            {"rendered": "Iter([7])"},
            {"rendered": "Iter([])"},
        ),
    },
    29354: {
        "final formatter-state projection": (
            {"rendered": "IterMut([7])"},
            {"rendered": "IterMut([])"},
        ),
    },
    29366: {
        "final formatter-state projection": (
            {"rendered": "IntoIter { inner: [7] }"},
            {"rendered": "IntoIter { inner: [] }"},
        ),
    },
}

SPEC_PACKAGE_ARTIFACTS = (
    "inventory/core_result_exec_fn_inventory.json",
    "inventory/core_result_exclusions.json",
    "inventory/coverage_summary.json",
    "inventory/exact_vstd_audit.json",
    "provenance/result_derive_expansion.json",
    "provenance/result_derive_expansion.rs",
    "provenance/vstd_dependency_closure.json",
    "provenance/vstd_dependency_closure_independent_audit.json",
    "provenance/vstd_contracts.json",
    "specgen/result_feedback_relation_capability.json",
    "specgen/result_seed_candidates.json",
    "specgen/result_stable_manifest.json",
    "specs/README.md",
    "specs/all_result_specs.json",
    "specs/existing_vstd/README.md",
    "specs/existing_vstd/exact_result_references.json",
    "specs/generated_result_specs.rs",
    "specs/result_helper_usage.json",
    "specs/result_outcome_equivalence.json",
    "specs/result_shared_vocabulary.rs",
    "tests/test_specification_package.py",
    "tools/audit_specification.py",
    "tools/build_specification_package.py",
    "tools/check_specification_gate.py",
    "tools/prepare_specification_review.py",
    "tools/run_feedback_with_equivalence.py",
    "tools/run_spec_negative_mutations.py",
    "tools/run_supervised_feedback.py",
    "tools/run_verus_typecheck.py",
    "tools/specification_support.py",
    "tools/audit_from_iter_projection.py",
    "tools/run_from_iter_projection_probe.py",
    "verification/audits/negative_mutation.json",
    "verification/feedback_determinism/final/batch_summary.json",
    "verification/feedback_determinism/final/run_binding.json",
    "verification/feedback_determinism/from_iter_projection_adjudication.json",
    "verification/feedback_determinism/from_iter_projection_probe/result.json",
    "verification/feedback_probes/from_iter_projection_determinism.rs",
    "verification/verus_typecheck.json",
    "verification/verus_typecheck.stderr.log",
    "verification/verus_typecheck.stdout.log",
)


BINDING_FRAGMENTS: dict[int, str] = {
    26760: "<Result<T, E> as Sum<Result<U, E>>>::sum::<I>",
    26882: "<Result<T, E> as Product<Result<U, E>>>::product::<I>",
    29329: "<Result<T, E> as Debug>::fmt",
    29331: "<Result<T, E> as Hash>::hash::<H>",
    11356: "<Result<T, E> as Ord>::cmp",
    11011: "<Result<T, E> as PartialEq>::eq",
    11599: "<Result<T, E> as PartialOrd>::partial_cmp",
    29279: "Result::<T, E>::is_ok_and",
    29281: "Result::<T, E>::is_err_and",
    29285: "Result::<T, E>::as_mut",
    29288: "Result::<T, E>::map_or::<U, F>",
    29287: "Result::<T, E>::map_or_else::<U, D, F>",
    29291: "Result::<T, E>::inspect::<F>",
    29292: "Result::<T, E>::inspect_err::<F>",
    29293: "Result::<T, E>::as_deref",
    29294: "Result::<T, E>::as_deref_mut",
    29295: "Result::<T, E>::iter",
    29296: "Result::<T, E>::iter_mut",
    29299: "Result::<T, E>::unwrap_or_default",
    29300: "Result::<T, E>::expect_err",
    29305: "Result::<T, E>::and::<U>",
    29304: "Result::<T, E>::and_then::<U, F>",
    29307: "Result::<T, E>::or::<F>",
    29306: "Result::<T, E>::or_else::<F, O>",
    29297: "Result::<T, E>::unwrap_or",
    29298: "Result::<T, E>::unwrap_or_else::<F>",
    29308: "Result::<T, E>::unwrap_unchecked",
    29309: "Result::<T, E>::unwrap_err_unchecked",
    29311: "Result::<&T, E>::copied",
    29312: "Result::<&T, E>::cloned",
    29314: "Result::<&mut T, E>::copied",
    29315: "Result::<&mut T, E>::cloned",
    29317: "Result::<Option<T>, E>::transpose",
    29319: "Result::<Result<T, E>, E>::flatten",
    10004: "<Result<T, E> as Clone>::clone",
    10005: "<Result<T, E> as Clone>::clone_from",
    26988: "<Result<T, E> as IntoIterator>::into_iter",
    26992: "<&'a Result<T, E> as IntoIterator>::into_iter",
    26996: "<&'a mut Result<T, E> as IntoIterator>::into_iter",
    29343: "<Iter<'a, T> as Debug>::fmt",
    27283: "<Iter<'a, T> as Iterator>::next",
    27284: "<Iter<'a, T> as Iterator>::size_hint",
    27047: "<Iter<'a, T> as DoubleEndedIterator>::next_back",
    10007: "<Iter<'a, T> as Clone>::clone",
    29354: "<IterMut<'a, T> as Debug>::fmt",
    27287: "<IterMut<'a, T> as Iterator>::next",
    27288: "<IterMut<'a, T> as Iterator>::size_hint",
    27049: "<IterMut<'a, T> as DoubleEndedIterator>::next_back",
    10010: "<IntoIter<T> as Clone>::clone",
    29366: "<IntoIter<T> as Debug>::fmt",
    27291: "<IntoIter<T> as Iterator>::next",
    27292: "<IntoIter<T> as Iterator>::size_hint",
    27051: "<IntoIter<T> as DoubleEndedIterator>::next_back",
    26942: (
        "<Result<V, E> as FromIterator<Result<A, E>>>::from_iter::<I>"
    ),
}


DIRECT_FRAGMENTS: dict[int, tuple[str, ...]] = {
    26760: (
        "result is Ok",
        "into_iter_remaining::<Result<U, E>, I>(iter)",
        "result_short_circuit_trace::<U, E, T, I>",
        "ResultShortCircuitOperation::Sum",
        ").len() == stop + 1",
        "forall|prior: int|",
        "result == Err(",
        "result_sum_output",
    ),
    26882: (
        "result is Ok",
        "into_iter_remaining::<Result<U, E>, I>(iter)",
        "result_short_circuit_trace::<U, E, T, I>",
        "ResultShortCircuitOperation::Product",
        ").len() == stop + 1",
        "forall|prior: int|",
        "result == Err(",
        "result_product_output",
    ),
    29329: (
        "ResultFormatLiteral::OkName",
        "ResultFormatLiteral::ErrName",
        "result_formatter_state(*final(formatter))",
    ),
    29331: (
        "result_hasher_discriminant_post(0int",
        "result_hasher_discriminant_post(1int",
        "*final(state)",
    ),
    11356: (
        "result_cmp_output",
        "result == Ordering::Less",
        "result == Ordering::Greater",
    ),
    11011: (
        "result_partial_eq_output",
        "*left is Ok && *right is Err ==> result == false",
        "*left is Err && *right is Ok ==> result == false",
    ),
    11599: (
        "result_partial_cmp_output",
        "result == Some(Ordering::Less)",
        "result == Some(Ordering::Greater)",
    ),
    29279: (
        "input is Err ==> result == false",
        "f.ensures",
        "result_fn_once_output",
    ),
    29281: (
        "input is Ok ==> result == false",
        "f.ensures",
        "result_fn_once_output",
    ),
    29285: (
        "*old(input) is Ok ==> result is Ok",
        "*final(input) == Ok(*final(result->Ok_0))",
        "*final(input) == Err(*final(result->Err_0))",
        "result_mut_ref_identity",
    ),
    29288: (
        "input is Err ==> result == default",
        "input is Ok ==> f.requires",
        "f.ensures",
        "result_fn_once_output",
    ),
    29287: (
        "input is Ok ==> f.requires",
        "input is Err ==> default.requires",
        "f.ensures",
        "default.ensures",
        "result_fn_once_output",
    ),
    29291: ("result == input", "input is Ok ==> f.requires", "f.ensures"),
    29292: ("result == input", "input is Err ==> f.requires", "f.ensures"),
    29293: (
        "*input is Ok ==> result is Ok",
        "result_deref_shared",
        "result_err_payload_identity",
    ),
    29294: (
        "*old(input) is Ok ==> result is Ok",
        "result_deref_mut_state((*old(input))->Ok_0)",
        "result_deref_mut_state((*final(input))->Ok_0)",
        "result_mut_ref_initial_state(result->Ok_0)",
        "result_mut_ref_final_state(result->Ok_0)",
        "*final(input) is Ok",
        "*final(input) is Err",
        "result_mut_ref_identity",
    ),
    29295: (
        "result_iter_values(&result).len() == if *input is Ok",
        "input->Ok_0",
        "result_ok_payload_identity",
    ),
    29296: (
        "result_iter_mut_values(&result).len() == if *old(input) is Ok",
        "*final(input) is Ok",
        "result_iter_mut_identities",
    ),
    29299: (
        "input is Ok ==> result == input->Ok_0",
        "result_default_output",
        "T::default.ensures",
    ),
    29300: ("input is Err", "result == input->Err_0"),
    29305: (
        "input is Ok ==> result == other",
        "input is Err ==> result == Err(input->Err_0)",
    ),
    29304: (
        "input is Err ==> result == Err(input->Err_0)",
        "input is Ok ==> op.requires",
        "op.ensures",
        "result_fn_once_output",
    ),
    29307: (
        "input is Ok ==> result == Ok(input->Ok_0)",
        "input is Err ==> result == other",
    ),
    29306: (
        "input is Ok ==> result == Ok(input->Ok_0)",
        "input is Err ==> op.requires",
        "op.ensures",
        "result_fn_once_output",
    ),
    29297: (
        "input is Ok ==> result == input->Ok_0",
        "input is Err ==> result == default",
    ),
    29298: (
        "input is Ok ==> result == input->Ok_0",
        "input is Err ==> op.requires",
        "op.ensures",
        "result_fn_once_output",
    ),
    29308: ("input is Ok", "result == input->Ok_0"),
    29309: ("input is Err", "result == input->Err_0"),
    29311: (
        "input is Ok ==> result == Ok(*input->Ok_0)",
        "input is Err ==> result == Err(input->Err_0)",
    ),
    29312: (
        "input is Err ==> result == Err(input->Err_0)",
        "result_clone_output",
        "cloned::<T>",
    ),
    29314: (
        "input is Ok ==> result == Ok(*input->Ok_0)",
        "input is Err ==> result == Err(input->Err_0)",
    ),
    29315: (
        "input is Err ==> result == Err(input->Err_0)",
        "result_clone_output",
        "cloned::<T>",
    ),
    29317: (
        "input is Ok && input->Ok_0 is Some ==> result == Some",
        "result == Some(Ok(input->Ok_0->0))",
        "result is None",
        "result == Some(Err(input->Err_0))",
    ),
    29319: (
        "input is Ok ==> result == input->Ok_0",
        "input is Err ==> result == Err(input->Err_0)",
    ),
    10004: (
        "*input is Ok ==> result is Ok",
        "*input is Err ==> result is Err",
        "result_clone_output",
        "cloned::<",
    ),
    10005: (
        "*old(input) is Ok && *source is Ok ==> *final(input) == Ok",
        "result_clone_from_output",
        "result_clone_output",
        "*final(input) == Ok",
        "*final(input) == Err",
    ),
    26988: (
        "result_into_iter_values(&result) == if input is Ok",
        "seq![input->Ok_0]",
    ),
    26992: (
        "result_iter_values(&result).len() == if *input is Ok",
        "result_iter_identities",
        "input->Ok_0",
    ),
    26996: (
        "result_iter_mut_values(&result).len() == if *old(input) is Ok",
        "result_iter_mut_identities",
        "*final(input) is Ok",
    ),
    29343: (
        "ResultFormatLiteral::IterName",
        "ResultFormatLiteral::InnerField",
        "result_formatter_state(*final(formatter))",
    ),
    27283: (
        "result is None",
        "result_shared_ref_identity",
        "result_iter_value_values(*final(iter))",
        "drop_first",
    ),
    27284: (
        "result_iter_values(iter).len() <= 1",
        "Some(result_iter_values(iter).len() as usize)",
    ),
    27047: (
        "result is None",
        "result_shared_ref_identity",
        "result_iter_value_values(*final(iter))",
        "drop_first",
    ),
    10007: (
        "result_iter_values(&result) == result_iter_values(iter)",
        "result_iter_identities(&result) == result_iter_identities(iter)",
    ),
    29354: (
        "ResultFormatLiteral::IterMutName",
        "ResultFormatLiteral::InnerField",
        "result_formatter_state(*final(formatter))",
    ),
    27287: (
        "result is None",
        "result_mut_ref_identity",
        "result_iter_mut_value_values(*final(iter))",
        "drop_first",
    ),
    27288: (
        "result_iter_mut_values(iter).len() <= 1",
        "Some(result_iter_mut_values(iter).len() as usize)",
    ),
    27049: (
        "result is None",
        "result_mut_ref_identity",
        "result_iter_mut_value_values(*final(iter))",
        "drop_first",
    ),
    10010: (
        "result_into_iter_values(&result).len()",
        "result_into_iter_values(iter).len() <= 1",
        "result_clone_output",
        "cloned::<T>",
    ),
    29366: (
        "ResultFormatLiteral::IntoIterName",
        "ResultFormatLiteral::InnerField",
        "result_formatter_state(*final(formatter))",
    ),
    27291: (
        "result is None",
        "result == Some(",
        "result_into_iter_value_values(*final(iter))",
        "drop_first",
    ),
    27292: (
        "result_into_iter_values(iter).len() <= 1",
        "Some(result_into_iter_values(iter).len() as usize)",
    ),
    27051: (
        "result is None",
        "result == Some(",
        "result_into_iter_value_values(*final(iter))",
        "drop_first",
    ),
    26942: (
        "result is Ok",
        "into_iter_remaining::<Result<A, E>, I>(iter)",
        "result_short_circuit_trace::<A, E, V, I>",
        "ResultShortCircuitOperation::FromIterator",
        ").len() == stop + 1",
        "forall|prior: int|",
        "result == Err(",
        "result_collect_output",
        "FromIteratorSpec::from_iter_ensures",
    ),
}


SOURCE_FRAGMENTS: dict[int, tuple[str, ...]] = {
    26760: ("iter::try_process", "|i| i.sum()"),
    26882: ("iter::try_process", "|i| i.product()"),
    29279: ("Err(_) => false", "Ok(x) => f(x)"),
    29281: ("Ok(_) => false", "Err(e) => f(e)"),
    29285: ("Ok(ref mut x) => Ok(x)", "Err(ref mut x) => Err(x)"),
    29288: ("Ok(t) => f(t)", "Err(_) => default"),
    29287: ("Ok(t) => f(t)", "Err(e) => default(e)"),
    29291: ("if let Ok(ref t) = self", "f(t)", "self"),
    29292: ("if let Err(ref e) = self", "f(e)", "self"),
    29293: ("self.as_ref().map(Deref::deref)",),
    29294: ("self.as_mut().map(DerefMut::deref_mut)",),
    29295: ("Iter { inner: self.as_ref().ok() }",),
    29296: ("IterMut { inner: self.as_mut().ok() }",),
    29299: ("Ok(x) => x", "Err(_) => Default::default()"),
    29300: ("Ok(t) => unwrap_failed(msg, &t)", "Err(e) => e"),
    29305: ("Ok(_) => res", "Err(e) => Err(e)"),
    29304: ("Ok(t) => op(t)", "Err(e) => Err(e)"),
    29307: ("Ok(v) => Ok(v)", "Err(_) => res"),
    29306: ("Ok(t) => Ok(t)", "Err(e) => op(e)"),
    29297: ("Ok(t) => t", "Err(_) => default"),
    29298: ("Ok(t) => t", "Err(e) => op(e)"),
    29308: ("Ok(t) => t", "hint::unreachable_unchecked()"),
    29309: ("hint::unreachable_unchecked()", "Err(e) => e"),
    29311: ("Ok(&v) => Ok(v)", "Err(e) => Err(e)"),
    29312: ("self.map(|t| t.clone())",),
    29314: ("Ok(&mut v) => Ok(v)", "Err(e) => Err(e)"),
    29315: ("self.map(|t| t.clone())",),
    29317: (
        "Ok(Some(x)) => Some(Ok(x))",
        "Ok(None) => None",
        "Err(e) => Some(Err(e))",
    ),
    29319: ("Ok(inner) => inner", "Err(e) => Err(e)"),
    10004: ("Ok(x) => Ok(x.clone())", "Err(x) => Err(x.clone())"),
    10005: (
        "(Ok(to), Ok(from)) => to.clone_from(from)",
        "(Err(to), Err(from)) => to.clone_from(from)",
        "(to, from) => *to = from.clone()",
    ),
    26988: ("IntoIter { inner: self.ok() }",),
    26992: ("self.iter()",),
    26996: ("self.iter_mut()",),
    27283: ("self.inner.take()",),
    27284: (
        "if self.inner.is_some() { 1 } else { 0 }",
        "(n, Some(n))",
    ),
    27047: ("self.inner.take()",),
    10007: ("Iter { inner: self.inner }",),
    27287: ("self.inner.take()",),
    27288: (
        "if self.inner.is_some() { 1 } else { 0 }",
        "(n, Some(n))",
    ),
    27049: ("self.inner.take()",),
    27291: ("self.inner.take()",),
    27292: (
        "if self.inner.is_some() { 1 } else { 0 }",
        "(n, Some(n))",
    ),
    27051: ("self.inner.take()",),
    26942: ("iter::try_process", "|i| i.collect()"),
}


GROUP_BY_ID: dict[int, str] = {}
for _item in SHORT_CIRCUIT_IDS:
    GROUP_BY_ID[_item] = "short_circuit"
for _item in DERIVED_IDS:
    GROUP_BY_ID[_item] = "derived_effect"
for _item in CALLBACK_IDS:
    GROUP_BY_ID[_item] = "callback"
for _item in ITERATOR_STATE_IDS:
    GROUP_BY_ID.setdefault(_item, "iterator_state")
for _item in UNSAFE_IDS:
    GROUP_BY_ID[_item] = "unsafe_extraction"
for _item in MUTABLE_PROJECTION_IDS:
    GROUP_BY_ID[_item] = "mutable_projection"


def group_for(item_id: int) -> str:
    return GROUP_BY_ID.get(item_id, "branch_payload")


def mutation_kind(item_id: int) -> str:
    if item_id in SHORT_CIRCUIT_IDS:
        return "short_circuit_consumption_boundary"
    if item_id in DERIVED_IDS:
        return "derived_operation_order"
    if item_id in CALLBACK_IDS:
        return "callback_branch_or_result"
    if item_id in UNSAFE_IDS:
        return "unsafe_domain"
    if item_id in ITERATOR_TRANSITION_IDS:
        return "iterator_transition"
    if item_id in MUTABLE_PROJECTION_IDS:
        return "mutable_post_state"
    if item_id in ITERATOR_STATE_IDS:
        return "iterator_state_or_identity"
    return "branch_or_output"


def helper_names() -> set[str]:
    source = VOCABULARY_PATH.read_text(encoding="utf-8")
    return set(
        re.findall(
            r"\b(?:open\s+|uninterp\s+)?spec\s+fn\s+([A-Za-z_]\w*)",
            source,
        )
    )


def used_helpers(block: ContractBlock) -> list[str]:
    return sorted(
        helper
        for helper in helper_names()
        if re.search(rf"\b{re.escape(helper)}\b", block.text)
    )


def helper_classification(helper: str) -> tuple[str, bool]:
    if helper in DEFINED_MATHEMATICAL_HELPERS:
        return "defined_mathematical_view", False
    if helper in SHORT_CIRCUIT_TRACE_HELPERS:
        return "short_circuit_trace_projection", True
    if helper in LINKED_ITERATOR_PROJECTION_HELPERS:
        return "linked_iterator_projection", False
    if helper in ITERATOR_PROJECTION_HELPERS:
        return "iterator_private_state_projection", True
    if helper in REFERENCE_IDENTITY_HELPERS:
        return "reference_identity_projection", True
    if helper in MUTABLE_STATE_HELPERS:
        return "mutable_state_projection", True
    if helper in FORMATTER_STATE_HELPERS:
        return "formatter_private_state_projection", True
    if helper in helper_names():
        return "narrow_dependency_law", True
    raise ValueError(f"unknown shared helper {helper}")


def outcome_equivalence_identity(item_id: int) -> dict[str, Any]:
    equivalence_id = f"core-result-rustdoc-{item_id}"
    version = (
        2 if item_id in PROJECTED_EXACT_OBSERVATION_SCHEMAS else 1
    )
    return {
        "equivalence_id": equivalence_id,
        "equivalence_version": version,
        "equivalence_version_id": f"{equivalence_id}-v{version}",
    }


def outcome_equivalence_witnesses(
    item_id: int,
    components: list[str],
    observation_schema: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity = outcome_equivalence_identity(item_id)
    equivalence_id = str(identity["equivalence_id"])
    if observation_schema is None:
        shared = {
            component: f"{equivalence_id}:observable-{index}:shared"
            for index, component in enumerate(components)
        }
        distinct = {
            component: f"{equivalence_id}:observable-{index}:different"
            for index, component in enumerate(components)
        }
        positive_description = (
            "Two target-specific candidate executions agree on every "
            "complete output and explicit post-state observation."
        )
    else:
        examples = {
            **OBSERVATION_EXAMPLES,
            **TARGET_OBSERVATION_EXAMPLE_OVERRIDES.get(item_id, {}),
        }
        shared = {
            component: examples[component][0]
            for component in components
        }
        distinct = {
            component: examples[component][1]
            for component in components
        }
        positive_description = (
            "Two candidate executions expose the same concrete observation "
            "tuple under this exact source-backed observation schema."
        )
    positive = {
        "description": positive_description,
        "expected_equivalent": True,
        "left_candidate": f"{equivalence_id}:positive:left",
        "left_observations": shared,
        "right_candidate": f"{equivalence_id}:positive:right",
        "right_observations": dict(shared),
    }
    negatives = []
    for index, distinguishing_component in enumerate(components):
        negative_right = dict(shared)
        negative_right[distinguishing_component] = distinct[
            distinguishing_component
        ]
        negatives.append(
            {
                "description": (
                    "Changing exactly this required observation makes the "
                    "observation tuples unequal."
                ),
                "distinguishing_component": distinguishing_component,
                "expected_equivalent": False,
                "left_candidate": (
                    f"{equivalence_id}:negative-{index}:left"
                ),
                "left_observations": shared,
                "right_candidate": (
                    f"{equivalence_id}:negative-{index}:right"
                ),
                "right_observations": negative_right,
            }
        )
    return positive, negatives


def outcome_equivalence_record(row: dict[str, Any]) -> dict[str, Any]:
    item_id = int(row["rustdoc_item_id"])
    observation_schema = PROJECTED_EXACT_OBSERVATION_SCHEMAS.get(item_id)
    identity = outcome_equivalence_identity(item_id)
    source_binding = {
        "excerpt_sha256": row["source_excerpt_sha256"],
        "path": row["frozen_source_path"],
        "start_line": int(row["source_start_line"]),
    }
    if observation_schema is None:
        components = [
            "complete returned value",
            "every explicit mutable post-state",
        ]
        record: dict[str, Any] = {
            "dependency_relative": True,
            "equality_scope": "complete_output_and_explicit_post_state",
            "equivalence_expression": (
                "output1 == output2 and every explicit mutable "
                "post_state1 == post_state2"
            ),
            "kind": "exact_equality",
            "non_exact_justification": None,
            "observation_schema_id": (
                "complete-output-and-explicit-post-state-v1"
            ),
            "observable_components": components,
            "proof_observation_schema": {
                "mode": "exact_result_and_explicit_post_state"
            },
            "rustdoc_item_id": item_id,
            "source_binding": source_binding,
            "target": row["target"],
        }
    else:
        components = list(TARGET_OBSERVATION_COMPONENTS[item_id])
        record = {
            "component_contract_bindings": {
                component: list(anchors)
                for component, anchors in TARGET_OBSERVATION_BINDINGS[
                    item_id
                ].items()
            },
            "dependency_relative": True,
            "equality_scope": "source_backed_observation_schema",
            "equivalence_expression": (
                "left and right observation tuples are exactly equal "
                "component by component"
            ),
            "kind": "exact_equality",
            "non_exact_justification": None,
            "observation_schema_id": (
                f"core-result-rustdoc-{item_id}-{observation_schema}-"
                "observations-v1"
            ),
            "observable_components": components,
            "proof_observation_schema": {
                "components": components,
                "mode": (
                    "exact_componentwise_source_observation_equality"
                ),
                "representation_boundary": (
                    "Unmodeled private representation is outside the "
                    "observation schema and outside the completeness theorem "
                    "domain; it is not treated as a second equivalent output."
                ),
                "source_basis": OBSERVATION_SCHEMA_SOURCE_BASIS[
                    observation_schema
                ],
            },
            "rustdoc_item_id": item_id,
            "source_binding": source_binding,
            "target": row["target"],
        }
    positive, negatives = outcome_equivalence_witnesses(
        item_id, components, observation_schema
    )
    record.update(
        {
            **identity,
            "component_inequality_witnesses": negatives,
            "negative_witness": negatives[0],
            "positive_witness": positive,
            "witness_role": (
                "Relation-operator test vectors, not claims that both tuples "
                "satisfy the target contract."
            ),
        }
    )
    return {
        **record,
        "record_sha256": object_sha256(record),
    }


def outcome_equivalence_version_set_sha256(
    records: list[dict[str, Any]],
) -> str:
    versions = [
        {
            "equivalence_id": record["equivalence_id"],
            "equivalence_version": record["equivalence_version"],
            "equivalence_version_id": record["equivalence_version_id"],
            "observation_schema_id": record["observation_schema_id"],
            "record_sha256": record["record_sha256"],
            "rustdoc_item_id": int(record["rustdoc_item_id"]),
            "target": record["target"],
        }
        for record in sorted(
            records, key=lambda value: int(value["rustdoc_item_id"])
        )
    ]
    return object_sha256(versions)


def outcome_equivalence_artifact_binding(
    payload: dict[str, Any],
    path: Path = OUTCOME_EQUIVALENCE_PATH,
) -> dict[str, Any]:
    return {
        "artifact_path": str(path.relative_to(ROOT)),
        "artifact_sha256": sha256(path),
        "schema_version": int(payload["schema_version"]),
        "version_set_sha256": payload["version_set_sha256"],
    }


def outcome_equivalence_binding(
    record: dict[str, Any],
    payload: dict[str, Any],
    path: Path = OUTCOME_EQUIVALENCE_PATH,
) -> dict[str, Any]:
    return {
        **outcome_equivalence_artifact_binding(payload, path),
        "equivalence_id": record["equivalence_id"],
        "equivalence_version": record["equivalence_version"],
        "equivalence_version_id": record["equivalence_version_id"],
        "equality_scope": record["equality_scope"],
        "equivalence_expression": record["equivalence_expression"],
        "kind": record["kind"],
        "observation_schema_id": record["observation_schema_id"],
        "proof_observation_schema": record["proof_observation_schema"],
        "record_sha256": record["record_sha256"],
        "rustdoc_item_id": int(record["rustdoc_item_id"]),
        "target": record["target"],
    }


def feedback_relation_capability_payload(
    equivalence: dict[str, Any],
) -> dict[str, Any]:
    generated = generated_ids()
    records = [
        {
            "equivalence_version_id": record[
                "equivalence_version_id"
            ],
            "rustdoc_item_id": int(record["rustdoc_item_id"]),
            "status": "unsupported",
            "target": record["target"],
        }
        for record in equivalence["records"]
        if int(record["rustdoc_item_id"]) in generated
    ]
    records.sort(key=lambda record: int(record["rustdoc_item_id"]))
    canonical_runner = ROOT.parent / "run_rust_std_spec_feedback.py"
    return {
        "capability": (
            "selected_outcome_equivalence_relation_evaluation"
        ),
        "canonical_runner": {
            "path": str(canonical_runner),
            "sha256": sha256(canonical_runner),
        },
        "outcome_equivalence": outcome_equivalence_artifact_binding(
            equivalence
        ),
        "reason": (
            "The canonical feedback runner constructs its own equality policy "
            "and accepts no selected outcome-equivalence relation input. Its "
            "SAT/UNSAT/UNKNOWN result is retained only as a canonical checker "
            "diagnostic and is not evidence for the selected relation."
        ),
        "reason_code": (
            "canonical_runner_has_no_selected_relation_input"
        ),
        "records": records,
        "schema_version": 1,
        "selected_relation_evaluated_target_count": 0,
        "status": "unsupported",
        "unsupported_target_count": len(records),
    }


def feedback_relation_capability_binding(
    payload: dict[str, Any],
    path: Path = FEEDBACK_RELATION_CAPABILITY_PATH,
) -> dict[str, Any]:
    return {
        "artifact_path": str(path.relative_to(ROOT)),
        "artifact_sha256": sha256(path),
        "capability": payload["capability"],
        "reason_code": payload["reason_code"],
        "schema_version": int(payload["schema_version"]),
        "status": payload["status"],
    }


def feedback_relation_target_classification(
    equivalence_binding: dict[str, Any],
    capability: dict[str, Any],
    path: Path = FEEDBACK_RELATION_CAPABILITY_PATH,
) -> dict[str, Any]:
    return {
        **feedback_relation_capability_binding(capability, path),
        "equivalence_version_id": equivalence_binding[
            "equivalence_version_id"
        ],
        "rustdoc_item_id": int(equivalence_binding["rustdoc_item_id"]),
        "target": equivalence_binding["target"],
    }


def feedback_round_diagnostic_binding(
    target: str,
    round_dir: Path,
    equivalence_binding: dict[str, Any],
    relation_evaluation: dict[str, Any],
) -> dict[str, Any]:
    artifacts = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for path in sorted(round_dir.rglob("*"))
        if path.is_file()
        and path.name != FEEDBACK_DIAGNOSTIC_BINDING_FILENAME
    ]
    return {
        "artifacts": artifacts,
        "canonical_evidence_role": "diagnostic_only",
        "outcome_equivalence": equivalence_binding,
        "round": round_dir.name,
        "schema_version": 1,
        "selected_relation_evaluated": False,
        "selected_relation_evaluation": relation_evaluation,
        "target": target,
    }


def feedback_diagnostic_binding_set(
    root: Path = FEEDBACK_ROOT,
) -> dict[str, Any]:
    paths = sorted(
        root.glob(
            "targets/*/round_*/"
            f"{FEEDBACK_DIAGNOSTIC_BINDING_FILENAME}"
        )
    )
    records = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for path in paths
        if path.is_file()
    ]
    return {
        "binding_count": len(records),
        "set_sha256": object_sha256(records),
    }


def source_context(
    path: Path, row: dict[str, Any], radius: int = 12
) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(1, int(row["source_start_line"]) - radius)
    end = min(len(lines), int(row["source_end_line"]) + radius)
    return "\n".join(
        f"{line_number}: {lines[line_number - 1]}"
        for line_number in range(start, end + 1)
    )


def safe_name(target: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", target).strip("_")


def observability(row: dict[str, Any]) -> dict[str, bool]:
    signature = str(row["signature"])
    output = (
        signature.rsplit("->", 1)[1].strip()
        if "->" in signature
        else "()"
    )
    return {
        "has_modeled_output": output != "()" or "&mut" in signature,
        "return_is_raw_pointer": output.startswith("*"),
        "return_is_reference": output.startswith("&") or "Result<&" in output,
        "return_is_unit": output == "()",
    }


def feedback_risks(item_id: int, row: dict[str, Any]) -> list[str]:
    risks: set[str] = set()
    if item_id in CALLBACK_IDS:
        risks.update(("callback_cardinality", "callback_result"))
    if item_id in MUTABLE_PROJECTION_IDS:
        risks.update(("mutable_reference_return", "post_state"))
    if item_id in ITERATOR_STATE_IDS:
        risks.update(("iterator_private_state", "iterator_transition"))
    if item_id in SHORT_CIRCUIT_IDS:
        risks.update(
            (
                "generic_trait_dependency",
                "iterator_consumption_trace",
                "short_circuit",
            )
        )
    if item_id in UNSAFE_IDS or bool(row.get("is_unsafe")):
        risks.add("unsafe_domain")
    if item_id in DERIVED_IDS:
        risks.add("derived_implementation")
    if item_id in PROJECTED_EXACT_OBSERVATION_SCHEMAS:
        risks.add("exact_source_observation_schema")
    return sorted(risks)


def validate_metadata_coverage() -> None:
    expected = generated_ids()
    mappings = {
        "bindings": set(BINDING_FRAGMENTS),
        "direct fragments": set(DIRECT_FRAGMENTS),
    }
    for label, actual in mappings.items():
        if actual != expected:
            raise ValueError(
                f"{label} do not match pending rows: "
                f"missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )
    expected_source = expected - DERIVED_IDS
    if set(SOURCE_FRAGMENTS) != expected_source:
        raise ValueError(
            "source fragments do not match non-derived pending rows: "
            f"missing={sorted(expected_source - set(SOURCE_FRAGMENTS))}, "
            f"extra={sorted(set(SOURCE_FRAGMENTS) - expected_source)}"
        )
    projected = set(PROJECTED_EXACT_OBSERVATION_SCHEMAS)
    if set(TARGET_OBSERVATION_COMPONENTS) != projected:
        raise ValueError(
            "target observation components do not cover projected exact "
            "schemas"
        )
    if set(TARGET_OBSERVATION_BINDINGS) != projected:
        raise ValueError(
            "target observation bindings do not cover projected exact "
            "schemas"
        )
    for item_id in sorted(projected):
        components = TARGET_OBSERVATION_COMPONENTS[item_id]
        bindings = TARGET_OBSERVATION_BINDINGS[item_id]
        if set(bindings) != set(components) or any(
            not anchors for anchors in bindings.values()
        ):
            raise ValueError(
                "target observation binding mismatch for "
                f"rustdoc-{item_id}"
            )


def derived_captures() -> dict[int, dict[str, Any]]:
    captures = load_json(DERIVE_AUDIT_PATH).get("captures")
    if not isinstance(captures, list):
        raise ValueError("derive captures are missing")
    result: dict[int, dict[str, Any]] = {}
    for capture in captures:
        if not isinstance(capture, dict):
            raise ValueError("derive capture is not an object")
        item_id = int(capture["rustdoc_item_id"])
        if item_id in result:
            raise ValueError(f"duplicate derive capture {item_id}")
        result[item_id] = capture
    return result
