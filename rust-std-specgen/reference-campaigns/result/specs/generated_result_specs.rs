#![feature(sized_hierarchy)]
#![allow(unused_imports, dead_code)]

use core::clone::Clone;
use core::cmp::{Ord, Ordering, PartialEq, PartialOrd};
use core::default::Default;
use core::fmt::{Debug, Formatter};
use core::hash::{Hash, Hasher};
use core::iter::{
    DoubleEndedIterator, FromIterator, IntoIterator, Iterator, Product, Sum,
};
use core::ops::{Deref, DerefMut};
use core::option::Option;
use core::result::{IntoIter, Iter, IterMut, Result};
use vstd::prelude::*;
use vstd::std_specs::iter::{into_iter_remaining, FromIteratorSpec};

include!("result_shared_vocabulary.rs");

verus! {

// @spec-row rustdoc-26760
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<
    T: Sum<U>,
    U,
    E,
    I: Iterator<Item = Result<U, E>>,
>[
    <Result<T, E> as Sum<Result<U, E>>>::sum::<I>
](
    iter: I,
) -> (result: Result<T, E>)
    ensures
        result_short_circuit_trace::<U, E, T, I>(
            ResultShortCircuitOperation::Sum,
            iter,
        ).len()
            <= into_iter_remaining::<Result<U, E>, I>(iter).len(),
        forall|index: int|
            0 <= index
                < result_short_circuit_trace::<U, E, T, I>(
                    ResultShortCircuitOperation::Sum,
                    iter,
                ).len() ==>
            result_short_circuit_trace::<U, E, T, I>(
                ResultShortCircuitOperation::Sum,
                iter,
            )[index]
                == into_iter_remaining::<Result<U, E>, I>(iter)[index],
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            result_short_circuit_trace::<U, E, T, I>(
                ResultShortCircuitOperation::Sum,
                iter,
            ) == into_iter_remaining::<Result<U, E>, I>(iter),
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) <==> result is Ok,
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            exists|payloads: Seq<U>|
                result_ok_payloads_match(
                    into_iter_remaining::<Result<U, E>, I>(iter),
                    payloads,
                )
                && result == Ok(result_sum_output::<U, T>(payloads)),
        !result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            exists|stop: int|
                0 <= stop
                    < into_iter_remaining::<Result<U, E>, I>(iter).len()
                && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err
                && (forall|prior: int| 0 <= prior < stop ==>
                    into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok)
                && result_short_circuit_trace::<U, E, T, I>(
                    ResultShortCircuitOperation::Sum,
                    iter,
                ).len() == stop + 1
                && result == Err(
                    into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0
                ),
;

// @spec-row rustdoc-26882
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<
    T: Product<U>,
    U,
    E,
    I: Iterator<Item = Result<U, E>>,
>[
    <Result<T, E> as Product<Result<U, E>>>::product::<I>
](
    iter: I,
) -> (result: Result<T, E>)
    ensures
        result_short_circuit_trace::<U, E, T, I>(
            ResultShortCircuitOperation::Product,
            iter,
        ).len()
            <= into_iter_remaining::<Result<U, E>, I>(iter).len(),
        forall|index: int|
            0 <= index
                < result_short_circuit_trace::<U, E, T, I>(
                    ResultShortCircuitOperation::Product,
                    iter,
                ).len() ==>
            result_short_circuit_trace::<U, E, T, I>(
                ResultShortCircuitOperation::Product,
                iter,
            )[index]
                == into_iter_remaining::<Result<U, E>, I>(iter)[index],
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            result_short_circuit_trace::<U, E, T, I>(
                ResultShortCircuitOperation::Product,
                iter,
            ) == into_iter_remaining::<Result<U, E>, I>(iter),
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) <==> result is Ok,
        result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            exists|payloads: Seq<U>|
                result_ok_payloads_match(
                    into_iter_remaining::<Result<U, E>, I>(iter),
                    payloads,
                )
                && result == Ok(result_product_output::<U, T>(payloads)),
        !result_all_ok(
            into_iter_remaining::<Result<U, E>, I>(iter),
        ) ==>
            exists|stop: int|
                0 <= stop
                    < into_iter_remaining::<Result<U, E>, I>(iter).len()
                && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err
                && (forall|prior: int| 0 <= prior < stop ==>
                    into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok)
                && result_short_circuit_trace::<U, E, T, I>(
                    ResultShortCircuitOperation::Product,
                    iter,
                ).len() == stop + 1
                && result == Err(
                    into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0
                ),
;

