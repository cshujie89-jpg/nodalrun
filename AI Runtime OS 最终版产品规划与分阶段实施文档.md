# AI Runtime OS 最终版产品规划与分阶段实施文档

版本：Final Planning v1.0

日期：2026-05-18

状态：可执行产品路线图

---

## 1. 最终产品定位

AI Runtime OS 是一个面向 AI Worker 的任务运行时、调度系统和管理控制台。

它的最终目标是：

> 让不同模型、不同工具链、不同职责的 AI Worker，像云资源一样被注册、调度、监控、审计和交付。

它不是聊天机器人。

它不是单一 Agent 框架。

它不是从第一天就复制 Kubernetes。

它是一个 AI Worker Control Plane。

---

## 2. 最终产品形态

最终版本由六个核心系统组成：

```txt
AI Runtime OS

1. Control Plane
   管理项目、任务、Worker、Role、权限、审计。

2. Workflow Plane
   管理长任务状态、失败恢复、重试、取消、人工审批。

3. Execution Plane
   管理 Worker Pool、Session、Workspace、Sandbox。

4. Tool Plane
   管理 Tool Registry、MCP Tool Server、Secret、工具调用审计。

5. Memory Plane
   管理 Project Facts、Task History、Reflection Memory、知识检索。

6. Web Management UI
   提供任务、Worker、项目、工具、Memory、日志、交付物的可视化管理界面。
```

最终系统架构：

```txt
┌──────────────────────────────────────────────┐
│ Web Management UI / CLI / PM Agent API        │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Runtime API Gateway                           │
│ Auth / RBAC / Rate Limit / Audit              │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Control Plane                                 │
│ Project / Task / Worker / Role / Policy       │
└───────┬──────────────┬──────────────┬────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐
│ Workflow    │ │ Memory      │ │ Tool         │
│ Engine      │ │ Plane       │ │ Registry     │
└──────┬──────┘ └──────┬──────┘ └──────┬───────┘
       │               │               │
       ▼               ▼               ▼
┌──────────────────────────────────────────────┐
│ Execution Plane                               │
│ Worker Pool / Session / Workspace / Sandbox   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Workers                                       │
│ Claude / OpenAI / Gemini / Local / Custom     │
└──────────────────────────────────────────────┘
```

---

## 3. 最终版产品能力地图

### 3.1 项目管理

- 创建项目
- 绑定 Git 仓库
- 管理项目环境
- 管理项目 Facts
- 管理项目 Secrets
- 查看项目任务历史
- 查看项目 Worker 使用情况
- 查看项目交付物

### 3.2 任务管理

- 创建任务
- 拆分任务
- 设置优先级
- 设置验收标准
- 指定 Role / Skill / Tool
- 暂停、取消、重试任务
- Review 交付物
- 请求返工
- 归档任务

### 3.3 Worker 管理

- 注册 Worker
- 查看 Worker 在线状态
- 管理 Worker Role
- 管理 Worker 能力
- 设置并发上限
- 查看 Worker 当前任务
- 查看 Worker 成功率、失败率、成本
- 禁用或下线 Worker

### 3.4 调度系统

- Role 匹配
- Capability 匹配
- Tool 匹配
- 项目访问权限匹配
- Secret 权限匹配
- 成本评分
- 成功率评分
- 负载均衡
- 优先级队列
- 失败重试
- Worker 心跳和租约

### 3.5 Workspace 与交付

- 项目 Repo 同步
- Session Workspace 创建
- Git worktree 隔离
- Diff 生成
- Commit 生成
- PR 生成
- Build/Test 验证
- Preview URL
- Artifact 存储

### 3.6 Tool 系统

- Tool Registry
- Tool Version
- Tool Risk Level
- Tool Permission
- Tool Call Audit
- MCP Tool Server
- Secret Broker
- Approval Gate

### 3.7 Memory 系统

- Project Facts
- Runtime State
- Task History
- Reflection Memory
- Memory Review
- Memory Expiration
- Memory Confidence
- Memory Retrieval

### 3.8 Web UI 管理界面

