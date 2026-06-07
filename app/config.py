"""Application configuration from environment variables and .env file."""
import os
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars


class Settings:
    APP_NAME: str = "Patent-KG Platform"
    VERSION: str = "0.1.0"

    # Database: PostgreSQL (Docker) or SQLite fallback
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./patent_kg.db",
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    PDF_STORAGE_DIR: str = os.getenv(
        "PDF_STORAGE_DIR",
        str(Path(__file__).parent.parent / "data" / "pdfs"),
    )

    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"


settings = Settings()
