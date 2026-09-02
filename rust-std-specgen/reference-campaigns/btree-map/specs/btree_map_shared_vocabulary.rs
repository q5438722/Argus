// Shared ordered-map vocabulary for Rust 1.96 alloc::collections::btree_map.
extern crate alloc;

use alloc::alloc::Allocator;
use alloc::boxed::Box;
use alloc::collections::BTreeMap;
use alloc::collections::btree_map::{
    Entry, ExtractIf, IntoIter, IntoKeys, IntoValues, Iter, IterMut, Keys, OccupiedEntry,
    Range, RangeMut, VacantEntry, Values, ValuesMut,
};
use core::borrow::Borrow;
use core::cmp::Ordering;
use core::fmt::Formatter;
use core::hash::Hasher;
use core::iter::{IntoIterator, Iterator};
use core::ops::{FnMut, Index, RangeBounds};
use vstd::prelude::*;
use vstd::std_specs::btree::{
    borrowed_key_removed, contains_borrowed_key, increasing_seq, key_obeys_cmp_spec,
    maps_borrowed_key_to_value,
};
use vstd::std_specs::cmp::{OrdSpec, PartialOrdSpec};
use vstd::std_specs::iter::{IteratorSpec, IteratorSpecImpl, into_iter_remaining};
use vstd::std_specs::core::IndexSpec;
use vstd::std_specs::range::{RangeBoundsSpec, SpecBound};

verus! {

pub broadcast axiom fn axiom_btree_map_index_req<
    'key,
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
    A: Allocator + Clone,
>(
    map: &BTreeMap<K, V, A>,
    key: &'key Q,
)
    ensures
        key_obeys_cmp_spec::<K>() && key_obeys_cmp_spec::<Q>() ==> (
            <BTreeMap<K, V, A> as IndexSpec<&'key Q>>::index_req(map, &key)
                <==> contains_borrowed_key(map@, key)
        ),
;

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExEntry<'a, K: 'a, V: 'a, A: Allocator + Clone>(Entry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExOccupiedEntry<'a, K, V, A: Allocator + Clone>(OccupiedEntry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExVacantEntry<'a, K, V, A: Allocator + Clone>(VacantEntry<'a, K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExIterMut<'a, K: 'a, V: 'a>(IterMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoIter<K, V, A: Allocator + Clone>(IntoIter<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExValuesMut<'a, K, V>(ValuesMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoKeys<K, V, A: Allocator + Clone>(IntoKeys<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(A)]
pub struct ExIntoValues<K, V, A: Allocator + Clone>(IntoValues<K, V, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExRange<'a, K, V>(Range<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
pub struct ExRangeMut<'a, K: 'a, V: 'a>(RangeMut<'a, K, V>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::accept_recursive_types(K)]
#[verifier::accept_recursive_types(V)]
#[verifier::reject_recursive_types(R)]
#[verifier::reject_recursive_types(F)]
#[verifier::reject_recursive_types(A)]
pub struct ExExtractIf<
    'a,
    K,
    V,
    R,
    F,
    A: Allocator + Clone,
>(ExtractIf<'a, K, V, R, F, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFormatter<'a>(Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExFmtError(core::fmt::Error);

pub trait BTreeMapIteratorModel {
    type Item;
    type Key;
    type Value;
    #[verifier::prophetic]
    spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    spec fn ordered_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn ordered_values(&self) -> Seq<Self::Value>;
}

pub trait ExtractIfIteratorModel {
    type Key;
    type Value;
    spec fn extract_model(&self) -> int;
    spec fn extract_visited_keys(&self) -> Seq<Self::Key>;
    spec fn extract_unvisited_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn extract_yielded_pairs(&self) -> Seq<(Self::Key, Self::Value)>;
    #[verifier::prophetic]
    spec fn extract_current_map(&self) -> Map<Self::Key, Self::Value>;
    #[verifier::prophetic]
    spec fn extract_next_consumed_keys(&self) -> Seq<Self::Key>;
    #[verifier::prophetic]
    spec fn extract_state_coherent(&self) -> bool;
}

impl<'a, K, V> BTreeMapIteratorModel for Iter<'a, K, V> {
    type Item = (&'a K, &'a V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.1,
        )
    }
}

impl<'a, K, V> BTreeMapIteratorModel for Keys<'a, K, V> {
    type Item = &'a K;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, key: &'a K| *key)
    }
    #[verifier::prophetic]
    uninterp spec fn ordered_values(&self) -> Seq<V>;
}

impl<'a, K, V> BTreeMapIteratorModel for Values<'a, K, V> {
    type Item = &'a V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, value: &'a V| *value)
    }
}

pub broadcast axiom fn axiom_iter_ordered_remaining<'a, K, V>(
    iterator: &Iter<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_keys_ordered_remaining<'a, K, V>(
    iterator: &Keys<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_values_ordered_remaining<'a, K, V>(
    iterator: &Values<'a, K, V>,
)
    ensures
        #[trigger] iterator.ordered_remaining() == IteratorSpec::remaining(iterator),
;

pub broadcast axiom fn axiom_spec_btree_map_iter_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_btree_map_iter(map);
            &&& IteratorSpec::remaining(&iterator).no_duplicates()
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
            &&& increasing_seq(IteratorSpec::remaining(&iterator).map_values(
                |pair: (&K, &V)| *pair.0,
            ))
        },
;

pub broadcast axiom fn axiom_spec_btree_map_keys_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_keys_iter(map);
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
        },
;

