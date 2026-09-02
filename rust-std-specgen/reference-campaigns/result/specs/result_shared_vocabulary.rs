// Shared mathematical views and narrow dependency laws for core::result.
verus! {

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::reject_recursive_types(A)]
pub struct ExResultIter<'a, A: 'a>(Iter<'a, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::reject_recursive_types(A)]
pub struct ExResultIterMut<'a, A: 'a>(IterMut<'a, A>);

#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::reject_recursive_types(A)]
pub struct ExResultIntoIter<A>(IntoIter<A>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExResultFormatter<'a>(Formatter<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExResultFmtError(core::fmt::Error);

pub open spec fn result_all_ok<A, E>(items: Seq<Result<A, E>>) -> bool {
    forall|i: int| 0 <= i < items.len() ==> items[i] is Ok
}

pub open spec fn result_ok_payloads_match<A, E>(
    items: Seq<Result<A, E>>,
    payloads: Seq<A>,
) -> bool {
    &&& payloads.len() == items.len()
    &&& forall|i: int| 0 <= i < items.len() ==>
        items[i] is Ok && payloads[i] == items[i]->Ok_0
}

pub enum ResultShortCircuitOperation {
    Sum,
    Product,
    FromIterator,
}

pub uninterp spec fn result_short_circuit_trace<A, E, Delegate, I>(
    operation: ResultShortCircuitOperation,
    iter: I,
) -> Seq<Result<A, E>>;

#[verifier::allow(undeclared_external_trait)]
pub uninterp spec fn result_sum_output<U, T: Sum<U>>(
    payloads: Seq<U>,
) -> T;

#[verifier::allow(undeclared_external_trait)]
pub uninterp spec fn result_product_output<U, T: Product<U>>(
    payloads: Seq<U>,
) -> T;

pub uninterp spec fn result_collect_output<A, V: FromIterator<A>>(
    payloads: Seq<A>,
) -> V;

pub uninterp spec fn result_default_output<T: Default>() -> T;

pub uninterp spec fn result_clone_output<T: Clone>(source: T) -> T;

pub uninterp spec fn result_clone_from_output<T: Clone>(
    before: T,
    source: T,
) -> T;

pub uninterp spec fn result_fn_once_output<F, A, B>(
    f: F,
    argument: A,
) -> B;

pub uninterp spec fn result_shared_ref_identity<A: ?Sized>(
    reference: &A,
) -> int;

pub uninterp spec fn result_mut_ref_identity<A: ?Sized>(
    reference: &mut A,
) -> int;

pub uninterp spec fn result_mut_ref_initial_state<A: ?Sized>(
    reference: &mut A,
) -> int;

#[verifier::prophetic]
pub uninterp spec fn result_mut_ref_final_state<A: ?Sized>(
    reference: &mut A,
) -> int;

pub uninterp spec fn result_ok_payload_identity<A, E>(
    result: &Result<A, E>,
) -> int;

pub uninterp spec fn result_err_payload_identity<A, E>(
    result: &Result<A, E>,
) -> int;

pub uninterp spec fn result_ok_value_identity<A, E>(
    result: Result<A, E>,
) -> int;

pub uninterp spec fn result_err_value_identity<A, E>(
    result: Result<A, E>,
) -> int;

pub uninterp spec fn result_deref_shared<'a, T: Deref>(
    value: &'a T,
) -> &'a T::Target;

pub uninterp spec fn result_deref_mut_state<T: DerefMut>(
    value: T,
) -> int;

pub uninterp spec fn result_deref_mut_identity<T: DerefMut>(
    value: T,
) -> int;

pub uninterp spec fn result_partial_eq_output<T: PartialEq>(
    left: T,
    right: T,
) -> bool;

pub uninterp spec fn result_partial_cmp_output<T: PartialOrd>(
    left: T,
    right: T,
) -> Option<Ordering>;

pub uninterp spec fn result_cmp_output<T: Ord>(
    left: T,
    right: T,
) -> Ordering;

#[verifier::prophetic]
pub uninterp spec fn result_iter_values<'a, A>(
    iter: &Iter<'a, A>,
) -> Seq<A>;

#[verifier::prophetic]
pub uninterp spec fn result_iter_identities<'a, A>(
    iter: &Iter<'a, A>,
) -> Seq<int>;

#[verifier::prophetic]
pub open spec fn result_iter_value_values<'a, A>(
    iter: Iter<'a, A>,
) -> Seq<A> {
    result_iter_values(&iter)
}

#[verifier::prophetic]
pub open spec fn result_iter_value_identities<'a, A>(
    iter: Iter<'a, A>,
) -> Seq<int> {
    result_iter_identities(&iter)
}

#[verifier::prophetic]
pub uninterp spec fn result_iter_mut_values<'a, A>(
    iter: &IterMut<'a, A>,
) -> Seq<A>;

#[verifier::prophetic]
pub uninterp spec fn result_iter_mut_identities<'a, A>(
    iter: &IterMut<'a, A>,
) -> Seq<int>;

#[verifier::prophetic]
pub open spec fn result_iter_mut_value_values<'a, A>(
    iter: IterMut<'a, A>,
) -> Seq<A> {
    result_iter_mut_values(&iter)
}

#[verifier::prophetic]
pub open spec fn result_iter_mut_value_identities<'a, A>(
    iter: IterMut<'a, A>,
) -> Seq<int> {
    result_iter_mut_identities(&iter)
}

#[verifier::prophetic]
pub uninterp spec fn result_into_iter_values<A>(
    iter: &IntoIter<A>,
) -> Seq<A>;

#[verifier::prophetic]
pub open spec fn result_into_iter_value_values<A>(
    iter: IntoIter<A>,
) -> Seq<A> {
    result_into_iter_values(&iter)
}

pub uninterp spec fn result_formatter_state<'a>(
    formatter: Formatter<'a>,
) -> int;

pub enum ResultFormatLiteral {
    OkName,
    ErrName,
    IterName,
    IterMutName,
    IntoIterName,
    InnerField,
}

pub uninterp spec fn result_formatter_debug_tuple_result<T: Debug>(
    name: ResultFormatLiteral,
    value: T,
    before: int,
) -> core::fmt::Result;

pub uninterp spec fn result_formatter_debug_tuple_post<T: Debug>(
    name: ResultFormatLiteral,
    value: T,
    before: int,
) -> int;

pub uninterp spec fn result_formatter_debug_struct_result<A: Debug>(
    name: ResultFormatLiteral,
    field: ResultFormatLiteral,
    remaining: Seq<A>,
    before: int,
) -> core::fmt::Result;

pub uninterp spec fn result_formatter_debug_struct_post<A: Debug>(
    name: ResultFormatLiteral,
    field: ResultFormatLiteral,
    remaining: Seq<A>,
    before: int,
) -> int;

pub uninterp spec fn result_hasher_discriminant_post<H: Hasher>(
    discriminant: int,
    before: H,
) -> H;

pub uninterp spec fn result_hasher_payload_post<T: Hash, H: Hasher>(
    value: T,
    before: H,
) -> H;

} // verus!
