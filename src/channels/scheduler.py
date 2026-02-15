"""
Cron / scheduled tasks for Gulama.

Supports:
- Cron expression scheduling (e.g., "0 9 * * *" = daily at 9am)
- Interval-based scheduling (e.g., every 30 minutes)
- One-time delayed tasks
- Heartbeat checks (periodic health pings)
- Memory summarization triggers
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine

from src.utils.logging import get_logger

logger = get_logger("scheduler")


@dataclass
class ScheduledTask:
    """A scheduled task definition."""
    id: str
    name: str
    schedule_type: str  # "cron", "interval", "once"
    schedule_value: str  # cron expression, interval seconds, or ISO datetime
    action_type: str  # "message", "skill", "summarize", "heartbeat", "custom"
    action_config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0


class CronParser:
    """Simple cron expression parser (minute, hour, day, month, weekday)."""

    @staticmethod
    def matches(expression: str, dt: datetime) -> bool:
        """Check if a datetime matches a cron expression."""
        parts = expression.strip().split()
        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        return (
            CronParser._field_matches(minute, dt.minute, 0, 59)
            and CronParser._field_matches(hour, dt.hour, 0, 23)
            and CronParser._field_matches(day, dt.day, 1, 31)
            and CronParser._field_matches(month, dt.month, 1, 12)
            and CronParser._field_matches(weekday, dt.weekday(), 0, 6)
        )

    @staticmethod
    def _field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
        """Check if a single cron field matches a value."""
        if field == "*":
            return True

        # Handle */N (every N)
        if field.startswith("*/"):
            step = int(field[2:])
            return value % step == 0

        # Handle N-M (range)
        if "-" in field:
            start, end = field.split("-", 1)
            return int(start) <= value <= int(end)

        # Handle comma-separated values
        if "," in field:
            values = [int(v) for v in field.split(",")]
            return value in values

        # Exact value
        try:
            return value == int(field)
        except ValueError:
            return False

    @staticmethod
    def next_run(expression: str, after: datetime | None = None) -> datetime | None:
        """Calculate the next run time for a cron expression."""
        if after is None:
            after = datetime.now(timezone.utc)

        # Check every minute for the next 48 hours
        check_time = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        max_check = after + timedelta(hours=48)

        while check_time < max_check:
            if CronParser.matches(expression, check_time):
                return check_time
            check_time += timedelta(minutes=1)

        return None


class TaskScheduler:
    """
    Manages scheduled tasks and their execution.

    Task types:
    - message: Send a pre-configured message to the agent
    - skill: Execute a specific skill
    - summarize: Trigger memory summarization
    - heartbeat: Health check ping
    - custom: Run a custom async function
    """

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._handlers: dict[str, Callable[..., Coroutine]] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    def register_handler(
        self, action_type: str, handler: Callable[..., Coroutine]
    ) -> None:
        """Register a handler for a task action type."""
        self._handlers[action_type] = handler
        logger.debug("handler_registered", action_type=action_type)

    def add_task(
        self,
        name: str,
        schedule_type: str,
        schedule_value: str,
        action_type: str,
        action_config: dict[str, Any] | None = None,
    ) -> str:
        """Add a new scheduled task."""
        task_id = str(uuid.uuid4())[:8]

        task = ScheduledTask(
            id=task_id,
            name=name,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            action_type=action_type,
            action_config=action_config or {},
        )

        # Calculate initial next_run
        task.next_run = self._calculate_next_run(task)

        self._tasks[task_id] = task
        logger.info(
            "task_added",
            task_id=task_id,
            name=name,
            schedule=f"{schedule_type}:{schedule_value}",
            next_run=str(task.next_run),
        )
        return task_id

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info("task_removed", task_id=task_id)
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = True
            task.next_run = self._calculate_next_run(task)
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = False
            return True
        return False

    def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks with their status."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "schedule_type": t.schedule_type,
                "schedule_value": t.schedule_value,
                "action_type": t.action_type,
                "enabled": t.enabled,
                "last_run": str(t.last_run) if t.last_run else None,
                "next_run": str(t.next_run) if t.next_run else None,
                "run_count": t.run_count,
            }
            for t in self._tasks.values()
        ]

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("scheduler_started", tasks=len(self._tasks))

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler_stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop — checks every 30 seconds."""
        while self._running:
            now = datetime.now(timezone.utc)

            for task in list(self._tasks.values()):
                if not task.enabled or not task.next_run:
                    continue

                if now >= task.next_run:
                    await self._execute_task(task)
                    task.last_run = now
                    task.run_count += 1

                    # Remove one-time tasks after execution
                    if task.schedule_type == "once":
                        task.enabled = False
                    else:
                        task.next_run = self._calculate_next_run(task)

            await asyncio.sleep(30)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        logger.info("task_executing", task_id=task.id, name=task.name)

        handler = self._handlers.get(task.action_type)
        if not handler:
            logger.warning("no_handler", action_type=task.action_type)
            return

        try:
            await handler(task.action_config)
            logger.info("task_completed", task_id=task.id, name=task.name)
        except Exception as e:
            logger.error("task_failed", task_id=task.id, error=str(e))

    @staticmethod
    def _calculate_next_run(task: ScheduledTask) -> datetime | None:
        """Calculate the next run time for a task."""
        now = datetime.now(timezone.utc)

        if task.schedule_type == "cron":
            return CronParser.next_run(task.schedule_value, now)

        elif task.schedule_type == "interval":
            seconds = int(task.schedule_value)
            if task.last_run:
                return task.last_run + timedelta(seconds=seconds)
            return now + timedelta(seconds=seconds)

        elif task.schedule_type == "once":
            try:
                run_at = datetime.fromisoformat(task.schedule_value)
                if run_at.tzinfo is None:
                    run_at = run_at.replace(tzinfo=timezone.utc)
                if run_at > now:
                    return run_at
            except ValueError:
                pass

        return None

    # --- Built-in task types ---

    def add_heartbeat(self, interval_seconds: int = 300) -> str:
        """Add a heartbeat task that runs every N seconds."""
        return self.add_task(
            name="Heartbeat",
            schedule_type="interval",
            schedule_value=str(interval_seconds),
            action_type="heartbeat",
        )

    def add_daily_summary(self, hour: int = 9, minute: int = 0) -> str:
        """Add a daily summary task."""
        return self.add_task(
            name="Daily Summary",
            schedule_type="cron",
            schedule_value=f"{minute} {hour} * * *",
            action_type="message",
            action_config={"message": "Generate a daily summary of yesterday's activities."},
        )

    def add_memory_cleanup(self, interval_hours: int = 24) -> str:
        """Add a periodic memory summarization task."""
        return self.add_task(
            name="Memory Cleanup",
            schedule_type="interval",
            schedule_value=str(interval_hours * 3600),
            action_type="summarize",
        )
