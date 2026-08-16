"""Dispatch an external task to the local Hermes agent.

Bridges an external-facing endpoint (external A2A / ANP) to this machine's own
Hermes agent in a single local hop: the task text, annotated with the
authenticated *external caller identity*, is handed to ``hermes -z`` (the
official scripted one-shot entry point), and the agent's final reply is
returned to the caller. There is no network relay and no cross-port proxy —
the local Hermes executable is the sole execution engine.

This file is deliberately free of any machine-specific value: everything is
injected via environment variables so the same template installs unchanged on
any member instance.

Environment variables (all optional):

    HERMES_DISPATCH_BIN      Path to the Hermes executable (default "hermes").
    HERMES_DISPATCH_PROFILE  Hermes profile name, e.g. "home" (default: none).
    HERMES_DISPATCH_WORKDIR  Working directory for the one-shot run.
    DISPATCH_IDENTITY_LABEL  Noun for the caller identity in the prompt, e.g.
                             "external caller DID" or "external A2A peer".

The caller identity is injected as an explicit context line so the local agent
can distinguish external callers (per-peer authorisation / audit), which is
what makes the DID / sender identity from the external auth layer actually
reach the agent instead of being discarded at the boundary.
"""
import os
import subprocess

HERMES_BIN = os.environ.get("HERMES_DISPATCH_BIN", "hermes")
HERMES_PROFILE = os.environ.get("HERMES_DISPATCH_PROFILE", "")
HERMES_WORKDIR = os.environ.get("HERMES_DISPATCH_WORKDIR", "")
IDENTITY_LABEL = os.environ.get("DISPATCH_IDENTITY_LABEL", "external caller")


def _profile_args() -> list[str]:
    if HERMES_PROFILE:
        return ["--profile", HERMES_PROFILE]
    return []


def _prompt(task: str, identity: str | None) -> str:
    """Build the one-shot prompt: identity context line + the task itself."""
    prelude = "\n".join(
        (
            "You are handling a task delivered through this machine's external"
            f" interop boundary. The authenticated {IDENTITY_LABEL} is:"
            f" {identity or 'anonymous'}"
            "Complete the requested task and reply with your final answer only."
        )
    )
    return f"{prelude}\n\n[task]\n{task}"


def run_hermes_oneshot(
    task: str,
    identity: str | None = None,
    timeout: int = 300,
) -> str:
    """Execute ``task`` on the local Hermes agent as a one-shot and return its
    final reply. Raises DispatchError on a non-zero exit or timeout.
    """
    cmd = [HERMES_BIN, *_profile_args(), "-z", _prompt(task, identity)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=HERMES_WORKDIR or None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise DispatchError(f"hermes one-shot timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise DispatchError(f"hermes executable not found: {HERMES_BIN!r}") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        raise DispatchError(
            f"hermes one-shot exited {proc.returncode}: {detail}"
        )
    return (proc.stdout or "").strip()


def dispatch_ok(identity: str | None = None) -> str:
    """Lightweight self-check (used to verify the dispatch bridge is wired)."""
    return run_hermes_oneshot(
        "Reply with exactly: dispatch-ok",
        identity=identity,
        timeout=60,
    )


class DispatchError(Exception):
    """Raised when the local Hermes dispatch fails to produce a result."""
