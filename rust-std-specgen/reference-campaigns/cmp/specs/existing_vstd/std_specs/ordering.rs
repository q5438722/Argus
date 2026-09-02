//! Specifications for `core::cmp::Ordering` convenience methods.
use super::super::prelude::*;

use core::cmp::Ordering;

verus! {

pub assume_specification[ Ordering::is_eq ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> ordering is Equal,
;

pub assume_specification[ Ordering::is_ne ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> !(ordering is Equal),
;

pub assume_specification[ Ordering::is_lt ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> ordering is Less,
;

pub assume_specification[ Ordering::is_gt ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> ordering is Greater,
;

pub assume_specification[ Ordering::is_le ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> !(ordering is Greater),
;

pub assume_specification[ Ordering::is_ge ](ordering: Ordering) -> (result: bool)
    ensures
        result <==> !(ordering is Less),
;

pub assume_specification[ Ordering::reverse ](ordering: Ordering) -> (result: Ordering)
    ensures
        result == match ordering {
            Ordering::Less => Ordering::Greater,
            Ordering::Equal => Ordering::Equal,
            Ordering::Greater => Ordering::Less,
        },
;

pub assume_specification[ Ordering::then ](ordering: Ordering, other: Ordering) -> (result:
    Ordering)
    ensures
        result == if ordering is Equal {
            other
        } else {
            ordering
        },
;

} // verus!
