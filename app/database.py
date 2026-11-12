from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_SIZE


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()