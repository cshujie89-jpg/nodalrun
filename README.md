# NodalRun

NodalRun is a minimal commercial-ready control plane for PM agents, remote coding/vibe agents, local CLI workers, review, artifacts, and merge workflows.

- Runtime API with FastAPI and SQLite
- Project, Task, Worker, Session, Artifact, and Audit records
- Isolated session workspaces with Git worktree support
- Local worker that can run in dry-run, claude-deepseek, kimi-code, or opencode mode
- Remote Agent Protocol v1 for PM, Worker, Vibe, and Hybrid agents
- Minimal Web UI for plans, tasks, projects, workers, agents, review, merge, and artifacts

Full manual:

```txt
USER_MANUAL.md
```

Brand and deployment:

```txt
BRAND.md
DEPLOYMENT.md
COMMERCIAL_READINESS.md
REMOTE_AGENT_PROTOCOL.md
```

## Start API

```powershell
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8777
```

Open:

```txt
http://127.0.0.1:8777
```

## Run Worker

Dry run:

```powershell
python workers/local_worker.py --agent dry-run
```

Intentional failure test:

```powershell
python workers/local_worker.py --agent fail-test --once
```

Use local Claude DeepSeek CLI:

```powershell
python workers/local_worker.py --agent claude-deepseek
```

Use local Kimi Code CLI:

```powershell
python workers/local_worker.py --agent kimi-code
```

## Managed Worker Runner

Open the Web UI, go to `Workers`, then start a managed runner:

- `Start Dry Run` for safe end-to-end testing
- `Start Claude DeepSeek` for local `claude-deepseek`
- `Start Kimi Code` for local `kimi-code`

After a runner is started, queued matching tasks are claimed and executed automatically. Use `Stop` to terminate a managed runner.

## PM Plans

Open the Web UI, go to `PM Plans`, then create a plan from a project-level objective. Runtime creates a PM plan record and decomposes it into four linked child tasks:

- scope audit
- implementation slice
- validation pass
- delivery notes

The child tasks enter the normal queue and can be processed automatically by managed worker runners.

## Review and Merge

Tasks delivered by local git workers move to `waiting_review`. Use `Complete` to approve without changing the project repo, or `Merge` to commit the session worktree and merge it back into the project's default branch. Merge is explicit and will fail if the project repository has uncommitted changes.

## Remote Agents

Open the Web UI, go to `Agents`, then register a remote PM, Worker, Vibe, or Hybrid agent. Registration returns a one-time token. Remote agents use that token to create plans/tasks, claim work, send logs, complete/fail sessions, and upload artifacts.

Run a remote worker client:

```powershell
python workers/remote_worker.py --agent-id agent_xxx --token "<token>" --agent artifact-only
```

Create a PM plan through the SDK demo:

```powershell
python scripts/remote_pm_demo.py --project-id proj_xxx --title "Improve dashboard" --objective "Add better runtime visibility"
```

Protocol reference:

```txt
REMOTE_AGENT_PROTOCOL.md
```

## CLI Examples

```powershell
python apps/cli/runtime_cli.py project-create --name demo --repo-path "E:\path\to\repo"
python apps/cli/runtime_cli.py task-create --project-id proj_xxx --title "Add landing page" --description "Create a landing page"
python apps/cli/runtime_cli.py task-list
```

## Smoke Test

```powershell
python scripts/smoke_test.py
```

Final acceptance:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/final_acceptance.ps1
```

The smoke test passes only if project creation, central task policy, worker enable/disable, retry exhaustion, dry-run artifacts, review completion, review merge, stale worker reconciliation, managed runner start/stop, PM plan decomposition, remote agent register/auth/claim/complete, and the remote SDK/worker CLI all work.
