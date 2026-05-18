const state = {
  view: "dashboard",
  lang: localStorage.getItem("runtime-lang") || "en",
  projects: [],
  plans: [],
  tasks: [],
  workers: [],
  audit: [],
  runners: [],
  remoteAgents: [],
  lastAgentToken: null,
};

const i18n = {
  en: {
    brandSubtitle: "Agent runtime console",
    navDashboard: "Dashboard",
    navPlans: "PM Plans",
    navTasks: "Tasks",
    navProjects: "Projects",
    navWorkers: "Workers",
    navAgents: "Agents",
    navAudit: "Audit",
    refresh: "Refresh",
    languageToggle: "中文",
    metricQueued: "Queued",
    metricRunning: "Running",
    metricReview: "Waiting Review",
    metricWorkers: "Workers",
    recentTasks: "Recent Tasks",
    pmPlans: "PM Plans",
    createPlan: "Create PM Plan",
    objective: "Objective",
    planTitlePlaceholder: "Build worker dashboard",
    objectivePlaceholder: "Describe the outcome PM agents should plan and deliver.",
    noPlans: "No PM plans yet.",
    planProgress: "Progress",
    childTasks: "Child tasks",
    createTask: "Create Task",
    project: "Project",
    title: "Title",
    description: "Description",
    validationCommand: "Validation command",
    priority: "Priority",
    maxRetries: "Max retries",
    acceptanceCriteria: "Acceptance criteria",
    taskQueue: "Task Queue",
    createProject: "Create Project",
    name: "Name",
    localRepoPath: "Local repo path",
    gitRepoUrl: "Git repo URL",
    defaultBranch: "Default branch",
    auditEvents: "Audit Events",
    noTasks: "No tasks yet.",
    noProjects: "No projects yet.",
    noRepo: "No repo bound",
    noArtifacts: "No artifacts yet.",
    noWorkers: "No workers registered.",
    noAudit: "No audit events.",
    open: "Open",
    complete: "Complete",
    merge: "Merge",
    requestRevision: "Request Revision",
    retry: "Retry",
    cancel: "Cancel",
    taskTitlePlaceholder: "Add landing page",
    criteriaPlaceholder: "One item per line",
    capabilities: "Capabilities",
    tools: "Tools",
    currentSession: "Current session",
    workerRunners: "Worker Runners",
    remoteAgents: "Remote Agents",
    registerAgent: "Register Remote Agent",
    agentKind: "Agent kind",
    role: "Role",
    noAgents: "No remote agents registered.",
    tokenCreated: "Token created. Store it now; it will not be shown again.",
    rotateToken: "Rotate token",
    startDryRun: "Start Dry Run",
    startClaude: "Start Claude DeepSeek",
    startKimi: "Start Kimi Code",
    startOpenCode: "Start OpenCode",
    stop: "Stop",
    running: "running",
    stopped: "stopped",
    noRunners: "No managed worker runners",
    retries: "Retries",
    disable: "Disable",
    enable: "Enable",
    drain: "Drain",
    none: "none",
    page: {
      dashboard: ["Command Center", "Runtime health, queue, and review status."],
      plans: ["PM Plans", "Create goals that PM agents decompose into executable tasks."],
      tasks: ["Tasks", "Create tasks, inspect logs, and review artifacts."],
      projects: ["Projects", "Bind repos and manage project runtime roots."],
      workers: ["Workers", "Worker status, capabilities, and current sessions."],
      agents: ["Agents", "Remote PM, Worker, and Vibe agents connected through the protocol."],
      audit: ["Audit", "Recent runtime and worker events."],
    },
    headings: {
      description: "Description",
      acceptanceCriteria: "Acceptance Criteria",
      events: "Events",
      sessionLogs: "Session Logs",
      artifacts: "Artifacts",
    },
  },
  zh: {
    brandSubtitle: "Agent 运行中枢",
    navDashboard: "仪表盘",
    navPlans: "PM 计划",
    navTasks: "任务",
    navProjects: "项目",
    navWorkers: "Worker",
    navAgents: "Agent",
    navAudit: "审计",
    refresh: "刷新",
    languageToggle: "EN",
    metricQueued: "排队中",
    metricRunning: "运行中",
    metricReview: "待审核",
    metricWorkers: "Worker",
    recentTasks: "最近任务",
    pmPlans: "PM 计划",
    createPlan: "创建 PM 计划",
    objective: "目标",
    planTitlePlaceholder: "构建 Worker 仪表盘",
    objectivePlaceholder: "描述 PM Agent 需要规划并交付的结果。",
    noPlans: "还没有 PM 计划。",
    planProgress: "进度",
    childTasks: "子任务",
    createTask: "创建任务",
    project: "项目",
    title: "标题",
    description: "描述",
    validationCommand: "验证命令",
    priority: "优先级",
    maxRetries: "最大重试次数",
    acceptanceCriteria: "验收标准",
    taskQueue: "任务队列",
    createProject: "创建项目",
    name: "名称",
    localRepoPath: "本地仓库路径",
    gitRepoUrl: "Git 仓库 URL",
    defaultBranch: "默认分支",
    auditEvents: "审计事件",
    noTasks: "还没有任务。",
    noProjects: "还没有项目。",
    noRepo: "未绑定仓库",
    noArtifacts: "还没有交付物。",
    noWorkers: "还没有注册 Worker。",
    noAudit: "还没有审计事件。",
    open: "打开",
    complete: "完成",
    merge: "合并",
    requestRevision: "要求返工",
    retry: "重试",
    cancel: "取消",
    taskTitlePlaceholder: "新增落地页",
    criteriaPlaceholder: "每行一条验收标准",
    capabilities: "能力",
    tools: "工具",
    currentSession: "当前 Session",
    workerRunners: "Worker 运行器",
    remoteAgents: "远程 Agent",
    registerAgent: "注册远程 Agent",
    agentKind: "Agent 类型",
    role: "角色",
    noAgents: "还没有远程 Agent。",
    tokenCreated: "Token 已创建，请立即保存；之后不会再次显示。",
    rotateToken: "轮换 Token",
    startDryRun: "启动 Dry Run",
    startClaude: "启动 Claude DeepSeek",
    startKimi: "启动 Kimi Code",
    startOpenCode: "启动 OpenCode",
    stop: "停止",
    running: "运行中",
    stopped: "已停止",
    noRunners: "暂无托管 Worker 运行器",
    retries: "重试",
    disable: "禁用",
    enable: "启用",
    drain: "排空",
    none: "无",
    page: {
      dashboard: ["指挥中心", "Runtime 健康状态、任务队列和待审核情况。"],
      plans: ["PM 计划", "创建目标，由 PM Agent 自动拆解为可执行任务。"],
      tasks: ["任务", "创建任务、查看日志并审核交付物。"],
      projects: ["项目", "绑定代码仓库并管理项目运行时。"],
      workers: ["Worker", "查看 Worker 状态、能力和当前 Session。"],
      agents: ["Agent", "通过协议接入的远程 PM、Worker 和 Vibe Agent。"],
      audit: ["审计", "最近的 Runtime 与 Worker 事件。"],
    },
    headings: {
      description: "描述",
      acceptanceCriteria: "验收标准",
      events: "事件",
      sessionLogs: "Session 日志",
      artifacts: "交付物",
    },
  },
};

