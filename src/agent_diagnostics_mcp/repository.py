from __future__ import annotations

import sqlite3
from threading import Lock
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReport,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)

_DEFAULT_DB_PATH = Path.home() / ".agent-diagnostics" / "diagnostics.sqlite3"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence TEXT NOT NULL,
    suggested_fix TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


class DiagnosticRepository(Protocol):
    def save(self, report: DiagnosticReportCreate) -> DiagnosticReport: ...
    def list_recent(self, limit: int = 20) -> list[DiagnosticReport]: ...


class InMemoryDiagnosticRepository:
    def __init__(self) -> None:
        self._reports: list[DiagnosticReport] = []
        self._next_id: int = 1

    def save(self, report: DiagnosticReportCreate) -> DiagnosticReport:
        saved = DiagnosticReport(
            id=self._next_id,
            category=report.category,
            severity=report.severity,
            summary=report.summary,
            evidence=report.evidence,
            suggested_fix=report.suggested_fix,
            created_at=datetime.now(timezone.utc),
        )
        self._next_id += 1
        self._reports.append(saved)
        return saved

    def list_recent(self, limit: int = 20) -> list[DiagnosticReport]:
        return list(reversed(self._reports[-limit:]))


class SqliteDiagnosticRepository:
    def __init__(self, db_path: Path = _DEFAULT_DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(_CREATE_TABLE)
            self._conn.commit()

    def save(self, report: DiagnosticReportCreate) -> DiagnosticReport:
        now = datetime.now(timezone.utc)
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO diagnostic_reports (category, severity, summary, evidence, suggested_fix, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.category.value,
                    report.severity.value,
                    report.summary,
                    report.evidence,
                    report.suggested_fix,
                    now.isoformat(),
                ),
            )
            self._conn.commit()
        return DiagnosticReport(
            id=cursor.lastrowid,  # type: ignore[arg-type]
            category=report.category,
            severity=report.severity,
            summary=report.summary,
            evidence=report.evidence,
            suggested_fix=report.suggested_fix,
            created_at=now,
        )

    def list_recent(self, limit: int = 20) -> list[DiagnosticReport]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, category, severity, summary, evidence, suggested_fix, created_at "
                "FROM diagnostic_reports ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            DiagnosticReport(
                id=row[0],
                category=DiagnosticCategory(row[1]),
                severity=DiagnosticSeverity(row[2]),
                summary=row[3],
                evidence=row[4],
                suggested_fix=row[5],
                created_at=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
