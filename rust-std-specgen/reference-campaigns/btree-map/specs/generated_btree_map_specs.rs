// Generated Rust 1.96 BTreeMap specifications; exact vstd rows are referenced only.
#![allow(unused_imports, unused_variables)]
#![feature(allocator_api)]
#![verifier::allow(broadcast_without_trigger)]

include!("btree_map_shared_vocabulary.rs");

verus! {

// 002_Iter_Debug_fmt_1514: <Iter<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:379-381
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug, V: core::fmt::Debug>[ <Iter<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &Iter<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 003_Iter_Default_default_1516: <Iter<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:393-395
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::default::Default>::default ](

) -> (result: Iter<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 004_IterMut_Debug_fmt_1551: <IterMut<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:416-419
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug, V: core::fmt::Debug>[ <IterMut<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &IterMut<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 005_IterMut_Default_default_1553: <IterMut<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:431-433
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K: 'a, V: 'a>[ <IterMut<'a, K, V> as core::default::Default>::default ](

) -> (result: IterMut<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 006_IntoIter_Debug_fmt_1587: <IntoIter<K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:465-467
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<K: core::fmt::Debug, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<K, V, A> as core::fmt::Debug>::fmt ](
    this: &IntoIter<K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 007_IntoIter_Default_default_1589: <IntoIter<K, V, A> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:482-484
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<K, V, A>[ <IntoIter<K, V, A> as core::default::Default>::default ](

) -> (result: IntoIter<K, V, A>) where A: alloc::alloc::Allocator + core::default::Default + core::clone::Clone
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 008_Keys_Debug_fmt_1621: <Keys<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:501-503
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug, V>[ <Keys<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &Keys<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 009_Values_Debug_fmt_1658: <Values<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:520-522
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K, V: core::fmt::Debug>[ <Values<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &Values<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 010_ValuesMut_Debug_fmt_1691: <ValuesMut<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:539-541
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K, V: core::fmt::Debug>[ <ValuesMut<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &ValuesMut<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 011_IntoKeys_Debug_fmt_1722: <IntoKeys<K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:562-564
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<K: core::fmt::Debug, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::fmt::Debug>::fmt ](
    this: &IntoKeys<K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 012_IntoValues_Debug_fmt_1755: <IntoValues<K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:585-587
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<K, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::fmt::Debug>::fmt ](
    this: &IntoValues<K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 013_Range_Debug_fmt_1788: <Range<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:604-606
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug, V: core::fmt::Debug>[ <Range<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &Range<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 014_RangeMut_Debug_fmt_1820: <RangeMut<'a, K, V> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:626-629
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug, V: core::fmt::Debug>[ <RangeMut<'a, K, V> as core::fmt::Debug>::fmt ](
    this: &RangeMut<'a, K, V>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_iterator_debug_result(this, *old(f), result, *final(f)),
;

// 018_BTreeMap_inherent_get_key_value_1392: alloc::collections::btree_map::BTreeMap::<K, V, A>::get_key_value::<Q>
// Source: alloc/src/collections/btree/map.rs:783-793
// Principal behavior: result branch matches key membership or map emptiness; returned key/value belongs to the pre-state map; endpoint result respects comparator order.
pub assume_specification<'s, K, V, A: alloc::alloc::Allocator + core::clone::Clone, Q>[ BTreeMap::<K, V, A>::get_key_value::<Q> ](
    this: &'s BTreeMap<K, V, A>,
    k: &Q
) -> (result: Option<(&'s K, &'s V)>) where K: core::borrow::Borrow<Q> + core::cmp::Ord, Q: core::cmp::Ord + ?Sized
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (match result { Some((stored_key, value)) => borrowed_key_matches(stored_key, k) && *stored_key == borrowed_lookup_stored_key::<K, Q, V>(this@, k) && this@.contains_key(*stored_key) && this@[*stored_key] == *value, None => !contains_borrowed_key(this@, k) }),
;

// 019_BTreeMap_inherent_first_key_value_1393: alloc::collections::btree_map::BTreeMap::<K, V, A>::first_key_value
// Source: alloc/src/collections/btree/map.rs:810-816
// Principal behavior: result branch matches key membership or map emptiness; returned key/value belongs to the pre-state map; endpoint result respects comparator order.
pub assume_specification<'s, K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::first_key_value ](
    this: &'s BTreeMap<K, V, A>
) -> (result: Option<(&'s K, &'s V)>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !this@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some((key, value)) => this@.contains_key(*key) && this@[*key] == *value && ordered_map_first_key(this@, *key), None => true }),
;

// 020_BTreeMap_inherent_first_entry_1394: alloc::collections::btree_map::BTreeMap::<K, V, A>::first_entry
// Source: alloc/src/collections/btree/map.rs:838-851
// Principal behavior: entry branch matches key membership or endpoint availability; handle retains the selected key and mutable map frame.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::first_entry ](
    this: &mut BTreeMap<K, V, A>
) -> (result: Option<OccupiedEntry<'_, K, V, A>>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !old(this)@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some(handle) => ordered_handle_map::<K, V, _>(handle) == old(this)@ && ordered_map_first_key(old(this)@, ordered_handle_key::<K, _>(handle)) && ordered_handle_is_occupied(handle) && final(this)@ == ordered_handle_final_map::<K, V, _>(handle), None => final(this)@ == old(this)@ }),
;

// 021_BTreeMap_inherent_pop_first_1395: alloc::collections::btree_map::BTreeMap::<K, V, A>::pop_first
// Source: alloc/src/collections/btree/map.rs:872-877
// Principal behavior: result branch matches pre-state membership or emptiness; returned key/value is the removed binding; final map removes exactly that comparator-equal key and updates length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::pop_first ](
    this: &mut BTreeMap<K, V, A>
) -> (result: Option<(K, V)>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !old(this)@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some((key, value)) => old(this)@.contains_key(key) && old(this)@[key] == value && ordered_map_first_key(old(this)@, key) && final(this)@ == old(this)@.remove(key), None => final(this)@ == old(this)@ }),
;

// 022_BTreeMap_inherent_last_key_value_1396: alloc::collections::btree_map::BTreeMap::<K, V, A>::last_key_value
// Source: alloc/src/collections/btree/map.rs:893-899
// Principal behavior: result branch matches key membership or map emptiness; returned key/value belongs to the pre-state map; endpoint result respects comparator order.
pub assume_specification<'s, K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::last_key_value ](
    this: &'s BTreeMap<K, V, A>
) -> (result: Option<(&'s K, &'s V)>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !this@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some((key, value)) => this@.contains_key(*key) && this@[*key] == *value && ordered_map_last_key(this@, *key), None => true }),
;

// 023_BTreeMap_inherent_last_entry_1397: alloc::collections::btree_map::BTreeMap::<K, V, A>::last_entry
// Source: alloc/src/collections/btree/map.rs:921-934
// Principal behavior: entry branch matches key membership or endpoint availability; handle retains the selected key and mutable map frame.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::last_entry ](
    this: &mut BTreeMap<K, V, A>
) -> (result: Option<OccupiedEntry<'_, K, V, A>>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !old(this)@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some(handle) => ordered_handle_map::<K, V, _>(handle) == old(this)@ && ordered_map_last_key(old(this)@, ordered_handle_key::<K, _>(handle)) && ordered_handle_is_occupied(handle) && final(this)@ == ordered_handle_final_map::<K, V, _>(handle), None => final(this)@ == old(this)@ }),
;

// 024_BTreeMap_inherent_pop_last_1398: alloc::collections::btree_map::BTreeMap::<K, V, A>::pop_last
// Source: alloc/src/collections/btree/map.rs:955-960
// Principal behavior: result branch matches pre-state membership or emptiness; returned key/value is the removed binding; final map removes exactly that comparator-equal key and updates length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::pop_last ](
    this: &mut BTreeMap<K, V, A>
) -> (result: Option<(K, V)>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (result.is_some() <==> !old(this)@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (match result { Some((key, value)) => old(this)@.contains_key(key) && old(this)@[key] == value && ordered_map_last_key(old(this)@, key) && final(this)@ == old(this)@.remove(key), None => final(this)@ == old(this)@ }),
;

// 026_BTreeMap_inherent_get_mut_1400: alloc::collections::btree_map::BTreeMap::<K, V, A>::get_mut::<Q>
// Source: alloc/src/collections/btree/map.rs:1006-1016
// Principal behavior: result branch matches borrowed-key membership; returned mutable reference frames the selected value into the final map.
pub assume_specification<'s, K, V, A: alloc::alloc::Allocator + core::clone::Clone, Q>[ BTreeMap::<K, V, A>::get_mut::<Q> ](
    this: &'s mut BTreeMap<K, V, A>,
    key: &Q
) -> (result: Option<&'s mut V>) where K: core::borrow::Borrow<Q> + core::cmp::Ord, Q: core::cmp::Ord + ?Sized
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (match result { Some(value) => contains_borrowed_key(old(this)@, key) && maps_borrowed_key_to_value(old(this)@, key, *value) && borrowed_key_value_updated(old(this)@, final(this)@, key, *final(value)) && final(this)@.dom() == old(this)@.dom(), None => !contains_borrowed_key(old(this)@, key) && final(this)@ == old(this)@ }),
;

// 029_BTreeMap_inherent_remove_entry_1403: alloc::collections::btree_map::BTreeMap::<K, V, A>::remove_entry::<Q>
// Source: alloc/src/collections/btree/map.rs:1133-1152
// Principal behavior: result branch matches pre-state membership or emptiness; returned key/value is the removed binding; final map removes exactly that comparator-equal key and updates length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone, Q>[ BTreeMap::<K, V, A>::remove_entry::<Q> ](
    this: &mut BTreeMap<K, V, A>,
    key: &Q
) -> (result: Option<(K, V)>) where K: core::borrow::Borrow<Q> + core::cmp::Ord, Q: core::cmp::Ord + ?Sized
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (match result { Some((stored_key, value)) => borrowed_key_matches(&stored_key, key) && stored_key == borrowed_lookup_stored_key::<K, Q, V>(old(this)@, key) && old(this)@.contains_key(stored_key) && old(this)@[stored_key] == value && maps_borrowed_key_to_value(old(this)@, key, value) && borrowed_key_removed(old(this)@, final(this)@, key), None => !contains_borrowed_key(old(this)@, key) && final(this)@ == old(this)@ }),
;

// 030_BTreeMap_inherent_retain_1404: alloc::collections::btree_map::BTreeMap::<K, V, A>::retain::<F>
// Source: alloc/src/collections/btree/map.rs:1171-1177
// Principal behavior: callback visits keys in ascending order; final domain is a subset of the pre-state domain; kept/removed bindings match callback outcomes including current-item retention.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone, F>[ BTreeMap::<K, V, A>::retain::<F> ](
    this: &mut BTreeMap<K, V, A>,
    f: F
) where K: core::cmp::Ord, F: core::ops::FnMut(&K, &mut V) -> bool
    requires
        ordered_callback_domain(old(this)@, &f),
    ensures
        key_obeys_cmp_spec::<K>() ==> (final(this)@.dom().subset_of(old(this)@.dom())),
        key_obeys_cmp_spec::<K>() ==> (final(this)@.len() <= old(this)@.len()),
        key_obeys_cmp_spec::<K>() ==> (ordered_callback_filter(old(this)@, ordered_map_key_sequence(old(this)@), f, final(this)@)),
        key_obeys_cmp_spec::<K>() ==> (ordered_callback_unwind_contract(old(this)@, ordered_map_key_sequence(old(this)@), &f)),
;

// 031_BTreeMap_inherent_append_1405: alloc::collections::btree_map::BTreeMap::<K, V, A>::append
// Source: alloc/src/collections/btree/map.rs:1215-1222
// Principal behavior: other map is empty afterward; final domain is the union; other value wins comparator-equal conflicts while stored-key identity is retained.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::append ](
    this: &mut BTreeMap<K, V, A>,
    other: &mut BTreeMap<K, V, A>
) where K: core::cmp::Ord, A: core::clone::Clone
    ensures
        key_obeys_cmp_spec::<K>() ==> (final(other)@.is_empty()),
        key_obeys_cmp_spec::<K>() ==> (append_last_value_wins(old(this)@, old(other)@, final(this)@)),
        key_obeys_cmp_spec::<K>() ==> (final(this)@.dom() == old(this)@.dom().union(old(other)@.dom())),
