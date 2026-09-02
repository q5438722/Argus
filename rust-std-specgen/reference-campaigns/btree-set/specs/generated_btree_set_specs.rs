// Generated Rust 1.96 BTreeSet specifications; exact-vstd rows are references only.
#![allow(unused_imports, unused_variables)]
#![feature(allocator_api)]

include!("btree_set_shared_vocabulary.rs");

verus! {

// 001_BTreeSet_Hash_hash_2126: <alloc::collections::btree_set::BTreeSet<T, A> as core::hash::Hash>::hash::<H>
// Source: alloc/src/collections/btree/set.rs:87-89
// Principal behavior: the exact length prefix and ascending representative sequence determine the final hasher state.
pub assume_specification<T: core::hash::Hash, A: alloc::alloc::Allocator + core::clone::Clone, H: core::hash::Hasher>[ <BTreeSet<T, A> as core::hash::Hash>::hash::<H> ](
    this: &BTreeSet<T, A>,
    state: &mut H
)
    ensures
        *final(state) == apply_set_hash(*old(state), btree_set_sequence(*this).len() as nat, btree_set_sequence(*this)),
;

// 002_BTreeSet_PartialEq_eq_2128: <alloc::collections::btree_set::BTreeSet<T, A> as core::cmp::PartialEq>::eq
// Source: alloc/src/collections/btree/set.rs:94-96
// Principal behavior: result is exact extensional set equality.
pub assume_specification<T: core::cmp::PartialEq, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::cmp::PartialEq>::eq ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: bool)
    ensures
        result == seq_eq_spec(btree_set_sequence(*this), btree_set_sequence(*other)),
;

// 003_BTreeSet_PartialOrd_partial_cmp_2131: <alloc::collections::btree_set::BTreeSet<T, A> as core::cmp::PartialOrd>::partial_cmp
// Source: alloc/src/collections/btree/set.rs:104-106
// Principal behavior: result is the lexicographic comparison of ascending observations.
pub assume_specification<T: core::cmp::PartialOrd, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::cmp::PartialOrd>::partial_cmp ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: Option<core::cmp::Ordering>)
    ensures
        (T::obeys_partial_cmp_spec()) ==> (result == seq_lex_partial_cmp(btree_set_sequence(*this), btree_set_sequence(*other))),
;

// 004_BTreeSet_Ord_cmp_2133: <alloc::collections::btree_set::BTreeSet<T, A> as core::cmp::Ord>::cmp
// Source: alloc/src/collections/btree/set.rs:111-113
// Principal behavior: result is the lexicographic comparison of ascending observations.
pub assume_specification<T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::cmp::Ord>::cmp ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: core::cmp::Ordering)
    ensures
        (obeys_cmp::<T>()) ==> (obeys_cmp::<T>() ==> (result == seq_lex_cmp(btree_set_sequence(*this), btree_set_sequence(*other)))),
;

// 006_BTreeSet_Clone_clone_from_2136: <alloc::collections::btree_set::BTreeSet<T, A> as core::clone::Clone>::clone_from
// Source: alloc/src/collections/btree/set.rs:122-124
// Principal behavior: clone_from makes the receiver observationally equal to the source.
pub assume_specification<T: core::clone::Clone, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::clone::Clone>::clone_from ](
    this: &mut BTreeSet<T, A>,
    source: &BTreeSet<T, A>
)
    ensures
        btree_set_sequence(*final(this)) == clone_sequence(btree_set_sequence(*source)),
        clone_sequence_preserves_values(btree_set_sequence(*source)) ==> (final(this)@ == source@),
;

// 007_Iter_Debug_fmt_2194: <Iter<'a, T> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:141-143
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug>[ <Iter<'a, T> as core::fmt::Debug>::fmt ](
    this: &Iter<'a, T>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), iter_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), iter_debug_shape(*this)).1,
        iter_debug_shape_law(*this),
;

// 008_IntoIter_Debug_fmt_2229: <IntoIter<T, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:153-153
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<T: core::fmt::Debug, A: core::fmt::Debug + alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<T, A> as core::fmt::Debug>::fmt ](
    this: &IntoIter<T, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), into_iter_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), into_iter_debug_shape(*this)).1,
        into_iter_debug_shape_law(*this),
;

