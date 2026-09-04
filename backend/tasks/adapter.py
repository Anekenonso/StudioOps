import os
from typing import Dict, Any, Optional
import threading
import json
from datetime import datetime

REDIS_URL = os.getenv("REDIS_URL")
JOB_DIR = os.path.join(os.getcwd(), "outputs", "jobs")


def ensure_job_dir():
    os.makedirs(JOB_DIR, exist_ok=True)


def _write_job_file(job_id: str, data: Dict[str, Any]):
    ensure_job_dir()
    path = os.path.join(JOB_DIR, f"{job_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def enqueue_job(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Enqueue a research job. If REDIS_URL is configured, use RQ; otherwise spawn a thread and record status to outputs/jobs."""
    if REDIS_URL:
        try:
            from rq import Queue
            from redis import Redis
            from backend.tasks.research_task import perform_research

            conn = Redis.from_url(REDIS_URL)
            q = Queue(connection=conn)
            job = q.enqueue(perform_research, brief)
            return {"queued": True, "job_id": job.get_id()}
        except Exception as e:
            return {"queued": False, "error": str(e)}

    # Threaded fallback
    try:
        import uuid
        from backend.tasks.research_task import perform_research

        job_id = uuid.uuid4().hex
        _write_job_file(job_id, {"status": "queued", "created_at": datetime.utcnow().isoformat()})

        def _run():
            try:
                _write_job_file(job_id, {"status": "running", "started_at": datetime.utcnow().isoformat()})
                res = perform_research(brief)
                _write_job_file(job_id, {"status": "finished", "finished_at": datetime.utcnow().isoformat(), "result": res})
            except Exception as e:
                _write_job_file(job_id, {"status": "failed", "error": str(e)})

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return {"queued": True, "job_id": job_id}
    except Exception as e:
        return {"queued": False, "error": str(e)}


def get_job_result(job_id: str) -> Dict[str, Any]:
    if REDIS_URL:
        try:
            from rq import Queue
            from redis import Redis

            conn = Redis.from_url(REDIS_URL)
            q = Queue(connection=conn)
            from rq.job import Job

            job = Job.fetch(job_id, connection=conn)
            if job.is_finished:
                return {"status": "finished", "result": job.result}
            if job.is_queued:
                return {"status": "queued"}
            if job.is_failed:
                return {"status": "failed", "error": str(job.exc_info)}
            return {"status": "unknown"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    else:
        # Read job file from outputs/jobs
        try:
            ensure_job_dir()
            path = os.path.join(JOB_DIR, f"{job_id}.json")
            if not os.path.exists(path):
                return {"status": "not_found"}
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "error", "error": str(e)}
