from sqlalchemy.orm import Session
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import math
from datetime import datetime
import uuid
from .models import CreditTransaction, CreditPackage, TransactionType, TransactionStatus
from ..users.models import User
from ..chats.models import Chat
from ..rag.models import CategoryInsightType, Insight, InsightStatus
from fastapi import HTTPException
from ..rag.tasks import orchestrate_insight_generation  # ADD THIS IMPORT
from ..rag.generation_service import InsightGenerationOrchestrator  # ADD THIS

class CreditService:
    def __init__(self, db: Session):
        self.db = db

    def get_balance(self, user_id: str) -> int:
        """Get user's current credit balance"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.credit_balance

    def add_signup_bonus(self, user_id: str, bonus_amount: int = 50) -> CreditTransaction:
        """Give signup bonus to new user"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already received signup bonus
        existing_bonus = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.type == TransactionType.SIGNUP_BONUS
        ).first()
        
        if existing_bonus:
            return existing_bonus  # Already received bonus
        
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
        
        return transaction

    def deduct_credits(
        self, 
        user_id: str, 
        amount: int, 
        transaction_type: TransactionType,
        description: str,
        chat_id: Optional[UUID] = None,
        metadata: Optional[dict] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user balance (atomic transaction)
        Raises HTTPException if insufficient balance
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check balance
        if user.credit_balance < amount:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "insufficient_credits",
                    "required": amount,
                    "available": user.credit_balance,
                    "deficit": amount - user.credit_balance
                }
            )
        
        # Deduct credits (atomic)
        user.credit_balance -= amount
        
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
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction

    def add_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: str,
        payment_id: Optional[str] = None,
        package_id: Optional[UUID] = None,
        metadata: Optional[dict] = None
    ) -> CreditTransaction:
        """Add credits to user balance"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.credit_balance += amount
        
        transaction = CreditTransaction(
            user_id=user_id,
            type=transaction_type,
            amount=amount,
            balance_after=user.credit_balance,
            description=description,
            payment_id=payment_id,
            package_id=package_id,
            status=TransactionStatus.COMPLETED,
            metadata=metadata
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction

    def get_transaction_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> tuple[List[CreditTransaction], int]:
        """Get user's transaction history with pagination"""
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        )
        
        total_count = query.count()
        
        transactions = query.order_by(
            desc(CreditTransaction.created_at)
        ).limit(limit).offset(offset).all()
        
        return transactions, total_count

    def get_packages(self, active_only: bool = True) -> List[CreditPackage]:
        """Get available credit packages"""
        query = self.db.query(CreditPackage)
        
        if active_only:
            query = query.filter(CreditPackage.is_active == True)
        
        return query.order_by(CreditPackage.sort_order).all()

    def get_package(self, package_id: UUID) -> Optional[CreditPackage]:
        """Sync: get a single credit package by id (used by sync callers)."""
        pkg = self.db.query(CreditPackage).filter(CreditPackage.id == package_id).first()
        return pkg

    @classmethod
    async def get_package_async(cls, db: AsyncSession, package_id: UUID) -> Optional[CreditPackage]:
        """
        Async helper to fetch a single CreditPackage using an AsyncSession.
        Use this from async endpoints/services to avoid blocking the event loop.
        Example:
            package = await CreditService.get_package_async(async_db, package_id)
        """
        result = await db.execute(
            select(CreditPackage).where(CreditPackage.id == package_id)
        )
        package = result.scalars().first()
        return package

    def unlock_insights_for_category(
        self, 
        user_id: str, 
        chat_id: UUID, 
        category_id: UUID
    ) -> dict:
        """
        Unlock all insights for a chat's category with lazy vector indexing
        Flow:
        1. Verify chat ownership
        2. Check vector status → trigger indexing if needed
        3. Deduct credits
        4. Create insight records
        5. Launch generation job
        """
        # 1. Verify chat exists and belongs to user
        chat = self.db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == user_id
        ).first()
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # 2. Check if insights already unlocked
        if chat.insights_unlocked_at:
            raise HTTPException(
                status_code=400, 
                detail="Insights already unlocked for this chat. Check job status or retry failed insights."
            )
        
        # 3. CRITICAL: Check vector status and trigger indexing if needed
        if chat.vector_status != "completed":
            print(f"⚠️  Chat {chat_id} not indexed yet. Status: {chat.vector_status}")
            
            if chat.vector_status == "indexing":
                raise HTTPException(
                    status_code=409,
                    detail="Chat is currently being indexed. Please wait and try again in a few seconds."
                )
            
            if chat.vector_status == "failed":
                raise HTTPException(
                    status_code=400,
                    detail="Chat indexing failed. Please contact support or re-upload the chat."
                )
            
            # Vector status is "pending" - trigger indexing NOW
            print(f"🔄 Triggering vector indexing for chat {chat_id}")
            
            # SYNCHRONOUS indexing (blocks for 1-3 seconds)
            # This ensures vectors are ready before generating insights
            from ..vector.service import vector_service
            
            try:
                success = vector_service.create_chat_chunks(self.db, chat_id)
                
                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to index chat. Please try again or contact support."
                    )
                
                print(f"✓ Chat {chat_id} indexed successfully")
                
            except Exception as e:
                print(f"✗ Indexing failed for chat {chat_id}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to prepare chat for insights: {str(e)}"
                )
        
        # 4. Get all insight types for this category
        category_insights = self.db.query(CategoryInsightType).filter(
            CategoryInsightType.category_id == category_id
        ).all()
        
        if not category_insights:
            raise HTTPException(status_code=404, detail="No insights found for this category")
        
        # 5. Calculate total cost
        total_cost = sum(
            ci.insight_type.credit_cost 
            for ci in category_insights 
            if ci.insight_type.is_active
        )
        
        # 6. Deduct credits (AFTER successful indexing)
        transaction = self.deduct_credits(
            user_id=user_id,
            amount=total_cost,
            transaction_type=TransactionType.INSIGHT_UNLOCK,
            description=f"Unlocked {len(category_insights)} insights for chat",
            metadata={
                "chat_id": str(chat_id),
                "category_id": str(category_id),
                "insight_count": len(category_insights),
                "cost_per_insight": {
                    str(ci.insight_type_id): ci.insight_type.credit_cost
                    for ci in category_insights
                }
            }
        )
        
        # 7. Create insight records
        job_id = str(uuid.uuid4())
        
        for category_insight in category_insights:
            if not category_insight.insight_type.is_active:
                continue
            
            existing = self.db.query(Insight).filter(
                Insight.chat_id == chat_id,
                Insight.insight_type_id == category_insight.insight_type_id
            ).first()
            
            if not existing:
                insight = Insight(
                    chat_id=chat_id,
                    insight_type_id=category_insight.insight_type_id,
                    status=InsightStatus.PENDING,
                    content=None
                )
                self.db.add(insight)
        
        # Update chat category if not set
        if not chat.category_id:
            chat.category_id = category_id
        
        self.db.commit()
        
        # 8. Create generation job record
        orchestrator = InsightGenerationOrchestrator(self.db)
        job = orchestrator.create_generation_job(
            job_id=job_id,
            chat_id=chat_id,
            category_id=category_id,
            user_id=user_id,
            insight_types=category_insights
        )
        
        # 9. Launch Celery orchestrator task
        orchestrate_insight_generation.delay(job_id)
        
        if job.estimated_completion_at:
            secs = job.estimated_completion_at.timestamp() - datetime.utcnow().timestamp()
            # round up so UI doesn't see 0 prematurely; clamp to 0 minimum
            estimated_seconds = max(0, int(math.ceil(secs)))
        else:
            estimated_seconds = None

        return {
            "success": True,
            "job_id": job_id,
            "coins_deducted": total_cost,
            "remaining_balance": self.get_balance(user_id),
            "total_insights": len(category_insights),
            "estimated_time_seconds": estimated_seconds,
            "message": f"Successfully unlocked {len(category_insights)} insights. Processing started in background.",
            "poll_url": f"/insights/jobs/{job_id}/status",
            "indexed_on_demand": chat.vector_status == "pending"  # NEW: Tell frontend indexing happened
        }

    def refund_transaction(
            self, 
            transaction_id: UUID, 
            reason: str
        ) -> CreditTransaction:
            """Refund a transaction"""
            transaction = self.db.query(CreditTransaction).filter(
                CreditTransaction.id == transaction_id
            ).first()
            
            if not transaction:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            if transaction.status == TransactionStatus.REFUNDED:
                raise HTTPException(status_code=400, detail="Transaction already refunded")
            
            # Refund the amount
            refund = self.add_credits(
                user_id=transaction.user_id,
                amount=abs(transaction.amount),
                transaction_type=TransactionType.REFUND,
                description=f"Refund: {reason}",
                metadata={
                    "original_transaction_id": str(transaction_id),
                    "reason": reason
                }
            )
            
            # Mark original as refunded
            transaction.status = TransactionStatus.REFUNDED
            self.db.commit()
            
            return refund
