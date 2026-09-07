"""In-memory run store: progress fan-out, replay, and lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from backend.services.run_store import DONE, QUEUE_MAXSIZE, Run, RunStore


def event(stage: str = "plan", status: str = "done") -> dict:
    return {"stage": stage, "status": status, "message": "m"}


class TestProgressFanOut:
    async def test_delivers_events_to_every_subscriber(self):
        run = Run("r1", {})
        a, b = run.subscribe(), run.subscribe()
        await run.publish(event())

        assert (await a.get())["stage"] == "plan"
        assert (await b.get())["stage"] == "plan"

    async def test_a_late_subscriber_replays_past_events(self):
        """A browser that connects after the run started must still see the
        earlier stages, otherwise the timeline starts half-empty."""
        run = Run("r1", {})
        await run.publish(event("intake"))
        await run.publish(event("plan"))

        queue = run.subscribe()
        assert (await queue.get())["stage"] == "intake"
        assert (await queue.get())["stage"] == "plan"

    async def test_a_subscriber_to_a_finished_run_gets_replay_then_done(self):
        run = Run("r1", {})
        await run.publish(event("intake"))
        run.complete({"status": "completed"})

        queue = run.subscribe()
        assert (await queue.get())["stage"] == "intake"
        assert await queue.get() is DONE

    async def test_completion_closes_live_subscribers(self):
        run = Run("r1", {})
        queue = run.subscribe()
        run.complete({"status": "completed"})

        assert await queue.get() is DONE

    async def test_failure_closes_live_subscribers(self):
        run = Run("r1", {})
        queue = run.subscribe()
        run.fail("everything broke", stage="search")

        assert await queue.get() is DONE
        assert run.status == "failed"
        assert run.error == "everything broke"
        assert run.error_stage == "search"

    async def test_unsubscribe_stops_delivery(self):
        run = Run("r1", {})
        queue = run.subscribe()
        run.unsubscribe(queue)
        await run.publish(event())

        assert queue.empty()

    async def test_unsubscribing_twice_is_safe(self):
        run = Run("r1", {})
        queue = run.subscribe()
        run.unsubscribe(queue)
        run.unsubscribe(queue)

    async def test_a_stalled_subscriber_does_not_block_the_run(self):
        """A browser that stops reading must not stall the research pipeline."""
        run = Run("r1", {})
        run.subscribe()  # never drained
        for _ in range(QUEUE_MAXSIZE + 20):
            await run.publish(event())

        # The run keeps its own full history regardless of subscriber backpressure.
        assert len(run.events) == QUEUE_MAXSIZE + 20

    async def test_replay_is_bounded_by_the_queue_size(self):
        run = Run("r1", {})
        for _ in range(QUEUE_MAXSIZE + 50):
            await run.publish(event())

        queue = run.subscribe()
        assert queue.qsize() == QUEUE_MAXSIZE


class TestLifecycle:
    def test_starts_running(self):
        run = Run("r1", {})
        assert run.status == "running"
        assert run.is_finished is False
        assert run.created_at

    def test_complete_adopts_the_payload_status(self):
        run = Run("r1", {})
        run.complete({"status": "partial"})

        assert run.status == "partial"
        assert run.is_finished
        assert run.finished_at
        assert run.result == {"status": "partial"}

    def test_complete_defaults_to_completed(self):
        run = Run("r1", {})
        run.complete({})
        assert run.status == "completed"

    async def test_status_payload_omits_the_report_body(self):
        run = Run("r1", {"title": "T"})
        await run.publish(event("plan"))
        run.complete({"status": "completed", "report": {"huge": "x" * 10_000}})
        payload = run.status_payload()

        assert "result" not in payload
        assert payload["run_id"] == "r1"
        assert payload["event_count"] == 1
        assert payload["stages"] == {"plan": "done"}

    async def test_stage_summary_ignores_per_search_info_events(self):
        """`info` events fire many times per stage; they'd overwrite the state."""
        run = Run("r1", {})
        await run.publish(event("search", "active"))
        await run.publish(event("search", "info"))
        await run.publish(event("search", "done"))

        assert run.status_payload()["stages"]["search"] == "done"

    async def test_stage_summary_keeps_the_latest_state(self):
        run = Run("r1", {})
        await run.publish(event("plan", "active"))
        await run.publish(event("plan", "done"))
        assert run.status_payload()["stages"]["plan"] == "done"


class TestRunStore:
    def test_creates_and_retrieves_a_run(self):
        store = RunStore()
        run = store.create("r1", {"title": "T"})

        assert store.get("r1") is run
        assert run.brief == {"title": "T"}

    def test_unknown_run_is_none(self):
        assert RunStore().get("nope") is None

    def test_evicts_the_oldest_run_beyond_the_cap(self):
        store = RunStore(max_runs=3)
        for i in range(5):
            store.create(f"r{i}", {})

        assert store.get("r0") is None
        assert store.get("r1") is None
        assert store.get("r4") is not None

    def test_access_refreshes_recency(self):
        store = RunStore(max_runs=3)
        for i in range(3):
            store.create(f"r{i}", {})
        store.get("r0")  # touch the oldest
        store.create("r3", {})

        assert store.get("r0") is not None
        assert store.get("r1") is None
