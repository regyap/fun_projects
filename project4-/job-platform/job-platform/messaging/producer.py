import json
import aio_pika
from aio_pika import DeliveryMode

from config import settings
from messaging.events import JOBS_EXCHANGE, JOBS_QUEUE, JOBS_ROUTING_KEY


async def publish_job(job_id: str):
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            JOBS_EXCHANGE,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        queue = await channel.declare_queue(JOBS_QUEUE, durable=True)
        await queue.bind(exchange, routing_key=JOBS_ROUTING_KEY)

        message = aio_pika.Message(
            body=json.dumps({"job_id": job_id}).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=JOBS_ROUTING_KEY)
