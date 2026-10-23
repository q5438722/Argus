---
name: "Verus Campaign-Local Toolchain"
description: "Allow one Argus campaign to maintain, modify, build and use its own Verus plus matching vstd when a pinned verifier demonstrably lacks a required Rust language feature. Keep the official baseline immutable and retain exact patch, binary and proof provenance."
---

# Verus Campaign-Local Toolchain

[Chinese reference](references/verus-campaign-local-toolchain.zh-CN.md)

Policy: **campaign-local-verus-v1**, authorized on 2026-10-16.
Read the [shared specification workflow](verus-spec-generation-and-repair.md)
and [artifact policy](spec-artifact-workspace.md).

Each Argus specification campaign may maintain and compile its own local Verus
source tree, with a matching locally built vstd, to address a demonstrated
unsupported Rust language feature or a verifier translation/modeling gap.
This permission applies without waiting for another operator decision for each
bounded local patch. It does not authorize editing the shared official
toolchain, silently changing the proof baseline, weakening verification, or
publishing changes upstream.

## Layout and baseline identity

Keep the immutable official baseline under the shared artifact toolchain root.
Put the mutable campaign-local source/build under the campaign workdir, for
example:

```text
<campaign>/toolchains/local-verus/
    source/
    patches/
    build/
    manifest.json
```

Start from the campaign's pinned upstream commit. Record:

- upstream repository, commit and original source-tree digest;
- every local patch/diff, its purpose, affected verifier phase and review;
- Rust toolchain, solver, build command and matched vstd source/build;
- resulting verifier/vstd/binary hashes and regression commands;
- which APIs and proof artifacts used the official or local toolchain.

Do not combine a locally changed verifier with unrelated prebuilt vstd
artifacts. Build a compatible verifier and vstd together. Keep local toolchains,
targets and compiler logs out of specdet input snapshots.

## When to modify the local verifier

First reproduce the limitation on the immutable official baseline with a
minimal input and actual diagnostic. Rule out a faulty API contract, source
translation, missing existing specification, unsupported proof encoding,
resource limit, or ordinary Rust version mismatch.

Use a local patch for a narrow, demonstrated issue such as parser/lowering
support, method/function-item correspondence, a missing safe translation of a
Rust construct, or another bounded verifier capability required by the real
source. Do not modify Rust/std executable semantics merely to avoid adding
language support.

Prefer the smallest semantic change. Do not:

- turn a failed obligation into an assumption or delete it;
- add answer-bearing axioms, `admit`, broad `external_body`, or a target-specific
  special case that returns the expected proof result;
- weaken soundness, skip bodies, suppress diagnostics or silently narrow the
  original API domain;
- alter the shared official Verus/vstd installation.

The patch must include positive tests for the intended construct and negative
or regression controls that would fail if the new rule were overly broad.
Build and verify the matching vstd, then run the minimal reproducer and affected
project checks. A green build alone is not evidence of soundness or source
correspondence.

## Proof result labels

Results obtained with a campaign-local verifier must name its manifest and
binary digest. Report them as **verified with campaign-local Verus**, not as
official-baseline successes. Historical official results remain unchanged.

An API may be accepted for the campaign when both required proof tracks pass
on the same reviewed local toolchain and the API contract/source correspondence
is independently accepted. The final report must separate:

- official-baseline results;
- local-toolchain results and exact patch dependency;
- remaining upstream-porting or independent-review obligations.

Do not copy a local-toolchain result into a shared vstd/upstream claim. A later
official release may replace the local patch only after exact contract and
behavioral compatibility are checked.

## Independent review and failure handling

Before counting a local-toolchain proof, Reviewer inspects the patch, original
diagnostic, generated queries/obligations, regression controls, matched vstd
build and toolchain manifest. Verifier implementation changes are allowed by
this policy only inside the campaign-local tree; broader tool changes still
need separate authorization.

If the patch becomes broad, affects the trusted basis in an unclear way, fails
regressions, or needs substantial new language/callback semantics, retain the
attempt as a local issue and replan or skip the affected API according to the
applicable API-family policy. Do not let local verifier development block
independent module work indefinitely.
