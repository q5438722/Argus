#![feature(sized_hierarchy)]
#![allow(dead_code, unused_imports, unused_variables, unused_mut, unused_parens)]
// Source-shaped completeness proof for <core::result::Result<T, E> as core::iter::traits::accum::Sum<core::result::Result<U, E>>>::sum.
// Rustdoc item: 26760
// Semantic family: short_circuit_first_err_forwarding
// Proof template: short_circuit_sum
// Exact source/derive excerpt sha256: da050c3bf87df6a96dbc7bccf116bbe998dedbbf78f51a96d4804635a1d49f9c
// Accepted contract segment sha256: e77bd9c7497335fe5233b2e7a75e9c704c0ac33a6c79c2c68529812ef8c779f4
// Accepted target signature: fn sum<I>(iter: I) -> core::result::Result<T, E>
// Proof target signature: pub fn implementation_target<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> Result<T, E>
// The accepted contract clauses below are reproduced from the frozen
// accepted declaration; the executable link calls the real
// `implementation_target` and the theorem compares two accepted outcomes
// under the same fixed named lower-dependency observations.

#[path = "implementation_proof.rs"]
pub mod implementation_proof;

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
use implementation_proof::accepted_vocabulary::*;
use implementation_proof::*;

verus! {

#[verifier::allow(undeclared_external_trait)]
pub open spec fn accepted_contract_requires<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> bool {
    &&& true
}

#[verifier::allow(undeclared_external_trait)]
pub open spec fn accepted_contract<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I, result: Result<T, E>) -> bool {
    &&& result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() <= into_iter_remaining::<Result<U, E>, I>(iter).len()
    &&& forall|index: int| 0 <= index < result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter)[index] == into_iter_remaining::<Result<U, E>, I>(iter)[index]
    &&& result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter) == into_iter_remaining::<Result<U, E>, I>(iter)
    &&& result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) <==> result is Ok
    &&& result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && result == Ok(result_sum_output::<U, T>(payloads))
    &&& !result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) ==> exists|stop: int| 0 <= stop < into_iter_remaining::<Result<U, E>, I>(iter).len() && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err && (forall|prior: int| 0 <= prior < stop ==> into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok) && result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() == stop + 1 && result == Err(into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0)
}

pub open spec fn outcomes_equivalent<ProofOutcome>(
    left: ProofOutcome,
    right: ProofOutcome,
) -> bool {
    &&& left == right
}

#[verifier::allow(undeclared_external_trait)]
pub fn implementation_contract_link<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> (result: Result<T, E>)
    requires
        accepted_contract_requires::<T, U, E, I>(iter),
    ensures
        accepted_contract::<T, U, E, I>(iter, result),
{
    implementation_target::<T, U, E, I>(iter)
}

#[verifier::allow(undeclared_external_trait)]
pub proof fn completeness_theorem<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I, left: Result<T, E>, right: Result<T, E>)
    requires
        accepted_contract_requires::<T, U, E, I>(iter),
        accepted_contract::<T, U, E, I>(iter, left),
        accepted_contract::<T, U, E, I>(iter, right),
    ensures
        outcomes_equivalent(left, right),
{
    if result_all_ok(into_iter_remaining::<Result<U, E>, I>(iter)) {
        let left_payloads = choose|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && left == Ok(result_sum_output::<U, T>(payloads));
        let right_payloads = choose|payloads: Seq<U>| result_ok_payloads_match(into_iter_remaining::<Result<U, E>, I>(iter), payloads) && right == Ok(result_sum_output::<U, T>(payloads));
        assert(left_payloads =~= right_payloads);
    } else {
        let left_stop = choose|stop: int| 0 <= stop < into_iter_remaining::<Result<U, E>, I>(iter).len() && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err && (forall|prior: int| 0 <= prior < stop ==> into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok) && result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() == stop + 1 && left == Err(into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0);
        let right_stop = choose|stop: int| 0 <= stop < into_iter_remaining::<Result<U, E>, I>(iter).len() && into_iter_remaining::<Result<U, E>, I>(iter)[stop] is Err && (forall|prior: int| 0 <= prior < stop ==> into_iter_remaining::<Result<U, E>, I>(iter)[prior] is Ok) && result_short_circuit_trace::<U, E, T, I>(ResultShortCircuitOperation::Sum, iter).len() == stop + 1 && right == Err(into_iter_remaining::<Result<U, E>, I>(iter)[stop]->Err_0);
        if left_stop < right_stop {
            assert(into_iter_remaining::<Result<U, E>, I>(iter)[left_stop] is Ok);
        }
        if right_stop < left_stop {
            assert(into_iter_remaining::<Result<U, E>, I>(iter)[right_stop] is Ok);
        }
    }
}

#[verifier::allow(undeclared_external_trait)]
pub fn contract_link_outcome_uniqueness<T: Sum<U>, U, E, I: Iterator<Item = Result<U, E>>>(iter: I) -> (result: Result<T, E>)
    requires
        accepted_contract_requires::<T, U, E, I>(iter),
    ensures
        accepted_contract::<T, U, E, I>(iter, result),
        forall|alternative: Result<T, E>| accepted_contract::<T, U, E, I>(iter, alternative) ==> outcomes_equivalent(result, alternative),
{
    let executed = implementation_contract_link::<T, U, E, I>(iter);
    proof {
        assert forall|alternative: Result<T, E>| accepted_contract::<T, U, E, I>(iter, alternative) implies
            outcomes_equivalent(executed, alternative) by {
            completeness_theorem::<T, U, E, I>(iter, executed, alternative);
        }
    }
    executed
}

} // verus!
