#![feature(sized_hierarchy)]
#![allow(dead_code, unused_imports, unused_variables, unused_mut, unused_parens)]
// Source-shaped implementation proof for <core::result::Result<T, E> as core::iter::traits::accum::Sum<core::result::Result<U, E>>>::sum.
// Rustdoc item: 26760
// Semantic family: short_circuit_first_err_forwarding
// Proof template: short_circuit_sum
// Exact source/derive excerpt sha256: da050c3bf87df6a96dbc7bccf116bbe998dedbbf78f51a96d4804635a1d49f9c
// Accepted contract segment sha256: e77bd9c7497335fe5233b2e7a75e9c704c0ac33a6c79c2c68529812ef8c779f4
// Accepted target signature: fn sum<I>(iter: I) -> core::result::Result<T, E>
// Proof target signature: pub fn implementation_target<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> Result<T, E>

pub mod accepted_vocabulary {
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
    include!("../../specs/result_shared_vocabulary.rs");
}

use core::clone::Clone;
use core::cmp::{Ord, Ordering, PartialEq, PartialOrd};
use core::default::Default;
use core::fmt::{Debug, Formatter};
use core::hash::{Hash, Hasher};
use core::iter::{DoubleEndedIterator, FromIterator, IntoIterator, Iterator, Product, Sum};
use core::ops::{Deref, DerefMut};
use core::option::Option;
use core::result::{IntoIter, Iter, IterMut, Result};
use vstd::prelude::*;
use vstd::std_specs::iter::{into_iter_remaining, FromIteratorSpec};
use accepted_vocabulary::*;

verus! {


// `<Result<T, E> as Sum<Result<U, E>>>::sum` is
//     iter::try_process(iter.into_iter(), |i| i.sum())
// The `ShuntIterator` inside `try_process` yields an ordered prefix of the
// source items to the inner adapter and stops at the first `Err`, storing that
// error as the residual.  Only that behaviour is modelled here; the residual is
// an explicit `Option<E>` out-parameter so the target itself performs the
// `ControlFlow`-to-`Result` conversion.
#[verifier::external_body]
#[verifier::allow(undeclared_external_trait)]
pub fn source_try_process<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(
    iter: I,
    residual: &mut Option<E>,
) -> (value: T)
    requires
        *old(residual) is None,
    ensures
        result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() <= into_iter_remaining::<Result<U, E>, I>(iter).len(),
        forall|index: int| 0 <= index < result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter)[index] == into_iter_remaining::<Result<U, E>, I>(iter)[index],
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter) == into_iter_remaining::<Result<U, E>, I>(iter),
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) <==> *final(residual) is None,
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && value == result_sum_output::<U, T>(payloads),
        !result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|stop: int| 0 <= stop < into_iter_remaining::<Result<U, E>, I>(iter).len() && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err && (forall|prior: int| 0 <= prior < stop ==> into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok) && result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() == stop + 1 && *final(residual) == Some(into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0),
{
    unimplemented!()
}

#[verifier::allow(undeclared_external_trait)]
pub fn implementation_target<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> (result: Result<T, E>)
    ensures
        result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() <= into_iter_remaining::<Result<U, E>, I>(iter).len(),
        forall|index: int| 0 <= index < result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter)[index] == into_iter_remaining::<Result<U, E>, I>(iter)[index],
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter) == into_iter_remaining::<Result<U, E>, I>(iter),
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) <==> result is Ok,
        result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && result == Ok(result_sum_output::<U, T>(payloads)),
        !result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|stop: int| 0 <= stop < into_iter_remaining::<Result<U, E>, I>(iter).len() && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err && (forall|prior: int| 0 <= prior < stop ==> into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok) && result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() == stop + 1 && result == Err(into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0),
{
    let mut residual: Option<E> = None;
    let value = source_try_process::<T, U, E, I>(iter, &mut residual);
    match residual {
        Some(error) => Err(error),
        None => {
            let collected: Result<T, E> = Ok(value);
            proof {
                // Name the ordered Ok payload sequence of the consumed prefix and
                // carry the delegated aggregate output law onto the returned `Ok`.
                let payloads = choose|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && value == result_sum_output::<U, T>(payloads);
                assert(result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && collected == Ok(result_sum_output::<U, T>(payloads)));
            }
            collected
        }
    }
}

} // verus!
