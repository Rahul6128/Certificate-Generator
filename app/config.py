"""Application configuration.

Kept deliberately simple (env vars with sane defaults) rather than pulling in
pydantic-settings, since the assignment scope doesn't need multi-environment
config management.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite by default so the project runs with zero external setup.
# Swap DATABASE_URL for a Postgres DSN (e.g. postgresql+psycopg2://...) in production.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'certificates.db'}")

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage" / "certificates"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE_PATH = BASE_DIR / "app" / "templates" / "certificate_template.png"
