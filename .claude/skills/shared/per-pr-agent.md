# Per-PR Worker Adapter

The per-PR workflow is no longer owned by a Claude-only shared prompt. Use the
canonical agent-agnostic contract instead:

- [docs/agent-workflows/pr-resolution.md](../../../docs/agent-workflows/pr-resolution.md)
- [AGENTS.md](../../../AGENTS.md)

Claude skills may still use this file as a stable include point, but it should
remain an adapter pointer. Do not add repo policy here; update the canonical
workflow or AGENTS.md so Codex and future agents receive the same instructions.