// 009_Range_Debug_fmt_2261: <Range<'a, T> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:168-168
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug + 'a>[ <Range<'a, T> as core::fmt::Debug>::fmt ](
    this: &Range<'a, T>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), range_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), range_debug_shape(*this)).1,
        range_debug_shape_law(*this),
;

// 010_Difference_Debug_fmt_2294: <Difference<'a, T, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:225-227
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <Difference<'a, T, A> as core::fmt::Debug>::fmt ](
    this: &Difference<'a, T, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), difference_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), difference_debug_shape(*this)).1,
        difference_debug_shape_law(*this),
;

// 011_SymmetricDifference_Debug_fmt_2322: <SymmetricDifference<'a, T> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:243-245
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug>[ <SymmetricDifference<'a, T> as core::fmt::Debug>::fmt ](
    this: &SymmetricDifference<'a, T>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), symmetric_difference_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), symmetric_difference_debug_shape(*this)).1,
        symmetric_difference_debug_shape_law(*this),
;

// 012_Intersection_Debug_fmt_2350: <Intersection<'a, T, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:297-299
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <Intersection<'a, T, A> as core::fmt::Debug>::fmt ](
    this: &Intersection<'a, T, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), intersection_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), intersection_debug_shape(*this)).1,
        intersection_debug_shape_law(*this),
;

// 013_Union_Debug_fmt_2378: <Union<'a, T> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:315-317
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T: core::fmt::Debug>[ <Union<'a, T> as core::fmt::Debug>::fmt ](
    this: &Union<'a, T>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), union_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), union_debug_shape(*this)).1,
        union_debug_shape_law(*this),
;

// 015_BTreeSet_inherent_range_2069: alloc::collections::btree_set::BTreeSet::<T, A>::range::<K, R>
// Source: alloc/src/collections/btree/set.rs:398-405
// Principal behavior: normal return requires non-inverted, non-double-excluded equal bounds; remaining observations are exactly ascending in-range representatives.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, K, R>[ BTreeSet::<T, A>::range::<K, R> ](
    this: &BTreeSet<T, A>,
    range: R
) -> (result: Range<'_, T>) where K: core::cmp::Ord + ?Sized, T: core::borrow::Borrow<K> + core::cmp::Ord, R: core::ops::RangeBounds<K>
    requires
        K::obeys_cmp_spec() ==> range_order_law(btree_set_sequence(*this), &range),
        btree_set_sequence(*this).len() == 0 || !range_start_after_end(&range),
        btree_set_sequence(*this).len() == 0 || !range_equal_excluded(&range),
    ensures
        (obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> (range_bounds_law(&range)),
        (obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> (range_remaining(result).unref() == range_sequence(btree_set_sequence(*this), &range)),
        (obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> (range_remaining(result).unref().to_set().subset_of(this@)),
        (obeys_cmp::<T>() && K::obeys_cmp_spec()) ==> (increasing_seq(range_remaining(result).unref())),
;

// 016_BTreeSet_inherent_difference_2071: alloc::collections::btree_set::BTreeSet::<T, A>::difference
// Source: alloc/src/collections/btree/set.rs:428-462
// Principal behavior: remaining observations are exactly self minus other; items are yielded in strictly ascending order without duplicates.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, 'a>[ BTreeSet::<T, A>::difference ](
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>
) -> (result: Difference<'a, T, A>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (difference_remaining(result).unref() == difference_sequence(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (difference_remaining(result).unref().to_set() == this@.difference(other@)),
        (obeys_cmp::<T>()) ==> (increasing_seq(difference_remaining(result).unref())),
        (obeys_cmp::<T>()) ==> (difference_remaining(result).no_duplicates()),
        (obeys_cmp::<T>()) ==> (difference_source_state(result) == difference_initial_state(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (difference_source_state_law(result)),
;

// 017_BTreeSet_inherent_symmetric_difference_2073: alloc::collections::btree_set::BTreeSet::<T, A>::symmetric_difference
// Source: alloc/src/collections/btree/set.rs:485-493
// Principal behavior: remaining observations are exactly membership in one input but not both; items are yielded in strictly ascending order without duplicates.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, 'a>[ BTreeSet::<T, A>::symmetric_difference ](
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>
) -> (result: SymmetricDifference<'a, T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (symmetric_difference_remaining(result).unref() == symmetric_difference_sequence(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (symmetric_difference_remaining(result).unref().to_set() == this@.union(other@).difference(this@.intersect(other@))),
        (obeys_cmp::<T>()) ==> (increasing_seq(symmetric_difference_remaining(result).unref())),
        (obeys_cmp::<T>()) ==> (symmetric_difference_remaining(result).no_duplicates()),
        (obeys_cmp::<T>()) ==> (symmetric_difference_source_state(result) == merge_initial_state(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (symmetric_difference_source_state_law(result)),
;

// 018_BTreeSet_inherent_intersection_2075: alloc::collections::btree_set::BTreeSet::<T, A>::intersection
// Source: alloc/src/collections/btree/set.rs:516-542
// Principal behavior: remaining observations are exactly the intersection; items are yielded in strictly ascending order without duplicates.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, 'a>[ BTreeSet::<T, A>::intersection ](
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>
) -> (result: Intersection<'a, T, A>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (intersection_remaining(result).unref() == intersection_source_sequence(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (intersection_remaining(result).unref().to_set() == this@.intersect(other@)),
        (obeys_cmp::<T>()) ==> (increasing_seq(intersection_remaining(result).unref())),
        (obeys_cmp::<T>()) ==> (intersection_remaining(result).no_duplicates()),
        (obeys_cmp::<T>()) ==> (intersection_source_state(result) == intersection_initial_state(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (intersection_source_state_law(result)),
;

// 019_BTreeSet_inherent_union_2077: alloc::collections::btree_set::BTreeSet::<T, A>::union
// Source: alloc/src/collections/btree/set.rs:563-568
// Principal behavior: remaining observations are exactly the union; items are yielded in strictly ascending order without duplicates.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, 'a>[ BTreeSet::<T, A>::union ](
    this: &'a BTreeSet<T, A>,
    other: &'a BTreeSet<T, A>
) -> (result: Union<'a, T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (union_remaining(result).unref() == union_sequence(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (union_remaining(result).unref().to_set() == this@.union(other@)),
        (obeys_cmp::<T>()) ==> (increasing_seq(union_remaining(result).unref())),
        (obeys_cmp::<T>()) ==> (union_remaining(result).no_duplicates()),
        (obeys_cmp::<T>()) ==> (union_source_state(result) == merge_initial_state(btree_set_sequence(*this), btree_set_sequence(*other))),
        (obeys_cmp::<T>()) ==> (union_source_state_law(result)),
;

// 023_BTreeSet_inherent_is_disjoint_2082: alloc::collections::btree_set::BTreeSet::<T, A>::is_disjoint
// Source: alloc/src/collections/btree/set.rs:658-663
// Principal behavior: result exactly states disjointness, subset, or superset membership.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::is_disjoint ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: bool) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result == (this@.intersect(other@).len() == 0)),
;

// 024_BTreeSet_inherent_is_subset_2083: alloc::collections::btree_set::BTreeSet::<T, A>::is_subset
// Source: alloc/src/collections/btree/set.rs:684-741
// Principal behavior: result exactly states disjointness, subset, or superset membership.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::is_subset ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: bool) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result == this@.subset_of(other@)),
;

// 025_BTreeSet_inherent_is_superset_2084: alloc::collections::btree_set::BTreeSet::<T, A>::is_superset
// Source: alloc/src/collections/btree/set.rs:765-770
// Principal behavior: result exactly states disjointness, subset, or superset membership.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::is_superset ](
    this: &BTreeSet<T, A>,
    other: &BTreeSet<T, A>
) -> (result: bool) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result == other@.subset_of(this@)),
;

// 026_BTreeSet_inherent_first_2085: alloc::collections::btree_set::BTreeSet::<T, A>::first
// Source: alloc/src/collections/btree/set.rs:792-797
// Principal behavior: None is returned exactly for the empty set; Some returns the minimum or maximum stored representative.
pub assume_specification<'s, T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::first ](
    this: &'s BTreeSet<T, A>
) -> (result: Option<&'s T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result.is_some() <==> btree_set_sequence(*this).len() > 0),
        (obeys_cmp::<T>()) ==> (match result { Some(item) => *item == btree_set_sequence(*this)[0], None => true }),
;

// 027_BTreeSet_inherent_last_2086: alloc::collections::btree_set::BTreeSet::<T, A>::last
// Source: alloc/src/collections/btree/set.rs:819-824
// Principal behavior: None is returned exactly for the empty set; Some returns the minimum or maximum stored representative.
pub assume_specification<'s, T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::last ](
    this: &'s BTreeSet<T, A>
) -> (result: Option<&'s T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result.is_some() <==> btree_set_sequence(*this).len() > 0),
        (obeys_cmp::<T>()) ==> (match result { Some(item) => *item == btree_set_sequence(*this).last(), None => true }),
;

// 028_BTreeSet_inherent_pop_first_2087: alloc::collections::btree_set::BTreeSet::<T, A>::pop_first
// Source: alloc/src/collections/btree/set.rs:843-848
// Principal behavior: None leaves an empty set unchanged; Some returns and removes exactly the minimum or maximum representative.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::pop_first ](
    this: &mut BTreeSet<T, A>
) -> (result: Option<T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result.is_some() <==> btree_set_sequence(*old(this)).len() > 0),
        (obeys_cmp::<T>()) ==> (result == if btree_set_sequence(*old(this)).len() > 0 { Some(btree_set_sequence(*old(this))[0]) } else { None }),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == if btree_set_sequence(*old(this)).len() > 0 { btree_set_sequence(*old(this)).drop_first() } else { btree_set_sequence(*old(this)) }),
        (obeys_cmp::<T>()) ==> (match result { Some(item) => final(this)@ == old(this)@.remove(item), None => final(this)@ == old(this)@ }),
;

// 029_BTreeSet_inherent_pop_last_2088: alloc::collections::btree_set::BTreeSet::<T, A>::pop_last
// Source: alloc/src/collections/btree/set.rs:867-872
// Principal behavior: None leaves an empty set unchanged; Some returns and removes exactly the minimum or maximum representative.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::pop_last ](
    this: &mut BTreeSet<T, A>
) -> (result: Option<T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result.is_some() <==> btree_set_sequence(*old(this)).len() > 0),
        (obeys_cmp::<T>()) ==> (result == if btree_set_sequence(*old(this)).len() > 0 { Some(btree_set_sequence(*old(this)).last()) } else { None }),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == if btree_set_sequence(*old(this)).len() > 0 { btree_set_sequence(*old(this)).drop_last() } else { btree_set_sequence(*old(this)) }),
        (obeys_cmp::<T>()) ==> (match result { Some(item) => final(this)@ == old(this)@.remove(item), None => final(this)@ == old(this)@ }),
;

// 031_BTreeSet_inherent_replace_2090: alloc::collections::btree_set::BTreeSet::<T, A>::replace
// Source: alloc/src/collections/btree/set.rs:924-929
// Principal behavior: membership gains the supplied comparator class; an old comparator-equal representative is returned and replaced when present.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::replace ](
    this: &mut BTreeSet<T, A>,
    value: T
) -> (result: Option<T>) where T: core::cmp::Ord
    ensures
        (obeys_cmp::<T>()) ==> (result == cmp_equal_representative(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == replace_representative(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>()) ==> (final(this)@ == old(this)@.insert(value)),
;

// 033_BTreeSet_inherent_take_2094: alloc::collections::btree_set::BTreeSet::<T, A>::take::<Q>
// Source: alloc/src/collections/btree/set.rs:1078-1084
// Principal behavior: result presence equals borrowed-key membership; the comparator-equal stored representative is returned and removed.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, Q>[ BTreeSet::<T, A>::take::<Q> ](
    this: &mut BTreeSet<T, A>,
    value: &Q
) -> (result: Option<T>) where T: core::borrow::Borrow<Q> + core::cmp::Ord, Q: core::cmp::Ord + ?Sized
    requires
        borrowed_key_order_law(btree_set_sequence(*this), value),
    ensures
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (result == borrowed_representative(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (btree_set_sequence(*final(this)) == remove_borrowed_representative(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (match result { Some(item) => sets_borrowed_key_to_key(old(this)@, value, &item) && sets_differ_by_borrowed_key(old(this)@, final(this)@, value), None => !set_contains_borrowed_key(old(this)@, value) && final(this)@ == old(this)@ }),
;

// 034_BTreeSet_inherent_retain_2095: alloc::collections::btree_set::BTreeSet::<T, A>::retain::<F>
// Source: alloc/src/collections/btree/set.rs:1102-1108
// Principal behavior: callbacks are observed in ascending key order; the final set contains exactly retained pre-state representatives.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, F>[ BTreeSet::<T, A>::retain::<F> ](
    this: &mut BTreeSet<T, A>,
    f: F
) where T: core::cmp::Ord, F: core::ops::FnMut(&T) -> bool
    requires
        retain_callback_trace_law(f, btree_set_sequence(*this)),
    ensures
        (obeys_cmp::<T>()) ==> (retain_decisions(&f, btree_set_sequence(*old(this))).len() == btree_set_sequence(*old(this)).len()),
        (obeys_cmp::<T>()) ==> (retain_effect_trace(&f, btree_set_sequence(*old(this))).len() == btree_set_sequence(*old(this)).len()),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == retain_selected(btree_set_sequence(*old(this)), retain_decisions(&f, btree_set_sequence(*old(this))))),
        (obeys_cmp::<T>()) ==> (final(this)@ == retain_selected(btree_set_sequence(*old(this)), retain_decisions(&f, btree_set_sequence(*old(this)))).to_set()),
;

// 035_BTreeSet_inherent_append_2096: alloc::collections::btree_set::BTreeSet::<T, A>::append
// Source: alloc/src/collections/btree/set.rs:1139-1145
// Principal behavior: other is empty afterward and membership is the union; representative identity follows BTreeMap append conflict handling.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeSet::<T, A>::append ](
    this: &mut BTreeSet<T, A>,
    other: &mut BTreeSet<T, A>
) where T: core::cmp::Ord, A: core::clone::Clone
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(other)) == Seq::empty()),
        (obeys_cmp::<T>()) ==> (final(other)@ == Set::empty()),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == union_sequence(btree_set_sequence(*old(this)), btree_set_sequence(*old(other)))),
        (obeys_cmp::<T>()) ==> (final(this)@ == old(this)@.union(old(other)@)),
;

// 036_BTreeSet_inherent_split_off_2097: alloc::collections::btree_set::BTreeSet::<T, A>::split_off::<Q>
// Source: alloc/src/collections/btree/set.rs:1177-1183
// Principal behavior: left and returned sets partition the old set at the borrowed-order boundary; partition lengths sum to the old length.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, Q: ?Sized + core::cmp::Ord>[ BTreeSet::<T, A>::split_off::<Q> ](
    this: &mut BTreeSet<T, A>,
    value: &Q
) -> (result: BTreeSet<T, A>) where T: core::borrow::Borrow<Q> + core::cmp::Ord, A: core::clone::Clone
    requires
        borrowed_key_order_law(btree_set_sequence(*this), value),
    ensures
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (btree_set_sequence(*final(this)) == split_before(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (btree_set_sequence(result) == split_at_or_after(btree_set_sequence(*old(this)), value)),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (final(this)@.union(result@) == old(this)@),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (final(this)@.intersect(result@).len() == 0),
        (obeys_cmp::<T>() && Q::obeys_cmp_spec()) ==> (final(this)@.len() + result@.len() == old(this)@.len()),
;

// 037_BTreeSet_inherent_extract_if_2098: alloc::collections::btree_set::BTreeSet::<T, A>::extract_if::<F, R>
// Source: alloc/src/collections/btree/set.rs:1218-1226
// Principal behavior: initial construction preserves the set and records exactly the ascending in-range candidates; normal steps scan callbacks in candidate order and remove only the first accepted candidate; partial drop retains every rejected and unvisited candidate; a panicking candidate is retained.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone, F, R>[ BTreeSet::<T, A>::extract_if::<F, R> ](
    this: &mut BTreeSet<T, A>,
    range: R,
    pred: F
) -> (result: ExtractIf<'_, T, R, F, A>) where T: core::cmp::Ord, R: core::ops::RangeBounds<T>, F: core::ops::FnMut(&T) -> bool
    requires
        T::obeys_cmp_spec() ==> range_order_law(btree_set_sequence(*this), &range),
    ensures
        (obeys_cmp::<T>()) ==> (range_bounds_law(&range)),
        (obeys_cmp::<T>()) ==> (final(this)@ == old(this)@),
        (obeys_cmp::<T>()) ==> (extract_if_set(result) == old(this)@),
        (obeys_cmp::<T>()) ==> (extract_if_pending(result) == range_sequence(btree_set_sequence(*old(this)), &range)),
        (obeys_cmp::<T>()) ==> (extract_if_decisions(result).len() == extract_if_pending(result).len()),
        (obeys_cmp::<T>()) ==> (extract_if_callback_count(result) == 0),
        (obeys_cmp::<T>()) ==> (extract_if_predicate_state(result) == pred),
        (obeys_cmp::<T>()) ==> (extract_if_remaining(result) == retain_selected(extract_if_pending(result), extract_if_decisions(result))),
        (obeys_cmp::<T>()) ==> (increasing_seq(extract_if_pending(result))),
        (obeys_cmp::<T>()) ==> (extract_if_initial_set(result) == old(this)@),
        (obeys_cmp::<T>()) ==> (extract_if_yielded(result) == Seq::empty()),
        (obeys_cmp::<T>()) ==> (extract_if_drop_law(result)),
        (obeys_cmp::<T>()) ==> (extract_if_panic_law(result)),
;

// 041_BTreeSet_FromIterator_from_iter_2138: <alloc::collections::btree_set::BTreeSet<T> as core::iter::FromIterator<T>>::from_iter::<I>
// Source: alloc/src/collections/btree/set.rs:1471-1481
// Principal behavior: result contains every input comparator class exactly once; stable sorting and DedupSortedIter retain the last comparator-equal input.
pub assume_specification<T: core::cmp::Ord, I: core::iter::IntoIterator<Item = T>>[ <BTreeSet<T> as core::iter::FromIterator<T>>::from_iter::<I> ](
    iter: I
) -> (result: BTreeSet<T>)
    ensures
        (obeys_cmp::<T>()) ==> (stable_sorted_sequence(into_iterator_sequence::<T, I>(&iter)).len() == into_iterator_sequence::<T, I>(&iter).len()),
        (obeys_cmp::<T>()) ==> (stable_sorted_sequence(into_iterator_sequence::<T, I>(&iter)).to_multiset() == into_iterator_sequence::<T, I>(&iter).to_multiset()),
        (obeys_cmp::<T>()) ==> (nondecreasing_sequence(stable_sorted_sequence(into_iterator_sequence::<T, I>(&iter)))),
        (obeys_cmp::<T>()) ==> (stable_tie_order(into_iterator_sequence::<T, I>(&iter), stable_sorted_sequence(into_iterator_sequence::<T, I>(&iter)))),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == dedup_last_sorted(stable_sorted_sequence(into_iterator_sequence::<T, I>(&iter)))),
        (obeys_cmp::<T>()) ==> (result@ == into_iterator_sequence::<T, I>(&iter).to_set()),
;

// 042_BTreeSet_From_from_2140: <alloc::collections::btree_set::BTreeSet<T> as core::convert::From<[T; N]>>::from
// Source: alloc/src/collections/btree/set.rs:1508-1516
// Principal behavior: result contains every input comparator class exactly once; stable sorting and DedupSortedIter retain the last comparator-equal input.
pub assume_specification<T: core::cmp::Ord, const N: usize>[ <BTreeSet<T> as core::convert::From<[T; N]>>::from ](
    arr: [T; N]
) -> (result: BTreeSet<T>)
    ensures
        (obeys_cmp::<T>()) ==> (stable_sorted_sequence(arr@).len() == arr@.len()),
        (obeys_cmp::<T>()) ==> (stable_sorted_sequence(arr@).to_multiset() == arr@.to_multiset()),
        (obeys_cmp::<T>()) ==> (nondecreasing_sequence(stable_sorted_sequence(arr@))),
        (obeys_cmp::<T>()) ==> (stable_tie_order(arr@, stable_sorted_sequence(arr@))),
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == dedup_last_sorted(stable_sorted_sequence(arr@))),
        (obeys_cmp::<T>()) ==> (result@ == arr@.to_set()),
;

// 043_BTreeSet_IntoIterator_into_iter_2065: <alloc::collections::btree_set::BTreeSet<T, A> as core::iter::IntoIterator>::into_iter
// Source: alloc/src/collections/btree/set.rs:1536-1538
// Principal behavior: the iterator observes exactly the source set; items are yielded in strictly ascending order without duplicates.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::iter::IntoIterator>::into_iter ](
    this: BTreeSet<T, A>
) -> (result: IntoIter<T, A>)
    ensures
        into_iter_remaining(result).to_set() == this@,
        into_iter_remaining(result) == btree_set_sequence(this),
        increasing_seq(btree_set_sequence(this)),
;

// 044_BTreeSet_IntoIterator_into_iter_2148: <&'a alloc::collections::btree_set::BTreeSet<T, A> as core::iter::IntoIterator>::into_iter
// Source: alloc/src/collections/btree/set.rs:1546-1548
// Principal behavior: the iterator observes exactly the source set; items are yielded in strictly ascending order without duplicates.
pub assume_specification<'a, T, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'a BTreeSet<T, A> as core::iter::IntoIterator>::into_iter ](
    this: &'a BTreeSet<T, A>
) -> (result: Iter<'a, T>)
    ensures
        iter_remaining(result).unref().to_set() == this@,
        iter_remaining(result).unref() == btree_set_sequence(*this),
        increasing_seq(btree_set_sequence(*this)),
;

// 045_ExtractIf_Debug_fmt_2406: <ExtractIf<'a, T, R, F, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:1576-1580
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<'a, T, R, F, A>[ <ExtractIf<'a, T, R, F, A> as core::fmt::Debug>::fmt ](
    this: &ExtractIf<'a, T, R, F, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result) where T: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone
    ensures
        *final(f) == apply_debug_shape(*old(f), extract_if_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), extract_if_debug_shape(*this)).1,
        extract_if_debug_shape_law(*this),
;

// 046_ExtractIf_Iterator_next_2409: <ExtractIf<'a, T, R, F, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:1592-1596
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T, R, F, A: alloc::alloc::Allocator + core::clone::Clone>[ <ExtractIf<'a, T, R, F, A> as core::iter::Iterator>::next ](
    this: &mut ExtractIf<'a, T, R, F, A>
) -> (result: Option<T>) where T: core::cmp::PartialOrd, R: core::ops::RangeBounds<T>, F: core::ops::FnMut(&T) -> bool
    requires
        retain_callback_trace_law(extract_if_predicate_state(*this), extract_if_pending(*this)),
    ensures
        (T::obeys_partial_cmp_spec()) ==> (extract_if_decisions(*old(this)).len() == extract_if_pending(*old(this)).len()),
        (T::obeys_partial_cmp_spec()) ==> (result == if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { Some(extract_if_pending(*old(this))[first_true(extract_if_decisions(*old(this)))]) } else { None }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_pending(*final(this)) == if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { extract_if_pending(*old(this)).subrange(first_true(extract_if_decisions(*old(this))) + 1, extract_if_pending(*old(this)).len() as int) } else { Seq::empty() }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_set(*final(this)) == if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { extract_if_set(*old(this)).remove(extract_if_pending(*old(this))[first_true(extract_if_decisions(*old(this)))]) } else { extract_if_set(*old(this)) }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_callback_count(*final(this)) == extract_if_callback_count(*old(this)) + if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { (first_true(extract_if_decisions(*old(this))) + 1) as nat } else { extract_if_pending(*old(this)).len() as nat }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_predicate_state(*final(this)) == retain_callback_state_after(extract_if_predicate_state(*old(this)), extract_if_pending(*old(this)), if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { (first_true(extract_if_decisions(*old(this))) + 1) as nat } else { extract_if_pending(*old(this)).len() as nat })),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_initial_set(*final(this)) == extract_if_initial_set(*old(this))),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_yielded(*final(this)) == if first_true(extract_if_decisions(*old(this))) < extract_if_pending(*old(this)).len() { extract_if_yielded(*old(this)).push(extract_if_pending(*old(this))[first_true(extract_if_decisions(*old(this)))]) } else { extract_if_yielded(*old(this)) }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_remaining(*final(this)) == if result.is_some() { extract_if_remaining(*old(this)).drop_first() } else { extract_if_remaining(*old(this)) }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_drop_law(*final(this))),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_panic_law(*final(this))),