pub broadcast axiom fn axiom_spec_btree_map_values_properties<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
)
    ensures
        key_obeys_cmp_spec::<K>() ==> {
            let iterator = #[trigger] vstd::std_specs::btree::spec_values_iter(map);
            &&& IteratorSpec::decrease(&iterator) is Some
            &&& IteratorSpec::initial_value_relation(&iterator, &iterator)
            &&& exists|key_seq: Seq<K>| {
                &&& increasing_seq(key_seq)
                &&& key_seq.to_set() == map@.dom()
                &&& key_seq.no_duplicates()
                &&& IteratorSpec::remaining(&iterator) == key_seq.map(
                    |_index: int, key: K| &map@[key],
                )
            }
        },
;

impl<'a, K, V> BTreeMapIteratorModel for IterMut<'a, K, V> {
    type Item = (&'a K, &'a mut V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.1,
        )
    }
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoIter<K, V, A> {
    type Item = (K, V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.0)
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.1)
    }
}

impl<'a, K, V> BTreeMapIteratorModel for ValuesMut<'a, K, V> {
    type Item = &'a mut V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, value: &'a mut V| *value)
    }
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoKeys<K, V, A> {
    type Item = K;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining()
    }
    #[verifier::prophetic]
    uninterp spec fn ordered_values(&self) -> Seq<V>;
}

impl<K, V, A: Allocator + Clone> BTreeMapIteratorModel for IntoValues<K, V, A> {
    type Item = V;
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    uninterp spec fn ordered_keys(&self) -> Seq<K>;
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining()
    }
}

impl<'a, K, V> BTreeMapIteratorModel for Range<'a, K, V> {
    type Item = (&'a K, &'a V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a V)| *item.1,
        )
    }
}

impl<'a, K, V> BTreeMapIteratorModel for RangeMut<'a, K, V> {
    type Item = (&'a K, &'a mut V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.0,
        )
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(
            |_index: int, item: (&'a K, &'a mut V)| *item.1,
        )
    }
}

impl<'a, K, V, R, F, A: Allocator + Clone> BTreeMapIteratorModel
    for ExtractIf<'a, K, V, R, F, A>
where
    K: PartialOrd,
    R: RangeBounds<K>,
    F: FnMut(&K, &mut V) -> bool,
{
    type Item = (K, V);
    type Key = K;
    type Value = V;
    #[verifier::prophetic]
    uninterp spec fn ordered_remaining(&self) -> Seq<Self::Item>;
    #[verifier::prophetic]
    open spec fn ordered_keys(&self) -> Seq<K> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.0)
    }
    #[verifier::prophetic]
    open spec fn ordered_values(&self) -> Seq<V> {
        self.ordered_remaining().map(|_index: int, item: (K, V)| item.1)
    }
}

impl<'a, K, V, R, F, A: Allocator + Clone> ExtractIfIteratorModel
    for ExtractIf<'a, K, V, R, F, A>
