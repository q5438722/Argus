#![feature(sized_hierarchy)]
#![allow(unused_imports, dead_code, deprecated)]

use core::cmp::{Eq, Ord, Ordering, PartialEq, PartialOrd, Reverse};
use core::clone::Clone;
use core::default::Default;
use core::fmt::Debug;
use core::hash::Hash;
use core::marker::PointeeSized;
use vstd::prelude::*;
use vstd::std_specs::cmp::{OrdSpec, PartialOrdSpec};

include!("cmp_shared_vocabulary.rs");

verus! {

// @spec-row rustdoc-10786-10785 family=ordering_value
pub assume_specification[
    <Ordering as PartialEq<Ordering>>::eq
](
    left: &Ordering,
    right: &Ordering,
) -> (result: bool)
    ensures
        result <==> cmp_ordering_rank(*left) == cmp_ordering_rank(*right),
;

// @spec-row rustdoc-10788-10787 family=reverse_forwarding
pub assume_specification<T: PartialEq>[
    <Reverse<T> as PartialEq<Reverse<T>>>::eq
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: bool)
    ensures
        call_ensures(<T as PartialEq>::eq, (&left.0, &right.0), result),
;

// @spec-row rustdoc-10791-10789 family=unit_value
pub assume_specification[
    <() as PartialEq<()>>::eq
](
    left: &(),
    right: &(),
) -> (result: bool)
    ensures
        result,
;

// @spec-row rustdoc-10791-10790 family=unit_value
pub assume_specification[
    <() as PartialEq<()>>::ne
](
    left: &(),
    right: &(),
) -> (result: bool)
    ensures
        !result,
;

// @spec-row rustdoc-10797-10795 family=char_value
pub assume_specification[
    <char as PartialEq<char>>::eq
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_char_rank(*left) == cmp_char_rank(*right),
;

// @spec-row rustdoc-10797-10796 family=char_value
pub assume_specification[
    <char as PartialEq<char>>::ne
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_char_rank(*left) != cmp_char_rank(*right),
;

// @spec-row rustdoc-10853-10851 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a mut A as PartialEq<&mut B>>::eq
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::eq, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-10853-10852 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a mut A as PartialEq<&mut B>>::ne
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::ne, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-10856-10854 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a A as PartialEq<&mut B>>::eq
](
    left: &&'a A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::eq, (*left, cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-10856-10855 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a A as PartialEq<&mut B>>::ne
](
    left: &&'a A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::ne, (*left, cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-10859-10857 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a mut A as PartialEq<&B>>::eq
](
    left: &&'a mut A,
    right: &&B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::eq, (cmp_shared_reborrow(left), *right), result),
;

// @spec-row rustdoc-10859-10858 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialEq<B>, B: PointeeSized>[
    <&'a mut A as PartialEq<&B>>::ne
](
    left: &&'a mut A,
    right: &&B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialEq<B>>::ne, (cmp_shared_reborrow(left), *right), result),
;

// @spec-row rustdoc-10900-10898 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<[U; N]>>::eq
](
    left: &[T; N],
    right: &[U; N],
) -> (result: bool)
    ensures
        cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == outcomes.len(),
        cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 1,
;

// @spec-row rustdoc-10900-10899 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<[U; N]>>::ne
](
    left: &[T; N],
    right: &[U; N],
) -> (result: bool)
    ensures
        cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == outcomes.len(),
        cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == 1,
;

