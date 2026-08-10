import asyncio
import json
import os
import time
from datetime import datetime, timezone

from database.models import AttemptStatus, JobAttempt, JobStatus
from database.session import SessionLocal
from messaging.consumer import open_consumer
from messaging.producer import publish_job
from repositories.job_repository import JobRepository
from observability.metrics import (
    JOBS_COMPLETED,
    JOBS_DEAD_LETTERED,
    JOBS_FAILED,
    JOBS_RETRIED,
    JOBS_RUNNING,
    JOB_DURATION,
)

WORKER_ID = os.getenv("WORKER_ID", "worker-local")


def run_task(task: str, number: int):
    if task == "calculate":
        return {"value": number * number}

    if task == "slow":
        time.sleep(15)
        return {"value": number}

    if task == "fail":
        raise RuntimeError("Intentional test failure")

    raise RuntimeError(f"Unsupported task: {task}")


async def handle_job(job_id: str):
    with SessionLocal() as db:
        repo = JobRepository(db)
        job = repo.get(job_id)

        if not job:
            return

        # Message may still exist even though a queued job was cancelled.
        if job.status == JobStatus.CANCELLED:
            repo.add_event(job.id, "JOB_SKIPPED_CANCELLED")
            return

        # Prevent already-final jobs from running if RabbitMQ redelivers old messages.
        if job.status in {JobStatus.SUCCESS, JobStatus.DEAD_LETTERED}:
            repo.add_event(job.id, "JOB_SKIPPED_FINAL_STATE", {"status": job.status.value})
            return

        attempt_number = repo.attempt_count(job.id) + 1
        attempt = JobAttempt(
            job_id=job.id,
            attempt_number=attempt_number,
            worker_id=WORKER_ID,
            status=AttemptStatus.RUNNING,
        )
        repo.add_attempt(attempt)

        job.status = JobStatus.RUNNING
        repo.save(job)
        repo.add_event(
            job.id,
            "JOB_STARTED",
            {"worker_id": WORKER_ID, "attempt": attempt_number},
        )

        JOBS_RUNNING.inc()
        started = time.monotonic()

        try:
            result = await asyncio.to_thread(
                run_task,
                job.task,
                int(job.payload["number"]),
            )

            duration = time.monotonic() - started

            # This demonstrates timeout classification.
            # It does not kill the task while it is running.
            if duration > job.timeout_seconds:
                raise TimeoutError(
                    f"Job exceeded timeout of {job.timeout_seconds}s"
                )

            # Refresh state in case the API requested cancellation.
            db.refresh(job)
            if job.status == JobStatus.CANCEL_REQUESTED:
                job.status = JobStatus.CANCELLED
                attempt.status = AttemptStatus.CANCELLED
                attempt.completed_at = datetime.now(timezone.utc)
                repo.save(job)
                db.add(attempt)
                db.commit()
                repo.add_event(job.id, "JOB_CANCELLED", {"worker_id": WORKER_ID})
                return

            job.status = JobStatus.SUCCESS
            job.result = result
            job.last_error = None
            attempt.status = AttemptStatus.SUCCESS
            attempt.result = result
            attempt.completed_at = datetime.now(timezone.utc)

            db.add(attempt)
            repo.save(job)
            db.commit()

            repo.add_event(
                job.id,
                "JOB_COMPLETED",
                {"worker_id": WORKER_ID, "duration_seconds": round(duration, 3)},
            )
            JOBS_COMPLETED.inc()
            JOB_DURATION.observe(duration)

        except Exception as exc:
            duration = time.monotonic() - started
            JOBS_FAILED.inc()

            attempt.status = AttemptStatus.FAILED
            attempt.error = str(exc)
            attempt.completed_at = datetime.now(timezone.utc)
            db.add(attempt)

            job.last_error = str(exc)

            if attempt_number <= job.max_retries:
                job.status = JobStatus.RETRYING
                repo.save(job)
                db.commit()
                repo.add_event(
                    job.id,
                    "JOB_RETRY_SCHEDULED",
                    {
                        "attempt": attempt_number,
                        "error": str(exc),
                    },
                )
                JOBS_RETRIED.inc()

                # Simple learning-project backoff.
                # Production: use a RabbitMQ retry queue with TTL.
                await asyncio.sleep(min(2 ** attempt_number, 10))

                db.refresh(job)
                if job.status == JobStatus.CANCEL_REQUESTED:
                    job.status = JobStatus.CANCELLED
                    repo.save(job)
                    repo.add_event(job.id, "JOB_CANCELLED")
                    return

                job.status = JobStatus.QUEUED
                repo.save(job)
                await publish_job(job.id)
                repo.add_event(job.id, "JOB_QUEUED", {"reason": "retry"})

            else:
                job.status = JobStatus.DEAD_LETTERED
                repo.save(job)
                db.commit()
                repo.add_event(
                    job.id,
                    "JOB_DEAD_LETTERED",
                    {
                        "attempts": attempt_number,
                        "last_error": str(exc),
                    },
                )
                JOBS_DEAD_LETTERED.inc()

            JOB_DURATION.observe(duration)

        finally:
            JOBS_RUNNING.dec()


async def main():
    connection, queue = await open_consumer()
    print(f"{WORKER_ID} listening for jobs")

    try:
        async with queue.iterator() as iterator:
            async for message in iterator:
                async with message.process(requeue=True):
                    body = json.loads(message.body.decode())
                    await handle_job(body["job_id"])
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
