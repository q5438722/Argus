// Shared ordered-set vocabulary for Rust 1.96 alloc::collections::btree_set.
extern crate alloc;

use alloc::alloc::Allocator;
use alloc::collections::BTreeSet;
use alloc::collections::btree_set::{
    Difference, ExtractIf, Intersection, IntoIter, Iter, Range, SymmetricDifference, Union,
};
use core::borrow::Borrow;
use core::cmp::Ordering;
use core::fmt::Formatter;
use vstd::prelude::*;
use vstd::laws_cmp::obeys_cmp;
use vstd::std_specs::btree::{
    increasing_seq, set_contains_borrowed_key, sets_borrowed_key_to_key,
    sets_differ_by_borrowed_key, spec_btree_keys_iter,
};
use vstd::std_specs::cmp::{OrdSpec, PartialEqSpec, PartialOrdSpec};
use vstd::std_specs::iter::IteratorSpec;
use vstd::std_specs::range::{RangeBoundsSpec, SpecBound};

verus! {

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoIter<T, A: Allocator + Clone>(IntoIter<T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExRange<'a, T: 'a>(Range<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExDifference<'a, T: 'a, A: Allocator + Clone>(Difference<'a, T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExSymmetricDifference<'a, T: 'a>(SymmetricDifference<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntersection<'a, T: 'a, A: Allocator + Clone>(Intersection<'a, T, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
pub struct ExUnion<'a, T: 'a>(Union<'a, T>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(T)]
#[verifier::reject_recursive_types(R)]
#[verifier::reject_recursive_types(F)]
#[verifier::reject_recursive_types(A)]
pub struct ExExtractIf<'a, T, R, F, A: Allocator + Clone>(ExtractIf<'a, T, R, F, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFormatter<'a>(Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFmtError(core::fmt::Error);

#[verifier::prophetic]
pub open spec fn btree_set_sequence<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> Seq<T> {
    spec_btree_keys_iter(&set).remaining().unref()
}

pub uninterp spec fn iter_remaining<'a, T>(iter: Iter<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn into_iter_remaining<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> Seq<T>;
pub uninterp spec fn range_remaining<'a, T>(iter: Range<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn difference_remaining<'a, T, A: Allocator + Clone>(
    iter: Difference<'a, T, A>,
) -> Seq<&'a T>;
pub uninterp spec fn symmetric_difference_remaining<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> Seq<&'a T>;
pub uninterp spec fn intersection_remaining<'a, T, A: Allocator + Clone>(
    iter: Intersection<'a, T, A>,
) -> Seq<&'a T>;
pub uninterp spec fn union_remaining<'a, T>(iter: Union<'a, T>) -> Seq<&'a T>;
pub uninterp spec fn extract_if_remaining<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;

pub broadcast axiom fn axiom_iter_remaining<'a, T>(iter: Iter<'a, T>)
    ensures
        #[trigger] iter_remaining(iter) == IteratorSpec::remaining(&iter),
;

pub open spec fn seq_eq_spec<T: PartialEq>(left: Seq<T>, right: Seq<T>) -> bool
    decreases left.len() + right.len()
{
    if left.len() == 0 || right.len() == 0 {
        left.len() == right.len()
    } else {
        left[0].eq_spec(&right[0])
            && seq_eq_spec(left.drop_first(), right.drop_first())
    }
}

pub open spec fn seq_lex_partial_cmp<T: PartialOrd>(
    left: Seq<T>,
    right: Seq<T>,
) -> Option<Ordering>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        if right.len() == 0 { Some(Ordering::Equal) } else { Some(Ordering::Less) }
    } else if right.len() == 0 {
        Some(Ordering::Greater)
    } else {
        match left[0].partial_cmp_spec(&right[0]) {
            Some(Ordering::Equal) => seq_lex_partial_cmp(left.drop_first(), right.drop_first()),
            answer => answer,
        }
    }
}

pub open spec fn seq_lex_cmp<T: Ord>(left: Seq<T>, right: Seq<T>) -> Ordering
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        if right.len() == 0 { Ordering::Equal } else { Ordering::Less }
    } else if right.len() == 0 {
        Ordering::Greater
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Equal => seq_lex_cmp(left.drop_first(), right.drop_first()),
            answer => answer,
        }
    }
}

pub open spec fn seq_contains_cmp<T: Ord>(items: Seq<T>, value: T) -> bool
    decreases items.len()
{
    items.len() > 0
        && (items[0].cmp_spec(&value) == Ordering::Equal
            || seq_contains_cmp(items.drop_first(), value))
}

pub open spec fn difference_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T>
    decreases left.len()
{
    if left.len() == 0 {
        Seq::empty()
    } else if seq_contains_cmp(right, left[0]) {
        difference_sequence(left.drop_first(), right)
    } else {
        seq![left[0]] + difference_sequence(left.drop_first(), right)
    }
}

pub open spec fn intersection_from_first<T: Ord>(
    first: Seq<T>,
    second: Seq<T>,
) -> Seq<T>
    decreases first.len()
{
    if first.len() == 0 {
        Seq::empty()
    } else if seq_contains_cmp(second, first[0]) {
        seq![first[0]] + intersection_from_first(first.drop_first(), second)
    } else {
        intersection_from_first(first.drop_first(), second)
    }
}

pub open spec fn intersection_source_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T> {
    if left.len() == 0 || right.len() == 0 {
        Seq::empty()
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        Seq::empty()
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        seq![left[0]]
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        seq![left.last()]
    } else if left.len() <= right.len() / 16 {
        intersection_from_first(left, right)
    } else if right.len() <= left.len() / 16 {
        intersection_from_first(right, left)
    } else {
        intersection_from_first(left, right)
    }
}

pub open spec fn union_sequence<T: Ord>(left: Seq<T>, right: Seq<T>) -> Seq<T>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less =>
                seq![left[0]] + union_sequence(left.drop_first(), right),
            Ordering::Greater =>
                seq![right[0]] + union_sequence(left, right.drop_first()),
            Ordering::Equal =>
                seq![left[0]] + union_sequence(left.drop_first(), right.drop_first()),
        }
    }
}

pub open spec fn symmetric_difference_sequence<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> Seq<T>
    decreases left.len() + right.len()
{
    if left.len() == 0 {
        right
    } else if right.len() == 0 {
        left
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less =>
                seq![left[0]] + symmetric_difference_sequence(left.drop_first(), right),
            Ordering::Greater =>
                seq![right[0]] + symmetric_difference_sequence(left, right.drop_first()),
            Ordering::Equal =>
                symmetric_difference_sequence(left.drop_first(), right.drop_first()),
        }
    }
}

