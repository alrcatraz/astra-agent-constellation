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

EXTERNAL_HOSTS = [os.environ.get("EXTERNAL_HOST", "0.0.0.0")]
PORT = int(os.environ.get("EXTERNAL_A2A_PORT", "9910"))
ACCESS_KEY = os.environ.get("EXTERNAL_A2A_KEY", "")
# Agent Card URL is what clients use to locate us; override with the public
# host:port when a stable address is known.
CARD_URL = os.environ.get("EXTERNAL_CARD_URL", f"http://{EXTERNAL_HOSTS[0]}:{PORT}")


class VerificationAgent:
    """Minimal external-facing verification agent for the astra constellation."""

    async def invoke(self, user_request: str) -> str:
        return (
            f"external-interop-ok | astra constellation | echo: {user_request}"
        )


class VerificationAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = VerificationAgent()

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
        result = await self.agent.invoke(user_request=query or "no-input")
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
    """Reject requests missing/invalid the API key (X-API-Key header)."""

    def __init__(self, app, *, key: str) -> None:
        super().__init__(app)
        self._key = key

    async def dispatch(self, request: Request, call_next):
        if not self._key:
            return await call_next(request)
        presented = request.headers.get("X-API-Key", "")
        if presented != self._key:
            return JSONResponse(
                {"detail": "invalid or missing API key"}, status_code=401
            )
        return await call_next(request)


def build_app() -> Starlette:
    skill = AgentSkill(
        id="verification_echo",
        name="Astra External Verification",
        description="Verifies external A2A connectivity to the astra constellation.",
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["astra", "external-interop", "verification"],
        examples=["ping your constellation"],
    )

    security_scheme = SecurityScheme(
        api_key_security_scheme=APIKeySecurityScheme(
            name="X-API-Key",
            location="HEADER",
            description="API key for external access to the astra constellation.",
        )
    )

    public_agent_card = AgentCard(
        name="astra-external-verification",
        description=(
            "Astra constellation external A2A endpoint. "
            "Verifies external agent-to-agent connectivity."
        ),
        version="0.0.1",
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
        agent_executor=VerificationAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=public_agent_card,
        extended_agent_card=public_agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(public_agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    middleware = [Middleware(APIKeyMiddleware, key=ACCESS_KEY)] if ACCESS_KEY else []
    return Starlette(routes=routes, middleware=middleware)


if __name__ == "__main__":
    app = build_app()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