;

// 047_ExtractIf_Iterator_size_hint_2410: <ExtractIf<'a, T, R, F, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:1598-1600
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T, R, F, A: alloc::alloc::Allocator + core::clone::Clone>[ <ExtractIf<'a, T, R, F, A> as core::iter::Iterator>::size_hint ](
    this: &ExtractIf<'a, T, R, F, A>
) -> (result: (usize, Option<usize>)) where T: core::cmp::PartialOrd, R: core::ops::RangeBounds<T>, F: core::ops::FnMut(&T) -> bool
    ensures
        (T::obeys_partial_cmp_spec()) ==> (result.0 == 0),
        (T::obeys_partial_cmp_spec()) ==> (match result.1 { Some(upper) => upper as nat == extract_if_length_bound(this), None => false }),
        (T::obeys_partial_cmp_spec()) ==> (extract_if_remaining(*this).len() <= extract_if_length_bound(this)),
;

// 048_BTreeSet_Extend_extend_2150: <alloc::collections::btree_set::BTreeSet<T, A> as core::iter::Extend<T>>::extend::<Iter>
// Source: alloc/src/collections/btree/set.rs:1615-1619
// Principal behavior: input items are processed in iterator order; new comparator classes are inserted while existing representatives are retained.
pub assume_specification<T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone, Iter: core::iter::IntoIterator<Item = T>>[ <BTreeSet<T, A> as core::iter::Extend<T>>::extend::<Iter> ](
    this: &mut BTreeSet<T, A>,
    iter: Iter
)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == extend_sequence(btree_set_sequence(*old(this)), into_iterator_sequence::<T, Iter>(&iter))),
        (obeys_cmp::<T>()) ==> (final(this)@ == extend_sequence(btree_set_sequence(*old(this)), into_iterator_sequence::<T, Iter>(&iter)).to_set()),
        (obeys_cmp::<T>()) ==> (increasing_seq(btree_set_sequence(*final(this)))),
