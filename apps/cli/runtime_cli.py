from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
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


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Runtime OS CLI")
    parser.add_argument("--api", default=DEFAULT_API)
    sub = parser.add_subparsers(dest="command", required=True)

    project_create = sub.add_parser("project-create")
    project_create.add_argument("--name", required=True)
    project_create.add_argument("--repo-path")
    project_create.add_argument("--repo-url")
    project_create.add_argument("--default-branch", default="main")

    sub.add_parser("project-list")

    task_create = sub.add_parser("task-create")
    task_create.add_argument("--project-id", required=True)
    task_create.add_argument("--title", required=True)
    task_create.add_argument("--description", required=True)
    task_create.add_argument("--validation-command")
    task_create.add_argument("--criteria", action="append", default=[])

    sub.add_parser("task-list")

    task_status = sub.add_parser("task-status")
    task_status.add_argument("task_id")

    sub.add_parser("worker-list")

    args = parser.parse_args()

    if args.command == "project-create":
        print_json(
            api(
                args.api,
                "POST",
                "/api/projects",
                {
                    "name": args.name,
                    "repo_path": args.repo_path,
                    "repo_url": args.repo_url,
                    "default_branch": args.default_branch,
                },
            )
        )
    elif args.command == "project-list":
        print_json(api(args.api, "GET", "/api/projects"))
    elif args.command == "task-create":
        print_json(
            api(
                args.api,
                "POST",
                "/api/tasks",
                {
                    "project_id": args.project_id,
                    "title": args.title,
                    "description": args.description,
                    "validation_command": args.validation_command,
                    "acceptance_criteria": args.criteria,
                },
            )
        )
    elif args.command == "task-list":
        print_json(api(args.api, "GET", "/api/tasks"))
    elif args.command == "task-status":
        print_json(api(args.api, "GET", f"/api/tasks/{args.task_id}"))
    elif args.command == "worker-list":
        print_json(api(args.api, "GET", "/api/workers"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
