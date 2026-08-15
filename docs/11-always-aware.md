# 11. Always-Aware — Orchestrator & Guardian Architecture Awareness

> **Purpose**: guarantee that the orchestrator and the guardian are aware of
> the multi-agent architecture **at every decision point** — not just when
> task keywords happen to match a skill description. This chapter defines the
> guarantee mechanism: layered approach (public) and deployment notes (private
> copy only).

## 11.1 Problem & Goal

**Background**: the constellation skill does not auto-load; in long tasks the
orchestrator may work solo instead of dispatching. Triggering relies on a
memory hint plus skill-description keyword matching, which leaves a coverage
gap. **Goal** = the orchestrator always knows the dispatchable set and routes
via ACP/A2A at the right moment (routing table: 01 §2.1).

**Constraint**: the mechanism must be low-maintenance — adding "always inject
X" must not require changing plugin code (Unix-style extension: drop a file,
it works).

## 11.2 Guarantee Mechanism (layered approach, implementation-agnostic)

### Layer 1 — Resident injection (visible on every LLM call)

**Idea**: append a block of **static architecture facts** (existence +
dispatchable set + routing pointer) to the system prompt of every LLM call.
This is the physical guarantee of "always": as long as the model runs, the
facts are in context.

**Implementation principle (Linux drop-in pattern)**: injection content is
provided by an **operator-owned directory**, merged in filename-sorted order
on every call; a single failing file is skipped (safe degradation).
`10-*.md` / `20-*.md` prefixes control ordering. Add = new file; disable =
rename; delete = remove file. **Content ownership stays with the operator,
not the implementation** — replacing the implementation never loses content.

**Current injected content**: the dispatchable set (executor via ACP, guardian
deferred) + routing pointer (01 §2.1) + "if parallelisable or needs a second
machine, dispatch via ACP instead of working solo".

### Layer 2 — Triggered loading (skill-description hook)

**Idea**: the constellation skill's description (resident in the system
prompt's skill index) carries trigger keywords — dispatch / parallel /
multi-machine / cross-machine. On a hit, `skill_view` loads the full skill as
procedural memory. Layer 1 guarantees "knows it exists"; layer 2 guarantees
"knows the details when needed".

### Layer 3 — Dynamic discovery (future evolution)

**Idea**: A2A discover queries peer agents at runtime, replacing the static
snapshot (ADR 0006). Current topology (2 executors + deferred guardian) is
100% covered by the static snapshot, **so no dynamic layer is needed yet**.
Adoption trigger: member count/topology changes frequently, or new
discoverable services appear. Interface reserved, not implemented.

## 11.3 Deployment Notes (private copy only)

> ⚠️ The concrete implementation — plugin, paths, environment variables, and
> the exact injected snapshot — is recorded **only in the private copy** of
> this blueprint (sanitisation gate: AGENTS.md). The public copy intentionally
> carries the mechanism rationale (11.2) without deployment specifics. When
> reproducing the mechanism, follow the private copy's deployment notes and
> its operator-owned drop-in content directory.

## 11.4 Guardian Awareness

The guardian has **no carrier device yet** — deployment deferred
(PLAN.md). Design intent:

- the guardian senses architecture state via the shared fact layer
  (registry + status files; 06 twin-star pattern);
- its "always aware" is guaranteed by the cron trigger chain + status-file
  polling, not by LLM resident injection;
- once a device is available, activate per 08 guardian-runbook (real registry
  → cron chain → guardian skill).

## 11.5 Verification & Regression

- **Unit / end-to-end**: injection merge logic (ordering, empty dir, bad-file
  skip, empty-file skip, full chain) is covered by the plugin's test suite
  (unit tests + e2e smoke).
- **Manual check**: a new session's system prompt containing the injected
  section = injection active; editing a drop-in file changes the next call's
  injection = live update.
- **Regression risk**: unreadable/empty injection directory → silently skipped
  (no injection; the base anchor block is unaffected).