// @spec-row rustdoc-10903-10901 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<[U]>>::eq
](
    left: &[T; N],
    right: &[U],
) -> (result: bool)
    ensures
        !(right@.len() == N) ==> !result,
        !(right@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 0,
        right@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == outcomes.len(),
        right@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 1,
;

// @spec-row rustdoc-10903-10902 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<[U]>>::ne
](
    left: &[T; N],
    right: &[U],
) -> (result: bool)
    ensures
        !(right@.len() == N) ==> result,
        !(right@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == 0,
        right@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == outcomes.len(),
        right@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == 1,
;

// @spec-row rustdoc-10906-10904 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T] as PartialEq<[U; N]>>::eq
](
    left: &[T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !(left@.len() == N) ==> !result,
        !(left@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 0,
        left@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == outcomes.len(),
        left@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 1,
;

// @spec-row rustdoc-10906-10905 family=array_equality_dispatch
pub assume_specification<T: PartialEq<U>, U, const N: usize>[
    <[T] as PartialEq<[U; N]>>::ne
](
    left: &[T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !(left@.len() == N) ==> result,
        !(left@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == 0,
        left@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == outcomes.len(),
        left@.len() == N ==> cmp_array_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Ne, left@, right@) == 1,
;

// @spec-row rustdoc-10909-10907 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<&'a [U]>>::eq
](
    left: &[T; N],
    right: &&[U],
) -> (result: bool)
    ensures
        !((*right)@.len() == N) ==> !result,
        !((*right)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, left@, (*right)@) == 0,
        (*right)@.len() == N ==> cmp_array_eq_dispatch(left@, (*right)@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, (*right)@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, (*right)@) == outcomes.len(),
        (*right)@.len() == N ==> cmp_array_eq_dispatch(left@, (*right)@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, (*right)@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, (*right)@) == 1,
;

// @spec-row rustdoc-10909-10908 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<&'a [U]>>::ne
](
    left: &[T; N],
    right: &&[U],
) -> (result: bool)
    ensures
        !((*right)@.len() == N) ==> result,
        !((*right)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, left@, (*right)@) == 0,
        (*right)@.len() == N ==> cmp_array_eq_dispatch(left@, (*right)@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, (*right)@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, left@, (*right)@) == outcomes.len(),
        (*right)@.len() == N ==> cmp_array_eq_dispatch(left@, (*right)@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(left@, (*right)@)) && cmp_sequence_observation_count(CmpOperation::Ne, left@, (*right)@) == 1,
;

// @spec-row rustdoc-10912-10910 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <&[T] as PartialEq<[U; N]>>::eq
](
    left: &&'a [T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !((*left)@.len() == N) ==> !result,
        !((*left)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, (*left)@, right@) == 0,
        (*left)@.len() == N ==> cmp_array_eq_dispatch((*left)@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix((*left)@, right@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, (*left)@, right@) == outcomes.len(),
        (*left)@.len() == N ==> cmp_array_eq_dispatch((*left)@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal((*left)@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, (*left)@, right@) == 1,
;

// @spec-row rustdoc-10912-10911 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <&[T] as PartialEq<[U; N]>>::ne
](
    left: &&'a [T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !((*left)@.len() == N) ==> result,
        !((*left)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, (*left)@, right@) == 0,
        (*left)@.len() == N ==> cmp_array_eq_dispatch((*left)@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix((*left)@, right@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, (*left)@, right@) == outcomes.len(),
        (*left)@.len() == N ==> cmp_array_eq_dispatch((*left)@, right@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal((*left)@, right@)) && cmp_sequence_observation_count(CmpOperation::Ne, (*left)@, right@) == 1,
;

// @spec-row rustdoc-10915-10913 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<&'a mut [U]>>::eq
](
    left: &[T; N],
    right: &&mut [U],
) -> (result: bool)
    ensures
        !(old(*right)@.len() == N) ==> !result,
        !(old(*right)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, left@, old(*right)@) == 0,
        old(*right)@.len() == N ==> cmp_array_eq_dispatch(left@, old(*right)@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, old(*right)@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, old(*right)@) == outcomes.len(),
        old(*right)@.len() == N ==> cmp_array_eq_dispatch(left@, old(*right)@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, old(*right)@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, old(*right)@) == 1,
;

// @spec-row rustdoc-10915-10914 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <[T; N] as PartialEq<&'a mut [U]>>::ne
](
    left: &[T; N],
    right: &&mut [U],
) -> (result: bool)
    ensures
        !(old(*right)@.len() == N) ==> result,
        !(old(*right)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, left@, old(*right)@) == 0,
        old(*right)@.len() == N ==> cmp_array_eq_dispatch(left@, old(*right)@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, old(*right)@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, left@, old(*right)@) == outcomes.len(),
        old(*right)@.len() == N ==> cmp_array_eq_dispatch(left@, old(*right)@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(left@, old(*right)@)) && cmp_sequence_observation_count(CmpOperation::Ne, left@, old(*right)@) == 1,
;

// @spec-row rustdoc-10918-10916 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <&mut [T] as PartialEq<[U; N]>>::eq
](
    left: &&'a mut [T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !(old(*left)@.len() == N) ==> !result,
        !(old(*left)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Eq, old(*left)@, right@) == 0,
        old(*left)@.len() == N ==> cmp_array_eq_dispatch(old(*left)@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(old(*left)@, right@, outcomes) && (result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, old(*left)@, right@) == outcomes.len(),
        old(*left)@.len() == N ==> cmp_array_eq_dispatch(old(*left)@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(old(*left)@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, old(*left)@, right@) == 1,
;

// @spec-row rustdoc-10918-10917 family=array_equality_dispatch
pub assume_specification<'a, T: PartialEq<U>, U, const N: usize>[
    <&mut [T] as PartialEq<[U; N]>>::ne
](
    left: &&'a mut [T],
    right: &[U; N],
) -> (result: bool)
    ensures
        !(old(*left)@.len() == N) ==> result,
        !(old(*left)@.len() == N) ==> cmp_sequence_observation_count(CmpOperation::Ne, old(*left)@, right@) == 0,
        old(*left)@.len() == N ==> cmp_array_eq_dispatch(old(*left)@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(old(*left)@, right@, outcomes) && (!result <==> outcomes.len() == N && forall|i: int| 0 <= i < N ==> !outcomes[i]) && (result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Ne, old(*left)@, right@) == outcomes.len(),
        old(*left)@.len() == N ==> cmp_array_eq_dispatch(old(*left)@, right@) == CmpEqDispatch::Bytewise ==> (result <==> ! cmp_bytewise_equal(old(*left)@, right@)) && cmp_sequence_observation_count(CmpOperation::Ne, old(*left)@, right@) == 1,
;

// @spec-row rustdoc-11030-11029 family=slice_equality_dispatch
pub assume_specification<T: PartialEq<U>, U>[
    <[T] as PartialEq<[U]>>::eq
](
    left: &[T],
    right: &[U],
) -> (result: bool)
    ensures
        left@.len() != right@.len() ==> !result,
        left@.len() != right@.len() ==> cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 0,
        left@.len() == right@.len() && cmp_slice_eq_dispatch(left@, right@) == CmpEqDispatch::GenericElementLoop ==> exists|outcomes: Seq<bool>| cmp_lexicographic_ne_prefix(left@, right@, outcomes) && (result <==> outcomes.len() == left@.len() && forall|i: int| 0 <= i < left@.len() ==> !outcomes[i]) && (!result <==> outcomes.len() > 0 && outcomes.last()) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == outcomes.len(),
        left@.len() == right@.len() && cmp_slice_eq_dispatch(left@, right@) == CmpEqDispatch::Bytewise ==> (result <==> cmp_bytewise_equal(left@, right@)) && cmp_sequence_observation_count(CmpOperation::Eq, left@, right@) == 1,
;

// @spec-row rustdoc-11064-11062 family=tuple_short_circuit
pub assume_specification<T: PartialEq>[
    <(T,) as PartialEq<(T,)>>::eq
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        exists|o0: bool|
            call_ensures(<T as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (result <==> (o0)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == 1nat,
;

// @spec-row rustdoc-11064-11063 family=tuple_short_circuit
pub assume_specification<T: PartialEq>[
    <(T,) as PartialEq<(T,)>>::ne
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        exists|o0: bool|
            call_ensures(<T as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (result <==> (o0)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == 1nat,
;

// @spec-row rustdoc-11181-11180 family=ordering_then_with
pub assume_specification<F: FnOnce() -> Ordering>[
    Ordering::then_with::<F>
](
    ordering: Ordering,
    callback: F,
) -> (result: Ordering)
    requires
        ordering == Ordering::Equal ==> callback.requires(()),
    ensures
        ordering != Ordering::Equal ==> result == ordering,
        ordering != Ordering::Equal ==> cmp_then_with_observation_count(ordering, callback) == 0,
        ordering == Ordering::Equal ==> callback.ensures((), result),
        ordering == Ordering::Equal ==> cmp_then_with_observation_count(ordering, callback) == 1,
;

// @spec-row rustdoc-11198-11197 family=ordering_value
pub assume_specification[
    <Ordering as PartialOrd<Ordering>>::partial_cmp
](
    left: &Ordering,
    right: &Ordering,
) -> (result: Option<Ordering>)
    ensures
        result == Some(cmp_ordering_compare(*left, *right)),
;

// @spec-row rustdoc-11200-11199 family=ordering_value
pub assume_specification[
    <Ordering as Ord>::cmp
](
    left: &Ordering,
    right: &Ordering,
) -> (result: Ordering)
    ensures
        result == cmp_ordering_compare(*left, *right),
;

// @spec-row rustdoc-11204-11203 family=ordering_debug
#[verifier::allow(undeclared_external_trait)]
pub assume_specification[
    <Ordering as Debug>::fmt
](
    value: &Ordering,
    formatter: &mut core::fmt::Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        cmp_ordering_debug_effect(*value, formatter, result),
;

// @spec-row rustdoc-11206-11205 family=ordering_hash
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<H: core::hash::Hasher>[
    <Ordering as Hash>::hash
](
    value: &Ordering,
    state: &mut H,
)
    ensures
        cmp_ordering_hash_effect(*value, state),
;

// @spec-row rustdoc-11225-11224 family=reverse_default
pub assume_specification<T: Default>[
    <Reverse<T> as Default>::default
](
) -> (result: Reverse<T>)
    ensures
        exists|value: T| call_ensures(T::default, (), value) && result == Reverse(value),
;

// @spec-row rustdoc-11228-11227 family=reverse_debug
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: core::fmt::Debug>[
    <Reverse<T> as Debug>::fmt
](
    value: &Reverse<T>,
    formatter: &mut core::fmt::Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        cmp_reverse_debug_effect(&value.0, formatter, result),
;

// @spec-row rustdoc-11230-11229 family=reverse_hash
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: core::hash::Hash, H: core::hash::Hasher>[
    <Reverse<T> as Hash>::hash
](
    value: &Reverse<T>,
    state: &mut H,
)
    ensures
        cmp_reverse_hash_effect(&value.0, state),
;

// @spec-row rustdoc-11236-11231 family=reverse_operand_reversal
pub assume_specification<T: PartialOrd>[
    <Reverse<T> as PartialOrd<Reverse<T>>>::partial_cmp
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: Option<Ordering>)
    ensures
        call_ensures(<T as PartialOrd>::partial_cmp, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11236-11232 family=reverse_operand_reversal
pub assume_specification<T: PartialOrd>[
    <Reverse<T> as PartialOrd<Reverse<T>>>::lt
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::lt, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11236-11233 family=reverse_operand_reversal
pub assume_specification<T: PartialOrd>[
    <Reverse<T> as PartialOrd<Reverse<T>>>::le
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::le, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11236-11234 family=reverse_operand_reversal
pub assume_specification<T: PartialOrd>[
    <Reverse<T> as PartialOrd<Reverse<T>>>::gt
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::gt, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11236-11235 family=reverse_operand_reversal
pub assume_specification<T: PartialOrd>[
    <Reverse<T> as PartialOrd<Reverse<T>>>::ge
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::ge, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11238-11237 family=reverse_operand_reversal
pub assume_specification<T: Ord>[
    <Reverse<T> as Ord>::cmp
](
    left: &Reverse<T>,
    right: &Reverse<T>,
) -> (result: Ordering)
    ensures
        call_ensures(<T as Ord>::cmp, (&right.0, &left.0), result),
;

// @spec-row rustdoc-11249-11248 family=unit_value
pub assume_specification[
    <() as Ord>::cmp
](
    left: &(),
    right: &(),
) -> (result: Ordering)
    ensures
        result == Ordering::Equal,
;

// @spec-row rustdoc-11254-11250 family=bool_value
pub assume_specification[
    <bool as Ord>::cmp
](
    left: &bool,
    right: &bool,
) -> (result: Ordering)
    ensures
        result == cmp_bool_compare(*left, *right),
;

// @spec-row rustdoc-11254-11251 family=bool_value
pub assume_specification[
    <bool as Ord>::min
](
    left: bool,
    right: bool,
) -> (result: bool)
    ensures
        result == (left && right),
;

// @spec-row rustdoc-11254-11252 family=bool_value
pub assume_specification[
    <bool as Ord>::max
](
    left: bool,
    right: bool,
) -> (result: bool)
    ensures
        result == (left || right),
;

// @spec-row rustdoc-11254-11253 family=primitive_clamp
pub assume_specification[
    <bool as Ord>::clamp
](
    value: bool,
    min: bool,
    max: bool,
) -> (result: bool)
    ensures
        (if min && !max { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if !value && min { min } else if value && !max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11257-11255 family=char_value
pub assume_specification[
    <char as Ord>::cmp
](
    left: &char,
    right: &char,
) -> (result: Ordering)
    ensures
        result == cmp_char_compare(*left, *right),
;

// @spec-row rustdoc-11257-11256 family=primitive_clamp
pub assume_specification[
    <char as Ord>::clamp
](
    value: char,
    min: char,
    max: char,
) -> (result: char)
    ensures
        (if !(cmp_char_rank(min) <= cmp_char_rank(max)) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if cmp_char_rank(value) < cmp_char_rank(min) { min } else if cmp_char_rank(value) > cmp_char_rank(max) { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11260-11259 family=primitive_clamp
pub assume_specification[
    <usize as Ord>::clamp
](
    value: usize,
    min: usize,
    max: usize,
) -> (result: usize)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11263-11262 family=primitive_clamp
pub assume_specification[
    <u8 as Ord>::clamp
](
    value: u8,
    min: u8,
    max: u8,
) -> (result: u8)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11266-11265 family=primitive_clamp
pub assume_specification[
    <u16 as Ord>::clamp
](
    value: u16,
    min: u16,
    max: u16,
) -> (result: u16)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11269-11268 family=primitive_clamp
pub assume_specification[
    <u32 as Ord>::clamp
](
    value: u32,
    min: u32,
    max: u32,
) -> (result: u32)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11272-11271 family=primitive_clamp
pub assume_specification[
    <u64 as Ord>::clamp
](
    value: u64,
    min: u64,
    max: u64,
) -> (result: u64)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11275-11274 family=primitive_clamp
pub assume_specification[
    <u128 as Ord>::clamp
](
    value: u128,
    min: u128,
    max: u128,
) -> (result: u128)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11278-11277 family=primitive_clamp
pub assume_specification[
    <isize as Ord>::clamp
](
    value: isize,
    min: isize,
    max: isize,
) -> (result: isize)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11281-11280 family=primitive_clamp
pub assume_specification[
    <i8 as Ord>::clamp
](
    value: i8,
    min: i8,
    max: i8,
) -> (result: i8)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11284-11283 family=primitive_clamp
pub assume_specification[
    <i16 as Ord>::clamp
](
    value: i16,
    min: i16,
    max: i16,
) -> (result: i16)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11287-11286 family=primitive_clamp
pub assume_specification[
    <i32 as Ord>::clamp
](
    value: i32,
    min: i32,
    max: i32,
) -> (result: i32)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11290-11289 family=primitive_clamp
pub assume_specification[
    <i64 as Ord>::clamp
](
    value: i64,
    min: i64,
    max: i64,
) -> (result: i64)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11293-11292 family=primitive_clamp
pub assume_specification[
    <i128 as Ord>::clamp
](
    value: i128,
    min: i128,
    max: i128,
) -> (result: i128)
    ensures
        (if !(min <= max) { CmpCallOutcome::Panicked } else { CmpCallOutcome::Returned(if value < min { min } else if value > max { max } else { value }) }) == CmpCallOutcome::Returned(result),
;

// @spec-row rustdoc-11299-11298 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, A: PointeeSized + Ord>[
    <&'a mut A as Ord>::cmp
](
    left: &&'a mut A,
    right: &&'a mut A,
) -> (result: Ordering)
    ensures
        call_ensures(<A as Ord>::cmp, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11323-11322 family=array_slice_order_forwarding
pub assume_specification<T: Ord, const N: usize>[
    <[T; N] as Ord>::cmp
](
    left: &[T; N],
    right: &[T; N],
) -> (result: core::cmp::Ordering)
    ensures
        cmp_array_slice_forwarding(CmpOperation::Cmp, left@, right@),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop ==> exists|outcomes: Seq<core::cmp::Ordering>| cmp_lexicographic_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != core::cmp::Ordering::Equal) && result == if outcomes.len() > 0 && outcomes.last() != core::cmp::Ordering::Equal { outcomes.last() } else { cmp_length_order(left@.len(), right@.len()) },
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> result == cmp_unsigned_bytewise_order(left@, right@),
;

// @spec-row rustdoc-11363-11362 family=slice_order_dispatch
pub assume_specification<T: Ord>[
    <[T] as Ord>::cmp
](
    left: &[T],
    right: &[T],
) -> (result: core::cmp::Ordering)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop ==> exists|outcomes: Seq<core::cmp::Ordering>| cmp_lexicographic_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != core::cmp::Ordering::Equal) && result == if outcomes.len() > 0 && outcomes.last() != core::cmp::Ordering::Equal { outcomes.last() } else { cmp_length_order(left@.len(), right@.len()) },
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> result == cmp_unsigned_bytewise_order(left@, right@),
;

// @spec-row rustdoc-11371-11370 family=tuple_short_circuit
pub assume_specification<T: Ord>[
    <(T,) as Ord>::cmp
](
    left: &(T,),
    right: &(T,),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering|
            call_ensures(<T as Ord>::cmp, (&left.0, &right.0), o0) &&
            (result == (o0)) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == 1nat,
;

// @spec-row rustdoc-11396-11395 family=unit_value
pub assume_specification[
    <() as PartialOrd<()>>::partial_cmp
](
    left: &(),
    right: &(),
) -> (result: Option<Ordering>)
    ensures
        result == Some(Ordering::Equal),
;

// @spec-row rustdoc-11402-11397 family=bool_value
pub assume_specification[
    <bool as PartialOrd<bool>>::partial_cmp
](
    left: &bool,
    right: &bool,
) -> (result: Option<Ordering>)
    ensures
        result == Some(cmp_bool_compare(*left, *right)),
;

// @spec-row rustdoc-11402-11398 family=bool_value
pub assume_specification[
    <bool as PartialOrd<bool>>::lt
](
    left: &bool,
    right: &bool,
) -> (result: bool)
    ensures
        result <==> !*left && *right,
;

// @spec-row rustdoc-11402-11399 family=bool_value
pub assume_specification[
    <bool as PartialOrd<bool>>::le
](
    left: &bool,
    right: &bool,
) -> (result: bool)
    ensures
        result <==> !*left || *right,
;

// @spec-row rustdoc-11402-11400 family=bool_value
pub assume_specification[
    <bool as PartialOrd<bool>>::gt
](
    left: &bool,
    right: &bool,
) -> (result: bool)
    ensures
        result <==> *left && !*right,
;

// @spec-row rustdoc-11402-11401 family=bool_value
pub assume_specification[
    <bool as PartialOrd<bool>>::ge
](
    left: &bool,
    right: &bool,
) -> (result: bool)
    ensures
        result <==> *left || !*right,
;

// @spec-row rustdoc-11432-11427 family=char_value
pub assume_specification[
    <char as PartialOrd<char>>::partial_cmp
](
    left: &char,
    right: &char,
) -> (result: Option<Ordering>)
    ensures
        result == Some(cmp_char_compare(*left, *right)),
;

// @spec-row rustdoc-11432-11428 family=char_value
pub assume_specification[
    <char as PartialOrd<char>>::lt
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_relation_holds(CmpRelation::Lt, cmp_char_compare(*left, *right)),
;

// @spec-row rustdoc-11432-11429 family=char_value
pub assume_specification[
    <char as PartialOrd<char>>::le
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_relation_holds(CmpRelation::Le, cmp_char_compare(*left, *right)),
;

// @spec-row rustdoc-11432-11430 family=char_value
pub assume_specification[
    <char as PartialOrd<char>>::gt
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_relation_holds(CmpRelation::Gt, cmp_char_compare(*left, *right)),
;

// @spec-row rustdoc-11432-11431 family=char_value
pub assume_specification[
    <char as PartialOrd<char>>::ge
](
    left: &char,
    right: &char,
) -> (result: bool)
    ensures
        result <==> cmp_relation_holds(CmpRelation::Ge, cmp_char_compare(*left, *right)),
;

// @spec-row rustdoc-11518-11513 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized>[
    <&'a mut A as PartialOrd<&mut B>>::partial_cmp
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: Option<Ordering>)
    ensures
        call_ensures(<A as PartialOrd<B>>::partial_cmp, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11518-11514 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized>[
    <&'a mut A as PartialOrd<&mut B>>::lt
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialOrd<B>>::lt, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11518-11515 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized>[
    <&'a mut A as PartialOrd<&mut B>>::le
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialOrd<B>>::le, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11518-11516 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized>[
    <&'a mut A as PartialOrd<&mut B>>::gt
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialOrd<B>>::gt, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11518-11517 family=reference_forwarding
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'_0, 'a, A: PointeeSized + PartialOrd<B>, B: PointeeSized>[
    <&'a mut A as PartialOrd<&mut B>>::ge
](
    left: &&'a mut A,
    right: &&mut B,
) -> (result: bool)
    ensures
        call_ensures(<A as PartialOrd<B>>::ge, (cmp_shared_reborrow(left), cmp_shared_reborrow(right)), result),
;

// @spec-row rustdoc-11546-11541 family=array_slice_order_forwarding
pub assume_specification<T: PartialOrd, const N: usize>[
    <[T; N] as PartialOrd<[T; N]>>::partial_cmp
](
    left: &[T; N],
    right: &[T; N],
) -> (result: Option<core::cmp::Ordering>)
    ensures
        cmp_array_slice_forwarding(CmpOperation::PartialCmp, left@, right@),
        (cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::AlwaysApplicableOrd),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && result == if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() } else { Some(cmp_length_order(left@.len(), right@.len())) },
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::AlwaysApplicableOrd ==> (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop || cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd) && (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop ==> exists|outcomes: Seq<core::cmp::Ordering>, order: core::cmp::Ordering| cmp_hidden_ord_lexicographic_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != core::cmp::Ordering::Equal) && order == if outcomes.len() > 0 && outcomes.last() != core::cmp::Ordering::Equal { outcomes.last() } else { cmp_length_order(left@.len(), right@.len()) } && result == Some(order)) && (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> result == Some(cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11546-11542 family=array_slice_order_forwarding
pub assume_specification<T: PartialOrd, const N: usize>[
    <[T; N] as PartialOrd<[T; N]>>::lt
](
    left: &[T; N],
    right: &[T; N],
) -> (result: bool)
    ensures
        cmp_array_slice_forwarding(CmpOperation::Lt, left@, right@),
        (cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Lt, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Lt, cmp_length_order(left@.len(), right@.len())) }),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Lt, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11546-11543 family=array_slice_order_forwarding
pub assume_specification<T: PartialOrd, const N: usize>[
    <[T; N] as PartialOrd<[T; N]>>::le
](
    left: &[T; N],
    right: &[T; N],
) -> (result: bool)
    ensures
        cmp_array_slice_forwarding(CmpOperation::Le, left@, right@),
        (cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Le, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Le, cmp_length_order(left@.len(), right@.len())) }),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Le, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11546-11544 family=array_slice_order_forwarding
pub assume_specification<T: PartialOrd, const N: usize>[
    <[T; N] as PartialOrd<[T; N]>>::ge
](
    left: &[T; N],
    right: &[T; N],
) -> (result: bool)
    ensures
        cmp_array_slice_forwarding(CmpOperation::Ge, left@, right@),
        (cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Ge, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Ge, cmp_length_order(left@.len(), right@.len())) }),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Ge, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11546-11545 family=array_slice_order_forwarding
pub assume_specification<T: PartialOrd, const N: usize>[
    <[T; N] as PartialOrd<[T; N]>>::gt
](
    left: &[T; N],
    right: &[T; N],
) -> (result: bool)
    ensures
        cmp_array_slice_forwarding(CmpOperation::Gt, left@, right@),
        (cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= N && (N == 0 ==> outcomes.len() == 0) && (N > 0 ==> outcomes.len() > 0) && (outcomes.len() < N ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Gt, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Gt, cmp_length_order(left@.len(), right@.len())) }),
        cmp_array_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Gt, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11610-11605 family=slice_order_dispatch
pub assume_specification<T: PartialOrd>[
    <[T] as PartialOrd<[T]>>::partial_cmp
](
    left: &[T],
    right: &[T],
) -> (result: Option<core::cmp::Ordering>)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::AlwaysApplicableOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && result == if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() } else { Some(cmp_length_order(left@.len(), right@.len())) },
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::AlwaysApplicableOrd ==> (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop || cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd) && (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::GenericOrdLoop ==> exists|outcomes: Seq<core::cmp::Ordering>, order: core::cmp::Ordering| cmp_hidden_ord_lexicographic_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != core::cmp::Ordering::Equal) && order == if outcomes.len() > 0 && outcomes.last() != core::cmp::Ordering::Equal { outcomes.last() } else { cmp_length_order(left@.len(), right@.len()) } && result == Some(order)) && (cmp_always_applicable_ord_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> result == Some(cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11610-11606 family=slice_order_dispatch
pub assume_specification<T: PartialOrd>[
    <[T] as PartialOrd<[T]>>::lt
](
    left: &[T],
    right: &[T],
) -> (result: bool)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Lt, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Lt, cmp_length_order(left@.len(), right@.len())) }),
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Lt, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11610-11607 family=slice_order_dispatch
pub assume_specification<T: PartialOrd>[
    <[T] as PartialOrd<[T]>>::le
](
    left: &[T],
    right: &[T],
) -> (result: bool)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Le, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Le, cmp_length_order(left@.len(), right@.len())) }),
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Le, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11610-11608 family=slice_order_dispatch
pub assume_specification<T: PartialOrd>[
    <[T] as PartialOrd<[T]>>::gt
](
    left: &[T],
    right: &[T],
) -> (result: bool)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Gt, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Gt, cmp_length_order(left@.len(), right@.len())) }),
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Gt, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11610-11609 family=slice_order_dispatch
pub assume_specification<T: PartialOrd>[
    <[T] as PartialOrd<[T]>>::ge
](
    left: &[T],
    right: &[T],
) -> (result: bool)
    ensures
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop || cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd,
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::GenericPartialOrdLoop ==> exists|outcomes: Seq<Option<core::cmp::Ordering>>| cmp_lexicographic_partial_cmp_prefix(left@, right@, outcomes) && outcomes.len() <= cmp_min_len(left@.len(), right@.len()) && (cmp_min_len(left@.len(), right@.len()) == 0 ==> outcomes.len() == 0) && (cmp_min_len(left@.len(), right@.len()) > 0 ==> outcomes.len() > 0) && (outcomes.len() < cmp_min_len(left@.len(), right@.len()) ==> outcomes.last() != Some(core::cmp::Ordering::Equal)) && (result <==> if outcomes.len() > 0 && outcomes.last() != Some(core::cmp::Ordering::Equal) { outcomes.last() is Some && cmp_relation_holds(CmpRelation::Ge, outcomes.last()->0) } else { cmp_relation_holds(CmpRelation::Ge, cmp_length_order(left@.len(), right@.len())) }),
        cmp_slice_order_dispatch(left@, right@) == CmpOrderDispatch::UnsignedBytewiseOrd ==> (result <==> cmp_relation_holds(CmpRelation::Ge, cmp_unsigned_bytewise_order(left@, right@))),
;

// @spec-row rustdoc-11622-11617 family=tuple_short_circuit
pub assume_specification<T: PartialOrd>[
    <(T,) as PartialOrd<(T,)>>::partial_cmp
](
    left: &(T,),
    right: &(T,),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>|
            call_ensures(<T as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (result == (o0)) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == 1nat,
;

// @spec-row rustdoc-11622-11618 family=tuple_short_circuit
pub assume_specification<T: PartialOrd>[
    <(T,) as PartialOrd<(T,)>>::lt
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::lt, (&left.0, &right.0), result),
        cmp_tuple_observation_count(CmpOperation::Lt, left, right) == 1,
;

// @spec-row rustdoc-11622-11619 family=tuple_short_circuit
pub assume_specification<T: PartialOrd>[
    <(T,) as PartialOrd<(T,)>>::le
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::le, (&left.0, &right.0), result),
        cmp_tuple_observation_count(CmpOperation::Le, left, right) == 1,
;

// @spec-row rustdoc-11622-11620 family=tuple_short_circuit
pub assume_specification<T: PartialOrd>[
    <(T,) as PartialOrd<(T,)>>::ge
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::ge, (&left.0, &right.0), result),
        cmp_tuple_observation_count(CmpOperation::Ge, left, right) == 1,
;

// @spec-row rustdoc-11622-11621 family=tuple_short_circuit
pub assume_specification<T: PartialOrd>[
    <(T,) as PartialOrd<(T,)>>::gt
](
    left: &(T,),
    right: &(T,),
) -> (result: bool)
    ensures
        call_ensures(<T as PartialOrd>::gt, (&left.0, &right.0), result),
        cmp_tuple_observation_count(CmpOperation::Gt, left, right) == 1,
;

// @spec-row rustdoc-11629 family=free_ord_forwarding
pub assume_specification<T: Ord>[
    core::cmp::min::<T>
](
    v1: T,
    v2: T,
) -> (result: T)
    ensures
        call_ensures(<T as Ord>::min, (v1, v2), result),
;

// @spec-row rustdoc-11630 family=comparator_callback
pub assume_specification<T, F: FnOnce(&T, &T) -> Ordering>[
    core::cmp::min_by::<T, F>
](
    v1: T,
    v2: T,
    compare: F,
) -> (result: T)
    requires
        compare.requires((&v1, &v2)),
    ensures
        exists|order: Ordering| compare.ensures((&v1, &v2), order) && result == if order == Ordering::Less || order == Ordering::Equal { v1 } else { v2 } && cmp_comparator_observation_count(compare, &v1, &v2) == 1,
;

// @spec-row rustdoc-11631 family=key_callback_order
pub assume_specification<T, F: FnMut(&T) -> K, K: Ord>[
    core::cmp::min_by_key::<T, F, K>
](
    v1: T,
    v2: T,
    callback: F,
) -> (result: T)
    requires
        callback.requires((&v2,)),
        forall|key2: K, callback_after_v2: F| cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2) ==> callback_after_v2.requires((&v1,)),
    ensures
        exists|key2: K, key1: K, callback_after_v2: F, callback_after_v1: F, second_is_less: bool| callback.ensures((&v2,), key2) && cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2) && callback_after_v2.ensures((&v1,), key1) && cmp_fn_mut_state_transition(callback_after_v2, &v1, key1, callback_after_v1) && call_ensures(<K as PartialOrd>::lt, (&key2, &key1), second_is_less) && result == if second_is_less { v2 } else { v1 } && cmp_key_callback_observation_count(callback, &v2, &v1) == 2,
;

// @spec-row rustdoc-11632 family=free_ord_forwarding
pub assume_specification<T: Ord>[
    core::cmp::max::<T>
](
    v1: T,
    v2: T,
) -> (result: T)
    ensures
        call_ensures(<T as Ord>::max, (v1, v2), result),
;

// @spec-row rustdoc-11633 family=comparator_callback
pub assume_specification<T, F: FnOnce(&T, &T) -> Ordering>[
    core::cmp::max_by::<T, F>
](
    v1: T,
    v2: T,
    compare: F,
) -> (result: T)
    requires
        compare.requires((&v1, &v2)),
    ensures
        exists|order: Ordering| compare.ensures((&v1, &v2), order) && result == if order == Ordering::Greater { v1 } else { v2 } && cmp_comparator_observation_count(compare, &v1, &v2) == 1,
;

// @spec-row rustdoc-11634 family=key_callback_order
pub assume_specification<T, F: FnMut(&T) -> K, K: Ord>[
    core::cmp::max_by_key::<T, F, K>
](
    v1: T,
    v2: T,
    callback: F,
) -> (result: T)
    requires
        callback.requires((&v2,)),
        forall|key2: K, callback_after_v2: F| cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2) ==> callback_after_v2.requires((&v1,)),
    ensures
        exists|key2: K, key1: K, callback_after_v2: F, callback_after_v1: F, second_is_less: bool| callback.ensures((&v2,), key2) && cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2) && callback_after_v2.ensures((&v1,), key1) && cmp_fn_mut_state_transition(callback_after_v2, &v1, key1, callback_after_v1) && call_ensures(<K as PartialOrd>::lt, (&key2, &key1), second_is_less) && result == if second_is_less { v1 } else { v2 } && cmp_key_callback_observation_count(callback, &v2, &v1) == 2,
;

// @spec-row rustdoc-9698-9697 family=ordering_value
pub assume_specification[
    <Ordering as Clone>::clone
](
    source: &Ordering,
) -> (result: Ordering)
    ensures
        result == *source,
;

// @spec-row rustdoc-9702-9699 family=reverse_clone
pub assume_specification<T: Clone>[
    <Reverse<T> as Clone>::clone
](
    source: &Reverse<T>,
) -> (result: Reverse<T>)
    ensures
        cloned::<T>(source.0, result.0),
;

// @spec-row rustdoc-9702-9701 family=reverse_clone
pub assume_specification<T: Clone>[
    <Reverse<T> as Clone>::clone_from
](
    target: &mut Reverse<T>,
    source: &Reverse<T>,
)
    ensures
        cmp_clone_from_effect(old(target).0, source.0, final(target).0),
;

// @spec-row source-trait-default-eq-assert_receiver_is_total_eq family=empty_eq_default
#[allow(deprecated)]
pub open spec fn cmp_eq_assert_receiver_is_total_eq_contract<
    T: Eq + ?Sized,
>(
    receiver: &T,
) -> bool {
    true
}

// @spec-row source-tuple-arity-02-ord-cmp family=tuple_short_circuit
pub assume_specification<U: Ord, T: Ord>[
    <(U, T) as Ord>::cmp
](
    left: &(U, T),
    right: &(U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering|
            call_ensures(<U as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { o1 } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialeq-eq family=tuple_short_circuit
pub assume_specification<U: PartialEq, T: PartialEq>[
    <(U, T) as PartialEq<(U, T)>>::eq
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool|
            call_ensures(<U as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<T as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (result <==> (o0 && o1)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialeq-ne family=tuple_short_circuit
pub assume_specification<U: PartialEq, T: PartialEq>[
    <(U, T) as PartialEq<(U, T)>>::ne
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool|
            call_ensures(<U as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<T as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (result <==> (o0 || o1)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialord-ge family=tuple_short_circuit
pub assume_specification<U: PartialOrd, T: PartialOrd>[
    <(U, T) as PartialOrd<(U, T)>>::ge
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, last)) &&
            call_ensures(<U as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.1, &right.1), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { last } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialord-gt family=tuple_short_circuit
pub assume_specification<U: PartialOrd, T: PartialOrd>[
    <(U, T) as PartialOrd<(U, T)>>::gt
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, last)) &&
            call_ensures(<U as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.1, &right.1), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { last } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialord-le family=tuple_short_circuit
pub assume_specification<U: PartialOrd, T: PartialOrd>[
    <(U, T) as PartialOrd<(U, T)>>::le
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, last)) &&
            call_ensures(<U as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.1, &right.1), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { last } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialord-lt family=tuple_short_circuit
pub assume_specification<U: PartialOrd, T: PartialOrd>[
    <(U, T) as PartialOrd<(U, T)>>::lt
](
    left: &(U, T),
    right: &(U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, last)) &&
            call_ensures(<U as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.1, &right.1), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { last } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-02-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<U: PartialOrd, T: PartialOrd>[
    <(U, T) as PartialOrd<(U, T)>>::partial_cmp
](
    left: &(U, T),
    right: &(U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>|
            call_ensures(<U as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { o1 } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { 2nat },
;

// @spec-row source-tuple-arity-03-ord-cmp family=tuple_short_circuit
pub assume_specification<V: Ord, U: Ord, T: Ord>[
    <(V, U, T) as Ord>::cmp
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering|
            call_ensures(<V as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { o2 } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialeq-eq family=tuple_short_circuit
pub assume_specification<V: PartialEq, U: PartialEq, T: PartialEq>[
    <(V, U, T) as PartialEq<(V, U, T)>>::eq
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool|
            call_ensures(<V as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<U as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<T as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (result <==> (o0 && o1 && o2)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialeq-ne family=tuple_short_circuit
pub assume_specification<V: PartialEq, U: PartialEq, T: PartialEq>[
    <(V, U, T) as PartialEq<(V, U, T)>>::ne
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool|
            call_ensures(<V as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<U as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<T as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (result <==> (o0 || o1 || o2)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialord-ge family=tuple_short_circuit
pub assume_specification<V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(V, U, T) as PartialOrd<(V, U, T)>>::ge
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, last)) &&
            call_ensures(<V as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.2, &right.2), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { last } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialord-gt family=tuple_short_circuit
pub assume_specification<V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(V, U, T) as PartialOrd<(V, U, T)>>::gt
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, last)) &&
            call_ensures(<V as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.2, &right.2), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { last } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialord-le family=tuple_short_circuit
pub assume_specification<V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(V, U, T) as PartialOrd<(V, U, T)>>::le
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, last)) &&
            call_ensures(<V as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.2, &right.2), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { last } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialord-lt family=tuple_short_circuit
pub assume_specification<V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(V, U, T) as PartialOrd<(V, U, T)>>::lt
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, last)) &&
            call_ensures(<V as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.2, &right.2), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { last } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-03-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(V, U, T) as PartialOrd<(V, U, T)>>::partial_cmp
](
    left: &(V, U, T),
    right: &(V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>|
            call_ensures(<V as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { o2 } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { 3nat } },
;

// @spec-row source-tuple-arity-04-ord-cmp family=tuple_short_circuit
pub assume_specification<W: Ord, V: Ord, U: Ord, T: Ord>[
    <(W, V, U, T) as Ord>::cmp
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering|
            call_ensures(<W as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { o3 } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialeq-eq family=tuple_short_circuit
pub assume_specification<W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(W, V, U, T) as PartialEq<(W, V, U, T)>>::eq
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool|
            call_ensures(<W as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<V as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<U as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<T as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (result <==> (o0 && o1 && o2 && o3)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialeq-ne family=tuple_short_circuit
pub assume_specification<W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(W, V, U, T) as PartialEq<(W, V, U, T)>>::ne
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool|
            call_ensures(<W as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<V as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<U as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<T as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (result <==> (o0 || o1 || o2 || o3)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialord-ge family=tuple_short_circuit
pub assume_specification<W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(W, V, U, T) as PartialOrd<(W, V, U, T)>>::ge
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, last)) &&
            call_ensures(<W as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.3, &right.3), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { last } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialord-gt family=tuple_short_circuit
pub assume_specification<W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(W, V, U, T) as PartialOrd<(W, V, U, T)>>::gt
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, last)) &&
            call_ensures(<W as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.3, &right.3), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { last } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialord-le family=tuple_short_circuit
pub assume_specification<W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(W, V, U, T) as PartialOrd<(W, V, U, T)>>::le
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, last)) &&
            call_ensures(<W as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.3, &right.3), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { last } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialord-lt family=tuple_short_circuit
pub assume_specification<W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(W, V, U, T) as PartialOrd<(W, V, U, T)>>::lt
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, last)) &&
            call_ensures(<W as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.3, &right.3), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { last } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-04-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(W, V, U, T) as PartialOrd<(W, V, U, T)>>::partial_cmp
](
    left: &(W, V, U, T),
    right: &(W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>|
            call_ensures(<W as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { o3 } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { 4nat } } },
;

// @spec-row source-tuple-arity-05-ord-cmp family=tuple_short_circuit
pub assume_specification<X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(X, W, V, U, T) as Ord>::cmp
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering|
            call_ensures(<X as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { o4 } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialeq-eq family=tuple_short_circuit
pub assume_specification<X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(X, W, V, U, T) as PartialEq<(X, W, V, U, T)>>::eq
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool|
            call_ensures(<X as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<W as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<V as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<U as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<T as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialeq-ne family=tuple_short_circuit
pub assume_specification<X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(X, W, V, U, T) as PartialEq<(X, W, V, U, T)>>::ne
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool|
            call_ensures(<X as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<W as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<V as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<U as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<T as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialord-ge family=tuple_short_circuit
pub assume_specification<X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(X, W, V, U, T) as PartialOrd<(X, W, V, U, T)>>::ge
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, last)) &&
            call_ensures(<X as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.4, &right.4), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { last } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialord-gt family=tuple_short_circuit
pub assume_specification<X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(X, W, V, U, T) as PartialOrd<(X, W, V, U, T)>>::gt
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, last)) &&
            call_ensures(<X as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.4, &right.4), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { last } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialord-le family=tuple_short_circuit
pub assume_specification<X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(X, W, V, U, T) as PartialOrd<(X, W, V, U, T)>>::le
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, last)) &&
            call_ensures(<X as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.4, &right.4), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { last } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialord-lt family=tuple_short_circuit
pub assume_specification<X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(X, W, V, U, T) as PartialOrd<(X, W, V, U, T)>>::lt
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, last)) &&
            call_ensures(<X as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.4, &right.4), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { last } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-05-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(X, W, V, U, T) as PartialOrd<(X, W, V, U, T)>>::partial_cmp
](
    left: &(X, W, V, U, T),
    right: &(X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>|
            call_ensures(<X as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { o4 } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { 5nat } } } },
;

// @spec-row source-tuple-arity-06-ord-cmp family=tuple_short_circuit
pub assume_specification<Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering|
            call_ensures(<Y as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { o5 } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialeq-eq family=tuple_short_circuit
pub assume_specification<Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(Y, X, W, V, U, T) as PartialEq<(Y, X, W, V, U, T)>>::eq
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool|
            call_ensures(<Y as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<X as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<W as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<V as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<U as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<T as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialeq-ne family=tuple_short_circuit
pub assume_specification<Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(Y, X, W, V, U, T) as PartialEq<(Y, X, W, V, U, T)>>::ne
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool|
            call_ensures(<Y as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<X as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<W as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<V as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<U as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<T as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialord-ge family=tuple_short_circuit
pub assume_specification<Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Y, X, W, V, U, T) as PartialOrd<(Y, X, W, V, U, T)>>::ge
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, last)) &&
            call_ensures(<Y as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.5, &right.5), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { last } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialord-gt family=tuple_short_circuit
pub assume_specification<Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Y, X, W, V, U, T) as PartialOrd<(Y, X, W, V, U, T)>>::gt
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, last)) &&
            call_ensures(<Y as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.5, &right.5), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { last } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialord-le family=tuple_short_circuit
pub assume_specification<Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Y, X, W, V, U, T) as PartialOrd<(Y, X, W, V, U, T)>>::le
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, last)) &&
            call_ensures(<Y as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.5, &right.5), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { last } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialord-lt family=tuple_short_circuit
pub assume_specification<Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Y, X, W, V, U, T) as PartialOrd<(Y, X, W, V, U, T)>>::lt
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, last)) &&
            call_ensures(<Y as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.5, &right.5), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { last } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-06-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Y, X, W, V, U, T) as PartialOrd<(Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(Y, X, W, V, U, T),
    right: &(Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>|
            call_ensures(<Y as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { o5 } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { 6nat } } } } },
;

// @spec-row source-tuple-arity-07-ord-cmp family=tuple_short_circuit
pub assume_specification<Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering|
            call_ensures(<Z as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { o6 } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialeq-eq family=tuple_short_circuit
pub assume_specification<Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(Z, Y, X, W, V, U, T) as PartialEq<(Z, Y, X, W, V, U, T)>>::eq
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool|
            call_ensures(<Z as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<Y as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<X as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<W as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<V as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<U as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<T as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialeq-ne family=tuple_short_circuit
pub assume_specification<Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(Z, Y, X, W, V, U, T) as PartialEq<(Z, Y, X, W, V, U, T)>>::ne
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool|
            call_ensures(<Z as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<Y as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<X as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<W as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<V as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<U as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<T as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialord-ge family=tuple_short_circuit
pub assume_specification<Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Z, Y, X, W, V, U, T) as PartialOrd<(Z, Y, X, W, V, U, T)>>::ge
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, last)) &&
            call_ensures(<Z as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.6, &right.6), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { last } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialord-gt family=tuple_short_circuit
pub assume_specification<Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Z, Y, X, W, V, U, T) as PartialOrd<(Z, Y, X, W, V, U, T)>>::gt
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, last)) &&
            call_ensures(<Z as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.6, &right.6), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { last } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialord-le family=tuple_short_circuit
