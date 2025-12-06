# test_app.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
import time

app = FastAPI()

# Remove '-pooler' and change port 6543 → 5432
engine = create_async_engine(
    "postgresql+asyncpg://neondb_owner:npg_Ssa2wryPA5qf@ep-restless-water-a1y5ofd8.ap-southeast-1.aws.neon.tech:5432/neondb",
    pool_size=2,
    max_overflow=0,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

@app.get("/test")
async def test(db: AsyncSession = Depends(get_db)):
    start = time.time()
    await db.execute(text("SELECT 1"))
    return {"time_ms": (time.time() - start) * 1000}

# Run: uvicorn test_app:app --reload
# Hit /test 10 times, check timings