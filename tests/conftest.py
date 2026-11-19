"""Base SQLite aislada. Las variables se fijan antes de importar la app."""

import os
from pathlib import Path

_DB = Path(__file__).resolve().parents[1] / "test_mvp.db"
if _DB.exists():
    _DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB}"
os.environ["AUTO_SEED_SANDBOX"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["JWT_SECRET"] = "pytest-behu-secret-key-32-chars-min"
os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:1"