pub assume_specification<Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Z, Y, X, W, V, U, T) as PartialOrd<(Z, Y, X, W, V, U, T)>>::le
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, last)) &&
            call_ensures(<Z as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.6, &right.6), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { last } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialord-lt family=tuple_short_circuit
pub assume_specification<Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Z, Y, X, W, V, U, T) as PartialOrd<(Z, Y, X, W, V, U, T)>>::lt
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, last)) &&
            call_ensures(<Z as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.6, &right.6), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { last } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-07-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(Z, Y, X, W, V, U, T) as PartialOrd<(Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(Z, Y, X, W, V, U, T),
    right: &(Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>|
            call_ensures(<Z as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { o6 } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { 7nat } } } } } },
;

// @spec-row source-tuple-arity-08-ord-cmp family=tuple_short_circuit
pub assume_specification<A: Ord, Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(A, Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering, o7: core::cmp::Ordering|
            call_ensures(<A as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<Z as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.7, &right.7), o7)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { if o6 == core::cmp::Ordering::Equal { o7 } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { if o6 != core::cmp::Ordering::Equal { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialeq-eq family=tuple_short_circuit
pub assume_specification<A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(A, Z, Y, X, W, V, U, T) as PartialEq<(A, Z, Y, X, W, V, U, T)>>::eq
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool|
            call_ensures(<A as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<Z as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<Y as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<X as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<W as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<V as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<U as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 ==> call_ensures(<T as PartialEq>::eq, (&left.7, &right.7), o7)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { if !o6 { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialeq-ne family=tuple_short_circuit
pub assume_specification<A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(A, Z, Y, X, W, V, U, T) as PartialEq<(A, Z, Y, X, W, V, U, T)>>::ne
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool|
            call_ensures(<A as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<Z as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<Y as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<X as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<W as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<V as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<U as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 ==> call_ensures(<T as PartialEq>::ne, (&left.7, &right.7), o7)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6 || o7)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { if o6 { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialord-ge family=tuple_short_circuit
pub assume_specification<A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(A, Z, Y, X, W, V, U, T) as PartialOrd<(A, Z, Y, X, W, V, U, T)>>::ge
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, last)) &&
            call_ensures(<A as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.7, &right.7), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Ge, outcome6->0) } else { last } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialord-gt family=tuple_short_circuit
pub assume_specification<A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(A, Z, Y, X, W, V, U, T) as PartialOrd<(A, Z, Y, X, W, V, U, T)>>::gt
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, last)) &&
            call_ensures(<A as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.7, &right.7), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Gt, outcome6->0) } else { last } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialord-le family=tuple_short_circuit