;

// 049_BTreeSet_Extend_extend_2153: <alloc::collections::btree_set::BTreeSet<T, A> as core::iter::Extend<&'a T>>::extend::<I>
// Source: alloc/src/collections/btree/set.rs:1629-1631
// Principal behavior: input items are processed in iterator order; new comparator classes are inserted while existing representatives are retained.
pub assume_specification<'a, T: 'a + core::cmp::Ord + core::marker::Copy, A: alloc::alloc::Allocator + core::clone::Clone, I: core::iter::IntoIterator<Item = &'a T>>[ <BTreeSet<T, A> as core::iter::Extend<&'a T>>::extend::<I> ](
    this: &mut BTreeSet<T, A>,
    iter: I
)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(*final(this)) == extend_sequence(btree_set_sequence(*old(this)), into_iterator_sequence::<&'a T, I>(&iter).unref())),
        (obeys_cmp::<T>()) ==> (final(this)@ == extend_sequence(btree_set_sequence(*old(this)), into_iterator_sequence::<&'a T, I>(&iter).unref()).to_set()),
        (obeys_cmp::<T>()) ==> (increasing_seq(btree_set_sequence(*final(this)))),
;

// 051_BTreeSet_Sub_sub_2159: <&'b alloc::collections::btree_set::BTreeSet<T, A> as core::ops::Sub<&'a BTreeSet<T, A>>>::sub
// Source: alloc/src/collections/btree/set.rs:1664-1669
// Principal behavior: result membership is the selected set operation; representatives follow the source adapter and stable sorted-build path.
pub assume_specification<'a, 'b, T: core::cmp::Ord + core::clone::Clone, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'b BTreeSet<T, A> as core::ops::Sub<&'a BTreeSet<T, A>>>::sub ](
    this: &'b BTreeSet<T, A>,
    rhs: &BTreeSet<T, A>
) -> (result: BTreeSet<T, A>)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == clone_sequence(difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
        (obeys_cmp::<T>()) ==> (clone_sequence_preserves_values(difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs))) ==> (result@ == this@.difference(rhs@))),
        (obeys_cmp::<T>()) ==> (increasing_seq(difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
;

// 052_BTreeSet_BitXor_bitxor_2163: <&'b alloc::collections::btree_set::BTreeSet<T, A> as core::ops::BitXor<&'a BTreeSet<T, A>>>::bitxor
// Source: alloc/src/collections/btree/set.rs:1689-1694
// Principal behavior: result membership is the selected set operation; representatives follow the source adapter and stable sorted-build path.
pub assume_specification<'a, 'b, T: core::cmp::Ord + core::clone::Clone, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'b BTreeSet<T, A> as core::ops::BitXor<&'a BTreeSet<T, A>>>::bitxor ](
    this: &'b BTreeSet<T, A>,
    rhs: &BTreeSet<T, A>
) -> (result: BTreeSet<T, A>)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == clone_sequence(symmetric_difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
        (obeys_cmp::<T>()) ==> (clone_sequence_preserves_values(symmetric_difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs))) ==> (result@ == this@.union(rhs@).difference(this@.intersect(rhs@)))),
        (obeys_cmp::<T>()) ==> (increasing_seq(symmetric_difference_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
;

// 053_BTreeSet_BitAnd_bitand_2167: <&'b alloc::collections::btree_set::BTreeSet<T, A> as core::ops::BitAnd<&'a BTreeSet<T, A>>>::bitand
// Source: alloc/src/collections/btree/set.rs:1714-1719
// Principal behavior: result membership is the selected set operation; representatives follow the source adapter and stable sorted-build path.
pub assume_specification<'a, 'b, T: core::cmp::Ord + core::clone::Clone, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'b BTreeSet<T, A> as core::ops::BitAnd<&'a BTreeSet<T, A>>>::bitand ](
    this: &'b BTreeSet<T, A>,
    rhs: &BTreeSet<T, A>
) -> (result: BTreeSet<T, A>)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == clone_sequence(intersection_source_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
        (obeys_cmp::<T>()) ==> (clone_sequence_preserves_values(intersection_source_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs))) ==> (result@ == this@.intersect(rhs@))),
        (obeys_cmp::<T>()) ==> (increasing_seq(intersection_source_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
;

// 054_BTreeSet_BitOr_bitor_2171: <&'b alloc::collections::btree_set::BTreeSet<T, A> as core::ops::BitOr<&'a BTreeSet<T, A>>>::bitor
// Source: alloc/src/collections/btree/set.rs:1739-1744
// Principal behavior: result membership is the selected set operation; representatives follow the source adapter and stable sorted-build path.
pub assume_specification<'a, 'b, T: core::cmp::Ord + core::clone::Clone, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'b BTreeSet<T, A> as core::ops::BitOr<&'a BTreeSet<T, A>>>::bitor ](
    this: &'b BTreeSet<T, A>,
    rhs: &BTreeSet<T, A>
) -> (result: BTreeSet<T, A>)
    ensures
        (obeys_cmp::<T>()) ==> (btree_set_sequence(result) == clone_sequence(union_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
        (obeys_cmp::<T>()) ==> (clone_sequence_preserves_values(union_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs))) ==> (result@ == this@.union(rhs@))),
        (obeys_cmp::<T>()) ==> (increasing_seq(union_sequence(btree_set_sequence(*this), btree_set_sequence(*rhs)))),
;

// 055_BTreeSet_Debug_fmt_2174: <alloc::collections::btree_set::BTreeSet<T, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/set.rs:1749-1751
// Principal behavior: the source-specific debug builder tag and ordered entries determine formatter state and result.
pub assume_specification<T: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeSet<T, A> as core::fmt::Debug>::fmt ](
    this: &BTreeSet<T, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        *final(f) == apply_debug_shape(*old(f), btree_set_debug_shape(*this)).0,
        result == apply_debug_shape(*old(f), btree_set_debug_shape(*this)).1,
        btree_set_debug_shape_law(*this),
        btree_set_sequence(*this).to_set() == this@,
        increasing_seq(btree_set_sequence(*this)),
;

// 056_Iter_Clone_clone_2196: <Iter<'a, T> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:1756-1758
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::clone::Clone>::clone ](
    this: &Iter<'a, T>
) -> (result: Iter<'a, T>)
    ensures
        iter_remaining(result) == iter_remaining(*this),
;

// 057_Iter_Iterator_next_2199: <Iter<'a, T> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:1765-1767
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::Iterator>::next ](
    this: &mut Iter<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if iter_remaining(*old(this)).len() > 0 { Some(iter_remaining(*old(this))[0]) } else { None },
        iter_remaining(*final(this)) == if iter_remaining(*old(this)).len() > 0 { iter_remaining(*old(this)).drop_first() } else { iter_remaining(*old(this)) },
;

// 058_Iter_Iterator_size_hint_2200: <Iter<'a, T> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:1769-1771
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::Iterator>::size_hint ](
    this: &Iter<'a, T>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == iter_remaining(*this).len(),
        result.1 == Some(result.0),
;

// 059_Iter_Iterator_last_2201: <Iter<'a, T> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/set.rs:1773-1775
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::Iterator>::last ](
    this: Iter<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if iter_remaining(this).len() > 0 { Some(iter_remaining(this).last()) } else { None },
;

// 060_Iter_Iterator_min_2202: <Iter<'a, T> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:1777-1782
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::Iterator>::min ](
    this: Iter<'a, T>
) -> (result: Option<&'a T>) where &'a T: core::cmp::Ord
    ensures
        (obeys_cmp::<&'a T>()) ==> (result == if iter_remaining(this).len() > 0 { Some(iter_remaining(this)[0]) } else { None }),
;

// 061_Iter_Iterator_max_2203: <Iter<'a, T> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/set.rs:1784-1789
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::Iterator>::max ](
    this: Iter<'a, T>
) -> (result: Option<&'a T>) where &'a T: core::cmp::Ord
    ensures
        (obeys_cmp::<&'a T>()) ==> (result == if iter_remaining(this).len() > 0 { Some(iter_remaining(this).last()) } else { None }),
;

// 062_Iter_DoubleEndedIterator_next_back_2205: <Iter<'a, T> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/set.rs:1794-1796
// Principal behavior: Some removes exactly the last remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Iter<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if iter_remaining(*old(this)).len() > 0 { Some(iter_remaining(*old(this)).last()) } else { None },
        iter_remaining(*final(this)) == if iter_remaining(*old(this)).len() > 0 { iter_remaining(*old(this)).drop_last() } else { iter_remaining(*old(this)) },
;

// 063_Iter_ExactSizeIterator_len_2207: <Iter<'a, T> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/set.rs:1801-1803
// Principal behavior: returned length exactly equals remaining observations.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::iter::ExactSizeIterator>::len ](
    this: &Iter<'a, T>
) -> (result: usize)
    ensures
        result as nat == iter_remaining(*this).len(),
;

// 064_IntoIter_Iterator_next_2232: <IntoIter<T, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:1816-1818
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<T, A> as core::iter::Iterator>::next ](
    this: &mut IntoIter<T, A>
) -> (result: Option<T>)
    ensures
        result == if into_iter_remaining(*old(this)).len() > 0 { Some(into_iter_remaining(*old(this))[0]) } else { None },
        into_iter_remaining(*final(this)) == if into_iter_remaining(*old(this)).len() > 0 { into_iter_remaining(*old(this)).drop_first() } else { into_iter_remaining(*old(this)) },
;

// 065_IntoIter_Iterator_size_hint_2233: <IntoIter<T, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:1820-1822
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<T, A> as core::iter::Iterator>::size_hint ](
    this: &IntoIter<T, A>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == into_iter_remaining(*this).len(),
        result.1 == Some(result.0),
;

// 066_Iter_Default_default_2211: <Iter<'a, T> as core::default::Default>::default
// Source: alloc/src/collections/btree/set.rs:1834-1836
// Principal behavior: the default iterator has no remaining observations.
pub assume_specification<'a, T>[ <Iter<'a, T> as core::default::Default>::default ](

) -> (result: Iter<'a, T>)
    ensures
        iter_remaining(result) == Seq::empty(),
;

// 067_IntoIter_DoubleEndedIterator_next_back_2235: <IntoIter<T, A> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/set.rs:1841-1843
// Principal behavior: Some removes exactly the last remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<T, A> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut IntoIter<T, A>
) -> (result: Option<T>)
    ensures
        result == if into_iter_remaining(*old(this)).len() > 0 { Some(into_iter_remaining(*old(this)).last()) } else { None },
        into_iter_remaining(*final(this)) == if into_iter_remaining(*old(this)).len() > 0 { into_iter_remaining(*old(this)).drop_last() } else { into_iter_remaining(*old(this)) },
;

// 068_IntoIter_ExactSizeIterator_len_2237: <IntoIter<T, A> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/set.rs:1848-1850
// Principal behavior: returned length exactly equals remaining observations.
pub assume_specification<T, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<T, A> as core::iter::ExactSizeIterator>::len ](
    this: &IntoIter<T, A>
) -> (result: usize)
    ensures
        result as nat == into_iter_remaining(*this).len(),
