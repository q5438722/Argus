// frozen accepted generated declaration
// source: specs/generated_result_specs.rs:22-87
// accepted segment sha256: 0fe143042f6b6ecc9ad64c088f3703b71d3369ad76d5dde7b1fd32b921d440a4

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
