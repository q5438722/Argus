// Shared source-backed observations used by the generated core::cmp contracts.
verus! {

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExCmpFormatter<'a>(core::fmt::Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExCmpFmtError(core::fmt::Error);

#[verifier::external_type_specification]
#[verifier::reject_recursive_types(T)]
pub struct ExCmpReverse<T>(core::cmp::Reverse<T>);

pub enum CmpOperation {
    Eq,
    Ne,
    PartialCmp,
    Cmp,
    Lt,
    Le,
    Gt,
    Ge,
}

pub enum CmpRelation {
    Lt,
    Le,
    Gt,
    Ge,
}

pub enum CmpEqDispatch {
    GenericElementLoop,
    Bytewise,
}

pub enum CmpOrderDispatch {
    GenericPartialOrdLoop,
    AlwaysApplicableOrd,
    GenericOrdLoop,
    UnsignedBytewiseOrd,
}

pub enum CmpCallOutcome<T> {
    Returned(T),
    Panicked,
}

pub open spec fn cmp_ordering_rank(value: core::cmp::Ordering) -> int {
    match value {
        core::cmp::Ordering::Less => -1,
        core::cmp::Ordering::Equal => 0,
        core::cmp::Ordering::Greater => 1,
    }
}

pub open spec fn cmp_ordering_compare(
    left: core::cmp::Ordering,
    right: core::cmp::Ordering,
) -> core::cmp::Ordering {
    if cmp_ordering_rank(left) < cmp_ordering_rank(right) {
        core::cmp::Ordering::Less
    } else if cmp_ordering_rank(left) > cmp_ordering_rank(right) {
        core::cmp::Ordering::Greater
    } else {
        core::cmp::Ordering::Equal
    }
}

pub open spec fn cmp_bool_compare(left: bool, right: bool) -> core::cmp::Ordering {
    if !left && right {
        core::cmp::Ordering::Less
    } else if left && !right {
        core::cmp::Ordering::Greater
    } else {
        core::cmp::Ordering::Equal
    }
}

pub open spec fn cmp_char_rank(value: char) -> int {
    (value as u32) as int
}

pub open spec fn cmp_char_compare(left: char, right: char) -> core::cmp::Ordering {
    if cmp_char_rank(left) < cmp_char_rank(right) {
        core::cmp::Ordering::Less
    } else if cmp_char_rank(left) > cmp_char_rank(right) {
        core::cmp::Ordering::Greater
    } else {
        core::cmp::Ordering::Equal
    }
}

pub open spec fn cmp_relation_holds(
    relation: CmpRelation,
    ordering: core::cmp::Ordering,
) -> bool {
    match relation {
        CmpRelation::Lt => ordering == core::cmp::Ordering::Less,
        CmpRelation::Le => ordering != core::cmp::Ordering::Greater,
        CmpRelation::Gt => ordering == core::cmp::Ordering::Greater,
        CmpRelation::Ge => ordering != core::cmp::Ordering::Less,
    }
}

pub open spec fn cmp_length_order(left: nat, right: nat) -> core::cmp::Ordering {
    if left < right {
        core::cmp::Ordering::Less
    } else if left > right {
        core::cmp::Ordering::Greater
    } else {
        core::cmp::Ordering::Equal
    }
}

pub open spec fn cmp_min_len(left: nat, right: nat) -> nat {
    if left < right { left } else { right }
}

pub uninterp spec fn cmp_tuple_observation_count<L: ?Sized, R: ?Sized>(
    operation: CmpOperation,
    left: &L,
    right: &R,
) -> nat;

pub open spec fn cmp_tuple_chaining_trigger<T>(value: T) -> bool {
    true
}

pub uninterp spec fn cmp_shared_reborrow<
    'outer,
    'inner,
    T: core::marker::PointeeSized,
>(
    value: &'outer &'inner mut T,
) -> &'outer T;

pub uninterp spec fn cmp_sequence_observation_count<T, U>(
    operation: CmpOperation,
    left: Seq<T>,
    right: Seq<U>,
) -> nat;

pub uninterp spec fn cmp_array_eq_dispatch<T, U>(
    left: Seq<T>,
    right: Seq<U>,
) -> CmpEqDispatch;

pub uninterp spec fn cmp_slice_eq_dispatch<T, U>(
    left: Seq<T>,
    right: Seq<U>,
) -> CmpEqDispatch;

pub uninterp spec fn cmp_array_order_dispatch<T>(
    left: Seq<T>,
    right: Seq<T>,
) -> CmpOrderDispatch;

pub uninterp spec fn cmp_slice_order_dispatch<T>(
    left: Seq<T>,
    right: Seq<T>,
) -> CmpOrderDispatch;

pub uninterp spec fn cmp_always_applicable_ord_dispatch<T: PartialOrd>(
    left: Seq<T>,
    right: Seq<T>,
) -> CmpOrderDispatch;

pub uninterp spec fn cmp_bytewise_equal<T, U>(
    left: Seq<T>,
    right: Seq<U>,
) -> bool;

pub uninterp spec fn cmp_unsigned_bytewise_order<T>(
    left: Seq<T>,
    right: Seq<T>,
) -> core::cmp::Ordering;

pub uninterp spec fn cmp_array_slice_forwarding<T>(
    operation: CmpOperation,
    left: Seq<T>,
    right: Seq<T>,
) -> bool;

pub uninterp spec fn cmp_then_with_observation_count<F>(
    ordering: core::cmp::Ordering,
    callback: F,
) -> nat;

pub uninterp spec fn cmp_comparator_observation_count<F, T>(
    callback: F,
    first: &T,
    second: &T,
) -> nat;

pub uninterp spec fn cmp_fn_mut_state_transition<F, T, K>(
    before: F,
    argument: &T,
    output: K,
    after: F,
) -> bool
    where F: FnMut(&T) -> K
;

pub uninterp spec fn cmp_key_callback_observation_count<F, T>(
    callback: F,
    first: &T,
    second: &T,
) -> nat;

pub uninterp spec fn cmp_clone_from_effect<T: Clone>(
    before: T,
    source: T,
    after: T,
) -> bool;

#[verifier::prophetic]
pub uninterp spec fn cmp_ordering_debug_effect<'a>(
    value: core::cmp::Ordering,
    formatter: &mut core::fmt::Formatter<'a>,
    result: core::fmt::Result,
) -> bool;