where
    K: PartialOrd,
    R: RangeBounds<K>,
    F: FnMut(&K, &mut V) -> bool,
{
    type Key = K;
    type Value = V;
    open spec fn extract_model(&self) -> int {
        extract_if_model(self)
    }
    open spec fn extract_visited_keys(&self) -> Seq<K> {
        extract_if_visited_keys::<K, V, _>(self)
    }
    open spec fn extract_unvisited_keys(&self) -> Seq<K> {
        extract_if_unvisited_keys::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_yielded_pairs(&self) -> Seq<(K, V)> {
        extract_if_yielded_pairs::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_current_map(&self) -> Map<K, V> {
        extract_if_current_map::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_next_consumed_keys(&self) -> Seq<K> {
        extract_if_next_consumed_keys::<K, V, _>(self)
    }
    #[verifier::prophetic]
    open spec fn extract_state_coherent(&self) -> bool {
        extract_if_state_coherent::<K, V, _>(self)
    }
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_remaining_len<I: BTreeMapIteratorModel>(
    iter: &I,
) -> nat {
    iter.ordered_remaining().len()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_front_matches<I: BTreeMapIteratorModel>(
    iter: &I,
    item: &I::Item,
) -> bool {
    iter.ordered_remaining().len() > 0 && *item == iter.ordered_remaining()[0]
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_back_matches<I: BTreeMapIteratorModel>(
    iter: &I,
    item: &I::Item,
) -> bool {
    iter.ordered_remaining().len() > 0 && *item == iter.ordered_remaining().last()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_equivalent<I: BTreeMapIteratorModel>(
    left: &I,
    right: &I,
) -> bool {
    left.ordered_remaining() == right.ordered_remaining()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_key_trace<
    K,
    I: BTreeMapIteratorModel<Key = K>,
>(
    iterator: &I,
) -> Seq<K> {
    iterator.ordered_keys()
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_value_trace<
    V,
    I: BTreeMapIteratorModel<Value = V>,
>(
    iterator: &I,
) -> Seq<V> {
    iterator.ordered_values()
}

pub uninterp spec fn ordered_map_pairs<K, V>(map: Map<K, V>) -> Seq<(K, V)>;
pub uninterp spec fn ordered_map_key_sequence<K, V>(map: Map<K, V>) -> Seq<K>;

pub broadcast axiom fn axiom_ordered_map_pairs<K, V>(map: Map<K, V>)
    ensures
        ordered_map_pairs(map).len() == map.len(),
        ordered_map_pairs(map).no_duplicates(),
        forall|i: int| 0 <= i < ordered_map_pairs(map).len() ==> {
            let pair = #[trigger] ordered_map_pairs(map)[i];
            map.contains_key(pair.0) && map[pair.0] == pair.1
        },
        forall|key: K| #[trigger] map.contains_key(key) ==> exists|i: int|
            0 <= i < ordered_map_pairs(map).len()
                && ordered_map_pairs(map)[i].0 == key,
        ordered_map_key_sequence(map).len() == map.len(),
        ordered_map_key_sequence(map).to_set() == map.dom(),
        forall|i: int| 0 <= i < ordered_map_pairs(map).len() ==>
            #[trigger] ordered_map_pairs(map)[i].0 == ordered_map_key_sequence(map)[i],
        key_obeys_cmp_spec::<K>() ==> increasing_seq(ordered_map_key_sequence(map)),
;

pub broadcast axiom fn axiom_ordered_map_pairs_extensional<K, V>(
    left: Map<K, V>,
    right: Map<K, V>,
)
    ensures
        #![trigger ordered_map_pairs(left), ordered_map_pairs(right)]
        ordered_map_pairs(left) == ordered_map_pairs(right) ==> left == right,
;

pub open spec fn ordered_map_first_key<K, V>(map: Map<K, V>, key: K) -> bool {
    ordered_map_pairs(map).len() > 0 && ordered_map_pairs(map)[0].0 == key
}

pub open spec fn ordered_map_last_key<K, V>(map: Map<K, V>, key: K) -> bool {
    ordered_map_pairs(map).len() > 0 && ordered_map_pairs(map).last().0 == key
}

pub open spec fn ordered_map_well_formed<K, V>(map: Map<K, V>) -> bool {
    ordered_map_pairs(map).len() == map.len()
        && ordered_map_pairs(map).no_duplicates()
}

pub uninterp spec fn borrowed_key_matches<K, Q: ?Sized>(stored: &K, query: &Q) -> bool;
pub uninterp spec fn borrowed_lookup_stored_key<K, Q: ?Sized, V>(
    map: Map<K, V>,
    query: &Q,
) -> K;

pub broadcast axiom fn axiom_borrowed_key_matches<K: Borrow<Q> + Ord, Q: Ord + ?Sized, V>(
    map: Map<K, V>,
    stored: &K,
    query: &Q,
)
    requires
        borrowed_key_matches(stored, query),
        map.contains_key(*stored),
    ensures
        contains_borrowed_key(map, query),
;

pub open spec fn borrowed_lookup_value_functional<
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
>(
    map: Map<K, V>,
    query: &Q,
) -> bool {
    &&& forall|value: V|
        #[trigger] maps_borrowed_key_to_value(map, query, value)
            ==> contains_borrowed_key(map, query)
    &&& forall|left: V, right: V|
        #[trigger] maps_borrowed_key_to_value(map, query, left)
        && #[trigger] maps_borrowed_key_to_value(map, query, right)
            ==> left == right
}

pub open spec fn borrowed_removal_functional<
    K: Borrow<Q> + Ord,
    Q: Ord + ?Sized,
    V,
>(
    map: Map<K, V>,
    query: &Q,
) -> bool {
    &&& borrowed_lookup_value_functional(map, query)
    &&& forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] borrowed_key_removed(map, left, query)
        && #[trigger] borrowed_key_removed(map, right, query)
            ==> left == right
}

pub uninterp spec fn formatter_trace(formatter: Formatter<'_>) -> Seq<int>;
pub uninterp spec fn ordered_debug_trace<T>(subject: &T) -> Seq<int>;
pub uninterp spec fn debug_value_trace<T>(subject: T) -> Seq<int>;
pub uninterp spec fn formatter_failed(formatter: Formatter<'_>) -> bool;
pub uninterp spec fn formatter_failure_after_trace(
    pre_formatter: Formatter<'_>,
    emitted: Seq<int>,
) -> bool;

pub open spec fn debug_result_from_trace(
    emitted: Seq<int>,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    formatter_trace(post_formatter) == formatter_trace(pre_formatter) + emitted
        && formatter_failed(post_formatter)
            == formatter_failure_after_trace(pre_formatter, emitted)
        && (result.is_err() <==> formatter_failed(post_formatter))
}

pub open spec fn ordered_debug_result<T>(
    subject: &T,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        ordered_debug_trace(subject),
        pre_formatter,
        result,
        post_formatter,
    )
}

pub open spec fn ordered_map_debug_trace<K, V>(map: Map<K, V>) -> Seq<int> {
    ordered_map_pairs(map).fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, pair: (K, V)| trace + debug_value_trace(pair),
    )
}

pub open spec fn ordered_map_debug_result<K, V>(
    map: Map<K, V>,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        ordered_map_debug_trace(map),
        pre_formatter,
        result,
        post_formatter,
    )
}

#[verifier::prophetic]
pub open spec fn ordered_iterator_debug_result<I: BTreeMapIteratorModel>(
    iterator: &I,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        iterator.ordered_remaining().fold_left(
            Seq::<int>::empty(),
            |trace: Seq<int>, item: I::Item| trace + debug_value_trace(item),
        ),
        pre_formatter,
        result,
        post_formatter,
    )
}

pub open spec fn ordered_handle_debug_result<K, V, H>(
    handle: &H,
    pre_formatter: Formatter<'_>,
    result: core::fmt::Result,
    post_formatter: Formatter<'_>,
) -> bool {
    debug_result_from_trace(
        debug_value_trace(ordered_handle_key::<K, _>(handle))
            + ordered_map_debug_trace(ordered_handle_map::<K, V, _>(handle)),
        pre_formatter,
        result,
        post_formatter,
    )
}
pub uninterp spec fn ordered_handle_map<K, V, H>(handle: H) -> Map<K, V>;
pub uninterp spec fn ordered_handle_final_map<K, V, H>(handle: H) -> Map<K, V>;
pub uninterp spec fn ordered_handle_key<K, H>(handle: H) -> K;
pub uninterp spec fn ordered_handle_is_occupied<H>(handle: H) -> bool;

pub broadcast axiom fn axiom_ordered_handle_reference_coherence<K, V, H>(
    handle: &H,
)
    ensures
        ordered_handle_map::<K, V, H>(*handle)
            == ordered_handle_map::<K, V, &H>(handle),
        ordered_handle_final_map::<K, V, H>(*handle)
            == ordered_handle_final_map::<K, V, &H>(handle),
        ordered_handle_key::<K, H>(*handle)
            == ordered_handle_key::<K, &H>(handle),
        ordered_handle_is_occupied::<H>(*handle)
            == ordered_handle_is_occupied::<&H>(handle),
;

pub broadcast axiom fn axiom_ordered_handle_occupancy_coherent<K, V, H>(
    handle: H,
)
    ensures
        #![trigger
            ordered_handle_is_occupied(handle),
            ordered_handle_map::<K, V, H>(handle),
            ordered_handle_key::<K, H>(handle)
        ]
        ordered_handle_is_occupied(handle)
            <==> ordered_handle_map::<K, V, H>(handle).contains_key(
                ordered_handle_key::<K, H>(handle),
            ),
;

pub uninterp spec fn borrowed_key_value_updated<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    post: Map<K, V>,
    key: &Q,
    value: V,
) -> bool;

pub broadcast axiom fn axiom_borrowed_key_value_updated_direct<Q, V>(
    pre: Map<Q, V>,
    post: Map<Q, V>,
    key: &Q,
    value: V,
)
    ensures
        #[trigger] borrowed_key_value_updated(pre, post, key, value)
            <==> post == pre.insert(*key, value),
;

pub broadcast axiom fn axiom_borrowed_key_value_updated_box<Q, V>(
    pre: Map<Box<Q>, V>,
    post: Map<Box<Q>, V>,
    key: &Q,
    value: V,
)
    ensures
        #[trigger] borrowed_key_value_updated(pre, post, key, value)
            <==> post == pre.insert(Box::new(*key), value),
;

pub open spec fn ordered_callback_domain<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    callback: &F,
) -> bool {
    forall|key_ref: &K, value_ref: &mut V|
        pre.contains_key(*key_ref) && *value_ref == pre[*key_ref]
            ==> #[trigger] callback.requires((key_ref, value_ref))
}

#[verifier::prophetic]
pub open spec fn ordered_callback_domain_for_keys<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: &F,
) -> bool {
    forall|key_ref: &K, value_ref: &mut V|
        pre.contains_key(*key_ref)
            && keys.contains(*key_ref)
            && *value_ref == pre[*key_ref]
            ==> #[trigger] callback.requires((key_ref, value_ref))
}

#[verifier::prophetic]
pub open spec fn ordered_callback_observation<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    state: Map<K, V>,
    callback: F,
    key: K,
    decision: bool,
    final_value: V,
) -> bool {
    exists|key_ref: &K, value_ref: &mut V|
        *key_ref == key
        && *value_ref == state[key]
        && #[trigger] callback.ensures((key_ref, value_ref), decision)
        && *final(value_ref) == final_value
}

#[verifier::no_auto_trigger]
pub uninterp spec fn ordered_callback_filter_trigger<K, V>(
    keep: spec_fn(Map<K, V>, K) -> bool,
    final_value: spec_fn(Map<K, V>, K) -> V,
) -> bool;

#[verifier::prophetic]
pub open spec fn ordered_callback_filter<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: F,
    post: Map<K, V>,
) -> bool {
    exists|
        keep: spec_fn(Map<K, V>, K) -> bool,
        final_value: spec_fn(Map<K, V>, K) -> V,
    |
    #![trigger ordered_callback_filter_trigger(keep, final_value)]
    {
        &&& forall|state: Map<K, V>, key: K|
            state.contains_key(key) && keys.contains(key) ==> {
                ordered_callback_observation(
                    state,
                    callback,
                    key,
                    #[trigger] keep(state, key),
                    #[trigger] final_value(state, key),
                )
            }
        &&& post == keys.fold_left(
            pre,
            |state: Map<K, V>, key: K| {
                if keep(state, key) {
                    state.insert(key, final_value(state, key))
                } else {
                    state.remove(key)
                }
            },
        )
    }
}

