from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Job, JobAttempt, JobEvent, JobStatus


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, job_id: str):
        return self.db.get(Job, job_id)

    def get_by_idempotency_key(self, key: str):
        return self.db.scalar(select(Job).where(Job.idempotency_key == key))

    def list(self, status: JobStatus | None = None, limit: int = 50, offset: int = 0):
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(Job.status == status)
        return list(self.db.scalars(stmt))

    def create(self, job: Job):
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def save(self, job: Job):
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def add_event(self, job_id: str, event_type: str, data: dict | None = None):
        event = JobEvent(job_id=job_id, event_type=event_type, data=data or {})
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def events(self, job_id: str, after_id: int = 0):
        stmt = (
            select(JobEvent)
            .where(JobEvent.job_id == job_id, JobEvent.id > after_id)
            .order_by(JobEvent.id.asc())
        )
        return list(self.db.scalars(stmt))

    def attempts(self, job_id: str):
        stmt = (
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_number.asc())
        )
        return list(self.db.scalars(stmt))

    def attempt_count(self, job_id: str):
        return len(self.attempts(job_id))

    def add_attempt(self, attempt: JobAttempt):
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt
