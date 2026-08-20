---
title: "13 — DSH 配置档"
date: 2026-08-19
status: draft
---

# 13 — DSH 配置档

## Overview

DSH ships an **executor edition** (`examples/acp-agent/cordis.yml`, used in
`executor/cordis.yml`) but no official orchestrator edition. This document
presents both profiles side-by-side for reference.

## Profile Comparison

| Aspect | Executor Edition | Orchestrator Edition |
|:--|:--|:--|
| **Primary role** | Receive commands, execute tasks | Discover sessions, route tasks, manage subagents |
| **Transport** | ACP stdio server (driven by Hermes) | No ACP server; drives executors via ACP client |
| **Agent core** | `acp-agent` (ACP bridge + persistence) | `agent-spine-demo` (pre-created agents) |
| **File access** | Sandboxed (workspace-write) | Local or relaxed policy |
| **Bash** | `bash-sandbox` | `bash-local` |
| **Subagents** | spawn + fork (in-process only) | + `subagent-acp` (remote executors) |
| **Session mgmt** | Own session only | Multiple sessions, discovery, injection |
| **Terminal/PTY** | Yes (for code execution) | Yes (short ops — orchestrator runs commands directly too; delegates only long build-fix loops) |
| **LSP** | Yes (code intelligence) | Optional (symbol navigation when orchestrator reviews executor diffs) |
| **Code runtime** | Yes (safe model-written programs) | No (delegates to executors) |
| **Web tools** | Yes (docs lookup) | Optional |
| **Hooks** | Claude Code + Codex bridges | Not applicable |
| **MCP clients** | markitdown / pageindex / astra-kb | Same (if shared tools needed) |
| **Skills base** | dev-skills + vcs-assist | Same |

## Shared Plugins (Both Profiles)

These plugins are common to both executor and orchestrator editions:

```yaml
# LLM adapter (config differs per profile)
- id: llm
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      aigate:
        displayName: Astra AI Gate
        apiKeyEnv: AIGATE_<PROFILE>_KEY   # executor or orchestrator
        api: openai-completions
        baseURL: http://homecentre01.nb.internal:20128/v1
        models:
          - id: auto/<profile>
            name: AIGate <profile>
            contextWindow: 65536

# Session persistence
- id: persistence
  name: '@deepseek-ai/dsh-session-persistence-jsonl'
  config:
    root: './.sessions'
    compression: zstd

# Token management
- id: token-meter
  name: '@deepseek-ai/dsh-token-meter'

# Context compaction
- id: compaction-basic
  name: '@deepseek-ai/dsh-compaction-basic'
  config:
    thresholdRatio: 0.8
    retainRatio: 0.08
    maxTokens: 8192
    compactionRetries: 1

# Subprocess management
- id: subprocess
  name: '@deepseek-ai/dsh-subprocess-local'

# Sandbox (executor only, not in orchestrator)
# - id: sandbox
#   name: '@deepseek-ai/dsh-sandbox-local'
# - id: sandbox-policy
#   name: '@deepseek-ai/dsh-sandbox-policy'
#   config:
#     mode: workspace-write
#     workspaceRoot: !!js process.cwd()

# Approval policy
# Executor: ask (sandboxed writes need a grant)
# Orchestrator: ask — see "Approval policy" section below.
#   `never` is NOT a relaxed mode: it fail-closes (rejects every gated op),
#   which would lock the orchestrator out of its own structural writes.
- id: approval
  name: '@deepseek-ai/dsh-user-approval'
  config:
    policy: ask

# Skills base
- id: skill
  name: '@deepseek-ai/dsh-skill'
- id: skill-filesystem
  name: '@deepseek-ai/dsh-skill-filesystem'
- id: tool-skill
  name: '@deepseek-ai/dsh-tool-skill'

# Code search (ripgrep)
- id: tool-fs-search
  name: '@deepseek-ai/dsh-tool-fs-search'
  config:
    sampleOverCapGlobResults: true

# Precise editor
- id: str-replace-editor
  name: '@deepseek-ai/dsh-tool-str-replace-editor'

# Workflow engine
- id: workflow-worker-thread
  name: '@deepseek-ai/dsh-workflow-worker-thread'
  config:
    provider: spawn
- id: tool-workflow
  name: '@deepseek-ai/dsh-tool-workflow'

# Ralph (goal iteration)
- id: tool-ralph
  name: '@deepseek-ai/dsh-tool-ralph'

# Todo tracking
- id: tool-todo
  name: '@deepseek-ai/dsh-tool-todo'
  config:
    allowParallelInProgress: true

# Repeat reminder
- id: repeat-tool-reminder
  name: '@deepseek-ai/dsh-repeat-tool-reminder'

# MCP clients (optional, same for both)
# - id: mcp-markitdown
#   name: '@deepseek-ai/dsh-mcp-client'
#   config:
#     serverName: markitdown
#     transport: streamable-http
#     url: http://homecentre01.nb.internal:20128/api/mcp/servers/markitdown/stream
#     headers:
#       Authorization: !!js '`Bearer ${process.env.AIGATE_<PROFILE>_KEY}`'
#     failOnStartupError: true
# - id: mcp-pageindex
#   name: '@deepseek-ai/dsh-mcp-client'
#   config:
#     serverName: pageindex
#     transport: streamable-http
#     url: http://homecentre01.nb.internal:20128/api/mcp/servers/pageindex/stream
#     headers:
#       Authorization: !!js '`Bearer ${process.env.AIGATE_<PROFILE>_KEY}`'
#     failOnStartupError: true
# - id: mcp-astra-kb
#   name: '@deepseek-ai/dsh-mcp-client'
#   config:
#     serverName: astra-kb
#     transport: streamable-http
#     url: http://homecentre01.nb.internal:20128/api/mcp/servers/astra-kb/stream
#     headers:
#       Authorization: !!js '`Bearer ${process.env.AIGATE_<PROFILE>_KEY}`'
#     failOnStartupError: true
```

