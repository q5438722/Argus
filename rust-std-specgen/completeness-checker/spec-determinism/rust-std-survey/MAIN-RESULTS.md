# Verus vstd coverage of Nanvix-used Rust std APIs

## Main result

| Scope | Used modules | Modules with exec APIs | Module-listed API paths | Deduplicated API paths | Covered by vstd | Uncovered | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Production source | 80 | 78 | 5887 | 3553 | 348 | 3205 | 9.79% |
| Production, stable APIs only | 80 | 78 | - | 2464 | 343 | 2121 | 13.92% |
| All tracked source, including tests/benchmarks | 81 | 79 | 12031 | 9697 | 348 | 9349 | 3.59% |

## Complete module list

| Module | Scope | Source files | Exec APIs | Stable APIs | vstd covered (stable) | vstd uncovered (stable) |
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
