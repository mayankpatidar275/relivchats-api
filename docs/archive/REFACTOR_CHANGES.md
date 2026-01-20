# Code Changes - asyncio.run() Refactoring

## File 1: src/credits/service.py

### New Method: charge_reserved_coins_sync()

```python
def charge_reserved_coins_sync(self, chat_id: UUID) -> CreditTransaction:
    """
    SYNC version: Charge coins after successful generation

    Used by Celery tasks (sync_generation_service.py)
    Same logic as async version but for sync context
    """
    logger.info(
        "Charging reserved coins (SYNC)",
        extra={"extra_data": {"chat_id": str(chat_id)}}
    )

    try:
        # Get chat
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()

        if not chat:
            raise NotFoundException("Chat", str(chat_id))

        if chat.reserved_coins == 0:
            raise AppException(
                message="No coins reserved for this chat",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400
            )

        # Check if reservation expired
        if chat.reservation_expires_at and chat.reservation_expires_at < datetime.now(timezone.utc):
            logger.error(
                "Reservation expired, cannot charge",
                extra={
                    "user_id": chat.user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "expired_at": chat.reservation_expires_at.isoformat()
                    }
                }
            )
            raise AppException(
                message="Reservation expired",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400
            )

        amount = chat.reserved_coins
        user_id = chat.user_id

        # Deduct coins with row lock (prevent race conditions)
        user = self.db.query(User).filter(
            User.user_id == user_id
        ).with_for_update().first()

        if not user:
            raise NotFoundException("User", user_id)

        # Check balance
        if user.credit_balance < amount:
            logger.critical(
                "User spent coins during generation!",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "reserved": amount,
                        "available": user.credit_balance
                    }
                }
            )

            # POLICY DECISION: Hide insights until user adds credits
            chat.insights_generation_status = "payment_failed"
            self.db.commit()

            # Queue retry task
            from ..rag.tasks import retry_payment_deduction
            retry_payment_deduction.apply_async(
                args=[str(chat_id)],
                countdown=300  # Retry after 5 minutes
            )

            raise InsufficientCreditsException(
                required=amount,
                available=user.credit_balance
            )

        # Deduct coins (atomic)
        user.credit_balance -= amount

        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            type=TransactionType.INSIGHT_UNLOCK,
            amount=-amount,  # Negative for deduction
            balance_after=user.credit_balance,
            description=f"Generated {chat.total_insights_requested} insights",
            chat_id=chat_id,
            status=TransactionStatus.COMPLETED,
            metadata={
                "chat_id": str(chat_id),
                "category_id": str(chat.category_id),
                "insights_count": chat.total_insights_requested,
                "charged_after_generation": True
            }
        )

        # Release reservation
        chat.reserved_coins = 0
        chat.reservation_expires_at = None
        chat.insights_generation_status = "completed"

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        log_business_event(
            "coins_charged_after_generation",
            user_id=user_id,
            chat_id=str(chat_id),
            amount=amount,
            transaction_id=str(transaction.id)
        )

        logger.info(
            f"Coins charged successfully: {amount}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "transaction_id": str(transaction.id)
                }
            }
        )

        return transaction

    except (NotFoundException, InsufficientCreditsException, AppException):
        self.db.rollback()
        raise
    except Exception as e:
        self.db.rollback()
        logger.error(
            f"Failed to charge coins: {str(e)}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        raise DatabaseException(
            message="Failed to charge coins",
            original_error=e
        )
```

### New Method: release_reservation_sync()

```python
def release_reservation_sync(self, chat_id: UUID, reason: str = "Generation failed"):
    """
    SYNC version: Release coin reservation without charging

    Used by Celery tasks (sync_generation_service.py)
    Called when generation fails or is cancelled
    """
    logger.info(
        "Releasing coin reservation (SYNC)",
        extra={"extra_data": {"chat_id": str(chat_id), "reason": reason}}
    )

    try:
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()

        if not chat:
            return

        if chat.reserved_coins > 0:
            reserved_amount = chat.reserved_coins

            chat.reserved_coins = 0
            chat.reservation_expires_at = None
            chat.insights_generation_status = "failed"

            self.db.commit()

            log_business_event(
                "reservation_released",
                user_id=chat.user_id,
                chat_id=str(chat_id),
                amount=reserved_amount,
                reason=reason
            )

            logger.info(
                f"Reservation released: {reserved_amount} coins",
                extra={
                    "user_id": chat.user_id,
                    "extra_data": {"chat_id": str(chat_id)}
                }
            )

    except Exception as e:
        self.db.rollback()
        logger.error(
            f"Failed to release reservation: {str(e)}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
```

