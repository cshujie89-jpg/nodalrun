from __future__ import annotations

import os
import hashlib
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from runtime_core import workspace
from runtime_core.store import (
    ROOT_DIR as RUNTIME_ROOT,
    add_audit_event,
    add_task_event,
    connect,
    dumps,
    init_db,
    new_id,
    now_ms,
    row_to_dict,
    rows_to_dicts,
)


APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parents[1]
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="AI Runtime OS", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

STALE_WORKER_MS = 120_000
TASK_POLICY = {
    "default_priority": 50,
    "default_max_retries": 1,
    "allow_client_priority": False,
    "allow_client_max_retries": False,
}

WORKER_RUNNERS: dict[str, dict[str, Any]] = {}


class ProjectCreate(BaseModel):
    name: str
    repo_url: str | None = None
    repo_path: str | None = None
    default_branch: str = "main"


class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: str
    task_type: str = "frontend_dev"
    required_role: str = "dev_worker"
    required_capabilities: list[str] = Field(default_factory=lambda: ["git"])
    required_tools: list[str] = Field(default_factory=lambda: ["git"])
    priority: int | None = None
    max_retries: int | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    validation_command: str | None = None
    created_by: str = "web_user"


class PMPlanCreate(BaseModel):
    project_id: str
    title: str
    objective: str
    created_by: str = "pm_agent"


class WorkerRegister(BaseModel):
    worker_type: str = "local_worker"
    role: str = "dev_worker"
    capabilities: list[str] = Field(default_factory=lambda: ["git", "python"])
    tools: list[str] = Field(default_factory=lambda: ["git", "terminal"])
    max_concurrency: int = 1


class WorkerRunnerStart(BaseModel):
    agent: str = "dry-run"
    worker_type: str = "managed_worker"


class RemoteAgentRegister(BaseModel):
    name: str
    agent_kind: str = "worker"
    role: str = "dev_worker"
    capabilities: list[str] = Field(default_factory=lambda: ["git"])
    tools: list[str] = Field(default_factory=lambda: ["git"])
    endpoint_url: str | None = None
    max_concurrency: int = 1


class RemoteArtifactUpload(BaseModel):
    type: str = "text"
    filename: str = "artifact.txt"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogCreate(BaseModel):
    level: str = "info"
    message: str


class CompleteSession(BaseModel):
    summary: str = ""
    validation_status: str = "not_run"
    validation_output: str = ""


class RemoteCompleteSession(CompleteSession):
    artifacts: list[RemoteArtifactUpload] = Field(default_factory=list)


class RemoteLogBatch(BaseModel):
    entries: list[LogCreate] = Field(default_factory=list)


class FailSession(BaseModel):
    reason: str


class ReviewTask(BaseModel):
    decision: str
    message: str = ""