// @spec-row rustdoc-29329
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Debug, E: Debug>[
    <Result<T, E> as Debug>::fmt
](
    input: &Result<T, E>,
    formatter: &mut Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        *input is Ok ==>
            result == result_formatter_debug_tuple_result(
                ResultFormatLiteral::OkName,
                input->Ok_0,
                result_formatter_state(*old(formatter)),
            ),
        *input is Ok ==>
            result_formatter_state(*final(formatter))
                == result_formatter_debug_tuple_post(
                    ResultFormatLiteral::OkName,
                    input->Ok_0,
                    result_formatter_state(*old(formatter)),
                ),
        *input is Err ==>
            result == result_formatter_debug_tuple_result(
                ResultFormatLiteral::ErrName,
                input->Err_0,
                result_formatter_state(*old(formatter)),
            ),
        *input is Err ==>
            result_formatter_state(*final(formatter))
                == result_formatter_debug_tuple_post(
                    ResultFormatLiteral::ErrName,
                    input->Err_0,
                    result_formatter_state(*old(formatter)),
                ),
;

// @spec-row rustdoc-29331
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Hash, E: Hash, H: Hasher>[
    <Result<T, E> as Hash>::hash::<H>
](
    input: &Result<T, E>,
    state: &mut H,
)
    ensures
        *input is Ok ==>
            *final(state) == result_hasher_payload_post(
                input->Ok_0,
                result_hasher_discriminant_post(0int, *old(state)),
            ),
        *input is Err ==>
            *final(state) == result_hasher_payload_post(
                input->Err_0,
                result_hasher_discriminant_post(1int, *old(state)),
            ),
;

// @spec-row rustdoc-11356
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Ord, E: Ord>[
    <Result<T, E> as Ord>::cmp
](
    left: &Result<T, E>,
    right: &Result<T, E>,
) -> (result: Ordering)
    ensures
        *left is Ok && *right is Ok ==>
            result == result_cmp_output(left->Ok_0, right->Ok_0),
        *left is Err && *right is Err ==>
            result == result_cmp_output(left->Err_0, right->Err_0),
        *left is Ok && *right is Err ==> result == Ordering::Less,
        *left is Err && *right is Ok ==> result == Ordering::Greater,
;

// @spec-row rustdoc-11011
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: PartialEq, E: PartialEq>[
    <Result<T, E> as PartialEq>::eq
](
    left: &Result<T, E>,
    right: &Result<T, E>,
) -> (result: bool)
    ensures
        *left is Ok && *right is Ok ==>
            result == result_partial_eq_output(left->Ok_0, right->Ok_0),
        *left is Err && *right is Err ==>
            result == result_partial_eq_output(left->Err_0, right->Err_0),
        *left is Ok && *right is Err ==> result == false,
        *left is Err && *right is Ok ==> result == false,
;

// @spec-row rustdoc-11599
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: PartialOrd, E: PartialOrd>[
    <Result<T, E> as PartialOrd>::partial_cmp
](
    left: &Result<T, E>,
    right: &Result<T, E>,
) -> (result: Option<Ordering>)
    ensures
        *left is Ok && *right is Ok ==>
            result == result_partial_cmp_output(left->Ok_0, right->Ok_0),
        *left is Err && *right is Err ==>
            result == result_partial_cmp_output(left->Err_0, right->Err_0),
        *left is Ok && *right is Err ==>
            result == Some(Ordering::Less),
        *left is Err && *right is Ok ==>
            result == Some(Ordering::Greater),
;

// @spec-row rustdoc-29279
pub assume_specification<T, E, F: FnOnce(T) -> bool>[
    Result::<T, E>::is_ok_and
](
    input: Result<T, E>,
    f: F,
) -> (result: bool)
    requires
        input is Ok ==> f.requires((input->Ok_0,)),
    ensures
        input is Err ==> result == false,
        input is Ok ==> f.ensures((input->Ok_0,), result),
        input is Ok ==>
            result == result_fn_once_output::<F, T, bool>(f, input->Ok_0),
;

// @spec-row rustdoc-29281
pub assume_specification<T, E, F: FnOnce(E) -> bool>[
    Result::<T, E>::is_err_and
](
    input: Result<T, E>,
    f: F,
) -> (result: bool)
    requires
        input is Err ==> f.requires((input->Err_0,)),
    ensures
        input is Ok ==> result == false,
        input is Err ==> f.ensures((input->Err_0,), result),
        input is Err ==>
            result == result_fn_once_output::<F, E, bool>(f, input->Err_0),
;

// @spec-row rustdoc-29285
pub assume_specification<T, E>[ Result::<T, E>::as_mut ](
    input: &mut Result<T, E>,
) -> (result: Result<&mut T, &mut E>)
    ensures
        *old(input) is Ok ==> result is Ok,
        *old(input) is Err ==> result is Err,
        result is Ok ==> *result->Ok_0 == (*old(input))->Ok_0,
        result is Err ==> *result->Err_0 == (*old(input))->Err_0,
        result is Ok ==> *final(input) == Ok(*final(result->Ok_0)),
        result is Err ==> *final(input) == Err(*final(result->Err_0)),
        result is Ok ==>
            result_ok_value_identity(*final(input))
                == result_mut_ref_identity(result->Ok_0),
        result is Err ==>
            result_err_value_identity(*final(input))
                == result_mut_ref_identity(result->Err_0),
    no_unwind
;

// @spec-row rustdoc-29288
pub assume_specification<T, E, U, F: FnOnce(T) -> U>[
    Result::<T, E>::map_or::<U, F>
](
    input: Result<T, E>,
    default: U,
    f: F,
) -> (result: U)
    requires
        input is Ok ==> f.requires((input->Ok_0,)),
    ensures
        input is Err ==> result == default,
        input is Ok ==> f.ensures((input->Ok_0,), result),
        input is Ok ==>
            result == result_fn_once_output::<F, T, U>(f, input->Ok_0),
;

// @spec-row rustdoc-29287
pub assume_specification<
    T,
    E,
    U,
    D: FnOnce(E) -> U,
    F: FnOnce(T) -> U,
>[
    Result::<T, E>::map_or_else::<U, D, F>
](
    input: Result<T, E>,
    default: D,
    f: F,
) -> (result: U)
    requires
        input is Ok ==> f.requires((input->Ok_0,)),
        input is Err ==> default.requires((input->Err_0,)),
    ensures
        input is Ok ==> f.ensures((input->Ok_0,), result),
        input is Ok ==>
            result == result_fn_once_output::<F, T, U>(f, input->Ok_0),
        input is Err ==> default.ensures((input->Err_0,), result),
        input is Err ==>
            result == result_fn_once_output::<D, E, U>(
                default,
                input->Err_0,
            ),
;

// @spec-row rustdoc-29291
pub assume_specification<T, E, F: FnOnce(&T)>[
    Result::<T, E>::inspect::<F>
](
    input: Result<T, E>,
    f: F,
) -> (result: Result<T, E>)
    requires
        input is Ok ==> f.requires((&input->Ok_0,)),
    ensures
        result == input,
        input is Ok ==> f.ensures((&input->Ok_0,), ()),
;

// @spec-row rustdoc-29292
pub assume_specification<T, E, F: FnOnce(&E)>[
    Result::<T, E>::inspect_err::<F>
](
    input: Result<T, E>,
    f: F,
) -> (result: Result<T, E>)
    requires
        input is Err ==> f.requires((&input->Err_0,)),
    ensures
        result == input,
        input is Err ==> f.ensures((&input->Err_0,), ()),
;

// @spec-row rustdoc-29293
pub assume_specification<T: Deref, E>[ Result::<T, E>::as_deref ](
    input: &Result<T, E>,
) -> (result: Result<&T::Target, &E>)
    ensures
        *input is Ok ==> result is Ok,
        *input is Err ==> result is Err,
        *input is Ok ==>
            result->Ok_0 == result_deref_shared(&input->Ok_0),
        *input is Ok ==>
            result_shared_ref_identity(result->Ok_0)
                == result_shared_ref_identity(
                    result_deref_shared(&input->Ok_0),
                ),
        *input is Err ==> *result->Err_0 == input->Err_0,
        *input is Err ==>
            result_shared_ref_identity(result->Err_0)
                == result_err_payload_identity(input),
;

// @spec-row rustdoc-29294
pub assume_specification<T: DerefMut, E>[
    Result::<T, E>::as_deref_mut
](
    input: &mut Result<T, E>,
) -> (result: Result<&mut T::Target, &mut E>)
    ensures
        *old(input) is Ok ==> result is Ok,
        *old(input) is Err ==> result is Err,
        *old(input) is Ok ==> *final(input) is Ok,
        *old(input) is Err ==> *final(input) is Err,
        result is Ok ==>
            result_mut_ref_initial_state(result->Ok_0)
                == result_deref_mut_state((*old(input))->Ok_0),
        result is Ok ==>
            result_mut_ref_final_state(result->Ok_0)
                == result_deref_mut_state((*final(input))->Ok_0),
        result is Ok ==>
            result_deref_mut_identity((*old(input))->Ok_0)
                == result_mut_ref_identity(result->Ok_0),
        result is Ok ==>
            result_deref_mut_identity((*final(input))->Ok_0)
                == result_mut_ref_identity(result->Ok_0),
        result is Err ==> *result->Err_0 == (*old(input))->Err_0,
        result is Err ==> *final(input) == Err(*final(result->Err_0)),
        result is Err ==>
            result_err_value_identity(*final(input))
                == result_mut_ref_identity(result->Err_0),
;

// @spec-row rustdoc-29295
pub assume_specification<'a, T, E>[ Result::<T, E>::iter ](
    input: &'a Result<T, E>,
) -> (result: Iter<'a, T>)
    ensures
        result_iter_values(&result).len()
            == if *input is Ok { 1nat } else { 0nat },
        result_iter_identities(&result).len()
            == result_iter_values(&result).len(),
        *input is Ok ==> result_iter_values(&result)[0] == input->Ok_0,
        *input is Ok ==>
            result_iter_identities(&result)[0]
                == result_ok_payload_identity(input),
    no_unwind
;

// @spec-row rustdoc-29296
pub assume_specification<'a, T, E>[ Result::<T, E>::iter_mut ](
    input: &'a mut Result<T, E>,
) -> (result: IterMut<'a, T>)
    ensures
        result_iter_mut_values(&result).len()
            == if *old(input) is Ok { 1nat } else { 0nat },
        result_iter_mut_identities(&result).len()
            == result_iter_mut_values(&result).len(),
        *old(input) is Ok ==>
            result_iter_mut_values(&result)[0] == (*old(input))->Ok_0,
        *old(input) is Ok ==>
            result_iter_mut_identities(&result)[0]
                == result_ok_value_identity(*old(input)),
        *old(input) is Err ==> *final(input) is Err,
        *old(input) is Ok ==> *final(input) is Ok,
        *old(input) is Ok ==>
            result_ok_value_identity(*final(input))
                == result_iter_mut_identities(&result)[0],
    no_unwind
;

// @spec-row rustdoc-29299
pub assume_specification<T: Default, E>[
    Result::<T, E>::unwrap_or_default
](
    input: Result<T, E>,
) -> (result: T)
    ensures
        input is Ok ==> result == input->Ok_0,
        input is Err ==> result == result_default_output::<T>(),
        input is Err ==> T::default.ensures((), result),
;

// @spec-row rustdoc-29300
pub assume_specification<T: Debug, E>[
    Result::<T, E>::expect_err
](
    input: Result<T, E>,
    msg: &str,
) -> (result: E)
    requires
        input is Err,
    ensures
        result == input->Err_0,
;

// @spec-row rustdoc-29305
pub assume_specification<T, E, U>[ Result::<T, E>::and::<U> ](
    input: Result<T, E>,
    other: Result<U, E>,
) -> (result: Result<U, E>)
    ensures
        input is Ok ==> result == other,
        input is Err ==> result == Err(input->Err_0),
;

// @spec-row rustdoc-29304
pub assume_specification<
    T,
    E,
    U,
    F: FnOnce(T) -> Result<U, E>,
>[
    Result::<T, E>::and_then::<U, F>
](
    input: Result<T, E>,
    op: F,
) -> (result: Result<U, E>)
    requires
        input is Ok ==> op.requires((input->Ok_0,)),
    ensures
        input is Err ==> result == Err(input->Err_0),
        input is Ok ==> op.ensures((input->Ok_0,), result),
        input is Ok ==>
            result == result_fn_once_output::<F, T, Result<U, E>>(
                op,
                input->Ok_0,
            ),
;

// @spec-row rustdoc-29307
pub assume_specification<T, E, F>[ Result::<T, E>::or::<F> ](
    input: Result<T, E>,
    other: Result<T, F>,
) -> (result: Result<T, F>)
    ensures
        input is Ok ==> result == Ok(input->Ok_0),
        input is Err ==> result == other,
;

// @spec-row rustdoc-29306
pub assume_specification<
    T,
    E,
    F,
    O: FnOnce(E) -> Result<T, F>,
>[
    Result::<T, E>::or_else::<F, O>
](
    input: Result<T, E>,
    op: O,
) -> (result: Result<T, F>)
    requires
        input is Err ==> op.requires((input->Err_0,)),
    ensures
        input is Ok ==> result == Ok(input->Ok_0),
        input is Err ==> op.ensures((input->Err_0,), result),
        input is Err ==>
            result == result_fn_once_output::<O, E, Result<T, F>>(
                op,
                input->Err_0,
            ),
;

// @spec-row rustdoc-29297
pub assume_specification<T, E>[ Result::<T, E>::unwrap_or ](
    input: Result<T, E>,
    default: T,
) -> (result: T)
    ensures
        input is Ok ==> result == input->Ok_0,
        input is Err ==> result == default,
;

// @spec-row rustdoc-29298
pub assume_specification<T, E, F: FnOnce(E) -> T>[
    Result::<T, E>::unwrap_or_else::<F>
](
    input: Result<T, E>,
    op: F,
) -> (result: T)
    requires
        input is Err ==> op.requires((input->Err_0,)),
    ensures
        input is Ok ==> result == input->Ok_0,
        input is Err ==> op.ensures((input->Err_0,), result),
        input is Err ==>
            result == result_fn_once_output::<F, E, T>(
                op,
                input->Err_0,
            ),
;

// @spec-row rustdoc-29308
pub assume_specification<T, E>[ Result::<T, E>::unwrap_unchecked ](
    input: Result<T, E>,
) -> (result: T)
    requires
        input is Ok,
    ensures
        result == input->Ok_0,
    no_unwind
;

// @spec-row rustdoc-29309
pub assume_specification<T, E>[
    Result::<T, E>::unwrap_err_unchecked
](
    input: Result<T, E>,
) -> (result: E)
    requires
        input is Err,
    ensures
        result == input->Err_0,
    no_unwind
;

// @spec-row rustdoc-29311
pub assume_specification<T: Copy, E>[ Result::<&T, E>::copied ](
    input: Result<&T, E>,
) -> (result: Result<T, E>)
    ensures
        input is Ok ==> result == Ok(*input->Ok_0),
        input is Err ==> result == Err(input->Err_0),
    no_unwind
;

// @spec-row rustdoc-29312
pub assume_specification<T: Clone, E>[ Result::<&T, E>::cloned ](
    input: Result<&T, E>,
) -> (result: Result<T, E>)
    ensures
        input is Err ==> result == Err(input->Err_0),
        input is Ok ==> result is Ok,
        input is Ok ==>
            result->Ok_0 == result_clone_output::<T>(*input->Ok_0),
        input is Ok ==> cloned::<T>(*input->Ok_0, result->Ok_0),
;

// @spec-row rustdoc-29314
pub assume_specification<T: Copy, E>[ Result::<&mut T, E>::copied ](
    input: Result<&mut T, E>,
) -> (result: Result<T, E>)
    ensures
        input is Ok ==> result == Ok(*input->Ok_0),
        input is Err ==> result == Err(input->Err_0),
    no_unwind
;

// @spec-row rustdoc-29315
pub assume_specification<T: Clone, E>[ Result::<&mut T, E>::cloned ](
    input: Result<&mut T, E>,
) -> (result: Result<T, E>)
    ensures
        input is Err ==> result == Err(input->Err_0),
        input is Ok ==> result is Ok,
        input is Ok ==>
            result->Ok_0 == result_clone_output::<T>(*input->Ok_0),
        input is Ok ==> cloned::<T>(*input->Ok_0, result->Ok_0),
;

// @spec-row rustdoc-29317
pub assume_specification<T, E>[
    Result::<Option<T>, E>::transpose
](
    input: Result<Option<T>, E>,
) -> (result: Option<Result<T, E>>)
    ensures
        input is Ok && input->Ok_0 is Some ==>
            result == Some(Ok(input->Ok_0->0)),
        input is Ok && input->Ok_0 is None ==> result is None,
        input is Err ==> result == Some(Err(input->Err_0)),
    no_unwind
;

// @spec-row rustdoc-29319
pub assume_specification<T, E>[
    Result::<Result<T, E>, E>::flatten
](
    input: Result<Result<T, E>, E>,
) -> (result: Result<T, E>)
    ensures
        input is Ok ==> result == input->Ok_0,
        input is Err ==> result == Err(input->Err_0),
    no_unwind
;

// @spec-row rustdoc-10004
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Clone, E: Clone>[
    <Result<T, E> as Clone>::clone
](
    input: &Result<T, E>,
) -> (result: Result<T, E>)
    ensures
        *input is Ok ==> result is Ok,
        *input is Err ==> result is Err,
        *input is Ok ==>
            result->Ok_0 == result_clone_output(input->Ok_0),
        *input is Ok ==> cloned::<T>(input->Ok_0, result->Ok_0),
        *input is Err ==>
            result->Err_0 == result_clone_output(input->Err_0),
        *input is Err ==> cloned::<E>(input->Err_0, result->Err_0),
;

// @spec-row rustdoc-10005
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Clone, E: Clone>[
    <Result<T, E> as Clone>::clone_from
](
    input: &mut Result<T, E>,
    source: &Result<T, E>,
)
    ensures
        *old(input) is Ok && *source is Ok ==>
            *final(input) == Ok(result_clone_from_output(
                (*old(input))->Ok_0,
                source->Ok_0,
            )),
        *old(input) is Err && *source is Err ==>
            *final(input) == Err(result_clone_from_output(
                (*old(input))->Err_0,
                source->Err_0,
            )),
        *old(input) is Ok && *source is Err ==>
            *final(input) == Err(result_clone_output(source->Err_0)),
        *old(input) is Ok && *source is Err ==>
            cloned::<E>(source->Err_0, (*final(input))->Err_0),
        *old(input) is Err && *source is Ok ==>
            *final(input) == Ok(result_clone_output(source->Ok_0)),
        *old(input) is Err && *source is Ok ==>
            cloned::<T>(source->Ok_0, (*final(input))->Ok_0),
;

// @spec-row rustdoc-26988
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T, E>[
    <Result<T, E> as IntoIterator>::into_iter
](
    input: Result<T, E>,
) -> (result: IntoIter<T>)
    ensures
        result_into_iter_values(&result)
            == if input is Ok { seq![input->Ok_0] } else { seq![] },
    no_unwind
;

// @spec-row rustdoc-26992
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T, E>[
    <&'a Result<T, E> as IntoIterator>::into_iter
](
    input: &'a Result<T, E>,
) -> (result: Iter<'a, T>)
    ensures
        result_iter_values(&result).len()
            == if *input is Ok { 1nat } else { 0nat },
        result_iter_identities(&result).len()
            == result_iter_values(&result).len(),
        *input is Ok ==> result_iter_values(&result)[0] == input->Ok_0,
        *input is Ok ==>
            result_iter_identities(&result)[0]
                == result_ok_payload_identity(input),
    no_unwind
;

// @spec-row rustdoc-26996
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T, E>[
    <&'a mut Result<T, E> as IntoIterator>::into_iter
](
    input: &'a mut Result<T, E>,
) -> (result: IterMut<'a, T>)
    ensures
        result_iter_mut_values(&result).len()
            == if *old(input) is Ok { 1nat } else { 0nat },
        result_iter_mut_identities(&result).len()
            == result_iter_mut_values(&result).len(),
        *old(input) is Ok ==>
            result_iter_mut_values(&result)[0] == (*old(input))->Ok_0,
        *old(input) is Ok ==>
            result_iter_mut_identities(&result)[0]
                == result_ok_value_identity(*old(input)),
        *old(input) is Err ==> *final(input) is Err,
        *old(input) is Ok ==> *final(input) is Ok,
        *old(input) is Ok ==>
            result_ok_value_identity(*final(input))
                == result_iter_mut_identities(&result)[0],
    no_unwind
;

// @spec-row rustdoc-29343
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T: 'a + Debug>[
    <Iter<'a, T> as Debug>::fmt
](
    iter: &Iter<'a, T>,
    formatter: &mut Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        result_iter_values(iter).len() <= 1,
        result == result_formatter_debug_struct_result(
            ResultFormatLiteral::IterName,
            ResultFormatLiteral::InnerField,
            result_iter_values(iter),
            result_formatter_state(*old(formatter)),
        ),
        result_formatter_state(*final(formatter))
            == result_formatter_debug_struct_post(
                ResultFormatLiteral::IterName,
                ResultFormatLiteral::InnerField,
                result_iter_values(iter),
                result_formatter_state(*old(formatter)),
            ),
;

// @spec-row rustdoc-27283
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <Iter<'a, T> as Iterator>::next
](
    iter: &mut Iter<'a, T>,
) -> (result: Option<&'a T>)
    ensures
        result_iter_value_values(*old(iter)).len() <= 1,
        result_iter_value_identities(*old(iter)).len()
            == result_iter_value_values(*old(iter)).len(),
        result_iter_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_iter_value_values(*old(iter)).len() > 0 ==>
            result is Some
                && *result->0 == result_iter_value_values(*old(iter))[0]
                && result_shared_ref_identity(result->0)
                    == result_iter_value_identities(*old(iter))[0],
        result_iter_value_values(*final(iter))
            == if result_iter_value_values(*old(iter)).len() > 0 {
                result_iter_value_values(*old(iter)).drop_first()
            } else {
                result_iter_value_values(*old(iter))
            },
        result_iter_value_identities(*final(iter))
            == if result_iter_value_identities(*old(iter)).len() > 0 {
                result_iter_value_identities(*old(iter)).drop_first()
            } else {
                result_iter_value_identities(*old(iter))
            },
    no_unwind
;

// @spec-row rustdoc-27284
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <Iter<'a, T> as Iterator>::size_hint
](
    iter: &Iter<'a, T>,
) -> (result: (usize, Option<usize>))
    ensures
        result_iter_values(iter).len() <= 1,
        result == (
            result_iter_values(iter).len() as usize,
            Some(result_iter_values(iter).len() as usize),
        ),
    no_unwind
;

// @spec-row rustdoc-27047
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <Iter<'a, T> as DoubleEndedIterator>::next_back
](
    iter: &mut Iter<'a, T>,
) -> (result: Option<&'a T>)
    ensures
        result_iter_value_values(*old(iter)).len() <= 1,
        result_iter_value_identities(*old(iter)).len()
            == result_iter_value_values(*old(iter)).len(),
        result_iter_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_iter_value_values(*old(iter)).len() > 0 ==>
            result is Some
                && *result->0 == result_iter_value_values(*old(iter))[0]
                && result_shared_ref_identity(result->0)
                    == result_iter_value_identities(*old(iter))[0],
        result_iter_value_values(*final(iter))
            == if result_iter_value_values(*old(iter)).len() > 0 {
                result_iter_value_values(*old(iter)).drop_first()
            } else {
                result_iter_value_values(*old(iter))
            },
        result_iter_value_identities(*final(iter))
            == if result_iter_value_identities(*old(iter)).len() > 0 {
                result_iter_value_identities(*old(iter)).drop_first()
            } else {
                result_iter_value_identities(*old(iter))
            },
    no_unwind
;

// @spec-row rustdoc-10007
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <Iter<'a, T> as Clone>::clone
](
    iter: &Iter<'a, T>,
) -> (result: Iter<'a, T>)
    ensures
        result_iter_values(&result) == result_iter_values(iter),
        result_iter_identities(&result) == result_iter_identities(iter),
;

// @spec-row rustdoc-29354
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T: 'a + Debug>[
    <IterMut<'a, T> as Debug>::fmt
](
    iter: &IterMut<'a, T>,
    formatter: &mut Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        result_iter_mut_values(iter).len() <= 1,
        result == result_formatter_debug_struct_result(
            ResultFormatLiteral::IterMutName,
            ResultFormatLiteral::InnerField,
            result_iter_mut_values(iter),
            result_formatter_state(*old(formatter)),
        ),
        result_formatter_state(*final(formatter))
            == result_formatter_debug_struct_post(
                ResultFormatLiteral::IterMutName,
                ResultFormatLiteral::InnerField,
                result_iter_mut_values(iter),
                result_formatter_state(*old(formatter)),
            ),
;

// @spec-row rustdoc-27287
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <IterMut<'a, T> as Iterator>::next
](
    iter: &mut IterMut<'a, T>,
) -> (result: Option<&'a mut T>)
    ensures
        result_iter_mut_value_values(*old(iter)).len() <= 1,
        result_iter_mut_value_identities(*old(iter)).len()
            == result_iter_mut_value_values(*old(iter)).len(),
        result_iter_mut_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_iter_mut_value_values(*old(iter)).len() > 0 ==>
            result is Some
                && *result->0
                    == result_iter_mut_value_values(*old(iter))[0]
                && result_mut_ref_identity(result->0)
                    == result_iter_mut_value_identities(*old(iter))[0],
        result_iter_mut_value_values(*final(iter))
            == if result_iter_mut_value_values(*old(iter)).len() > 0 {
                result_iter_mut_value_values(*old(iter)).drop_first()
            } else {
                result_iter_mut_value_values(*old(iter))
            },
        result_iter_mut_value_identities(*final(iter))
            == if result_iter_mut_value_identities(*old(iter)).len() > 0 {
                result_iter_mut_value_identities(*old(iter)).drop_first()
            } else {
                result_iter_mut_value_identities(*old(iter))
            },
        result is Some ==>
            result_iter_mut_value_values(*final(iter)).len() == 0,
        result is Some ==>
            result_iter_mut_value_identities(*final(iter)).len() == 0,
    no_unwind
;

// @spec-row rustdoc-27288
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <IterMut<'a, T> as Iterator>::size_hint
](
    iter: &IterMut<'a, T>,
) -> (result: (usize, Option<usize>))
    ensures
        result_iter_mut_values(iter).len() <= 1,
        result == (
            result_iter_mut_values(iter).len() as usize,
            Some(result_iter_mut_values(iter).len() as usize),
        ),
    no_unwind
;

// @spec-row rustdoc-27049
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<'a, T>[
    <IterMut<'a, T> as DoubleEndedIterator>::next_back
](
    iter: &mut IterMut<'a, T>,
) -> (result: Option<&'a mut T>)
    ensures
        result_iter_mut_value_values(*old(iter)).len() <= 1,
        result_iter_mut_value_identities(*old(iter)).len()
            == result_iter_mut_value_values(*old(iter)).len(),
        result_iter_mut_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_iter_mut_value_values(*old(iter)).len() > 0 ==>
            result is Some
                && *result->0
                    == result_iter_mut_value_values(*old(iter))[0]
                && result_mut_ref_identity(result->0)
                    == result_iter_mut_value_identities(*old(iter))[0],
        result_iter_mut_value_values(*final(iter))
            == if result_iter_mut_value_values(*old(iter)).len() > 0 {
                result_iter_mut_value_values(*old(iter)).drop_first()
            } else {
                result_iter_mut_value_values(*old(iter))
            },
        result_iter_mut_value_identities(*final(iter))
            == if result_iter_mut_value_identities(*old(iter)).len() > 0 {
                result_iter_mut_value_identities(*old(iter)).drop_first()
            } else {
                result_iter_mut_value_identities(*old(iter))
            },
        result is Some ==>
            result_iter_mut_value_values(*final(iter)).len() == 0,
        result is Some ==>
            result_iter_mut_value_identities(*final(iter)).len() == 0,
    no_unwind
;

// @spec-row rustdoc-10010
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Clone>[
    <IntoIter<T> as Clone>::clone
](
    iter: &IntoIter<T>,
) -> (result: IntoIter<T>)
    ensures
        result_into_iter_values(iter).len() <= 1,
        result_into_iter_values(&result).len()
            == result_into_iter_values(iter).len(),
        result_into_iter_values(iter).len() == 0 ==>
            result_into_iter_values(&result).len() == 0,
        result_into_iter_values(iter).len() > 0 ==>
            result_into_iter_values(&result)[0]
                == result_clone_output(result_into_iter_values(iter)[0]),
        result_into_iter_values(iter).len() > 0 ==>
            cloned::<T>(
                result_into_iter_values(iter)[0],
                result_into_iter_values(&result)[0],
            ),
;

// @spec-row rustdoc-29366
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T: Debug>[
    <IntoIter<T> as Debug>::fmt
](
    iter: &IntoIter<T>,
    formatter: &mut Formatter<'_>,
) -> (result: core::fmt::Result)
    ensures
        result_into_iter_values(iter).len() <= 1,
        result == result_formatter_debug_struct_result(
            ResultFormatLiteral::IntoIterName,
            ResultFormatLiteral::InnerField,
            result_into_iter_values(iter),
            result_formatter_state(*old(formatter)),
        ),
        result_formatter_state(*final(formatter))
            == result_formatter_debug_struct_post(
                ResultFormatLiteral::IntoIterName,
                ResultFormatLiteral::InnerField,
                result_into_iter_values(iter),
                result_formatter_state(*old(formatter)),
            ),
;

// @spec-row rustdoc-27291
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T>[
    <IntoIter<T> as Iterator>::next
](
    iter: &mut IntoIter<T>,
) -> (result: Option<T>)
    ensures
        result_into_iter_value_values(*old(iter)).len() <= 1,
        result_into_iter_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_into_iter_value_values(*old(iter)).len() > 0 ==>
            result == Some(result_into_iter_value_values(*old(iter))[0]),
        result_into_iter_value_values(*final(iter))
            == if result_into_iter_value_values(*old(iter)).len() > 0 {
                result_into_iter_value_values(*old(iter)).drop_first()
            } else {
                result_into_iter_value_values(*old(iter))
            },
    no_unwind
;

// @spec-row rustdoc-27292
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T>[
    <IntoIter<T> as Iterator>::size_hint
](
    iter: &IntoIter<T>,
) -> (result: (usize, Option<usize>))
    ensures
        result_into_iter_values(iter).len() <= 1,
        result == (
            result_into_iter_values(iter).len() as usize,
            Some(result_into_iter_values(iter).len() as usize),
        ),
    no_unwind
;

// @spec-row rustdoc-27051
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<T>[
    <IntoIter<T> as DoubleEndedIterator>::next_back
](
    iter: &mut IntoIter<T>,
) -> (result: Option<T>)
    ensures
        result_into_iter_value_values(*old(iter)).len() <= 1,
        result_into_iter_value_values(*old(iter)).len() == 0 ==>
            result is None,
        result_into_iter_value_values(*old(iter)).len() > 0 ==>
            result == Some(result_into_iter_value_values(*old(iter))[0]),
        result_into_iter_value_values(*final(iter))
            == if result_into_iter_value_values(*old(iter)).len() > 0 {
                result_into_iter_value_values(*old(iter)).drop_first()
            } else {
                result_into_iter_value_values(*old(iter))
            },
    no_unwind
;

// @spec-row rustdoc-26942
#[verifier::allow(undeclared_external_trait)]
pub assume_specification<
    A,
    E,
    V: FromIterator<A>,
    I: IntoIterator<Item = Result<A, E>>,
>[
    <Result<V, E> as FromIterator<Result<A, E>>>::from_iter::<I>
](
    iter: I,
) -> (result: Result<V, E>)
    ensures
        result_short_circuit_trace::<A, E, V, I>(
            ResultShortCircuitOperation::FromIterator,
            iter,
        ).len()
            <= into_iter_remaining::<Result<A, E>, I>(iter).len(),
        forall|index: int|
            0 <= index
                < result_short_circuit_trace::<A, E, V, I>(
                    ResultShortCircuitOperation::FromIterator,
                    iter,
                ).len() ==>
            result_short_circuit_trace::<A, E, V, I>(
                ResultShortCircuitOperation::FromIterator,
                iter,
            )[index]
                == into_iter_remaining::<Result<A, E>, I>(iter)[index],
        result_all_ok(
            into_iter_remaining::<Result<A, E>, I>(iter),
        ) ==>
            result_short_circuit_trace::<A, E, V, I>(
                ResultShortCircuitOperation::FromIterator,
                iter,
            ) == into_iter_remaining::<Result<A, E>, I>(iter),
        result_all_ok(
            into_iter_remaining::<Result<A, E>, I>(iter),
        ) <==> result is Ok,
        result_all_ok(
            into_iter_remaining::<Result<A, E>, I>(iter),
        ) ==>
            exists|payloads: Seq<A>|
                result_ok_payloads_match(
                    into_iter_remaining::<Result<A, E>, I>(iter),
                    payloads,
                )
                && result == Ok(result_collect_output::<A, V>(payloads))
                && FromIteratorSpec::from_iter_ensures(
                    payloads,
                    result->Ok_0,
                ),
        !result_all_ok(
            into_iter_remaining::<Result<A, E>, I>(iter),
        ) ==>
            exists|stop: int|
                0 <= stop
                    < into_iter_remaining::<Result<A, E>, I>(iter).len()
                && into_iter_remaining::<Result<A, E>, I>(iter)[stop] is Err
                && (forall|prior: int| 0 <= prior < stop ==>
                    into_iter_remaining::<Result<A, E>, I>(iter)[prior] is Ok)
                && result_short_circuit_trace::<A, E, V, I>(
                    ResultShortCircuitOperation::FromIterator,
                    iter,
                ).len() == stop + 1
                && result == Err(
                    into_iter_remaining::<Result<A, E>, I>(iter)[stop]->Err_0
                ),
;

} // verus!
