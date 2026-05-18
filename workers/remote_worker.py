from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from runtime_core.remote_client import RemoteWorkerClient
from workers.local_worker import build_prompt, run_claude_deepseek, run_dry_task, run_kimi_code, run_opencode, run_validation


DEFAULT_API = "http://127.0.0.1:8777"


def artifact_from_text(filename: str, content: str, artifact_type: str = "remote_result") -> dict[str, str]:
    return {"type": artifact_type, "filename": filename, "content": content}


def process_claim(client: RemoteWorkerClient, agent: str) -> bool:
    claim = client.claim()
    if not claim.get("claimed"):
        return False

    task = claim["task"]
    project = claim["project"]
    session = claim["session"]
    session_id = session["id"]
    workspace = Path(session["workspace_path"])
    client.log(session_id, f"Claimed task {task['id']}: {task['title']}")

    try:
        prompt = build_prompt(task, project, str(workspace))
        validation_status = "not_run"
        validation_output = "No validation command configured."

        if agent == "dry-run":
            workspace.mkdir(parents=True, exist_ok=True)
            agent_output = run_dry_task(task, project, workspace)
            validation_status, validation_output = run_validation(task.get("validation_command"), workspace)
        elif agent == "artifact-only":
            agent_output = f"Remote artifact-only worker accepted task {task['id']}."
        elif agent == "claude-deepseek":
            client.log(session_id, "Invoking claude-deepseek")
            agent_output = run_claude_deepseek(prompt, workspace)
            validation_status, validation_output = run_validation(task.get("validation_command"), workspace)
        elif agent == "kimi-code":
            client.log(session_id, "Invoking kimi-code")
            agent_output = run_kimi_code(prompt, workspace)
            validation_status, validation_output = run_validation(task.get("validation_command"), workspace)
        elif agent == "opencode":
            client.log(session_id, "Invoking opencode")
            agent_output = run_opencode(prompt, workspace)
            validation_status, validation_output = run_validation(task.get("validation_command"), workspace)
        else:
            raise RuntimeError(f"Unknown agent: {agent}")

        client.log(session_id, agent_output[-4000:] or "Agent returned no output.")
        client.complete(
            session_id,
            summary=f"Remote task processed by {agent}",
            validation_status=validation_status,
            validation_output=validation_output[-8000:],
            artifacts=[
                artifact_from_text("REMOTE_WORKER_RESULT.md", agent_output),
                artifact_from_text("REMOTE_VALIDATION.txt", validation_output, "remote_validation"),
            ],
        )
        return True
    except Exception as exc:
        client.log(session_id, str(exc), level="error")
        client.fail(session_id, str(exc))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Runtime OS remote worker protocol client")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--agent-id")
    parser.add_argument("--token")
    parser.add_argument("--name", default="remote-worker")
    parser.add_argument("--role", default="dev_worker")
    parser.add_argument("--agent", choices=["dry-run", "artifact-only", "claude-deepseek", "kimi-code", "opencode"], default="artifact-only")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    args = parser.parse_args()

    client = RemoteWorkerClient(args.api, agent_id=args.agent_id, token=args.token)
    if not args.agent_id or not args.token:
        registered = client.register(
            args.name,
            role=args.role,
            capabilities=["git", "python", "nodejs"],
            tools=["git", "terminal", "node", "browser"],
        )
        print(f"Registered remote worker: {registered['id']}")
        print(f"Token: {registered['token']}")

    while True:
        client.heartbeat()
        did_work = process_claim(client, args.agent)
        if args.once:
            break
        if not did_work:
            time.sleep(args.poll_interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

