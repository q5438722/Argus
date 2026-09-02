"""Shared result shape for independently rendered core::cmp proof families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProofTemplate:
    proof_family: str
    accepted_relation_name: str
    implementation_proof: str
    completeness_proof: str
    source_shape_tokens: tuple[str, ...]
    boundaries: tuple[dict[str, Any], ...]
    implementation_mutation: dict[str, str]
    completeness_mutation: dict[str, str]
    implementation_mutations: tuple[dict[str, str], ...] = ()
    completeness_mutations: tuple[dict[str, str], ...] = ()
