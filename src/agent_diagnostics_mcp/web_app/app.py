from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from agent_diagnostics_mcp.domain import DiagnosticReport
from agent_diagnostics_mcp.mcp_server import build_diagnostics_mcp
from agent_diagnostics_mcp.repository import DiagnosticRepository, SqliteDiagnosticRepository
from agent_diagnostics_mcp.service import DiagnosticService
from agent_diagnostics_mcp.web_app.html import render_html
from agent_diagnostics_mcp.web_app.tool_failures import (
    build_diagnostic,
    detect_provider,
    should_save,
)


def create_app(repository: DiagnosticRepository | None = None) -> FastAPI:
    repo = repository or SqliteDiagnosticRepository()
    service = DiagnosticService(repo)
    mcp_app = build_diagnostics_mcp(repo).http_app(path="/")

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

        saved = service.report(build_diagnostic(payload, detected))
        return {
            "saved": True,
            "id": saved.id,
            "category": saved.category.value,
            "severity": saved.severity.value,
        }

    @app.get("/", response_class=HTMLResponse)
    def index(limit: int = Query(default=20, ge=1, le=100)) -> HTMLResponse:
        reports = service.list_recent(limit)
        return HTMLResponse(render_html(reports, limit))

    app.mount("/mcp", mcp_app)
    return app
