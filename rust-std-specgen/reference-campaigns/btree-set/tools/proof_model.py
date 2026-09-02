from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from tools import campaign_model as model


ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS = frozenset(
    {
        "041_BTreeSet_FromIterator_from_iter_2138",
        "048_BTreeSet_Extend_extend_2150",
        "049_BTreeSet_Extend_extend_2153",
    }
)

SELECTED_PUBLIC_DEPENDENCY_METHODS: dict[
    tuple[str, str, str], tuple[tuple[str, str, str], ...]
] = {
    ("BTreeSet", "inherent", "difference"): (
        ("BTreeSet", "inherent", "first"),
        ("BTreeSet", "inherent", "last"),
        ("BTreeSet", "inherent", "len"),
        ("BTreeSet", "inherent", "iter"),
        ("Iter", "Iterator", "next"),
        ("Iter", "DoubleEndedIterator", "next_back"),
    ),
    ("BTreeSet", "inherent", "symmetric_difference"): (
        ("BTreeSet", "inherent", "iter"),
    ),
    ("BTreeSet", "inherent", "intersection"): (
        ("BTreeSet", "inherent", "first"),
        ("BTreeSet", "inherent", "last"),
        ("BTreeSet", "inherent", "len"),
        ("BTreeSet", "inherent", "iter"),
    ),
    ("BTreeSet", "inherent", "union"): (
        ("BTreeSet", "inherent", "iter"),
    ),
    ("BTreeSet", "inherent", "is_disjoint"): (
        ("BTreeSet", "inherent", "intersection"),
        ("Intersection", "Iterator", "next"),
    ),
    ("BTreeSet", "inherent", "is_subset"): (
        ("BTreeSet", "inherent", "first"),
        ("BTreeSet", "inherent", "last"),
        ("BTreeSet", "inherent", "len"),
        ("BTreeSet", "inherent", "iter"),
        ("BTreeSet", "inherent", "contains"),
        ("Iter", "Iterator", "next"),
        ("Iter", "DoubleEndedIterator", "next_back"),
        ("Iter", "ExactSizeIterator", "len"),
    ),
    ("BTreeSet", "inherent", "is_superset"): (
        ("BTreeSet", "inherent", "is_subset"),
    ),
    ("BTreeSet", "inherent", "retain"): (
        ("BTreeSet", "inherent", "extract_if"),
    ),
    ("BTreeSet", "inherent", "is_empty"): (
        ("BTreeSet", "inherent", "len"),
    ),
    ("BTreeSet", "FromIterator", "from_iter"): (
        ("BTreeSet", "inherent", "new"),
    ),
    ("BTreeSet", "From", "from"): (
        ("BTreeSet", "inherent", "new"),
    ),
    ("BTreeSet", "IntoIterator", "into_iter"): (
        ("BTreeSet", "inherent", "iter"),
    ),
    ("BTreeSet", "Extend", "extend"): (
        ("BTreeSet", "inherent", "insert"),
    ),
    ("BTreeSet", "Default", "default"): (
        ("BTreeSet", "inherent", "new"),
    ),
    ("BTreeSet", "Sub", "sub"): (
        ("BTreeSet", "inherent", "difference"),
    ),
    ("BTreeSet", "BitXor", "bitxor"): (
        ("BTreeSet", "inherent", "symmetric_difference"),
    ),
    ("BTreeSet", "BitAnd", "bitand"): (
        ("BTreeSet", "inherent", "intersection"),
    ),
    ("BTreeSet", "BitOr", "bitor"): (
        ("BTreeSet", "inherent", "union"),
    ),
    ("BTreeSet", "Debug", "fmt"): (
        ("BTreeSet", "inherent", "iter"),
    ),
    ("Iter", "Iterator", "last"): (
        ("Iter", "DoubleEndedIterator", "next_back"),
    ),
    ("Iter", "Iterator", "min"): (
        ("Iter", "Iterator", "next"),
    ),
    ("Iter", "Iterator", "max"): (
        ("Iter", "DoubleEndedIterator", "next_back"),
    ),
    ("Range", "Iterator", "last"): (
        ("Range", "DoubleEndedIterator", "next_back"),
    ),
    ("Range", "Iterator", "min"): (
        ("Range", "Iterator", "next"),
    ),
    ("Range", "Iterator", "max"): (
        ("Range", "DoubleEndedIterator", "next_back"),
    ),
    ("Difference", "Iterator", "min"): (
        ("Difference", "Iterator", "next"),
    ),
    ("SymmetricDifference", "Iterator", "min"): (
        ("SymmetricDifference", "Iterator", "next"),
    ),
    ("Intersection", "Iterator", "min"): (
        ("Intersection", "Iterator", "next"),
    ),
    ("Union", "Iterator", "min"): (
        ("Union", "Iterator", "next"),
    ),
}

SELECTED_PUBLIC_DEPENDENCY_OVERRIDES = {
    "049_BTreeSet_Extend_extend_2153": (
        ("BTreeSet", "Extend", "extend"),
    ),
}


def selected_public_dependency_keys(
    row: model.Row,
) -> tuple[tuple[str, str, str], ...]:
    override = SELECTED_PUBLIC_DEPENDENCY_OVERRIDES.get(row.target_id)
    if override is not None:
        return override
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "IntoIterator"
        and "self.iter()" not in row.source_excerpt
    ):
        return ()
    return SELECTED_PUBLIC_DEPENDENCY_METHODS.get(
        (row.owner["name"], row.trait, row.function["name"]),
        (),
    )


def selected_public_dependency_target_ids(
    row: model.Row,
    target_by_key: dict[tuple[str, str, str], str],
) -> list[str]:
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        return ["048_BTreeSet_Extend_extend_2150"]
    return [
        target_by_key[key]
        for key in selected_public_dependency_keys(row)
        if key in target_by_key
    ]


def requires_selected_public_composition(row: model.Row) -> bool:
    return bool(selected_public_dependency_keys(row))


def terminal_override_selected_method(row: model.Row) -> str | None:
    if row.semantic_family != "ordered_iterator_terminal_selection":
        return None
    dependencies = selected_public_dependency_keys(row)
    if len(dependencies) != 1:
        return None
    return dependencies[0][2]


SOURCE_CALL_PATTERN = re.compile(
    r"\b(?P<callee>[A-Za-z_][A-Za-z0-9_]*"
    r"(?:(?:::|\.)[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s*(?:::\s*<[^(){};\n]+>)?\s*\("
)


def source_call_callees(row: model.Row) -> list[str]:
    source = re.sub(
        r"//[^\n]*|/\*.*?\*/",
        "",
        row.source_excerpt,
        flags=re.DOTALL,
    )
    body_start = source.find("{")
    body = source[body_start + 1 :] if body_start >= 0 else source
    return [
        match.group("callee")
        for match in SOURCE_CALL_PATTERN.finditer(body)
        if match.group("callee")
        not in {
            "if",
            "let",
            "match",
            "while",
            "for",
            "loop",
            "return",
        }
    ]


UNION_LEFT_BIASED_NEXT_TARGET = "090_Union_Iterator_next_2383"
SYMMETRIC_DIFFERENCE_NEXT_TARGET = (
    "082_SymmetricDifference_Iterator_next_2327"
)
CORE_OPTION_SOURCE = (
    "provenance/frozen/rust-1.96/library/core/src/option.rs"
)
CORE_OPTION_SOURCE_SHA256 = (
    "b5800ef3c6efda2a7685d66db83833e458025131a0a8fba6c9ddd3c025f1ec90"
)


def union_left_biased_next(row: model.Row) -> bool:
    return row.target_id == UNION_LEFT_BIASED_NEXT_TARGET


def executable_source_call_requirements(
    row: model.Row,
) -> list[dict[str, object]]:
    if union_left_biased_next(row):
        fragments = {
            "nexts": f"{dependency_call_name(row)}(this)",
            "a_next.or": "a_next.or(b_next)",
        }
    elif row.target_id == SYMMETRIC_DIFFERENCE_NEXT_TARGET:
        fragments = {
            "nexts": f"{dependency_call_name(row)}(this)",
            "a_next.and": "a_next.and(b_next)",
            "is_none": "a_next.and(b_next).is_none()",
            "a_next.or": "a_next.or(b_next)",
        }
    else:
        return []
    calls = source_call_callees(row)
    return [
        {
            "callee": callee,
            "source_occurrences": calls.count(callee),
            "required_occurrences": 1,
            "executable_fragment": fragment,
        }
        for callee, fragment in fragments.items()
    ]


def standard_library_assumption_boundaries(
    row: model.Row,
) -> list[dict[str, object]]:
    operations: list[tuple[str, str]] = []
    if row.target_id == SYMMETRIC_DIFFERENCE_NEXT_TARGET:
        operations.append(("Option::and", "1497-1507"))
    if (
        row.target_id == SYMMETRIC_DIFFERENCE_NEXT_TARGET
        or union_left_biased_next(row)
    ):
        operations.append(("Option::or", "1621-1631"))
    return [
        {
            "category": "core_option_combinator_semantics",
            "acceptance": "unaccepted_narrow_dependency",
            "boundary": (
                f"Verus vstd does not specify {operation}; this local binding "
                f"states only Rust's frozen {operation} result"
            ),
            "source": CORE_OPTION_SOURCE,
            "source_sha256": CORE_OPTION_SOURCE_SHA256,
            "source_span": f"{CORE_OPTION_SOURCE}:{source_span}",
            "operation": operation,
            "verifier_allow": "undeclared_external_trait",
            "whole_target_contract": False,
        }
        for operation, source_span in operations
    ]


def selected_dependency_source_fragments(
    row: model.Row,
    dependency: tuple[str, str, str],
) -> list[str]:
    owner, trait, method = dependency
    source = row.source_excerpt
    candidates = [f".{method}(", f"::{method}("]
    if owner == "BTreeSet" and method == "new":
        candidates = ["BTreeSet::new(", "Self::new("]
    elif owner == "BTreeSet" and trait == "Extend":
        candidates = ["self.extend("]
    elif owner == row.owner["name"]:
        candidates.insert(0, f"self.{method}(")
    return [candidate for candidate in candidates if candidate in source]


def source_call_coverage(row: model.Row) -> dict[str, object]:
    selected = selected_public_dependency_keys(row)
    selected_records = []
    missing = []
    selected_methods = {method for _owner, _trait, method in selected}
    for dependency in selected:
        fragments = selected_dependency_source_fragments(row, dependency)
        record = {
            "owner_type": dependency[0],
            "trait": dependency[1],
            "method": dependency[2],
            "source_fragments": fragments,
        }
        selected_records.append(record)
        if not fragments:
            missing.append(record)

    calls = source_call_callees(row)
    classified = []
    for callee in sorted(set(calls)):
        method = re.split(r"::|\.", callee)[-1]
        if method in selected_methods:
            classification = "selected_public_target"
        elif any(
            token in callee
            for token in (
                ".map",
                ".iter",
                "BTreeMap",
                "MergeIter",
                "from_sorted_iter",
                "extract_if_inner",
            )
        ):
            classification = "private_representation_or_map_boundary"
        else:
            classification = "standard_library_or_local_source_step"
        classified.append(
            {
                "callee": callee,
                "occurrences": calls.count(callee),
                "classification": classification,
            }
        )
    executable_requirements = executable_source_call_requirements(row)
    missing_executable = [
        record
        for record in executable_requirements
        if record["source_occurrences"] != record["required_occurrences"]
    ]
    return {
        "source_sha256": row.source_sha256,
        "source_call_count": len(calls),
        "calls": classified,
        "selected_public_dependencies": selected_records,
        "operation_specific_lower": dependency_operation(row),
        "missing_selected_public_calls": missing,
        "executable_body_calls": executable_requirements,
        "missing_executable_body_calls": missing_executable,
        "complete": not missing and not missing_executable,
    }


def retained_source_construct_kinds(row: model.Row) -> list[str]:
    retained: set[str] = set()
    if uses_private_branch(row) or (
        source_owned_adapter_loop(row) and "match " in row.source_excerpt
    ):
        retained.add("match")
    if retains_adapter_source_loop(row):
        retained.add("loop")
    if (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        retained.update(("conditional", "match"))
    if row.semantic_family == "sorted_deduplicating_conversion":
        retained.add("conditional")
    return sorted(retained)


def selected_observer_support_source(row: model.Row) -> str:
    if terminal_override_selected_method(row) is not None:
        return ""
    keys = set(selected_public_dependency_keys(row))
    if ("BTreeSet", "inherent", "is_subset") in keys:
        keys.update(
            SELECTED_PUBLIC_DEPENDENCY_METHODS[
                ("BTreeSet", "inherent", "is_subset")
            ]
        )
    selected = {(owner, trait, method) for owner, trait, method in keys}
    parts: list[str] = []
    if ("BTreeSet", "inherent", "first") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_first<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            project_map_entry(result).is_some()
                <==> wrapped_btree_map_key_sequence(set).len() > 0
        ),
        obeys_cmp::<T>() ==> (
            match project_map_entry(result) {
                Some(item) =>
                    *item == wrapped_btree_map_key_sequence(set)[0],
                None => true,
            }
        ),
{
    loop { }
}

pub fn rust_1_96_selected_first<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: Option<&'a T>)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result.is_some()
                <==> wrapped_btree_map_key_sequence(set).len() > 0
        ),
        obeys_cmp::<T>() ==> (
            match result {
                Some(item) =>
                    *item == wrapped_btree_map_key_sequence(set)[0],
                None => true,
            }
        ),
{
    project_map_entry_exec(rust_1_96_selected_map_first(set))
}
"""
        )
    if ("BTreeSet", "inherent", "last") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_last<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            project_map_entry(result).is_some()
                <==> wrapped_btree_map_key_sequence(set).len() > 0
        ),
        obeys_cmp::<T>() ==> (
            match project_map_entry(result) {
                Some(item) =>
                    *item == wrapped_btree_map_key_sequence(set).last(),
                None => true,
            }
        ),
{
    loop { }
}

pub fn rust_1_96_selected_last<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: Option<&'a T>)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result.is_some()
                <==> wrapped_btree_map_key_sequence(set).len() > 0
        ),
        obeys_cmp::<T>() ==> (
            match result {
                Some(item) =>
                    *item == wrapped_btree_map_key_sequence(set).last(),
                None => true,
            }
        ),
{
    project_map_entry_exec(rust_1_96_selected_map_last(set))
}
"""
        )
    if ("BTreeSet", "inherent", "len") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_len<T, A: Allocator + Clone>(
    set: &BTreeSet<T, A>,
) -> (result: MapLengthResult)
    ensures
        result.value as nat
            == wrapped_btree_map_key_sequence(set).len(),
{
    loop { }
}

pub fn rust_1_96_selected_len<T, A: Allocator + Clone>(
    set: &BTreeSet<T, A>,
) -> (result: usize)
    ensures
        result as nat
            == wrapped_btree_map_key_sequence(set).len(),
{
    rust_1_96_selected_map_len(set).value
}
"""
        )
    if ("BTreeSet", "inherent", "iter") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_iter<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: MapBorrowedIteratorState<'a, T>)
    ensures
        result.valid,
        result.remaining@.unref()
            == wrapped_btree_map_key_sequence(set),
{
    loop { }
}

#[verifier::external_body]
pub fn rust_1_96_project_selected_iter<'a, T>(
    lower: MapBorrowedIteratorState<'a, T>,
) -> (result: Iter<'a, T>)
    ensures
        lower.valid ==> iter_remaining(result) == lower.remaining@,
{
    loop { }
}

pub fn rust_1_96_selected_iter<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
) -> (result: Iter<'a, T>)
    ensures
        iter_remaining(result).unref()
            == wrapped_btree_map_key_sequence(set),
        iter_remaining(result).len()
            == wrapped_btree_map_key_sequence(set).len(),
{
    let lower = rust_1_96_selected_map_iter(set);
    rust_1_96_project_selected_iter(lower)
}
"""
        )
    if ("BTreeSet", "inherent", "contains") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_contains<T, A: Allocator + Clone>(
    set: &BTreeSet<T, A>,
    value: &T,
) -> (result: MapBoolResult)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result.value
                == wrapped_btree_map_keys(set).contains(*value)
        ),
{
    loop { }
}

pub fn rust_1_96_selected_contains<T, A: Allocator + Clone>(
    set: &BTreeSet<T, A>,
    value: &T,
) -> (result: bool)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result == wrapped_btree_map_keys(set).contains(*value)
        ),
{
    rust_1_96_selected_map_contains(set, value).value
}
"""
        )
    if any(
        key in selected
        for key in (
            ("Iter", "Iterator", "next"),
            ("Iter", "DoubleEndedIterator", "next_back"),
            ("Iter", "ExactSizeIterator", "len"),
        )
    ):
        parts.append(
            r"""
pub uninterp spec fn selected_map_iter_remaining<'a, T>(
    iter: Iter<'a, T>,
) -> Seq<&'a T>;

#[verifier::external_body]
pub proof fn reveal_selected_map_iter<'a, T>(
    iter: &Iter<'a, T>,
)
    ensures
        selected_map_iter_remaining(*iter) == iter_remaining(*iter),
{
}
"""
        )
    if ("Iter", "ExactSizeIterator", "len") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_iter_len<'a, T>(
    iter: &Iter<'a, T>,
) -> (result: MapLengthResult)
    ensures
        result.value as nat
            == selected_map_iter_remaining(*iter).len(),
{
    loop { }
}

pub fn rust_1_96_selected_iter_len<'a, T>(
    iter: &Iter<'a, T>,
) -> (result: usize)
    ensures
        result as nat == iter_remaining(*iter).len(),
{
    proof { reveal_selected_map_iter(iter); }
    rust_1_96_selected_map_iter_len(iter).value
}
"""
        )
    if ("Iter", "Iterator", "next") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_iter_next<'a, T>(
    iter: &mut Iter<'a, T>,
) -> (result: Option<MapEntry<&'a T>>)
    ensures
        project_map_entry(result)
            == if selected_map_iter_remaining(*old(iter)).len() > 0 {
                Some(selected_map_iter_remaining(*old(iter))[0])
            } else {
                None
            },
        selected_map_iter_remaining(*final(iter))
            == if selected_map_iter_remaining(*old(iter)).len() > 0 {
                selected_map_iter_remaining(*old(iter)).drop_first()
            } else {
                selected_map_iter_remaining(*old(iter))
            },
{
    loop { }
}

pub fn rust_1_96_selected_iter_next<'a, T>(
    iter: &mut Iter<'a, T>,
) -> (result: Option<&'a T>)
    ensures
        result == if iter_remaining(*old(iter)).len() > 0 {
            Some(iter_remaining(*old(iter))[0])
        } else {
            None
        },
        iter_remaining(*final(iter))
            == if iter_remaining(*old(iter)).len() > 0 {
                iter_remaining(*old(iter)).drop_first()
            } else {
                iter_remaining(*old(iter))
            },
        iter_remaining(*final(iter)).len()
            == if iter_remaining(*old(iter)).len() > 0 {
                iter_remaining(*old(iter)).drop_first().len()
            } else {
                iter_remaining(*old(iter)).len()
            },
{
    proof { reveal_selected_map_iter(iter); }
    let lower = rust_1_96_selected_map_iter_next(iter);
    proof { reveal_selected_map_iter(iter); }
    project_map_entry_exec(lower)
}
"""
        )
    if ("Iter", "DoubleEndedIterator", "next_back") in selected:
        parts.append(
            r"""
#[verifier::external_body]
pub fn rust_1_96_selected_map_iter_next_back<'a, T>(
    iter: &mut Iter<'a, T>,
) -> (result: Option<MapEntry<&'a T>>)
    ensures
        project_map_entry(result)
            == if selected_map_iter_remaining(*old(iter)).len() > 0 {
                Some(selected_map_iter_remaining(*old(iter)).last())
            } else {
                None
            },
        selected_map_iter_remaining(*final(iter))
            == if selected_map_iter_remaining(*old(iter)).len() > 0 {
                selected_map_iter_remaining(*old(iter)).drop_last()
            } else {
                selected_map_iter_remaining(*old(iter))
            },
{
    loop { }
}

pub fn rust_1_96_selected_iter_next_back<'a, T>(
    iter: &mut Iter<'a, T>,
) -> (result: Option<&'a T>)
    ensures
        result == if iter_remaining(*old(iter)).len() > 0 {
            Some(iter_remaining(*old(iter)).last())
        } else {
            None
        },
        iter_remaining(*final(iter))
            == if iter_remaining(*old(iter)).len() > 0 {
                iter_remaining(*old(iter)).drop_last()
            } else {
                iter_remaining(*old(iter))
            },
        iter_remaining(*final(iter)).len()
            == if iter_remaining(*old(iter)).len() > 0 {
                iter_remaining(*old(iter)).drop_last().len()
            } else {
                iter_remaining(*old(iter)).len()
            },
{
    proof { reveal_selected_map_iter(iter); }
    let lower = rust_1_96_selected_map_iter_next_back(iter);
    proof { reveal_selected_map_iter(iter); }
    project_map_entry_exec(lower)
}
"""
        )
    return "\n".join(parts)


def contract_requirements(row: model.Row) -> list[str]:
    if row.disposition != "generated":
        return []
    _binder, inputs, output, _where_clause = model.proxy_parts(row)
    return model.require_lines(row, inputs, output)


def contract_lines(row: model.Row) -> list[str]:
    _binder, inputs, output, _where_clause = model.proxy_parts(row)
    if row.disposition == "generated":
        return model.ensure_lines(row, inputs, output)

    receiver, _receiver_kind = model.receiver_info(inputs)
    args = {source: name for name, _rust_type, source in inputs}
    name = row.function["name"]
    if (row.owner["name"], row.trait, name) == ("BTreeSet", "Clone", "clone"):
        return ["result@ == this@"]
    if name == "new" or row.trait == "Default":
        return ["result@ == Set::empty()"]
    if name == "len":
        return ["result == spec_btree_set_len(this)"]
    if name == "is_empty":
        return ["result == this@.is_empty()"]
    if name == "clear":
        return ["final(this)@ == Set::empty()"]
    if name == "contains":
        value = args.get("value", "value")
        return [
            (
                "obeys_cmp::<T>() ==> "
                f"(result == set_contains_borrowed_key({receiver}@, {value}))"
            )
        ]
    if name == "get":
        value = args.get("value", "value")
        return [
            (
                "obeys_cmp::<T>() ==> "
                "(match result { Some(found) => "
                f"sets_borrowed_key_to_key({receiver}@, {value}, found), "
                f"None => !set_contains_borrowed_key({receiver}@, {value}) }})"
            )
        ]
    if name == "insert":
        value = args.get("value", "value")
        return [
            f"obeys_cmp::<T>() ==> (final(this)@ == old(this)@.insert({value}))",
            (
                "obeys_cmp::<T>() ==> "
                f"(result == !old(this)@.contains({value}))"
            ),
        ]
    if name == "remove":
        value = args.get("value", "value")
        return [
            (
                "obeys_cmp::<T>() ==> "
                f"sets_differ_by_borrowed_key(old(this)@, final(this)@, {value})"
            ),
            (
                "obeys_cmp::<T>() ==> "
                f"(result == set_contains_borrowed_key(old(this)@, {value}))"
            ),
        ]
    if name == "iter":
        return [
            "key_obeys_cmp_spec::<T>() ==> (result == spec_btree_keys_iter(this))",
            (
                "key_obeys_cmp_spec::<T>() ==> "
                "(IteratorSpec::decrease(&result) is Some)"
            ),
            (
                "key_obeys_cmp_spec::<T>() ==> "
                "IteratorSpec::initial_value_relation(&result, &result)"
            ),
        ]
    raise RuntimeError(f"missing exact-vstd proof contract for {row.target_id}")


def render_ensures(lines: list[str], indent: str = "        ") -> str:
    return "\n".join(f"{indent}{line}," for line in lines)


def render_requires(lines: list[str], indent: str = "        ") -> str:
    if not lines:
        return ""
    return "    requires\n" + "\n".join(
        f"{indent}{line}," for line in lines
    ) + "\n"


def signature_parts(
    row: model.Row,
    function_name: str,
    *,
    output_override: str | None = None,
    override_output: bool = False,
    extra_inputs: tuple[tuple[str, str], ...] = (),
) -> tuple[list[tuple[str, str, str]], str | None, str]:
    binder, inputs, output, where_clause = model.proxy_parts(row)
    rendered = [
        f"{name}: {rust_type}" for name, rust_type, _source in inputs
    ]
    rendered.extend(f"{name}: {rust_type}" for name, rust_type in extra_inputs)
    rendered_inputs = ",\n    ".join(rendered)
    selected_output = output_override if override_output else output
    return_part = (
        f" -> (result: {selected_output})"
        if selected_output is not None
        else ""
    )
    signature = (
        f"pub fn {function_name}{binder}(\n"
        f"    {rendered_inputs}\n"
        f"){return_part}{where_clause}"
    )
    return inputs, output, signature


def dependency_operation(row: model.Row) -> str:
    owner = row.owner["name"]
    name = row.function["name"]
    trait = row.trait
    if union_left_biased_next(row):
        return "union_iterator_next_merge_nexts"
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        return "selected_owned_extend"
    selected_terminal = terminal_override_selected_method(row)
    if selected_terminal is not None:
        return (
            f"selected_{owner.lower()}_{selected_terminal}"
            .replace("symmetricdifference", "symmetric_difference")
        )
    if owner == "BTreeSet" and trait == "inherent":
        operation = {
            "new": "btree_map_new",
            "range": "btree_map_range_cursor",
            "difference": "difference_variant_constructor",
            "symmetric_difference": "merge_iter_symmetric_constructor",
            "intersection": "intersection_variant_constructor",
            "union": "merge_iter_union_constructor",
            "clear": "btree_map_clear",
            "contains": "btree_map_contains_key",
            "get": "btree_map_get_key_value",
            "is_disjoint": "intersection_next_projection",
            "is_subset": "subset_endpoint_and_scan",
            "is_superset": "subset_endpoint_and_scan",
            "first": "btree_map_first_key_value",
            "last": "btree_map_last_key_value",
            "pop_first": "btree_map_pop_first",
            "pop_last": "btree_map_pop_last",
            "insert": "btree_map_insert_set_value",
            "replace": "btree_map_replace_key",
            "remove": "btree_map_remove_value",
            "take": "btree_map_remove_entry",
            "retain": "extract_if_for_each_drop",
            "append": "btree_map_append",
            "split_off": "btree_map_split_off",
            "extract_if": "btree_map_extract_if_inner",
            "iter": "btree_map_keys_projection",
            "len": "btree_map_len_projection",
            "is_empty": "btree_set_len_zero",
        }.get(name)
        if operation is not None:
            return operation
    if owner == "BTreeSet":
        operation = {
            "Hash": "btree_map_hash",
            "PartialEq": "btree_map_eq",
            "PartialOrd": "btree_map_partial_cmp",
            "Ord": "btree_map_cmp",
            "Clone": "btree_map_clone_projection",
            "FromIterator": "stable_sort_dedup_bulk_build",
            "From": "array_stable_sort_dedup_bulk_build",
            "IntoIterator": "btree_map_into_or_borrowed_iter",
            "Extend": "iterator_for_each_btree_map_insert",
            "Default": "btree_map_new",
            "Sub": "difference_clone_bulk_build",
            "BitXor": "symmetric_difference_clone_bulk_build",
            "BitAnd": "intersection_clone_bulk_build",
            "BitOr": "union_clone_bulk_build",
            "Debug": "debug_set_entries",
        }.get(trait)
        if operation is not None:
            return operation
    return (
        f"{owner.lower()}_{trait.lower()}_{name}_private_state"
        .replace("::", "_")
        .replace(" ", "_")
    )


def dependency_function_name(row: model.Row) -> str:
    return f"rust_1_96_{dependency_operation(row)}"


def dependency_function_names(row: model.Row) -> list[str]:
    base = dependency_function_name(row)
    if source_owned_adapter_loop(row):
        suffixes = {
            "Difference": (
                "",
                "_read_source_discriminant",
                "_stitch_peek_other",
                "_stitch_compare",
                "_stitch_next_other",
                "_search_next_self",
                "_search_contains",
                "_iterate_next",
            ),
            "SymmetricDifference": ("",),
            "Intersection": (
                "",
                "_read_source_discriminant",
                "_stitch_next_b",
                "_stitch_compare",
                "_stitch_advance_a",
                "_stitch_advance_b",
                "_search_next_small",
                "_search_contains",
                "_answer_take",
            ),
        }[row.owner["name"]]
        return [f"{base}{suffix}" for suffix in suffixes]
    if not uses_private_branch(row):
        return [base]
    return [
        base if not suffix else f"{base}_{suffix}"
        for _pattern, _guard, suffix in branch_arm_specs(row)
    ]


def generic_call_name(row: model.Row, function_name: str) -> str:
    binder = model.proxy_parts(row)[0]
    arguments = [
        item["name"]
        for item in model.parse_generic_declarations(binder)
        if item["kind"] != "lifetime"
    ]
    suffix = f"::<{', '.join(arguments)}>" if arguments else ""
    return f"{function_name}{suffix}"


def dependency_call_name(row: model.Row) -> str:
    return generic_call_name(row, dependency_function_name(row))


def dependency_call_names(row: model.Row) -> list[str]:
    return [
        generic_call_name(row, name)
        for name in dependency_function_names(row)
    ]


CONTROL_FLOW_FAMILIES = {
    "sorted_deduplicating_conversion",
}

SOURCE_OWNED_ADAPTER_LOOP_TARGETS = frozenset(
    {
        "078_Difference_Iterator_next_2299",
        "082_SymmetricDifference_Iterator_next_2327",
        "086_Intersection_Iterator_next_2355",
    }
)


def source_owned_adapter_loop(row: model.Row) -> bool:
    return row.target_id in SOURCE_OWNED_ADAPTER_LOOP_TARGETS


EMPTY_ADAPTER_STATE_MUTATION_FAMILIES = frozenset(
    {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }
)

EMPTY_ADAPTER_STATE_EXPRESSION = (
    "Ghost(adapter_state(0, Seq::empty(), Seq::empty(), "
    "Seq::empty(), None, 0, None))"
)


def uses_private_branch(row: model.Row) -> bool:
    if union_left_biased_next(row):
        return False
    if source_owned_adapter_loop(row):
        return False
    if row.semantic_family in CONTROL_FLOW_FAMILIES:
        return True
    return (
        row.owner["name"]
        in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
            "ExtractIf",
        }
        and row.function["name"] == "next"
    )


def adapter_loop_control_mutation_required(row: model.Row) -> bool:
    return (
        not union_left_biased_next(row)
        and
        row.owner["name"]
        in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
        }
        and row.function["name"] == "next"
    )


def retains_adapter_source_loop(row: model.Row) -> bool:
    return source_owned_adapter_loop(row)


def adapter_loop_steps_spec(row: model.Row) -> str:
    owner = row.owner["name"]
    prefix = {
        "Difference": "difference",
        "SymmetricDifference": "symmetric_difference",
        "Intersection": "intersection",
    }.get(owner)
    if prefix is None:
        raise RuntimeError(f"{row.target_id}: no source loop step model")
    return f"{prefix}_source_loop_steps"


def adapter_loop_control_source_and_call(
    row: model.Row,
    inputs: list[tuple[str, str, str]],
) -> tuple[str, str]:
    if not retains_adapter_source_loop(row):
        return "", ""
    receiver, receiver_type, _source = next(
        item for item in inputs if item[2] == "self"
    )
    receiver_base = re.sub(
        r"^&(?:'[^ ]+\s+)?mut\s+", "", receiver_type
    )
    binder, _inputs, _output, where_clause = model.proxy_parts(row)
    function_name = (
        f"rust_1_96_{dependency_operation(row)}_read_source_loop_steps"
    )
    callee = generic_call_name(row, function_name)
    state = {
        "Difference": "difference_source_state",
        "SymmetricDifference": "symmetric_difference_source_state",
        "Intersection": "intersection_source_state",
    }[row.owner["name"]]
    steps = adapter_loop_steps_spec(row)
    source = f"""
pub uninterp spec fn {steps}<T>(
    state: SetAdapterState<T>,
    source_branch: u8,
) -> nat;

#[verifier::external_body]
pub fn {function_name}{binder}(
    this: &{receiver_base},
    source_branch: u8,
) -> (steps: usize)
{where_clause}    ensures
        steps as nat == {steps}(
            {state}(*this),
            source_branch,
        ),
{{
    loop {{ }}
}}
"""
    return source, f"{callee}(&*{receiver}, source_branch)"


def branch_arm_specs(row: model.Row) -> list[tuple[str, str, str]]:
    if not uses_private_branch(row):
        return []
    if row.semantic_family in {
        "sorted_deduplicating_conversion",
    } or (
        row.owner["name"] == "ExtractIf"
        and row.function["name"] == "next"
    ):
        return [
            ("0", "source_branch == 0", ""),
            ("_", "source_branch == 1", "branch_nonempty"),
        ]
    if (
        row.owner["name"] == "Intersection"
        and row.function["name"] == "next"
    ):
        return [
            ("0", "source_branch == 0", ""),
            ("1", "source_branch == 1", "branch_1"),
            (
                "_",
                "2 <= source_branch && source_branch <= 3",
                "branch_answer",
            ),
        ]
    if row.semantic_family == "intersection_adapter_construction" or (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        return [
            ("0", "source_branch == 0", ""),
            ("1", "source_branch == 1", "branch_1"),
            ("2", "source_branch == 2", "branch_2"),
            ("_", "source_branch == 3", "branch_3"),
        ]
    return [
        ("0", "source_branch == 0", ""),
        ("1", "source_branch == 1", "branch_1"),
        ("_", "source_branch == 2", "branch_2"),
    ]


# The lower-observation projection carriers emitted into every regenerated
# harness are defined once below. An earlier alias vocabulary kept only as
# migration history has been removed; no alias is emitted into any harness.
COMMON_PROJECTION_TYPES = r"""
pub struct MapSetValue;

pub struct PrivateCompletion {
    pub completed: bool,
}

pub struct MapEntry<R> {
    pub key: R,
    pub value: MapSetValue,
}

pub struct MapBoolResult {
    pub value: bool,
}

pub struct MapSubsetScanResult<'a, T> {
    pub value: bool,
    pub remaining_before: Ghost<Seq<&'a T>>,
    pub search_branch: bool,
    pub source_branch: u8,
}

pub struct MapLengthResult {
    pub value: usize,
}

pub struct PrivateSizeHintResult {
    pub lower: usize,
    pub upper: Option<usize>,
}

pub struct MapOrderingResult {
    pub value: core::cmp::Ordering,
}

pub struct MapPartialOrderingResult {
    pub value: Option<core::cmp::Ordering>,
}

pub struct FormatterFinishResult {
    pub value: core::fmt::Result,
}

pub struct MapReplacedKey<T> {
    pub key: Option<T>,
}

pub struct MapSetResultState<T> {
    pub keys: Ghost<Seq<T>>,
    pub valid: bool,
}

pub struct MapStableSortedInput<T> {
    pub source: Ghost<Seq<T>>,
    pub sorted: Ghost<Seq<T>>,
    pub valid: bool,
}

pub struct MapBorrowedIteratorState<'a, T> {
    pub remaining: Ghost<Seq<&'a T>>,
    pub valid: bool,
}

pub struct MapOwnedIteratorState<T> {
    pub remaining: Ghost<Seq<T>>,
    pub valid: bool,
}

pub struct MapSetAdapterState<'a, T> {
    pub state: Ghost<SetAdapterState<T>>,
    pub remaining: Ghost<Seq<&'a T>>,
    pub valid: bool,
    pub marker: Ghost<Option<&'a T>>,
}

pub struct MapExtractIfState<'a, T, F> {
    pub set: Ghost<Set<T>>,
    pub pending: Ghost<Seq<T>>,
    pub remaining: Ghost<Seq<T>>,
    pub callback_count: Ghost<nat>,
    pub predicate_state: Ghost<F>,
    pub initial_set: Ghost<Set<T>>,
    pub yielded: Ghost<Seq<T>>,
    pub drop_valid: bool,
    pub panic_valid: bool,
    pub marker: Ghost<Option<&'a T>>,
}

pub struct MapExtractIfConsumption<T> {
    pub retained: Ghost<Seq<T>>,
    pub consumed: bool,
    pub callback_count: Ghost<nat>,
}

pub open spec fn project_map_entry<R>(entry: Option<MapEntry<R>>) -> Option<R> {
    match entry {
        Some(value) => Some(value.key),
        None => None,
    }
}

pub fn project_map_entry_exec<R>(
    entry: Option<MapEntry<R>>,
) -> (result: Option<R>)
    ensures
        result == project_map_entry(entry),
{
    match entry {
        Some(value) => Some(value.key),
        None => None,
    }
}
"""

@dataclass(frozen=True)
class Projection:
    lower_type: str
    contract_expression: str | None
    body_expression: str
    lower_shape: str
    kind: str = "direct"


def projection_for(row: model.Row, output: str | None) -> Projection:
    name = row.function["name"]
    if output is None:
        return Projection(
            "PrivateCompletion",
            None,
            "let completion = lower;\n    assert(completion.completed);",
            "private operation-completion token",
            "completion",
        )
    if name == "insert" and row.owner["name"] == "BTreeSet":
        return Projection(
            "Option<MapSetValue>",
            "result.is_none()",
            "lower.is_none()",
            "BTreeMap::insert Option<SetValZST> presence",
            "direct",
        )
    if name == "remove" and row.owner["name"] == "BTreeSet":
        return Projection(
            "Option<MapSetValue>",
            "result.is_some()",
            "lower.is_some()",
            "BTreeMap::remove Option<SetValZST> presence",
            "direct",
        )
    if output.startswith("Option<") and output != "Option<core::cmp::Ordering>" and name != "replace":
        inner = output[len("Option<") : -1]
        return Projection(
            f"Option<MapEntry<{inner}>>",
            "project_map_entry(result)",
            "project_map_entry_exec(lower)",
            "map/private iterator Option<(key, SetValZST)> key projection",
            "direct",
        )
    if output == "usize":
        return Projection(
            "MapLengthResult",
            "result.value",
            "lower.value",
            "BTreeMap/private iterator exact length",
            "direct",
        )
    if output == "(usize, Option<usize>)":
        return Projection(
            "PrivateSizeHintResult",
            "(result.lower, result.upper)",
            "(lower.lower, lower.upper)",
            "private source size-hint return tuple",
            "direct",
        )
    if output == "core::cmp::Ordering":
        return Projection(
            "MapOrderingResult",
            "result.value",
            "lower.value",
            "BTreeMap lexicographic comparison return",
            "direct",
        )
    if output == "Option<core::cmp::Ordering>":
        return Projection(
            "MapPartialOrderingResult",
            "result.value",
            "lower.value",
            "BTreeMap partial lexicographic comparison return",
            "direct",
        )
    if output == "core::fmt::Result":
        return Projection(
            "FormatterFinishResult",
            "result.value",
            "lower.value",
            "formatter builder finish result",
            "direct",
        )
    if output == "BTreeSet<T, A>":
        return Projection(
            "MapSetResultState<T>",
            None,
            "rust_1_96_project_set_result::<T, A>(lower)",
            "BTreeMap key sequence/set result state",
            "set_state",
        )
    if output == "BTreeSet<T>":
        return Projection(
            "MapSetResultState<T>",
            None,
            "rust_1_96_project_global_set_result::<T>(lower)",
            "global-allocator BTreeMap key sequence/set result state",
            "set_state_global",
        )
    if output == "bool":
        return Projection(
            "MapBoolResult",
            "result.value",
            "lower.value",
            f"boolean return of {dependency_operation(row)}",
            "direct",
        )
    if output == "Option<T>" and name == "replace":
        return Projection(
            "MapReplacedKey<T>",
            "result.key",
            "lower.key",
            "BTreeMap occupied-entry key replacement result",
            "direct",
        )
    if output.startswith("ExtractIf<"):
        return Projection(
            "MapExtractIfState<'_, T, F>",
            None,
            "rust_1_96_project_extract_if_result::<T, R, F, A>(lower)",
            "BTreeMap ExtractIf state without the public adapter",
            "extract_state",
        )
    if output.startswith(
        ("Difference<", "Intersection<", "SymmetricDifference<", "Union<")
    ):
        projector = {
            "Difference": "rust_1_96_project_difference_result::<T, A>",
            "Intersection": "rust_1_96_project_intersection_result::<T, A>",
            "SymmetricDifference": (
                "rust_1_96_project_symmetric_difference_result::<T>"
            ),
            "Union": "rust_1_96_project_union_result::<T>",
        }[row.owner["name"] if row.owner["name"] != "BTreeSet" else {
            "difference": "Difference",
            "intersection": "Intersection",
            "symmetric_difference": "SymmetricDifference",
            "union": "Union",
        }[name]]
        return Projection(
            "MapSetAdapterState<'a, T>",
            None,
            f"{projector}(lower)",
            "set-operation variant/components without the public adapter",
            "set_adapter",
        )
    if output.startswith("IntoIter<"):
        return Projection(
            "MapOwnedIteratorState<T>",
            None,
            "rust_1_96_project_into_iter_result::<T, A>(lower)",
            "BTreeMap owned key-iterator state",
            "owned_iter",
        )
    if output.startswith("Iter<"):
        lifetime = "'a" if "'a" in output else "'_"
        projector = (
            "rust_1_96_project_iter_result::<T, A>(this, lower)"
            if row.owner["name"] == "BTreeSet"
            and row.function["name"] == "iter"
            else "rust_1_96_project_iter_result::<T>(lower)"
        )
        return Projection(
            f"MapBorrowedIteratorState<{lifetime}, T>",
            None,
            projector,
            "BTreeMap borrowed key-iterator state",
            "borrowed_iter",
        )
    if output.startswith("Range<"):
        lifetime = "'a" if "'a" in output else "'_"
        return Projection(
            f"MapBorrowedIteratorState<{lifetime}, T>",
            None,
            "rust_1_96_project_range_result::<T>(lower)",
            "BTreeMap borrowed range state",
            "borrowed_range",
        )
    raise RuntimeError(
        f"missing narrow dependency return shape for {row.target_id}: {output}"
    )


def dependency_return_type(row: model.Row, projection: Projection) -> str:
    if union_left_biased_next(row):
        return "MapMergeEntries<'a, T>"
    if (
        requires_selected_public_composition(row)
        and row.function["name"] == "retain"
    ):
        return "MapExtractIfConsumption<T>"
    if (
        requires_selected_public_composition(row)
        and row.function["name"] == "is_disjoint"
    ):
        return "Option<MapEntry<&'a T>>"
    if (
        requires_selected_public_composition(row)
        and row.function["name"] in {"is_subset", "is_superset"}
    ):
        return "Option<MapEntry<&'a T>>"
    return projection.lower_type


def dependency_lower_shape(row: model.Row, projection: Projection) -> str:
    if union_left_biased_next(row):
        return (
            "pair of private MergeIter nexts candidates as map-entry "
            "projections with a private merge-state witness"
        )
    if not requires_selected_public_composition(row):
        return projection.lower_shape
    if row.semantic_family in {
        "difference_adapter_construction",
        "symmetric_difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
    }:
        return "private adapter variant built from selected live iterator cursors"
    if row.function["name"] == "is_disjoint":
        return "one private Intersection iterator item"
    if row.function["name"] == "is_empty":
        return "zero comparison over the selected BTreeSet length"
    if row.function["name"] in {"is_subset", "is_superset"}:
        return "one indexed key observation for the executable subset scan"
    if row.function["name"] == "retain":
        return "consumption state from the selected live ExtractIf adapter"
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        return "completion from selected owned Extend over the cloned input"
    if terminal_override_selected_method(row) is not None:
        return "one selected next/next_back transition on the live cursor"
    if row.trait == "Extend":
        return "one BTreeMap insertion transition"
    if row.trait == "IntoIterator":
        return "private iterator state tied to the selected iter result"
    if row.trait == "Default":
        return "BTreeMap state tied to the selected new result"
    if row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}:
        return "sorted BTreeMap build from a selected adapter cursor"
    if row.trait == "Debug":
        return "formatter finish from a selected iterator"
    return projection.lower_shape


def btree_map_bridge_required(row: model.Row) -> bool:
    _binder, inputs, _output, _where_clause = model.proxy_parts(row)
    return any("BTreeSet<" in rust_type for _name, rust_type, _source in inputs)


PRIVATE_CURSOR_OBSERVATIONS: dict[str, dict[str, tuple[str, str]]] = {
    "Iter": {
        "iter_remaining": (
            "map_keys_cursor_remaining",
            "Seq<&'a T>",
        ),
        "iter_debug_shape": (
            "map_keys_cursor_debug_shape",
            "AdapterDebugShape<&'a T>",
        ),
        "iter_debug_shape_law": (
            "map_keys_cursor_debug_shape_law",
            "bool",
        ),
    },
    "IntoIter": {
        "into_iter_remaining": (
            "map_into_cursor_remaining",
            "Seq<T>",
        ),
        "into_iter_debug_shape": (
            "map_into_cursor_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "into_iter_debug_shape_law": (
            "map_into_cursor_debug_shape_law",
            "bool",
        ),
    },
    "Range": {
        "range_remaining": (
            "map_range_cursor_remaining",
            "Seq<&'a T>",
        ),
        "range_debug_shape": (
            "map_range_cursor_debug_shape",
            "AdapterDebugShape<&'a T>",
        ),
        "range_debug_shape_law": (
            "map_range_cursor_debug_shape_law",
            "bool",
        ),
    },
    "Difference": {
        "difference_remaining": (
            "difference_inner_cursor_remaining",
            "Seq<&'a T>",
        ),
        "difference_source_state": (
            "difference_inner_state",
            "SetAdapterState<T>",
        ),
        "difference_source_state_law": (
            "difference_inner_state_law",
            "bool",
        ),
        "difference_debug_shape": (
            "difference_inner_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "difference_debug_shape_law": (
            "difference_inner_debug_shape_law",
            "bool",
        ),
    },
    "SymmetricDifference": {
        "symmetric_difference_remaining": (
            "symmetric_difference_inner_cursor_remaining",
            "Seq<&'a T>",
        ),
        "symmetric_difference_source_state": (
            "symmetric_difference_inner_state",
            "SetAdapterState<T>",
        ),
        "symmetric_difference_source_state_law": (
            "symmetric_difference_inner_state_law",
            "bool",
        ),
        "symmetric_difference_debug_shape": (
            "symmetric_difference_inner_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "symmetric_difference_debug_shape_law": (
            "symmetric_difference_inner_debug_shape_law",
            "bool",
        ),
    },
    "Intersection": {
        "intersection_remaining": (
            "intersection_inner_cursor_remaining",
            "Seq<&'a T>",
        ),
        "intersection_source_state": (
            "intersection_inner_state",
            "SetAdapterState<T>",
        ),
        "intersection_source_state_law": (
            "intersection_inner_state_law",
            "bool",
        ),
        "intersection_debug_shape": (
            "intersection_inner_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "intersection_debug_shape_law": (
            "intersection_inner_debug_shape_law",
            "bool",
        ),
    },
    "Union": {
        "union_remaining": (
            "union_inner_cursor_remaining",
            "Seq<&'a T>",
        ),
        "union_source_state": (
            "union_inner_state",
            "SetAdapterState<T>",
        ),
        "union_source_state_law": (
            "union_inner_state_law",
            "bool",
        ),
        "union_debug_shape": (
            "union_inner_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "union_debug_shape_law": (
            "union_inner_debug_shape_law",
            "bool",
        ),
    },
    "ExtractIf": {
        "extract_if_debug_shape": (
            "map_extract_if_debug_shape",
            "AdapterDebugShape<T>",
        ),
        "extract_if_debug_shape_law": (
            "map_extract_if_debug_shape_law",
            "bool",
        ),
        "extract_if_remaining": (
            "map_extract_if_remaining",
            "Seq<T>",
        ),
        "extract_if_set": (
            "map_extract_if_set",
            "Set<T>",
        ),
        "extract_if_pending": (
            "map_extract_if_pending",
            "Seq<T>",
        ),
        "extract_if_decisions": (
            "map_extract_if_decisions",
            "Seq<bool>",
        ),
        "extract_if_callback_count": (
            "map_extract_if_callback_count",
            "nat",
        ),
        "extract_if_predicate_state": (
            "map_extract_if_predicate_state",
            "F",
        ),
        "extract_if_initial_set": (
            "map_extract_if_initial_set",
            "Set<T>",
        ),
        "extract_if_yielded": (
            "map_extract_if_yielded",
            "Seq<T>",
        ),
        "extract_if_drop_law": (
            "map_extract_if_drop_law",
            "bool",
        ),
        "extract_if_panic_law": (
            "map_extract_if_panic_law",
            "bool",
        ),
        "extract_if_length_bound": (
            "map_extract_if_length_bound",
            "nat",
        ),
    },
}


def private_cursor_bridge_required(row: model.Row) -> bool:
    if not private_cursor_observations_for_row(row):
        return False
    _binder, inputs, _output, _where_clause = model.proxy_parts(row)
    return any(source == "self" for _name, _type, source in inputs)


def private_cursor_observations_for_row(
    row: model.Row,
) -> dict[str, tuple[str, str]]:
    observations = PRIVATE_CURSOR_OBSERVATIONS.get(row.owner["name"], {})
    contract = "\n".join(
        [*contract_requirements(row), *contract_lines(row)]
    )
    return {
        public: value
        for public, value in observations.items()
        if re.search(rf"\b{re.escape(public)}\b", contract)
    }


def private_cursor_bridge_source(row: model.Row) -> str:
    observations = private_cursor_observations_for_row(row)
    if not observations or not private_cursor_bridge_required(row):
        return ""
    binder, inputs, _output, where_clause = model.proxy_parts(row)
    receiver = next(
        (item for item in inputs if item[2] == "self"),
        None,
    )
    if receiver is None:
        raise RuntimeError(
            f"{row.target_id}: private cursor bridge lacks receiver"
        )
    _name, rust_type, _source = receiver
    owner_type = re.sub(r"^&(?:'[^ ]+\s+)?(?:mut\s+)?", "", rust_type)
    if row.owner["name"] == "ExtractIf":
        value_observations = {
            public: (private, return_type)
            for public, (private, return_type) in observations.items()
            if public != "extract_if_length_bound"
        }
        declarations = [
            f"pub uninterp spec fn {private}{binder}("
            f"iter: {owner_type}) -> {return_type}{where_clause};"
            for private, return_type in value_observations.values()
        ]
        declarations.append(
            f"pub uninterp spec fn map_extract_if_length_bound{binder}("
            f"iter: &{owner_type}) -> nat{where_clause};"
        )
        guarantees = [
            f"        {private}(*iter) == {public}(*iter),"
            for public, (private, _return_type) in value_observations.items()
        ]
        guarantees.append(
            "        map_extract_if_length_bound(iter) "
            "== extract_if_length_bound(iter),"
        )
        return f"""
{chr(10).join(declarations)}

#[verifier::external_body]
pub proof fn reveal_private_cursor_projection{binder}(
    iter: &{owner_type},
){where_clause}
    ensures
{chr(10).join(guarantees)}
{{
}}
"""
    declarations = []
    guarantees = []
    for public, (private, return_type) in observations.items():
        declarations.append(
            f"pub uninterp spec fn {private}{binder}("
            f"iter: {owner_type}) -> {return_type}{where_clause};"
        )
        guarantees.append(
            f"        {private}(*iter) == {public}(*iter),"
        )
    if source_owned_adapter_loop(row) or union_left_biased_next(row):
        prefix = {
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
        }[row.owner["name"]]
        guarantees.append(
            f"        {prefix}_source_cursor_step_law("
            f"{prefix}_remaining(*iter), "
            f"{prefix}_source_state(*iter)),"
        )
    rendered_guarantees = "\n".join(guarantees)
    return f"""
{chr(10).join(declarations)}

#[verifier::external_body]
pub proof fn reveal_private_cursor_projection{binder}(
    iter: &{owner_type},
){where_clause}
    ensures
{rendered_guarantees}
{{
}}
"""


def private_cursor_bridge_calls(
    row: model.Row,
    inputs: list[tuple[str, str, str]],
) -> tuple[str, str]:
    if not private_cursor_bridge_required(row):
        return "", ""
    receiver = next(item for item in inputs if item[2] == "self")
    name, rust_type, _source = receiver
    reference = name if rust_type.startswith("&") else f"&{name}"
    before = f"proof {{ reveal_private_cursor_projection({reference}); }}"
    after = (
        f"proof {{ reveal_private_cursor_projection({name}); }}"
        if rust_type.startswith("&mut ")
        else ""
    )
    return before, after


def btree_map_bridge_source(row: model.Row) -> str:
    if not btree_map_bridge_required(row):
        return ""
    _binder, inputs, _output, _where_clause = model.proxy_parts(row)
    mutable = any(
        "BTreeSet<" in rust_type and rust_type.startswith("&mut ")
        for _name, rust_type, _source in inputs
    )
    immutable = any(
        "BTreeSet<" in rust_type and not rust_type.startswith("&mut ")
        for _name, rust_type, _source in inputs
    )
    bridges: list[str] = []
    if immutable:
        bridges.append(
            """
#[verifier::external_body]
pub proof fn reveal_btree_set_map_projection<
    T,
    A: Allocator + Clone,
>(
    set: &BTreeSet<T, A>,
)
    ensures
        wrapped_btree_map_key_sequence(set)
            == btree_set_sequence(*set),
        wrapped_btree_map_keys(set) == (*set)@,
        wrapped_btree_map_key_sequence(set).to_set()
            == wrapped_btree_map_keys(set),
        wrapped_btree_map_key_sequence(set).no_duplicates(),
        wrapped_btree_map_key_sequence(set).len()
            == wrapped_btree_map_keys(set).len(),
        wrapped_btree_map_debug_shape(*set)
            == btree_set_debug_shape(*set),
        wrapped_btree_map_debug_shape_law(*set)
            == btree_set_debug_shape_law(*set),
{
}
"""
        )
    if mutable:
        bridges.append(
            """
#[verifier::external_body]
pub proof fn reveal_btree_set_map_mut_projection<
    T,
    A: Allocator + Clone,
>(
    set: &mut BTreeSet<T, A>,
)
    ensures
        wrapped_btree_map_key_sequence(old(set))
            == btree_set_sequence(*old(set)),
        wrapped_btree_map_keys(old(set)) == (*old(set))@,
        wrapped_btree_map_key_sequence(old(set)).to_set()
            == wrapped_btree_map_keys(old(set)),
        wrapped_btree_map_key_sequence(old(set)).no_duplicates(),
        wrapped_btree_map_key_sequence(old(set)).len()
            == wrapped_btree_map_keys(old(set)).len(),
        wrapped_btree_map_key_sequence(final(set))
            == btree_set_sequence(*final(set)),
        wrapped_btree_map_keys(final(set)) == (*final(set))@,
        wrapped_btree_map_key_sequence(final(set)).to_set()
            == wrapped_btree_map_keys(final(set)),
        wrapped_btree_map_key_sequence(final(set)).no_duplicates(),
        wrapped_btree_map_key_sequence(final(set)).len()
            == wrapped_btree_map_keys(final(set)).len(),
{
}
"""
        )
    return """
pub uninterp spec fn wrapped_btree_map_key_sequence<
    T,
    A: Allocator + Clone,
>(
    set: &BTreeSet<T, A>,
) -> Seq<T>;

pub uninterp spec fn wrapped_btree_map_keys<
    T,
    A: Allocator + Clone,
>(
    set: &BTreeSet<T, A>,
) -> Set<T>;

pub uninterp spec fn wrapped_btree_map_debug_shape<
    T,
    A: Allocator + Clone,
>(
    set: BTreeSet<T, A>,
) -> AdapterDebugShape<T>;

pub uninterp spec fn wrapped_btree_map_debug_shape_law<
    T,
    A: Allocator + Clone,
>(
    set: BTreeSet<T, A>,
) -> bool;
""" + "\n".join(bridges)


def btree_map_bridge_function_for_type(rust_type: str) -> str:
    return (
        "reveal_btree_set_map_mut_projection"
        if rust_type.startswith("&mut ")
        else "reveal_btree_set_map_projection"
    )


def btree_map_bridge_function_names(row: model.Row) -> list[str]:
    _binder, inputs, _output, _where_clause = model.proxy_parts(row)
    return list(
        dict.fromkeys(
            btree_map_bridge_function_for_type(rust_type)
            for _name, rust_type, _source in inputs
            if "BTreeSet<" in rust_type
        )
    )


def btree_map_bridge_calls(
    row: model.Row,
    inputs: list[tuple[str, str, str]],
) -> tuple[str, str]:
    before: list[str] = []
    for name, rust_type, _source in inputs:
        if "BTreeSet<" not in rust_type:
            continue
        bridge = btree_map_bridge_function_for_type(rust_type)
        reference = name if rust_type.startswith("&") else f"&{name}"
        before.append(
            f"proof {{ {bridge}({reference}); }}"
        )
    return "\n    ".join(before), ""


def _private_cursor_name(row: model.Row, public_name: str) -> str:
    try:
        return PRIVATE_CURSOR_OBSERVATIONS[row.owner["name"]][public_name][0]
    except KeyError as error:
        raise RuntimeError(
            f"{row.target_id}: no private observation for {public_name}"
        ) from error


def _adapter_public_prefix(row: model.Row) -> str:
    owner = row.owner["name"]
    if owner == "BTreeSet":
        owner = {
            "difference": "Difference",
            "symmetric_difference": "SymmetricDifference",
            "intersection": "Intersection",
            "union": "Union",
        }[row.function["name"]]
    return {
        "Difference": "difference",
        "SymmetricDifference": "symmetric_difference",
        "Intersection": "intersection",
        "Union": "union",
    }[owner]


def _authored_adapter_construction_contract(row: model.Row) -> list[str]:
    prefix = _adapter_public_prefix(row)
    sequence = {
        "difference": "difference_sequence",
        "symmetric_difference": "symmetric_difference_sequence",
        "intersection": "intersection_source_sequence",
        "union": "union_sequence",
    }[prefix]
    set_expression = {
        "difference": (
            "wrapped_btree_map_keys(this).difference("
            "wrapped_btree_map_keys(other))"
        ),
        "symmetric_difference": (
            "wrapped_btree_map_keys(this).union("
            "wrapped_btree_map_keys(other)).difference("
            "wrapped_btree_map_keys(this).intersect("
            "wrapped_btree_map_keys(other)))"
        ),
        "intersection": (
            "wrapped_btree_map_keys(this).intersect("
            "wrapped_btree_map_keys(other))"
        ),
        "union": (
            "wrapped_btree_map_keys(this).union("
            "wrapped_btree_map_keys(other))"
        ),
    }[prefix]
    initial_state = (
        "difference_initial_state"
        if prefix == "difference"
        else "intersection_initial_state"
        if prefix == "intersection"
        else "merge_initial_state"
    )
    left = "wrapped_btree_map_key_sequence(this)"
    right = "wrapped_btree_map_key_sequence(other)"
    remaining = f"{sequence}({left}, {right})"
    guard = "(obeys_cmp::<T>()) ==> "
    return [
        f"{guard}(result.remaining@.unref() == {remaining})",
        f"{guard}(result.remaining@.unref().to_set() == {set_expression})",
        f"{guard}(increasing_seq(result.remaining@.unref()))",
        f"{guard}(result.remaining@.no_duplicates())",
        f"{guard}(result.state@ == {initial_state}({left}, {right}))",
    ]


def _authored_debug_contract(row: model.Row) -> list[str]:
    owner = row.owner["name"]
    if owner == "BTreeSet":
        shape = "wrapped_btree_map_debug_shape"
        law = "wrapped_btree_map_debug_shape_law"
    else:
        public_prefix = {
            "Iter": "iter",
            "IntoIter": "into_iter",
            "Range": "range",
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
            "ExtractIf": "extract_if",
        }[owner]
        shape = _private_cursor_name(
            row, f"{public_prefix}_debug_shape"
        )
        law = _private_cursor_name(
            row, f"{public_prefix}_debug_shape_law"
        )
    lines = [
        f"*final(f) == apply_debug_shape(*old(f), {shape}(*this)).0",
        f"(result.value) == apply_debug_shape(*old(f), {shape}(*this)).1",
        f"{law}(*this)",
    ]
    if owner == "BTreeSet":
        lines.extend(
            (
                "wrapped_btree_map_key_sequence(this).to_set() "
                "== wrapped_btree_map_keys(this)",
                "increasing_seq(wrapped_btree_map_key_sequence(this))",
            )
        )
    return lines


def _authored_exact_vstd_contract(row: model.Row) -> list[str]:
    name = row.function["name"]
    if name in {"new", "default"} or row.trait == "Default":
        return ["result.valid", "result.keys@.to_set() == Set::empty()"]
    if name == "clear":
        return [
            "result.completed",
            "wrapped_btree_map_keys(final(this)) == Set::empty()",
        ]
    if name == "contains":
        return [
            "obeys_cmp::<T>() ==> ((result.value) == "
            "set_contains_borrowed_key("
            "wrapped_btree_map_keys(this), value))"
        ]
    if name == "get":
        return [
            "obeys_cmp::<T>() ==> (match project_map_entry(result) { "
            "Some(found) => sets_borrowed_key_to_key("
            "wrapped_btree_map_keys(this), value, found), "
            "None => !set_contains_borrowed_key("
            "wrapped_btree_map_keys(this), value) })"
        ]
    if name == "insert":
        return [
            "obeys_cmp::<T>() ==> (wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)).insert(value))",
            "obeys_cmp::<T>() ==> ((result.is_none()) "
            "== !wrapped_btree_map_keys(old(this)).contains(value))",
        ]
    if name == "remove":
        return [
            "obeys_cmp::<T>() ==> sets_differ_by_borrowed_key("
            "wrapped_btree_map_keys(old(this)), "
            "wrapped_btree_map_keys(final(this)), value)",
            "obeys_cmp::<T>() ==> ((result.is_some()) "
            "== set_contains_borrowed_key("
            "wrapped_btree_map_keys(old(this)), value))",
        ]
    if name == "iter":
        return [
            "result.valid",
            "result.remaining@.unref() "
            "== wrapped_btree_map_key_sequence(this)"
        ]
    if name == "len":
        return ["(result.value) == spec_btree_set_len(this)"]
    if name == "is_empty":
        return [
            "(result.value) == wrapped_btree_map_keys(this).is_empty()"
        ]
    raise RuntimeError(
        f"{row.target_id}: missing authored exact-vstd lower contract"
    )


def _authored_iterator_step_contract(
    row: model.Row,
    *,
    backwards: bool,
) -> list[str]:
    owner = row.owner["name"]
    public_prefix = {
        "Iter": "iter",
        "IntoIter": "into_iter",
        "Range": "range",
        "Difference": "difference",
        "SymmetricDifference": "symmetric_difference",
        "Intersection": "intersection",
        "Union": "union",
        "ExtractIf": "extract_if",
    }[owner]
    remaining = _private_cursor_name(
        row, f"{public_prefix}_remaining"
    )
    old_remaining = f"{remaining}(*old(this))"
    selected = (
        f"{old_remaining}.last()"
        if backwards
        else f"{old_remaining}[0]"
    )
    remainder = (
        f"{old_remaining}.drop_last()"
        if backwards
        else f"{old_remaining}.drop_first()"
    )
    guard = (
        "(T::obeys_partial_cmp_spec()) ==> "
        if owner == "ExtractIf"
        else "(obeys_cmp::<T>()) ==> "
        if owner in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
        }
        else ""
    )
    if owner == "ExtractIf":
        decisions = _private_cursor_name(
            row, "extract_if_decisions"
        )
        pending = _private_cursor_name(row, "extract_if_pending")
        set_state = _private_cursor_name(row, "extract_if_set")
        callback_count = _private_cursor_name(
            row, "extract_if_callback_count"
        )
        predicate_state = _private_cursor_name(
            row, "extract_if_predicate_state"
        )
        initial_set = _private_cursor_name(
            row, "extract_if_initial_set"
        )
        yielded = _private_cursor_name(row, "extract_if_yielded")
        drop_law = _private_cursor_name(row, "extract_if_drop_law")
        panic_law = _private_cursor_name(row, "extract_if_panic_law")
        old_pending = f"{pending}(*old(this))"
        old_decisions = f"{decisions}(*old(this))"
        found = (
            f"first_true({old_decisions}) < {old_pending}.len()"
        )
        index = f"first_true({old_decisions})"
        count = (
            f"if {found} {{ ({index} + 1) as nat }} "
            f"else {{ {old_pending}.len() as nat }}"
        )
        return [
            f"{guard}(project_map_entry(result) == if {found} "
            f"{{ Some({old_pending}[{index}]) }} else {{ None }})",
            f"{guard}({pending}(*final(this)) == if {found} "
            f"{{ {old_pending}.subrange({index} + 1, "
            f"{old_pending}.len() as int) }} else {{ Seq::empty() }})",
            f"{guard}({set_state}(*final(this)) == if {found} "
            f"{{ {set_state}(*old(this)).remove("
            f"{old_pending}[{index}]) }} "
            f"else {{ {set_state}(*old(this)) }})",
            f"{guard}({callback_count}(*final(this)) == "
            f"{callback_count}(*old(this)) + {count})",
            f"{guard}({predicate_state}(*final(this)) == "
            "retain_callback_state_after("
            f"{predicate_state}(*old(this)), {old_pending}, {count}))",
            f"{guard}({initial_set}(*final(this)) "
            f"== {initial_set}(*old(this)))",
            f"{guard}({yielded}(*final(this)) == if {found} "
            f"{{ {yielded}(*old(this)).push("
            f"{old_pending}[{index}]) }} "
            f"else {{ {yielded}(*old(this)) }})",
            f"{guard}({remaining}(*final(this)) == "
            "if project_map_entry(result).is_some() "
            f"{{ {old_remaining}.drop_first() }} "
            f"else {{ {old_remaining} }})",
            f"{guard}({drop_law}(*final(this)))",
            f"{guard}({panic_law}(*final(this)))",
        ]
    lines = [
        f"{guard}(project_map_entry(result) == "
        f"if {old_remaining}.len() > 0 "
        f"{{ Some({selected}) }} else {{ None }})",
        f"{guard}({remaining}(*final(this)) == "
        f"if {old_remaining}.len() > 0 "
        f"{{ {remainder} }} else {{ {old_remaining} }})",
    ]
    if owner in {
        "Difference",
        "SymmetricDifference",
        "Intersection",
        "Union",
    }:
        state = _private_cursor_name(
            row, f"{public_prefix}_source_state"
        )
        state_law = _private_cursor_name(
            row, f"{public_prefix}_source_state_law"
        )
        lines.extend(
            (
                f"{guard}({state}(*final(this)) == "
                f"{public_prefix}_next_step("
                f"{state}(*old(this))).state)",
                f"{guard}({state_law}(*final(this)))",
            )
        )
    return lines


def _authored_size_hint_contract(row: model.Row) -> list[str]:
    owner = row.owner["name"]
    result = "(result.lower, result.upper)"
    if owner in {"Iter", "IntoIter", "Range"}:
        prefix = {
            "Iter": "iter",
            "IntoIter": "into_iter",
            "Range": "range",
        }[owner]
        remaining = _private_cursor_name(row, f"{prefix}_remaining")
        return [
            f"{result}.0 as nat == {remaining}(*this).len()",
            f"{result}.1 == Some({result}.0)",
        ]
    if owner == "ExtractIf":
        remaining = _private_cursor_name(row, "extract_if_remaining")
        bound = _private_cursor_name(row, "extract_if_length_bound")
        guard = "(T::obeys_partial_cmp_spec()) ==> "
        return [
            f"{guard}({result}.0 == 0)",
            f"{guard}(match {result}.1 {{ Some(upper) => "
            f"upper as nat == {bound}(this), None => false }})",
            f"{guard}({remaining}(*this).len() <= {bound}(this))",
        ]
    prefix = {
        "Difference": "difference",
        "SymmetricDifference": "symmetric_difference",
        "Intersection": "intersection",
        "Union": "union",
    }[owner]
    remaining = _private_cursor_name(row, f"{prefix}_remaining")
    variant = f"{prefix}_hint_variant(this)"
    lengths = f"{prefix}_hint_lengths(this)"
    guard = "(obeys_cmp::<T>()) ==> "
    if owner == "Difference":
        return [
            f"{guard}(0 <= {variant} <= 2)",
            f"{guard}({variant} == 2 ==> {lengths}.1 == 0)",
            f"{guard}({result}.0 as nat == if {lengths}.0 "
            f">= {lengths}.1 {{ {lengths}.0 - {lengths}.1 }} "
            "else { 0 })",
            f"{guard}(match {result}.1 {{ Some(upper) => "
            f"upper as nat == {lengths}.0, None => false }})",
            f"{guard}({result}.0 as nat <= {remaining}(*this).len())",
            f"{guard}(match {result}.1 {{ Some(upper) => "
            f"{remaining}(*this).len() <= upper as nat, "
            "None => false })",
        ]
    if owner == "Intersection":
        return [
            f"{guard}(0 <= {variant} <= 3)",
            f"{guard}({result}.0 as nat == intersection_hint_lower("
            f"{variant}, {lengths}.0, {lengths}.1))",
            f"{guard}(match {result}.1 {{ Some(upper) => "
            "upper as nat == intersection_hint_upper("
            f"{variant}, {lengths}.0, {lengths}.1), None => false }})",
            f"{guard}({result}.0 as nat <= {remaining}(*this).len())",
            f"{guard}(match {result}.1 {{ Some(upper) => "
            f"{remaining}(*this).len() <= upper as nat, "
            "None => false })",
        ]
    lower = (
        "0"
        if owner == "SymmetricDifference"
        else f"if {lengths}.0 >= {lengths}.1 "
        f"{{ {lengths}.0 }} else {{ {lengths}.1 }}"
    )
    lines = [
        f"{guard}({result}.0 as nat == {lower})",
        f"{guard}(match {result}.1 {{ Some(upper) => "
        f"upper as nat == {lengths}.0 + {lengths}.1, "
        "None => false })",
    ]
    if owner == "Union":
        lines.extend(
            (
                f"{guard}({result}.0 as nat "
                f"<= {remaining}(*this).len())",
                f"{guard}(match {result}.1 {{ Some(upper) => "
                f"{remaining}(*this).len() <= upper as nat, "
                "None => false })",
            )
        )
    elif owner == "SymmetricDifference":
        lines.append(
            f"{guard}(match {result}.1 {{ Some(upper) => "
            f"{remaining}(*this).len() <= upper as nat, "
            "None => false })"
        )
    return lines


def callback_length_lemma_source(row: model.Row) -> str:
    if row.semantic_family not in {
        "ordered_callback_retain",
        "extract_if_construction",
    } and not (
        row.owner["name"] == "ExtractIf"
        and row.function["name"] == "next"
    ):
        return ""
    return """
pub proof fn lemma_retain_callback_observation_lengths<
    T,
    F: FnMut(&T) -> bool,
>(
    state: F,
    items: Seq<T>,
)
    ensures
        retain_decisions_from(state, items).len() == items.len(),
        retain_effect_trace_from(state, items).len() == items.len(),
    decreases items.len(),
{
    if items.len() > 0 {
        let keep = fn_mut_result(state, &items[0]);
        lemma_retain_callback_observation_lengths(
            fn_mut_post_state(state, &items[0], keep),
            items.drop_first(),
        );
    }
}
"""


def retain_control_flow_source(row: model.Row) -> str:
    if (
        row.semantic_family != "ordered_callback_retain"
        or requires_selected_public_composition(row)
    ):
        return ""
    return """
pub open spec fn negate_callback_decisions(
    decisions: Seq<bool>,
) -> Seq<bool>
    decreases decisions.len()
{
    if decisions.len() == 0 {
        Seq::empty()
    } else {
        seq![!decisions[0]]
            + negate_callback_decisions(decisions.drop_first())
    }
}

pub proof fn lemma_callback_decision_double_negation(
    decisions: Seq<bool>,
)
    ensures
        negate_callback_decisions(
            negate_callback_decisions(decisions),
        ) == decisions,
    decreases decisions.len(),
{
    if decisions.len() > 0 {
        lemma_callback_decision_double_negation(
            decisions.drop_first(),
        );
        assert(negate_callback_decisions(decisions).len() > 0);
        assert(
            negate_callback_decisions(decisions)[0]
                == !decisions[0]
        );
        assert(
            negate_callback_decisions(decisions).drop_first()
                == negate_callback_decisions(decisions.drop_first())
        );
        assert(
            negate_callback_decisions(
                negate_callback_decisions(decisions),
            ) =~= decisions
        );
    }
}

#[verifier::external_body]
pub fn rust_1_96_call_retain_predicate<T, F: FnMut(&T) -> bool>(
    callback: &mut F,
    Ghost(decisions): Ghost<Seq<bool>>,
    Ghost(item): Ghost<T>,
    index: usize,
) -> (keep: bool)
    requires
        index < decisions.len(),
    ensures
        keep == decisions[index as int],
{
    loop { }
}

pub fn rust_1_96_drop_extracted_decision(remove: bool) {
    if remove {
        let _dropped = remove;
    }
}
"""


def extract_if_callback_source(row: model.Row) -> str:
    if not (
        row.owner["name"] == "ExtractIf"
        and row.function["name"] == "next"
    ):
        return ""
    binder, inputs, _output, where_clause = model.proxy_parts(row)
    receiver = next(item for item in inputs if item[2] == "self")
    receiver_base = re.sub(
        r"^&(?:'[^ ]+\s+)?mut\s+", "", receiver[1]
    )
    return f"""
#[verifier::external_body]
pub fn rust_1_96_call_extract_if_predicate{binder}(
    this: &{receiver_base},
) -> (remove: bool)
{where_clause}
    requires
        extract_if_pending(*this).len() > 0,
    ensures
        remove == extract_if_decisions(*this)[0],
{{
    loop {{ }}
}}
"""


def branch_arm_prelude(row: model.Row, branch: str) -> str:
    if not (
        row.owner["name"] == "ExtractIf"
        and row.function["name"] == "next"
        and branch != "0"
    ):
        return ""
    callee = generic_call_name(
        row, "rust_1_96_call_extract_if_predicate"
    )
    return (
        f"            let observed_remove = {callee}(&*this);\n"
    )


def retain_dependency_signature(
    row: model.Row,
    dependency_name: str,
    projection: Projection,
) -> str:
    binder, inputs, _output, where_clause = model.proxy_parts(row)
    receiver = next(item for item in inputs if item[2] == "self")
    return (
        f"pub fn {dependency_name}{binder}(\n"
        f"    {receiver[0]}: {receiver[1]},\n"
        "    Ghost(removals): Ghost<Seq<bool>>\n"
        f") -> (result: {projection.lower_type}){where_clause}"
    )


def retain_control_flow_body(
    row: model.Row,
    dependency_callee: str,
    *,
    mutation: bool,
) -> str:
    removal_expression = (
        "observed_decisions"
        if mutation
        else "negate_callback_decisions(observed_decisions)"
    )
    remove_expression = "keep" if mutation else "!keep"
    return f"""let ghost source_items =
        wrapped_btree_map_key_sequence(this);
    let ghost expected_decisions = retain_decisions(&f, source_items);
    proof {{
        lemma_retain_callback_observation_lengths(f, source_items);
    }}
    let mut callback = f;
    let callback_steps = rust_1_96_retain_map_len(&*this);
    let mut callback_index: usize = 0;
    let ghost mut observed_decisions: Seq<bool> = Seq::empty();
    while callback_index < callback_steps
        invariant
            callback_index <= callback_steps,
            callback_steps as nat == source_items.len(),
            expected_decisions.len() == source_items.len(),
            observed_decisions
                == expected_decisions.subrange(
                    0,
                    callback_index as int,
                ),
        decreases
            callback_steps - callback_index,
    {{
        let keep = rust_1_96_call_retain_predicate::<T, F>(
            &mut callback,
            Ghost(expected_decisions),
            Ghost(source_items[callback_index as int]),
            callback_index,
        );
        let remove = {remove_expression};
        rust_1_96_drop_extracted_decision(remove);
        proof {{
            assert(
                expected_decisions.subrange(
                    0,
                    callback_index as int,
                ).push(expected_decisions[callback_index as int])
                =~= expected_decisions.subrange(
                    0,
                    callback_index as int + 1,
                )
            );
            observed_decisions =
                observed_decisions.push(keep);
        }}
        callback_index = callback_index + 1;
    }}
    proof {{
        assert(callback_index == callback_steps);
        assert(callback_index as nat == expected_decisions.len());
        assert(
            expected_decisions.subrange(
                0,
                expected_decisions.len() as int,
            ) =~= expected_decisions
        );
        assert(observed_decisions =~= expected_decisions);
    }}
    let ghost removal_decisions = {removal_expression};
    proof {{
        lemma_callback_decision_double_negation(
            observed_decisions,
        );
    }}
    let lower: PrivateCompletion = {dependency_callee}(
        this,
        Ghost(removal_decisions),
    );"""


def extend_input_expression(
    row: model.Row,
    *,
    borrowed_parameter: bool,
) -> tuple[str, str, str]:
    binder, inputs, _output, _where_clause = model.proxy_parts(row)
    name, rust_type, _source = next(
        item for item in inputs if item[2] == "iter"
    )
    borrowed_items = "Item = &'a T" in binder
    item_type = "&'a T" if borrowed_items else "T"
    argument = name if borrowed_parameter else f"&{name}"
    expression = (
        f"into_iterator_sequence::<{item_type}, {rust_type}>({argument})"
    )
    if borrowed_items:
        expression += ".unref()"
    parameter_type = f"&{rust_type}" if borrowed_parameter else rust_type
    return name, parameter_type, expression


def extend_control_flow_source(row: model.Row) -> str:
    if row.semantic_family != "ordered_extend_transition":
        return ""
    binder, _inputs, _output, where_clause = model.proxy_parts(row)
    name, parameter_type, input_expression = extend_input_expression(
        row, borrowed_parameter=True
    )
    source_type = parameter_type.removeprefix("&")
    operation = dependency_operation(row)
    length_name = f"rust_1_96_{operation}_input_len"
    next_name = f"rust_1_96_{operation}_next_input"
    return f"""
#[verifier::external_body]
pub fn {length_name}{binder}(
    {name}: {parameter_type},
) -> (length: usize)
{where_clause}
    ensures
        length as nat == {input_expression}.len(),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {next_name}{binder}(
    source: &mut {source_type},
    Ghost(expected): Ghost<Seq<T>>,
    index: usize,
) -> (item: T)
{where_clause}
    requires
        index < expected.len(),
    ensures
        item == expected[index as int],
{{
    loop {{ }}
}}
"""


def extend_dependency_signature(
    row: model.Row,
    dependency_name: str,
    projection: Projection,
) -> str:
    binder, inputs, _output, where_clause = model.proxy_parts(row)
    receiver = next(item for item in inputs if item[2] == "self")
    return (
        f"pub fn {dependency_name}{binder}(\n"
        f"    {receiver[0]}: {receiver[1]},\n"
        "    Ghost(input): Ghost<Seq<T>>\n"
        f") -> (result: {projection.lower_type}){where_clause}"
    )


def extend_control_flow_body(
    row: model.Row,
    dependency_callee: str,
    *,
    mutation: bool,
) -> str:
    binder, _inputs, _output, _where_clause = model.proxy_parts(row)
    iterator, _parameter_type, input_expression = extend_input_expression(
        row, borrowed_parameter=False
    )
    generic_arguments = [
        item["name"]
        for item in model.parse_generic_declarations(binder)
        if item["kind"] != "lifetime"
    ]
    suffix = (
        f"::<{', '.join(generic_arguments)}>"
        if generic_arguments
        else ""
    )
    operation = dependency_operation(row)
    length_call = (
        f"rust_1_96_{operation}_input_len{suffix}(&{iterator})"
    )
    next_call = f"rust_1_96_{operation}_next_input{suffix}"
    applied_input = "Seq::empty()" if mutation else "observed_input"
    return f"""let ghost expected_input = {input_expression};
    let input_steps = {length_call};
    let mut source = {iterator};
    let mut input_index: usize = 0;
    let ghost mut observed_input: Seq<T> = Seq::empty();
    while input_index < input_steps
        invariant
            input_index <= input_steps,
            input_steps as nat == expected_input.len(),
            observed_input
                == expected_input.subrange(0, input_index as int),
        decreases
            input_steps - input_index,
    {{
        let completion = {next_call}(
            &mut source,
            Ghost(expected_input),
            input_index,
        );
        assert(completion.completed);
        proof {{
            assert(
                expected_input.subrange(
                    0,
                    input_index as int,
                ).push(expected_input[input_index as int])
                =~= expected_input.subrange(
                    0,
                    input_index as int + 1,
                )
            );
            observed_input =
                observed_input.push(expected_input[input_index as int]);
        }}
        input_index = input_index + 1;
    }}
    proof {{
        assert(input_index == input_steps);
        assert(input_index as nat == expected_input.len());
        assert(
            expected_input.subrange(
                0,
                expected_input.len() as int,
            ) =~= expected_input
        );
        assert(observed_input =~= expected_input);
    }}
    let lower: PrivateCompletion = {dependency_callee}(
        this,
        Ghost({applied_input}),
    );"""


def extract_if_constructor_body(*, mutation: bool) -> str:
    pending = "Seq::empty()" if mutation else "lower.pending@"
    remaining = (
        "Seq::empty()"
        if mutation
        else (
            "retain_selected(lower.pending@, "
            "retain_decisions_from(pred, lower.pending@))"
        )
    )
    return f"""proof {{
        lemma_retain_callback_observation_lengths(pred, lower.pending@);
    }}
    let constructed = MapExtractIfState {{
        set: Ghost(lower.set@),
        pending: Ghost({pending}),
        remaining: Ghost({remaining}),
        callback_count: Ghost(0nat),
        predicate_state: Ghost(pred),
        initial_set: Ghost(lower.set@),
        yielded: Ghost(Seq::empty()),
        drop_valid: lower.drop_valid,
        panic_valid: lower.panic_valid,
        marker: lower.marker,
    }};
    rust_1_96_project_extract_if_result::<T, R, F, A>(constructed)"""


def adapter_constructor_body(
    row: model.Row,
    projection: Projection,
    *,
    mutation: bool,
) -> str:
    state = (
        EMPTY_ADAPTER_STATE_EXPRESSION
        if mutation
        and row.semantic_family in EMPTY_ADAPTER_STATE_MUTATION_FAMILIES
        else "lower.state"
    )
    remaining = "Ghost(Seq::empty())" if mutation else "lower.remaining"
    projected = projection.body_expression.replace("lower", "constructed")
    return f"""let constructed = MapSetAdapterState {{
        state: {state},
        remaining: {remaining},
        valid: true,
        marker: lower.marker,
    }};
    {projected}"""


def set_constructor_body(
    projection: Projection,
    *,
    mutation: bool,
) -> str:
    keys = "Ghost(Seq::empty())" if mutation else "lower.keys"
    projected = projection.body_expression.replace("lower", "constructed")
    return f"""let constructed = MapSetResultState {{
        keys: {keys},
        valid: true,
    }};
    {projected}"""


def dependency_contract_lines(
    row: model.Row,
    projection: Projection,
) -> list[str]:
    """Return a source-operation contract without consulting the public clauses."""
    family = row.semantic_family
    name = row.function["name"]
    owner = row.owner["name"]
    guard = "(obeys_cmp::<T>()) ==> "
    left_sequence = "wrapped_btree_map_key_sequence(this)"
    other_sequence = "wrapped_btree_map_key_sequence(other)"

    if union_left_biased_next(row):
        old_state = "union_inner_state(*old(this))"
        return [
            "option_ref_matches(project_map_entry(result.left), "
            f"merge_next_step({old_state}).left)",
            "option_ref_matches(project_map_entry(result.right), "
            f"merge_next_step({old_state}).right)",
            f"result.state@ == merge_next_step({old_state}).state",
            "union_inner_state(*final(this)) == result.state@",
            "union_inner_state_law(*final(this)) == result.valid",
            "result.valid",
        ]

    if source_owned_adapter_loop(row):
        if owner == "Difference":
            return [
                "source_branch == "
                "difference_source_state(*this).variant as u8",
                "project_map_entry(result).is_some() <==> "
                "difference_source_state(*old(this)).first.len() > 0",
                "project_map_entry(result).is_some() <==> "
                "difference_source_state(*this).second.len() > 0",
                "result.value == left.cmp_spec(right)",
                "project_map_entry(result).is_some() <==> "
                "difference_source_state(*old(this)).second.len() > 0",
                "result.value == seq_contains_cmp("
                "difference_source_state(*this).lookup, *value)",
                "difference_source_state_law(*final(this))",
            ]
        if owner == "SymmetricDifference":
            old_state = (
                "symmetric_difference_source_state(*old(this))"
            )
            return [
                "option_ref_matches(project_map_entry(result.left), "
                f"merge_next_step({old_state}).left)",
                "option_ref_matches(project_map_entry(result.right), "
                f"merge_next_step({old_state}).right)",
                "symmetric_difference_source_state(*final(this)) "
                f"== merge_next_step({old_state}).state",
                "symmetric_difference_source_state_law(*final(this))",
            ]
        if owner == "Intersection":
            return [
                "source_branch == "
                "intersection_source_state(*this).variant as u8",
                "project_map_entry(result).is_some() <==> "
                "intersection_source_state(*old(this)).first.len() > 0",
                "project_map_entry(result).is_some() <==> "
                "intersection_source_state(*old(this)).second.len() > 0",
                "result.value == left.cmp_spec(right)",
                "result.value == seq_contains_cmp("
                "intersection_source_state(*this).lookup, *value)",
                "option_ref_matches(project_map_entry(result), "
                "intersection_source_state(*old(this)).answer)",
                "intersection_source_state_law(*final(this))",
            ]
        raise RuntimeError(
            f"{row.target_id}: missing source-loop dependency contract"
        )

    if (
        requires_selected_public_composition(row)
        and family == "difference_adapter_construction"
    ):
        return [
            "result.valid",
            "result.state@ == source_state",
            f"{guard}(result.remaining@.unref() == difference_sequence("
            "self_source.unref(), other_source.unref()))",
            f"{guard}(result.remaining@.unref().to_set() == "
            "self_source.unref().to_set().difference("
            "other_source.unref().to_set()))",
            f"{guard}(increasing_seq(result.remaining@.unref()))",
            f"{guard}(result.remaining@.no_duplicates())",
        ]
    if (
        requires_selected_public_composition(row)
        and family == "intersection_adapter_construction"
    ):
        return [
            "result.valid",
            "result.state@ == source_state",
            "result.marker@ == answer",
            f"{guard}(result.remaining@.unref() == "
            "intersection_source_sequence("
            "self_source.unref(), other_source.unref()))",
            f"{guard}(result.remaining@.unref().to_set() == "
            "self_source.unref().to_set().intersect("
            "other_source.unref().to_set()))",
            f"{guard}(increasing_seq(result.remaining@.unref()))",
            f"{guard}(result.remaining@.no_duplicates())",
        ]
    if (
        requires_selected_public_composition(row)
        and family
        in {
            "symmetric_difference_adapter_construction",
            "union_adapter_construction",
        }
    ):
        sequence = (
            "symmetric_difference_sequence"
            if family == "symmetric_difference_adapter_construction"
            else "union_sequence"
        )
        set_expression = (
            "self_source.unref().to_set().union("
            "other_source.unref().to_set()).difference("
            "self_source.unref().to_set().intersect("
            "other_source.unref().to_set()))"
            if family == "symmetric_difference_adapter_construction"
            else (
                "self_source.unref().to_set().union("
                "other_source.unref().to_set())"
            )
        )
        return [
            "result.valid",
            f"{guard}(result.remaining@.unref() == {sequence}("
            "self_source.unref(), other_source.unref()))",
            f"{guard}(result.remaining@.unref().to_set() "
            f"== {set_expression})",
            f"{guard}(increasing_seq(result.remaining@.unref()))",
            f"{guard}(result.remaining@.no_duplicates())",
            f"{guard}(result.state@ == merge_initial_state("
            "self_source.unref(), other_source.unref()))",
        ]
    selected_terminal = terminal_override_selected_method(row)
    if selected_terminal is not None:
        return terminal_selected_observations(row, source="source")

    if requires_selected_public_composition(row) and family not in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        if name == "is_disjoint":
            return [
                "project_map_entry(result).is_none() <==> "
                "intersection_remaining(*old(iter)).len() == 0"
            ]
        if name == "is_empty":
            return ["result.value == (observed_len == 0)"]
        if name in {"is_subset", "is_superset"}:
            return [
                "project_map_entry(result).is_some()",
                "match project_map_entry(result) { Some(value) => "
                "*value == source[index as int], None => false }",
            ]
        if name == "retain":
            return [
                "result.consumed",
                "result.retained@ == retain_selected(source, keeps)",
                "result.callback_count@ == source.len()",
            ]
        if row.target_id == "049_BTreeSet_Extend_extend_2153":
            return [
                "result.completed",
                f"{guard}(wrapped_btree_map_key_sequence(final(set)) "
                "== extend_sequence("
                "wrapped_btree_map_key_sequence(old(set)), input.items@))",
                f"{guard}(wrapped_btree_map_keys(final(set)) "
                "== wrapped_btree_map_key_sequence(final(set)).to_set())",
                f"{guard}(increasing_seq("
                "wrapped_btree_map_key_sequence(final(set))))",
            ]
        if row.trait == "Extend":
            return [
                "result.completed",
                f"{guard}(wrapped_btree_map_key_sequence(final(set)) "
                "== insert_keep_existing("
                "wrapped_btree_map_key_sequence(old(set)), value))",
                f"{guard}(wrapped_btree_map_keys(final(set)) "
                "== wrapped_btree_map_key_sequence(final(set)).to_set())",
                f"{guard}(increasing_seq("
                "wrapped_btree_map_key_sequence(final(set))))",
            ]
        if row.trait == "IntoIterator":
            return [
                "result.valid",
                "result.remaining@ == iter_remaining(source)",
                "result.remaining@.unref() "
                "== wrapped_btree_map_key_sequence(set)",
                "increasing_seq(wrapped_btree_map_key_sequence(set))",
            ]
        if row.trait == "Default":
            return [
                "result.valid",
                "result.keys@.to_set() == source@",
            ]
        if row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}:
            remaining = {
                "Sub": "difference_remaining",
                "BitXor": "symmetric_difference_remaining",
                "BitAnd": "intersection_remaining",
                "BitOr": "union_remaining",
            }[row.trait]
            return [
                "result.valid",
                f"{guard}(result.keys@ == clone_sequence("
                f"{remaining}(*iter).unref()))",
                f"{guard}(clone_sequence_preserves_values("
                f"{remaining}(*iter).unref()) ==> "
                f"(result.keys@.to_set() == "
                f"{remaining}(*iter).unref().to_set()))",
                f"{guard}(increasing_seq({remaining}(*iter).unref()))",
            ]
        if row.trait == "Debug":
            return [
                "*final(f) == apply_debug_shape(*old(f), "
                "selected_iter_debug_shape(*iter)).0",
                "result.value == apply_debug_shape(*old(f), "
                "selected_iter_debug_shape(*iter)).1",
                "selected_iter_debug_shape_law(*iter)",
                "increasing_seq(iter_remaining(*iter).unref())",
            ]

    if family == "ordered_set_hash":
        return [
            "result.completed",
            "*final(state) == apply_set_hash(*old(state), "
            f"{left_sequence}.len() as nat, {left_sequence})",
        ]
    if family == "set_equality":
        return [
            "(result.value) == seq_eq_spec("
            f"{left_sequence}, {other_sequence})"
        ]
    if family == "ordered_set_comparison":
        operation = (
            "seq_lex_partial_cmp"
            if row.trait == "PartialOrd"
            else "seq_lex_cmp"
        )
        law = (
            "T::obeys_partial_cmp_spec()"
            if row.trait == "PartialOrd"
            else "obeys_cmp::<T>()"
        )
        body = f"(result.value) == {operation}({left_sequence}, {other_sequence})"
        if row.trait == "Ord":
            body = f"obeys_cmp::<T>() ==> ({body})"
        return [f"({law}) ==> ({body})"]
    if family == "set_clone_transition":
        if name == "clone":
            return [
                "result.valid",
                "result.keys@.to_set() == wrapped_btree_map_keys(this)",
            ]
        return [
            "result.completed",
            "wrapped_btree_map_key_sequence(final(this)) "
            "== clone_sequence(wrapped_btree_map_key_sequence(source))",
            "clone_sequence_preserves_values("
            "wrapped_btree_map_key_sequence(source)) ==> "
            "(wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(source))",
        ]
    if family == "ordered_debug_format":
        return _authored_debug_contract(row)
    if family == "exact_vstd_transition":
        return _authored_exact_vstd_contract(row)
    if family == "ordered_range_construction":
        return [
            "result.valid",
            "(obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> "
            "(range_bounds_law(&range))",
            "(obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> "
            "(result.remaining@.unref() == range_sequence("
            f"{left_sequence}, &range))",
            "(obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> "
            "(result.remaining@.unref().to_set().subset_of("
            "wrapped_btree_map_keys(this)))",
            "(obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> "
            "(increasing_seq(result.remaining@.unref()))",
        ]
    if family in {
        "difference_adapter_construction",
        "symmetric_difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
    }:
        return _authored_adapter_construction_contract(row)
    if family == "set_relation_observer":
        relation = {
            "is_disjoint": (
                "(wrapped_btree_map_keys(this).intersect("
                "wrapped_btree_map_keys(other)).len() == 0)"
            ),
            "is_subset": (
                "wrapped_btree_map_keys(this).subset_of("
                "wrapped_btree_map_keys(other))"
            ),
            "is_superset": (
                "wrapped_btree_map_keys(other).subset_of("
                "wrapped_btree_map_keys(this))"
            ),
        }[name]
        return [f"{guard}((result.value) == {relation})"]
    if family == "ordered_endpoint_observer":
        selected = (
            f"{left_sequence}[0]"
            if name == "first"
            else f"{left_sequence}.last()"
        )
        return [
            f"{guard}(project_map_entry(result).is_some() "
            f"<==> {left_sequence}.len() > 0)",
            f"{guard}(match project_map_entry(result) {{ "
            f"Some(item) => *item == {selected}, None => true }})",
        ]
    if family == "ordered_endpoint_removal":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        selected = (
            f"{old_sequence}[0]"
            if name == "pop_first"
            else f"{old_sequence}.last()"
        )
        remainder = (
            f"{old_sequence}.drop_first()"
            if name == "pop_first"
            else f"{old_sequence}.drop_last()"
        )
        return [
            f"{guard}(project_map_entry(result).is_some() "
            f"<==> {old_sequence}.len() > 0)",
            f"{guard}(project_map_entry(result) == "
            f"if {old_sequence}.len() > 0 "
            f"{{ Some({selected}) }} else {{ None }})",
            f"{guard}(wrapped_btree_map_key_sequence(final(this)) == "
            f"if {old_sequence}.len() > 0 "
            f"{{ {remainder} }} else {{ {old_sequence} }})",
            f"{guard}(match project_map_entry(result) {{ Some(item) => "
            "wrapped_btree_map_keys(final(this)) == "
            "wrapped_btree_map_keys(old(this)).remove(item), "
            "None => wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)) })",
        ]
    if family == "representative_replacement":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        return [
            f"{guard}((result.key) == cmp_equal_representative("
            f"{old_sequence}, value))",
            f"{guard}(wrapped_btree_map_key_sequence(final(this)) "
            f"== replace_representative({old_sequence}, value))",
            f"{guard}(wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)).insert(value))",
        ]
    if family == "borrowed_representative_removal":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        borrowed_guard = "(obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> "
        return [
            f"{borrowed_guard}(project_map_entry(result) == "
            f"borrowed_representative({old_sequence}, value))",
            f"{borrowed_guard}(wrapped_btree_map_key_sequence(final(this)) "
            f"== remove_borrowed_representative({old_sequence}, value))",
            f"{borrowed_guard}(match project_map_entry(result) {{ "
            "Some(item) => sets_borrowed_key_to_key("
            "wrapped_btree_map_keys(old(this)), value, &item) "
            "&& sets_differ_by_borrowed_key("
            "wrapped_btree_map_keys(old(this)), "
            "wrapped_btree_map_keys(final(this)), value), "
            "None => !set_contains_borrowed_key("
            "wrapped_btree_map_keys(old(this)), value) "
            "&& wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)) })",
        ]
    if family == "ordered_callback_retain":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        return [
            "result.completed",
            f"{guard}(wrapped_btree_map_key_sequence(final(this)) "
            "== retain_selected("
            f"{old_sequence}, negate_callback_decisions(removals)))",
            f"{guard}(wrapped_btree_map_keys(final(this)) "
            "== retain_selected("
            f"{old_sequence}, negate_callback_decisions(removals)).to_set())",
        ]
    if family == "set_append_transition":
        return [
            "result.completed",
            f"{guard}(wrapped_btree_map_key_sequence(final(other)) "
            "== Seq::empty())",
            f"{guard}(wrapped_btree_map_keys(final(other)) "
            "== Set::empty())",
            f"{guard}(wrapped_btree_map_key_sequence(final(this)) "
            "== union_sequence("
            "wrapped_btree_map_key_sequence(old(this)), "
            "wrapped_btree_map_key_sequence(old(other))))",
            f"{guard}(wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)).union("
            "wrapped_btree_map_keys(old(other))))",
        ]
    if family == "ordered_set_partition":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        borrowed_guard = "(obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> "
        return [
            "result.valid",
            f"{borrowed_guard}(wrapped_btree_map_key_sequence(final(this)) "
            f"== split_before({old_sequence}, value))",
            f"{borrowed_guard}(result.keys@ "
            f"== split_at_or_after({old_sequence}, value))",
            f"{borrowed_guard}(wrapped_btree_map_keys(final(this)).union("
            "result.keys@.to_set()) == "
            "wrapped_btree_map_keys(old(this)))",
            f"{borrowed_guard}(wrapped_btree_map_keys(final(this)).intersect("
            "result.keys@.to_set()).len() == 0)",
            f"{borrowed_guard}(wrapped_btree_map_keys(final(this)).len() "
            "+ result.keys@.to_set().len() "
            "== wrapped_btree_map_keys(old(this)).len())",
        ]
    if family == "extract_if_construction":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        return [
            f"{guard}(range_bounds_law(&range))",
            f"{guard}(wrapped_btree_map_keys(final(this)) "
            "== wrapped_btree_map_keys(old(this)))",
            f"{guard}(result.set@ == wrapped_btree_map_keys(old(this)))",
            f"{guard}(result.pending@ == "
            f"range_sequence({old_sequence}, &range))",
            f"{guard}(increasing_seq(result.pending@))",
            f"{guard}(result.drop_valid)",
            f"{guard}(result.panic_valid)",
        ]
    if family == "sorted_deduplicating_conversion":
        input_sequence = (
            "arr@"
            if "arr" in {source for _name, _type, source in model.proxy_parts(row)[1]}
            else "into_iterator_sequence::<T, I>(&iter)"
        )
        sorted_sequence = f"stable_sorted_sequence({input_sequence})"
        return [
            f"{guard}({sorted_sequence}.len() == {input_sequence}.len())",
            f"{guard}({sorted_sequence}.to_multiset() "
            f"== {input_sequence}.to_multiset())",
            f"{guard}(nondecreasing_sequence({sorted_sequence}))",
            f"{guard}(stable_tie_order("
            f"{input_sequence}, {sorted_sequence}))",
            f"{guard}(result.keys@ "
            f"== dedup_last_sorted({sorted_sequence}))",
            f"{guard}(result.keys@.to_set() "
            f"== {input_sequence}.to_set())",
        ]
    if family == "ordered_iterator_construction":
        borrowed = projection.kind == "borrowed_iter"
        source = "this" if borrowed else "&this"
        remaining = (
            "result.remaining@.unref()"
            if borrowed
            else "result.remaining@"
        )
        return [
            "result.valid",
            f"{remaining}.to_set() == wrapped_btree_map_keys({source})",
            f"{remaining} == wrapped_btree_map_key_sequence({source})",
            f"increasing_seq(wrapped_btree_map_key_sequence({source}))",
        ]
    if family == "ordered_iterator_forward_step":
        return _authored_iterator_step_contract(row, backwards=False)
    if family == "ordered_iterator_backward_step":
        return _authored_iterator_step_contract(row, backwards=True)
    if family == "adapter_specific_size_hint":
        return _authored_size_hint_contract(row)
    if family == "ordered_extend_transition":
        old_sequence = "wrapped_btree_map_key_sequence(old(this))"
        extended = f"extend_sequence({old_sequence}, input)"
        return [
            "result.completed",
            f"{guard}(wrapped_btree_map_key_sequence(final(this)) "
            f"== {extended})",
            f"{guard}(wrapped_btree_map_keys(final(this)) "
            f"== {extended}.to_set())",
            f"{guard}(increasing_seq("
            "wrapped_btree_map_key_sequence(final(this))))",
        ]
    if family == "owned_set_operation":
        sequence_function, set_expression = {
            "Sub": (
                "difference_sequence",
                "wrapped_btree_map_keys(this).difference("
                "wrapped_btree_map_keys(rhs))",
            ),
            "BitXor": (
                "symmetric_difference_sequence",
                "wrapped_btree_map_keys(this).union("
                "wrapped_btree_map_keys(rhs)).difference("
                "wrapped_btree_map_keys(this).intersect("
                "wrapped_btree_map_keys(rhs)))",
            ),
            "BitAnd": (
                "intersection_source_sequence",
                "wrapped_btree_map_keys(this).intersect("
                "wrapped_btree_map_keys(rhs))",
            ),
            "BitOr": (
                "union_sequence",
                "wrapped_btree_map_keys(this).union("
                "wrapped_btree_map_keys(rhs))",
            ),
        }[row.trait]
        sequence = (
            f"{sequence_function}(wrapped_btree_map_key_sequence(this), "
            "wrapped_btree_map_key_sequence(rhs))"
        )
        return [
            "result.valid",
            f"{guard}(result.keys@ == clone_sequence({sequence}))",
            f"{guard}(clone_sequence_preserves_values({sequence}) "
            f"==> (result.keys@.to_set() == {set_expression}))",
            f"{guard}(increasing_seq({sequence}))",
        ]
    if family == "ordered_iterator_clone":
        prefix = {
            "Iter": "iter",
            "Range": "range",
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
        }[owner]
        remaining = _private_cursor_name(row, f"{prefix}_remaining")
        lines = [f"result.remaining@ == {remaining}(*this)"]
        if owner in {"Iter", "Range"}:
            lines.insert(0, "result.valid")
        else:
            state = _private_cursor_name(
                row, f"{prefix}_source_state"
            )
            lines.append(f"result.state@ == {state}(*this)")
        return lines
    if family == "ordered_iterator_exact_len":
        prefix = "iter" if owner == "Iter" else "into_iter"
        remaining = _private_cursor_name(row, f"{prefix}_remaining")
        return [f"(result.value) as nat == {remaining}(*this).len()"]
    if family == "ordered_iterator_empty_default":
        return ["result.valid", "result.remaining@ == Seq::empty()"]
    if family == "ordered_iterator_terminal_selection":
        prefix = {
            "Iter": "iter",
            "Range": "range",
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
        }[owner]
        remaining = _private_cursor_name(row, f"{prefix}_remaining")
        sequence = f"{remaining}(this)"
        selected = (
            f"{sequence}.last()"
            if name in {"last", "max"}
            else f"{sequence}[0]"
        )
        law = (
            "(obeys_cmp::<T>()) ==> "
            if owner in {
                "Difference",
                "SymmetricDifference",
                "Intersection",
                "Union",
            }
            else "(obeys_cmp::<&'a T>()) ==> "
            if name in {"min", "max"}
            else ""
        )
        return [
            f"{law}(project_map_entry(result) == "
            f"if {sequence}.len() > 0 "
            f"{{ Some({selected}) }} else {{ None }})"
        ]
    raise RuntimeError(
        f"{row.target_id}: missing independently authored lower contract"
    )


def mutation_clause_index(row: model.Row) -> int:
    lines = contract_lines(row)
    principal_tokens = (
        "result ==",
        "result@",
        "final(",
        "remaining(&result)",
        "remaining(&result)",
        "extract_if_set(&result)",
        "btree_set_sequence(&result)",
        "*final(",
    )
    for index, line in enumerate(lines):
        if any(token in line for token in principal_tokens):
            return index
    return 0


def mutation_clause(row: model.Row) -> str:
    return contract_lines(row)[mutation_clause_index(row)]


def mutation_descriptor(row: model.Row) -> dict[str, object]:
    operation = dependency_operation(row)
    projection = projection_for(row, model.proxy_parts(row)[2])
    if union_left_biased_next(row):
        mutation_id = "union_iterator_next_left_biased_or_fallback_omitted"
        kind = "wrong_left_biased_selection"
    elif source_owned_adapter_loop(row):
        if row.owner["name"] == "SymmetricDifference":
            mutation_id = f"{operation}_duplicate_branch_reversed"
            kind = "wrong_duplicate_handling"
        else:
            mutation_id = f"{operation}_comparison_operands_reversed"
            kind = "wrong_source_comparison"
    elif retains_adapter_source_loop(row):
        mutation_id = f"{operation}_loop_progress_changed"
        kind = "wrong_source_loop_control"
    elif adapter_loop_control_mutation_required(row):
        mutation_id = f"{operation}_branch_dispatch_changed"
        kind = "wrong_source_control"
    elif row.semantic_family in {
        "difference_adapter_construction",
        "symmetric_difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
    } or (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_superset"
    ):
        mutation_id = f"{operation}_selected_receiver_changed"
        kind = "wrong_selected_receiver"
    elif (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_subset"
    ):
        mutation_id = f"{operation}_length_branch_reversed"
        kind = "wrong_source_control"
    elif row.semantic_family == "sorted_deduplicating_conversion":
        mutation_id = f"{operation}_empty_branch_forced"
        kind = "wrong_source_control"
    elif row.target_id == "049_BTreeSet_Extend_extend_2153":
        mutation_id = f"{operation}_selected_call_replaced"
        kind = "wrong_selected_call"
    elif terminal_override_selected_method(row) is not None:
        mutation_id = f"{operation}_selected_call_duplicated"
        kind = "wrong_selected_call_count"
    elif (
        row.semantic_family == "ordered_callback_retain"
        and requires_selected_public_composition(row)
    ):
        mutation_id = f"{operation}_consumption_omitted"
        kind = "omitted_extract_if_consumption"
    else:
        mutation_id = f"{operation}_executable_projection_changed"
        kind = "executable_source_projection_or_call"
    return {
        "mutation_id": mutation_id,
        "kind": kind,
        "source_step": (
            "left_biased_option_or"
            if union_left_biased_next(row)
            else operation
        ),
        "original_fragment": mutation_original_fragment(row, projection),
        "mutated_fragment": mutation_changed_fragment(row, projection),
        "affected_clause_indices": (
            [1]
            if union_left_biased_next(row)
            else [
                index + 1 for index in range(len(contract_lines(row))
            )]
        ),
    }


def projection_helper_required(projection: Projection) -> bool:
    return projection.kind not in {"direct", "completion"}


LITERAL_EXTERNAL_BODY_CATEGORIES = (
    "target",
    "completeness",
    "dependency",
    "helper",
    "harness",
)


def literal_external_body_function_names(source: str) -> list[str]:
    return re.findall(
        r"#\[verifier::external_body\]\s+pub\s+"
        r"(?:(?:open|closed|proof|exec|spec|unsafe)\s+)*fn\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        source,
    )


def literal_external_body_counts(row: model.Row) -> dict[str, int]:
    source = implementation_source(row)
    functions = literal_external_body_function_names(source)
    dependency_names = set(dependency_function_names(row))
    dependency = sum(name in dependency_names for name in functions)
    helper = len(functions) - dependency
    return {
        "target": 0,
        "completeness": 0,
        "dependency": dependency,
        "helper": helper,
        "harness": dependency + helper,
    }


def aggregate_literal_external_body_counts(
    rows: list[model.Row],
) -> dict[str, int]:
    totals = {category: 0 for category in LITERAL_EXTERNAL_BODY_CATEGORIES}
    for row in rows:
        for category, count in literal_external_body_counts(row).items():
            totals[category] += count
    return totals


def literal_external_body_count(row: model.Row) -> int:
    return literal_external_body_counts(row)["harness"]


def projection_helper_source(row: model.Row, projection: Projection) -> str:
    if projection.kind == "set_state":
        return """
#[verifier::external_body]
pub fn rust_1_96_project_set_result<T, A: Allocator + Clone>(
    lower: MapSetResultState<T>,
) -> (result: BTreeSet<T, A>)
    ensures
        lower.valid ==> btree_set_sequence(result) == lower.keys@,
        lower.valid ==> result@ == lower.keys@.to_set(),
{
    loop { }
}
"""
    if projection.kind == "set_state_global":
        return """
#[verifier::external_body]
pub fn rust_1_96_project_global_set_result<T>(
    lower: MapSetResultState<T>,
) -> (result: BTreeSet<T>)
    ensures
        lower.valid ==> btree_set_sequence(result) == lower.keys@,
        lower.valid ==> result@ == lower.keys@.to_set(),
{
    loop { }
}
"""
    if projection.kind == "borrowed_iter":
        if (
            row.owner["name"] == "BTreeSet"
            and row.function["name"] == "iter"
        ):
            return """
#[verifier::external_body]
pub fn rust_1_96_project_iter_result<
    'a,
    T,
    A: Allocator + Clone,
>(
    source: &'a BTreeSet<T, A>,
    lower: MapBorrowedIteratorState<'a, T>,
) -> (result: Iter<'a, T>)
    ensures
        lower.valid ==> iter_remaining(result) == lower.remaining@,
        lower.valid ==> result == spec_btree_keys_iter(source),
        lower.valid ==> IteratorSpec::decrease(&result) is Some,
        lower.valid ==> IteratorSpec::initial_value_relation(&result, &result),
{
    loop { }
}
"""
        return """
#[verifier::external_body]
pub fn rust_1_96_project_iter_result<'a, T>(
    lower: MapBorrowedIteratorState<'a, T>,
) -> (result: Iter<'a, T>)
    ensures
        lower.valid ==> iter_remaining(result) == lower.remaining@,
{
    loop { }
}
"""
    if projection.kind == "borrowed_range":
        return """
#[verifier::external_body]
pub fn rust_1_96_project_range_result<'a, T>(
    lower: MapBorrowedIteratorState<'a, T>,
) -> (result: Range<'a, T>)
    ensures
        lower.valid ==> range_remaining(result) == lower.remaining@,
{
    loop { }
}
"""
    if projection.kind == "owned_iter":
        return """
#[verifier::external_body]
pub fn rust_1_96_project_into_iter_result<T, A: Allocator + Clone>(
    lower: MapOwnedIteratorState<T>,
) -> (result: IntoIter<T, A>)
    ensures
        lower.valid ==> into_iter_remaining(result) == lower.remaining@,
{
    loop { }
}
"""
    if projection.kind == "set_adapter":
        owner = (
            row.owner["name"]
            if row.owner["name"] != "BTreeSet"
            else {
                "difference": "Difference",
                "symmetric_difference": "SymmetricDifference",
                "intersection": "Intersection",
                "union": "Union",
            }[row.function["name"]]
        )
        if owner == "Difference":
            law = (
                "        difference_source_state_law(result) == lower.valid,\n"
                if any(
                    "difference_source_state_law(result)" in line
                    for line in contract_lines(row)
                )
                else ""
            )
            where = "    where T: Ord\n" if law else ""
            return f"""
#[verifier::external_body]
pub fn rust_1_96_project_difference_result<'a, T, A: Allocator + Clone>(
    lower: MapSetAdapterState<'a, T>,
) -> (result: Difference<'a, T, A>)
{where}    ensures
        difference_remaining(result) == lower.remaining@,
        difference_source_state(result) == lower.state@,
{law}{{
    loop {{ }}
}}
"""
        if owner == "Intersection":
            law = (
                "        intersection_source_state_law(result) == lower.valid,\n"
                if any(
                    "intersection_source_state_law(result)" in line
                    for line in contract_lines(row)
                )
                else ""
            )
            where = "    where T: Ord\n" if law else ""
            return f"""
#[verifier::external_body]
pub fn rust_1_96_project_intersection_result<'a, T, A: Allocator + Clone>(
    lower: MapSetAdapterState<'a, T>,
) -> (result: Intersection<'a, T, A>)
{where}    ensures
        intersection_remaining(result) == lower.remaining@,
        intersection_source_state(result) == lower.state@,
{law}{{
    loop {{ }}
}}
"""
        if owner == "SymmetricDifference":
            law = (
                "        symmetric_difference_source_state_law(result) == lower.valid,\n"
                if any(
                    "symmetric_difference_source_state_law(result)" in line
                    for line in contract_lines(row)
                )
                else ""
            )
            where = "    where T: Ord\n" if law else ""
            return f"""
#[verifier::external_body]
pub fn rust_1_96_project_symmetric_difference_result<'a, T>(
    lower: MapSetAdapterState<'a, T>,
) -> (result: SymmetricDifference<'a, T>)
{where}    ensures
        symmetric_difference_remaining(result) == lower.remaining@,
        symmetric_difference_source_state(result) == lower.state@,
{law}{{
    loop {{ }}
}}
"""
        law = (
            "        union_source_state_law(result) == lower.valid,\n"
            if any(
                "union_source_state_law(result)" in line
                for line in contract_lines(row)
            )
            else ""
        )
        where = "    where T: Ord\n" if law else ""
        return f"""
#[verifier::external_body]
pub fn rust_1_96_project_union_result<'a, T>(
    lower: MapSetAdapterState<'a, T>,
) -> (result: Union<'a, T>)
{where}    ensures
        union_remaining(result) == lower.remaining@,
        union_source_state(result) == lower.state@,
{law}{{
    loop {{ }}
}}
"""
    if projection.kind == "extract_state":
        return """
#[verifier::external_body]
pub fn rust_1_96_project_extract_if_result<
    'a,
    T: Ord,
    R: core::ops::RangeBounds<T>,
    F: FnMut(&T) -> bool,
    A: Allocator + Clone,
>(
    lower: MapExtractIfState<'a, T, F>,
) -> (result: ExtractIf<'a, T, R, F, A>)
    ensures
        extract_if_set(result) == lower.set@,
        extract_if_pending(result) == lower.pending@,
        extract_if_remaining(result) == lower.remaining@,
        extract_if_callback_count(result) == lower.callback_count@,
        extract_if_predicate_state(result) == lower.predicate_state@,
        extract_if_initial_set(result) == lower.initial_set@,
        extract_if_yielded(result) == lower.yielded@,
        extract_if_drop_law(result) == lower.drop_valid,
        extract_if_panic_law(result) == lower.panic_valid,
{
    loop { }
}
"""
    raise RuntimeError(
        f"missing lower representation projector for {row.target_id}: "
        f"{projection.kind}"
    )


def adapter_source_comparison_call_fragment(
    row: model.Row,
    *,
    reverse_operands: bool = False,
) -> str:
    base = dependency_function_name(row)
    owner = row.owner["name"]
    if owner == "SymmetricDifference":
        callee = generic_call_name(row, base)
        arguments = "this"
    else:
        callee = generic_call_name(row, f"{base}_stitch_compare")
        argument_pairs = {
            "Difference": ("self_next", "other_next"),
            "Intersection": ("a_next", "b_next"),
        }
        left, right = argument_pairs[owner]
        if reverse_operands:
            left, right = right, left
        arguments = f"{left}, {right}"
    return f"{callee}({arguments})"


def mutation_original_fragment(
    row: model.Row,
    projection: Projection,
) -> str:
    if union_left_biased_next(row):
        return "let answer = a_next.or(b_next);"
    if source_owned_adapter_loop(row):
        if row.owner["name"] == "SymmetricDifference":
            return "if a_next.and(b_next).is_none() {"
        return adapter_source_comparison_call_fragment(row)
    if retains_adapter_source_loop(row):
        return (
            "completed_source_steps =\n"
            "            completed_source_steps + 1;"
        )
    if adapter_loop_control_mutation_required(row):
        inputs = signature_parts(row, "implementation")[0]
        _selector_source, selector_call = branch_selector_source_and_call(
            row,
            inputs,
        )
        return f"let source_branch = {selector_call};"
    if terminal_override_selected_method(row) is not None:
        return (
            f"let lower = {dependency_call_name(row)}(&mut source);"
        )
    if row.semantic_family == "difference_adapter_construction":
        return "let other_min = rust_1_96_selected_first(other);"
    if row.semantic_family == "intersection_adapter_construction":
        return "let other_max = rust_1_96_selected_last(other);"
    if row.semantic_family in {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }:
        return "let other_iter = rust_1_96_selected_iter(other);"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_subset"
    ):
        return "if this_len > other_len {"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_superset"
    ):
        return "rust_1_96_selected_is_subset_source(other, this)"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_disjoint"
    ):
        return "next.is_none()"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_empty"
    ):
        return "        observed_len,"
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "IntoIterator"
        and row.function["name"] == "into_iter"
        and requires_selected_public_composition(row)
    ):
        return "valid: lower.valid"
    if row.owner["name"] == "BTreeSet" and row.trait == "Default":
        return "valid: lower.valid"
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}
    ):
        return "keys: lower.keys"
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        return "let completion = rust_1_96_selected_owned_extend::<T, A>("
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "Extend"
    ):
        return f"let completion = {dependency_function_name(row)}::<T, A>("
    if (
        row.semantic_family == "ordered_callback_retain"
        and requires_selected_public_composition(row)
    ):
        return (
            f"let consumed = {dependency_function_name(row)}"
            "::<T, F, A>("
        )
    if row.semantic_family == "ordered_callback_retain":
        return "let remove = !keep;"
    if row.semantic_family == "ordered_extend_transition":
        return "Ghost(observed_input)"
    if row.semantic_family == "extract_if_construction":
        return "pending: Ghost(lower.pending@)"
    if row.semantic_family in EMPTY_ADAPTER_STATE_MUTATION_FAMILIES:
        return "state: lower.state"
    if row.semantic_family in {
        "difference_adapter_construction",
    }:
        return "remaining: lower.remaining"
    if row.semantic_family == "sorted_deduplicating_conversion":
        inputs = signature_parts(row, "implementation")[0]
        _selector_source, selector_call = branch_selector_source_and_call(
            row,
            inputs,
        )
        return f"let source_branch = {selector_call};"
    if projection.kind == "completion":
        return f"{dependency_call_name(row)}("
    return projection.body_expression


def mutation_changed_fragment(
    row: model.Row,
    projection: Projection,
) -> str:
    if union_left_biased_next(row):
        return "let answer = a_next;"
    if source_owned_adapter_loop(row):
        if row.owner["name"] == "SymmetricDifference":
            return "if !a_next.and(b_next).is_none() {"
        return adapter_source_comparison_call_fragment(
            row,
            reverse_operands=True,
        )
    if retains_adapter_source_loop(row):
        return (
            "completed_source_steps =\n"
            "            completed_source_steps + 2;"
        )
    if adapter_loop_control_mutation_required(row):
        inputs = signature_parts(row, "implementation")[0]
        _selector_source, selector_call = branch_selector_source_and_call(
            row,
            inputs,
        )
        return (
            f"let observed_source_branch = {selector_call};\n"
            "    let source_branch = if observed_source_branch == 0 "
            "{ 1 } else { 0 };"
        )
    if terminal_override_selected_method(row) is not None:
        call = dependency_call_name(row)
        return (
            f"let _skipped = {call}(&mut source);\n"
            f"    let lower = {call}(&mut source);"
        )
    if row.semantic_family == "difference_adapter_construction":
        return "let other_min = rust_1_96_selected_first(this);"
    if row.semantic_family == "intersection_adapter_construction":
        return "let other_max = rust_1_96_selected_last(this);"
    if row.semantic_family in {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }:
        return "let other_iter = rust_1_96_selected_iter(this);"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_subset"
    ):
        return "if this_len <= other_len {"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_superset"
    ):
        return "rust_1_96_selected_is_subset_source(this, other)"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_disjoint"
    ):
        return "!next.is_none()"
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_empty"
    ):
        return "        if observed_len == 0 { 1 } else { 0 },"
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "IntoIterator"
        and row.function["name"] == "into_iter"
        and requires_selected_public_composition(row)
    ):
        return "valid: false"
    if row.owner["name"] == "BTreeSet" and row.trait == "Default":
        return "valid: false"
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}
    ):
        return "keys: Ghost(Seq::empty())"
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        return (
            "let completion = "
            "rust_1_96_drop_selected_owned_extend::<T, A>("
        )
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "Extend"
    ):
        return "let insertion_bypassed = item;"
    if (
        row.semantic_family == "ordered_callback_retain"
        and requires_selected_public_composition(row)
    ):
        return (
            "let consumed = "
            "rust_1_96_drop_selected_extract_if_unconsumed"
            "::<T, F, A>("
        )
    if row.semantic_family == "ordered_callback_retain":
        return "let remove = keep;"
    if row.semantic_family == "ordered_extend_transition":
        return "Ghost(Seq::empty())"
    if row.semantic_family == "extract_if_construction":
        return "pending: Ghost(Seq::empty())"
    if row.semantic_family in EMPTY_ADAPTER_STATE_MUTATION_FAMILIES:
        return f"state: {EMPTY_ADAPTER_STATE_EXPRESSION}"
    if row.semantic_family in {
        "difference_adapter_construction",
    }:
        return "remaining: Ghost(Seq::empty())"
    if row.semantic_family == "sorted_deduplicating_conversion":
        return "let source_branch = 0u8;"
    if projection.kind == "completion":
        return "let source_call_bypassed = ()"
    if projection.kind == "direct":
        output = model.proxy_parts(row)[2]
        if output == "bool":
            return (
                "lower.is_some()"
                if projection.body_expression == "lower.is_none()"
                else f"!({projection.body_expression})"
            )
        if output == "usize":
            return "if lower.value == 0"
        if output == "(usize, Option<usize>)":
            return "if lower.lower == 0"
        if output == "core::cmp::Ordering":
            return "match lower.value"
        if output == "Option<core::cmp::Ordering>":
            return "None"
        if output == "core::fmt::Result":
            return "Ok(())"
        return "None"
    return "let mutated_lower ="


def mutation_invalidates_projector(
    row: model.Row,
    projection: Projection,
) -> bool:
    if projection.kind in {"set_state", "set_state_global"}:
        return row.function["name"] == "new" or row.trait == "Default"
    if projection.kind == "borrowed_iter":
        return (
            row.trait == "Default"
            or (
                row.trait == "IntoIterator"
                and requires_selected_public_composition(row)
            )
            or (
                row.owner["name"] == "BTreeSet"
                and row.function["name"] == "iter"
            )
        )
    if projection.kind in {"borrowed_range", "owned_iter"}:
        return row.trait == "Default"
    return False


def mutation_body_expression(
    row: model.Row,
    projection: Projection,
) -> str:
    if projection.kind == "completion":
        return "let source_call_bypassed = ();"
    if projection.kind == "direct":
        output = model.proxy_parts(row)[2]
        if output == "bool":
            normal = projection.body_expression
            return (
                "lower.is_some()"
                if normal == "lower.is_none()"
                else f"!({normal})"
            )
        if output == "usize":
            return "if lower.value == 0 { 1 } else { 0 }"
        if output == "(usize, Option<usize>)":
            return (
                "(if lower.lower == 0 { 1 } else { 0 }, lower.upper)"
            )
        if output == "core::cmp::Ordering":
            return (
                "match lower.value { Ordering::Less => Ordering::Greater, "
                "Ordering::Equal => Ordering::Less, "
                "Ordering::Greater => Ordering::Less }"
            )
        if output == "Option<core::cmp::Ordering>":
            return "None"
        if output == "core::fmt::Result":
            return "Ok(())"
        return "None"
    if projection.kind in {"set_state", "set_state_global"}:
        keys = (
            "lower.keys"
            if mutation_invalidates_projector(row, projection)
            else "Ghost(Seq::empty())"
        )
        valid = (
            "false"
            if mutation_invalidates_projector(row, projection)
            else "lower.valid"
        )
        return (
            "let mutated_lower = MapSetResultState {\n"
            f"        keys: {keys},\n"
            f"        valid: {valid},\n"
            "    };\n"
            f"    {projection.body_expression.replace('lower', 'mutated_lower')}"
        )
    if projection.kind in {"borrowed_iter", "borrowed_range"}:
        remaining = (
            "lower.remaining"
            if mutation_invalidates_projector(row, projection)
            else "Ghost(Seq::empty())"
        )
        valid = (
            "false"
            if mutation_invalidates_projector(row, projection)
            else "lower.valid"
        )
        return (
            "let mutated_lower = MapBorrowedIteratorState {\n"
            f"        remaining: {remaining},\n"
            f"        valid: {valid},\n"
            "    };\n"
            f"    {projection.body_expression.replace('lower', 'mutated_lower')}"
        )
    if projection.kind == "owned_iter":
        remaining = (
            "lower.remaining"
            if mutation_invalidates_projector(row, projection)
            else "Ghost(Seq::empty())"
        )
        valid = (
            "false"
            if mutation_invalidates_projector(row, projection)
            else "lower.valid"
        )
        return (
            "let mutated_lower = MapOwnedIteratorState {\n"
            f"        remaining: {remaining},\n"
            f"        valid: {valid},\n"
            "    };\n"
            f"    {projection.body_expression.replace('lower', 'mutated_lower')}"
        )
    if projection.kind == "set_adapter":
        return (
            "let mutated_lower = MapSetAdapterState {\n"
            "        state: lower.state,\n"
            "        remaining: Ghost(Seq::empty()),\n"
            "        valid: lower.valid,\n"
            "        marker: lower.marker,\n"
            "    };\n"
            f"    {projection.body_expression.replace('lower', 'mutated_lower')}"
        )
    if projection.kind == "extract_state":
        return (
            "let mutated_lower = MapExtractIfState {\n"
            "        set: lower.set,\n"
            "        pending: Ghost(Seq::empty()),\n"
            "        remaining: Ghost(Seq::empty()),\n"
            "        callback_count: lower.callback_count,\n"
            "        predicate_state: lower.predicate_state,\n"
            "        initial_set: lower.initial_set,\n"
            "        yielded: lower.yielded,\n"
            "        drop_valid: lower.drop_valid,\n"
            "        panic_valid: lower.panic_valid,\n"
            "        marker: lower.marker,\n"
            "    };\n"
            f"    {projection.body_expression.replace('lower', 'mutated_lower')}"
        )
    raise RuntimeError(
        f"missing executable mutation for {row.target_id}: {projection.kind}"
    )


def branch_source_value(
    row: model.Row,
    inputs: list[tuple[str, str, str]],
) -> str:
    by_source = {
        source: (name, rust_type) for name, rust_type, source in inputs
    }
    owner = row.owner["name"]
    if owner in {
        "Difference",
        "SymmetricDifference",
        "Intersection",
        "Union",
    }:
        receiver, rust_type = by_source["self"]
        value = receiver if not rust_type.startswith("&") else f"*{receiver}"
        state = {
            "Difference": "difference_source_state",
            "SymmetricDifference": "symmetric_difference_source_state",
            "Intersection": "intersection_source_state",
            "Union": "union_source_state",
        }[owner]
        field = (
            "peeked_side"
            if owner in {"SymmetricDifference", "Union"}
            else "variant"
        )
        return f"{state}({value}).{field} as u8"
    if owner == "ExtractIf":
        receiver, rust_type = by_source["self"]
        value = receiver if not rust_type.startswith("&") else f"*{receiver}"
        return (
            f"if extract_if_pending({value}).len() == 0 "
            "{ 0u8 } else { 1u8 }"
        )
    if row.semantic_family == "difference_adapter_construction":
        left = by_source["self"][0]
        right = by_source["other"][0]
        return (
            "difference_initial_state("
            f"wrapped_btree_map_key_sequence({left}), "
            f"wrapped_btree_map_key_sequence({right})).variant as u8"
        )
    if row.semantic_family == "intersection_adapter_construction":
        left = by_source["self"][0]
        right = by_source["other"][0]
        return (
            "intersection_initial_state("
            f"wrapped_btree_map_key_sequence({left}), "
            f"wrapped_btree_map_key_sequence({right})).variant as u8"
        )
    if (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        left = by_source["self"][0]
        right = by_source["other"][0]
        left_seq = f"wrapped_btree_map_key_sequence({left})"
        right_seq = f"wrapped_btree_map_key_sequence({right})"
        return (
            f"if {left_seq}.len() > {right_seq}.len() {{ 0u8 }} "
            f"else if {left_seq}.len() == 0 {{ 1u8 }} "
            f"else if {right_seq}.len() == 0 {{ 2u8 }} "
            "else { 3u8 }"
        )
    if "iter" in by_source:
        iterator, iterator_type = by_source["iter"]
        return (
            f"if into_iterator_sequence::<T, {iterator_type}>(&{iterator})"
            ".len() == 0 { 0u8 } else { 1u8 }"
        )
    if "arr" in by_source:
        return (
            f"if {by_source['arr'][0]}@.len() == 0 "
            "{ 0u8 } else { 1u8 }"
        )
    raise RuntimeError(
        f"missing deterministic source discriminant for {row.target_id}"
    )


def implementation_operation_order(row: model.Row) -> list[str]:
    _binder, inputs, output, _where_clause = model.proxy_parts(row)
    projection = projection_for(row, output)
    if union_left_biased_next(row):
        return [
            "observe_private_cursor_before:self",
            "execute_source_call:nexts",
            "execute_source_call:a_next.or",
            "observe_private_cursor_after:self",
            "project_lower_result:left_biased_option_or",
        ]
    if source_owned_adapter_loop(row):
        prefix = {
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
        }[row.owner["name"]]
        source_operations = {
            "Difference": (
                "read_private_variant",
                "iterator_next_self",
                "iterator_peek_other",
                "compare_peeked",
                "iterator_next_other",
                "set_contains",
                "iterator_next_iterate",
            ),
            "SymmetricDifference": (
                "merge_nexts_with_comparator",
                "test_duplicate_pair",
                "left_biased_option_or",
            ),
            "Intersection": (
                "read_private_variant",
                "iterator_next_first",
                "iterator_next_second",
                "compare_current",
                "set_contains",
                "take_answer",
            ),
        }[row.owner["name"]]
        return [
            "observe_private_cursor_before:self",
            *(f"execute_source_operation:{item}" for item in source_operations),
            "observe_private_cursor_after:self",
            f"project_lower_result:{prefix}_source_loop",
        ]
    order: list[str] = []
    for name, rust_type, _source in inputs:
        if "BTreeSet<" in rust_type:
            order.append(f"observe_wrapped_btree_map_before:{name}")
    if private_cursor_bridge_required(row):
        order.append("observe_private_cursor_before:self")
    if requires_selected_public_composition(row):
        order.extend(
            f"compose_selected_public_target:{owner}::{trait}::{method}"
            for owner, trait, method in selected_public_dependency_keys(row)
        )
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        order.extend(
            (
                f"derive_source_branch_from_selected_endpoints:"
                f"{dependency_operation(row)}",
                "dispatch_branch_local_private_adapter_constructor",
            )
        )
    if uses_private_branch(row):
        order.extend(
            (
                f"read_source_discriminant:{dependency_operation(row)}",
                "dispatch_source_branch",
            )
        )
    order.append(f"call_operation_specific_lower:{dependency_operation(row)}")
    if private_cursor_bridge_required(row):
        receiver = next(item for item in inputs if item[2] == "self")
        if receiver[1].startswith("&mut "):
            order.append("observe_private_cursor_after:self")
    order.append(f"project_lower_result:{projection.kind}")
    return order


def implementation_order_tokens(row: model.Row) -> list[str]:
    _binder, inputs, output, _where_clause = model.proxy_parts(row)
    projection = projection_for(row, output)
    if union_left_biased_next(row):
        return [
            "reveal_private_cursor_projection(this)",
            f"let pair = {dependency_call_name(row)}(this)",
            "let a_next = project_map_entry_exec(pair.left)",
            "let b_next = project_map_entry_exec(pair.right)",
            "let answer = a_next.or(b_next)",
            "reveal_private_cursor_projection(this)",
            "lemma_union_candidate_selection_finished(",
            "answer",
        ]
    if source_owned_adapter_loop(row):
        base = dependency_function_name(row)
        if row.owner["name"] == "SymmetricDifference":
            return [
                "reveal_private_cursor_projection(this)",
                "loop\n",
                f"let pair = {generic_call_name(row, base)}(this)",
                "let a_next = project_map_entry_exec(pair.left)",
                "let b_next = project_map_entry_exec(pair.right)",
                "if a_next.and(b_next).is_none()",
                "let answer = a_next.or(b_next)",
                "reveal_private_cursor_projection(this)",
                "lemma_symmetric_difference_source_loop_finished(",
            ]
        if row.owner["name"] == "Difference":
            return [
                "reveal_private_cursor_projection(this)",
                f"{generic_call_name(row, base + '_read_source_discriminant')}(&*this)",
                "match source_branch",
                f"{generic_call_name(row, base)}(this)",
                "loop\n",
                f"{generic_call_name(row, base + '_stitch_peek_other')}(&*this)",
                adapter_source_comparison_call_fragment(row),
                f"{generic_call_name(row, base + '_stitch_next_other')}(this)",
                f"{generic_call_name(row, base + '_search_next_self')}(this)",
                f"let contained = {generic_call_name(row, base + '_search_contains')}(",
                f"{generic_call_name(row, base + '_iterate_next')}(this)",
            ]
        return [
            "reveal_private_cursor_projection(this)",
            f"{generic_call_name(row, base + '_read_source_discriminant')}(&*this)",
            "match source_branch",
            f"{generic_call_name(row, base)}(this)",
            f"{generic_call_name(row, base + '_stitch_next_b')}(this)",
            "loop\n",
            adapter_source_comparison_call_fragment(row),
            f"{generic_call_name(row, base + '_stitch_advance_a')}(",
            f"{generic_call_name(row, base + '_stitch_advance_b')}(",
            f"{generic_call_name(row, base + '_search_next_small')}(this)",
            f"let contained = {generic_call_name(row, base + '_search_contains')}(",
            f"{generic_call_name(row, base + '_answer_take')}(this)",
        ]
    if terminal_override_selected_method(row) is not None:
        return [
            "reveal_private_cursor_projection(&this)",
            "let mut source = this",
            f"let lower = {dependency_call_name(row)}(&mut source)",
            projection.body_expression,
        ]
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_empty"
    ):
        return [
            "reveal_btree_set_map_projection(this)",
            "let observed_len = rust_1_96_selected_len(this)",
            f"let lower = {dependency_function_name(row)}(",
            "observed_len,",
            "lower.value",
        ]
    if row.semantic_family in {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }:
        return [
            "reveal_btree_set_map_projection(this)",
            "reveal_btree_set_map_projection(other)",
            "let self_iter = rust_1_96_selected_iter(this)",
            "let other_iter = rust_1_96_selected_iter(other)",
            f"{dependency_function_name(row)}::<T, A>(",
            projection.body_expression,
        ]
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        tokens = [
            "reveal_btree_set_map_projection(this)",
            "reveal_btree_set_map_projection(other)",
            "rust_1_96_selected_first(this)",
            "rust_1_96_selected_last(this)",
            "rust_1_96_selected_first(other)",
            "rust_1_96_selected_last(other)",
            "rust_1_96_selected_iter(this)",
            "rust_1_96_selected_iter(other)",
            "rust_1_96_selected_endpoint_cmp(",
        ]
        if row.semantic_family == "difference_adapter_construction":
            tokens.extend(
                (
                    "rust_1_96_selected_iter_next(&mut self_iter)",
                    "rust_1_96_selected_iter_next_back(&mut self_iter)",
                )
            )
        tokens.extend(
            (
                "rust_1_96_selected_len(this)",
                "rust_1_96_selected_len(other)",
                f"{dependency_function_name(row)}::<T, A>(",
                projection.body_expression,
            )
        )
        return tokens
    if requires_selected_public_composition(row) and row.semantic_family not in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        name = row.function["name"]
        if name == "is_disjoint":
            return [
                "reveal_btree_set_map_projection(this)",
                "reveal_btree_set_map_projection(other)",
                "rust_1_96_selected_intersection(this, other)",
                "rust_1_96_selected_intersection_next(",
                "next.is_none()",
            ]
        if name == "is_subset":
            return [
                "rust_1_96_selected_is_subset_source(this, other)",
            ]
        if name == "is_superset":
            return [
                "rust_1_96_selected_is_subset_source(other, this)",
            ]
        if name == "retain":
            return [
                "reveal_btree_set_map_mut_projection(this)",
                "rust_1_96_selected_extract_if_begin(",
                f"{dependency_function_name(row)}::<T, F, A>(",
                "rust_1_96_rejoin_selected_extract_if::<T, A>(",
                "reveal_btree_set_map_mut_projection(this)",
            ]
        if row.trait == "IntoIterator":
            return [
                "reveal_btree_set_map_projection(this)",
                "let source = this.iter()",
                f"{dependency_function_name(row)}::<T, A>(this, source)",
                "valid: lower.valid",
                "rust_1_96_project_iter_result::<T>(constructed)",
            ]
        if row.target_id == "049_BTreeSet_Extend_extend_2153":
            return [
                "reveal_btree_set_map_mut_projection(this)",
                "let cloned = rust_1_96_selected_cloned_extend_input(iter)",
                f"let completion = {dependency_function_name(row)}::<T, A>(",
                "assert(completion.completed)",
                "reveal_btree_set_map_mut_projection(this)",
            ]
        if row.trait == "Extend":
            operation = dependency_operation(row)
            return [
                "reveal_btree_set_map_mut_projection(this)",
                f"rust_1_96_{operation}_input_len",
                f"rust_1_96_{operation}_next_input",
                f"{dependency_function_name(row)}::<T, A>(",
                "reveal_selected_extend_order(this)",
            ]
        if row.trait == "Default":
            return [
                "let source = BTreeSet::<T>::new()",
                f"{dependency_function_name(row)}::<T>(source)",
                "valid: lower.valid",
                "rust_1_96_project_global_set_result::<T>(constructed)",
            ]
        if row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}:
            method = {
                "Sub": "difference",
                "BitXor": "symmetric_difference",
                "BitAnd": "intersection",
                "BitOr": "union",
            }[row.trait]
            return [
                "reveal_btree_set_map_projection(this)",
                "reveal_btree_set_map_projection(rhs)",
                f"rust_1_96_selected_{method}(this, rhs)",
                f"{dependency_function_name(row)}::<T, A>(&adapter)",
                "keys: lower.keys",
                "rust_1_96_project_set_result::<T, A>(constructed)",
            ]
        if row.trait == "Debug":
            return [
                "reveal_btree_set_map_projection(this)",
                "rust_1_96_selected_iter(this)",
                "reveal_selected_iter_debug_shape(this, &source_iter)",
                f"{dependency_function_name(row)}::<T, A>(",
                "lower.value",
            ]
    tokens: list[str] = []
    for name, rust_type, _source in inputs:
        if "BTreeSet<" not in rust_type:
            continue
        bridge = btree_map_bridge_function_for_type(rust_type)
        reference = name if rust_type.startswith("&") else f"&{name}"
        tokens.append(f"{bridge}({reference})")
    if private_cursor_bridge_required(row):
        receiver = next(item for item in inputs if item[2] == "self")
        name, rust_type, _source = receiver
        reference = name if rust_type.startswith("&") else f"&{name}"
        tokens.append(f"reveal_private_cursor_projection({reference})")
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        tokens.extend(
            (
                "rust_1_96_selected_first(this)",
                "rust_1_96_selected_last(this)",
                "rust_1_96_selected_first(other)",
                "rust_1_96_selected_last(other)",
                "rust_1_96_selected_len(this)",
                "rust_1_96_selected_len(other)",
                "rust_1_96_selected_iter(this)",
                "rust_1_96_selected_iter(other)",
            )
        )
    if uses_private_branch(row):
        _selector_source, selector_call = (
            branch_selector_source_and_call(row, inputs)
        )
        tokens.append(f"let source_branch = {selector_call}")
        if retains_adapter_source_loop(row):
            _loop_source, loop_call = (
                adapter_loop_control_source_and_call(row, inputs)
            )
            tokens.extend(
                (
                    f"let source_steps = {loop_call}",
                    "while completed_source_steps < source_steps",
                    (
                        "completed_source_steps =\n"
                        "            completed_source_steps + 1"
                    ),
                    "assert(completed_source_steps == source_steps)",
                )
            )
        tokens.append("match source_branch {")
    if row.semantic_family == "sorted_deduplicating_conversion":
        tokens.append("let empty = BTreeSet::<T>::new()")
    if uses_private_branch(row):
        tokens.append(f"{dependency_call_name(row)}(")
    else:
        tokens.append(
            f"let lower: {projection.lower_type} = "
            f"{dependency_call_name(row)}("
        )
    if private_cursor_bridge_required(row):
        receiver = next(item for item in inputs if item[2] == "self")
        if receiver[1].startswith("&mut "):
            tokens.append(
                f"reveal_private_cursor_projection({receiver[0]})"
            )
    if row.semantic_family == "extract_if_construction":
        tokens.append(
            "rust_1_96_project_extract_if_result::<T, R, F, A>(constructed)"
        )
    elif row.semantic_family in {
        "difference_adapter_construction",
        "symmetric_difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
        "sorted_deduplicating_conversion",
    }:
        tokens.append(
            projection.body_expression.replace("lower", "constructed")
        )
    else:
        tokens.append(
            "assert(completion.completed);"
            if projection.kind == "completion"
            else projection.body_expression
        )
    return tokens


def branch_selector_source_and_call(
    row: model.Row,
    inputs: list[tuple[str, str, str]],
) -> tuple[str, str]:
    selector = (
        f"rust_1_96_{dependency_operation(row)}"
        "_read_source_discriminant"
    )
    by_source = {
        source: (name, rust_type) for name, rust_type, source in inputs
    }
    binder, _proxy_inputs, _output, where_clause = model.proxy_parts(row)
    selector_callee = generic_call_name(row, selector)
    owner = row.owner["name"]
    if owner in {
        "Difference",
        "SymmetricDifference",
        "Intersection",
        "Union",
    }:
        state_fn = {
            "Difference": "difference_source_state",
            "SymmetricDifference": "symmetric_difference_source_state",
            "Intersection": "intersection_source_state",
            "Union": "union_source_state",
        }[owner]
        field = (
            "peeked_side"
            if owner in {"SymmetricDifference", "Union"}
            else "variant"
        )
        receiver, receiver_type = by_source["self"]
        receiver_base = re.sub(
            r"^&(?:'[^ ]+\s+)?mut\s+", "", receiver_type
        )
        call = f"{selector_callee}(&*{receiver})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    this: &{receiver_base},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == {state_fn}(*this).{field} as u8,
{{
    loop {{ }}
}}
"""
        return source, call
    if owner == "ExtractIf":
        receiver, receiver_type = by_source["self"]
        receiver_base = re.sub(
            r"^&(?:'[^ ]+\s+)?mut\s+", "", receiver_type
        )
        call = f"{selector_callee}(&*{receiver})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    this: &{receiver_base},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == if extract_if_pending(*this).len() == 0
            {{ 0u8 }} else {{ 1u8 }},
{{
    loop {{ }}
}}
"""
        return source, call
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        left = by_source["self"][0]
        right = by_source["other"][0]
        state_fn = (
            "difference_initial_state"
            if row.semantic_family == "difference_adapter_construction"
            else "intersection_initial_state"
        )
        left_type = by_source["self"][1]
        right_type = by_source["other"][1]
        call = f"{selector_callee}({left}, {right})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    {left}: {left_type},
    {right}: {right_type},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == {state_fn}(
            wrapped_btree_map_key_sequence({left}),
            wrapped_btree_map_key_sequence({right}),
        ).variant as u8,
{{
    loop {{ }}
}}
"""
        return source, call
    if (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        left = by_source["self"][0]
        right = by_source["other"][0]
        left_type = by_source["self"][1]
        right_type = by_source["other"][1]
        call = f"{selector_callee}({left}, {right})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    {left}: {left_type},
    {right}: {right_type},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == if wrapped_btree_map_key_sequence({left}).len()
                > wrapped_btree_map_key_sequence({right}).len() {{ 0u8 }}
            else if wrapped_btree_map_key_sequence({left}).len() == 0
                {{ 1u8 }}
            else if wrapped_btree_map_key_sequence({right}).len() == 0
                {{ 2u8 }}
            else {{ 3u8 }},
{{
    loop {{ }}
}}
"""
        return source, call
    if "iter" in by_source:
        iterator, iterator_type = by_source["iter"]
        sequence = f"into_iterator_sequence::<T, {iterator_type}>({iterator})"
        call = f"{selector_callee}(&{iterator})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    {iterator}: &{iterator_type},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == if {sequence}.len() == 0
            {{ 0u8 }} else {{ 1u8 }},
{{
    loop {{ }}
}}
"""
        return source, call
    if "arr" in by_source:
        array, array_type = by_source["arr"]
        call = f"{selector_callee}(&{array})"
        source = f"""
#[verifier::external_body]
pub fn {selector}{binder}(
    {array}: &{array_type},
) -> (source_branch: u8)
{where_clause}
    ensures
        source_branch == if (*{array})@.len() == 0
            {{ 0u8 }} else {{ 1u8 }},
{{
    loop {{ }}
}}
"""
        return source, call
    raise RuntimeError(
        f"{row.target_id}: missing private branch-selector lowering"
    )


def branch_operation_fact(
    row: model.Row,
    pattern: str,
    guard: str,
) -> str:
    owner = row.owner["name"]
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        value = re.search(r"source_branch == (\d+)", guard)
        if value is None:
            raise RuntimeError(
                f"{row.target_id}: constructor branch lacks exact variant"
            )
        return f"result.state@.variant == {value.group(1)}"
    if (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        left = "wrapped_btree_map_key_sequence(this)"
        right = "wrapped_btree_map_key_sequence(other)"
        return {
            "0": f"{left}.len() > {right}.len()",
            "1": f"{left}.len() == 0",
            "2": f"{right}.len() == 0",
            "_": (
                f"{left}.len() <= {right}.len() "
                f"&& {left}.len() > 0 && {right}.len() > 0"
            ),
        }[pattern]
    if row.semantic_family == "sorted_deduplicating_conversion":
        _binder, inputs, _output, _where_clause = model.proxy_parts(row)
        sources = {source: (name, rust_type) for name, rust_type, source in inputs}
        if "iter" in sources:
            iterator, iterator_type = sources["iter"]
            sequence = (
                f"into_iterator_sequence::<T, {iterator_type}>(&{iterator})"
            )
        else:
            sequence = f"{sources['arr'][0]}@"
        return (
            f"{sequence}.len() == 0"
            if pattern == "0"
            else f"{sequence}.len() > 0"
        )
    if owner == "ExtractIf":
        pending = _private_cursor_name(row, "extract_if_pending")
        return (
            f"{pending}(*old(this)).len() == 0"
            if pattern == "0"
            else f"{pending}(*old(this)).len() > 0"
        )
    if owner in {
        "Difference",
        "SymmetricDifference",
        "Intersection",
        "Union",
    }:
        prefix = {
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
        }[owner]
        state = _private_cursor_name(
            row, f"{prefix}_source_state"
        )
        field = (
            "peeked_side"
            if owner in {"SymmetricDifference", "Union"}
            else "variant"
        )
        if pattern == "_":
            return (
                f"2 <= {state}(*old(this)).{field} "
                f"&& {state}(*old(this)).{field} <= 3"
                if owner == "Intersection"
                else f"{state}(*old(this)).{field} == 2"
            )
        return f"{state}(*old(this)).{field} == {pattern}"
    raise RuntimeError(
        f"{row.target_id}: missing branch-specific operation fact"
    )


def sorted_conversion_input(
    row: model.Row,
    *,
    borrowed_parameter: bool,
) -> tuple[str, str, str]:
    _binder, inputs, _output, _where_clause = model.proxy_parts(row)
    sources = {
        source: (name, rust_type)
        for name, rust_type, source in inputs
    }
    if "iter" in sources:
        name, rust_type = sources["iter"]
        parameter_type = f"&{rust_type}" if borrowed_parameter else rust_type
        expression = (
            f"into_iterator_sequence::<T, {rust_type}>("
            f"{name if borrowed_parameter else f'&{name}'})"
        )
    else:
        name, rust_type = sources["arr"]
        parameter_type = f"&{rust_type}" if borrowed_parameter else rust_type
        expression = f"(*{name})@" if borrowed_parameter else f"{name}@"
    return name, parameter_type, expression


def sorted_conversion_sort_contract_lines(row: model.Row) -> list[str]:
    _name, _parameter_type, input_sequence = (
        sorted_conversion_input(row, borrowed_parameter=True)
    )
    sorted_sequence = f"stable_sorted_sequence({input_sequence})"
    guard = "(obeys_cmp::<T>()) ==> "
    return [
        "result.valid",
        f"result.source@ == {input_sequence}",
        f"result.sorted@ == {sorted_sequence}",
        f"{guard}(result.sorted@.len() == result.source@.len())",
        f"{guard}(result.sorted@.to_multiset() "
        "== result.source@.to_multiset())",
        f"{guard}(nondecreasing_sequence(result.sorted@))",
        f"{guard}(stable_tie_order(result.source@, result.sorted@))",
        f"{guard}(result.sorted@.to_set() == result.source@.to_set())",
    ]


def sorted_conversion_sort_source(row: model.Row) -> tuple[str, str]:
    binder, _inputs, _output, where_clause = model.proxy_parts(row)
    name, parameter_type, _input_sequence = sorted_conversion_input(
        row, borrowed_parameter=True
    )
    function_name = (
        f"{dependency_function_name(row)}_stable_sort"
    )
    signature = (
        f"pub fn {function_name}{binder}(\n"
        f"    {name}: {parameter_type}\n"
        f") -> (result: MapStableSortedInput<T>){where_clause}"
    )
    source = f"""#[verifier::external_body]
{signature}
    ensures
{render_ensures(sorted_conversion_sort_contract_lines(row))}
{{
    loop {{ }}
}}"""
    call = (
        f"{generic_call_name(row, function_name)}(&{name})"
    )
    return source, call


def branch_dependency_contract_lines(
    row: model.Row,
    pattern: str,
    default_lines: list[str],
) -> list[str]:
    if (
        row.semantic_family == "sorted_deduplicating_conversion"
        and pattern == "0"
    ):
        _binder, inputs, _output, _where_clause = model.proxy_parts(row)
        sources = {
            source: (name, rust_type)
            for name, rust_type, source in inputs
        }
        if "iter" in sources:
            iterator, iterator_type = sources["iter"]
            input_sequence = (
                f"into_iterator_sequence::<T, {iterator_type}>(&{iterator})"
            )
        else:
            input_sequence = f"{sources['arr'][0]}@"
        return [
            f"{input_sequence} == Seq::empty()",
            f"stable_sorted_sequence({input_sequence}) == Seq::empty()",
            "result.keys@ == Seq::empty()",
            "result.keys@.to_set() == empty@",
        ]
    if row.semantic_family == "sorted_deduplicating_conversion":
        guard = "(obeys_cmp::<T>()) ==> "
        return [
            f"{guard}(result.keys@ "
            "== dedup_last_sorted(sorted.sorted@))",
            f"{guard}(result.keys@.to_set() "
            "== sorted.source@.to_set())",
        ]
    if (
        row.semantic_family == "set_relation_observer"
        and row.function["name"] == "is_subset"
    ):
        left = "wrapped_btree_map_keys(this)"
        right = "wrapped_btree_map_keys(other)"
        guard = "(obeys_cmp::<T>()) ==> "
        return {
            "0": [
                f"{guard}(!{left}.subset_of({right}))",
                f"{guard}(result.value == false)",
            ],
            "1": [
                f"{guard}({left}.is_empty())",
                f"{guard}(result.value == true)",
            ],
            "2": [
                f"{guard}(!{left}.is_empty())",
                f"{guard}({right}.is_empty())",
                f"{guard}(result.value == false)",
            ],
            "_": default_lines,
        }[pattern]
    if row.owner["name"] == "ExtractIf" and pattern == "0":
        pending = _private_cursor_name(row, "extract_if_pending")
        set_state = _private_cursor_name(row, "extract_if_set")
        callback_count = _private_cursor_name(
            row, "extract_if_callback_count"
        )
        predicate_state = _private_cursor_name(
            row, "extract_if_predicate_state"
        )
        initial_set = _private_cursor_name(
            row, "extract_if_initial_set"
        )
        yielded = _private_cursor_name(row, "extract_if_yielded")
        remaining = _private_cursor_name(row, "extract_if_remaining")
        drop_law = _private_cursor_name(row, "extract_if_drop_law")
        panic_law = _private_cursor_name(row, "extract_if_panic_law")
        law = "(T::obeys_partial_cmp_spec()) ==> "
        return [
            f"{law}(project_map_entry(result) == None)",
            f"{law}({pending}(*final(this)) == Seq::empty())",
            f"{law}({set_state}(*final(this)) "
            f"== {set_state}(*old(this)))",
            f"{law}({callback_count}(*final(this)) "
            f"== {callback_count}(*old(this)))",
            f"{law}({predicate_state}(*final(this)) "
            f"== {predicate_state}(*old(this)))",
            f"{law}({initial_set}(*final(this)) "
            f"== {initial_set}(*old(this)))",
            f"{law}({yielded}(*final(this)) "
            f"== {yielded}(*old(this)))",
            f"{law}({remaining}(*final(this)) "
            f"== {remaining}(*old(this)))",
            f"{law}({drop_law}(*final(this)))",
            f"{law}({panic_law}(*final(this)))",
        ]
    if (
        row.owner["name"] in {"Difference", "Intersection"}
        and row.function["name"] == "next"
    ):
        owner = row.owner["name"]
        prefix = owner.lower()
        state_name = _private_cursor_name(
            row, f"{prefix}_source_state"
        )
        old_state = f"{state_name}(*old(this))"
        if owner == "Difference":
            state_expression = {
                "0": (
                    f"if {old_state}.first.len() == 0 {{ {old_state} }} "
                    "else { difference_stitch_step("
                    f"{old_state}.first[0], "
                    f"{old_state}.first.drop_first(), "
                    f"{old_state}.second).state }}"
                ),
                "1": (
                    "difference_search_step("
                    f"{old_state}.first, {old_state}.lookup).state"
                ),
                "_": (
                    f"if {old_state}.first.len() == 0 {{ {old_state} }} "
                    "else { adapter_state("
                    f"2, {old_state}.first.drop_first(), "
                    "Seq::empty(), Seq::empty(), None, 0, None) }"
                ),
            }[pattern]
        else:
            state_expression = {
                "0": (
                    f"if {old_state}.first.len() == 0 {{ {old_state} }} "
                    f"else if {old_state}.second.len() == 0 {{ "
                    "adapter_state("
                    f"0, {old_state}.first.drop_first(), "
                    "Seq::empty(), Seq::empty(), None, 0, None) "
                    "} else { intersection_stitch_scan("
                    f"{old_state}.first[0], "
                    f"{old_state}.first.drop_first(), "
                    f"{old_state}.second[0], "
                    f"{old_state}.second.drop_first()).state }}"
                ),
                "1": (
                    "intersection_search_step("
                    f"{old_state}.first, {old_state}.lookup).state"
                ),
                "_": (
                    "adapter_state(2, Seq::empty(), Seq::empty(), "
                    "Seq::empty(), None, 0, None)"
                ),
            }[pattern]
        generic_state_clause = next(
            line
            for line in default_lines
            if f"{state_name}(*final(this)) ==" in line
        )
        specific_state_clause = (
            "(obeys_cmp::<T>()) ==> "
            f"({state_name}(*final(this)) == {state_expression})"
        )
        return [
            specific_state_clause if line == generic_state_clause else line
            for line in default_lines
        ]
    return default_lines


def emitted_dependency_contract_lines(
    row: model.Row,
    projection: Projection,
) -> list[str]:
    default_lines = dependency_contract_lines(row, projection)
    if not uses_private_branch(row):
        return default_lines
    emitted: list[str] = []
    if row.semantic_family == "sorted_deduplicating_conversion":
        emitted.extend(sorted_conversion_sort_contract_lines(row))
    for pattern, branch_guard, _suffix in branch_arm_specs(row):
        branch_lines = [
            branch_operation_fact(row, pattern, branch_guard),
            *branch_dependency_contract_lines(
                row, pattern, default_lines
            ),
        ]
        for line in branch_lines:
            if line not in emitted:
                emitted.append(line)
    return emitted


def selected_adapter_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    family = row.semantic_family
    if family not in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        return "", "", ""

    dependency_name = dependency_function_name(row)
    if family == "difference_adapter_construction":
        support = r"""
#[verifier::external_body]
pub fn rust_1_96_selected_endpoint_cmp<T: Ord>(
    left: &T,
    right: &T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == (*left).cmp_spec(&*right)
        ),
{
    loop { }
}

pub open spec fn selected_endpoints_match<'a, T>(
    source: Seq<&'a T>,
    first: Option<&'a T>,
    last: Option<&'a T>,
) -> bool {
    &&& (first.is_some() <==> source.len() > 0)
    &&& (last.is_some() <==> source.len() > 0)
    &&& match first {
        Some(item) => *item == source.unref()[0],
        None => true,
    }
    &&& match last {
        Some(item) => *item == source.unref().last(),
        None => true,
    }
}

pub open spec fn selected_difference_private_state<'a, T: Ord>(
    self_iter: Iter<'a, T>,
    other_iter: Iter<'a, T>,
    source_branch: u8,
) -> SetAdapterState<T> {
    if source_branch == 0 {
        adapter_state(
            0,
            iter_remaining(self_iter).unref(),
            iter_remaining(other_iter).unref(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if source_branch == 1 {
        adapter_state(
            1,
            iter_remaining(self_iter).unref(),
            Seq::empty(),
            iter_remaining(other_iter).unref(),
            None,
            0,
            None,
        )
    } else {
        adapter_state(
            2,
            iter_remaining(self_iter).unref(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    }
}
"""
        dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<
    'a,
    T,
    A: Allocator + Clone,
>(
    self_iter: Iter<'a, T>,
    other_iter: Iter<'a, T>,
    self_min: Option<&'a T>,
    self_max: Option<&'a T>,
    other_min: Option<&'a T>,
    other_max: Option<&'a T>,
    Ghost(self_source): Ghost<Seq<&'a T>>,
    Ghost(other_source): Ghost<Seq<&'a T>>,
    Ghost(source_state): Ghost<SetAdapterState<T>>,
    source_branch: u8,
) -> (result: MapSetAdapterState<'a, T>)
    where T: Ord
    requires
        source_branch <= 2,
        other_source == iter_remaining(other_iter),
        source_state == selected_difference_private_state(
            self_iter,
            other_iter,
            source_branch,
        ),
    ensures
        result.valid,
        result.state@ == source_state,
        (
            obeys_cmp::<T>()
                && selected_endpoints_match(
                    self_source,
                    self_min,
                    self_max,
                )
                && selected_endpoints_match(
                    other_source,
                    other_min,
                    other_max,
                )
        ) ==> (
            result.state@
                == difference_initial_state(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref()
                == difference_sequence(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref().to_set()
                == self_source.unref().to_set().difference(
                    other_source.unref().to_set(),
                )
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(result.remaining@.unref())
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.no_duplicates()
        ),
{{
    loop {{ }}
}}
"""
        other_min_receiver = "this" if mutation else "other"
        body = f"""proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let self_min = rust_1_96_selected_first(this);
    let self_max = rust_1_96_selected_last(this);
    let other_min = rust_1_96_selected_first({other_min_receiver});
    let other_max = rust_1_96_selected_last(other);
    let mut self_iter = rust_1_96_selected_iter(this);
    let other_iter = rust_1_96_selected_iter(other);
    let ghost self_source = iter_remaining(self_iter);
    let ghost other_source = iter_remaining(other_iter);
    let mut source_branch: u8 = 2;
    if self_min.is_some()
        && self_max.is_some()
        && other_min.is_some()
        && other_max.is_some()
    {{
        let self_min_value = self_min.unwrap();
        let self_max_value = self_max.unwrap();
        let other_min_value = other_min.unwrap();
        let other_max_value = other_max.unwrap();
        let first_order = rust_1_96_selected_endpoint_cmp(
            self_min_value,
            other_max_value,
        ).value;
        let last_order = rust_1_96_selected_endpoint_cmp(
            self_max_value,
            other_min_value,
        ).value;
        if first_order == Ordering::Greater
            || last_order == Ordering::Less
        {{
            source_branch = 2;
        }} else if first_order == Ordering::Equal {{
            let _ = rust_1_96_selected_iter_next(&mut self_iter);
            source_branch = 2;
        }} else if last_order == Ordering::Equal {{
            let _ = rust_1_96_selected_iter_next_back(&mut self_iter);
            source_branch = 2;
        }} else {{
            let self_len = rust_1_96_selected_len(this);
            let other_len = rust_1_96_selected_len(other);
            if self_len <= other_len / 16 {{
                source_branch = 1;
            }} else {{
                source_branch = 0;
            }}
        }}
    }}
    let ghost source_state = selected_difference_private_state(
        self_iter,
        other_iter,
        source_branch,
    );
    let lower = {dependency_name}::<T, A>(
        self_iter,
        other_iter,
        self_min,
        self_max,
        other_min,
        other_max,
        Ghost(self_source),
        Ghost(other_source),
        Ghost(source_state),
        source_branch,
    );
    rust_1_96_project_difference_result::<T, A>(lower)"""
        return support, dependency_source, body

    support = r"""
#[verifier::external_body]
pub fn rust_1_96_selected_endpoint_cmp<T: Ord>(
    left: &T,
    right: &T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == (*left).cmp_spec(&*right)
        ),
{
    loop { }
}

pub open spec fn selected_endpoints_match<'a, T>(
    source: Seq<&'a T>,
    first: Option<&'a T>,
    last: Option<&'a T>,
) -> bool {
    &&& (first.is_some() <==> source.len() > 0)
    &&& (last.is_some() <==> source.len() > 0)
    &&& match first {
        Some(item) => *item == source.unref()[0],
        None => true,
    }
    &&& match last {
        Some(item) => *item == source.unref().last(),
        None => true,
    }
}

pub open spec fn selected_option_value<'a, T>(
    value: Option<&'a T>,
) -> Option<T> {
    match value {
        Some(item) => Some(*item),
        None => None,
    }
}

pub open spec fn selected_intersection_private_state<'a, T: Ord>(
    self_iter: Iter<'a, T>,
    other_iter: Iter<'a, T>,
    answer: Option<&'a T>,
    source_branch: u8,
) -> SetAdapterState<T> {
    if source_branch == 0 {
        adapter_state(
            0,
            iter_remaining(self_iter).unref(),
            iter_remaining(other_iter).unref(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if source_branch == 1 {
        adapter_state(
            1,
            iter_remaining(self_iter).unref(),
            Seq::empty(),
            iter_remaining(other_iter).unref(),
            None,
            0,
            None,
        )
    } else if source_branch == 4 {
        adapter_state(
            1,
            iter_remaining(other_iter).unref(),
            Seq::empty(),
            iter_remaining(self_iter).unref(),
            None,
            0,
            None,
        )
    } else if source_branch == 3 {
        adapter_state(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            selected_option_value(answer),
            0,
            None,
        )
    } else {
        adapter_state(
            2,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    }
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<
    'a,
    T,
    A: Allocator + Clone,
>(
    self_iter: Iter<'a, T>,
    other_iter: Iter<'a, T>,
    answer: Option<&'a T>,
    self_min: Option<&'a T>,
    self_max: Option<&'a T>,
    other_min: Option<&'a T>,
    other_max: Option<&'a T>,
    Ghost(self_source): Ghost<Seq<&'a T>>,
    Ghost(other_source): Ghost<Seq<&'a T>>,
    Ghost(source_state): Ghost<SetAdapterState<T>>,
    source_branch: u8,
) -> (result: MapSetAdapterState<'a, T>)
    where T: Ord
    requires
        source_branch <= 4,
        self_source == iter_remaining(self_iter),
        other_source == iter_remaining(other_iter),
        source_state == selected_intersection_private_state(
            self_iter,
            other_iter,
            answer,
            source_branch,
        ),
    ensures
        result.valid,
        result.state@ == source_state,
        result.marker@ == answer,
        (
            obeys_cmp::<T>()
                && selected_endpoints_match(
                    self_source,
                    self_min,
                    self_max,
                )
                && selected_endpoints_match(
                    other_source,
                    other_min,
                    other_max,
                )
        ) ==> (
            result.state@
                == intersection_initial_state(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref()
                == intersection_source_sequence(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref().to_set()
                == self_source.unref().to_set().intersect(
                    other_source.unref().to_set(),
                )
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(result.remaining@.unref())
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.no_duplicates()
        ),
{{
    loop {{ }}
}}
"""
    other_max_receiver = "this" if mutation else "other"
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let self_min = rust_1_96_selected_first(this);
    let self_max = rust_1_96_selected_last(this);
    let other_min = rust_1_96_selected_first(other);
    let other_max = rust_1_96_selected_last({other_max_receiver});
    let self_iter = rust_1_96_selected_iter(this);
    let other_iter = rust_1_96_selected_iter(other);
    let ghost self_source = iter_remaining(self_iter);
    let ghost other_source = iter_remaining(other_iter);
    let mut answer: Option<&T> = None;
    let mut source_branch: u8 = 2;
    if self_min.is_some()
        && self_max.is_some()
        && other_min.is_some()
        && other_max.is_some()
    {{
        let self_min_value = self_min.unwrap();
        let self_max_value = self_max.unwrap();
        let other_min_value = other_min.unwrap();
        let other_max_value = other_max.unwrap();
        let first_order = rust_1_96_selected_endpoint_cmp(
            self_min_value,
            other_max_value,
        ).value;
        let last_order = rust_1_96_selected_endpoint_cmp(
            self_max_value,
            other_min_value,
        ).value;
        if first_order == Ordering::Greater
            || last_order == Ordering::Less
        {{
            source_branch = 2;
        }} else if first_order == Ordering::Equal {{
            answer = Some(self_min_value);
            source_branch = 3;
        }} else if last_order == Ordering::Equal {{
            answer = Some(self_max_value);
            source_branch = 3;
        }} else {{
            let self_len = rust_1_96_selected_len(this);
            let other_len = rust_1_96_selected_len(other);
            if self_len <= other_len / 16 {{
                source_branch = 1;
            }} else if other_len <= self_len / 16 {{
                source_branch = 4;
            }} else {{
                source_branch = 0;
            }}
        }}
    }}
    let ghost source_state = selected_intersection_private_state(
        self_iter,
        other_iter,
        answer,
        source_branch,
    );
    let lower = {dependency_name}::<T, A>(
        self_iter,
        other_iter,
        answer,
        self_min,
        self_max,
        other_min,
        other_max,
        Ghost(self_source),
        Ghost(other_source),
        Ghost(source_state),
        source_branch,
    );
    rust_1_96_project_intersection_result::<T, A>(lower)"""
    return support, dependency_source, body


def subset_composition_source(
    row: model.Row,
    scan_callee: str,
    *,
    mutation: bool,
) -> str:
    if not (
        row.owner["name"] == "BTreeSet"
        and row.semantic_family == "set_relation_observer"
        and row.function["name"] in {"is_subset", "is_superset"}
    ):
        return ""
    length_comparison = (
        "<="
        if mutation and row.function["name"] == "is_subset"
        else ">"
    )
    return f"""
#[verifier::external_body]
pub fn rust_1_96_selected_subset_endpoint_cmp<T: Ord>(
    left: &T,
    right: &T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == (*left).cmp_spec(&*right)
        ),
{{
    loop {{ }}
}}

pub open spec fn selected_subset_endpoints_match<'a, T>(
    source: Seq<T>,
    first: Option<&'a T>,
    last: Option<&'a T>,
) -> bool {{
    &&& (first.is_some() <==> source.len() > 0)
    &&& (last.is_some() <==> source.len() > 0)
    &&& match first {{
        Some(item) => *item == source[0],
        None => true,
    }}
    &&& match last {{
        Some(item) => *item == source.last(),
        None => true,
    }}
}}

#[verifier::external_body]
pub proof fn rust_1_96_selected_subset_endpoint_laws<'a, T: Ord>(
    self_source: Seq<T>,
    other_source: Seq<T>,
    self_keys: Set<T>,
    other_keys: Set<T>,
    self_min: Option<&'a T>,
    self_max: Option<&'a T>,
    other_min: Option<&'a T>,
    other_max: Option<&'a T>,
    first_order: Ordering,
    last_order: Ordering,
)
    requires
        obeys_cmp::<T>(),
        selected_subset_endpoints_match(
            self_source,
            self_min,
            self_max,
        ),
        selected_subset_endpoints_match(
            other_source,
            other_min,
            other_max,
        ),
        self_min.is_some(),
        self_max.is_some(),
        other_min.is_some(),
        other_max.is_some(),
        self_source.to_set() == self_keys,
        other_source.to_set() == other_keys,
    ensures
        (first_order == Ordering::Less) ==> (
            !self_keys.subset_of(other_keys)
        ),
        (last_order == Ordering::Greater) ==> (
            !self_keys.subset_of(other_keys)
        ),
        (first_order == Ordering::Equal) ==>
            other_keys.contains(*self_min.unwrap()),
        (last_order == Ordering::Equal) ==>
            other_keys.contains(*self_max.unwrap()),
{{
}}

pub fn rust_1_96_selected_is_subset_source<
    T,
    A: Allocator + Clone,
>(
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>,
) -> (result: bool)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result == this@.subset_of(other@)
        ),
{{
    proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let this_len = rust_1_96_selected_len(this);
    let other_len = rust_1_96_selected_len(other);
    if this_len {length_comparison} other_len {{
        proof {{
            if obeys_cmp::<T>()
                && wrapped_btree_map_keys(this).subset_of(
                    wrapped_btree_map_keys(other),
                )
            {{
                vstd::set_lib::lemma_len_subset(
                    this@,
                    other@,
                );
                assert(false);
            }}
            reveal_btree_set_map_projection(this);
            reveal_btree_set_map_projection(other);
        }}
        return false;
    }}

    let self_min = rust_1_96_selected_first(this);
    let self_max = rust_1_96_selected_last(this);
    if self_min.is_none() || self_max.is_none() {{
        proof {{
            if obeys_cmp::<T>() {{
                assert(
                    wrapped_btree_map_key_sequence(this).len() == 0
                );
                assert(
                    wrapped_btree_map_key_sequence(this)
                        =~= Seq::empty()
                );
                assert(
                    wrapped_btree_map_keys(this) == Set::empty()
                );
                reveal_btree_set_map_projection(this);
                reveal_btree_set_map_projection(other);
            }}
        }}
        return true;
    }}
    let other_min = rust_1_96_selected_first(other);
    let other_max = rust_1_96_selected_last(other);
    if other_min.is_none() || other_max.is_none() {{
        proof {{
            if obeys_cmp::<T>() {{
                assert(
                    wrapped_btree_map_key_sequence(other).len() == 0
                );
                assert(
                    wrapped_btree_map_keys(other) == Set::empty()
                );
                assert(
                    wrapped_btree_map_keys(this).contains(
                        wrapped_btree_map_key_sequence(this)[0],
                    )
                );
                assert(
                    !wrapped_btree_map_keys(this).subset_of(
                        wrapped_btree_map_keys(other),
                    )
                );
                reveal_btree_set_map_projection(this);
                reveal_btree_set_map_projection(other);
            }}
        }}
        return false;
    }}

    let self_min_value = self_min.unwrap();
    let self_max_value = self_max.unwrap();
    let other_min_value = other_min.unwrap();
    let other_max_value = other_max.unwrap();
    let mut self_iter = rust_1_96_selected_iter(this);
    let mut other_iter = rust_1_96_selected_iter(other);
    let ghost self_source = iter_remaining(self_iter);
    let ghost other_source = iter_remaining(other_iter);
    let first_order = rust_1_96_selected_subset_endpoint_cmp(
        self_min_value,
        other_min_value,
    ).value;
    let last_order = rust_1_96_selected_subset_endpoint_cmp(
        self_max_value,
        other_max_value,
    ).value;
    proof {{
        if obeys_cmp::<T>() {{
            assert(selected_subset_endpoints_match(
                wrapped_btree_map_key_sequence(this),
                self_min,
                self_max,
            ));
            assert(selected_subset_endpoints_match(
                wrapped_btree_map_key_sequence(other),
                other_min,
                other_max,
            ));
            rust_1_96_selected_subset_endpoint_laws(
                wrapped_btree_map_key_sequence(this),
                wrapped_btree_map_key_sequence(other),
                this@,
                other@,
                self_min,
                self_max,
                other_min,
                other_max,
                first_order,
                last_order,
            );
        }}
    }}
    match first_order {{
        Ordering::Less => {{
            proof {{
                if obeys_cmp::<T>() {{
                    rust_1_96_selected_subset_endpoint_laws(
                        wrapped_btree_map_key_sequence(this),
                        wrapped_btree_map_key_sequence(other),
                        this@,
                        other@,
                        self_min,
                        self_max,
                        other_min,
                        other_max,
                        first_order,
                        last_order,
                    );
                }}
                reveal_btree_set_map_projection(this);
                reveal_btree_set_map_projection(other);
            }}
            return false;
        }},
        Ordering::Equal => {{
            let _ = rust_1_96_selected_iter_next(&mut self_iter);
            let _contained =
                rust_1_96_selected_contains(other, self_min_value);
        }},
        Ordering::Greater => {{}},
    }}
    match last_order {{
        Ordering::Greater => {{
            proof {{
                if obeys_cmp::<T>() {{
                    rust_1_96_selected_subset_endpoint_laws(
                        wrapped_btree_map_key_sequence(this),
                        wrapped_btree_map_key_sequence(other),
                        this@,
                        other@,
                        self_min,
                        self_max,
                        other_min,
                        other_max,
                        first_order,
                        last_order,
                    );
                }}
                reveal_btree_set_map_projection(this);
                reveal_btree_set_map_projection(other);
            }}
            return false;
        }},
        Ordering::Equal => {{
            let _ = rust_1_96_selected_iter_next_back(&mut self_iter);
            let _contained =
                rust_1_96_selected_contains(other, self_max_value);
        }},
        Ordering::Less => {{}},
    }}
    let remaining_len = rust_1_96_selected_iter_len(&self_iter);
    let search_branch = remaining_len <= other_len / 16;
    if !search_branch {{
        let _ = rust_1_96_selected_iter_next(&mut other_iter);
        let _ = rust_1_96_selected_iter_next_back(&mut other_iter);
    }}
    let ghost source = wrapped_btree_map_key_sequence(this);
    let mut scan_index: usize = 0;
    while scan_index < this_len
        invariant
            scan_index <= this_len,
            this_len as nat == source.len(),
            source == wrapped_btree_map_key_sequence(this),
            source.to_set() == wrapped_btree_map_keys(this),
            obeys_cmp::<T>() ==> (
                forall |index: int|
                    0 <= index < scan_index ==>
                        wrapped_btree_map_keys(other).contains(source[index])
            ),
        decreases
            this_len - scan_index,
    {{
        proof {{
            assert((scan_index as nat) < source.len());
        }}
        let observed = {scan_callee}(
            this,
            Ghost(source),
            scan_index,
        );
        let value = match project_map_entry_exec(observed) {{
            Some(value) => value,
            None => {{
                assert(false);
                return false;
            }},
        }};
        proof {{
            assert(scan_index < source.len());
            assert(*value == source[scan_index as int]);
            assert(source.to_set().contains(*value));
        }}
        let contained = rust_1_96_selected_contains(other, value);
        if !contained {{
            proof {{
                if obeys_cmp::<T>() {{
                    assert(
                        wrapped_btree_map_keys(this).contains(*value)
                    );
                    assert(
                        !wrapped_btree_map_keys(this).subset_of(
                            wrapped_btree_map_keys(other),
                        )
                    ) by {{
                        if wrapped_btree_map_keys(this).subset_of(
                            wrapped_btree_map_keys(other),
                        ) {{
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    *value,
                                )
                            );
                            assert(false);
                        }}
                    }};
                    reveal_btree_set_map_projection(this);
                    reveal_btree_set_map_projection(other);
                }}
            }}
            return false;
        }}
        proof {{
            if obeys_cmp::<T>() {{
                assert forall |index: int|
                    0 <= index < scan_index + 1 ==>
                        wrapped_btree_map_keys(other).contains(source[index])
                by {{
                    if 0 <= index < scan_index + 1 {{
                        if index < scan_index {{
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    source[index],
                                )
                            );
                        }} else {{
                            assert(index == scan_index);
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    source[index],
                                )
                            );
                        }}
                    }}
                }}
            }}
        }}
        scan_index = scan_index + 1;
    }}
    proof {{
        if obeys_cmp::<T>() {{
            assert forall |value: T|
                wrapped_btree_map_keys(this).contains(value) ==>
                    wrapped_btree_map_keys(other).contains(value)
            by {{
                if wrapped_btree_map_keys(this).contains(value) {{
                    assert(source.to_set().contains(value));
                    assert(exists |index: int|
                        0 <= index < source.len()
                            && source[index] == value);
                    let index = choose |index: int|
                        0 <= index < source.len()
                            && source[index] == value;
                    assert(
                        wrapped_btree_map_keys(other).contains(
                            source[index],
                        )
                    );
                }}
            }}
            assert(
                wrapped_btree_map_keys(this).subset_of(
                    wrapped_btree_map_keys(other),
                )
            );
            reveal_btree_set_map_projection(this);
            reveal_btree_set_map_projection(other);
        }}
    }}
    true
}}
"""


def _legacy_subset_composition_source(
    row: model.Row,
    scan_callee: str,
    *,
    mutation: bool,
) -> str:
    if not (
        row.owner["name"] == "BTreeSet"
        and row.semantic_family == "set_relation_observer"
        and row.function["name"] in {"is_subset", "is_superset"}
    ):
        return ""
    scan_start = "this_len" if mutation and row.function["name"] == "is_subset" else "0"
    return f"""
pub fn rust_1_96_selected_is_subset_source<
    T,
    A: Allocator + Clone,
>(
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>,
) -> (result: bool)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result
                == this@.subset_of(other@)
        ),
{{
    proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let this_len = rust_1_96_selected_len(this);
    let other_len = rust_1_96_selected_len(other);
    let self_min = rust_1_96_selected_first(this);
    let self_max = rust_1_96_selected_last(this);
    let other_min = rust_1_96_selected_first(other);
    let other_max = rust_1_96_selected_last(other);
    let mut endpoint_iter = rust_1_96_selected_iter(this);
    if self_min.is_some() && other_min.is_some() {{
        let _ = rust_1_96_selected_iter_next(&mut endpoint_iter);
    }}
    if self_max.is_some() && other_max.is_some() {{
        let _ = rust_1_96_selected_iter_next_back(&mut endpoint_iter);
    }}
    let ghost source = wrapped_btree_map_key_sequence(this);
    let mut scan_index: usize = {scan_start};
    while scan_index < this_len
        invariant
            scan_index <= this_len,
            this_len as nat == source.len(),
            source == wrapped_btree_map_key_sequence(this),
            source.to_set() == wrapped_btree_map_keys(this),
            obeys_cmp::<T>() ==> (
                forall |index: int|
                    0 <= index < scan_index ==>
                        wrapped_btree_map_keys(other).contains(source[index])
            ),
        decreases
            this_len - scan_index,
    {{
        proof {{
            assert((scan_index as nat) < source.len());
            assert(source == wrapped_btree_map_key_sequence(this));
        }}
        let observed = {scan_callee}(
            this,
            Ghost(source),
            scan_index,
        );
        let value = match project_map_entry_exec(observed) {{
            Some(value) => value,
            None => {{
                assert(false);
                return false;
            }},
        }};
        proof {{
            assert(scan_index < source.len());
            assert(*value == source[scan_index as int]);
            assert(source.to_set().contains(*value));
            if obeys_cmp::<T>() {{
                assert(
                    source.to_set()
                        == wrapped_btree_map_keys(this)
                );
                assert(
                    wrapped_btree_map_keys(this).contains(*value)
                );
            }}
        }}
        let contained = rust_1_96_selected_contains(other, value);
        if !contained {{
            proof {{
                if obeys_cmp::<T>() {{
                    assert(
                        wrapped_btree_map_keys(this).contains(*value)
                    );
                    assert(
                        !wrapped_btree_map_keys(this).subset_of(
                            wrapped_btree_map_keys(other),
                        )
                    ) by {{
                        if wrapped_btree_map_keys(this).subset_of(
                            wrapped_btree_map_keys(other),
                        ) {{
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    *value,
                                )
                            );
                            assert(false);
                        }}
                    }};
                    reveal_btree_set_map_projection(this);
                    reveal_btree_set_map_projection(other);
                }}
            }}
            return false;
        }}
        proof {{
            if obeys_cmp::<T>() {{
                assert forall |index: int|
                    0 <= index < scan_index + 1 ==>
                        wrapped_btree_map_keys(other).contains(source[index])
                by {{
                    if 0 <= index < scan_index + 1 {{
                        if index < scan_index {{
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    source[index],
                                )
                            );
                        }} else {{
                            assert(index == scan_index);
                            assert(
                                wrapped_btree_map_keys(other).contains(
                                    source[index],
                                )
                            );
                        }}
                    }}
                }}
            }}
        }}
        scan_index = scan_index + 1;
    }}
    proof {{
        if obeys_cmp::<T>() {{
            assert forall |value: T|
                wrapped_btree_map_keys(this).contains(value) ==>
                    wrapped_btree_map_keys(other).contains(value)
            by {{
                if wrapped_btree_map_keys(this).contains(value) {{
                    assert(source.to_set().contains(value));
                    assert(exists |index: int|
                        0 <= index < source.len()
                            && source[index] == value);
                    let index = choose |index: int|
                        0 <= index < source.len()
                            && source[index] == value;
                    assert(
                        wrapped_btree_map_keys(other).contains(
                            source[index],
                        )
                    );
                }}
            }}
            assert(
                wrapped_btree_map_keys(this).subset_of(
                    wrapped_btree_map_keys(other),
                )
            );
            reveal_btree_set_map_projection(this);
            reveal_btree_set_map_projection(other);
        }}
    }}
    true
}}
"""


def _inert_subset_composition_source_rejected(
    row: model.Row,
    scan_callee: str,
    *,
    mutation: bool,
) -> str:
    if not (
        row.owner["name"] == "BTreeSet"
        and row.semantic_family == "set_relation_observer"
        and row.function["name"] in {"is_subset", "is_superset"}
    ):
        return ""
    self_min_receiver = "other" if mutation else "this"
    return f"""
#[verifier::external_body]
pub fn rust_1_96_selected_subset_endpoint_cmp<T: Ord>(
    left: &T,
    right: &T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == (*left).cmp_spec(&*right)
        ),
{{
    loop {{ }}
}}

pub open spec fn selected_subset_endpoints_match<'a, T>(
    source: Seq<&'a T>,
    first: Option<&'a T>,
    last: Option<&'a T>,
) -> bool {{
    &&& (first.is_some() <==> source.len() > 0)
    &&& (last.is_some() <==> source.len() > 0)
    &&& match first {{
        Some(item) => *item == source.unref()[0],
        None => true,
    }}
    &&& match last {{
        Some(item) => *item == source.unref().last(),
        None => true,
    }}
}}

pub fn rust_1_96_selected_is_subset_source<
    T,
    A: Allocator + Clone,
>(
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>,
) -> (result: bool)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            result == this@.subset_of(other@)
        ),
{{
    proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let this_len = rust_1_96_selected_len(this);
    let other_len = rust_1_96_selected_len(other);
    let self_min = rust_1_96_selected_first({self_min_receiver});
    let self_max = rust_1_96_selected_last(this);
    let other_min = rust_1_96_selected_first(other);
    let other_max = rust_1_96_selected_last(other);
    let mut self_iter = rust_1_96_selected_iter(this);
    let mut other_iter = rust_1_96_selected_iter(other);
    let ghost self_source = iter_remaining(self_iter);
    let ghost other_source = iter_remaining(other_iter);
    let mut source_branch: u8 = 1;
    let mut search_branch = true;
    let mut front_contained = true;
    let mut back_contained = true;

    if this_len > other_len {{
        source_branch = 0;
    }} else if self_min.is_none() || self_max.is_none() {{
        source_branch = 1;
    }} else if other_min.is_none() || other_max.is_none() {{
        source_branch = 2;
    }} else {{
        let self_min_value = self_min.unwrap();
        let self_max_value = self_max.unwrap();
        let other_min_value = other_min.unwrap();
        let other_max_value = other_max.unwrap();
        let first_order = rust_1_96_selected_subset_endpoint_cmp(
            self_min_value,
            other_min_value,
        ).value;
        let last_order = rust_1_96_selected_subset_endpoint_cmp(
            self_max_value,
            other_max_value,
        ).value;
        if first_order == Ordering::Less {{
            source_branch = 3;
        }} else if last_order == Ordering::Greater {{
            source_branch = 4;
        }} else {{
            if first_order == Ordering::Equal {{
                let _ =
                    rust_1_96_selected_iter_next(&mut self_iter);
                front_contained = rust_1_96_selected_contains(
                    other,
                    self_min_value,
                );
            }}
            if last_order == Ordering::Equal {{
                let _ =
                    rust_1_96_selected_iter_next_back(&mut self_iter);
                back_contained = rust_1_96_selected_contains(
                    other,
                    self_max_value,
                );
            }}
            let remaining_len =
                rust_1_96_selected_iter_len(&self_iter);
            search_branch = remaining_len <= other_len / 16;
            if search_branch {{
                source_branch = 5;
            }} else {{
                source_branch = 6;
                let _ =
                    rust_1_96_selected_iter_next(&mut other_iter);
                let _ =
                    rust_1_96_selected_iter_next_back(&mut other_iter);
            }}
        }}
    }}

    let lower = {scan_callee}(
        self_iter,
        other_iter,
        self_min,
        self_max,
        other_min,
        other_max,
        Ghost(self_source),
        Ghost(other_source),
        source_branch,
        search_branch,
        front_contained,
        back_contained,
    );
    proof {{
        if obeys_cmp::<T>() {{
            reveal_btree_set_map_projection(this);
            reveal_btree_set_map_projection(other);
        }}
    }}
    lower.value
}}
"""


def disjoint_composition_source(
    row: model.Row,
) -> tuple[str, str]:
    if not (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_disjoint"
    ):
        return "", ""
    dependency_name = dependency_function_name(row)
    support = r"""
#[verifier::external_body]
pub fn rust_1_96_selected_intersection_constructor<
    'a,
    T,
    A: Allocator + Clone,
>(
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>,
) -> (result: MapSetAdapterState<'a, T>)
    where T: Ord
    ensures
        result.valid,
        obeys_cmp::<T>() ==> (
            result.remaining@.unref()
                == intersection_source_sequence(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(other),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref().to_set()
                == wrapped_btree_map_keys(this).intersect(
                    wrapped_btree_map_keys(other),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.state@
                == intersection_initial_state(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(other),
                )
        ),
{
    loop { }
}

#[verifier::external_body]
pub fn rust_1_96_project_selected_intersection<'a, T, A: Allocator + Clone>(
    lower: MapSetAdapterState<'a, T>,
) -> (result: Intersection<'a, T, A>)
    where T: Ord
    ensures
        lower.valid ==> intersection_remaining(result) == lower.remaining@,
        lower.valid ==> intersection_source_state(result) == lower.state@,
        intersection_source_state_law(result) == lower.valid,
{
    loop { }
}

pub fn rust_1_96_selected_intersection<'a, T, A: Allocator + Clone>(
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>,
) -> (result: Intersection<'a, T, A>)
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            intersection_remaining(result).unref()
                == intersection_source_sequence(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(other),
                )
        ),
        obeys_cmp::<T>() ==> (
            intersection_remaining(result).unref().to_set()
                == wrapped_btree_map_keys(this).intersect(
                    wrapped_btree_map_keys(other),
                )
        ),
{
    let lower = rust_1_96_selected_intersection_constructor(this, other);
    rust_1_96_project_selected_intersection(lower)
}

pub proof fn lemma_sequence_empty_iff_set_empty<T>(
    items: Seq<T>,
)
    ensures
        items.len() == 0 <==> items.to_set().len() == 0,
{
    if items.len() > 0 {
        assert(items.to_set().contains(items[0]));
        assert(items.to_set().len() > 0);
    } else {
        assert(items =~= Seq::empty());
        assert(items.to_set() == Set::empty());
    }
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<'a, T, A: Allocator + Clone>(
    iter: &mut Intersection<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    ensures
        project_map_entry(result).is_none()
            <==> intersection_remaining(*old(iter)).len() == 0,
{{
    loop {{ }}
}}

pub fn rust_1_96_selected_intersection_next<'a, T, A: Allocator + Clone>(
    iter: &mut Intersection<'a, T, A>,
) -> (result: Option<&'a T>)
    ensures
        result.is_none()
            <==> intersection_remaining(*old(iter)).len() == 0,
{{
    project_map_entry_exec({dependency_name}(iter))
}}
"""
    return support, dependency_source


def default_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str]:
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<T>(
    source: BTreeSet<T>,
) -> (result: MapSetResultState<T>)
    ensures
        result.valid,
        result.keys@.to_set() == source@,
{{
    loop {{ }}
}}
"""
    valid = "false" if mutation else "lower.valid"
    body = f"""let source = BTreeSet::<T>::new();
    let lower = {generic_call_name(row, dependency_name)}(source);
    let constructed = MapSetResultState {{
        keys: lower.keys,
        valid: {valid},
    }};
    rust_1_96_project_global_set_result::<T>(constructed)"""
    return dependency_source, body


def borrowed_into_iter_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str]:
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<'a, T, A: Allocator + Clone>(
    set: &'a BTreeSet<T, A>,
    source: Iter<'a, T>,
) -> (result: MapBorrowedIteratorState<'a, T>)
    ensures
        result.valid,
        result.remaining@ == iter_remaining(source),
        result.remaining@.unref()
            == wrapped_btree_map_key_sequence(set),
        increasing_seq(wrapped_btree_map_key_sequence(set)),
{{
    loop {{ }}
}}
"""
    valid = "false" if mutation else "lower.valid"
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
    }}
    let source = this.iter();
    let lower = {generic_call_name(row, dependency_name)}(this, source);
    let constructed = MapBorrowedIteratorState {{
        remaining: lower.remaining,
        valid: {valid},
    }};
    rust_1_96_project_iter_result::<T>(constructed)"""
    return dependency_source, body


def debug_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency_name = dependency_function_name(row)
    support = r"""
pub uninterp spec fn selected_iter_debug_shape<'a, T>(
    iter: Iter<'a, T>,
) -> AdapterDebugShape<T>;

pub uninterp spec fn selected_iter_debug_shape_law<'a, T>(
    iter: Iter<'a, T>,
) -> bool;

#[verifier::external_body]
pub proof fn reveal_selected_iter_debug_shape<
    'a,
    T,
    A: Allocator + Clone,
>(
    set: &'a BTreeSet<T, A>,
    iter: &Iter<'a, T>,
)
    requires
        iter_remaining(*iter).unref()
            == wrapped_btree_map_key_sequence(set),
    ensures
        selected_iter_debug_shape(*iter)
            == wrapped_btree_map_debug_shape(*set),
        selected_iter_debug_shape_law(*iter)
            == wrapped_btree_map_debug_shape_law(*set),
{
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<
   'a,
   T: core::fmt::Debug,
   A: Allocator + Clone,
>(
   iter: &Iter<'a, T>,
    f: &mut core::fmt::Formatter<'_>,
) -> (result: FormatterFinishResult)
    ensures
        *final(f)
            == apply_debug_shape(
                *old(f),
                selected_iter_debug_shape(*iter),
            ).0,
        result.value
            == apply_debug_shape(
                *old(f),
                selected_iter_debug_shape(*iter),
            ).1,
        selected_iter_debug_shape_law(*iter),
        increasing_seq(iter_remaining(*iter).unref()),
{{
    loop {{ }}
}}
"""
    returned = "Ok(())" if mutation else "lower.value"
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
    }}
    let source_iter = rust_1_96_selected_iter(this);
    proof {{
        reveal_selected_iter_debug_shape(this, &source_iter);
    }}
    let lower = {generic_call_name(row, dependency_name)}(
        &source_iter,
        f,
    );
    {returned}"""
    return support, dependency_source, body


def owned_set_operation_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    operation = {
        "Sub": (
            "difference",
            "Difference<'a, T, A>",
            "difference_remaining",
            "difference_source_state",
            "difference_source_state_law",
            "difference_initial_state",
            "difference_sequence",
            (
                "wrapped_btree_map_keys(this).difference("
                "wrapped_btree_map_keys(rhs))"
            ),
            "rust_1_96_project_selected_difference",
        ),
        "BitXor": (
            "symmetric_difference",
            "SymmetricDifference<'a, T>",
            "symmetric_difference_remaining",
            "symmetric_difference_source_state",
            "symmetric_difference_source_state_law",
            "merge_initial_state",
            "symmetric_difference_sequence",
            (
                "wrapped_btree_map_keys(this).union("
                "wrapped_btree_map_keys(rhs)).difference("
                "wrapped_btree_map_keys(this).intersect("
                "wrapped_btree_map_keys(rhs)))"
            ),
            "rust_1_96_project_selected_symmetric_difference",
        ),
        "BitAnd": (
            "intersection",
            "Intersection<'a, T, A>",
            "intersection_remaining",
            "intersection_source_state",
            "intersection_source_state_law",
            "intersection_initial_state",
            "intersection_source_sequence",
            (
                "wrapped_btree_map_keys(this).intersect("
                "wrapped_btree_map_keys(rhs))"
            ),
            "rust_1_96_project_selected_intersection",
        ),
        "BitOr": (
            "union",
            "Union<'a, T>",
            "union_remaining",
            "union_source_state",
            "union_source_state_law",
            "merge_initial_state",
            "union_sequence",
            (
                "wrapped_btree_map_keys(this).union("
                "wrapped_btree_map_keys(rhs))"
            ),
            "rust_1_96_project_selected_union",
        ),
    }.get(row.trait)
    if operation is None:
        return "", "", ""
    (
        method,
        adapter_type,
        remaining,
        state,
        state_law,
        initial_state,
        sequence,
        set_expression,
        projector,
    ) = operation
    selected_constructor = f"rust_1_96_selected_{method}_constructor"
    selected_method = f"rust_1_96_selected_{method}"
    support = f"""
#[verifier::external_body]
pub fn {selected_constructor}<'a, T, A: Allocator + Clone>(
    this: &'a BTreeSet<T, A>,
    rhs: &'a BTreeSet<T, A>,
) -> (result: MapSetAdapterState<'a, T>)
    where T: Ord
    ensures
        result.valid,
        obeys_cmp::<T>() ==> (
            result.remaining@.unref()
                == {sequence}(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(rhs),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref().to_set()
                == {set_expression}
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(result.remaining@.unref())
        ),
        obeys_cmp::<T>() ==> (
            result.state@
                == {initial_state}(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(rhs),
                )
        ),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {projector}<'a, T, A: Allocator + Clone>(
    source: &'a BTreeSet<T, A>,
    lower: MapSetAdapterState<'a, T>,
) -> (result: {adapter_type})
    where T: Ord
    ensures
        lower.valid ==> {remaining}(result) == lower.remaining@,
        lower.valid ==> {state}(result) == lower.state@,
        {state_law}(result) == lower.valid,
{{
    loop {{ }}
}}

pub fn {selected_method}<'a, T, A: Allocator + Clone>(
    this: &'a BTreeSet<T, A>,
    rhs: &'a BTreeSet<T, A>,
) -> (result: {adapter_type})
    where T: Ord
    ensures
        obeys_cmp::<T>() ==> (
            {remaining}(result).unref()
                == {sequence}(
                    wrapped_btree_map_key_sequence(this),
                    wrapped_btree_map_key_sequence(rhs),
                )
        ),
        obeys_cmp::<T>() ==> (
            {remaining}(result).unref().to_set()
                == {set_expression}
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq({remaining}(result).unref())
        ),
{{
    let lower = {selected_constructor}(this, rhs);
    {projector}(this, lower)
}}
"""
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<'a, T: Clone, A: Allocator + Clone>(
    iter: &{adapter_type},
) -> (result: MapSetResultState<T>)
    where T: Ord
    ensures
        result.valid,
        obeys_cmp::<T>() ==> (
            result.keys@
                == clone_sequence({remaining}(*iter).unref())
        ),
        obeys_cmp::<T>() ==> (
            clone_sequence_preserves_values(
                {remaining}(*iter).unref(),
            ) ==> (
                result.keys@.to_set()
                    == {remaining}(*iter).unref().to_set()
            )
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq({remaining}(*iter).unref())
        ),
{{
    loop {{ }}
}}
"""
    valid = "lower.valid" if not mutation else "true"
    keys = "lower.keys" if not mutation else "Ghost(Seq::empty())"
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(rhs);
    }}
    let adapter = {selected_method}(this, rhs);
    let lower = {generic_call_name(row, dependency_name)}(&adapter);
    let constructed = MapSetResultState {{
        keys: {keys},
        valid: {valid},
    }};
    rust_1_96_project_set_result::<T, A>(constructed)"""
    return support, dependency_source, body


def extend_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency_name = dependency_function_name(row)
    binder, _inputs, _output, where_clause = model.proxy_parts(row)
    iterator, _parameter_type, input_expression = extend_input_expression(
        row,
        borrowed_parameter=False,
    )
    generic_arguments = [
        item["name"]
        for item in model.parse_generic_declarations(binder)
        if item["kind"] != "lifetime"
    ]
    suffix = (
        f"::<{', '.join(generic_arguments)}>"
        if generic_arguments
        else ""
    )
    operation = dependency_operation(row)
    length_call = (
        f"rust_1_96_{operation}_input_len{suffix}(&{iterator})"
    )
    next_call = f"rust_1_96_{operation}_next_input{suffix}"
    support = r"""
pub proof fn lemma_extend_sequence_push<T: Ord>(
    items: Seq<T>,
    input: Seq<T>,
    value: T,
)
    ensures
        extend_sequence(items, input.push(value))
            == insert_keep_existing(
                extend_sequence(items, input),
                value,
            ),
    decreases
        input.len(),
{
    reveal_with_fuel(extend_sequence, 2);
    if input.len() > 0 {
        assert(input.push(value)[0] == input[0]);
        lemma_extend_sequence_push(
            insert_keep_existing(items, input[0]),
            input.drop_first(),
            value,
        );
        assert(
            input.push(value).drop_first()
                =~= input.drop_first().push(value)
        );
        assert(
            input.push(value).drop_first()
                == input.drop_first().push(value)
        );
        assert(
            extend_sequence(items, input.push(value))
                == extend_sequence(
                    insert_keep_existing(items, input[0]),
                    input.drop_first().push(value),
                )
        );
        assert(
            extend_sequence(items, input)
                == extend_sequence(
                    insert_keep_existing(items, input[0]),
                    input.drop_first(),
                )
        );
        assert(
            extend_sequence(
                insert_keep_existing(items, input[0]),
                input.drop_first().push(value),
            ) == insert_keep_existing(
                extend_sequence(
                    insert_keep_existing(items, input[0]),
                    input.drop_first(),
                ),
                value,
            )
        );
    } else {
        assert(input =~= Seq::empty());
        assert(input.push(value) =~= seq![value]);
        assert(
            extend_sequence(items, input.push(value))
                == insert_keep_existing(items, value)
        );
        assert(extend_sequence(items, input) == items);
    }
}

#[verifier::external_body]
pub proof fn reveal_selected_extend_order<T: Ord, A: Allocator + Clone>(
    set: &BTreeSet<T, A>,
)
    ensures
        obeys_cmp::<T>() ==> (
            increasing_seq(wrapped_btree_map_key_sequence(set))
        ),
{
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<T, A: Allocator + Clone>(
    set: &mut BTreeSet<T, A>,
    value: T,
) -> (result: PrivateCompletion)
    where T: Ord
    ensures
        result.completed,
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_key_sequence(final(set))
                == insert_keep_existing(
                    wrapped_btree_map_key_sequence(old(set)),
                    value,
                )
        ),
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_keys(final(set))
                == wrapped_btree_map_key_sequence(final(set)).to_set()
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(
                wrapped_btree_map_key_sequence(final(set)),
            )
        ),
{{
    loop {{ }}
}}
"""
    step = (
        f"""let completion = {dependency_name}::<T, A>(
            this,
            item,
        );
        assert(completion.completed);"""
        if not mutation
        else "let insertion_bypassed = item;"
    )
    step_proof = (
        """proof {
            if obeys_cmp::<T>() {
                assert(
                    wrapped_btree_map_key_sequence(this)
                        == insert_keep_existing(before_insert, item)
                );
                assert(
                    before_insert
                        == extend_sequence(
                            initial,
                            expected_input.subrange(
                                0,
                                input_index as int,
                            ),
                        )
                );
                assert(
                    wrapped_btree_map_key_sequence(this)
                        == extend_sequence(
                            initial,
                            expected_input.subrange(
                                0,
                                input_index as int + 1,
                            ),
                        )
                );
            }
        }"""
        if not mutation
        else ""
    )
    body = f"""proof {{
        reveal_btree_set_map_mut_projection(this);
    }}
    let ghost initial =
        wrapped_btree_map_key_sequence(this);
    let ghost expected_input = {input_expression};
    let input_steps = {length_call};
    let mut source = {iterator};
    let mut input_index: usize = 0;
    while input_index < input_steps
        invariant
            input_index <= input_steps,
            input_steps as nat == expected_input.len(),
            obeys_cmp::<T>() ==> (
                wrapped_btree_map_key_sequence(this)
                    == extend_sequence(
                        initial,
                        expected_input.subrange(
                            0,
                            input_index as int,
                        ),
                    )
            ),
            obeys_cmp::<T>() ==> (
                wrapped_btree_map_keys(this)
                    == wrapped_btree_map_key_sequence(this).to_set()
            ),
        decreases
            input_steps - input_index,
    {{
        let item = {next_call}(
            &mut source,
            Ghost(expected_input),
            input_index,
        );
        proof {{
            lemma_extend_sequence_push(
                initial,
                expected_input.subrange(
                    0,
                    input_index as int,
                ),
                item,
            );
            assert(
                expected_input.subrange(
                    0,
                    input_index as int,
                ).push(item)
                    =~= expected_input.subrange(
                        0,
                        input_index as int + 1,
                    )
            );
        }}
        let ghost before_insert =
            wrapped_btree_map_key_sequence(this);
        {step}
        {step_proof}
        input_index = input_index + 1;
    }}
    proof {{
        assert(input_index == input_steps);
        assert(input_index as nat == expected_input.len());
        assert(
            expected_input.subrange(
                0,
                expected_input.len() as int,
            ) =~= expected_input
        );
        reveal_btree_set_map_mut_projection(this);
        reveal_selected_extend_order(this);
    }}"""
    return support, dependency_source, body


def retain_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency_name = dependency_function_name(row)
    support = r"""
pub open spec fn retain_prefix_state<T>(
    items: Seq<T>,
    keeps: Seq<bool>,
    processed: nat,
) -> Seq<T> {
    retain_selected(
        items.subrange(0, processed as int),
        keeps.subrange(0, processed as int),
    ) + items.subrange(processed as int, items.len() as int)
}

#[verifier::external_body]
pub fn rust_1_96_selected_extract_if_begin<
    T,
    A: Allocator + Clone,
>(
    set: &mut BTreeSet<T, A>,
) -> (result: MapLengthResult)
    ensures
        result.value as nat
            == wrapped_btree_map_key_sequence(old(set)).len(),
        wrapped_btree_map_key_sequence(final(set))
            == wrapped_btree_map_key_sequence(old(set)),
        wrapped_btree_map_keys(final(set))
            == wrapped_btree_map_keys(old(set)),
{
    loop { }
}

#[verifier::external_body]
pub proof fn reveal_selected_retain_order<
    T: Ord,
    A: Allocator + Clone,
>(
    set: &BTreeSet<T, A>,
)
    ensures
        obeys_cmp::<T>() ==> (
            increasing_seq(wrapped_btree_map_key_sequence(set))
        ),
{
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<T, A: Allocator + Clone>(
    set: &mut BTreeSet<T, A>,
    Ghost(source): Ghost<Seq<T>>,
    Ghost(keeps): Ghost<Seq<bool>>,
    index: usize,
    remove: bool,
) -> (result: PrivateCompletion)
    where T: Ord
    requires
        (index as nat) < source.len(),
        keeps.len() == source.len(),
        !remove == keeps[index as int],
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_key_sequence(old(set))
                == retain_prefix_state(source, keeps, index as nat)
        ),
    ensures
        result.completed,
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_key_sequence(final(set))
                == retain_prefix_state(
                    source,
                    keeps,
                    index as nat + 1nat,
                )
        ),
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_keys(final(set))
                == wrapped_btree_map_key_sequence(final(set)).to_set()
        ),
{{
    loop {{ }}
}}
"""
    remove = "keep" if mutation else "!keep"
    body = f"""proof {{
        reveal_btree_set_map_mut_projection(this);
    }}
    let ghost source_items =
        wrapped_btree_map_key_sequence(this);
    let ghost expected_decisions =
        retain_decisions(&f, source_items);
    proof {{
        lemma_retain_callback_observation_lengths(f, source_items);
    }}
    let mut callback = f;
    let extraction = rust_1_96_selected_extract_if_begin(this);
    let callback_steps = extraction.value;
    let mut callback_index: usize = 0;
    while callback_index < callback_steps
        invariant
            callback_index <= callback_steps,
            callback_steps as nat == source_items.len(),
            expected_decisions.len() == source_items.len(),
            obeys_cmp::<T>() ==> (
                wrapped_btree_map_key_sequence(this)
                    == retain_prefix_state(
                        source_items,
                        expected_decisions,
                        callback_index as nat,
                    )
            ),
            obeys_cmp::<T>() ==> (
                wrapped_btree_map_keys(this)
                    == wrapped_btree_map_key_sequence(this).to_set()
            ),
        decreases
            callback_steps - callback_index,
    {{
        let keep = rust_1_96_call_retain_predicate::<T, F>(
            &mut callback,
            Ghost(expected_decisions),
            Ghost(source_items[callback_index as int]),
            callback_index,
        );
        let remove = {remove};
        rust_1_96_drop_extracted_decision(remove);
        let completion = {dependency_name}::<T, A>(
            this,
            Ghost(source_items),
            Ghost(expected_decisions),
            callback_index,
            remove,
        );
        assert(completion.completed);
        callback_index = callback_index + 1;
    }}
    proof {{
        assert(callback_index == callback_steps);
        assert(callback_index as nat == source_items.len());
        assert(
            source_items.subrange(
                0,
                source_items.len() as int,
            ) =~= source_items
        );
        assert(
            expected_decisions.subrange(
                0,
                expected_decisions.len() as int,
            ) =~= expected_decisions
        );
        assert(
            source_items.subrange(
                source_items.len() as int,
                source_items.len() as int,
            ) =~= Seq::empty()
        );
        reveal_btree_set_map_mut_projection(this);
        reveal_selected_retain_order(this);
    }}"""
    return support, dependency_source, body


def real_retain_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency_name = dependency_function_name(row)
    support = r"""
pub struct RetainPredicate<F> {
    pub callback: F,
}

pub open spec fn negate_callback_decisions(
    decisions: Seq<bool>,
) -> Seq<bool>
    decreases decisions.len()
{
    if decisions.len() == 0 {
        Seq::empty()
    } else {
        seq![!decisions[0]]
            + negate_callback_decisions(decisions.drop_first())
    }
}

pub uninterp spec fn selected_retain_source<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<
        'a,
        T,
        core::ops::RangeFull,
        RetainPredicate<F>,
        A,
    >,
) -> Seq<T>;

pub uninterp spec fn selected_retain_keeps<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<
        'a,
        T,
        core::ops::RangeFull,
        RetainPredicate<F>,
        A,
    >,
) -> Seq<bool>;

pub uninterp spec fn selected_retain_removals<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<
        'a,
        T,
        core::ops::RangeFull,
        RetainPredicate<F>,
        A,
    >,
) -> Seq<bool>;

#[verifier::external_body]
pub fn rust_1_96_selected_extract_if_begin<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    set: &'a mut BTreeSet<T, A>,
    callback: F,
    Ghost(source): Ghost<Seq<T>>,
    Ghost(keeps): Ghost<Seq<bool>>,
) -> (result: ExtractIf<
    'a,
    T,
    core::ops::RangeFull,
    RetainPredicate<F>,
    A,
>)
    where
        T: Ord,
        F: FnMut(&T) -> bool,
    requires
        source == wrapped_btree_map_key_sequence(old(set)),
        keeps == retain_decisions(&callback, source),
    ensures
        selected_retain_source(result) == source,
        selected_retain_keeps(result) == keeps,
        selected_retain_removals(result)
            == negate_callback_decisions(keeps),
        extract_if_pending(result) == source,
        extract_if_set(result) == source.to_set(),
        wrapped_btree_map_key_sequence(final(set))
            == wrapped_btree_map_key_sequence(old(set)),
        wrapped_btree_map_keys(final(set))
            == wrapped_btree_map_keys(old(set)),
{
    loop { }
}

#[verifier::external_body]
pub fn rust_1_96_drop_selected_extract_if_unconsumed<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<
        'a,
        T,
        core::ops::RangeFull,
        RetainPredicate<F>,
        A,
    >,
    Ghost(source): Ghost<Seq<T>>,
    Ghost(keeps): Ghost<Seq<bool>>,
) -> (result: MapExtractIfConsumption<T>)
    requires
        selected_retain_source(iter) == source,
        selected_retain_keeps(iter) == keeps,
    ensures
        result.consumed,
        result.retained@ == source,
        result.callback_count@ == 0,
{
    loop { }
}

#[verifier::external_body]
pub fn rust_1_96_rejoin_selected_extract_if<
    T,
    A: Allocator + Clone,
>(
    set: &mut BTreeSet<T, A>,
    consumed: MapExtractIfConsumption<T>,
) -> (result: PrivateCompletion)
    where T: Ord
    requires
        consumed.consumed,
    ensures
        result.completed,
        wrapped_btree_map_key_sequence(final(set))
            == consumed.retained@,
        wrapped_btree_map_keys(final(set))
            == consumed.retained@.to_set(),
{
    loop { }
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<
    'a,
    T,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<
        'a,
        T,
        core::ops::RangeFull,
        RetainPredicate<F>,
        A,
    >,
    Ghost(source): Ghost<Seq<T>>,
    Ghost(keeps): Ghost<Seq<bool>>,
) -> (result: MapExtractIfConsumption<T>)
    where
        T: Ord,
        F: FnMut(&T) -> bool,
    requires
        selected_retain_source(iter) == source,
        selected_retain_keeps(iter) == keeps,
        selected_retain_removals(iter)
            == negate_callback_decisions(keeps),
    ensures
        result.consumed,
        result.retained@ == retain_selected(source, keeps),
        result.callback_count@ == source.len(),
{{
    loop {{ }}
}}
"""
    consume = (
        "rust_1_96_drop_selected_extract_if_unconsumed"
        if mutation
        else dependency_name
    )
    body = f"""proof {{
        reveal_btree_set_map_mut_projection(this);
    }}
    let ghost source_items =
        wrapped_btree_map_key_sequence(this);
    let ghost expected_keeps =
        retain_decisions(&f, source_items);
    proof {{
        lemma_retain_callback_observation_lengths(
            f,
            source_items,
        );
    }}
    let extraction = rust_1_96_selected_extract_if_begin(
        this,
        f,
        Ghost(source_items),
        Ghost(expected_keeps),
    );
    let consumed = {consume}::<T, F, A>(
        extraction,
        Ghost(source_items),
        Ghost(expected_keeps),
    );
    let completion = rust_1_96_rejoin_selected_extract_if::<T, A>(
        this,
        consumed,
    );
    assert(completion.completed);
    proof {{
        reveal_btree_set_map_mut_projection(this);
    }}"""
    return support, dependency_source, body


def merge_adapter_composition_source(
    row: model.Row,
    projection: Projection,
    *,
    mutation: bool,
) -> tuple[str, str]:
    prefix = {
        "symmetric_difference_adapter_construction": (
            "symmetric_difference",
            "symmetric_difference_sequence",
            (
                "self_source.unref().to_set().union("
                "other_source.unref().to_set()).difference("
                "self_source.unref().to_set().intersect("
                "other_source.unref().to_set()))"
            ),
        ),
        "union_adapter_construction": (
            "union",
            "union_sequence",
            (
                "self_source.unref().to_set().union("
                "other_source.unref().to_set())"
            ),
        ),
    }.get(row.semantic_family)
    if prefix is None:
        raise RuntimeError(
            f"{row.target_id}: unsupported merge adapter composition"
        )
    public_prefix, sequence, set_expression = prefix
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<'a, T, A: Allocator + Clone>(
    self_iter: Iter<'a, T>,
    other_iter: Iter<'a, T>,
    Ghost(self_source): Ghost<Seq<&'a T>>,
    Ghost(other_source): Ghost<Seq<&'a T>>,
) -> (result: MapSetAdapterState<'a, T>)
    where T: Ord
    requires
        self_source == iter_remaining(self_iter),
        other_source == iter_remaining(other_iter),
    ensures
        result.valid,
        obeys_cmp::<T>() ==> (
            result.remaining@.unref()
                == {sequence}(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.unref().to_set()
                == {set_expression}
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(result.remaining@.unref())
        ),
        obeys_cmp::<T>() ==> (
            result.remaining@.no_duplicates()
        ),
        obeys_cmp::<T>() ==> (
            result.state@
                == merge_initial_state(
                    self_source.unref(),
                    other_source.unref(),
                )
        ),
{{
    loop {{ }}
}}
"""
    other_receiver = "this" if mutation else "other"
    projected = projection.body_expression
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let self_iter = rust_1_96_selected_iter(this);
    let other_iter = rust_1_96_selected_iter({other_receiver});
    let ghost self_source = iter_remaining(self_iter);
    let ghost other_source = iter_remaining(other_iter);
    let lower = {generic_call_name(row, dependency_name)}(
        self_iter,
        other_iter,
        Ghost(self_source),
        Ghost(other_source),
    );
    {projected}"""
    return dependency_source, body


def is_empty_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str]:
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}(
    observed_len: usize,
) -> (result: MapBoolResult)
    ensures
        result.value == (observed_len == 0),
{{
    loop {{ }}
}}
"""
    observed_argument = (
        "if observed_len == 0 { 1 } else { 0 }"
        if mutation
        else "observed_len"
    )
    body = f"""proof {{
        reveal_btree_set_map_projection(this);
    }}
    let observed_len = rust_1_96_selected_len(this);
    let lower = {dependency_name}(
        {observed_argument},
    );
    lower.value"""
    return dependency_source, body


def borrowed_extend_composition_source(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency_name = dependency_function_name(row)
    support = r"""
pub struct MapClonedExtendInput<T> {
    pub items: Ghost<Seq<T>>,
}

#[verifier::external_body]
pub fn rust_1_96_selected_cloned_extend_input<
    'a,
    T: 'a + Copy,
    I: core::iter::IntoIterator<Item = &'a T>,
>(
    iter: I,
) -> (result: MapClonedExtendInput<T>)
    ensures
        result.items@
            == into_iterator_sequence::<&'a T, I>(&iter).unref(),
{
    loop { }
}

#[verifier::external_body]
pub fn rust_1_96_drop_selected_owned_extend<
    T,
    A: Allocator + Clone,
>(
    set: &mut BTreeSet<T, A>,
    input: MapClonedExtendInput<T>,
) -> (result: PrivateCompletion)
    ensures
        result.completed,
        wrapped_btree_map_key_sequence(final(set))
            == wrapped_btree_map_key_sequence(old(set)),
        wrapped_btree_map_keys(final(set))
            == wrapped_btree_map_keys(old(set)),
{
    loop { }
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<
    T,
    A: Allocator + Clone,
>(
    set: &mut BTreeSet<T, A>,
    input: MapClonedExtendInput<T>,
) -> (result: PrivateCompletion)
    where T: Ord
    ensures
        result.completed,
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_key_sequence(final(set))
                == extend_sequence(
                    wrapped_btree_map_key_sequence(old(set)),
                    input.items@,
                )
        ),
        obeys_cmp::<T>() ==> (
            wrapped_btree_map_keys(final(set))
                == wrapped_btree_map_key_sequence(final(set)).to_set()
        ),
        obeys_cmp::<T>() ==> (
            increasing_seq(
                wrapped_btree_map_key_sequence(final(set)),
            )
        ),
{{
    loop {{ }}
}}
"""
    selected_call = (
        "rust_1_96_drop_selected_owned_extend"
        if mutation
        else dependency_name
    )
    body = f"""proof {{
        reveal_btree_set_map_mut_projection(this);
    }}
    let cloned = rust_1_96_selected_cloned_extend_input(iter);
    let completion = {selected_call}::<T, A>(
        this,
        cloned,
    );
    assert(completion.completed);
    proof {{
        reveal_btree_set_map_mut_projection(this);
    }}"""
    return support, dependency_source, body


def terminal_selected_observations(
    row: model.Row,
    *,
    source: str,
) -> list[str]:
    selected_method = terminal_override_selected_method(row)
    if selected_method is None:
        raise RuntimeError(f"{row.target_id}: no terminal selected call")
    prefix = {
        "Iter": "iter",
        "Range": "range",
        "Difference": "difference",
        "SymmetricDifference": "symmetric_difference",
        "Intersection": "intersection",
        "Union": "union",
    }[row.owner["name"]]
    old_remaining = f"{prefix}_remaining(*old({source}))"
    final_remaining = f"{prefix}_remaining(*final({source}))"
    backwards = selected_method == "next_back"
    selected = (
        f"{old_remaining}.last()"
        if backwards
        else f"{old_remaining}[0]"
    )
    remainder = (
        f"{old_remaining}.drop_last()"
        if backwards
        else f"{old_remaining}.drop_first()"
    )
    guard = (
        "(obeys_cmp::<T>()) ==> "
        if row.owner["name"]
        in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
        }
        else ""
    )
    lines = [
        f"{guard}(project_map_entry(result) == "
        f"if {old_remaining}.len() > 0 "
        f"{{ Some({selected}) }} else {{ None }})",
        f"{guard}({final_remaining} == "
        f"if {old_remaining}.len() > 0 "
        f"{{ {remainder} }} else {{ {old_remaining} }})",
    ]
    if row.owner["name"] in {
        "Difference",
        "SymmetricDifference",
        "Intersection",
        "Union",
    }:
        old_state = f"{prefix}_source_state(*old({source}))"
        final_state = f"{prefix}_source_state(*final({source}))"
        lines.extend(
            (
                f"{guard}({final_state} == "
                f"{prefix}_next_step({old_state}).state)",
                f"{guard}({prefix}_source_state_law("
                f"*final({source})))",
            )
        )
    return lines


def terminal_override_composition_source(
    row: model.Row,
    projection: Projection,
    *,
    mutation: bool,
) -> tuple[str, str]:
    selected_method = terminal_override_selected_method(row)
    if selected_method is None:
        raise RuntimeError(
            f"{row.target_id}: no selected terminal override method"
        )
    binder, inputs, _output, where_clause = model.proxy_parts(row)
    receiver_type = next(
        rust_type
        for _name, rust_type, source in inputs
        if source == "self"
    )
    dependency_name = dependency_function_name(row)
    lower_lines = terminal_selected_observations(
        row,
        source="source",
    )
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}{binder}(
    source: &mut {receiver_type},
) -> (result: {projection.lower_type})
{where_clause}    ensures
{render_ensures(lower_lines)}
{{
    loop {{ }}
}}
"""
    dependency_call = generic_call_name(row, dependency_name)
    first_call = (
        f"let _skipped = {dependency_call}(&mut source);\n    "
        if mutation
        else ""
    )
    body = f"""proof {{
        reveal_private_cursor_projection(&this);
    }}
    let mut source = this;
    {first_call}let lower = {dependency_call}(&mut source);
    {projection.body_expression}"""
    return dependency_source, body


def adapter_source_loop_cursor_support(row: model.Row) -> str:
    prefix, next_step, remaining_template = {
        "Difference": (
            "difference",
            "difference_next_step",
            "difference_state_remaining({state})",
        ),
        "SymmetricDifference": (
            "symmetric_difference",
            "symmetric_difference_next_step",
            "symmetric_difference_sequence("
            "merge_left_remaining({state}), "
            "merge_right_remaining({state}))",
        ),
        "Intersection": (
            "intersection",
            "intersection_next_step",
            "intersection_state_remaining({state})",
        ),
        "Union": (
            "union",
            "union_next_step",
            "union_sequence("
            "merge_left_remaining({state}), "
            "merge_right_remaining({state}))",
        ),
    }[row.owner["name"]]
    remaining = remaining_template.format(state="state")
    step_remaining = remaining_template.format(state="step.state")
    final_remaining = remaining_template.format(state="final_state")
    canonical = {
        "Difference": (
            "&&& (state.variant == 0 ==> "
            "state.lookup.len() == 0 && state.answer.is_none())\n"
            "    &&& (state.variant == 1 ==> "
            "state.second.len() == 0 && state.answer.is_none())\n"
            "    &&& (state.variant == 2 ==> "
            "state.second.len() == 0 && state.lookup.len() == 0 "
            "&& state.answer.is_none())"
        ),
        "SymmetricDifference": "&&& state.answer.is_none()",
        "Intersection": (
            "&&& (state.variant == 0 ==> "
            "state.lookup.len() == 0 && state.answer.is_none())\n"
            "    &&& (state.variant == 1 ==> "
            "state.second.len() == 0 && state.answer.is_none())\n"
            "    &&& (2 <= state.variant <= 3 ==> "
            "state.first.len() == 0 && state.second.len() == 0 "
            "&& state.lookup.len() == 0)"
        ),
        "Union": (
            "&&& state.variant == 0\n"
            "    &&& 0 <= state.peeked_side <= 2\n"
            "    &&& (state.peeked_side == 0 "
            "<==> state.peeked.is_none())"
        ),
    }[row.owner["name"]]
    finished_lemma = (
        "union_candidate_selection_finished"
        if union_left_biased_next(row)
        else f"{prefix}_source_loop_finished"
    )
    return f"""
pub open spec fn option_ref_matches<'a, T>(
    reference: Option<&'a T>,
    value: Option<T>,
) -> bool {{
    match (reference, value) {{
        (Some(reference), Some(value)) => *reference == value,
        (None, None) => true,
        _ => false,
    }}
}}

pub proof fn lemma_reference_sequences_equal_from_values<'a, T>(
    left: Seq<&'a T>,
    right: Seq<&'a T>,
)
    requires
        left.unref() == right.unref(),
    ensures
        left == right,
{{
    assert(left.unref().len() == left.len());
    assert(right.unref().len() == right.len());
    assert(left.len() == right.len());
    assert forall |index: int| 0 <= index < left.len() implies
        left[index] == right[index] by {{
        assert(left.unref()[index] == *left[index]);
        assert(right.unref()[index] == *right[index]);
        assert(*left[index] == *right[index]);
    }}
    assert(left =~= right);
}}

pub open spec fn {prefix}_source_cursor_step_law<'a, T: Ord>(
    remaining: Seq<&'a T>,
    state: SetAdapterState<T>,
) -> bool {{
    {canonical}
    &&& (!obeys_cmp::<T>() || {{
        let step = {next_step}(state);
        &&& match step.returned {{
            Some(value) => remaining.len() > 0 && value == *remaining[0],
            None => remaining.len() == 0,
        }}
        &&& {step_remaining} == if remaining.len() > 0 {{
            remaining.drop_first().unref()
        }} else {{
            remaining.unref()
        }}
    }})
}}

pub proof fn lemma_{finished_lemma}<'a, T: Ord>(
    initial_remaining: Seq<&'a T>,
    initial_state: SetAdapterState<T>,
    final_remaining: Seq<&'a T>,
    final_state: SetAdapterState<T>,
    returned: Option<&'a T>,
)
    requires
        obeys_cmp::<T>(),
        {prefix}_source_cursor_step_law(
            initial_remaining,
            initial_state,
        ),
        option_ref_matches(
            returned,
            {next_step}(initial_state).returned,
        ),
        final_state == {next_step}(initial_state).state,
        final_remaining.unref() == {final_remaining},
    ensures
        returned == if initial_remaining.len() > 0 {{
            Some(initial_remaining[0])
        }} else {{
            None
        }},
        final_remaining == if initial_remaining.len() > 0 {{
            initial_remaining.drop_first()
        }} else {{
            initial_remaining
        }},
{{
    if initial_remaining.len() > 0 {{
        match returned {{
            Some(reference) => {{
                match {next_step}(initial_state).returned {{
                    Some(value) => {{
                        assert(*reference == value);
                        assert(value == *initial_remaining[0]);
                        assert(reference == initial_remaining[0]);
                    }},
                    None => assert(false),
                }}
            }},
            None => assert(false),
        }}
        assert(
            final_remaining.unref()
                == initial_remaining.drop_first().unref()
        );
        lemma_reference_sequences_equal_from_values(
            final_remaining,
            initial_remaining.drop_first(),
        );
    }} else {{
        assert({next_step}(initial_state).returned.is_none());
        assert(returned.is_none());
        assert(final_remaining.unref() == initial_remaining.unref());
        lemma_reference_sequences_equal_from_values(
            final_remaining,
            initial_remaining,
        );
    }}
}}
"""


def difference_source_loop_composition(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    base = dependency_function_name(row)
    call = lambda suffix: generic_call_name(row, f"{base}{suffix}")
    support = adapter_source_loop_cursor_support(row) + r"""
pub proof fn lemma_difference_next_step_unfold<T: Ord>(
    state: SetAdapterState<T>,
)
    ensures
        state.variant == 0 && state.first.len() == 0 ==> (
            difference_next_step(state).returned.is_none()
                && difference_next_step(state).state == state
        ),
        state.variant == 0 && state.first.len() > 0 ==> (
            difference_next_step(state)
                == difference_stitch_step(
                    state.first[0],
                    state.first.drop_first(),
                    state.second,
                )
        ),
        state.variant == 1 ==> (
            difference_next_step(state)
                == difference_search_step(state.first, state.lookup)
        ),
        state.variant == 2 && state.first.len() == 0 ==> (
            difference_next_step(state).returned.is_none()
                && difference_next_step(state).state == state
        ),
        state.variant == 2 && state.first.len() > 0 ==> (
            difference_next_step(state).returned == Some(state.first[0])
                && difference_next_step(state).state == adapter_state(
                    2,
                    state.first.drop_first(),
                    Seq::empty(),
                    Seq::empty(),
                    None,
                    0,
                    None,
                )
        ),
{
}

pub proof fn lemma_difference_stitch_step_unfold<T: Ord>(
    current: T,
    first: Seq<T>,
    second: Seq<T>,
)
    ensures
        second.len() == 0 ==> (
            difference_stitch_step(current, first, second).returned
                == Some(current)
                && difference_stitch_step(current, first, second).state
                    == adapter_state(
                        0, first, second, Seq::empty(), None, 0, None,
                    )
        ),
        second.len() > 0
            && current.cmp_spec(&second[0]) == Ordering::Less ==> (
                difference_stitch_step(current, first, second).returned
                    == Some(current)
                    && difference_stitch_step(current, first, second).state
                        == adapter_state(
                            0, first, second, Seq::empty(), None, 0, None,
                        )
            ),
        second.len() > 0
            && current.cmp_spec(&second[0]) == Ordering::Equal
            && first.len() == 0 ==> (
                difference_stitch_step(current, first, second).returned
                    .is_none()
                    && difference_stitch_step(current, first, second).state
                        == adapter_state(
                            0, first, second, Seq::empty(), None, 0, None,
                        )
            ),
        second.len() > 0
            && current.cmp_spec(&second[0]) == Ordering::Equal
            && first.len() > 0 ==> (
                difference_stitch_step(current, first, second)
                    == difference_stitch_step(
                        first[0],
                        first.drop_first(),
                        second.drop_first(),
                    )
            ),
        second.len() > 0
            && current.cmp_spec(&second[0]) == Ordering::Greater ==> (
                difference_stitch_step(current, first, second)
                    == difference_stitch_step(
                        current,
                        first,
                        second.drop_first(),
                    )
            ),
{
    if second.len() > 0
        && current.cmp_spec(&second[0]) == Ordering::Equal
        && first.len() == 0
    {
        assert(first =~= Seq::empty());
    }
}

pub proof fn lemma_difference_search_step_unfold<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
)
    ensures
        first.len() == 0 ==> (
            difference_search_step(first, lookup).returned.is_none()
                && difference_search_step(first, lookup).state
                    == adapter_state(
                        1,
                        first,
                        Seq::empty(),
                        lookup,
                        None,
                        0,
                        None,
                    )
        ),
        first.len() > 0 && seq_contains_cmp(lookup, first[0]) ==> (
            difference_search_step(first, lookup)
                == difference_search_step(first.drop_first(), lookup)
        ),
        first.len() > 0 && !seq_contains_cmp(lookup, first[0]) ==> (
            difference_search_step(first, lookup).returned == Some(first[0])
                && difference_search_step(first, lookup).state
                    == adapter_state(
                        1,
                        first.drop_first(),
                        Seq::empty(),
                        lookup,
                        None,
                        0,
                        None,
                    )
        ),
{
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {base}<'a, T: Ord, A: Allocator + Clone>(
    this: &mut Difference<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            difference_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == difference_source_state(*old(this)).first[0],
            None => true,
        }},
        difference_source_state(*final(this)) == if
            difference_source_state(*old(this)).first.len() > 0
        {{
            adapter_state(
                0,
                difference_source_state(*old(this)).first.drop_first(),
                difference_source_state(*old(this)).second,
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            difference_source_state(*old(this))
        }},
        difference_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_read_source_discriminant<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &Difference<'a, T, A>,
) -> (source_branch: u8)
    ensures
        source_branch == difference_source_state(*this).variant as u8,
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_peek_other<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &Difference<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            difference_source_state(*this).second.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value == difference_source_state(*this).second[0],
            None => true,
        }},
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_compare<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    left: &'a T,
    right: &'a T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == left.cmp_spec(right)
        ),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_next_other<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Difference<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            difference_source_state(*old(this)).second.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == difference_source_state(*old(this)).second[0],
            None => true,
        }},
        difference_source_state(*final(this)) == if
            difference_source_state(*old(this)).second.len() > 0
        {{
            adapter_state(
                0,
                difference_source_state(*old(this)).first,
                difference_source_state(*old(this)).second.drop_first(),
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            difference_source_state(*old(this))
        }},
        difference_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_search_next_self<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Difference<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 1,
    ensures
        project_map_entry(result).is_some() <==>
            difference_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == difference_source_state(*old(this)).first[0],
            None => true,
        }},
        difference_source_state(*final(this)) == adapter_state(
            1,
            if difference_source_state(*old(this)).first.len() > 0 {{
                difference_source_state(*old(this)).first.drop_first()
            }} else {{
                difference_source_state(*old(this)).first
            }},
            Seq::empty(),
            difference_source_state(*old(this)).lookup,
            None,
            0,
            None,
        ),
        difference_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_search_contains<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &Difference<'a, T, A>,
    value: &'a T,
) -> (result: MapBoolResult)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 1,
    ensures
        obeys_cmp::<T>() ==> (
            result.value == seq_contains_cmp(
                difference_source_state(*this).lookup,
                *value,
            )
        ),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_iterate_next<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Difference<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        difference_source_state_law(*this),
        difference_source_state(*this).variant == 2,
    ensures
        project_map_entry(result).is_some() <==>
            difference_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == difference_source_state(*old(this)).first[0],
            None => true,
        }},
        difference_source_state(*final(this)) == if
            difference_source_state(*old(this)).first.len() > 0
        {{
            adapter_state(
                2,
                difference_source_state(*old(this)).first.drop_first(),
                Seq::empty(),
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            difference_source_state(*old(this))
        }},
        difference_source_state_law(*final(this)),
{{
    loop {{ }}
}}
"""
    body = f"""proof {{
        reveal_private_cursor_projection(this);
    }}
    let ghost initial_remaining = difference_remaining(*this);
    let ghost initial_state = difference_source_state(*this);
    let source_branch = {call('_read_source_discriminant')}(&*this);
    proof {{
        lemma_difference_next_step_unfold(initial_state);
    }}
    match source_branch {{
        0 => {{
            assert(initial_state.variant == 0);
            let first = {call('')}(this);
            match project_map_entry_exec(first) {{
                None => {{
                    proof {{
                        assert(initial_state.first.len() == 0);
                        assert(
                            difference_source_state(*this)
                                == difference_next_step(initial_state).state
                        );
                        if obeys_cmp::<T>() {{
                            assert(option_ref_matches(
                                None,
                                difference_next_step(initial_state).returned,
                            ));
                            reveal_private_cursor_projection(this);
                            lemma_difference_source_loop_finished(
                                initial_remaining,
                                initial_state,
                                difference_remaining(*this),
                                difference_source_state(*this),
                                None,
                            );
                        }}
                    }}
                    None
                }},
                Some(first_value) => {{
                    let mut self_next = first_value;
                    proof {{
                        assert(initial_state.first.len() > 0);
                        if obeys_cmp::<T>() {{
                            assert(
                                difference_next_step(initial_state)
                                    == difference_stitch_step(
                                        *self_next,
                                        difference_source_state(*this).first,
                                        difference_source_state(*this).second,
                                    )
                            );
                        }}
                    }}
                    loop
                        invariant
                            initial_remaining
                                == difference_remaining(*old(this)),
                            initial_state
                                == difference_source_state(*old(this)),
                            difference_source_state_law(*this),
                            difference_source_state(*this).variant == 0,
                            difference_source_state(*this) == adapter_state(
                                0,
                                difference_source_state(*this).first,
                                difference_source_state(*this).second,
                                Seq::empty(),
                                None,
                                0,
                                None,
                            ),
                            difference_source_cursor_step_law(
                                initial_remaining,
                                initial_state,
                            ),
                            obeys_cmp::<T>() ==> (
                                difference_next_step(initial_state)
                                    == difference_stitch_step(
                                        *self_next,
                                        difference_source_state(*this).first,
                                        difference_source_state(*this).second,
                                    )
                            ),
                        decreases
                            difference_source_state(*this).first.len()
                                + difference_source_state(*this).second.len(),
                    {{
                        let ghost before =
                            difference_source_state(*this);
                        proof {{
                            lemma_difference_stitch_step_unfold(
                                *self_next,
                                before.first,
                                before.second,
                            );
                        }}
                        let peeked = {call('_stitch_peek_other')}(&*this);
                        match project_map_entry_exec(peeked) {{
                            None => {{
                                proof {{
                                    assert(before.second.len() == 0);
                                    if obeys_cmp::<T>() {{
                                        assert(option_ref_matches(
                                            Some(self_next),
                                            difference_next_step(
                                                initial_state,
                                            ).returned,
                                        ));
                                        assert(
                                            difference_source_state(*this)
                                                == difference_next_step(
                                                    initial_state,
                                                ).state
                                        );
                                        reveal_private_cursor_projection(this);
                                        lemma_difference_source_loop_finished(
                                            initial_remaining,
                                            initial_state,
                                            difference_remaining(*this),
                                            difference_source_state(*this),
                                            Some(self_next),
                                        );
                                    }}
                                }}
                                return Some(self_next);
                            }},
                            Some(other_next) => {{
                                let order = {
                                    adapter_source_comparison_call_fragment(
                                        row,
                                        reverse_operands=mutation,
                                    )
                                };
                                match order.value {{
                                    Ordering::Less => {{
                                        proof {{
                                            if obeys_cmp::<T>() {{
                                                assert(option_ref_matches(
                                                    Some(self_next),
                                                    difference_next_step(
                                                        initial_state,
                                                    ).returned,
                                                ));
                                                assert(
                                                    difference_source_state(
                                                        *this,
                                                    ) == difference_next_step(
                                                        initial_state,
                                                    ).state
                                                );
                                                reveal_private_cursor_projection(
                                                    this,
                                                );
                                                lemma_difference_source_loop_finished(
                                                    initial_remaining,
                                                    initial_state,
                                                    difference_remaining(*this),
                                                    difference_source_state(*this),
                                                    Some(self_next),
                                                );
                                            }}
                                        }}
                                        return Some(self_next);
                                    }},
                                    Ordering::Equal => {{
                                        let next = {call('')}(this);
                                        match project_map_entry_exec(next) {{
                                            None => {{
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(option_ref_matches(
                                                            None,
                                                            difference_next_step(
                                                                initial_state,
                                                            ).returned,
                                                        ));
                                                        assert(
                                                            difference_source_state(
                                                                *this,
                                                            ) == difference_next_step(
                                                                initial_state,
                                                            ).state
                                                        );
                                                        reveal_private_cursor_projection(
                                                            this,
                                                        );
                                                        lemma_difference_source_loop_finished(
                                                            initial_remaining,
                                                            initial_state,
                                                            difference_remaining(
                                                                *this,
                                                            ),
                                                            difference_source_state(
                                                                *this,
                                                            ),
                                                            None,
                                                        );
                                                    }}
                                                }}
                                                return None;
                                            }},
                                            Some(next_value) => {{
                                                self_next = next_value;
                                                let _ = {call('_stitch_next_other')}(this);
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(
                                                            difference_next_step(
                                                                initial_state,
                                                            ) == difference_stitch_step(
                                                                *self_next,
                                                                difference_source_state(
                                                                    *this,
                                                                ).first,
                                                                difference_source_state(
                                                                    *this,
                                                                ).second,
                                                            )
                                                        );
                                                    }}
                                                }}
                                            }},
                                        }}
                                    }},
                                    Ordering::Greater => {{
                                        let _ = {call('_stitch_next_other')}(this);
                                        proof {{
                                            if obeys_cmp::<T>() {{
                                                assert(
                                                    difference_next_step(
                                                        initial_state,
                                                    ) == difference_stitch_step(
                                                        *self_next,
                                                        difference_source_state(
                                                            *this,
                                                        ).first,
                                                        difference_source_state(
                                                            *this,
                                                        ).second,
                                                    )
                                                );
                                            }}
                                        }}
                                    }},
                                }}
                            }},
                        }}
                    }}
                }},
            }}
        }},
        1 => {{
            assert(initial_state.variant == 1);
            loop
                invariant
                    initial_remaining
                        == difference_remaining(*old(this)),
                    initial_state
                        == difference_source_state(*old(this)),
                    difference_source_state_law(*this),
                    difference_source_state(*this).variant == 1,
                    difference_source_cursor_step_law(
                        initial_remaining,
                        initial_state,
                    ),
                    obeys_cmp::<T>() ==> (
                        difference_next_step(initial_state)
                            == difference_search_step(
                                difference_source_state(*this).first,
                                difference_source_state(*this).lookup,
                            )
                    ),
                decreases
                    difference_source_state(*this).first.len(),
            {{
                let ghost before = difference_source_state(*this);
                proof {{
                    lemma_difference_search_step_unfold(
                        before.first,
                        before.lookup,
                    );
                }}
                let next = {call('_search_next_self')}(this);
                match project_map_entry_exec(next) {{
                    None => {{
                        proof {{
                            if obeys_cmp::<T>() {{
                                assert(option_ref_matches(
                                    None,
                                    difference_next_step(
                                        initial_state,
                                    ).returned,
                                ));
                                assert(
                                    difference_source_state(*this)
                                        == difference_next_step(
                                            initial_state,
                                        ).state
                                );
                                reveal_private_cursor_projection(this);
                                lemma_difference_source_loop_finished(
                                    initial_remaining,
                                    initial_state,
                                    difference_remaining(*this),
                                    difference_source_state(*this),
                                    None,
                                );
                            }}
                        }}
                        return None;
                    }},
                    Some(self_next) => {{
                        let contained = {call('_search_contains')}(
                            &*this,
                            self_next,
                        ).value;
                        if !contained {{
                            proof {{
                                if obeys_cmp::<T>() {{
                                    assert(option_ref_matches(
                                        Some(self_next),
                                        difference_next_step(
                                            initial_state,
                                        ).returned,
                                    ));
                                    assert(
                                        difference_source_state(*this)
                                            == difference_next_step(
                                                initial_state,
                                            ).state
                                    );
                                    reveal_private_cursor_projection(this);
                                    lemma_difference_source_loop_finished(
                                        initial_remaining,
                                        initial_state,
                                        difference_remaining(*this),
                                        difference_source_state(*this),
                                        Some(self_next),
                                    );
                                }}
                            }}
                            return Some(self_next);
                        }}
                        proof {{
                            if obeys_cmp::<T>() {{
                                assert(
                                    difference_next_step(initial_state)
                                        == difference_search_step(
                                            difference_source_state(
                                                *this,
                                            ).first,
                                            difference_source_state(
                                                *this,
                                            ).lookup,
                                        )
                                );
                            }}
                        }}
                    }},
                }}
            }}
        }},
        _ => {{
            assert(source_branch == 2);
            assert(initial_state.variant == 2);
            let next = {call('_iterate_next')}(this);
            let answer = project_map_entry_exec(next);
            proof {{
                if obeys_cmp::<T>() {{
                    assert(option_ref_matches(
                        answer,
                        difference_next_step(initial_state).returned,
                    ));
                    assert(
                        difference_source_state(*this)
                            == difference_next_step(initial_state).state
                    );
                    reveal_private_cursor_projection(this);
                    lemma_difference_source_loop_finished(
                        initial_remaining,
                        initial_state,
                        difference_remaining(*this),
                        difference_source_state(*this),
                        answer,
                    );
                }}
            }}
            answer
        }},
    }}"""
    return support, dependency_source, body


def option_combinator_assumption_source(row: model.Row) -> str:
    operations = {
        record["operation"]
        for record in standard_library_assumption_boundaries(row)
    }
    parts: list[str] = []
    if "Option::and" in operations:
        parts.append(
            """
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<R, U>[ Option::<R>::and::<U> ](
    left: Option<R>,
    right: Option<U>,
) -> (result: Option<U>)
    where
        R: core::marker::Destruct,
        U: core::marker::Destruct,
    ensures
        result == match left {
            Some(_) => right,
            None => None,
        },
;
"""
        )
    if "Option::or" in operations:
        parts.append(
            """
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<R>[ Option::<R>::or ](
    left: Option<R>,
    right: Option<R>,
) -> (result: Option<R>)
    where R: core::marker::Destruct
    ensures
        result == match left {
            Some(value) => Some(value),
            None => right,
        },
;
"""
        )
    return "\n".join(parts)


def symmetric_difference_source_loop_composition(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency = dependency_function_name(row)
    duplicate_condition = (
        "!a_next.and(b_next).is_none()"
        if mutation
        else "a_next.and(b_next).is_none()"
    )
    support = (
        adapter_source_loop_cursor_support(row)
        + """
pub struct MapMergeEntries<'a, T> {
    pub left: Option<MapEntry<&'a T>>,
    pub right: Option<MapEntry<&'a T>>,
}
"""
        + option_combinator_assumption_source(row)
    )
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency}<'a, T: Ord>(
    this: &mut SymmetricDifference<'a, T>,
) -> (result: MapMergeEntries<'a, T>)
    requires
        symmetric_difference_source_state_law(*this),
    ensures
        option_ref_matches(
            project_map_entry(result.left),
            merge_next_step(
                symmetric_difference_source_state(*old(this)),
            ).left,
        ),
        option_ref_matches(
            project_map_entry(result.right),
            merge_next_step(
                symmetric_difference_source_state(*old(this)),
            ).right,
        ),
        symmetric_difference_source_state(*final(this))
            == merge_next_step(
                symmetric_difference_source_state(*old(this)),
            ).state,
        symmetric_difference_source_state_law(*final(this)),
        project_map_entry(result.left).is_some()
            && project_map_entry(result.right).is_some() ==> (
                merge_left_remaining(
                    symmetric_difference_source_state(*final(this)),
                ).len()
                    + merge_right_remaining(
                        symmetric_difference_source_state(*final(this)),
                    ).len()
                < merge_left_remaining(
                    symmetric_difference_source_state(*old(this)),
                ).len()
                    + merge_right_remaining(
                        symmetric_difference_source_state(*old(this)),
                    ).len()
            ),
{{
    loop {{ }}
}}
"""
    body = f"""proof {{
        reveal_private_cursor_projection(this);
    }}
    let ghost initial_remaining =
        symmetric_difference_remaining(*this);
    let ghost initial_state =
        symmetric_difference_source_state(*this);
    loop
        invariant
            initial_remaining
                == symmetric_difference_remaining(*old(this)),
            initial_state
                == symmetric_difference_source_state(*old(this)),
            symmetric_difference_source_state_law(*this),
            symmetric_difference_source_cursor_step_law(
                initial_remaining,
                initial_state,
            ),
            symmetric_difference_next_step(initial_state)
                == symmetric_difference_next_step(
                    symmetric_difference_source_state(*this),
                ),
        decreases
            merge_left_remaining(
                symmetric_difference_source_state(*this),
            ).len()
                + merge_right_remaining(
                    symmetric_difference_source_state(*this),
                ).len(),
    {{
        let ghost before =
            symmetric_difference_source_state(*this);
        let pair = {generic_call_name(row, dependency)}(this);
        let a_next = project_map_entry_exec(pair.left);
        let b_next = project_map_entry_exec(pair.right);
        if {duplicate_condition} {{
            let answer = a_next.or(b_next);
            proof {{
                if obeys_cmp::<T>() {{
                    assert(
                        symmetric_difference_next_step(initial_state)
                            == symmetric_difference_next_step(before)
                    );
                    assert(
                        option_ref_matches(
                            answer,
                            symmetric_difference_next_step(
                                initial_state,
                            ).returned,
                        )
                    );
                    assert(
                        symmetric_difference_source_state(*this)
                            == symmetric_difference_next_step(
                                initial_state,
                            ).state
                    );
                    reveal_private_cursor_projection(this);
                    lemma_symmetric_difference_source_loop_finished(
                        initial_remaining,
                        initial_state,
                        symmetric_difference_remaining(*this),
                        symmetric_difference_source_state(*this),
                        answer,
                    );
                }}
            }}
            return answer;
        }}
        proof {{
            assert(a_next.is_some() && b_next.is_some());
            assert(
                symmetric_difference_next_step(initial_state)
                    == symmetric_difference_next_step(
                        symmetric_difference_source_state(*this),
                    )
            );
        }}
    }}"""
    return support, dependency_source, body


def union_candidate_selection_composition(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    dependency = dependency_function_name(row)
    selection = "a_next" if mutation else "a_next.or(b_next)"
    support = (
        adapter_source_loop_cursor_support(row)
        + """
pub struct MapMergeEntries<'a, T> {
    pub left: Option<MapEntry<&'a T>>,
    pub right: Option<MapEntry<&'a T>>,
    pub state: Ghost<SetAdapterState<T>>,
    pub valid: bool,
}
"""
        + option_combinator_assumption_source(row)
    )
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency}<'a, T: Ord>(
    this: &mut Union<'a, T>,
) -> (result: MapMergeEntries<'a, T>)
    requires
        union_source_state_law(*this),
    ensures
        option_ref_matches(
            project_map_entry(result.left),
            merge_next_step(
                union_inner_state(*old(this)),
            ).left,
        ),
        option_ref_matches(
            project_map_entry(result.right),
            merge_next_step(
                union_inner_state(*old(this)),
            ).right,
        ),
        result.state@ == merge_next_step(
            union_inner_state(*old(this)),
        ).state,
        union_inner_state(*final(this)) == result.state@,
        union_inner_state_law(*final(this)) == result.valid,
        result.valid,
{{
    loop {{ }}
}}
"""
    body = f"""proof {{
        reveal_private_cursor_projection(this);
    }}
    let ghost initial_remaining = union_remaining(*this);
    let ghost initial_state = union_source_state(*this);
    let pair = {generic_call_name(row, dependency)}(this);
    let a_next = project_map_entry_exec(pair.left);
    let b_next = project_map_entry_exec(pair.right);
    let answer = {selection};
    proof {{
        if obeys_cmp::<T>() {{
            assert(option_ref_matches(
                answer,
                union_next_step(initial_state).returned,
            ));
            reveal_private_cursor_projection(this);
            assert(
                union_source_state(*this)
                    == union_next_step(initial_state).state
            );
            lemma_union_candidate_selection_finished(
                initial_remaining,
                initial_state,
                union_remaining(*this),
                union_source_state(*this),
                answer,
            );
        }}
    }}
    answer"""
    return support, dependency_source, body


def intersection_source_loop_composition(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    base = dependency_function_name(row)
    call = lambda suffix: generic_call_name(row, f"{base}{suffix}")
    support = adapter_source_loop_cursor_support(row) + r"""
pub proof fn lemma_intersection_next_step_unfold<T: Ord>(
    state: SetAdapterState<T>,
)
    ensures
        state.variant == 0 && state.first.len() == 0 ==> (
            intersection_next_step(state).returned.is_none()
                && intersection_next_step(state).state == state
        ),
        state.variant == 0 && state.first.len() > 0
            && state.second.len() == 0 ==> (
                intersection_next_step(state).returned.is_none()
                    && intersection_next_step(state).state == adapter_state(
                        0,
                        state.first.drop_first(),
                        Seq::empty(),
                        Seq::empty(),
                        None,
                        0,
                        None,
                    )
            ),
        state.variant == 0 && state.first.len() > 0
            && state.second.len() > 0 ==> (
                intersection_next_step(state)
                    == intersection_stitch_scan(
                        state.first[0],
                        state.first.drop_first(),
                        state.second[0],
                        state.second.drop_first(),
                    )
            ),
        state.variant == 1 ==> (
            intersection_next_step(state)
                == intersection_search_step(state.first, state.lookup)
        ),
        2 <= state.variant <= 3 ==> (
            intersection_next_step(state).returned == state.answer
                && intersection_next_step(state).state == adapter_state(
                    2,
                    Seq::empty(),
                    Seq::empty(),
                    Seq::empty(),
                    None,
                    0,
                    None,
                )
        ),
{
}

pub proof fn lemma_intersection_stitch_step_unfold<T: Ord>(
    a: T,
    a_tail: Seq<T>,
    b: T,
    b_tail: Seq<T>,
)
    ensures
        a.cmp_spec(&b) == Ordering::Equal ==> (
            intersection_stitch_scan(a, a_tail, b, b_tail).returned
                == Some(a)
                && intersection_stitch_scan(a, a_tail, b, b_tail).state
                    == adapter_state(
                        0,
                        a_tail,
                        b_tail,
                        Seq::empty(),
                        None,
                        0,
                        None,
                    )
        ),
        a.cmp_spec(&b) == Ordering::Less && a_tail.len() == 0 ==> (
            intersection_stitch_scan(a, a_tail, b, b_tail).returned
                .is_none()
                && intersection_stitch_scan(a, a_tail, b, b_tail).state
                    == adapter_state(
                        0,
                        Seq::empty(),
                        b_tail,
                        Seq::empty(),
                        None,
                        0,
                        None,
                    )
        ),
        a.cmp_spec(&b) == Ordering::Less && a_tail.len() > 0 ==> (
            intersection_stitch_scan(a, a_tail, b, b_tail)
                == intersection_stitch_scan(
                    a_tail[0],
                    a_tail.drop_first(),
                    b,
                    b_tail,
                )
        ),
        a.cmp_spec(&b) == Ordering::Greater && b_tail.len() == 0 ==> (
            intersection_stitch_scan(a, a_tail, b, b_tail).returned
                .is_none()
                && intersection_stitch_scan(a, a_tail, b, b_tail).state
                    == adapter_state(
                        0,
                        a_tail,
                        Seq::empty(),
                        Seq::empty(),
                        None,
                        0,
                        None,
                    )
        ),
        a.cmp_spec(&b) == Ordering::Greater && b_tail.len() > 0 ==> (
            intersection_stitch_scan(a, a_tail, b, b_tail)
                == intersection_stitch_scan(
                    a,
                    a_tail,
                    b_tail[0],
                    b_tail.drop_first(),
                )
        ),
{
    if a.cmp_spec(&b) == Ordering::Less && a_tail.len() == 0 {
        assert(a_tail =~= Seq::empty());
    }
    if a.cmp_spec(&b) == Ordering::Greater && b_tail.len() == 0 {
        assert(b_tail =~= Seq::empty());
    }
}

pub proof fn lemma_intersection_search_step_unfold<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
)
    ensures
        first.len() == 0 ==> (
            intersection_search_step(first, lookup).returned.is_none()
                && intersection_search_step(first, lookup).state
                    == adapter_state(
                        1,
                        first,
                        Seq::empty(),
                        lookup,
                        None,
                        0,
                        None,
                    )
        ),
        first.len() > 0 && seq_contains_cmp(lookup, first[0]) ==> (
            intersection_search_step(first, lookup).returned == Some(first[0])
                && intersection_search_step(first, lookup).state
                    == adapter_state(
                        1,
                        first.drop_first(),
                        Seq::empty(),
                        lookup,
                        None,
                        0,
                        None,
                    )
        ),
        first.len() > 0 && !seq_contains_cmp(lookup, first[0]) ==> (
            intersection_search_step(first, lookup)
                == intersection_search_step(first.drop_first(), lookup)
        ),
{
}
"""
    dependency_source = f"""
#[verifier::external_body]
pub fn {base}<'a, T: Ord, A: Allocator + Clone>(
    this: &mut Intersection<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            intersection_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == intersection_source_state(*old(this)).first[0],
            None => true,
        }},
        intersection_source_state(*final(this)) == if
            intersection_source_state(*old(this)).first.len() > 0
        {{
            adapter_state(
                0,
                intersection_source_state(*old(this)).first.drop_first(),
                intersection_source_state(*old(this)).second,
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            intersection_source_state(*old(this))
        }},
        intersection_source_state(*old(this)).first.len() > 0
            && intersection_source_state(*old(this)).second.len() == 0 ==> (
                intersection_next_step(
                    intersection_source_state(*old(this)),
                ).returned.is_none()
                    && intersection_next_step(
                        intersection_source_state(*old(this)),
                    ).state == intersection_source_state(*final(this))
            ),
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_read_source_discriminant<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &Intersection<'a, T, A>,
) -> (source_branch: u8)
    ensures
        source_branch == intersection_source_state(*this).variant as u8,
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_next_b<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Intersection<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            intersection_source_state(*old(this)).second.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == intersection_source_state(*old(this)).second[0],
            None => true,
        }},
        intersection_source_state(*final(this)) == if
            intersection_source_state(*old(this)).second.len() > 0
        {{
            adapter_state(
                0,
                intersection_source_state(*old(this)).first,
                intersection_source_state(*old(this)).second.drop_first(),
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            intersection_source_state(*old(this))
        }},
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_compare<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    left: &'a T,
    right: &'a T,
) -> (result: MapOrderingResult)
    ensures
        obeys_cmp::<T>() ==> (
            result.value == left.cmp_spec(right)
        ),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_advance_a<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Intersection<'a, T, A>,
    a: &'a T,
    b: &'a T,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            intersection_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == intersection_source_state(*old(this)).first[0],
            None => true,
        }},
        intersection_source_state(*final(this)) == if
            intersection_source_state(*old(this)).first.len() > 0
        {{
            adapter_state(
                0,
                intersection_source_state(*old(this)).first.drop_first(),
                intersection_source_state(*old(this)).second,
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            intersection_source_state(*old(this))
        }},
        obeys_cmp::<T>() && a.cmp_spec(b) == Ordering::Less ==> (
            match project_map_entry(result) {{
                Some(value) => intersection_stitch_scan(
                    *a,
                    intersection_source_state(*old(this)).first,
                    *b,
                    intersection_source_state(*old(this)).second,
                ) == intersection_stitch_scan(
                    *value,
                    intersection_source_state(*final(this)).first,
                    *b,
                    intersection_source_state(*final(this)).second,
                ),
                None => (
                    intersection_stitch_scan(
                        *a,
                        intersection_source_state(*old(this)).first,
                        *b,
                        intersection_source_state(*old(this)).second,
                    ).returned.is_none()
                        && intersection_stitch_scan(
                            *a,
                            intersection_source_state(*old(this)).first,
                            *b,
                            intersection_source_state(*old(this)).second,
                        ).state
                            == intersection_source_state(*final(this))
                ),
            }}
        ),
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_stitch_advance_b<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Intersection<'a, T, A>,
    a: &'a T,
    b: &'a T,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 0,
    ensures
        project_map_entry(result).is_some() <==>
            intersection_source_state(*old(this)).second.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == intersection_source_state(*old(this)).second[0],
            None => true,
        }},
        intersection_source_state(*final(this)) == if
            intersection_source_state(*old(this)).second.len() > 0
        {{
            adapter_state(
                0,
                intersection_source_state(*old(this)).first,
                intersection_source_state(*old(this)).second.drop_first(),
                Seq::empty(),
                None,
                0,
                None,
            )
        }} else {{
            intersection_source_state(*old(this))
        }},
        obeys_cmp::<T>() && a.cmp_spec(b) == Ordering::Greater ==> (
            match project_map_entry(result) {{
                Some(value) => intersection_stitch_scan(
                    *a,
                    intersection_source_state(*old(this)).first,
                    *b,
                    intersection_source_state(*old(this)).second,
                ) == intersection_stitch_scan(
                    *a,
                    intersection_source_state(*final(this)).first,
                    *value,
                    intersection_source_state(*final(this)).second,
                ),
                None => (
                    intersection_stitch_scan(
                        *a,
                        intersection_source_state(*old(this)).first,
                        *b,
                        intersection_source_state(*old(this)).second,
                    ).returned.is_none()
                        && intersection_stitch_scan(
                            *a,
                            intersection_source_state(*old(this)).first,
                            *b,
                            intersection_source_state(*old(this)).second,
                        ).state
                            == intersection_source_state(*final(this))
                ),
            }}
        ),
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_search_next_small<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Intersection<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 1,
    ensures
        project_map_entry(result).is_some() <==>
            intersection_source_state(*old(this)).first.len() > 0,
        match project_map_entry(result) {{
            Some(value) => *value
                == intersection_source_state(*old(this)).first[0],
            None => true,
        }},
        intersection_source_state(*final(this)) == adapter_state(
            1,
            if intersection_source_state(*old(this)).first.len() > 0 {{
                intersection_source_state(*old(this)).first.drop_first()
            }} else {{
                intersection_source_state(*old(this)).first
            }},
            Seq::empty(),
            intersection_source_state(*old(this)).lookup,
            None,
            0,
            None,
        ),
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_search_contains<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &Intersection<'a, T, A>,
    value: &'a T,
) -> (result: MapBoolResult)
    requires
        intersection_source_state_law(*this),
        intersection_source_state(*this).variant == 1,
    ensures
        obeys_cmp::<T>() ==> (
            result.value == seq_contains_cmp(
                intersection_source_state(*this).lookup,
                *value,
            )
        ),
{{
    loop {{ }}
}}

#[verifier::external_body]
pub fn {base}_answer_take<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    this: &mut Intersection<'a, T, A>,
) -> (result: Option<MapEntry<&'a T>>)
    requires
        intersection_source_state_law(*this),
        2 <= intersection_source_state(*this).variant <= 3,
    ensures
        option_ref_matches(
            project_map_entry(result),
            intersection_source_state(*old(this)).answer,
        ),
        intersection_source_state(*final(this)) == adapter_state(
            2,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        ),
        intersection_source_state_law(*final(this)),
{{
    loop {{ }}
}}
"""
    body = f"""proof {{
        reveal_private_cursor_projection(this);
    }}
    let ghost initial_remaining = intersection_remaining(*this);
    let ghost initial_state = intersection_source_state(*this);
    let source_branch = {call('_read_source_discriminant')}(&*this);
    proof {{
        lemma_intersection_next_step_unfold(initial_state);
    }}
    match source_branch {{
        0 => {{
            assert(initial_state.variant == 0);
            let first = {call('')}(this);
            match project_map_entry_exec(first) {{
                None => {{
                    proof {{
                        assert(initial_state.first.len() == 0);
                        assert(
                            intersection_source_state(*this)
                                == intersection_next_step(initial_state).state
                        );
                        if obeys_cmp::<T>() {{
                            assert(option_ref_matches(
                                None,
                                intersection_next_step(initial_state).returned,
                            ));
                            reveal_private_cursor_projection(this);
                            lemma_intersection_source_loop_finished(
                                initial_remaining,
                                initial_state,
                                intersection_remaining(*this),
                                intersection_source_state(*this),
                                None,
                            );
                        }}
                    }}
                    None
                }},
                Some(first_value) => {{
                    let ghost after_first =
                        intersection_source_state(*this);
                    proof {{
                        if initial_state.second.len() == 0 {{
                            assert(
                                after_first
                                    == intersection_next_step(
                                        initial_state,
                                    ).state
                            );
                        }}
                    }}
                    let second = {call('_stitch_next_b')}(this);
                    match project_map_entry_exec(second) {{
                        None => {{
                            proof {{
                                if obeys_cmp::<T>() {{
                                    assert(option_ref_matches(
                                        None,
                                        intersection_next_step(
                                            initial_state,
                                        ).returned,
                                    ));
                                    assert(
                                        intersection_source_state(*this)
                                            == intersection_next_step(
                                                initial_state,
                                            ).state
                                    );
                                    reveal_private_cursor_projection(this);
                                    lemma_intersection_source_loop_finished(
                                        initial_remaining,
                                        initial_state,
                                        intersection_remaining(*this),
                                        intersection_source_state(*this),
                                        None,
                                    );
                                }}
                            }}
                            None
                        }},
                        Some(second_value) => {{
                            let mut a_next = first_value;
                            let mut b_next = second_value;
                            proof {{
                                if obeys_cmp::<T>() {{
                                    assert(
                                        intersection_next_step(initial_state)
                                            == intersection_stitch_scan(
                                                *a_next,
                                                intersection_source_state(
                                                    *this,
                                                ).first,
                                                *b_next,
                                                intersection_source_state(
                                                    *this,
                                                ).second,
                                            )
                                    );
                                }}
                            }}
                            loop
                                invariant
                                    initial_remaining
                                        == intersection_remaining(*old(this)),
                                    initial_state
                                        == intersection_source_state(
                                            *old(this),
                                        ),
                                    intersection_source_state_law(*this),
                                    intersection_source_state(*this).variant == 0,
                                    intersection_source_state(*this)
                                        == adapter_state(
                                            0,
                                            intersection_source_state(
                                                *this,
                                            ).first,
                                            intersection_source_state(
                                                *this,
                                            ).second,
                                            Seq::empty(),
                                            None,
                                            0,
                                            None,
                                        ),
                                    intersection_source_cursor_step_law(
                                        initial_remaining,
                                        initial_state,
                                    ),
                                    obeys_cmp::<T>() ==> (
                                        intersection_next_step(initial_state)
                                            == intersection_stitch_scan(
                                                *a_next,
                                                intersection_source_state(
                                                    *this,
                                                ).first,
                                                *b_next,
                                                intersection_source_state(
                                                    *this,
                                                ).second,
                                            )
                                    ),
                                decreases
                                    intersection_source_state(*this).first.len()
                                        + intersection_source_state(
                                            *this,
                                        ).second.len(),
                            {{
                                let ghost before =
                                    intersection_source_state(*this);
                                proof {{
                                    lemma_intersection_stitch_step_unfold(
                                        *a_next,
                                        before.first,
                                        *b_next,
                                        before.second,
                                    );
                                }}
                                let order = {
                                    adapter_source_comparison_call_fragment(
                                        row,
                                        reverse_operands=mutation,
                                    )
                                };
                                match order.value {{
                                    Ordering::Less => {{
                                        let next = {call('_stitch_advance_a')}(
                                            this,
                                            a_next,
                                            b_next,
                                        );
                                        match project_map_entry_exec(next) {{
                                            None => {{
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(option_ref_matches(
                                                            None,
                                                            intersection_next_step(
                                                                initial_state,
                                                            ).returned,
                                                        ));
                                                        assert(
                                                            intersection_source_state(
                                                                *this,
                                                            ) == intersection_next_step(
                                                                initial_state,
                                                            ).state
                                                        );
                                                        reveal_private_cursor_projection(
                                                            this,
                                                        );
                                                        lemma_intersection_source_loop_finished(
                                                            initial_remaining,
                                                            initial_state,
                                                            intersection_remaining(
                                                                *this,
                                                            ),
                                                            intersection_source_state(
                                                                *this,
                                                            ),
                                                            None,
                                                        );
                                                    }}
                                                }}
                                                return None;
                                            }},
                                            Some(next_value) => {{
                                                a_next = next_value;
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(
                                                            intersection_next_step(
                                                                initial_state,
                                                            ) == intersection_stitch_scan(
                                                                *a_next,
                                                                intersection_source_state(
                                                                    *this,
                                                                ).first,
                                                                *b_next,
                                                                intersection_source_state(
                                                                    *this,
                                                                ).second,
                                                            )
                                                        );
                                                    }}
                                                }}
                                            }},
                                        }}
                                    }},
                                    Ordering::Greater => {{
                                        let next = {call('_stitch_advance_b')}(
                                            this,
                                            a_next,
                                            b_next,
                                        );
                                        match project_map_entry_exec(next) {{
                                            None => {{
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(option_ref_matches(
                                                            None,
                                                            intersection_next_step(
                                                                initial_state,
                                                            ).returned,
                                                        ));
                                                        assert(
                                                            intersection_source_state(
                                                                *this,
                                                            ) == intersection_next_step(
                                                                initial_state,
                                                            ).state
                                                        );
                                                        reveal_private_cursor_projection(
                                                            this,
                                                        );
                                                        lemma_intersection_source_loop_finished(
                                                            initial_remaining,
                                                            initial_state,
                                                            intersection_remaining(
                                                                *this,
                                                            ),
                                                            intersection_source_state(
                                                                *this,
                                                            ),
                                                            None,
                                                        );
                                                    }}
                                                }}
                                                return None;
                                            }},
                                            Some(next_value) => {{
                                                b_next = next_value;
                                                proof {{
                                                    if obeys_cmp::<T>() {{
                                                        assert(
                                                            intersection_next_step(
                                                                initial_state,
                                                            ) == intersection_stitch_scan(
                                                                *a_next,
                                                                intersection_source_state(
                                                                    *this,
                                                                ).first,
                                                                *b_next,
                                                                intersection_source_state(
                                                                    *this,
                                                                ).second,
                                                            )
                                                        );
                                                    }}
                                                }}
                                            }},
                                        }}
                                    }},
                                    Ordering::Equal => {{
                                        proof {{
                                            if obeys_cmp::<T>() {{
                                                assert(option_ref_matches(
                                                    Some(a_next),
                                                    intersection_next_step(
                                                        initial_state,
                                                    ).returned,
                                                ));
                                                assert(
                                                    intersection_source_state(
                                                        *this,
                                                    ) == intersection_next_step(
                                                        initial_state,
                                                    ).state
                                                );
                                                reveal_private_cursor_projection(
                                                    this,
                                                );
                                                lemma_intersection_source_loop_finished(
                                                    initial_remaining,
                                                    initial_state,
                                                    intersection_remaining(*this),
                                                    intersection_source_state(
                                                        *this,
                                                    ),
                                                    Some(a_next),
                                                );
                                            }}
                                        }}
                                        return Some(a_next);
                                    }},
                                }}
                            }}
                        }},
                    }}
                }},
            }}
        }},
        1 => {{
            assert(initial_state.variant == 1);
            loop
                invariant
                    initial_remaining
                        == intersection_remaining(*old(this)),
                    initial_state
                        == intersection_source_state(*old(this)),
                    intersection_source_state_law(*this),
                    intersection_source_state(*this).variant == 1,
                    intersection_source_cursor_step_law(
                        initial_remaining,
                        initial_state,
                    ),
                    obeys_cmp::<T>() ==> (
                        intersection_next_step(initial_state)
                            == intersection_search_step(
                                intersection_source_state(*this).first,
                                intersection_source_state(*this).lookup,
                            )
                    ),
                decreases
                    intersection_source_state(*this).first.len(),
            {{
                proof {{
                    lemma_intersection_search_step_unfold(
                        intersection_source_state(*this).first,
                        intersection_source_state(*this).lookup,
                    );
                }}
                let next = {call('_search_next_small')}(this);
                match project_map_entry_exec(next) {{
                    None => {{
                        proof {{
                            if obeys_cmp::<T>() {{
                                assert(option_ref_matches(
                                    None,
                                    intersection_next_step(
                                        initial_state,
                                    ).returned,
                                ));
                                assert(
                                    intersection_source_state(*this)
                                        == intersection_next_step(
                                            initial_state,
                                        ).state
                                );
                                reveal_private_cursor_projection(this);
                                lemma_intersection_source_loop_finished(
                                    initial_remaining,
                                    initial_state,
                                    intersection_remaining(*this),
                                    intersection_source_state(*this),
                                    None,
                                );
                            }}
                        }}
                        return None;
                    }},
                    Some(small_next) => {{
                        let contained = {call('_search_contains')}(
                            &*this,
                            small_next,
                        ).value;
                        if contained {{
                            proof {{
                                if obeys_cmp::<T>() {{
                                    assert(option_ref_matches(
                                        Some(small_next),
                                        intersection_next_step(
                                            initial_state,
                                        ).returned,
                                    ));
                                    assert(
                                        intersection_source_state(*this)
                                            == intersection_next_step(
                                                initial_state,
                                            ).state
                                    );
                                    reveal_private_cursor_projection(this);
                                    lemma_intersection_source_loop_finished(
                                        initial_remaining,
                                        initial_state,
                                        intersection_remaining(*this),
                                        intersection_source_state(*this),
                                        Some(small_next),
                                    );
                                }}
                            }}
                            return Some(small_next);
                        }}
                        proof {{
                            if obeys_cmp::<T>() {{
                                assert(
                                    intersection_next_step(initial_state)
                                        == intersection_search_step(
                                            intersection_source_state(
                                                *this,
                                            ).first,
                                            intersection_source_state(
                                                *this,
                                            ).lookup,
                                        )
                                );
                            }}
                        }}
                    }},
                }}
            }}
        }},
        _ => {{
            assert(2 <= source_branch && source_branch <= 3);
            assert(2 <= initial_state.variant <= 3);
            let next = {call('_answer_take')}(this);
            let answer = project_map_entry_exec(next);
            proof {{
                if obeys_cmp::<T>() {{
                    assert(option_ref_matches(
                        answer,
                        intersection_next_step(initial_state).returned,
                    ));
                    assert(
                        intersection_source_state(*this)
                            == intersection_next_step(initial_state).state
                    );
                    reveal_private_cursor_projection(this);
                    lemma_intersection_source_loop_finished(
                        initial_remaining,
                        initial_state,
                        intersection_remaining(*this),
                        intersection_source_state(*this),
                        answer,
                    );
                }}
            }}
            answer
        }},
    }}"""
    return support, dependency_source, body


def adapter_source_loop_composition(
    row: model.Row,
    *,
    mutation: bool,
) -> tuple[str, str, str]:
    if row.owner["name"] == "Difference":
        return difference_source_loop_composition(
            row,
            mutation=mutation,
        )
    if row.owner["name"] == "SymmetricDifference":
        return symmetric_difference_source_loop_composition(
            row,
            mutation=mutation,
        )
    if row.owner["name"] == "Intersection":
        return intersection_source_loop_composition(
            row,
            mutation=mutation,
        )
    raise RuntimeError(
        f"{row.target_id}: missing source-owned adapter loop lowering"
    )


def selected_public_composition_override(
    row: model.Row,
    projection: Projection,
    inputs: list[tuple[str, str, str]],
    *,
    mutation: bool,
) -> tuple[str, str, str, str] | None:
    if union_left_biased_next(row):
        support, dependency_source, body = (
            union_candidate_selection_composition(
                row,
                mutation=mutation,
            )
        )
        return support, dependency_source, "", body
    if source_owned_adapter_loop(row):
        support, dependency_source, body = (
            adapter_source_loop_composition(row, mutation=mutation)
        )
        return support, dependency_source, "", body
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        support, dependency_source, body = (
            selected_adapter_composition_source(
                row,
                mutation=mutation,
            )
        )
        return support, dependency_source, "", body
    if row.semantic_family in {
        "symmetric_difference_adapter_construction",
        "union_adapter_construction",
    }:
        dependency_source, body = merge_adapter_composition_source(
            row,
            projection,
            mutation=mutation,
        )
        return "", dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_empty"
    ):
        dependency_source, body = is_empty_composition_source(
            row,
            mutation=mutation,
        )
        return "", dependency_source, "", body
    if row.target_id == "049_BTreeSet_Extend_extend_2153":
        support, dependency_source, body = (
            borrowed_extend_composition_source(
                row,
                mutation=mutation,
            )
        )
        return support, dependency_source, "", body
    if terminal_override_selected_method(row) is not None:
        dependency_source, body = terminal_override_composition_source(
            row,
            projection,
            mutation=mutation,
        )
        return "", dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "Default"
    ):
        dependency_source, body = default_composition_source(
            row,
            mutation=mutation,
        )
        return "", dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "IntoIterator"
        and row.function["name"] == "into_iter"
        and requires_selected_public_composition(row)
    ):
        dependency_source, body = (
            borrowed_into_iter_composition_source(
                row,
                mutation=mutation,
            )
        )
        return "", dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "Debug"
    ):
        support, dependency_source, body = debug_composition_source(
            row,
            mutation=mutation,
        )
        return support, dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait in {"Sub", "BitXor", "BitAnd", "BitOr"}
    ):
        support, dependency_source, body = (
            owned_set_operation_composition_source(
                row,
                mutation=mutation,
            )
        )
        return support, dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.trait == "Extend"
    ):
        support, dependency_source, body = extend_composition_source(
            row,
            mutation=mutation,
        )
        return support, dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "retain"
    ):
        support, dependency_source, body = real_retain_composition_source(
            row,
            mutation=mutation,
        )
        return support, dependency_source, "", body
    if (
        row.owner["name"] == "BTreeSet"
        and row.function["name"] == "is_disjoint"
    ):
        support, dependency_source = disjoint_composition_source(row)
        result = (
            "!next.is_none()"
            if mutation
            else "next.is_none()"
        )
        body = f"""proof {{
        reveal_btree_set_map_projection(this);
        reveal_btree_set_map_projection(other);
    }}
    let mut intersection =
        rust_1_96_selected_intersection(this, other);
    let ghost initial_remaining =
        intersection_remaining(intersection);
    let next = rust_1_96_selected_intersection_next(
        &mut intersection,
    );
    proof {{
        if obeys_cmp::<T>() {{
            lemma_sequence_empty_iff_set_empty(
                initial_remaining.unref(),
            );
            assert(
                initial_remaining.unref().to_set()
                    == wrapped_btree_map_keys(this).intersect(
                        wrapped_btree_map_keys(other),
                    )
            );
            reveal_btree_set_map_projection(this);
            reveal_btree_set_map_projection(other);
        }}
    }}
    {result}"""
        return support, dependency_source, "", body
    if not (
        row.owner["name"] == "BTreeSet"
        and row.semantic_family == "set_relation_observer"
        and row.function["name"] in {"is_subset", "is_superset"}
    ):
        return None
    dependency_name = dependency_function_name(row)
    dependency_source = f"""
#[verifier::external_body]
pub fn {dependency_name}<'a, T, A: Allocator + Clone>(
    this: &'a BTreeSet<T, A>,
    Ghost(source): Ghost<Seq<T>>,
    index: usize,
) -> (result: Option<MapEntry<&'a T>>)
    where T: Ord
    requires
        source == wrapped_btree_map_key_sequence(this),
        index < source.len(),
    ensures
        project_map_entry(result).is_some(),
        match project_map_entry(result) {{
            Some(value) => *value == source[index as int],
            None => false,
        }},
{{
    loop {{ }}
}}
"""
    scan_callee = generic_call_name(row, dependency_name)
    support = subset_composition_source(
        row,
        scan_callee,
        mutation=mutation,
    )
    if row.function["name"] == "is_superset":
        helper_call = (
            "rust_1_96_selected_is_subset_source(this, other)"
            if mutation
            else "rust_1_96_selected_is_subset_source(other, this)"
        )
    else:
        helper_call = "rust_1_96_selected_is_subset_source(this, other)"
    return support, dependency_source, "", helper_call


def implementation_source(row: model.Row, mutation: bool = False) -> str:
    lines = contract_lines(row)
    requirements = contract_requirements(row)
    dependency_name = dependency_function_name(row)
    dependency_callee = dependency_call_name(row)
    inputs, output, implementation_signature = signature_parts(
        row, "implementation"
    )
    projection = projection_for(row, output)
    branch = uses_private_branch(row)
    extra_inputs = (
        ((("source_branch", "u8"),) if branch else ())
    )
    _dep_inputs, _dep_output, dependency_signature = signature_parts(
        row,
        dependency_name,
        output_override=projection.lower_type,
        override_output=True,
        extra_inputs=extra_inputs,
    )
    if row.semantic_family == "ordered_callback_retain":
        dependency_signature = retain_dependency_signature(
            row, dependency_name, projection
        )
    if row.semantic_family == "ordered_extend_transition":
        dependency_signature = extend_dependency_signature(
            row, dependency_name, projection
        )
    dependency_lines = dependency_contract_lines(row, projection)
    implementation_lines = lines
    call_args = ", ".join(name for name, _rust_type, _source in inputs)
    call_prefix = f"{call_args}, " if call_args else ""
    dependency_requirements = list(requirements)
    if row.semantic_family in {
        "ordered_callback_retain",
        "ordered_extend_transition",
    }:
        dependency_requirements = []
    if branch:
        expected_branch = branch_source_value(row, inputs)
        dependency_requirements.append(
            f"source_branch == {expected_branch}"
        )
        selector_source, selector_call = branch_selector_source_and_call(
            row, inputs
        )
        arm_specs = branch_arm_specs(row)
        branch_names = dependency_function_names(row)
        branch_callees = dependency_call_names(row)
        sort_source = ""
        sort_call = ""
        if row.semantic_family == "sorted_deduplicating_conversion":
            sort_source, sort_call = sorted_conversion_sort_source(row)
        dependency_blocks: list[str] = []
        rendered_arms: list[str] = []
        for (
            pattern,
            branch_guard,
            _suffix,
        ), branch_name, branch_callee in zip(
            arm_specs, branch_names, branch_callees, strict=True
        ):
            extra_dependency_inputs: tuple[tuple[str, str], ...] = (
                ("source_branch", "u8"),
            )
            call_suffix = ""
            arm_prelude = branch_arm_prelude(row, pattern)
            if (
                row.semantic_family
                == "sorted_deduplicating_conversion"
                and pattern == "0"
            ):
                extra_dependency_inputs = (
                    *extra_dependency_inputs,
                    ("empty", "BTreeSet<T>"),
                )
                call_suffix = ", empty"
                arm_prelude += (
                    "            let empty = BTreeSet::<T>::new();\n"
                )
            if (
                row.semantic_family
                == "sorted_deduplicating_conversion"
                and pattern != "0"
            ):
                extra_dependency_inputs = (
                    *extra_dependency_inputs,
                    ("sorted", "MapStableSortedInput<T>"),
                )
                call_suffix = ", sorted"
                arm_prelude += (
                    f"            let sorted = {sort_call};\n"
                )
            if (
                row.owner["name"] == "ExtractIf"
                and row.function["name"] == "next"
                and pattern != "0"
            ):
                extra_dependency_inputs = (
                    *extra_dependency_inputs,
                    ("observed_remove", "bool"),
                )
                call_suffix += ", observed_remove"
            if retains_adapter_source_loop(row):
                extra_dependency_inputs = (
                    *extra_dependency_inputs,
                    ("completed_source_steps", "usize"),
                )
                call_suffix += ", completed_source_steps"
            _branch_inputs, _branch_output, branch_signature = (
                signature_parts(
                    row,
                    branch_name,
                    output_override=projection.lower_type,
                    override_output=True,
                    extra_inputs=extra_dependency_inputs,
                )
            )
            branch_requirements = [
                *requirements,
                f"source_branch == {expected_branch}",
                branch_guard,
            ]
            if (
                row.owner["name"] == "ExtractIf"
                and row.function["name"] == "next"
                and pattern != "0"
            ):
                branch_requirements.append(
                    "observed_remove == extract_if_decisions(*this)[0]"
                )
            if retains_adapter_source_loop(row):
                state = {
                    "Difference": "difference_source_state",
                    "SymmetricDifference": (
                        "symmetric_difference_source_state"
                    ),
                    "Intersection": "intersection_source_state",
                }[row.owner["name"]]
                branch_requirements.append(
                    "completed_source_steps as nat == "
                    f"{adapter_loop_steps_spec(row)}("
                    f"{state}(*old(this)), source_branch)"
                )
            operation_fact = branch_operation_fact(
                row, pattern, branch_guard
            )
            branch_lines = branch_dependency_contract_lines(
                row, pattern, dependency_lines
            )
            dependency_blocks.append(
                f"""#[verifier::external_body]
{branch_signature}
{render_requires(branch_requirements)}    ensures
{render_ensures([branch_guard, operation_fact, *branch_lines])}
{{
    loop {{ }}
}}"""
            )
            rendered_arms.append(
                f"""        {pattern} => {{
            assert({branch_guard});
{arm_prelude}            {branch_callee}({call_prefix}source_branch{call_suffix})
        }},"""
            )
        dependency_source = "\n\n".join(
            part
            for part in (*dependency_blocks, sort_source)
            if part
        )
        loop_source, loop_steps_call = (
            adapter_loop_control_source_and_call(row, inputs)
        )
        if loop_source:
            selector_source = "\n".join(
                part for part in (selector_source, loop_source) if part
            )
        selected_branch = (
            "0u8"
            if mutation
            and row.semantic_family == "sorted_deduplicating_conversion"
            else selector_call
        )
        branch_assignment = (
            f"let observed_source_branch = {selector_call};\n"
            "    let source_branch = if observed_source_branch == 0 "
            "{ 1 } else { 0 };"
            if mutation
            and adapter_loop_control_mutation_required(row)
            and not retains_adapter_source_loop(row)
            else f"let source_branch = {selected_branch};"
        )
        loop_increment = 2 if mutation else 1
        loop_control = (
            f"""    let source_steps = {loop_steps_call};
    let mut completed_source_steps: usize = 0;
    while completed_source_steps < source_steps
        invariant
            completed_source_steps <= source_steps,
        decreases
            source_steps - completed_source_steps,
    {{
        completed_source_steps =
            completed_source_steps + {loop_increment};
    }}
    assert(completed_source_steps == source_steps);
"""
            if retains_adapter_source_loop(row)
            else ""
        )
        dependency_call = (
            f"{branch_assignment}\n"
            f"{loop_control}"
            f"    let lower: {projection.lower_type} = match source_branch {{\n"
            f"{chr(10).join(rendered_arms)}\n"
            "    };"
        )
        if (
            row.owner["name"] == "ExtractIf"
            and row.function["name"] == "next"
        ):
            dependency_call = (
                "proof {\n"
                "        lemma_retain_callback_observation_lengths(\n"
                "            extract_if_predicate_state(*this),\n"
                "            extract_if_pending(*this),\n"
                "        );\n"
                "    }\n"
                f"    {dependency_call}"
            )
    else:
        if row.semantic_family == "ordered_callback_retain":
            dependency_call = retain_control_flow_body(
                row, dependency_callee, mutation=mutation
            )
        elif row.semantic_family == "ordered_extend_transition":
            dependency_call = extend_control_flow_body(
                row, dependency_callee, mutation=mutation
            )
        else:
            dependency_call = (
                f"let lower: {projection.lower_type} = "
                f"{dependency_callee}({call_args});"
            )
        selector_source = ""
        dependency_source = f"""#[verifier::external_body]
{dependency_signature}
{render_requires(dependency_requirements)}    ensures
{render_ensures(dependency_lines)}
{{
    loop {{ }}
}}"""
    if (
        mutation
        and projection.kind == "completion"
        and row.semantic_family
        not in {"ordered_callback_retain", "ordered_extend_transition"}
    ):
        dependency_call = ""
    if row.semantic_family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
    }:
        dependency_call = f"""let self_min = rust_1_96_selected_first(this);
    let self_max = rust_1_96_selected_last(this);
    let other_min = rust_1_96_selected_first(other);
    let other_max = rust_1_96_selected_last(other);
    let self_len = rust_1_96_selected_len(this);
    let other_len = rust_1_96_selected_len(other);
    let self_iter = rust_1_96_selected_iter(this);
    let other_iter = rust_1_96_selected_iter(other);
    proof {{
        assert(self_len as nat
            == wrapped_btree_map_key_sequence(this).len());
        assert(other_len as nat
            == wrapped_btree_map_key_sequence(other).len());
        assert(iter_remaining(self_iter).unref()
            == wrapped_btree_map_key_sequence(this));
        assert(iter_remaining(other_iter).unref()
            == wrapped_btree_map_key_sequence(other));
    }}
    {dependency_call}"""
    map_before, map_after = btree_map_bridge_calls(row, inputs)
    cursor_before, cursor_after = private_cursor_bridge_calls(row, inputs)
    dependency_call = "\n    ".join(
        part
        for part in (
            map_before,
            cursor_before,
            dependency_call,
            map_after,
            cursor_after,
        )
        if part
    )
    body_expression = (
        mutation_body_expression(row, projection)
        if mutation
        else projection.body_expression
    )
    if mutation and adapter_loop_control_mutation_required(row):
        body_expression = projection.body_expression
    if row.semantic_family == "ordered_callback_retain":
        body_expression = projection.body_expression
    if row.semantic_family == "ordered_extend_transition":
        body_expression = projection.body_expression
    if row.semantic_family == "extract_if_construction":
        body_expression = extract_if_constructor_body(mutation=mutation)
    if row.semantic_family in {
        "difference_adapter_construction",
        "symmetric_difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
    }:
        body_expression = adapter_constructor_body(
            row, projection, mutation=mutation
        )
    if row.semantic_family == "sorted_deduplicating_conversion":
        body_expression = set_constructor_body(
            projection, mutation=False
        )
    composition_override = selected_public_composition_override(
        row,
        projection,
        inputs,
        mutation=mutation,
    )
    composition_source = ""
    if composition_override is not None:
        (
            composition_source,
            dependency_source,
            dependency_call,
            body_expression,
        ) = composition_override
    title = (
        "Source-step mutation"
        if mutation
        else "Source-shaped implementation proof"
    )
    clause_hashes = "\n".join(
        f"// Accepted clause {index + 1} sha256: {hashlib.sha256(line.encode()).hexdigest()}"
        for index, line in enumerate(lines)
    )
    descriptor = mutation_descriptor(row)
    original_fragment = str(descriptor["original_fragment"]).replace(
        "\n", "\n// "
    )
    mutated_fragment = str(descriptor["mutated_fragment"]).replace(
        "\n", "\n// "
    )
    mutation_note = (
        f"// Mutated source step: {descriptor['source_step']}.\n"
        f"// Original fragment: {original_fragment}.\n"
        f"// Mutated fragment: {mutated_fragment}.\n"
        if mutation
        else ""
    )
    return f"""#![feature(allocator_api)]
#![allow(dead_code, unused_imports, unused_variables)]
// {title} for {row.canonical_target}.
// Rust source: {row.source_file}:{row.line_start}-{row.line_end}
// Source excerpt sha256: {row.source_sha256}
// Accepted contract fingerprint: {row.contract_fingerprint}
// Narrow source dependency: {dependency_operation(row)}.
// Lower return shape: {dependency_lower_shape(row, projection)}.
// The lower dependency cannot return the public target shape directly.
// The mutation changes only the executable body; the lower contract is identical.
{mutation_note}{clause_hashes}

use vstd::prelude::*;
use vstd::std_specs::btree::{{
    key_obeys_cmp_spec, spec_btree_set_len,
}};

include!("../../specs/btree_set_shared_vocabulary.rs");

verus! {{

{COMMON_PROJECTION_TYPES}
{btree_map_bridge_source(row)}
{private_cursor_bridge_source(row)}
{selected_observer_support_source(row)}
{callback_length_lemma_source(row)}
{retain_control_flow_source(row)}
{extend_control_flow_source(row)}
{extract_if_callback_source(row)}
{composition_source}
{projection_helper_source(row, projection) if projection_helper_required(projection) else ""}
{selector_source}
{dependency_source}

{implementation_signature}
{render_requires(requirements)}    ensures
{render_ensures(implementation_lines)}
{{
    {dependency_call}
    {body_expression}
}}

}} // verus!
"""


@dataclass(frozen=True)
class OutcomeField:
    name: str
    rust_type: str
    model_hint: str
    source_clause_hint: int


COMPLETENESS_INPUT_TYPES = {
    "order_laws": "bool",
    "pre_set": "Set<int>",
    "other_set": "Set<int>",
    "pre_seq": "Seq<int>",
    "other_seq": "Seq<int>",
    "input_seq": "Seq<int>",
    "remaining": "Seq<int>",
    "pending": "Seq<int>",
    "adapter_state": "AdapterStateModel",
    "item": "int",
    "pre_hasher": "int",
    "pre_formatter": "int",
    "hint_a": "nat",
    "hint_b": "nat",
    "hint_variant": "int",
    "pre_callback_count": "nat",
    "extract_initial_set": "Set<int>",
    "yielded": "Seq<int>",
    "predicate_state": "int",
    "predicate_seed": "int",
    "range_start_kind": "int",
    "range_start_value": "int",
    "range_end_kind": "int",
    "range_end_value": "int",
}


COMPLETENESS_MODEL = r"""
pub open spec fn seq_contains_model(items: Seq<int>, value: int) -> bool
    decreases items.len()
{
    items.len() > 0
        && (items[0] == value || seq_contains_model(items.drop_first(), value))
}

pub open spec fn strictly_increasing_model(items: Seq<int>) -> bool
    decreases items.len()
{
    items.len() <= 1
        || (items[0] < items[1] && strictly_increasing_model(items.drop_first()))
}

pub open spec fn borrowed_key_order_law_model(
    items: Seq<int>,
    _key: int,
) -> bool {
    strictly_increasing_model(items)
}

pub open spec fn nondecreasing_model(items: Seq<int>) -> bool
    decreases items.len()
{
    items.len() <= 1
        || (items[0] <= items[1] && nondecreasing_model(items.drop_first()))
}

pub open spec fn difference_sequence_model(
    left: Seq<int>,
    right: Seq<int>,
) -> Seq<int>
    decreases left.len()
{
    if left.len() == 0 {
        Seq::empty()
    } else if seq_contains_model(right, left[0]) {
        difference_sequence_model(left.drop_first(), right)
    } else {
        seq![left[0]] + difference_sequence_model(left.drop_first(), right)
    }
}

pub open spec fn intersection_sequence_model(
    left: Seq<int>,
    right: Seq<int>,
) -> Seq<int>
    decreases left.len()
{
    if left.len() == 0 {
        Seq::empty()
    } else if seq_contains_model(right, left[0]) {
        seq![left[0]] + intersection_sequence_model(left.drop_first(), right)
    } else {
        intersection_sequence_model(left.drop_first(), right)
    }
}

pub open spec fn union_sequence_model(
    left: Seq<int>,
    right: Seq<int>,
) -> Seq<int>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else if left[0] < right[0] {
        seq![left[0]] + union_sequence_model(left.drop_first(), right)
    } else if right[0] < left[0] {
        seq![right[0]] + union_sequence_model(left, right.drop_first())
    } else {
        seq![left[0]] + union_sequence_model(left.drop_first(), right.drop_first())
    }
}

pub open spec fn symmetric_difference_sequence_model(
    left: Seq<int>,
    right: Seq<int>,
) -> Seq<int>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else if left[0] < right[0] {
        seq![left[0]] + symmetric_difference_sequence_model(left.drop_first(), right)
    } else if right[0] < left[0] {
        seq![right[0]] + symmetric_difference_sequence_model(left, right.drop_first())
    } else {
        symmetric_difference_sequence_model(left.drop_first(), right.drop_first())
    }
}

pub open spec fn representative_model(items: Seq<int>, value: int) -> Option<int>
    decreases items.len()
{
    if items.len() == 0 {
        None
    } else if items[0] == value {
        Some(items[0])
    } else {
        representative_model(items.drop_first(), value)
    }
}

pub open spec fn insert_keep_existing_model(
    items: Seq<int>,
    value: int,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else if value < items[0] {
        seq![value] + items
    } else if value == items[0] {
        items
    } else {
        seq![items[0]] + insert_keep_existing_model(items.drop_first(), value)
    }
}

pub open spec fn replace_representative_model(
    items: Seq<int>,
    value: int,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else if value < items[0] {
        seq![value] + items
    } else if value == items[0] {
        seq![value] + items.drop_first()
    } else {
        seq![items[0]] + replace_representative_model(items.drop_first(), value)
    }
}

pub open spec fn remove_representative_model(
    items: Seq<int>,
    value: int,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if items[0] == value {
        items.drop_first()
    } else {
        seq![items[0]] + remove_representative_model(items.drop_first(), value)
    }
}

pub open spec fn retain_selected_model(
    items: Seq<int>,
    decisions: Seq<bool>,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 || decisions.len() == 0 {
        Seq::empty()
    } else if decisions[0] {
        seq![items[0]]
            + retain_selected_model(items.drop_first(), decisions.drop_first())
    } else {
        retain_selected_model(items.drop_first(), decisions.drop_first())
    }
}

pub open spec fn range_bounds_model_law(
    start_kind: int,
    end_kind: int,
) -> bool {
    &&& 0 <= start_kind <= 2
    &&& 0 <= end_kind <= 2
}

pub open spec fn range_start_after_end_model(
    start_kind: int,
    start_value: int,
    end_kind: int,
    end_value: int,
) -> bool {
    start_kind != 0 && end_kind != 0 && start_value > end_value
}

pub open spec fn range_equal_excluded_model(
    start_kind: int,
    start_value: int,
    end_kind: int,
    end_value: int,
) -> bool {
    start_kind == 2 && end_kind == 2 && start_value == end_value
}

pub open spec fn range_contains_model(
    item: int,
    start_kind: int,
    start_value: int,
    end_kind: int,
    end_value: int,
) -> bool {
    let starts_after = start_kind == 0
        || item > start_value
        || (start_kind == 1 && item == start_value);
    let ends_before = end_kind == 0
        || item < end_value
        || (end_kind == 1 && item == end_value);
    starts_after && ends_before
}

pub open spec fn range_sequence_model(
    items: Seq<int>,
    start_kind: int,
    start_value: int,
    end_kind: int,
    end_value: int,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if range_contains_model(
        items[0],
        start_kind,
        start_value,
        end_kind,
        end_value,
    ) {
        seq![items[0]] + range_sequence_model(
            items.drop_first(),
            start_kind,
            start_value,
            end_kind,
            end_value,
        )
    } else {
        range_sequence_model(
            items.drop_first(),
            start_kind,
            start_value,
            end_kind,
            end_value,
        )
    }
}

pub open spec fn split_before_model(items: Seq<int>, value: int) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if items[0] < value {
        seq![items[0]] + split_before_model(items.drop_first(), value)
    } else {
        Seq::empty()
    }
}

pub open spec fn split_at_or_after_model(items: Seq<int>, value: int) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if items[0] < value {
        split_at_or_after_model(items.drop_first(), value)
    } else {
        items
    }
}

pub open spec fn dedup_last_sorted_model(items: Seq<int>) -> Seq<int>
    decreases items.len()
{
    if items.len() <= 1 {
        items
    } else if items[0] == items[1] {
        dedup_last_sorted_model(items.drop_first())
    } else {
        seq![items[0]] + dedup_last_sorted_model(items.drop_first())
    }
}

pub open spec fn last_equal_input_model(
    input: Seq<int>,
    value: int,
) -> Option<int>
    decreases input.len()
{
    if input.len() == 0 {
        None
    } else {
        let later = last_equal_input_model(input.drop_first(), value);
        if later.is_some() {
            later
        } else if input[0] == value {
            Some(input[0])
        } else {
            None
        }
    }
}

pub open spec fn stable_tie_order_model(
    input: Seq<int>,
    sorted: Seq<int>,
) -> bool {
    let representatives = dedup_last_sorted_model(sorted);
    forall |index: int|
        0 <= index < representatives.len()
        ==> #[trigger] last_equal_input_model(input, representatives[index])
            == Some(representatives[index])
}

pub open spec fn extend_sequence_model(
    items: Seq<int>,
    input: Seq<int>,
) -> Seq<int>
    decreases input.len()
{
    if input.len() == 0 {
        items
    } else {
        extend_sequence_model(
            insert_keep_existing_model(items, input[0]),
            input.drop_first(),
        )
    }
}

pub open spec fn first_true_model(decisions: Seq<bool>) -> int
    decreases decisions.len()
{
    if decisions.len() == 0 {
        0
    } else if decisions[0] {
        0
    } else {
        1 + first_true_model(decisions.drop_first())
    }
}

pub open spec fn partial_drop_set_model(
    initial: Set<int>,
    yielded: Seq<int>,
) -> Set<int>
    decreases yielded.len()
{
    if yielded.len() == 0 {
        initial
    } else {
        partial_drop_set_model(initial.remove(yielded[0]), yielded.drop_first())
    }
}

pub uninterp spec fn callback_next_state_model(
    state: int,
    item: int,
    result: bool,
) -> int;
pub uninterp spec fn callback_result_model(state: int, item: int) -> bool;

pub open spec fn callback_decisions_model(
    state: int,
    items: Seq<int>,
) -> Seq<bool>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        seq![callback_result_model(state, items[0])]
            + callback_decisions_model(
                callback_next_state_model(
                    state,
                    items[0],
                    callback_result_model(state, items[0]),
                ),
                items.drop_first(),
            )
    }
}

pub open spec fn callback_states_model(
    state: int,
    items: Seq<int>,
) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        let next = callback_next_state_model(
            state,
            items[0],
            callback_result_model(state, items[0]),
        );
        seq![next] + callback_states_model(next, items.drop_first())
    }
}

pub open spec fn callback_trace_law_model(
    state: int,
    items: Seq<int>,
) -> bool {
    &&& callback_decisions_model(state, items).len() == items.len()
    &&& callback_states_model(state, items).len() == items.len()
}

pub open spec fn callback_state_after_model(
    state: int,
    items: Seq<int>,
    count: nat,
) -> int
    decreases count
{
    if count == 0 || items.len() == 0 {
        state
    } else {
        callback_state_after_model(
            callback_next_state_model(
                state,
                items[0],
                callback_result_model(state, items[0]),
            ),
            items.drop_first(),
            (count - 1) as nat,
        )
    }
}

pub struct AdapterStateModel {
    pub variant: int,
    pub first: Seq<int>,
    pub second: Seq<int>,
    pub lookup: Seq<int>,
    pub answer: Option<int>,
    pub peeked_side: int,
    pub peeked: Option<int>,
}

pub open spec fn adapter_state_model(
    variant: int,
    first: Seq<int>,
    second: Seq<int>,
    lookup: Seq<int>,
    answer: Option<int>,
    peeked_side: int,
    peeked: Option<int>,
) -> AdapterStateModel {
    AdapterStateModel {
        variant,
        first,
        second,
        lookup,
        answer,
        peeked_side,
        peeked,
    }
}

pub open spec fn optional_sequence_model(item: Option<int>) -> Seq<int> {
    match item {
        Some(value) => seq![value],
        None => Seq::empty(),
    }
}

pub open spec fn adapter_merge_left_model(
    state: AdapterStateModel,
) -> Seq<int> {
    if state.peeked_side == 1 {
        optional_sequence_model(state.peeked) + state.first
    } else {
        state.first
    }
}

pub open spec fn adapter_merge_right_model(
    state: AdapterStateModel,
) -> Seq<int> {
    if state.peeked_side == 2 {
        optional_sequence_model(state.peeked) + state.second
    } else {
        state.second
    }
}

pub open spec fn difference_state_remaining_model(
    state: AdapterStateModel,
) -> Seq<int> {
    if state.variant == 0 {
        difference_sequence_model(state.first, state.second)
    } else if state.variant == 1 {
        difference_sequence_model(state.first, state.lookup)
    } else {
        state.first
    }
}

pub open spec fn intersection_state_remaining_model(
    state: AdapterStateModel,
) -> Seq<int> {
    if state.variant == 0 {
        intersection_sequence_model(state.first, state.second)
    } else if state.variant == 1 {
        intersection_sequence_model(state.first, state.lookup)
    } else {
        optional_sequence_model(state.answer)
    }
}

pub open spec fn difference_initial_state_model(
    left: Seq<int>,
    right: Seq<int>,
) -> AdapterStateModel {
    if left.len() == 0 || right.len() == 0
        || left[0] > right.last() || left.last() < right[0]
    {
        adapter_state_model(
            2, left, Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0] == right.last() {
        adapter_state_model(
            2,
            left.drop_first(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.last() == right[0] {
        adapter_state_model(
            2,
            left.drop_last(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state_model(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else {
        adapter_state_model(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn intersection_initial_state_model(
    left: Seq<int>,
    right: Seq<int>,
) -> AdapterStateModel {
    if left.len() == 0 || right.len() == 0
        || left[0] > right.last() || left.last() < right[0]
    {
        adapter_state_model(
            2, Seq::empty(), Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0] == right.last() {
        adapter_state_model(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left[0]),
            0,
            None,
        )
    } else if left.last() == right[0] {
        adapter_state_model(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left.last()),
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state_model(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else if right.len() <= left.len() / 16 {
        adapter_state_model(
            1, right, Seq::empty(), left, None, 0, None,
        )
    } else {
        adapter_state_model(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn merge_initial_state_model(
    left: Seq<int>,
    right: Seq<int>,
) -> AdapterStateModel {
    adapter_state_model(
        0, left, right, Seq::empty(), None, 0, None,
    )
}

pub uninterp spec fn difference_next_state_model(
    state: AdapterStateModel,
) -> AdapterStateModel;
pub uninterp spec fn symmetric_difference_next_state_model(
    state: AdapterStateModel,
) -> AdapterStateModel;
pub uninterp spec fn intersection_next_state_model(
    state: AdapterStateModel,
) -> AdapterStateModel;
pub uninterp spec fn union_next_state_model(
    state: AdapterStateModel,
) -> AdapterStateModel;

pub open spec fn adapter_state_law_model(
    owner: int,
    state: AdapterStateModel,
    remaining: Seq<int>,
) -> bool {
    if owner == 1 {
        &&& 0 <= state.variant <= 2
        &&& remaining == difference_state_remaining_model(state)
    } else if owner == 2 {
        &&& state.variant == 0
        &&& 0 <= state.peeked_side <= 2
        &&& remaining == symmetric_difference_sequence_model(
            adapter_merge_left_model(state),
            adapter_merge_right_model(state),
        )
    } else if owner == 3 {
        &&& 0 <= state.variant <= 3
        &&& remaining == intersection_state_remaining_model(state)
    } else {
        &&& state.variant == 0
        &&& 0 <= state.peeked_side <= 2
        &&& remaining == union_sequence_model(
            adapter_merge_left_model(state),
            adapter_merge_right_model(state),
        )
    }
}

pub uninterp spec fn stable_sorted_sequence_model(input: Seq<int>) -> Seq<int>;
pub uninterp spec fn hash_length_step_model(state: int, length: nat) -> int;
pub uninterp spec fn hash_item_step_model(state: int, item: int) -> int;
pub uninterp spec fn debug_builder_start_model(state: int, tag: int) -> int;
pub uninterp spec fn debug_builder_structure_model(state: int, code: int) -> int;
pub uninterp spec fn debug_builder_entry_model(state: int, item: int) -> int;
pub uninterp spec fn debug_builder_finish_state_model(
    state: int,
    non_exhaustive: bool,
) -> int;
pub uninterp spec fn debug_builder_finish_result_model(
    state: int,
    non_exhaustive: bool,
) -> int;

pub open spec fn hash_items_model(state: int, items: Seq<int>) -> int
    decreases items.len()
{
    if items.len() == 0 {
        state
    } else {
        hash_items_model(
            hash_item_step_model(state, items[0]),
            items.drop_first(),
        )
    }
}

pub open spec fn hash_set_model(
    state: int,
    items: Seq<int>,
) -> int {
    hash_items_model(hash_length_step_model(state, items.len()), items)
}

pub open spec fn apply_set_hash_model(
    state: int,
    length: nat,
    items: Seq<int>,
) -> int {
    hash_items_model(hash_length_step_model(state, length), items)
}

pub open spec fn sequence_equal_model(
    left: Seq<int>,
    right: Seq<int>,
) -> bool {
    left == right
}

pub open spec fn sequence_partial_compare_model(
    left: Seq<int>,
    right: Seq<int>,
) -> Option<int> {
    Some(lex_compare_model(left, right))
}

pub open spec fn clone_sequence_model(items: Seq<int>) -> Seq<int>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        seq![items[0]] + clone_sequence_model(items.drop_first())
    }
}

pub open spec fn clone_sequence_preserves_values_model(
    _items: Seq<int>,
) -> bool {
    true
}

pub open spec fn borrowed_set_contains_model(
    items: Set<int>,
    key: int,
) -> bool {
    items.contains(key)
}

pub open spec fn borrowed_key_represents_model(
    items: Set<int>,
    key: int,
    found: int,
) -> bool {
    items.contains(key) && found == key
}

pub open spec fn borrowed_set_difference_model(
    before: Set<int>,
    after: Set<int>,
    key: int,
) -> bool {
    after == before.remove(key)
}

pub open spec fn debug_entries_model(state: int, items: Seq<int>) -> int
    decreases items.len()
{
    if items.len() == 0 {
        state
    } else {
        debug_entries_model(
            debug_builder_entry_model(state, items[0]),
            items.drop_first(),
        )
    }
}

pub open spec fn debug_structure_model(state: int, items: Seq<int>) -> int
    decreases items.len()
{
    if items.len() == 0 {
        state
    } else {
        debug_structure_model(
            debug_builder_structure_model(state, items[0]),
            items.drop_first(),
        )
    }
}

pub open spec fn debug_state_model(
    state: int,
    tag: int,
    items: Seq<int>,
    non_exhaustive: bool,
) -> int {
    debug_builder_finish_state_model(
        debug_entries_model(debug_builder_start_model(state, tag), items),
        non_exhaustive,
    )
}

pub open spec fn debug_shape_state_model(
    state: int,
    tag: int,
    variant: int,
    structure: Seq<int>,
    primary: Seq<int>,
    secondary: Seq<int>,
    tertiary: Seq<int>,
    non_exhaustive: bool,
) -> int {
    let started = debug_builder_start_model(state, tag);
    let variant_state = debug_builder_entry_model(started, variant);
    let structured = debug_structure_model(variant_state, structure);
    let primary_done = debug_entries_model(structured, primary);
    let secondary_done = debug_entries_model(primary_done, secondary);
    let tertiary_done = debug_entries_model(secondary_done, tertiary);
    debug_builder_finish_state_model(tertiary_done, non_exhaustive)
}

pub open spec fn debug_shape_result_model(
    state: int,
    tag: int,
    variant: int,
    structure: Seq<int>,
    primary: Seq<int>,
    secondary: Seq<int>,
    tertiary: Seq<int>,
    non_exhaustive: bool,
) -> int {
    let started = debug_builder_start_model(state, tag);
    let variant_state = debug_builder_entry_model(started, variant);
    let structured = debug_structure_model(variant_state, structure);
    let primary_done = debug_entries_model(structured, primary);
    let secondary_done = debug_entries_model(primary_done, secondary);
    let tertiary_done = debug_entries_model(secondary_done, tertiary);
    debug_builder_finish_result_model(tertiary_done, non_exhaustive)
}

pub open spec fn debug_result_model(
    state: int,
    tag: int,
    items: Seq<int>,
    non_exhaustive: bool,
) -> int {
    debug_builder_finish_result_model(
        debug_entries_model(debug_builder_start_model(state, tag), items),
        non_exhaustive,
    )
}

pub open spec fn debug_shape_law_model(
    owner: int,
    state: AdapterStateModel,
    pre_seq: Seq<int>,
    remaining: Seq<int>,
    pending: Seq<int>,
) -> bool {
    if owner == 4 {
        0 <= state.variant <= 2
    } else if owner == 5 {
        0 <= state.peeked_side <= 2
    } else if owner == 6 {
        0 <= state.variant <= 3
    } else if owner == 7 {
        0 <= state.peeked_side <= 2
    } else if owner == 8 {
        (pending.len() > 0 ==> optional_sequence_model(Some(pending[0])).len() == 1)
            && (pending.len() == 0 ==> optional_sequence_model(None).len() == 0)
    } else if owner == 9 {
        pre_seq.len() == pre_seq.len()
    } else {
        remaining.len() == remaining.len()
    }
}

pub open spec fn lex_compare_model(left: Seq<int>, right: Seq<int>) -> int
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        if right.len() == 0 { 0 } else { -1 }
    } else if right.len() == 0 {
        1
    } else if left[0] < right[0] {
        -1
    } else if right[0] < left[0] {
        1
    } else {
        lex_compare_model(left.drop_first(), right.drop_first())
    }
}

pub struct AdapterStepModel {
    pub state: AdapterStateModel,
}

pub open spec fn difference_next_step_model(
    state: AdapterStateModel,
) -> AdapterStepModel {
    AdapterStepModel { state: difference_next_state_model(state) }
}

pub open spec fn symmetric_difference_next_step_model(
    state: AdapterStateModel,
) -> AdapterStepModel {
    AdapterStepModel {
        state: symmetric_difference_next_state_model(state),
    }
}

pub open spec fn intersection_next_step_model(
    state: AdapterStateModel,
) -> AdapterStepModel {
    AdapterStepModel { state: intersection_next_state_model(state) }
}

pub open spec fn union_next_step_model(
    state: AdapterStateModel,
) -> AdapterStepModel {
    AdapterStepModel { state: union_next_state_model(state) }
}

pub open spec fn intersection_hint_lower_model(
    variant: int,
    _first: nat,
    _second: nat,
) -> nat {
    if variant == 3 { 1 } else { 0 }
}

pub open spec fn intersection_hint_upper_model(
    variant: int,
    first: nat,
    second: nat,
) -> nat {
    if variant == 0 {
        if first <= second { first } else { second }
    } else if variant == 1 {
        first
    } else if variant == 2 {
        0
    } else {
        1
    }
}
"""


def sequence_operation_expression(row: model.Row) -> str:
    family = row.semantic_family
    trait = row.trait
    if family == "difference_adapter_construction" or trait == "Sub":
        return "difference_sequence_model(pre_seq, other_seq)"
    if family == "intersection_adapter_construction" or trait == "BitAnd":
        return "intersection_sequence_model(pre_seq, other_seq)"
    if family == "union_adapter_construction" or trait == "BitOr":
        return "union_sequence_model(pre_seq, other_seq)"
    if family == "symmetric_difference_adapter_construction" or trait == "BitXor":
        return "symmetric_difference_sequence_model(pre_seq, other_seq)"
    raise RuntimeError(f"no sequence operation for {row.target_id}")


def set_operation_expression(row: model.Row) -> str:
    if row.semantic_family == "difference_adapter_construction" or row.trait == "Sub":
        return "pre_set.difference(other_set)"
    if row.semantic_family == "intersection_adapter_construction" or row.trait == "BitAnd":
        return "pre_set.intersect(other_set)"
    if row.semantic_family == "union_adapter_construction" or row.trait == "BitOr":
        return "pre_set.union(other_set)"
    if (
        row.semantic_family == "symmetric_difference_adapter_construction"
        or row.trait == "BitXor"
    ):
        return "pre_set.union(other_set).difference(pre_set.intersect(other_set))"
    raise RuntimeError(f"no set operation for {row.target_id}")


def adapter_owner_code(owner: str) -> int:
    return {
        "Difference": 1,
        "SymmetricDifference": 2,
        "Intersection": 3,
        "Union": 4,
    }[owner]


def adapter_initial_state_expression(row: model.Row) -> str:
    return {
        "difference_adapter_construction": (
            "difference_initial_state_model(pre_seq, other_seq)"
        ),
        "symmetric_difference_adapter_construction": (
            "merge_initial_state_model(pre_seq, other_seq)"
        ),
        "intersection_adapter_construction": (
            "intersection_initial_state_model(pre_seq, other_seq)"
        ),
        "union_adapter_construction": (
            "merge_initial_state_model(pre_seq, other_seq)"
        ),
    }[row.semantic_family]


def adapter_next_state_expression(owner: str) -> str:
    return {
        "Difference": "difference_next_state_model(adapter_state)",
        "SymmetricDifference": (
            "symmetric_difference_next_state_model(adapter_state)"
        ),
        "Intersection": "intersection_next_state_model(adapter_state)",
        "Union": "union_next_state_model(adapter_state)",
    }[owner]


def debug_model_components(row: model.Row) -> tuple[str, str, str, str, str]:
    owner = row.owner["name"]
    if owner == "BTreeSet":
        return ("0", "seq![1]", "pre_seq", "Seq::empty()", "Seq::empty()")
    if owner == "Iter":
        return (
            "0",
            "seq![2, 101, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "IntoIter":
        return (
            "0",
            "seq![3, 102, 201, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "Range":
        return (
            "0",
            "seq![3, 103, 201, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "Difference":
        return (
            "adapter_state.variant",
            (
                "if adapter_state.variant == 0 { "
                "seq![2, 104, 3, 110, 202, 203] "
                "} else if adapter_state.variant == 1 { "
                "seq![2, 104, 3, 111, 202, 203] "
                "} else { seq![2, 104, 2, 112] }"
            ),
            "adapter_state.first",
            (
                "if adapter_state.variant == 0 { adapter_state.second } "
                "else if adapter_state.variant == 1 { adapter_state.lookup } "
                "else { Seq::empty() }"
            ),
            "Seq::empty()",
        )
    if owner == "SymmetricDifference":
        return (
            "adapter_state.peeked_side",
            "seq![2, 105, 2, 109, 204, 205, 208]",
            "adapter_state.first",
            "adapter_state.second",
            "optional_sequence_model(adapter_state.peeked)",
        )
    if owner == "Intersection":
        return (
            "adapter_state.variant",
            (
                "if adapter_state.variant == 0 { "
                "seq![2, 106, 3, 110, 204, 205] "
                "} else if adapter_state.variant == 1 { "
                "seq![2, 106, 3, 111, 206, 207] "
                "} else { seq![2, 106, 2, 113] }"
            ),
            "adapter_state.first",
            (
                "if adapter_state.variant == 0 { adapter_state.second } "
                "else if adapter_state.variant == 1 { adapter_state.lookup } "
                "else { optional_sequence_model(adapter_state.answer) }"
            ),
            "Seq::empty()",
        )
    if owner == "Union":
        return (
            "adapter_state.peeked_side",
            "seq![2, 107, 2, 109, 204, 205, 208]",
            "adapter_state.first",
            "adapter_state.second",
            "optional_sequence_model(adapter_state.peeked)",
        )
    if owner == "ExtractIf":
        return (
            "0",
            "seq![3, 108, 208]",
            (
                "if pending.len() > 0 { seq![pending[0]] } "
                "else { Seq::empty() }"
            ),
            "Seq::empty()",
            "Seq::empty()",
        )
    raise RuntimeError(f"missing debug model for {row.target_id}")


def outcome_profile(row: model.Row) -> list[OutcomeField]:
    family = row.semantic_family
    owner = row.owner["name"]
    name = row.function["name"]
    trait = row.trait
    if family == "ordered_set_hash":
        return [OutcomeField("post_hasher", "int", "hash_set_model(pre_hasher, pre_seq)", 1)]
    if family == "ordered_debug_format":
        tag = model.debug_tag(owner)
        variant, structure, primary, secondary, tertiary = debug_model_components(row)
        non_exhaustive = "true" if owner == "ExtractIf" else "false"
        return [
            OutcomeField(
                "post_formatter",
                "int",
                (
                    f"debug_shape_state_model(pre_formatter, {tag}, "
                    f"{variant}, {structure}, {primary}, {secondary}, "
                    f"{tertiary}, {non_exhaustive})"
                ),
                1,
            ),
            OutcomeField(
                "format_result",
                "int",
                (
                    f"debug_shape_result_model(pre_formatter, {tag}, "
                    f"{variant}, {structure}, {primary}, {secondary}, "
                    f"{tertiary}, {non_exhaustive})"
                ),
                2,
            ),
        ]
    if family == "set_equality":
        return [OutcomeField("returned", "bool", "pre_seq == other_seq", 1)]
    if family == "ordered_set_comparison":
        output_type = "Option<int>" if trait == "PartialOrd" else "int"
        expected = (
            "Some(lex_compare_model(pre_seq, other_seq))"
            if trait == "PartialOrd"
            else "lex_compare_model(pre_seq, other_seq)"
        )
        return [OutcomeField("comparison", output_type, expected, 1)]
    if family == "set_relation_observer":
        expected = {
            "is_disjoint": "pre_set.intersect(other_set).is_empty()",
            "is_subset": "pre_set.subset_of(other_set)",
            "is_superset": "other_set.subset_of(pre_set)",
        }[name]
        return [OutcomeField("returned", "bool", expected, 1)]
    if family == "set_clone_transition":
        if name == "clone":
            return [OutcomeField("result_set", "Set<int>", "pre_set", 1)]
        return [
            OutcomeField("post_seq", "Seq<int>", "other_seq", 1),
            OutcomeField("post_set", "Set<int>", "other_set", 2),
        ]
    if family == "exact_vstd_transition":
        if name in {"new", "default"} or trait == "Default":
            return [OutcomeField("result_set", "Set<int>", "Set::empty()", 1)]
        if name == "clear":
            return [OutcomeField("post_set", "Set<int>", "Set::empty()", 1)]
        if name == "contains":
            return [OutcomeField("returned", "bool", "pre_set.contains(item)", 1)]
        if name == "get":
            return [
                OutcomeField(
                    "returned",
                    "Option<int>",
                    "representative_model(pre_seq, item)",
                    1,
                )
            ]
        if name == "insert":
            return [
                OutcomeField("post_set", "Set<int>", "pre_set.insert(item)", 1),
                OutcomeField("returned", "bool", "!pre_set.contains(item)", 2),
            ]
        if name == "remove":
            return [
                OutcomeField("post_set", "Set<int>", "pre_set.remove(item)", 1),
                OutcomeField("returned", "bool", "pre_set.contains(item)", 2),
            ]
        if name == "iter":
            return [
                OutcomeField("result_remaining", "Seq<int>", "pre_seq", 1),
                OutcomeField("decrease_defined", "bool", "true", 2),
                OutcomeField("initial_relation", "bool", "true", 3),
            ]
        if name == "len":
            return [OutcomeField("scalar", "nat", "pre_set.len()", 1)]
        if name == "is_empty":
            return [OutcomeField("returned", "bool", "pre_set.is_empty()", 1)]
    if family == "ordered_range_construction":
        return [
            OutcomeField(
                "result_remaining",
                "Seq<int>",
                (
                    "range_sequence_model("
                    "pre_seq, range_start_kind, range_start_value, "
                    "range_end_kind, range_end_value)"
                ),
                2,
            )
        ]
    if family in {
        "difference_adapter_construction",
        "intersection_adapter_construction",
        "union_adapter_construction",
        "symmetric_difference_adapter_construction",
    }:
        return [
            OutcomeField(
                "result_remaining",
                "Seq<int>",
                sequence_operation_expression(row),
                1,
            ),
            OutcomeField(
                "result_adapter_state",
                "AdapterStateModel",
                adapter_initial_state_expression(row),
                5,
            ),
        ]
    if family == "ordered_iterator_construction":
        return [OutcomeField("result_remaining", "Seq<int>", "pre_seq", 2)]
    if family == "ordered_endpoint_observer":
        selected = "pre_seq[0]" if name == "first" else "pre_seq.last()"
        return [
            OutcomeField(
                "returned",
                "Option<int>",
                f"if pre_seq.len() > 0 {{ Some({selected}) }} else {{ None }}",
                2,
            )
        ]
    if family == "ordered_endpoint_removal":
        selected = "pre_seq[0]" if name == "pop_first" else "pre_seq.last()"
        remainder = "pre_seq.drop_first()" if name == "pop_first" else "pre_seq.drop_last()"
        return [
            OutcomeField(
                "returned",
                "Option<int>",
                f"if pre_seq.len() > 0 {{ Some({selected}) }} else {{ None }}",
                2,
            ),
            OutcomeField(
                "post_seq",
                "Seq<int>",
                f"if pre_seq.len() > 0 {{ {remainder} }} else {{ pre_seq }}",
                3,
            ),
            OutcomeField(
                "post_set",
                "Set<int>",
                f"if pre_seq.len() > 0 {{ pre_set.remove({selected}) }} else {{ pre_set }}",
                4,
            ),
        ]
    if family == "representative_replacement":
        return [
            OutcomeField("returned", "Option<int>", "representative_model(pre_seq, item)", 1),
            OutcomeField(
                "post_seq",
                "Seq<int>",
                "replace_representative_model(pre_seq, item)",
                2,
            ),
            OutcomeField("post_set", "Set<int>", "pre_set.insert(item)", 3),
        ]
    if family == "borrowed_representative_removal":
        return [
            OutcomeField("returned", "Option<int>", "representative_model(pre_seq, item)", 1),
            OutcomeField(
                "post_seq",
                "Seq<int>",
                "remove_representative_model(pre_seq, item)",
                2,
            ),
            OutcomeField("post_set", "Set<int>", "pre_set.remove(item)", 3),
        ]
    if family == "ordered_callback_retain":
        decisions = "callback_decisions_model(predicate_seed, pre_seq)"
        selected = f"retain_selected_model(pre_seq, {decisions})"
        return [
            OutcomeField("post_seq", "Seq<int>", selected, 3),
            OutcomeField("post_set", "Set<int>", f"{selected}.to_set()", 4),
        ]
    if family == "set_append_transition":
        return [
            OutcomeField("other_post_seq", "Seq<int>", "Seq::empty()", 1),
            OutcomeField("other_post_set", "Set<int>", "Set::empty()", 2),
            OutcomeField(
                "post_seq",
                "Seq<int>",
                "union_sequence_model(pre_seq, other_seq)",
                3,
            ),
            OutcomeField("post_set", "Set<int>", "pre_set.union(other_set)", 4),
        ]
    if family == "ordered_set_partition":
        return [
            OutcomeField(
                "post_seq",
                "Seq<int>",
                "split_before_model(pre_seq, item)",
                1,
            ),
            OutcomeField(
                "result_seq",
                "Seq<int>",
                "split_at_or_after_model(pre_seq, item)",
                2,
            ),
            OutcomeField("post_set", "Set<int>", "post_seq.to_set()", 3),
            OutcomeField("result_set", "Set<int>", "result_seq.to_set()", 3),
        ]
    if family == "extract_if_construction":
        bounds = (
            "range_start_kind, range_start_value, "
            "range_end_kind, range_end_value"
        )
        decisions = (
            "callback_decisions_model(predicate_seed, result_pending)"
        )
        selected = f"retain_selected_model(result_pending, {decisions})"
        return [
            OutcomeField("post_set", "Set<int>", "pre_set", 2),
            OutcomeField("iterator_set", "Set<int>", "pre_set", 3),
            OutcomeField(
                "result_pending",
                "Seq<int>",
                f"range_sequence_model(pre_seq, {bounds})",
                4,
            ),
            OutcomeField("result_callback_count", "nat", "0", 6),
            OutcomeField(
                "result_predicate_state", "int", "predicate_seed", 7
            ),
            OutcomeField("result_remaining", "Seq<int>", selected, 8),
            OutcomeField("result_initial_set", "Set<int>", "pre_set", 10),
            OutcomeField("result_yielded", "Seq<int>", "Seq::empty()", 11),
            OutcomeField(
                "drop_set",
                "Set<int>",
                "partial_drop_set_model(result_initial_set, result_yielded)",
                12,
            ),
            OutcomeField("panic_set", "Set<int>", "iterator_set", 13),
        ]
    if family == "sorted_deduplicating_conversion":
        sorted_input = "stable_sorted_sequence_model(input_seq)"
        return [
            OutcomeField(
                "result_seq",
                "Seq<int>",
                f"dedup_last_sorted_model({sorted_input})",
                5,
            ),
            OutcomeField("result_set", "Set<int>", "input_seq.to_set()", 6),
        ]
    if family == "ordered_extend_transition":
        selected = "extend_sequence_model(pre_seq, input_seq)"
        return [
            OutcomeField("post_seq", "Seq<int>", selected, 1),
            OutcomeField("post_set", "Set<int>", f"{selected}.to_set()", 2),
        ]
    if family == "owned_set_operation":
        selected = sequence_operation_expression(row)
        return [
            OutcomeField("result_seq", "Seq<int>", selected, 1),
            OutcomeField("result_set", "Set<int>", set_operation_expression(row), 2),
        ]
    if family in {"ordered_iterator_forward_step", "ordered_iterator_backward_step"}:
        if owner == "ExtractIf":
            decisions = "callback_decisions_model(predicate_state, pending)"
            selected_index = f"first_true_model({decisions})"
            found = f"{selected_index} < pending.len()"
            selected = f"pending[{selected_index}]"
            return [
                OutcomeField(
                    "returned",
                    "Option<int>",
                    f"if {found} {{ Some({selected}) }} else {{ None }}",
                    2,
                ),
                OutcomeField(
                    "post_pending",
                    "Seq<int>",
                    f"if {found} {{ pending.subrange({selected_index} + 1, pending.len() as int) }} else {{ Seq::empty() }}",
                    3,
                ),
                OutcomeField(
                    "post_set",
                    "Set<int>",
                    f"if {found} {{ pre_set.remove({selected}) }} else {{ pre_set }}",
                    4,
                ),
                OutcomeField(
                    "post_callback_count",
                    "nat",
                    f"pre_callback_count + if {found} {{ ({selected_index} + 1) as nat }} else {{ pending.len() as nat }}",
                    5,
                ),
                OutcomeField(
                    "post_initial_set",
                    "Set<int>",
                    "extract_initial_set",
                    7,
                ),
                OutcomeField(
                    "post_predicate_state",
                    "int",
                    (
                        "callback_state_after_model(predicate_state, pending, "
                        f"if {found} {{ ({selected_index} + 1) as nat }} "
                        "else { pending.len() as nat })"
                    ),
                    6,
                ),
                OutcomeField(
                    "post_yielded",
                    "Seq<int>",
                    f"if {found} {{ yielded + seq![{selected}] }} else {{ yielded }}",
                    8,
                ),
                OutcomeField(
                    "post_remaining",
                    "Seq<int>",
                    "if returned.is_some() { remaining.drop_first() } else { remaining }",
                    9,
                ),
                OutcomeField(
                    "drop_set",
                    "Set<int>",
                    "partial_drop_set_model(post_initial_set, post_yielded)",
                    10,
                ),
                OutcomeField("panic_set", "Set<int>", "post_set", 11),
            ]
        front = family == "ordered_iterator_forward_step"
        selected = "remaining[0]" if front else "remaining.last()"
        remainder = "remaining.drop_first()" if front else "remaining.drop_last()"
        fields = [
            OutcomeField(
                "returned",
                "Option<int>",
                f"if remaining.len() > 0 {{ Some({selected}) }} else {{ None }}",
                1,
            ),
            OutcomeField(
                "post_remaining",
                "Seq<int>",
                f"if remaining.len() > 0 {{ {remainder} }} else {{ remaining }}",
                2,
            ),
        ]
        if owner in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
        }:
            fields.append(
                OutcomeField(
                    "post_adapter_state",
                    "AdapterStateModel",
                    adapter_next_state_expression(owner),
                    3,
                )
            )
        return fields
    if family == "ordered_iterator_terminal_selection":
        selected = "remaining.last()" if name in {"last", "max"} else "remaining[0]"
        return [
            OutcomeField(
                "returned",
                "Option<int>",
                f"if remaining.len() > 0 {{ Some({selected}) }} else {{ None }}",
                1,
            )
        ]
    if family == "adapter_specific_size_hint":
        if owner == "Difference":
            first = "adapter_state.first.len()"
            second = (
                "if adapter_state.variant == 0 { adapter_state.second.len() } "
                "else if adapter_state.variant == 1 { adapter_state.lookup.len() } "
                "else { 0 }"
            )
            lower = f"if {first} >= {second} {{ {first} - {second} }} else {{ 0 }}"
            upper = f"Some({first})"
        elif owner == "Union":
            first = "adapter_merge_left_model(adapter_state).len()"
            second = "adapter_merge_right_model(adapter_state).len()"
            lower = f"if {first} >= {second} {{ {first} }} else {{ {second} }}"
            upper = f"Some({first} + {second})"
        elif owner == "SymmetricDifference":
            first = "adapter_merge_left_model(adapter_state).len()"
            second = "adapter_merge_right_model(adapter_state).len()"
            lower, upper = "0", f"Some({first} + {second})"
        elif owner == "Intersection":
            first = "adapter_state.first.len()"
            second = (
                "if adapter_state.variant == 0 { adapter_state.second.len() } "
                "else if adapter_state.variant == 1 { adapter_state.lookup.len() } "
                "else { 0 }"
            )
            lower = "if adapter_state.variant == 3 { 1nat } else { 0nat }"
            upper = (
                "Some(intersection_hint_upper_model("
                f"adapter_state.variant, {first}, {second}))"
            )
        elif owner == "ExtractIf":
            lower, upper = "0", "Some(pre_set.len())"
        else:
            lower = "remaining.len() as nat"
            upper = "Some(lower)"
        lower_clause = (
            3 if owner == "Difference" else
            2 if owner == "Intersection" else
            1 if owner in {"Union", "SymmetricDifference"} else
            1
        )
        upper_clause = (
            4 if owner == "Difference" else
            3 if owner == "Intersection" else
            2 if owner in {"Union", "SymmetricDifference"} else
            2
        )
        return [
            OutcomeField("lower", "nat", lower, lower_clause),
            OutcomeField("upper", "Option<nat>", upper, upper_clause),
        ]
    if family == "ordered_iterator_exact_len":
        return [OutcomeField("scalar", "nat", "remaining.len() as nat", 1)]
    if family == "ordered_iterator_clone":
        fields = [OutcomeField("result_remaining", "Seq<int>", "remaining", 1)]
        if owner in {
            "Difference",
            "SymmetricDifference",
            "Intersection",
            "Union",
        }:
            fields.append(
                OutcomeField(
                    "result_adapter_state",
                    "AdapterStateModel",
                    "adapter_state",
                    2,
                )
            )
        return fields
    if family == "ordered_iterator_empty_default":
        return [OutcomeField("result_remaining", "Seq<int>", "Seq::empty()", 1)]
    raise RuntimeError(f"missing completeness outcome profile for {row.target_id}")


# --- Mechanical completeness translation -------------------------------------
# Every completeness predicate is obtained from its accepted requirement/clause
# by substituting public observations with explicitly declared model
# observations. Outcome profiles only declare which observations are compared;
# they never supply a replacement equation for an accepted clause. A residual
# untranslated source token is a fail-closed error.

_COMPLETENESS_ADAPTER_PREFIXES = (
    "symmetric_difference", "difference", "intersection", "union",
)
_COMPLETENESS_OWNER_OF_PREFIX = {
    "difference": "Difference",
    "symmetric_difference": "SymmetricDifference",
    "intersection": "Intersection",
    "union": "Union",
}
_COMPLETENESS_OBS_PREFIXES = (
    "symmetric_difference", "difference", "intersection", "union",
    "range", "into_iter", "iter",
)
_COMPLETENESS_RESIDUAL_TOKENS = (
    "apply_debug_shape(", "apply_set_hash(", "seq_lex_cmp(",
    "seq_lex_partial_cmp(", "seq_eq_spec(", "clone_sequence(",
    "_debug_shape(",
    "obeys_cmp", "btree_set_sequence", "&range", "&f", "IteratorSpec",
    "sets_borrowed", "set_contains_borrowed", "->", "::<", "*old(",
    "*final(", "@", "extract_if_",
)


def _completeness_result_observation(row: model.Row) -> str | None:
    family = row.semantic_family
    if family == "ordered_set_comparison":
        return "comparison"
    if family == "ordered_debug_format":
        return "format_result"
    if family in {"adapter_specific_size_hint"}:
        return None
    if family in {
        "ordered_iterator_exact_len",
    } or (
        family == "exact_vstd_transition"
        and row.function["name"] == "len"
    ):
        return "scalar"
    if (
        family == "exact_vstd_transition"
        and row.function["name"] == "iter"
    ):
        return "result_remaining"
    if family in {
        "set_equality",
        "set_relation_observer",
        "ordered_endpoint_observer",
        "ordered_endpoint_removal",
        "representative_replacement",
        "borrowed_representative_removal",
        "ordered_iterator_forward_step",
        "ordered_iterator_backward_step",
        "ordered_iterator_terminal_selection",
    } or (
        family == "exact_vstd_transition"
        and row.function["name"] in {
            "contains",
            "get",
            "insert",
            "remove",
            "is_empty",
        }
    ):
        return "returned"
    return None


def _completeness_debug_shape_expression(row: model.Row) -> str:
    owner = row.owner["name"]
    tag = model.debug_tag(owner)
    variant, structure, primary, secondary, tertiary = (
        debug_model_components(row)
    )
    non_exhaustive = "true" if owner == "ExtractIf" else "false"
    return (
        f"{tag}, {variant}, {structure}, {primary}, {secondary}, "
        f"{tertiary}, {non_exhaustive}"
    )


def _completeness_observation_subs(
    row: model.Row,
) -> list[tuple[str, str]]:
    owner = row.owner["name"]
    subs: list[tuple[str, str]] = []

    if row.semantic_family == "ordered_set_hash":
        subs.extend(
            (
                ("*final(state)", "post_hasher"),
                ("*old(state)", "pre_hasher"),
            )
        )

    if row.semantic_family == "ordered_debug_format":
        shape = _completeness_debug_shape_expression(row)
        prefix = {
            "BTreeSet": "btree_set",
            "Iter": "iter",
            "IntoIter": "into_iter",
            "Range": "range",
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
            "ExtractIf": "extract_if",
        }[owner]
        subs.extend(
            (
                (
                    f"*final(f) == apply_debug_shape("
                    f"*old(f), {prefix}_debug_shape(*this)).0",
                    f"post_formatter == debug_shape_state_model("
                    f"pre_formatter, {shape})",
                ),
                (
                    f"result == apply_debug_shape("
                    f"*old(f), {prefix}_debug_shape(*this)).1",
                    f"format_result == debug_shape_result_model("
                    f"pre_formatter, {shape})",
                ),
                (
                    f"{prefix}_debug_shape_law(*this)",
                    _completeness_debug_law_body(row),
                ),
            )
        )

    subs.extend(
        (
            ("btree_set_sequence(result)", "result_seq"),
            ("result@", "result_set"),
            ("btree_set_sequence(*source)", "other_seq"),
            ("source@", "other_set"),
            ("btree_set_sequence(*old(other))", "other_seq"),
            ("btree_set_sequence(*final(other))", "other_post_seq"),
            ("final(other)@", "other_post_set"),
            ("old(other)@", "other_set"),
            ("rhs@", "other_set"),
        )
    )

    if row.semantic_family == "extract_if_construction":
        subs.extend(
            (
                ("extract_if_set(result)", "iterator_set"),
                ("extract_if_pending(result)", "result_pending"),
                (
                    "extract_if_callback_count(result)",
                    "result_callback_count",
                ),
                (
                    "extract_if_predicate_state(result)",
                    "result_predicate_state",
                ),
                ("extract_if_remaining(result)", "result_remaining"),
                ("extract_if_initial_set(result)", "result_initial_set"),
                ("extract_if_yielded(result)", "result_yielded"),
                (
                    "extract_if_drop_law(result)",
                    "drop_set == partial_drop_set_model("
                    "result_initial_set, result_yielded)",
                ),
                (
                    "extract_if_panic_law(result)",
                    "panic_set == iterator_set",
                ),
            )
        )

    if owner == "ExtractIf" and row.function["name"] == "next":
        subs.extend(
            (
                ("extract_if_pending(*final(this))", "post_pending"),
                ("extract_if_pending(*old(this))", "pending"),
                ("extract_if_set(*final(this))", "post_set"),
                ("extract_if_set(*old(this))", "pre_set"),
                (
                    "extract_if_callback_count(*final(this))",
                    "post_callback_count",
                ),
                (
                    "extract_if_callback_count(*old(this))",
                    "pre_callback_count",
                ),
                (
                    "extract_if_predicate_state(*final(this))",
                    "post_predicate_state",
                ),
                (
                    "extract_if_predicate_state(*old(this))",
                    "predicate_state",
                ),
                (
                    "extract_if_initial_set(*final(this))",
                    "post_initial_set",
                ),
                (
                    "extract_if_initial_set(*old(this))",
                    "extract_initial_set",
                ),
                ("extract_if_yielded(*final(this))", "post_yielded"),
                ("extract_if_yielded(*old(this))", "yielded"),
                ("extract_if_remaining(*final(this))", "post_remaining"),
                ("extract_if_remaining(*old(this))", "remaining"),
                (
                    "extract_if_drop_law(*final(this))",
                    "drop_set == partial_drop_set_model("
                    "post_initial_set, post_yielded)",
                ),
                (
                    "extract_if_panic_law(*final(this))",
                    "panic_set == post_set",
                ),
            )
        )

    if (
        row.semantic_family == "exact_vstd_transition"
        and row.function["name"] == "iter"
    ):
        subs.extend(
            (
                ("spec_btree_keys_iter(this)", "pre_seq"),
                ("IteratorSpec::decrease(&result) is Some", "decrease_defined"),
                (
                    "IteratorSpec::initial_value_relation(&result, &result)",
                    "initial_relation",
                ),
            )
        )

    if row.semantic_family == "exact_vstd_transition":
        subs.append(("spec_btree_set_len(this)", "pre_set.len()"))

    for prefix in _COMPLETENESS_OBS_PREFIXES:
        subs.extend(
            (
                (f"{prefix}_remaining(this)", "remaining"),
                (f"{prefix}_remaining(&this)", "remaining"),
            )
        )

    if row.semantic_family == "adapter_specific_size_hint":
        if owner in {"Difference", "Intersection"}:
            second = (
                "if adapter_state.variant == 0 { "
                "adapter_state.second.len() } "
                "else if adapter_state.variant == 1 { "
                "adapter_state.lookup.len() } else { 0 }"
            )
            lengths = f"(adapter_state.first.len(), {second})"
        elif owner in {"SymmetricDifference", "Union"}:
            lengths = (
                "(adapter_merge_left_model(adapter_state).len(), "
                "adapter_merge_right_model(adapter_state).len())"
            )
        else:
            lengths = ""
        if lengths:
            prefix = {
                "Difference": "difference",
                "SymmetricDifference": "symmetric_difference",
                "Intersection": "intersection",
                "Union": "union",
            }[owner]
            subs.append((f"{prefix}_hint_lengths(this)", lengths))

    return subs


def _completeness_generic_subs(row: model.Row) -> list[tuple[str, str]]:
    subs: list[tuple[str, str]] = []
    subs += [
        ("(obeys_cmp::<T>() && K::obeys_cmp_spec())", "order_laws"),
        ("(obeys_cmp::<T>() && Q::obeys_cmp_spec())", "order_laws"),
        ("(obeys_cmp::<T>())", "order_laws"),
        ("(T::obeys_partial_cmp_spec())", "order_laws"),
    ]
    subs += [
        ("Some(upper) =>", "Some(value) =>"),
        ("upper as nat", "value"),
    ]
    for prefix in _COMPLETENESS_ADAPTER_PREFIXES:
        code = adapter_owner_code(_COMPLETENESS_OWNER_OF_PREFIX[prefix])
        subs += [
            (f"{prefix}_source_state_law(result)",
             f"adapter_state_law_model({code}, result_adapter_state, "
             "result_remaining)"),
            (f"{prefix}_source_state_law(*final(this))",
             f"adapter_state_law_model({code}, post_adapter_state, "
             "post_remaining)"),
            (f"{prefix}_source_state_law(*old(this))",
             f"adapter_state_law_model({code}, adapter_state, remaining)"),
            (f"{prefix}_source_state_law(*this)",
             f"adapter_state_law_model({code}, adapter_state, remaining)"),
        ]
    for prefix in _COMPLETENESS_ADAPTER_PREFIXES:
        subs += [(f"{prefix}_hint_variant(this)", "adapter_state.variant")]
    for prefix in _COMPLETENESS_OBS_PREFIXES:
        subs += [
            (f"{prefix}_remaining(result).unref()", "result_remaining"),
            (f"{prefix}_remaining(result)", "result_remaining"),
            (f"{prefix}_remaining(*final(this))", "post_remaining"),
            (f"{prefix}_remaining(*old(this))", "remaining"),
            (f"{prefix}_remaining(*this)", "remaining"),
            (f"{prefix}_source_state(result)", "result_adapter_state"),
            (f"{prefix}_source_state(*final(this))", "post_adapter_state"),
            (f"{prefix}_source_state(*old(this))", "adapter_state"),
            (f"{prefix}_source_state(*this)", "adapter_state"),
        ]
    subs += [
        ("extract_if_decisions(result)",
         "callback_decisions_model(predicate_seed, result_pending)"),
        ("extract_if_decisions(*old(this))",
         "callback_decisions_model(predicate_state, pending)"),
        ("extract_if_pending(result)", "result_pending"),
        ("extract_if_pending(*old(this))", "pending"),
        ("extract_if_pending(*this)", "pending"),
        ("extract_if_remaining(*this)", "remaining"),
        ("extract_if_predicate_state(*this)", "predicate_state"),
        ("extract_if_length_bound(this)", "pre_set.len()"),
    ]
    subs += [
        ("into_iterator_sequence::<T, I>(&iter)", "input_seq"),
        ("arr@", "input_seq"),
    ]
    subs += [
        ("range_bounds_law(&range)",
         "range_bounds_model_law(range_start_kind, range_end_kind)"),
        ("range_start_after_end(&range)",
         "range_start_after_end_model(range_start_kind, range_start_value, "
         "range_end_kind, range_end_value)"),
        ("range_equal_excluded(&range)",
         "range_equal_excluded_model(range_start_kind, range_start_value, "
         "range_end_kind, range_end_value)"),
    ]
    subs += [
        ("btree_set_sequence(*old(this))", "pre_seq"),
        ("btree_set_sequence(*final(this))", "post_seq"),
        ("btree_set_sequence(*this)", "pre_seq"),
        ("btree_set_sequence(this)", "pre_seq"),
        ("btree_set_sequence(*other)", "other_seq"),
        ("btree_set_sequence(*rhs)", "other_seq"),
        ("final(this)@", "post_set"),
        ("old(this)@", "pre_set"),
        ("this@", "pre_set"),
        ("other@", "other_set"),
    ]
    subs += [
        ("range_order_law(pre_seq, &range)",
         "range_bounds_model_law(range_start_kind, range_end_kind)"),
    ]
    subs += [
        ("result.0 as nat", "lower"),
        ("result.0", "lower"),
        ("result.1", "upper"),
    ]
    subs += [
        ("increasing_seq(", "strictly_increasing_model("),
        ("nondecreasing_sequence(", "nondecreasing_model("),
        ("stable_tie_order(", "stable_tie_order_model("),
        ("stable_sorted_sequence(", "stable_sorted_sequence_model("),
        ("difference_sequence(pre_seq, other_seq)",
         "difference_sequence_model(pre_seq, other_seq)"),
        ("symmetric_difference_sequence(pre_seq, other_seq)",
         "symmetric_difference_sequence_model(pre_seq, other_seq)"),
        ("intersection_source_sequence(pre_seq, other_seq)",
         "intersection_sequence_model(pre_seq, other_seq)"),
        ("union_sequence(pre_seq, other_seq)",
         "union_sequence_model(pre_seq, other_seq)"),
    ]
    subs += [
        ("obeys_cmp::<T>()", "order_laws"),
        ("key_obeys_cmp_spec::<T>()", "order_laws"),
        ("K::obeys_cmp_spec()", "order_laws"),
        ("Q::obeys_cmp_spec()", "order_laws"),
        ("T::obeys_cmp_spec()", "order_laws"),
        ("T::obeys_partial_cmp_spec()", "order_laws"),
    ]
    return subs


def _completeness_retain_subs(text: str) -> str:
    text = re.sub(r"retain_decisions\(&f, ([^)]*)\)",
                  r"callback_decisions_model(predicate_seed, \1)", text)
    text = re.sub(r"retain_effect_trace\(&f, ([^)]*)\)",
                  r"callback_states_model(predicate_seed, \1)", text)
    text = re.sub(r"retain_callback_trace_law\(f, ([^)]*)\)",
                  r"callback_trace_law_model(predicate_seed, \1)", text)
    text = text.replace("retain_callback_trace_law(",
                        "callback_trace_law_model(")
    return text


def _completeness_debug_law_body(row: model.Row) -> str:
    owner = row.owner["name"]
    tag = model.debug_tag(owner)
    if owner in {"Difference", "SymmetricDifference", "Intersection", "Union"}:
        state = "adapter_state"
    else:
        state = ("adapter_state_model(0, Seq::empty(), Seq::empty(), "
                 "Seq::empty(), None, 0, None)")
    return (f"debug_shape_law_model({tag}, {state}, pre_seq, remaining, "
            "pending)")


def _completeness_translate(row: model.Row, line: str) -> str:
    text = line
    if "match result { Some(item) =>" in text:
        text = text.replace(
            "match result { Some(item) =>",
            "match result { Some(found) =>",
        ).replace("&item", "found").replace("*item", "found")
    text = _completeness_retain_subs(text)
    text = text.replace("borrowed_key_order_law(",
                        "borrowed_key_order_law_model(")
    for old, new in _completeness_observation_subs(row):
        text = text.replace(old, new)
    text = re.sub(r"\bvalue\b", "item", text)          # source input parameter
    for old, new in _completeness_generic_subs(row):
        text = text.replace(old, new)
    text = re.sub(
        r"into_iterator_sequence::<[^>]+>\(&iter\)(?:\.unref\(\))?",
        "input_seq",
        text,
    )
    model_symbols = (
        ("apply_set_hash", "apply_set_hash_model"),
        ("seq_eq_spec", "sequence_equal_model"),
        ("seq_lex_partial_cmp", "sequence_partial_compare_model"),
        ("seq_lex_cmp", "lex_compare_model"),
        ("clone_sequence_preserves_values", "clone_sequence_preserves_values_model"),
        ("clone_sequence", "clone_sequence_model"),
        ("dedup_last_sorted", "dedup_last_sorted_model"),
        ("extend_sequence", "extend_sequence_model"),
        ("retain_selected", "retain_selected_model"),
        ("first_true", "first_true_model"),
        ("retain_callback_state_after", "callback_state_after_model"),
        ("sets_borrowed_key_to_key", "borrowed_key_represents_model"),
        ("sets_differ_by_borrowed_key", "borrowed_set_difference_model"),
        ("set_contains_borrowed_key", "borrowed_set_contains_model"),
        ("replace_representative", "replace_representative_model"),
        ("cmp_equal_representative", "representative_model"),
        ("borrowed_representative", "representative_model"),
        (
            "remove_borrowed_representative",
            "remove_representative_model",
        ),
        ("difference_initial_state", "difference_initial_state_model"),
        ("intersection_initial_state", "intersection_initial_state_model"),
        ("merge_initial_state", "merge_initial_state_model"),
        ("intersection_hint_lower", "intersection_hint_lower_model"),
        ("intersection_hint_upper", "intersection_hint_upper_model"),
        ("difference_next_step", "difference_next_step_model"),
        (
            "symmetric_difference_next_step",
            "symmetric_difference_next_step_model",
        ),
        ("intersection_next_step", "intersection_next_step_model"),
        ("union_next_step", "union_next_step_model"),
    )
    for old, new in model_symbols:
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    bounds = (
        "range_start_kind, range_start_value, "
        "range_end_kind, range_end_value"
    )
    text = text.replace("&range", bounds)
    text = text.replace("range_sequence(", "range_sequence_model(")
    text = text.replace("split_before(", "split_before_model(")
    text = text.replace("split_at_or_after(", "split_at_or_after_model(")
    text = text.replace("old(other)@", "other_set")
    text = text.replace("rhs@", "other_set")
    text = text.replace("obeys_cmp::<&'a T>()", "order_laws")
    if row.semantic_family == "extract_if_construction":
        text = re.sub(r"\bpred\b", "predicate_seed", text)
    result_observation = _completeness_result_observation(row)
    if result_observation is not None:
        text = re.sub(r"\bresult\b", result_observation, text)
    return text


def _completeness_has_residual(body: str) -> bool:
    if re.search(r"\bresult\b", body):
        return True
    return any(token in body for token in _COMPLETENESS_RESIDUAL_TOKENS)


def completeness_clause_body(
    row: model.Row,
    line: str,
) -> str:
    body = _completeness_translate(row, line)
    if _completeness_has_residual(body):
        raise RuntimeError(
            f"{row.target_id}: completeness clause is not a mechanical "
            f"translation of the accepted source: {line!r} -> {body!r}"
        )
    return body


def _completeness_needs_order_laws(row: model.Row) -> bool:
    if model.comparison_law_binding(row) is not None:
        return True
    return (
        row.semantic_family == "exact_vstd_transition"
        and row.function["name"] in {"contains", "get", "insert", "remove"}
    )


def clause_bodies(row: model.Row, fields: list[OutcomeField]) -> list[str]:
    lines = contract_lines(row)
    bodies = [
        completeness_clause_body(row, line)
        for line in lines
    ]
    if _completeness_needs_order_laws(row):
        bodies = [
            body if body.startswith("order_laws ==>")
            else f"order_laws ==> ({body})"
            for body in bodies
        ]
    return bodies


def referenced_names(expression: str, candidates: dict[str, str]) -> list[str]:
    return [
        name
        for name in candidates
        if re.search(rf"\b{re.escape(name)}\b", expression)
    ]


def completeness_requirement_body(row: model.Row, line: str) -> str:
    body = _completeness_translate(row, line)
    if _completeness_has_residual(body):
        raise RuntimeError(
            f"{row.target_id}: completeness requirement is not a mechanical "
            f"translation of the accepted source: {line!r} -> {body!r}"
        )
    return body


def completeness_requirement_bodies(row: model.Row) -> list[str]:
    requirements = contract_requirements(row)
    bodies = [
        completeness_requirement_body(row, line) for line in requirements
    ]
    if len(bodies) != len(requirements):
        raise RuntimeError(
            f"{row.target_id}: completeness requirement mapping "
            f"{len(bodies)} != {len(requirements)}"
        )
    return bodies


def completeness_domain_requirements(row: model.Row) -> list[str]:
    name = row.function["name"]
    requirements: list[str] = []
    if model.comparison_law_binding(row) is not None:
        requirements.append("order_laws")
    if row.semantic_family == "exact_vstd_transition" and name in {
        "contains",
        "get",
        "insert",
        "remove",
        "iter",
    }:
        if "order_laws" not in requirements:
            requirements.append("order_laws")
    if row.semantic_family == "set_clone_transition" and name == "clone_from":
        requirements.append("other_seq.to_set() == other_set")
    if row.semantic_family == "owned_set_operation":
        requirements.append(
            f"{sequence_operation_expression(row)}.to_set() == "
            f"{set_operation_expression(row)}"
        )
    return requirements


def completeness_observable_requirements(
    fields: list[OutcomeField],
    side: str,
) -> list[str]:
    names = {field.name for field in fields}
    requirements: list[str] = []
    for sequence, extensional_set in (
        ("post_seq", "post_set"),
        ("other_post_seq", "other_post_set"),
        ("result_seq", "result_set"),
    ):
        if sequence in names and extensional_set in names:
            requirements.append(
                f"{side}_{extensional_set} == "
                f"{side}_{sequence}.to_set()"
            )
    return requirements


def completeness_source(row: model.Row) -> str:
    lines = contract_lines(row)
    requirement_lines = contract_requirements(row)
    requirement_bodies = completeness_requirement_bodies(row)
    fields = outcome_profile(row)
    bodies = clause_bodies(row, fields)
    field_types = {field.name: field.rust_type for field in fields}
    all_types = {**COMPLETENESS_INPUT_TYPES, **field_types}
    clause_functions: list[str] = []
    clause_arguments: list[list[str]] = []
    requirement_functions: list[str] = []
    requirement_arguments: list[list[str]] = []
    for index, (line, body) in enumerate(
        zip(requirement_lines, requirement_bodies, strict=True),
        start=1,
    ):
        digest = hashlib.sha256(line.encode()).hexdigest()
        names = referenced_names(body, COMPLETENESS_INPUT_TYPES)
        requirement_arguments.append(names)
        parameters = ",\n    ".join(
            f"{name}: {COMPLETENESS_INPUT_TYPES[name]}" for name in names
        )
        requirement_functions.append(
            f"""// Accepted requirement {index}: {line}
// Accepted requirement {index} sha256: {digest}
pub open spec fn accepted_requirement_{index}(
    {parameters}
) -> bool {{
    {body}
}}
"""
        )
    for index, (line, body) in enumerate(zip(lines, bodies, strict=True), start=1):
        digest = hashlib.sha256(line.encode()).hexdigest()
        names = referenced_names(body, all_types)
        clause_arguments.append(names)
        parameters = ",\n    ".join(
            f"{name}: {all_types[name]}" for name in names
        )
        clause_functions.append(
            f"""// Accepted clause {index}: {line}
// Accepted clause {index} sha256: {digest}
pub open spec fn accepted_clause_{index}(
    {parameters}
) -> bool {{
    {body}
}}
"""
        )

    input_names = referenced_names(
        "\n".join(
            [
                *requirement_bodies,
                *bodies,
                *completeness_domain_requirements(row),
            ]
        ),
        COMPLETENESS_INPUT_TYPES,
    )
    theorem_parameters = [
        *(f"{name}: {COMPLETENESS_INPUT_TYPES[name]}" for name in input_names),
        *(f"left_{field.name}: {field.rust_type}" for field in fields),
        *(f"right_{field.name}: {field.rust_type}" for field in fields),
    ]

    def clause_call(index: int, side: str) -> str:
        arguments = [
            f"{side}_{name}" if name in field_types else name
            for name in clause_arguments[index - 1]
        ]
        return f"accepted_clause_{index}({', '.join(arguments)})"

    requirements = [
        *(
            f"accepted_requirement_{index}("
            + ", ".join(requirement_arguments[index - 1])
            + ")"
            for index in range(1, len(requirement_lines) + 1)
        ),
        *completeness_domain_requirements(row),
        *(
            requirement
            for side in ("left", "right")
            for requirement in completeness_observable_requirements(
                fields, side
            )
        ),
        *(
            clause_call(index, side)
            for side in ("left", "right")
            for index in range(1, len(lines) + 1)
        ),
    ]
    ensures = [
        f"left_{field.name} == right_{field.name}" for field in fields
    ]
    assertions = "\n".join(f"    assert({line});" for line in ensures)
    rendered_parameters = ",\n    ".join(theorem_parameters)
    rendered_requirements = "\n".join(f"        {line}," for line in requirements)
    rendered_ensures = "\n".join(f"        {line}," for line in ensures)
    return f"""#![allow(dead_code, unused_imports, unused_variables)]
// Clause-derived exact-observation completeness proof for {row.canonical_target}.
// Accepted contract fingerprint: {row.contract_fingerprint}
// Each candidate is constrained by every accepted clause; there is no aggregate
// outcome object or whole-contract dependency.

use vstd::prelude::*;

verus! {{

{COMPLETENESS_MODEL}

{''.join(requirement_functions)}
{''.join(clause_functions)}
pub proof fn completeness(
    {rendered_parameters}
)
    requires
{rendered_requirements}
    ensures
{rendered_ensures}
{{
{assertions}
}}

}} // verus!
"""


def source(
    row: model.Row,
    *,
    completeness: bool = False,
    mutation: bool = False,
) -> str:
    if completeness:
        return completeness_source(row)
    return implementation_source(row, mutation=mutation)


def requires_associated_item_air_adjudication(row: model.Row) -> bool:
    return row.target_id in ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS


def associated_item_bound_declarations(row: model.Row) -> list[str]:
    binder = model.proxy_parts(row)[0]
    return [
        f"{item['name']}: {item['bounds']}"
        for item in model.parse_generic_declarations(binder)
        if "core::iter::IntoIterator<Item =" in item["bounds"]
    ]


def checker_adjudication_source(
    row: model.Row,
    *,
    mutation: bool = False,
) -> str:
    if not requires_associated_item_air_adjudication(row):
        raise RuntimeError(
            f"{row.target_id}: no associated-item AIR adjudication is allowed"
        )
    result = implementation_source(row, mutation=mutation)
    declarations = associated_item_bound_declarations(row)
    if len(declarations) != 1:
        raise RuntimeError(
            f"{row.target_id}: expected one associated-item bound, "
            f"found {declarations}"
        )
    declaration = declarations[0]
    parameter = declaration.split(":", 1)[0]
    occurrences = result.count(declaration)
    if occurrences < 2:
        raise RuntimeError(
            f"{row.target_id}: associated-item bound occurs only "
            f"{occurrences} times"
        )
    result = result.replace(declaration, parameter)
    marker = "#![allow(dead_code, unused_imports, unused_variables)]"
    note = (
        "\n// Verus associated-item AIR adjudication: the exact source-shaped "
        "harness is retained\n"
        "// separately and passes --no-verify. Removing only the "
        "IntoIterator::Item equality\n"
        "// precondition strengthens the proof domain while avoiding the "
        "recorded verifier crash.\n"
    )
    return result.replace(marker, marker + note, 1)
