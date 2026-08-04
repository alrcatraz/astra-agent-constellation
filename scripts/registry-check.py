#!/usr/bin/env python3
"""registry-check.py — validate the agent registry against the schema.

Checks that every agent entry carries the mandatory fields (name, role,
host, version), that roles are drawn from the known set, and that no real
hostnames leaked into a public copy (sanitisation gate).

Reference semantics (ADR 0001 / 06 §5): the registry references facts that
belong to other layers instead of duplicating them. Reference fields carry
either a placeholder (<HOST-N>, <CHAN-N>) in public copies or an agent name
(owner) that MUST resolve to another entry in the same registry.

Exit 0 = valid; exit 1 = invalid. Written in British English.
"""

import sys
import re

import yaml

REQUIRED_FIELDS = ("name", "role", "host", "version")
KNOWN_ROLES = ("orchestrator", "executor", "guardian")
PLACEHOLDER_RE = re.compile(r"^<[A-Z0-9-]+>$")
# Optional reference fields: (field, must-be-placeholder-in-public)
REF_FIELDS = (
    ("channel", True),   # chan-ref -> <CHAN-N> in public copy
    ("model", False),    # tier-ref -> tier name (standard/light)
    ("deploy_def", False),  # doc-ref -> path into the docs
)
OWNER_FIELD = "owner"    # agent-ref -> must resolve to a name in this registry


def main(path: str, private: bool = False) -> int:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    errors = []
    agents = data.get("agents", [])
    if not agents:
        print("INFO: no agents registered")
        return 0

    names = {a.get("name") for a in agents if a.get("name")}

    for i, agent in enumerate(agents):
        for field in REQUIRED_FIELDS:
            if field not in agent:
                errors.append(f"agent[{i}] missing required field: {field}")
        role = agent.get("role")
        if role not in KNOWN_ROLES:
            errors.append(f"agent[{i}] unknown role: {role!r} (expected one of {KNOWN_ROLES})")
        host = agent.get("host", "")
        # Sanitisation gate: public copies MUST use <PLACEHOLDER> hosts.
        # Private copies (--private) hold real hostnames and skip this gate.
        if not private and not PLACEHOLDER_RE.match(host):
            errors.append(f"agent[{i}] host {host!r} is not a sanitised placeholder "
                          "(public copy must use <HOST-N>; run with --private for a "
                          "private copy)")

        # Reference fields: validate format when present.
        for field, must_placeholder in REF_FIELDS:
            if field not in agent:
                continue
            value = agent[field]
            if not private and must_placeholder and not PLACEHOLDER_RE.match(str(value)):
                errors.append(f"agent[{i}] {field} {value!r} must be a sanitised "
                              f"placeholder in the public copy (e.g. <CHAN-N>)")

        # owner (agent-ref): MUST resolve to another entry in this registry.
        owner = agent.get(OWNER_FIELD)
        if owner is not None:
            if owner not in names:
                errors.append(f"agent[{i}] owner {owner!r} does not resolve to "
                              "any agent in this registry")
            elif owner == agent.get("name"):
                errors.append(f"agent[{i}] owner must not be the agent itself")

    if errors:
        print("INVALID:")
        for err in errors:
            print(f"  - {err}")
        return 1

    mode = "private copy (sanitisation gate skipped)" if private else "public copy"
    print(f"VALID: all agents pass the registry schema ({mode})")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    private = "--private" in args
    args = [a for a in args if a != "--private"]
    if len(args) != 1:
        print(f"usage: {sys.argv[0]} [--private] <registry.yaml>")
        sys.exit(2)
    sys.exit(main(args[0], private=private))