#[verifier::prophetic]
pub uninterp spec fn cmp_reverse_debug_effect<'a, T: core::fmt::Debug>(
    value: &T,
    formatter: &mut core::fmt::Formatter<'a>,
    result: core::fmt::Result,
) -> bool;

#[verifier::prophetic]
pub uninterp spec fn cmp_ordering_hash_effect<H: core::hash::Hasher>(
    value: core::cmp::Ordering,
    state: &mut H,
) -> bool;

#[verifier::prophetic]
pub uninterp spec fn cmp_reverse_hash_effect<T: core::hash::Hash, H: core::hash::Hasher>(
    value: &T,
    state: &mut H,
) -> bool;

pub open spec fn cmp_element_ne_result<T: PartialEq<U>, U>(
    left: T,
    right: U,
    result: bool,
) -> bool {
    call_ensures(<T as PartialEq<U>>::ne, (&left, &right), result)
}

pub open spec fn cmp_element_partial_cmp_result<T: PartialOrd>(
    left: T,
    right: T,
    result: Option<core::cmp::Ordering>,
) -> bool {
    call_ensures(<T as PartialOrd>::partial_cmp, (&left, &right), result)
}

pub open spec fn cmp_element_cmp_result<T: Ord>(
    left: T,
    right: T,
    result: core::cmp::Ordering,
) -> bool {
    call_ensures(<T as Ord>::cmp, (&left, &right), result)
}

pub open spec fn cmp_lexicographic_ne_prefix<T: PartialEq<U>, U>(
    left: Seq<T>,
    right: Seq<U>,
    outcomes: Seq<bool>,
) -> bool {
    outcomes.len() <= left.len()
        && outcomes.len() <= right.len()
        && forall|i: int| 0 <= i < outcomes.len() ==>
            cmp_element_ne_result(left[i], right[i], outcomes[i])
        && forall|i: int| 0 <= i < outcomes.len() - 1 ==> !outcomes[i]
}

pub open spec fn cmp_lexicographic_partial_cmp_prefix<T: PartialOrd>(
    left: Seq<T>,
    right: Seq<T>,
    outcomes: Seq<Option<core::cmp::Ordering>>,
) -> bool {
    outcomes.len() <= left.len()
        && outcomes.len() <= right.len()
        && forall|i: int| 0 <= i < outcomes.len() ==>
            cmp_element_partial_cmp_result(left[i], right[i], outcomes[i])
        && forall|i: int| 0 <= i < outcomes.len() - 1 ==>
            outcomes[i] == Some(core::cmp::Ordering::Equal)
}

pub open spec fn cmp_lexicographic_cmp_prefix<T: Ord>(
    left: Seq<T>,
    right: Seq<T>,
    outcomes: Seq<core::cmp::Ordering>,
) -> bool {
    outcomes.len() <= left.len()
        && outcomes.len() <= right.len()
        && forall|i: int| 0 <= i < outcomes.len() ==>
            cmp_element_cmp_result(left[i], right[i], outcomes[i])
        && forall|i: int| 0 <= i < outcomes.len() - 1 ==>
            outcomes[i] == core::cmp::Ordering::Equal
}

pub uninterp spec fn cmp_hidden_ord_element_result<T: PartialOrd>(
    left: T,
    right: T,
    result: core::cmp::Ordering,
) -> bool;

pub open spec fn cmp_hidden_ord_lexicographic_prefix<T: PartialOrd>(
    left: Seq<T>,
    right: Seq<T>,
    outcomes: Seq<core::cmp::Ordering>,
) -> bool {
    outcomes.len() <= left.len()
        && outcomes.len() <= right.len()
        && forall|i: int| 0 <= i < outcomes.len() ==>
            cmp_hidden_ord_element_result(left[i], right[i], outcomes[i])
        && forall|i: int| 0 <= i < outcomes.len() - 1 ==>
            outcomes[i] == core::cmp::Ordering::Equal
}

} // verus!