#[verifier::prophetic]
pub open spec fn ordered_callback_filter_functional<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: F,
) -> bool {
    forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] ordered_callback_filter(pre, keys, callback, left)
        && #[trigger] ordered_callback_filter(pre, keys, callback, right)
        ==> left == right
}

pub open spec fn callback_unwind_retains_current_and_unvisited<K, V>(
    before_call: Map<K, V>,
    unwound: Map<K, V>,
    current: K,
    unvisited: Seq<K>,
) -> bool {
    &&& unwound.contains_key(current)
    &&& forall|key: K| unvisited.contains(key) ==> {
        &&& unwound.contains_key(key)
        &&& unwound[key] == before_call[key]
    }
}

pub uninterp spec fn ordered_callback_unwind_map<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    callback: &F,
    current: K,
    unvisited: Seq<K>,
) -> Map<K, V>;

#[verifier::prophetic]
pub open spec fn ordered_callback_unwind_contract<
    K,
    V,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    keys: Seq<K>,
    callback: &F,
) -> bool {
    forall|visited: Seq<K>, current: K, unvisited: Seq<K>|
        keys == visited + Seq::empty().push(current) + unvisited ==> {
            callback_unwind_retains_current_and_unvisited(
                pre,
                ordered_callback_unwind_map(pre, callback, current, unvisited),
                current,
                unvisited,
            )
        }
}

pub open spec fn append_last_value_wins<K, V>(
    left: Map<K, V>,
    right: Map<K, V>,
    post: Map<K, V>,
) -> bool {
    &&& post.dom() == left.dom().union(right.dom())
    &&& forall|key: K| #[trigger] right.contains_key(key) ==> post[key] == right[key]
    &&& forall|key: K|
        #![trigger left.contains_key(key)]
        #![trigger right.contains_key(key)]
        left.contains_key(key) && !right.contains_key(key) ==> post[key] == left[key]
}

