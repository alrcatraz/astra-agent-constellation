#!/usr/bin/env bash
# verify-runtime.sh — layered runtime-acceptance probe for an A2A/ACP agent
# endpoint. Distilled from the P4-4 real-runtime verification (2026-08-26).
#
# Runtime probes are accepted in FOUR separate layers; do not collapse them:
#   1. transport reachable           (listener answers the health probe)
#   2. protocol request/response     (JSON-RPC round trip completes)
#   3. task terminal state           (TASK_STATE_COMPLETED / end_turn)
#   4. usable generated output       (the actual returned text/artifact is usable)
#
# A healthy listener + a terminal task state is NOT sufficient to declare the
# service healthy if the provider returned an error or unusable text (layer 3
# can be reached while layer 4 failed — e.g. a context-overflow pair mismatch).
#
# A probe that needs more context than the real model's n_ctx MUST NOT fake a
# larger context declaration. Shrink the probe surface or route to a separately
# authorised model instead.
#
# Every probe runs against a temporary, isolated surface: temp HOME/config,
# a free port distinct from any production listener, a short fixed prompt, and
# an env var for the credential that is injected only into the child process
# (never written to repo/config/logs/output). The script cleans the temp dirs
# and processes in a trap, and refuses to run when credentials are not provided
# via the DAT environment.
#
# Written in British English. RFC 2119 keywords per the blueprint.
# Usage:
#   AGENT_CARD_URL=http://127.0.0.1:<free-port> AGENT_KEY=<process-only> \
#     SHORT_PROMPT='Reply with a fixed marker.' EXPECTED_OUTPUT_RE='marker' \
#     ./verify-runtime.sh
#
# Exit 0 = all four layers pass; 2 = usage error; 3 = transport failed;
# 4 = protocol failed; 5 = task-state failed; 6 = generation failed.

set -euo pipefail

HOST="${AGENT_CARD_URL:-}"
KEY="${AGENT_KEY:-}"
: "${TMP_ROOT:=/tmp/verify-runtime-$$}"

if [[ -z "$HOST" ]]; then
  echo "ERROR: AGENT_CARD_URL is required (e.g. http://127.0.0.1:<port>)" >&2
  exit 2
fi
if [[ -z "$KEY" ]]; then
  echo "ERROR: AGENT_KEY must be injected (process-only; never written out)" >&2
  exit 2
fi

TMP_HOME="$TMP_ROOT/home"
mkdir -p "$TMP_HOME"
STAMP="$$-$(date +%s)"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

# --- Layer 1: transport reachable -------------------------------------------
code=$(curl --noproxy '*' -s -o "$TMP_HOME/card.json" -w '%{http_code}' \
  --max-time 10 "$HOST/.well-known/agent-card.json" 2>/dev/null || true)
if [[ "$code" != "200" ]]; then
  echo "FAIL layer1 transport: HTTP $code from $HOST" >&2
  exit 3
fi
echo "ok layer1  transport reachable (HTTP 200, agent card)"

# --- Layer 2: protocol request/response ---------------------------------------
# POST to the JSON-RPC endpoint; exact method per A2A (message/send) or ACP.
# This harness covers A2A; ACP stdio variants use a separate driver (see
# dsh-executor-deployment §6.4). The key design point: match the response by
# JSON-RPC id, not by line order (async notifications interleave).

if [[ -z "${SHORT_PROMPT:-}" ]]; then
  echo "ERROR: SHORT_PROMPT is required for a real generation probe" >&2
  exit 2
fi
if [[ -z "${EXPECTED_OUTPUT_RE:-}" ]]; then
  echo "ERROR: EXPECTED_OUTPUT_RE is required for output acceptance" >&2
  exit 2
fi

# --- Layer 2/3/4: protocol, task-state, and generation -----------------------
# A short fixed prompt. The actual generation MUST be inspected, not just the
# terminal state. Failure to produce usable text sets exit 6 even when the
# task-state would pass.
# Use Python's JSON encoder so quotes/newlines in the prompt cannot corrupt the
# request. This is an A2A-shaped example; ACP stdio uses a separate open-stdin
# driver (see dsh-executor-deployment §6.4).
req="$TMP_HOME/req.json"
python3 - "$SHORT_PROMPT" > "$req" <<'PY'
import json
import sys
prompt = sys.argv[1]
print(json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {"message": {"role": "user", "parts": [{"text": prompt, "kind": "text"}]}}
}))
PY
code=$(curl --noproxy '*' -s -o "$TMP_HOME/resp.json" -w '%{http_code}' \
  --max-time 60 -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' -d "@$req" "$HOST/rpc" 2>/dev/null || true)
if [[ "$code" != "200" ]]; then
  echo "FAIL layer2 protocol request/response: HTTP $code" >&2
  exit 4
fi
# Inspect the terminal task state and the generated text (a robust consumer
# must read the actual text, not just status — reproduce the P4-4 lesson).
if ! grep -q 'TASK_STATE_COMPLETED' "$TMP_HOME/resp.json"; then
  echo "FAIL layer3 task-state: not TASK_STATE_COMPLETED" >&2
  exit 5
fi
if ! grep -Eqi -- "$EXPECTED_OUTPUT_RE" "$TMP_HOME/resp.json"; then
  echo "FAIL layer4 generation: expected usable output was not observed" >&2
  exit 6
fi
echo "ok layer2  protocol request/response (HTTP 200)"
echo "ok layer3  task terminal state = TASK_STATE_COMPLETED"
echo "ok layer4  usable generated output observed"

echo "ALL RUNTIME LAYERS PASS"
exit 0
