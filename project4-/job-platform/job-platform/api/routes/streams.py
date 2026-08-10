import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from database.session import get_db
from repositories.job_repository import JobRepository

router = APIRouter(prefix="/v1/jobs", tags=["streams"])


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    if not repo.get(job_id):
        raise HTTPException(404, "Job not found")

    async def event_generator():
        last_id = 0

        while True:
            if await request.is_disconnected():
                break

            events = repo.events(job_id, after_id=last_id)

            for event in events:
                last_id = event.id
                yield {
                    "id": str(event.id),
                    "event": event.event_type.lower(),
                    "data": json.dumps({
                        "job_id": job_id,
                        "event": event.event_type,
                        "data": event.data,
                        "created_at": event.created_at.isoformat(),
                    }),
                }

            job = repo.get(job_id)
            if job and job.status.value in {
                "SUCCESS", "FAILED", "CANCELLED", "DEAD_LETTERED"
            }:
                # Send final state and close after all current events were emitted.
                yield {
                    "event": "stream.closed",
                    "data": json.dumps({"status": job.status.value}),
                }
                break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
