# Commercial Readiness

NodalRun is ready as a commercial MVP when the following are true:

- `python scripts/smoke_test.py` passes.
- Web UI opens at `http://127.0.0.1:8777`.
- At least one project is bound to a Git repo.
- Dry-run Worker Runner can deliver a task.
- Claude DeepSeek, Kimi Code, or OpenCode Worker Runner can be started on the target machine.
- Remote Agent registration returns a token and token rotation works.
- Review and Merge flow succeeds on a disposable test repository.
- Operators understand that `Merge` is the irreversible Git action.

## What Is Included

- Multi-agent task control plane
- Local Worker Runners
- Remote Agent Protocol v1
- Python SDK
- PM Plan decomposition
- Artifact and log collection
- Human review and Git merge
- Smoke-test acceptance suite
- Minimal bilingual Web UI

## Known MVP Boundaries

- SQLite is suitable for local/small-team deployment. Use PostgreSQL for multi-server scale.
- Remote artifact upload is text-first in v1.
- Agent permissions are role-based but not yet tenant-scoped.
- PM Plan decomposition has a deterministic default path; advanced dynamic DAG planning is a next-tier feature.