;

// 069_IntoIter_Default_default_2241: <IntoIter<T, A> as core::default::Default>::default
// Source: alloc/src/collections/btree/set.rs:1871-1873
// Principal behavior: the default iterator has no remaining observations.
pub assume_specification<T, A>[ <IntoIter<T, A> as core::default::Default>::default ](

) -> (result: IntoIter<T, A>) where A: alloc::alloc::Allocator + core::default::Default + core::clone::Clone
    ensures
        into_iter_remaining(result) == Seq::empty(),
;

// 070_Range_Clone_clone_2263: <Range<'a, T> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:1878-1880
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T>[ <Range<'a, T> as core::clone::Clone>::clone ](
    this: &Range<'a, T>
) -> (result: Range<'a, T>)
    ensures
        range_remaining(result) == range_remaining(*this),
;

// 071_Range_Iterator_next_2266: <Range<'a, T> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:1887-1889
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Range<'a, T> as core::iter::Iterator>::next ](
    this: &mut Range<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if range_remaining(*old(this)).len() > 0 { Some(range_remaining(*old(this))[0]) } else { None },
        range_remaining(*final(this)) == if range_remaining(*old(this)).len() > 0 { range_remaining(*old(this)).drop_first() } else { range_remaining(*old(this)) },
;

// 072_Range_Iterator_last_2267: <Range<'a, T> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/set.rs:1891-1893
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Range<'a, T> as core::iter::Iterator>::last ](
    this: Range<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if range_remaining(this).len() > 0 { Some(range_remaining(this).last()) } else { None },
;

// 073_Range_Iterator_min_2268: <Range<'a, T> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:1895-1900
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Range<'a, T> as core::iter::Iterator>::min ](
    this: Range<'a, T>
) -> (result: Option<&'a T>) where &'a T: core::cmp::Ord
    ensures
        (obeys_cmp::<&'a T>()) ==> (result == if range_remaining(this).len() > 0 { Some(range_remaining(this)[0]) } else { None }),
;

// 074_Range_Iterator_max_2269: <Range<'a, T> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/set.rs:1902-1907
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Range<'a, T> as core::iter::Iterator>::max ](
    this: Range<'a, T>
) -> (result: Option<&'a T>) where &'a T: core::cmp::Ord
    ensures
        (obeys_cmp::<&'a T>()) ==> (result == if range_remaining(this).len() > 0 { Some(range_remaining(this).last()) } else { None }),
;

// 075_Range_DoubleEndedIterator_next_back_2271: <Range<'a, T> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/set.rs:1912-1914
// Principal behavior: Some removes exactly the last remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T>[ <Range<'a, T> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Range<'a, T>
) -> (result: Option<&'a T>)
    ensures
        result == if range_remaining(*old(this)).len() > 0 { Some(range_remaining(*old(this)).last()) } else { None },
        range_remaining(*final(this)) == if range_remaining(*old(this)).len() > 0 { range_remaining(*old(this)).drop_last() } else { range_remaining(*old(this)) },
;

// 076_Range_Default_default_2274: <Range<'a, T> as core::default::Default>::default
// Source: alloc/src/collections/btree/set.rs:1929-1931
// Principal behavior: the default iterator has no remaining observations.
pub assume_specification<'a, T>[ <Range<'a, T> as core::default::Default>::default ](

) -> (result: Range<'a, T>)
    ensures
        range_remaining(result) == Seq::empty(),
;

// 077_Difference_Clone_clone_2296: <Difference<'a, T, A> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:1936-1949
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T, A: alloc::alloc::Allocator + core::clone::Clone>[ <Difference<'a, T, A> as core::clone::Clone>::clone ](
    this: &Difference<'a, T, A>
) -> (result: Difference<'a, T, A>)
    ensures
        difference_remaining(result) == difference_remaining(*this),
        difference_source_state(result) == difference_source_state(*this),
;

// 078_Difference_Iterator_next_2299: <Difference<'a, T, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:1955-1980
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Difference<'a, T, A> as core::iter::Iterator>::next ](
    this: &mut Difference<'a, T, A>
) -> (result: Option<&'a T>)
    requires
        difference_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result == if difference_remaining(*old(this)).len() > 0 { Some(difference_remaining(*old(this))[0]) } else { None }),
        (obeys_cmp::<T>()) ==> (difference_remaining(*final(this)) == if difference_remaining(*old(this)).len() > 0 { difference_remaining(*old(this)).drop_first() } else { difference_remaining(*old(this)) }),
        (obeys_cmp::<T>()) ==> (difference_source_state(*final(this)) == difference_next_step(difference_source_state(*old(this))).state),
        (obeys_cmp::<T>()) ==> (difference_source_state_law(*final(this))),
;

// 079_Difference_Iterator_size_hint_2300: <Difference<'a, T, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:1982-1991
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Difference<'a, T, A> as core::iter::Iterator>::size_hint ](
    this: &Difference<'a, T, A>
) -> (result: (usize, Option<usize>))
    requires
        difference_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (0 <= difference_hint_variant(this) <= 2),
        (obeys_cmp::<T>()) ==> (difference_hint_variant(this) == 2 ==> difference_hint_lengths(this).1 == 0),
        (obeys_cmp::<T>()) ==> (result.0 as nat == if difference_hint_lengths(this).0 >= difference_hint_lengths(this).1 { difference_hint_lengths(this).0 - difference_hint_lengths(this).1 } else { 0 }),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => upper as nat == difference_hint_lengths(this).0, None => false }),
        (obeys_cmp::<T>()) ==> (result.0 as nat <= difference_remaining(*this).len()),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => difference_remaining(*this).len() <= upper as nat, None => false }),
