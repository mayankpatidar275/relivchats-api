# src/payments/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import uuid

from .models import PaymentOrder, PaymentRefund
from .base import PaymentProvider, PaymentStatus
from .factory import PaymentProviderFactory
from ..credits.service import CreditService
from ..credits.models import CreditTransaction, TransactionType

class PaymentService:
    """Service for handling payment operations"""
    
    def __init__(self, db: AsyncSession, provider_configs: dict):
        self.db = db
        self.provider_configs = provider_configs
    
    async def create_order(
        self,
        user_id: str,
        package_id: str,
        amount: int,
        currency: str,
        coins: int,
        provider: PaymentProvider,
        idempotency_key: Optional[str] = None
    ) -> PaymentOrder:
        """
        Create a payment order
        
        Args:
            user_id: User ID
            package_id: Credit package ID
            amount: Amount in smallest unit
            currency: Currency code
            coins: Coins to be credited
            provider: Payment provider
            idempotency_key: Idempotency key for duplicate prevention
        
        Returns:
            PaymentOrder instance
        """
        # Check for duplicate order
        if idempotency_key:
            existing = await self.db.execute(
                select(PaymentOrder).where(
                    PaymentOrder.idempotency_key == idempotency_key
                )
            )
            existing_order = existing.scalar_one_or_none()
            if existing_order:
                return existing_order
        
        # Create provider order
        provider_client = PaymentProviderFactory.create_provider(
            provider,
            self.provider_configs[provider.value]
        )
        
        order_response = await provider_client.create_order(
            amount=amount,
            currency=currency,
            user_id=user_id,
            package_id=package_id,
            metadata={"coins": coins}
        )
        
        # Store in database
        payment_order = PaymentOrder(
            user_id=user_id,
            package_id=package_id,
            provider=provider,
            provider_order_id=order_response.provider_order_id,
            amount=amount,
            currency=currency,
            coins=coins,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            payment_order_metadata={
                "client_secret": order_response.client_secret,
                "checkout_url": order_response.checkout_url,
                **order_response.metadata
            }
        )
        
        self.db.add(payment_order)
        await self.db.commit()
        await self.db.refresh(payment_order)
        
        return payment_order
    
    async def process_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes,
        signature: str,
        headers: dict
    ) -> bool:
        """
        Process payment webhook
        
        Args:
            provider: Payment provider
            payload: Webhook payload
            signature: Webhook signature
            headers: Request headers
        
        Returns:
            True if processed successfully
        """
        # Verify webhook
        provider_client = PaymentProviderFactory.create_provider(
            provider,
            self.provider_configs[provider.value]
        )
        
        verification = await provider_client.verify_webhook(
            payload, signature, headers
        )
        
        if not verification.is_valid:
            return False
        
        # Find payment order
        result = await self.db.execute(
            select(PaymentOrder).where(
                PaymentOrder.provider_order_id == verification.provider_order_id
            )
        )
        payment_order = result.scalar_one_or_none()
        
        if not payment_order:
            # Order not found, might be test webhook
            return True
        
        # Update webhook tracking
        payment_order.webhook_count += 1
        payment_order.webhook_received_at = datetime.utcnow()
        
        # Check if already processed (idempotency)
        if payment_order.status == PaymentStatus.COMPLETED:
            await self.db.commit()
            return True
        
        # Update order status
        payment_order.status = verification.status
        payment_order.provider_payment_id = verification.payment_id
        
        if verification.status == PaymentStatus.COMPLETED:
            payment_order.completed_at = datetime.utcnow()
            
            # Credit coins to user
            credit_service = CreditService(self.db)
            await credit_service.add_transaction(
                user_id=payment_order.user_id,
                transaction_type=TransactionType.PURCHASE,
                amount=payment_order.coins,
                description=f"Purchased {payment_order.coins} coins",
                metadata={
                    "payment_order_id": str(payment_order.id),
                    "provider_order_id": payment_order.provider_order_id,
                    "provider_payment_id": verification.payment_id,
                    "amount_paid": payment_order.amount,
                    "currency": payment_order.currency
                }
            )
        
        await self.db.commit()
        return True
    
    async def create_refund(
        self,
        payment_order_id: str,
        amount: int,
        reason: str,
        coins_to_deduct: int
    ) -> PaymentRefund:
        """
        Create a refund
        
        Args:
            payment_order_id: Payment order ID
            amount: Amount to refund (in smallest unit)
            reason: Refund reason
            coins_to_deduct: Coins to deduct from user
        
        Returns:
            PaymentRefund instance
        """
        # Get payment order
        result = await self.db.execute(
            select(PaymentOrder).where(PaymentOrder.id == payment_order_id)
        )
        payment_order = result.scalar_one_or_none()
        
        if not payment_order:
            raise ValueError("Payment order not found")
        
        if not payment_order.provider_payment_id:
            raise ValueError("No payment ID to refund")
        
        # Create provider refund
        provider_client = PaymentProviderFactory.create_provider(
            payment_order.provider,
            self.provider_configs[payment_order.provider.value]
        )
        
        refund_response = await provider_client.create_refund(
            payment_id=payment_order.provider_payment_id,
            amount=amount,
            reason=reason,
            metadata={"payment_order_id": str(payment_order_id)}
        )
        
        # Store refund
        payment_refund = PaymentRefund(
            payment_order_id=payment_order_id,
            user_id=payment_order.user_id,
            provider=payment_order.provider,
            provider_refund_id=refund_response.provider_refund_id,
            provider_payment_id=payment_order.provider_payment_id,
            amount=amount,
            currency=payment_order.currency,
            coins_refunded=coins_to_deduct,
            reason=reason,
            status=refund_response.status,
            processed_at=datetime.utcnow(),
            metadata=refund_response.metadata
        )
        
        self.db.add(payment_refund)
        
        # Deduct coins from user
        credit_service = CreditService(self.db)
        await credit_service.add_transaction(
            user_id=payment_order.user_id,
            transaction_type=TransactionType.REFUND,
            amount=-coins_to_deduct,
            description=f"Refund: {reason}",
            metadata={
                "payment_order_id": str(payment_order_id),
                "refund_id": str(payment_refund.id),
                "provider_refund_id": refund_response.provider_refund_id
            }
        )
        
        await self.db.commit()
        await self.db.refresh(payment_refund)
        
        return payment_refund
    
    async def get_order_status(
        self,
        order_id: str
    ) -> Optional[PaymentOrder]:
        """Get payment order by ID"""
        result = await self.db.execute(
            select(PaymentOrder).where(PaymentOrder.id == order_id)
        )
        return result.scalar_one_or_none()