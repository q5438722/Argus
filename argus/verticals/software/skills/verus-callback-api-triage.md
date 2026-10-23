---
name: "Verus Callback API Triage"
description: "Generate sound callback-driven API specifications when current Verus support is sufficient; otherwise preserve bounded attempts, classify the API as partial/local-skip, and continue independent module work without narrowing the original callback domain."
---

# Verus Callback API Triage

[Chinese reference](references/verus-callback-api-triage.zh-CN.md)

Policy: **callback-triage-v1**, authorized on 2026-10-16.
Use this for APIs whose behavior depends on `Fn`, `FnMut`, `FnOnce`, function
items, closures, mutable captures, callback argument writeback, or repeated
callback state.

Callback APIs remain in the canonical inventory. When current Verus/vstd and
the campaign-local verifier can express a sound, useful contract, generate it.
When callback support is still insufficient after bounded materially different
attempts, preserve the partial work, classify the API as a callback-support
local skip/deferral, and continue independent APIs. Callback limitations must
not block the whole module.

## Generate when the contract is sound and connected

Reuse existing callable protocols and model the actual invocation order,
return values, mutable argument updates and relevant callback state. Preserve
the original callback type and calling domain. For repeated calls, distinguish
each current callable state; do not freeze all calls at the initial state or
identify `mut_ref_current` with an arbitrary future value.

Write the useful API guarantees even if source/completeness proof support is
only partial, but report those dimensions separately. A generated callback
contract is not complete until it is effectively bound and both required proof
tracks pass in its stated scope.

Concrete clients, native tests and local call-scope lemmas are useful semantic
checks. They do not prove arbitrary callback behavior or replace the original
API's correctness/completeness result.

## Do not obtain a pass by changing the callback domain

Do not add callback purity, identity, deterministic output, `Copy`, `Clone`,
`View`, `'static`, no-capture, no-interior-mutation, or fixed-call-result
requirements unless the original Rust API already has them. Do not replace a
stateful callback with a pure spec function or write expected outputs into
analysis premises. Preserve panic/short-circuit/writeback behavior when it is
part of the selected functional observation.

## Bounded attempts and local skip

Try the existing vstd callable rules and at least one materially different,
source-faithful proof/encoding route when one is available. A campaign-local
Verus patch may be used for a narrow callback-language feature, but this policy
does not require implementing a broad callback semantics stack merely to close
one API.

Defer/skip when the remaining blocker requires substantial unsupported
callback machinery, for example:

- mutable-capture or function-item correspondence not supplied by current rules;
- enumeration/comparison of generic mutable callback post-state;
- repeated `FnMut` current/future state threading across complex loops;
- callback, element and Drop/panic effects whose useful state interface is not
  yet expressible without narrowing the API.

Record the exact API, generated candidate (if any), attempts, diagnostics,
missing Verus capability, and a clear reopening condition. Use statuses such as
`partial_callback_spec` or `local_skip_callback_support`, not `passed`.
Keep failed queries and source attempts. Do not count a skip as complete,
remove the identity, or use a trivial signature/length contract as a substitute.

Manager and Planner should continue other ready APIs after recording the
deferral. Reviewer confirms that the skip is supported by actual evidence,
the candidate is not overclaimed, and no simple existing mechanism was ignored.
Final reports list callback deferrals separately from other remaining work.