function t(key) {
  return i18n[state.lang][key] || i18n.en[key] || key;
}

function pageTitle(view) {
  return i18n[state.lang].page[view] || i18n.en.page[view];
}

function applyStaticText() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.getElementById("language-toggle").textContent = t("languageToggle");
  const [title, subtitle] = pageTitle(state.view);
  document.getElementById("page-title").textContent = title;
  document.getElementById("page-subtitle").textContent = subtitle;
}

function toggleLanguage() {
  state.lang = state.lang === "en" ? "zh" : "en";
  localStorage.setItem("runtime-lang", state.lang);
  render();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    const error = new Error(detail || response.statusText);
    showToast(error.message, "error");
    throw error;
  }
  return response.json();
}

function showToast(message, tone = "info") {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.className = `toast ${tone}`;
  toast.textContent = message;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.className = "toast";
    toast.textContent = "";
  }, 4200);
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach((el) => el.classList.toggle("active", el.id === view));
  document.querySelectorAll(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  applyStaticText();
}

async function refresh() {
  const [projects, plans, tasks, workers, audit, runners, remoteAgents] = await Promise.all([
    api("/api/projects"),
    api("/api/pm/plans"),
    api("/api/tasks"),
    api("/api/workers"),
    api("/api/audit-events"),
    api("/api/worker-runners"),
    api("/api/remote-agents"),
  ]);
  state.projects = projects;
  state.plans = plans;
  state.tasks = tasks;
  state.workers = workers;
  state.audit = audit;
  state.runners = runners;
  state.remoteAgents = remoteAgents;
  render();
}

