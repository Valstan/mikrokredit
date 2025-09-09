from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.abspath(os.environ.get('MIKROKREDIT_DB', 'mikrokredit.db'))}"

# SQLite needs check_same_thread=False for use across threads
# For PostgreSQL, use psycopg (not psycopg2)
if DATABASE_URL.startswith("sqlite:"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
else:
    # For PostgreSQL, replace postgresql:// with postgresql+psycopg://
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(DATABASE_URL, echo=False, future=True)

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