pub open spec fn cmp_equal_representative<T: Ord>(
    items: Seq<T>,
    value: T,
) -> Option<T>
    decreases items.len()
{
    if items.len() == 0 {
        None
    } else if items[0].cmp_spec(&value) == Ordering::Equal {
        Some(items[0])
    } else {
        cmp_equal_representative(items.drop_first(), value)
    }
}

pub open spec fn insert_keep_existing<T: Ord>(items: Seq<T>, value: T) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else {
        match value.cmp_spec(&items[0]) {
            Ordering::Less => seq![value] + items,
            Ordering::Equal => items,
            Ordering::Greater =>
                seq![items[0]] + insert_keep_existing(items.drop_first(), value),
        }
    }
}

pub open spec fn replace_representative<T: Ord>(items: Seq<T>, value: T) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        seq![value]
    } else {
        match value.cmp_spec(&items[0]) {
            Ordering::Less => seq![value] + items,
            Ordering::Equal => seq![value] + items.drop_first(),
            Ordering::Greater =>
                seq![items[0]] + replace_representative(items.drop_first(), value),
        }
    }
}

pub open spec fn extend_sequence<T: Ord>(items: Seq<T>, input: Seq<T>) -> Seq<T>
    decreases input.len()
{
    if input.len() == 0 {
        items
    } else {
        extend_sequence(insert_keep_existing(items, input[0]), input.drop_first())
    }
}

pub open spec fn dedup_last_sorted<T: Ord>(items: Seq<T>) -> Seq<T>
    decreases items.len()
{
    if items.len() <= 1 {
        items
    } else if items[0].cmp_spec(&items[1]) == Ordering::Equal {
        dedup_last_sorted(items.drop_first())
    } else {
        seq![items[0]] + dedup_last_sorted(items.drop_first())
    }
}

pub open spec fn nondecreasing_sequence<T: Ord>(items: Seq<T>) -> bool
    decreases items.len()
{
    items.len() <= 1
        || (items[0].cmp_spec(&items[1]) != Ordering::Greater
            && nondecreasing_sequence(items.drop_first()))
}

pub uninterp spec fn into_iterator_sequence<T, I>(iter: &I) -> Seq<T>;
pub uninterp spec fn stable_sorted_sequence<T: Ord>(input: Seq<T>) -> Seq<T>;

pub open spec fn last_cmp_equal_input<T: Ord>(
    input: Seq<T>,
    value: T,
) -> Option<T>
    decreases input.len()
{
    if input.len() == 0 {
        None
    } else {
        let later = last_cmp_equal_input(input.drop_first(), value);
        if later.is_some() {
            later
        } else if input[0].cmp_spec(&value) == Ordering::Equal {
            Some(input[0])
        } else {
            None
        }
    }
}

pub open spec fn stable_tie_order<T: Ord>(
    input: Seq<T>,
    sorted: Seq<T>,
) -> bool {
    let representatives = dedup_last_sorted(sorted);
    forall |index: int|
        0 <= index < representatives.len()
        ==> #[trigger] last_cmp_equal_input(input, representatives[index])
            == Some(representatives[index])
}
pub uninterp spec fn clone_value<T: Clone>(value: T) -> T;

pub open spec fn clone_sequence<T: Clone>(items: Seq<T>) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        seq![clone_value(items[0])] + clone_sequence(items.drop_first())
    }
}

pub open spec fn clone_sequence_preserves_values<T: Clone>(items: Seq<T>) -> bool
    decreases items.len()
{
    items.len() == 0
        || (clone_value(items[0]) == items[0]
            && clone_sequence_preserves_values(items.drop_first()))
}

pub uninterp spec fn borrowed_key_projection<
    'a,
    T: Borrow<K>,
    K: ?Sized,
>(
    item: &'a T,
) -> &'a K;

#[verifier::external_body]
pub fn borrowed_key_projection_exec<
    'a,
    T: Borrow<K>,
    K: ?Sized,
>(
    item: &'a T,
) -> (result: &'a K)
    ensures
        result == borrowed_key_projection(item),
{
    item.borrow()
}

pub open spec fn borrowed_key_order<T: Borrow<K>, K: ?Sized + Ord>(
    item: &T,
    key: &K,
) -> Ordering {
    borrowed_key_projection(item).cmp_spec(key)
}

pub open spec fn borrowed_key_order_law<
    T: Borrow<K>,
    K: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &K,
) -> bool {
    &&& forall |index: int| 0 <= index < items.len() ==>
        (#[trigger] borrowed_key_order(&items[index], key) == Ordering::Equal
            <==> sets_borrowed_key_to_key(
                items.to_set(),
                key,
                &items[index],
            ))
    &&& forall |left: int, right: int|
        #![trigger borrowed_key_order(&items[left], key),
            borrowed_key_order(&items[right], key)]
        0 <= left < right < items.len()
        && borrowed_key_order(&items[left], key) == Ordering::Greater
        ==> borrowed_key_order(&items[right], key) == Ordering::Greater
    &&& forall |left: int, right: int|
        #![trigger borrowed_key_order(&items[left], key),
            borrowed_key_order(&items[right], key)]
        0 <= left < right < items.len()
        && borrowed_key_order(&items[right], key) == Ordering::Less
        ==> borrowed_key_order(&items[left], key) == Ordering::Less
}

pub open spec fn range_bound_order<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> Option<Ordering> {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Included(start), SpecBound::Included(end))
        | (SpecBound::Included(start), SpecBound::Excluded(end))
        | (SpecBound::Excluded(start), SpecBound::Included(end))
        | (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            Some(start.cmp_spec(end))
        }
        _ => None,
    }
}

pub open spec fn range_bounds_law<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    range_bound_order(range).is_none() <==> (
        range.spec_start_bound() matches SpecBound::Unbounded
        || range.spec_end_bound() matches SpecBound::Unbounded
    )
}

pub open spec fn range_start_after_end<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    range_bound_order(range) == Some(Ordering::Greater)
}

pub open spec fn range_equal_excluded<
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Equal
        }
        _ => false,
    }
}

pub open spec fn range_contains<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    item: &T,
    range: &R,
) -> bool {
    let starts_after = match range.spec_start_bound() {
        SpecBound::Unbounded => true,
        SpecBound::Included(start) => {
            borrowed_key_order(item, start) != Ordering::Less
        }
        SpecBound::Excluded(start) => {
            borrowed_key_order(item, start) == Ordering::Greater
        }
    };
    let ends_before = match range.spec_end_bound() {
        SpecBound::Unbounded => true,
        SpecBound::Included(end) => {
            borrowed_key_order(item, end) != Ordering::Greater
        }
        SpecBound::Excluded(end) => {
            borrowed_key_order(item, end) == Ordering::Less
        }
    };
    starts_after && ends_before
}