;

// 032_BTreeMap_inherent_range_1407: alloc::collections::btree_map::BTreeMap::<K, V, A>::range::<T, R>
// Source: alloc/src/collections/btree/map.rs:1408-1419
// Principal behavior: normal return requires valid non-panicking bounds; remaining entries are exactly the ascending in-range bindings.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone, T, R>[ BTreeMap::<K, V, A>::range::<T, R> ](
    this: &BTreeMap<K, V, A>,
    range: R
) -> (result: Range<'_, K, V>) where T: core::cmp::Ord + ?Sized, K: core::borrow::Borrow<T> + core::cmp::Ord, R: core::ops::RangeBounds<T>
    requires
        ordered_range_domain::<T, R>(&range),
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> (ordered_range_result::<K, V, T, R, _>(this@, &range, &result)),
;

// 033_BTreeMap_inherent_range_mut_1410: alloc::collections::btree_map::BTreeMap::<K, V, A>::range_mut::<T, R>
// Source: alloc/src/collections/btree/map.rs:1448-1459
// Principal behavior: normal return requires valid non-panicking bounds; remaining entries are exactly the ascending in-range bindings.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone, T, R>[ BTreeMap::<K, V, A>::range_mut::<T, R> ](
    this: &mut BTreeMap<K, V, A>,
    range: R
) -> (result: RangeMut<'_, K, V>) where T: core::cmp::Ord + ?Sized, K: core::borrow::Borrow<T> + core::cmp::Ord, R: core::ops::RangeBounds<T>
    requires
        ordered_range_domain::<T, R>(&range),
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> (ordered_range_result::<K, V, T, R, _>(old(this)@, &range, &result)),
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> (final(this)@.dom() == old(this)@.dom()),
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<T>() ==> (forall|key: K| old(this)@.contains_key(key) && !ordered_key_in_range::<K, T, R>(&range, key) ==> final(this)@[key] == old(this)@[key]),
;

// 034_BTreeMap_inherent_entry_1267: alloc::collections::btree_map::BTreeMap::<K, V, A>::entry
// Source: alloc/src/collections/btree/map.rs:1480-1509
// Principal behavior: entry branch matches key membership or endpoint availability; handle retains the selected key and mutable map frame.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::entry ](
    this: &mut BTreeMap<K, V, A>,
    key: K
) -> (result: Entry<'_, K, V, A>) where K: core::cmp::Ord
    ensures
        key_obeys_cmp_spec::<K>() ==> (ordered_handle_map::<K, V, _>(result) == old(this)@),
        key_obeys_cmp_spec::<K>() ==> (ordered_handle_key::<K, _>(result) == key),
        key_obeys_cmp_spec::<K>() ==> (ordered_handle_is_occupied(result) <==> old(this)@.contains_key(key)),
        key_obeys_cmp_spec::<K>() ==> (final(this)@ == ordered_handle_final_map::<K, V, _>(result)),
;

// 035_BTreeMap_inherent_split_off_1412: alloc::collections::btree_map::BTreeMap::<K, V, A>::split_off::<Q>
// Source: alloc/src/collections/btree/map.rs:1540-1563
// Principal behavior: left and returned maps partition the old bindings at the comparator boundary; partition lengths sum to the old length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone, Q: ?Sized + core::cmp::Ord>[ BTreeMap::<K, V, A>::split_off::<Q> ](
    this: &mut BTreeMap<K, V, A>,
    key: &Q
) -> (result: BTreeMap<K, V, A>) where K: core::borrow::Borrow<Q> + core::cmp::Ord, A: core::clone::Clone
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (final(this)@.len() + result@.len() == old(this)@.len()),
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (ordered_split_partition(old(this)@, key, final(this)@, result@)),
;

