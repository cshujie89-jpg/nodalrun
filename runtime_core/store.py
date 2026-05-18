from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


ROOT_DIR = Path(os.environ.get("RUNTIME_ROOT", Path.cwd() / ".runtime"))
DB_PATH = Path(os.environ.get("RUNTIME_DB", ROOT_DIR / "runtime.db"))


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


def connect() -> sqlite3.Connection:
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in (
        "acceptance_criteria",
        "required_capabilities",
        "required_tools",
        "capabilities",
        "tools",
        "metadata",
        "result",
    ):
        if key in data:
            data[key] = loads(data[key], [] if key.endswith("s") or key == "acceptance_criteria" else {})
    return data


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in rows if row is not None]


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                repo_url TEXT,
                repo_path TEXT,
                default_branch TEXT NOT NULL DEFAULT 'main',
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                worker_type TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                tools TEXT NOT NULL,
                max_concurrency INTEGER NOT NULL DEFAULT 1,
                current_session_id TEXT,
                last_heartbeat_at INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS remote_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                agent_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                role TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                tools TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                worker_id TEXT,
                endpoint_url TEXT,
                last_heartbeat_at INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(worker_id) REFERENCES workers(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                plan_id TEXT,
                plan_sequence INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                task_type TEXT NOT NULL,
                required_role TEXT NOT NULL,
                required_capabilities TEXT NOT NULL,
                required_tools TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 50,
                status TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                validation_command TEXT,
                created_by TEXT NOT NULL,
                assigned_worker_id TEXT,
                active_session_id TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS pm_plans (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                objective TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                status TEXT NOT NULL,
                workspace_path TEXT NOT NULL,
                base_commit TEXT,
                branch_name TEXT,
                result TEXT NOT NULL DEFAULT '{}',
                started_at INTEGER NOT NULL,
                ended_at INTEGER,
                last_heartbeat_at INTEGER,
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(worker_id) REFERENCES workers(id)
            );

            CREATE TABLE IF NOT EXISTS session_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                uri TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS task_events (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                actor_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                task_id TEXT,
                session_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            );
            """
        )
        ensure_column(conn, "tasks", "plan_id", "TEXT")
        ensure_column(conn, "tasks", "plan_sequence", "INTEGER")
        ensure_column(conn, "tasks", "retry_count", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "tasks", "max_retries", "INTEGER NOT NULL DEFAULT 1")


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def add_task_event(task_id: str, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO task_events VALUES (?, ?, ?, ?, ?, ?)",
            (new_id("evt"), task_id, event_type, message, dumps(metadata or {}), now_ms()),
        )


def add_audit_event(
    actor_type: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    task_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("aud"),
                actor_type,
                actor_id,
                action,
                resource_type,
                resource_id,
                task_id,
                session_id,
                dumps(metadata or {}),
                now_ms(),
            ),
        )