- 全局 Dashboard
- Project Console
- Task Queue
- Task Detail
- Worker Dashboard
- Session Viewer
- Artifact Viewer
- Diff Review
- Tool Registry
- Memory Viewer
- Audit Log
- Settings

---

## 4. 分阶段路线图总览

推荐路线：

```txt
Phase 0  技术验证
Phase 1  单 Worker 任务闭环
Phase 2  多 Worker 调度与 Web UI 初版
Phase 3  权限、Tool Registry、审计
Phase 4  Memory Plane 与 Workflow Engine
Phase 5  多项目、多 PM Agent、平台化
Phase 6  企业级与商业化版本
```

每一阶段都必须能独立交付，不依赖后续阶段才能证明价值。

---

## 5. Phase 0：技术验证

周期：3-5 天

目标：

证明 Runtime 可以创建任务、Worker 可以领取任务、任务状态可以流转。

### 5.1 功能范围

- 初始化代码仓库
- FastAPI Runtime API
- SQLite 或 PostgreSQL
- Task 创建接口
- Worker 注册接口
- Worker 心跳接口
- Worker 领取任务接口
- Task 状态流转
- 简单 CLI

### 5.2 暂不做

- Web UI
- Git Workspace
- 多 Worker 调度
- Tool Registry
- Memory
- 权限系统

### 5.3 验收标准

```txt
1. CLI 创建一个任务。
2. Worker 注册成功。
3. Worker 领取任务。
4. Worker 模拟执行 5 秒。
5. Worker 上报完成。
6. Task 状态从 queued -> running -> completed。
```

### 5.4 产物

- `runtime-api`
- `runtime-worker`
- `runtime-cli`
- 最小数据库 schema

---

## 6. Phase 1：单 Worker 任务闭环

周期：1-2 周

目标：

让一个 AI Worker 在隔离 Workspace 中完成一个真实代码任务，并产生可 Review 交付物。

### 6.1 功能范围

- Project Registry
- Git 仓库 clone / sync
- Session Manager
- Git worktree Workspace
- Local Worker 或 Claude Worker
- Skill Prompt Bundle
- Worker 执行真实任务
- 日志采集
- Git diff artifact
- 验证命令执行
- 人工 Review 状态

### 6.2 核心状态流

```txt
draft
  -> queued
  -> assigned
  -> running
  -> waiting_review
  -> completed
```

失败状态：

```txt
running
  -> failed
  -> cancelled
  -> timed_out
```

### 6.3 最小 Web UI

Phase 1 需要一个非常轻的 Web UI，避免只靠 CLI。

页面：

1. Task List
2. Task Detail
3. Worker Status
4. Artifact Preview

Task Detail 展示：

- Task title
- Status
- Worker
- Logs
- Changed files
- Diff artifact
- Validation result
- Complete / Request Revision 按钮

### 6.4 验收标准

```txt
1. 创建一个绑定 Git 仓库的项目。
2. 创建一个前端修改任务。
3. Worker 在独立 worktree 中执行任务。
4. Runtime 收集 logs。
5. Runtime 生成 diff artifact。
6. Web UI 可以查看任务状态和 diff。
7. 人工点击 Review 完成任务。
```

### 6.5 产物

- 可运行的单机 Runtime
- 单 Worker 执行闭环
- 最小 Web 管理界面
- Git diff 交付链路

---

## 7. Phase 2：多 Worker 调度与 Web UI 初版

周期：2-3 周

目标：

支持多个 Worker 注册、调度、心跳、失败检测，并让 Web UI 成为主要管理入口。

### 7.1 功能范围

- Worker Pool
- Worker Role
- Worker Capability
- Worker Heartbeat
- Worker Lease
- 基于 role/capability/tool 的调度
- Worker 并发控制
- Task Priority
- Task Retry
- Worker 下线检测
- Web UI 初版

### 7.2 调度逻辑

调度分两步：

1. Filter：筛掉不可用 Worker。
2. Score：给可用 Worker 打分。

Filter：

- online
- role match
- capacity available
- capability match
- tool match
- project access allowed

Score：

