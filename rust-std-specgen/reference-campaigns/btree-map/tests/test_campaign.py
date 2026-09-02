from pathlib import Path
from typing import Any
import json
import re
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_campaign
import run_feedback_gate
import run_verus_matrix
import verify_campaign


class BTreeMapCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = json.loads(
            (ROOT / "inventory/btree_map_exec_fn_inventory.json").read_text()
        )
        rustdoc = json.loads(generate_campaign.RUSTDOC.read_text())
        live_rows, _ = generate_campaign.derive_inventory(rustdoc["index"])
        for row in live_rows:
            row.semantic_family = generate_campaign.semantic_family(row)
        cls.live_by_id = {row.item_id: row for row in live_rows}

    def test_inventory_counts_are_live_and_reconciled(self) -> None:
        self.assertEqual(
            self.inventory["counts"],
            {
                "stable_inventory_total": 151,
                "exact_vstd": 13,
                "generated": 137,
                "genuinely_impossible": 1,
                "pending": 0,
            },
        )
        rustdoc = json.loads(generate_campaign.RUSTDOC.read_text())
        rows, exclusions = generate_campaign.derive_inventory(rustdoc["index"])
        self.assertEqual(len(rows), 151)
        self.assertEqual(len(exclusions), 16)

    def test_main_stability_keeps_len_and_is_empty(self) -> None:
        selected = {
            (row["owner_type"], row["trait"], row["method"])
            for row in self.inventory["rows"]
        }
        self.assertIn(("BTreeMap", "inherent", "len"), selected)
        self.assertIn(("BTreeMap", "inherent", "is_empty"), selected)

    def test_exact_vstd_rows_match_full_audit(self) -> None:
        exact = [
            row for row in self.inventory["rows"] if row["disposition"] == "exact_vstd"
        ]
        self.assertEqual(len(exact), 13)
        self.assertTrue(all(row["vstd_reference"] for row in exact))
        self.assertTrue(
            all(
                len(row["vstd_reference"]["match_dimensions"]) == 8
                for row in exact
            )
        )

    def test_scope_excludes_btree_set_and_alias_duplicates(self) -> None:
        rendered = json.dumps(self.inventory["rows"])
        self.assertNotIn("BTreeSet", rendered)
        exclusions = json.loads(
            (ROOT / "inventory/unstable_non_executable_exclusions.json").read_text()
        )
        self.assertIn(
            "alloc::collections::BTreeMap",
            exclusions["aliases_excluded_as_duplicates"],
        )

    def test_generated_contracts_have_comparator_guards(self) -> None:
        guarded = 0
        unguarded = 0
        for row in self.inventory["rows"]:
            if row["disposition"] != "generated":
                continue
            self.assertTrue(row["contract"]["ensures"], row["target_id"])
            self.assertTrue(
                all(
                    not clause.startswith("key_obeys_cmp_spec")
                    for clause in row["contract"]["requires"]
                ),
                row["target_id"],
            )
            live = self.live_by_id[row["rustdoc_item_id"]]
            guard = generate_campaign.comparison_guard(live)
            if guard is None:
                unguarded += 1
                self.assertTrue(
                    all(
                        not clause.startswith("key_obeys_cmp_spec")
                        for clause in row["contract"]["ensures"]
                    ),
                    row["target_id"],
                )
            else:
                guarded += 1
                self.assertTrue(
                    all(clause.startswith(f"{guard} ==>") for clause in row["contract"]["ensures"]),
                    row["target_id"],
                )
        self.assertGreater(guarded, 0)
        self.assertGreater(unguarded, 0)

    def test_principal_models_are_source_defined(self) -> None:
        vocabulary = (
            ROOT / "specs/btree_map_shared_vocabulary.rs"
        ).read_text()
        generated = (ROOT / "specs/generated_btree_map_specs.rs").read_text()
        for declaration in (
            "pub open spec fn ordered_range_domain",
            "pub open spec fn ordered_key_in_range",
            "pub open spec fn ordered_split_partition",
            "pub open spec fn ordered_callback_filter",
            "pub open spec fn extract_if_lifecycle",
            "pub open spec fn extract_if_state_coherent",
            "pub open spec fn extract_if_callback_model_functional",
            "pub uninterp spec fn extract_if_yielded_pairs",
            "pub uninterp spec fn extract_if_current_map",
            "pub trait ExtractIfIteratorModel",
            "pub open spec fn ordered_callback_unwind_contract",
            "pub open spec fn owning_iterator_transfer",
            "pub uninterp spec fn ordered_handle_final_map",
            "pub open spec fn ordered_map_cmp",
            "pub open spec fn ordered_map_partial_cmp",
        ):
            self.assertIn(declaration, vocabulary)
        for forbidden in (
            "mutable_lookup_frame",
            "pub uninterp spec fn ordered_key_in_range",
            "pub uninterp spec fn ordered_split_partition",
            "pub uninterp spec fn ordered_callback_filter<",
            "pub uninterp spec fn extract_if_initial",
            "entry_return_map",
            "entry_consumed_post_map",
            "entry_branch_result",
        ):
            self.assertNotIn(forbidden, vocabulary)
        self.assertIn(".ordered_remaining().drop_first()", generated)
        self.assertIn(".ordered_remaining().drop_last()", generated)

    def test_removal_functionality_and_extract_if_initial_state(self) -> None:
        vocabulary = (
            ROOT / "specs/btree_map_shared_vocabulary.rs"
        ).read_text()
        self.assertIn(
            "pub open spec fn borrowed_removal_functional",
            vocabulary,
        )
        self.assertIn(
            "#[trigger] borrowed_key_removed(map, left, query)",
            vocabulary,
        )

        for item_id in (1402, 1403):
            row = next(
                row
                for row in self.inventory["rows"]
                if row["rustdoc_item_id"] == item_id
            )
            completeness = (
                ROOT
                / "proof_harnesses"
                / row["target_id"]
                / "completeness_proof.rs"
            ).read_text()
            self.assertIn(
                "borrowed_removal_functional::<K, Q, V>(pre_this@, key)",
                completeness,
            )

        extract_if = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1413
        )
        ensures = extract_if["contract"]["ensures"]
        self.assertTrue(
            any(
                "final(this)@ == old(this)@" in clause
                for clause in ensures
            )
        )
        self.assertTrue(
            any(
                "extract_if_unvisited_keys::<K, V, _>(&result)"
                in clause
                and "ordered_range_key_sequence::<K, V, K, R>" in clause
                for clause in ensures
            )
        )
        self.assertTrue(
            any(
                "Seq::<K>::empty()" in clause
                and "extract_if_lifecycle" in clause
                for clause in ensures
            )
        )
        self.assertTrue(
            any(
                "extract_if_visited_keys::<K, V, _>(&result)"
                in clause
                and "Seq::<K>::empty()" in clause
                for clause in ensures
            )
        )
        self.assertTrue(
            any(
                "extract_if_yielded_pairs::<K, V, _>(&result)"
                in clause
                and "Seq::<(K, V)>::empty()" in clause
                for clause in ensures
            )
        )
        self.assertTrue(
            any(
                "extract_if_current_map::<K, V, _>(&result)"
                in clause
                and "old(this)@" in clause
                for clause in ensures
            )
        )
        self.assertFalse(
            any(
                "result.ordered_remaining() == Seq::<(K, V)>::empty()"
                in clause
                for clause in ensures
            )
        )

        extract_if_next = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1854
        )
        next_contract = " ".join(extract_if_next["contract"]["ensures"])
        for required in (
            "extract_next_consumed_keys",
            "extract_current_map",
            "extract_yielded_pairs",
            "extract_state_coherent",
        ):
            self.assertIn(required, next_contract)
        next_completeness = (
            ROOT
            / "proof_harnesses"
            / extract_if_next["target_id"]
            / "completeness_proof.rs"
        ).read_text()
        self.assertIn(
            "post1_this.extract_model()",
            next_completeness,
        )

        extract_if_size_hint = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1855
        )
        self.assertTrue(
            any(
                "this.extract_current_map().len()" in clause
                for clause in extract_if_size_hint["contract"]["ensures"]
            )
        )

        retain = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1404
        )
        self.assertTrue(
            any(
                "ordered_callback_unwind_contract" in clause
                for clause in retain["contract"]["ensures"]
            )
        )

        occupied_insert = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1330
        )
        occupied_insert_contract = " ".join(
            occupied_insert["contract"]["ensures"]
        )
        self.assertIn(
            "ordered_handle_key::<K, _>(*final(this))"
            " == ordered_handle_key::<K, _>(*old(this))",
            occupied_insert_contract,
        )
        self.assertIn(
            "ordered_handle_is_occupied(*final(this))",
            occupied_insert_contract,
        )

    def test_exact_iter_remaining_observations_are_trait_qualified(self) -> None:
        row = next(
            row
            for row in self.inventory["rows"]
            if row["rustdoc_item_id"] == 1382
        )
        root = ROOT / "proof_harnesses" / row["target_id"]
        for filename in (
            "implementation_proof.rs",
            "completeness_proof.rs",
            "mutation_proof.rs",
        ):
            source = (root / filename).read_text()
            for subject in ("result", "r1", "r2"):
                self.assertNotIn(
                    f"{subject}.remaining()",
                    source,
                    f"{row['target_id']}/{filename}",
                )
            self.assertIn(
                "IteratorSpec::remaining(",
                source,
                f"{row['target_id']}/{filename}",
            )

    def test_owned_pair_item_constraint_has_reviewed_proof_lowering(self) -> None:
        for item_id in (1469, 1471):
            row = next(
                row
                for row in self.inventory["rows"]
                if row["rustdoc_item_id"] == item_id
            )
            exact_bound = "T: core::iter::IntoIterator<Item = (K, V)>"
            lowered_bound = "T: core::iter::IntoIterator"
            signature_boundary = (
                "into_iterator_item_is_owned_pair::<K, V, T>()"
            )
            self.assertIn(exact_bound, row["proxy"]["generic_binder"])

            root = ROOT / "proof_harnesses" / row["target_id"]
            for filename in (
                "implementation_proof.rs",
                "completeness_proof.rs",
                "mutation_proof.rs",
            ):
                source = (root / filename).read_text()
                self.assertNotIn(
                    exact_bound,
                    source,
                    f"{row['target_id']}/{filename}",
                )
                self.assertIn(
                    lowered_bound,
                    source,
                    f"{row['target_id']}/{filename}",
                )
                self.assertIn(
                    signature_boundary,
                    source,
                    f"{row['target_id']}/{filename}",
                )

            transformation = json.loads(
                (root / "transformation_manifest.json").read_text()
            )
            self.assertIn(
                "verifier_safe_associated_type_lowering",
                {
                    adaptation["kind"]
                    for adaptation in transformation["adaptations"]
                },
            )
            trust = json.loads((root / "trust_boundaries.json").read_text())
            self.assertIn(
                "associated_type_signature_lowering",
                trust["categories"],
            )
            dependencies = json.loads(
                (root / "dependency_assumptions.json").read_text()
            )
            self.assertIn(
                "associated_type_signature_lowering",
                {
                    dependency["category"]
                    for dependency in dependencies["dependencies"]
                },
            )

    def test_entry_completeness_dependencies_are_branch_functional(self) -> None:
        vocabulary = (
            ROOT / "specs/btree_map_shared_vocabulary.rs"
        ).read_text()
        for declaration in (
            "pub open spec fn entry_nullary_callback_functional",
            "pub open spec fn entry_key_callback_functional",
            "pub open spec fn entry_default_value_functional",
            "pub open spec fn entry_and_modify_transition_functional",
        ):
            self.assertIn(declaration, vocabulary)

        expected = {
            1271: (
                "==> entry_nullary_callback_functional::<V, F>(default)",
                "assert(entry_nullary_callback_functional::<V, F>(default));",
            ),
            1272: (
                "==> entry_key_callback_functional::<K, V, F>",
                "assert(entry_key_callback_functional::<K, V, F>(",
            ),
            1274: (
                "==> entry_and_modify_transition_functional::<K, V, F>",
                "assert(entry_and_modify_transition_functional::<K, V, F>(",
            ),
            1277: (
                "==> entry_default_value_functional::<V>()",
                "assert(entry_default_value_functional::<V>());",
            ),
        }
        for item_id, (branch_requirement, proof_use) in expected.items():
            row = next(
                row
                for row in self.inventory["rows"]
                if row["rustdoc_item_id"] == item_id
            )
            root = ROOT / "proof_harnesses" / row["target_id"]
            completeness = (root / "completeness_proof.rs").read_text()
            self.assertIn(branch_requirement, completeness, row["target_id"])
            self.assertIn(proof_use, completeness, row["target_id"])

            trust = json.loads((root / "trust_boundaries.json").read_text())
            self.assertIn(
                "completeness_functionality_hypothesis",
                trust["categories"],
                row["target_id"],
            )
            dependencies = json.loads(
                (root / "dependency_assumptions.json").read_text()
            )
            functionality = [
                dependency
                for dependency in dependencies["dependencies"]
                if dependency["category"]
                == "completeness_functionality_hypothesis"
            ]
            self.assertEqual(len(functionality), 1, row["target_id"])
            self.assertIn(
                branch_requirement,
                functionality[0]["boundary"][0],
                row["target_id"],
            )

    def test_feedback_summary_reader_defers_partial_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = Path(temporary) / "summary.json"
            summary.write_text("")
            self.assertIsNone(
                run_feedback_gate.read_summary_if_complete(summary)
            )
            summary.write_text('{"target":')
            self.assertIsNone(
                run_feedback_gate.read_summary_if_complete(summary)
            )
            summary.write_text('{"target": "complete"}')
            self.assertEqual(
                run_feedback_gate.read_summary_if_complete(summary),
                {"target": "complete"},
            )

    def test_phase_order_archive_tracks_post_authorization_tree(self) -> None:
        phase = json.loads(
            (ROOT / "verification/premature_phase_ordering.json").read_text()
        )
        selected = [
            self.live_by_id[row["rustdoc_item_id"]]
            for row in self.inventory["rows"]
            if row["disposition"] in {"exact_vstd", "generated"}
        ]
        file_count, tree_sha256 = (
            generate_campaign.generated_harness_tree_digest(selected)
        )
        self.assertEqual(phase["schema_version"], 2)
        self.assertTrue(phase["proof_phase_authorized"])
        self.assertTrue(phase["proof_tree_generated_after_authorization"])
        self.assertEqual(phase["file_count"], file_count)
        self.assertEqual(phase["tree_sha256"], tree_sha256)
        self.assertIn(
            phase["proof_status"],
            {
                "generated_pending_fresh_dynamic_evidence",
                "accepted_by_fresh_post_authorization_matrix",
            },
        )
        review = json.loads(
            (ROOT / "reviews/inventory_specification.json").read_text()
        )
        self.assertEqual(
            review["proof_phase_authorized"],
            review["review"]["status"] == "done",
        )

    def test_behavioral_mutations_match_manifests_and_are_distinct(self) -> None:
        distribution: dict[int, int] = {}
        total = 0
        artifact_hashes: list[str] = []
        for row in self.inventory["rows"]:
            if row["disposition"] not in {"exact_vstd", "generated"}:
                continue
            live = self.live_by_id[row["rustdoc_item_id"]]
            live.canonical_target = generate_campaign.canonical_target(live)
            root = ROOT / "proof_harnesses" / row["target_id"]
            source = (root / "mutation_proof.rs").read_text()
            manifest = json.loads((root / "mutations.json").read_text())
            mutations = generate_campaign.behavioral_mutations(live)
            fingerprints = [
                mutation.fingerprint_sha256 for mutation in mutations
            ]
            self.assertEqual(
                len(fingerprints),
                len(set(fingerprints)),
                row["target_id"],
            )
            for mutation in mutations:
                implication = generate_campaign._top_level_marker_index(
                    mutation.original_postcondition,
                    "==>",
                )
                if implication >= 0:
                    antecedent = mutation.original_postcondition[
                        :implication
                    ].strip()
                    self.assertEqual(
                        mutation.operator,
                        "implication_consequent_negation",
                    )
                    self.assertTrue(
                        mutation.mutated_postcondition.startswith(
                            f"{antecedent} ==> !("
                        ),
                        row["target_id"],
                    )
                elif "<==>" in mutation.original_postcondition:
                    self.assertEqual(
                        mutation.operator,
                        "logical_negation",
                    )
                    self.assertEqual(
                        mutation.mutated_postcondition,
                        f"!({mutation.original_postcondition})",
                    )
            self.assertEqual(
                verify_campaign.check_mutation_artifacts(
                    row["target_id"], live, source, manifest
                ),
                [],
                row["target_id"],
            )
            target_artifacts = [
                generate_campaign.mutation_manifest_entry(
                    live, mutation
                )["verification_artifact_sha256"]
                for mutation in mutations
            ]
            self.assertEqual(
                len(target_artifacts),
                len(set(target_artifacts)),
                row["target_id"],
            )
            artifact_hashes.extend(target_artifacts)
            count = len(mutations)
            self.assertGreaterEqual(count, 1, row["target_id"])
            self.assertEqual(
                count,
                len(
                    generate_campaign.source_lowering_plan(live).ensures
                ),
                row["target_id"],
            )
            distribution[count] = distribution.get(count, 0) + 1
            total += count
        self.assertEqual(
            distribution,
            {1: 78, 2: 49, 3: 10, 4: 9, 5: 1, 6: 1, 8: 1, 10: 1},
        )
        self.assertEqual(total, 271)
        self.assertEqual(len(set(artifact_hashes)), 270)

    def test_mutation_checker_rejects_manifest_and_code_drift(self) -> None:
        live = self.live_by_id[1410]
        live.canonical_target = generate_campaign.canonical_target(live)
        root = ROOT / "proof_harnesses" / live.target_id
        source = (root / "mutation_proof.rs").read_text()
        manifest = json.loads((root / "mutations.json").read_text())

        stale_manifest = json.loads(json.dumps(manifest))
        stale_manifest["mutants"][0]["change"] = "obsolete cursor mutation"
        self.assertTrue(
            any(
                "manifest differs from generated code" in error
                for error in verify_campaign.check_mutation_artifacts(
                    live.target_id,
                    live,
                    source,
                    stale_manifest,
                )
            )
        )

        mutation = generate_campaign.behavioral_mutations(live)[0]
        rendered = generate_campaign.render_behavioral_mutation(live, mutation)
        stale_source = source.replace(
            rendered,
            rendered.replace(
                mutation.mutated_postcondition,
                mutation.original_postcondition,
                1,
            ),
            1,
        )
        self.assertTrue(
            any(
                "does not exactly match" in error
                for error in verify_campaign.check_mutation_artifacts(
                    live.target_id,
                    live,
                    stale_source,
                    manifest,
                )
            )
        )

    def test_mutation_diagnostics_reject_mixed_error_kinds(self) -> None:
        source = "\n".join(
            [
                "pub fn mutation_one()",
                "    ensures false,",
                "{",
                "}",
                "",
                "pub fn mutation_two()",
                "    ensures false,",
                "{",
                "}",
            ]
        )
        output = "\n".join(
            [
                "error: postcondition not satisfied",
                "    --> mutation_proof.rs:2:13",
                "",
                "error: precondition not satisfied",
                "    --> mutation_proof.rs:7:13",
                "",
                "verification results:: 0 verified, 2 errors",
                "error: aborting due to 2 previous errors",
            ]
        )
        analysis = run_verus_matrix.analyze_mutation_diagnostics(
            source,
            output,
            ["mutation_one", "mutation_two"],
        )
        self.assertFalse(analysis["passed"])
        self.assertEqual(
            [diagnostic["kind"] for diagnostic in analysis["diagnostics"]],
            [
                "postcondition not satisfied",
                "precondition not satisfied",
            ],
        )

    def test_static_specification_gate(self) -> None:
        self.assertEqual(verify_campaign.verify_static(include_proofs=False), [])

    def test_source_call_traces_exclude_bounds_and_collapse_branches(self) -> None:
        all_calls = [
            call
            for row in self.live_by_id.values()
            for call in generate_campaign.source_call_names(row)
        ]
        self.assertNotIn("fnmut", all_calls)
        self.assertNotIn("fnonce", all_calls)
        vacant_insert = generate_campaign.source_call_names(
            self.live_by_id[1303]
        )
        self.assertIn("source_match_branch", vacant_insert)
        self.assertNotIn("insert_recursing", vacant_insert)
        self.assertNotIn("push_with_handle", vacant_insert)

    def test_generated_proofs_are_operation_local_source_lowerings(self) -> None:
        selected = [
            row
            for row in self.inventory["rows"]
            if row["disposition"] in {"exact_vstd", "generated"}
        ]
        self.assertEqual(len(selected), 150)
        leaf_exception_targets = []
        for row in selected:
            live = self.live_by_id[row["rustdoc_item_id"]]
            implementation = generate_campaign.implementation_harness_source(live)
            completeness = generate_campaign.completeness_harness_source(live)
            target_id = row["target_id"]
            self.assertNotIn("SourceState", implementation, target_id)
            self.assertNotIn("struct Outcome", implementation, target_id)
            self.assertNotIn("SourceState", completeness, target_id)
            self.assertNotIn("struct Outcome", completeness, target_id)
            self.assertIn("extern crate alloc;", implementation, target_id)
            for token in verify_campaign.LEGACY_LOWERING_TOKENS:
                self.assertNotIn(token, implementation, f"{target_id}: {token}")
            self.assertNotIn("pub assume_specification", implementation, target_id)
            _, inputs, _, where_clause, _, ensures = generate_campaign.proof_contract(
                live
            )
            self.assertNotIn(
                generate_campaign.actual_target_call(live, inputs),
                implementation,
                target_id,
            )
            self.assertEqual(
                verify_campaign.check_target_local_boundaries(
                    target_id, live, implementation
                ),
                [],
                target_id,
            )
            analysis = generate_campaign.analyze_target_local_lowering(
                live, implementation
            )
            self.assertTrue(
                analysis["boundaries"]
                or analysis["has_executable_source_call"],
                target_id,
            )
            self.assertFalse(analysis["target_external_body"], target_id)
            self.assertFalse(analysis["contract_cloning_boundaries"], target_id)
            body = generate_campaign.target_function_body(
                implementation, row["rustdoc_item_id"]
            )
            self.assertTrue(body.strip(), target_id)
            for boundary in analysis["boundaries"]:
                self.assertIn(
                    boundary["kind"],
                    generate_campaign.SOURCE_BOUNDARY_KINDS,
                    target_id,
                )
                self.assertTrue(boundary["source_span"], target_id)
                self.assertEqual(len(boundary["source_sha256"]), 64, target_id)
                self.assertTrue(boundary["footprint"]["reads"], target_id)
                self.assertTrue(boundary["footprint"]["writes"], target_id)
                self.assertTrue(boundary["used_in_target_body"], target_id)
                self.assertIn(f"{boundary['name']}(", body, target_id)
            if analysis["leaf_representation_exceptions"]:
                leaf_exception_targets.append(target_id)
            target_header = implementation.split(
                f"pub fn rust_1_96_target_{row['rustdoc_item_id']}", 1
            )[1].split("\n{\n", 1)[0]
            for clause in ensures:
                self.assertIn(clause, target_header, target_id)
            self.assertIn("pub open spec fn equivalent", completeness, target_id)
            self.assertIn("pub proof fn completeness", completeness, target_id)
            self.assertNotIn("assume(", completeness, target_id)
            if where_clause:
                theorem_header = completeness.split(
                    "pub proof fn completeness", 1
                )[1].split("    requires", 1)[0]
                for predicate in generate_campaign.split_top_level_predicates(
                    where_clause
                ):
                    self.assertIn(predicate, theorem_header, target_id)
        self.assertLessEqual(len(leaf_exception_targets), 12)
        self.assertTrue(leaf_exception_targets)

    def test_high_risk_targets_are_substantively_source_shaped(self) -> None:
        expectations = {
            1471: (  # BTreeMap as Extend::extend
                ["extend_into_iter_cursor", "extend_cursor_next_pair", "extend_insert_pair"],
                ["while", "decreases", "invariant", "match step"],
            ),
            1382: (  # BTreeMap::iter
                [
                    "map_root_present",
                    "root_full_leaf_range",
                    "iterator_from_full_leaf_range",
                    "iterator_from_absent_leaf_range",
                ],
                ["if root_present {", "} else {"],
            ),
            1519: (  # Iter as Iterator::next
                ["iterator_remaining_length_field", "iterator_step_front"],
                ["if length == 0 {", "None", "Some(item)"],
            ),
            1526: (  # Iter as DoubleEndedIterator::next_back
                ["iterator_remaining_length_field", "iterator_step_back"],
                ["if length == 0 {", "None", "Some(item)"],
            ),
            1404: (  # BTreeMap::retain
                [
                    "extract_if_range_cursor",
                    "extract_if_callback_law",
                    "extract_cursor_next_key",
                    "extract_if_visit_key",
                ],
                ["while", "decreases", "invariant", "cursor.visited@"],
            ),
        }
        for item_id, (boundaries, body_tokens) in expectations.items():
            live = self.live_by_id[item_id]
            implementation = generate_campaign.implementation_harness_source(live)
            names = generate_campaign.source_boundary_names(live)
            for boundary in boundaries:
                self.assertIn(boundary, names, item_id)
            body = generate_campaign.target_function_body(implementation, item_id)
            for token in body_tokens:
                self.assertIn(token, body, item_id)
            analysis = generate_campaign.analyze_target_local_lowering(
                live, implementation
            )
            self.assertFalse(analysis["contract_cloning_boundaries"], item_id)
            self.assertTrue(
                analysis["terminal_delegation"] is None
                or analysis["terminal_delegation"]["allowed"],
                analysis["terminal_delegation"],
            )

    def _lowering_fixture(self, item_id: int) -> tuple[Any, str]:
        live = self.live_by_id[item_id]
        return live, generate_campaign.implementation_harness_source(live)

    def test_checker_rejects_renamed_whole_target_helper(self) -> None:
        live, implementation = self._lowering_fixture(1391)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        clone = "\n".join(
            [
                "// boundary-op: renamed_source_helper",
                "// boundary-kind: node_search",
                "// boundary-operation: renamed whole-target private closure",
                "// boundary-source: alloc/src/collections/btree/map.rs:717-727",
                "// boundary-source-sha256: " + generate_campaign.sha256_text(
                    generate_campaign.source_span_text(live, (717, 727))
                ),
                "// boundary-source-tokens: self.root",
                "// boundary-reads: BTreeMap::root",
                "// boundary-writes: none",
                "// boundary-note: renamed whole-target helper",
                "#[verifier::external_body]",
                "fn renamed_source_helper<'s, K, V, A, Q>(",
                "    map: &'s BTreeMap<K, V, A>,",
                "    key: &Q",
                ") -> (outcome: Option<&'s V>)",
                "    ensures",
            ]
            + [
                "        "
                + re.sub(r"\bresult\b", "outcome", clause.replace("this@", "map@"))
                + ","
                for clause in ensures
            ]
            + ["{", "    loop { }", "}", ""]
        )
        marker = "pub fn rust_1_96_target_1391"
        mutated = implementation.replace(marker, clone + "\n" + marker, 1)
        mutated = mutated.replace(
            "    let root_present = map_root_present(this, key);",
            "    let ignored = renamed_source_helper(this, key);\n"
            "    let root_present = map_root_present(this, key);",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_renamed", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_rejects_indirect_terminal_delegation(self) -> None:
        live, implementation = self._lowering_fixture(1427)
        body = generate_campaign.target_function_body(implementation, 1427)
        indirect = body.replace(
            "    length",
            "    let alias = length;\n    alias",
            1,
        )
        mutated = implementation.replace(body, indirect, 1)
        mutated = mutated.replace(
            "// boundary-leaf-representation-exception:",
            "// boundary-removed-exception:",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_indirect", live, mutated
        )
        self.assertTrue(
            any(
                "returns the unchanged result of terminal external boundary" in error
                for error in errors
            ),
            errors,
        )

    def test_checker_rejects_contract_cloning_helper(self) -> None:
        live, implementation = self._lowering_fixture(1519)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        cloned = "\n".join(
            "        " + clause.replace("this", "iterator").replace("result", "item")
            + ","
            for clause in ensures
        )
        mutated = re.sub(
            r"(fn iterator_step_front[\s\S]*?\n    ensures\n)[\s\S]*?(\n\{\n)",
            lambda match: match.group(1) + cloned + match.group(2),
            implementation,
            count=1,
        )
        self.assertNotEqual(mutated, implementation)
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_clone", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_rejects_split_conjunct_contract_clone(self) -> None:
        live, implementation = self._lowering_fixture(1382)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        atoms = [
            atom
            for clause in ensures
            for atom in generate_campaign.normalized_contract_atoms(clause)
        ]
        span = generate_campaign.source_span_for(live, ("pub fn iter",))
        helper = "\n".join(
            [
                "// boundary-op: split_contract_clone",
                "// boundary-kind: iterator_representation",
                "// boundary-operation: split rendering of the whole target contract",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                "// boundary-source-sha256: "
                + generate_campaign.sha256_text(
                    generate_campaign.source_span_text(live, span)
                ),
                "// boundary-source-tokens: pub fn iter",
                "// boundary-reads: BTreeMap::root",
                "// boundary-writes: fresh iterator",
                "// boundary-note: adversarial split-conjunct clone",
                "#[verifier::external_body]",
                "fn split_contract_clone<'m, K, V, A>(",
                "    map: &'m BTreeMap<K, V, A>",
                ") -> (outcome: Iter<'m, K, V>)",
                "    ensures",
                *[
                    "        "
                    + re.sub(r"\bresult\b", "outcome", atom).replace(
                        "this", "map"
                    )
                    + ","
                    for atom in atoms
                ],
                "{",
                "    loop { }",
                "}",
                "",
            ]
        )
        marker = "pub fn rust_1_96_target_1382"
        mutated = implementation.replace(marker, helper + marker, 1).replace(
            "    let root_present = map_root_present(this);",
            "    let ignored = split_contract_clone(this);\n"
            "    let root_present = map_root_present(this);",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_split_clone", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_rejects_ghost_expected_contract_laundering(self) -> None:
        live, implementation = self._lowering_fixture(1382)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        atoms = [
            atom
            for clause in ensures
            for atom in generate_campaign.normalized_contract_atoms(clause)
        ]
        span = generate_campaign.source_span_for(live, ("pub fn iter",))
        helper = "\n".join(
            [
                "// boundary-op: ghost_contract_clone",
                "// boundary-kind: representation_read",
                "// boundary-operation: whole target contract hidden behind expected@",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                "// boundary-source-sha256: "
                + generate_campaign.sha256_text(
                    generate_campaign.source_span_text(live, span)
                ),
                "// boundary-source-tokens: pub fn iter",
                "// boundary-reads: BTreeMap::root",
                "// boundary-writes: fresh ghost token",
                "// boundary-note: adversarial ghost-token laundering",
                "#[verifier::external_body]",
                "fn ghost_contract_clone<'m, K, V, A>(",
                "    map: &'m BTreeMap<K, V, A>",
                ") -> (token: SourceIteratorContractToken<Iter<'m, K, V>>)",
                "    ensures",
                *[
                    "        "
                    + re.sub(r"\bresult\b", "token.expected@", atom).replace(
                        "this", "map"
                    )
                    + ","
                    for atom in atoms
                ],
                "{",
                "    loop { }",
                "}",
                "",
            ]
        )
        marker = "pub fn rust_1_96_target_1382"
        mutated = implementation.replace(marker, helper + marker, 1).replace(
            "    let root_present = map_root_present(this);",
            "    let ignored = ghost_contract_clone(this);\n"
            "    let root_present = map_root_present(this);",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_ghost_clone", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_unfolds_range_result_contract(self) -> None:
        live, implementation = self._lowering_fixture(1407)
        span = generate_campaign.source_span_for(live, ("range_search",))
        helper = "\n".join(
            [
                "// boundary-op: unfolded_range_clone",
                "// boundary-kind: iterator_representation",
                "// boundary-operation: old whole-range constructor clone",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                "// boundary-source-sha256: "
                + generate_campaign.sha256_text(
                    generate_campaign.source_span_text(live, span)
                ),
                "// boundary-source-tokens: range_search",
                "// boundary-reads: BTreeMap::root",
                "// boundary-writes: fresh range iterator",
                "// boundary-note: adversarial unfolded predicate clone",
                "#[verifier::external_body]",
                "fn unfolded_range_clone<'m, K, V, A, T, R>(",
                "    map: &'m BTreeMap<K, V, A>, range: R",
                ") -> (iterator: Range<'m, K, V>)",
                "    ensures",
                "        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> "
                "(ordered_iterator_key_trace::<K, _>(&iterator) == "
                "ordered_range_key_sequence::<K, V, T, R>(map@, &range)),",
                "        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> "
                "(iterator.ordered_remaining().len() == "
                "ordered_range_key_sequence::<K, V, T, R>(map@, &range).len()),",
                "        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> "
                "(ordered_iterator_value_trace::<V, _>(&iterator) == "
                "ordered_range_pair_sequence::<K, V, T, R>(map@, &range).map("
                "|_index: int, pair: (K, V)| pair.1)),",
                "{",
                "    loop { }",
                "}",
                "",
            ]
        )
        marker = "pub fn rust_1_96_target_1407"
        mutated = implementation.replace(marker, helper + marker, 1).replace(
            "    let root_present = map_root_present(this);",
            "    let ignored = unfolded_range_clone(this, range);\n"
            "    let root_present = map_root_present(this);",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_range_clone", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_parses_fnmut_generic_contract_clone(self) -> None:
        live, implementation = self._lowering_fixture(1413)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        span = generate_campaign.source_span_for(live, ("pub fn extract_if",))
        helper = "\n".join(
            [
                "// boundary-op: fnmut_contract_clone",
                "// boundary-kind: iterator_representation",
                "// boundary-operation: FnMut-bearing whole target clone",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                "// boundary-source-sha256: "
                + generate_campaign.sha256_text(
                    generate_campaign.source_span_text(live, span)
                ),
                "// boundary-source-tokens: pub fn extract_if",
                "// boundary-reads: BTreeMap::root, callback",
                "// boundary-writes: fresh iterator",
                "// boundary-note: adversarial FnMut parser fixture",
                "#[verifier::external_body]",
                "fn fnmut_contract_clone<'m, K: Ord, V, A: Allocator + Clone,",
                "    F: FnMut(&K, &mut V) -> bool, R: RangeBounds<K>>(",
                "    map: &'m mut BTreeMap<K, V, A>, range: R, pred: F",
                ") -> (outcome: ExtractIf<'m, K, V, R, F, A>)",
                "    ensures",
                *[
                    "        "
                    + re.sub(r"\bresult\b", "outcome", clause).replace(
                        "this", "map"
                    )
                    + ","
                    for clause in ensures
                ],
                "{",
                "    loop { }",
                "}",
                "",
            ]
        )
        marker = "pub fn rust_1_96_target_1413"
        mutated = implementation.replace(marker, helper + marker, 1).replace(
            "    proof { broadcast use group_generated_btree_map_axioms; }",
            "    let ignored = fnmut_contract_clone(this, range, pred);\n"
            "    proof { broadcast use group_generated_btree_map_axioms; }",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_fnmut_clone", live, mutated
        )
        self.assertFalse(
            any("signature parse failed" in error for error in errors), errors
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )

    def test_checker_rejects_padding_after_terminal_clone(self) -> None:
        live, implementation = self._lowering_fixture(1399)
        _, _, _, _, _, ensures = generate_campaign.proof_contract(live)
        span = generate_campaign.source_span_for(live, ("self.get(key)",))
        source_hash = generate_campaign.sha256_text(
            generate_campaign.source_span_text(live, span)
        )
        helpers = "\n".join(
            [
                "// boundary-op: whole_lookup_clone",
                "// boundary-kind: node_search",
                "// boundary-operation: whole contains_key contract clone",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                f"// boundary-source-sha256: {source_hash}",
                "// boundary-source-tokens: self.get(key)",
                "// boundary-reads: BTreeMap::root",
                "// boundary-writes: none",
                "// boundary-note: adversarial whole-target clone",
                "#[verifier::external_body]",
                "fn whole_lookup_clone<K, V, A, Q>(",
                "    map: &BTreeMap<K, V, A>, key: &Q",
                ") -> (outcome: bool)",
                "    ensures",
                *[
                    "        "
                    + re.sub(r"\bresult\b", "outcome", clause).replace(
                        "this", "map"
                    )
                    + ","
                    for clause in ensures
                ],
                "{",
                "    loop { }",
                "}",
                "",
                "// boundary-op: padding_noop",
                "// boundary-kind: representation_write",
                "// boundary-operation: padding write with unchanged value",
                f"// boundary-source: {live.source_file}:{span[0]}-{span[1]}",
                f"// boundary-source-sha256: {source_hash}",
                "// boundary-source-tokens: self.get(key)",
                "// boundary-reads: bool",
                "// boundary-writes: bool",
                "// boundary-note: adversarial padding boundary",
                "#[verifier::external_body]",
                "fn padding_noop(value: &mut bool)",
                "    ensures",
                "        *final(value) == *old(value),",
                "{",
                "}",
                "",
            ]
        )
        marker = "pub fn rust_1_96_target_1399"
        mutated = implementation.replace(marker, helpers + marker, 1)
        body = generate_campaign.target_function_body(mutated, 1399)
        mutated = mutated.replace(
            body,
            "    let mut outcome = whole_lookup_clone(this, key);\n"
            "    padding_noop(&mut outcome);\n"
            "    outcome",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_padding", live, mutated
        )
        self.assertTrue(
            any("duplicates or subsumes" in error for error in errors), errors
        )
        self.assertTrue(
            any(
                "declared write guarantees only unchanged observations" in error
                for error in errors
            ),
            errors,
        )
        self.assertTrue(
            any(
                "returns the unchanged result of terminal external boundary" in error
                for error in errors
            ),
            errors,
        )

    def test_checker_rejects_target_external_body_and_legacy_tokens(self) -> None:
        live, implementation = self._lowering_fixture(1391)
        mutated = implementation.replace(
            "pub fn rust_1_96_target_1391",
            "#[verifier::external_body]\npub fn rust_1_96_target_1391",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_external", live, mutated
        )
        self.assertTrue(
            any("public target body is external_body" in error for error in errors),
            errors,
        )
        legacy = implementation.replace(
            "    let root_present = map_root_present(this, key);",
            "    let mut source_cursor = begin_source_lowering();\n"
            "    let root_present = map_root_present(this, key);",
            1,
        )
        legacy_errors = verify_campaign.check_target_local_boundaries(
            "synthetic_legacy", live, legacy
        )
        self.assertTrue(
            any("legacy lowering token" in error for error in legacy_errors),
            legacy_errors,
        )

    def test_checker_rejects_unused_and_undeclared_boundaries(self) -> None:
        live, implementation = self._lowering_fixture(1391)
        unused = implementation.replace(
            "        let found = node_search_tree_found(this, key);",
            "        let found = true;",
            1,
        )
        errors = verify_campaign.check_target_local_boundaries(
            "synthetic_unused", live, unused
        )
        self.assertTrue(
            any("is never used" in error for error in errors), errors
        )
        undeclared = implementation.replace(
            "pub fn rust_1_96_target_1391",
            "#[verifier::external_body]\n"
            "fn undocumented_helper() -> (value: bool)\n{\n    loop { }\n}\n\n"
            "pub fn rust_1_96_target_1391",
            1,
        )
        undeclared_errors = verify_campaign.check_target_local_boundaries(
            "synthetic_undeclared", live, undeclared
        )
        self.assertTrue(
            any("has no boundary declaration" in error for error in undeclared_errors),
            undeclared_errors,
        )

    def test_checker_rejects_missing_span_hash_and_footprint(self) -> None:
        live, implementation = self._lowering_fixture(1391)
        wrong_hash = implementation.replace(
            "// boundary-source-sha256: ",
            "// boundary-source-sha256: 00",
            1,
        )
        self.assertTrue(
            any(
                "source span hash does not match frozen source" in error
                for error in verify_campaign.check_target_local_boundaries(
                    "synthetic_hash", live, wrong_hash
                )
            )
        )
        dropped_footprint = implementation.replace(
            "// boundary-reads: BTreeMap::root\n// boundary-writes: none",
            "// boundary-reads: none\n// boundary-writes: none",
            1,
        )
        self.assertTrue(
            any(
                "footprint declares neither reads nor writes" in error
                for error in verify_campaign.check_target_local_boundaries(
                    "synthetic_footprint", live, dropped_footprint
                )
            )
        )
        dropped_operation = implementation.replace(
            "// boundary-operation: BTreeMap::root Option discriminant read "
            "(`self.root.as_ref()?`)\n",
            "",
            1,
        )
        self.assertTrue(
            any(
                "missing boundary-operation" in error
                for error in verify_campaign.check_target_local_boundaries(
                    "synthetic_operation", live, dropped_operation
                )
            )
        )
        outside_span = implementation.replace(
            "// boundary-source: alloc/src/collections/btree/map.rs:722-722",
            "// boundary-source: alloc/src/collections/btree/map.rs:1-2",
            1,
        )
        self.assertTrue(
            any(
                "source span leaves the target source item" in error
                for error in verify_campaign.check_target_local_boundaries(
                    "synthetic_span", live, outside_span
                )
            )
        )

    def test_checker_rejects_boundary_type_shape_errors(self) -> None:
        live, implementation = self._lowering_fixture(1391)
        invalid_state = implementation.replace(
            "found <==> contains_borrowed_key(map@, key)",
            "found <==> contains_borrowed_key(old(map)@, key)",
            1,
        )
        state_errors = verify_campaign.check_target_local_boundaries(
            "synthetic_shared_old", live, invalid_state
        )
        self.assertTrue(
            any("old(map) is used for non-mutable parameter" in error
                for error in state_errors),
            state_errors,
        )
        invalid_result = implementation.replace(
            "found <==> contains_borrowed_key(map@, key)",
            "match found { Some(_) => true, None => false }",
            1,
        )
        result_errors = verify_campaign.check_target_local_boundaries(
            "synthetic_non_option", live, invalid_result
        )
        self.assertTrue(
            any("is matched as Option but has type bool" in error
                for error in result_errors),
            result_errors,
        )

    def test_trust_and_transformation_metadata_are_operation_local(self) -> None:
        for item_id in (1391, 1471, 1404, 1382):
            live = self.live_by_id[item_id]
            manifest = generate_campaign.source_boundary_manifest(live)
            self.assertTrue(manifest, item_id)
            for boundary in manifest:
                self.assertIn(
                    boundary["kind"],
                    generate_campaign.SOURCE_BOUNDARY_KINDS,
                    item_id,
                )
                self.assertRegex(
                    boundary["source_span"],
                    r"^alloc/src/collections/btree/.+\.rs:\d+-\d+$",
                    item_id,
                )
                self.assertEqual(len(boundary["source_sha256"]), 64, item_id)
                self.assertTrue(boundary["source_tokens"], item_id)
                self.assertIn(boundary["mode"], {"exec", "proof"}, item_id)
                self.assertTrue(boundary["footprint"]["reads"], item_id)
                self.assertTrue(boundary["footprint"]["writes"], item_id)
            realizations = generate_campaign.source_call_realizations(live)
            self.assertEqual(
                sorted(realizations), sorted(set(generate_campaign.source_call_names(live)))
            )
            allowed = set(generate_campaign.source_boundary_names(live)) | {
                "target_control_flow"
            }
            for call, realized in realizations.items():
                self.assertIn(realized, allowed, f"{item_id}:{call}")


if __name__ == "__main__":
    unittest.main()
