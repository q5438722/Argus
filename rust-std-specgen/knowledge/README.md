# Exported Argus knowledge

This directory contains the durable Rust std specgen context that was stored by
Argus outside its source repository.

- `wiki/`: admitted/source-linked Rust std findings and campaign lessons.
- `research/`: reviewed process definitions.
- `checkpoints/`: final compact state summaries for completed campaigns.
- `final-reviews/`: canonical final Reviewer `done` decisions.

Raw events, agent I/O, subagent logs, task databases, intermediate handoffs, and
runtime state are intentionally excluded. They are operational history rather
than reusable learned context and may contain machine-specific paths or large
amounts of redundant data.
