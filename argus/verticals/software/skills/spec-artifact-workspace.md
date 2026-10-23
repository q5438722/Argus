---
name: "Centralized Specification Artifacts"
description: "Keep spec-generation outputs and shared toolchains beneath one operator-selected artifact root, never as new top-level home directories. Migrate existing campaigns safely with lifecycle controls and evidence-preserving compatibility paths."
---

# Centralized Specification Artifacts

[Chinese reference](references/spec-artifact-workspace.zh-CN.md)

Use one operator-selected artifact root beneath the home directory. For the
current Rust std campaigns, the root is:

```text
~/rust-std-specgen-artifacts/
    runs/<campaign-directory>/
    toolchains/<baseline-date>/
```

Place generated specifications, correctness/completeness proofs, queries,
issues, project logs and scratch/build products beneath the assigned campaign
directory. Share an immutable pinned toolchain under `toolchains/` rather than
copying it into each proof attempt. Do not create new campaign output
directories directly under `~`.
Preserve an existing campaign directory's basename during relocation when
project-local caches or knowledge paths use it.

Manager supplies the exact absolute campaign path to all roles. Derive new
project-relative paths from that workdir; do not invent a second artifact root.
External source repositories and existing Argus control profiles are not
automatically relocated by this rule. New control profiles may also be placed
under the root when their supported lifecycle setup permits it.

## Moving an existing campaign

Get operator approval for migration of active work. Save current work and
checkpoint its unfinished commands, then use the supported cooperative
stop/drain controls before moving its workdir or shared in-use dependencies.
Do not force-kill an unrelated process or edit the job's control files to
pretend it stopped. Resume the same project ID through the supported lifecycle.

Inspect and enumerate exact source/destination directories before acting;
refuse a conflicting destination. Prefer a same-filesystem rename rather than
copying large proof trees. Preserve hidden files, permissions, hardlinks and
all unique source/proof/query evidence. Never recursively delete a broad
directory as part of relocation.

Frozen evidence often contains absolute paths. Preserve old paths as explicit
compatibility symlinks when approved, and record the old-to-new map. The real
artifact directories live under the central root; legacy aliases are not
new output locations. Do not rewrite historical commands, query files,
snapshots, hashes or verdicts merely to change their displayed paths.

Use the supported workdir/configuration interface for live campaign metadata,
update launch configuration and future objectives to the canonical new path,
and independently verify aliases, protected hashes, job IDs and readiness.
Only remove an alias after proving its dependent historical paths no longer
need it and obtaining any required cleanup approval.

## Storage and isolation remain in force

Centralizing storage does not relax the existing projected-input/free-space
gate. Exclude other campaigns, historical runs, toolchains, downloads and
proof-only adapted sysroots from completeness snapshots; preserve the full
actual dependency closure. Use separate task output directories and respect
the independent Reviewer's read-only input/writable-scratch boundary.
Do not broaden access to restricted historical material because its parent
directory moved.