pub uninterp spec fn borrowed_key_cmp<K, Q: ?Sized>(
    key: K,
    bound: &Q,
) -> Ordering;

pub broadcast axiom fn axiom_borrowed_key_cmp_direct<Q: Ord>(key: Q, bound: &Q)
    ensures
        #[trigger] borrowed_key_cmp::<Q, Q>(key, bound) == key.cmp_spec(bound),
;

pub broadcast axiom fn axiom_borrowed_key_cmp_box<Q: Ord>(key: Box<Q>, bound: &Q)
    ensures
        #[trigger] borrowed_key_cmp::<Box<Q>, Q>(key, bound) == (*key).cmp_spec(bound),
;

pub open spec fn range_start_after_end<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Included(start), SpecBound::Included(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Included(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Excluded(start), SpecBound::Included(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Greater
        },
        _ => false,
    }
}

pub open spec fn range_equal_excluded_bounds<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    match (range.spec_start_bound(), range.spec_end_bound()) {
        (SpecBound::Excluded(start), SpecBound::Excluded(end)) => {
            start.cmp_spec(end) == Ordering::Equal
        },
        _ => false,
    }
}

pub open spec fn ordered_range_domain<
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
) -> bool {
    !range_start_after_end(range) && !range_equal_excluded_bounds(range)
}

pub open spec fn ordered_key_in_range<
    K,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    range: &R,
    key: K,
) -> bool {
    &&& match range.spec_start_bound() {
        SpecBound::Included(start) => borrowed_key_cmp(key, start) != Ordering::Less,
        SpecBound::Excluded(start) => borrowed_key_cmp(key, start) == Ordering::Greater,
        SpecBound::Unbounded => true,
    }
    &&& match range.spec_end_bound() {
        SpecBound::Included(end) => borrowed_key_cmp(key, end) != Ordering::Greater,
        SpecBound::Excluded(end) => borrowed_key_cmp(key, end) == Ordering::Less,
        SpecBound::Unbounded => true,
    }
}

pub open spec fn ordered_range_key_sequence<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    map: Map<K, V>,
    range: &R,
) -> Seq<K> {
    ordered_map_key_sequence(map).filter(
        |key: K| ordered_key_in_range::<K, T, R>(range, key),
    )
}

pub open spec fn ordered_range_pair_sequence<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
>(
    map: Map<K, V>,
    range: &R,
) -> Seq<(K, V)> {
    ordered_map_pairs(map).filter(
        |pair: (K, V)| ordered_key_in_range::<K, T, R>(range, pair.0),
    )
}

#[verifier::prophetic]
pub open spec fn ordered_range_result<
    K,
    V,
    T: Ord + ?Sized,
    R: RangeBoundsSpec<T>,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    map: Map<K, V>,
    range: &R,
    iterator: &I,
) -> bool {
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_range_key_sequence::<K, V, T, R>(map, range)
    &&& iterator.ordered_remaining().len()
        == ordered_range_key_sequence::<K, V, T, R>(map, range).len()
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_range_pair_sequence::<K, V, T, R>(map, range).map(
            |_index: int, pair: (K, V)| pair.1,
        )
}

pub open spec fn ordered_key_before_split<K, Q: ?Sized>(
    boundary: &Q,
    key: K,
) -> bool {
    borrowed_key_cmp(key, boundary) == Ordering::Less
}

pub open spec fn ordered_split_left<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
) -> Map<K, V> {
    Map::new(
        pre.dom().filter(|key: K| ordered_key_before_split(boundary, key)),
        |key: K| pre[key],
    )
}

pub open spec fn ordered_split_right<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
) -> Map<K, V> {
    Map::new(
        pre.dom().filter(|key: K| !ordered_key_before_split(boundary, key)),
        |key: K| pre[key],
    )
}

pub open spec fn ordered_split_partition<K, V, Q: ?Sized>(
    pre: Map<K, V>,
    boundary: &Q,
    left: Map<K, V>,
    right: Map<K, V>,
) -> bool {
    &&& left == ordered_split_left(pre, boundary)
    &&& right == ordered_split_right(pre, boundary)
    &&& left.dom().disjoint(right.dom())
    &&& left.dom().union(right.dom()) == pre.dom()
    &&& forall|key: K| #[trigger] pre.contains_key(key) ==> {
        &&& left.contains_key(key) <==> ordered_key_before_split(boundary, key)
        &&& left.contains_key(key) ==> left[key] == pre[key]
        &&& right.contains_key(key) ==> right[key] == pre[key]
    }
}

pub proof fn lemma_ordered_split_partition_empty<K, V, Q: ?Sized>(
    boundary: &Q,
)
    ensures
        ordered_split_partition(
            Map::<K, V>::empty(),
            boundary,
            Map::<K, V>::empty(),
            Map::<K, V>::empty(),
        ),
{
    assert(ordered_split_left(Map::<K, V>::empty(), boundary)
        =~= Map::<K, V>::empty()) by {
        assert(ordered_split_left(Map::<K, V>::empty(), boundary).dom()
            =~= Set::<K>::empty());
    }
    assert(ordered_split_left(Map::<K, V>::empty(), boundary)
        == Map::<K, V>::empty());
    assert(ordered_split_right(Map::<K, V>::empty(), boundary)
        =~= Map::<K, V>::empty()) by {
        assert(ordered_split_right(Map::<K, V>::empty(), boundary).dom()
            =~= Set::<K>::empty());
    }
    assert(ordered_split_right(Map::<K, V>::empty(), boundary)
        == Map::<K, V>::empty());
    assert(Map::<K, V>::empty().dom().disjoint(Map::<K, V>::empty().dom()));
    assert(Map::<K, V>::empty().dom().union(Map::<K, V>::empty().dom())
        == Map::<K, V>::empty().dom());
    assert(forall|key: K| #[trigger] Map::<K, V>::empty().contains_key(key) ==> {
        &&& Map::<K, V>::empty().contains_key(key)
            <==> ordered_key_before_split(boundary, key)
        &&& Map::<K, V>::empty().contains_key(key)
            ==> Map::<K, V>::empty()[key] == Map::<K, V>::empty()[key]
        &&& Map::<K, V>::empty().contains_key(key)
            ==> Map::<K, V>::empty()[key] == Map::<K, V>::empty()[key]
    });
}