// 036_BTreeMap_inherent_extract_if_1413: alloc::collections::btree_map::BTreeMap::<K, V, A>::extract_if::<F, R>
// Source: alloc/src/collections/btree/map.rs:1603-1611
// Principal behavior: callback visits keys in ascending order; final domain is a subset of the pre-state domain; kept/removed bindings match callback outcomes including current-item retention.
pub assume_specification<K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone, F: core::ops::FnMut(&K, &mut V) -> bool, R: core::ops::RangeBounds<K>>[ BTreeMap::<K, V, A>::extract_if::<F, R> ](
    this: &mut BTreeMap<K, V, A>,
    range: R,
    pred: F
) -> (result: ExtractIf<'_, K, V, R, F, A>)
    requires
        ordered_range_domain::<K, R>(&range),
        ordered_callback_domain_for_keys(old(this)@, ordered_range_key_sequence::<K, V, K, R>(old(this)@, &range), &pred),
    ensures
        key_obeys_cmp_spec::<K>() ==> (final(this)@ == old(this)@),
        key_obeys_cmp_spec::<K>() ==> (extract_if_unvisited_keys::<K, V, _>(&result) == ordered_range_key_sequence::<K, V, K, R>(old(this)@, &range)),
        key_obeys_cmp_spec::<K>() ==> (extract_if_visited_keys::<K, V, _>(&result) == Seq::<K>::empty()),
        key_obeys_cmp_spec::<K>() ==> (extract_if_yielded_pairs::<K, V, _>(&result) == Seq::<(K, V)>::empty()),
        key_obeys_cmp_spec::<K>() ==> (extract_if_current_map::<K, V, _>(&result) == old(this)@),
        key_obeys_cmp_spec::<K>() ==> (result.ordered_remaining() == extract_if_removed_pairs(extract_if_model(&result), old(this)@, ordered_range_key_sequence::<K, V, K, R>(old(this)@, &range))),
        key_obeys_cmp_spec::<K>() ==> (ordered_callback_unwind_contract(old(this)@, ordered_range_key_sequence::<K, V, K, R>(old(this)@, &range), &pred)),
        key_obeys_cmp_spec::<K>() ==> (extract_if_lifecycle(old(this)@, &range, pred, &result, final(this)@, Seq::<K>::empty(), ordered_range_key_sequence::<K, V, K, R>(old(this)@, &range))),
;

// 037_BTreeMap_inherent_into_keys_1415: alloc::collections::btree_map::BTreeMap::<K, V, A>::into_keys
// Source: alloc/src/collections/btree/map.rs:1661-1663
// Principal behavior: remaining length equals map length; observable sequence is ascending by key; mutable/owning frame is preserved.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::into_keys ](
    this: BTreeMap<K, V, A>
) -> (result: IntoKeys<K, V, A>)
    ensures
        ordered_iterator_remaining_len(&result) == this@.len(),
        ordered_map_iterator_result(this@, &result),
        owning_iterator_transfer(&this, &result),
;

// 038_BTreeMap_inherent_into_values_1417: alloc::collections::btree_map::BTreeMap::<K, V, A>::into_values
// Source: alloc/src/collections/btree/map.rs:1683-1685
// Principal behavior: remaining length equals map length; observable sequence is ascending by key; mutable/owning frame is preserved.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::into_values ](
    this: BTreeMap<K, V, A>
) -> (result: IntoValues<K, V, A>)
    ensures
        ordered_iterator_remaining_len(&result) == this@.len(),
        ordered_map_iterator_result(this@, &result),
        owning_iterator_transfer(&this, &result),
;

