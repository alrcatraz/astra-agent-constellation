---
title: "15 — DSH Orchestrator Edition Configuration"
date: 2026-08-19
status: draft
---

# 15 — DSH Orchestrator Edition Configuration

## Overview

DSH ships an **executor edition** (`examples/acp-agent/cordis.yml`, used in
`executor/cordis.yml`) but no official orchestrator edition. This document
derives the plugin composition for a DSH orchestrator based on the executor
blueprint and the orchestrator's distinct responsibilities.

## Orchestrator vs Executor: Responsibility Split

| Aspect | Executor | Orchestrator |
|:--|:--|:--|
| **Primary role** | Receive commands, execute tasks | Discover sessions, route tasks, manage subagents |
| **Transport** | ACP stdio server (driven by Hermes) | No ACP server; drives executors via ACP client |
| **Agent core** | `acp-agent` (ACP bridge + persistence) | `agent-spine-demo` (pre-created agents) |
| **File access** | Sandboxed (workspace-write) | Local or relaxed policy |
| **Subagents** | None (leaf worker) | `subagent-acp` + `subagent-spawn` + `subagent-fork` |
| **Session management** | Own session only | Multiple sessions, discovery, injection |

## Derived Plugin Composition

### Core Plugins (shared with executor)

```yaml
# LLM adapter (same as executor)
- id: llm
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      aigate:
        displayName: Astra AI Gate
        apiKeyEnv: AIGATE_ORCHESTRATOR_KEY
        api: openai-completions
        baseURL: http://homecentre01.nb.internal:20128/v1
        models:
          - id: auto/orchestrator
            name: AIGate orchestrator
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

# Agent spine (orchestrator-specific: pre-create main agent)
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
```

### Subagent Providers (orchestrator-specific)

```yaml
# Spawn: in-process child (same thread, shared memory)
- id: subagent-spawn
  name: '@deepseek-ai/dsh-subagent-spawn-in-process'
  config:
    providerName: spawn

# Fork: forked child (separate process, inherits memory snapshot)
- id: subagent-fork
  name: '@deepseek-ai/dsh-subagent-fork-in-process'
  config:
    providerName: fork

# ACP: out-of-process child (fresh subprocess, driven via ACP protocol)
# THIS IS THE KEY PLUGIN FOR ORCHESTRATING REMOTE EXECUTORS
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
```

### Subagent Tools

```yaml
# Delegation control
- id: tool-subagent-control
  name: '@deepseek-ai/dsh-tool-subagent-control'

# List active subagents
- id: tool-subagent-list-agents
  name: '@deepseek-ai/dsh-tool-subagent-control/list-agents'

# Report from continuable children
- id: tool-subagent-report
  name: '@deepseek-ai/dsh-tool-subagent-report'

# Spawn-based delegation (foreground/background)
- id: tool-subagent-spawn
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: spawn
    toolName: subagent_spawn
    backgroundMode: continuable
    maxDepth: 1

# Fork-based delegation (one-shot)
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

### Filesystem and Bash (relaxed policy)

```yaml
# Local filesystem (no sandbox — orchestrator needs full access)
- id: fs-local
  name: '@deepseek-ai/dsh-fs-local'
  config:
    cwd: !!js process.cwd()

# Observation policy (read-before-edit)
- id: fs-observation-policy
  name: '@deepseek-ai/dsh-fs-observation-policy'

# File tools
- id: tool-fs
  name: '@deepseek-ai/dsh-tool-fs'

# Local bash (no sandbox — orchestrator needs full shell access)
- id: bash-local
  name: '@deepseek-ai/dsh-bash-local'
  config:
    timeoutMs: 60000

# Subprocess management
- id: subprocess
  name: '@deepseek-ai/dsh-subprocess-local'
```

### Optional Plugins (orchestrator-specific)

```yaml
# Session query (cross-session search)
- id: tool-session-query
  name: '@deepseek-ai/dsh-tool-session-query'

# Skills base
- id: skill
  name: '@deepseek-ai/dsh-skill'
- id: skill-filesystem
  name: '@deepseek-ai/dsh-skill-filesystem'
- id: tool-skill
  name: '@deepseek-ai/dsh-tool-skill'

# Code search
- id: tool-fs-search
  name: '@deepseek-ai/dsh-tool-fs-search'
  config:
    sampleOverCapGlobResults: true

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
```

### Excluded Plugins (not needed for orchestrator)

| Plugin | Reason |
|:--|:--|
| `acp-agent` | Orchestrator doesn't expose ACP server |
| `fs-sandbox` | Orchestrator needs full filesystem access |
| `bash-sandbox` | Orchestrator needs full shell access |
| `terminal` / `terminal-bash` | Orchestrator doesn't need PTY |
| `hooks-claude-code` / `hooks-codex` | Not applicable to orchestrator |
| `lsp` / `lsp-stdio` | Not needed for orchestration |
| `code-runtime` | Orchestrator delegates execution |

## Key Differences from Executor Edition

1. **No ACP server** — Orchestrator drives executors, not the other way around
2. **`agent-spine-demo` instead of `acp-agent`** — Pre-created agents, not ACP-driven
3. **`subagent-acp` plugin** — Critical for driving remote executors over ACP
4. **Relaxed file/shell policies** — Full access for configuration management
5. **Session query tool** — Cross-session discovery capability

## Deployment Notes

- **Orchestrator key**: Use a separate `AIGATE_ORCHESTRATOR_KEY` (different scope
  from executor key) in `~/Projects/dsh/.env`
- **BaseURL**: Same AIGate endpoint (`http://homecentre01.nb.internal:20128/v1`)
- **Model selection**: Consider using a larger context window model for
  orchestration (more session state to track)
- **Persistence root**: Separate from executor sessions to avoid confusion
- **Session ID format**: DSH uses UUIDs; coordinate with Hermes session IDs
  (format: `YYYYMMDD_HHMMSS_uuid_prefix`) for cross-agent discovery