pub open spec fn range_order_law<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    items: Seq<T>,
    range: &R,
) -> bool {
    &&& range_bounds_law(range)
    &&& match range.spec_start_bound() {
        SpecBound::Included(start) | SpecBound::Excluded(start) => {
            borrowed_key_order_law(items, start)
        }
        SpecBound::Unbounded => true,
    }
    &&& match range.spec_end_bound() {
        SpecBound::Included(end) | SpecBound::Excluded(end) => {
            borrowed_key_order_law(items, end)
        }
        SpecBound::Unbounded => true,
    }
}

pub open spec fn range_sequence<
    T: core::borrow::Borrow<K>,
    K: ?Sized + Ord,
    R: core::ops::RangeBounds<K>,
>(
    items: Seq<T>,
    range: &R,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if range_contains(&items[0], range) {
        seq![items[0]] + range_sequence(items.drop_first(), range)
    } else {
        range_sequence(items.drop_first(), range)
    }
}

pub open spec fn borrowed_representative<
    T: Borrow<Q>,
    Q: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &Q,
) -> Option<T>
    decreases items.len()
{
    if items.len() == 0 {
        None
    } else if borrowed_key_order(&items[0], key) == Ordering::Equal {
        Some(items[0])
    } else {
        borrowed_representative(items.drop_first(), key)
    }
}

pub open spec fn remove_borrowed_representative<
    T: Borrow<Q>,
    Q: ?Sized + Ord,
>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Equal {
        items.drop_first()
    } else {
        seq![items[0]] + remove_borrowed_representative(items.drop_first(), key)
    }
}

pub open spec fn split_before<T: Borrow<Q>, Q: ?Sized + Ord>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Less {
        seq![items[0]] + split_before(items.drop_first(), key)
    } else {
        Seq::empty()
    }
}

pub open spec fn split_at_or_after<T: Borrow<Q>, Q: ?Sized + Ord>(
    items: Seq<T>,
    key: &Q,
) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else if borrowed_key_order(&items[0], key) == Ordering::Less {
        split_at_or_after(items.drop_first(), key)
    } else {
        items
    }
}

pub open spec fn fn_mut_result<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
) -> bool
    recommends
        state.requires((item,)),
        exists |result: bool| state.ensures((item,), result),
{
    choose |result: bool| state.ensures((item,), result)
}

pub uninterp spec fn fn_mut_post_state<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
    result: bool,
) -> F;

#[verifier::prophetic]
pub open spec fn fn_mut_step_law<T, F: FnMut(&T) -> bool>(
    state: F,
    item: &T,
) -> bool {
    let result = fn_mut_result(state, item);
    let post = fn_mut_post_state(state, item, result);
    &&& state.requires((item,))
    &&& state.ensures((item,), result)
    &&& exists |callback: &mut F|
        #[trigger] call_ensures::<(&T,), &mut F>(
            callback,
            (item,),
            result,
        )
        && call_requires::<(&T,), &mut F>(callback, (item,))
        && mut_ref_current(callback) == state
        && mut_ref_future(callback) == post
}

pub open spec fn retain_decisions_from<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> Seq<bool>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        let keep = fn_mut_result(state, &items[0]);
        seq![keep]
            + retain_decisions_from(
                fn_mut_post_state(state, &items[0], keep),
                items.drop_first(),
            )
    }
}

pub open spec fn retain_effect_trace_from<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> Seq<F>
    decreases items.len()
{
    if items.len() == 0 {
        Seq::empty()
    } else {
        let keep = fn_mut_result(state, &items[0]);
        let next = fn_mut_post_state(state, &items[0], keep);
        seq![next]
            + retain_effect_trace_from(
                next,
                items.drop_first(),
            )
    }
}

pub open spec fn retain_callback_state_after<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
    count: nat,
) -> F
    decreases count
{
    if count == 0 || items.len() == 0 {
        state
    } else {
        let keep = fn_mut_result(state, &items[0]);
        retain_callback_state_after(
            fn_mut_post_state(state, &items[0], keep),
            items.drop_first(),
            (count - 1) as nat,
        )
    }
}

#[verifier::prophetic]
pub open spec fn retain_callback_trace_law<T, F: FnMut(&T) -> bool>(
    state: F,
    items: Seq<T>,
) -> bool
    decreases items.len()
{
    if items.len() == 0 {
        true
    } else {
        let keep = fn_mut_result(state, &items[0]);
        &&& fn_mut_step_law(state, &items[0])
        &&& retain_callback_trace_law(
            fn_mut_post_state(state, &items[0], keep),
            items.drop_first(),
        )
    }
}

pub open spec fn retain_decisions<T, F: FnMut(&T) -> bool>(
    callback: &F,
    items: Seq<T>,
) -> Seq<bool> {
    retain_decisions_from(*callback, items)
}

pub open spec fn retain_effect_trace<T, F: FnMut(&T) -> bool>(
    callback: &F,
    items: Seq<T>,
) -> Seq<F> {
    retain_effect_trace_from(*callback, items)
}

pub open spec fn retain_selected<T>(items: Seq<T>, decisions: Seq<bool>) -> Seq<T>
    decreases items.len()
{
    if items.len() == 0 || decisions.len() == 0 {
        Seq::empty()
    } else if decisions[0] {
        seq![items[0]] + retain_selected(items.drop_first(), decisions.drop_first())
    } else {
        retain_selected(items.drop_first(), decisions.drop_first())
    }
}

pub ghost struct SetAdapterState<T> {
    pub variant: int,
    pub first: Seq<T>,
    pub second: Seq<T>,
    pub lookup: Seq<T>,
    pub answer: Option<T>,
    pub peeked_side: int,
    pub peeked: Option<T>,
}

pub ghost struct AdapterStep<T> {
    pub returned: Option<T>,
    pub state: SetAdapterState<T>,
}

pub ghost struct MergeStep<T> {
    pub left: Option<T>,
    pub right: Option<T>,
    pub state: SetAdapterState<T>,
}

pub open spec fn adapter_state<T>(
    variant: int,
    first: Seq<T>,
    second: Seq<T>,
    lookup: Seq<T>,
    answer: Option<T>,
    peeked_side: int,
    peeked: Option<T>,
) -> SetAdapterState<T> {
    SetAdapterState {
        variant,
        first,
        second,
        lookup,
        answer,
        peeked_side,
        peeked,
    }
}

