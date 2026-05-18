from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from runtime_core.store import ROOT_DIR, new_id


def run(command: list[str], cwd: Path | None = None, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=check, timeout=timeout)


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() or (path / ".git").is_file()


def ensure_project_repo(project: dict[str, Any]) -> Path:
    project_root = ROOT_DIR / "projects" / project["id"]
    repo_root = project_root / "repo"
    project_root.mkdir(parents=True, exist_ok=True)

    repo_path = project.get("repo_path")
    repo_url = project.get("repo_url")

    if repo_path:
        source = Path(repo_path)
        if not source.exists():
            raise RuntimeError(f"repo_path does not exist: {source}")
        if is_git_repo(source):
            return source
        if not repo_root.exists():
            shutil.copytree(source, repo_root)
        return repo_root

    if repo_url:
        if repo_root.exists():
            run(["git", "fetch", "--all"], cwd=repo_root, check=False)
        else:
            run(["git", "clone", repo_url, str(repo_root)])
        return repo_root

    repo_root.mkdir(parents=True, exist_ok=True)
    readme = repo_root / "README.md"
    if not readme.exists():
        readme.write_text("# Empty AI Runtime Project\n", encoding="utf-8")
    return repo_root


def create_session_workspace(project: dict[str, Any], task_id: str, session_id: str) -> dict[str, str]:
    source_repo = ensure_project_repo(project)
    session_root = ROOT_DIR / "sessions" / session_id
    worktree = session_root / "worktree"
    session_root.mkdir(parents=True, exist_ok=True)

    branch_name = f"ai/{task_id}/{session_id}"
    base_commit = None

    if is_git_repo(source_repo):
        base_commit = run(["git", "rev-parse", "HEAD"], cwd=source_repo).stdout.strip()
        if worktree.exists():
            shutil.rmtree(worktree)
        run(["git", "worktree", "add", "-B", branch_name, str(worktree)], cwd=source_repo)
    else:
        if worktree.exists():
            shutil.rmtree(worktree)
        shutil.copytree(source_repo, worktree)

    return {
        "workspace_path": str(worktree),
        "branch_name": branch_name,
        "base_commit": base_commit or "",
    }


def collect_artifacts(workspace_path: str, artifact_dir: Path) -> list[dict[str, Any]]:
    workspace = Path(workspace_path)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    if is_git_repo(workspace):
        run(["git", "add", "-N", "."], cwd=workspace, check=False)
        diff = run(["git", "diff", "--binary"], cwd=workspace, check=False).stdout
        stat = run(["git", "diff", "--stat"], cwd=workspace, check=False).stdout
        status = run(["git", "status", "--short"], cwd=workspace, check=False).stdout

        diff_path = artifact_dir / "diff.patch"
        diff_path.write_text(diff, encoding="utf-8")
        artifacts.append(
            {
                "type": "git_diff",
                "uri": str(diff_path),
                "metadata": {"bytes": len(diff.encode("utf-8")), "stat": stat},
            }
        )

        status_path = artifact_dir / "changed_files.txt"
        status_path.write_text(status, encoding="utf-8")
        artifacts.append(
            {
                "type": "changed_files",
                "uri": str(status_path),
                "metadata": {"lines": len([line for line in status.splitlines() if line.strip()])},
            }
        )
    else:
        manifest = artifact_dir / "workspace_manifest.txt"
        lines = [str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file()]
        manifest.write_text("\n".join(lines), encoding="utf-8")
        artifacts.append({"type": "workspace_manifest", "uri": str(manifest), "metadata": {"files": len(lines)}})

    return artifacts


def make_artifact_dir(task_id: str, session_id: str) -> Path:
    return ROOT_DIR / "artifacts" / task_id / session_id / new_id("bundle")


def merge_session_workspace(project: dict[str, Any], session: dict[str, Any], message: str) -> dict[str, Any]:
    source_repo = ensure_project_repo(project)
    worktree = Path(session["workspace_path"])
    if not is_git_repo(source_repo):
        raise RuntimeError("Project source is not a git repository")
    if not is_git_repo(worktree):
        raise RuntimeError("Session workspace is not a git repository")

    source_status = run(["git", "status", "--porcelain"], cwd=source_repo, check=False).stdout.strip()
    if source_status:
        raise RuntimeError("Project repository has uncommitted changes; merge cancelled")

    worktree_status = run(["git", "status", "--porcelain"], cwd=worktree, check=False).stdout.strip()
    if worktree_status:
        run(["git", "add", "."], cwd=worktree)
        commit = run(
            [
                "git",
                "-c",
                "user.email=ai-runtime-os@example.local",
                "-c",
                "user.name=AI Runtime OS",
                "commit",
                "-m",
                message,
            ],
            cwd=worktree,
            check=False,
        )
        if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
            raise RuntimeError(f"Unable to commit session workspace:\n{commit.stdout}{commit.stderr}")

    default_branch = project.get("default_branch") or "main"
    branch_name = session["branch_name"]
    current_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=source_repo).stdout.strip()
    if current_branch != default_branch:
        checkout = run(["git", "checkout", default_branch], cwd=source_repo, check=False)
        if checkout.returncode != 0:
            raise RuntimeError(f"Unable to checkout {default_branch}:\n{checkout.stdout}{checkout.stderr}")

    before = run(["git", "rev-parse", "HEAD"], cwd=source_repo).stdout.strip()
    merge = run(
        [
            "git",
            "-c",
            "user.email=ai-runtime-os@example.local",
            "-c",
            "user.name=AI Runtime OS",
            "merge",
            "--no-ff",
            branch_name,
            "-m",
            f"Merge {branch_name}",
        ],
        cwd=source_repo,
        check=False,
    )
    if merge.returncode != 0:
        run(["git", "merge", "--abort"], cwd=source_repo, check=False)
        raise RuntimeError(f"Unable to merge {branch_name}:\n{merge.stdout}{merge.stderr}")
    after = run(["git", "rev-parse", "HEAD"], cwd=source_repo).stdout.strip()
    return {
        "source_repo": str(source_repo),
        "branch_name": branch_name,
        "default_branch": default_branch,
        "before": before,
        "after": after,
        "changed": before != after,
        "output": merge.stdout + merge.stderr,
    }
