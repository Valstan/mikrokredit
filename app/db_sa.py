from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Импортируем конфигурацию
try:
    from .config import DATABASE_URL, USE_SQLITE
except ImportError:
    # Fallback для случаев, когда config.py недоступен
    DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.abspath(os.environ.get('MIKROKREDIT_DB', 'mikrokredit.db'))}"
    USE_SQLITE = False

print(f"DEBUG: DATABASE_URL = {DATABASE_URL}")
print(f"DEBUG: USE_SQLITE = {USE_SQLITE}")

# SQLite needs check_same_thread=False for use across threads
# For PostgreSQL, use psycopg2 driver
if DATABASE_URL.startswith("sqlite:"):
    print("DEBUG: Using SQLite database")
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
else:
    print("DEBUG: Using PostgreSQL database")
    try:
        engine = create_engine(DATABASE_URL, echo=False, future=True)
        print("DEBUG: Engine created successfully")
    except Exception as e:
        print(f"DEBUG: Error creating engine: {e}")
        raise

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
