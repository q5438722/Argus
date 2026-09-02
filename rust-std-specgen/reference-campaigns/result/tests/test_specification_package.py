from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audit_specification  # noqa: E402
import check_specification_gate  # noqa: E402
import run_spec_negative_mutations  # noqa: E402
import run_verus_typecheck  # noqa: E402
import specification_support as support  # noqa: E402


class ResultSpecificationPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = support.load_json(support.CATALOG_PATH)
        cls.catalog_by_id = {
            int(row["rustdoc_item_id"]): row
            for row in cls.catalog["rows"]
        }

    def test_catalog_exactly_resolves_live_inventory(self) -> None:
        inventory = support.inventory_by_id()
        self.assertEqual(set(self.catalog_by_id), set(inventory))
        generated = {
            item_id
            for item_id, row in self.catalog_by_id.items()
            if row["disposition"] == "generated"
        }
        exact = {
            item_id
            for item_id, row in self.catalog_by_id.items()
            if row["disposition"] == "exact_vstd"
        }
        self.assertEqual(generated, support.generated_ids())
        self.assertEqual(exact, support.exact_ids())
        self.assertEqual(
            self.catalog["counts"]["specified"],
            self.catalog["counts"]["stable_inventory_total"],
        )
        self.assertEqual(self.catalog["counts"]["pending"], 0)

    def test_generated_markers_are_pending_rows_only(self) -> None:
        blocks = support.contract_blocks()
        self.assertEqual(set(blocks), support.generated_ids())
        self.assertFalse(set(blocks) & support.exact_ids())
        support.validate_metadata_coverage()

    def test_generated_contracts_have_direct_semantics(self) -> None:
        for item_id, block in support.contract_blocks().items():
            with self.subTest(rustdoc_item_id=item_id):
                expected = self.catalog_by_id[item_id]["contract"][
                    "semantic_clause_sha256"
                ]
                self.assertEqual(
                    audit_specification.direct_errors(
                        item_id, block.text, expected
                    ),
                    [],
                )

    def test_source_and_derive_fidelity_pass(self) -> None:
        payload = audit_specification.source_fidelity_audit()
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["checked_rows"], len(self.catalog_by_id))
        self.assertEqual(
            payload["derive_capture_count"], len(support.DERIVED_IDS)
        )

    def test_repaired_contracts_expose_direct_semantics(self) -> None:
        blocks = support.contract_blocks()
        for item_id in support.SHORT_CIRCUIT_IDS:
            text = support.squash(blocks[item_id].text)
            self.assertNotIn("result_delegate_trace", text)
            self.assertIn("result_all_ok( into_iter_remaining", text)
            self.assertIn("result_short_circuit_trace", text)
            self.assertIn(").len() == stop + 1", text)
            self.assertIn("forall|prior: int|", text)
            self.assertIn("result == Err(", text)
        deref_mut = support.squash(blocks[29294].text)
        self.assertNotIn("result_deref_mut_projection", deref_mut)
        self.assertIn("result_mut_ref_initial_state", deref_mut)
        self.assertIn("result_mut_ref_final_state", deref_mut)
        self.assertIn(
            "result_deref_mut_state((*final(input))->Ok_0)",
            deref_mut,
        )

    def test_iterator_transition_views_are_linked(self) -> None:
        vocabulary = support.VOCABULARY_PATH.read_text(encoding="utf-8")
        links = {
            "result_into_iter_value_values": "result_into_iter_values",
            "result_iter_mut_value_identities": "result_iter_mut_identities",
            "result_iter_mut_value_values": "result_iter_mut_values",
            "result_iter_value_identities": "result_iter_identities",
            "result_iter_value_values": "result_iter_values",
        }
        for helper, borrowed in links.items():
            with self.subTest(helper=helper):
                self.assertIn(f"pub open spec fn {helper}", vocabulary)
                self.assertIn(f"{borrowed}(&iter)", vocabulary)
                self.assertNotIn(
                    f"pub uninterp spec fn {helper}", vocabulary
                )

    def test_helper_usage_is_complete_and_narrow(self) -> None:
        payload = support.load_json(support.HELPER_USAGE_PATH)
        self.assertEqual(payload["unused_helpers"], [])
        self.assertEqual(payload["whole_target_helpers"], [])
        self.assertEqual(
            {row["helper"] for row in payload["records"]},
            support.helper_names(),
        )
        self.assertTrue(
            all(row["target_count"] > 0 for row in payload["records"])
        )

    def test_outcome_equivalence_covers_inventory(self) -> None:
        payload = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
        records = {
            int(row["rustdoc_item_id"]): row
            for row in payload["records"]
        }
        self.assertEqual(set(records), set(support.inventory_by_id()))
        self.assertEqual(
            {
                item_id
                for item_id, row in records.items()
                if row["kind"] != "exact_equality"
            },
            set(),
        )
        self.assertEqual(payload["schema_version"], 3)
        self.assertEqual(payload["exact_equality_count"], len(records))
        self.assertEqual(payload["non_exact_equivalence_count"], 0)
        self.assertEqual(
            payload["exact_observation_schema_equality_count"],
            len(support.PROJECTED_EXACT_OBSERVATION_SCHEMAS),
        )
        self.assertEqual(
            payload["version_set_sha256"],
            support.outcome_equivalence_version_set_sha256(
                list(records.values())
            ),
        )
        for item_id, record in records.items():
            with self.subTest(rustdoc_item_id=item_id):
                identity = support.outcome_equivalence_identity(item_id)
                for key, expected in identity.items():
                    self.assertEqual(record[key], expected)
                self.assertIsNone(record["non_exact_justification"])
                self.assertEqual(
                    self.catalog_by_id[item_id]["outcome_equivalence"],
                    support.outcome_equivalence_binding(record, payload),
                )
                self.assertNotIn(
                    "equivalence", self.catalog_by_id[item_id]
                )
                components = set(record["observable_components"])
                positive = record["positive_witness"]
                negative = record["negative_witness"]
                self.assertEqual(
                    set(positive["left_observations"]), components
                )
                self.assertEqual(
                    positive["left_observations"],
                    positive["right_observations"],
                )
                self.assertTrue(positive["expected_equivalent"])
                self.assertEqual(
                    set(negative["left_observations"]), components
                )
                differences = {
                    component
                    for component in components
                    if negative["left_observations"][component]
                    != negative["right_observations"][component]
                }
                self.assertEqual(
                    differences,
                    {negative["distinguishing_component"]},
                )
                self.assertFalse(negative["expected_equivalent"])
                component_witnesses = record[
                    "component_inequality_witnesses"
                ]
                self.assertEqual(
                    [
                        witness["distinguishing_component"]
                        for witness in component_witnesses
                    ],
                    record["observable_components"],
                )
                for component, witness in zip(
                    record["observable_components"],
                    component_witnesses,
                    strict=True,
                ):
                    self.assertEqual(
                        {
                            name
                            for name in components
                            if witness["left_observations"][name]
                            != witness["right_observations"][name]
                        },
                        {component},
                    )
                if (
                    item_id
                    in support.PROJECTED_EXACT_OBSERVATION_SCHEMAS
                ):
                    self.assertEqual(
                        record["equality_scope"],
                        "source_backed_observation_schema",
                    )
                    self.assertEqual(
                        record["proof_observation_schema"]["mode"],
                        "exact_componentwise_source_observation_equality",
                    )
                    self.assertEqual(
                        record["observable_components"],
                        list(
                            support.TARGET_OBSERVATION_COMPONENTS[
                                item_id
                            ]
                        ),
                    )
                    contract = self.catalog_by_id[item_id]["contract"]
                    contract_text = " ".join(
                        [
                            *contract.get("requires", []),
                            *contract.get("direct_ensures", []),
                        ]
                    )
                    for anchors in record[
                        "component_contract_bindings"
                    ].values():
                        self.assertTrue(
                            all(
                                anchor in contract_text
                                for anchor in anchors
                            )
                        )
                    self.assertFalse(
                        any(
                            isinstance(value, str)
                            and value.startswith(
                                f"core-result-rustdoc-{item_id}:"
                                "observable-"
                            )
                            for value in [
                                *positive["left_observations"].values(),
                                *positive["right_observations"].values(),
                                *negative["left_observations"].values(),
                                *negative["right_observations"].values(),
                            ]
                        )
                    )
                unhashed = {
                    key: value
                    for key, value in record.items()
                    if key != "record_sha256"
                }
                self.assertEqual(
                    record["record_sha256"],
                    support.object_sha256(unhashed),
                )

    def test_package_manifest_hashes_every_artifact(self) -> None:
        payload = support.load_json(support.PACKAGE_MANIFEST_PATH)
        artifacts = {
            row["path"]: row["sha256"] for row in payload["artifacts"]
        }
        self.assertEqual(
            set(artifacts), set(support.SPEC_PACKAGE_ARTIFACTS)
        )
        for relative, expected in artifacts.items():
            self.assertEqual(
                support.sha256(ROOT / relative),
                expected,
            )
        self.assertFalse(payload["proof_harnesses_authorized"])
        self.assertFalse((ROOT / "proof_harnesses").exists())

    def test_selected_relation_capability_is_explicitly_unsupported(
        self,
    ) -> None:
        equivalence = support.load_json(
            support.OUTCOME_EQUIVALENCE_PATH
        )
        capability = support.load_json(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        )
        self.assertEqual(
            capability,
            support.feedback_relation_capability_payload(equivalence),
        )
        self.assertEqual(capability["status"], "unsupported")
        self.assertEqual(
            capability["reason_code"],
            "canonical_runner_has_no_selected_relation_input",
        )
        self.assertEqual(
            capability["selected_relation_evaluated_target_count"],
            0,
        )
        self.assertEqual(
            capability["unsupported_target_count"],
            len(support.generated_ids()),
        )
        self.assertEqual(
            {
                int(record["rustdoc_item_id"])
                for record in capability["records"]
            },
            support.generated_ids(),
        )

    def test_exact_references_hash_loaded_declarations(self) -> None:
        audit = support.load_json(support.EXACT_AUDIT_PATH)
        declarations = {
            row["declaration_id"]: row for row in audit["declarations"]
        }
        references = support.load_json(support.EXACT_REFERENCES_PATH)
        self.assertEqual(
            {
                int(row["rustdoc_item_id"])
                for row in references["references"]
            },
            support.exact_ids(),
        )
        for reference in references["references"]:
            declaration = declarations[reference["declaration_id"]]
            path = ROOT / declaration["source_path"]
            text = support.extract_lines(
                path,
                declaration["start_line"],
                declaration["end_line"],
            ).rstrip("\n")
            self.assertEqual(
                hashlib.sha256(text.encode()).hexdigest(),
                declaration["declaration_sha256"],
            )

    def test_static_audit_evidence_is_passed_and_current(self) -> None:
        summary = support.load_json(audit_specification.SUMMARY_PATH)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(
            {row["audit"] for row in summary["audits"]},
            {name for name, _ in audit_specification.AUDITS},
        )
        for name, _ in audit_specification.AUDITS:
            payload = support.load_json(
                support.AUDIT_ROOT / f"{name}.json"
            )
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(
                payload["inputs"]["contracts_sha256"],
                support.sha256(support.CONTRACT_PATH),
            )

    def test_every_generated_row_has_rejected_mutation(self) -> None:
        payload = support.load_json(
            run_spec_negative_mutations.OUTPUT_PATH
        )
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(
            {int(row["rustdoc_item_id"]) for row in payload["records"]},
            support.generated_ids(),
        )
        for record in payload["records"]:
            self.assertEqual(record["parser_status"], "accepted")
            self.assertEqual(
                record["integrity_rejection_codes"],
                ["semantic_clause_hash_mismatch"],
            )
            self.assertTrue(record["semantic_rejection_codes"])
            self.assertNotEqual(
                record["semantic_rejection_codes"],
                ["semantic_clause_hash_mismatch"],
            )
        records = {
            int(record["rustdoc_item_id"]): record
            for record in payload["records"]
        }
        for item_id in support.SHORT_CIRCUIT_IDS:
            with self.subTest(short_circuit_rustdoc_item_id=item_id):
                record = records[item_id]
                self.assertEqual(
                    record["mutation_kind"],
                    "short_circuit_consumption_boundary",
                )
                self.assertEqual(
                    record["obligation"],
                    "stop_at_first_err_consumption_boundary",
                )
                self.assertEqual(
                    record["before"], ").len() == stop + 1"
                )
                self.assertEqual(
                    record["after"], ").len() > stop + 1"
                )
                self.assertIn(
                    "short_circuit_consumption_boundary_missing",
                    record["semantic_rejection_codes"],
                )

    def test_verus_typecheck_evidence_is_current(self) -> None:
        payload = support.load_json(run_verus_typecheck.OUTPUT_PATH)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["exit_code"], 0)
        self.assertFalse(payload["timed_out"])
        self.assertEqual(
            payload["inputs"]["contracts_sha256"],
            support.sha256(support.CONTRACT_PATH),
        )
        self.assertEqual(
            payload["inputs"]["catalog_sha256"],
            support.sha256(support.CATALOG_PATH),
        )

    def test_feedback_determinism_covers_every_generated_row(self) -> None:
        payload = support.load_json(
            support.AUDIT_ROOT / "feedback_determinism.json"
        )
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(
            {int(row["rustdoc_item_id"]) for row in payload["records"]},
            support.generated_ids(),
        )
        self.assertNotIn("sat", payload["taxonomy"])
        self.assertNotIn("missing", payload["taxonomy"])
        self.assertEqual(
            payload["taxonomy"],
            {"selected_relation_unsupported": len(support.generated_ids())},
        )
        summary = support.load_json(support.FEEDBACK_SUMMARY_PATH)
        equivalence = support.load_json(
            support.OUTCOME_EQUIVALENCE_PATH
        )
        common = support.outcome_equivalence_artifact_binding(
            equivalence
        )
        self.assertEqual(summary["outcome_equivalence"], common)
        self.assertEqual(
            summary["counts"]["equivalence_bound_targets"],
            len(support.generated_ids()),
        )
        self.assertEqual(
            summary["counts"]["selected_relation_evaluated_targets"],
            0,
        )
        self.assertEqual(
            summary["counts"]["selected_relation_unsupported_targets"],
            len(support.generated_ids()),
        )
        relation_capability = support.load_json(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        )
        relation_binding = (
            support.feedback_relation_capability_binding(
                relation_capability
            )
        )
        self.assertEqual(
            summary["selected_relation_evaluation"],
            relation_binding,
        )
        diagnostic_bindings = (
            support.feedback_diagnostic_binding_set()
        )
        self.assertEqual(
            summary["canonical_diagnostic_bindings"],
            diagnostic_bindings,
        )
        self.assertEqual(
            summary["counts"]["diagnostic_only_rounds"],
            diagnostic_bindings["binding_count"],
        )
        self.assertTrue(
            all(
                candidate["outcome_equivalence"][
                    "equivalence_version_id"
                ]
                for candidate in summary["final_candidates"]
            )
        )
        self.assertTrue(
            all(
                candidate["selected_relation_evaluation"]["status"]
                == "unsupported"
                for candidate in summary["final_candidates"]
            )
        )
        equivalence_by_target = {
            str(record["target"]): record
            for record in equivalence["records"]
        }
        for candidate in summary["final_candidates"]:
            target = str(candidate["target"])
            expected_equivalence = (
                support.outcome_equivalence_binding(
                    equivalence_by_target[target],
                    equivalence,
                )
            )
            expected_relation = (
                support.feedback_relation_target_classification(
                    expected_equivalence,
                    relation_capability,
                )
            )
            target_root = (
                support.FEEDBACK_ROOT
                / "targets"
                / support.safe_name(target)
            )
            target_summary = support.load_json(
                target_root / "summary.json"
            )
            self.assertEqual(
                target_summary["selected_relation_evaluation"],
                expected_relation,
            )
            self.assertEqual(
                target_summary["final"]["candidate"][
                    "outcome_equivalence"
                ],
                expected_equivalence,
            )
            round_dirs = sorted(target_root.glob("round_*"))
            self.assertTrue(round_dirs)
            for round_dir in round_dirs:
                binding_path = (
                    round_dir
                    / support.FEEDBACK_DIAGNOSTIC_BINDING_FILENAME
                )
                self.assertEqual(
                    support.load_json(binding_path),
                    support.feedback_round_diagnostic_binding(
                        target,
                        round_dir,
                        expected_equivalence,
                        expected_relation,
                    ),
                )
                round_result_path = round_dir / "round_result.json"
                if round_result_path.is_file():
                    round_result = support.load_json(
                        round_result_path
                    )
                    self.assertEqual(
                        round_result["canonical_evidence_role"],
                        "diagnostic_only",
                    )
                    self.assertEqual(
                        round_result["selected_relation_evaluation"],
                        expected_relation,
                    )

    def test_from_iter_projection_failure_is_adjudicated(self) -> None:
        probe = support.load_json(support.FROM_ITER_PROBE_REPORT_PATH)
        self.assertEqual(probe["status"], "passed")
        self.assertTrue(
            all(
                mutant["rejected_as_expected"]
                for mutant in probe["negative_mutants"].values()
            )
        )
        self.assertTrue(
            probe["negative_mutants"]["consumes_after_err"][
                "rejected_as_expected"
            ]
        )
        adjudication = support.load_json(
            support.FROM_ITER_ADJUDICATION_PATH
        )
        self.assertEqual(adjudication["status"], "passed")
        self.assertEqual(
            adjudication["adjudication"],
            "unsupported_projection_lowering",
        )
        self.assertEqual(
            adjudication["selected_relation_evaluation"]["status"],
            "unsupported",
        )

    def test_aggregate_gate_is_passed(self) -> None:
        payload = support.load_json(check_specification_gate.OUTPUT_PATH)
        self.assertEqual(payload["status"], "passed")
        self.assertFalse(payload["acceptance_claim"])
        self.assertEqual(payload["counts"]["pending"], 0)


if __name__ == "__main__":
    unittest.main()
