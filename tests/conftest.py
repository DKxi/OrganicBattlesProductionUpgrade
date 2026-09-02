import os
import sys
import tempfile
from pathlib import Path

# Ensure tests use an isolated database so organic_battles.sqlite3 is never polluted
_test_db_path = Path(tempfile.gettempdir()) / "test_organic_battles.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["DATABASE_PATH"] = str(_test_db_path)

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.infrastructure.database.engine import ensure_db_schema
ensure_db_schema()
