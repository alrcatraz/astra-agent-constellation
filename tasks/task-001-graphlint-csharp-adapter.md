# Task Brief — Add C# language support to graphlint

> Copy of `templates/task-brief/task-brief.md.example`, adapted for this task.
> Contract between the orchestrator (Hermes) and the executor (OpenCode on
> HomeCentre01 / HC01) for ONE task. British English. Normative keywords per
> RFC 2119 (MUST/SHOULD/MAY).
>
> Validation-first (05 §3): the acceptance criteria are written BEFORE the
> work starts, as exact commands with expected results. The executor's
> self-reported "it passes" is NEVER the conclusion — the orchestrator
> re-runs every command below.
>
> Stop-and-report (04 §2): when a chosen technical route fails, the executor
> STOPS and reports back — it never silently switches to an alternative
> route and keeps going.

## Metadata

| Field | Value |
|:--|:--|
| Task ID | `task-001` |
| Brief version | `1.0` |
| Orchestrator | `<agent-ref: hermes-orchestrator-hc01>` |
| Executor | `<agent-ref: opencode-executor-hc01>` |
| Target repo | `graphlint-fork` (local path `~/Projects/graphlint-fork`) |
| Branch | `feat/csharp-language-support` (already checked out by orchestrator) |
| Date issued | `2026-08-10` |
| Date due | `2026-08-11` |

## 1. Objective

Add a first-class C# language backend to graphlint so it can detect dead
code, unused imports and circular references in C# (`.cs`) projects, exactly
as it already does for Python and Rust. The implementation is an incremental
addition: it MUST follow the existing `LanguageAdapter` + `LanguageRegistry`
architecture and mirror the Rust backend's tree-sitter pattern, so that C#
files are discovered, parsed and routed through the same graph-builder
pipeline with no changes to the core graph logic.

The orchestrator has ALREADY verified end-to-end (via an isolated venv smoke
test) that `tree-sitter==0.26.0` + `tree-sitter-rust==0.24.2` +
`tree-sitter-c-sharp==0.23.5` all import together without conflict, and that
C# syntax parses to a `compilation_unit` tree. C# grammar is MIT-licensed.

## 2. Scope

- **In scope** (files the executor MAY touch):
  - `graphlint/analyzer/language/csharp/` — NEW directory:
    `__init__.py`, `parser.py`, `visitor.py`, `entry.py`, `imports.py`,
    `constants.py` (mirror the `rust/` backend structure).
  - `graphlint/analyzer/language/__init__.py` — export `CsharpAdapter`
    (plus `LanguageAdapter`/`LanguageRegistry` re-exports already present).
  - `graphlint/api.py` — add `_try_register_csharp(registry)` and call it from
    `_build_registry()` (mirror exactly how `_try_register_rust` works).
  - `pyproject.toml` — add a `csharp` optional-dependencies extra:
    `tree-sitter>=0.22,<0.27` + `tree-sitter-c-sharp>=0.23,<0.24`.
    MUST list BOTH, because `tree-sitter-c-sharp` does NOT pull the core
    `tree-sitter` package by default (its `core` extra is off by default).
  - `tests/unit/test_csharp_*.py` — NEW unit tests for the C# backend.
  - `tests/integration/fixtures/csharp-sample/` — NEW small C# sample project
    (Program + one or two unused classes) used by an integration test.
  - `tests/integration/test_csharp_dead_code.py` — NEW integration test.
  - `README.md`, `CHANGELOG.md`, `graphlint/analyzer/language/README*` (if any)
    — document C# support.
- **Out of scope** (executor MUST NOT touch):
  - Core graph-builder pipeline (`graphlint/analyzer/graph.py`,
    `_graph_algo.py`, `warnings.py`, `storage/`, `incremental/`, `query/`,
    `config/`, `i18n/`, `cli.py`). The C# backend MUST plug into the existing
    pipeline untouched.
  - The Python backend (`python/`) and Rust backend (`rust/`) — do NOT
    refactor them. Copy the Rust pattern, do not modify it.
  - Versioning/git-history changes, and any push to remote — the
    orchestrator handles commit + push after acceptance.
  - Porting C# support upstream to `AngelosZou/graphlint` — out of scope by
    decision.
  - `--public-as-entry`, test-framework entry detection, and library-mode
    analysis — deferred to a later task (see §4 note).
- The orchestrator's git diff review (5.3) is judged against this scope.

## 3. Stopping Conditions (MUST)

The executor is headless — the orchestrator is not watching. STOP and report
back in these situations. The report goes to the orchestrator and includes:
where it is stuck, what was tried, the failure evidence, and the suggested
way forward.

- **MUST**: when the chosen technical route fails (missing API, dependency
  conflict, design assumption falsified), STOP and report — do NOT silently
  switch to an alternative route and keep going. Route changes are the
  orchestrator's call.
- **MUST**: when an acceptance command fails, STOP and report with the raw
  output and a first-pass root-cause analysis — do NOT modify the command or
  the expected result to manufacture a pass.
- **MUST**: when an out-of-scope need surfaces (bug, side effect,
  pre-existing debt), record it in the report and STOP — do NOT expand the
  change beyond the scope declaration.
- **MUST**: when required information, permission or resource is missing,
  STOP and ask the orchestrator — do NOT fill the gap by guessing.
- **SHOULD**: when the task will clearly overshoot its time/effort budget,
  report progress and the revised estimate before continuing.

