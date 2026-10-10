from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        )

    # MySQL
    mysql_user: str
    mysql_password: str
    mysql_host: str
    mysql_port: int
    mysql_database: str

    # Redis
    redis_host: str
    redis_port: int
    redis_password: str

settings = Settings()


