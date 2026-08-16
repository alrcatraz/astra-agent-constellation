"""External ANP (Agent Network Protocol) endpoint for the astra constellation.

Exposes an agent over OpenANP, bound to the external-facing HTTPS facade.
The FastANP integration mounts the standard ANP discovery/RPC endpoints:

  /agent/ad.json        -> Agent Description (discovery, public)
  /agent/interface.json -> OpenRPC interface document (public)
  /rpc                  -> JSON-RPC 2.0 call surface (authenticated)
  /agent/did.json       -> DID document (DID-WBA identity, public)
  /.well-known/did.json -> DID document (standard did:wba resolution, public)

Authentication (two-phase, switchable via ANP_AUTH_MODE):
  phase-1 (default): HTTP Message Signature (RFC 9421) verified against
      pre-shared DID documents in ANP_TRUSTED_DIDS_DIR. Works over plain
      HTTP + bare IP, no TLS/dns resolution needed. Tolerates did:all peers.
  phase-2: full OpenANP DID-WBA (`did:wba:<domain>`). The native
      `DidWbaVerifier` middleware resolves each peer's DID document over
      HTTPS and verifies signatures network-wise. Enabled via
      ANP_AUTH_MODE=didwba. NOTE: native verifier only accepts did:wba
      peers — any did:all peer (e.g. a pre-migration test peer) will be
      401. Migrate peers to did:wba before switching.

DID-WBA identity is served *publicly* (standard requires it): the
public-paths pre-middleware short-circuits /agent/did.json and
/.well-known/did.json so discovery + DID resolve work WITHOUT auth even
when phase-2 native middleware would otherwise guard them. Everything else
is authenticated.

All machine/instance-specific values are injected via environment
variables -- nothing hard-coded. Defaults are placeholders for the public
template.

Run:
    ANP_AUTH_MODE=phase1 ANP_TRUSTED_DIDS_DIR=/path/to/trusted-dids \\
        ANP_KEYS_DIR=/path/to/keys <venv>/bin/python anp_server_main.py
"""
import json
import os

import starlette.middleware
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from anp.fastanp import Context, FastANP

from dispatch import run_hermes_oneshot, DispatchError

KEYS_DIR = os.environ.get("ANP_KEYS_DIR", "<KEYS_DIR>")
DID = os.environ.get(
    "EXTERNAL_ANP_DID",
    "did:wba:<FACADE-DOMAIN>",
)
AUTH_MODE = os.environ.get("ANP_AUTH_MODE", "phase1")  # phase1 | didwba

# Paths that MUST stay publicly resolvable (DID-WBA reaches them without auth).
PUBLIC_PATHS = {
    "/agent/did.json",
    "/.well-known/did.json",
    "/.well-known/wba/agent/ad.json",
}