function statusBadge(status) {
  return `<span class="status ${status}">${status}</span>`;
}

function render() {
  renderDashboard();
  renderProjects();
  renderPlanFormProjects();
  renderPlans();
  renderTaskFormProjects();
  renderTasks();
  renderRunners();
  renderWorkers();
  renderRemoteAgents();
  renderAudit();
  applyStaticText();
}

function renderDashboard() {
  document.getElementById("metric-queued").textContent = state.tasks.filter((task) => task.status === "queued").length;
  document.getElementById("metric-running").textContent = state.tasks.filter((task) => task.status === "running").length;
  document.getElementById("metric-review").textContent = state.tasks.filter((task) => task.status === "waiting_review").length;
  document.getElementById("metric-workers").textContent = state.workers.length;
  document.getElementById("recent-tasks").innerHTML = state.tasks.slice(0, 8).map(taskItem).join("") || empty(t("noTasks"));
}

function renderProjects() {
  document.getElementById("project-list").innerHTML =
    state.projects
      .map(
        (project) => `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(project.name)}</div>
            ${statusBadge(project.status)}
          </div>
          <div class="meta">${escapeHtml(project.id)}</div>
          <div class="meta">${escapeHtml(project.repo_path || project.repo_url || t("noRepo"))}</div>
        </div>`
      )
      .join("") || empty(t("noProjects"));
}

function renderTaskFormProjects() {
  const select = document.getElementById("task-project");
  select.innerHTML = state.projects.map((project) => `<option value="${project.id}">${escapeHtml(project.name)}</option>`).join("");
}

function renderPlanFormProjects() {
  const select = document.getElementById("plan-project");
  if (!select) return;
  select.innerHTML = state.projects.map((project) => `<option value="${project.id}">${escapeHtml(project.name)}</option>`).join("");
}

function renderPlans() {
  const target = document.getElementById("plan-list");
  if (!target) return;
  target.innerHTML = state.plans.map(planItem).join("") || empty(t("noPlans"));
}

function planItem(plan) {
  const progress = plan.progress || { total: 0, completed: 0, counts: {} };
  const childTasks = plan.tasks || [];
  return `
    <div class="item">
      <div class="item-head">
        <div class="item-title">${escapeHtml(plan.title)}</div>
        ${statusBadge(plan.status)}
      </div>
      <div class="meta">${escapeHtml(plan.id)} · ${t("project")} ${escapeHtml(plan.project_id)}</div>
      <div class="meta">${t("planProgress")}: ${escapeHtml(progress.completed)}/${escapeHtml(progress.total)} · ${escapeHtml(formatCounts(progress.counts || {}))}</div>
      <div class="meta">${escapeHtml(plan.objective)}</div>
      <div class="plan-child-list">
        <strong>${t("childTasks")}</strong>
        ${(childTasks || [])
          .map(
            (task) => `
              <div class="child-task">
                <button class="linklike" onclick="setView('tasks'); showTask('${task.id}')">${escapeHtml(task.plan_sequence || "")}. ${escapeHtml(task.title)}</button>
                ${statusBadge(task.status)}
              </div>`
          )
          .join("")}
      </div>
    </div>`;
}

function formatCounts(counts) {
  return Object.keys(counts)
    .sort()
    .map((key) => `${key}:${counts[key]}`)
    .join(", ");
}

function renderTasks() {
  document.getElementById("task-list").innerHTML = state.tasks.map(taskItem).join("") || empty(t("noTasks"));
}

