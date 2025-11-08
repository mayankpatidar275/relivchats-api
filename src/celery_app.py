# src/celery_app.py - NEW FILE

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "relivchats",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.rag.tasks",  # Import task modules
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes (better reliability)
    task_reject_on_worker_lost=True,
    task_time_limit=settings.INSIGHT_GENERATION_TIMEOUT,  # Hard timeout
    task_soft_time_limit=settings.INSIGHT_GENERATION_TIMEOUT - 10,  # Soft timeout (cleanup time)
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 2, "countdown": 5},  # Retry twice with 5s delay
    broker_connection_retry_on_startup=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Fetch 1 task at a time (better for long tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)

# Signals for monitoring

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log when task starts"""
    logger.info(f"Task started: {task.name} [ID: {task_id}]")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log when task completes"""
    logger.info(f"Task completed: {task.name} [ID: {task_id}] State: {state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, **extra):
    """Log when task fails"""
    logger.error(f"Task failed: {sender.name} [ID: {task_id}] Error: {exception}")