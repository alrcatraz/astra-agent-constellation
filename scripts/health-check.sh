#!/usr/bin/env bash
# health-check.sh — agent health check for the constellation.
#
# Reads the agent registry (agent-registry/registry.yaml.example) and probes
# each agent's health_check entry. Exit 0 = all healthy; exit 1 = at least
# one unhealthy. Intended for use by the Guardian.
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
import sys
import subprocess
import yaml

with open(sys.argv[1], encoding="utf-8") as fh:
    data = yaml.safe_load(fh)

agents = data.get("agents", [])
if not agents:
    print("INFO: no agents registered — nothing to check")
    sys.exit(0)

unhealthy = []
for agent in agents:
    name = agent.get("name", "<unnamed>")
    check = agent.get("health_check", {})
    ctype = check.get("type", "none")
    target = check.get("target", "")

    if ctype == "port":
        host, port = target.rsplit(":", 1)
        ok = _probe_port(host, int(port))
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
