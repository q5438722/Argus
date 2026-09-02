# Verus vstd coverage of Nanvix-used Rust std APIs

This workspace measures the Rust `core`/`alloc`/`std` modules used by Nanvix and compares their public executable APIs with direct Rust API contracts in Verus vstd.

## Main result

| Scope | Used modules | Modules with exec APIs | Module-listed API paths | Deduplicated API paths | Covered by vstd | Uncovered | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Production source | 80 | 78 | 5887 | 3553 | 348 | 3205 | 9.79% |
| Production, stable APIs only | 80 | 78 | - | 2464 | 343 | 2121 | 13.92% |
| All tracked source, including tests/benchmarks | 81 | 79 | 12031 | 9697 | 348 | 9349 | 3.59% |

The production result is the primary number. The module-listed count retains public aliases such as both `core::mem` and `std::mem`; the deduplicated count collapses those aliases to one canonical Rust API.

The only test/benchmark-only module is `core::arch::x86`, whose 6,144 intrinsic functions dominate the all-source total.

## Source snapshots

| Source | Commit | Branch/toolchain | Remote |
|---|---|---|---|
| Nanvix | `bac7075214a385b0088145eb0738cc0c4f121feb` | `dev` | `git@github.com:nanvix/nanvix.git` |
| rust-lang/rust | `14cae681329a63c622a6e1fbe1d30f9374bc51d8` | `nightly-2026-07-09` | `https://github.com/rust-lang/rust.git` |
| Verus vstd | `1beb0fad337b8f8a224cf8684162cb02d0c2fc01` | `main` | `https://github.com/verus-lang/verus.git` |

## Counting model

- Nanvix usage is extracted from every Git-tracked `.rs` file. tree-sitter-rust parses ordinary Rust; tree-sitter-verus parses files containing Verus syntax.
- A used module is the longest public `core`/`alloc`/`std` module prefix resolved through Rust public reexports and local aliases.
- An exec API is a public free function, inherent method, primitive method, or trait method. Associated constants and macros are excluded.
- Rust API enumeration comes from rustdoc JSON built from the pinned Rust sources, so macro-generated atomic, primitive, and architecture functions are included.
- vstd coverage includes direct `assume_specification` contracts, external trait specifications, and statically expanded atomic, number, and default-value contract macros.
- Coverage is path-level. Two covered production paths have multiple Rust declaration signatures: `Option::cloned` and `str::from_utf8_unchecked`.

## Data quality

- Nanvix: 1786 tracked Rust files, 0 parse-error files, and 1 unresolved path evidence. The only unresolved path is test-local `alloc::run`, which is not the Rust `alloc` crate.
- Parser selection: 1670 files used tree-sitter-rust and 116 used tree-sitter-verus.
- Verus vstd: 826 contract evidence records and 589 unique Rust API paths.
- The lexical fallback canonicalized 312 of 312 non-template `assume_specification` targets.

## Largest stable production gaps

| Module | Stable API paths | Covered | Uncovered |
|---|---:|---:|---:|
| `core::sync::atomic` | 329 | 150 | 179 |
| `std::sync::atomic` | 329 | 150 | 179 |
| `std::collections` | 218 | 61 | 157 |
| `std::sync` | 156 | 1 | 155 |
| `std::io` | 129 | 0 | 129 |
| `core::slice` | 132 | 12 | 120 |
| `std::slice` | 132 | 12 | 120 |
| `core::prelude::v1` | 175 | 56 | 119 |
| `alloc::collections` | 155 | 36 | 119 |
| `core::ptr` | 121 | 2 | 119 |
| `std::ptr` | 121 | 2 | 119 |
| `std::net` | 116 | 0 | 116 |
| `alloc::fmt` | 90 | 0 | 90 |
| `core::fmt` | 90 | 0 | 90 |
| `std::fmt` | 90 | 0 | 90 |
| `std::iter` | 88 | 9 | 79 |
| `std::str` | 87 | 9 | 78 |
| `core::str` | 86 | 9 | 77 |
| `std::thread` | 72 | 0 | 72 |
| `std::fs` | 68 | 0 | 68 |
| `std::path` | 66 | 0 | 66 |
| `std::ffi` | 62 | 0 | 62 |
| `core::cell` | 51 | 0 | 51 |
| `std::cell` | 51 | 0 | 51 |
| `std::time` | 49 | 0 | 49 |

## Complete module list

