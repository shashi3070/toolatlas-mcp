from pydantic_settings import BaseSettings
from toolatlas_mcp.registry.storage import get_data_dir


class Settings(BaseSettings):
    model_config = {
        "env_prefix": "TOOLATLAS_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    host: str = "127.0.0.1"
    port: int = 8081
    database_url: str = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
    storage_type: str = "json"
    log_level: str = "INFO"
    ui_dir: str = ""
    base_path: str = ""

    # Cache
    redis_url: str = ""
    cache_ttl: int = 300

    # Registry sync
    registry_sync_interval: int = 30

    # Plugin system
    plugins: list[str] = []
    plugin_dirs: list[str] = []

    @property
    def is_db_backend(self) -> bool:
        return self.storage_type != "json"


settings = Settings()
