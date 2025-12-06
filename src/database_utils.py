# src/database_utils.py
"""
Utility functions for advanced database operations including UPSERT,
lock timeout handling, and retry logic for async migrations.

These utilities are designed to prevent race conditions in high-concurrency
scenarios like parallel insight generation and payment processing.
"""

import asyncio
import random
from typing import TypeVar, Optional, Dict, Any
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, IntegrityError
from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


# ============================================================================
# LOCK TIMEOUT & RETRY LOGIC
# ============================================================================

class LockTimeoutError(Exception):
    """Raised when a row-level lock cannot be acquired within timeout"""
    pass


async def execute_with_lock_retry(
    db: AsyncSession,
    query_fn,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
) -> Optional[T]:
    """
    Execute a database query with row-level locking, retrying on lock timeout.

    Used for critical operations like credit deduction where multiple requests
    might contend for the same row lock.

    Args:
        db: AsyncSession for database operations
        query_fn: Async function that executes query with FOR UPDATE lock
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.1)
        max_delay: Maximum delay between retries in seconds (default: 1.0)

    Returns:
        Result from query_fn, or None if all retries exhausted

    Raises:
        OperationalError: If lock cannot be acquired after all retries

    Example:
        async def get_user_locked(db):
            stmt = select(User).where(User.user_id == "123").with_for_update(nowait=True)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        user = await execute_with_lock_retry(db, get_user_locked)
    """
    for attempt in range(max_retries):
        try:
            return await query_fn(db)

        except OperationalError as e:
            error_msg = str(e).lower()

            # Check if this is a lock timeout error
            if "lock not available" in error_msg or "deadlock detected" in error_msg:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter to prevent thundering herd
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)  # Add 10% jitter
                    wait_time = delay + jitter

                    logger.warning(
                        f"Lock timeout on attempt {attempt + 1}/{max_retries}, "
                        f"retrying after {wait_time:.3f}s",
                        extra={"extra_data": {
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "wait_time": wait_time,
                            "error": error_msg
                        }}
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Lock timeout after {max_retries} attempts",
                        extra={"extra_data": {
                            "max_retries": max_retries,
                            "error": error_msg
                        }},
                        exc_info=True
                    )
                    raise LockTimeoutError(
                        f"Could not acquire lock after {max_retries} attempts"
                    ) from e
            else:
                # Not a lock error, re-raise immediately
                raise

    return None


# ============================================================================
# UPSERT OPERATIONS
# ============================================================================

async def upsert_unique_record(
    db: AsyncSession,
    model_class,
    unique_keys: Dict[str, Any],
    update_values: Optional[Dict[str, Any]] = None,
    insert_values: Optional[Dict[str, Any]] = None,
) -> T:
    """
    Insert a record, or update if it already exists (UPSERT pattern).

    Prevents IntegrityError when multiple concurrent requests try to insert
    the same unique record (e.g., duplicate Insight generation).

    Args:
        db: AsyncSession for database operations
        model_class: SQLAlchemy ORM model class
        unique_keys: Dict of columns that form unique constraint (e.g., {"chat_id": "...", "insight_type_id": "..."})
        update_values: Dict of columns to update on conflict (optional)
        insert_values: Dict of additional columns to insert (merged with unique_keys)

    Returns:
        The inserted or updated record

    Example:
        # Prevent duplicate Insight records for same chat + type
        insight = await upsert_unique_record(
            db,
            Insight,
            unique_keys={"chat_id": chat_id, "insight_type_id": insight_type_id},
            update_values={"status": InsightStatus.PENDING},
            insert_values={"status": InsightStatus.PENDING, "created_at": datetime.now(timezone.utc)}
        )
    """
    try:
        # Prepare insert values: merge unique_keys + insert_values
        values_to_insert = {**unique_keys}
        if insert_values:
            values_to_insert.update(insert_values)

        # Build INSERT ... ON CONFLICT DO UPDATE statement
        stmt = insert(model_class).values(**values_to_insert)

        if update_values:
            # Update specific columns on conflict
            stmt = stmt.on_conflict_do_update(
                index_elements=list(unique_keys.keys()),
                set_=update_values
            )
        else:
            # Do nothing if record exists (and no updates specified)
            stmt = stmt.on_conflict_do_nothing()

        await db.execute(stmt)
        await db.commit()

        # Fetch the record (either newly inserted or existing)
        from sqlalchemy import select
        select_stmt = select(model_class)
        for key, value in unique_keys.items():
            select_stmt = select_stmt.where(getattr(model_class, key) == value)

        result = await db.execute(select_stmt)
        record = result.scalar_one_or_none()

        logger.info(
            f"UPSERT completed for {model_class.__name__}",
            extra={"extra_data": {
                "model": model_class.__name__,
                "unique_keys": unique_keys,
                "action": "inserted" if update_values is None else "updated"
            }}
        )

        return record

    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"UPSERT failed for {model_class.__name__} - integrity violation",
            extra={"extra_data": {
                "model": model_class.__name__,
                "unique_keys": unique_keys,
                "error": str(e)
            }},
            exc_info=True
        )
        raise

    except Exception as e:
        await db.rollback()
        logger.error(
            f"UPSERT failed for {model_class.__name__}",
            extra={"extra_data": {
                "model": model_class.__name__,
                "unique_keys": unique_keys,
                "error": str(e)
            }},
            exc_info=True
        )
        raise


