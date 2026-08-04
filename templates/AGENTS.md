# AGENTS.md — Project Rules Template

> Copy to `<project-root>/AGENTS.md` and adapt. All agents operating this
> repository MUST read this file before making changes.
>
> Written in British English. Normative keywords per RFC 2119 (MUST/SHOULD/MAY).

## Project

- One-line description of the project and its purpose.

## Build & Verification

- **Build host**: `<BUILD_HOST>` — compilation MUST run there, never on the
  dev machine (example: Next.js builds).
- **Verification**: `<CI-equivalent command>` — e.g. `npx tsc -p
  tsconfig.typecheck-core.json`. This command MUST exit 0 with no new errors
  before any change is considered complete.
- **Runtime**: `podman run ...` (rootless) — see `README.md` for exact flags.

## Code Hygiene (MUST)

- Deleted code leaves NO placeholder comment (no "XXX removed" markers).
  Git history is the record of deletion.
- Comments explain WHY, never WHAT was changed or deleted.
- No orphan TODO markers without an owner and a reason.
- Brand names, ports and hostnames MUST reference constants
  (`APP_CONFIG.name` etc.), never hard-coded literals.
- UI strings use British English (-ise/-our/-re); file names stay as-is
  (e.g. `en.json`).

## Git Workflow

- Feature branch → `development` → `main` via PR.
- Deliverables: push `development` (dual remote). Never push a feature branch
  as the deliverable.
- Versioning: official `Z` / personal `Z+alrcatraz.Y` / local
  `Z+alrcatraz.Y.<variant>.Z`.

## Language

- This repository's docs (docs/, README) are written in Simplified Chinese
  for the primary audience.
- Templates, scripts, internal skills and code comments use British English.

## Dependencies

| Repository | Resource | Required | Purpose |
|:-----------|:---------|:---------|:--------|
| _(list sibling repos)_ | _(file or concept)_ | yes/no | _(why)_ |

If no external dependencies: "This project has no external dependencies."
