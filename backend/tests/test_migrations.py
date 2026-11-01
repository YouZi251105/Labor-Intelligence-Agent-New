import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR


def test_initial_migration_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
    command = [sys.executable, "-m", "alembic", "upgrade", "head"]

    first = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    second = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"users", "cases", "evidence", "documents", "audit_logs"} <= tables
    assert "simulation_sessions" in tables
    assert "revenue_ledger" in tables
