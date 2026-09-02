from __future__ import annotations

import unittest
from collections import Counter

from tools import build_inventory


class CmpInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.derived = build_inventory.derive_inventory(
            build_inventory.read_rustdoc()
        )
        cls.rows = cls.derived["inventory"]["rows"]
        cls.rows_by_target = {row["target"]: row for row in cls.rows}

    def test_inventory_reconciles_without_duplicate_or_foreign_targets(self) -> None:
        reconciliation = self.derived["reconciliation"]
        self.assertTrue(reconciliation["equation"]["holds"])
        self.assertTrue(reconciliation["all_audits_pass"])
        self.assertFalse(reconciliation["hard_coded_acceptance_total"])
        self.assertEqual(
            reconciliation["stable_inventory_total"],
            sum(reconciliation["disposition_counts"].values()),
        )
        self.assertEqual(
            len(self.rows),
            len({row["row_id"] for row in self.rows}),
        )
        self.assertEqual(
            len(self.rows),
            len({row["target"] for row in self.rows}),
        )
        for row in self.rows:
            target = row["target"].lower()
            self.assertNotIn("result", target)
            self.assertNotIn("btreemap", target)
            self.assertNotIn("btreeset", target)

    def test_hidden_stable_and_unstable_items_are_adjudicated(self) -> None:
        hidden_eq = self.rows_by_target["Eq::assert_receiver_is_total_eq"]
        self.assertEqual(hidden_eq["implementation_kind"], "trait_default")
        self.assertEqual(
            hidden_eq["source_visibility"],
            "doc_hidden_but_public_and_stable",
        )
        self.assertEqual(hidden_eq["deprecation"]["since"], "1.95.0")
        self.assertEqual(hidden_eq["stable_since"], "1.0.0")

        exclusions = {
            record["target"]: record
            for record in self.derived["exclusions"]["records"]
        }
        self.assertEqual(
            exclusions["Eq::assert_fields_are_eq"]["reason"],
            "unstable_main_stability",
        )
        for method in (
            "__chaining_lt",
            "__chaining_le",
            "__chaining_gt",
            "__chaining_ge",
        ):
            self.assertEqual(
                exclusions[f"PartialOrd::{method}"]["reason"],
                "doc_hidden_perma_unstable_internal_dispatch",
            )
        self.assertEqual(
            exclusions["Ordering::as_raw"]["reason"],
            "private_non_public_method",
        )
        for type_name in ("f16", "f128"):
            for method in ("eq", "ne", "partial_cmp", "lt", "le", "gt", "ge"):
                trait = (
                    "PartialEq"
                    if method in ("eq", "ne")
                    else "PartialOrd"
                )
                target = f"<{type_name} as {trait}<{type_name}>>::{method}"
                self.assertNotIn(target, self.rows_by_target)
                self.assertEqual(
                    exclusions[target]["reason"],
                    "unstable_self_type",
                )
        for function in ("minmax", "minmax_by", "minmax_by_key"):
            self.assertEqual(
                exclusions[f"core::cmp::{function}"]["reason"],
                "unstable_main_stability",
            )
        self.assertIn("core::cmp::min", self.rows_by_target)
        self.assertEqual(
            self.rows_by_target["core::cmp::min"]["const_callability"]["state"],
            "unstable",
        )

    def test_default_ownership_expands_hidden_tuples_without_overlap(self) -> None:
        ownership = self.derived["ownership"]
        default_audit = self.derived["default_audit"]
        self.assertEqual(default_audit["status"], "pass")
        self.assertEqual(default_audit["unresolved_binding_count"], 0)
        self.assertEqual(default_audit["concrete_default_overlap_count"], 0)
        self.assertEqual(
            default_audit["default_binding_slot_count"],
            sum(default_audit["binding_owner_counts"].values()),
        )
        stable_records = [
            record
            for record in ownership["records"]
            if record["stable_runtime_implementation"]
        ]
        self.assertEqual(
            ownership["stable_cmp_trait_impl_count"],
            len(stable_records),
        )
        self.assertEqual(
            ownership["stable_impl_counts_by_trait"],
            dict(sorted(Counter(
                record["trait_name"] for record in stable_records
            ).items())),
        )

        hidden_tuple_arities = {
            int(row["row_id"].split("-")[3])
            for row in self.rows
            if row["row_id"].startswith("source-tuple-arity-")
        }
        self.assertEqual(hidden_tuple_arities, set(range(2, 13)))
        self.assertIn("<(T,) as PartialEq<(T,)>>::eq", self.rows_by_target)

        reverse_partial_ord = next(
            record
            for record in stable_records
            if record["self_type"] == "Reverse<T>"
            and record["trait_name"] == "PartialOrd"
        )
        self.assertTrue(reverse_partial_ord["effective_method_bindings"])
        self.assertTrue(all(
            binding["owner_kind"] == "concrete_override"
            for binding in reverse_partial_ord["effective_method_bindings"]
        ))

        option_partial_ord = next(
            record
            for record in stable_records
            if record["self_type"] == "Option<T>"
            and record["trait_name"] == "PartialOrd"
        )
        option_owners = {
            binding["method"]: binding["owner_kind"]
            for binding in option_partial_ord["effective_method_bindings"]
        }
        self.assertEqual(option_owners["partial_cmp"], "concrete_override")
        for method in ("lt", "le", "gt", "ge"):
            self.assertEqual(
                option_owners[method],
                "inherited_trait_default",
            )

    def test_specialization_slots_and_marker_expansions_are_unambiguous(self) -> None:
        audit = self.derived["specialization_audit"]
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["ambiguous_slot_count"], 0)
        self.assertEqual(
            audit["specialization_executable_identity_count"],
            2 * audit["specialization_slot_count"],
        )
        self.assertEqual(
            audit["marker_impl_count"],
            sum(audit["marker_impl_counts_by_trait"].values()),
        )
        self.assertEqual(
            set(audit["marker_impl_counts_by_trait"]),
            {"BytewiseEq", "AlwaysApplicableOrd", "UnsignedBytewiseOrd"},
        )
        for slot in audit["slots"]:
            self.assertTrue(slot["selection_is_unambiguous"])
            self.assertEqual(len(slot["specialized_identities"]), 1)
        self.assertEqual(
            audit["excluded_specialization_candidate"]["status"],
            "commented_out",
        )
        self.assertIn(
            "unsound",
            audit["excluded_specialization_candidate"]["reason"],
        )
        contains = audit["excluded_out_of_scope_specialization_families"][0]
        self.assertEqual(contains["trait_name"], "SliceContains")
        self.assertEqual(
            contains["executable_identity_count"],
            contains["default_identity_count"]
            + contains["concrete_override_count"],
        )

    def test_exact_vstd_requires_full_identity_and_signature_match(self) -> None:
        audit = self.derived["exact_vstd"]
        self.assertEqual(
            audit["exact_match_count"],
            len(audit["records"]),
        )
        self.assertEqual(
            audit["candidate_count"],
            audit["exact_match_count"] + audit["rejected_candidate_count"],
        )
        self.assertEqual(
            audit["exact_match_count"] + audit["unmatched_inventory_count"],
            len(self.rows),
        )
        for record in audit["records"]:
            self.assertTrue(record["full_signature_shape_matches"])
            self.assertTrue(record["implementation_identity_matches"])
            self.assertTrue(record["lifetime_comparison"]["alpha_equivalent"])
            self.assertTrue(all(
                comparison["matches"]
                for comparison in record["signature_comparison"].values()
            ))
            self.assertTrue(
                record["evidence"]["required_declaration_fragments"]
            )

        noncanonical = [
            record
            for record in audit["records"]
            if not record["canonical_upstream_binding"]
        ]
        self.assertEqual(
            {record["target"] for record in noncanonical},
            {
                "Ordering::is_eq",
                "Ordering::is_ne",
                "Ordering::is_lt",
                "Ordering::is_gt",
                "Ordering::is_le",
                "Ordering::is_ge",
                "Ordering::reverse",
                "Ordering::then",
            },
        )
        self.assertTrue(all(
            record["evidence"]["candidate_source_untracked"]
            for record in noncanonical
        ))
        self.assertFalse(
            audit["loading_audit"]["ordering_coverage_is_canonical_upstream"]
        )
        float_rows = [
            row
            for row in self.rows
            if row["owner_type"] in {"f32", "f64"}
            and row["method_name"]
            in {"eq", "ne", "partial_cmp", "lt", "le", "gt", "ge"}
        ]
        self.assertEqual(len(float_rows), 14)
        self.assertTrue(all(
            row["disposition"] == "pending"
            and row["vstd_binding_ids"] == []
            and row["specification_blocker"]["kind"]
            == "loaded_vstd_float_model_boundary"
            for row in float_rows
        ))
        rejected_float_ids = {
            record["row_id"]
            for record in audit["rejected_candidates"]
            if record.get("status") == "rejected_semantically_incomplete"
        }
        self.assertEqual(
            rejected_float_ids,
            {row["row_id"] for row in float_rows},
        )
        self.assertTrue(all(
            record["semantic_complete"] is False
            and "observable_result_semantics"
            in record["mismatch_dimensions"]
            for record in audit["rejected_candidates"]
            if record.get("row_id") in rejected_float_ids
        ))
        self.assertEqual(
            self.rows_by_target["Ordering::then_with"]["disposition"],
            "pending",
        )
        self.assertEqual(
            self.rows_by_target[
                "<&mut A as PartialEq<&mut B>>::eq"
            ]["disposition"],
            "pending",
        )
        self.assertEqual(
            self.rows_by_target[
                "<&mut A as PartialEq<&mut B>>::eq"
            ]["matching_shape"]["receiver_and_argument_mutability"],
            ["shared>mutable", "shared>mutable"],
        )
        self.assertEqual(
            self.rows_by_target[
                "<Option<T> as Ord>::cmp"
            ]["disposition"],
            "exact_vstd",
        )
        rejected = {
            record["candidate_id"]: record
            for record in audit["rejected_candidates"]
        }
        clamp = self.rows_by_target["Ord::clamp"]
        self.assertEqual(clamp["disposition"], "pending")
        rejected_clamp = rejected["vstd-trait-default-ord-clamp"]
        self.assertEqual(
            rejected_clamp["status"],
            "rejected_as_semantically_incomplete",
        )
        self.assertEqual(
            rejected_clamp["mismatch_dimensions"],
            ["observable_outcome", "panic_domain"],
        )
        self.assertTrue(rejected_clamp["inventory_target_present"])
        for candidate_id in (
            "vstd-trait-required-partialeq-eq",
            "vstd-trait-required-partialord-partial_cmp",
            "vstd-trait-required-ord-cmp",
        ):
            self.assertFalse(rejected[candidate_id]["inventory_target_present"])
            self.assertIn(
                "implementation_identity",
                rejected[candidate_id]["mismatch_dimensions"],
            )


if __name__ == "__main__":
    unittest.main()
