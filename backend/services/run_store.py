"""In-memory run store with progress fan-out.

Holds active and recently completed runs so the UI can subscribe to real
progress events over SSE and fetch the result afterwards. In-memory by design
(per the spec's "no database in V1" and cost-control rules) — a restart clears
runs, while the report files on disk persist.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_RUNS_RETAINED = 50
QUEUE_MAXSIZE = 200

# Sentinel pushed onto subscriber queues when a run finishes.
DONE = object()


class Run:
    """One research run: its status, progress events, and eventual result."""

    def __init__(self, run_id: str, brief: Dict[str, Any]) -> None:
        self.run_id = run_id
        self.brief = brief
        self.status = "running"  # running | completed | partial | failed
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self.events: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.error_stage: Optional[str] = None
        self._subscribers: List[asyncio.Queue] = []

    # --- progress ----------------------------------------------------------

    async def publish(self, event: Dict[str, Any]) -> None:
        """Record an event and fan it out to live subscribers."""
        self.events.append(event)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # A slow client must not stall the run; it will still get the
                # final result from the status endpoint.
                logger.debug("run_store.subscriber_queue_full run=%s", self.run_id)

    def subscribe(self) -> asyncio.Queue:
        """Register a subscriber, pre-loaded with events already emitted."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        for event in self.events:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                break
        if self.is_finished:
            queue.put_nowait(DONE)
        else:
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    # --- lifecycle ---------------------------------------------------------

    @property
    def is_finished(self) -> bool:
        return self.status in ("completed", "partial", "failed")

    def complete(self, result: Dict[str, Any]) -> None:
        self.result = result
        self.status = result.get("status") or "completed"
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self._close()

    def fail(self, message: str, stage: str = "search") -> None:
        self.status = "failed"
        self.error = message
        self.error_stage = stage
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self._close()

    def _close(self) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(DONE)
            except asyncio.QueueFull:
                pass
        self._subscribers.clear()

    def status_payload(self) -> Dict[str, Any]:
        """Status without the full report body."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "stages": self._stage_summary(),
            "error": self.error,
            "error_stage": self.error_stage,
            "event_count": len(self.events),
        }

    def _stage_summary(self) -> Dict[str, str]:
        summary: Dict[str, str] = {}
        for event in self.events:
            stage, status = event.get("stage"), event.get("status")
            if not stage or status == "info":
                continue
            summary[stage] = status
        return summary


class RunStore:
    """Bounded LRU of runs."""

    def __init__(self, max_runs: int = MAX_RUNS_RETAINED) -> None:
        self._runs: "OrderedDict[str, Run]" = OrderedDict()
        self._max_runs = max_runs

    def create(self, run_id: str, brief: Dict[str, Any]) -> Run:
        run = Run(run_id, brief)
        self._runs[run_id] = run
        self._runs.move_to_end(run_id)
        while len(self._runs) > self._max_runs:
            evicted_id, evicted = self._runs.popitem(last=False)
            if not evicted.is_finished:
                logger.warning("run_store.evicted_active_run run=%s", evicted_id)
        return run

    def get(self, run_id: str) -> Optional[Run]:
        run = self._runs.get(run_id)
        if run is not None:
            self._runs.move_to_end(run_id)
        return run


store = RunStore()
