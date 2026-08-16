"""
Custom HTTP Message Signature authentication middleware for the external ANP
endpoint (phase-1 of DID-WBA adoption).

Phase-1 rationale
-----------------
OpenANP's native DID-WBA verifier re-resolves the caller's DID document over
HTTPS (`resolve_did_wba_document`), which requires the caller to expose a
`did:wba:<domain>` identity on a TLS-terminated host. The current formal
endpoints run on plain HTTP + bare overlay/LAN IP (e.g. 192.168.x.x /
10.x.x.x), so a full DID-WBA handshake is not yet usable.

This middleware therefore implements the SAME RFC 9421-style HTTP Message
Signature verification (reusing `anp.authentication.http_signatures`) but
resolve the signer's DID document from a pre-shared local file instead of over
the network. This keeps the security properties (integrity via content-digest,
anti-replay via nonce, signature binding) while dropping the HTTPS/dns
dependency.

Phase-2 (when a TLS-terminated domain exists) can swap this for OpenANP's
native `DidWbaVerifier` by enabling `enable_auth_middleware=True`.

Signer provisioning
-------------------
Each trusted external peer has a DID document placed under the trust dir
(`ANP_TRUSTED_DIDS_DIR`). The document's `id` (a `did:all:...` or any stable
identifier) is matched against the `keyid` presented in `Signature-Input`.
"""

from __future__ import annotations

import json
import os
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from anp.authentication.http_signatures import verify_http_message_signature

DEFAULT_EXEMPT = [
    "/favicon.ico",
    "/health",
    "/docs",
    "*/ad.json",
    "/info/*",
]


def _load_trusted_did_documents(did_dir: str) -> dict[str, dict[str, Any]]:
    """Load every *.json file under dir into a {did_id: document} map.

    The document `id` is used as the lookup key so the middleware can match a
    presented `keyid` (`<did>#keys-1`) against a known trusted peer.
    """
    registry: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(did_dir):
        return registry
    for name in sorted(os.listdir(did_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(did_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            did = doc.get("id")
            if did:
                registry[did] = doc
        except (json.JSONDecodeError, OSError):
            continue
    return registry


def _get_header(headers: dict[str, str], name: str) -> str:
    low = name.lower()
    for k, v in headers.items():
        if k.lower() == low:
            return v
    return ""


def _is_exempt(path: str, exempt: list[str]) -> bool:
    import fnmatch

    for pattern in exempt:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def build_http_signature_middleware(
    trusted_dids_dir: str,
    allowed_domains: list[str] | None = None,
    exempt_paths: list[str] | None = None,
):
    """Build a FastAPI HTTP middleware that verifies RFC 9421 signatures.

    Verification keys come from pre-shared DID documents under the trust dir,
    so no network resolution is required.
    """
    trust_dir = trusted_dids_dir
    trusted = _load_trusted_did_documents(trust_dir)
    exempt = exempt_paths or DEFAULT_EXEMPT

    async def middleware(request: Request, call_next):
        path = request.url.path
        if _is_exempt(path, exempt):
            return await call_next(request)

        # Domain allow-list check against the Host header.
        if allowed_domains:
            host = request.headers.get("host", "")
            hostname = host.split(":")[0]
            allow = False
            for d in allowed_domains:
                if hostname == d or hostname.endswith("." + d):
                    allow = True
                    break
            if not allow:
                return JSONResponse(
                    {"detail": "host not in allowed domains"}, status_code=403
                )

        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        body = await request.body()

        # Reload trust when the dir mtime changes is overkill for phase-1;
        # resolve on demand so newly-added peers take effect without a restart.
        lookup = _load_trusted_did_documents(trust_dir)

        # Determine which trusted doc to validate with by inspecting keyid.
        sig_input = _get_header(headers, "Signature-Input")
        keyid = None
        if sig_input:
            try:
                from anp.authentication.http_signatures import extract_signature_metadata

                meta = extract_signature_metadata(headers)
                keyid = meta.get("params", {}).get("keyid")
            except Exception:
                keyid = None

        did = keyid.split("#", 1)[0] if keyid else None
        doc = lookup.get(did) if did else None
        if doc is None:
            # Fall back: if exactly one trusted peer is provisioned and the
            # keyid matches its verification method, use it.
            if len(lookup) == 1:
                (doc,) = lookup.values()
            else:
                return JSONResponse(
                    {
                        "detail": (
                            "signer DID not provisioned in trust dir "
                            f"({trust_dir!r})"
                        )
                    },
                    status_code=401,
                )

        ok, reason, _meta = verify_http_message_signature(
            did_document=doc,
            request_method=method,
            request_url=url,
            headers=headers,
            body=body,
        )
        if not ok:
            return JSONResponse({"detail": f"signature verification failed: {reason}"},
                                status_code=401)

        return await call_next(request)

    return middleware