function taskItem(task) {
  return `
    <div class="item">
      <div class="item-head">
        <button class="linklike item-title" onclick="showTask('${task.id}')">${escapeHtml(task.title)}</button>
        ${statusBadge(task.status)}
      </div>
      <div class="meta">${escapeHtml(task.id)} · ${escapeHtml(task.task_type)} · ${t("project")} ${escapeHtml(task.project_id)} · P${escapeHtml(task.priority ?? 50)} · ${t("retries")} ${escapeHtml(task.retry_count ?? 0)}/${escapeHtml(task.max_retries ?? 0)}</div>
      <div class="actions">
        <button class="secondary" onclick="showTask('${task.id}')">${t("open")}</button>
        ${task.status === "waiting_review" ? `<button class="primary" onclick="reviewTask('${task.id}', 'complete')">${t("complete")}</button>` : ""}
        ${canMerge(task.status) ? `<button class="primary" onclick="mergeTask('${task.id}')">${t("merge")}</button>` : ""}
        ${task.status === "waiting_review" ? `<button class="secondary" onclick="reviewTask('${task.id}', 'revision_requested')">${t("requestRevision")}</button>` : ""}
        ${canRetry(task.status) ? `<button class="secondary" onclick="retryTask('${task.id}')">${t("retry")}</button>` : ""}
      </div>
    </div>`;
}