- 当前负载
- 最近成功率
- 历史执行时间
- 任务等待时间
- 模型成本
- 项目亲和性

### 7.3 Web UI 初版页面

#### 7.3.1 Dashboard

展示：

- 总任务数
- Running 任务数
- Waiting Review 任务数
- Failed 任务数
- 在线 Worker 数
- 今日完成任务数
- 平均执行时长
- 最近失败任务

#### 7.3.2 Task Queue

功能：

- 按状态筛选
- 按项目筛选
- 按 Worker 筛选
- 按优先级排序
- 创建任务
- 暂停任务
- 取消任务
- 重试任务

#### 7.3.3 Task Detail

功能：

- 查看任务输入
- 查看状态时间线
- 查看 Session
- 查看 Worker
- 查看日志
- 查看 Tool calls
- 查看 changed files
- 查看 diff
- 查看 artifacts
- Review / Request Revision / Complete

#### 7.3.4 Worker Dashboard

功能：

- Worker 列表
- 在线/离线状态
- 当前任务
- Role
- Capabilities
- Tools
- Max concurrency
- Success rate
- Failure rate
- Disable / Drain

#### 7.3.5 Project Console

功能：

- 项目列表
- Repo 状态
- 当前活跃任务
- 最近交付物
- Project Facts
- 项目设置

### 7.4 验收标准

```txt
1. 至少 3 个 Worker 同时注册。
2. Runtime 能把不同任务分配给不同 Worker。
3. Worker 下线后，任务不丢失。
4. 失败任务可以重试。
5. Web UI 可以完成任务创建、查看、Review、重试。
```

---

## 8. Phase 3：权限、Tool Registry、审计

周期：3-4 周

目标：

把系统从“能跑任务”升级为“可控、可审计、可授权地跑任务”。

### 8.1 功能范围

- API Key / User Auth
- RBAC
- Project Access Policy
- Tool Registry
- Tool Risk Level
- Tool Permission
- Secret Broker
- Approval Gate
- Tool Call Audit
- Audit Log UI

### 8.2 Role 权限

基础角色：

- Admin
- Runtime Operator
- Project Owner
- Reviewer
- PM Agent
- Worker
-
权限模型：

```txt
subject -> action -> resource -> condition
```

示例：

```txt
pm_agent_001 can create_task on project_001
worker_001 can use_tool git on project_001
reviewer_001 can approve_delivery on task_001
```

### 8.3 Tool Registry

Tool 字段：

```json
{
  "tool_id": "github",
  "version": "1.0.0",
  "type": "mcp_server",
  "risk_level": "high",
  "allowed_roles": ["dev_worker"],
  "requires_secret": true,
  "approval_required": true
}
```

### 8.4 高风险操作

默认需要审批：

- push 到远程分支
- 创建 PR
- 部署到生产环境
- 删除数据
- 修改 secret
- 发布外部内容
- 大规模调用付费 API

### 8.5 Web UI 新增页面

#### Tool Registry

- Tool 列表
- 版本
- 风险等级
- 可用 Role
- 是否需要 Secret
- 是否需要审批
- 启用/禁用

#### Approval Center

- 待审批操作
- 操作来源
- 风险等级
- Worker
- Task
- Approve / Reject

#### Audit Log

- Actor
- Action
- Resource
- Task
- Session
- Timestamp
- Metadata

### 8.6 验收标准

```txt
1. Worker 无权限时不能调用高风险 Tool。
2. 高风险操作进入 Approval Center。
3. 审批通过后 Worker 才能继续执行。
4. 所有工具调用都有审计记录。
5. Web UI 可以搜索和过滤 Audit Log。
```

---

## 9. Phase 4：Memory Plane 与 Workflow Engine

周期：4-6 周

目标：

支持长任务、复杂任务、失败恢复、项目记忆和可控经验沉淀。

### 9.1 功能范围

- Durable Workflow Engine
- Task Timeout
- Retry Policy
- Cancellation
- Human Review Gate
- Project Facts
- Task History
- Reflection Memory
- Memory Review
- Memory Retrieval
- Memory Viewer UI

