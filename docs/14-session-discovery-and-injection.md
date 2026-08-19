---
title: "14 — Session Discovery and Injection"
date: 2026-08-19
status: draft
---

# 14 — Session Discovery and Injection

## Problem Definition

A2A `a2a_call` creates a new context with `chat_id = context_id`. Sessions
created manually (browser tabs) or by executors (DSH, OpenCode) lack this
binding. When an orchestrator needs to resume work in an existing session —
its own or a peer's — the A2A protocol provides no direct mechanism.

**Key finding: there is no universal injection protocol.** Each orchestrator
uses its own native interface for session injection.

## Core Design Decision

Rather than pursuing a one-size-fits-all injection API, this design adopts a
**delegated injection model**:

1. **Source orchestrator** discovers the target session ID (via local lookup)
2. **Source orchestrator** sends an A2A message containing `{target_session, content}` to the **destination orchestrator**
3. **Destination orchestrator** uses its own native injection method to deliver the message to the specified session

This keeps responsibilities clear: each agent handles its own sessions.

## Session Discovery

### Hermes Orchestrator

Query `~/.hermes/state.db`:

```sql
SELECT id, title, source FROM sessions WHERE title LIKE '%keyword%' AND ended_at IS NULL;
```

Verified working (2026-08-19). The `sessions` table schema:

| Column | Type | Notes |
|:--|:--|:--|
| `id` | TEXT PK | Format: `YYYYMMDD_HHMMSS_uuid_prefix` |
| `title` | TEXT | Auto-generated from first user message (may be truncated) |
| `source` | TEXT | Platform origin: `a2a`, `acp`, `cli`, `telegram`, etc. |
| `chat_id` | TEXT | Bound to `context_id` only for A2A-created sessions |
| `started_at` | REAL | Unix timestamp |
| `ended_at` | REAL | NULL if active |
| `message_count` | INTEGER | Total messages in session |
| `model` | TEXT | Model used |
| `last_activity_at` | REAL | Last activity timestamp |

**Limitation**: ACP-originated sessions (DSH/OpenCode) have `title IS NULL`,
making keyword-based discovery unreliable. Mitigation: require users to provide
session IDs or use descriptive titles when creating sessions.

### DSH Orchestrator

DSH stores sessions as JSONL files compressed with zstd:

```
~/.dsh/.sessions/<cwd_hash>/<session_uuid>/session.jsonl.zstd
```

The first line of each file contains session metadata:

```json
{
  "type": "session",
  "version": 0,
  "id": "<uuid>",
  "createdAt": <timestamp>,
  "cwd": "/path/to/workspace",
  "delegationDepth": 0
}
```

Title is auto-generated from the first user message (truncated at ~25 chars).
Discovery requires iterating all session directories and decompressing the first
line — slower than SQL but functional.

## Injection Methods

Each orchestrator uses its native interface:

### Hermes: `hermes chat --resume`

```bash
hermes chat --resume <session_id> -q "<message>"
```

**Verified working (2026-08-19)**:

- Binds the CLI process to the target `session_id`
- Loads full conversation history
- Sends the injected message
- Results are atomically written back to the original SQLite instance
- All subsequent turns append to the same session context

**Known limitation**: If the target session's toolset configuration references
non-existent toolsets (`Warning: Unknown toolsets: ...`), the agent may hang or
timeout. This is a session-specific configuration issue, not a `--resume` bug.

### DSH: ACP `session/prompt`

```typescript
// Via ACP client
await acpClient.prompt({
  sessionId: "<session_uuid>",
  prompt: [{ type: "text", text: "<message>" }]
});
```

DSH's ACP server accepts a `sessionId` parameter in `session/prompt`, allowing
messages to be injected into existing sessions. **Requires an active ACP channel
to the DSH orchestrator.**

**Limitation**: DSH runs as a stdio server. When driven by another orchestrator
(e.g., Hermes via CopilotACPClient), the stdin/stdout pipe is occupied. An
independent ACP connection must be established for external injection.

### Other Orchestrators

Each additional orchestrator type implements its own injection method. Document
them in their respective skills.

## Cross-Agent Collaboration Flow

```
Orchestrator A (Hermes)                    Orchestrator B (DSH)
     |                                           |
     |  User: "collaborate with B's 'task-x'    |
     |         session"                          |
     |                                           |
     |  1. Discover target session_id locally   |
     |  2. Construct A2A Message:               |
     |     {                                    |
     |       type: "a2a_injection",            |
     |       source: "orchestrator-a",         |
     |       target_session: "<session_id>",   |
     |       content: "Please collaborate on:  |
     |                  ..."                    |
     |     }                                    |
     |  3. Send via A2A to B                   |
     |─────────────────────────────────────────>│
     |                                           |
     |                                           |  4. B receives A2A Message
     |                                           |  5. B looks up session_id in local registry
     |                                           |  6. B uses native inject() to deliver
     |                                           |
```

The A2A message payload uses a structured format so the receiving orchestrator
can identify it as a cross-session collaboration request rather than a regular
user message.

## A2A Message Format

```json
{
  "type": "a2a_injection",
  "source": "<orchestrator_identifier>",
  "target_session": "<session_id>",
  "content": "<actual task description>"
}
```

- `type`: Identifies this as a cross-session injection (not a regular message)
- `source`: Identifier of the sending orchestrator (for audit trail)
- `target_session`: The session ID the receiving orchestrator should resume
- `content`: The actual task description to execute

Receiving orchestrators SHOULD parse this format and treat the `content` field
as the actionable instruction, while using `source` and `target_session` for
logging and verification.

## Limitations and Deferrals

### No Universal Protocol

There is no single API that works across all orchestrator types. Each must
implement its own injection method. This is intentional: forcing a common
interface would require modifying upstream projects (Hermes, DSH) and create
maintenance burden.

### ACP Session Metadata Gap

ACP-originated sessions (DSH, OpenCode) typically have empty `title` fields
in the orchestrator's session store. This makes natural-language keyword search
unreliable. Mitigations:

1. **Require session IDs**: When precise targeting is needed, users/orchestrators
   should provide the exact session ID rather than relying on keyword search.
2. **Descriptive titles**: Orchestrators that create sessions programmatically
   SHOULD set meaningful titles to improve discoverability.
3. **Parent-child relationships**: Use `parent_session_id` (where available) to
   trace session lineage instead of keyword matching.

### DSH Stdio Channel Constraint

DSH's stdio transport means only one ACP client can drive it at a time. External
injection requires either:

- An independent ACP connection (separate process)
- Coordination with the driving orchestrator to temporarily release the channel
- Using DSH's internal APIs (not through ACP)

This constraint applies specifically to the executor edition of DSH. The
orchestrator edition (if deployed) may support concurrent connections.

### OpenCode Injection Not Verified

OpenCode's `-s/--session` flag was tested and failed with a server error. This
may be a version-specific bug or limited to fork mode. OpenCode injection is
deferred until verified working.

## Relationship to Other Docs

- **docs/13** (§13.6): Covers A2A context routing and health checks. This doc
  addresses the complementary problem of injecting messages into non-A2A
  sessions.
- **ADR 0006** (inter-agent protocol): Defines the overlay network and auth
  boundary. Cross-agent session injection operates within this boundary.
