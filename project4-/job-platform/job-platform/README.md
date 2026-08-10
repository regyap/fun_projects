# Job Platform

A learning project for building a production-style asynchronous job backend with:

- FastAPI for the REST API
- PostgreSQL as the source of truth
- RabbitMQ for job delivery
- Worker processes for asynchronous execution
- Server-Sent Events (SSE) for live job updates
- Retry and dead-letter handling
- Cancellation requests
- Prometheus metrics
- Health/readiness endpoints

## Architecture

```text
Client
  |
  | REST / SSE
  v
FastAPI
  |   |  \-----> PostgreSQL
  |
  +-------> RabbitMQ -----> Worker 1
                         \-> Worker 2

Workers update PostgreSQL.
The SSE endpoint polls job events and streams new events to clients.
```

## Start

```bash
docker compose up --build
```

Open:

- API docs: http://localhost:8000/docs
- RabbitMQ UI: http://localhost:15672
- Metrics: http://localhost:8000/metrics

RabbitMQ default credentials:

```text
guest / guest
```

## API

### Submit a job

```bash
curl -X POST http://localhost:8000/v1/jobs   -H "Content-Type: application/json"   -H "Idempotency-Key: demo-001"   -d '{"task":"calculate","number":25,"timeout_seconds":30}'
```

### Get jobs

```bash
curl http://localhost:8000/v1/jobs
```

### Get one job

```bash
curl http://localhost:8000/v1/jobs/<job_id>
```

### Retry

```bash
curl -X POST http://localhost:8000/v1/jobs/<job_id>/retry
```

### Cancel

```bash
curl -X POST http://localhost:8000/v1/jobs/<job_id>/cancel
```

### History

```bash
curl http://localhost:8000/v1/jobs/<job_id>/history
```

### Stream updates

```bash
curl -N http://localhost:8000/v1/jobs/<job_id>/stream
```

## Built-in task types

`calculate`

Returns `number * number`.

`slow`

Sleeps long enough to demonstrate timeout handling.

`fail`

Always fails so retry / dead-letter behavior can be tested.

## Edge cases covered

- Duplicate requests through `Idempotency-Key`
- Invalid payloads through Pydantic validation
- Unknown tasks rejected
- Job-not-found handling
- Invalid state transitions
- Worker retries
- Dead-letter state after max retries
- Cancellation request state
- Worker identity per attempt
- Job attempt history
- Job event history
- RabbitMQ acknowledgements
- PostgreSQL persistence
- API liveness/readiness
- Prometheus counters and gauges

## Important learning limitation

The worker checks elapsed execution time after a task returns. It does not forcibly terminate arbitrary Python work when the timeout is exceeded. A production version would execute work in a separate process/container and terminate that execution unit when its lease or timeout expires.

Likewise, cancellation is cooperative. A queued job can be cancelled immediately; a running job records `CANCEL_REQUESTED`, and the worker checks state before finalizing.

## Next improvements

- RabbitMQ retry exchanges with TTL instead of worker-side sleep
- Worker heartbeat table
- Lease-based job ownership
- Scheduled jobs / cron jobs
- Authentication and authorization
- OpenTelemetry exporter
- WebSocket support for bidirectional control
- Kafka event topic for long-term replay / analytics
