import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parents[1] / "data" / "test.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
TEST_DB.unlink(missing_ok=True)

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
os.environ["DEMO_SEED"] = "true"
os.environ["QIANWEN_API_KEY"] = ""
