import aio_pika

from config import settings
from messaging.events import JOBS_EXCHANGE, JOBS_QUEUE, JOBS_ROUTING_KEY


async def open_consumer():
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        JOBS_EXCHANGE,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(JOBS_QUEUE, durable=True)
    await queue.bind(exchange, routing_key=JOBS_ROUTING_KEY)

    return connection, queue
