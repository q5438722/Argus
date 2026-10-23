# TB-PARTIAL-EQ: equality-model trust boundary

[Chinese reference](partial-eq.zh-CN.md)

Policy revision: **conditional-posts-v2**. The operator's correction supersedes
the earlier premise-only interpretation of this boundary.

## Rationale and preferred option

Clarified on 2026-10-12 from the reviewer guidance supplied by the operator:
**not all Rust types implementing `PartialEq` obey Verus's equality model**.
The trait bound `T: PartialEq<U>` does not establish
`<T as PartialEqSpec<U>>::obeys_eq_spec()`. This boundary is a policy for
conditional guarantees, not an axiom asserting universal model conformance.

With `B` denoting that exact conformance predicate and `Post` the complete
postcondition set, the two alternatives have different calling domains:

| Option | Contract shape | Calling domain |
|---|---|---|
| (1) Restricted precondition | `requires B; ensures Post` | Every caller must establish B. |
| **(2) Preferred default** | `ensures B ==> Post` | Original calls remain legal, including !B cases. |

This workflow selects **option (2)** whenever this boundary is needed, to
preserve the original Rust API domain. Option (1) can be valid for an explicitly
restricted API or wrapper, but is not an automatic fallback when a proof fails.
It requires separate operator approval of that restricted scope and an explicit
domain record; never silently apply it to the original std API or report its
results as original-domain conditional guarantees. This clarification retains
the existing **conditional-posts-v2** semantics and historical proof scopes.

## Conditional postconditions, only when needed

If needed for a function's equality-model specification, put **all of that
function's postconditions** on the right of `T::obeys_eq_spec() ==>`.
Do not apply this to every function. Functions that do not need this boundary
retain their ordinary postconditions and original bounds.

For an applicable `T: PartialEq<U>` pair, call the following predicate `B(T, U)`:

```rust
<T as vstd::std_specs::cmp::PartialEqSpec<U>>::obeys_eq_spec()
```

Use the qualified form for the exact receiver/Rhs pair where needed, including
heterogeneous comparisons. Do not substitute a same-type or reverse pair.
`B` is a condition on the guarantees, not a condition on whether the API may be
called. Do not add B as an API precondition or assume that all Rust types obey
the model. Preserve the original Rust API identity, signature, lifetimes, trait
bounds and legitimate preconditions. Do not add `PartialEq` just to introduce
this guard on an unrelated API.

The required shape is schematically:

```rust
ensures
    <T as vstd::std_specs::cmp::PartialEqSpec<U>>::obeys_eq_spec() ==> {
        &&& P1
        &&& P2
        &&& P3
    },
```

`P1`, `P2` and `P3` stand for the complete postcondition set, including return,
content and frame/writeback clauses when present. Do not guard only a return
clause while leaving other project-written postconditions outside the
implication. An equivalent shared predicate is fine if expansion shows the
same complete guard; avoid redundant double guards. Keep fixed upstream vstd
contracts unchanged.

If a project-written inherited-model clause already has its own container
condition `C`, keep that condition inside the outer element guard `B`:

```text
B ==> ((C ==> P_inherited) && P_contents && P_frame)
```

Do not replace this by `(B && C) ==> (P_inherited && P_contents && P_frame)`:
that would drop the content/frame guarantees when B holds but C does not.
Do not infer B implies C, equate the two flags, or leave the inherited clause
outside B. This guards the project's full postcondition without editing the
fixed upstream contracts.

When `B` is true, all guarded guarantees must hold. When `B` is false, the
guarded postconditions give no guarantee; the Rust call is not thereby invalid
or forbidden. Missing model conformance is not permission to assert `B`, hide
an assumption, or redefine logical value equality as Rust's `PartialEq`.

## Dedicated project record

Before using this boundary, maintain `trust_boundaries/TB-PARTIAL-EQ.md`
in the project, separate from `issues/` and proof files. Record the boundary ID
and **conditional-posts-v2** revision, why each affected function needs it,
exact predicates/type pairs, the complete guarded postconditions, pinned vstd
model definitions/contracts, proof/query locations and remaining obligations.
Link the record from the per-API coverage index, both proof tracks, review
verdicts and final report. Other trust boundaries need their own records and
explicit operator approval; this policy is not blanket permission to add them.

## Verify the conditional claim, not a stronger calling requirement

Correctness must check the actual source body or an authorized faithful copy
with the original preconditions and the entire guarded postcondition. In a
proof-only branch where `B` holds, reuse the existing conditional `eq`/`ne`
contracts. Do not assume the target postcondition, patch vstd, invent an axiom,
or bypass an obligation with `assume`/`admit`.

Completeness must say exactly what was checked. With `CondPost = (B ==> Post)`,
the conditional uniqueness question is:

```text
original_preconditions => source establishes CondPost
original_preconditions && CondPost(input, r1) && CondPost(input, r2)
    => (B ==> selected_outputs_equal(r1, r2))
```

Use a supported checker encoding and inspect its generated comparison and
reexecution. If a separate analysis-only adapter uses `B` as a premise to check
this conditional claim, identify that scope explicitly; never transfer the
adapter's premise into the API contract or call it unrestricted determinism.
If the checker cannot express the conditional question, report the limitation;
do not modify queries or manufacture a successful result.

An `!B` example allowing multiple outputs demonstrates lack of unrestricted
uniqueness, not failure of the conditional guarantee. Retain that distinction
without excluding the call from the API domain. Check lawful `B`-true instances
and the vacuous `!B` behavior; false or contradictory premises and zero relevant
obligations are not evidence of a useful proof. Do not automatically add
unconditional empty/length clauses outside the chosen full guard.

## What this boundary does not establish

`eq_spec` is the element comparison model, not Verus logical value equality.
The flag does not supply reflexivity, symmetry, reverse-pair conformance,
absence of interior mutation, call order, short circuiting or panic freedom.
Required state/effect observations remain part of the guarded contract and
still need proof when the guard holds. The source's use of `ne` and bytewise
specialization still needs the relevant existing contracts and correspondence.

Conformance of a container's comparison does not define its `eq_spec` as a
sequence relation; conformance of its elements does not automatically prove
the container's conformance. Reuse actual model definitions where available.
Missing Cow Deref content relations, private/raw-pointer representation
bridges, and target implementation proofs remain obligations. Do not assume
the target postcondition or new content/view equations under this boundary.

## Migration and reporting

For affected project API contracts, remove `B` preconditions introduced solely
by the old policy and replace them with the full conditional postcondition.
Keep unrelated safety preconditions and functions unchanged. Update dependent
clients and proof inputs, preserving old candidates/results and their precise
policy revision. A change to the pre/post contract requires corresponding
correctness and conditional-completeness review; an old premise-only success
is not automatically a success for the new API contract.

Report checked results as **verified under TB-PARTIAL-EQ (conditional-posts-v2)**,
with conditional completeness distinguished from unrestricted determinism.
Keep the canonical API inventory and do not double-count a migrated API.
Old `UNKNOWN`/failed runs do not become passes; old successes retain their
historical scope until migration is actually checked. This policy revision
neither proves missing source bridges nor authorizes tool/implementation edits.
