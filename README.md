# relivchats-api

# Terminal 1: Start Redis

docker-compose up redis

<!-- docker-compose -f docker-compose.dev.yml up -->

# Terminal 2: Start Celery Worker

celery -A src.celery_app worker --loglevel=info --concurrency=3

<!-- celery -A src.celery_app worker --loglevel=info --pool=solo      -->

# Terminal 3: Start FastAPI

uvicorn src.main:app --reload

# Terminal 4 (Optional): Start Flower monitoring

celery -A src.celery_app flower --port=5555

# Visit http://localhost:5555 to see tasks