// 039_BTreeMap_IntoIterator_into_iter_1459: <&'a alloc::collections::btree_map::BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter
// Source: alloc/src/collections/btree/map.rs:1705-1707
// Principal behavior: iterator owns or borrows exactly the source map bindings in ascending order.
pub assume_specification<'a, K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'a BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter ](
    this: &'a BTreeMap<K, V, A>
) -> (result: Iter<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == this@.len(),
        ordered_map_iterator_result(this@, &result),
;

// 040_Iter_Iterator_next_1519: <Iter<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:1714-1721
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut Iter<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 041_Iter_Iterator_size_hint_1520: <Iter<'a, K, V> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:1723-1725
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::Iterator>::size_hint ](
    this: &Iter<'a, K, V>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 042_Iter_Iterator_last_1521: <Iter<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:1727-1729
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::Iterator>::last ](
    this: Iter<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 043_Iter_Iterator_min_1522: <Iter<'a, K, V> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:1731-1736
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::Iterator>::min ](
    this: Iter<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>) where (&'a K, &'a V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 044_Iter_Iterator_max_1523: <Iter<'a, K, V> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:1738-1743
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::Iterator>::max ](
    this: Iter<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>) where (&'a K, &'a V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 045_Iter_DoubleEndedIterator_next_back_1526: <Iter<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:1751-1758
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K: 'a, V: 'a>[ <Iter<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Iter<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 046_Iter_ExactSizeIterator_len_1528: <Iter<'a, K, V> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:1763-1765
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<'a, K, V>[ <Iter<'a, K, V> as core::iter::ExactSizeIterator>::len ](
    this: &Iter<'a, K, V>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 047_Iter_Clone_clone_1531: <Iter<'a, K, V> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/map.rs:1773-1775
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, K, V>[ <Iter<'a, K, V> as core::clone::Clone>::clone ](
    this: &Iter<'a, K, V>
) -> (result: Iter<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == ordered_iterator_remaining_len(this),
        ordered_iterator_equivalent(this, &result),
;

// 048_BTreeMap_IntoIterator_into_iter_1463: <&'a mut alloc::collections::btree_map::BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter
// Source: alloc/src/collections/btree/map.rs:1783-1785
// Principal behavior: iterator owns or borrows exactly the source map bindings in ascending order.
pub assume_specification<'a, K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <&'a mut BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter ](
    this: &'a mut BTreeMap<K, V, A>
) -> (result: IterMut<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == old(this)@.len(),
        ordered_map_iterator_result(old(this)@, &result),
;

// 049_IterMut_Iterator_next_1556: <IterMut<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:1792-1799
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut IterMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 050_IterMut_Iterator_size_hint_1557: <IterMut<'a, K, V> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:1801-1803
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::Iterator>::size_hint ](
    this: &IterMut<'a, K, V>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 051_IterMut_Iterator_last_1558: <IterMut<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:1805-1807
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::Iterator>::last ](
    this: IterMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 052_IterMut_Iterator_min_1559: <IterMut<'a, K, V> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:1809-1814
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::Iterator>::min ](
    this: IterMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>) where (&'a K, &'a mut V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 053_IterMut_Iterator_max_1560: <IterMut<'a, K, V> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:1816-1821
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::Iterator>::max ](
    this: IterMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>) where (&'a K, &'a mut V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 054_IterMut_DoubleEndedIterator_next_back_1562: <IterMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:1826-1833
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut IterMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 055_IterMut_ExactSizeIterator_len_1564: <IterMut<'a, K, V> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:1838-1840
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<'a, K, V>[ <IterMut<'a, K, V> as core::iter::ExactSizeIterator>::len ](
    this: &IterMut<'a, K, V>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 056_BTreeMap_IntoIterator_into_iter_1383: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter
// Source: alloc/src/collections/btree/map.rs:1863-1880
// Principal behavior: iterator owns or borrows exactly the source map bindings in ascending order.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeMap<K, V, A> as core::iter::IntoIterator>::into_iter ](
    this: BTreeMap<K, V, A>
) -> (result: IntoIter<K, V, A>)
    ensures
        ordered_iterator_remaining_len(&result) == this@.len(),
        ordered_map_iterator_result(this@, &result),
        owning_iterator_transfer(&this, &result),
;

// 057_IntoIter_Iterator_next_1594: <IntoIter<K, V, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:1942-1945
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<K, V, A> as core::iter::Iterator>::next ](
    this: &mut IntoIter<K, V, A>
) -> (result: Option<(K, V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 058_IntoIter_Iterator_size_hint_1595: <IntoIter<K, V, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:1947-1949
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<K, V, A> as core::iter::Iterator>::size_hint ](
    this: &IntoIter<K, V, A>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 059_IntoIter_DoubleEndedIterator_next_back_1597: <IntoIter<K, V, A> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:1954-1957
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<K, V, A> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut IntoIter<K, V, A>
) -> (result: Option<(K, V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 060_IntoIter_ExactSizeIterator_len_1599: <IntoIter<K, V, A> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:1962-1964
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoIter<K, V, A> as core::iter::ExactSizeIterator>::len ](
    this: &IntoIter<K, V, A>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 061_Keys_Iterator_next_1624: <Keys<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:1977-1979
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut Keys<'a, K, V>
) -> (result: Option<&'a K>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 062_Keys_Iterator_size_hint_1625: <Keys<'a, K, V> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:1981-1983
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::Iterator>::size_hint ](
    this: &Keys<'a, K, V>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 063_Keys_Iterator_last_1626: <Keys<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:1985-1987
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::Iterator>::last ](
    this: Keys<'a, K, V>
) -> (result: Option<&'a K>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 064_Keys_Iterator_min_1627: <Keys<'a, K, V> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:1989-1994
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::Iterator>::min ](
    this: Keys<'a, K, V>
) -> (result: Option<&'a K>) where &'a K: core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 065_Keys_Iterator_max_1628: <Keys<'a, K, V> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:1996-2001
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::Iterator>::max ](
    this: Keys<'a, K, V>
) -> (result: Option<&'a K>) where &'a K: core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 066_Keys_DoubleEndedIterator_next_back_1630: <Keys<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2006-2008
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Keys<'a, K, V>
) -> (result: Option<&'a K>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 067_Keys_ExactSizeIterator_len_1632: <Keys<'a, K, V> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:2013-2015
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::iter::ExactSizeIterator>::len ](
    this: &Keys<'a, K, V>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 068_Keys_Clone_clone_1636: <Keys<'a, K, V> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/map.rs:2026-2028
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::clone::Clone>::clone ](
    this: &Keys<'a, K, V>
) -> (result: Keys<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == ordered_iterator_remaining_len(this),
        ordered_iterator_equivalent(this, &result),
;

// 069_Keys_Default_default_1638: <Keys<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2040-2042
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K, V>[ <Keys<'a, K, V> as core::default::Default>::default ](

) -> (result: Keys<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 070_Values_Iterator_next_1661: <Values<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2049-2051
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut Values<'a, K, V>
) -> (result: Option<&'a V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 071_Values_Iterator_size_hint_1662: <Values<'a, K, V> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:2053-2055
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::iter::Iterator>::size_hint ](
    this: &Values<'a, K, V>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 072_Values_Iterator_last_1663: <Values<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2057-2059
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::iter::Iterator>::last ](
    this: Values<'a, K, V>
) -> (result: Option<&'a V>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 073_Values_DoubleEndedIterator_next_back_1665: <Values<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2064-2066
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Values<'a, K, V>
) -> (result: Option<&'a V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 074_Values_ExactSizeIterator_len_1667: <Values<'a, K, V> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:2071-2073
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::iter::ExactSizeIterator>::len ](
    this: &Values<'a, K, V>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 075_Values_Clone_clone_1671: <Values<'a, K, V> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/map.rs:2084-2086
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::clone::Clone>::clone ](
    this: &Values<'a, K, V>
) -> (result: Values<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == ordered_iterator_remaining_len(this),
        ordered_iterator_equivalent(this, &result),
;

// 076_Values_Default_default_1673: <Values<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2098-2100
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K, V>[ <Values<'a, K, V> as core::default::Default>::default ](

) -> (result: Values<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 077_ExtractIf_Debug_fmt_1851: <ExtractIf<'a, K, V, R, F, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:2147-2149
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K, V, R, F, A>[ <ExtractIf<'a, K, V, R, F, A> as core::fmt::Debug>::fmt ](
    this: &ExtractIf<'a, K, V, R, F, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result) where K: core::fmt::Debug, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone
    ensures
        ordered_debug_result(this, *old(f), result, *final(f)),
;

// 078_ExtractIf_Iterator_next_1854: <ExtractIf<'a, K, V, R, F, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2161-2163
// Principal behavior: predicate visits unvisited keys in ascending order through the first removal; Some yields that removed binding and advances the visited/unvisited partition; None exhausts the unvisited range while retained values stay in the map.
pub assume_specification<'a, K, V, R, F, A: alloc::alloc::Allocator + core::clone::Clone>[ <ExtractIf<'a, K, V, R, F, A> as core::iter::Iterator>::next ](
    this: &mut ExtractIf<'a, K, V, R, F, A>
) -> (result: Option<(K, V)>) where K: core::cmp::PartialOrd, R: core::ops::RangeBounds<K>, F: core::ops::FnMut(&K, &mut V) -> bool
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
        final(this).extract_model() == old(this).extract_model(),
        final(this).extract_visited_keys() == old(this).extract_visited_keys() + old(this).extract_next_consumed_keys(),
        final(this).extract_unvisited_keys() == old(this).extract_unvisited_keys().skip(old(this).extract_next_consumed_keys().len() as int),
        final(this).extract_current_map() == extract_if_visit_map(old(this).extract_model(), old(this).extract_current_map(), old(this).extract_next_consumed_keys()),
        final(this).extract_yielded_pairs() == match result { Some(pair) => old(this).extract_yielded_pairs().push(pair), None => old(this).extract_yielded_pairs() },
        old(this).extract_state_coherent(),
        final(this).extract_state_coherent(),
        match result { Some(_) => final(this).extract_unvisited_keys().len() < old(this).extract_unvisited_keys().len(), None => final(this).extract_unvisited_keys().len() == 0 },
        forall|key: K| final(this).extract_unvisited_keys().contains(key) ==> { &&& final(this).extract_current_map().contains_key(key) &&& final(this).extract_current_map()[key] == old(this).extract_current_map()[key] },
;

// 079_ExtractIf_Iterator_size_hint_1855: <ExtractIf<'a, K, V, R, F, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:2165-2167
// Principal behavior: lower size hint is zero and upper size hint is the live borrowed-map length.
pub assume_specification<'a, K, V, R, F, A: alloc::alloc::Allocator + core::clone::Clone>[ <ExtractIf<'a, K, V, R, F, A> as core::iter::Iterator>::size_hint ](
    this: &ExtractIf<'a, K, V, R, F, A>
) -> (result: (usize, Option<usize>)) where K: core::cmp::PartialOrd, R: core::ops::RangeBounds<K>, F: core::ops::FnMut(&K, &mut V) -> bool
    ensures
        result.0 == 0,
        result.1 == Some(this.extract_current_map().len() as usize),
;

// 080_Range_Iterator_next_1791: <Range<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2239-2241
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut Range<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 081_Range_Iterator_last_1792: <Range<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2243-2245
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::iter::Iterator>::last ](
    this: Range<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 082_Range_Iterator_min_1793: <Range<'a, K, V> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:2247-2252
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::iter::Iterator>::min ](
    this: Range<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>) where (&'a K, &'a V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 083_Range_Iterator_max_1794: <Range<'a, K, V> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:2254-2259
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::iter::Iterator>::max ](
    this: Range<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>) where (&'a K, &'a V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 084_Range_Default_default_1796: <Range<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2271-2273
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::default::Default>::default ](

) -> (result: Range<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 085_RangeMut_Default_default_1822: <RangeMut<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2285-2287
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::default::Default>::default ](

) -> (result: RangeMut<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 086_ValuesMut_Iterator_next_1694: <ValuesMut<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2294-2296
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut ValuesMut<'a, K, V>
) -> (result: Option<&'a mut V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 087_ValuesMut_Iterator_size_hint_1695: <ValuesMut<'a, K, V> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:2298-2300
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::iter::Iterator>::size_hint ](
    this: &ValuesMut<'a, K, V>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 088_ValuesMut_Iterator_last_1696: <ValuesMut<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2302-2304
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::iter::Iterator>::last ](
    this: ValuesMut<'a, K, V>
) -> (result: Option<&'a mut V>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 089_ValuesMut_DoubleEndedIterator_next_back_1698: <ValuesMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2309-2311
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut ValuesMut<'a, K, V>
) -> (result: Option<&'a mut V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 090_ValuesMut_ExactSizeIterator_len_1700: <ValuesMut<'a, K, V> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:2316-2318
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::iter::ExactSizeIterator>::len ](
    this: &ValuesMut<'a, K, V>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 091_ValuesMut_Default_default_1704: <ValuesMut<'a, K, V> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2336-2338
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<'a, K, V>[ <ValuesMut<'a, K, V> as core::default::Default>::default ](

) -> (result: ValuesMut<'a, K, V>)
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 092_IntoKeys_Iterator_next_1725: <IntoKeys<K, V, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2345-2347
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::Iterator>::next ](
    this: &mut IntoKeys<K, V, A>
) -> (result: Option<K>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 093_IntoKeys_Iterator_size_hint_1726: <IntoKeys<K, V, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:2349-2351
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::Iterator>::size_hint ](
    this: &IntoKeys<K, V, A>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 094_IntoKeys_Iterator_last_1727: <IntoKeys<K, V, A> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2353-2355
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::Iterator>::last ](
    this: IntoKeys<K, V, A>
) -> (result: Option<K>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 095_IntoKeys_Iterator_min_1728: <IntoKeys<K, V, A> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:2357-2362
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::Iterator>::min ](
    this: IntoKeys<K, V, A>
) -> (result: Option<K>) where K: core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 096_IntoKeys_Iterator_max_1729: <IntoKeys<K, V, A> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:2364-2369
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::Iterator>::max ](
    this: IntoKeys<K, V, A>
) -> (result: Option<K>) where K: core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 097_IntoKeys_DoubleEndedIterator_next_back_1731: <IntoKeys<K, V, A> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2374-2376
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut IntoKeys<K, V, A>
) -> (result: Option<K>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 098_IntoKeys_ExactSizeIterator_len_1733: <IntoKeys<K, V, A> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:2381-2383
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoKeys<K, V, A> as core::iter::ExactSizeIterator>::len ](
    this: &IntoKeys<K, V, A>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 099_IntoKeys_Default_default_1737: <IntoKeys<K, V, A> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2404-2406
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<K, V, A>[ <IntoKeys<K, V, A> as core::default::Default>::default ](

) -> (result: IntoKeys<K, V, A>) where A: alloc::alloc::Allocator + core::default::Default + core::clone::Clone
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 100_IntoValues_Iterator_next_1758: <IntoValues<K, V, A> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2413-2415
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::iter::Iterator>::next ](
    this: &mut IntoValues<K, V, A>
) -> (result: Option<V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 101_IntoValues_Iterator_size_hint_1759: <IntoValues<K, V, A> as core::iter::Iterator>::size_hint
// Source: alloc/src/collections/btree/map.rs:2417-2419
// Principal behavior: lower and upper size hints exactly equal remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::iter::Iterator>::size_hint ](
    this: &IntoValues<K, V, A>
) -> (result: (usize, Option<usize>))
    ensures
        result.0 as nat == ordered_iterator_remaining_len(this),
        result.1 == Some(result.0),
;

// 102_IntoValues_Iterator_last_1760: <IntoValues<K, V, A> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2421-2423
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::iter::Iterator>::last ](
    this: IntoValues<K, V, A>
) -> (result: Option<V>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 103_IntoValues_DoubleEndedIterator_next_back_1762: <IntoValues<K, V, A> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2428-2430
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut IntoValues<K, V, A>
) -> (result: Option<V>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 104_IntoValues_ExactSizeIterator_len_1764: <IntoValues<K, V, A> as core::iter::ExactSizeIterator>::len
// Source: alloc/src/collections/btree/map.rs:2435-2437
// Principal behavior: returned length exactly equals remaining length.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <IntoValues<K, V, A> as core::iter::ExactSizeIterator>::len ](
    this: &IntoValues<K, V, A>
) -> (result: usize)
    ensures
        result as nat == ordered_iterator_remaining_len(this),
;

// 105_IntoValues_Default_default_1768: <IntoValues<K, V, A> as core::default::Default>::default
// Source: alloc/src/collections/btree/map.rs:2458-2460
// Principal behavior: default iterator has zero remaining items.
pub assume_specification<K, V, A>[ <IntoValues<K, V, A> as core::default::Default>::default ](

) -> (result: IntoValues<K, V, A>) where A: alloc::alloc::Allocator + core::default::Default + core::clone::Clone
    ensures
        result.ordered_remaining() == Seq::<_>::empty(),
;

// 106_Range_DoubleEndedIterator_next_back_1798: <Range<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2465-2467
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut Range<'a, K, V>
) -> (result: Option<(&'a K, &'a V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 107_Range_Clone_clone_1801: <Range<'a, K, V> as core::clone::Clone>::clone
// Source: alloc/src/collections/btree/map.rs:2475-2477
// Principal behavior: clone preserves the complete ordered remaining observation.
pub assume_specification<'a, K, V>[ <Range<'a, K, V> as core::clone::Clone>::clone ](
    this: &Range<'a, K, V>
) -> (result: Range<'a, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == ordered_iterator_remaining_len(this),
        ordered_iterator_equivalent(this, &result),
;

// 108_RangeMut_Iterator_next_1825: <RangeMut<'a, K, V> as core::iter::Iterator>::next
// Source: alloc/src/collections/btree/map.rs:2484-2486
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the first ordered observable item.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::iter::Iterator>::next ](
    this: &mut RangeMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_first() &&& result == Some(old(this).ordered_remaining()[0]) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 109_RangeMut_Iterator_last_1826: <RangeMut<'a, K, V> as core::iter::Iterator>::last
// Source: alloc/src/collections/btree/map.rs:2488-2490
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::iter::Iterator>::last ](
    this: RangeMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 110_RangeMut_Iterator_min_1827: <RangeMut<'a, K, V> as core::iter::Iterator>::min
// Source: alloc/src/collections/btree/map.rs:2492-2497
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::iter::Iterator>::min ](
    this: RangeMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>) where (&'a K, &'a mut V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_front_matches(&this, &item), None => true },
;

// 111_RangeMut_Iterator_max_1828: <RangeMut<'a, K, V> as core::iter::Iterator>::max
// Source: alloc/src/collections/btree/map.rs:2499-2504
// Principal behavior: result presence equals non-empty remaining state; selected item is the documented first or last ordered endpoint.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::iter::Iterator>::max ](
    this: RangeMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>) where (&'a K, &'a mut V): core::cmp::Ord
    ensures
        result.is_some() <==> ordered_iterator_remaining_len(&this) > 0,
        match result { Some(item) => ordered_iterator_back_matches(&this, &item), None => true },
