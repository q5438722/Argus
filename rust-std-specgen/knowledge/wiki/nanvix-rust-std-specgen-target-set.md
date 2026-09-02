---
title: Nanvix Rust Std Specgen Target Set
description: Provenance of the 2,121 pre-abstraction executable Rust std API targets.
---

# Nanvix Rust Std Specgen Target Set

The 2,121-target Nanvix-used Rust std executable API set is the pre-abstraction uncovered set. In the survey workspace, the current `results/uncovered_production_stable_apis.csv` reflects later vstd abstraction coverage and yields 1,910 targets, so it is not equivalent to the 2,121-target full-rerun input.

For the 2,121 pre-abstraction set, use `results/coverage-before-abstractions.csv` together with production-module membership from `results/modules.csv`. The generated output is a fresh spec-generation artifact tree containing manifests, batch summary, final candidates, and analysis; it does not require modifying Rust, vstd, or survey source files.
