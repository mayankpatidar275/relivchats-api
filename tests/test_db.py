# test_db.py
from src.config import settings
from sqlalchemy import create_engine

print(f"Database URL: {settings.DATABASE_URL}")
try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")