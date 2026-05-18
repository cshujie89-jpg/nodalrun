from __future__ import annotations

import argparse

from runtime_core.remote_client import RemotePMClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a PM plan through Remote Agent Protocol v1")
    parser.add_argument("--api", default="http://127.0.0.1:8777")
    parser.add_argument("--agent-id")
    parser.add_argument("--token")
    parser.add_argument("--name", default="remote-pm")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--objective", required=True)
    args = parser.parse_args()

    client = RemotePMClient(args.api, agent_id=args.agent_id, token=args.token)
    if not args.agent_id or not args.token:
        registered = client.register(args.name)
        print(f"Registered remote PM: {registered['id']}")
        print(f"Token: {registered['token']}")

    plan = client.create_plan({"project_id": args.project_id, "title": args.title, "objective": args.objective})
    print(f"Created PM plan: {plan['id']}")
    print(f"Child tasks: {plan['progress']['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