class MergeTask(BaseModel):
    message: str = ""


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "time": now_ms()}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def model_data(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def read_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="agent_auth_required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="agent_auth_required")
    return token


def get_remote_agent(agent_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM remote_agents WHERE id = ?", (agent_id,)).fetchone()
    agent = row_to_dict(row)
    if not agent:
        raise HTTPException(status_code=404, detail="Remote agent not found")
    return agent


def require_remote_agent(agent_id: str, authorization: str | None, allowed_kinds: set[str] | None = None) -> dict[str, Any]:
    token = read_bearer_token(authorization)
    agent = get_remote_agent(agent_id)
    if agent["token_hash"] != hash_token(token):
        raise HTTPException(status_code=401, detail="agent_auth_invalid")
    if agent["status"] == "disabled":
        raise HTTPException(status_code=403, detail="agent_disabled")
    if allowed_kinds and agent["agent_kind"] not in allowed_kinds:
        raise HTTPException(status_code=403, detail="agent_kind_mismatch")
    return agent


def touch_remote_agent(agent_id: str, status: str = "online") -> None:
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            "UPDATE remote_agents SET status = ?, last_heartbeat_at = ?, updated_at = ? WHERE id = ?",
            (status, ts, ts, agent_id),
        )


def safe_artifact_filename(name: str, fallback: str) -> str:
    filename = Path(name or fallback).name.strip()
    if not filename or filename in {".", ".."}:
        filename = fallback
    return filename


def cleanup_worker_runners() -> None:
    for runner in WORKER_RUNNERS.values():
        process: subprocess.Popen[str] = runner["process"]
        runner["running"] = process.poll() is None
        runner["returncode"] = process.returncode
        if runner["returncode"] is not None and runner.get("log_file"):
            runner["log_file"].close()
            runner["log_file"] = None


def runner_to_dict(runner_id: str, runner: dict[str, Any]) -> dict[str, Any]:
    process: subprocess.Popen[str] = runner["process"]
    return {
        "id": runner_id,
        "agent": runner["agent"],
        "worker_type": runner["worker_type"],
        "pid": process.pid,
        "running": process.poll() is None,
        "returncode": process.returncode,
        "log_path": runner["log_path"],
        "started_at": runner["started_at"],
        "api_url": runner["api_url"],
    }


def reconcile_runtime() -> None:
    threshold = now_ms() - STALE_WORKER_MS
    stale_workers: list[dict[str, Any]] = []
    stale_sessions: list[dict[str, Any]] = []

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM workers
            WHERE status IN ('online', 'busy')
              AND last_heartbeat_at IS NOT NULL
              AND last_heartbeat_at < ?
            """,
            (threshold,),
        ).fetchall()
        stale_workers = rows_to_dicts(rows)

        for worker in stale_workers:
            session_id = worker.get("current_session_id")
            if session_id:
                session_row = conn.execute(
                    "SELECT * FROM sessions WHERE id = ? AND status = 'running'",
                    (session_id,),
                ).fetchone()
                session = row_to_dict(session_row)
                if session:
                    stale_sessions.append(session)
                    result = dumps({"reason": "Worker heartbeat timed out"})
                    ts = now_ms()
                    conn.execute(
                        "UPDATE sessions SET status = ?, result = ?, ended_at = ? WHERE id = ?",
                        ("failed", result, ts, session_id),
                    )

            conn.execute(
                "UPDATE workers SET status = ?, current_session_id = ?, updated_at = ? WHERE id = ?",
                ("offline", None, now_ms(), worker["id"]),
            )

    for worker in stale_workers:
        add_audit_event("runtime", "monitor", "worker.offline", "worker", worker["id"], metadata={"reason": "heartbeat_timeout"})

    for session in stale_sessions:
        transition_task_after_failure(session["task_id"], "Worker heartbeat timed out", session["id"])
        add_audit_event(
            "runtime",
            "monitor",
            "session.timeout",
            "session",
            session["id"],
            task_id=session["task_id"],
            session_id=session["id"],
        )


@app.post("/api/projects")
def create_project(payload: ProjectCreate) -> dict[str, Any]:
    project_id = new_id("proj")
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                payload.name,
                payload.repo_url,
                payload.repo_path,
                payload.default_branch,
                "active",
                ts,
                ts,
            ),
        )
    add_audit_event("user", "web_user", "project.create", "project", project_id)
    return get_project(project_id)


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    project = row_to_dict(row)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/tasks")
def create_task(payload: TaskCreate) -> dict[str, Any]:
    return create_task_record(payload)


def create_task_record(
    payload: TaskCreate,
    actor_type: str = "user",
    actor_id: str | None = None,
    plan_id: str | None = None,
    plan_sequence: int | None = None,
) -> dict[str, Any]:
    _ = get_project(payload.project_id)
    task_id = new_id("task")
    ts = now_ms()
    priority = TASK_POLICY["default_priority"]
    if TASK_POLICY["allow_client_priority"] and payload.priority is not None:
        priority = max(0, min(100, payload.priority))

    max_retries = TASK_POLICY["default_max_retries"]
    if TASK_POLICY["allow_client_max_retries"] and payload.max_retries is not None:
        max_retries = max(0, min(10, payload.max_retries))

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (
                id, project_id, plan_id, plan_sequence, title, description, task_type, required_role,
                required_capabilities, required_tools, priority, status,
                acceptance_criteria, validation_command, created_by,
                assigned_worker_id, active_session_id, created_at, updated_at,
                retry_count, max_retries
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                payload.project_id,
                plan_id,
                plan_sequence,
                payload.title,
                payload.description,
                payload.task_type,
                payload.required_role,
                dumps(payload.required_capabilities),
                dumps(payload.required_tools),
                priority,
                "queued",
                dumps(payload.acceptance_criteria),
                payload.validation_command,
                payload.created_by,
                None,
                None,
                ts,
                ts,
                0,
                max_retries,
            ),
        )
    metadata = {"title": payload.title, "plan_id": plan_id, "plan_sequence": plan_sequence}
    add_task_event(task_id, "task.created", "Task created", metadata)
    add_audit_event(actor_type, actor_id or payload.created_by, "task.create", "task", task_id, task_id=task_id, metadata=metadata)
    return get_task(task_id)


def build_pm_tasks(payload: PMPlanCreate) -> list[TaskCreate]:
    objective = payload.objective.strip()
    return [
        TaskCreate(
            project_id=payload.project_id,
            title=f"{payload.title}: scope audit",
            description=(
                "Analyze the project and objective. Identify the smallest safe implementation scope, "
                f"risks, dependencies, and files likely to change.\n\nObjective:\n{objective}"
            ),
            task_type="pm_scope",
            acceptance_criteria=[
                "Summarize project impact and implementation scope.",
                "List risks, assumptions, and validation needs.",
            ],
            created_by=payload.created_by,
        ),
        TaskCreate(
            project_id=payload.project_id,
            title=f"{payload.title}: implementation slice",
            description=(
                "Implement the first production-ready slice for the objective. Keep the change focused, "
                "follow existing project patterns, and leave reviewable artifacts.\n\nObjective:\n"
                f"{objective}"
            ),
            task_type="implementation",
            acceptance_criteria=[
                "Implement the core user-visible behavior.",
                "Keep changes scoped and compatible with the current runtime.",
            ],
            created_by=payload.created_by,
        ),
        TaskCreate(
            project_id=payload.project_id,
            title=f"{payload.title}: validation pass",
            description=(
                "Run or define validation for the implementation slice. Capture failures clearly and "
                f"recommend fixes if validation cannot run.\n\nObjective:\n{objective}"
            ),
            task_type="validation",
            acceptance_criteria=[
                "Run applicable checks or explain why they are unavailable.",
                "Report pass/fail status and remaining risks.",
            ],
            created_by=payload.created_by,
        ),
        TaskCreate(
            project_id=payload.project_id,
            title=f"{payload.title}: delivery notes",
            description=(
                "Prepare concise handoff notes for the completed slice, including what changed, how to "
                f"test it, and what should happen next.\n\nObjective:\n{objective}"
            ),
            task_type="handoff",
            acceptance_criteria=[
                "Provide a short operator-facing test flow.",
                "Document follow-up work and known limitations.",
            ],
            created_by=payload.created_by,
        ),
    ]


def sync_pm_plan_status(plan_id: str) -> None:
    ts = now_ms()
    with connect() as conn:
        task_rows = conn.execute("SELECT status FROM tasks WHERE plan_id = ?", (plan_id,)).fetchall()
        if not task_rows:
            next_status = "active"
        else:
            statuses = {row["status"] for row in task_rows}
            if statuses <= {"completed", "merged", "cancelled"} and (statuses & {"completed", "merged"}):
                next_status = "completed"
            elif statuses & {"failed", "revision_requested"}:
                next_status = "blocked"
            else:
                next_status = "active"
        conn.execute("UPDATE pm_plans SET status = ?, updated_at = ? WHERE id = ?", (next_status, ts, plan_id))


def plan_progress(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    total = len(tasks)
    done = counts.get("completed", 0) + counts.get("merged", 0)
    return {"total": total, "completed": done, "counts": counts}


@app.post("/api/pm/plans")
def create_pm_plan(payload: PMPlanCreate) -> dict[str, Any]:
    _ = get_project(payload.project_id)
    plan_id = new_id("plan")
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            "INSERT INTO pm_plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plan_id, payload.project_id, payload.title, payload.objective, "active", "", payload.created_by, ts, ts),
        )
    add_audit_event("pm_agent", payload.created_by, "pm_plan.create", "pm_plan", plan_id, metadata={"title": payload.title})

    for index, task_payload in enumerate(build_pm_tasks(payload), start=1):
        create_task_record(task_payload, actor_type="pm_agent", actor_id=plan_id, plan_id=plan_id, plan_sequence=index)

    add_audit_event("pm_agent", plan_id, "pm_plan.decompose", "pm_plan", plan_id, metadata={"task_count": 4})
    return get_pm_plan(plan_id)


@app.get("/api/pm/plans")
def list_pm_plans() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM pm_plans ORDER BY created_at DESC").fetchall()
    plans = rows_to_dicts(rows)
    return [get_pm_plan(plan["id"]) for plan in plans]


@app.get("/api/pm/plans/{plan_id}")
def get_pm_plan(plan_id: str) -> dict[str, Any]:
    sync_pm_plan_status(plan_id)
    with connect() as conn:
        plan_row = conn.execute("SELECT * FROM pm_plans WHERE id = ?", (plan_id,)).fetchone()
        task_rows = conn.execute(
            "SELECT * FROM tasks WHERE plan_id = ? ORDER BY plan_sequence ASC, created_at ASC",
            (plan_id,),
        ).fetchall()
    plan = row_to_dict(plan_row)
    if not plan:
        raise HTTPException(status_code=404, detail="PM plan not found")
    tasks = rows_to_dicts(task_rows)
    plan["tasks"] = tasks
    plan["progress"] = plan_progress(tasks)
    return plan


@app.post("/api/remote-agents/register")
def register_remote_agent(payload: RemoteAgentRegister) -> dict[str, Any]:
    if payload.agent_kind not in {"pm", "worker", "vibe", "hybrid"}:
        raise HTTPException(status_code=400, detail="agent_kind must be pm, worker, vibe, or hybrid")

    worker_id = None
    if payload.agent_kind in {"worker", "vibe", "hybrid"}:
        worker = register_worker(
            WorkerRegister(
                worker_type=f"remote_{payload.agent_kind}",
                role=payload.role,
                capabilities=payload.capabilities,
                tools=payload.tools,
                max_concurrency=payload.max_concurrency,
            )
        )
        worker_id = worker["id"]

    agent_id = new_id("agent")
    token = secrets.token_urlsafe(32)
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO remote_agents (
                id, name, agent_kind, status, role, capabilities, tools,
                token_hash, worker_id, endpoint_url, last_heartbeat_at,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                payload.name,
                payload.agent_kind,
                "online",
                payload.role,
                dumps(payload.capabilities),
                dumps(payload.tools),
                hash_token(token),
                worker_id,
                payload.endpoint_url,
                ts,
                ts,
                ts,
            ),
        )
    add_audit_event("remote_agent", agent_id, "remote_agent.register", "remote_agent", agent_id, metadata={"agent_kind": payload.agent_kind})
    agent = get_remote_agent(agent_id)
    agent.pop("token_hash", None)
    agent["token"] = token
    return agent


@app.get("/api/remote-agents")
def list_remote_agents() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM remote_agents ORDER BY created_at DESC").fetchall()
    agents = rows_to_dicts(rows)
    for agent in agents:
        agent.pop("token_hash", None)
    return agents


@app.get("/api/remote-agents/{agent_id}")
def get_remote_agent_public(agent_id: str) -> dict[str, Any]:
    agent = get_remote_agent(agent_id)
    agent.pop("token_hash", None)
    return agent


@app.post("/api/remote-agents/{agent_id}/disable")
def disable_remote_agent(agent_id: str) -> dict[str, Any]:
    agent = get_remote_agent(agent_id)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE remote_agents SET status = ?, updated_at = ? WHERE id = ?", ("disabled", ts, agent_id))
    if agent.get("worker_id"):
        disable_worker(agent["worker_id"])
    add_audit_event("user", "web_user", "remote_agent.disable", "remote_agent", agent_id)
    return get_remote_agent_public(agent_id)


@app.post("/api/remote-agents/{agent_id}/enable")
def enable_remote_agent(agent_id: str) -> dict[str, Any]:
    agent = get_remote_agent(agent_id)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE remote_agents SET status = ?, updated_at = ? WHERE id = ?", ("online", ts, agent_id))
    if agent.get("worker_id"):
        enable_worker(agent["worker_id"])
    add_audit_event("user", "web_user", "remote_agent.enable", "remote_agent", agent_id)
    return get_remote_agent_public(agent_id)


@app.post("/api/remote-agents/{agent_id}/rotate-token")
def rotate_remote_agent_token(agent_id: str) -> dict[str, Any]:
    _ = get_remote_agent(agent_id)
    token = secrets.token_urlsafe(32)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE remote_agents SET token_hash = ?, updated_at = ? WHERE id = ?", (hash_token(token), ts, agent_id))
    add_audit_event("user", "web_user", "remote_agent.rotate_token", "remote_agent", agent_id)
    agent = get_remote_agent_public(agent_id)
    agent["token"] = token
    return agent


@app.post("/api/remote-agents/{agent_id}/heartbeat")
def remote_agent_heartbeat(agent_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    agent = require_remote_agent(agent_id, authorization)
    touch_remote_agent(agent_id)
    if agent.get("worker_id"):
        worker_heartbeat(agent["worker_id"])
    add_audit_event("remote_agent", agent_id, "remote_agent.heartbeat", "remote_agent", agent_id)
    return {"ok": True, "time": now_ms(), "status": "online"}


@app.post("/api/remote-agents/{agent_id}/pm/plans")
def remote_agent_create_plan(agent_id: str, payload: PMPlanCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_remote_agent(agent_id, authorization, {"pm", "hybrid"})
    data = model_data(payload)
    data["created_by"] = agent_id
    plan = create_pm_plan(PMPlanCreate(**data))
    add_audit_event("remote_agent", agent_id, "remote_agent.pm_plan.create", "pm_plan", plan["id"])
    return plan


@app.post("/api/remote-agents/{agent_id}/tasks")
def remote_agent_create_task(agent_id: str, payload: TaskCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_remote_agent(agent_id, authorization, {"pm", "vibe", "hybrid"})
    data = model_data(payload)
    data["created_by"] = agent_id
    return create_task_record(TaskCreate(**data), actor_type="remote_agent", actor_id=agent_id)


@app.post("/api/remote-agents/{agent_id}/pm/plans/{plan_id}/tasks")
def remote_agent_create_plan_task(agent_id: str, plan_id: str, payload: TaskCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_remote_agent(agent_id, authorization, {"pm", "hybrid"})
    plan = get_pm_plan(plan_id)
    data = model_data(payload)
    data["project_id"] = plan["project_id"]
    data["created_by"] = agent_id
    with connect() as conn:
        row = conn.execute("SELECT MAX(plan_sequence) AS max_sequence FROM tasks WHERE plan_id = ?", (plan_id,)).fetchone()
    sequence = int(row["max_sequence"] or 0) + 1
    task = create_task_record(TaskCreate(**data), actor_type="remote_agent", actor_id=agent_id, plan_id=plan_id, plan_sequence=sequence)
    sync_pm_plan_status(plan_id)
    return task


@app.post("/api/remote-agents/{agent_id}/claim")
def remote_agent_claim_task(agent_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    agent = require_remote_agent(agent_id, authorization, {"worker", "vibe", "hybrid"})
    worker_id = agent.get("worker_id")
    if not worker_id:
        raise HTTPException(status_code=400, detail="agent_has_no_worker")
    touch_remote_agent(agent_id)
    claim = claim_task(worker_id)
    if claim.get("claimed"):
        add_audit_event("remote_agent", agent_id, "remote_agent.task.claim", "task", claim["task"]["id"], task_id=claim["task"]["id"], session_id=claim["session"]["id"])
    return claim


def require_remote_session(agent: dict[str, Any], session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not agent.get("worker_id") or session["worker_id"] != agent["worker_id"]:
        raise HTTPException(status_code=403, detail="session_not_owned_by_agent")
    return session


def write_remote_artifacts(task_id: str, session_id: str, artifacts: list[RemoteArtifactUpload]) -> list[dict[str, Any]]:
    artifact_dir = workspace.make_artifact_dir(task_id, session_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    for index, artifact in enumerate(artifacts, start=1):
        filename = safe_artifact_filename(artifact.filename, f"artifact_{index}.txt")
        path = artifact_dir / filename
        path.write_text(artifact.content, encoding="utf-8")
        metadata = dict(artifact.metadata)
        metadata["bytes"] = len(artifact.content.encode("utf-8"))
        metadata["remote_uploaded"] = True
        written.append({"type": artifact.type, "uri": str(path), "metadata": metadata})
    return written


def complete_session_with_artifacts(session_id: str, payload: CompleteSession, extra_artifacts: list[dict[str, Any]] | None = None, collect_workspace: bool = True) -> dict[str, Any]:
    session = get_session(session_id)
    artifacts: list[dict[str, Any]] = []
    if collect_workspace:
        artifact_dir = workspace.make_artifact_dir(session["task_id"], session_id)
        artifacts.extend(workspace.collect_artifacts(session["workspace_path"], artifact_dir))
    artifacts.extend(extra_artifacts or [])
    ts = now_ms()
    result = {
        "summary": payload.summary,
        "validation_status": payload.validation_status,
        "validation_output": payload.validation_output,
    }
    worker = get_worker(session["worker_id"])
    next_worker_status = "disabled" if worker["status"] == "draining" else "online"
    with connect() as conn:
        conn.execute("UPDATE sessions SET status = ?, result = ?, ended_at = ? WHERE id = ?", ("completed", dumps(result), ts, session_id))
        conn.execute("UPDATE workers SET status = ?, current_session_id = ?, updated_at = ? WHERE id = ?", (next_worker_status, None, ts, session["worker_id"]))
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("waiting_review", ts, session["task_id"]))
        for item in artifacts:
            conn.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id("art"),
                    session["task_id"],
                    session_id,
                    item["type"],
                    item["uri"],
                    dumps(item["metadata"]),
                    ts,
                ),
            )
    add_task_event(session["task_id"], "task.waiting_review", "Worker completed session; waiting for review", result)
    add_audit_event("worker", session["worker_id"], "session.complete", "session", session_id, task_id=session["task_id"], session_id=session_id, metadata=result)
    task = get_task(session["task_id"])
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])
    return task


@app.post("/api/remote-agents/{agent_id}/sessions/{session_id}/logs")
def remote_agent_add_session_logs(agent_id: str, session_id: str, payload: RemoteLogBatch, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    agent = require_remote_agent(agent_id, authorization, {"worker", "vibe", "hybrid"})
    session = require_remote_session(agent, session_id)
    entries = payload.entries or []
    ts = now_ms()
    with connect() as conn:
        for entry in entries:
            conn.execute("INSERT INTO session_logs VALUES (?, ?, ?, ?, ?)", (new_id("log"), session_id, entry.level, entry.message, ts))
        conn.execute("UPDATE sessions SET last_heartbeat_at = ? WHERE id = ?", (ts, session_id))
    touch_remote_agent(agent_id)
    add_audit_event("remote_agent", agent_id, "remote_agent.session.logs", "session", session_id, task_id=session["task_id"], session_id=session_id, metadata={"count": len(entries)})
    return {"ok": True, "count": len(entries), "time": ts}


@app.post("/api/remote-agents/{agent_id}/sessions/{session_id}/complete")
def remote_agent_complete_session(agent_id: str, session_id: str, payload: RemoteCompleteSession, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    agent = require_remote_agent(agent_id, authorization, {"worker", "vibe", "hybrid"})
    session = require_remote_session(agent, session_id)
    uploaded = write_remote_artifacts(session["task_id"], session_id, payload.artifacts)
    touch_remote_agent(agent_id)
    add_audit_event("remote_agent", agent_id, "remote_agent.session.complete", "session", session_id, task_id=session["task_id"], session_id=session_id, metadata={"artifacts": len(uploaded)})
    return complete_session_with_artifacts(session_id, payload, extra_artifacts=uploaded, collect_workspace=False)


@app.post("/api/remote-agents/{agent_id}/sessions/{session_id}/fail")
def remote_agent_fail_session(agent_id: str, session_id: str, payload: FailSession, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    agent = require_remote_agent(agent_id, authorization, {"worker", "vibe", "hybrid"})
    session = require_remote_session(agent, session_id)
    touch_remote_agent(agent_id)
    add_audit_event("remote_agent", agent_id, "remote_agent.session.fail", "session", session_id, task_id=session["task_id"], session_id=session_id)
    return fail_session(session_id, payload)


@app.get("/api/tasks")
def list_tasks(status: str | None = None, project_id: str | None = None, plan_id: str | None = None) -> list[dict[str, Any]]:
    reconcile_runtime()
    query = "SELECT * FROM tasks"
    params: list[Any] = []
    clauses: list[str] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if project_id:
        clauses.append("project_id = ?")
        params.append(project_id)
    if plan_id:
        clauses.append("plan_id = ?")
        params.append(plan_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY priority DESC, created_at ASC"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    with connect() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        events = conn.execute("SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at ASC", (task_id,)).fetchall()
        artifacts = conn.execute("SELECT * FROM artifacts WHERE task_id = ? ORDER BY created_at DESC", (task_id,)).fetchall()
    task = row_to_dict(task_row)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task["events"] = rows_to_dicts(events)
    task["artifacts"] = rows_to_dicts(artifacts)
    return task


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str) -> dict[str, Any]:
    task = get_task(task_id)
    if task["status"] in {"completed", "cancelled"}:
        return task
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("cancelled", ts, task_id))
    add_task_event(task_id, "task.cancelled", "Task cancelled")
    add_audit_event("user", "web_user", "task.cancel", "task", task_id, task_id=task_id)
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str) -> dict[str, Any]:
    task = get_task(task_id)
    if task["status"] in {"queued", "running"}:
        raise HTTPException(status_code=400, detail="Task is already queued or running")
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, assigned_worker_id = ?, active_session_id = ?, retry_count = ?, updated_at = ?
            WHERE id = ?
            """,
            ("queued", None, None, 0, ts, task_id),
        )
    add_task_event(task_id, "task.retried", "Task returned to queue")
    add_audit_event("user", "web_user", "task.retry", "task", task_id, task_id=task_id)
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/review")
def review_task(task_id: str, payload: ReviewTask) -> dict[str, Any]:
    task = get_task(task_id)
    if payload.decision not in {"complete", "revision_requested"}:
        raise HTTPException(status_code=400, detail="decision must be complete or revision_requested")
    next_status = "completed" if payload.decision == "complete" else "revision_requested"
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (next_status, ts, task_id))
    add_task_event(task_id, f"task.{next_status}", payload.message or next_status)
    add_audit_event("reviewer", "web_user", f"task.review.{payload.decision}", "task", task_id, task_id=task_id)
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/merge")
def merge_task(task_id: str, payload: MergeTask) -> dict[str, Any]:
    task = get_task(task_id)
    if task["status"] not in {"waiting_review", "completed"}:
        raise HTTPException(status_code=400, detail="Task must be waiting_review or completed before merge")
    sessions = list_task_sessions(task_id)
    if not sessions:
        raise HTTPException(status_code=400, detail="Task has no sessions to merge")
    session = sessions[0]
    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail="Latest session is not completed")
    project = get_project(task["project_id"])
    message = payload.message or f"AI Runtime OS merge: {task['title']}"
    try:
        result = workspace.merge_session_workspace(project, session, message)
    except Exception as exc:
        add_task_event(task_id, "task.merge_failed", str(exc), {"session_id": session["id"]})
        raise HTTPException(status_code=409, detail=f"Merge failed: {exc}") from exc

    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ("merged", ts, task_id))
    add_task_event(task_id, "task.merged", "Task merged into project repository", result)
    add_audit_event("reviewer", "web_user", "task.merge", "task", task_id, task_id=task_id, session_id=session["id"], metadata=result)
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])
    return get_task(task_id)


