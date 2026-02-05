"""
Automated Data Retention & Cleanup Script
Celery task to enforce data retention policies and clean up expired data

Add this to: src/tasks/cleanup_tasks.py
"""

from celery import shared_task
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging

from src.database import SessionLocal
from src.chats.models import Chat, Message
from src.chats.service import _delete_chat_sync
from src.vector.service import vector_service
from src.logging_config import get_logger

logger = get_logger(__name__)


@shared_task(name="cleanup.expired_chats")
def cleanup_expired_chats() -> Dict[str, int]:
    """
    Daily task to delete chats that have exceeded their retention period

    Schedule in celery_app.py:
        celery_app.conf.beat_schedule = {
            'cleanup-expired-chats': {
                'task': 'cleanup.expired_chats',
                'schedule': crontab(hour=2, minute=0),  # 2 AM daily
            }
        }

    Returns:
        Dict with cleanup statistics
    """

    db = SessionLocal()
    stats = {
        "chats_deleted": 0,
        "messages_deleted": 0,
        "errors": 0,
        "execution_time_seconds": 0
    }

    start_time = datetime.now(timezone.utc)

    logger.info("Starting daily data cleanup task")

    try:
        # Find chats that have expired
        now = datetime.now(timezone.utc)

        expired_chats = db.query(Chat).filter(
            and_(
                Chat.auto_delete_enabled == True,
                Chat.expires_at.isnot(None),
                Chat.expires_at <= now,
                ~Chat.is_deleted  # Not already soft-deleted
            )
        ).all()

        logger.info(
            f"Found {len(expired_chats)} expired chats",
            extra={"extra_data": {"expired_count": len(expired_chats)}}
        )

        # Delete each chat
        for chat in expired_chats:
            try:
                # Count messages before deletion (for stats)
                message_count = db.query(Message).filter(
                    Message.chat_id == chat.id
                ).count()

                # Permanent deletion
                success = _delete_chat_sync(db, str(chat.id))

                if success:
                    stats["chats_deleted"] += 1
                    stats["messages_deleted"] += message_count

                    logger.info(
                        f"Deleted expired chat: {chat.id}",
                        extra={
                            "extra_data": {
                                "chat_id": str(chat.id),
                                "user_id": chat.user_id,
                                "message_count": message_count,
                                "retention_days": chat.retention_days,
                                "expired_at": chat.expires_at.isoformat()
                            }
                        }
                    )
                else:
                    stats["errors"] += 1
                    logger.error(f"Failed to delete expired chat: {chat.id}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"Error deleting chat {chat.id}: {e}",
                    exc_info=True
                )

        # Update chats that need new expiry dates
        # (in case user changed last_accessed_at)
        update_expiry_dates(db)

        end_time = datetime.now(timezone.utc)
        stats["execution_time_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            "Data cleanup task completed",
            extra={"extra_data": stats}
        )

        # Send notification if many chats deleted (possible issue)
        if stats["chats_deleted"] > 100:
            logger.warning(
                f"Unusual cleanup: {stats['chats_deleted']} chats deleted",
                extra={"extra_data": stats}
            )

        return stats

    except Exception as e:
        logger.error(
            f"Fatal error in cleanup task: {e}",
            exc_info=True
        )
        raise

    finally:
        db.close()


def update_expiry_dates(db: Session) -> int:
    """
    Update expires_at for chats based on last_accessed_at + retention_days
    """

    updated_count = 0

    # Get all chats with auto-delete enabled
    chats = db.query(Chat).filter(
        and_(
            Chat.auto_delete_enabled == True,
            Chat.retention_days > 0,
            ~Chat.is_deleted
        )
    ).all()

    for chat in chats:
        if chat.last_accessed_at:
            new_expiry = chat.last_accessed_at + timedelta(days=chat.retention_days)

            # Only update if changed (avoid unnecessary writes)
            if chat.expires_at != new_expiry:
                chat.expires_at = new_expiry
                updated_count += 1

    if updated_count > 0:
        db.commit()
        logger.info(f"Updated expiry dates for {updated_count} chats")

    return updated_count


