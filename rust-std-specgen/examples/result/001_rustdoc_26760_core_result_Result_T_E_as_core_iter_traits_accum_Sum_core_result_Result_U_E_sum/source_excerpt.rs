// exact source evidence for <core::result::Result<T, E> as core::iter::traits::accum::Sum<core::result::Result<U, E>>>::sum
// /home/chentianyu/nanvix-rust-std-spec-survey/rust-1.96/library/core/src/iter/traits/accum.rs:233-238
// sha256: da050c3bf87df6a96dbc7bccf116bbe998dedbbf78f51a96d4804635a1d49f9c

fn sum<I>(iter: I) -> Result<T, E>
    where
        I: Iterator<Item = Result<U, E>>,
    {
        iter::try_process(iter, |i| i.sum())
    }