;

// 112_RangeMut_DoubleEndedIterator_next_back_1830: <RangeMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back
// Source: alloc/src/collections/btree/map.rs:2509-2511
// Principal behavior: result presence equals non-empty remaining state; remaining length decreases by exactly one on Some; yielded item is the last ordered observable item.
pub assume_specification<'a, K, V>[ <RangeMut<'a, K, V> as core::iter::DoubleEndedIterator>::next_back ](
    this: &mut RangeMut<'a, K, V>
) -> (result: Option<(&'a K, &'a mut V)>)
    ensures
        if old(this).ordered_remaining().len() > 0 { &&& final(this).ordered_remaining() == old(this).ordered_remaining().drop_last() &&& result == Some(old(this).ordered_remaining().last()) } else { &&& final(this).ordered_remaining() == old(this).ordered_remaining() &&& result.is_none() },
;

// 113_BTreeMap_FromIterator_from_iter_1469: <alloc::collections::btree_map::BTreeMap<K, V> as core::iter::FromIterator<(K, V)>>::from_iter::<T>
// Source: alloc/src/collections/btree/map.rs:2523-2533
// Principal behavior: all input bindings are processed in order; last comparator-equal input wins while stable key identity is retained.
pub assume_specification<K: core::cmp::Ord, V, T: core::iter::IntoIterator<Item = (K, V)>>[ <BTreeMap<K, V> as core::iter::FromIterator<(K, V)>>::from_iter::<T> ](
    iter: T
) -> (result: BTreeMap<K, V>)
    ensures
        key_obeys_cmp_spec::<K>() ==> (from_iterator_last_value_wins(iter, result@)),
        key_obeys_cmp_spec::<K>() ==> (ordered_map_well_formed(result@)),
