# OpenTelemetry hook for the next iteration.
#
# Keeping this file separate means tracing can be added without changing
# the business logic in routes/services/workers.


def trace_job(job_id: str):
    return {"job_id": job_id}