@shared_task(name="cleanup.orphaned_vectors")
def cleanup_orphaned_vectors() -> Dict[str, int]:
    """
    Weekly task to clean up orphaned vectors in Qdrant
    (vectors for deleted chats)

    Schedule:
        celery_app.conf.beat_schedule = {
            'cleanup-orphaned-vectors': {
                'task': 'cleanup.orphaned_vectors',
                'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Monday 3 AM
            }
        }
    """

    db = SessionLocal()
    stats = {
        "vectors_deleted": 0,
        "chats_checked": 0,
        "errors": 0
    }

    logger.info("Starting orphaned vectors cleanup")

    try:
        # Get all chat IDs in database
        existing_chat_ids = {
            str(chat_id[0])
            for chat_id in db.query(Chat.id).all()
        }

        # Get all chat IDs in Qdrant
        # (This requires adding a method to vector_service to list all stored chat IDs)
        qdrant_chat_ids = vector_service.get_all_stored_chat_ids()

        # Find orphaned chat IDs (in Qdrant but not in DB)
        orphaned_ids = qdrant_chat_ids - existing_chat_ids

        logger.info(
            f"Found {len(orphaned_ids)} orphaned vector collections",
            extra={"extra_data": {"orphaned_count": len(orphaned_ids)}}
        )

        # Delete orphaned vectors
        for chat_id in orphaned_ids:
            try:
                vector_service.cleanup_failed_indexing(db, chat_id)
                stats["vectors_deleted"] += 1

                logger.info(f"Deleted orphaned vectors for chat: {chat_id}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Failed to delete vectors for {chat_id}: {e}")

        stats["chats_checked"] = len(existing_chat_ids)

        logger.info(
            "Orphaned vectors cleanup completed",
            extra={"extra_data": stats}
        )

        return stats

    except Exception as e:
        logger.error(f"Error in orphaned vectors cleanup: {e}", exc_info=True)
        raise

    finally:
        db.close()


@shared_task(name="cleanup.old_logs")
def cleanup_old_logs(days_to_keep: int = 90) -> Dict[str, int]:
    """
    Monthly task to delete old application logs

    Schedule:
        celery_app.conf.beat_schedule = {
            'cleanup-old-logs': {
                'task': 'cleanup.old_logs',
                'schedule': crontab(day_of_month=1, hour=4, minute=0),  # 1st of month, 4 AM
            }
        }
    """

    import os
    import glob
    from pathlib import Path

    stats = {
        "files_deleted": 0,
        "bytes_freed": 0,
        "errors": 0
    }

    logger.info(f"Starting log cleanup (keeping last {days_to_keep} days)")

    try:
        log_dir = Path("logs")
        if not log_dir.exists():
            logger.warning("Logs directory not found")
            return stats

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Find all log files
        log_files = glob.glob(str(log_dir / "*.log*"))

        for log_file in log_files:
            try:
                file_path = Path(log_file)
                file_modified = datetime.fromtimestamp(
                    file_path.stat().st_mtime,
                    tz=timezone.utc
                )

                # Delete if older than cutoff
                if file_modified < cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()

                    stats["files_deleted"] += 1
                    stats["bytes_freed"] += file_size

                    logger.info(f"Deleted old log file: {log_file}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error deleting log file {log_file}: {e}")

        logger.info(
            f"Log cleanup completed: deleted {stats['files_deleted']} files, "
            f"freed {stats['bytes_freed'] / 1024 / 1024:.2f} MB",
            extra={"extra_data": stats}
        )

        return stats

    except Exception as e:
        logger.error(f"Error in log cleanup: {e}", exc_info=True)
        raise


