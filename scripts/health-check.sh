#!/usr/bin/env bash
# health-check.sh — agent health check for the constellation.
#
# Reads the agent registry (agent-registry/registry.yaml) and probes
# each agent's health_check entry. Exit 0 = all healthy; exit 1 = at least
# one unhealthy. Intended for use by the Guardian.
#
# Check types:
#   port     — TCP connect to <host>:<port>
#   command  — run a command WHERE THE SCRIPT RUNS (use ssh type to probe
#              an agent on another machine; the registry host field does not
#              relocate a command probe)
#   ssh      — BatchMode SSH "true" against the agent host
#   none     — no check declared; not counted as a failure
#
# Not-deployed agents are SKIPPED, never failed: an agent whose host is
# `unassigned` or whose version is `uninstalled` is deferred by design
# (e.g. guardian without a carrier device — PLAN.md), so its placeholder
# probe must not turn every run red. Sanitised placeholders in the public
# copy are skipped for the same reason.
#
# Written in British English. RFC 2119 keywords per the blueprint.

set -euo pipefail

REGISTRY="${1:-agent-registry/registry.yaml}"

if [[ ! -f "$REGISTRY" ]]; then
  echo "ERROR: registry not found at $REGISTRY (copy from registry.yaml.example)"
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required"
  exit 2
fi

# Parse the registry and probe each agent. Delegating to python keeps the
# YAML parsing robust; bash only orchestrates.
python3 - "$REGISTRY" <<'PYEOF'
import socket
import subprocess
import sys

import yaml

CONNECT_TIMEOUT = 5      # seconds per TCP/SSH probe
COMMAND_TIMEOUT = 30     # seconds per command probe (versions can be slow)

# Deferred-by-design markers: these agents are registered but not deployed
# (PLAN.md). A placeholder probe on them is meaningless, not a failure.
NOT_DEPLOYED_HOSTS = {"", "unassigned"}
NOT_DEPLOYED_VERSIONS = {"", "uninstalled", "unassigned"}


def _probe_port(host: str, port: int) -> bool:
    """TCP connect probe — True only if the port accepts a connection."""
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT):
            return True
    except (OSError, ValueError):
        return False


def _run_check(cmd) -> bool:
    """Run a probe command — True only on exit 0; probe errors count as down."""
    try:
        proc = subprocess.run(
            cmd,
            timeout=COMMAND_TIMEOUT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _is_placeholder(value: str) -> bool:
    """Sanitised public copy still carries <PLACEHOLDER> values."""
    return "<" in value and ">" in value


with open(sys.argv[1], encoding="utf-8") as fh:
    data = yaml.safe_load(fh)

agents = data.get("agents", [])
if not agents:
    print("INFO: no agents registered — nothing to check")
    sys.exit(0)

unhealthy = []
for agent in agents:
    name = agent.get("name", "<unnamed>")
    host = str(agent.get("host", "") or "")
    version = str(agent.get("version", "") or "")
    check = agent.get("health_check") or {}
    ctype = str(check.get("type", "none") or "none")
    target = str(check.get("target", "") or "")

    # Deferred by design — skip, never fail (see header).
    if host.strip().lower() in NOT_DEPLOYED_HOSTS or \
       version.strip().lower() in NOT_DEPLOYED_VERSIONS:
        print(f"SKIP {name:20} ({ctype}) not deployed — host={host or '-'}, "
              f"version={version or '-'}")
        continue
    if _is_placeholder(target) or _is_placeholder(host):
        print(f"SKIP {name:20} ({ctype}) sanitised placeholder in public copy")
        continue

    if ctype == "port":
        host_part, _, port_part = target.rpartition(":")
        ok = _probe_port(host_part, int(port_part))
    elif ctype == "command":
        ok = _run_check(["bash", "-c", target])
    elif ctype == "ssh":
        ok = _run_check(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                         target, "true"])
    else:
        ok = True  # no check declared — not counted as failure

    status = "OK" if ok else "FAIL"
    print(f"{status:4} {name:20} ({ctype}) {target}")
    if not ok:
        unhealthy.append(name)

if unhealthy:
    print(f"ERROR: unhealthy agents: {', '.join(unhealthy)}")
    sys.exit(1)
print("ALL HEALTHY")
PYEOF