pub assume_specification<A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(A, Z, Y, X, W, V, U, T) as PartialOrd<(A, Z, Y, X, W, V, U, T)>>::le
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, last)) &&
            call_ensures(<A as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.7, &right.7), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Le, outcome6->0) } else { last } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialord-lt family=tuple_short_circuit
pub assume_specification<A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(A, Z, Y, X, W, V, U, T) as PartialOrd<(A, Z, Y, X, W, V, U, T)>>::lt
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, last)) &&
            call_ensures(<A as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.7, &right.7), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Lt, outcome6->0) } else { last } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-08-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(A, Z, Y, X, W, V, U, T) as PartialOrd<(A, Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(A, Z, Y, X, W, V, U, T),
    right: &(A, Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>, o7: Option<core::cmp::Ordering>|
            call_ensures(<A as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.7, &right.7), o7)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { if o6 == Some(core::cmp::Ordering::Equal) { o7 } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if o6 != Some(core::cmp::Ordering::Equal) { 7nat } else { 8nat } } } } } } },
;

// @spec-row source-tuple-arity-09-ord-cmp family=tuple_short_circuit
pub assume_specification<B: Ord, A: Ord, Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(B, A, Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering, o7: core::cmp::Ordering, o8: core::cmp::Ordering|
            call_ensures(<B as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<A as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<Z as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.7, &right.7), o7)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.8, &right.8), o8)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { if o6 == core::cmp::Ordering::Equal { if o7 == core::cmp::Ordering::Equal { o8 } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { if o6 != core::cmp::Ordering::Equal { 7nat } else { if o7 != core::cmp::Ordering::Equal { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialeq-eq family=tuple_short_circuit
pub assume_specification<B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialEq<(B, A, Z, Y, X, W, V, U, T)>>::eq
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool|
            call_ensures(<B as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<A as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<Z as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<Y as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<X as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<W as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<V as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 ==> call_ensures(<U as PartialEq>::eq, (&left.7, &right.7), o7)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 ==> call_ensures(<T as PartialEq>::eq, (&left.8, &right.8), o8)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { if !o6 { 7nat } else { if !o7 { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialeq-ne family=tuple_short_circuit
pub assume_specification<B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialEq<(B, A, Z, Y, X, W, V, U, T)>>::ne
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool|
            call_ensures(<B as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<A as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<Z as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<Y as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<X as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<W as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<V as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 ==> call_ensures(<U as PartialEq>::ne, (&left.7, &right.7), o7)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 ==> call_ensures(<T as PartialEq>::ne, (&left.8, &right.8), o8)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6 || o7 || o8)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { if o6 { 7nat } else { if o7 { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialord-ge family=tuple_short_circuit
pub assume_specification<B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialOrd<(B, A, Z, Y, X, W, V, U, T)>>::ge
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, last)) &&
            call_ensures(<B as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.8, &right.8), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Ge, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Ge, outcome7->0) } else { last } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialord-gt family=tuple_short_circuit
pub assume_specification<B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialOrd<(B, A, Z, Y, X, W, V, U, T)>>::gt
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, last)) &&
            call_ensures(<B as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.8, &right.8), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Gt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Gt, outcome7->0) } else { last } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialord-le family=tuple_short_circuit
pub assume_specification<B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialOrd<(B, A, Z, Y, X, W, V, U, T)>>::le
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, last)) &&
            call_ensures(<B as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.8, &right.8), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Le, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Le, outcome7->0) } else { last } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialord-lt family=tuple_short_circuit
