from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
from pathlib import Path
from typing import Any

from tools import build_specification
from tools import check_implementation_proofs as checker
from tools import check_specification
from tools import proof_templates_cmp as templates
from tools.proof_template_common import ProofTemplate

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
GENERATED = ROOT / "specs" / "generated_cmp_specs.rs"

DEFAULT_VERUS = (
    ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
)
DEFAULT_Z3 = ROOT.parent / "verus" / "source" / "z3"
VERUS_AVAILABLE = DEFAULT_VERUS.is_file() and DEFAULT_Z3.is_file()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structural analysis of the rendered proof text.
#
# These helpers exist so the passthrough guard below is decided by the
# *declared contract* of every `external_body` helper `implementation_target`
# actually calls, and never by the helper's body text: a helper whose
# `requires`/`ensures` are alpha-identical to `implementation_target`'s is a
# whole-target passthrough no matter what its body says, and an
# `implementation_target` whose entire body is one call to such a helper is a
# passthrough no matter how the helper is named.
# ---------------------------------------------------------------------------

_FN_HEADER_RE = re.compile(
    r"(?m)^(?P<attrs>(?:#\[[^\n]*\]\n)*)"
    r"(?:pub(?:\([^)]*\))?\s+)?"
    r"(?:unsafe\s+)?(?:broadcast\s+)?(?:(?:open|closed)\s+)?"
    r"(?:(?:spec|proof|exec)\s+)?"
    r"fn\s+(?P<name>[A-Za-z0-9_]+)"
)

_EXTERNAL_BODY_RE = re.compile(r"#\[\s*verifier\s*::\s*external_body\s*\]")


def _balanced(text: str, start: int, opener: str, closer: str) -> int:
    """Return the index just past the balanced group starting at ``start``.

    ``->`` is skipped so a `>` that belongs to a return-type arrow inside a
    generic parameter list (`F: FnMut(&T) -> K`) does not close an angle
    group.
    """

    assert text[start] == opener
    depth = 0
    index = start
    while index < len(text):
        if text.startswith("->", index):
            index += 2
            continue
        character = text[index]
        if character == opener:
            depth += 1
        elif character == closer:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise AssertionError(f"unbalanced {opener!r} group at {start}")


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    index = 0
    while index < len(text):
        if text.startswith("->", index):
            current.append("->")
            index += 2
            continue
        character = text[index]
        if character in "(<[":
            depth += 1
        elif character in ")>]":
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
        index += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [part.strip() for part in parts if part.strip()]


def _clause_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"requires": [], "ensures": []}
    current: str | None = None
    buffer: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped in ("requires", "ensures"):
            if buffer and current is not None:
                sections[current].append(" ".join(buffer))
                buffer = []
            current = stripped
            continue
        head = stripped.split(None, 1)
        if head[0] in ("requires", "ensures"):
            if buffer and current is not None:
                sections[current].append(" ".join(buffer))
                buffer = []
            current = head[0]
            if len(head) == 1:
                continue
            stripped = head[1]
        if current is None:
            continue
        buffer.append(stripped)
        if stripped.endswith(","):
            sections[current].append(" ".join(buffer))
            buffer = []
    if buffer and current is not None:
        sections[current].append(" ".join(buffer))
    return sections


