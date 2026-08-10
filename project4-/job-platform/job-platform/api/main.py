from fastapi import FastAPI
from prometheus_client import make_asgi_app

from api.routes import jobs, workers, streams, health
from database.models import Base
from database.session import engine

app = FastAPI(
    title="Job Platform",
    version="0.1.0",
    description="Async job platform using FastAPI, PostgreSQL and RabbitMQ.",
)


@app.on_event("startup")
def startup():
    # Fine for a learning project.
    # Use Alembic migrations in a production system.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "name": "job-platform",
        "docs": "/docs",
        "health": "/health/ready",
        "metrics": "/metrics",
    }


app.include_router(jobs.router)
app.include_router(workers.router)
app.include_router(streams.router)
app.include_router(health.router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