@app.post("/api/workers/register")
def register_worker(payload: WorkerRegister) -> dict[str, Any]:
    worker_id = new_id("worker")
    ts = now_ms()
    with connect() as conn:
        conn.execute(
            "INSERT INTO workers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                worker_id,
                payload.worker_type,
                payload.role,
                "online",
                dumps(payload.capabilities),
                dumps(payload.tools),
                payload.max_concurrency,
                None,
                ts,
                ts,
                ts,
            ),
        )
    add_audit_event("worker", worker_id, "worker.register", "worker", worker_id)
    return get_worker(worker_id)


@app.get("/api/workers")
def list_workers() -> list[dict[str, Any]]:
    reconcile_runtime()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM workers ORDER BY created_at DESC").fetchall()
    return rows_to_dicts(rows)


@app.get("/api/workers/{worker_id}")
def get_worker(worker_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    worker = row_to_dict(row)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@app.post("/api/workers/{worker_id}/heartbeat")
def worker_heartbeat(worker_id: str) -> dict[str, Any]:
    worker = get_worker(worker_id)
    ts = now_ms()
    next_status = "online"
    if worker["status"] == "disabled":
        next_status = "disabled"
    elif worker["status"] == "draining":
        next_status = "draining" if worker.get("current_session_id") else "disabled"
    elif worker["status"] == "busy" and worker.get("current_session_id"):
        next_status = "busy"
    with connect() as conn:
        conn.execute("UPDATE workers SET status = ?, last_heartbeat_at = ?, updated_at = ? WHERE id = ?", (next_status, ts, ts, worker_id))
    return {"ok": True, "time": ts, "status": next_status}


@app.post("/api/workers/{worker_id}/disable")
def disable_worker(worker_id: str) -> dict[str, Any]:
    worker = get_worker(worker_id)
    if worker.get("current_session_id"):
        return drain_worker(worker_id)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE workers SET status = ?, updated_at = ? WHERE id = ?", ("disabled", ts, worker_id))
    add_audit_event("user", "web_user", "worker.disable", "worker", worker_id)
    return get_worker(worker_id)


@app.post("/api/workers/{worker_id}/enable")
def enable_worker(worker_id: str) -> dict[str, Any]:
    _ = get_worker(worker_id)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE workers SET status = ?, updated_at = ? WHERE id = ?", ("online", ts, worker_id))
    add_audit_event("user", "web_user", "worker.enable", "worker", worker_id)
    return get_worker(worker_id)


@app.post("/api/workers/{worker_id}/drain")
def drain_worker(worker_id: str) -> dict[str, Any]:
    _ = get_worker(worker_id)
    ts = now_ms()
    with connect() as conn:
        conn.execute("UPDATE workers SET status = ?, updated_at = ? WHERE id = ?", ("draining", ts, worker_id))
    add_audit_event("user", "web_user", "worker.drain", "worker", worker_id)
    return get_worker(worker_id)


@app.get("/api/worker-runners")
def list_worker_runners() -> list[dict[str, Any]]:
    cleanup_worker_runners()
    return [runner_to_dict(runner_id, runner) for runner_id, runner in WORKER_RUNNERS.items()]


@app.post("/api/worker-runners/start")
def start_worker_runner(payload: WorkerRunnerStart, request: Request) -> dict[str, Any]:
    if payload.agent not in {"dry-run", "fail-test", "claude-deepseek", "kimi-code", "opencode"}:
        raise HTTPException(status_code=400, detail="Unsupported agent")

    cleanup_worker_runners()
    runner_id = new_id("runner")
    api_url = str(request.base_url).rstrip("/")
    log_dir = RUNTIME_ROOT / "runner-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{runner_id}.log"
    log_file = log_path.open("w", encoding="utf-8")
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT))
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [
            sys.executable,
            str(PROJECT_ROOT / "workers" / "local_worker.py"),
            "--api",
            api_url,
            "--agent",
            payload.agent,
            "--worker-type",
            payload.worker_type,
            "--poll-interval",
            "1",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    WORKER_RUNNERS[runner_id] = {
        "process": process,
        "agent": payload.agent,
        "worker_type": payload.worker_type,
        "log_path": str(log_path),
        "started_at": now_ms(),
        "api_url": api_url,
        "log_file": log_file,
    }
    add_audit_event("user", "web_user", "worker_runner.start", "worker_runner", runner_id, metadata={"agent": payload.agent})
    return runner_to_dict(runner_id, WORKER_RUNNERS[runner_id])


@app.post("/api/worker-runners/{runner_id}/stop")
def stop_worker_runner(runner_id: str) -> dict[str, Any]:
    runner = WORKER_RUNNERS.get(runner_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Runner not found")
    process: subprocess.Popen[str] = runner["process"]
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    if runner.get("log_file"):
        runner["log_file"].close()
        runner["log_file"] = None
    runner["running"] = process.poll() is None
    runner["returncode"] = process.returncode
    add_audit_event("user", "web_user", "worker_runner.stop", "worker_runner", runner_id)
    return runner_to_dict(runner_id, runner)


@app.post("/api/workers/{worker_id}/claim")
def claim_task(worker_id: str) -> dict[str, Any]:
    reconcile_runtime()
    worker = get_worker(worker_id)
    if worker["status"] != "online":
        return {"claimed": False, "reason": f"worker_{worker['status']}"}
    if worker["current_session_id"]:
        return {"claimed": False, "reason": "worker_busy"}

    with connect() as conn:
        task_rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC"
        ).fetchall()

    for row in task_rows:
        task = row_to_dict(row)
        if not task:
            continue
        if task["required_role"] != worker["role"]:
            continue
        if not set(task["required_capabilities"]).issubset(set(worker["capabilities"])):
            continue
        if not set(task["required_tools"]).issubset(set(worker["tools"])):
            continue
        return assign_task(task, worker)

    return {"claimed": False, "reason": "no_matching_task"}


def assign_task(task: dict[str, Any], worker: dict[str, Any]) -> dict[str, Any]:
    project = get_project(task["project_id"])
    session_id = new_id("sess")
    try:
        ws = workspace.create_session_workspace(project, task["id"], session_id)
    except Exception as exc:
        add_task_event(task["id"], "task.workspace_failed", str(exc))
        raise HTTPException(status_code=500, detail=f"Workspace error: {exc}") from exc

    ts = now_ms()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                task["id"],
                task["project_id"],
                worker["id"],
                "running",
                ws["workspace_path"],
                ws["base_commit"],
                ws["branch_name"],
                "{}",
                ts,
                None,
                ts,
            ),
        )
        conn.execute(
            "UPDATE tasks SET status = ?, assigned_worker_id = ?, active_session_id = ?, updated_at = ? WHERE id = ?",
            ("running", worker["id"], session_id, ts, task["id"]),
        )
        conn.execute(
            "UPDATE workers SET status = ?, current_session_id = ?, updated_at = ? WHERE id = ?",
            ("busy", session_id, ts, worker["id"]),
        )

    add_task_event(task["id"], "task.assigned", f"Assigned to {worker['id']}", {"session_id": session_id})
    add_audit_event("runtime", "scheduler", "task.assign", "task", task["id"], task_id=task["id"], session_id=session_id)
    return {"claimed": True, "task": get_task(task["id"]), "session": get_session(session_id), "project": project}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        logs = conn.execute("SELECT * FROM session_logs WHERE session_id = ? ORDER BY created_at ASC", (session_id,)).fetchall()
    session = row_to_dict(row)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["logs"] = rows_to_dicts(logs)
    return session