;

// 080_Difference_Iterator_min_2301: <Difference<'a, T, A> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:1993-1995
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Difference<'a, T, A> as core::iter::Iterator>::min ](
    this: Difference<'a, T, A>
) -> (result: Option<&'a T>)
    ensures
        (obeys_cmp::<T>()) ==> (result == if difference_remaining(this).len() > 0 { Some(difference_remaining(this)[0]) } else { None }),
;

// 081_SymmetricDifference_Clone_clone_2324: <SymmetricDifference<'a, T> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:2003-2005
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T>[ <SymmetricDifference<'a, T> as core::clone::Clone>::clone ](
    this: &SymmetricDifference<'a, T>
) -> (result: SymmetricDifference<'a, T>)
    ensures
        symmetric_difference_remaining(result) == symmetric_difference_remaining(*this),
        symmetric_difference_source_state(result) == symmetric_difference_source_state(*this),
;

// 082_SymmetricDifference_Iterator_next_2327: <SymmetricDifference<'a, T> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:2011-2018
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord>[ <SymmetricDifference<'a, T> as core::iter::Iterator>::next ](
    this: &mut SymmetricDifference<'a, T>
) -> (result: Option<&'a T>)
    requires
        symmetric_difference_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result == if symmetric_difference_remaining(*old(this)).len() > 0 { Some(symmetric_difference_remaining(*old(this))[0]) } else { None }),
        (obeys_cmp::<T>()) ==> (symmetric_difference_remaining(*final(this)) == if symmetric_difference_remaining(*old(this)).len() > 0 { symmetric_difference_remaining(*old(this)).drop_first() } else { symmetric_difference_remaining(*old(this)) }),
        (obeys_cmp::<T>()) ==> (symmetric_difference_source_state(*final(this)) == symmetric_difference_next_step(symmetric_difference_source_state(*old(this))).state),
        (obeys_cmp::<T>()) ==> (symmetric_difference_source_state_law(*final(this))),
;

// 083_SymmetricDifference_Iterator_size_hint_2328: <SymmetricDifference<'a, T> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:2020-2026
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T: core::cmp::Ord>[ <SymmetricDifference<'a, T> as core::iter::Iterator>::size_hint ](
    this: &SymmetricDifference<'a, T>
) -> (result: (usize, Option<usize>))
    requires
        symmetric_difference_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result.0 == 0),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => upper as nat == symmetric_difference_hint_lengths(this).0 + symmetric_difference_hint_lengths(this).1, None => false }),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => symmetric_difference_remaining(*this).len() <= upper as nat, None => false }),