def _load_did_document() -> dict | None:
    """Return the DID-WBA document for this agent, or None if not generated."""
    if KEYS_DIR.startswith("<"):
        return None
    doc_path = os.path.join(KEYS_DIR, "did_wba_document.json")
    if os.path.isfile(doc_path):
        with open(doc_path, encoding="utf-8") as fh:
            return json.load(fh)
    # Fall back to the legacy did:all document for phase-1.
    legacy = os.path.join(KEYS_DIR, "did_document.json")
    if os.path.isfile(legacy):
        with open(legacy, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def build_app() -> FastAPI:
    app = FastAPI(title="astra-external-anp")

    enable_native = AUTH_MODE == "didwba"
    trusted_dids_dir = os.environ.get("ANP_TRUSTED_DIDS_DIR", "~/.anp/trusted-dids")
    allowed_domains = [
        d.strip()
        for d in os.environ.get("ANP_ALLOWED_DOMAINS", "").split(",")
        if d.strip()
    ]

    did_doc = _load_did_document()
    did = DID
    if did_doc and did_doc.get("id", "").startswith("did:wba:"):
        did = did_doc["id"]

    anp = FastANP(
        app=app,
        name="astra-external-anp",
        description=(
            "Astra constellation external ANP endpoint. "
            "Verifies external agent-to-agent connectivity over the Agent Network Protocol."
        ),
        agent_domain=f"https://{allowed_domains[0]}" if allowed_domains else "<DOMAIN>",
        did=did,
        enable_auth_middleware=enable_native,
        auth_config=_native_auth_config(trusted_dids_dir, allowed_domains)
        if enable_native
        else None,
    )

    if AUTH_MODE == "phase1":
        from anp_auth import build_http_signature_middleware

        app.add_middleware(
            starlette.middleware.base.BaseHTTPMiddleware,
            dispatch=build_http_signature_middleware(
                trusted_dids_dir=os.path.expanduser(trusted_dids_dir),
                allowed_domains=allowed_domains or None,
            ),
        )

    @anp.interface("/echo", description="Echo a string back to verify ANP connectivity.")
    async def echo(text: str = "") -> dict:
        return {"message": f"external-anp-ok | astra constellation | echo: {text}"}

    @anp.interface(
        "/task",
        description=(
            "Execute an operational/administrative task by handing it to the "
            "local Hermes agent. The caller is identified by the DID-WBA "
            "signature verified at the boundary (context.did)."
        ),
    )
    async def task(context: Context, text: str = "") -> dict:
        caller_did = getattr(context, "did", None) or "anonymous"
        try:
            result = run_hermes_oneshot(task=text, identity=caller_did)
            return {"message": result, "origin_did": caller_did}
        except DispatchError as exc:
            return {"error": str(exc), "origin_did": caller_did}

    def _build_ad() -> dict:
        ad = anp.get_common_header(agent_description_path="/agent/ad.json")
        ad["Infomations"] = anp.get_information_list(
            exclude_paths=["/agent/ad.json", "/ad.json"]
        )
        ad["interfaces"] = [proxy.link_summary for proxy in anp.interfaces.values()]
        return ad

    @app.get("/ad.json", include_in_schema=False)
    async def ad_alias() -> dict:
        return _build_ad()

    @app.get("/agent/ad.json", include_in_schema=False)
    async def ad_endpoint() -> dict:
        return _build_ad()

    @app.get("/agent/interface.json", include_in_schema=False)
    async def interface_endpoint() -> dict:
        first = next(iter(anp.interfaces.values()), None)
        return first.openrpc_doc if first else {}

    @app.get("/.well-known/wba/agent/ad.json", include_in_schema=False)
    async def ad_wellknown() -> dict:
        return _build_ad()

    @app.get("/agent/did.json", include_in_schema=False)
    async def did_document() -> dict:
        return did_doc or {"error": "no DID document generated"}

    @app.get("/.well-known/did.json", include_in_schema=False)
    async def did_document_wellknown() -> dict:
        return did_doc or {"error": "no DID document generated"}

    # PUBLIC-PATHS pre-middleware: registered AFTER FastANP so it runs FIRST
    # (FastAPI executes later-registered http middleware outermost). It lets
    # discovery + DID resolution through without auth regardless of auth mode.
    @app.middleware("http")
    async def public_paths(request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS:
            if path.endswith("did.json"):
                payload = did_doc or {"error": "no DID document generated"}
            else:
                payload = _build_ad()
            return JSONResponse(payload)
        return await call_next(request)

    return app


def _native_auth_config(trusted_dids_dir: str, allowed_domains: list[str]):
    """Build DidWbaVerifierConfig for phase-2 native verification."""
    from anp.authentication.did_wba_verifier import DidWbaVerifierConfig

    keys_dir = os.path.expanduser(KEYS_DIR)
    jwt_priv = jwt_pub = None
    for cand in (keys_dir, os.path.expanduser("~/.anp")):
        p = os.path.join(cand, "jwt_private.pem")
        if os.path.isfile(p):
            jwt_priv = open(p, encoding="utf-8").read()
        p2 = os.path.join(cand, "jwt_public.pem")
        if os.path.isfile(p2):
            jwt_pub = open(p2, encoding="utf-8").read()
        if jwt_priv and jwt_pub:
            break
    if not (jwt_priv and jwt_pub):
        raise RuntimeError(
            "phase-2 DID-WBA requires jwt_private.pem + jwt_public.pem in "
            f"ANP_KEYS_DIR or ~/.anp (found none in {KEYS_DIR})"
        )

    alg = os.environ.get("ANP_JWT_ALG", "ES256")
    return DidWbaVerifierConfig(
        jwt_private_key=jwt_priv,
        jwt_public_key=jwt_pub,
        jwt_algorithm=alg,
        allowed_domains=allowed_domains or None,
        allow_http_signatures=os.environ.get("ANP_ALLOW_HTTP_SIG", "1") == "1",
        allow_legacy_didwba=os.environ.get("ANP_ALLOW_LEGACY", "1") == "1",
    )


if __name__ == "__main__":
    port = int(os.environ.get("EXTERNAL_ANP_PORT", "9911"))
    uvicorn.run(
        build_app(),
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",  # trust X-Forwarded-* set by the gateway nginx
    )