;

// 114_BTreeMap_Extend_extend_1471: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::iter::Extend<(K, V)>>::extend::<T>
// Source: alloc/src/collections/btree/map.rs:2539-2543
// Principal behavior: all input bindings are processed in order; last comparator-equal input wins while stable key identity is retained.
pub assume_specification<K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone, T: core::iter::IntoIterator<Item = (K, V)>>[ <BTreeMap<K, V, A> as core::iter::Extend<(K, V)>>::extend::<T> ](
    this: &mut BTreeMap<K, V, A>,
    iter: T
)
    ensures
        key_obeys_cmp_spec::<K>() ==> (final(this)@.len() >= old(this)@.len()),
        key_obeys_cmp_spec::<K>() ==> (extend_last_value_wins(old(this)@, iter, final(this)@)),
;

// 116_BTreeMap_Hash_hash_1477: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::hash::Hash>::hash::<H>
// Source: alloc/src/collections/btree/map.rs:2567-2572
// Principal behavior: length prefix and ascending key/value pairs are hashed in source order.
pub assume_specification<K: core::hash::Hash, V: core::hash::Hash, A: alloc::alloc::Allocator + core::clone::Clone, H: core::hash::Hasher>[ <BTreeMap<K, V, A> as core::hash::Hash>::hash::<H> ](
    this: &BTreeMap<K, V, A>,
    state: &mut H
)
    ensures
        ordered_hash_transition(this@, *old(state), *final(state)),
;

// 118_BTreeMap_PartialEq_eq_1481: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::cmp::PartialEq>::eq
// Source: alloc/src/collections/btree/map.rs:2585-2587
// Principal behavior: result equals lexicographic comparison of ascending key/value observations.
pub assume_specification<K: core::cmp::PartialEq, V: core::cmp::PartialEq, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeMap<K, V, A> as core::cmp::PartialEq>::eq ](
    this: &BTreeMap<K, V, A>,
    other: &BTreeMap<K, V, A>
) -> (result: bool)
    ensures
        key_obeys_cmp_spec::<K>() ==> (result == (this@ == other@)),
;

// 119_BTreeMap_PartialOrd_partial_cmp_1484: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::cmp::PartialOrd>::partial_cmp
// Source: alloc/src/collections/btree/map.rs:2596-2598
// Principal behavior: result equals lexicographic comparison of ascending key/value observations.
pub assume_specification<K: core::cmp::PartialOrd, V: core::cmp::PartialOrd, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeMap<K, V, A> as core::cmp::PartialOrd>::partial_cmp ](
    this: &BTreeMap<K, V, A>,
    other: &BTreeMap<K, V, A>
) -> (result: Option<core::cmp::Ordering>)
    ensures
        key_obeys_cmp_spec::<K>() ==> (result == ordered_map_partial_cmp(this@, other@)),
;

// 120_BTreeMap_Ord_cmp_1486: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::cmp::Ord>::cmp
// Source: alloc/src/collections/btree/map.rs:2604-2606
// Principal behavior: result equals lexicographic comparison of ascending key/value observations.
pub assume_specification<K: core::cmp::Ord, V: core::cmp::Ord, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeMap<K, V, A> as core::cmp::Ord>::cmp ](
    this: &BTreeMap<K, V, A>,
    other: &BTreeMap<K, V, A>
) -> (result: core::cmp::Ordering)
    ensures
        key_obeys_cmp_spec::<K>() ==> (result == ordered_map_cmp(this@, other@)),
;