async function showTask(taskId) {
  const [task, sessions] = await Promise.all([api(`/api/tasks/${taskId}`), api(`/api/tasks/${taskId}/sessions`)]);
  const detail = document.getElementById("task-detail");
  const artifacts = task.artifacts || [];
  const latestSession = sessions[0];
  let logs = [];
  if (latestSession) {
    const session = await api(`/api/sessions/${latestSession.id}`);
    logs = session.logs || [];
  }
  const artifactHtml = await Promise.all(
    artifacts.map(async (artifact) => {
      const full = await api(`/api/artifacts/${artifact.id}`);
      return `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(artifact.type)}</div>
            <span class="status">${escapeHtml(artifact.id)}</span>
          </div>
          <div class="meta">${escapeHtml(artifact.uri)}</div>
          <pre>${escapeHtml(full.content || "")}</pre>
        </div>`;
    })
  );
  detail.classList.remove("hidden");
  detail.innerHTML = `
    <div class="item-head">
      <div>
        <div class="panel-title">${escapeHtml(task.title)}</div>
        <div class="meta">${escapeHtml(task.id)} · ${statusBadge(task.status)} · P${escapeHtml(task.priority ?? 50)} · ${t("retries")} ${escapeHtml(task.retry_count ?? 0)}/${escapeHtml(task.max_retries ?? 0)}</div>
      </div>
      <div class="actions">
        ${task.status === "waiting_review" ? `<button class="primary" onclick="reviewTask('${task.id}', 'complete')">${t("complete")}</button>` : ""}
        ${canMerge(task.status) ? `<button class="primary" onclick="mergeTask('${task.id}')">${t("merge")}</button>` : ""}
        ${task.status === "waiting_review" ? `<button class="secondary" onclick="reviewTask('${task.id}', 'revision_requested')">${t("requestRevision")}</button>` : ""}
        ${canRetry(task.status) ? `<button class="secondary" onclick="retryTask('${task.id}')">${t("retry")}</button>` : ""}
        ${!["completed", "merged", "cancelled"].includes(task.status) ? `<button class="danger" onclick="cancelTask('${task.id}')">${t("cancel")}</button>` : ""}
      </div>
    </div>
    <div class="detail-grid">
      <div>
        <h3>${i18n[state.lang].headings.description}</h3>
        <p>${escapeHtml(task.description)}</p>
        <h3>${i18n[state.lang].headings.acceptanceCriteria}</h3>
        <ul>${(task.acceptance_criteria || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        <h3>${i18n[state.lang].headings.events}</h3>
        <div class="list">${(task.events || []).map((event) => `<div class="item"><strong>${escapeHtml(event.event_type)}</strong><div class="meta">${escapeHtml(event.message)}</div></div>`).join("")}</div>
      </div>
      <div>
        <h3>${i18n[state.lang].headings.sessionLogs}</h3>
        <pre>${escapeHtml(logs.map((log) => `[${log.level}] ${log.message}`).join("\n"))}</pre>
      </div>
    </div>
    <h3>${i18n[state.lang].headings.artifacts}</h3>
    <div class="list">${artifactHtml.join("") || empty(t("noArtifacts"))}</div>
  `;
  detail.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderWorkers() {
  document.getElementById("worker-list").innerHTML =
    state.workers
      .map(
        (worker) => `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(worker.id)}</div>
            ${statusBadge(worker.status)}
          </div>
          <div class="meta">${escapeHtml(worker.worker_type)} · ${escapeHtml(worker.role)}</div>
          <div class="meta">${t("capabilities")}: ${(worker.capabilities || []).map(escapeHtml).join(", ")}</div>
          <div class="meta">${t("tools")}: ${(worker.tools || []).map(escapeHtml).join(", ")}</div>
          <div class="meta">${t("currentSession")}: ${escapeHtml(worker.current_session_id || t("none"))}</div>
          <div class="actions">
            ${worker.status === "disabled" || worker.status === "offline" ? `<button class="primary" onclick="workerAction('${worker.id}', 'enable')">${t("enable")}</button>` : ""}
            ${worker.status === "online" ? `<button class="secondary" onclick="workerAction('${worker.id}', 'drain')">${t("drain")}</button>` : ""}
            ${worker.status !== "disabled" ? `<button class="danger" onclick="workerAction('${worker.id}', 'disable')">${t("disable")}</button>` : ""}
          </div>
        </div>`
      )
      .join("") || empty(t("noWorkers"));
}

function renderRunners() {
  const target = document.getElementById("runner-list");
  if (!target) return;
  target.innerHTML =
    state.runners
      .map(
        (runner) => `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(runner.agent)} · ${escapeHtml(runner.id)}</div>
            <span class="status ${runner.running ? "running" : "disabled"}">${runner.running ? t("running") : t("stopped")}</span>
          </div>
          <div class="meta">PID ${escapeHtml(runner.pid)} · ${escapeHtml(runner.log_path)}</div>
          <div class="actions">
            ${runner.running ? `<button class="danger" onclick="stopRunner('${runner.id}')">${t("stop")}</button>` : ""}
          </div>
        </div>`
      )
      .join("") || empty(t("noRunners"));
}

function renderRemoteAgents() {
  const target = document.getElementById("remote-agent-list");
  if (!target) return;
  target.innerHTML =
    state.remoteAgents
      .map(
        (agent) => `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(agent.name)} · ${escapeHtml(agent.id)}</div>
            ${statusBadge(agent.status)}
          </div>
          <div class="meta">${escapeHtml(agent.agent_kind)} · ${escapeHtml(agent.role)} · worker ${escapeHtml(agent.worker_id || t("none"))}</div>
          <div class="meta">${t("capabilities")}: ${(agent.capabilities || []).map(escapeHtml).join(", ")}</div>
          <div class="meta">${t("tools")}: ${(agent.tools || []).map(escapeHtml).join(", ")}</div>
          <div class="actions">
            ${agent.status === "disabled" ? `<button class="primary" onclick="remoteAgentAction('${agent.id}', 'enable')">${t("enable")}</button>` : `<button class="danger" onclick="remoteAgentAction('${agent.id}', 'disable')">${t("disable")}</button>`}
            <button class="secondary" onclick="remoteAgentAction('${agent.id}', 'rotate-token')">${t("rotateToken")}</button>
          </div>
        </div>`
      )
      .join("") || empty(t("noAgents"));

  const tokenBox = document.getElementById("agent-token");
  if (!tokenBox) return;
  if (!state.lastAgentToken) {
    tokenBox.classList.add("hidden");
    tokenBox.textContent = "";
    return;
  }
  tokenBox.classList.remove("hidden");
  tokenBox.textContent = `${t("tokenCreated")} ${state.lastAgentToken.agent_id}: ${state.lastAgentToken.token}`;
}

function renderAudit() {
  document.getElementById("audit-list").innerHTML =
    state.audit
      .map(
        (event) => `
        <div class="item">
          <div class="item-head">
            <div class="item-title">${escapeHtml(event.action)}</div>
            <span class="status">${escapeHtml(event.actor_type)}</span>
          </div>
          <div class="meta">${escapeHtml(event.actor_id)} -> ${escapeHtml(event.resource_type)}:${escapeHtml(event.resource_id)}</div>
        </div>`
      )
      .join("") || empty(t("noAudit"));
}

async function createProject(event) {
  event.preventDefault();
  await api("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: value("project-name"),
      repo_path: value("project-repo-path") || null,
      repo_url: value("project-repo-url") || null,
      default_branch: value("project-branch") || "main",
    }),
  });
  event.target.reset();
  document.getElementById("project-branch").value = "main";
  await refresh();
}

