import aio_pika
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from config import settings
from database.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live():
    return {"status": "alive"}


@router.get("/health/ready")
async def ready():
    checks = {"database": False, "rabbitmq": False}

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        await connection.close()
        checks["rabbitmq"] = True
    except Exception:
        pass

    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"ready": False, "checks": checks})

    return {"ready": True, "checks": checks}