// 121_BTreeMap_Debug_fmt_1488: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map.rs:2611-2613
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<K: core::fmt::Debug, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <BTreeMap<K, V, A> as core::fmt::Debug>::fmt ](
    this: &BTreeMap<K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_map_debug_result(this@, *old(f), result, *final(f)),
;

// 122_BTreeMap_Index_index_1491: <alloc::collections::btree_map::BTreeMap<K, V, A> as core::ops::Index<&'a Q>>::index
// Source: alloc/src/collections/btree/map.rs:2630-2632
// Normal-return membership is inherited through axiom_btree_map_index_req and vstd IndexSpec::index_req.
// Principal behavior: normal return requires borrowed-key membership; returned value is the mapped value.
pub assume_specification<
    '_0,
    K: core::borrow::Borrow<Q> + core::cmp::Ord,
    Q: core::cmp::Ord + ?Sized,
    V,
    A: alloc::alloc::Allocator + core::clone::Clone,
    'receiver,
>[
    <BTreeMap<K, V, A> as core::ops::Index<&Q>>::index
](
    this: &'receiver BTreeMap<K, V, A>,
    key: &Q,
) -> (result: &'receiver V)
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>()
            ==> maps_borrowed_key_to_value(this@, key, *result),
;

// 123_BTreeMap_From_from_1493: <alloc::collections::btree_map::BTreeMap<K, V> as core::convert::From<[(K, V); N]>>::from
// Source: alloc/src/collections/btree/map.rs:2649-2657
// Principal behavior: all input bindings are processed in order; last comparator-equal input wins while stable key identity is retained.
pub assume_specification<K: core::cmp::Ord, V, const N: usize>[ <BTreeMap<K, V> as core::convert::From<[(K, V); N]>>::from ](
    arr: [(K, V); N]
) -> (result: BTreeMap<K, V>)
    ensures
        key_obeys_cmp_spec::<K>() ==> (result@.len() <= N),
        key_obeys_cmp_spec::<K>() ==> (array_last_value_wins(&arr, result@)),
;

// 125_BTreeMap_inherent_iter_mut_1421: alloc::collections::btree_map::BTreeMap::<K, V, A>::iter_mut
// Source: alloc/src/collections/btree/map.rs:2712-2720
// Principal behavior: remaining length equals map length; observable sequence is ascending by key; mutable/owning frame is preserved.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::iter_mut ](
    this: &mut BTreeMap<K, V, A>
) -> (result: IterMut<'_, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == old(this)@.len(),
        ordered_map_mut_iterator_frame(old(this)@, &result, final(this)@),
;

// 128_BTreeMap_inherent_values_mut_1425: alloc::collections::btree_map::BTreeMap::<K, V, A>::values_mut
// Source: alloc/src/collections/btree/map.rs:2780-2782
// Principal behavior: remaining length equals map length; observable sequence is ascending by key; mutable/owning frame is preserved.
pub assume_specification<K, V, A: alloc::alloc::Allocator + core::clone::Clone>[ BTreeMap::<K, V, A>::values_mut ](
    this: &mut BTreeMap<K, V, A>
) -> (result: ValuesMut<'_, K, V>)
    ensures
        ordered_iterator_remaining_len(&result) == old(this)@.len(),
        ordered_map_mut_iterator_frame(old(this)@, &result, final(this)@),
;

// 131_Entry_Debug_fmt_1293: <Entry<'a, K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map/entry.rs:36-41
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug + core::cmp::Ord, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <Entry<'a, K, V, A> as core::fmt::Debug>::fmt ](
    this: &Entry<'a, K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_handle_debug_result::<K, V, _>(this, *old(f), result, *final(f)),
;

// 132_VacantEntry_Debug_fmt_1319: <VacantEntry<'a, K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map/entry.rs:67-69
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug + core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ <VacantEntry<'a, K, V, A> as core::fmt::Debug>::fmt ](
    this: &VacantEntry<'a, K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_handle_debug_result::<K, V, _>(this, *old(f), result, *final(f)),
;

// 133_OccupiedEntry_Debug_fmt_1347: <OccupiedEntry<'a, K, V, A> as core::fmt::Debug>::fmt
// Source: alloc/src/collections/btree/map/entry.rs:93-95
// Principal behavior: formatter observes entries in key order and preserves formatter result/effect.
pub assume_specification<'a, K: core::fmt::Debug + core::cmp::Ord, V: core::fmt::Debug, A: alloc::alloc::Allocator + core::clone::Clone>[ <OccupiedEntry<'a, K, V, A> as core::fmt::Debug>::fmt ](
    this: &OccupiedEntry<'a, K, V, A>,
    f: &mut core::fmt::Formatter<'_>
) -> (result: core::fmt::Result)
    ensures
        ordered_handle_debug_result::<K, V, _>(this, *old(f), result, *final(f)),
;

// 134_Entry_inherent_or_insert_1270: Entry::<'a, K, V, A>::or_insert
// Source: alloc/src/collections/btree/map/entry.rs:161-166
// Principal behavior: occupied branch retains and returns the stored value; vacant branch inserts and returns the supplied value; entry key, map length, and mutable-reference final frame are preserved.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ Entry::<'a, K, V, A>::or_insert ](
    this: Entry<'a, K, V, A>,
    default: V
) -> (result: &'a mut V)
    ensures
        ordered_handle_is_occupied(this) <==> ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), *final(result)),
        *result == if ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) { ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)] } else { default },
;

// 135_Entry_inherent_or_insert_with_1271: Entry::<'a, K, V, A>::or_insert_with::<F>
// Source: alloc/src/collections/btree/map/entry.rs:184-189
// Principal behavior: callback/default is invoked only on its documented entry branch; entry key, map length, and returned-reference frame are preserved.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone, F: core::ops::FnOnce() -> V>[ Entry::<'a, K, V, A>::or_insert_with::<F> ](
    this: Entry<'a, K, V, A>,
    default: F
) -> (result: &'a mut V)
    requires
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> default.requires(()),
    ensures
        ordered_handle_is_occupied(this) <==> ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), *final(result)),
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> *result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> default.ensures((), *result),
;

// 136_Entry_inherent_or_insert_with_key_1272: Entry::<'a, K, V, A>::or_insert_with_key::<F>
// Source: alloc/src/collections/btree/map/entry.rs:212-220
// Principal behavior: callback/default is invoked only on its documented entry branch; entry key, map length, and returned-reference frame are preserved.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone, F: core::ops::FnOnce(&K) -> V>[ Entry::<'a, K, V, A>::or_insert_with_key::<F> ](
    this: Entry<'a, K, V, A>,
    default: F
) -> (result: &'a mut V)
    requires
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> default.requires((&ordered_handle_key::<K, _>(this),)),
    ensures
        ordered_handle_is_occupied(this) <==> ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), *final(result)),
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> *result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> default.ensures((&ordered_handle_key::<K, _>(this),), *result),
;

// 137_Entry_inherent_key_1273: Entry::<'a, K, V, A>::key
// Source: alloc/src/collections/btree/map/entry.rs:233-238
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, 's, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ Entry::<'a, K, V, A>::key ](
    this: &'s Entry<'a, K, V, A>
) -> (result: &'s K)
    ensures
        *result == ordered_handle_key::<K, _>(this),
;

// 138_Entry_inherent_and_modify_1274: Entry::<'a, K, V, A>::and_modify::<F>
// Source: alloc/src/collections/btree/map/entry.rs:261-272
// Principal behavior: callback/default is invoked only on its documented entry branch; entry key, map length, and returned-reference frame are preserved.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone, F>[ Entry::<'a, K, V, A>::and_modify::<F> ](
    this: Entry<'a, K, V, A>,
    f: F
) -> (result: Entry<'a, K, V, A>) where F: core::ops::FnOnce(&mut V)
    requires
        entry_callback_domain(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), &f),
    ensures
        ordered_handle_key::<K, _>(result) == ordered_handle_key::<K, _>(this),
        entry_and_modify_transition(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), f, ordered_handle_map::<K, V, _>(result)),
        ordered_handle_is_occupied(result) <==> ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_final_map::<K, V, _>(result),
;

// 139_Entry_inherent_insert_entry_1275: Entry::<'a, K, V, A>::insert_entry
// Source: alloc/src/collections/btree/map/entry.rs:288-296
// Principal behavior: vacant insertion increases length; occupied insertion replaces only the value; returned handle/reference frames the final map binding.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ Entry::<'a, K, V, A>::insert_entry ](
    this: Entry<'a, K, V, A>,
    value: V
) -> (result: OccupiedEntry<'a, K, V, A>)
    ensures
        ordered_handle_key::<K, _>(result) == ordered_handle_key::<K, _>(this),
        ordered_handle_map::<K, V, _>(result) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), value),
        ordered_handle_is_occupied(result),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_final_map::<K, V, _>(result),
;