async function createPlan(event) {
  event.preventDefault();
  await api("/api/pm/plans", {
    method: "POST",
    body: JSON.stringify({
      project_id: value("plan-project"),
      title: value("plan-title"),
      objective: value("plan-objective"),
    }),
  });
  event.target.reset();
  await refresh();
}

async function registerRemoteAgent(event) {
  event.preventDefault();
  const agent = await api("/api/remote-agents/register", {
    method: "POST",
    body: JSON.stringify({
      name: value("agent-name"),
      agent_kind: value("agent-kind"),
      role: value("agent-role") || "dev_worker",
      capabilities: lines("agent-capabilities"),
      tools: lines("agent-tools"),
    }),
  });
  state.lastAgentToken = { agent_id: agent.id, token: agent.token };
  event.target.reset();
  document.getElementById("agent-role").value = "dev_worker";
  await refresh();
}

async function remoteAgentAction(agentId, action) {
  const result = await api(`/api/remote-agents/${agentId}/${action}`, { method: "POST" });
  if (result.token) {
    state.lastAgentToken = { agent_id: result.id, token: result.token };
  }
  await refresh();
}

async function createTask(event) {
  event.preventDefault();
  await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({
      project_id: value("task-project"),
      title: value("task-title"),
      description: value("task-description"),
      validation_command: value("task-validation") || null,
      acceptance_criteria: lines("task-criteria"),
    }),
  });
  event.target.reset();
  await refresh();
}

async function reviewTask(taskId, decision) {
  await api(`/api/tasks/${taskId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, message: decision }),
  });
  await refresh();
  await showTask(taskId);
}

async function mergeTask(taskId) {
  await api(`/api/tasks/${taskId}/merge`, {
    method: "POST",
    body: JSON.stringify({ message: `AI Runtime OS merge ${taskId}` }),
  });
  await refresh();
  await showTask(taskId);
}

async function cancelTask(taskId) {
  await api(`/api/tasks/${taskId}/cancel`, { method: "POST" });
  await refresh();
  await showTask(taskId);
}

async function retryTask(taskId) {
  await api(`/api/tasks/${taskId}/retry`, { method: "POST" });
  await refresh();
  await showTask(taskId);
}

function canRetry(status) {
  return ["failed", "cancelled", "revision_requested"].includes(status);
}

function canMerge(status) {
  return ["waiting_review", "completed"].includes(status);
}

function value(id) {
  return document.getElementById(id).value.trim();
}

async function workerAction(workerId, action) {
  await api(`/api/workers/${workerId}/${action}`, { method: "POST" });
  await refresh();
}

async function startRunner(agent) {
  await api("/api/worker-runners/start", {
    method: "POST",
    body: JSON.stringify({ agent, worker_type: `managed_${agent}` }),
  });
  await refresh();
}

async function stopRunner(runnerId) {
  await api(`/api/worker-runners/${runnerId}/stop`, { method: "POST" });
  await refresh();
}

function lines(id) {
  return value(id)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function empty(text) {
  return `<div class="item"><div class="meta">${escapeHtml(text)}</div></div>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});
document.getElementById("refresh").addEventListener("click", refresh);
window.toggleLanguage = toggleLanguage;
window.startRunner = startRunner;
window.stopRunner = stopRunner;
window.remoteAgentAction = remoteAgentAction;
document.getElementById("project-form").addEventListener("submit", createProject);
document.getElementById("plan-form").addEventListener("submit", createPlan);
document.getElementById("task-form").addEventListener("submit", createTask);
document.getElementById("remote-agent-form").addEventListener("submit", registerRemoteAgent);

applyStaticText();
refresh().catch((error) => {
  console.error(error);
  alert(error.message);
});
setInterval(() => {
  if (document.visibilityState === "visible") {
    refresh().catch((error) => console.error(error));
  }
}, 5000);