## Executor Edition: Unique Plugins

```yaml
# Agent spine: ACP automation server (executor-specific)
- id: acp-agent
  name: '@deepseek-ai/dsh-acp-demo'
  config:
    provider: aigate
    model: auto/executor
    persistenceRoot: !!js "process.env.DSH_SESSIONS_ROOT ?? './.sessions'"
    persistenceCompression: zstd
    workspaceContext:
      maxBytes: 65536
    persona: |
      You are a coding executor powered by the {{model}} model. Your working
      directory is {{cwd}}. Your bash tool runs under a file sandbox — a
      `[sandbox: file access denied …]` result is policy, not a command bug.

      You are the executor: write, test, debug code. Nothing else.
      NEVER run git write operations (commit/push/rebase/reset/checkout).
      Verify your work by running the code or tests. Keep answers brief
      and factual. On a permission wall, STOP and report the exact tool name.

# Filesystem: sandboxed (executor-specific)
- id: fs-sandbox
  name: '@deepseek-ai/dsh-fs-sandbox'
  config:
    cwd: !!js process.cwd()

# Bash: sandboxed (executor-specific)
- id: bash
  name: '@deepseek-ai/dsh-bash-sandbox'
  config:
    timeoutMs: 60000

# Hooks (Claude Code + Codex bridges, executor-specific)
- id: hooks-claude-code
  name: '@deepseek-ai/dsh-hooks-claude-code'
  config:
    configPath: ./hooks.json
- id: hooks-codex
  name: '@deepseek-ai/dsh-hooks-codex'
  config:
    configPath: ./codex-hooks.json

# Terminal (PTY, executor-specific)
- id: terminal
  name: '@deepseek-ai/dsh-terminal'
- id: terminal-bash
  name: '@deepseek-ai/dsh-terminal-bash'
- id: tool-terminal
  name: '@deepseek-ai/dsh-tool-terminal'

# LSP (language intelligence, executor-specific)
- id: lsp
  name: '@deepseek-ai/dsh-lsp'
- id: lsp-stdio
  name: '@deepseek-ai/dsh-lsp-stdio'
  config:
    servers:
      clangd:
        command: clangd
        extensionToLanguage:
          '.c': c
          '.h': h
          '.cpp': cpp
          '.cc': cpp
          '.cxx': cpp
          '.hpp': cpp
          '.hh': hh
          '.hxx': hxx
      rust-analyzer:
        command: rust-analyzer
        extensionToLanguage:
          '.rs': rust
- id: tool-lsp
  name: '@deepseek-ai/dsh-tool-lsp'

# Code runtime (safe model-written program execution, executor-specific)
- id: code-runtime
  name: '@deepseek-ai/dsh-code-runtime-worker-thread'

# Web (docs/dependency lookup, optional)
- id: web
  name: '@deepseek-ai/dsh-web'
- id: web-search-deepseek
  name: '@deepseek-ai/dsh-web-search-deepseek'
- id: tool-web
  name: '@deepseek-ai/dsh-tool-web'
```

## Orchestrator Edition: Unique Plugins