pub uninterp spec fn extract_if_unvisited_keys<K, V, I>(
    iterator: &I,
) -> Seq<K>;

pub uninterp spec fn extract_if_visited_keys<K, V, I>(
    iterator: &I,
) -> Seq<K>;

#[verifier::prophetic]
pub uninterp spec fn extract_if_yielded_pairs<K, V, I>(
    iterator: &I,
) -> Seq<(K, V)>;

#[verifier::prophetic]
pub uninterp spec fn extract_if_current_map<K, V, I>(
    iterator: &I,
) -> Map<K, V>;

pub uninterp spec fn extract_if_model<I>(iterator: &I) -> int;

pub uninterp spec fn extract_if_remove_decision<K, V>(
    model: int,
    state: Map<K, V>,
    key: K,
) -> bool;

pub uninterp spec fn extract_if_callback_final_value<K, V>(
    model: int,
    state: Map<K, V>,
    key: K,
) -> V;

pub open spec fn extract_if_visit_map<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> Map<K, V>
    decreases keys.len(),
{
    if keys.len() == 0 {
        state
    } else {
        let key = keys[0];
        let final_value = extract_if_callback_final_value(model, state, key);
        let next_state = if extract_if_remove_decision(model, state, key) {
            state.remove(key)
        } else {
            state.insert(key, final_value)
        };
        extract_if_visit_map(model, next_state, keys.drop_first())
    }
}

pub open spec fn extract_if_removed_pairs<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> Seq<(K, V)>
    decreases keys.len(),
{
    if keys.len() == 0 {
        Seq::empty()
    } else {
        let key = keys[0];
        let final_value = extract_if_callback_final_value(model, state, key);
        let remove = extract_if_remove_decision(model, state, key);
        let next_state = if remove {
            state.remove(key)
        } else {
            state.insert(key, final_value)
        };
        let remaining = extract_if_removed_pairs(
            model,
            next_state,
            keys.drop_first(),
        );
        if remove {
            Seq::empty().push((key, final_value)) + remaining
        } else {
            remaining
        }
    }
}

pub open spec fn extract_if_next_visit_count<K, V>(
    model: int,
    state: Map<K, V>,
    keys: Seq<K>,
) -> nat
    decreases keys.len(),
{
    if keys.len() == 0 {
        0
    } else {
        let key = keys[0];
        if extract_if_remove_decision(model, state, key) {
            1
        } else {
            let next_state = state.insert(
                key,
                extract_if_callback_final_value(model, state, key),
            );
            1 + extract_if_next_visit_count(
                model,
                next_state,
                keys.drop_first(),
            )
        }
    }
}

#[verifier::prophetic]
pub open spec fn extract_if_next_consumed_keys<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    iterator: &I,
) -> Seq<K> {
    let keys = extract_if_unvisited_keys::<K, V, I>(iterator);
    keys.take(
        extract_if_next_visit_count(
            extract_if_model(iterator),
            extract_if_current_map::<K, V, I>(iterator),
            keys,
        ) as int,
    )
}

#[verifier::prophetic]
pub open spec fn extract_if_state_coherent<
    K,
    V,
    I: BTreeMapIteratorModel<Item = (K, V), Key = K, Value = V>,
>(
    iterator: &I,
) -> bool {
    iterator.ordered_remaining() == extract_if_removed_pairs(
        extract_if_model(iterator),
        extract_if_current_map::<K, V, I>(iterator),
        extract_if_unvisited_keys::<K, V, I>(iterator),
    )
}

#[verifier::prophetic]
pub open spec fn extract_if_callback_model_matches<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
    model: int,
) -> bool {
    let range_keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    forall|state: Map<K, V>, key: K|
        state.contains_key(key) && range_keys.contains(key) ==> {
            ordered_callback_observation(
                state,
                predicate,
                key,
                #[trigger] extract_if_remove_decision(model, state, key),
                #[trigger] extract_if_callback_final_value(model, state, key),
            )
        }
}

#[verifier::prophetic]
pub open spec fn extract_if_callback_model_functional<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
) -> bool {
    let keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    forall|left: int, right: int|
        #[trigger] extract_if_callback_model_matches(
            pre,
            range,
            predicate,
            left,
        )
        && #[trigger] extract_if_callback_model_matches(
            pre,
            range,
            predicate,
            right,
        )
        ==> extract_if_removed_pairs(left, pre, keys)
            == extract_if_removed_pairs(right, pre, keys)
}

#[verifier::prophetic]
pub open spec fn extract_if_lifecycle<
    K: Ord,
    V,
    R: RangeBoundsSpec<K>,
    F: FnMut(&K, &mut V) -> bool,
    I: BTreeMapIteratorModel<Item = (K, V), Key = K, Value = V>,
