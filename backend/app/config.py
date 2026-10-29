"""Environment-based configuration.

Loads backend/.env (if present) once at import time, regardless of the current
working directory. Values are read from the environment on every access so that
tests can override them with monkeypatch. Secrets are never logged.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")  # does not override variables already set


class Settings:
    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL", "sqlite:///./flood_app.db")

    @property
    def openweather_api_key(self) -> str:
        return os.getenv("OPENWEATHER_API_KEY", "").strip()

    @property
    def cors_origins(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def upload_max_bytes(self) -> int:
        try:
            mb = float(os.getenv("UPLOAD_MAX_MB", "8"))
        except ValueError:
            mb = 8.0
        return int(mb * 1024 * 1024)

    @property
    def model_dir(self) -> str:
        raw = os.getenv("MODEL_DIR", "").strip()
        if raw:
            p = Path(raw)
            return str(p if p.is_absolute() else BACKEND_DIR / p)
        if (BACKEND_DIR / "models_deployed" / "model.json").is_file():
            return str(BACKEND_DIR / "models_deployed")
        return str(BACKEND_DIR / "models")

    @property
    def max_image_pixels(self) -> int:
        try:
            return max(1, int(os.getenv("MAX_IMAGE_PIXELS", "25000000")))
        except ValueError:
            return 25_000_000

    @property
    def overlay_max_px(self) -> int:
        try:
            return max(64, int(os.getenv("OVERLAY_MAX_PX", "1024")))
        except ValueError:
            return 1024

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()
