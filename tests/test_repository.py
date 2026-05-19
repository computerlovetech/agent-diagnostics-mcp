from collections.abc import Callable
from pathlib import Path

import pytest

from agent_diagnostics_mcp.domain import (
    DiagnosticCategory,
    DiagnosticReportCreate,
    DiagnosticSeverity,
)
from agent_diagnostics_mcp.repository import (
    DiagnosticRepository,
    InMemoryDiagnosticRepository,
    SqliteDiagnosticRepository,
)


def _sample_creation(
    category: DiagnosticCategory = DiagnosticCategory.MISSING_CONTEXT,
    severity: DiagnosticSeverity = DiagnosticSeverity.HIGH,
) -> DiagnosticReportCreate:
    return DiagnosticReportCreate(
        category=category,
        severity=severity,
        summary="Cannot find API key",
        evidence="Tried three env var names, none set",
        suggested_fix="Add API_KEY to .env.example",
    )


@pytest.fixture
def inmemory_repo() -> InMemoryDiagnosticRepository:
    return InMemoryDiagnosticRepository()


@pytest.fixture
def sqlite_repo(tmp_path: Path) -> SqliteDiagnosticRepository:
    return SqliteDiagnosticRepository(tmp_path / "test.sqlite3")


@pytest.mark.parametrize(
    "repo_factory",
    [
        pytest.param(lambda p: InMemoryDiagnosticRepository(), id="inmemory"),
        pytest.param(lambda p: SqliteDiagnosticRepository(p / "t.db"), id="sqlite"),
    ],
)
class TestRepositoryContract:
    def test_save_returns_report_with_id(
        self,
        tmp_path: Path,
        repo_factory: Callable[[Path], DiagnosticRepository],
    ) -> None:
        repo = repo_factory(tmp_path)
        saved = repo.save(_sample_creation())
        assert saved.id >= 1
        assert saved.category == DiagnosticCategory.MISSING_CONTEXT
        assert saved.severity == DiagnosticSeverity.HIGH

    def test_list_recent_empty(
        self,
        tmp_path: Path,
        repo_factory: Callable[[Path], DiagnosticRepository],
    ) -> None:
        repo = repo_factory(tmp_path)
        assert repo.list_recent() == []

    def test_list_recent_returns_newest_first(
        self,
        tmp_path: Path,
        repo_factory: Callable[[Path], DiagnosticRepository],
    ) -> None:
        repo = repo_factory(tmp_path)
        repo.save(_sample_creation(severity=DiagnosticSeverity.LOW))
        repo.save(_sample_creation(severity=DiagnosticSeverity.HIGH))
        reports = repo.list_recent()
        assert reports[0].severity == DiagnosticSeverity.HIGH
        assert reports[1].severity == DiagnosticSeverity.LOW

    def test_list_recent_respects_limit(
        self,
        tmp_path: Path,
        repo_factory: Callable[[Path], DiagnosticRepository],
    ) -> None:
        repo = repo_factory(tmp_path)
        for _ in range(5):
            repo.save(_sample_creation())
        assert len(repo.list_recent(limit=3)) == 3
