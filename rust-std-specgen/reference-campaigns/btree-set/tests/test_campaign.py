from __future__ import annotations

import hashlib
import inspect
import json
import re
import unittest
from pathlib import Path
from unittest import mock

from tools import campaign_model
from tools import check_campaign
from tools import completeness_audit
from tools import proof_model
from tools import run_feedback_gate
from tools import run_independent_review
from tools import run_verus_matrix
from tools import verus_evidence


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = json.loads(
            (ROOT / "inventory/btree_set_exec_fn_inventory.json").read_text(
                encoding="utf-8"
            )
        )
        cls.rows, cls.exclusions, _ = campaign_model.derive_inventory(
            campaign_model.load_rustdoc()
        )

    def test_inventory_is_live_and_reconciled(self) -> None:
        stored = self.inventory["rows"]
        self.assertEqual(
            [row["target_id"] for row in stored],
            [row.target_id for row in self.rows],
        )
        dispositions = {
            name: sum(row["disposition"] == name for row in stored)
            for name in (
                "exact_vstd",
                "generated",
                "genuinely_impossible",
                "pending",
            )
        }
        self.assertEqual(
            self.inventory["counts"]["stable_inventory_total"], len(stored)
        )
        self.assertEqual(
            len(stored),
            sum(dispositions.values()),
        )
        self.assertEqual(dispositions["pending"], 0)

    def test_required_owned_surface_is_present(self) -> None:
        selected = {
            (row["owner_type"], row["trait"], row["method"])
            for row in self.inventory["rows"]
        }
        required = {
            ("BTreeSet", "inherent", "extract_if"),
            ("BTreeSet", "inherent", "range"),
            ("BTreeSet", "inherent", "difference"),
            ("BTreeSet", "inherent", "symmetric_difference"),
            ("BTreeSet", "inherent", "intersection"),
            ("BTreeSet", "inherent", "union"),
            ("BTreeSet", "Sub", "sub"),
            ("BTreeSet", "BitAnd", "bitand"),
            ("BTreeSet", "BitOr", "bitor"),
            ("BTreeSet", "BitXor", "bitxor"),
            ("Difference", "Iterator", "next"),
            ("ExtractIf", "Iterator", "next"),
            ("Intersection", "Iterator", "next"),
            ("IntoIter", "DoubleEndedIterator", "next_back"),
            ("Iter", "ExactSizeIterator", "len"),
            ("Range", "DoubleEndedIterator", "next_back"),
            ("SymmetricDifference", "Iterator", "next"),
            ("Union", "Iterator", "next"),
        }
        self.assertTrue(required.issubset(selected), required - selected)

    def test_unstable_and_non_executable_items_are_exclusions(self) -> None:
        names = {str(row["name"]) for row in self.exclusions}
        self.assertIn("<BTreeSet as Extend>::extend_one", names)
        self.assertTrue(any("Entry" in name for name in names))
        self.assertTrue(any("Cursor" in name for name in names))
        self.assertFalse(
            any(
                row["method"] == "extend_one"
                for row in self.inventory["rows"]
            )
        )

    def test_exact_vstd_rows_have_all_signature_dimensions(self) -> None:
        exact = [
            row
            for row in self.inventory["rows"]
            if row["disposition"] == "exact_vstd"
        ]
        self.assertEqual(
            {row["method"] for row in exact},
            {
                "clear",
                "clone",
                "contains",
                "default",
                "get",
                "insert",
                "is_empty",
                "iter",
                "len",
                "new",
                "remove",
            },
        )
        for row in exact:
            reference = row["vstd_reference"]
            self.assertIn("parsed_vstd_signature", reference)
            self.assertEqual(
                reference["match_dimensions"],
                list(campaign_model.MATCH_DIMENSIONS),
            )
            self.assertTrue(
                all(
                    reference["dimensions"][dimension]["matched"]
                    for dimension in campaign_model.MATCH_DIMENSIONS
                )
            )
            for dimension in campaign_model.MATCH_DIMENSIONS:
                self.assertIn("source", reference["dimensions"][dimension])
                self.assertIn("vstd", reference["dimensions"][dimension])

    def test_exact_vstd_parser_rejects_signature_drift(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.disposition == "exact_vstd" and row.function["name"] == "len"
        )
        reference = campaign_model.exact_vstd_evidence(row)
        source = dict(reference["source_structural_signature"])
        source["output"] = "bool"
        dimensions = campaign_model.signature_dimensions(
            row,
            source,
            reference["parsed_vstd_signature"],
        )
        self.assertFalse(dimensions["return_shape"]["matched"])

    def test_exact_vstd_reverse_scan_covers_every_declaration(self) -> None:
        scan = campaign_model.exact_vstd_reverse_scan(self.rows)
        self.assertTrue(scan["complete"], scan)
        self.assertEqual(scan["scanned_declaration_count"], 11)
        self.assertEqual(scan["matched_count"], 11)

        extra = campaign_model.VSTD_FILE.read_text(encoding="utf-8") + """
pub assume_specification<T>[ BTreeSet::<T>::invented ](
    value: &BTreeSet<T>,
) -> (result: bool)
    ensures
        result == true,
;
"""
        mutated = campaign_model.exact_vstd_reverse_scan(
            self.rows,
            source=extra,
        )
        self.assertFalse(mutated["complete"])
        self.assertEqual(len(mutated["unmatched_declarations"]), 1)

    def test_one_source_bound_harness_per_selected_row(self) -> None:
        rows = self.inventory["rows"]
        directories = {
            path.name
            for path in (ROOT / "proof_harnesses").iterdir()
            if path.is_dir()
        }
        self.assertEqual(directories, {row["target_id"] for row in rows})
        for row in rows:
            target = ROOT / "proof_harnesses" / row["target_id"]
            self.assertEqual(
                sha256_file(target / "source_excerpt.rs"),
                row["source_sha256"],
            )
            implementation = (target / "implementation_proof.rs").read_text(
                encoding="utf-8"
            )
            self.assertIn("pub fn implementation", implementation)
            self.assertEqual(
                implementation.count("#[verifier::external_body]"),
                proof_model.literal_external_body_count(
                    self.rows[row["ordinal"] - 1]
                ),
            )
            self.assertNotIn(
                "#[verifier::external_body]\npub fn implementation",
                implementation,
            )

    def test_proof_generator_uses_real_api_shapes_and_contracts(self) -> None:
        for row in self.rows:
            implementation = proof_model.source(row)
            completeness = proof_model.source(row, completeness=True)
            self.assertNotIn("pub struct Snapshot", implementation)
            self.assertIn("pub fn implementation", implementation)
            self.assertIn(row.contract_fingerprint, implementation)
            self.assertIn(row.contract_fingerprint, completeness)
            self.assertNotIn("source_contract_observation", completeness)
            self.assertNotIn("ContractInput", completeness)
            self.assertNotIn("ContractOutcome", completeness)
            self.assertNotIn("accepted_contract(", completeness)
            self.assertNotIn(
                "pub uninterp spec fn source_sequence", completeness
            )
            self.assertNotIn(
                "pub uninterp spec fn source_optional_item", completeness
            )
            self.assertNotIn(
                "pub uninterp spec fn source_set_transition", completeness
            )
            self.assertNotIn(
                "pub uninterp spec fn source_callback_sequence", completeness
            )
            self.assertNotIn("pub struct Snapshot", implementation)
            self.assertNotIn("pub struct Outcome", implementation)
            self.assertNotIn("PrivateResult<", implementation)
            self.assertNotIn("mutated_source_step", implementation)
            self.assertIn(
                proof_model.dependency_operation(row),
                implementation,
            )
            self.assertNotEqual(
                proof_model.projection_for(
                    row, campaign_model.proxy_parts(row)[2]
                ).lower_type,
                campaign_model.proxy_parts(row)[2],
            )

            self.assertIn(
                "pub open spec fn accepted_clause_1",
                completeness,
            )
            for index, requirement in enumerate(
                proof_model.contract_requirements(row), start=1
            ):
                self.assertIn(requirement, implementation)
                self.assertIn(
                    f"Accepted requirement {index} sha256: "
                    f"{campaign_model.sha256_text(requirement)}",
                    completeness,
                )
                self.assertGreaterEqual(
                    completeness.count(f"accepted_requirement_{index}("),
                    2,
                )
            for index, clause in enumerate(
                proof_model.contract_lines(row), start=1
            ):
                self.assertIn(
                    f"Accepted clause {index} sha256: "
                    f"{campaign_model.sha256_text(clause)}",
                    completeness,
                )
                self.assertGreaterEqual(
                    completeness.count(f"accepted_clause_{index}("),
                    3,
                )
            projection = proof_model.projection_for(
                row, campaign_model.proxy_parts(row)[2]
            )
            lower_clauses = proof_model.emitted_dependency_contract_lines(
                row, projection
            )
            for clause in lower_clauses:
                self.assertIn(
                    check_campaign.structural_rust(clause),
                    check_campaign.structural_rust(implementation),
                )
            mutation = proof_model.source(row, mutation=True)
            descriptor = proof_model.mutation_descriptor(row)
            implementation_body = check_campaign.executable_function_body(
                implementation,
                "implementation",
            )
            mutation_body = check_campaign.executable_function_body(
                mutation,
                "implementation",
            )
            semantic_implementation_body = implementation_body
            semantic_mutation_body = mutation_body
            if row.function["name"] == "is_subset":
                semantic_implementation_body = (
                    check_campaign.executable_function_body(
                        implementation,
                        "rust_1_96_selected_is_subset_source",
                    )
                )
                semantic_mutation_body = (
                    check_campaign.executable_function_body(
                        mutation,
                        "rust_1_96_selected_is_subset_source",
                    )
                )
            self.assertIn(
                descriptor["original_fragment"],
                semantic_implementation_body,
            )
            self.assertIn(
                descriptor["mutated_fragment"],
                semantic_mutation_body,
            )
            self.assertNotEqual(
                semantic_implementation_body,
                semantic_mutation_body,
            )
            self.assertNotIn("mutated_source_step", mutation)
            self.assertNotIn("private_source_branch", implementation)
            if proof_model.uses_private_branch(row):
                self.assertTrue(
                    all(
                        implementation_body.count(f"{name}(") == 1
                        for name in proof_model.dependency_call_names(row)
                    )
                )
            projection = proof_model.projection_for(
                row,
                campaign_model.proxy_parts(row)[2],
            )
            if (
                projection.kind == "set_adapter"
                and not proof_model.requires_selected_public_composition(row)
                and row.semantic_family not in {
                    "difference_adapter_construction",
                    "intersection_adapter_construction",
                }
            ):
                self.assertIn(
                    "remaining: Ghost(Seq::empty())",
                    mutation_body,
                )
            if projection.kind == "extract_state":
                self.assertIn(
                    "pending: Ghost(Seq::empty())",
                    mutation_body,
                )
                self.assertIn(
                    "remaining: Ghost(Seq::empty())",
                    mutation_body,
                )
            if row.owner["name"] == "BTreeSet":
                self.assertIn("BTreeSet", implementation)
            else:
                self.assertIn(row.owner["name"], implementation)

    def test_literal_external_body_accounting_is_category_specific(self) -> None:
        totals = proof_model.aggregate_literal_external_body_counts(self.rows)
        self.assertEqual(
            totals,
            {
                "target": 0,
                "completeness": 0,
                "dependency": 110,
                "helper": 189,
                "harness": 299,
            },
        )
        self.assertEqual(
            sum(
                len(
                    proof_model.standard_library_assumption_boundaries(row)
                )
                for row in self.rows
            ),
            3,
        )
        for row in self.rows:
            counts = proof_model.literal_external_body_counts(row)
            implementation = proof_model.source(row)
            completeness = proof_model.source(row, completeness=True)
            self.assertEqual(
                counts["harness"],
                implementation.count("#[verifier::external_body]"),
            )
            self.assertEqual(
                counts["harness"],
                len(
                    proof_model.literal_external_body_function_names(
                        implementation
                    )
                ),
            )
            self.assertEqual(
                counts["completeness"],
                completeness.count("#[verifier::external_body]"),
            )
            self.assertEqual(
                counts["harness"],
                counts["target"] + counts["dependency"] + counts["helper"],
            )

    def test_contracts_expose_principal_semantics(self) -> None:
        errors = check_campaign.verify_contract_semantics(self.rows)
        self.assertEqual(errors, [])
        vocabulary = campaign_model.SHARED_VOCABULARY
        self.assertIn("extract_if_panic_preserves_elements", vocabulary)
        self.assertIn("extract_if_partial_drop_set", vocabulary)
        self.assertIn("pub open spec fn range_contains", vocabulary)
        self.assertIn("pub open spec fn apply_set_hash", vocabulary)
        self.assertIn("pub open spec fn apply_debug_shape", vocabulary)
        self.assertIn("pub open spec fn retain_decisions", vocabulary)
        self.assertIn("pub open spec fn extract_if_decisions", vocabulary)
        self.assertIn("stable_tie_order", vocabulary)
        self.assertNotIn("source_contract_observation", vocabulary)

    def test_every_ordered_generated_contract_binds_comparison_laws(
        self,
    ) -> None:
        ordered = [
            row
            for row in self.rows
            if row.disposition == "generated"
            and (
                "core::cmp::Ord" in row.proxy_signature
                or "core::cmp::PartialOrd" in row.proxy_signature
            )
        ]
        self.assertEqual(len(ordered), 46)
        for row in ordered:
            law = check_campaign.required_comparison_law(row)
            self.assertTrue(law, row.target_id)
            _binder, inputs, output, _where_clause = (
                campaign_model.proxy_parts(row)
            )
            clauses = campaign_model.ensure_lines(row, inputs, output)
            self.assertTrue(clauses, row.target_id)
            self.assertTrue(
                all(clause.startswith(f"({law}) ==> (") for clause in clauses),
                row.target_id,
            )

        with mock.patch.object(
            campaign_model,
            "comparison_law_binding",
            return_value=None,
        ):
            errors = check_campaign.verify_contract_semantics(self.rows)
        rejected = {
            error.split(":", 1)[0]
            for error in errors
            if "order-dependent contract is not guarded" in error
        }
        self.assertEqual(
            rejected,
            {row.target_id for row in ordered},
        )

        original_binding = campaign_model.comparison_law_binding

        def weaken_borrowed_binding(
            row: campaign_model.Row,
        ) -> str | None:
            binding = original_binding(row)
            if binding is not None and " && " in binding:
                return binding.split(" && ", 1)[0]
            return binding

        with mock.patch.object(
            campaign_model,
            "comparison_law_binding",
            side_effect=weaken_borrowed_binding,
        ):
            weakened_errors = check_campaign.verify_contract_semantics(
                self.rows
            )
        weakened_rejected = {
            error.split(":", 1)[0]
            for error in weakened_errors
            if "order-dependent contract is not guarded" in error
        }
        self.assertEqual(
            weakened_rejected,
            {
                "015_BTreeSet_inherent_range_2069",
                "033_BTreeSet_inherent_take_2094",
                "036_BTreeSet_inherent_split_off_2097",
            },
        )

    def test_append_proxy_preserves_source_method_bounds(
        self,
    ) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "035_BTreeSet_inherent_append_2096"
        )
        binder, _inputs, _output, where_clause = campaign_model.proxy_parts(
            row
        )
        self.assertIn(
            "A: alloc::alloc::Allocator + core::clone::Clone",
            binder,
        )
        self.assertEqual(
            where_clause,
            " where T: core::cmp::Ord, A: core::clone::Clone",
        )

    def test_append_checker_codegen_failure_is_narrowly_adjudicated(
        self,
    ) -> None:
        stderr = """
error[E0277]: the trait bound `T: std::cmp::Ord` is not satisfied
note: required by a bound in `vstd::laws_cmp::obeys_cmp`
det___rust_std_candidate_equal
"""
        self.assertEqual(
            run_feedback_gate.checker_limitation(
                run_feedback_gate.APPEND_TARGET,
                "verus_error",
                stderr,
            ),
            "spec-determinism-dropped-duplicate-method-where-clause",
        )
        self.assertIsNone(
            run_feedback_gate.checker_limitation(
                "alloc::collections::btree_set::BTreeSet::<T, A>::clear",
                "verus_error",
                stderr,
            )
        )
        adjudication = {
            "target": run_feedback_gate.APPEND_TARGET,
            "checker_limitation": (
                "spec-determinism-dropped-duplicate-method-where-clause"
            ),
        }
        self.assertTrue(
            check_campaign.narrowly_evidenced_checker_limitation(
                adjudication,
                stderr,
            )
        )
        adjudication["target"] = (
            "alloc::collections::btree_set::BTreeSet::<T, A>::clear"
        )
        self.assertFalse(
            check_campaign.narrowly_evidenced_checker_limitation(
                adjudication,
                stderr,
            )
        )

    def test_mutation_rejection_requires_semantic_verus_obligation(
        self,
    ) -> None:
        result = "verification results:: 40 verified, 1 errors"
        self.assertEqual(
            verus_evidence.mutation_rejection_kind(
                f"error: postcondition not satisfied\n{result}"
            ),
            "postcondition",
        )
        self.assertEqual(
            verus_evidence.mutation_rejection_kind(
                "error: invariant not satisfied at end of loop body\n"
                f"{result}"
            ),
            "loop_invariant",
        )
        self.assertEqual(
            verus_evidence.mutation_rejection_kind(
                f"error: precondition not satisfied\n{result}"
            ),
            "precondition",
        )
        self.assertEqual(
            verus_evidence.mutation_rejection_kind(
                f"error: assertion failed\n{result}"
            ),
            "assertion",
        )
        self.assertIsNone(
            verus_evidence.mutation_rejection_kind(
                f"error: mismatched types\n{result}"
            )
        )
        self.assertIsNone(
            verus_evidence.mutation_rejection_kind(
                "error: invariant not satisfied at end of loop body\n"
                "verification results:: 39 verified, 2 errors"
            )
        )

    def test_intersection_hint_completeness_uses_typed_nat_literals(
        self,
    ) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "087_Intersection_Iterator_size_hint_2356"
        )
        lower = next(
            field
            for field in proof_model.outcome_profile(row)
            if field.name == "lower"
        )
        self.assertEqual(
            lower.model_hint,
            "if adapter_state.variant == 3 { 1nat } else { 0nat }",
        )

    def test_semantic_checker_rejects_source_binding_mutations(self) -> None:
        vocabulary = campaign_model.SHARED_VOCABULARY

        def replace_body(name: str, replacement: str) -> str:
            body = check_campaign.spec_function_body(vocabulary, name)
            self.assertTrue(body, name)
            return vocabulary.replace(
                "{" + body + "}",
                "{" + replacement + "}",
                1,
            )

        mutations = {
            "borrowed_key_order": replace_body(
                "borrowed_key_order",
                "\n    Ordering::Less\n",
            ),
            "range_contains": replace_body("range_contains", "\n    true\n"),
            "split_before": replace_body(
                "split_before",
                """
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Greater {
        seq![items[0]] + split_before(items.drop_first(), key)
    } else {
        Seq::empty()
    }
""",
            ),
            "difference_stitch_step": replace_body(
                "difference_stitch_step",
                check_campaign.spec_function_body(
                    vocabulary,
                    "difference_stitch_step",
                ).replace(
                    "Seq::empty(),\n                            second,",
                    "Seq::empty(),\n                            second.drop_first(),",
                    1,
                ),
            ),
            "fn_mut_step_law": replace_body(
                "fn_mut_step_law", "\n    true\n"
            ),
            "difference_hint_lengths": replace_body(
                "difference_hint_lengths", "\n    (0, 0)\n"
            ),
            "difference_debug_shape": replace_body(
                "difference_debug_shape",
                "\n    iter_debug_shape(Iter::<'a, T>::default())\n",
            ),
            "extract_if_panic_transition": replace_body(
                "extract_if_panic_transition",
                """
    extract_if_drop_transition(iter)
""",
            ),
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                errors = check_campaign.verify_contract_semantics(
                    self.rows,
                    vocabulary_override=mutated,
                )
                self.assertTrue(
                    any(name in error for error in errors),
                    errors,
                )

    def test_determinism_models_use_principal_source_inputs(self) -> None:
        affected = {
            "015_BTreeSet_inherent_range_2069": (
                "range_start_kind",
                "range_end_kind",
            ),
            "034_BTreeSet_inherent_retain_2095": (
                "callback_decisions_model",
                "predicate_seed",
            ),
            "037_BTreeSet_inherent_extract_if_2098": (
                "callback_decisions_model",
                "range_start_kind",
            ),
            "079_Difference_Iterator_size_hint_2300": (
                "AdapterStateModel",
                "adapter_state_law_model",
            ),
            "010_Difference_Debug_fmt_2294": (
                "AdapterStateModel",
                "debug_shape_law_model",
            ),
        }
        by_id = {row.target_id: row for row in self.rows}
        for target_id, required in affected.items():
            source = proof_model.source(by_id[target_id], completeness=True)
            theorem_signature = source.split(
                "pub proof fn completeness(", 1
            )[1].split(")\n    requires", 1)[0]
            for token in required:
                self.assertIn(token, source)
            for forbidden in (
                "range_mask:",
                "decisions:",
                "hint_a:",
                "hint_b:",
                "debug_primary:",
                "debug_shape_valid:",
            ):
                self.assertNotIn(forbidden, theorem_signature)

    def test_checker_rejects_surrogate_and_whole_dependency(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.semantic_family == "difference_adapter_construction"
        )
        implementation = proof_model.source(row)
        completeness = proof_model.source(row, completeness=True)
        self.assertEqual(
            check_campaign.proof_text_policy_errors(
                implementation, completeness
            ),
            [],
        )
        self.assertTrue(
            check_campaign.proof_text_policy_errors(
                implementation,
                completeness
                + "\npub ghost struct ContractOutcome { value: int }\n",
            )
        )
        self.assertTrue(
            check_campaign.proof_text_policy_errors(
                implementation + "\npub struct PrivateResult<T> { value: T }\n",
                completeness,
            )
        )
        accepted = proof_model.contract_lines(row)
        projection = proof_model.projection_for(
            row, campaign_model.proxy_parts(row)[2]
        )
        lower = proof_model.emitted_dependency_contract_lines(
            row, projection
        )
        clean_errors = check_campaign.dependency_policy_errors(
            implementation,
            proof_model.dependency_function_name(row),
            accepted,
            lower,
        )
        self.assertEqual(clean_errors, [])
        mutated = implementation.replace(
            lower[1],
            accepted[0],
            1,
        )
        mutation_errors = check_campaign.dependency_policy_errors(
            mutated,
            proof_model.dependency_function_name(row),
            accepted,
            lower,
        )
        self.assertTrue(
            any("restates a public accepted clause" in error for error in mutation_errors)
        )

    def test_lower_contracts_are_authored_without_public_clause_lowering(
        self,
    ) -> None:
        authored_source = inspect.getsource(
            proof_model.dependency_contract_lines
        )
        self.assertNotIn("contract_lines(row", authored_source)
        self.assertNotIn("lower_state_clause(", authored_source)
        with mock.patch.object(
            proof_model,
            "contract_lines",
            side_effect=AssertionError("public contract consulted"),
        ):
            for row in self.rows:
                projection = proof_model.projection_for(
                    row, campaign_model.proxy_parts(row)[2]
                )
                self.assertTrue(
                    proof_model.dependency_contract_lines(row, projection)
                )

        by_id = {row.target_id: row for row in self.rows}
        retain = by_id["034_BTreeSet_inherent_retain_2095"]
        retain_lower = "\n".join(
            proof_model.dependency_contract_lines(
                retain,
                proof_model.projection_for(
                    retain, campaign_model.proxy_parts(retain)[2]
                ),
            )
        )
        self.assertIn("result.retained@ == retain_selected", retain_lower)
        self.assertIn("keeps", retain_lower)
        self.assertIn("result.callback_count@ == source.len()", retain_lower)
        self.assertNotIn("retain_decisions(&f", retain_lower)
        self.assertNotIn("retain_effect_trace", retain_lower)
        retain_body = check_campaign.executable_function_body(
            proof_model.source(retain), "implementation"
        )
        for token in (
            "let extraction = rust_1_96_selected_extract_if_begin(",
            "let consumed = rust_1_96_extract_if_for_each_drop::<T, F, A>(",
            "rust_1_96_rejoin_selected_extract_if::<T, A>(",
        ):
            self.assertIn(token, retain_body)
        self.assertIn(
            "iter: ExtractIf<",
            proof_model.source(retain),
        )

        extract = by_id["037_BTreeSet_inherent_extract_if_2098"]
        extract_lower = proof_model.dependency_contract_lines(
            extract,
            proof_model.projection_for(
                extract, campaign_model.proxy_parts(extract)[2]
            ),
        )
        self.assertEqual(len(extract_lower), 7)
        extract_body = check_campaign.executable_function_body(
            proof_model.source(extract), "implementation"
        )
        self.assertIn("let constructed = MapExtractIfState", extract_body)
        self.assertIn("predicate_state: Ghost(pred)", extract_body)
        self.assertIn("drop_valid: lower.drop_valid", extract_body)

        for row in self.rows:
            if not proof_model.uses_private_branch(row):
                continue
            inputs = proof_model.signature_parts(
                row, "implementation"
            )[0]
            selector_source, _selector_call = (
                proof_model.branch_selector_source_and_call(row, inputs)
            )
            self.assertNotIn("Ghost(", selector_source)
            facts = [
                proof_model.branch_operation_fact(row, pattern, guard)
                for pattern, guard, _suffix
                in proof_model.branch_arm_specs(row)
            ]
            self.assertEqual(len(facts), len(set(facts)))

        sorted_row = by_id["041_BTreeSet_FromIterator_from_iter_2138"]
        sorted_source = proof_model.source(sorted_row)
        for token in (
            "MapStableSortedInput<T>",
            "_stable_sort",
            "let sorted =",
            "dedup_last_sorted(sorted.sorted@)",
        ):
            self.assertIn(token, sorted_source)

        for target_id in ("048_BTreeSet_Extend_extend_2150",):
            extend_body = check_campaign.executable_function_body(
                proof_model.source(by_id[target_id]), "implementation"
            )
            for token in (
                "while input_index < input_steps",
                "let item =",
                "insert_keep_existing(before_insert, item)",
                "let ghost before_insert",
            ):
                self.assertIn(token, extend_body)

        borrowed_extend = check_campaign.executable_function_body(
            proof_model.source(
                by_id["049_BTreeSet_Extend_extend_2153"]
            ),
            "implementation",
        )
        self.assertIn(
            "rust_1_96_selected_cloned_extend_input(iter)",
            borrowed_extend,
        )
        self.assertIn(
            "rust_1_96_selected_owned_extend::<T, A>(",
            borrowed_extend,
        )
        self.assertNotIn("while input_index < input_steps", borrowed_extend)

        self.assertEqual(
            set(completeness_audit.LITERAL_RECONSTRUCTION_DIGESTS),
            {row.target_id for row in self.rows},
        )

    def test_selected_public_dependencies_are_executable_compositions(
        self,
    ) -> None:
        coverage = {
            row.target_id: proof_model.source_call_coverage(row)
            for row in self.rows
        }
        self.assertEqual(len(coverage), 92)
        self.assertTrue(
            all(record["complete"] is True for record in coverage.values())
        )
        self.assertTrue(
            all(
                record["source_sha256"] == row.source_sha256
                for row in self.rows
                for record in (coverage[row.target_id],)
            )
        )
        affected = {
            row.target_id: row
            for row in self.rows
            if proof_model.requires_selected_public_composition(row)
        }
        self.assertEqual(
            set(affected),
            {
                target_id
                for target_id, record in coverage.items()
                if record["selected_public_dependencies"]
            },
        )
        self.assertTrue(
            {
                "017_BTreeSet_inherent_symmetric_difference_2073",
                "019_BTreeSet_inherent_union_2077",
                "040_BTreeSet_inherent_is_empty_2102",
                "041_BTreeSet_FromIterator_from_iter_2138",
                "042_BTreeSet_From_from_2140",
                "049_BTreeSet_Extend_extend_2153",
                "059_Iter_Iterator_last_2201",
                "060_Iter_Iterator_min_2202",
                "061_Iter_Iterator_max_2203",
                "072_Range_Iterator_last_2267",
                "073_Range_Iterator_min_2268",
                "074_Range_Iterator_max_2269",
                "080_Difference_Iterator_min_2301",
                "084_SymmetricDifference_Iterator_min_2329",
                "088_Intersection_Iterator_min_2357",
                "092_Union_Iterator_min_2385",
            }.issubset(affected)
        )
        target_by_key = {
            (row.owner["name"], row.trait, row.function["name"]):
                row.target_id
            for row in self.rows
        }
        for target_id, row in affected.items():
            with self.subTest(target_id=target_id):
                implementation = proof_model.source(row)
                self.assertEqual(
                    check_campaign.selected_public_composition_policy_errors(
                        row,
                        implementation,
                    ),
                    [],
                )
                self.assertTrue(
                    proof_model.selected_public_dependency_target_ids(
                        row,
                        target_by_key,
                    )
                )
                projection = proof_model.projection_for(
                    row,
                    campaign_model.proxy_parts(row)[2],
                )
                lower_clauses = (
                    proof_model.emitted_dependency_contract_lines(
                        row,
                        projection,
                    )
                )
                self.assertEqual(
                    check_campaign.dependency_policy_errors(
                        implementation,
                        proof_model.dependency_function_name(row),
                        proof_model.contract_lines(row),
                        lower_clauses,
                        reject_projected_equivalence=True,
                    ),
                    [],
                )
                body = check_campaign.executable_function_body(
                    implementation,
                    "implementation",
                )
                first_token = next(
                    token
                    for token in proof_model.implementation_order_tokens(
                        row
                    )
                    if body.count(token) == 1
                )
                mutated_body = body.replace(
                    first_token,
                    "selected_composition_removed",
                    1,
                )
                mutated = implementation.replace(body, mutated_body, 1)
                self.assertTrue(
                    check_campaign.selected_public_composition_policy_errors(
                        row,
                        mutated,
                    )
                )

    def test_checker_rejects_projected_public_restatement(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "023_BTreeSet_inherent_is_disjoint_2082"
        )
        accepted = proof_model.contract_lines(row)[0]
        restatement = (
            accepted.replace("result", "(result.value)")
            .replace(
                "this@",
                "wrapped_btree_map_keys(this)",
            )
            .replace(
                "other@",
                "wrapped_btree_map_keys(other)",
            )
        )
        self.assertTrue(
            check_campaign.projected_clause_equivalent(
                restatement,
                accepted,
            )
        )
        dependency = "projected_public_restatement"
        implementation = f"""#[verifier::external_body]
pub fn {dependency}() -> (result: MapBoolResult)
    ensures
        {restatement},
{{
    loop {{ }}
}}

pub fn implementation() {{}}
"""
        errors = check_campaign.dependency_policy_errors(
            implementation,
            dependency,
            [accepted],
            [restatement],
            reject_projected_equivalence=True,
        )
        self.assertIn(
            "dependency restates a public accepted clause after projection",
            errors,
        )

    def test_union_next_retains_parsed_left_biased_selection(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "090_Union_Iterator_next_2383"
        )
        implementation = proof_model.source(row)
        mutation = proof_model.source(row, mutation=True)
        implementation_body = check_campaign.executable_function_body(
            implementation,
            "implementation",
        )
        mutation_body = check_campaign.executable_function_body(
            mutation,
            "implementation",
        )
        self.assertEqual(
            proof_model.source_call_callees(row),
            ["nexts", "a_next.or"],
        )
        requirements = proof_model.executable_source_call_requirements(row)
        self.assertEqual(
            [record["callee"] for record in requirements],
            ["nexts", "a_next.or"],
        )
        self.assertEqual(
            proof_model.source_call_coverage(row)[
                "missing_executable_body_calls"
            ],
            [],
        )
        self.assertEqual(
            check_campaign.parsed_source_call_policy_errors(
                row,
                implementation,
            ),
            [],
        )
        self.assertEqual(
            check_campaign.union_candidate_selection_policy_errors(
                row,
                implementation,
                mutation,
            ),
            [],
        )
        lower_call = f"{proof_model.dependency_call_name(row)}(this)"
        self.assertEqual(implementation_body.count(lower_call), 1)
        self.assertIn(
            "let answer = a_next.or(b_next);",
            implementation_body,
        )
        self.assertIn("let answer = a_next;", mutation_body)
        self.assertNotIn("source_branch", implementation_body)
        self.assertNotIn("read_source_discriminant", implementation_body)

        without_nexts = implementation.replace(
            lower_call,
            lower_call.replace("nexts", "omitted"),
            1,
        )
        self.assertTrue(
            check_campaign.parsed_source_call_policy_errors(
                row,
                without_nexts,
            )
        )
        without_or = implementation.replace(
            "let answer = a_next.or(b_next);",
            "let answer = a_next;",
            1,
        )
        self.assertTrue(
            check_campaign.parsed_source_call_policy_errors(
                row,
                without_or,
            )
        )

        projection = proof_model.projection_for(
            row,
            campaign_model.proxy_parts(row)[2],
        )
        lower_clauses = proof_model.emitted_dependency_contract_lines(
            row,
            projection,
        )
        accepted_clauses = proof_model.contract_lines(row)
        self.assertTrue(
            check_campaign.reject_projected_dependency_equivalence(row)
        )
        self.assertFalse(
            any(
                check_campaign.projected_clause_equivalent(lower, accepted)
                for lower in lower_clauses
                for accepted in accepted_clauses
            )
        )
        projected_restatement = (
            accepted_clauses[0]
            .replace("result", "project_map_entry(result)")
            .replace(
                "union_remaining",
                "union_inner_cursor_remaining",
            )
        )
        self.assertTrue(
            check_campaign.projected_clause_equivalent(
                projected_restatement,
                accepted_clauses[0],
            )
        )
        self.assertTrue(
            check_campaign.projected_clause_equivalent(
                "union_inner_state(*final(this)) == "
                "merge_next_step("
                "union_inner_state(*old(this))).state",
                accepted_clauses[2],
            )
        )
        self.assertTrue(
            check_campaign.projected_clause_equivalent(
                "union_inner_state_law(*final(this))",
                accepted_clauses[3],
            )
        )
        self.assertEqual(
            check_campaign.dependency_policy_errors(
                implementation,
                proof_model.dependency_function_name(row),
                accepted_clauses,
                lower_clauses,
                reject_projected_equivalence=True,
            ),
            [],
        )
        self.assertEqual(implementation.count("pub assume_specification"), 1)
        self.assertEqual(
            len(proof_model.standard_library_assumption_boundaries(row)),
            1,
        )

    def test_symmetric_difference_retains_option_source_calls(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id
            == "082_SymmetricDifference_Iterator_next_2327"
        )
        implementation = proof_model.source(row)
        body = check_campaign.executable_function_body(
            implementation,
            "implementation",
        )
        self.assertEqual(
            proof_model.source_call_callees(row),
            ["nexts", "a_next.and", "is_none", "a_next.or"],
        )
        self.assertEqual(
            [
                record["callee"]
                for record in proof_model.executable_source_call_requirements(
                    row
                )
            ],
            ["nexts", "a_next.and", "is_none", "a_next.or"],
        )
        self.assertEqual(
            check_campaign.parsed_source_call_policy_errors(
                row,
                implementation,
            ),
            [],
        )
        for token in (
            "a_next.and(b_next).is_none()",
            "a_next.or(b_next)",
        ):
            self.assertEqual(body.count(token), 1)
        self.assertEqual(implementation.count("pub assume_specification"), 2)

    def test_completeness_bodies_are_literal_mechanical_translations(self) -> None:
        self.assertNotIn(
            "from tools import proof_model",
            inspect.getsource(completeness_audit),
        )
        for row in self.rows:
            completeness = proof_model.source(row, completeness=True)
            clause_bodies = [
                completeness_audit.reconstruct_clause(row, clause)
                for clause in proof_model.contract_lines(row)
            ]
            requirement_bodies = [
                completeness_audit.reconstruct(row, requirement)
                for requirement in proof_model.contract_requirements(row)
            ]
            for index, body in enumerate(clause_bodies, start=1):
                emitted = check_campaign.spec_function_body(
                    completeness, f"accepted_clause_{index}"
                ).strip()
                self.assertEqual(emitted, body.strip())
            for index, body in enumerate(requirement_bodies, start=1):
                emitted = check_campaign.spec_function_body(
                    completeness, f"accepted_requirement_{index}"
                ).strip()
                self.assertEqual(emitted, body.strip())
            tampered = completeness.replace(
                clause_bodies[0].strip(),
                clause_bodies[0].strip() + " || true",
                1,
            )
            self.assertNotEqual(tampered, completeness)
            self.assertNotEqual(
                check_campaign.spec_function_body(
                    tampered, "accepted_clause_1"
                ).strip(),
                clause_bodies[0].strip(),
            )

    def test_checker_rejects_field_isomorphic_lower_alias(self) -> None:
        row = next(
            row for row in self.rows if row.function["name"] == "contains"
        )
        implementation = proof_model.source(row)
        sanctioned = check_campaign.parse_struct_fields(
            proof_model.COMMON_PROJECTION_TYPES
        )
        sanctioned_signatures = {
            check_campaign.struct_signature(sanctioned, name)
            for name in sanctioned
        }

        def alias_names(text: str) -> list[str]:
            harness = check_campaign.parse_struct_fields(text)
            return [
                name
                for name in harness
                if name not in sanctioned
                and check_campaign.struct_signature(harness, name)
                in sanctioned_signatures
            ]

        self.assertEqual(alias_names(implementation), [])
        aliased = implementation.replace(
            "pub struct MapBoolResult {",
            "pub struct FakeBoolResult {\n    pub value: bool,\n}\n\n"
            "pub struct MapBoolResult {",
            1,
        )
        self.assertIn("FakeBoolResult", alias_names(aliased))

    def test_checker_rejects_constant_source_discriminant(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "078_Difference_Iterator_next_2299"
        )
        implementation = proof_model.source(row)
        selector_name = (
            f"{proof_model.dependency_function_name(row)}"
            "_read_source_discriminant"
        )
        selector_call = (
            f"{proof_model.generic_call_name(row, selector_name)}(&*this)"
        )
        constant_pattern = r"let source_branch\s*=\s*0u8"
        self.assertIn(selector_call, implementation)
        selector_start = check_campaign.external_function_start(
            implementation,
            selector_name,
        )
        selector_end = implementation.find(
            "#[verifier::external_body]",
            selector_start + 1,
        )
        self.assertNotIn(
            "Ghost(",
            implementation[selector_start:selector_end],
        )
        self.assertIsNone(re.search(constant_pattern, implementation))
        constant = implementation.replace(
            f"let source_branch = {selector_call}",
            "let source_branch = 0u8",
            1,
        )
        self.assertNotEqual(constant, implementation)
        self.assertIsNotNone(re.search(constant_pattern, constant))
        self.assertNotIn(selector_call, constant)

    def test_adapter_comparison_fragment_uses_owner_bindings(self) -> None:
        rows = {row.target_id: row for row in self.rows}
        cases = {
            "078_Difference_Iterator_next_2299": (
                "self_next, other_next",
                "a_next, b_next",
            ),
            "086_Intersection_Iterator_next_2355": (
                "a_next, b_next",
                "self_next, other_next",
            ),
        }
        for target_id, (arguments, wrong_arguments) in cases.items():
            with self.subTest(target_id=target_id):
                row = rows[target_id]
                callee = proof_model.generic_call_name(
                    row,
                    f"{proof_model.dependency_function_name(row)}"
                    "_stitch_compare",
                )
                expected = f"{callee}({arguments})"
                self.assertEqual(
                    proof_model.adapter_source_comparison_call_fragment(
                        row
                    ),
                    expected,
                )
                self.assertIn(expected, proof_model.source(row))
                self.assertNotIn(
                    f"{callee}({wrong_arguments})",
                    proof_model.source(row),
                )

    def test_source_owned_adapter_mutations_change_live_control_flow(
        self,
    ) -> None:
        rows = {row.target_id: row for row in self.rows}
        cases = {
            "078_Difference_Iterator_next_2299": (
                "rust_1_96_difference_iterator_next_private_state"
                "_stitch_compare::<T, A>(self_next, other_next)",
                "rust_1_96_difference_iterator_next_private_state"
                "_stitch_compare::<T, A>(other_next, self_next)",
                "wrong_source_comparison",
            ),
            "082_SymmetricDifference_Iterator_next_2327": (
                "if a_next.and(b_next).is_none() {",
                "if !a_next.and(b_next).is_none() {",
                "wrong_duplicate_handling",
            ),
            "086_Intersection_Iterator_next_2355": (
                "rust_1_96_intersection_iterator_next_private_state"
                "_stitch_compare::<T, A>(a_next, b_next)",
                "rust_1_96_intersection_iterator_next_private_state"
                "_stitch_compare::<T, A>(b_next, a_next)",
                "wrong_source_comparison",
            ),
        }
        for target_id, (original, changed, kind) in cases.items():
            with self.subTest(target_id=target_id):
                row = rows[target_id]
                implementation = proof_model.source(row)
                mutation = proof_model.source(row, mutation=True)
                descriptor = proof_model.mutation_descriptor(row)
                implementation_body = check_campaign.executable_function_body(
                    implementation,
                    "implementation",
                )
                mutation_body = check_campaign.executable_function_body(
                    mutation,
                    "implementation",
                )
                self.assertEqual(descriptor["original_fragment"], original)
                self.assertEqual(descriptor["mutated_fragment"], changed)
                self.assertEqual(descriptor["kind"], kind)
                self.assertIn(original, implementation_body)
                self.assertIn(changed, mutation_body)
                self.assertEqual(
                    mutation_body.replace(changed, original, 1),
                    implementation_body,
                )
                self.assertNotIn("source_order", implementation)
                self.assertNotIn("source_order", mutation)
                self.assertEqual(
                    check_campaign.adapter_source_mutation_policy_errors(
                        row,
                        implementation,
                        mutation,
                    ),
                    [],
                )

    def test_checker_rejects_proof_only_adapter_guard_mutation(self) -> None:
        row = next(
            row
            for row in self.rows
            if row.target_id == "086_Intersection_Iterator_next_2355"
        )
        implementation = proof_model.source(row)
        call = proof_model.adapter_source_comparison_call_fragment(row)
        guarded_call = call[:-1] + ", true)"
        guarded_implementation = implementation.replace(
            call,
            guarded_call,
            1,
        )
        guarded_mutation = guarded_implementation.replace(
            guarded_call,
            call[:-1] + ", false)",
            1,
        )
        errors = check_campaign.adapter_source_mutation_policy_errors(
            row,
            guarded_implementation,
            guarded_mutation,
        )
        self.assertTrue(
            any("proof-only boolean guard" in error for error in errors),
            errors,
        )

    def test_checker_rejects_direct_adapter_loop_bypass(self) -> None:
        targets = {
            "078_Difference_Iterator_next_2299",
            "082_SymmetricDifference_Iterator_next_2327",
            "086_Intersection_Iterator_next_2355",
        }
        rows = {row.target_id: row for row in self.rows}
        for target_id in targets:
            with self.subTest(target_id=target_id):
                row = rows[target_id]
                implementation = proof_model.source(row)
                self.assertEqual(
                    check_campaign.adapter_source_loop_policy_errors(
                        row,
                        implementation,
                    ),
                    [],
                )
                body = check_campaign.executable_function_body(
                    implementation,
                    "implementation",
                )
                bypassed_body = """
    let source_steps: usize = 0;
    let completed_source_steps = source_steps;
"""
                bypassed = implementation.replace(
                    body,
                    bypassed_body,
                    1,
                )
                errors = (
                    check_campaign.adapter_source_loop_policy_errors(
                        row,
                        bypassed,
                    )
                )
                self.assertTrue(
                    any("synthetic control token" in error for error in errors),
                    errors,
                )
                self.assertTrue(
                    any("source operation" in error for error in errors),
                    errors,
                )

    def test_source_lowerings_cover_verus_edge_cases(self) -> None:
        by_id = {row.target_id: row for row in self.rows}
        for target_id in (
            "016_BTreeSet_inherent_difference_2071",
            "018_BTreeSet_inherent_intersection_2075",
            "024_BTreeSet_inherent_is_subset_2083",
        ):
            row = by_id[target_id]
            inputs = proof_model.signature_parts(
                row,
                "implementation",
            )[0]
            discriminant = proof_model.branch_source_value(row, inputs)
            self.assertIn("wrapped_btree_map_key_sequence", discriminant)
            self.assertNotIn("btree_set_sequence", discriminant)
            if target_id.startswith("024_"):
                self.assertIn("else { 3u8 }", discriminant)

        extract_if = by_id["037_BTreeSet_inherent_extract_if_2098"]
        extract_source = proof_model.source(extract_if)
        self.assertIn(
            "reveal_btree_set_map_mut_projection(this)",
            extract_source,
        )
        self.assertIn(
            "wrapped_btree_map_keys(final(set)) == (*final(set))@",
            extract_source,
        )

        iter_row = by_id["038_BTreeSet_inherent_iter_2064"]
        iter_projection = proof_model.projection_for(
            iter_row,
            campaign_model.proxy_parts(iter_row)[2],
        )
        self.assertIn(
            "result.remaining@.unref() == "
            "wrapped_btree_map_key_sequence(this)",
            proof_model.dependency_contract_lines(
                iter_row,
                iter_projection,
            ),
        )

        default_iter = by_id["066_Iter_Default_default_2211"]
        self.assertFalse(
            proof_model.private_cursor_bridge_required(default_iter)
        )
        default_into_iter = by_id["069_IntoIter_Default_default_2241"]
        default_source = proof_model.source(default_into_iter)
        self.assertIn(
            "let lower: MapOwnedIteratorState<T> = "
            "rust_1_96_intoiter_default_default_private_state::<T, A>()",
            default_source,
        )

        debug_row = by_id["055_BTreeSet_Debug_fmt_2174"]
        debug_mutation = proof_model.source(debug_row, mutation=True)
        self.assertIn("Ok(())", debug_mutation)
        self.assertNotIn("Err(core::fmt::Error)", debug_mutation)

        equality = by_id["002_BTreeSet_PartialEq_eq_2128"]
        equality_body = proof_model.clause_bodies(
            equality,
            proof_model.outcome_profile(equality),
        )[0]
        self.assertEqual(
            equality_body,
            "returned == sequence_equal_model(pre_seq, other_seq)",
        )

        new_row = by_id["014_BTreeSet_inherent_new_2066"]
        new_projection = proof_model.projection_for(
            new_row,
            campaign_model.proxy_parts(new_row)[2],
        )
        self.assertEqual(
            proof_model.dependency_contract_lines(
                new_row,
                new_projection,
            )[0],
            "result.valid",
        )
        self.assertIn(
            "valid: false",
            proof_model.source(new_row, mutation=True),
        )

    def test_associated_item_adjudication_erases_only_crashing_bounds(
        self,
    ) -> None:
        affected = {
            row.target_id: row
            for row in self.rows
            if proof_model.requires_associated_item_air_adjudication(row)
        }
        self.assertEqual(
            set(affected),
            set(proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS),
        )
        for target_id, row in affected.items():
            with self.subTest(target_id=target_id):
                exact = proof_model.source(row)
                adjudicated = proof_model.checker_adjudication_source(row)
                mutation = proof_model.checker_adjudication_source(
                    row,
                    mutation=True,
                )
                declarations = (
                    proof_model.associated_item_bound_declarations(row)
                )
                self.assertEqual(len(declarations), 1)
                self.assertIn(declarations[0], exact)
                self.assertNotIn(declarations[0], adjudicated)
                self.assertNotIn(declarations[0], mutation)
                self.assertIn(
                    "Removing only the IntoIterator::Item equality",
                    adjudicated,
                )
                exact_body = check_campaign.executable_function_body(
                    exact,
                    "implementation",
                )
                adjudicated_body = (
                    check_campaign.executable_function_body(
                        adjudicated,
                        "implementation",
                    )
                )
                self.assertEqual(
                    exact_body,
                    adjudicated_body,
                )

    def test_associated_item_air_matcher_accepts_current_verus_panic(
        self,
    ) -> None:
        diagnostic = """
internal error: generated ill-typed AIR code: error 'use of undeclared function proj%%core!iter.traits.collect.IntoIterator./Item'
"""
        headers = (
            (
                "thread 'rustc' (547318) panicked at "
                "rust_verify/src/verifier.rs:858:21:"
            ),
            (
                "thread '<unnamed>' (564703) panicked at "
                "rust_verify/src/verifier.rs:858:21:"
            ),
        )
        for header in headers:
            with self.subTest(header=header):
                for matcher in (
                    verus_evidence.associated_item_air_limitation_matches,
                    run_verus_matrix.associated_item_air_limitation_matches,
                ):
                    self.assertTrue(
                        matcher(
                            1,
                            f"{header}\n{diagnostic}",
                        )
                    )
        output = f"{headers[0]}\n{diagnostic}"
        self.assertFalse(
            run_verus_matrix.associated_item_air_limitation_matches(
                0,
                output,
            )
        )
        self.assertFalse(
            run_verus_matrix.associated_item_air_limitation_matches(
                1,
                output.replace("thread 'rustc'", "thread 'other'", 1),
            )
        )
        for token in (
            "internal error: generated ill-typed AIR code",
            (
                "use of undeclared function "
                "proj%%core!iter.traits.collect.IntoIterator./Item"
            ),
        ):
            with self.subTest(missing=token):
                self.assertFalse(
                    run_verus_matrix.associated_item_air_limitation_matches(
                        1,
                        output.replace(token, "different failure", 1),
                    )
                )
        verifier_source = inspect.getsource(check_campaign.verify_verus)
        self.assertRegex(
            verifier_source,
            (
                r"verus_evidence\s*\.\s*"
                r"associated_item_air_limitation_matches"
            ),
        )
        self.assertNotIn("worker thread panicked", verifier_source)

    def test_checker_can_enforce_source_operation_order(self) -> None:
        for candidate in self.rows:
            with self.subTest(target_id=candidate.target_id):
                candidate_body = check_campaign.executable_function_body(
                    proof_model.source(candidate),
                    "implementation",
                )
                cursor = 0
                positions: list[int] = []
                for token in proof_model.implementation_order_tokens(
                    candidate
                ):
                    position = candidate_body.find(token, cursor)
                    self.assertGreaterEqual(position, 0, token)
                    positions.append(position)
                    cursor = position + len(token)
                self.assertEqual(positions, sorted(positions))

        row = next(
            row
            for row in self.rows
            if row.target_id == "078_Difference_Iterator_next_2299"
        )
        implementation = proof_model.source(row)
        body = check_campaign.executable_function_body(
            implementation,
            "implementation",
        )
        tokens = proof_model.implementation_order_tokens(row)
        cursor = 0
        for token in tokens:
            position = body.find(token, cursor)
            self.assertGreaterEqual(position, 0, token)
            cursor = position + len(token)

        first = tokens[0]
        lower_call = next(
            token
            for token in tokens
            if proof_model.dependency_call_name(row) in token
        )
        reordered = body.replace(first, "__FIRST__", 1)
        reordered = reordered.replace(lower_call, first, 1)
        reordered = reordered.replace("__FIRST__", lower_call, 1)
        cursor = 0
        for token in tokens:
            position = reordered.find(token, cursor)
            if position < 0:
                break
            cursor = position + len(token)
        self.assertLess(position, 0)

    def test_checker_rejects_inert_projector_mutations(self) -> None:
        by_family: dict[str, object] = {}
        for row in self.rows:
            by_family.setdefault(row.semantic_family, row)
        adapter_mutation = check_campaign.executable_function_body(
            proof_model.source(
                by_family["union_adapter_construction"], mutation=True
            ),
            "implementation",
        )
        self.assertIn(
            "let other_iter = rust_1_96_selected_iter(this);",
            adapter_mutation,
        )
        extract_mutation = check_campaign.executable_function_body(
            proof_model.source(
                by_family["extract_if_construction"], mutation=True
            ),
            "implementation",
        )
        self.assertIn("pending: Ghost(Seq::empty())", extract_mutation)
        self.assertIn("remaining: Ghost(Seq::empty())", extract_mutation)
        set_mutation = check_campaign.executable_function_body(
            proof_model.source(
                by_family["sorted_deduplicating_conversion"],
                mutation=True,
            ),
            "implementation",
        )
        self.assertNotIn(
            "keys: Ghost(Seq::empty())",
            set_mutation,
        )
        self.assertIn(
            "let source_branch = 0u8;",
            set_mutation,
        )

    def test_set_algebra_constructor_mutations_replace_observed_state(self) -> None:
        target_ids = {
            "017_BTreeSet_inherent_symmetric_difference_2073",
            "019_BTreeSet_inherent_union_2077",
        }
        rows = {row.target_id: row for row in self.rows}
        self.assertTrue(target_ids.issubset(rows))
        for target_id in sorted(target_ids):
            with self.subTest(target_id=target_id):
                row = rows[target_id]
                implementation_body = check_campaign.executable_function_body(
                    proof_model.source(row),
                    "implementation",
                )
                mutation_body = check_campaign.executable_function_body(
                    proof_model.source(row, mutation=True),
                    "implementation",
                )
                self.assertIn(
                    "let other_iter = rust_1_96_selected_iter(other);",
                    implementation_body,
                )
                self.assertIn(
                    "let other_iter = rust_1_96_selected_iter(this);",
                    mutation_body,
                )
                restored = mutation_body.replace(
                    "let other_iter = rust_1_96_selected_iter(this);",
                    "let other_iter = rust_1_96_selected_iter(other);",
                )
                self.assertEqual(restored, implementation_body)

    def test_selected_state_mutations_target_receivers_and_consumption(
        self,
    ) -> None:
        rows = {row.target_id: row for row in self.rows}
        receiver_targets = {
            "016_BTreeSet_inherent_difference_2071",
            "017_BTreeSet_inherent_symmetric_difference_2073",
            "018_BTreeSet_inherent_intersection_2075",
            "019_BTreeSet_inherent_union_2077",
            "025_BTreeSet_inherent_is_superset_2084",
        }
        for target_id in receiver_targets:
            with self.subTest(target_id=target_id):
                row = rows[target_id]
                descriptor = proof_model.mutation_descriptor(row)
                self.assertEqual(
                    descriptor["kind"],
                    "wrong_selected_receiver",
                )
                self.assertIn(
                    descriptor["original_fragment"],
                    proof_model.source(row),
                )
                self.assertIn(
                    descriptor["mutated_fragment"],
                    proof_model.source(row, mutation=True),
                )

        subset = rows["024_BTreeSet_inherent_is_subset_2083"]
        descriptor = proof_model.mutation_descriptor(subset)
        self.assertEqual(descriptor["kind"], "wrong_source_control")
        self.assertIn(descriptor["original_fragment"], proof_model.source(subset))
        self.assertIn(
            descriptor["mutated_fragment"],
            proof_model.source(subset, mutation=True),
        )

        retain = rows["034_BTreeSet_inherent_retain_2095"]
        descriptor = proof_model.mutation_descriptor(retain)
        self.assertEqual(
            descriptor["kind"],
            "omitted_extract_if_consumption",
        )
        implementation = proof_model.source(retain)
        mutation = proof_model.source(retain, mutation=True)
        self.assertIn("iter: ExtractIf<", implementation)
        self.assertIn(descriptor["original_fragment"], implementation)
        self.assertIn(descriptor["mutated_fragment"], mutation)

    def test_static_aggregate_gate_passes(self) -> None:
        self.assertEqual(check_campaign.verify_static(), [])

    def test_aggregate_schema_is_inventory_derived_and_fail_closed(self) -> None:
        schema = json.loads(
            (ROOT / "aggregate/schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["inventory"]["totals_source"], "inventory_rows")
        self.assertTrue(schema["inventory"]["zero_pending_required"])
        self.assertTrue(schema["exact_vstd"]["reverse_scan_required"])
        self.assertTrue(
            schema["exact_vstd"][
                "comparison_derived_from_parsed_declarations"
            ]
        )
        self.assertTrue(schema["harness"]["forbid_snapshot_outcome_surrogates"])
        self.assertTrue(schema["harness"]["forbid_generic_source_surrogates"])
        self.assertTrue(schema["harness"]["forbid_whole_contract_dependency"])
        self.assertTrue(
            schema["harness"]["reject_field_isomorphic_lower_results"]
        )
        self.assertTrue(
            schema["harness"]["require_literal_clause_translation"]
        )
        self.assertTrue(
            schema["harness"][
                "require_narrow_associated_item_checker_adjudication"
            ]
        )
        self.assertTrue(schema["harness"]["require_exact_generated_proof_sources"])
        self.assertTrue(
            schema["harness"]["require_narrow_dependency_clause_lowering"]
        )
        self.assertTrue(schema["harness"]["require_clause_derived_completeness"])
        self.assertTrue(
            schema["harness"]["require_projector_observed_mutation"]
        )
        self.assertTrue(
            schema["harness"]["require_source_derived_discriminants"]
        )
        self.assertTrue(
            schema["harness"]["require_operation_specific_lower_contracts"]
        )
        self.assertTrue(
            schema["harness"]["require_source_operation_order"]
        )
        self.assertTrue(
            schema["trust_accounting"][
                "category_specific_literal_counts_required"
            ]
        )
        self.assertTrue(
            schema["trust_accounting"][
                "checker_adjudication_surface_required"
            ]
        )
        self.assertEqual(
            schema["review_gates"],
            [
                "inventory_specification",
                "proof_completeness",
                "final_aggregate",
            ],
        )

    def test_independent_review_reason_coverage_is_fail_closed(self) -> None:
        values = run_independent_review.counts()
        incomplete_reason = (
            "Independent review accepts all 92 source-shaped harnesses. "
            "The immutable matrix contains 462 successful trials: 89 native "
            "and 3 narrowly adjudicated implementation proofs, 92 completeness "
            "proofs, and 92 semantic mutation rejections. No public target uses "
            "external_body, and BTreeMap/core comparison behavior remains "
            "explicitly unaccepted."
        )
        coverage = run_independent_review.required_coverage(
            "proof_completeness",
            incomplete_reason,
            values,
        )
        self.assertEqual(
            {label for label, covered in coverage.items() if not covered},
            {
                "exact-vstd count",
                "generated count",
                "actual Verus",
                "BTreeMap delegation",
                "zero failed",
                "zero pending",
            },
        )
        self.assertFalse(
            run_independent_review.acceptance_eligible(
                "proof_completeness",
                "done",
                incomplete_reason,
                values,
            )
        )

    def test_independent_review_contract_requires_complete_reason(self) -> None:
        values = run_independent_review.counts()
        statement = run_independent_review.required_reason_statement(
            "proof_completeness",
            values,
        )
        self.assertTrue(
            all(
                run_independent_review.required_coverage(
                    "proof_completeness",
                    statement,
                    values,
                ).values()
            )
        )
        self.assertTrue(
            run_independent_review.acceptance_eligible(
                "proof_completeness",
                "done",
                statement,
                values,
            )
        )
        self.assertIn(
            statement,
            run_independent_review.objective("proof_completeness", values),
        )


if __name__ == "__main__":
    unittest.main()