| Module | Scope | Source files | Exec APIs | Stable APIs | vstd covered | vstd uncovered (stable) |
|---|---|---:|---:|---:|---:|---:|
| `alloc::alloc` | production | 9 | 36 | 23 | 0 | 23 |
| `alloc::borrow` | production | 14 | 8 | 6 | 0 | 6 |
| `alloc::boxed` | production | 38 | 55 | 17 | 2 | 15 |
| `alloc::collections` | production | 38 | 197 | 155 | 36 | 119 |
| `alloc::collections::btree_map` | production | 13 | 85 | 49 | 11 | 38 |
| `alloc::collections::btree_set` | production | 3 | 70 | 27 | 9 | 18 |
| `alloc::collections::linked_list` | production | 1 | 60 | 20 | 0 | 20 |
| `alloc::collections::vec_deque` | production | 6 | 70 | 54 | 16 | 38 |
| `alloc::ffi` | production | 6 | 19 | 19 | 0 | 19 |
| `alloc::fmt` | production | 3 | 121 | 90 | 0 | 90 |
| `alloc::rc` | production | 7 | 68 | 31 | 3 | 28 |
| `alloc::string` | production | 75 | 56 | 47 | 3 | 44 |
| `alloc::sync` | production | 15 | 71 | 31 | 1 | 30 |
| `alloc::vec` | production | 121 | 77 | 49 | 21 | 30 |
| `core::alloc` | production | 9 | 31 | 18 | 0 | 18 |
| `core::arch` | production | 41 | 1 | 0 | 0 | 0 |
| `core::arch::x86` | test/benchmark only | 1 | 6144 | 6080 | 0 | 6080 |
| `core::array` | production | 3 | 23 | 12 | 1 | 11 |
| `core::cell` | production | 16 | 70 | 51 | 0 | 51 |
| `core::cmp` | production | 35 | 29 | 26 | 11 | 15 |
| `core::convert` | production | 19 | 12 | 7 | 4 | 3 |
| `core::error` | production | 2 | 12 | 3 | 0 | 3 |
| `core::f32::consts` | production | 11 | 0 | 0 | 0 | 0 |
| `core::f64::consts` | production | 12 | 0 | 0 | 0 | 0 |
| `core::ffi` | production | 79 | 14 | 10 | 0 | 10 |
| `core::fmt` | production | 97 | 121 | 90 | 0 | 90 |
| `core::hint` | production | 23 | 14 | 6 | 1 | 5 |
| `core::intrinsics` | production | 3 | 231 | 4 | 2 | 4 |
| `core::marker` | production | 3 | 8 | 0 | 0 | 0 |
| `core::mem` | production | 270 | 63 | 32 | 12 | 20 |
| `core::ops` | production | 15 | 70 | 52 | 13 | 39 |
| `core::panic` | production | 2 | 11 | 9 | 0 | 9 |
| `core::pin` | production | 5 | 23 | 16 | 0 | 16 |
| `core::prelude::v1` | production | 1 | 210 | 175 | 56 | 119 |
| `core::ptr` | production | 191 | 175 | 121 | 2 | 119 |
| `core::result` | production | 2 | 38 | 36 | 10 | 26 |
| `core::slice` | production | 51 | 174 | 132 | 13 | 120 |
| `core::str` | production | 20 | 106 | 86 | 9 | 77 |
| `core::sync::atomic` | production | 76 | 331 | 329 | 150 | 179 |
| `core::time` | production | 24 | 42 | 36 | 0 | 36 |
| `std::alloc` | production | 1 | 38 | 23 | 0 | 23 |
| `std::borrow` | production | 1 | 8 | 6 | 0 | 6 |
| `std::cell` | production | 3 | 70 | 51 | 0 | 51 |
| `std::cmp` | production | 1 | 29 | 26 | 11 | 15 |
| `std::collections` | production | 21 | 272 | 218 | 61 | 157 |
| `std::env` | production | 85 | 15 | 15 | 0 | 15 |
| `std::error` | production | 3 | 15 | 3 | 0 | 3 |
| `std::ffi` | production | 20 | 71 | 62 | 0 | 62 |
| `std::fmt` | production | 8 | 121 | 90 | 0 | 90 |
| `std::fs` | production | 85 | 76 | 68 | 0 | 68 |
| `std::future` | production | 3 | 8 | 6 | 0 | 6 |
| `std::io` | production | 78 | 168 | 129 | 0 | 129 |
| `std::iter` | production | 1 | 119 | 88 | 9 | 79 |
| `std::marker` | production | 1 | 8 | 0 | 0 | 0 |
| `std::mem` | production | 19 | 63 | 32 | 12 | 20 |
| `std::net` | production | 10 | 145 | 116 | 0 | 116 |
| `std::ops` | production | 1 | 70 | 52 | 13 | 39 |
| `std::os::fd` | production | 2 | 7 | 7 | 0 | 7 |
| `std::os::unix::ffi` | production | 1 | 4 | 4 | 0 | 4 |
| `std::os::unix::fs` | production | 5 | 42 | 36 | 0 | 36 |
| `std::os::unix::io` | production | 4 | 10 | 7 | 0 | 7 |
| `std::os::unix::net` | production | 1 | 73 | 45 | 0 | 45 |
| `std::os::windows::fs` | production | 3 | 28 | 17 | 0 | 17 |
| `std::os::windows::io` | production | 2 | 16 | 16 | 0 | 16 |
| `std::os::windows::prelude` | production | 1 | 34 | 29 | 0 | 29 |
| `std::panic` | production | 1 | 23 | 16 | 0 | 16 |
| `std::path` | production | 91 | 76 | 66 | 0 | 66 |
| `std::pin` | production | 3 | 23 | 16 | 0 | 16 |
| `std::process` | production | 25 | 42 | 32 | 0 | 32 |
| `std::ptr` | production | 12 | 175 | 121 | 2 | 119 |
| `std::rc` | production | 2 | 68 | 31 | 3 | 28 |
| `std::result` | production | 4 | 38 | 36 | 10 | 26 |
| `std::slice` | production | 5 | 173 | 132 | 13 | 120 |
| `std::str` | production | 7 | 105 | 87 | 9 | 78 |
| `std::string` | production | 13 | 56 | 47 | 3 | 44 |
| `std::sync` | production | 35 | 236 | 156 | 1 | 155 |
| `std::sync::atomic` | production | 12 | 331 | 329 | 150 | 179 |
| `std::sync::mpsc` | production | 2 | 13 | 10 | 0 | 10 |
| `std::thread` | production | 10 | 81 | 72 | 0 | 72 |
| `std::time` | production | 32 | 58 | 49 | 0 | 49 |
| `std::vec` | production | 64 | 77 | 49 | 21 | 30 |

