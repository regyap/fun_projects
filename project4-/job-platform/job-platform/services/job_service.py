from sqlalchemy.orm import Session

from database.models import Job, JobStatus
from domain.job import JobCreate
from messaging.producer import publish_job
from repositories.job_repository import JobRepository
from observability.metrics import JOBS_SUBMITTED


class JobNotFound(Exception):
    pass


class InvalidJobState(Exception):
    pass


class JobService:
    def __init__(self, db: Session):
        self.repo = JobRepository(db)

    async def create_job(self, data: JobCreate, idempotency_key: str | None = None):
        if idempotency_key:
            existing = self.repo.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing, False

        job = Job(
            task=data.task,
            payload={"number": data.number},
            priority=data.priority,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
            idempotency_key=idempotency_key,
            status=JobStatus.QUEUED,
        )
        self.repo.create(job)
        self.repo.add_event(job.id, "JOB_CREATED", {"task": job.task})
        await publish_job(job.id)
        self.repo.add_event(job.id, "JOB_QUEUED")
        JOBS_SUBMITTED.inc()
        return job, True

    def get_job(self, job_id: str):
        job = self.repo.get(job_id)
        if not job:
            raise JobNotFound(job_id)
        return job

    def list_jobs(self, status=None, limit=50, offset=0):
        return self.repo.list(status=status, limit=limit, offset=offset)

    def history(self, job_id: str):
        self.get_job(job_id)
        return {
            "events": self.repo.events(job_id),
            "attempts": self.repo.attempts(job_id),
        }