;

// 084_SymmetricDifference_Iterator_min_2329: <SymmetricDifference<'a, T> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:2028-2030
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord>[ <SymmetricDifference<'a, T> as core::iter::Iterator>::min ](
    this: SymmetricDifference<'a, T>
) -> (result: Option<&'a T>)
    ensures
        (obeys_cmp::<T>()) ==> (result == if symmetric_difference_remaining(this).len() > 0 { Some(symmetric_difference_remaining(this)[0]) } else { None }),
;

// 085_Intersection_Clone_clone_2352: <Intersection<'a, T, A> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:2038-2050
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T, A: alloc::alloc::Allocator + core::clone::Clone>[ <Intersection<'a, T, A> as core::clone::Clone>::clone ](
    this: &Intersection<'a, T, A>
) -> (result: Intersection<'a, T, A>)
    ensures
        intersection_remaining(result) == intersection_remaining(*this),
        intersection_source_state(result) == intersection_source_state(*this),
;

// 086_Intersection_Iterator_next_2355: <Intersection<'a, T, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:2056-2077
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Intersection<'a, T, A> as core::iter::Iterator>::next ](
    this: &mut Intersection<'a, T, A>
) -> (result: Option<&'a T>)
    requires
        intersection_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result == if intersection_remaining(*old(this)).len() > 0 { Some(intersection_remaining(*old(this))[0]) } else { None }),
        (obeys_cmp::<T>()) ==> (intersection_remaining(*final(this)) == if intersection_remaining(*old(this)).len() > 0 { intersection_remaining(*old(this)).drop_first() } else { intersection_remaining(*old(this)) }),
        (obeys_cmp::<T>()) ==> (intersection_source_state(*final(this)) == intersection_next_step(intersection_source_state(*old(this))).state),
        (obeys_cmp::<T>()) ==> (intersection_source_state_law(*final(this))),
;

// 087_Intersection_Iterator_size_hint_2356: <Intersection<'a, T, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:2079-2086
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Intersection<'a, T, A> as core::iter::Iterator>::size_hint ](
    this: &Intersection<'a, T, A>
) -> (result: (usize, Option<usize>))
    requires
        intersection_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (0 <= intersection_hint_variant(this) <= 3),
        (obeys_cmp::<T>()) ==> (result.0 as nat == intersection_hint_lower(intersection_hint_variant(this), intersection_hint_lengths(this).0, intersection_hint_lengths(this).1)),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => upper as nat == intersection_hint_upper(intersection_hint_variant(this), intersection_hint_lengths(this).0, intersection_hint_lengths(this).1), None => false }),
        (obeys_cmp::<T>()) ==> (result.0 as nat <= intersection_remaining(*this).len()),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => intersection_remaining(*this).len() <= upper as nat, None => false }),