## Important limitations

- This is a source-wide cfg union, not one concrete Nanvix target build. Unix, Windows, kernel, user, and tool code are all included.
- Module-complete counting intentionally includes APIs that Nanvix does not call directly. The experiment asks whether every API in a used module already has a vstd contract.
- tree-sitter cannot resolve the receiver type of an arbitrary instance method call. Explicit imports, aliases, associated calls, and qualified paths still provide module evidence.
- vstd operator/conversion repetition macros are not fully expanded; their public trait methods are already represented by external trait specifications, so this does not remove those API paths from coverage.
- Type aliases that do not exactly match one rustdoc inherent impl are conservatively propagated and marked by `alias_approximate=true` in the detailed CSV.
- Many uncovered APIs are I/O, OS, formatting, synchronization, or runtime effects. They should be semantically triaged before treating them as ordinary postcondition-generation targets.

## Artifacts

- `results/modules.csv`: complete module list and per-module coverage.
- `results/complete_modules.csv`: concise module list using the report column order.
- `results/usage_evidence.csv`: Nanvix source evidence for each module.
- `results/rust_exec_apis.csv`: every module-listed Rust exec API.
- `results/vstd_contracts.csv`: extracted vstd Rust API contracts.
- `results/coverage.csv`: path-level API-to-contract match.
- `results/uncovered_production_apis.csv`: deduplicated production gaps.
- `results/uncovered_production_stable_apis.csv`: stable production gap list recommended for semantic triage.
- `results/uncovered_all_apis.csv`: all-source gaps including tests.
- `results/summary.json` and `results/metadata.json`: aggregate counts and exact source revisions.

## Reproduce

The source checkouts and rustdoc JSON already exist in this workspace. To rerun the analysis:

```bash
cd /home/chentianyu/nanvix-rust-std-spec-survey
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python survey.py
```

The source snapshots were created with:

```bash
git clone git@github.com:nanvix/nanvix.git nanvix
git -C nanvix checkout --detach bac7075214a385b0088145eb0738cc0c4f121feb
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/rust-lang/rust.git rust
git -C rust fetch --depth 1 origin 14cae681329a63c622a6e1fbe1d30f9374bc51d8
git -C rust sparse-checkout init --cone
git -C rust sparse-checkout set library
git -C rust checkout --detach 14cae681329a63c622a6e1fbe1d30f9374bc51d8
git -C rust submodule update --init --depth 1 library/backtrace
git clone --filter=blob:none --sparse https://github.com/verus-lang/verus.git verus
git -C verus sparse-checkout set source/vstd
git -C verus checkout --detach 1beb0fad337b8f8a224cf8684162cb02d0c2fc01
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install tree-sitter-rust
```

To regenerate the macro-expanded Rust API JSON:

```bash
cd rust/library
for crate in core alloc std; do
  CARGO_TARGET_DIR=../../rustdoc-target RUSTC_BOOTSTRAP=1 \
    cargo +nightly-2026-07-09 rustdoc -p "$crate" --lib -- \
    -Z unstable-options --output-format json
done
mkdir -p ../../rustdoc-json
cp ../../rustdoc-target/doc/{core,alloc,std}.json ../../rustdoc-json/
```
