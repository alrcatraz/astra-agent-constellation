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

Private-only content that MUST stay off the public branch (`public`):
`agent-registry/` (real registry), `PLAN.md` (progression log), `tasks/`
(task-brief instances — carry real agent refs and machine names). The
`public` branch carries the sanitised tree; any sync from `main` MUST
exclude these paths.

`scripts/registry-check.py` enforces the placeholder rule on the agent
registry — run it before publishing.

## External interop (2026-08-16)

The constellation exposes an **external interop boundary** for
peer-to-peer collaboration with agents/agent groups outside the
organisation (recorded as an update to ADR 0006). Written content
about this boundary MUST stay at the level of the ADR — the generic
`{agent}.{public-domain}` sub-domain scheme, overlay multi-tier
fallback, and layered A2A + ANP auth — and MUST NOT name:

- the external entry node (jump host / front proxy) or its address;
- the specific public domain or its DNS record values;
- the internal overlay organisation (zone prefixes, machine network,
  member hostnames);
- the concrete external service ports.

Those values live only in the private copy and the per-machine instance
copy. Any doc, ADR or PLAN entry describing the boundary is written with
role names and placeholders. A doc that would need a real domain or
hostname to make sense is split: generic decision stays in the public
copy, deployment specifics go to the private copy.

## Releasing (dual-track) (2026-08-16)

This repository is released on **two independent tracks**. GitHub is NOT a
plain mirror of Gitea:

- **Private track** (Gitea): complete tree on the local `main` branch.
  Holds `PLAN.md`, `agent-registry/`, `tasks/` and real machine/host/port
  values.
- **Public track** (GitHub): sanitised subset on the local `public` branch.
  Excludes every file below that could leak private topology; real
  host/IP/domain/machine names MUST NOT appear anywhere.

Both tracks publish to the **remote `development` branch** of their
respective remote (Gitea and GitHub). The remote **`main`** branch IS a
publish target too — it is advanced by a **pull request** from each remote's
`development`, not by a direct push from here. (`development` is the
evolving workspace branch; `main` is the remote's stable/merged head for
that track.)

### Release procedure (end-to-end)

1. **Develop on `development`**: feature work lands on `development` (or a
   feature branch merged into it). Commit with `git commit -S`. The release
   version is `+1` of the latest tag (`git tag -l | sort -V`) and is
   recorded in `PLAN.md` line 4 before pushing.
2. **Merge into local `main`** (private track): `git checkout main &&
   git merge development --no-ff`. Local `main` is now the complete private
   tree for this release.
3. **Publish private track**: `git -c http.version=HTTP/1.1 push gitea
   main:development`. (Gitea presents a self-signed cert; without `-c
   http.version=HTTP/1.1` you hit TLS `error:0A000126`.)
3b. **Advance Gitea `main` by PR** (not direct push): open a pull request
   `development` → `main` on Gitea and merge it. Gitea CLI/API or the web
   UI both work; the merge must land as a merge commit on `main`.
4. **Build the public branch from local `main`** (do NOT `git merge main`
   into `public` — that drags private files back in). Reconcile `public` to
   the sanitised target:
   ```
   git checkout main
   git checkout -B public             # re-point public at main's tree
   git rm --cached PLAN.md            # progression log, private-only
   git rm --cached agent-registry/registry.yaml   # real registry
   git rm --cached -r tasks           # task-brief instances, real refs
   # Files kept OUT of public entirely (leak topology / real hosts):
   #   docs/10-acp-mapping.md          (real test hosts)
   #   docs/references/0006-...inter-agent-protocol-selection.md
   #   skills/.../references/a2a-interop.md  (real port plan)
   #   templates/cordis-executor.yml.example
   # Public-safe additions to KEEP (written sanitised):
   #   docs/12-external-interop.md, templates/external-interop/*
   # Scan the staged tree for real host/IP/domain/machine-name hits
   # (incl. any machine abbreviation such as HC01) before committing.
   git commit -S -m "... (sanitised)"
   ```
   The `(sanitised)` marker in the commit message identifies public-track
   commits whose content was scrubbed — preserve it when amending.