;

// 088_Intersection_Iterator_min_2357: <Intersection<'a, T, A> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:2088-2090
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <Intersection<'a, T, A> as core::iter::Iterator>::min ](
    this: Intersection<'a, T, A>
) -> (result: Option<&'a T>)
    ensures
        (obeys_cmp::<T>()) ==> (result == if intersection_remaining(this).len() > 0 { Some(intersection_remaining(this)[0]) } else { None }),
;

// 089_Union_Clone_clone_2380: <Union<'a, T> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/set.rs:2098-2100
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, T>[ <Union<'a, T> as core::clone::Clone>::clone ](
    this: &Union<'a, T>
) -> (result: Union<'a, T>)
    ensures
        union_remaining(result) == union_remaining(*this),
        union_source_state(result) == union_source_state(*this),
;

// 090_Union_Iterator_next_2383: <Union<'a, T> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/set.rs:2106-2109
// Principal behavior: Some removes exactly the first remaining ordered observation; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord>[ <Union<'a, T> as core::iter::Iterator>::next ](
    this: &mut Union<'a, T>
) -> (result: Option<&'a T>)
    requires
        union_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result == if union_remaining(*old(this)).len() > 0 { Some(union_remaining(*old(this))[0]) } else { None }),
        (obeys_cmp::<T>()) ==> (union_remaining(*final(this)) == if union_remaining(*old(this)).len() > 0 { union_remaining(*old(this)).drop_first() } else { union_remaining(*old(this)) }),
        (obeys_cmp::<T>()) ==> (union_source_state(*final(this)) == union_next_step(union_source_state(*old(this))).state),
        (obeys_cmp::<T>()) ==> (union_source_state_law(*final(this))),
;

// 091_Union_Iterator_size_hint_2384: <Union<'a, T> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/set.rs:2111-2115
// Principal behavior: the exact Rust source lower and upper formulas are stated for each adapter state variant; the resulting interval contains the exact remaining output length.
pub assume_specification<'a, T: core::cmp::Ord>[ <Union<'a, T> as core::iter::Iterator>::size_hint ](
    this: &Union<'a, T>
) -> (result: (usize, Option<usize>))
    requires
        union_source_state_law(*this),
    ensures
        (obeys_cmp::<T>()) ==> (result.0 as nat == if union_hint_lengths(this).0 >= union_hint_lengths(this).1 { union_hint_lengths(this).0 } else { union_hint_lengths(this).1 }),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => upper as nat == union_hint_lengths(this).0 + union_hint_lengths(this).1, None => false }),
        (obeys_cmp::<T>()) ==> (result.0 as nat <= union_remaining(*this).len()),
        (obeys_cmp::<T>()) ==> (match result.1 { Some(upper) => union_remaining(*this).len() <= upper as nat, None => false }),
;

// 092_Union_Iterator_min_2385: <Union<'a, T> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/set.rs:2117-2119
// Principal behavior: the returned item is the documented first or last ordered endpoint; None is returned exactly when no observation remains.
pub assume_specification<'a, T: core::cmp::Ord>[ <Union<'a, T> as core::iter::Iterator>::min ](
    this: Union<'a, T>
) -> (result: Option<&'a T>)
    ensures
        (obeys_cmp::<T>()) ==> (result == if union_remaining(this).len() > 0 { Some(union_remaining(this)[0]) } else { None }),
;

} // verus!
