from sqlalchemy.orm import Session

from database.models import JobStatus
from repositories.job_repository import JobRepository
from services.job_service import JobNotFound, InvalidJobState


class CancellationService:
    def __init__(self, db: Session):
        self.repo = JobRepository(db)

    def cancel(self, job_id: str):
        job = self.repo.get(job_id)
        if not job:
            raise JobNotFound(job_id)

        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
            self.repo.save(job)
            self.repo.add_event(job.id, "JOB_CANCELLED", {"reason": "cancelled before execution"})
            return job

        if job.status == JobStatus.RUNNING:
            job.status = JobStatus.CANCEL_REQUESTED
            self.repo.save(job)
            self.repo.add_event(job.id, "JOB_CANCEL_REQUESTED")
            return job

        raise InvalidJobState(f"Cannot cancel job in {job.status.value}")
