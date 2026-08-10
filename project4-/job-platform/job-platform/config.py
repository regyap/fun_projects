from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://jobuser:jobpass@localhost:5432/jobdb"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    max_retries: int = 3
    worker_id: str = "worker-local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
