from prometheus_client import Counter, Gauge, Histogram

JOBS_SUBMITTED = Counter("jobs_submitted_total", "Total jobs submitted")
JOBS_COMPLETED = Counter("jobs_completed_total", "Total jobs completed")
JOBS_FAILED = Counter("jobs_failed_total", "Total job attempts failed")
JOBS_RETRIED = Counter("jobs_retried_total", "Total job retries")
JOBS_DEAD_LETTERED = Counter("jobs_dead_lettered_total", "Jobs moved to dead-letter state")
JOBS_RUNNING = Gauge("jobs_running", "Jobs currently running")
JOB_DURATION = Histogram("job_duration_seconds", "Job execution duration")