@app.get("/api/tasks/{task_id}/sessions")
def list_task_sessions(task_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM sessions WHERE task_id = ? ORDER BY started_at DESC", (task_id,)).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/sessions/{session_id}/logs")
def add_session_log(session_id: str, payload: LogCreate) -> dict[str, Any]:
    session = get_session(session_id)
    log_id = new_id("log")
    ts = now_ms()
    with connect() as conn:
        conn.execute("INSERT INTO session_logs VALUES (?, ?, ?, ?, ?)", (log_id, session_id, payload.level, payload.message, ts))
        conn.execute("UPDATE sessions SET last_heartbeat_at = ? WHERE id = ?", (ts, session_id))
    add_audit_event("worker", session["worker_id"], "session.log", "session", session_id, task_id=session["task_id"], session_id=session_id)
    return {"id": log_id, "created_at": ts}


@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: str, payload: CompleteSession) -> dict[str, Any]:
    return complete_session_with_artifacts(session_id, payload)


@app.post("/api/sessions/{session_id}/fail")
def fail_session(session_id: str, payload: FailSession) -> dict[str, Any]:
    session = get_session(session_id)
    ts = now_ms()
    result = {"reason": payload.reason}
    with connect() as conn:
        conn.execute("UPDATE sessions SET status = ?, result = ?, ended_at = ? WHERE id = ?", ("failed", dumps(result), ts, session_id))
        conn.execute("UPDATE workers SET status = ?, current_session_id = ?, updated_at = ? WHERE id = ?", ("online", None, ts, session["worker_id"]))
    transition_task_after_failure(session["task_id"], payload.reason, session_id)
    add_audit_event("worker", session["worker_id"], "session.fail", "session", session_id, task_id=session["task_id"], session_id=session_id, metadata=result)
    return get_task(session["task_id"])