### 9.2 Workflow Engine

可选方案：

- Temporal
- Prefect
- 自研轻量 Workflow Engine

推荐：

Phase 4 开始引入 Temporal 或同类 durable workflow。

原因：

- 长任务可恢复
- 状态持久化
- Retry/Timeout 标准化
- Human-in-the-loop 更自然

### 9.3 Memory 分类

#### Project Facts

项目事实：

- 技术栈
- 目录结构
- 部署结构
- 测试命令
- 代码规范
- 常见坑

#### Task History

任务历史：

- 输入
- 使用 Worker
- 使用 Skill
- 使用 Tool
- 执行结果
- 失败原因
- 交付物

#### Reflection Memory

经验记忆：

- Bug 经验
- Review 经验
- SEO 经验
- 运维经验

Reflection Memory 必须包含：

- source
- confidence
- scope
- expires_at
- approved_by
- superseded_by

### 9.4 Web UI 新增页面

#### Memory Viewer

- Project Facts
- Task History
- Reflection Memory
- 来源
- 置信度
- 适用范围
- 过期时间
- Approve / Edit / Delete

#### Workflow Monitor

- Workflow 状态
- 当前步骤
- Retry 次数
- Timeout 信息
- Waiting approval
- Failed step

### 9.5 验收标准

```txt
1. 长任务中断后可以恢复或明确失败。
2. Task History 可以被后续任务引用。
3. Project Facts 可以在 Web UI 中查看和编辑。
4. Reflection Memory 需要 Review 后才能启用。
5. Worker 执行任务时能收到相关 Project Facts。
```

---

## 10. Phase 5：多项目、多 PM Agent、平台化

周期：6-8 周

目标：

从单项目运行时变成多项目 AI Worker 平台。

### 10.1 功能范围

- 多项目隔离
- 多 PM Agent 注册
- PM Agent API Key
- Agent 权限边界
- Project Quota
- Worker Pool 分组
- 成本统计
- 任务模板
- Skill Registry
- Project Dashboard
- Organization Settings

### 10.2 PM Agent 协作

PM Agent 可以：

- 创建任务
- 查询任务状态
- 追加需求
- 请求 Review
- 获取交付物

PM Agent 不能默认：

- 访问所有项目
- 读取所有 Memory
- 调用所有 Tool
- 批准高风险操作

### 10.3 Web UI 新增页面

#### PM Agent Management

- Agent 列表
- API Key
- 项目权限
- 可创建任务类型
- 调用记录
- 禁用/启用

#### Cost Dashboard

- 按项目统计成本
- 按 Worker 统计成本
- 按模型统计成本
- 按任务类型统计成本
- 失败任务浪费成本

#### Skill Registry

- Skill 列表
- 版本
- 适用 Role
- Prompt Template
- Output Schema
- Review Criteria

### 10.4 验收标准

```txt
1. 多个 PM Agent 可以在权限范围内创建任务。
2. 不同项目之间 Workspace、Memory、Secret 隔离。
3. 可以统计每个项目的任务量和成本。
4. Skill 可以版本化管理。
5. Web UI 可以管理 PM Agent 和 Skill。
```

---

## 11. Phase 6：企业级与商业化版本

周期：持续迭代

目标：

把平台变成可部署、可销售、可运维的企业级产品。

### 11.1 企业级能力

- SSO / OIDC
- Organization / Team
- Multi-tenant
- Advanced RBAC
- Audit Export
- Compliance Report
- Private Deployment
- Kubernetes Worker Pool
- HA Runtime API
- Backup / Restore
- Usage Billing
- SLA Monitor

### 11.2 商业化版本

推荐版本：

#### Community

- 单机部署
- 单项目
- Local Worker
- 基础 CLI
- 基础 Web UI

#### Team

- 多项目
- 多 Worker
- Web UI
- Tool Registry
- Audit Log
- Role 权限

#### Enterprise

- SSO
- 多租户
- 高级权限
- 私有部署
- Kubernetes Worker Pool
- Compliance
- Support SLA

### 11.3 Web UI 企业级页面