pub open spec fn optional_sequence<T>(item: Option<T>) -> Seq<T> {
    match item {
        Some(value) => seq![value],
        None => Seq::empty(),
    }
}

pub open spec fn difference_state_remaining<T: Ord>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.variant == 0 {
        difference_sequence(state.first, state.second)
    } else if state.variant == 1 {
        difference_sequence(state.first, state.lookup)
    } else {
        state.first
    }
}

pub open spec fn intersection_state_remaining<T: Ord>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.variant == 0 {
        intersection_from_first(state.first, state.second)
    } else if state.variant == 1 {
        intersection_from_first(state.first, state.lookup)
    } else {
        optional_sequence(state.answer)
    }
}

pub open spec fn merge_left_remaining<T>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.peeked_side == 1 {
        optional_sequence(state.peeked) + state.first
    } else {
        state.first
    }
}

pub open spec fn merge_right_remaining<T>(
    state: SetAdapterState<T>,
) -> Seq<T> {
    if state.peeked_side == 2 {
        optional_sequence(state.peeked) + state.second
    } else {
        state.second
    }
}

pub open spec fn difference_initial_state<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    if left.len() == 0 || right.len() == 0 {
        adapter_state(
            2, left, Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        adapter_state(
            2, left, Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        adapter_state(
            2,
            left.drop_first(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        adapter_state(
            2,
            left.drop_last(),
            Seq::empty(),
            Seq::empty(),
            None,
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else {
        adapter_state(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn intersection_initial_state<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    if left.len() == 0 || right.len() == 0 {
        adapter_state(
            2, Seq::empty(), Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Greater
        || left.last().cmp_spec(&right[0]) == Ordering::Less
    {
        adapter_state(
            2, Seq::empty(), Seq::empty(), Seq::empty(), None, 0, None,
        )
    } else if left[0].cmp_spec(&right.last()) == Ordering::Equal {
        adapter_state(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left[0]),
            0,
            None,
        )
    } else if left.last().cmp_spec(&right[0]) == Ordering::Equal {
        adapter_state(
            3,
            Seq::empty(),
            Seq::empty(),
            Seq::empty(),
            Some(left.last()),
            0,
            None,
        )
    } else if left.len() <= right.len() / 16 {
        adapter_state(
            1, left, Seq::empty(), right, None, 0, None,
        )
    } else if right.len() <= left.len() / 16 {
        adapter_state(
            1, right, Seq::empty(), left, None, 0, None,
        )
    } else {
        adapter_state(
            0, left, right, Seq::empty(), None, 0, None,
        )
    }
}

pub open spec fn merge_initial_state<T>(
    left: Seq<T>,
    right: Seq<T>,
) -> SetAdapterState<T> {
    adapter_state(
        0, left, right, Seq::empty(), None, 0, None,
    )
}

pub open spec fn difference_stitch_step<T: Ord>(
    current: T,
    first: Seq<T>,
    second: Seq<T>,
) -> AdapterStep<T>
    decreases first.len() + second.len()
{
    if second.len() == 0 {
        AdapterStep {
            returned: Some(current),
            state: adapter_state(
                0, first, second, Seq::empty(), None, 0, None,
            ),
        }
    } else {
        match current.cmp_spec(&second[0]) {
            Ordering::Less => AdapterStep {
                returned: Some(current),
                state: adapter_state(
                    0, first, second, Seq::empty(), None, 0, None,
                ),
            },
            Ordering::Equal => {
                if first.len() == 0 {
                    AdapterStep {
                        returned: None,
                        state: adapter_state(
                            0,
                            Seq::empty(),
                            second,
                            Seq::empty(),
                            None,
                            0,
                            None,
                        ),
                    }
                } else {
                    difference_stitch_step(
                        first[0],
                        first.drop_first(),
                        second.drop_first(),
                    )
                }
            }
            Ordering::Greater => {
                difference_stitch_step(
                    current,
                    first,
                    second.drop_first(),
                )
            }
        }
    }
}

pub open spec fn difference_search_step<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
) -> AdapterStep<T>
    decreases first.len()
{
    if first.len() == 0 {
        AdapterStep {
            returned: None,
            state: adapter_state(
                1, first, Seq::empty(), lookup, None, 0, None,
            ),
        }
    } else if seq_contains_cmp(lookup, first[0]) {
        difference_search_step(first.drop_first(), lookup)
    } else {
        AdapterStep {
            returned: Some(first[0]),
            state: adapter_state(
                1,
                first.drop_first(),
                Seq::empty(),
                lookup,
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn difference_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    if state.variant == 0 {
        if state.first.len() == 0 {
            AdapterStep { returned: None, state }
        } else {
            difference_stitch_step(
                state.first[0],
                state.first.drop_first(),
                state.second,
            )
        }
    } else if state.variant == 1 {
        difference_search_step(state.first, state.lookup)
    } else if state.first.len() == 0 {
        AdapterStep { returned: None, state }
    } else {
        AdapterStep {
            returned: Some(state.first[0]),
            state: adapter_state(
                2,
                state.first.drop_first(),
                Seq::empty(),
                Seq::empty(),
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn intersection_stitch_scan<T: Ord>(
    a: T,
    a_tail: Seq<T>,
    b: T,
    b_tail: Seq<T>,
) -> AdapterStep<T>
    decreases a_tail.len() + b_tail.len()
{
    match a.cmp_spec(&b) {
        Ordering::Equal => AdapterStep {
            returned: Some(a),
            state: adapter_state(
                0, a_tail, b_tail, Seq::empty(), None, 0, None,
            ),
        },
        Ordering::Less => {
            if a_tail.len() == 0 {
                AdapterStep {
                    returned: None,
                    state: adapter_state(
                        0,
                        Seq::empty(),
                        b_tail,
                        Seq::empty(),
                        None,
                        0,
                        None,
                    ),
                }
            } else {
                intersection_stitch_scan(
                    a_tail[0],
                    a_tail.drop_first(),
                    b,
                    b_tail,
                )
            }
        }
        Ordering::Greater => {
            if b_tail.len() == 0 {
                AdapterStep {
                    returned: None,
                    state: adapter_state(
                        0,
                        a_tail,
                        Seq::empty(),
                        Seq::empty(),
                        None,
                        0,
                        None,
                    ),
                }
            } else {
                intersection_stitch_scan(
                    a,
                    a_tail,
                    b_tail[0],
                    b_tail.drop_first(),
                )
            }
        }
    }
}

pub open spec fn intersection_search_step<T: Ord>(
    first: Seq<T>,
    lookup: Seq<T>,
) -> AdapterStep<T>
    decreases first.len()
{
    if first.len() == 0 {
        AdapterStep {
            returned: None,
            state: adapter_state(
                1, first, Seq::empty(), lookup, None, 0, None,
            ),
        }
    } else if seq_contains_cmp(lookup, first[0]) {
        AdapterStep {
            returned: Some(first[0]),
            state: adapter_state(
                1,
                first.drop_first(),
                Seq::empty(),
                lookup,
                None,
                0,
                None,
            ),
        }
    } else {
        intersection_search_step(first.drop_first(), lookup)
    }
}

pub open spec fn intersection_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    if state.variant == 0 {
        if state.first.len() == 0 {
            AdapterStep { returned: None, state }
        } else if state.second.len() == 0 {
            AdapterStep {
                returned: None,
                state: adapter_state(
                    0,
                    state.first.drop_first(),
                    Seq::empty(),
                    Seq::empty(),
                    None,
                    0,
                    None,
                ),
            }
        } else {
            intersection_stitch_scan(
                state.first[0],
                state.first.drop_first(),
                state.second[0],
                state.second.drop_first(),
            )
        }
    } else if state.variant == 1 {
        intersection_search_step(state.first, state.lookup)
    } else {
        AdapterStep {
            returned: state.answer,
            state: adapter_state(
                2,
                Seq::empty(),
                Seq::empty(),
                Seq::empty(),
                None,
                0,
                None,
            ),
        }
    }
}

pub open spec fn merge_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> MergeStep<T> {
    let left = merge_left_remaining(state);
    let right = merge_right_remaining(state);
    if left.len() == 0 {
        if right.len() == 0 {
            MergeStep {
                left: None,
                right: None,
                state: merge_initial_state(left, right),
            }
        } else {
            MergeStep {
                left: None,
                right: Some(right[0]),
                state: merge_initial_state(left, right.drop_first()),
            }
        }
    } else if right.len() == 0 {
        MergeStep {
            left: Some(left[0]),
            right: None,
            state: merge_initial_state(left.drop_first(), right),
        }
    } else {
        match left[0].cmp_spec(&right[0]) {
            Ordering::Less => MergeStep {
                left: Some(left[0]),
                right: None,
                state: adapter_state(
                    0,
                    left.drop_first(),
                    right.drop_first(),
                    Seq::empty(),
                    None,
                    2,
                    Some(right[0]),
                ),
            },
            Ordering::Greater => MergeStep {
                left: None,
                right: Some(right[0]),
                state: adapter_state(
                    0,
                    left.drop_first(),
                    right.drop_first(),
                    Seq::empty(),
                    None,
                    1,
                    Some(left[0]),
                ),
            },
            Ordering::Equal => MergeStep {
                left: Some(left[0]),
                right: Some(right[0]),
                state: merge_initial_state(
                    left.drop_first(),
                    right.drop_first(),
                ),
            },
        }
    }
}

pub open spec fn union_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T> {
    let step = merge_next_step(state);
    AdapterStep {
        returned: if step.left.is_some() { step.left } else { step.right },
        state: step.state,
    }
}

pub open spec fn symmetric_difference_next_step<T: Ord>(
    state: SetAdapterState<T>,
) -> AdapterStep<T>
    decreases merge_left_remaining(state).len()
        + merge_right_remaining(state).len()
{
    let step = merge_next_step(state);
    if step.left.is_some() && step.right.is_some() {
        symmetric_difference_next_step(step.state)
    } else {
        AdapterStep {
            returned: if step.left.is_some() { step.left } else { step.right },
            state: step.state,
        }
    }
}

pub uninterp spec fn difference_source_state<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> SetAdapterState<T>;

pub uninterp spec fn symmetric_difference_source_state<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> SetAdapterState<T>;

pub uninterp spec fn intersection_source_state<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> SetAdapterState<T>;

pub uninterp spec fn union_source_state<'a, T>(
    iter: Union<'a, T>,
) -> SetAdapterState<T>;

pub open spec fn difference_source_state_law<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> bool {
    let state = difference_source_state(iter);
    &&& 0 <= state.variant <= 2
    &&& state.peeked_side == 0
    &&& state.peeked.is_none()
    &&& difference_remaining(iter).unref()
        == difference_state_remaining(state)
}

pub open spec fn symmetric_difference_source_state_law<'a, T: Ord>(
    iter: SymmetricDifference<'a, T>,
) -> bool {
    let state = symmetric_difference_source_state(iter);
    &&& state.variant == 0
    &&& 0 <= state.peeked_side <= 2
    &&& (state.peeked_side == 0 <==> state.peeked.is_none())
    &&& symmetric_difference_remaining(iter).unref()
        == symmetric_difference_sequence(
            merge_left_remaining(state),
            merge_right_remaining(state),
        )
}

pub open spec fn intersection_source_state_law<
    'a,
    T: Ord,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> bool {
    let state = intersection_source_state(iter);
    &&& 0 <= state.variant <= 3
    &&& state.peeked_side == 0
    &&& state.peeked.is_none()
    &&& (state.variant == 2 ==> state.answer.is_none())
    &&& (state.variant == 3 ==> state.answer.is_some())
    &&& intersection_remaining(iter).unref()
        == intersection_state_remaining(state)
}

pub open spec fn union_source_state_law<'a, T: Ord>(
    iter: Union<'a, T>,
) -> bool {
    let state = union_source_state(iter);
    &&& state.variant == 0
    &&& 0 <= state.peeked_side <= 2
    &&& (state.peeked_side == 0 <==> state.peeked.is_none())
    &&& union_remaining(iter).unref()
        == union_sequence(
            merge_left_remaining(state),
            merge_right_remaining(state),
        )
}

pub ghost struct AdapterDebugShape<T> {
    pub source_tag: int,
    pub variant: int,
    pub structure: Seq<int>,
    pub primary: Seq<T>,
    pub secondary: Seq<T>,
    pub tertiary: Seq<T>,
    pub non_exhaustive: bool,
}

#[verifier::prophetic]
pub open spec fn btree_set_debug_shape<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> AdapterDebugShape<T> {
    AdapterDebugShape {
        source_tag: 9,
        variant: 0,
        structure: seq![1],
        primary: btree_set_sequence(set),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}

#[verifier::prophetic]
pub open spec fn btree_set_debug_shape_law<T, A: Allocator + Clone>(
    set: BTreeSet<T, A>,
) -> bool {
    &&& btree_set_debug_shape(set).source_tag == 9
    &&& btree_set_debug_shape(set).variant == 0
    &&& btree_set_debug_shape(set).structure == seq![1]
    &&& btree_set_debug_shape(set).primary == btree_set_sequence(set)
    &&& btree_set_debug_shape(set).secondary == Seq::empty()
    &&& btree_set_debug_shape(set).tertiary == Seq::empty()
    &&& !btree_set_debug_shape(set).non_exhaustive
}

// Structure codes name the exact source builders/fields:
// 1 debug_set, 2 debug_tuple, 3 debug_struct, 4 debug_list,
// 101 Iter, 102 IntoIter, 103 Range, 104 Difference,
// 105 SymmetricDifference, 106 Intersection, 107 Union,
// 108 ExtractIf, 109 MergeIterInner, 110 Stitch, 111 Search,
// 112 Iterate, 113 Answer, 201 iter, 202 self_iter, 203 other_iter,
// 204 a, 205 b, 206 small_iter, 207 large_set, 208 peek.
pub open spec fn iter_debug_shape<'a, T>(
    iter: Iter<'a, T>,
) -> AdapterDebugShape<&'a T> {
    AdapterDebugShape {
        source_tag: 1,
        variant: 0,
        structure: seq![2, 101, 4],
        primary: iter_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn iter_debug_shape_law<'a, T>(iter: Iter<'a, T>) -> bool {
    &&& iter_debug_shape(iter).source_tag == 1
    &&& iter_debug_shape(iter).variant == 0
    &&& iter_debug_shape(iter).structure == seq![2, 101, 4]
    &&& iter_debug_shape(iter).primary == iter_remaining(iter)
    &&& iter_debug_shape(iter).secondary == Seq::empty()
    &&& iter_debug_shape(iter).tertiary == Seq::empty()
    &&& !iter_debug_shape(iter).non_exhaustive
}

pub open spec fn into_iter_debug_shape<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> AdapterDebugShape<T> {
    AdapterDebugShape {
        source_tag: 2,
        variant: 0,
        structure: seq![3, 102, 201, 4],
        primary: into_iter_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn into_iter_debug_shape_law<T, A: Allocator + Clone>(
    iter: IntoIter<T, A>,
) -> bool {
    &&& into_iter_debug_shape(iter).source_tag == 2
    &&& into_iter_debug_shape(iter).variant == 0
    &&& into_iter_debug_shape(iter).structure == seq![3, 102, 201, 4]
    &&& into_iter_debug_shape(iter).primary == into_iter_remaining(iter)
    &&& into_iter_debug_shape(iter).secondary == Seq::empty()
    &&& into_iter_debug_shape(iter).tertiary == Seq::empty()
    &&& !into_iter_debug_shape(iter).non_exhaustive
}

pub open spec fn range_debug_shape<'a, T>(
    iter: Range<'a, T>,
) -> AdapterDebugShape<&'a T> {
    AdapterDebugShape {
        source_tag: 3,
        variant: 0,
        structure: seq![3, 103, 201, 4],
        primary: range_remaining(iter),
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn range_debug_shape_law<'a, T>(iter: Range<'a, T>) -> bool {
    &&& range_debug_shape(iter).source_tag == 3
    &&& range_debug_shape(iter).variant == 0
    &&& range_debug_shape(iter).structure == seq![3, 103, 201, 4]
    &&& range_debug_shape(iter).primary == range_remaining(iter)
    &&& range_debug_shape(iter).secondary == Seq::empty()
    &&& range_debug_shape(iter).tertiary == Seq::empty()
    &&& !range_debug_shape(iter).non_exhaustive
}

pub open spec fn difference_debug_shape<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> AdapterDebugShape<T> {
    let state = difference_source_state(iter);
    AdapterDebugShape {
        source_tag: 4,
        variant: state.variant,
        structure: if state.variant == 0 {
            seq![2, 104, 3, 110, 202, 203]
        } else if state.variant == 1 {
            seq![2, 104, 3, 111, 202, 203]
        } else {
            seq![2, 104, 2, 112]
        },
        primary: state.first,
        secondary: if state.variant == 0 {
            state.second
        } else if state.variant == 1 {
            state.lookup
        } else {
            Seq::empty()
        },
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn difference_debug_shape_law<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Difference<'a, T, A>,
) -> bool {
    let state = difference_source_state(iter);
    &&& 0 <= state.variant <= 2
    &&& difference_debug_shape(iter).source_tag == 4
    &&& difference_debug_shape(iter).variant == state.variant
    &&& difference_debug_shape(iter).primary == state.first
    &&& difference_debug_shape(iter).secondary == if state.variant == 0 {
        state.second
    } else if state.variant == 1 {
        state.lookup
    } else {
        Seq::empty()
    }
    &&& difference_debug_shape(iter).tertiary == Seq::empty()
    &&& !difference_debug_shape(iter).non_exhaustive
}

pub open spec fn symmetric_difference_debug_shape<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> AdapterDebugShape<T> {
    let state = symmetric_difference_source_state(iter);
    AdapterDebugShape {
        source_tag: 5,
        variant: state.peeked_side,
        structure: seq![2, 105, 2, 109, 204, 205, 208],
        primary: state.first,
        secondary: state.second,
        tertiary: optional_sequence(state.peeked),
        non_exhaustive: false,
    }
}
pub open spec fn symmetric_difference_debug_shape_law<'a, T>(
    iter: SymmetricDifference<'a, T>,
) -> bool {
    let state = symmetric_difference_source_state(iter);
    &&& 0 <= state.peeked_side <= 2
    &&& symmetric_difference_debug_shape(iter).source_tag == 5
    &&& symmetric_difference_debug_shape(iter).variant == state.peeked_side
    &&& symmetric_difference_debug_shape(iter).primary == state.first
    &&& symmetric_difference_debug_shape(iter).secondary == state.second
    &&& symmetric_difference_debug_shape(iter).tertiary
        == optional_sequence(state.peeked)
    &&& !symmetric_difference_debug_shape(iter).non_exhaustive
}

pub open spec fn intersection_debug_shape<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> AdapterDebugShape<T> {
    let state = intersection_source_state(iter);
    AdapterDebugShape {
        source_tag: 6,
        variant: state.variant,
        structure: if state.variant == 0 {
            seq![2, 106, 3, 110, 204, 205]
        } else if state.variant == 1 {
            seq![2, 106, 3, 111, 206, 207]
        } else {
            seq![2, 106, 2, 113]
        },
        primary: state.first,
        secondary: if state.variant == 0 {
            state.second
        } else if state.variant == 1 {
            state.lookup
        } else {
            optional_sequence(state.answer)
        },
        tertiary: Seq::empty(),
        non_exhaustive: false,
    }
}
pub open spec fn intersection_debug_shape_law<
    'a,
    T,
    A: Allocator + Clone,
>(
    iter: Intersection<'a, T, A>,
) -> bool {
    let state = intersection_source_state(iter);
    &&& 0 <= state.variant <= 3
    &&& intersection_debug_shape(iter).source_tag == 6
    &&& intersection_debug_shape(iter).variant == state.variant
    &&& intersection_debug_shape(iter).primary == state.first
    &&& intersection_debug_shape(iter).secondary == if state.variant == 0 {
        state.second
    } else if state.variant == 1 {
        state.lookup
    } else {
        optional_sequence(state.answer)
    }
    &&& intersection_debug_shape(iter).tertiary == Seq::empty()
    &&& !intersection_debug_shape(iter).non_exhaustive
}

pub open spec fn union_debug_shape<'a, T>(
    iter: Union<'a, T>,
) -> AdapterDebugShape<T> {
    let state = union_source_state(iter);
    AdapterDebugShape {
        source_tag: 7,
        variant: state.peeked_side,
        structure: seq![2, 107, 2, 109, 204, 205, 208],
        primary: state.first,
        secondary: state.second,
        tertiary: optional_sequence(state.peeked),
        non_exhaustive: false,
    }
}
pub open spec fn union_debug_shape_law<'a, T>(iter: Union<'a, T>) -> bool {
    let state = union_source_state(iter);
    &&& 0 <= state.peeked_side <= 2
    &&& union_debug_shape(iter).source_tag == 7
    &&& union_debug_shape(iter).variant == state.peeked_side
    &&& union_debug_shape(iter).primary == state.first
    &&& union_debug_shape(iter).secondary == state.second
    &&& union_debug_shape(iter).tertiary == optional_sequence(state.peeked)
    &&& !union_debug_shape(iter).non_exhaustive
}

pub open spec fn extract_if_debug_shape<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> AdapterDebugShape<T> {
    let pending = extract_if_pending(iter);
    AdapterDebugShape {
        source_tag: 8,
        variant: 0,
        structure: seq![3, 108, 208],
        primary: if pending.len() > 0 {
            seq![pending[0]]
        } else {
            Seq::empty()
        },
        secondary: Seq::empty(),
        tertiary: Seq::empty(),
        non_exhaustive: true,
    }
}

pub open spec fn extract_if_debug_shape_law<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let pending = extract_if_pending(iter);
    &&& extract_if_debug_shape(iter).source_tag == 8
    &&& extract_if_debug_shape(iter).variant == 0
    &&& extract_if_debug_shape(iter).structure == seq![3, 108, 208]
    &&& extract_if_debug_shape(iter).primary == if pending.len() > 0 {
        seq![pending[0]]
    } else {
        Seq::empty()
    }
    &&& extract_if_debug_shape(iter).secondary == Seq::empty()
    &&& extract_if_debug_shape(iter).tertiary == Seq::empty()
    &&& extract_if_debug_shape(iter).non_exhaustive
}

pub uninterp spec fn hash_length_step<H>(pre_hasher: H, length_prefix: nat) -> H;
pub uninterp spec fn hash_item_step<T, H>(pre_hasher: H, item: T) -> H;

pub open spec fn hash_items_in_order<T, H>(
    pre_hasher: H,
    ordered_items: Seq<T>,
) -> H
    decreases ordered_items.len()
{
    if ordered_items.len() == 0 {
        pre_hasher
    } else {
        hash_items_in_order(
            hash_item_step(pre_hasher, ordered_items[0]),
            ordered_items.drop_first(),
        )
    }
}

pub open spec fn apply_set_hash<T, H>(
    pre_hasher: H,
    length_prefix: nat,
    ordered_items: Seq<T>,
) -> H {
    hash_items_in_order(
        hash_length_step(pre_hasher, length_prefix),
        ordered_items,
    )
}

pub uninterp spec fn debug_builder_start<F>(pre_formatter: F, source_tag: int) -> F;
pub uninterp spec fn debug_builder_variant<F>(formatter: F, variant: int) -> F;
pub uninterp spec fn debug_builder_structure<F>(formatter: F, code: int) -> F;
pub uninterp spec fn debug_builder_entry<T, F>(formatter: F, item: T) -> F;
pub uninterp spec fn debug_builder_finish<F>(
    formatter: F,
    non_exhaustive: bool,
) -> (F, core::fmt::Result);

pub open spec fn debug_entries_in_order<T, F>(
    formatter: F,
    ordered_items: Seq<T>,
) -> F
    decreases ordered_items.len()
{
    if ordered_items.len() == 0 {
        formatter
    } else {
        debug_entries_in_order(
            debug_builder_entry(formatter, ordered_items[0]),
            ordered_items.drop_first(),
        )
    }
}

pub open spec fn debug_structure_in_order<F>(
    formatter: F,
    structure: Seq<int>,
) -> F
    decreases structure.len()
{
    if structure.len() == 0 {
        formatter
    } else {
        debug_structure_in_order(
            debug_builder_structure(formatter, structure[0]),
            structure.drop_first(),
        )
    }
}

pub open spec fn apply_debug_sequence<T, F>(
    pre_formatter: F,
    source_tag: int,
    ordered_items: Seq<T>,
    non_exhaustive: bool,
) -> (F, core::fmt::Result) {
    apply_debug_shape(
        pre_formatter,
        AdapterDebugShape {
            source_tag,
            variant: 0,
            structure: Seq::empty(),
            primary: ordered_items,
            secondary: Seq::empty(),
            tertiary: Seq::empty(),
            non_exhaustive,
        },
    )
}

pub open spec fn apply_debug_shape<T, F>(
    pre_formatter: F,
    shape: AdapterDebugShape<T>,
) -> (F, core::fmt::Result) {
    let started = debug_builder_variant(
        debug_builder_start(pre_formatter, shape.source_tag),
        shape.variant,
    );
    let structured = debug_structure_in_order(started, shape.structure);
    let primary_done = debug_entries_in_order(structured, shape.primary);
    let secondary_done = debug_entries_in_order(primary_done, shape.secondary);
    let tertiary_done = debug_entries_in_order(secondary_done, shape.tertiary);
    debug_builder_finish(tertiary_done, shape.non_exhaustive)
}

pub open spec fn difference_hint_variant<'a, T, A: Allocator + Clone>(
    iter: &Difference<'a, T, A>,
) -> int {
    difference_source_state(*iter).variant
}
pub open spec fn difference_hint_lengths<'a, T, A: Allocator + Clone>(
    iter: &Difference<'a, T, A>,
) -> (nat, nat) {
    let state = difference_source_state(*iter);
    (
        state.first.len(),
        if state.variant == 0 {
            state.second.len()
        } else if state.variant == 1 {
            state.lookup.len()
        } else {
            0
        },
    )
}
pub open spec fn symmetric_difference_hint_lengths<'a, T>(
    iter: &SymmetricDifference<'a, T>,
) -> (nat, nat) {
    let state = symmetric_difference_source_state(*iter);
    (
        merge_left_remaining(state).len(),
        merge_right_remaining(state).len(),
    )
}
pub open spec fn union_hint_lengths<'a, T>(
    iter: &Union<'a, T>,
) -> (nat, nat) {
    let state = union_source_state(*iter);
    (
        merge_left_remaining(state).len(),
        merge_right_remaining(state).len(),
    )
}
pub open spec fn intersection_hint_variant<'a, T, A: Allocator + Clone>(
    iter: &Intersection<'a, T, A>,
) -> int {
    intersection_source_state(*iter).variant
}
pub open spec fn intersection_hint_lengths<'a, T, A: Allocator + Clone>(
    iter: &Intersection<'a, T, A>,
) -> (nat, nat) {
    let state = intersection_source_state(*iter);
    (
        state.first.len(),
        if state.variant == 0 {
            state.second.len()
        } else if state.variant == 1 {
            state.lookup.len()
        } else {
            0
        },
    )
}

pub open spec fn intersection_hint_lower(variant: int, first: nat, second: nat) -> nat {
    if variant == 3 { 1 } else { 0 }
}

pub open spec fn intersection_hint_upper(variant: int, first: nat, second: nat) -> nat {
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

pub uninterp spec fn extract_if_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T>;
pub open spec fn extract_if_length_bound<'a, T, R, F, A: Allocator + Clone>(
    iter: &ExtractIf<'a, T, R, F, A>,
) -> nat {
    extract_if_set(*iter).len()
}
pub uninterp spec fn extract_if_pending<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;
pub uninterp spec fn extract_if_predicate_state<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> F;
pub open spec fn extract_if_decisions<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<bool>
    where F: FnMut(&T) -> bool
{
    retain_decisions_from(
        extract_if_predicate_state(iter),
        extract_if_pending(iter),
    )
}
pub uninterp spec fn extract_if_callback_count<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> nat;
pub uninterp spec fn extract_if_initial_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T>;
pub uninterp spec fn extract_if_yielded<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Seq<T>;
pub ghost struct ExtractIfTerminalState<T> {
    pub retained: Set<T>,
    pub unvisited: Seq<T>,
    pub panicking_candidate: Option<T>,
    pub cursor_taken: bool,
    pub predicate_unwound: bool,
    pub removal_performed: bool,
    pub active: bool,
}

pub open spec fn extract_if_drop_transition<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> ExtractIfTerminalState<T> {
    ExtractIfTerminalState {
        retained: extract_if_set(iter),
        unvisited: extract_if_pending(iter),
        panicking_candidate: None,
        cursor_taken: false,
        predicate_unwound: false,
        removal_performed: false,
        active: false,
    }
}

pub open spec fn extract_if_unwind_step<T>(
    current_set: Set<T>,
    pending: Seq<T>,
) -> ExtractIfTerminalState<T> {
    let candidate = if pending.len() > 0 {
        Some(pending[0])
    } else {
        None
    };
    ExtractIfTerminalState {
        retained: current_set,
        unvisited: Seq::empty(),
        panicking_candidate: candidate,
        cursor_taken: candidate.is_some(),
        predicate_unwound: candidate.is_some(),
        removal_performed: false,
        active: false,
    }
}

pub open spec fn extract_if_panic_transition<
    'a,
    T,
    R,
    F,
    A: Allocator + Clone,
>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> ExtractIfTerminalState<T> {
    extract_if_unwind_step(
        extract_if_set(iter),
        extract_if_pending(iter),
    )
}

pub open spec fn extract_if_drop_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T> {
    extract_if_drop_transition(iter).retained
}

pub open spec fn extract_if_panic_set<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> Set<T> {
    extract_if_panic_transition(iter).retained
}

pub open spec fn first_true(decisions: Seq<bool>) -> int
    decreases decisions.len()
{
    if decisions.len() == 0 {
        0
    } else if decisions[0] {
        0
    } else {
        1 + first_true(decisions.drop_first())
    }
}

pub open spec fn extract_if_panic_preserves_elements<T>(
    pre_set: Set<T>,
    pending: Seq<T>,
    post_set_after_drop: Set<T>,
) -> bool {
    &&& post_set_after_drop == pre_set
    &&& pending.to_set().subset_of(post_set_after_drop)
}

pub open spec fn extract_if_partial_drop_set<T>(
    initial: Set<T>,
    yielded: Seq<T>,
) -> Set<T>
    decreases yielded.len()
{
    if yielded.len() == 0 {
        initial
    } else {
        extract_if_partial_drop_set(initial.remove(yielded[0]), yielded.drop_first())
    }
}

pub open spec fn extract_if_drop_law<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let transition = extract_if_drop_transition(iter);
    &&& !transition.active
    &&& transition.retained == extract_if_set(iter)
    &&& transition.unvisited == extract_if_pending(iter)
    &&& transition.retained == extract_if_partial_drop_set(
            extract_if_initial_set(iter),
            extract_if_yielded(iter),
        )
}

pub open spec fn extract_if_panic_law<'a, T, R, F, A: Allocator + Clone>(
    iter: ExtractIf<'a, T, R, F, A>,
) -> bool {
    let transition = extract_if_panic_transition(iter);
    let expected_set = extract_if_partial_drop_set(
        extract_if_initial_set(iter),
        extract_if_yielded(iter),
    );
    &&& !transition.active
    &&& transition.unvisited == Seq::empty()
    &&& transition.cursor_taken == transition.panicking_candidate.is_some()
    &&& transition.predicate_unwound == transition.panicking_candidate.is_some()
    &&& !transition.removal_performed
    &&& transition.panicking_candidate == if extract_if_pending(iter).len() > 0 {
        Some(extract_if_pending(iter)[0])
    } else {
        None
    }
    &&& extract_if_set(iter) == expected_set
    &&& transition.retained == expected_set
    &&& extract_if_panic_set(iter) == expected_set
    &&& extract_if_panic_preserves_elements(
        expected_set,
        extract_if_pending(iter),
        extract_if_panic_set(iter),
    )
}

} // verus!