>(
    pre: Map<K, V>,
    range: &R,
    predicate: F,
    iterator: &I,
    post: Map<K, V>,
    visited: Seq<K>,
    unvisited: Seq<K>,
) -> bool {
    let range_keys = ordered_range_key_sequence::<K, V, K, R>(pre, range);
    let model = extract_if_model(iterator);
    &&& range_keys == visited + unvisited
    &&& extract_if_visited_keys::<K, V, I>(iterator) == visited
    &&& extract_if_unvisited_keys::<K, V, I>(iterator) == unvisited
    &&& extract_if_current_map::<K, V, I>(iterator) == post
    &&& extract_if_yielded_pairs::<K, V, I>(iterator)
        == extract_if_removed_pairs(model, pre, visited)
    &&& post == extract_if_visit_map(model, pre, visited)
    &&& extract_if_state_coherent::<K, V, I>(iterator)
    &&& extract_if_callback_model_matches(pre, range, predicate, model)
    &&& forall|key: K| unvisited.contains(key) ==> {
        &&& post.contains_key(key)
        &&& post[key] == pre[key]
    }
}

#[verifier::prophetic]
pub open spec fn ordered_map_iterator_result<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    map: Map<K, V>,
    iterator: &I,
) -> bool {
    &&& iterator.ordered_remaining().len() == map.len()
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_map_key_sequence(map)
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_map_pairs(map).map(|_index: int, pair: (K, V)| pair.1)
}

#[verifier::prophetic]
pub open spec fn ordered_map_mut_iterator_frame<
    K,
    V,
    I: BTreeMapIteratorModel<Key = K, Value = V>,
>(
    pre: Map<K, V>,
    iterator: &I,
    post: Map<K, V>,
) -> bool {
    &&& iterator.ordered_remaining().len() == pre.len()
    &&& post.dom() == pre.dom()
    &&& ordered_iterator_key_trace::<K, I>(iterator)
        == ordered_map_key_sequence(pre)
    &&& ordered_iterator_value_trace::<V, I>(iterator)
        == ordered_map_pairs(pre).map(|_index: int, pair: (K, V)| pair.1)
}

pub uninterp spec fn map_allocator_token<K, V, A: Allocator + Clone>(
    map: &BTreeMap<K, V, A>,
) -> int;
pub uninterp spec fn owning_iterator_allocator_token<I>(iterator: &I) -> int;
pub uninterp spec fn owning_iterator_drop_plan<K, V, I>(
    iterator: &I,
) -> Seq<(K, V)>;
pub uninterp spec fn owning_iterator_unwind_prefix<I>(iterator: &I) -> nat;

pub open spec fn owning_iterator_transfer<
    K,
    V,
    A: Allocator + Clone,
    I: BTreeMapIteratorModel,
>(
    map: &BTreeMap<K, V, A>,
    iterator: &I,
) -> bool {
    &&& map_allocator_token(map) == owning_iterator_allocator_token(iterator)
    &&& owning_iterator_drop_plan::<K, V, I>(iterator) == ordered_map_pairs(map@)
    &&& owning_iterator_unwind_prefix(iterator)
        <= owning_iterator_drop_plan::<K, V, I>(iterator).len()
}

pub open spec fn map_from_pairs_last_wins<K, V>(pairs: Seq<(K, V)>) -> Map<K, V>
    decreases pairs.len(),
{
    if pairs.len() == 0 {
        Map::empty()
    } else {
        let prefix = pairs.drop_last();
        let pair = pairs.last();
        map_from_pairs_last_wins(prefix).insert(pair.0, pair.1)
    }
}

pub open spec fn map_extend_pairs_last_wins<K, V>(
    pre: Map<K, V>,
    pairs: Seq<(K, V)>,
) -> Map<K, V>
    decreases pairs.len(),
{
    if pairs.len() == 0 {
        pre
    } else {
        let prefix = pairs.drop_last();
        let pair = pairs.last();
        map_extend_pairs_last_wins(pre, prefix).insert(pair.0, pair.1)
    }
}

pub uninterp spec fn collection_input_pairs<I, K, V>(
    iterator: I,
) -> Seq<(K, V)>;

pub uninterp spec fn into_iterator_item_is_owned_pair<
    K,
    V,
    T: IntoIterator,
>() -> bool;

pub open spec fn from_iterator_last_value_wins<I, K, V>(
    iterator: I,
    map: Map<K, V>,
) -> bool {
    map == map_from_pairs_last_wins(
        collection_input_pairs::<I, K, V>(iterator),
    )
}

pub open spec fn extend_last_value_wins<I, K, V>(
    pre: Map<K, V>,
    iterator: I,
    post: Map<K, V>,
) -> bool {
    post == map_extend_pairs_last_wins(
        pre,
        collection_input_pairs::<I, K, V>(iterator),
    )
}

pub uninterp spec fn hasher_trace<H>(hasher: H) -> Seq<int>;
pub uninterp spec fn hash_pair_trace<K, V>(pair: (K, V)) -> Seq<int>;

pub broadcast axiom fn axiom_hash_pair_trace_len<K, V>(pair: (K, V))
    ensures
        #[trigger] hash_pair_trace(pair).len() == 2,
;

pub open spec fn ordered_map_hash_trace<K, V>(map: Map<K, V>) -> Seq<int> {
    seq![map.len() as int] + ordered_map_pairs(map).fold_left(
        Seq::<int>::empty(),
        |trace: Seq<int>, pair: (K, V)| trace + hash_pair_trace(pair),
    )
}

pub open spec fn ordered_hash_transition<K, V, H>(
    map: Map<K, V>,
    pre_hasher: H,
    post_hasher: H,
) -> bool {
    hasher_trace(post_hasher)
        == hasher_trace(pre_hasher) + ordered_map_hash_trace(map)
}

pub open spec fn ordered_pair_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: (K, V),
    right: (K, V),
) -> Option<Ordering> {
    match left.0.partial_cmp_spec(&right.0) {
        Some(Ordering::Equal) => left.1.partial_cmp_spec(&right.1),
        result => result,
    }
}

