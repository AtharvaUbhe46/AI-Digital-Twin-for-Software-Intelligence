from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TimeStampedModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
