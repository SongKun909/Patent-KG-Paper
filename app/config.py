"""Application configuration from environment variables."""
import os
from pathlib import Path


class Settings:
    APP_NAME: str = "Patent-KG Platform"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/patent_kg",
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    PDF_STORAGE_DIR: str = str(Path(__file__).parent.parent / "data" / "pdfs")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"


settings = Settings()