### Known technical risks (orchestrator pre-verified, FYI — do not re-litigate)

- `tree-sitter-c-sharp` default install does NOT include core `tree-sitter`.
  The `csharp` extra MUST declare both packages.
- The grammar is the official `tree-sitter/tree-sitter-c-sharp` (C# 1–13.0).
  Top-level statements and `using` directives ARE part of the `compilation_unit`.
- Node type names used by the visitor: `class_declaration`,
  `method_declaration`, `property_declaration`, `interface_declaration`,
  `enum_declaration`, `struct_declaration`, `record_declaration`,
  `local_function_statement`, `using_directive`, `namespace_declaration`,
  `field_declaration`, `variable_declaration`. Confirm each against the live
  parse tree with a quick tree-walk before hard-coding.

## 4. Acceptance Criteria (MUST)

Each criterion is an exact command and its expected result. The executor
runs these during work; the orchestrator re-runs them after hand-off.

Setup (once, inside the fork): `python -m venv env && source env/bin/activate
&& pip install -e ".[dev,csharp]"`.

| # | Command | Expected result |
|:--|:--|:--|
| 1 | `cd ~/Projects/graphlint-fork && source env/bin/activate && python3 -m py_compile graphlint/analyzer/language/csharp/*.py graphlint/api.py` | exit 0, no output (all files compile). |
| 2 | `cd ~/Projects/graphlint-fork && source env/bin/activate && python3 -c "from graphlint.analyzer.language.csharp import CsharpAdapter; print(CsharpAdapter.language_name, sorted(CsharpAdapter.file_extensions))"` | prints `csharp ['.cs']`. |
| 3 | `cd ~/Projects/graphlint-fork && source env/bin/activate && python3 -c "from graphlint.analyzer import ..."` — invoke `_build_registry()` and assert `.cs` resolves to the C# adapter: `from graphlint.api import _build_registry; r=_build_registry(); a=r.adapter_for_file('x.cs'); print(a.language_name)` | prints `csharp` (registry routes `.cs`). |
| 4 | `cd ~/Projects/graphlint-fork && source env/bin/activate && pytest tests/unit/test_csharp*.py -v` | all new C# unit tests pass (0 failures). |
| 5 | `cd ~/Projects/graphlint-fork && source env/bin/activate && pytest tests/integration/test_csharp_dead_code.py -v` | integration passes: dead + unused classes in the fixture detected; live entry-reachable code not reported. |
| 6 | `cd ~/Projects/graphlint-fork && source env/bin/activate && ruff check graphlint/analyzer/language/csharp/` | no ruff violations in the new backend. |
| 7 | `cd ~/Projects/graphlint-fork && source env/bin/activate && pytest -q` (full suite) | existing Python+Rust tests still pass (no regression). |

- **MUST**: every acceptance criterion carries a verification command above.
- **MUST**: expected results are objective (exit codes, counts, output
  strings), not subjective.
- **MUST**: the C# unit/integration tests SHOW the dead-code detection working
  on a minimal program (a `Program.cs` with a `static void Main` or
  Top-Level Statements, plus at least one unreferenced class/method that MUST
  be flagged as `dead_code`).
- **Note (deferred by decision)**: entry-point detection for this task is the
  MINIMAL set — `static void Main` / `static int Main` / `static Task Main`
  and C# 9+ Top-Level Statements. xUnit/NUnit/MSTest test methods and
  `--public-as-entry` library mode are explicitly OUT of scope for this task;
  do not implement them.

## 5. Hand-off Protocol

### 5.1 Deliverables

- Working tree on branch `feat/csharp-language-support` in
  `~/Projects/graphlint-fork` containing: the new `csharp/` backend module
  (in scope files), the `pyproject.toml` extra, the `api.py` registration,
  unit + integration tests, and doc updates.
- The exact `git diff --stat` summary of the change (reported, NOT committed —
  the orchestrator commits after acceptance).
- The decision record (5.2) accompanies the deliverables, never replaces
  the diff.

### 5.2 Decision record (MUST)

The executor appends a decision record to the task report: what changed, why,
which alternatives were considered, and why they were rejected. The
orchestrator reviews it for consistency with this brief's scope. Any
stopping-condition event (section 3) and its resolution MUST also be recorded
here.

### 5.3 Orchestrator verification (MUST)

1. Re-run every command in section 4 — the executor's self-report is
   informational only.
2. `git diff` review against the scope declaration in section 2 (ensure no
   core-graph / python-backend / rust-backend changes leaked in).
3. Session record (JSONL) kept in the project directory, retrievable on
   demand (05 §5). MUST NOT contain credential values.

## 6. Definition of Done

The task is complete ONLY when ALL of the following hold:

- [ ] All acceptance criteria in section 4 pass under the orchestrator's
      re-run, not just the executor's run.
- [ ] `git diff` matches the declared scope; nothing out-of-scope changed
      (core graph, Python/Rust backends untouched).
- [ ] C# dead-code detection demonstrably works on the minimal fixture
      (Main / Top-Level reachability).
- [ ] Decision record delivered and consistent with the brief; all
      stopping-condition events documented with their resolutions.
- [ ] No placeholder comments ("XXX removed"), no orphan TODOs, comments
      explain WHY.
- [ ] Orchestrator installs the change back into the local graphlint tool and
      confirms C# queries work on this machine post-acceptance.
