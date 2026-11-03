import json
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


def test_content_owner_terms_are_migrated(tmp_path: Path) -> None:
    database = tmp_path / "content-terms.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"

    before = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "f0a1b2c3d4e5"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert before.returncode == 0, before.stderr

    now = "2026-11-03 12:00:00"
    content = {"disclaimer": "待法律内容负责人复核"}
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO rule_configs (
                dispute_type, name, evidence_requirements, next_steps,
                source_note, review_status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wage",
                "欠薪规则",
                "[]",
                "[]",
                "待法律内容负责人复核",
                "pending_review",
                1,
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO rule_packages (
                package_type, package_id, version, status, content_json,
                checksum, created_by_id, reviewed_by_id, created_at,
                updated_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "workflow",
                "test-package",
                "1.0.0",
                "pending_review",
                json.dumps(content, ensure_ascii=False),
                "old-checksum",
                None,
                None,
                now,
                now,
                None,
            ),
        )
        connection.commit()

    after = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert after.returncode == 0, after.stderr

    with sqlite3.connect(database) as connection:
        source_note = connection.execute(
            "SELECT source_note FROM rule_configs"
        ).fetchone()[0]
        migrated = connection.execute(
            "SELECT content_json, checksum FROM rule_packages"
        ).fetchone()

    assert source_note == "待内容复核人员校验"
    assert json.loads(migrated[0])["disclaimer"] == "待内容复核人员校验"
    assert migrated[1] != "old-checksum"
