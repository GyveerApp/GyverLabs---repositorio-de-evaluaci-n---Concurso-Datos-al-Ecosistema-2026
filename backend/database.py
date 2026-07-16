from core.config import settings
from models import get_engine, get_sessionmaker

engine = get_engine(settings.DATABASE_URL)
SessionLocal = get_sessionmaker(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