async def upsert_or_create(
    db: AsyncSession,
    model_class,
    filters: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None,
) -> tuple[T, bool]:
    """
    Get or create a record (upsert pattern for non-unique constraints).

    Simpler alternative to upsert_unique_record for cases where you have
    a filter condition but not a unique constraint.

    Args:
        db: AsyncSession for database operations
        model_class: SQLAlchemy ORM model class
        filters: Dict of filter conditions (e.g., {"user_id": "...", "chat_id": "..."})
        defaults: Dict of default values for new records

    Returns:
        Tuple of (record, is_new) where is_new=True if record was just created

    Example:
        job, is_new = await upsert_or_create(
            db,
            InsightGenerationJob,
            filters={"job_id": job_id},
            defaults={"status": "pending", "chat_id": chat_id}
        )
    """
    from sqlalchemy import select

    try:
        # Try to find existing record
        stmt = select(model_class)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model_class, key) == value)

        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            logger.debug(
                f"Found existing {model_class.__name__} record",
                extra={"extra_data": {
                    "model": model_class.__name__,
                    "filters": filters
                }}
            )
            return record, False

        # Create new record
        create_values = {**filters}
        if defaults:
            create_values.update(defaults)

        record = model_class(**create_values)
        db.add(record)
        await db.commit()
        await db.refresh(record)

        logger.info(
            f"Created new {model_class.__name__} record",
            extra={"extra_data": {
                "model": model_class.__name__,
                "filters": filters
            }}
        )

        return record, True

    except Exception as e:
        await db.rollback()
        logger.error(
            f"Upsert-or-create failed for {model_class.__name__}",
            extra={"extra_data": {
                "model": model_class.__name__,
                "filters": filters,
                "error": str(e)
            }},
            exc_info=True
        )
        raise


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================

async def execute_in_transaction(
    db: AsyncSession,
    operation_fn,
    max_retries: int = 1,
) -> Optional[T]:
    """
    Execute a database operation in a transaction with automatic rollback.

    Ensures atomicity: either the entire operation succeeds or none of it.

    Args:
        db: AsyncSession for database operations
        operation_fn: Async function that performs database operations
        max_retries: Number of times to retry on failure (default: 1, no retries)

    Returns:
        Result from operation_fn

    Example:
        async def transfer_credits(db):
            # Multiple operations
            user1.credit_balance -= 100
            db.add(user1)
            user2.credit_balance += 100
            db.add(user2)
            return True

        result = await execute_in_transaction(db, transfer_credits)
    """
    for attempt in range(max_retries):
        try:
            result = await operation_fn(db)
            await db.commit()

            logger.debug(
                "Transaction completed successfully",
                extra={"extra_data": {
                    "attempt": attempt + 1,
                    "max_retries": max_retries
                }}
            )

            return result

        except Exception as e:
            await db.rollback()

            if attempt < max_retries - 1:
                logger.warning(
                    f"Transaction failed on attempt {attempt + 1}/{max_retries}, retrying",
                    extra={"extra_data": {
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error": str(e)
                    }}
                )
                await asyncio.sleep(0.5)  # Brief delay before retry
            else:
                logger.error(
                    f"Transaction failed after {max_retries} attempts",
                    extra={"extra_data": {
                        "max_retries": max_retries,
                        "error": str(e)
                    }},
                    exc_info=True
                )
                raise

    return None
