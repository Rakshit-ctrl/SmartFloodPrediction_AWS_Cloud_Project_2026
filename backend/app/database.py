import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)

URL = settings.database_url
engine = create_engine(
    URL,
    connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# Additive-only upgrades for databases created by an earlier phase.
# Temporary stand-in until Alembic migrations are introduced for the MySQL target.
_ADDITIVE_COLUMNS = {
    "risk_assessments": {
        "method": "VARCHAR(40) NOT NULL DEFAULT 'demo_heuristic_v1'",
        "validated": "BOOLEAN NOT NULL DEFAULT 0",
    },
}


def ensure_schema(eng=None) -> None:
    """Create missing tables, then add any missing columns listed in _ADDITIVE_COLUMNS."""
    eng = eng or engine
    Base.metadata.create_all(bind=eng)
    insp = inspect(eng)
    with eng.begin() as conn:
        for table, columns in _ADDITIVE_COLUMNS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in columns.items():  # names/DDL are constants above, never user input
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    logger.info("Added column %s.%s", table, name)


def get_db():
    """Yield a session; roll back on any error so a failed request never leaves a dirty transaction."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
