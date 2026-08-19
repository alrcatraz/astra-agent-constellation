"""
External A2A endpoint for the astra constellation.

Exposes a minimal verification agent over the A2A Protocol v1.0 (JSON-RPC
binding) on port 9910, bound to the external-facing interfaces (injected via
environment variables). API-key authorisation is enforced in the Starlette
app; the Agent Card declares the security scheme so clients know to send
the key.

This is the "external A2A" half of the external-interop deployment. The
internal Hermes A2A endpoint stays on the loopback address untouched.

Run:
    <VENV>/bin/python a2a_server_main.py

Machine/instance-specific values (bind host, port, key, card URL) are
injected via environment variables -- see the defaults below for the
placeholder shape.
"""
import os

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    APIKeySecurityScheme,
    SecurityScheme,
    TaskState,
)

from dispatch import run_hermes_oneshot, DispatchError

EXTERNAL_HOSTS = [os.environ.get("EXTERNAL_HOST", "0.0.0.0")]
PORT = int(os.environ.get("EXTERNAL_A2A_PORT", "9910"))
ACCESS_KEY = os.environ.get("EXTERNAL_A2A_KEY", "")
# Optional per-peer API keys -> external caller identity. Format:
#   EXTERNAL_A2A_PEERS="alpha=<keyA>,beta=<keyB>"
# Lets the agent distinguish specific external peers (Alpha -> "alpha"), not
# just "internal vs external". When unset, falls back to the single
# EXTERNAL_A2A_KEY and every authenticated caller is labelled "external".
PEERS = {}
_peers_env = os.environ.get("EXTERNAL_A2A_PEERS", "").strip()
if _peers_env:
    for chunk in _peers_env.split(","):
        if "=" in chunk:
            name, key = chunk.split("=", 1)
            PEERS[name.strip()] = key.strip()
# Card URL is what clients use to locate us; override with the public
# host:port when a stable address is known.
CARD_URL = os.environ.get("EXTERNAL_CARD_URL", f"http://{EXTERNAL_HOSTS[0]}:{PORT}")


class DispatchAgent:
    """External-facing agent: hands tasks to the local Hermes agent for real
    execution, tagging each request with the authenticated external caller.
    """

    async def invoke(self, user_request: str, identity: str) -> str:
        try:
            return run_hermes_oneshot(task=user_request, identity=identity)
        except DispatchError as exc:
            return f"dispatch-error: {exc}"


class DispatchAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = DispatchAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue, task_id=task.id, context_id=task.context_id
        )
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Processing request..."),
        )

        query = get_message_text(context.message)
        identity = getattr(context, "peer_name", None) or "unknown"
        result = await self.agent.invoke(
            user_request=query or "no-input", identity=identity
        )
        await task_updater.add_artifact(
            parts=[new_text_part(text=result, media_type="text/plain")]
        )
        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Request is completed!"),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests missing/invalid an API key (X-API-Key header), and label
    the authenticated external caller on ``request.state.peer_name`` so the
    executor can pass a specific identity down to the local agent.
    """

    def __init__(self, app, *, peers: dict[str, str], single_key: str) -> None:
        super().__init__(app)
        self._peers = peers
        self._single_key = single_key

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("X-API-Key", "")
        if self._peers:
            identity = next((name for name, k in self._peers.items() if k == key), None)
            if identity is None:
                return JSONResponse(
                    {"detail": "invalid or missing API key"}, status_code=401
                )
            request.state.peer_name = identity
        elif self._single_key:
            if key != self._single_key:
                return JSONResponse(
                    {"detail": "invalid or missing API key"}, status_code=401
                )
            request.state.peer_name = "external"
        else:
            request.state.peer_name = "unauthenticated"
        return await call_next(request)


def build_app() -> Starlette:
    skill = AgentSkill(
        id="external_task",
        name="Astra External Task",
        description="Executes operational/administrative tasks by handing them to the local Hermes agent.",
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["astra", "external-interop", "task"],
        examples=["ping your constellation", "report current status"],
    )

    security_scheme = SecurityScheme(
        api_key_security_scheme=APIKeySecurityScheme(
            name="X-API-Key",
            location="HEADER",
            description="API key for external access to the astra constellation.",
        )
    )

    public_agent_card = AgentCard(
        name="astra-external-task",
        description=(
            "Astra constellation external A2A endpoint. "
            "Dispatches external requests to the local Hermes agent for execution."
        ),
        version="0.0.2",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=CARD_URL,
                protocol_version="1.0",
            )
        ],
        skills=[skill],
        security_schemes={skill.id: security_scheme},
    )

    request_handler = DefaultRequestHandler(
        agent_executor=DispatchAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=public_agent_card,
        extended_agent_card=public_agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(public_agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    middleware = [Middleware(APIKeyMiddleware, peers=PEERS, single_key=ACCESS_KEY)]
    return Starlette(routes=routes, middleware=middleware)


if __name__ == "__main__":
    app = build_app()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
