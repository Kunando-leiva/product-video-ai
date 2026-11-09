"""Configuración central del backend."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Product Video AI Local"
    APP_VERSION: str = "0.1.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Rutas base del proyecto (raíz del repo)
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    PROJECTS_DIR: Path = BASE_DIR / "projects"
    MODELS_DIR: Path = BASE_DIR / "models"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    TEMP_DIR: Path = BASE_DIR / "temp"
    LOGS_DIR: Path = BASE_DIR / "logs"
    MUSIC_DIR: Path = BASE_DIR / "assets" / "music"

    # Base de datos (Regla 44)
    DATABASE_URL: str = "sqlite+aiosqlite:///./product_video_ai.db"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ]

    def ensure_dirs(self) -> None:
        for d in (
            self.PROJECTS_DIR,
            self.MODELS_DIR,
            self.ASSETS_DIR,
            self.MUSIC_DIR,
            self.EXPORTS_DIR,
            self.TEMP_DIR,
            self.LOGS_DIR,
        ):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()