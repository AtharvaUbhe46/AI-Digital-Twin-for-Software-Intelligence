import pytest
from app.core.database import init_db, SessionLocal, engine, Base
import app.models  # ensure models registered


@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    init_db()
    yield


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    if SessionLocal:
        db = SessionLocal()
        try:
            # Clean up records before each test for clean isolation
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    yield
