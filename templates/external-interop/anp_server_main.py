"""
External ANP (Agent Network Protocol) endpoint for the astra constellation.

Exposes an agent over OpenANP, bound to the external-facing interfaces. The
FastANP integration mounts the standard ANP discovery/RPC endpoints:

  /agent/ad.json        -> Agent Description (discovery, public)
  /agent/interface.json -> OpenRPC interface document (public)
  /rpc                  -> JSON-RPC 2.0 call surface (authenticated)
  /agent/did.json       -> DID document (DID-WBA identity resolution)

Authentication (two-phase):
  Phase-1 (current): HTTP Message Signature (RFC 9421) verified against
      pre-shared DID documents in ANP_TRUSTED_DIDS_DIR. Works over plain
      HTTP + bare IP, no TLS/dns resolution needed.
  Phase-2 (future): full OpenANP DID-WBA (`did:wba:<domain>`) once a
      TLS-terminated domain is available. Native auth middleware is kept
      disabled here so phase-1 runs.

All machine/instance-specific values (host, ports, DID, trust dir) are
injected via environment variables -- nothing hard-coded. The defaults here
are placeholders for the public template.

Run:
    ANP_ENABLE_AUTH=1 ANP_TRUSTED_DIDS_DIR=/path/to/trusted-dids \\
        <venv>/bin/python anp_server_main.py
"""

import json
import os

import starlette.middleware
import uvicorn
from fastapi import FastAPI

from anp.fastanp import FastANP

KEYS_DIR = os.environ.get("ANP_KEYS_DIR", "<KEYS_DIR>")
EXTERNAL_HOST = os.environ.get("EXTERNAL_HOST", "<EXTERNAL_HOST>")
PORT = int(os.environ.get("EXTERNAL_ANP_PORT", "9911"))
DOMAIN = f"{EXTERNAL_HOST}:{PORT}"
AGENT_NAME = os.environ.get("EXTERNAL_ANP_NAME", "astra-external-anp")
DID = os.environ.get(
    "EXTERNAL_ANP_DID",
    "did:all:<BITCOIN-ADDRESS>",
)


def build_app() -> FastAPI:
    app = FastAPI(title=AGENT_NAME)

    # Phase-1 authentication: HTTP Message Signature (RFC 9421) using
    # pre-shared DID documents (no HTTPS/dns resolution needed). Full OpenANP
    # DID-WBA (requires a TLS-terminated domain) is deferred to phase-2.
    # OpenANP's native auth middleware is therefore left disabled here; we
    # attach our own verifier middleware to the FastAPI app.
    enable_auth = os.environ.get("ANP_ENABLE_AUTH", "1") == "1"
    trusted_dids_dir = os.environ.get("ANP_TRUSTED_DIDS_DIR", "~/.anp/trusted-dids")
    allowed_domains = [
        d.strip()
        for d in os.environ.get("ANP_ALLOWED_DOMAINS", "").split(",")
        if d.strip()
    ]

    anp = FastANP(
        app=app,
        name=AGENT_NAME,
        description=(
            "Astra constellation external ANP endpoint. "
            "Verifies external agent-to-agent connectivity over the Agent Network Protocol."
        ),
        agent_domain=DOMAIN,
        did=DID,
        enable_auth_middleware=False,  # native DID-WBA deferred to phase-2
    )

    if enable_auth:
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

    def _build_ad() -> dict:
        """Assemble the Agent Description (ad.json) document."""
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

    # Expose the DID document so external peers can resolve this agent's DID.
    did_doc_path = os.path.join(KEYS_DIR, "did_document.json")
    if not KEYS_DIR.startswith("<") and os.path.isfile(did_doc_path):
        @app.get("/agent/did.json", include_in_schema=False)
        async def did_document() -> dict:
            with open(did_doc_path, encoding="utf-8") as fh:
                return json.load(fh)

    return app


if __name__ == "__main__":
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
