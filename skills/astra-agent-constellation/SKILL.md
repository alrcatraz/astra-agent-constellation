---
name: astra-agent-constellation
description: >
  Orchestrator operation manual for the multi-agent constellation — load when a
  task involves executor/guardian routing, agent registry, tool gate, task
  briefs, or cross-machine build-fix loops. Dispatch/parallel/multi-machine
  tasks: remember the constellation can delegate via ACP/A2A — load this skill
  before doing it alone. Also covers maintenance of the blueprint spec repo.
---

# astra-agent-constellation — Orchestrator operation manual + blueprint spec repo

## What this is

This skill serves two functions (same file, different triggers):

1. **Orchestrator operation manual** (core): the orchestrator's (Hermes)
   routing / invocation / acceptance behaviour in multi-agent constellation
   scenarios. Normative source = `~/Projects/astra/astra-agent-constellation/docs/`
   (01 topology, 02 sync layers, 03 tool gate, 04 harness discipline,
   05 observability, 06 twin-star pattern, 08 guardian runbook, 09 game day).
2. **Blueprint spec repo maintenance**: compliance rules when changing
   `docs/`, `templates/`, `scripts/` (language split, sanitisation gate,
   verification gate).

## When to load (triggers)

- The user's task involves a **multi-agent constellation scenario**: any of
  cross-machine work, health checks, version upgrades, service recovery, long
  coding tasks, build-fix loops, guardian / executor / tool gate / agent
  registry / task brief keywords.
- A decision is needed on "should I do this myself or delegate to an
  executor / route to the guardian" — consult the routing decision.
- Maintaining the blueprint spec repo itself (changing docs/templates/scripts).

## Orchestrator runtime behaviour (core function)

### 1. Routing decision (consult 01 §2.1 first, before acting)

When the user makes a request, the orchestrator **routes first, acts second**
— decide the invocation chain per the 01 §2.1 task-routing table:

| Task characteristics | Invocation chain |
|:--|:--|
| Ops work (service restart, status check, small config change) | Orchestrator executes directly |
| Single-file small change / docs edit / parallel sub-task | Orchestrator executes directly |
| Long coding task (multi-file, cross-module) | Orchestrator → executor (same/remote machine), task-brief contract |
| Cross-machine build-fix loop | Orchestrator → executor (build machine) |
| Health check / version upgrade / service recovery | Orchestrator → guardian (indirect via shared fact layer) |
| Result verification / change approval | Orchestrator acceptance (re-run commands + diff review), never delegated |

Discipline: short tasks MUST NOT be delegated to an executor; long tasks MUST
NOT be tackled solo; when in doubt and the user is present, direct execution
by the orchestrator takes priority.

### 2. Invoking the executor (OpenCode, via ACP)

- When splitting a task, generate a task brief (copy
  `templates/task-brief/task-brief.md.example` →
  `tasks/<ID>-<name>.md`): Metadata (agent-ref resolved via the registry) +
  Objective + Scope (including out-of-scope) + 5 Stopping Conditions +
  Acceptance Criteria (commands with expected results) + Hand-off + DoD.
- **Preferred: ACP dispatch (verified 2026-08-14)** — Hermes' native
  `copilot-acp` provider drives the executor over the Agent Client
  Protocol. Configure once per executor host (env vars, or
  `providers.copilot-acp` in config.yaml if the schema supports command/args):
  ```bash
  export HERMES_COPILOT_ACP_COMMAND="ssh"
  export HERMES_COPILOT_ACP_ARGS="-T -p 2222 <BUILD_HOST> opencode acp --cwd <WORKDIR> --pure"
  # then delegate with:
  #   hermes chat --provider copilot-acp --model copilot-acp -q "<brief>"
  # or via delegate_task with the provider configured on the agent.
  ```
  Full-chain verified end-to-end: Hermes → CopilotACPClient (native ACP
  client) → SSH stdio passthrough → remote `opencode acp` → reply. Task-brief
  content maps to ACP content blocks per blueprint 10 (Metadata → `_meta`,
  body → text blocks, AGENTS.md → resource_link, acceptance → per-command
  blocks). Client MUST consume the `session/update` notification stream —
  reply body arrives as `agent_message_chunk`, RESP is only the end marker.