4b. **Public reconcile trap (2026-08-18, v0.2.7)**: if the GitHub
   `development` branch has diverged from the freshly-rebuilt `public`
   (e.g. older public commits were already merged into GitHub `main`), a PR
   `development → main` will refuse to merge (non-fast-forward) and a naive
   `git merge github/main` back into `public` silently **re-imports the leak
   set** (`docs/10-acp-mapping.md`, `skills/.../references/a2a-interop.md`,
   `templates/cordis-executor.yml.example`,
   `docs/references/0006-...inter-agent-protocol-selection.md`). This
   happened once already. Correct reconcile when histories have forked —
   push the sanitised tree onto GitHub `main`'s history, resolving content
   to the NEW public side:
   ```
   # (1) user-ok'd force: bring GitHub development to the new sanitised tree
   git push --force-with-lease github public:development
   # (2) rebase-style reconcile so the PR can merge; -X ours = new/scrubbed wins
   git checkout public
   git merge github/main -X ours -m "chore: reconcile github main history (new wins) (sanitised)"
   # (3) re-delete any leak file the merge resurrected; re-verify the WHOLE tree
   git rm --cached docs/10-acp-mapping.md ...          # whatever reappeared
   git grep -nE "HC01|SUSETLearn00|homecentre|\.nb\.internal|10\.20\.|10\.30\." -- # must be empty
   git commit -S -m "chore: purge leak re-import (sanitised)"
   git push github public:development                    # now fast-forward
   ```
   A file present on GitHub is NOT a license to keep it there — treat
   "public has it" as a bug to purge, not a signal to preserve. Force-pushes
   on GitHub require explicit user approval (see Rules).
5. **Publish public track**: `git push github public:development`.
5b. **Advance GitHub `main` by PR**: open a pull request
   `development` → `main` on GitHub and merge it (`gh pr create` +
   `gh pr merge` work). The GitHub `main` then reflects the sanitised
   public track's stable head.
6. **Tag both tracks**: annotated, GPG-signed `git tag -s vX.Y.Z` on local
   `main` and on `public`. Push the tag to both remotes.
7. **GitHub release**: `gh release create v0.2.3 --title "v0.2.3"` — **the
   release title is ONLY the version string**, nothing else (no description,
   no changelog, no prefix). A bare tag name as the whole title. (This is a
   documented recurring mistake in another project — do not repeat it.)

### Rules

- Local `main` is the complete-tree parent; local `public` is its sanitised
  subset. A file must never appear on GitHub that is missing from Gitea, but
  the reverse (Gitea-only files) is normal.
- `development` is the deliverable branch name published to both remotes
  (`main:development`, `public:development`), never a feature branch.
- Private-only content — `PLAN.md`, `agent-registry/registry.yaml`,
  `tasks/` — MUST be removed from any tree pushed to GitHub.
- Reconcile `public` by deletion/trimming from `main`; never `git merge`
  straight into `public` (that re-imports the private files).

## ACP transport note (2026-08-14, updated 2026-08-15)

The orchestrator→executor dispatch seam uses ACP. **Hermes' native
`copilot-acp` provider is the ACP client** — configure
`HERMES_COPILOT_ACP_COMMAND`/`HERMES_COPILOT_ACP_ARGS` to point at the
executor. **dsh (DeepSeek Harness) is the recommended production executor since
2026-08-15** (OpenCode remains available as legacy):

```bash
# ~/.hermes/.env — orchestrator side holds ONLY the launch command, no key
HERMES_COPILOT_ACP_COMMAND="bash"
HERMES_COPILOT_ACP_ARGS="-c 'cd ~/Projects/dsh && node --import tsx packages/examples/acp-demo/src/bin.ts --config executor/cordis.yml'"
```

- Local (HC01): command above. Remote (SUSETLearn00): same via
  `ssh -T -p <port> <build-host> "<command>"`.
- **Executor key**: each machine's `AIGATE_EXECUTOR_KEY` lives ONLY in
  that host's `~/Projects/dsh/.env` (gitignored; dsh `loadEnv()` reads it
  at boot). Never in the tar deploy, never in the repo, never in Hermes'
  own env — the orchestrator must not hold the executor identity.
  `cordis.yml` references the env var name (`apiKeyEnv: AIGATE_EXECUTOR_KEY`),
  so the same config file works on every host.
- dsh sandbox (workspace-write) has no headless ask-hang; verified local
  (HC01) and remote (SUSETLearn00). Deployment manual:
  `dsh-executor-deployment` skill.
- **Legacy**: OpenCode remains supported as a fallback (same env-var
  mechanism, `opencode acp --cwd <workdir>`). When OpenCode adds official
  ACP Web Transport support, switch the remote transport to the official
  standard — the provider runtime accepts any command, so this is a
  drop-in config change.

## Code hygiene

- No placeholder comments for deleted content ("XXX removed" style).
- Comments explain WHY, never WHAT changed.
- No orphan TODO markers.
