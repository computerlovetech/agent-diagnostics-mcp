from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, EventSourceResponse
from fastapi.staticfiles import StaticFiles

from agent_diagnostics_mcp.domain import (
    CATEGORY_DESCRIPTIONS,
    DiagnosticReport,
    DiagnosticReportCreate,
)
from agent_diagnostics_mcp.events import event_hub
from agent_diagnostics_mcp.factory import create_diagnostic_service
from agent_diagnostics_mcp.mcp_server import build_diagnostics_mcp
from agent_diagnostics_mcp.repository import DiagnosticRepository
from agent_diagnostics_mcp.web_app.diagnostic_stream import diagnostic_events
from agent_diagnostics_mcp.web_app.tool_failures import (
    build_diagnostic,
    detect_provider,
    should_save,
)

_WEB_APP_DIR = Path(__file__).parent
_PUBLIC_DIR = _WEB_APP_DIR / "public"
_STATIC_DIR = _WEB_APP_DIR / "static"


def create_app(repository: DiagnosticRepository | None = None) -> FastAPI:
    service = create_diagnostic_service(repository)

    def _save_and_publish(creation: DiagnosticReportCreate) -> DiagnosticReport:
        saved = service.report(creation)
        event_hub.publish(saved)
        return saved

    mcp_app = build_diagnostics_mcp(service=service).http_app(path="/")

    app = FastAPI(
        title="Agent Diagnostics",
        version="0.1.0",
        lifespan=mcp_app.lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/diagnostics")
    def list_diagnostics(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[DiagnosticReport]:
        return service.list_recent(limit)

    @app.get("/api/diagnostics/stream", response_class=EventSourceResponse)
    async def stream_diagnostics(request: Request):
        async for event in diagnostic_events(request, event_hub):
            yield event

    @app.get("/api/diagnostics/categories")
    def list_diagnostic_categories() -> list[dict[str, str]]:
        return [
            {"name": category.value, "description": description}
            for category, description in CATEGORY_DESCRIPTIONS.items()
        ]

    @app.post("/api/tool-call-failures")
    async def log_tool_call_failure(
        request: Request,
        provider: str | None = Query(default=None),
    ) -> dict[str, Any]:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")

        detected = detect_provider(payload, provider)
        save = should_save(payload, detected)
        if save is None:
            hook_event = payload.get("hook_event_name", "")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported hook event for {detected.value}: {hook_event}",
            )
        if not save:
            return {"saved": False, "reason": "not_a_failure"}

        saved = _save_and_publish(build_diagnostic(payload, detected))
        return {
            "saved": True,
            "id": saved.id,
            "category": saved.category.value,
            "severity": saved.severity.value,
        }

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_PUBLIC_DIR / "index.html", media_type="text/html")

    app.mount("/assets", StaticFiles(directory=_STATIC_DIR), name="assets")
    app.mount("/mcp", mcp_app)
    return app