pub assume_specification<B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialOrd<(B, A, Z, Y, X, W, V, U, T)>>::lt
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, last)) &&
            call_ensures(<B as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.8, &right.8), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Lt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Lt, outcome7->0) } else { last } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-09-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(B, A, Z, Y, X, W, V, U, T) as PartialOrd<(B, A, Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(B, A, Z, Y, X, W, V, U, T),
    right: &(B, A, Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>, o7: Option<core::cmp::Ordering>, o8: Option<core::cmp::Ordering>|
            call_ensures(<B as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.7, &right.7), o7)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.8, &right.8), o8)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { if o6 == Some(core::cmp::Ordering::Equal) { if o7 == Some(core::cmp::Ordering::Equal) { o8 } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if o6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if o7 != Some(core::cmp::Ordering::Equal) { 8nat } else { 9nat } } } } } } } },
;

// @spec-row source-tuple-arity-10-ord-cmp family=tuple_short_circuit
pub assume_specification<C: Ord, B: Ord, A: Ord, Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(C, B, A, Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering, o7: core::cmp::Ordering, o8: core::cmp::Ordering, o9: core::cmp::Ordering|
            call_ensures(<C as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<B as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<A as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<Z as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.7, &right.7), o7)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.8, &right.8), o8)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.9, &right.9), o9)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { if o6 == core::cmp::Ordering::Equal { if o7 == core::cmp::Ordering::Equal { if o8 == core::cmp::Ordering::Equal { o9 } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { if o6 != core::cmp::Ordering::Equal { 7nat } else { if o7 != core::cmp::Ordering::Equal { 8nat } else { if o8 != core::cmp::Ordering::Equal { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialeq-eq family=tuple_short_circuit
pub assume_specification<C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(C, B, A, Z, Y, X, W, V, U, T)>>::eq
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool|
            call_ensures(<C as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<B as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<A as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<Z as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<Y as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<X as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<W as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 ==> call_ensures(<V as PartialEq>::eq, (&left.7, &right.7), o7)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 ==> call_ensures(<U as PartialEq>::eq, (&left.8, &right.8), o8)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 ==> call_ensures(<T as PartialEq>::eq, (&left.9, &right.9), o9)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { if !o6 { 7nat } else { if !o7 { 8nat } else { if !o8 { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialeq-ne family=tuple_short_circuit
pub assume_specification<C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(C, B, A, Z, Y, X, W, V, U, T)>>::ne
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool|
            call_ensures(<C as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<B as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<A as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<Z as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<Y as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<X as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<W as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 ==> call_ensures(<V as PartialEq>::ne, (&left.7, &right.7), o7)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 ==> call_ensures(<U as PartialEq>::ne, (&left.8, &right.8), o8)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 ==> call_ensures(<T as PartialEq>::ne, (&left.9, &right.9), o9)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6 || o7 || o8 || o9)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { if o6 { 7nat } else { if o7 { 8nat } else { if o8 { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialord-ge family=tuple_short_circuit
pub assume_specification<C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(C, B, A, Z, Y, X, W, V, U, T)>>::ge
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, last)) &&
            call_ensures(<C as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.9, &right.9), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Ge, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Ge, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Ge, outcome8->0) } else { last } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialord-gt family=tuple_short_circuit
pub assume_specification<C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(C, B, A, Z, Y, X, W, V, U, T)>>::gt
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, last)) &&
            call_ensures(<C as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.9, &right.9), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Gt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Gt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Gt, outcome8->0) } else { last } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialord-le family=tuple_short_circuit
pub assume_specification<C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(C, B, A, Z, Y, X, W, V, U, T)>>::le
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, last)) &&
            call_ensures(<C as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.9, &right.9), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Le, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Le, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Le, outcome8->0) } else { last } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialord-lt family=tuple_short_circuit
pub assume_specification<C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(C, B, A, Z, Y, X, W, V, U, T)>>::lt
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, last)) &&
            call_ensures(<C as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.9, &right.9), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Lt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Lt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Lt, outcome8->0) } else { last } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-10-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(C, B, A, Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(C, B, A, Z, Y, X, W, V, U, T),
    right: &(C, B, A, Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>, o7: Option<core::cmp::Ordering>, o8: Option<core::cmp::Ordering>, o9: Option<core::cmp::Ordering>|
            call_ensures(<C as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.7, &right.7), o7)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.8, &right.8), o8)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.9, &right.9), o9)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { if o6 == Some(core::cmp::Ordering::Equal) { if o7 == Some(core::cmp::Ordering::Equal) { if o8 == Some(core::cmp::Ordering::Equal) { o9 } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if o6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if o7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if o8 != Some(core::cmp::Ordering::Equal) { 9nat } else { 10nat } } } } } } } } },
