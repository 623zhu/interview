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

    # email
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str

    # jwt
    jwt_secret: str
    jwt_algorithm: str
    jwt_access_token_expires_minutes: int
    jwt_refresh_token_expires_days: int

    # resume
    resume_upload_dir: str

    #llm
    llm_api_key: str
    llm_model_light: str
    llm_model_heavy: str
    llm_base_url: str
    
settings = Settings()


