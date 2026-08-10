from sqlalchemy.orm import Session

from database.models import JobStatus
from messaging.producer import publish_job
from repositories.job_repository import JobRepository
from services.job_service import JobNotFound, InvalidJobState


class RetryService:
    def __init__(self, db: Session):
        self.repo = JobRepository(db)

    async def retry(self, job_id: str):
        job = self.repo.get(job_id)
        if not job:
            raise JobNotFound(job_id)

        if job.status not in {JobStatus.FAILED, JobStatus.DEAD_LETTERED}:
            raise InvalidJobState(f"Cannot retry job in {job.status.value}")

        job.status = JobStatus.QUEUED
        job.last_error = None
        self.repo.save(job)
        self.repo.add_event(job.id, "JOB_MANUAL_RETRY")
        await publish_job(job.id)
        self.repo.add_event(job.id, "JOB_QUEUED")
        return job
