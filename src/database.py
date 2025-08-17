from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .config import settings

# This is the SQLAlchemy engine. We'll use a `Pool` of connections to the database.
engine = create_engine(settings.DATABASE_URL)

# This is a `sessionmaker` class, which will create a new session for each request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# `Base` is the superclass that all our SQLAlchemy models will inherit from.
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()