// 140_Entry_inherent_or_default_1277: Entry::<'a, K, V, A>::or_default
// Source: alloc/src/collections/btree/map/entry.rs:314-319
// Principal behavior: callback/default is invoked only on its documented entry branch; entry key, map length, and returned-reference frame are preserved.
pub assume_specification<'a, K: core::cmp::Ord, V: core::default::Default, A: alloc::alloc::Allocator + core::clone::Clone>[ Entry::<'a, K, V, A>::or_default ](
    this: Entry<'a, K, V, A>
) -> (result: &'a mut V)
    ensures
        ordered_handle_is_occupied(this) <==> ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), *final(result)),
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> *result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)) ==> V::default.ensures((), *result),
;

// 141_VacantEntry_inherent_key_1300: VacantEntry::<'a, K, V, A>::key
// Source: alloc/src/collections/btree/map/entry.rs:335-337
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, 's, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ VacantEntry::<'a, K, V, A>::key ](
    this: &'s VacantEntry<'a, K, V, A>
) -> (result: &'s K)
    ensures
        *result == ordered_handle_key::<K, _>(this),
;

// 142_VacantEntry_inherent_into_key_1301: VacantEntry::<'a, K, V, A>::into_key
// Source: alloc/src/collections/btree/map/entry.rs:354-356
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ VacantEntry::<'a, K, V, A>::into_key ](
    this: VacantEntry<'a, K, V, A>
) -> (result: K)
    ensures
        result == ordered_handle_key::<K, _>(this),
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this),
;

// 143_VacantEntry_inherent_insert_1302: VacantEntry::<'a, K, V, A>::insert
// Source: alloc/src/collections/btree/map/entry.rs:376-378
// Principal behavior: vacant insertion increases length; occupied insertion replaces only the value; returned handle/reference frames the final map binding.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ VacantEntry::<'a, K, V, A>::insert ](
    this: VacantEntry<'a, K, V, A>,
    value: V
) -> (result: &'a mut V)
    ensures
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        *result == value,
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), *final(result)),
;

// 144_VacantEntry_inherent_insert_entry_1303: VacantEntry::<'a, K, V, A>::insert_entry
// Source: alloc/src/collections/btree/map/entry.rs:398-430
// Principal behavior: vacant insertion increases length; occupied insertion replaces only the value; returned handle/reference frames the final map binding.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ VacantEntry::<'a, K, V, A>::insert_entry ](
    this: VacantEntry<'a, K, V, A>,
    value: V
) -> (result: OccupiedEntry<'a, K, V, A>)
    ensures
        ordered_handle_key::<K, _>(result) == ordered_handle_key::<K, _>(this),
        ordered_handle_map::<K, V, _>(result) == ordered_handle_map::<K, V, _>(this).insert(ordered_handle_key::<K, _>(this), value),
        ordered_handle_is_occupied(result),
        ordered_handle_final_map::<K, V, _>(this) == ordered_handle_final_map::<K, V, _>(result),
        !ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
;

// 145_OccupiedEntry_inherent_key_1325: OccupiedEntry::<'a, K, V, A>::key
// Source: alloc/src/collections/btree/map/entry.rs:447-449
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, 's, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::key ](
    this: &'s OccupiedEntry<'a, K, V, A>
) -> (result: &'s K)
    ensures
        *result == ordered_handle_key::<K, _>(this),
;

// 146_OccupiedEntry_inherent_remove_entry_1326: OccupiedEntry::<'a, K, V, A>::remove_entry
// Source: alloc/src/collections/btree/map/entry.rs:476-478
// Principal behavior: occupied binding is returned and removed exactly once.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::remove_entry ](
    this: OccupiedEntry<'a, K, V, A>
) -> (result: (K, V))
    ensures
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        result.0 == ordered_handle_key::<K, _>(this),
        result.1 == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        entry_remove_transition(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), ordered_handle_final_map::<K, V, _>(this)),
;

// 147_OccupiedEntry_inherent_get_1327: OccupiedEntry::<'a, K, V, A>::get
// Source: alloc/src/collections/btree/map/entry.rs:497-499
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, 's, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::get ](
    this: &'s OccupiedEntry<'a, K, V, A>
) -> (result: &'s V)
    ensures
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        *result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
;

// 148_OccupiedEntry_inherent_get_mut_1329: OccupiedEntry::<'a, K, V, A>::get_mut
// Source: alloc/src/collections/btree/map/entry.rs:528-530
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, 's, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::get_mut ](
    this: &'s mut OccupiedEntry<'a, K, V, A>
) -> (result: &'s mut V)
    ensures
        ordered_handle_map::<K, V, _>(*old(this)).contains_key(ordered_handle_key::<K, _>(*old(this))),
        *result == ordered_handle_map::<K, V, _>(*old(this))[ordered_handle_key::<K, _>(*old(this))],
        entry_mutable_frame(ordered_handle_map::<K, V, _>(*old(this)), ordered_handle_key::<K, _>(*old(this)), *result, *final(result), ordered_handle_map::<K, V, _>(*final(this))),
        ordered_handle_final_map::<K, V, _>(*old(this)) == ordered_handle_final_map::<K, V, _>(*final(this)),
;

// 149_OccupiedEntry_inherent_into_mut_1328: OccupiedEntry::<'a, K, V, A>::into_mut
// Source: alloc/src/collections/btree/map/entry.rs:555-557
// Principal behavior: returned key/value matches the selected entry; mutable return is framed into the final underlying map.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::into_mut ](
    this: OccupiedEntry<'a, K, V, A>
) -> (result: &'a mut V)
    ensures
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        *result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        entry_mutable_frame(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), *result, *final(result), ordered_handle_final_map::<K, V, _>(this)),
;

// 150_OccupiedEntry_inherent_insert_1330: OccupiedEntry::<'a, K, V, A>::insert
// Source: alloc/src/collections/btree/map/entry.rs:578-580
// Principal behavior: vacant insertion increases length; occupied insertion replaces only the value; returned handle/reference frames the final map binding.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::insert ](
    this: &mut OccupiedEntry<'a, K, V, A>,
    value: V
) -> (result: V)
    ensures
        ordered_handle_map::<K, V, _>(*old(this)).contains_key(ordered_handle_key::<K, _>(*old(this))),
        result == ordered_handle_map::<K, V, _>(*old(this))[ordered_handle_key::<K, _>(*old(this))],
        ordered_handle_key::<K, _>(*final(this)) == ordered_handle_key::<K, _>(*old(this)),
        ordered_handle_is_occupied(*final(this)),
        entry_replace_transition(ordered_handle_map::<K, V, _>(*old(this)), ordered_handle_key::<K, _>(*old(this)), value, ordered_handle_map::<K, V, _>(*final(this))),
        ordered_handle_final_map::<K, V, _>(*old(this)) == ordered_handle_final_map::<K, V, _>(*final(this)),
;

// 151_OccupiedEntry_inherent_remove_1331: OccupiedEntry::<'a, K, V, A>::remove
// Source: alloc/src/collections/btree/map/entry.rs:601-603
// Principal behavior: occupied binding is returned and removed exactly once.
pub assume_specification<'a, K: core::cmp::Ord, V, A: alloc::alloc::Allocator + core::clone::Clone>[ OccupiedEntry::<'a, K, V, A>::remove ](
    this: OccupiedEntry<'a, K, V, A>
) -> (result: V)
    ensures
        ordered_handle_map::<K, V, _>(this).contains_key(ordered_handle_key::<K, _>(this)),
        result == ordered_handle_map::<K, V, _>(this)[ordered_handle_key::<K, _>(this)],
        entry_remove_transition(ordered_handle_map::<K, V, _>(this), ordered_handle_key::<K, _>(this), ordered_handle_final_map::<K, V, _>(this)),
;

} // verus!