- Organization Settings
- Team Management
- Billing
- Compliance
- Audit Export
- Worker Cluster
- Deployment Status
- System Health

---

## 12. Web UI 总体设计

Web UI 是最终产品的核心入口，不是附属功能。

### 12.1 信息架构

```txt
Dashboard

Projects
  Project Detail
  Project Facts
  Project Tasks
  Project Artifacts
  Project Settings

Tasks
  Task Queue
  Task Detail
  Review Center

Workers
  Worker Dashboard
  Worker Detail
  Worker Pool

Tools
  Tool Registry
  Approval Center

Memory
  Project Facts
  Task History
  Reflection Memory

Artifacts
  Diff Viewer
  Logs
  Reports
  Preview URLs

Audit
  Audit Log
  Tool Calls
  Security Events

Settings
  Users
  Roles
  PM Agents
  Secrets
  Runtime Config
```

### 12.2 首屏 Dashboard

首屏必须让用户一眼知道系统是否健康。

模块：

- Active Tasks
- Waiting Review
- Failed Tasks
- Online Workers
- Queue Depth
- Average Runtime
- Tool Approval Pending
- Recent Deliveries
- System Health

### 12.3 Task Detail 页面

Task Detail 是最重要页面。

布局建议：

```txt
Header
  Title / Status / Priority / Project / Actions

Left Panel
  Task description
  Acceptance criteria
  Runtime context

Center Panel
  Timeline
  Logs
  Tool calls
  Validation results

Right Panel
  Worker
  Session
  Artifacts
  Cost

Bottom / Tab
  Diff viewer
  Review comments
```

关键操作：

- Pause
- Cancel
- Retry
- Request Revision
- Approve
- Complete
- Download Artifact

### 12.4 Worker Detail 页面

展示：

- Worker ID
- Worker Type
- Role
- Status
- Capabilities
- Tools
- Current Session
- Recent Tasks
- Success Rate
- Failure Rate
- Average Duration
- Cost
- Heartbeat
- Logs

操作：

- Disable
- Drain
- Restart instruction
- Change role
- Change concurrency

### 12.5 Diff Review 页面

能力：

- 文件树
- Side-by-side diff
- Changed files summary
- Validation result
- Reviewer comments
- Approve / Request changes
- Create PR

### 12.6 Tool Registry 页面

展示：

- Tool name
- Version
- Type
- Risk level
- Allowed roles
- Required secrets
- Approval required
- Enabled status

操作：

- Enable / Disable
- Update version
- Change policy
- View tool call history

---

## 13. 推荐技术栈

### 13.1 Backend

- Python
- FastAPI
- SQLAlchemy / SQLModel
- PostgreSQL
- Alembic

### 13.2 Workflow

- Phase 0-2：PostgreSQL queue 或 Redis Queue
- Phase 4 起：Temporal

### 13.3 Worker Runtime

- Python Worker SDK
- Docker Sandbox
- Git worktree
- MCP client

### 13.4 Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- Monaco Editor 或 CodeMirror

### 13.5 Storage

- 本地文件系统起步
- S3-compatible object storage 演进

### 13.6 Auth

- Phase 1：API Key
- Phase 3：User Auth + RBAC
- Phase 6：OIDC / SSO

---

## 14. 推荐代码仓库结构

```txt
ai-runtime-os/
  apps/
    api/
    web/
    cli/

  packages/
    runtime-core/
    worker-sdk/
    scheduler/
    skill-registry/
    tool-registry/
    memory/

  workers/
    local-worker/
    claude-worker/
    openai-worker/

  infra/
    docker/
    migrations/
    temporal/
    k8s/

  docs/
    product/
    architecture/
    api/
    worker-protocol/

  examples/
    nextjs-demo/
    python-demo/
```

---

## 15. 数据模型总览

核心表：

```txt
organizations
users
projects
project_members
pm_agents
workers
worker_heartbeats
roles
skills
tools
tool_policies
tasks
task_events
sessions
session_logs
tool_calls
artifacts
project_facts
task_history
reflection_memory
approvals
audit_events
secrets_metadata
cost_records
```