---

## File 2: src/rag/sync_generation_service.py

### Method: _charge_coins_after_success()

**BEFORE**:
```python
def _charge_coins_after_success(self, job: InsightGenerationJob, chat: Chat):
    """Charge coins after all insights succeed"""
    logger.info(
        f"All insights completed successfully! Charging {chat.reserved_coins} coins",
        extra={
            "user_id": job.user_id,
            "extra_data": {
                "job_id": job.job_id,
                "chat_id": str(job.chat_id),
                "reserved_coins": chat.reserved_coins
            }
        }
    )

    # Run async function in sync context
    import asyncio

    async def charge_coins():
        from ..database import async_session
        async with async_session() as async_db:
            try:
                transaction = await CreditService.charge_reserved_coins(
                    db=async_db,
                    chat_id=job.chat_id
                )
                logger.info(f"✓ Coins charged: {transaction.amount}")
                return True
            except Exception as e:
                logger.error(f"Failed to charge coins: {e}")
                return False

    try:
        success = asyncio.run(charge_coins())
        if not success:
            # Queue retry
            from .tasks import retry_payment_deduction
            retry_payment_deduction.delay(str(job.chat_id))

    except Exception as e:
        logger.error(f"Error charging coins: {e}")
        # Queue retry
        from .tasks import retry_payment_deduction
        retry_payment_deduction.delay(str(job.chat_id))
```

**AFTER**:
```python
def _charge_coins_after_success(self, job: InsightGenerationJob, chat: Chat):
    """Charge coins after all insights succeed"""
    logger.info(
        f"All insights completed successfully! Charging {chat.reserved_coins} coins",
        extra={
            "user_id": job.user_id,
            "extra_data": {
                "job_id": job.job_id,
                "chat_id": str(job.chat_id),
                "reserved_coins": chat.reserved_coins
            }
        }
    )

    # Use sync version of CreditService (no asyncio.run overhead)
    try:
        service = CreditService(self.db)
        transaction = service.charge_reserved_coins_sync(job.chat_id)
        logger.info(f"✓ Coins charged: {transaction.amount}")

    except Exception as e:
        logger.error(f"Error charging coins: {e}")
        # Queue retry
        from .tasks import retry_payment_deduction
        retry_payment_deduction.delay(str(job.chat_id))
```

### Method: _release_reservation_after_failure()

**BEFORE**:
```python
def _release_reservation_after_failure(self, job: InsightGenerationJob, chat: Chat):
    """Release coin reservation when generation fails"""
    logger.info(
        f"{job.failed_insights} insights failed, releasing reservation",
        extra={
            "user_id": job.user_id,
            "extra_data": {
                "job_id": job.job_id,
                "chat_id": str(job.chat_id),
                "reserved_coins": chat.reserved_coins
            }
        }
    )

    from ..credits.service import CreditService
    import asyncio

    async def release_reservation():
        from ..database import async_session
        async with async_session() as async_db:
            await CreditService.release_reservation(
                db=async_db,
                chat_id=job.chat_id,
                reason=f"{job.failed_insights}/{job.total_insights} insights failed"
            )

    try:
        asyncio.run(release_reservation())
        logger.info("✓ Reservation released (no charge)")
    except Exception as e:
        logger.error(f"Failed to release reservation: {e}")
```

**AFTER**:
```python
def _release_reservation_after_failure(self, job: InsightGenerationJob, chat: Chat):
    """Release coin reservation when generation fails"""
    logger.info(
        f"{job.failed_insights} insights failed, releasing reservation",
        extra={
            "user_id": job.user_id,
            "extra_data": {
                "job_id": job.job_id,
                "chat_id": str(job.chat_id),
                "reserved_coins": chat.reserved_coins
            }
        }
    )

    from ..credits.service import CreditService

    # Use sync version of CreditService (no asyncio.run overhead)
    try:
        service = CreditService(self.db)
        service.release_reservation_sync(
            job.chat_id,
            reason=f"{job.failed_insights}/{job.total_insights} insights failed"
        )
        logger.info("✓ Reservation released (no charge)")
    except Exception as e:
        logger.error(f"Failed to release reservation: {e}")
```

---

## Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| Lines in charge method | 31 | 12 |
| Lines in release method | 17 | 10 |
| asyncio imports | 2 | 0 |
| Event loops created per job | 2 | 0 |
| Async function definitions | 2 | 0 |
| Direct sync method calls | 0 | 2 |
| Code complexity | High | Low |

**Efficiency Gain**: 100% reduction in event loop creation/destruction overhead per job execution.
