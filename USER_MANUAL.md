# NodalRun 使用手册

NodalRun 是一个多 Agent 工作调度中枢。它让 PM Agent 发布目标和任务，让本地或远程 Worker/Vibe Agent 自动领取任务、执行、回传日志和交付物，并由人类或 Reviewer 做审核与合并。

## 1. 快速启动

```powershell
cd "E:\360MoveData\Users\Admin\Desktop\AI Runtime OS"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8777
```

打开：

```txt
http://127.0.0.1:8777
```

## 2. 新手最短流程

1. 打开 Web UI。
2. 进入 `Projects`，创建项目，填本地 Git 仓库路径。
3. 进入 `Workers`，点击 `Start Dry Run`。
4. 进入 `Tasks`，创建一个任务。
5. 等待任务进入 `waiting_review`。
6. 打开任务详情，查看日志和 artifacts。
7. 如果满意，点击 `Merge` 合并到项目默认分支。

## 3. PM Plan 流程

进入 `PM Plans`：

1. 选择项目。
2. 输入计划标题。
3. 输入目标描述。
4. 点击 `Create PM Plan`。

系统会创建一个 PM Plan，并拆出默认子任务：

- scope audit
- implementation slice
- validation pass
- delivery notes

这些子任务会进入正常任务队列，可由 Worker Runner 或远程 Agent 执行。

## 4. Worker Runner

进入 `Workers`，可启动：

- `Start Dry Run`
- `Start Claude DeepSeek`
- `Start Kimi Code`
- `Start OpenCode`

启动后，Runner 会持续从队列领取匹配任务。

## 5. 远程 Agent 接入

进入 `Agents`，注册远程 Agent：

- `pm`: 发布计划和任务
- `worker`: 执行任务
- `vibe`: 执行内容、设计、素材类任务
- `hybrid`: 同时具备 PM 和 Worker 能力

注册后会显示一次性 token。请立即保存。

远程 Worker 示例：

```powershell
python workers/remote_worker.py --agent-id agent_xxx --token "<token>" --agent artifact-only
```

远程 PM 示例：

```powershell
python scripts/remote_pm_demo.py --project-id proj_xxx --title "Improve dashboard" --objective "Add better runtime visibility"
```

协议详情见：

```txt
REMOTE_AGENT_PROTOCOL.md
```

## 6. 审核与合并

任务完成后会进入 `waiting_review`。

- `Complete`: 标记审核完成，但不改项目仓库。
- `Merge`: 将 session worktree 的变更 commit 并 merge 回项目默认分支。
- `Request Revision`: 要求返工。
- `Retry`: 将失败、取消或返工任务重新放回队列。

Merge 会在项目仓库有未提交变更时拒绝执行，避免覆盖人工修改。

## 7. 自动化验收

```powershell
python scripts/smoke_test.py
```

成功标准：

```txt
[success] smoke test passed
```

该测试覆盖项目、任务、Worker、重试、artifact、review、merge、PM Plan、远程 Agent 协议、SDK 和远程 Worker CLI。

## 8. 运维建议

- 只把 NodalRun 暴露在可信网络中。
- 远程 Agent token 泄露后，立即在 `Agents` 页面轮换 token 或禁用 Agent。
- 合并前确认项目 Git 仓库没有未提交人工改动。
- 定期备份 `.runtime/runtime.db` 和项目 Git 仓库。
- 生产部署时建议使用反向代理、HTTPS 和系统服务管理。

