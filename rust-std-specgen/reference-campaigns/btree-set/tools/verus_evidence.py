from __future__ import annotations

import re


MUTATION_RESULT = re.compile(
    r"verification results::\s+\d+ verified, 1 errors"
)
MUTATION_REJECTION_MARKERS = (
    ("postcondition", "postcondition not satisfied"),
    ("precondition", "precondition not satisfied"),
    ("loop_invariant", "invariant not satisfied at end of loop body"),
    ("assertion", "assertion failed"),
)
ASSOCIATED_ITEM_AIR_TOKENS = (
    "internal error: generated ill-typed AIR code",
    (
        "use of undeclared function "
        "proj%%core!iter.traits.collect.IntoIterator./Item"
    ),
)
ASSOCIATED_ITEM_AIR_PANIC = re.compile(
    r"thread '(?:rustc|<unnamed>)' \(\d+\) panicked at "
    r"rust_verify/src/verifier\.rs:\d+:\d+:"
)


def mutation_rejection_kind(output: str) -> str | None:
    if MUTATION_RESULT.search(output) is None:
        return None
    for kind, marker in MUTATION_REJECTION_MARKERS:
        if marker in output:
            return kind
    return None


def associated_item_air_limitation_matches(
    returncode: int,
    output: str,
) -> bool:
    return (
        isinstance(returncode, int)
        and not isinstance(returncode, bool)
        and returncode != 0
        and all(token in output for token in ASSOCIATED_ITEM_AIR_TOKENS)
        and ASSOCIATED_ITEM_AIR_PANIC.search(output) is not None
    )
