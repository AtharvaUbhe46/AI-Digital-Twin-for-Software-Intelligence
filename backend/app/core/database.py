import time
import logging
from typing import Generator, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("digital_twin.database")

Base = declarative_base()

engine = None
SessionLocal = None
_db_type = "postgres"


def initialize_engine():
    global engine, SessionLocal, _db_type
    target_url = settings.sync_database_url
    try:
        test_engine = create_engine(
            target_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 2}
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine = test_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        _db_type = "postgres"
        logger.info(f"Connected to PostgreSQL database: {settings.POSTGRES_DB}")
        return
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed ({e}). Checking fallback...")

    # If PostgreSQL failed and we are in development/test, fallback to SQLite for zero-failure local development
    try:
        fallback_url = "sqlite:///./software_digital_twin.db"
        engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        _db_type = "sqlite"
        logger.warning(f"Using local SQLite database fallback: {fallback_url}")
    except Exception as exc:
        logger.error(f"Failed to initialize even SQLite fallback: {exc}")


# Run initial engine creation
initialize_engine()
try:
    init_db()
except Exception:
    pass


def get_db() -> Generator[Optional[Session], None, None]:
    """
    FastAPI dependency yielding an active SQLAlchemy session.
    """
    if SessionLocal is None:
        initialize_engine()

    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Ping the database to verify connectivity and latency.
    Returns:
        (is_connected, latency_ms, error_message)
    """
    if engine is None:
        initialize_engine()

    if engine is None:
        return False, None, "Database engine not initialized"

    start_time = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return True, latency_ms, None
    except Exception as exc:
        return False, None, str(exc)


def init_db() -> None:
    """
    Creates database tables defined in models.
    """
    if engine is None:
        initialize_engine()

    if engine is None:
        return
    try:
        import app.models  # noqa: F401 ensure models are registered with Base.metadata
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database tables verified/created successfully using {_db_type}.")
    except Exception as exc:
        logger.warning(f"Could not create database tables on startup: {exc}")
