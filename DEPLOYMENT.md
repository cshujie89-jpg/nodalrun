# NodalRun Deployment Guide

## Local Development

```powershell
cd "E:\360MoveData\Users\Admin\Desktop\AI Runtime OS"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8777
```

Open:

```txt
http://127.0.0.1:8777
```

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `RUNTIME_ROOT` | Runtime data directory | `.runtime` under cwd |
| `RUNTIME_DB` | SQLite database path | `RUNTIME_ROOT/runtime.db` |
| `PYTHONPATH` | Project import path | repo root |

## Production Notes

Recommended production shape:

```txt
HTTPS reverse proxy
        |
        v
uvicorn / FastAPI service
        |
        v
SQLite runtime DB + Git project repos
```

Use a process manager such as Windows Task Scheduler, NSSM, systemd, or Docker. Keep Runtime API behind HTTPS if remote agents connect over a network.

## Backup

Back up:

- Git repositories bound as projects
- `.runtime/runtime.db`
- `.runtime/artifacts`
- `.runtime/runner-logs`

## Final Acceptance

```powershell
python scripts/smoke_test.py
```

The release is healthy when the command ends with:

```txt
[success] smoke test passed
```

