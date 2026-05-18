from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class RuntimeClientError(RuntimeError):
    pass


class RuntimeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8777", agent_id: str | None = None, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.token = token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, auth: bool = True, timeout: int = 30) -> Any:
        data = None
        headers = {"Content-Type": "application/json"}
        if auth:
            if not self.token:
                raise RuntimeClientError("Missing agent token")
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeClientError(f"{method} {path} failed: {exc.code} {body}") from exc

    def register_agent(
        self,
        name: str,
        agent_kind: str,
        role: str = "dev_worker",
        capabilities: list[str] | None = None,
        tools: list[str] | None = None,
        endpoint_url: str | None = None,
        max_concurrency: int = 1,
    ) -> dict[str, Any]:
        agent = self.request(
            "POST",
            "/api/remote-agents/register",
            {
                "name": name,
                "agent_kind": agent_kind,
                "role": role,
                "capabilities": capabilities or ["git"],
                "tools": tools or ["git"],
                "endpoint_url": endpoint_url,
                "max_concurrency": max_concurrency,
            },
            auth=False,
        )
        self.agent_id = agent["id"]
        self.token = agent["token"]
        return agent

    def heartbeat(self) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/heartbeat")

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/tasks", payload)

    def create_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/pm/plans", payload)

    def create_plan_task(self, plan_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/pm/plans/{plan_id}/tasks", payload)

    def claim(self) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/claim")

    def log(self, session_id: str, message: str, level: str = "info") -> dict[str, Any]:
        return self.logs(session_id, [{"level": level, "message": message}])

    def logs(self, session_id: str, entries: list[dict[str, str]]) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/sessions/{session_id}/logs", {"entries": entries})

    def complete(
        self,
        session_id: str,
        summary: str,
        validation_status: str = "not_run",
        validation_output: str = "",
        artifacts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/remote-agents/{self._agent_id()}/sessions/{session_id}/complete",
            {
                "summary": summary,
                "validation_status": validation_status,
                "validation_output": validation_output,
                "artifacts": artifacts or [],
            },
        )

    def fail(self, session_id: str, reason: str) -> dict[str, Any]:
        return self.request("POST", f"/api/remote-agents/{self._agent_id()}/sessions/{session_id}/fail", {"reason": reason})

    def _agent_id(self) -> str:
        if not self.agent_id:
            raise RuntimeClientError("Missing agent id")
        return self.agent_id


class RemotePMClient(RuntimeClient):
    def register(self, name: str, capabilities: list[str] | None = None, tools: list[str] | None = None) -> dict[str, Any]:
        return self.register_agent(name=name, agent_kind="pm", role="pm_agent", capabilities=capabilities or ["planning"], tools=tools or ["api"])


class RemoteWorkerClient(RuntimeClient):
    def register(
        self,
        name: str,
        role: str = "dev_worker",
        capabilities: list[str] | None = None,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.register_agent(
            name=name,
            agent_kind="worker",
            role=role,
            capabilities=capabilities or ["git", "python"],
            tools=tools or ["git", "terminal"],
        )


class RemoteVibeClient(RuntimeClient):
    def register(
        self,
        name: str,
        role: str = "dev_worker",
        capabilities: list[str] | None = None,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.register_agent(
            name=name,
            agent_kind="vibe",
            role=role,
            capabilities=capabilities or ["design", "content"],
            tools=tools or ["api"],
        )

