# Starter point for scheduled jobs.
#
# A later version can:
# 1. store scheduled_at on Job
# 2. periodically query due jobs
# 3. publish them to RabbitMQ
# 4. record JOB_QUEUED events


class SchedulerService:
    def tick(self):
        return []