@shared_task(name="cleanup.soft_deleted_chats")
def cleanup_soft_deleted_chats(grace_period_days: int = 30) -> Dict[str, int]:
    """
    Weekly task to permanently delete chats that have been soft-deleted
    for more than grace_period_days

    This gives users a grace period to recover accidentally deleted chats

    Schedule:
        celery_app.conf.beat_schedule = {
            'cleanup-soft-deleted-chats': {
                'task': 'cleanup.soft_deleted_chats',
                'schedule': crontab(day_of_week=0, hour=3, minute=30),  # Sunday 3:30 AM
            }
        }
    """

    db = SessionLocal()
    stats = {
        "chats_deleted": 0,
        "errors": 0
    }

    logger.info(
        f"Starting soft-deleted chats cleanup (grace period: {grace_period_days} days)"
    )

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=grace_period_days)

        # Find soft-deleted chats older than grace period
        old_soft_deleted = db.query(Chat).filter(
            and_(
                Chat.is_deleted == True,
                Chat.deleted_at.isnot(None),
                Chat.deleted_at <= cutoff_date
            )
        ).all()

        logger.info(
            f"Found {len(old_soft_deleted)} soft-deleted chats past grace period",
            extra={"extra_data": {"count": len(old_soft_deleted)}}
        )

        for chat in old_soft_deleted:
            try:
                success = _delete_chat_sync(db, str(chat.id))

                if success:
                    stats["chats_deleted"] += 1
                    logger.info(
                        f"Permanently deleted soft-deleted chat: {chat.id}",
                        extra={
                            "extra_data": {
                                "chat_id": str(chat.id),
                                "deleted_at": chat.deleted_at.isoformat(),
                                "days_since_deletion": (datetime.now(timezone.utc) - chat.deleted_at).days
                            }
                        }
                    )
                else:
                    stats["errors"] += 1

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error permanently deleting chat {chat.id}: {e}")

        logger.info(
            "Soft-deleted chats cleanup completed",
            extra={"extra_data": stats}
        )

        return stats

    except Exception as e:
        logger.error(f"Error in soft-deleted cleanup: {e}", exc_info=True)
        raise

    finally:
        db.close()


@shared_task(name="cleanup.report")
def generate_cleanup_report() -> Dict[str, any]:
    """
    Generate weekly cleanup report for admin monitoring

    Schedule:
        celery_app.conf.beat_schedule = {
            'cleanup-report': {
                'task': 'cleanup.report',
                'schedule': crontab(day_of_week=1, hour=9, minute=0),  # Monday 9 AM
            }
        }
    """

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Gather statistics
        total_chats = db.query(Chat).filter(~Chat.is_deleted).count()
        total_messages = db.query(Message).count()

        # Chats with auto-delete enabled
        auto_delete_enabled = db.query(Chat).filter(
            and_(
                Chat.auto_delete_enabled == True,
                ~Chat.is_deleted
            )
        ).count()

        # Chats expiring in next 7 days
        expiring_soon = db.query(Chat).filter(
            and_(
                Chat.expires_at.isnot(None),
                Chat.expires_at <= now + timedelta(days=7),
                Chat.expires_at > now,
                ~Chat.is_deleted
            )
        ).count()

        # Soft-deleted chats (in grace period)
        soft_deleted = db.query(Chat).filter(
            Chat.is_deleted == True
        ).count()

        report = {
            "generated_at": now.isoformat(),
            "period": "Last 7 days",
            "statistics": {
                "total_active_chats": total_chats,
                "total_messages": total_messages,
                "auto_delete_enabled": auto_delete_enabled,
                "auto_delete_percentage": round(auto_delete_enabled / total_chats * 100, 1) if total_chats > 0 else 0,
                "expiring_in_7_days": expiring_soon,
                "soft_deleted_in_grace_period": soft_deleted
            },
            "recommendations": []
        }

        # Add recommendations
        if auto_delete_enabled / total_chats < 0.5 if total_chats > 0 else False:
            report["recommendations"].append(
                "Less than 50% of users have auto-delete enabled. Consider promoting this feature."
            )

        if expiring_soon > 100:
            report["recommendations"].append(
                f"{expiring_soon} chats will be deleted in the next 7 days. Monitor cleanup job closely."
            )

        logger.info(
            "Weekly cleanup report generated",
            extra={"extra_data": report}
        )

        # TODO: Send email to admin with this report

        return report

    except Exception as e:
        logger.error(f"Error generating cleanup report: {e}", exc_info=True)
        raise

    finally:
        db.close()