class _FunctionContract:
    """The declared contract of one rendered Verus function."""

    def __init__(self, name: str, attributes: str, declaration: str, body: str):
        self.name = name
        self.attributes = attributes
        self.declaration = declaration
        self.body = body
        self.external_body = bool(_EXTERNAL_BODY_RE.search(attributes))

        index = 0
        while index < len(declaration) and declaration[index].isspace():
            index += 1
        generics = ""
        if index < len(declaration) and declaration[index] == "<":
            end = _balanced(declaration, index, "<", ">")
            generics = declaration[index + 1:end - 1]
            index = end
        while index < len(declaration) and declaration[index].isspace():
            index += 1
        assert declaration[index] == "(", declaration
        end = _balanced(declaration, index, "(", ")")
        parameters = declaration[index + 1:end - 1]
        rest = declaration[end:]

        self.generic_names = [
            item.split(":", 1)[0].strip().removeprefix("const ").strip()
            for item in _split_top_level(generics)
            if not item.strip().startswith("'")
        ]
        self.lifetime_names = [
            item.split(":", 1)[0].strip().lstrip("'")
            for item in _split_top_level(generics)
            if item.strip().startswith("'")
        ]
        self.parameter_names = [
            item.split(":", 1)[0].strip()
            for item in _split_top_level(parameters)
            if ":" in item
        ]
        binder = re.search(r"->\s*\(\s*([A-Za-z0-9_]+)\s*:", rest)
        self.result_binder = binder.group(1) if binder else None
        self.clauses = _clause_sections(rest)

    def normalized_contract(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Alpha-invariant `(requires, ensures)` for this function.

        Parameter names, generic parameter names, lifetimes and the result
        binder are all replaced by positional placeholders, so two functions
        that differ only by renaming compare equal.
        """

        substitutions: list[tuple[re.Pattern[str], str]] = []
        for position, name in enumerate(self.parameter_names):
            substitutions.append(
                (re.compile(rf"(?<!['\w]){re.escape(name)}\b"), f"@p{position}")
            )
        for position, name in enumerate(self.generic_names):
            substitutions.append(
                (re.compile(rf"(?<!['\w]){re.escape(name)}\b"), f"@t{position}")
            )
        for position, name in enumerate(self.lifetime_names):
            substitutions.append(
                (re.compile(rf"'{re.escape(name)}\b"), f"'@l{position}")
            )
        if self.result_binder is not None:
            substitutions.append(
                (
                    re.compile(rf"(?<!['\w]){re.escape(self.result_binder)}\b"),
                    "@ret",
                )
            )

        def normalize(clause: str) -> str:
            for pattern, replacement in substitutions:
                clause = pattern.sub(replacement, clause)
            return re.sub(r"\s+", " ", clause).strip().rstrip(",").strip()

        return (
            tuple(sorted(normalize(clause) for clause in self.clauses["requires"])),
            tuple(sorted(normalize(clause) for clause in self.clauses["ensures"])),
        )


def _parse_functions(text: str) -> dict[str, _FunctionContract]:
    functions: dict[str, _FunctionContract] = {}
    for match in _FN_HEADER_RE.finditer(text):
        name = match.group("name")
        opening = text.find("\n{", match.end())
        if opening < 0:
            continue
        opening += 1
        depth = 0
        closing = None
        for index in range(opening, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    closing = index
                    break
        if closing is None:
            continue
        functions[name] = _FunctionContract(
            name,
            match.group("attrs"),
            text[match.end():opening],
            text[opening + 1:closing],
        )
    return functions


def _strip_comments(body: str) -> str:
    return "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("//")
    )


def _called_names(body: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:::\s*<[^;]*?>\s*)?\(",
            _strip_comments(body),
        )
    }


def _called_external_helpers(text: str) -> tuple[dict[str, _FunctionContract], set[str]]:
    functions = _parse_functions(text)
    target = functions.get("implementation_target")
    if target is None:
        return functions, set()
    called = _called_names(target.body)
    return functions, {
        name
        for name, function in functions.items()
        if function.external_body and name != "implementation_target" and name in called
    }


def _single_call_passthrough(text: str) -> str | None:
    """Return the helper name when the whole body is one call to it."""

    functions, called = _called_external_helpers(text)
    target = functions.get("implementation_target")
    if target is None:
        return None
    body = _strip_comments(target.body).strip().rstrip(";").strip()
    for name in called:
        if re.fullmatch(
            rf"{re.escape(name)}\s*(?:::\s*<[^>]*>\s*)?\([\s\S]*\)", body
        ):
            return name
    return None


def _passthrough_helpers(text: str) -> list[str]:
    """Helpers whose declared contract is alpha-identical to the target's."""

    functions, called = _called_external_helpers(text)
    target = functions.get("implementation_target")
    if target is None:
        return []
    target_contract = target.normalized_contract()
    return sorted(
        name
        for name in called
        if functions[name].normalized_contract() == target_contract
    )


def _run_verus(path: Path, *, timeout: int = 100) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(DEFAULT_Z3)
    return subprocess.run(
        [str(DEFAULT_VERUS), str(path), "--crate-type=lib"],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
    )


class ProofTemplatesCmpOwnershipTests(unittest.TestCase):
    """`supports` owns the 73 accepted generated core/src/cmp.rs rows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _load(INVENTORY)["rows"]
        cls.rows_by_id = {row["row_id"]: row for row in cls.rows}
        cls.accepted_disposition_by_id = {
            row["row_id"]: row["disposition"]
            for row in _load(build_specification.CATALOG)["rows"]
        }

    def test_row_family_table_has_exactly_73_entries(self) -> None:
        self.assertEqual(len(templates.ROW_FAMILY), 73)
        self.assertEqual(
            len(templates.ROW_FAMILY),
            len(set(templates.ROW_FAMILY)),
        )

    def test_owned_rows_are_exactly_the_generated_core_cmp_rs_rows(self) -> None:
        expected = {
            row["row_id"]
            for row in self.rows
            if self.accepted_disposition_by_id[row["row_id"]] == "generated"
            and row["source_file"] == "core/src/cmp.rs"
        }
        self.assertEqual(set(templates.ROW_FAMILY), expected)

    def test_supports_accepts_every_owned_row_under_its_assigned_family(self) -> None:
        for row_id, family in templates.ROW_FAMILY.items():
            with self.subTest(row_id=row_id):
                row = self.rows_by_id[row_id]
                self.assertTrue(templates.supports(row, family))

    def test_supports_rejects_wrong_family_for_owned_rows(self) -> None:
        for row_id, family in templates.ROW_FAMILY.items():
            with self.subTest(row_id=row_id):
                row = self.rows_by_id[row_id]
                self.assertFalse(templates.supports(row, family + "_not_owned"))
                self.assertFalse(templates.supports(row, "unrelated_family"))

    def test_supports_rejects_non_owned_rows_under_any_family(self) -> None:
        non_owned = [
            row
            for row in self.rows
            if row["row_id"] not in templates.ROW_FAMILY
        ]
        self.assertGreater(len(non_owned), 0)
        for row in non_owned:
            with self.subTest(row_id=row["row_id"]):
                for family in set(templates.ROW_FAMILY.values()):
                    self.assertFalse(templates.supports(row, family))

    def test_supports_rejects_malformed_rows(self) -> None:
        self.assertFalse(templates.supports({}, "ordering_value"))
        self.assertFalse(templates.supports(None, "ordering_value"))  # type: ignore[arg-type]
        sample_id = next(iter(templates.ROW_FAMILY))
        sample = dict(self.rows_by_id[sample_id])
        sample["disposition"] = "exact_vstd"
        self.assertFalse(templates.supports(sample, templates.ROW_FAMILY[sample_id]))
        sample = dict(self.rows_by_id[sample_id])
        sample["source_file"] = "core/src/tuple.rs"
        self.assertFalse(templates.supports(sample, templates.ROW_FAMILY[sample_id]))


class ProofTemplatesCmpMutationCoverageTests(unittest.TestCase):
    """The mutation plan assigned to each owned family must collectively
    cover forwarding, callback_order_state, branch_reversal,
    equality_ordering_distinction, and panic_domain -- and no other label."""

    def test_family_mutation_categories_cover_required_five(self) -> None:
        self.assertEqual(
            templates.REQUIRED_MUTATION_CATEGORIES,
            frozenset(
                {
                    "forwarding",
                    "callback_order_state",
                    "branch_reversal",
                    "equality_ordering_distinction",
                    "panic_domain",
                }
            ),
        )

    def test_every_family_has_an_assigned_mutation_category(self) -> None:
        families = set(templates.ROW_FAMILY.values())
        self.assertEqual(families, set(templates._FAMILY_MUTATION_CATEGORY))
        for family, category in templates._FAMILY_MUTATION_CATEGORY.items():
            with self.subTest(family=family):
                self.assertIn(category, templates.REQUIRED_MUTATION_CATEGORIES)


class ProofTemplatesCmpRenderTests(unittest.TestCase):
    """Render every owned row and check the artifact-level anchors that the
    (separately owned) implementation-proof checker enforces: a verified,
    non-external `implementation_target`; a `completeness_theorem` that
    compares two accepted outcomes and proves exact equality; source-shape
    tokens actually present in the implementation text; and boundaries that
    never claim to summarise the whole target outcome."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {row["row_id"]: row for row in _load(INVENTORY)["rows"]}
        cls.contract_blocks = check_specification.contract_blocks(
            GENERATED.read_text(encoding="utf-8")
        )
        cls.rendered: dict[str, ProofTemplate] = {}
        for row_id, family in templates.ROW_FAMILY.items():
            block_family, block_text = cls.contract_blocks[row_id]
            assert block_family == family, (row_id, block_family, family)
            cls.rendered[row_id] = templates.render(
                cls.rows[row_id], family, block_text
            )

    def test_every_owned_row_is_bound_to_its_real_accepted_contract_text(self) -> None:
        # Cross-check: the family this module assigns to every owned row
        # matches the family independently recorded by the accepted,
        # reviewed specification for that same row.
        self.assertEqual(len(self.contract_blocks), 196)
        for row_id, family in templates.ROW_FAMILY.items():
            with self.subTest(row_id=row_id):
                block_family, _ = self.contract_blocks[row_id]
                self.assertEqual(block_family, family)

    def test_render_rejects_a_row_it_does_not_own(self) -> None:
        foreign_row = next(
            row
            for row in _load(INVENTORY)["rows"]
            if row["row_id"] not in templates.ROW_FAMILY
        )
        with self.assertRaises(ValueError):
            templates.render(foreign_row, "ordering_value", "some text")

    def test_render_rejects_empty_accepted_contract_text(self) -> None:
        row_id = "rustdoc-10786-10785"
        row = self.rows[row_id]
        with self.assertRaises(ValueError):
            templates.render(row, "ordering_value", "")
        with self.assertRaises(ValueError):
            templates.render(row, "ordering_value", "   \n  ")

    def test_render_rejects_accepted_contract_text_unbound_to_the_row(self) -> None:
        row_id = "rustdoc-10786-10785"
        row = self.rows[row_id]
        with self.assertRaises(ValueError):
            templates.render(row, "ordering_value", "totally unrelated text")

    def test_implementation_target_present_verified_and_non_vacuous(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                text = template.implementation_proof
                externals = checker.external_functions(text)
                self.assertNotIn("implementation_target", externals)
                body = checker.function_body(text, "implementation_target")
                self.assertIsNotNone(body)
                assert body is not None
                self.assertTrue(body.strip())
                for forbidden in (
                    "unimplemented!()",
                    "todo!()",
                    "loop {}",
                    "assume(",
                    "admit(",
                ):
                    self.assertNotIn(forbidden, body)
                self.assertNotRegex(text, r"\b(?:assume|admit)\s*!?\(")

    def test_completeness_theorem_compares_two_accepted_outcomes(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                text = template.completeness_proof
                externals = checker.external_functions(text)
                self.assertNotIn("completeness_theorem", externals)
                declaration = checker.function_declaration(
                    text, "completeness_theorem"
                )
                self.assertIsNotNone(declaration)
                assert declaration is not None
                self.assertGreaterEqual(
                    declaration.count("accepted_contract("), 2
                )
                self.assertRegex(
                    declaration,
                    r"ensures[\s\S]*\bresult1\s*==\s*result2\b",
                )
                self.assertNotRegex(text, r"\b(?:assume|admit)\s*!?\(")

    def test_source_shape_tokens_are_literally_present_in_implementation(
        self,
    ) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertTrue(template.source_shape_tokens)
                for token in template.source_shape_tokens:
                    self.assertIn(token, template.implementation_proof)

    def test_boundaries_never_summarise_the_whole_target_outcome(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                for boundary in template.boundaries:
                    self.assertIs(boundary["whole_target_outcome"], False)
                    self.assertTrue(boundary.get("literal_external_body"))
                    self.assertIsInstance(boundary["function"], str)
                    self.assertTrue(boundary["function"])

    def test_boundary_functions_match_declared_external_body_helpers(self) -> None:
        # Every external_body helper other than implementation_target /
        # completeness_theorem must be named by exactly one boundary, and no
        # boundary may name a helper that is not actually external_body.
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                helpers = sorted(
                    {
                        *(
                            name
                            for name in checker.external_functions(
                                template.implementation_proof
                            )
                            if name != "implementation_target"
                        ),
                        *(
                            name
                            for name in checker.external_functions(
                                template.completeness_proof
                            )
                            if name != "completeness_theorem"
                        ),
                    }
                )
                boundary_names = sorted(
                    boundary["function"] for boundary in template.boundaries
                )
                self.assertEqual(helpers, boundary_names)

    def test_mutation_fragment_is_a_unique_anchor_in_its_own_proof_text(
        self,
    ) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertEqual(
                    template.implementation_proof.count(
                        template.implementation_mutation["fragment"]
                    ),
                    1,
                )
                self.assertEqual(
                    template.completeness_proof.count(
                        template.completeness_mutation["fragment"]
                    ),
                    1,
                )
                self.assertNotEqual(
                    template.implementation_mutation["fragment"],
                    template.implementation_mutation["replacement"],
                )
                self.assertNotEqual(
                    template.completeness_mutation["fragment"],
                    template.completeness_mutation["replacement"],
                )

    def test_mutation_categories_are_drawn_from_the_required_five(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                family = templates.ROW_FAMILY[row_id]
                expected_category = templates._FAMILY_MUTATION_CATEGORY[family]
                self.assertEqual(
                    template.implementation_mutation["category"],
                    expected_category,
                )
                self.assertEqual(
                    template.completeness_mutation["category"],
                    expected_category,
                )
                self.assertIn(
                    expected_category, templates.REQUIRED_MUTATION_CATEGORIES
                )

    def test_mutations_collectively_cover_every_required_category(self) -> None:
        implementation_categories = {
            template.implementation_mutation["category"]
            for template in self.rendered.values()
        }
        completeness_categories = {
            template.completeness_mutation["category"]
            for template in self.rendered.values()
        }
        self.assertEqual(
            implementation_categories, templates.REQUIRED_MUTATION_CATEGORIES
        )
        self.assertEqual(
            completeness_categories, templates.REQUIRED_MUTATION_CATEGORIES
        )

    def test_all_fifteen_clamp_identities_have_total_outcome_mutations(
        self,
    ) -> None:
        clamp_rows = {
            row_id
            for row_id, row in self.rows.items()
            if row["method_name"] == "clamp"
        }
        self.assertEqual(len(clamp_rows), 15)
        self.assertEqual(clamp_rows, clamp_rows & set(self.rendered))
        for row_id in sorted(clamp_rows):
            template = self.rendered[row_id]
            with self.subTest(row_id=row_id):
                self.assertEqual(
                    template.implementation_mutation["category"],
                    "panic_domain",
                )
                self.assertEqual(
                    template.completeness_mutation["category"],
                    "panic_domain",
                )
                self.assertIn(
                    "CmpCallOutcome::Panicked",
                    template.implementation_proof,
                )
                self.assertIn(
                    "CmpCallOutcome::Returned",
                    template.implementation_proof,
                )
                self.assertNotIn(
                    "min.partial_cmp_spec(&max) matches "
                    "Some(Ordering::Less | Ordering::Equal),",
                    template.implementation_proof,
                )

    def test_no_external_theorem_assume_or_admit_anywhere(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                for text in (
                    template.implementation_proof,
                    template.completeness_proof,
                ):
                    self.assertNotIn("assume(", text)
                    self.assertNotIn("admit(", text)
                    self.assertNotIn("#[verifier::external_theorem]", text)


# A frozen copy of the whole-target `external_body` passthrough shapes that
# canonical proof review rejected. They are kept literally (rather than read
# back from `proof_harnesses/`, which the parent regenerates) so the detector
# below is pinned against the exact patterns it has to keep out, including the
# case where the helper body is the honest delegation and only the *contract*
# is a passthrough.
_REJECTED_REBORROW_PASSTHROUGH = """\
#![feature(sized_hierarchy)]
#![crate_type = "lib"]
use vstd::prelude::*;
use core::marker::PointeeSized;

verus! {

pub uninterp spec fn cmp_reborrow_forwarding_boundary<'outer, 'inner, X: PointeeSized>(
    value: &'outer &'inner mut X,
) -> &'outer X;

pub open spec fn accepted_contract<A: PointeeSized + PartialEq<B>, B: PointeeSized>(
    left_value: &A,
    right_value: &B,
    result: bool,
) -> bool {
    call_ensures(<A as PartialEq<B>>::eq, (left_value, right_value), result)
}

#[verifier::external_body]
fn cmp_reborrow_forwarding_eq<A: PointeeSized + PartialEq<B>, B: PointeeSized>(
    left: &&mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        accepted_contract(cmp_reborrow_forwarding_boundary(left), cmp_reborrow_forwarding_boundary(right), result),
{
    PartialEq::eq(&**left, &**right)
}

pub fn implementation_target<A: PointeeSized + PartialEq<B>, B: PointeeSized>(
    left: &&mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        accepted_contract(cmp_reborrow_forwarding_boundary(left), cmp_reborrow_forwarding_boundary(right), result),
{
    cmp_reborrow_forwarding_eq(left, right)
}

}
"""

# Same passthrough, but with every helper identifier renamed and the helper
# body replaced by unrelated text: the guard must still reject it.
_REJECTED_REBORROW_PASSTHROUGH_RENAMED = (
    _REJECTED_REBORROW_PASSTHROUGH.replace(
        "cmp_reborrow_forwarding_eq", "honest_looking_source_delegate"
    )
    .replace("left: &&mut A,\n    right: &&mut B,\n) -> (result: bool)\n    ensures\n        accepted_contract(cmp_reborrow_forwarding_boundary(left), cmp_reborrow_forwarding_boundary(right), result),\n{\n    PartialEq::eq(&**left, &**right)\n}",
             "lhs: &&mut A,\n    rhs: &&mut B,\n) -> (outcome: bool)\n    ensures\n        accepted_contract(cmp_reborrow_forwarding_boundary(lhs), cmp_reborrow_forwarding_boundary(rhs), outcome),\n{\n    // deliberately unrelated body text\n    let a = &**lhs; let b = &**rhs; PartialEq::eq(a, b)\n}")
)

_REJECTED_KEY_CALLBACK_PASSTHROUGH = """\
#![crate_type = "lib"]
use vstd::prelude::*;

verus! {

pub uninterp spec fn cmp_fn_mut_state_transition<T, F: FnMut(&T) -> K, K>(
    before: F,
    argument: &T,
    output: K,
    after: F,
) -> bool;

pub open spec fn accepted_contract<T, F: FnMut(&T) -> K, K: Ord>(
    v1: T,
    v2: T,
    callback: F,
    result: T,
) -> bool {
    true
}

#[verifier::external_body]
fn key_callback_order_effect<T, F: FnMut(&T) -> K, K: Ord>(v1: T, v2: T, callback: F) -> (result: T)
    requires
        callback.requires((&v2,)),
        forall|key2: K, callback_after_v2: F|
            cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2)
                ==> callback_after_v2.requires((&v1,)),
    ensures
        accepted_contract(v1, v2, callback, result),
{
    let mut callback = callback;
    let key2 = callback(&v2);
    let key1 = callback(&v1);
    if key2 < key1 { v2 } else { v1 }
}

pub fn implementation_target<T, F: FnMut(&T) -> K, K: Ord>(v1: T, v2: T, callback: F) -> (result: T)
    requires
        callback.requires((&v2,)),
        forall|key2: K, callback_after_v2: F|
            cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2)
                ==> callback_after_v2.requires((&v1,)),
    ensures
        accepted_contract(v1, v2, callback, result),
{
    key_callback_order_effect(v1, v2, callback)
}

}
"""

_REJECTED_FORMATTER_PASSTHROUGH = """\
#![crate_type = "lib"]
use vstd::prelude::*;
use core::cmp::Ordering;

verus! {

pub uninterp spec fn cmp_ordering_debug_effect<'a>(
    value: Ordering,
    before: core::fmt::Formatter<'a>,
    after: core::fmt::Formatter<'a>,
    result: core::fmt::Result,
) -> bool;

pub open spec fn accepted_contract<'a>(
    value: Ordering,
    before: core::fmt::Formatter<'a>,
    after: core::fmt::Formatter<'a>,
    result: core::fmt::Result,
) -> bool {
    cmp_ordering_debug_effect(value, before, after, result)
}

#[verifier::external_body]
fn ordering_debug_effect(value: &Ordering, formatter: &mut core::fmt::Formatter<'_>) -> (result: core::fmt::Result)
    ensures
        accepted_contract(*value, *old(formatter), *final(formatter), result),
{
    core::fmt::Debug::fmt(value, formatter)
}

pub fn implementation_target(value: &Ordering, formatter: &mut core::fmt::Formatter<'_>) -> (result: core::fmt::Result)
    ensures
        accepted_contract(*value, *old(formatter), *final(formatter), result),
{
    ordering_debug_effect(value, formatter)
}

}
"""


class ProofTemplatesCmpPassthroughDetectorTests(unittest.TestCase):
    """The passthrough detector itself must be sound on known-bad shapes.

    Every fixture below is a whole-target `external_body` passthrough of the
    kind canonical proof review rejected. The detector has to flag them from
    the *declared contracts* alone -- helper renaming and arbitrary helper body
    text must not hide them.
    """

    _REJECTED = {
        "reborrow_forwarding": (
            _REJECTED_REBORROW_PASSTHROUGH,
            "cmp_reborrow_forwarding_eq",
        ),
        "reborrow_forwarding_renamed": (
            _REJECTED_REBORROW_PASSTHROUGH_RENAMED,
            "honest_looking_source_delegate",
        ),
        "key_callback_order": (
            _REJECTED_KEY_CALLBACK_PASSTHROUGH,
            "key_callback_order_effect",
        ),
        "ordering_debug": (
            _REJECTED_FORMATTER_PASSTHROUGH,
            "ordering_debug_effect",
        ),
    }

    def test_rejected_fixtures_expose_their_called_external_helper(self) -> None:
        for label, (text, helper) in self._REJECTED.items():
            with self.subTest(label=label):
                _, called = _called_external_helpers(text)
                self.assertEqual(called, {helper})

    def test_rejected_fixtures_are_flagged_as_identical_contract_passthroughs(
        self,
    ) -> None:
        for label, (text, helper) in self._REJECTED.items():
            with self.subTest(label=label):
                self.assertEqual(_passthrough_helpers(text), [helper])

    def test_rejected_fixtures_are_flagged_as_single_call_bodies(self) -> None:
        for label, (text, helper) in self._REJECTED.items():
            with self.subTest(label=label):
                self.assertEqual(_single_call_passthrough(text), helper)

    def test_renaming_the_helper_and_its_body_does_not_hide_the_passthrough(
        self,
    ) -> None:
        original, _ = self._REJECTED["reborrow_forwarding"]
        renamed, helper = self._REJECTED["reborrow_forwarding_renamed"]
        # The renamed fixture really is textually different -- including the
        # helper's parameter names, result binder and body.
        self.assertNotIn(helper, original)
        self.assertIn("deliberately unrelated body text", renamed)
        self.assertNotIn("deliberately unrelated body text", original)
        functions = _parse_functions(renamed)
        self.assertNotEqual(
            functions[helper].body, functions["implementation_target"].body
        )
        # ... and is still recognised as the same whole-target passthrough.
        self.assertEqual(_passthrough_helpers(renamed), [helper])


class ProofTemplatesCmpRenderTimeDerivedBoundaryCheckTests(unittest.TestCase):
    """`proof_templates_cmp` must refuse to *record* a narrow boundary until it
    has derived narrowness from the rendered text.

    `whole_target_outcome=False` is a claim, so the module re-derives it: these
    tests drive the module's own render-time check with the rejected shapes and
    require it to raise."""

    def test_render_time_check_accepts_the_real_rendered_families(self) -> None:
        rows = {row["row_id"]: row for row in _load(INVENTORY)["rows"]}
        blocks = check_specification.contract_blocks(
            GENERATED.read_text(encoding="utf-8")
        )
        for row_id, family in templates.ROW_FAMILY.items():
            with self.subTest(row_id=row_id):
                _, block_text = blocks[row_id]
                template = templates.render(rows[row_id], family, block_text)
                templates._assert_boundaries_are_derived_narrow(
                    template.implementation_proof, template.boundaries
                )

    def test_render_time_check_rejects_whole_target_passthroughs(self) -> None:
        cases = (
            (
                "reborrow_forwarding",
                _REJECTED_REBORROW_PASSTHROUGH,
                "cmp_reborrow_forwarding_eq",
            ),
            (
                "reborrow_forwarding_renamed",
                _REJECTED_REBORROW_PASSTHROUGH_RENAMED,
                "honest_looking_source_delegate",
            ),
            (
                "key_callback_order",
                _REJECTED_KEY_CALLBACK_PASSTHROUGH,
                "key_callback_order_effect",
            ),
            (
                "ordering_debug",
                _REJECTED_FORMATTER_PASSTHROUGH,
                "ordering_debug_effect",
            ),
        )
        for label, text, helper in cases:
            with self.subTest(label=label):
                with self.assertRaises(AssertionError):
                    templates._assert_boundaries_are_derived_narrow(
                        text, (templates._boundary(helper, "narrow_claim"),)
                    )

    def test_render_time_check_rejects_an_undeclared_called_helper(self) -> None:
        # Declaring *no* boundary for a helper the target actually calls is
        # just as bad as declaring a whole-target one.
        with self.assertRaises(AssertionError):
            templates._assert_boundaries_are_derived_narrow(
                _REJECTED_REBORROW_PASSTHROUGH, ()
            )

    def test_render_time_check_rejects_a_helper_naming_accepted_contract(
        self,
    ) -> None:
        # Give the helper a genuinely different signature so it is no longer
        # alpha-identical to the target, and make the target body more than one
        # call: naming `accepted_contract` in the helper's own `ensures` must
        # still be rejected on its own.
        text = _REJECTED_FORMATTER_PASSTHROUGH.replace(
            "fn ordering_debug_effect(value: &Ordering, "
            "formatter: &mut core::fmt::Formatter<'_>) "
            "-> (result: core::fmt::Result)\n"
            "    ensures\n"
            "        accepted_contract(*value, *old(formatter), "
            "*final(formatter), result),",
            "fn ordering_debug_effect(value: &Ordering, "
            "formatter: &mut core::fmt::Formatter<'_>, extra: bool) "
            "-> (outcome: core::fmt::Result)\n"
            "    ensures\n"
            "        accepted_contract(*value, *old(formatter), "
            "*final(formatter), outcome),",
        ).replace(
            "{\n    ordering_debug_effect(value, formatter)\n}",
            "{\n    let extra = true;\n    ordering_debug_effect(value, formatter, extra)\n}",
        )
        self.assertIn("extra: bool", text)
        with self.assertRaises(AssertionError):
            templates._assert_boundaries_are_derived_narrow(
                text, (templates._boundary("ordering_debug_effect", "narrow_claim"),)
            )


class ProofTemplatesCmpNoWholeTargetPassthroughTests(unittest.TestCase):
    """No rendered `implementation_target` may hand its whole outcome to an
    `external_body` helper.

    This is decided structurally, from the declared contract of every helper
    the target actually calls, and never from helper body text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {row["row_id"]: row for row in _load(INVENTORY)["rows"]}
        cls.contract_blocks = check_specification.contract_blocks(
            GENERATED.read_text(encoding="utf-8")
        )
        cls.rendered: dict[str, ProofTemplate] = {}
        for row_id, family in templates.ROW_FAMILY.items():
            _, block_text = cls.contract_blocks[row_id]
            cls.rendered[row_id] = templates.render(
                cls.rows[row_id], family, block_text
            )

    def test_implementation_target_is_never_external_body(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                functions = _parse_functions(template.implementation_proof)
                self.assertIn("implementation_target", functions)
                self.assertFalse(
                    functions["implementation_target"].external_body
                )

    def test_called_external_helpers_are_exactly_the_declared_boundaries(
        self,
    ) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                _, called = _called_external_helpers(
                    template.implementation_proof
                )
                declared = {
                    boundary["function"] for boundary in template.boundaries
                }
                # Every helper the target actually calls is a declared, narrow
                # boundary, and no boundary is declared for a helper the target
                # never calls.
                self.assertEqual(called, declared)

    def test_no_called_helper_has_the_targets_requires_and_ensures(
        self,
    ) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertEqual(
                    _passthrough_helpers(template.implementation_proof),
                    [],
                    msg=(
                        "an external_body helper called by "
                        "implementation_target declares the same "
                        "requires/ensures as the target itself"
                    ),
                )

    def test_implementation_target_body_is_never_one_helper_call(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                self.assertIsNone(
                    _single_call_passthrough(template.implementation_proof),
                    msg=(
                        "implementation_target's whole body is a single call "
                        "to an external_body helper"
                    ),
                )

    def test_no_called_helper_mentions_the_accepted_contract(self) -> None:
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                functions, called = _called_external_helpers(
                    template.implementation_proof
                )
                for name in sorted(called):
                    clauses = functions[name].clauses
                    for section in ("requires", "ensures"):
                        for clause in clauses[section]:
                            self.assertNotIn(
                                "accepted_contract(",
                                clause,
                                msg=f"{row_id}: {name} {section} {clause!r}",
                            )

    def test_every_called_helper_contract_is_strictly_smaller(self) -> None:
        # A narrow boundary may not simply restate the target's whole
        # postcondition set: the target must retain at least one ensures
        # conjunct of its own that the helper does not already declare.
        for row_id, template in self.rendered.items():
            with self.subTest(row_id=row_id):
                functions, called = _called_external_helpers(
                    template.implementation_proof
                )
                if not called:
                    continue
                target_ensures = set(
                    functions["implementation_target"].normalized_contract()[1]
                )
                self.assertTrue(target_ensures)
                for name in sorted(called):
                    helper_ensures = set(
                        functions[name].normalized_contract()[1]
                    )
                    self.assertFalse(
                        target_ensures <= helper_ensures,
                        msg=(
                            f"{row_id}: helper {name} already declares every "
                            "postcondition the target has to prove"
                        ),
                    )


@unittest.skipUnless(
    VERUS_AVAILABLE,
    "actual verus/z3 binaries are not present in this environment",
)
class ProofTemplatesCmpActualVerusTests(unittest.TestCase):
    """Run one representative row per proof family through the actual
    (non-`--no-verify`) Verus binary: the baseline implementation and
    completeness proofs must verify, and the row's own implementation and
    completeness mutations -- which must still type-check under
    `--no-verify` -- must be rejected by full verification."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {row["row_id"]: row for row in _load(INVENTORY)["rows"]}
        cls.contract_blocks = check_specification.contract_blocks(
            GENERATED.read_text(encoding="utf-8")
        )
        representative: dict[str, str] = {}
        for row_id, family in templates.ROW_FAMILY.items():
            representative.setdefault(family, row_id)
        cls.representative_row_ids = representative
        cls.tmp_dir = Path(
            os.environ.get("PYTEST_TMP_CMP_PROOF_DIR")
            or str(ROOT / ".pytest_cache" / "proof_templates_cmp_verus")
        )
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def _render(self, row_id: str) -> ProofTemplate:
        family = templates.ROW_FAMILY[row_id]
        block_family, block_text = self.contract_blocks[row_id]
        self.assertEqual(block_family, family)
        return templates.render(self.rows[row_id], family, block_text)

    def _write(self, name: str, text: str) -> Path:
        path = self.tmp_dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_every_family_representative_verifies_with_actual_verus(
        self,
    ) -> None:
        for family, row_id in sorted(self.representative_row_ids.items()):
            with self.subTest(family=family, row_id=row_id):
                template = self._render(row_id)
                impl_path = self._write(
                    f"{family}_implementation_proof.rs",
                    template.implementation_proof,
                )
                comp_path = self._write(
                    f"{family}_completeness_proof.rs",
                    template.completeness_proof,
                )
                impl_result = _run_verus(impl_path)
                self.assertEqual(
                    impl_result.returncode,
                    0,
                    msg=impl_result.stdout + impl_result.stderr,
                )
                self.assertIn(
                    "0 errors",
                    impl_result.stdout + impl_result.stderr,
                )
                comp_result = _run_verus(comp_path)
                self.assertEqual(
                    comp_result.returncode,
                    0,
                    msg=comp_result.stdout + comp_result.stderr,
                )
                self.assertIn(
                    "0 errors",
                    comp_result.stdout + comp_result.stderr,
                )

    def test_every_family_representative_mutation_is_rejected(self) -> None:
        expected_rejection = (
            "postcondition not satisfied",
            "assertion failed",
            "precondition not satisfied",
        )
        for family, row_id in sorted(self.representative_row_ids.items()):
            template = self._render(row_id)
            for proof_kind, base_text, mutation in (
                (
                    "implementation",
                    template.implementation_proof,
                    template.implementation_mutation,
                ),
                (
                    "completeness",
                    template.completeness_proof,
                    template.completeness_mutation,
                ),
            ):
                with self.subTest(family=family, row_id=row_id, proof_kind=proof_kind):
                    self.assertEqual(
                        base_text.count(mutation["fragment"]), 1
                    )
                    mutated_text = base_text.replace(
                        mutation["fragment"], mutation["replacement"], 1
                    )
                    mutated_path = self._write(
                        f"{family}_{proof_kind}_mutated.rs", mutated_text
                    )
                    no_verify = subprocess.run(
                        [
                            str(DEFAULT_VERUS),
                            str(mutated_path),
                            "--crate-type=lib",
                            "--no-verify",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=100,
                        env={
                            **os.environ,
                            "VERUS_Z3_PATH": str(DEFAULT_Z3),
                        },
                    )
                    self.assertEqual(
                        no_verify.returncode,
                        0,
                        msg=(
                            "mutation must still type-check under --no-verify: "
                            + no_verify.stdout
                            + no_verify.stderr
                        ),
                    )
                    actual = _run_verus(mutated_path)
                    self.assertNotEqual(actual.returncode, 0)
                    combined = actual.stdout + actual.stderr
                    self.assertTrue(
                        any(message in combined for message in expected_rejection),
                        msg=combined,
                    )

    def test_key_callback_order_both_row_ids_verify_and_reject_mutations(
        self,
    ) -> None:
        # key_callback_order owns exactly two rows (min_by_key, max_by_key)
        # with opposite v2-vs-v1 selections; the family-representative tests
        # above only exercise one of them with actual Verus, so this checks
        # both key representatives -- and both of their mutations -- directly
        # against actual Verus, guarding the threaded callback_after_v2
        # precondition for both selection directions.
        expected_rejection = (
            "postcondition not satisfied",
            "assertion failed",
            "precondition not satisfied",
        )
        row_ids = ("rustdoc-11631", "rustdoc-11634")
        self.assertEqual(
            {templates.ROW_FAMILY[row_id] for row_id in row_ids},
            {"key_callback_order"},
        )
        for row_id in row_ids:
            with self.subTest(row_id=row_id):
                template = self._render(row_id)
                impl_path = self._write(
                    f"key_callback_order_{row_id}_implementation_proof.rs",
                    template.implementation_proof,
                )
                comp_path = self._write(
                    f"key_callback_order_{row_id}_completeness_proof.rs",
                    template.completeness_proof,
                )
                impl_result = _run_verus(impl_path)
                self.assertEqual(
                    impl_result.returncode,
                    0,
                    msg=impl_result.stdout + impl_result.stderr,
                )
                self.assertIn("0 errors", impl_result.stdout + impl_result.stderr)
                comp_result = _run_verus(comp_path)
                self.assertEqual(
                    comp_result.returncode,
                    0,
                    msg=comp_result.stdout + comp_result.stderr,
                )
                self.assertIn("0 errors", comp_result.stdout + comp_result.stderr)

                for proof_kind, base_text, mutation in (
                    (
                        "implementation",
                        template.implementation_proof,
                        template.implementation_mutation,
                    ),
                    (
                        "completeness",
                        template.completeness_proof,
                        template.completeness_mutation,
                    ),
                ):
                    with self.subTest(row_id=row_id, proof_kind=proof_kind):
                        self.assertEqual(base_text.count(mutation["fragment"]), 1)
                        mutated_text = base_text.replace(
                            mutation["fragment"], mutation["replacement"], 1
                        )
                        mutated_path = self._write(
                            f"key_callback_order_{row_id}_{proof_kind}_mutated.rs",
                            mutated_text,
                        )
                        no_verify = subprocess.run(
                            [
                                str(DEFAULT_VERUS),
                                str(mutated_path),
                                "--crate-type=lib",
                                "--no-verify",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=100,
                            env={
                                **os.environ,
                                "VERUS_Z3_PATH": str(DEFAULT_Z3),
                            },
                        )
                        self.assertEqual(
                            no_verify.returncode,
                            0,
                            msg=(
                                "mutation must still type-check under "
                                "--no-verify: "
                                + no_verify.stdout
                                + no_verify.stderr
                            ),
                        )
                        actual = _run_verus(mutated_path)
                        self.assertNotEqual(actual.returncode, 0)
                        combined = actual.stdout + actual.stderr
                        self.assertTrue(
                            any(
                                message in combined
                                for message in expected_rejection
                            ),
                            msg=combined,
                        )


@unittest.skipUnless(
    VERUS_AVAILABLE,
    "actual verus/z3 binaries are not present in this environment",
)
class ProofTemplatesCmpRepairedRowsActualVerusTests(unittest.TestCase):
    """Actual Verus for every one of the 18 rows canonical proof review
    rejected as whole-target `external_body` passthroughs.

    Each row's implementation and completeness proof must verify, and each
    row's implementation and completeness mutation must still type-check under
    `--no-verify` yet be rejected by full verification. These rows are checked
    individually (not by family representative) because the repair is per-row:
    the reference-forwarding rows differ in which operand is behind a `&mut`,
    and the two key-callback rows differ in their tie selection."""

    # 039-044, 117, 208-212 (mutable reference forwarding),
    # 074/075/077/078 (Ordering + Reverse derived Debug/Hash),
    # 231/234 (min_by_key/max_by_key).
    REPAIRED_ROW_IDS = (
        "rustdoc-10853-10851",
        "rustdoc-10853-10852",
        "rustdoc-10856-10854",
        "rustdoc-10856-10855",
        "rustdoc-10859-10857",
        "rustdoc-10859-10858",
        "rustdoc-11299-11298",
        "rustdoc-11518-11513",
        "rustdoc-11518-11514",
        "rustdoc-11518-11515",
        "rustdoc-11518-11516",
        "rustdoc-11518-11517",
        "rustdoc-11204-11203",
        "rustdoc-11206-11205",
        "rustdoc-11228-11227",
        "rustdoc-11230-11229",
        "rustdoc-11631",
        "rustdoc-11634",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {row["row_id"]: row for row in _load(INVENTORY)["rows"]}
        cls.contract_blocks = check_specification.contract_blocks(
            GENERATED.read_text(encoding="utf-8")
        )
        cls.tmp_dir = Path(
            os.environ.get("PYTEST_TMP_CMP_PROOF_DIR")
            or str(ROOT / ".pytest_cache" / "proof_templates_cmp_verus")
        )
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_repaired_row_set_is_exactly_the_rejected_eighteen(self) -> None:
        self.assertEqual(len(self.REPAIRED_ROW_IDS), 18)
        self.assertEqual(len(set(self.REPAIRED_ROW_IDS)), 18)
        families = {
            templates.ROW_FAMILY[row_id] for row_id in self.REPAIRED_ROW_IDS
        }
        self.assertEqual(
            families,
            {
                "reference_forwarding",
                "ordering_debug",
                "ordering_hash",
                "reverse_debug",
                "reverse_hash",
                "key_callback_order",
            },
        )
        # Every row of each repaired family is covered, not just a sample.
        for family in families:
            self.assertEqual(
                {
                    row_id
                    for row_id, assigned in templates.ROW_FAMILY.items()
                    if assigned == family
                },
                {
                    row_id
                    for row_id in self.REPAIRED_ROW_IDS
                    if templates.ROW_FAMILY[row_id] == family
                },
            )

    def _render(self, row_id: str) -> ProofTemplate:
        family = templates.ROW_FAMILY[row_id]
        block_family, block_text = self.contract_blocks[row_id]
        self.assertEqual(block_family, family)
        return templates.render(self.rows[row_id], family, block_text)

    def _write(self, name: str, text: str) -> Path:
        path = self.tmp_dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_every_repaired_row_verifies_and_rejects_both_mutations(
        self,
    ) -> None:
        expected_rejection = (
            "postcondition not satisfied",
            "assertion failed",
            "precondition not satisfied",
        )
        for row_id in self.REPAIRED_ROW_IDS:
            template = self._render(row_id)
            family = templates.ROW_FAMILY[row_id]
            for proof_kind, base_text, mutation in (
                (
                    "implementation",
                    template.implementation_proof,
                    template.implementation_mutation,
                ),
                (
                    "completeness",
                    template.completeness_proof,
                    template.completeness_mutation,
                ),
            ):
                with self.subTest(
                    row_id=row_id, family=family, proof_kind=proof_kind
                ):
                    base_path = self._write(
                        f"repaired_{row_id}_{proof_kind}.rs", base_text
                    )
                    base_result = _run_verus(base_path)
                    self.assertEqual(
                        base_result.returncode,
                        0,
                        msg=base_result.stdout + base_result.stderr,
                    )
                    self.assertIn(
                        "0 errors", base_result.stdout + base_result.stderr
                    )

                    self.assertEqual(base_text.count(mutation["fragment"]), 1)
                    mutated_text = base_text.replace(
                        mutation["fragment"], mutation["replacement"], 1
                    )
                    mutated_path = self._write(
                        f"repaired_{row_id}_{proof_kind}_mutated.rs",
                        mutated_text,
                    )
                    no_verify = subprocess.run(
                        [
                            str(DEFAULT_VERUS),
                            str(mutated_path),
                            "--crate-type=lib",
                            "--no-verify",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=100,
                        env={**os.environ, "VERUS_Z3_PATH": str(DEFAULT_Z3)},
                    )
                    self.assertEqual(
                        no_verify.returncode,
                        0,
                        msg=(
                            "mutation must still type-check under "
                            "--no-verify: "
                            + no_verify.stdout
                            + no_verify.stderr
                        ),
                    )
                    mutated_result = _run_verus(mutated_path)
                    self.assertNotEqual(mutated_result.returncode, 0)
                    combined = mutated_result.stdout + mutated_result.stderr
                    self.assertTrue(
                        any(
                            message in combined
                            for message in expected_rejection
                        ),
                        msg=combined,
                    )


if __name__ == "__main__":
    unittest.main()
