# Remote Agent Protocol v1

Remote Agent Protocol v1 lets external PM, Worker, Vibe, or hybrid agents connect to AI Runtime OS over HTTP.

## Register

```http
POST /api/remote-agents/register
Content-Type: application/json
```

```json
{
  "name": "remote-claude-01",
  "agent_kind": "worker",
  "role": "dev_worker",
  "capabilities": ["git", "python", "nodejs"],
  "tools": ["git", "terminal"]
}
```

The response includes a one-time `token`. Store it immediately.

Supported `agent_kind` values:

- `pm`: can create PM plans and tasks
- `worker`: can claim and execute tasks
- `vibe`: can create tasks and execute tasks
- `hybrid`: can do both PM and Worker operations

## Authentication

Agent endpoints require:

```http
Authorization: Bearer <token>
```

## PM Agent

Create a plan:

```http
POST /api/remote-agents/{agent_id}/pm/plans
Authorization: Bearer <token>
```

Create a standalone task:

```http
POST /api/remote-agents/{agent_id}/tasks
Authorization: Bearer <token>
```

Create a task inside an existing plan:

```http
POST /api/remote-agents/{agent_id}/pm/plans/{plan_id}/tasks
Authorization: Bearer <token>
```

## Worker or Vibe Agent

Heartbeat:

```http
POST /api/remote-agents/{agent_id}/heartbeat
Authorization: Bearer <token>
```

Claim a task:

```http
POST /api/remote-agents/{agent_id}/claim
Authorization: Bearer <token>
```

Submit logs:

```http
POST /api/remote-agents/{agent_id}/sessions/{session_id}/logs
Authorization: Bearer <token>
```

```json
{
  "entries": [
    {"level": "info", "message": "Started implementation"}
  ]
}
```

Complete a session with uploaded artifacts:

```http
POST /api/remote-agents/{agent_id}/sessions/{session_id}/complete
Authorization: Bearer <token>
```

```json
{
  "summary": "Implemented requested change",
  "validation_status": "passed",
  "validation_output": "tests passed",
  "artifacts": [
    {
      "type": "remote_patch",
      "filename": "change.patch",
      "content": "diff --git ..."
    }
  ]
}
```

Fail a session:

```http
POST /api/remote-agents/{agent_id}/sessions/{session_id}/fail
Authorization: Bearer <token>
```

```json
{"reason": "dependency install failed"}
```

## Python SDK

```python
from runtime_core.remote_client import RemotePMClient, RemoteWorkerClient

pm = RemotePMClient("http://127.0.0.1:8777")
pm_agent = pm.register("remote-pm")
task = pm.create_task({
    "project_id": "proj_xxx",
    "title": "Build feature",
    "description": "Implement the requested change"
})

worker = RemoteWorkerClient("http://127.0.0.1:8777")
worker.register("remote-worker")
claim = worker.claim()
if claim["claimed"]:
    session_id = claim["session"]["id"]
    worker.log(session_id, "Working")
    worker.complete(
        session_id,
        summary="Done",
        artifacts=[{"type": "remote_result", "filename": "result.md", "content": "Done"}],
    )
```

## Reference Clients

```powershell
python workers/remote_worker.py --agent-id agent_xxx --token "<token>" --agent artifact-only
python scripts/remote_pm_demo.py --project-id proj_xxx --title "Improve dashboard" --objective "Add better runtime visibility"
```
