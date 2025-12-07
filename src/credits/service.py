# src/credits/service.py
"""
Production-grade credit service with:
- Async operations for scalability
- Atomic transactions with row-level locking
- Comprehensive error handling
- Business event logging
- Refund handling for failed insights
"""

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, and_
from sqlalchemy.orm import selectinload
import time
from typing import List, Optional
from uuid import UUID
import math
from datetime import datetime, timedelta, timezone
import uuid

from .models import CreditTransaction, CreditPackage, TransactionType, TransactionStatus
from ..users.models import User
from ..chats.models import Chat
from ..rag.models import CategoryInsightType, AnalysisCategory, Insight, InsightStatus
from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    NotFoundException,
    InsufficientCreditsException,
    DatabaseException,
    ExternalServiceException,
    ErrorCode,
    AppException
)

logger = get_logger(__name__)


class CreditService:
    """Service for handling credit operations"""
    
    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # SYNC METHODS (Legacy - Keep for backward compatibility)
    # ========================================================================
    
    def get_balance(self, user_id: str) -> int:
        """Get user's current credit balance (SYNC)"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundException("User", user_id)
        return user.credit_balance

    def add_signup_bonus(self, user_id: str, bonus_amount: int = 50) -> CreditTransaction:
        """Give signup bonus to new user (SYNC)"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundException("User", user_id)
        
        # Check if user already received signup bonus
        existing_bonus = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.type == TransactionType.SIGNUP_BONUS
        ).first()
        
        if existing_bonus:
            logger.info(
                "Signup bonus already claimed",
                extra={"user_id": user_id}
            )
            return existing_bonus
        
        # Add bonus
        user.credit_balance += bonus_amount
        
        transaction = CreditTransaction(
            user_id=user_id,
            type=TransactionType.SIGNUP_BONUS,
            amount=bonus_amount,
            balance_after=user.credit_balance,
            description=f"Welcome bonus: {bonus_amount} coins",
            status=TransactionStatus.COMPLETED
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        log_business_event(
            "signup_bonus_granted",
            user_id=user_id,
            amount=bonus_amount
        )
        
        return transaction

    def get_transaction_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> tuple[List[CreditTransaction], int]:
        """Get user's transaction history with pagination (SYNC)"""
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        )
        
        total_count = query.count()
        
        transactions = query.order_by(
            desc(CreditTransaction.created_at)
        ).limit(limit).offset(offset).all()
        
        return transactions, total_count

    def get_packages(self, active_only: bool = True) -> List[CreditPackage]:
        """Get available credit packages (SYNC)"""
        query = self.db.query(CreditPackage)
        
        if active_only:
            query = query.filter(CreditPackage.is_active)
        
        return query.order_by(CreditPackage.sort_order).all()

    def get_package(self, package_id: UUID) -> Optional[CreditPackage]:
        """Sync: get a single credit package by id (used by sync callers)."""
        return self.db.query(CreditPackage).filter(
            CreditPackage.id == package_id
        ).first()


    # ========================================================================
    # ASYNC METHODS (New - Production Ready)
    # ========================================================================
    
    @classmethod
    async def get_balance_async(cls, db: AsyncSession, user_id: str) -> int:
        """Get user's current credit balance (ASYNC)"""
        start = time.time()
        logger.info(f"DB query START")
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        logger.info(f"DB query DONE in {(time.time()-start)*1000:.1f}ms")

        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException("User", user_id)
        
        return user.credit_balance
    
    @classmethod
    async def add_signup_bonus_async(
        cls,
        db: AsyncSession,
        user_id: str,
        bonus_amount: int = 50
    ) -> CreditTransaction:
        """
        Give signup bonus to new user (ASYNC)
        
        This is called when user first registers.
        Idempotent - won't give bonus twice.
        
        Args:
            db: Async database session
            user_id: User ID
            bonus_amount: Bonus amount (default 50 coins)
        
        Returns:
            CreditTransaction record
        """
        logger.info(
            "Processing signup bonus",
            extra={
                "user_id": user_id,
                "extra_data": {"bonus_amount": bonus_amount}
            }
        )
        
        try:
            # Get user with row lock
            result = await db.execute(
                select(User)
                .where(User.user_id == user_id)
                .with_for_update()
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundException("User", user_id)
            
            # Check if user already received signup bonus (idempotency)
            result = await db.execute(
                select(CreditTransaction).where(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.type == TransactionType.SIGNUP_BONUS
                )
            )
            existing_bonus = result.scalar_one_or_none()
            
            if existing_bonus:
                logger.info(
                    "Signup bonus already claimed",
                    extra={
                        "user_id": user_id,
                        "extra_data": {
                            "transaction_id": str(existing_bonus.id),
                            "claimed_at": existing_bonus.created_at.isoformat()
                        }
                    }
                )
                return existing_bonus
            
            # Add bonus to balance
            user.credit_balance += bonus_amount
            
            # Create transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                type=TransactionType.SIGNUP_BONUS,
                amount=bonus_amount,
                balance_after=user.credit_balance,
                description=f"Welcome bonus: {bonus_amount} coins",
                status=TransactionStatus.COMPLETED
            )
            
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
            
            log_business_event(
                "signup_bonus_granted",
                user_id=user_id,
                amount=bonus_amount,
                new_balance=user.credit_balance
            )
            
            logger.info(
                f"✓ Signup bonus granted: {bonus_amount} coins",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "transaction_id": str(transaction.id),
                        "new_balance": user.credit_balance
                    }
                }
            )
            
            return transaction
            
        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to grant signup bonus: {str(e)}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to grant signup bonus",
                original_error=e
            )

    @classmethod
    async def add_transaction_async(
        cls,
        db: AsyncSession,
        user_id: str,
        transaction_type: TransactionType,
        amount: int,
        description: str,
        payment_id: Optional[str] = None,
        package_id: Optional[UUID] = None,
        transaction_metadata: Optional[dict] = None
    ) -> CreditTransaction:
        """
        Add credits to user balance (ASYNC)
        Used by payment webhook to credit coins after successful payment
        """
        logger.info(
            f"Adding transaction: {amount} coins",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "type": transaction_type.value,
                    "amount": amount
                }
            }
        )
        
        try:
            # Get user with row-level lock to prevent race conditions
            result = await db.execute(
                select(User)
                .where(User.user_id == user_id)
                .with_for_update()  # CRITICAL: Row-level lock
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundException("User", user_id)
            
            # Update balance
            user.credit_balance += amount
            
            # Create transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                type=transaction_type,
                amount=amount,
                balance_after=user.credit_balance,
                description=description,
                payment_id=payment_id,
                package_id=package_id,
                status=TransactionStatus.COMPLETED,
                transaction_metadata=transaction_metadata or {}
            )
            
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
            
            logger.info(
                f"Transaction added: {amount} coins",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "transaction_id": str(transaction.id),
                        "new_balance": user.credit_balance
                    }
                }
            )
            
            return transaction
            
        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to add transaction: {str(e)}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to credit coins",
                original_error=e
            )

    @classmethod
    async def deduct_credits_async(
        cls,
        db: AsyncSession,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: str,
        chat_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        metadata: Optional[dict] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user balance with atomic locking (ASYNC)
        
        This is called BEFORE insight generation starts.
        Uses row-level locking to prevent race conditions.
        
        Raises:
            InsufficientCreditsException: Not enough credits
            DatabaseException: Database operation failed
        """
        logger.info(
            f"Deducting {amount} credits",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "type": transaction_type.value,
                    "chat_id": str(chat_id) if chat_id else None
                }
            }
        )
        
        try:
            # CRITICAL: Get user with row-level lock
            # This prevents concurrent unlock requests from the same user
            result = await db.execute(
                select(User)
                .where(User.user_id == user_id)
                .with_for_update()  # Exclusive row lock
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundException("User", user_id)
            
            # Check balance
            if user.credit_balance < amount:
                logger.warning(
                    "Insufficient credits",
                    extra={
                        "user_id": user_id,
                        "extra_data": {
                            "required": amount,
                            "available": user.credit_balance
                        }
                    }
                )
                raise InsufficientCreditsException(
                    required=amount,
                    available=user.credit_balance
                )
            
            # Deduct credits (atomic)
            user.credit_balance -= amount
            
            # Create transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                type=transaction_type,
                amount=-amount,  # Negative for deduction
                balance_after=user.credit_balance,
                description=description,
                chat_id=chat_id,
                status=TransactionStatus.COMPLETED,
                metadata=metadata
            )
            
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
            
            log_business_event(
                "credits_deducted",
                user_id=user_id,
                amount=amount,
                chat_id=str(chat_id) if chat_id else None,
                category_id=str(category_id) if category_id else None,
                new_balance=user.credit_balance
            )
            
            logger.info(
                f"Credits deducted: {amount}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "transaction_id": str(transaction.id),
                        "new_balance": user.credit_balance
                    }
                }
            )
            
            return transaction
            
        except (NotFoundException, InsufficientCreditsException):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to deduct credits: {str(e)}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to deduct credits",
                original_error=e
            )

    @classmethod
    async def get_package_async(
        cls, 
        db: AsyncSession, 
        package_id: UUID
    ) -> Optional[CreditPackage]:
        """Get single credit package by ID (ASYNC)"""
        result = await db.execute(
            select(CreditPackage).where(CreditPackage.id == package_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def unlock_insights_for_category(
        cls,
        db: AsyncSession,
        user_id: str,
        chat_id: UUID,
        category_id: UUID
    ) ->  dict:
        """
        Reserve coins and start insight generation
        
        NO COINS DEDUCTED YET - only reserved.
        Coins will be charged after ALL insights succeed.
        """
        logger.info(
            "Insights unlock requested",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "category_id": str(category_id)
                }
            }
        )
        
        try:
            # 1. Verify chat ownership
            result = await db.execute(
                select(Chat).where(
                    and_(
                        Chat.id == chat_id,
                        Chat.user_id == user_id,
                        Chat.is_deleted == False
                    )
                )
            )
            chat = result.scalar_one_or_none()
            
            if not chat:
                raise NotFoundException("Chat", str(chat_id))
            
            # 2. Check if already unlocked (idempotency)
            if chat.insights_unlocked_at and chat.insights_generation_status == "completed":
                logger.warning(
                    "Insights already completed",
                    extra={
                        "user_id": user_id,
                        "extra_data": {"chat_id": str(chat_id)}
                    }
                )
                raise AppException(
                    message="Insights already generated for this chat",
                    error_code=ErrorCode.VALIDATION_ERROR,
                    status_code=400
                )
            
            # 3. Get category cost
            result = await db.execute(
                select(AnalysisCategory).where(
                    AnalysisCategory.id == category_id
                )
            )
            category = result.scalar_one_or_none()
            
            if not category or not category.is_active:
                raise NotFoundException("Category", str(category_id))
            
            total_cost = category.credit_cost
            
            # 4. Ensure chat is indexed
            if chat.vector_status != "completed":
                await cls._ensure_chat_indexed(db, chat, user_id)
            
            # 5. Get insight types for this category (with eager loading)
            result = await db.execute(
                select(CategoryInsightType)
                .where(CategoryInsightType.category_id == category_id)
                .options(selectinload(CategoryInsightType.insight_type))  # CRITICAL: Eager load
            )
            category_insights = result.scalars().all()
            
            if not category_insights:
                raise NotFoundException("Category insights", str(category_id))
            
            # 6. DEDUCT COINS IMMEDIATELY (will refund if generation fails)
            transaction = await cls.deduct_credits_async(
                db=db,
                user_id=user_id,
                amount=total_cost,
                transaction_type=TransactionType.INSIGHT_UNLOCK,
                description=f"Unlock {category.display_name or category.name} insights",
                chat_id=chat_id,
                category_id=category_id,
                metadata={
                    "chat_id": str(chat_id),
                    "category_id": str(category_id),
                    "insights_count": len(category_insights),
                    "immediate_deduction": True  # Mark for tracking
                }
            )
            
            # 7. Create insight records
            job_id = str(uuid.uuid4())
            
            for category_insight in category_insights:
                if not category_insight.insight_type.is_active:
                    continue
                
                result = await db.execute(
                    select(Insight).where(
                        and_(
                            Insight.chat_id == chat_id,
                            Insight.insight_type_id == category_insight.insight_type_id
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    insight = Insight(
                        chat_id=chat_id,
                        insight_type_id=category_insight.insight_type_id,
                        status=InsightStatus.PENDING,
                        content=None
                    )
                    db.add(insight)
            
            # Update chat
            if not chat.category_id:
                chat.category_id = category_id
            
            chat.insights_job_id = job_id
            chat.total_insights_requested = len(category_insights)
            
            await db.commit()
            
            # 8. Launch generation
            from ..rag.generation_service import InsightGenerationOrchestrator
            from ..rag.tasks import orchestrate_insight_generation
            
            orchestrator = InsightGenerationOrchestrator(db)
            job = await orchestrator.create_generation_job_async(
                job_id=job_id,
                chat_id=chat_id,
                category_id=category_id,
                user_id=user_id,
                insight_types=category_insights
            )
            
            # Launch Celery task
            orchestrate_insight_generation.delay(job_id)

            if job.estimated_completion_at:
                secs = job.estimated_completion_at.timestamp() - datetime.now(timezone.utc).timestamp()
                # round up so UI doesn't see 0 prematurely; clamp to 0 minimum
                estimated_seconds = max(0, int(math.ceil(secs)))
            else:
                estimated_seconds = None

            # Get remaining balance (after deduction)
            remaining_balance = await cls.get_balance_async(db, user_id)
            
            log_business_event(
                "insights_generation_started",
                user_id=user_id,
                chat_id=str(chat_id),
                category_id=str(category_id),
                category_name=category.name,
                insight_count=len(category_insights),
                coins_deducted=total_cost,  # Deducted immediately
                transaction_id=str(transaction.id),
                job_id=job_id
            )

            return {
                "success": True,
                "job_id": job_id,
                "coins_deducted": total_cost,  # Deducted immediately
                "transaction_id": str(transaction.id),
                "remaining_balance": remaining_balance,
                "total_insights": len(category_insights),
                "estimated_time_seconds": estimated_seconds,
                "message": f"Generating {len(category_insights)} insights. {total_cost} coins deducted (auto-refunded if generation fails).",
                "poll_url": f"/insights/jobs/{job_id}/status",
                "indexed_on_demand": chat.vector_status == "pending"
            }
            
        except (NotFoundException, InsufficientCreditsException, AppException):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to unlock insights: {str(e)}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "category_id": str(category_id)
                    }
                },
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to unlock insights",
                original_error=e
            )

    @classmethod
    async def _ensure_chat_indexed(
        cls,
        db: AsyncSession,
        chat: Chat,
        user_id: str
    ):
        """
        Ensure chat is indexed before generating insights
        
        This is synchronous (blocks for 1-3 seconds) but necessary
        to ensure vectors are ready for RAG.
        """
        logger.info(
            f"Chat not indexed. Status: {chat.vector_status}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat.id)}
            }
        )
        
        if chat.vector_status == "indexing":
            raise AppException(
                message="Chat is currently being indexed. Please wait.",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=409
            )
        
        # if chat.vector_status == "failed":
        #     raise AppException(
        #         message="Chat indexing failed. Please re-upload or contact support.",
        #         error_code=ErrorCode.VECTOR_INDEXING_FAILED,
        #         status_code=400
        #     )
        
        # Vector status is "pending" - trigger indexing NOW
        logger.info(
            "Triggering synchronous vector indexing",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat.id)}
            }
        )
        
        try:
            # Import here to avoid circular dependency
            from ..vector.service import vector_service
            
            # SYNCHRONOUS indexing (blocks for 1-3 seconds)
            # We need a sync Session for vector_service
            from ..database import SessionLocal
            sync_db = SessionLocal()
            try:
                success = vector_service.create_chat_chunks(sync_db, chat.id)
                
                if not success:
                    raise ExternalServiceException(
                        "Vector Database",
                        "Failed to index chat",
                        error_code=ErrorCode.VECTOR_INDEXING_FAILED
                    )
                
                # Refresh chat to get updated vector_status
                await db.refresh(chat)
                
                logger.info(
                    "Vector indexing completed",
                    extra={
                        "user_id": user_id,
                        "extra_data": {"chat_id": str(chat.id)}
                    }
                )
            finally:
                sync_db.close()
                
        except Exception as e:
            logger.error(
                f"Indexing failed: {str(e)}",
                extra={
                    "user_id": user_id,
                    "extra_data": {"chat_id": str(chat.id)}
                },
                exc_info=True
            )
            raise ExternalServiceException(
                "Vector Database",
                f"Failed to prepare chat: {str(e)}",
                error_code=ErrorCode.VECTOR_INDEXING_FAILED
            )


    @classmethod
    async def refund_transaction_async(
        cls,
        db: AsyncSession,
        chat_id: UUID,
        reason: str
    ) -> CreditTransaction:
        """
        Refund credits for failed insight generation
        Called automatically when >50% of insights fail
        
        Args:
            db: Async database session
            chat_id: Chat ID
            reason: Refund reason
        
        Returns:
            CreditTransaction (refund record)
        """
        logger.info(
            "Processing refund",
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "reason": reason
                }
            }
        )
        
        try:
            # Get chat
            result = await db.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            chat = result.scalar_one_or_none()
            
            if not chat:
                raise NotFoundException("Chat", str(chat_id))
            
            # Find original deduction transaction
            result = await db.execute(
                select(CreditTransaction).where(
                    and_(
                        CreditTransaction.chat_id == chat_id,
                        CreditTransaction.type == TransactionType.INSIGHT_UNLOCK,
                        CreditTransaction.status == TransactionStatus.COMPLETED
                    )
                ).order_by(desc(CreditTransaction.created_at))
            )
            original_transaction = result.scalars().first()
            
            if not original_transaction:
                logger.warning(
                    "No transaction found to refund",
                    extra={"extra_data": {"chat_id": str(chat_id)}}
                )
                raise NotFoundException("Transaction", str(chat_id))
            
            # Check if already refunded
            if original_transaction.status == TransactionStatus.REFUNDED:
                logger.info(
                    "Transaction already refunded",
                    extra={"extra_data": {"transaction_id": str(original_transaction.id)}}
                )
                return original_transaction
            
            # Refund the amount (positive because we're adding back)
            refund_amount = abs(original_transaction.amount)
            
            refund = await cls.add_transaction_async(
                db=db,
                user_id=original_transaction.user_id,
                transaction_type=TransactionType.REFUND,
                amount=refund_amount,  # Positive to add back
                description=f"Refund: {reason}",
                transaction_metadata={
                    "original_transaction_id": str(original_transaction.id),
                    "chat_id": str(chat_id),
                    "reason": reason
                }
            )
            
            # Mark original as refunded
            original_transaction.status = TransactionStatus.REFUNDED
            await db.commit()
            
            log_business_event(
                "credits_refunded",
                user_id=original_transaction.user_id,
                chat_id=str(chat_id),
                amount=refund_amount,
                reason=reason
            )
            
            logger.info(
                f"Refund completed: {refund_amount} credits",
                extra={
                    "user_id": original_transaction.user_id,
                    "extra_data": {
                        "refund_id": str(refund.id),
                        "amount": refund_amount
                    }
                }
            )
            
            return refund
            
        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to process refund: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to process refund",
                original_error=e
            )