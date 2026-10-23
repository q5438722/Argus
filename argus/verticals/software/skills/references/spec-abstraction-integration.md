# Integrate specifications with existing abstractions

[Chinese reference](spec-abstraction-integration.zh-CN.md)

Use this reference when an API creates or exposes a value that callers consume
through an existing library protocol, especially iterators and borrowed views.
It supplements the [shared Verus workflow](../verus-spec-generation-and-repair.md);
it is supporting knowledge, not a separate Skill or authorization to change
source code, the verifier, or the trusted basis.

## 1. Reuse a semantic protocol before inventing a parallel view

Inspect the intended library baseline for an existing specification protocol:
its trait extension, state observations, consumer contracts, enabling conditions,
and nearby implementations. Reusing only a data type or naming convention is
not enough; the new API's guarantees must reach the contracts callers use.

Prefer implementing or extending that protocol over introducing an independent
view with similar fields. If the existing abstraction is insufficient, explain
the missing observation and provide a source-backed bridge between the new
model and the existing interface. Do not require Manager to choose the exact
representation or make a new view mandatory merely because the API is new.

## 2. Model what the consumer actually receives

Select observable contents, order, branches, state changes, and borrowing
effects from the source and docstrings. Metadata such as source contents,
length, direction, or group size can support a model, but does not by itself
determine the returned values.

For an iterator, the standard remaining sequence is `Seq<Self::Item>`, not
necessarily a flattened sequence of source elements. If each item is a slice,
specify the sequence of slices and their contents, order, and boundaries.
Preserve the actual item type and generic calling domain.
State whether a completeness result concerns view-level uniqueness or raw
return identity; do not promote one to the other.

## 3. Connect construction, consumption, and later observation

Check the constructor -> consumer -> observer chain, not only a constructor's
initial metadata. Construction should establish the selected protocol state
and applicable enabling conditions. Consumption should expose its return value
and state transition through the existing contracts. Later observers must agree
with the state they actually observe, including exhaustion when relevant.

An auxiliary observer's equality with the protocol state at construction is a
constructor-only relation unless preservation or a state-relative relation is
independently established. Do not reuse it after consumption without that
evidence. Likewise, declaring trait conformance does not by itself prove the
source implementation obeys the claimed laws.

Prefer the existing protocol's transitions and termination support to a second
hand-written state machine. If the protocol cannot express required behavior,
retain the precise missing obligation instead of presenting an isolated view
as a complete API family.

## 4. Preserve borrowing and callback effects

For mutable borrowed items, describe both their initial contents and how their
eventual values flow back to the owner, with frames for unaffected regions.
Use the baseline's existing `old`/`final` and prophecy support where appropriate.
Do not mechanically copy immutable-item specifications, freeze lawful caller
writes, or mistake a borrow's final value for guaranteed destruction.

For callback-driven consumers, retain relevant callback preconditions, state,
call behavior, and termination conditions. An unconnected pure predicate is
not a model of a stateful callback merely because it has matching arguments.

## 5. Judge auxiliary models by their semantic connections

A ghost or uninterpreted helper is not rejected merely by its syntax. It must
have meaningful, source-backed constraints and connect to the selected
observations and consumer contracts. Reuse established trusted abstractions
within their supported conditions; do not add a new axiom, assume the target
answer, or hide missing behavior in an opaque helper.

This does not relax an explicit task requirement such as zero-UF. Distinguish
that requirement from library integration style, and disclose any remaining
boundary or blocker rather than claiming completion.

## 6. Exercise the contracts through real clients

Add representative verification clients to the repository's existing test suite.
Use the actual API bindings and loaded candidate contracts, not manual
assumptions of the expected outputs. For a stateful family, cover a meaningful
construction-and-consumption sequence, applicable boundary/exhaustion cases,
and mutable writeback when relevant.

Assert concrete observations that distinguish the intended behavior from
metadata-only or unconstrained alternatives. A client that checks only creation,
length, or well-formedness may leave the missing semantic connection untouched.
Keep clients bounded to the affected behavior rather than testing every
combination or adding a separate testing framework.

These clients check integration and usability; they do not replace either
required proof track. Source correctness still establishes implementation
correspondence, and completeness still uses the declared observation and
comparison. A unique answer in a detached model does not establish that the
library consumer is connected to it.

## Motivating evidence, not a fixed template

The review on
[verus-lang/verus#2839](https://github.com/verus-lang/verus/pull/2839#pullrequestreview-5432144255)
asks for reuse of the existing iterator specification interface instead of a
separate view. The changes in
[verus-lang/verus#2836](https://github.com/verus-lang/verus/pull/2836/files)
show constructor guarantees connected to that interface and clients using
ordinary iteration. Generalize that connection, not a particular API's helper
names, formulas, or representation. Keep current paths, versions, and scope in
the project.