- **dsh executor (DeepSeek Harness, verified 2026-08-14)** — same ACP dispatch,
  different server command:
  ```bash
  export HERMES_COPILOT_ACP_COMMAND="ssh"
  export HERMES_COPILOT_ACP_ARGS="-T -p 2222 <BUILD_HOST> \"cd ~/Projects/dsh && node --import tsx packages/examples/acp-demo/src/bin.ts --config executor/cordis.yml\""
  ```
  dsh replaces OpenCode for new deployments (sandbox write-wall has no
  headless ask-hang; 36-tool set incl. LSP/subagents/terminal; MCP tool naming
  `mcp__<server>__<tool>` matches Hermes). Deployment/config manual:
  `dsh-executor-deployment` skill. Both executors emit `session/update`
  chunks + committed RESP — the client-side handling is identical.
- **Fallback: `opencode run`** (pre-ACP, still works): same machine
  `opencode run "..." --continue --format json`; remote machine: ssh to the
  build host.
- Executor permission hard locks are configured in opencode.json (see the
  `opencode-executor-deployment` skill §4): `edit`/`todowrite` are `allow`
  (the executor's job IS writing code); `git push`/`git commit`/`sudo`/`rm -rf`
  are `deny` (git lifecycle belongs ENTIRELY to the orchestrator — commit/push/
  stage are the orchestrator's, never the executor's); `read_env` deny;
  `external_directory` ask. So: (a) the executor writes code & runs tests freely,
  (b) it CANNOT touch git history, (c) it cannot read fork-external configs/secrets.
- **Dispatch contract for a headless-capable run** — before sending an executor
  task, verify these are true:
  - any file the executor must read (task brief) is INSIDE its workdir — a brief
    stored in the constellation repo is unreachable (`external_directory: ask`
    auto-rejects headlessly). Copy it in as a git-ignored `.task-brief.md`.
  - **Prefer a git-ignored, local-tracking AGENTS.md beside the brief** over a
    long prompt (user guidance 2026-08-10: "配合 PLAN.md、AGENTS.md(仅本地追踪版)
    等工具帮助你，不一定全要靠 prompt"). OpenCode loads a project `AGENTS.md` as
    its instruction layer automatically, so it is the right home for durable
    executor discipline — tool set (simple: read/write/edit/glob/grep/todo/bash),
    command-shape rules (one simple command per step, no pipes/&&/redirects —
    pitfall #14), env setup, language-specific implementation pointers. Keep the
    dispatch prompt minimal ("read AGENTS.md + brief, execute"; "on a permission
    wall STOP and report the exact tool name"). Remember to add `AGENTS.md` to
    `.gitignore` so it never leaks into a commit.
  - git operations are entirely absent from the executor's brief (commit/push are
    hard-denied; the orchestrator does all of it).

### 3. Invoking the guardian (indirect — no live channel)

- The guardian is not a conversation partner (01 §3.3): it is triggered
  indirectly via the **shared fact layer** — health-check cron + registry
  state + status files.
- When the orchestrator needs guardian action: update the registry / status
  files and let the cron cycle pick it up; do not send direct messages.
- The guardian is **currently deferred (no carrier device)** — see PLAN.md.
  Its operations (update/recover/sync/report) are specified in 08
  guardian-runbook.md; activate when a device becomes available.

### 4. Tool gate

- Agents consume shared tool services only through the gate (03 §3.4);
  configuration carries only gate-key references.
- Registration contract: service/kind/endpoint/scopes/exposed/audit;
  register before exposing; `*` never granted to agents; changes land in git;
  no credentials embedded.
- Implementation pointer = astra-aigate (03 §3.4.1); gate audit log
  (operational facts) and session records (reasoning) are separate sinks,
  formats per 05 §5.1/§5.2.

### 5. Acceptance discipline (04 §2 MUST + 05 §3)

- After the executor returns: the orchestrator **re-runs every acceptance
  command** and diffs against the task-brief Scope — an executor's self-report
  of "passed" is never conclusive.
- Decision records accompany the report (05 §2); session JSONL is queryable
  and free of credentials.

### 6. Importing skills from outside (via AI Gate)

When a new skill must be introduced from outside the constellation, the
orchestrator imports it **through AI Gate's Skill Hub** — AI Gate is the
registry and provisioning source, the orchestrator is the installation
decision-maker. AI Gate never writes into any agent's skill directory
(03 §3.4.1): it only produces bytes; the consumer resolves and installs
them. **Verified end-to-end 2026-08-10** (godot-agentic served as the first
real import — no design fiction).

The orchestrator's own skill is held in the constellation blueprint repo;
skills for the executors are provisioned via this flow. A skill that is an
annex of a service / MCP MUST bring in that service / MCP for the target
agent(s) too.

Flow (steps 1–2 are source analysis, 3–5 are the actual install):

1. **Discover the source catalogue**: `GET /api/skills/sources` returns the
   registered sources (8 as of 2026-08-10: 5 gitea-private + 3
   github-public, incl. `godot-agentic-toolkits`). Per source,
   `GET /api/skills/sources/<id>/discover` returns every skill with
   `sourceUrl`, `commitSha`, `externalId`, `artifact`, `ref` — the analyse
   input before any install.
2. **Register the skill into AI Gate** (prerequisite so it appears in the
   consumable catalogue): `POST /api/skills/sources/<id>/install` with
   `{name, version, description, externalId}` → returns `{success, id}`.
   The orchestrator's own key has the required scope — no management token.
3. **List the consumable catalogue**: `GET /api/skills/artifacts` → the
   installed skills (id, name, version, sourceKind, sourceRef, externalId,
   artifact; `formats: ["agent-plugin", "tarball"]`).
4. **Fetch a skill as bytes**:
   `GET /api/skills/artifacts/<id>?format=agent-plugin` (or `tarball`) →
   agent-plugin is a text bundle (`---FILE plugin.json---` +
   `---FILE skills/<name>/SKILL.md---` sections). Verify
   `X-Artifact-Sha256` against the downloaded bytes before use.
5. **Analyse then install**: is the skill self-contained, or an annex of a
   service / MCP? Decide the target (orchestrator `~/.hermes/skills`, or an
   executor's `~/.config/opencode/skills/<name>/SKILL.md`) and normalise.
6. **Re-verify**: load the skill on the target (e.g. have the executor list
   its available skills), confirm references/scripts resolve.

## Blueprint spec repo maintenance (secondary function)

- **Language split**: `docs/` + README = Simplified Chinese (RFC 2119
  keywords stay in English); `templates/`, `scripts/`, AGENTS.md, commit
  messages = British English (-ise/-our/-re).
- **Sanitisation gate**: private copy (Gitea) holds real values; public copy
  (GitHub) MUST use placeholders (`<HOST-1>`/`<PORT-1>`) — zero real
  agent/machine names. Run `scripts/registry-check.py` before publishing.
- **git workflow**: feature → development → main via PRs; delivery shape =
  push development (Gitea first, GitHub second); feature branches are never
  the delivery; version tags are annotated.
- **Verification gate**: after touching `mkdocs.yml`/`DESIGN.md`/`tokens.css`/
  docs run `mkdocs build --strict`; `bash -n scripts/health-check.sh`;
  `python3 -m py_compile scripts/registry-check.py`. DESIGN.md ↔ mkdocs.yml ↔
  tokens.css must stay consistent (tokens.css = single source for
  colour/font/spacing).
- **ADR**: decisions live in `docs/references/` (one file per decision;
  append a new ADR rather than rewriting old decisions).

## Progress status (authoritative in PLAN.md)

- ✅ 0.1.0 released (private Gitea + signed v0.1.0 tag, rebuilt as 4
  contribution commits); official v1.0.0 awaits AIGate development completion
  + our own deployment verification.
- ✅ Checklist items ①–⑦ (registry schema / task brief / runbook / game day /
  gate contract / audit format / volume-2 English compliance).
- ✅ 01 §2.1 routing table, 03 §3.4.1 gate implementation pointer
  (2026-08-04).
- ⏸ **Guardian deferred**: no carrier device; activate when a device is
  available, in order "real registry → cron trigger chain → guardian skill →
  game-day variant A" (PLAN.md).

## Pitfalls

- `read_file` misdetects Chinese-dense documents as binary ("Binary file —
  cannot display") — use terminal `sed -n 'x,yp'` instead.
- **mkdocs Chinese heading anchors are unreliable**: Chinese-title slugs do
  not generate dependably — reference sections by plain-text citation (e.g.
  "03 §6, section on adding a tool service") rather than markdown anchor
  links to Chinese headings.
- **Explaining blueprint content requires background → problem → why → how
  (with analogies) — do not lead with structure tables.** "So what is X?" from
  the user = too-brief signal.
- **This skill does not auto-load** — triggering relies on the MEMORY.md hint
  plus this description matching user task keywords. If a task matches the
  triggers but the skill was not loaded, immediately `skill_view` to load it.
- External links from docs/ to the meta-repo (e.g. Reference Protocol →
  astra-aiagent-infra) are URL form — hash rewrites do not affect them, but
  broken paths must be fixed.
- **Executor permission model (verified 2026-08-10)**: the OpenCode executor
  runs headless (background, no interaction), so any `ask`-gated permission
  is auto-rejected. `read` is `allow` ONLY inside the executor's workdir;
  a path outside it hits `external_directory: ask` → auto-rejected. A task
  brief stored in the constellation repo (`~/Projects/astra/...`) is therefore
  NOT readable by the executor. Fix: copy the brief into the target repo
  (workdir) as a git-ignored file (e.g. `.task-brief.md`, append to
  `.gitignore`), point the executor at it, and clean it up after acceptance.
  Do NOT loosen opencode.json permissions for this — it is a global executor
  config change with broad blast radius.
- Dark-mode rendering: table headers/zebra/admonition colours derive from
  tokens.css variables — never hardcode component colours outside tokens.css.
- 06 §5 registry fields: use the reference protocol
  (`device-ref`/`tier-ref`/`chan-ref`/`agent-ref`/`doc-ref`,
  reference-not-copy), never free-text duplication.

## Related skills

- `work-principles` — orchestrator discipline mechanism (phase gates /
  HARNESS markers / stopping conditions). Complementary: discipline governs
  "how the orchestrator is constrained", this skill governs "how it works".
- `meta-repo-governance` (software-development) — astra-aiagent-infra
  meta-repo governance; a different repository from this blueprint, do not
  confuse.
- `open-source-publication` — publication / dual-copy sanitisation workflow;
  load when publishing.
- `astra-vcs-assist-git-dev` — feature→development→main branch discipline.
- `repo-language-convention` — basis of the reader-facing-Chinese /
  internal-British-English split.
- A2A inter-agent protocol — enable/configure/test ladder (L0 discovery →
  L1 self-loopback → L2 dual-instance peering), Hermes port allocation
  (9900/9901/9119/8642/8644/8645/9222), agent-card verification:
  `skill_view(name='astra-agent-constellation', file_path='references/a2a-interop.md')`.
  Decision record: `docs/references/0006-inter-agent-protocol-selection.md`.
