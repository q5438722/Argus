---
title: Nanvix Rust Std Specgen Delta Surface
description: Measured prior-vs-fresh decision-change and semantic taxonomy surface for the canonical fresh rerun.
---

# Nanvix Rust Std Specgen Delta Surface

The canonical fresh tree `/home/chentianyu/nanvix-rust-std-specgen-rerun-2026-08-06/specgen/all-2121-gpt56sol-fresh-20260806-0453` contains a prior-vs-fresh audit under `prior_fresh_delta/`. Its machine summary uses nested keys, including `target_set.*`, `decision_delta.*`, `fresh_verifier_counts.*`, and `acceptance_checks.*`; do not expect flat keys such as `prior_targets` or `changed_decisions`.

The stored audit compares the prior tree `/home/chentianyu/nanvix-rust-std-spec-survey/specgen/all-2121-gpt56sol` with the canonical fresh tree by target name and final decision. Its files have been refreshed after the source-backed `alloc::string::String::replace_range`, `alloc::collections::LinkedList::back_mut`, and `core::array::each_mut` recoveries. The canonical verifier records equal 2,121-target sets, 127 accepted semantic candidates, and 1,994 skips; the delta summary records 147 final-decision changes, 117 `add_spec->skip` changes, 30 `skip->add_spec` changes, and zero changed fresh skip rows with empty rationales. `alloc::string::String::replace_range` is absent from `decision_changes.csv` because both prior and fresh final decisions are now `add_spec`; `core::slice::reverse`, `alloc::collections::LinkedList::back_mut`, and `core::array::each_mut` appear in `decision_changes.csv` and `newly_accepted_prior_skip_fresh_add.csv` as `skip->add_spec` rows.

In the refreshed audit, the 117 prior-`add_spec` now-fresh-`skip` rows are concentrated in `data_structure` (71), `io_os_runtime` (17), `memory_pointer` (15), `other` (11), `formatting` (2), and `trait_method` (1). Their fresh issue tags are led by `determinism_unsupported_contract_form` (80), `classification:higher_order_contract` (37), `classification:unsafe_or_representation_sensitive` (31), and `classification:runtime_or_hidden_state` (17); all 117 have `fresh_requires_source_fidelity_classification == not_applicable`.

In the refreshed audit, the 30 prior-`skip` now-fresh-`add_spec` rows are concentrated in `data_structure` (27), `other` (2), and `io_os_runtime` (1). They have empty fresh issue fields; 7 have non-empty source-justified `requires` and 23 have `requires_source_fidelity_classification == not_applicable`.

The stored semantic taxonomy audit artifacts are `prior_fresh_delta/semantic_taxonomy_audit.csv`, `prior_fresh_delta/semantic_taxonomy_summary.json`, and `prior_fresh_delta/SEMANTIC_TAXONOMY_AUDIT.md`. They classify the refreshed 147 changed decisions with zero unclassified rows and zero unjustified downgrade or upgrade rows. The 117 `add_spec->skip` rows all have source-backed `adequate_source_backed_skip` verdicts, and the 30 `skip->add_spec` rows all have source-backed `adequate_source_backed_add_spec` verdicts with empty fresh issue fields and source-justified `requires` clauses where present.
