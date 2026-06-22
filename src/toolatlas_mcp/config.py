from pydantic_settings import BaseSettings
from toolatlas_mcp.registry.storage import get_data_dir


class Settings(BaseSettings):
    model_config = {"env_prefix": "TOOLATLAS_"}

    host: str = "127.0.0.1"
    port: int = 8081
    database_url: str = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
    storage_type: str = "json"
    log_level: str = "INFO"
    ui_dir: str = ""
    base_path: str = ""


settings = Settings()
