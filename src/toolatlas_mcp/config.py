from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "TOOLATLAS_"}

    host: str = "127.0.0.1"
    port: int = 8080
    database_url: str = "sqlite+aiosqlite:///toolatlas.db"
    log_level: str = "INFO"
    ui_dir: str = ""


settings = Settings()
