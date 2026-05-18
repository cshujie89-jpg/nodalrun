from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API = "http://127.0.0.1:8777"


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {body}") from exc


def api(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    return request_json(method, f"{base_url}{path}", payload)


def log(base_url: str, session_id: str, message: str, level: str = "info") -> None:
    print(f"[{level}] {message}")
    api(base_url, "POST", f"/api/sessions/{session_id}/logs", {"level": level, "message": message})


def build_prompt(task: dict[str, Any], project: dict[str, Any], workspace_path: str) -> str:
    criteria = "\n".join(f"- {item}" for item in task.get("acceptance_criteria", [])) or "- Produce a reviewable change."
    return f"""You are an AI Runtime OS worker.

Project: {project["name"]}
Workspace: {workspace_path}
Task title: {task["title"]}
Task description:
{task["description"]}

Acceptance criteria:
{criteria}

Rules:
- Work only inside the workspace.
- Keep changes focused on the task.
- Do not push to remotes.
- Leave a concise implementation summary in RUNTIME_WORKER_RESULT.md.
"""


def run_command(command: list[str], cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def run_dry_task(task: dict[str, Any], project: dict[str, Any], workspace: Path) -> str:
    result = workspace / "RUNTIME_WORKER_RESULT.md"
    result.write_text(
        "\n".join(
            [
                "# Runtime Worker Result",
                "",
                f"Project: {project['name']}",
                f"Task: {task['title']}",
                "",
                "This is a dry-run worker result. Replace `--agent dry-run` with",
                "`--agent claude-deepseek` or `--agent kimi-code` to execute with a local AI CLI.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return "Dry-run artifact created."


def run_claude_deepseek(prompt: str, workspace: Path) -> str:
    completed = run_command(
        [
            "claude-deepseek",
            "-p",
            "--permission-mode",
            "dontAsk",
            "--add-dir",
            str(workspace),
            prompt,
        ],
        cwd=workspace,
    )
    return completed.stdout + completed.stderr


def run_kimi_code(prompt: str, workspace: Path) -> str:
    completed = run_command(
        [
            "kimi-code",
            "--work-dir",
            str(workspace),
            "--print",
            "--prompt",
            prompt,
        ],
        cwd=workspace,
    )
    return completed.stdout + completed.stderr


def run_opencode(prompt: str, workspace: Path) -> str:
    completed = run_command(
        [
            "opencode",
            "run",
            "--dir",
            str(workspace),
            "--dangerously-skip-permissions",
            prompt,
        ],
        cwd=workspace,
    )
    return completed.stdout + completed.stderr


def run_validation(command: str | None, workspace: Path) -> tuple[str, str]:
    if not command:
        return "not_run", "No validation command configured."
    completed = subprocess.run(command, cwd=workspace, shell=True, text=True, capture_output=True, timeout=600, check=False)
    status = "passed" if completed.returncode == 0 else "failed"
    output = completed.stdout + completed.stderr
    return status, output


def process_claim(base_url: str, worker_id: str, agent: str) -> bool:
    claim = api(base_url, "POST", f"/api/workers/{worker_id}/claim")
    if not claim.get("claimed"):
        return False

    task = claim["task"]
    session = claim["session"]
    project = claim["project"]
    session_id = session["id"]
    workspace = Path(session["workspace_path"])

    try:
        log(base_url, session_id, f"Claimed task {task['id']}: {task['title']}")
        log(base_url, session_id, f"Workspace: {workspace}")
        prompt = build_prompt(task, project, str(workspace))

        if agent == "dry-run":
            agent_output = run_dry_task(task, project, workspace)
        elif agent == "fail-test":
            raise RuntimeError("Intentional fail-test worker error")
        elif agent == "claude-deepseek":
            log(base_url, session_id, "Invoking claude-deepseek")
            agent_output = run_claude_deepseek(prompt, workspace)
        elif agent == "kimi-code":
            log(base_url, session_id, "Invoking kimi-code")
            agent_output = run_kimi_code(prompt, workspace)
        elif agent == "opencode":
            log(base_url, session_id, "Invoking opencode")
            agent_output = run_opencode(prompt, workspace)
        else:
            raise RuntimeError(f"Unknown agent: {agent}")

        log(base_url, session_id, agent_output[-4000:] or "Agent returned no output.")
        validation_status, validation_output = run_validation(task.get("validation_command"), workspace)
        log(base_url, session_id, f"Validation status: {validation_status}")
        if validation_output:
            log(base_url, session_id, validation_output[-4000:])

        api(
            base_url,
            "POST",
            f"/api/sessions/{session_id}/complete",
            {
                "summary": f"Task processed by {agent}",
                "validation_status": validation_status,
                "validation_output": validation_output[-8000:],
            },
        )
        return True
    except Exception as exc:
        try:
            log(base_url, session_id, str(exc), level="error")
            api(base_url, "POST", f"/api/sessions/{session_id}/fail", {"reason": str(exc)})
        finally:
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Runtime OS local worker")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--agent", choices=["dry-run", "fail-test", "claude-deepseek", "kimi-code", "opencode"], default="dry-run")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--worker-type", default="local_worker")
    args = parser.parse_args()

    worker = api(
        args.api,
        "POST",
        "/api/workers/register",
        {
            "worker_type": args.worker_type,
            "role": "dev_worker",
            "capabilities": ["git", "python", "nodejs"],
            "tools": ["git", "terminal", "node", "browser"],
            "max_concurrency": 1,
        },
    )
    worker_id = worker["id"]
    print(f"Registered worker: {worker_id}")

    while True:
        api(args.api, "POST", f"/api/workers/{worker_id}/heartbeat")
        did_work = process_claim(args.api, worker_id, args.agent)
        if args.once:
            break
        if not did_work:
            time.sleep(args.poll_interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
