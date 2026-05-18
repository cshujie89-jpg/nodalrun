from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime_core.remote_client import RemotePMClient


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 10,
    headers: dict[str, str] | None = None,
) -> Any:
    data = None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{base_url}{path}", data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {path} failed: {exc.code} {body}") from exc


def wait_for_api(base_url: str, process: subprocess.Popen[str]) -> None:
    for _ in range(60):
        if process.poll() is not None:
            raise AssertionError(f"API exited early with code {process.returncode}")
        try:
            health = request_json("GET", base_url, "/health")
            if health.get("ok"):
                return
        except Exception:
            time.sleep(0.25)
    raise AssertionError("API did not become healthy")


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def create_demo_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("# Smoke Demo\n", encoding="utf-8")
    (path / "app.txt").write_text("hello smoke\n", encoding="utf-8")
    init = run(["git", "init", "-b", "main"], cwd=path, check=False)
    if init.returncode != 0:
        run(["git", "init"], cwd=path)
        run(["git", "checkout", "-b", "main"], cwd=path)
    run(["git", "add", "."], cwd=path)
    run(["git", "-c", "user.email=smoke@example.test", "-c", "user.name=Smoke Test", "commit", "-m", "Initial smoke repo"], cwd=path)


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value: Any, label: str) -> None:
    if not value:
        raise AssertionError(label)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def worker_command(agent: str, base_url: str) -> list[str]:
    return [sys.executable, str(ROOT / "workers" / "local_worker.py"), "--api", base_url, "--agent", agent, "--once"]


def remote_worker_command(base_url: str, agent_id: str, token: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "workers" / "remote_worker.py"),
        "--api",
        base_url,
        "--agent-id",
        agent_id,
        "--token",
        token,
        "--agent",
        "artifact-only",
        "--once",
    ]