```yaml
# Agent spine: pre-created agents (orchestrator-specific)
- id: agent-spine
  name: '@deepseek-ai/dsh-agent-spine-demo'
  config:
    agents:
      - id: main
        provider: aigate
        model: auto/orchestrator
        cwd: !!js process.cwd()
    workspaceContext:
      maxBytes: 65536
    persona: |
      You are a multi-agent orchestrator. Your job is to discover sessions,
      route tasks to appropriate executors, and manage inter-agent collaboration.
      NEVER execute code directly — delegate to executors.

# Filesystem: local, no sandbox (orchestrator-specific)
- id: fs-local
  name: '@deepseek-ai/dsh-fs-local'
  config:
    cwd: !!js process.cwd()

# Bash: local, no sandbox (orchestrator-specific)
- id: bash-local
  name: '@deepseek-ai/dsh-bash-local'
  config:
    timeoutMs: 60000

# ACP subagent provider (orchestrator-specific: drives remote executors)
- id: subagent-acp
  name: '@deepseek-ai/dsh-subagent-acp'
  config:
    providerName: acp
    command: node
    args:
      - --import
      - tsx
      - packages/examples/acp-demo/src/bin.ts
      - --config
      - executor/cordis.yml
    cwd: !!js "'/home/alrcatraz/Projects/dsh'"

# Session query (cross-session search, orchestrator-specific)
- id: tool-session-query
  name: '@deepseek-ai/dsh-tool-session-query'

# Subagent tools (orchestrator-specific: multiple transports)
- id: tool-subagent-control
  name: '@deepseek-ai/dsh-tool-subagent-control'
- id: tool-subagent-list-agents
  name: '@deepseek-ai/dsh-tool-subagent-control/list-agents'
- id: tool-subagent-report
  name: '@deepseek-ai/dsh-tool-subagent-report'

# Spawn-based delegation
- id: tool-subagent-spawn
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: spawn
    toolName: subagent_spawn
    backgroundMode: continuable
    maxDepth: 1

# Fork-based delegation
- id: tool-subagent-fork
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: fork
    toolName: subagent_fork
    backgroundMode: one-shot
    enableRunInBackground: false
    maxDepth: 1

# ACP-based delegation (remote executors)
- id: tool-subagent-acp
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: acp
    toolName: subagent_acp
    backgroundMode: continuable
    maxDepth: 1
```

## Key Differences Summary

### What the Executor Has That the Orchestrator Doesn't

| Plugin | Reason |
|:--|:--|
| `acp-agent` | Orchestrator doesn't expose ACP server |
| `fs-sandbox` | Orchestrator needs full filesystem access |
| `bash-sandbox` | Orchestrator needs full shell access |
| `hooks-claude-code` / `hooks-codex` | Not applicable to orchestration |
| `code-runtime` | Orchestrator delegates execution |
| `web` / `web-search` / `tool-web` | Optional for orchestrator (docs/dependency lookup) |

> Note: `terminal` / `terminal-bash` / `tool-terminal` and `lsp` / `lsp-stdio` /
> `tool-lsp` are **shared capabilities**, not executor-only — the orchestrator
> runs short ops directly (see profile table above). Remove the executor-only
> designation for these when diffs are copied between profiles.

### What the Orchestrator Has That the Executor Doesn't

| Plugin | Reason |
|:--|:--|
| `agent-spine-demo` | Pre-created agents, not ACP-driven |
| `subagent-acp` | Drives remote executors over ACP |
| `tool-subagent-acp` | Model-facing ACP delegation tool |
| `tool-session-query` | Cross-session discovery capability |
| `fs-local` | Full filesystem access (no sandbox) |
| `bash-local` | Full shell access (no sandbox) |

## Deployment Notes

### Keys

- **Executor key**: `AIGATE_EXECUTOR_KEY` — scope `execute:completions`
- **Orchestrator key**: `AIGATE_ORCHESTRATOR_KEY` — scope `orchestrate:completions`
- Each key is machine-local, stored in `~/Projects/dsh/.env` (gitignored)

### Models

- **Executor**: Use a coding-optimized model with moderate context window
- **Orchestrator**: Consider a larger context window model (more session state to track)

### Persistence

- **Executor sessions**: `~/.dsh/.sessions/` (JSONL + zstd)
- **Orchestrator sessions**: Separate root to avoid confusion
- Both use UUID session IDs; coordinate with Hermes session IDs
  (format: `YYYYMMDD_HHMMSS_uuid_prefix`) for cross-agent discovery

### Subagent Transport Selection

| Transport | Use Case | Characteristics |
|:--|:--|:--|
| `spawn` | In-process child | Fast, shared memory, same thread |
| `fork` | Forked child | Process isolation, inherits memory snapshot |
| `acp` | Remote executor | Fresh subprocess, separate runtime, ACP protocol |

For most orchestration scenarios, use `spawn` for local subtasks and `acp`
for remote executors. Reserve `fork` for one-shot tasks that benefit from
memory inheritance.

## Orchestrator Operational Additions

The Orchestrator Edition spine above covers session discovery, delegation and
filesystem reach. Three capabilities are deliberate additions for orchestration
work (decompose→plan→delegate, hold durable objectives, timed dispatch):

### Plan mode (decompose before you delegate)

