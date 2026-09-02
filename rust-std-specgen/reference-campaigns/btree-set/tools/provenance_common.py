from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final


MODULE: Final = "alloc::collections::btree_set"
RUST_VERSION: Final = "1.96.0"
RUST_COMMIT: Final = "ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96"
VERUS_COMMIT: Final = "1beb0fad337b8f8a224cf8684162cb02d0c2fc01"


@dataclass(frozen=True)
class ProvenanceInput:
    source_path: str
    frozen_path: str
    role: str
    ownership: str


INPUTS: Final = (
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/mod.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/mod.rs",
        "public_resolution_authority",
        "module_alias_resolution",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/mod.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/mod.rs",
        "internal_resolution_authority",
        "module_owner_resolution",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/set.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/set.rs",
        "primary_module_source",
        "btree_set_owned",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/set/entry.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/set/entry.rs",
        "unstable_exclusion_source",
        "btree_set_owned_unstable",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/set_val.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/set_val.rs",
        "representation_dependency",
        "private_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/map.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/map.rs",
        "delegation_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/merge_iter.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/merge_iter.rs",
        "set_operation_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/search.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/search.rs",
        "range_validation_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/alloc/src/collections/btree/dedup_sorted_iter.rs",
        "provenance/frozen/rust-1.96/library/alloc/src/collections/btree/dedup_sorted_iter.rs",
        "representative_selection_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/core/src/cmp.rs",
        "provenance/frozen/rust-1.96/library/core/src/cmp.rs",
        "order_semantics_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/core/src/option.rs",
        "provenance/frozen/rust-1.96/library/core/src/option.rs",
        "option_combinator_semantics_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rust-1.96/library/core/src/iter/traits/collect.rs",
        "provenance/frozen/rust-1.96/library/core/src/iter/traits/collect.rs",
        "trait_method_stability_authority",
        "public_inventory_dependency",
    ),
    ProvenanceInput(
        "verus/source/vstd/std_specs/btree.rs",
        "provenance/frozen/vstd/std_specs/btree.rs",
        "existing_vstd_baseline",
        "exact_match_candidate_only",
    ),
    ProvenanceInput(
        "verus/source/vstd/laws_cmp.rs",
        "provenance/frozen/vstd/laws_cmp.rs",
        "order_model_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "verus/source/vstd/std_specs/iter.rs",
        "provenance/frozen/vstd/std_specs/iter.rs",
        "iterator_model_dependency",
        "shared_vstd_dependency",
    ),
    ProvenanceInput(
        "verus/source/vstd/std_specs/range.rs",
        "provenance/frozen/vstd/std_specs/range.rs",
        "range_bounds_model_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "verus/source/vstd/function.rs",
        "provenance/frozen/vstd/function.rs",
        "callback_contract_model_dependency",
        "unaccepted_narrow_dependency",
    ),
    ProvenanceInput(
        "rustdoc-json-1.96/alloc.json",
        "provenance/frozen/rustdoc-json-1.96/alloc.json",
        "public_api_inventory_authority",
        "rustdoc_authority",
    ),
)


COMMANDS: Final = (
    {
        "id": "regenerate_rustdoc_json",
        "kind": "exact",
        "state": "declared_unexecuted_at_freeze",
        "command": (
            'RUSTC_BOOTSTRAP=1 cargo +1.96.0 clean --manifest-path '
            '../rust-1.96/library/Cargo.toml -p alloc '
            '--target-dir "$PWD/provenance/rustdoc-target" && '
            'CARGO_TARGET_DIR="$PWD/provenance/rustdoc-target" '
            "RUSTC_BOOTSTRAP=1 cargo +1.96.0 rustdoc --manifest-path "
            "../rust-1.96/library/Cargo.toml -p alloc --lib -- "
            "-Z unstable-options --output-format json"
        ),
    },
    {
        "id": "generate_campaign",
        "kind": "exact",
        "state": "active",
        "command": "python3 tools/generate_campaign.py",
    },
    {
        "id": "campaign_tests",
        "kind": "exact",
        "state": "active",
        "command": "PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py' -v",
    },
    {
        "id": "generated_specs_no_verify",
        "kind": "exact",
        "state": "active_after_generation",
        "command": (
            "../verus/source/target-verus/release/verus --crate-type=lib "
            "--no-verify specs/generated_btree_set_specs.rs"
        ),
    },
    {
        "id": "feedback_determinism",
        "kind": "template",
        "state": "supervised_after_generation",
        "command": (
            "PYTHONPATH=/home/chentianyu/argus-skill "
            "/home/chentianyu/argus-skill/.venv/bin/python "
            "-m argus_skill.tools.subagent submit "
            "--task-id <task-id> --description "
            "\"BTreeSet generated-contract feedback determinism\" "
            "--command \"python3 tools/run_feedback_gate.py --run-id <run-id>\" "
            "--mode supervised "
            "--run-dir verification/evidence/supervised/<task-id> "
            "--cwd . --timeout 7200 --monitor-interval 120"
        ),
    },
    {
        "id": "proof_harnesses_two_mode",
        "kind": "template",
        "state": "supervised_after_generation",
        "command": (
            "PYTHONPATH=/home/chentianyu/argus-skill "
            "/home/chentianyu/argus-skill/.venv/bin/python "
            "-m argus_skill.tools.subagent submit "
            "--task-id <task-id> --description "
            "\"BTreeSet two-mode Verus and mutation matrix\" "
            "--command \"PYTHONPATH=. python3 tools/run_verus_matrix.py "
            "--run-id <run-id>\" "
            "--mode supervised "
            "--run-dir verification/evidence/verus_matrix/<run-id> "
            "--cwd . --timeout 7200 --monitor-interval 120"
        ),
    },
    {
        "id": "provenance_check",
        "kind": "exact",
        "state": "active",
        "command": "python3 tools/check_provenance.py",
    },
    {
        "id": "independent_review_gate",
        "kind": "template",
        "state": "supervised_after_evidence",
        "command": (
            "PYTHONPATH=/home/chentianyu/argus-skill "
            "/home/chentianyu/argus-skill/.venv/bin/python "
            "-m argus_skill.tools.subagent submit "
            "--task-id <task-id> --description "
            "\"BTreeSet independent <stage> review\" "
            "--command \"PYTHONPATH=/home/chentianyu/argus-skill "
            "/home/chentianyu/argus-skill/.venv/bin/python "
            "tools/run_independent_review.py --stage <stage> "
            "--task-id <task-id> --run-dir "
            "verification/evidence/supervised/<task-id>\" "
            "--mode supervised "
            "--run-dir verification/evidence/supervised/<task-id> "
            "--cwd . --timeout 7200 --monitor-interval 120"
        ),
    },
    {
        "id": "final_aggregate",
        "kind": "exact",
        "state": "active",
        "command": "python3 tools/check_campaign.py",
    },
)


def campaign_root_from(script_path: Path) -> Path:
    return script_path.resolve().parents[1]


def survey_root_from(campaign_root: Path) -> Path:
    return campaign_root.parent