# ============================================================================
# CELERY BEAT SCHEDULE CONFIGURATION
# ============================================================================

"""
Add this to src/celery_app.py:

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Daily: Delete expired chats (2 AM)
    'cleanup-expired-chats': {
        'task': 'cleanup.expired_chats',
        'schedule': crontab(hour=2, minute=0),
    },

    # Weekly: Delete soft-deleted chats past grace period (Sunday 3:30 AM)
    'cleanup-soft-deleted-chats': {
        'task': 'cleanup.soft_deleted_chats',
        'schedule': crontab(day_of_week=0, hour=3, minute=30),
    },

    # Weekly: Clean up orphaned vectors (Monday 3 AM)
    'cleanup-orphaned-vectors': {
        'task': 'cleanup.orphaned_vectors',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),
    },

    # Monthly: Delete old logs (1st of month, 4 AM)
    'cleanup-old-logs': {
        'task': 'cleanup.old_logs',
        'schedule': crontab(day_of_month=1, hour=4, minute=0),
    },

    # Weekly: Generate cleanup report (Monday 9 AM)
    'cleanup-report': {
        'task': 'cleanup.report',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
    },
}
"""


# ============================================================================
# MANUAL CLEANUP UTILITIES (Run from shell)
# ============================================================================

def manual_cleanup_user_data(user_id: str) -> Dict[str, int]:
    """
    Manually clean up all data for a specific user

    Usage:
        from src.tasks.cleanup_tasks import manual_cleanup_user_data
        manual_cleanup_user_data("user_123")
    """

    db = SessionLocal()
    stats = {
        "chats_deleted": 0,
        "messages_deleted": 0
    }

    try:
        # Get all user's chats
        chats = db.query(Chat).filter(Chat.user_id == user_id).all()

        for chat in chats:
            message_count = db.query(Message).filter(
                Message.chat_id == chat.id
            ).count()

            success = _delete_chat_sync(db, str(chat.id))

            if success:
                stats["chats_deleted"] += 1
                stats["messages_deleted"] += message_count

        logger.info(
            f"Manual cleanup completed for user: {user_id}",
            extra={"extra_data": stats}
        )

        return stats

    finally:
        db.close()


def preview_upcoming_deletions(days_ahead: int = 7) -> List[Dict]:
    """
    Preview chats that will be deleted in the next N days

    Usage:
        from src.tasks.cleanup_tasks import preview_upcoming_deletions
        upcoming = preview_upcoming_deletions(7)
        print(f"{len(upcoming)} chats will be deleted in next 7 days")
    """

    db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        upcoming = db.query(Chat).filter(
            and_(
                Chat.expires_at.isnot(None),
                Chat.expires_at <= cutoff,
                ~Chat.is_deleted
            )
        ).all()

        preview = []
        for chat in upcoming:
            preview.append({
                "chat_id": str(chat.id),
                "user_id": chat.user_id,
                "expires_at": chat.expires_at.isoformat(),
                "days_until_deletion": (chat.expires_at - datetime.now(timezone.utc)).days,
                "message_count": db.query(Message).filter(Message.chat_id == chat.id).count()
            })

        return preview

    finally:
        db.close()


if __name__ == "__main__":
    # Test cleanup tasks locally
    print("Testing cleanup tasks...")

    print("\n1. Preview upcoming deletions:")
    upcoming = preview_upcoming_deletions(7)
    print(f"   {len(upcoming)} chats will be deleted in next 7 days")

    print("\n2. Running expired chats cleanup:")
    result = cleanup_expired_chats()
    print(f"   Deleted: {result['chats_deleted']} chats, {result['messages_deleted']} messages")

    print("\n3. Generating cleanup report:")
    report = generate_cleanup_report()
    print(f"   Total active chats: {report['statistics']['total_active_chats']}")
    print(f"   Auto-delete enabled: {report['statistics']['auto_delete_percentage']}%")

    print("\nAll tests complete!")
