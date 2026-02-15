"""
Sub-agent manager for Gulama.

Supports spawning background sub-agents for:
- Long-running tasks (research, data processing)
- Scheduled actions (daily summaries, memory cleanup)
- Parallel tool execution
- Autonomous background monitoring

Each sub-agent gets its own AgentBrain instance and runs in an
asyncio Task. Results are collected and stored in memory.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("sub_agents")


class SubAgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution."""
    agent_id: str
    status: SubAgentStatus
    output: str = ""
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tools_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0


class SubAgentManager:
    """
    Manages background sub-agents for parallel and scheduled tasks.

    Sub-agents run as asyncio Tasks with their own AgentBrain instance.
    The manager tracks all running agents and collects results.
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        self._agents: dict[str, SubAgentResult] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._max_concurrent = max_concurrent

    @property
    def active_count(self) -> int:
        """Number of currently running sub-agents."""
        return sum(
            1 for r in self._agents.values()
            if r.status == SubAgentStatus.RUNNING
        )

    def list_agents(self) -> list[dict[str, Any]]:
        """List all sub-agents and their status."""
        return [
            {
                "id": r.agent_id,
                "status": r.status.value,
                "output_preview": r.output[:100] if r.output else "",
                "error": r.error,
                "started_at": str(r.started_at) if r.started_at else None,
                "completed_at": str(r.completed_at) if r.completed_at else None,
                "tools_used": r.tools_used,
                "tokens_used": r.tokens_used,
            }
            for r in self._agents.values()
        ]

    def get_result(self, agent_id: str) -> SubAgentResult | None:
        """Get result of a specific sub-agent."""
        return self._agents.get(agent_id)

    async def spawn(
        self,
        message: str,
        channel: str = "sub_agent",
        user_id: str | None = None,
    ) -> str:
        """
        Spawn a new background sub-agent.

        Returns the agent_id for tracking.
        """
        if self.active_count >= self._max_concurrent:
            raise RuntimeError(
                f"Maximum concurrent sub-agents ({self._max_concurrent}) reached. "
                "Wait for a running agent to complete."
            )

        agent_id = f"sa-{str(uuid.uuid4())[:8]}"

        result = SubAgentResult(
            agent_id=agent_id,
            status=SubAgentStatus.PENDING,
        )
        self._agents[agent_id] = result

        task = asyncio.create_task(
            self._run_agent(agent_id, message, channel, user_id)
        )
        self._tasks[agent_id] = task

        logger.info("sub_agent_spawned", agent_id=agent_id, message=message[:80])
        return agent_id

    async def _run_agent(
        self,
        agent_id: str,
        message: str,
        channel: str,
        user_id: str | None,
    ) -> None:
        """Run a sub-agent in the background."""
        result = self._agents[agent_id]
        result.status = SubAgentStatus.RUNNING
        result.started_at = datetime.now(timezone.utc)

        try:
            # Lazy import to avoid circular deps
            from src.agent.brain import AgentBrain
            from src.gateway.config import load_config

            config = load_config()
            brain = AgentBrain(config=config)

            response = await brain.process_message(
                message=message,
                channel=channel,
                user_id=user_id,
            )

            result.status = SubAgentStatus.COMPLETED
            result.output = response.get("response", "")
            result.tools_used = response.get("tools_used", [])
            result.tokens_used = response.get("tokens_used", 0)
            result.cost_usd = response.get("cost_usd", 0.0)

            logger.info(
                "sub_agent_completed",
                agent_id=agent_id,
                tools=result.tools_used,
                tokens=result.tokens_used,
            )

        except asyncio.CancelledError:
            result.status = SubAgentStatus.CANCELLED
            logger.info("sub_agent_cancelled", agent_id=agent_id)

        except Exception as e:
            result.status = SubAgentStatus.FAILED
            result.error = str(e)[:500]
            logger.error("sub_agent_failed", agent_id=agent_id, error=str(e))

        finally:
            result.completed_at = datetime.now(timezone.utc)
            self._tasks.pop(agent_id, None)

    async def cancel(self, agent_id: str) -> bool:
        """Cancel a running sub-agent."""
        task = self._tasks.get(agent_id)
        if task and not task.done():
            task.cancel()
            logger.info("sub_agent_cancel_requested", agent_id=agent_id)
            return True
        return False

    async def cancel_all(self) -> int:
        """Cancel all running sub-agents."""
        cancelled = 0
        for agent_id, task in list(self._tasks.items()):
            if not task.done():
                task.cancel()
                cancelled += 1
        if cancelled:
            logger.info("sub_agents_cancelled", count=cancelled)
        return cancelled

    def cleanup_completed(self, keep_last: int = 20) -> int:
        """Remove old completed/failed results, keeping the last N."""
        completed = [
            (aid, r) for aid, r in self._agents.items()
            if r.status in (SubAgentStatus.COMPLETED, SubAgentStatus.FAILED, SubAgentStatus.CANCELLED)
        ]
        # Sort by completion time
        completed.sort(key=lambda x: x[1].completed_at or datetime.min.replace(tzinfo=timezone.utc))

        removed = 0
        while len(completed) > keep_last:
            aid, _ = completed.pop(0)
            del self._agents[aid]
            removed += 1
        return removed


# ── Scheduler handler wiring ──────────────────────────────────


def create_scheduler_handlers(
    sub_agent_manager: SubAgentManager,
) -> dict[str, Any]:
    """
    Create handler functions for the TaskScheduler action types.

    Returns a dict of action_type -> async handler function.
    """

    async def handle_message(config: dict[str, Any]) -> None:
        """Handle 'message' scheduled tasks — send a message to the agent."""
        message = config.get("message", "")
        if not message:
            logger.warning("scheduled_message_empty")
            return
        await sub_agent_manager.spawn(
            message=message,
            channel="scheduler",
        )

    async def handle_skill(config: dict[str, Any]) -> None:
        """Handle 'skill' scheduled tasks — execute a specific skill."""
        skill_name = config.get("skill", "")
        skill_args = config.get("args", {})
        if not skill_name:
            logger.warning("scheduled_skill_empty")
            return
        # Wrap as a tool-use request
        message = f"Execute the {skill_name} tool with these arguments: {skill_args}"
        await sub_agent_manager.spawn(
            message=message,
            channel="scheduler",
        )

    async def handle_summarize(config: dict[str, Any]) -> None:
        """Handle 'summarize' scheduled tasks — trigger memory summarization."""
        await sub_agent_manager.spawn(
            message=(
                "Summarize all conversations from the last 24 hours. "
                "Extract key facts, decisions, and action items. "
                "Store the summary for future reference."
            ),
            channel="scheduler",
        )

    async def handle_heartbeat(config: dict[str, Any]) -> None:
        """Handle 'heartbeat' scheduled tasks — health check."""
        logger.info("heartbeat_ok")

    return {
        "message": handle_message,
        "skill": handle_skill,
        "summarize": handle_summarize,
        "heartbeat": handle_heartbeat,
    }
