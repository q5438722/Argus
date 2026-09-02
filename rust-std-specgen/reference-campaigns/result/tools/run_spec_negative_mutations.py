#!/usr/bin/env python3
"""Reject one meaning-changing contract mutation for every generated row."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_specification
import specification_support as support


OUTPUT_PATH = support.AUDIT_ROOT / "negative_mutation.json"
MUTANT_ROOT = support.VERIFICATION_ROOT / "negative_mutations" / "mutants"


DERIVED_REPLACEMENTS: dict[int, tuple[str, str]] = {
    10010: (".len() <= 1", ".len() == 0"),
    11011: ("result == false", "result == true"),
    11356: ("result == Ordering::Less", "result == Ordering::Greater"),
    11599: (
        "result == Some(Ordering::Less)",
        "result == Some(Ordering::Greater)",
    ),
    29329: (
        "ResultFormatLiteral::OkName",
        "ResultFormatLiteral::ErrName",
    ),
    29331: (
        "result_hasher_discriminant_post(0int",
        "result_hasher_discriminant_post(1int",
    ),
    29343: (
        "ResultFormatLiteral::IterName",
        "ResultFormatLiteral::IntoIterName",
    ),
    29354: (
        "ResultFormatLiteral::IterMutName",
        "ResultFormatLiteral::IterName",
    ),
    29366: (
        "ResultFormatLiteral::IntoIterName",
        "ResultFormatLiteral::IterName",
    ),
}


def replace_once(
    source: str, before: str, after: str
) -> tuple[str, str, str]:
    if before not in source:
        raise ValueError(f"mutation source fragment not found: {before}")
    mutant = source.replace(before, after, 1)
    if mutant == source:
        raise ValueError("mutation did not change contract")
    return mutant, before, after


def replace_all(
    source: str, before: str, after: str
) -> tuple[str, str, str]:
    if before not in source:
        raise ValueError(f"mutation source fragment not found: {before}")
    mutant = source.replace(before, after)
    if mutant == source:
        raise ValueError("mutation did not change contract")
    return mutant, before, after


def semantic_mutation(
    item_id: int, source: str
) -> tuple[str, str, str]:
    if item_id in DERIVED_REPLACEMENTS:
        before, after = DERIVED_REPLACEMENTS[item_id]
        return replace_all(source, before, after)
    if item_id in support.SHORT_CIRCUIT_IDS:
        return replace_once(
            source, ").len() == stop + 1", ").len() > stop + 1"
        )
    if item_id == 29308:
        return replace_once(source, "input is Ok,", "input is Err,")
    if item_id in {29309, 29300}:
        return replace_once(source, "input is Err,", "input is Ok,")
    if item_id in support.ITERATOR_TRANSITION_IDS:
        return replace_all(source, ".drop_first()", ".take(0)")

    candidates = (
        ("input is Err ==> result == false", "input is Ok ==> result == false"),
        ("input is Ok ==> result == false", "input is Err ==> result == false"),
        ("input is Ok ==> f.requires", "input is Err ==> f.requires"),
        ("input is Err ==> f.requires", "input is Ok ==> f.requires"),
        ("input is Ok ==> op.requires", "input is Err ==> op.requires"),
        ("input is Err ==> op.requires", "input is Ok ==> op.requires"),
        ("*old(input) is Ok ==> result is Ok", "*old(input) is Err ==> result is Ok"),
        ("*input is Ok ==> result is Ok", "*input is Err ==> result is Ok"),
        ("input is Ok ==> result == other", "input is Err ==> result == other"),
        ("input is Ok ==> result == input->Ok_0", "input is Err ==> result == input->Ok_0"),
        ("input is Ok ==> result == Ok(", "input is Err ==> result == Ok("),
        ("input is Ok ==> result == Some(", "input is Err ==> result == Some("),
        (
            "input is Err ==> result == Err(input->Err_0)",
            "input is Ok ==> result == Err(input->Err_0)",
        ),
        (
            "input is Ok && input->Ok_0 is Some ==>",
            "input is Ok && input->Ok_0 is None ==>",
        ),
        ("result == input,", "result != input,"),
        (
            "result_iter_values(&result).len()\n            == if *input is Ok",
            "result_iter_values(&result).len()\n            == if *input is Err",
        ),
        (
            "result_iter_mut_values(&result).len()\n            == if *old(input) is Ok",
            "result_iter_mut_values(&result).len()\n            == if *old(input) is Err",
        ),
        (
            "result_into_iter_values(&result)\n            == if input is Ok",
            "result_into_iter_values(&result)\n            == if input is Err",
        ),
        (
            "result_iter_values(&result) == result_iter_values(iter)",
            "result_iter_values(&result) != result_iter_values(iter)",
        ),
        (".len() <= 1", ".len() == 0"),
        ("*old(input) is Ok && *source is Ok", "*old(input) is Err && *source is Ok"),
    )
    for before, after in candidates:
        if before in source:
            return replace_once(source, before, after)
    raise ValueError(f"no semantic mutation rule for rustdoc-{item_id}")


def main() -> int:
    support.validate_metadata_coverage()
    catalog = support.load_json(support.CATALOG_PATH)
    catalog_rows = {
        int(row["rustdoc_item_id"]): row
        for row in catalog["rows"]
        if row["disposition"] == "generated"
    }
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    MUTANT_ROOT.mkdir(parents=True, exist_ok=True)
    for item_id, block in sorted(support.contract_blocks().items()):
        record: dict[str, Any] = {
            "mutation_kind": support.mutation_kind(item_id),
            "obligation": (
                "stop_at_first_err_consumption_boundary"
                if item_id in support.SHORT_CIRCUIT_IDS
                else "target_direct_semantics"
            ),
            "rustdoc_item_id": item_id,
            "target": catalog_rows[item_id]["target"],
        }
        try:
            mutant, before, after = semantic_mutation(item_id, block.text)
            parsed = audit_specification.semantic_record(
                support.ContractBlock(item_id, mutant, 0, 0)
            )
            expected_hash = catalog_rows[item_id]["contract"][
                "semantic_clause_sha256"
            ]
            rejection = audit_specification.direct_errors(
                item_id, mutant, expected_hash
            )
            rejection_codes = sorted(
                {entry["code"] for entry in rejection}
            )
            integrity_codes = [
                code
                for code in rejection_codes
                if code == "semantic_clause_hash_mismatch"
            ]
            semantic_codes = [
                code
                for code in rejection_codes
                if code != "semantic_clause_hash_mismatch"
            ]
            mutant_path = MUTANT_ROOT / f"rustdoc-{item_id}.rs"
            mutant_path.write_text(mutant, encoding="utf-8")
            passed = (
                support.object_sha256(parsed) != expected_hash
                and integrity_codes == ["semantic_clause_hash_mismatch"]
                and bool(semantic_codes)
            )
            record.update(
                {
                    "after": after,
                    "before": before,
                    "mutant_path": str(
                        mutant_path.relative_to(support.ROOT)
                    ),
                    "mutant_sha256": support.sha256(mutant_path),
                    "parser_status": "accepted",
                    "integrity_rejection_codes": integrity_codes,
                    "rejection_codes": rejection_codes,
                    "semantic_rejection_codes": semantic_codes,
                    "status": "passed" if passed else "failed",
                }
            )
            if not passed:
                failures.append(
                    {
                        "code": "mutation_not_rejected",
                        "rustdoc_item_id": item_id,
                    }
                )
        except Exception as exception:
            record.update(
                {
                    "message": str(exception),
                    "status": "failed",
                }
            )
            failures.append(
                {
                    "code": "mutation_execution_failed",
                    "message": str(exception),
                    "rustdoc_item_id": item_id,
                }
            )
        records.append(record)

    expected = support.generated_ids()
    actual = {int(record["rustdoc_item_id"]) for record in records}
    if actual != expected:
        failures.append(
            {
                "code": "mutation_row_set_mismatch",
                "extra": sorted(actual - expected),
                "missing": sorted(expected - actual),
            }
        )
    payload = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "error_details": failures,
        "errors": sorted({row["code"] for row in failures}),
        "inputs": {
            "catalog_sha256": support.sha256(support.CATALOG_PATH),
            "checker_sha256": support.sha256(Path(__file__)),
            "contracts_sha256": support.sha256(support.CONTRACT_PATH),
        },
        "mutation_count": len(records),
        "records": records,
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
    }
    support.write_json(OUTPUT_PATH, payload)
    print(
        {
            "mutations": len(records),
            "status": payload["status"],
        }
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