The orchestrator decomposes a task into a plan and presents it via
`exit_plan_mode` for review *before* dispatching any sub-delegation. Add:

```yaml
- id: plan-mode
  name: '@deepseek-ai/dsh-plan-mode'
  config:
    section: |
      You are in plan mode. Explore the task and design the sub-delegation
      plan, then present it via exit_plan_mode for review before acting.
```

### Durable same-session objectives (goal state)

Hold the run's objectives in goal state so a long orchestration keeps its
decomposed targets across subagent returns:

```yaml
- id: goal
  name: '@deepseek-ai/dsh-goal'
- id: tool-goal
  name: '@deepseek-ai/dsh-tool-goal'
- id: command-goal
  name: '@deepseek-ai/dsh-command-goal'
```

### Scheduled / recurring dispatch

Optional `schedule` if the orchestrator drives timed or recurring dispatch
(health re-checks, dependency bumps):

```yaml
- id: schedule
  name: '@deepseek-ai/dsh-schedule'
```

### Approval policy (why `ask`)

`@deepseek-ai/dsh-user-approval` has a binary `policy`: `ask` or `never`.
There is no smart/split tier; the decision lives in the **answerer** that
listens for `approval/request`.

- `never` fail-closes: every operation requiring approval is rejected
  outright. On the orchestrator this locks out its own structural writes —
  it is **not** an "unrestricted" mode. Do not use `never` on the orchestrator.
- `ask` routes gated ops to an answerer. Headless without a composed answerer
  resolves `unavailable` (also fail-closed). Compose a decision answerer —
  e.g. a community reviewer plugin (`Letter2025/dsh-approval-llm`,
  `PerryLink/dsh-auto-review`) that backs `approval/request` with a reviewer
  LLM returning ALLOW/DENY/ESCALATE — for the same "model reviews first, human
  fallback" shape as Hermes smart approval.

Use `ask` with a decision answerer. For orchestrator write discipline, every
structural write then goes through review rather than an unlogged pass.

### Orchestrator key scope

`AIGATE_ORCHESTRATOR_KEY` — scope `orchestrate:completions`, machine-local in
`~/Projects/dsh/.env` (gitignored). A separate scope from
`AIGATE_EXECUTOR_KEY` (`execute:completions`) keeps orchestrate separate from
execute in the gate.

### Boot / launch (canonical)

The executor edition boots directly from a `cordis.yml` via tsx
(`node --import tsx …/bin.ts --config executor/cordis.yml`). The orchestrator
edition boots through the **official `--profile` launcher** instead — the same
path as the shipped `headless` and `web` profiles — giving it layered
configuration (bundle layers below, your `cordis.patch.yml` overlay above),
hot-reload of the user layer, and `dsh plugin` for out-of-tree plugins.

```bash
dsh --profile orchestrator --dump-config      # dry-run: inspect resolved tree
dsh --profile orchestrator "<task>"            # live one-shot run
```

The profile lives at `~/.dsh/profiles/orchestrator/`:

- `package.json` → `dsh.profile.bundles: ["@deepseek-ai/dsh-base",
  "@deepseek-ai/dsh-headless"]` plus any out-of-tree plugin dependencies
  (e.g. `@deepseek-ai/dsh-llm-pi-ai`).
- `cordis.patch.yml` → the orchestrator overlay applied last (AIGate routing
  via `agent-default-model` + `llm-pi-ai`, the orchestrator persona, and any
  plugin not already in a bundle).
- `~/.dsh/.env` → the machine-local `AIGATE_ORCHESTRATOR_KEY`
  (`loadLayeredEnv` reads inherited → invoking-dir → Harness-home).

`dsh-base` already mounts the approval seam (`approval` →
`@deepseek-ai/dsh-user-approval`; policy resolves from the permission presets,
`workspace-write` ⇒ `ask`), `goal`/`tool-goal`, and the `llm-pi-ai` adapter —
so the overlay must **override** these, **not re-insert** them (re-inserting
`approval`/`goal` fails with `duplicate loader entry id`). `dsh-headless`
mounts the one-shot runner (`dsh --profile orchestrator "<task>"`). During
bring-up you may reuse the executor key (scope `execute:completions`) for model
calls, moving to the dedicated `orchestrate:completions` key before production.

#### Interactivity note

The `headless` bundle runs a **one-shot** agent: it takes one task, produces a
durable result, and exits. In this mode the orchestrator **plans and narrates
the split but does not spawn live ACP subprocesses that outlive the turn** —
genuine long-lived dispatch across remote executors is the executor
(`acp-agent`) / future orchestrator TUI surface. `headless` is the right fit
for validating configuration and model routing; choose the interactive surface
for sustained orchestration. This bounds the scope of what a `headless`
deploy verifies.