def transition_task_after_failure(task_id: str, reason: str, session_id: str | None = None) -> None:
    ts = now_ms()
    with connect() as conn:
        row = conn.execute("SELECT retry_count, max_retries FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return
        retry_count = row["retry_count"] or 0
        max_retries = row["max_retries"] or 0
        if retry_count < max_retries:
            next_retry_count = retry_count + 1
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, retry_count = ?, assigned_worker_id = ?, active_session_id = ?, updated_at = ?
                WHERE id = ?
                """,
                ("queued", next_retry_count, None, None, ts, task_id),
            )
            event_type = "task.auto_retried"
            message = f"{reason}; auto retry {next_retry_count}/{max_retries}"
        else:
            conn.execute(
                "UPDATE tasks SET status = ?, assigned_worker_id = ?, active_session_id = ?, updated_at = ? WHERE id = ?",
                ("failed", None, None, ts, task_id),
            )
            event_type = "task.failed"
            message = reason

    add_task_event(task_id, event_type, message, {"session_id": session_id, "reason": reason})
    task = get_task(task_id)
    if task.get("plan_id"):
        sync_pm_plan_status(task["plan_id"])


@app.get("/api/artifacts/{artifact_id}")
def get_artifact(artifact_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    artifact = row_to_dict(row)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = Path(artifact["uri"])
    artifact["content"] = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return artifact


@app.get("/api/audit-events")
def list_audit_events() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 200").fetchall()
    return rows_to_dicts(rows)


@app.get("/api/runtime/status")
def runtime_status() -> dict[str, Any]:
    reconcile_runtime()
    with connect() as conn:
        task_rows = conn.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status").fetchall()
        worker_rows = conn.execute("SELECT status, COUNT(*) AS count FROM workers GROUP BY status").fetchall()
        session_rows = conn.execute("SELECT status, COUNT(*) AS count FROM sessions GROUP BY status").fetchall()
        plan_rows = conn.execute("SELECT status, COUNT(*) AS count FROM pm_plans GROUP BY status").fetchall()
        remote_agent_rows = conn.execute("SELECT status, COUNT(*) AS count FROM remote_agents GROUP BY status").fetchall()
    return {
        "time": now_ms(),
        "tasks": {row["status"]: row["count"] for row in task_rows},
        "workers": {row["status"]: row["count"] for row in worker_rows},
        "sessions": {row["status"]: row["count"] for row in session_rows},
        "plans": {row["status"]: row["count"] for row in plan_rows},
        "remote_agents": {row["status"]: row["count"] for row in remote_agent_rows},
        "stale_worker_ms": STALE_WORKER_MS,
        "task_policy": TASK_POLICY,
    }