pub open spec fn ordered_pairs_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: Seq<(K, V)>,
    right: Seq<(K, V)>,
) -> Option<Ordering>
    decreases left.len() + right.len(),
{
    if left.len() == 0 {
        if right.len() == 0 { Some(Ordering::Equal) } else { Some(Ordering::Less) }
    } else if right.len() == 0 {
        Some(Ordering::Greater)
    } else {
        match ordered_pair_partial_cmp(left[0], right[0]) {
            Some(Ordering::Equal) => {
                ordered_pairs_partial_cmp(left.drop_first(), right.drop_first())
            },
            result => result,
        }
    }
}

pub open spec fn ordered_map_partial_cmp<K: PartialOrd, V: PartialOrd>(
    left: Map<K, V>,
    right: Map<K, V>,
) -> Option<Ordering> {
    ordered_pairs_partial_cmp(ordered_map_pairs(left), ordered_map_pairs(right))
}

pub open spec fn ordered_pair_cmp<K: Ord, V: Ord>(
    left: (K, V),
    right: (K, V),
) -> Ordering {
    match left.0.cmp_spec(&right.0) {
        Ordering::Equal => left.1.cmp_spec(&right.1),
        ordering => ordering,
    }
}

pub open spec fn ordered_pairs_cmp<K: Ord, V: Ord>(
    left: Seq<(K, V)>,
    right: Seq<(K, V)>,
) -> Ordering
    decreases left.len() + right.len(),
{
    if left.len() == 0 {
        if right.len() == 0 { Ordering::Equal } else { Ordering::Less }
    } else if right.len() == 0 {
        Ordering::Greater
    } else {
        match ordered_pair_cmp(left[0], right[0]) {
            Ordering::Equal => ordered_pairs_cmp(left.drop_first(), right.drop_first()),
            ordering => ordering,
        }
    }
}

pub open spec fn ordered_map_cmp<K: Ord, V: Ord>(
    left: Map<K, V>,
    right: Map<K, V>,
) -> Ordering {
    ordered_pairs_cmp(ordered_map_pairs(left), ordered_map_pairs(right))
}

pub open spec fn array_last_value_wins<K, V, const N: usize>(
    array: &[(K, V); N],
    map: Map<K, V>,
) -> bool {
    map == map_from_pairs_last_wins((*array)@)
}

pub open spec fn entry_mutable_frame<K, V>(
    pre: Map<K, V>,
    key: K,
    initial: V,
    final_value: V,
    post: Map<K, V>,
) -> bool {
    &&& pre.contains_key(key)
    &&& initial == pre[key]
    &&& post == pre.insert(key, final_value)
}

pub open spec fn entry_remove_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    post: Map<K, V>,
) -> bool {
    post == pre.remove(key)
}

pub open spec fn entry_replace_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    value: V,
    post: Map<K, V>,
) -> bool {
    pre.contains_key(key) && post == pre.insert(key, value) && post.len() == pre.len()
}

pub open spec fn entry_insert_transition<K, V>(
    pre: Map<K, V>,
    key: K,
    value: V,
) -> bool {
    !pre.contains_key(key)
}

pub open spec fn entry_callback_domain<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: &F,
) -> bool {
    !pre.contains_key(key) || forall|value_ref: &mut V|
        *value_ref == pre[key] ==> #[trigger] callback.requires((value_ref,))
}

pub open spec fn entry_nullary_callback_functional<
    V,
    F: FnOnce() -> V,
>(
    callback: F,
) -> bool {
    forall|left: V, right: V|
        #[trigger] callback.ensures((), left)
        && #[trigger] callback.ensures((), right)
        ==> left == right
}

pub open spec fn entry_key_callback_functional<
    K,
    V,
    F: FnOnce(&K) -> V,
>(
    key: &K,
    callback: F,
) -> bool {
    forall|left: V, right: V|
        #[trigger] callback.ensures((key,), left)
        && #[trigger] callback.ensures((key,), right)
        ==> left == right
}

pub open spec fn entry_default_value_functional<V: Default>() -> bool {
    forall|left: V, right: V|
        #[trigger] V::default.ensures((), left)
        && #[trigger] V::default.ensures((), right)
        ==> left == right
}

#[verifier::prophetic]
pub open spec fn entry_and_modify_transition<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: F,
    post: Map<K, V>,
) -> bool {
    if pre.contains_key(key) {
        exists|value_ref: &mut V|
            *value_ref == pre[key]
            && #[trigger] callback.ensures((value_ref,), ())
            && post == pre.insert(key, *final(value_ref))
    } else {
        post == pre
    }
}

#[verifier::prophetic]
pub open spec fn entry_and_modify_transition_functional<
    K,
    V,
    F: FnOnce(&mut V),
>(
    pre: Map<K, V>,
    key: K,
    callback: F,
) -> bool {
    forall|left: Map<K, V>, right: Map<K, V>|
        #[trigger] entry_and_modify_transition(pre, key, callback, left)
        && #[trigger] entry_and_modify_transition(pre, key, callback, right)
        ==> left == right
}

pub broadcast group group_generated_btree_map_axioms {
    axiom_btree_map_index_req,
    axiom_iter_ordered_remaining,
    axiom_keys_ordered_remaining,
    axiom_values_ordered_remaining,
    axiom_spec_btree_map_iter_properties,
    axiom_spec_btree_map_keys_properties,
    axiom_spec_btree_map_values_properties,
    axiom_ordered_map_pairs,
    axiom_ordered_map_pairs_extensional,
    axiom_borrowed_key_matches,
    axiom_borrowed_key_value_updated_direct,
    axiom_borrowed_key_value_updated_box,
    axiom_borrowed_key_cmp_direct,
    axiom_borrowed_key_cmp_box,
    axiom_hash_pair_trace_len,
    axiom_ordered_handle_reference_coherence,
    axiom_ordered_handle_occupancy_coherent,
}

} // verus!