def run_smoke(keep_runtime: bool = False) -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="ai-runtime-smoke-"))
    runtime_root = temp_root / "runtime"
    demo_repo = temp_root / "demo-repo"
    create_demo_repo(demo_repo)

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["RUNTIME_ROOT"] = str(runtime_root)
    env["PYTHONPATH"] = str(ROOT)
    runner_id: str | None = None
    api_log_path = temp_root / "api.log"
    api_log = api_log_path.open("w", encoding="utf-8")

    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=api_log,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_api(base_url, api_process)
        print(f"[ok] API healthy at {base_url}")

        project = request_json(
            "POST",
            base_url,
            "/api/projects",
            {"name": "smoke-demo", "repo_path": str(demo_repo), "default_branch": "main"},
        )
        assert_true(project["id"].startswith("proj_"), "Project id should be generated")
        print(f"[ok] project created: {project['id']}")

        policy_task = request_json(
            "POST",
            base_url,
            "/api/tasks",
            {
                "project_id": project["id"],
                "title": "policy override should be ignored",
                "description": "Verify central policy ignores caller priority and retry overrides.",
                "priority": 100,
                "max_retries": 9,
            },
        )
        assert_equal(policy_task["priority"], 50, "Runtime policy priority")
        assert_equal(policy_task["max_retries"], 1, "Runtime policy max_retries")
        request_json("POST", base_url, f"/api/tasks/{policy_task['id']}/cancel")
        print("[ok] central task policy enforced")

        worker = request_json(
            "POST",
            base_url,
            "/api/workers/register",
            {
                "worker_type": "smoke_worker",
                "role": "dev_worker",
                "capabilities": ["git", "python", "nodejs"],
                "tools": ["git", "terminal", "node", "browser"],
                "max_concurrency": 1,
            },
        )
        disabled = request_json("POST", base_url, f"/api/workers/{worker['id']}/disable")
        assert_equal(disabled["status"], "disabled", "Disabled worker status")
        claim = request_json("POST", base_url, f"/api/workers/{worker['id']}/claim")
        assert_equal(claim["reason"], "worker_disabled", "Disabled worker cannot claim")
        enabled = request_json("POST", base_url, f"/api/workers/{worker['id']}/enable")
        assert_equal(enabled["status"], "online", "Enabled worker status")
        print("[ok] worker enable/disable controls")

        task = request_json(
            "POST",
            base_url,
            "/api/tasks",
            {
                "project_id": project["id"],
                "title": "smoke retry and artifact task",
                "description": "Verify fail-test auto retry and dry-run artifact delivery.",
                "acceptance_criteria": ["auto retry once", "dry-run creates diff artifact"],
            },
        )

        first_fail = run(worker_command("fail-test", base_url), cwd=ROOT, env=env, check=False)
        assert_true(first_fail.returncode != 0, "fail-test worker should exit non-zero")
        after_first_fail = request_json("GET", base_url, f"/api/tasks/{task['id']}")
        assert_equal(after_first_fail["status"], "queued", "Task should be queued after first auto retry")
        assert_equal(after_first_fail["retry_count"], 1, "Task retry_count after first failure")
        print("[ok] automatic retry after first failure")

        second_fail = run(worker_command("fail-test", base_url), cwd=ROOT, env=env, check=False)
        assert_true(second_fail.returncode != 0, "second fail-test worker should exit non-zero")
        after_second_fail = request_json("GET", base_url, f"/api/tasks/{task['id']}")
        assert_equal(after_second_fail["status"], "failed", "Task should fail after retries exhausted")
        print("[ok] retry exhaustion moves task to failed")

        retried = request_json("POST", base_url, f"/api/tasks/{task['id']}/retry")
        assert_equal(retried["status"], "queued", "Manual retry returns task to queue")
        assert_equal(retried["retry_count"], 0, "Manual retry resets retry_count")
        dry_run = run(worker_command("dry-run", base_url), cwd=ROOT, env=env)
        assert_true("Dry-run artifact created" in dry_run.stdout, "dry-run worker should create artifact")

        delivered = request_json("GET", base_url, f"/api/tasks/{task['id']}")
        assert_equal(delivered["status"], "waiting_review", "Dry-run should move task to waiting_review")
        diff_artifacts = [artifact for artifact in delivered["artifacts"] if artifact["type"] == "git_diff"]
        assert_true(diff_artifacts, "Task should have a git_diff artifact")
        diff = request_json("GET", base_url, f"/api/artifacts/{diff_artifacts[0]['id']}")
        assert_true("RUNTIME_WORKER_RESULT.md" in diff["content"], "Diff should include dry-run result file")
        print("[ok] dry-run worker produced reviewable diff artifact")

        completed = request_json("POST", base_url, f"/api/tasks/{task['id']}/review", {"decision": "complete", "message": "smoke ok"})
        assert_equal(completed["status"], "completed", "Review complete should complete task")
        print("[ok] review completion")

        merge_candidate = request_json(
            "POST",
            base_url,
            "/api/tasks",
            {
                "project_id": project["id"],
                "title": "smoke merge task",
                "description": "Verify reviewable git worktree changes can be merged into the project repo.",
            },
        )
        merge_worker = run(worker_command("dry-run", base_url), cwd=ROOT, env=env)
        assert_true("Dry-run artifact created" in merge_worker.stdout, "merge dry-run worker should create artifact")
        merge_ready = request_json("GET", base_url, f"/api/tasks/{merge_candidate['id']}")
        assert_equal(merge_ready["status"], "waiting_review", "Merge candidate should wait for review")
        merged = request_json("POST", base_url, f"/api/tasks/{merge_candidate['id']}/merge", {"message": "Smoke merge task"})
        assert_equal(merged["status"], "merged", "Merge endpoint should mark task merged")
        assert_true((demo_repo / "RUNTIME_WORKER_RESULT.md").exists(), "Merge should update project repository")
        print("[ok] review merge into project repo")

        stale_worker = request_json(
            "POST",
            base_url,
            "/api/workers/register",
            {"worker_type": "stale_worker", "role": "dev_worker", "capabilities": ["git"], "tools": ["git"]},
        )
        db_path = runtime_root / "runtime.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE workers SET last_heartbeat_at = ? WHERE id = ?", (0, stale_worker["id"]))
        request_json("GET", base_url, "/api/runtime/status")
        stale_after = request_json("GET", base_url, f"/api/workers/{stale_worker['id']}")
        assert_equal(stale_after["status"], "offline", "Stale worker should be reconciled offline")
        print("[ok] stale worker reconciliation")

        managed_task = request_json(
            "POST",
            base_url,
            "/api/tasks",
            {
                "project_id": project["id"],
                "title": "managed runner task",
                "description": "Verify API-managed worker runner processes queued tasks.",
            },
        )
        runner = request_json("POST", base_url, "/api/worker-runners/start", {"agent": "dry-run", "worker_type": "smoke_managed"})
        runner_id = runner["id"]
        assert_true(runner["running"], "Managed runner should start")
        deadline = time.time() + 20
        managed_delivered = None
        while time.time() < deadline:
            managed_delivered = request_json("GET", base_url, f"/api/tasks/{managed_task['id']}", timeout=3)
            if managed_delivered["status"] == "waiting_review":
                break
            time.sleep(0.5)
        assert_true(managed_delivered and managed_delivered["status"] == "waiting_review", "Managed runner should deliver task")
        stopped = request_json("POST", base_url, f"/api/worker-runners/{runner['id']}/stop")
        assert_true(not stopped["running"], "Managed runner should stop")
        print("[ok] managed worker runner start/stop")

        plan = request_json(
            "POST",
            base_url,
            "/api/pm/plans",
            {
                "project_id": project["id"],
                "title": "smoke pm plan",
                "objective": "Verify PM plan decomposition creates executable child tasks.",
            },
        )
        assert_equal(plan["status"], "active", "New PM plan should be active")
        assert_equal(plan["progress"]["total"], 4, "PM plan should create four child tasks")
        plan_tasks = request_json("GET", base_url, f"/api/tasks?plan_id={plan['id']}")
        assert_equal(len(plan_tasks), 4, "PM plan task filter should return four child tasks")
        assert_true(all(task["plan_id"] == plan["id"] for task in plan_tasks), "Child tasks should be linked to plan")
        print("[ok] PM plan decomposition")

        remote_pm = request_json(
            "POST",
            base_url,
            "/api/remote-agents/register",
            {"name": "smoke-remote-pm", "agent_kind": "pm", "capabilities": ["planning"], "tools": ["api"]},
        )
        assert_true(remote_pm.get("token"), "Remote PM registration should return one-time token")
        assert_true("token_hash" not in remote_pm, "Remote registration should not expose token hash")
        try:
            request_json(
                "POST",
                base_url,
                f"/api/remote-agents/{remote_pm['id']}/tasks",
                {"project_id": project["id"], "title": "unauthorized remote task", "description": "should fail"},
            )
            raise AssertionError("Remote agent endpoint should require auth")
        except AssertionError as exc:
            assert_true("401" in str(exc), "Missing remote token should return 401")

        remote_worker = request_json(
            "POST",
            base_url,
            "/api/remote-agents/register",
            {
                "name": "smoke-remote-worker",
                "agent_kind": "worker",
                "role": "remote_worker",
                "capabilities": ["git"],
                "tools": ["git"],
            },
        )
        remote_task = request_json(
            "POST",
            base_url,
            f"/api/remote-agents/{remote_pm['id']}/tasks",
            {
                "project_id": project["id"],
                "title": "remote worker artifact task",
                "description": "Verify remote worker can claim and upload artifacts.",
                "required_role": "remote_worker",
                "required_capabilities": ["git"],
                "required_tools": ["git"],
            },
            headers=auth_headers(remote_pm["token"]),
        )
        claim = request_json(
            "POST",
            base_url,
            f"/api/remote-agents/{remote_worker['id']}/claim",
            headers=auth_headers(remote_worker["token"]),
        )
        assert_true(claim.get("claimed"), "Remote worker should claim matching task")
        assert_equal(claim["task"]["id"], remote_task["id"], "Remote worker should claim remote task")
        session_id = claim["session"]["id"]
        request_json(
            "POST",
            base_url,
            f"/api/remote-agents/{remote_worker['id']}/sessions/{session_id}/logs",
            {"entries": [{"level": "info", "message": "remote worker smoke log"}]},
            headers=auth_headers(remote_worker["token"]),
        )
        remote_done = request_json(
            "POST",
            base_url,
            f"/api/remote-agents/{remote_worker['id']}/sessions/{session_id}/complete",
            {
                "summary": "remote worker completed",
                "validation_status": "passed",
                "validation_output": "remote smoke ok",
                "artifacts": [
                    {
                        "type": "remote_patch",
                        "filename": "remote.patch",
                        "content": "diff --git a/remote.txt b/remote.txt\nnew file mode 100644\n",
                    }
                ],
            },
            headers=auth_headers(remote_worker["token"]),
        )
        assert_equal(remote_done["status"], "waiting_review", "Remote complete should move task to waiting_review")
        remote_artifacts = [artifact for artifact in remote_done["artifacts"] if artifact["type"] == "remote_patch"]
        assert_true(remote_artifacts, "Remote uploaded artifact should be recorded")
        remote_artifact = request_json("GET", base_url, f"/api/artifacts/{remote_artifacts[0]['id']}")
        assert_true("remote.txt" in remote_artifact["content"], "Remote artifact content should be readable")
        agents = request_json("GET", base_url, "/api/remote-agents")
        assert_true(len(agents) >= 2, "Remote agents should be listed")
        rotated_pm = request_json("POST", base_url, f"/api/remote-agents/{remote_pm['id']}/rotate-token")
        assert_true(rotated_pm.get("token"), "Remote token rotation should return new token")
        try:
            request_json(
                "POST",
                base_url,
                f"/api/remote-agents/{remote_pm['id']}/tasks",
                {"project_id": project["id"], "title": "old token should fail", "description": "should fail"},
                headers=auth_headers(remote_pm["token"]),
            )
            raise AssertionError("Old token should fail after rotation")
        except AssertionError as exc:
            assert_true("401" in str(exc), "Old token should return 401 after rotation")
        disabled_agent = request_json("POST", base_url, f"/api/remote-agents/{remote_worker['id']}/disable")
        assert_equal(disabled_agent["status"], "disabled", "Remote worker should be disabled")
        enabled_agent = request_json("POST", base_url, f"/api/remote-agents/{remote_worker['id']}/enable")
        assert_equal(enabled_agent["status"], "online", "Remote worker should be enabled")
        print("[ok] remote agent protocol register/auth/claim/complete/token admin")

        sdk_pm = RemotePMClient(base_url)
        sdk_registered = sdk_pm.register("smoke-sdk-pm")
        sdk_task = sdk_pm.create_task(
            {
                "project_id": project["id"],
                "title": "sdk remote worker task",
                "description": "Verify SDK PM client and remote worker CLI.",
                "required_role": "sdk_worker",
                "required_capabilities": ["git"],
                "required_tools": ["git"],
            }
        )
        sdk_worker = request_json(
            "POST",
            base_url,
            "/api/remote-agents/register",
            {
                "name": "smoke-sdk-worker",
                "agent_kind": "worker",
                "role": "sdk_worker",
                "capabilities": ["git"],
                "tools": ["git"],
            },
        )
        remote_cli = run(remote_worker_command(base_url, sdk_worker["id"], sdk_worker["token"]), cwd=ROOT, env=env)
        assert_true("Remote task processed by artifact-only" in remote_cli.stdout or remote_cli.returncode == 0, "Remote worker CLI should finish")
        sdk_done = request_json("GET", base_url, f"/api/tasks/{sdk_task['id']}")
        assert_equal(sdk_done["status"], "waiting_review", "Remote worker CLI should complete SDK-created task")
        assert_true(sdk_registered["id"].startswith("agent_"), "SDK PM should register an agent")
        print("[ok] remote SDK and remote worker CLI")

        status = request_json("GET", base_url, "/api/runtime/status")
        assert_true("task_policy" in status, "Runtime status should include task policy")
        assert_true("plans" in status, "Runtime status should include PM plan counts")
        assert_true("remote_agents" in status, "Runtime status should include remote agent counts")
        print("[ok] runtime status includes policy, PM plan counts, and remote agent counts")
        print("[success] smoke test passed")

    finally:
        if runner_id and api_process.poll() is None:
            try:
                request_json("POST", base_url, f"/api/worker-runners/{runner_id}/stop", timeout=3)
            except Exception:
                pass
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
            api_process.wait(timeout=5)
        api_log.close()
        if keep_runtime:
            print(f"[info] kept runtime root: {runtime_root}")
            print(f"[info] API log: {api_log_path}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI Runtime OS smoke test")
    parser.add_argument("--keep-runtime", action="store_true", help="Keep temporary runtime directory for debugging")
    args = parser.parse_args()
    run_smoke(keep_runtime=args.keep_runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
