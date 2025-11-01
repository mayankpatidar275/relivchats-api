import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError

from .config import settings

# Configure logger
logger = logging.getLogger("db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Create engine with better resilience
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Detects stale connections
    pool_size=5,              # Adjust as per load
    max_overflow=10,          # Extra temporary connections
    pool_timeout=30,          # Wait before giving up on a connection
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import all models to ensure they're registered
from .users import models as users_models
from .chats import models as chats_models
from .vector import models as vector_models


def get_db(max_retries: int = 3):
    """Dependency to get a DB session with retry + safe close."""
    for attempt in range(1, max_retries + 1):
        try:
            db = SessionLocal()
            yield db
            break
        except OperationalError as e:
            logger.error(f"Database connection error (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            time.sleep(2)  # short backoff before retry
        finally:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"Failed to close DB session cleanly: {e}")
