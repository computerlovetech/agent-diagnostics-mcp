from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DiagnosticCategory(StrEnum):
    MISSING_CONTEXT = "missing_context"
    REPEATEDLY_BROKEN_TOOL = "repeatedly_broken_tool"
    CAPABILITY_GAP = "capability_gap"
    COMPLETE_TASK_FAILURE = "complete_task_failure"
    SUSPICIOUS_LOOP = "suspicious_loop"
    BAD_TOOL_SELECTION = "bad_tool_selection"


CATEGORY_DESCRIPTIONS: dict[DiagnosticCategory, str] = {
    DiagnosticCategory.MISSING_CONTEXT: (
        "Critical information, credentials, or access is missing."
    ),
    DiagnosticCategory.REPEATEDLY_BROKEN_TOOL: (
        "A tool failed repeatedly and blocks progress."
    ),
    DiagnosticCategory.CAPABILITY_GAP: (
        "The task requires a capability, permission, or tool that is unavailable."
    ),
    DiagnosticCategory.COMPLETE_TASK_FAILURE: (
        "The agent attempted the task but could not complete it."
    ),
    DiagnosticCategory.SUSPICIOUS_LOOP: (
        "The agent appears to be repeating actions without progress."
    ),
    DiagnosticCategory.BAD_TOOL_SELECTION: (
        "The agent selected tools that do not match the task."
    ),
}


class DiagnosticSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DiagnosticReportCreate(BaseModel):
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    summary: str = Field(min_length=5)
    evidence: str = Field(min_length=5)
    suggested_fix: str = Field(min_length=5)


class DiagnosticReport(BaseModel):
    id: int
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    summary: str
    evidence: str
    suggested_fix: str
    created_at: datetime