Phase 1 必须表：

```txt
projects
tasks
workers
sessions
task_events
artifacts
audit_events
```

Phase 2 增加：

```txt
roles
worker_heartbeats
session_logs
```

Phase 3 增加：

```txt
tools
tool_policies
tool_calls
approvals
secrets_metadata
```

Phase 4 增加：

```txt
project_facts
task_history
reflection_memory
```

Phase 5/6 增加：

```txt
organizations
users
project_members
pm_agents
cost_records
```

---

## 16. 开发优先级

### 必须先做

1. Task 状态机
2. Worker 注册和心跳
3. Session Workspace
4. Git diff artifact
5. Web Task Detail
6. Audit Event

### 第二优先级

1. 多 Worker 调度
2. Worker Dashboard
3. Review Center
4. Tool Registry
5. Approval Gate

### 第三优先级

1. Durable Workflow
2. Memory Plane
3. PM Agent 管理
4. Cost Dashboard
5. Enterprise Auth

---

## 17. 风险与控制

### 17.1 产品范围过大

风险：

一开始就做 OS，导致半年没有可用产品。

控制：

每个 Phase 必须能独立演示和交付。

### 17.2 Worker 行为不可控

风险：

Worker 调用工具、修改文件、部署服务时产生不可控副作用。

控制：

Workspace 隔离、Tool Policy、Approval Gate、Audit Log。

### 17.3 长任务不可恢复

风险：

任务运行中断后状态丢失。

控制：

Heartbeat、Session State、Task Events、Phase 4 引入 Workflow Engine。

### 17.4 Memory 污染

风险：

错误经验被写入长期记忆。

控制：

Reflection Memory 默认需要 Review，带置信度、范围和过期时间。

### 17.5 Web UI 变成装饰

风险：

只有 CLI 能用，UI 不能管理真实流程。

控制：

Phase 1 就引入最小 Task UI，Phase 2 起所有核心流程必须能在 UI 中完成。

---

## 18. 最终验收标准

最终版本需要达到：

```txt
1. 支持多个项目同时运行。
2. 支持多个 PM Agent 创建和管理任务。
3. 支持多个异构 Worker 注册和调度。
4. 支持任务失败恢复、重试、取消、审批。
5. 支持隔离 Workspace 和标准化交付物。
6. 支持 Tool Registry、权限控制和审计。
7. 支持结构化 Memory 和 Review。
8. 支持完整 Web UI 管理界面。
9. 支持成本统计和 Worker 质量评估。
10. 支持企业级权限、审计导出和私有部署。
```

---

## 19. 建议的第一条开发线

如果现在开始开发，不要先做所有模块。

第一条开发线：

```txt
Project
  -> Task
  -> Worker
  -> Session
  -> Workspace
  -> Diff Artifact
  -> Web Task Detail
```

这条线打通以后，产品就有生命。

第二条开发线：

```txt
Worker Pool
  -> Scheduler
  -> Heartbeat
  -> Retry
  -> Worker Dashboard
```

第三条开发线：

```txt
Tool Registry
  -> Tool Policy
  -> Approval
  -> Audit Log
```

第四条开发线：

```txt
Memory
  -> Project Facts
  -> Task History
  -> Reflection Review
```

---

## 20. 最终结论

AI Runtime OS 的最终规划可以很大，但执行路径必须很窄。

正确路径是：

```txt
先做任务闭环。
再做多 Worker 调度。
再做权限和工具治理。
再做 Memory 和长任务恢复。
最后做平台化和企业级能力。
```

Web UI 必须从 Phase 1 开始进入产品，而不是最后补。

最终产品不是一个“会聊天的 AI 系统”，而是一个能管理 AI 劳动力的运行时平台。

它的核心价值是：

- 让 AI Worker 可调度
- 让 AI 执行过程可观察
- 让 AI 工具调用可审计
- 让 AI 交付物可 Review
- 让 AI 项目状态可恢复

最终对外定位：

> AI Runtime OS：面向 AI Worker 的任务运行时与管理控制台。

