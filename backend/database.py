"""SQLAlchemy database engine and session factory."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that yields a database session and closes it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables and apply safe additive migrations for local SQLite."""
    import models  # noqa: F401 - import so models are registered

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()


def _apply_sqlite_migrations():
    """Keep existing SQLite databases compatible with current models."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as conn:
        session_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(sessions)")).fetchall()
        }

        if "processing_status" not in session_columns:
            conn.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN processing_status VARCHAR(50) DEFAULT 'pending'"
                )
            )

        if "processing_progress" not in session_columns:
            conn.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN processing_progress INTEGER DEFAULT 0"
                )
            )
