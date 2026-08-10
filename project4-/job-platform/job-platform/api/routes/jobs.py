from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database.models import JobStatus
from database.session import get_db
from domain.job import JobCreate, JobView
from services.job_service import JobService, JobNotFound, InvalidJobState
from services.retry_service import RetryService
from services.cancellation_service import CancellationService

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.post("", response_model=JobView)
async def create_job(
    body: JobCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    job, created = await JobService(db).create_job(body, idempotency_key)
    response.status_code = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    return job


@router.get("", response_model=list[JobView])
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return JobService(db).list_jobs(status=status_filter, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobView)
def get_job(job_id: str, db: Session = Depends(get_db)):
    try:
        return JobService(db).get_job(job_id)
    except JobNotFound:
        raise HTTPException(404, "Job not found")


@router.post("/{job_id}/cancel", response_model=JobView)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    try:
        return CancellationService(db).cancel(job_id)
    except JobNotFound:
        raise HTTPException(404, "Job not found")
    except InvalidJobState as exc:
        raise HTTPException(409, str(exc))


@router.post("/{job_id}/retry", response_model=JobView)
async def retry_job(job_id: str, db: Session = Depends(get_db)):
    try:
        return await RetryService(db).retry(job_id)
    except JobNotFound:
        raise HTTPException(404, "Job not found")
    except InvalidJobState as exc:
        raise HTTPException(409, str(exc))


@router.get("/{job_id}/history")
def job_history(job_id: str, db: Session = Depends(get_db)):
    try:
        history = JobService(db).history(job_id)
        return {
            "job_id": job_id,
            "events": [
                {
                    "id": e.id,
                    "type": e.event_type,
                    "data": e.data,
                    "created_at": e.created_at,
                }
                for e in history["events"]
            ],
            "attempts": [
                {
                    "id": a.id,
                    "attempt_number": a.attempt_number,
                    "worker_id": a.worker_id,
                    "status": a.status.value,
                    "error": a.error,
                    "result": a.result,
                    "started_at": a.started_at,
                    "completed_at": a.completed_at,
                }
                for a in history["attempts"]
            ],
        }
    except JobNotFound:
        raise HTTPException(404, "Job not found")


@router.get("/{job_id}/logs")
def job_logs(job_id: str, db: Session = Depends(get_db)):
    # For this MVP the worker stores lifecycle events, not raw stdout.
    # This endpoint intentionally returns those operational messages.
    try:
        history = JobService(db).history(job_id)
    except JobNotFound:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job_id,
        "logs": [
            {
                "timestamp": e.created_at,
                "message": e.event_type,
                "details": e.data,
            }
            for e in history["events"]
        ],
    }
