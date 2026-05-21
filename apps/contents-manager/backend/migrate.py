"""alembic_version 없는 기존 DB는 001로 stamp 후 upgrade."""
import subprocess
from database import engine
from sqlalchemy import inspect, text

insp = inspect(engine)
tables = set(insp.get_table_names())

if tables and "alembic_version" not in tables:
    print("[migrate] Pre-Alembic DB 감지 → stamp 001")
    subprocess.run(["alembic", "stamp", "001"], check=True)

print("[migrate] alembic upgrade head")
subprocess.run(["alembic", "upgrade", "head"], check=True)
