# AGENTS.md — Instructions for agents operating this repository

> This file is the L1 project-rules layer of the constellation blueprint
> (see docs/02-sync-layers.md). Any agent touching this repository MUST
> read this file first and MUST follow the normative statements below.
>
> Written in British English. Normative keywords per RFC 2119.

## Repository nature

This repository is a **specification** (architecture blueprint), not a
software product. Changes to `docs/` alter published normative content and
MUST be deliberate:

- Normative text uses RFC 2119 keywords (MUST/SHOULD/MAY) consistently.
- Architectural decisions are recorded as ADRs in `docs/references/`
  (one file per decision, status + date + rationale). **Do not silently
  rewrite a decision in the body text — append a new ADR instead.**

## Language policy (MUST)

- **Simplified Chinese**: everything addressed to readers — `docs/` body
  text, `README.md`, MkDocs navigation. RFC 2119 keywords stay in English
  (MUST/SHOULD/MAY) inside Chinese prose.
- **British English**: everything internal — `templates/`, `scripts/`,
  `AGENTS.md`, code comments, skill files, commit messages, PR text.
- Spelling is British throughout (-ise/-our/-re, e.g. "orchestrator",
  "standardise", "colour").

## Build & verification

- Documentation site: `mkdocs build` (Material theme). Verify with
  `mkdocs build --strict` after any change to `mkdocs.yml`, `DESIGN.md`,
  `docs/stylesheets/tokens.css` or `docs/` content.
- Scripts: `bash -n scripts/health-check.sh` and
  `python3 -m py_compile scripts/registry-check.py` MUST pass.
- DESIGN.md MUST stay consistent with `mkdocs.yml` and
  `docs/stylesheets/tokens.css` (tokens are the single source of colour,
  typography and spacing — never hard-code values elsewhere).

## Git workflow

- Feature branch → `development` → `main` via PR.
- Deliverable form: push `development` (dual remote: Gitea private first,
  GitHub public). Never push a feature branch as the deliverable.
- Commits: one logical change per commit; no force-push without explicit
  approval; version tags are annotated.

## Sanitisation (MUST)

Two copies of this repository exist:

- **Private copy** (Gitea) — holds real values: agent names (e.g. the
  orchestrator and guardian instances), hostnames, ports, internal URLs.
- **Public copy** (GitHub) — MUST be sanitised: real agent names, machine
  names and their abbreviations MUST NOT appear. Use role names
  (orchestrator / executor / guardian) and placeholders (`<HOST-1>`,
  `<PORT-1>`) instead.

Publishing to GitHub without sanitisation is a release-blocking violation.

`scripts/registry-check.py` enforces the placeholder rule on the agent
registry — run it before publishing.

## Code hygiene

- No placeholder comments for deleted content ("XXX removed" style).
- Comments explain WHY, never WHAT changed.
- No orphan TODO markers.