;

// @spec-row source-tuple-arity-11-ord-cmp family=tuple_short_circuit
pub assume_specification<D: Ord, C: Ord, B: Ord, A: Ord, Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering, o7: core::cmp::Ordering, o8: core::cmp::Ordering, o9: core::cmp::Ordering, o10: core::cmp::Ordering|
            call_ensures(<D as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<C as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<B as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<A as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<Z as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.7, &right.7), o7)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.8, &right.8), o8)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.9, &right.9), o9)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal && o9 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.10, &right.10), o10)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { if o6 == core::cmp::Ordering::Equal { if o7 == core::cmp::Ordering::Equal { if o8 == core::cmp::Ordering::Equal { if o9 == core::cmp::Ordering::Equal { o10 } else { o9 } } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { if o6 != core::cmp::Ordering::Equal { 7nat } else { if o7 != core::cmp::Ordering::Equal { 8nat } else { if o8 != core::cmp::Ordering::Equal { 9nat } else { if o9 != core::cmp::Ordering::Equal { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialeq-eq family=tuple_short_circuit
pub assume_specification<D: PartialEq, C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(D, C, B, A, Z, Y, X, W, V, U, T)>>::eq
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool, o10: bool|
            call_ensures(<D as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<C as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<B as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<A as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<Z as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<Y as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<X as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 ==> call_ensures(<W as PartialEq>::eq, (&left.7, &right.7), o7)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 ==> call_ensures(<V as PartialEq>::eq, (&left.8, &right.8), o8)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 ==> call_ensures(<U as PartialEq>::eq, (&left.9, &right.9), o9)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9 ==> call_ensures(<T as PartialEq>::eq, (&left.10, &right.10), o10)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9 && o10)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { if !o6 { 7nat } else { if !o7 { 8nat } else { if !o8 { 9nat } else { if !o9 { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialeq-ne family=tuple_short_circuit
pub assume_specification<D: PartialEq, C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(D, C, B, A, Z, Y, X, W, V, U, T)>>::ne
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool, o10: bool|
            call_ensures(<D as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<C as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<B as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<A as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<Z as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<Y as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<X as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 ==> call_ensures(<W as PartialEq>::ne, (&left.7, &right.7), o7)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 ==> call_ensures(<V as PartialEq>::ne, (&left.8, &right.8), o8)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 ==> call_ensures(<U as PartialEq>::ne, (&left.9, &right.9), o9)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 && !o9 ==> call_ensures(<T as PartialEq>::ne, (&left.10, &right.10), o10)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6 || o7 || o8 || o9 || o10)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { if o6 { 7nat } else { if o7 { 8nat } else { if o8 { 9nat } else { if o9 { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialord-ge family=tuple_short_circuit
pub assume_specification<D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(D, C, B, A, Z, Y, X, W, V, U, T)>>::ge
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, last)) &&
            call_ensures(<D as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.10, &right.10), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Ge, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Ge, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Ge, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Ge, outcome9->0) } else { last } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialord-gt family=tuple_short_circuit
pub assume_specification<D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(D, C, B, A, Z, Y, X, W, V, U, T)>>::gt
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, last)) &&
            call_ensures(<D as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.10, &right.10), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Gt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Gt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Gt, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Gt, outcome9->0) } else { last } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialord-le family=tuple_short_circuit
pub assume_specification<D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(D, C, B, A, Z, Y, X, W, V, U, T)>>::le
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, last)) &&
            call_ensures(<D as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.10, &right.10), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Le, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Le, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Le, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Le, outcome9->0) } else { last } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialord-lt family=tuple_short_circuit
pub assume_specification<D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(D, C, B, A, Z, Y, X, W, V, U, T)>>::lt
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, last)) &&
            call_ensures(<D as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.10, &right.10), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Lt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Lt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Lt, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Lt, outcome9->0) } else { last } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-11-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(D, C, B, A, Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>, o7: Option<core::cmp::Ordering>, o8: Option<core::cmp::Ordering>, o9: Option<core::cmp::Ordering>, o10: Option<core::cmp::Ordering>|
            call_ensures(<D as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.7, &right.7), o7)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.8, &right.8), o8)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.9, &right.9), o9)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) && o9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.10, &right.10), o10)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { if o6 == Some(core::cmp::Ordering::Equal) { if o7 == Some(core::cmp::Ordering::Equal) { if o8 == Some(core::cmp::Ordering::Equal) { if o9 == Some(core::cmp::Ordering::Equal) { o10 } else { o9 } } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if o6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if o7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if o8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if o9 != Some(core::cmp::Ordering::Equal) { 10nat } else { 11nat } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-ord-cmp family=tuple_short_circuit
pub assume_specification<E: Ord, D: Ord, C: Ord, B: Ord, A: Ord, Z: Ord, Y: Ord, X: Ord, W: Ord, V: Ord, U: Ord, T: Ord>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as Ord>::cmp
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: core::cmp::Ordering)
    ensures
        exists|o0: core::cmp::Ordering, o1: core::cmp::Ordering, o2: core::cmp::Ordering, o3: core::cmp::Ordering, o4: core::cmp::Ordering, o5: core::cmp::Ordering, o6: core::cmp::Ordering, o7: core::cmp::Ordering, o8: core::cmp::Ordering, o9: core::cmp::Ordering, o10: core::cmp::Ordering, o11: core::cmp::Ordering|
            call_ensures(<E as Ord>::cmp, (&left.0, &right.0), o0) &&
            (o0 == core::cmp::Ordering::Equal ==> call_ensures(<D as Ord>::cmp, (&left.1, &right.1), o1)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal ==> call_ensures(<C as Ord>::cmp, (&left.2, &right.2), o2)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal ==> call_ensures(<B as Ord>::cmp, (&left.3, &right.3), o3)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal ==> call_ensures(<A as Ord>::cmp, (&left.4, &right.4), o4)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal ==> call_ensures(<Z as Ord>::cmp, (&left.5, &right.5), o5)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal ==> call_ensures(<Y as Ord>::cmp, (&left.6, &right.6), o6)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal ==> call_ensures(<X as Ord>::cmp, (&left.7, &right.7), o7)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal ==> call_ensures(<W as Ord>::cmp, (&left.8, &right.8), o8)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal ==> call_ensures(<V as Ord>::cmp, (&left.9, &right.9), o9)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal && o9 == core::cmp::Ordering::Equal ==> call_ensures(<U as Ord>::cmp, (&left.10, &right.10), o10)) &&
            (o0 == core::cmp::Ordering::Equal && o1 == core::cmp::Ordering::Equal && o2 == core::cmp::Ordering::Equal && o3 == core::cmp::Ordering::Equal && o4 == core::cmp::Ordering::Equal && o5 == core::cmp::Ordering::Equal && o6 == core::cmp::Ordering::Equal && o7 == core::cmp::Ordering::Equal && o8 == core::cmp::Ordering::Equal && o9 == core::cmp::Ordering::Equal && o10 == core::cmp::Ordering::Equal ==> call_ensures(<T as Ord>::cmp, (&left.11, &right.11), o11)) &&
            (result == (if o0 == core::cmp::Ordering::Equal { if o1 == core::cmp::Ordering::Equal { if o2 == core::cmp::Ordering::Equal { if o3 == core::cmp::Ordering::Equal { if o4 == core::cmp::Ordering::Equal { if o5 == core::cmp::Ordering::Equal { if o6 == core::cmp::Ordering::Equal { if o7 == core::cmp::Ordering::Equal { if o8 == core::cmp::Ordering::Equal { if o9 == core::cmp::Ordering::Equal { if o10 == core::cmp::Ordering::Equal { o11 } else { o10 } } else { o9 } } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::Cmp, left, right) == if o0 != core::cmp::Ordering::Equal { 1nat } else { if o1 != core::cmp::Ordering::Equal { 2nat } else { if o2 != core::cmp::Ordering::Equal { 3nat } else { if o3 != core::cmp::Ordering::Equal { 4nat } else { if o4 != core::cmp::Ordering::Equal { 5nat } else { if o5 != core::cmp::Ordering::Equal { 6nat } else { if o6 != core::cmp::Ordering::Equal { 7nat } else { if o7 != core::cmp::Ordering::Equal { 8nat } else { if o8 != core::cmp::Ordering::Equal { 9nat } else { if o9 != core::cmp::Ordering::Equal { 10nat } else { if o10 != core::cmp::Ordering::Equal { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialeq-eq family=tuple_short_circuit
pub assume_specification<E: PartialEq, D: PartialEq, C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::eq
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool, o10: bool, o11: bool|
            call_ensures(<E as PartialEq>::eq, (&left.0, &right.0), o0) &&
            (o0 ==> call_ensures(<D as PartialEq>::eq, (&left.1, &right.1), o1)) &&
            (o0 && o1 ==> call_ensures(<C as PartialEq>::eq, (&left.2, &right.2), o2)) &&
            (o0 && o1 && o2 ==> call_ensures(<B as PartialEq>::eq, (&left.3, &right.3), o3)) &&
            (o0 && o1 && o2 && o3 ==> call_ensures(<A as PartialEq>::eq, (&left.4, &right.4), o4)) &&
            (o0 && o1 && o2 && o3 && o4 ==> call_ensures(<Z as PartialEq>::eq, (&left.5, &right.5), o5)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 ==> call_ensures(<Y as PartialEq>::eq, (&left.6, &right.6), o6)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 ==> call_ensures(<X as PartialEq>::eq, (&left.7, &right.7), o7)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 ==> call_ensures(<W as PartialEq>::eq, (&left.8, &right.8), o8)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 ==> call_ensures(<V as PartialEq>::eq, (&left.9, &right.9), o9)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9 ==> call_ensures(<U as PartialEq>::eq, (&left.10, &right.10), o10)) &&
            (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9 && o10 ==> call_ensures(<T as PartialEq>::eq, (&left.11, &right.11), o11)) &&
            (result <==> (o0 && o1 && o2 && o3 && o4 && o5 && o6 && o7 && o8 && o9 && o10 && o11)) &&
            cmp_tuple_observation_count(CmpOperation::Eq, left, right) == if !o0 { 1nat } else { if !o1 { 2nat } else { if !o2 { 3nat } else { if !o3 { 4nat } else { if !o4 { 5nat } else { if !o5 { 6nat } else { if !o6 { 7nat } else { if !o7 { 8nat } else { if !o8 { 9nat } else { if !o9 { 10nat } else { if !o10 { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialeq-ne family=tuple_short_circuit
pub assume_specification<E: PartialEq, D: PartialEq, C: PartialEq, B: PartialEq, A: PartialEq, Z: PartialEq, Y: PartialEq, X: PartialEq, W: PartialEq, V: PartialEq, U: PartialEq, T: PartialEq>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialEq<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::ne
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|o0: bool, o1: bool, o2: bool, o3: bool, o4: bool, o5: bool, o6: bool, o7: bool, o8: bool, o9: bool, o10: bool, o11: bool|
            call_ensures(<E as PartialEq>::ne, (&left.0, &right.0), o0) &&
            (!o0 ==> call_ensures(<D as PartialEq>::ne, (&left.1, &right.1), o1)) &&
            (!o0 && !o1 ==> call_ensures(<C as PartialEq>::ne, (&left.2, &right.2), o2)) &&
            (!o0 && !o1 && !o2 ==> call_ensures(<B as PartialEq>::ne, (&left.3, &right.3), o3)) &&
            (!o0 && !o1 && !o2 && !o3 ==> call_ensures(<A as PartialEq>::ne, (&left.4, &right.4), o4)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 ==> call_ensures(<Z as PartialEq>::ne, (&left.5, &right.5), o5)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 ==> call_ensures(<Y as PartialEq>::ne, (&left.6, &right.6), o6)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 ==> call_ensures(<X as PartialEq>::ne, (&left.7, &right.7), o7)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 ==> call_ensures(<W as PartialEq>::ne, (&left.8, &right.8), o8)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 ==> call_ensures(<V as PartialEq>::ne, (&left.9, &right.9), o9)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 && !o9 ==> call_ensures(<U as PartialEq>::ne, (&left.10, &right.10), o10)) &&
            (!o0 && !o1 && !o2 && !o3 && !o4 && !o5 && !o6 && !o7 && !o8 && !o9 && !o10 ==> call_ensures(<T as PartialEq>::ne, (&left.11, &right.11), o11)) &&
            (result <==> (o0 || o1 || o2 || o3 || o4 || o5 || o6 || o7 || o8 || o9 || o10 || o11)) &&
            cmp_tuple_observation_count(CmpOperation::Ne, left, right) == if o0 { 1nat } else { if o1 { 2nat } else { if o2 { 3nat } else { if o3 { 4nat } else { if o4 { 5nat } else { if o5 { 6nat } else { if o6 { 7nat } else { if o7 { 8nat } else { if o8 { 9nat } else { if o9 { 10nat } else { if o10 { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialord-ge family=tuple_short_circuit
pub assume_specification<E: PartialOrd, D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::ge
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, outcome10: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, outcome10, last)) &&
            call_ensures(<E as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<D as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.10, &right.10), outcome10)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) && outcome10 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::ge, (&left.11, &right.11), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Ge, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Ge, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Ge, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Ge, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Ge, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Ge, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Ge, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Ge, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Ge, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Ge, outcome9->0) } else { if outcome10 != Some(core::cmp::Ordering::Equal) { outcome10 is Some && cmp_relation_holds(CmpRelation::Ge, outcome10->0) } else { last } } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Ge, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { if outcome10 != Some(core::cmp::Ordering::Equal) { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialord-gt family=tuple_short_circuit
pub assume_specification<E: PartialOrd, D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::gt
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, outcome10: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, outcome10, last)) &&
            call_ensures(<E as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<D as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.10, &right.10), outcome10)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) && outcome10 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::gt, (&left.11, &right.11), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Gt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Gt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Gt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Gt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Gt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Gt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Gt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Gt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Gt, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Gt, outcome9->0) } else { if outcome10 != Some(core::cmp::Ordering::Equal) { outcome10 is Some && cmp_relation_holds(CmpRelation::Gt, outcome10->0) } else { last } } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Gt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { if outcome10 != Some(core::cmp::Ordering::Equal) { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialord-le family=tuple_short_circuit
pub assume_specification<E: PartialOrd, D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::le
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, outcome10: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, outcome10, last)) &&
            call_ensures(<E as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<D as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.10, &right.10), outcome10)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) && outcome10 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::le, (&left.11, &right.11), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Le, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Le, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Le, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Le, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Le, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Le, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Le, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Le, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Le, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Le, outcome9->0) } else { if outcome10 != Some(core::cmp::Ordering::Equal) { outcome10 is Some && cmp_relation_holds(CmpRelation::Le, outcome10->0) } else { last } } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Le, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { if outcome10 != Some(core::cmp::Ordering::Equal) { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialord-lt family=tuple_short_circuit
pub assume_specification<E: PartialOrd, D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::lt
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: bool)
    ensures
        exists|outcome0: Option<core::cmp::Ordering>, outcome1: Option<core::cmp::Ordering>, outcome2: Option<core::cmp::Ordering>, outcome3: Option<core::cmp::Ordering>, outcome4: Option<core::cmp::Ordering>, outcome5: Option<core::cmp::Ordering>, outcome6: Option<core::cmp::Ordering>, outcome7: Option<core::cmp::Ordering>, outcome8: Option<core::cmp::Ordering>, outcome9: Option<core::cmp::Ordering>, outcome10: Option<core::cmp::Ordering>, last: bool|
            #[trigger] cmp_tuple_chaining_trigger((outcome0, outcome1, outcome2, outcome3, outcome4, outcome5, outcome6, outcome7, outcome8, outcome9, outcome10, last)) &&
            call_ensures(<E as PartialOrd>::partial_cmp, (&left.0, &right.0), outcome0) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<D as PartialOrd>::partial_cmp, (&left.1, &right.1), outcome1)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.2, &right.2), outcome2)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.3, &right.3), outcome3)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.4, &right.4), outcome4)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.5, &right.5), outcome5)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.6, &right.6), outcome6)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.7, &right.7), outcome7)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.8, &right.8), outcome8)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.9, &right.9), outcome9)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.10, &right.10), outcome10)) &&
            (outcome0 == Some(core::cmp::Ordering::Equal) && outcome1 == Some(core::cmp::Ordering::Equal) && outcome2 == Some(core::cmp::Ordering::Equal) && outcome3 == Some(core::cmp::Ordering::Equal) && outcome4 == Some(core::cmp::Ordering::Equal) && outcome5 == Some(core::cmp::Ordering::Equal) && outcome6 == Some(core::cmp::Ordering::Equal) && outcome7 == Some(core::cmp::Ordering::Equal) && outcome8 == Some(core::cmp::Ordering::Equal) && outcome9 == Some(core::cmp::Ordering::Equal) && outcome10 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::lt, (&left.11, &right.11), last)) &&
            result == if outcome0 != Some(core::cmp::Ordering::Equal) { outcome0 is Some && cmp_relation_holds(CmpRelation::Lt, outcome0->0) } else { if outcome1 != Some(core::cmp::Ordering::Equal) { outcome1 is Some && cmp_relation_holds(CmpRelation::Lt, outcome1->0) } else { if outcome2 != Some(core::cmp::Ordering::Equal) { outcome2 is Some && cmp_relation_holds(CmpRelation::Lt, outcome2->0) } else { if outcome3 != Some(core::cmp::Ordering::Equal) { outcome3 is Some && cmp_relation_holds(CmpRelation::Lt, outcome3->0) } else { if outcome4 != Some(core::cmp::Ordering::Equal) { outcome4 is Some && cmp_relation_holds(CmpRelation::Lt, outcome4->0) } else { if outcome5 != Some(core::cmp::Ordering::Equal) { outcome5 is Some && cmp_relation_holds(CmpRelation::Lt, outcome5->0) } else { if outcome6 != Some(core::cmp::Ordering::Equal) { outcome6 is Some && cmp_relation_holds(CmpRelation::Lt, outcome6->0) } else { if outcome7 != Some(core::cmp::Ordering::Equal) { outcome7 is Some && cmp_relation_holds(CmpRelation::Lt, outcome7->0) } else { if outcome8 != Some(core::cmp::Ordering::Equal) { outcome8 is Some && cmp_relation_holds(CmpRelation::Lt, outcome8->0) } else { if outcome9 != Some(core::cmp::Ordering::Equal) { outcome9 is Some && cmp_relation_holds(CmpRelation::Lt, outcome9->0) } else { if outcome10 != Some(core::cmp::Ordering::Equal) { outcome10 is Some && cmp_relation_holds(CmpRelation::Lt, outcome10->0) } else { last } } } } } } } } } } } &&
            cmp_tuple_observation_count(CmpOperation::Lt, left, right) == if outcome0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if outcome1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if outcome2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if outcome3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if outcome4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if outcome5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if outcome6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if outcome7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if outcome8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if outcome9 != Some(core::cmp::Ordering::Equal) { 10nat } else { if outcome10 != Some(core::cmp::Ordering::Equal) { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row source-tuple-arity-12-partialord-partial_cmp family=tuple_short_circuit
pub assume_specification<E: PartialOrd, D: PartialOrd, C: PartialOrd, B: PartialOrd, A: PartialOrd, Z: PartialOrd, Y: PartialOrd, X: PartialOrd, W: PartialOrd, V: PartialOrd, U: PartialOrd, T: PartialOrd>[
    <(E, D, C, B, A, Z, Y, X, W, V, U, T) as PartialOrd<(E, D, C, B, A, Z, Y, X, W, V, U, T)>>::partial_cmp
](
    left: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
    right: &(E, D, C, B, A, Z, Y, X, W, V, U, T),
) -> (result: Option<core::cmp::Ordering>)
    ensures
        exists|o0: Option<core::cmp::Ordering>, o1: Option<core::cmp::Ordering>, o2: Option<core::cmp::Ordering>, o3: Option<core::cmp::Ordering>, o4: Option<core::cmp::Ordering>, o5: Option<core::cmp::Ordering>, o6: Option<core::cmp::Ordering>, o7: Option<core::cmp::Ordering>, o8: Option<core::cmp::Ordering>, o9: Option<core::cmp::Ordering>, o10: Option<core::cmp::Ordering>, o11: Option<core::cmp::Ordering>|
            call_ensures(<E as PartialOrd>::partial_cmp, (&left.0, &right.0), o0) &&
            (o0 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<D as PartialOrd>::partial_cmp, (&left.1, &right.1), o1)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<C as PartialOrd>::partial_cmp, (&left.2, &right.2), o2)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<B as PartialOrd>::partial_cmp, (&left.3, &right.3), o3)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<A as PartialOrd>::partial_cmp, (&left.4, &right.4), o4)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Z as PartialOrd>::partial_cmp, (&left.5, &right.5), o5)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<Y as PartialOrd>::partial_cmp, (&left.6, &right.6), o6)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<X as PartialOrd>::partial_cmp, (&left.7, &right.7), o7)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<W as PartialOrd>::partial_cmp, (&left.8, &right.8), o8)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<V as PartialOrd>::partial_cmp, (&left.9, &right.9), o9)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) && o9 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<U as PartialOrd>::partial_cmp, (&left.10, &right.10), o10)) &&
            (o0 == Some(core::cmp::Ordering::Equal) && o1 == Some(core::cmp::Ordering::Equal) && o2 == Some(core::cmp::Ordering::Equal) && o3 == Some(core::cmp::Ordering::Equal) && o4 == Some(core::cmp::Ordering::Equal) && o5 == Some(core::cmp::Ordering::Equal) && o6 == Some(core::cmp::Ordering::Equal) && o7 == Some(core::cmp::Ordering::Equal) && o8 == Some(core::cmp::Ordering::Equal) && o9 == Some(core::cmp::Ordering::Equal) && o10 == Some(core::cmp::Ordering::Equal) ==> call_ensures(<T as PartialOrd>::partial_cmp, (&left.11, &right.11), o11)) &&
            (result == (if o0 == Some(core::cmp::Ordering::Equal) { if o1 == Some(core::cmp::Ordering::Equal) { if o2 == Some(core::cmp::Ordering::Equal) { if o3 == Some(core::cmp::Ordering::Equal) { if o4 == Some(core::cmp::Ordering::Equal) { if o5 == Some(core::cmp::Ordering::Equal) { if o6 == Some(core::cmp::Ordering::Equal) { if o7 == Some(core::cmp::Ordering::Equal) { if o8 == Some(core::cmp::Ordering::Equal) { if o9 == Some(core::cmp::Ordering::Equal) { if o10 == Some(core::cmp::Ordering::Equal) { o11 } else { o10 } } else { o9 } } else { o8 } } else { o7 } } else { o6 } } else { o5 } } else { o4 } } else { o3 } } else { o2 } } else { o1 } } else { o0 })) &&
            cmp_tuple_observation_count(CmpOperation::PartialCmp, left, right) == if o0 != Some(core::cmp::Ordering::Equal) { 1nat } else { if o1 != Some(core::cmp::Ordering::Equal) { 2nat } else { if o2 != Some(core::cmp::Ordering::Equal) { 3nat } else { if o3 != Some(core::cmp::Ordering::Equal) { 4nat } else { if o4 != Some(core::cmp::Ordering::Equal) { 5nat } else { if o5 != Some(core::cmp::Ordering::Equal) { 6nat } else { if o6 != Some(core::cmp::Ordering::Equal) { 7nat } else { if o7 != Some(core::cmp::Ordering::Equal) { 8nat } else { if o8 != Some(core::cmp::Ordering::Equal) { 9nat } else { if o9 != Some(core::cmp::Ordering::Equal) { 10nat } else { if o10 != Some(core::cmp::Ordering::Equal) { 11nat } else { 12nat } } } } } } } } } } },
;

// @spec-row trait-default-50-11241 family=trait_default_clamp
pub open spec fn cmp_ord_clamp_contract<
    Self_: Ord + PartialOrdSpec + OrdSpec,
>(
    value: Self_,
    min: Self_,
    max: Self_,
    result: CmpCallOutcome<Self_>,
) -> bool {
    Self_::obeys_partial_cmp_spec() ==> (
        result == if min.partial_cmp_spec(&max) == Some(Ordering::Greater) {
            CmpCallOutcome::Panicked
        } else {
            CmpCallOutcome::Returned(
                if value.partial_cmp_spec(&min) == Some(Ordering::Less) {
                    min
                } else if value.partial_cmp_spec(&max) == Some(Ordering::Greater) {
                    max
                } else {
                    value
                },
            )
        }
    )
}

} // verus!
