from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import build_specification as builder
from tools import check_specification as checker


class CmpSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = checker.load(builder.INVENTORY)
        cls.rows = cls.inventory["rows"]
        cls.pending = builder.generated_candidate_rows(cls.rows)
        cls.impossible = builder.model_boundary_rows(cls.rows)
        cls.exact = [
            row for row in cls.rows if row["disposition"] == "exact_vstd"
        ]
        cls.text = builder.GENERATED.read_text(encoding="utf-8")
        cls.blocks = checker.contract_blocks(cls.text)

    def test_package_rebuild_is_byte_deterministic(self) -> None:
        payloads = builder.build_payloads()
        for path, expected in payloads.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_bytes(), expected)

    def test_every_pending_identity_has_one_source_bound_contract(self) -> None:
        self.assertEqual(set(self.blocks), {row["row_id"] for row in self.pending})
        self.assertEqual(len(self.blocks), len(self.pending))
        self.assertEqual(
            checker.contract_text_errors(self.text, self.rows),
            [],
        )
        for row in self.pending:
            family, block = self.blocks[row["row_id"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertEqual(family, builder.build_contract(row).family)
                if family in {"empty_eq_default", "trait_default_clamp"}:
                    self.assertIn("pub open spec fn", block)
                    self.assertNotIn("assume_specification", block)
                else:
                    self.assertEqual(block.count("pub assume_specification"), 1)
                    self.assertIn("ensures", block)

    def test_exact_vstd_partition_preserves_noncanonical_bindings(self) -> None:
        bindings = checker.load(builder.EXISTING_BINDINGS)
        records = bindings["records"]
        self.assertEqual(len(records), len(self.exact))
        canonical = [
            record for record in records
            if record["canonical_upstream_binding"]
        ]
        noncanonical = [
            record for record in records
            if not record["canonical_upstream_binding"]
        ]
        self.assertEqual(
            len(canonical),
            sum(
                row["vstd_provenance_class"] == "tracked_clean_vstd"
                for row in self.exact
            ),
        )
        self.assertEqual(
            len(noncanonical),
            sum(
                row["vstd_provenance_class"]
                == "frozen_dirty_or_untracked_current_vstd"
                for row in self.exact
            ),
        )
        self.assertTrue(noncanonical)
        self.assertTrue(all(
            record["target"].startswith("Ordering::")
            and record["vstd_provenance_class"]
            == "frozen_dirty_or_untracked_current_vstd"
            for record in noncanonical
        ))
        self.assertIn(
            "canonical_upstream_binding: false",
            builder.EXISTING_README.read_text(encoding="utf-8"),
        )

    def test_catalog_reconciles_inventory_without_acceptance_constants(self) -> None:
        catalog = checker.load(builder.CATALOG)
        self.assertEqual(len(catalog["rows"]), len(self.rows))
        self.assertEqual(
            {row["row_id"] for row in catalog["rows"]},
            {row["row_id"] for row in self.rows},
        )
        counts = catalog["counts"]
        self.assertEqual(counts["stable_inventory_total"], len(self.rows))
        self.assertEqual(counts["generated"], len(self.pending))
        self.assertEqual(counts["exact_vstd"], len(self.exact))
        self.assertEqual(
            counts["genuinely_impossible"],
            len(self.impossible),
        )
        self.assertEqual(
            counts["specified_total"],
            len(self.pending) + len(self.exact),
        )
        self.assertEqual(counts["pending"], 0)
        generated_catalog = {
            row["row_id"]: row
            for row in catalog["rows"]
            if row["disposition"] == "generated"
        }
        self.assertEqual(set(generated_catalog), {row["row_id"] for row in self.pending})
        for row_id, row in generated_catalog.items():
            with self.subTest(row_id=row_id):
                self.assertTrue(row["source"]["span_sha256"])
                self.assertTrue(row["contract"]["semantic_summary"])
                self.assertTrue(row["contract"]["observable_components"])
        impossible_catalog = {
            row["row_id"]: row
            for row in catalog["rows"]
            if row["disposition"] == "genuinely_impossible"
        }
        self.assertEqual(
            set(impossible_catalog),
            {row["row_id"] for row in self.impossible},
        )
        self.assertTrue(all(
            row["contract"] is None
            and row["model_boundary"]["missing_model_boundary"][
                "whole_target_outcome"
            ]
            is True
            for row in impossible_catalog.values()
        ))

    def test_float_rows_are_honest_model_boundaries(self) -> None:
        self.assertEqual(len(self.impossible), 14)
        self.assertEqual(
            {
                (row["owner_type"], row["method_name"])
                for row in self.impossible
            },
            {
                (type_name, method)
                for type_name in ("f32", "f64")
                for method in (
                    "eq",
                    "ne",
                    "partial_cmp",
                    "lt",
                    "le",
                    "gt",
                    "ge",
                )
            },
        )
        self.assertTrue(all(
            row["disposition"] == "pending"
            and row["vstd_binding_ids"] == []
            for row in self.impossible
        ))
        audit = checker.load(builder.FLOAT_MODEL_BOUNDARY)
        self.assertEqual(audit["record_count"], 14)
        self.assertEqual(
            {record["row_id"] for record in audit["records"]},
            {row["row_id"] for row in self.impossible},
        )
        for record in audit["records"]:
            with self.subTest(row_id=record["row_id"]):
                self.assertTrue(
                    record["missing_model_boundary"][
                        "whole_target_outcome"
                    ]
                )
                self.assertFalse(
                    record["missing_model_boundary"][
                        "accepted_for_contract_or_proof"
                    ]
                )
                self.assertIn(
                    "nan_result",
                    record["required_direct_source_semantics"],
                )
                self.assertGreaterEqual(len(record["attempts"]), 4)
                self.assertGreaterEqual(
                    len(record["semantic_mutations"]),
                    2,
                )
                self.assertIn("not_claimed", record["mutation_status"])

    def test_float_functionality_premise_is_not_generated(self) -> None:
        active_sources = [
            builder.GENERATED.read_text(encoding="utf-8"),
            (
                builder.ROOT / "tools" / "proof_templates_exact.py"
            ).read_text(encoding="utf-8"),
        ]
        for text in active_sources:
            self.assertNotIn("float_contract_functionality", text)
            self.assertNotIn(
                "accepted_contract_functionality",
                text,
            )
            self.assertNotIn(
                "second_accepted_float_outcome",
                text,
            )

    def test_every_outcome_uses_exact_observable_equality(self) -> None:
        equivalence = checker.load(builder.EQUIVALENCE)
        self.assertEqual(len(equivalence["records"]), len(self.rows))
        self.assertEqual(equivalence["non_exact_equivalence_count"], 0)
        self.assertEqual(
            {row["row_id"] for row in equivalence["records"]},
            {row["row_id"] for row in self.rows},
        )
        for record in equivalence["records"]:
            with self.subTest(row_id=record["row_id"]):
                self.assertEqual(
                    record["kind"],
                    "exact_observable_outcome_equality",
                )
                self.assertFalse(record["quotient_used"])
                self.assertFalse(
                    record["positive_and_negative_witnesses_required"]
                )
                self.assertIn(
                    "panic_domain",
                    record["accepted_outcome_components"],
                )

    def test_source_hashes_and_spans_are_live(self) -> None:
        self.assertEqual(checker.source_evidence_errors(self.rows), [])

    def test_helper_audit_has_no_whole_target_outcome(self) -> None:
        audit = checker.load(builder.HELPER_AUDIT)
        self.assertEqual(audit["status"], "passed")
        self.assertTrue(audit["prohibited_helpers_absent"])
        self.assertEqual(audit["counts"]["whole_target_outcome"], 0)
        self.assertNotIn(
            "cmp_reference_forward_result",
            builder.VOCABULARY.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "cmp_private_chaining_outcome",
            builder.VOCABULARY.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "cmp_slice_chaining_prefix",
            builder.VOCABULARY.read_text(encoding="utf-8"),
        )
        self.assertTrue(audit["records"])
        self.assertTrue(all(
            record["whole_target_outcome"] is False
            for record in audit["records"]
        ))

    def test_callback_and_dispatch_families_are_explicit(self) -> None:
        by_target = {row["target"]: row for row in self.pending}
        then_with = self.blocks[
            by_target["Ordering::then_with"]["row_id"]
        ][1]
        self.assertIn("ordering != Ordering::Equal", then_with)
        self.assertIn("ordering == Ordering::Equal", then_with)
        min_by = self.blocks[
            by_target["core::cmp::min_by"]["row_id"]
        ][1]
        self.assertIn("compare.ensures((&v1, &v2), order)", min_by)
        min_key = self.blocks[
            by_target["core::cmp::min_by_key"]["row_id"]
        ][1]
        self.assertIn("&v2, &v1", min_key)
        reverse = self.blocks[
            by_target[
                "<Reverse<T> as PartialOrd<Reverse<T>>>::partial_cmp"
            ]["row_id"]
        ][1]
        self.assertIn("&right.0, &left.0", reverse)
        slice_eq = self.blocks[
            by_target["<[T] as PartialEq<[U]>>::eq"]["row_id"]
        ][1]
        self.assertIn("GenericElementLoop", slice_eq)
        self.assertIn("Bytewise", slice_eq)

    def test_clamp_contracts_expose_success_and_panic_domains(self) -> None:
        clamp_rows = [
            row for row in self.pending if row["method_name"] == "clamp"
        ]
        self.assertEqual(len(clamp_rows), 15)
        self.assertEqual(
            {row["target"] for row in clamp_rows},
            {
                "Ord::clamp",
                "<bool as Ord>::clamp",
                "<char as Ord>::clamp",
                "<usize as Ord>::clamp",
                "<u8 as Ord>::clamp",
                "<u16 as Ord>::clamp",
                "<u32 as Ord>::clamp",
                "<u64 as Ord>::clamp",
                "<u128 as Ord>::clamp",
                "<isize as Ord>::clamp",
                "<i8 as Ord>::clamp",
                "<i16 as Ord>::clamp",
                "<i32 as Ord>::clamp",
                "<i64 as Ord>::clamp",
                "<i128 as Ord>::clamp",
            },
        )
        catalog = {
            row["row_id"]: row
            for row in checker.load(builder.CATALOG)["rows"]
        }
        for row in clamp_rows:
            family, block = self.blocks[row["row_id"]]
            with self.subTest(row_id=row["row_id"]):
                self.assertIn(
                    family, {"primitive_clamp", "trait_default_clamp"}
                )
                self.assertNotIn("requires", block)
                self.assertIn("CmpCallOutcome::Panicked", block)
                self.assertIn("CmpCallOutcome::Returned(", block)
                if family == "primitive_clamp":
                    self.assertIn(
                        "== CmpCallOutcome::Returned(result)",
                        block,
                    )
                    self.assertIn("{ min } else if", block)
                    self.assertIn("{ max } else", block)
                else:
                    self.assertEqual(row["target"], "Ord::clamp")
                    self.assertIn(
                        "min.partial_cmp_spec(&max) == "
                        "Some(Ordering::Greater)",
                        block,
                    )
                    self.assertNotIn("assume_specification", block)
                self.assertEqual(
                    catalog[row["row_id"]]["contract"]["panic_domain"],
                    "panics_iff_min_greater_than_max",
                )

    def test_missing_marker_mutation_is_rejected(self) -> None:
        match = checker.MARKER.search(self.text)
        self.assertIsNotNone(match)
        mutated = self.text[:match.start()] + self.text[match.end():]
        self.assertIn(
            "generated_contract_identity_set_mismatch",
            checker.contract_text_errors(mutated, self.rows),
        )

    def test_reversed_key_callback_mutation_is_rejected(self) -> None:
        mutated = self.text.replace(
            "callback.ensures((&v2,), key2)",
            "callback.ensures((&v1,), key2)",
            1,
        )
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "callback.ensures((&v2,), key2)" in error
            for error in errors
        ))

    def test_unsequenced_key_callback_mutation_is_rejected(self) -> None:
        mutated = self.text.replace(
            "callback_after_v2.ensures((&v1,), key1)",
            "callback.ensures((&v1,), key1)",
            1,
        )
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "callback_after_v2.ensures((&v1,), key1)" in error
            for error in errors
        ))

    def test_missing_key_callback_final_state_mutation_is_rejected(self) -> None:
        required = (
            "cmp_fn_mut_state_transition("
            "callback_after_v2, &v1, key1, callback_after_v1)"
        )
        mutated = self.text.replace(required, "true", 1)
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and required in error
            for error in errors
        ))

    def test_all_48_chaining_contracts_expose_partial_cmp_branches(
        self,
    ) -> None:
        rows = []
        for row in self.pending:
            family = builder.build_contract(row).family
            method = row["method_name"]
            arity = len(
                row["signature"]["owner_generics"]["type_parameters"]
            )
            if (
                family == "tuple_short_circuit"
                and method in {"lt", "le", "gt", "ge"}
                and arity > 1
            ) or (
                family == "slice_order_dispatch"
                and method in {"lt", "le", "gt", "ge"}
            ):
                rows.append(row)
        self.assertEqual(len(rows), 48)
        for row in rows:
            family, block = self.blocks[row["row_id"]]
            relation = row["method_name"].capitalize()
            with self.subTest(row_id=row["row_id"]):
                self.assertNotIn("cmp_private_chaining_outcome", block)
                self.assertNotIn("cmp_slice_chaining_prefix", block)
                self.assertIn(
                    "!= Some(core::cmp::Ordering::Equal)",
                    block,
                )
                self.assertIn(
                    "is Some && cmp_relation_holds",
                    block,
                )
                self.assertIn(
                    f"cmp_relation_holds(CmpRelation::{relation},",
                    block,
                )
                if family == "tuple_short_circuit":
                    self.assertIn(
                        "as PartialOrd>::partial_cmp",
                        block,
                    )
                    self.assertIn(
                        "== Some(core::cmp::Ordering::Equal)",
                        block,
                    )
                else:
                    self.assertIn(
                        "cmp_lexicographic_partial_cmp_prefix",
                        block,
                    )

    def test_every_chaining_contract_rejects_each_branch_mutation(
        self,
    ) -> None:
        rows = []
        for row in self.pending:
            family = builder.build_contract(row).family
            method = row["method_name"]
            arity = len(
                row["signature"]["owner_generics"]["type_parameters"]
            )
            if (
                family == "tuple_short_circuit"
                and method in {"lt", "le", "gt", "ge"}
                and arity > 1
            ) or (
                family == "slice_order_dispatch"
                and method in {"lt", "le", "gt", "ge"}
            ):
                rows.append(row)
        self.assertEqual(len(rows), 48)
        for row in rows:
            _, block = self.blocks[row["row_id"]]
            relation = row["method_name"].capitalize()
            mutations = {
                "equal_continue": (
                    "!= Some(core::cmp::Ordering::Equal)",
                    "== Some(core::cmp::Ordering::Equal)",
                ),
                "non_equal_relation": (
                    f"cmp_relation_holds(CmpRelation::{relation},",
                    "cmp_relation_holds(CmpRelation::Lt,"
                    if relation != "Lt"
                    else "cmp_relation_holds(CmpRelation::Gt,",
                ),
                "none_false": (
                    "is Some && cmp_relation_holds",
                    "is None && cmp_relation_holds",
                ),
            }
            for branch, (fragment, replacement) in mutations.items():
                with self.subTest(
                    row_id=row["row_id"],
                    branch=branch,
                ):
                    self.assertIn(fragment, block)
                    mutated_block = block.replace(fragment, replacement)
                    mutated = self.text.replace(block, mutated_block, 1)
                    errors = checker.contract_text_errors(
                        mutated, self.rows
                    )
                    self.assertTrue(
                        any(
                            error.startswith(
                                f"missing_family_fragment:{row['row_id']}:"
                            )
                            and fragment in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_removed_bytewise_branch_mutation_is_rejected(self) -> None:
        mutated = self.text.replace(
            "CmpEqDispatch::Bytewise",
            "CmpEqDispatch::GenericElementLoop",
            1,
        )
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "CmpEqDispatch::Bytewise" in error
            for error in errors
        ))

    def test_unparenthesized_tuple_biconditional_is_rejected(self) -> None:
        mutated = self.text.replace(
            "(result <==> (",
            "result <==> ",
            1,
        )
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "(result <==> (" in error
            for error in errors
        ))

    def test_vacuous_direct_ensures_is_rejected(self) -> None:
        row = next(
            row
            for row in self.pending
            if builder.build_contract(row).family == "ordering_value"
        )
        family, block = self.blocks[row["row_id"]]
        mutated_block = block.replace(
            "ensures\n        ",
            "ensures\n        true,\n        ",
            1,
        )
        mutated = self.text.replace(block, mutated_block, 1)
        self.assertIn(
            f"vacuous_direct_ensures:{row['row_id']}",
            checker.contract_text_errors(mutated, self.rows),
        )

    def test_collapsed_always_applicable_dispatch_is_rejected(self) -> None:
        row = next(
            row
            for row in self.pending
            if row["target"] == "<[T] as PartialOrd<[T]>>::partial_cmp"
        )
        family, block = self.blocks[row["row_id"]]
        mutated_block = block.replace(
            "CmpOrderDispatch::AlwaysApplicableOrd",
            "CmpOrderDispatch::UnsignedBytewiseOrd",
        ).replace(
            "cmp_hidden_ord_lexicographic_prefix",
            "cmp_lexicographic_partial_cmp_prefix",
        )
        mutated = self.text.replace(block, mutated_block, 1)
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and (
                "CmpOrderDispatch::AlwaysApplicableOrd" in error
                or "cmp_hidden_ord_lexicographic_prefix" in error
            )
            for error in errors
        ))

    def test_length_fallback_without_no_decisive_guard_is_rejected(self) -> None:
        row = next(
            row
            for row in self.pending
            if row["target"] == "<[T; N] as PartialOrd<[T; N]>>::le"
        )
        family, block = self.blocks[row["row_id"]]
        required = (
            "if outcomes.len() > 0 && outcomes.last() "
            "!= Some(core::cmp::Ordering::Equal)"
        )
        mutated_block = block.replace(
            required,
            "if outcomes.len() == N || outcomes.len() == 0",
            1,
        )
        mutated = self.text.replace(block, mutated_block, 1)
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and required in error
            for error in errors
        ))

    def test_weakened_clamp_mutation_is_rejected(self) -> None:
        mutated = self.text.replace("{ min } else if", "{ value } else if", 1)
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "{ min } else if" in error
            for error in errors
        ))

    def test_removed_clamp_panic_outcome_mutation_is_rejected(self) -> None:
        mutated = self.text.replace(
            "CmpCallOutcome::Panicked",
            "CmpCallOutcome::Returned(value)",
            1,
        )
        errors = checker.contract_text_errors(mutated, self.rows)
        self.assertTrue(any(
            error.startswith("missing_family_fragment:")
            and "CmpCallOutcome::Panicked" in error
            for error in errors
        ))

    def test_all_reference_forwarding_wrapper_mutations_are_rejected(
        self,
    ) -> None:
        rows = [
            row
            for row in self.pending
            if builder.build_contract(row).family == "reference_forwarding"
        ]
        self.assertEqual(len(rows), 12)
        for row in rows:
            family, block = self.blocks[row["row_id"]]
            required = checker.required_family_fragments(row, family)
            direct_call = required[0]
            with self.subTest(row_id=row["row_id"]):
                self.assertIn(direct_call, block)
                self.assertNotIn("cmp_reference_forward_result", block)
                mutated_block = block.replace(
                    direct_call,
                    "cmp_reference_forward_result",
                    1,
                )
                mutated = self.text.replace(block, mutated_block, 1)
                errors = checker.contract_text_errors(mutated, self.rows)
                self.assertTrue(any(
                    error.startswith("missing_family_fragment:")
                    and direct_call in error
                    for error in errors
                ))

    def valid_review(self) -> dict[str, object]:
        request = checker.load(builder.REVIEW_REQUEST)
        row_ids = [row["row_id"] for row in self.rows]
        impossible_ids = sorted(
            row["row_id"] for row in self.impossible
        )
        return {
            "schema_version": 1,
            "module": "core::cmp",
            "review_type": "bounded_inventory_and_specification",
            "producer_role": "reviewer",
            "independence": {
                "independent": True,
                "artifacts_modified_by_reviewer": [],
            },
            "review_request": {
                "path": str(builder.REVIEW_REQUEST.relative_to(builder.ROOT)),
                "sha256": checker.sha256(builder.REVIEW_REQUEST),
            },
            "canonical_handoff": {
                "path": str(
                    checker.CANONICAL_HANDOFF.relative_to(builder.ROOT)
                ),
                "sha256": checker.sha256(checker.CANONICAL_HANDOFF),
            },
            "artifact_bindings": request["artifacts"],
            "review": {
                "status": "done",
                "implementation_proofs_authorized": True,
                "unresolved_findings": [],
                "question_verdicts": [
                    {
                        "question": question,
                        "verdict": (
                            "no"
                            if question.startswith(
                                "Are any whole target outcomes hidden"
                            )
                            else "satisfied"
                        ),
                    }
                    for question in request["review_questions"]
                ],
                "outcome_equivalence": {
                    "accepted": True,
                    "reviewed_row_count": len(row_ids),
                    "reviewed_row_ids_sha256": checker.compact_hash(row_ids),
                    "non_exact_equivalence_count": 0,
                },
                "genuinely_impossible": {
                    "accepted": True,
                    "approved_row_count": len(impossible_ids),
                    "approved_row_ids": impossible_ids,
                    "approved_row_ids_sha256": checker.compact_hash(
                        impossible_ids
                    ),
                    "evidence_path": str(
                        builder.FLOAT_MODEL_BOUNDARY.relative_to(
                            builder.ROOT
                        )
                    ),
                    "evidence_sha256": checker.sha256(
                        builder.FLOAT_MODEL_BOUNDARY
                    ),
                },
            },
        }

    def test_canonical_review_payload_passes(self) -> None:
        self.assertEqual(
            self.review_errors_for(self.valid_review()),
            [],
        )

    def test_accepted_review_authorizes_proof_layout(self) -> None:
        self.assertTrue(checker.proof_phase_authorized(self.rows))

    def review_errors_for(self, payload: dict[str, object]) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review.json"
            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            with mock.patch.object(checker, "INDEPENDENT_REVIEW", path):
                return checker.review_errors(self.rows)

    def test_canonical_reviewer_role_literal_is_enforced(self) -> None:
        review = self.valid_review()
        review["producer_role"] = "independent_specification_reviewer"
        self.assertIn(
            "independent_reviewer_role_invalid",
            self.review_errors_for(review),
        )

    def test_canonical_review_status_literal_is_enforced(self) -> None:
        review = self.valid_review()
        decision = review["review"]
        assert isinstance(decision, dict)
        decision["status"] = "accepted"
        self.assertIn(
            "independent_review_status_not_done",
            self.review_errors_for(review),
        )

    def test_canonical_review_authorization_is_enforced(self) -> None:
        review = self.valid_review()
        decision = review["review"]
        assert isinstance(decision, dict)
        decision["implementation_proofs_authorized"] = False
        self.assertIn(
            "review_does_not_authorize_proofs",
            self.review_errors_for(review),
        )

    def test_float_exception_row_approval_is_enforced(self) -> None:
        review = self.valid_review()
        decision = review["review"]
        assert isinstance(decision, dict)
        impossible = decision["genuinely_impossible"]
        assert isinstance(impossible, dict)
        impossible["approved_row_ids"] = []
        self.assertIn(
            "genuinely_impossible_review_ids_mismatch",
            self.review_errors_for(review),
        )

    def test_review_independence_is_enforced(self) -> None:
        review = self.valid_review()
        independence = review["independence"]
        assert isinstance(independence, dict)
        independence["artifacts_modified_by_reviewer"] = [
            "specs/generated_cmp_specs.rs"
        ]
        self.assertIn(
            "independent_review_not_independent",
            self.review_errors_for(review),
        )

    def test_duplicate_or_malformed_review_artifact_bindings_are_rejected(
        self,
    ) -> None:
        for mutation in ("duplicate", "malformed"):
            review = self.valid_review()
            bindings = review["artifact_bindings"]
            assert isinstance(bindings, list)
            if mutation == "duplicate":
                bindings.append(copy.deepcopy(bindings[0]))
            else:
                bindings.append("ignored malformed binding")
            with self.subTest(mutation=mutation):
                self.assertIn(
                    "independent_review_artifact_bindings_schema_invalid",
                    self.review_errors_for(review),
                )

    def test_proof_generation_requires_accepted_review(self) -> None:
        manifest = checker.load(builder.MANIFEST)
        request = checker.load(builder.REVIEW_REQUEST)
        self.assertFalse(manifest["implementation_proofs_authorized"])
        self.assertFalse(request["implementation_proofs_authorized"])
        self.assertTrue(checker.proof_phase_authorized(self.rows))
        harnesses = builder.ROOT / "proof_harnesses"
        self.assertTrue(harnesses.exists() and any(harnesses.iterdir()))
        self.assertNotIn(
            "proof_harnesses_exist_before_spec_acceptance",
            checker.validate(
                require_evidence=True,
                require_review=True,
            ),
        )

    def test_pre_review_package_passes_all_non_review_gates(self) -> None:
        self.assertEqual(
            checker.validate(
                require_evidence=False,
                require_review=False,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
