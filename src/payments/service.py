# src/payments/service.py
"""
Production-grade payment service with:
- Webhook signature verification
- Idempotency protection
- Atomic credit operations
- Comprehensive error handling
- Audit logging
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
import uuid

from .models import PaymentOrder, PaymentRefund
from .base import PaymentProvider, PaymentStatus
from .factory import PaymentProviderFactory
from ..credits.service import CreditService
from ..credits.models import TransactionType
from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    DatabaseException,
    ExternalServiceException,
    ErrorCode,
    AppException
)

logger = get_logger(__name__)


class PaymentService:
    """Service for handling payment operations with full error handling"""
    
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
        Create a payment order with idempotency protection
        
        Args:
            user_id: User ID
            package_id: Credit package ID
            amount: Amount in smallest unit (paise/cents)
            currency: Currency code (INR/USD)
            coins: Coins to be credited on payment
            provider: Payment provider (razorpay/stripe)
            idempotency_key: Unique key to prevent duplicate orders
        
        Returns:
            PaymentOrder instance
        
        Raises:
            ExternalServiceException: Payment gateway errors
            DatabaseException: Database operation failures
        """
        logger.info(
            "Creating payment order",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "package_id": package_id,
                    "amount": amount,
                    "currency": currency,
                    "coins": coins,
                    "provider": provider.value
                }
            }
        )
        
        try:
            # Check for duplicate order (idempotency)
            if idempotency_key:
                result = await self.db.execute(
                    select(PaymentOrder).where(
                        PaymentOrder.idempotency_key == idempotency_key
                    )
                )
                existing_order = result.scalar_one_or_none()
                
                if existing_order:
                    logger.info(
                        "Returning existing order (idempotent)",
                        extra={
                            "user_id": user_id,
                            "extra_data": {
                                "order_id": str(existing_order.id),
                                "idempotency_key": idempotency_key
                            }
                        }
                    )
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
            
            log_business_event(
                "payment_order_created",
                user_id=user_id,
                order_id=str(payment_order.id),
                provider=provider.value,
                amount=amount,
                currency=currency,
                coins=coins
            )
            
            logger.info(
                "Payment order created successfully",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "order_id": str(payment_order.id),
                        "provider_order_id": order_response.provider_order_id
                    }
                }
            )
            
            return payment_order
            
        except Exception as e:
            logger.error(
                f"Failed to create payment order: {str(e)}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "provider": provider.value,
                        "amount": amount,
                        "currency": currency
                    }
                },
                exc_info=True
            )
            
            await self.db.rollback()
            
            raise ExternalServiceException(
                service_name=f"{provider.value} Payment Gateway",
                message=f"Failed to create order: {str(e)}",
                error_code=ErrorCode.PAYMENT_GATEWAY_ERROR
            )
    
    async def process_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes,
        signature: str,
        headers: dict
    ) -> bool:
        """
        Process payment webhook with verification and idempotency
        
        This is THE critical function that credits coins after payment.
        It MUST be idempotent (safe to call multiple times).
        
        Args:
            provider: Payment provider
            payload: Webhook payload
            signature: Webhook signature for verification
            headers: Request headers
        
        Returns:
            True if processed successfully
        
        Raises:
            ExternalServiceException: Verification or processing failures
        """
        logger.info(
            "Processing payment webhook",
            extra={
                "extra_data": {
                    "provider": provider.value,
                    "signature_present": bool(signature)
                }
            }
        )
        
        try:
            # 1. Verify webhook signature
            provider_client = PaymentProviderFactory.create_provider(
                provider,
                self.provider_configs[provider.value]
            )
            
            verification = await provider_client.verify_webhook(
                payload, signature, headers
            )
            
            if not verification.is_valid:
                logger.warning(
                    "Invalid webhook signature",
                    extra={
                        "extra_data": {
                            "provider": provider.value,
                            "signature": signature[:20] + "..."
                        }
                    }
                )
                return False
            
            logger.info(
                "Webhook signature verified",
                extra={
                    "extra_data": {
                        "provider": provider.value,
                        "provider_order_id": verification.provider_order_id,
                        "status": verification.status.value
                    }
                }
            )
            
            # 2. Find payment order
            result = await self.db.execute(
                select(PaymentOrder).where(
                    PaymentOrder.provider_order_id == verification.provider_order_id
                )
            )
            payment_order = result.scalar_one_or_none()
            
            if not payment_order:
                logger.warning(
                    "Payment order not found for webhook",
                    extra={
                        "extra_data": {
                            "provider_order_id": verification.provider_order_id
                        }
                    }
                )
                # This might be a test webhook - return True to acknowledge
                return True
            
            # 3. Track webhook (for audit/debugging)
            payment_order.webhook_count += 1
            payment_order.webhook_received_at = datetime.now(timezone.utc)
            
            # 4. IDEMPOTENCY CHECK - Critical!
            # If already processed, just acknowledge and return
            if payment_order.status == PaymentStatus.COMPLETED:
                logger.info(
                    "Payment already processed (idempotent)",
                    extra={
                        "user_id": payment_order.user_id,
                        "extra_data": {
                            "order_id": str(payment_order.id),
                            "webhook_count": payment_order.webhook_count,
                            "completed_at": payment_order.completed_at.isoformat()
                        }
                    }
                )
                await self.db.commit()
                return True
            
            # 5. Update order status
            old_status = payment_order.status
            payment_order.status = verification.status
            payment_order.provider_payment_id = verification.payment_id
            
            # 6. Process successful payment
            if verification.status == PaymentStatus.COMPLETED:
                await self._process_successful_payment(payment_order, verification)
            elif verification.status == PaymentStatus.FAILED:
                logger.warning(
                    "Payment failed",
                    extra={
                        "user_id": payment_order.user_id,
                        "extra_data": {
                            "order_id": str(payment_order.id),
                            "provider_order_id": payment_order.provider_order_id,
                            "old_status": old_status.value
                        }
                    }
                )
            
            await self.db.commit()
            
            logger.info(
                "Webhook processed successfully",
                extra={
                    "user_id": payment_order.user_id,
                    "extra_data": {
                        "order_id": str(payment_order.id),
                        "status": verification.status.value,
                        "old_status": old_status.value
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to process webhook: {str(e)}",
                extra={
                    "extra_data": {
                        "provider": provider.value
                    }
                },
                exc_info=True
            )
            
            await self.db.rollback()
            
            # Don't raise - we want to return False so gateway retries
            return False
    
    async def _process_successful_payment(
        self,
        payment_order: PaymentOrder,
        verification
    ):
        """
        Process successful payment - credit coins to user
        
        This is wrapped in the same transaction as order update,
        ensuring atomicity.
        """
        payment_order.completed_at = datetime.now(timezone.utc)
        
        logger.info(
            "Processing successful payment",
            extra={
                "user_id": payment_order.user_id,
                "extra_data": {
                    "order_id": str(payment_order.id),
                    "coins": payment_order.coins,
                    "amount": payment_order.amount,
                    "currency": payment_order.currency
                }
            }
        )
        
        try:
            # Credit coins to user (using async method)
            await CreditService.add_transaction_async(
                db=self.db,
                user_id=payment_order.user_id,
                transaction_type=TransactionType.PURCHASE,
                amount=payment_order.coins,
                description=f"Purchased {payment_order.coins} coins",
                payment_id=verification.payment_id,
                package_id=payment_order.package_id,
                transaction_metadata={
                    "payment_order_id": str(payment_order.id),
                    "provider_order_id": payment_order.provider_order_id,
                    "provider_payment_id": verification.payment_id,
                    "amount_paid": payment_order.amount,
                    "currency": payment_order.currency,
                    "provider": payment_order.provider.value
                }
            )
            
            log_business_event(
                "payment_completed",
                user_id=payment_order.user_id,
                order_id=str(payment_order.id),
                coins=payment_order.coins,
                amount=payment_order.amount,
                currency=payment_order.currency,
                provider=payment_order.provider.value,
                payment_id=verification.payment_id
            )
            
            logger.info(
                "Coins credited successfully",
                extra={
                    "user_id": payment_order.user_id,
                    "extra_data": {
                        "coins": payment_order.coins,
                        "order_id": str(payment_order.id)
                    }
                }
            )
            
        except Exception as e:
            logger.critical(
                f"CRITICAL: Failed to credit coins after successful payment: {str(e)}",
                extra={
                    "user_id": payment_order.user_id,
                    "extra_data": {
                        "order_id": str(payment_order.id),
                        "coins": payment_order.coins,
                        "payment_id": verification.payment_id
                    }
                },
                exc_info=True
            )
            
            # This is critical - payment succeeded but credit failed
            # Manual intervention required - alert monitoring
            raise DatabaseException(
                message=f"Payment succeeded but failed to credit coins. Order ID: {payment_order.id}",
                original_error=e
            )
    
    async def create_refund(
        self,
        payment_order_id: str,
        amount: int,
        reason: str,
        coins_to_deduct: int
    ) -> PaymentRefund:
        """
        Create a refund for failed insight generation
        
        Args:
            payment_order_id: Original payment order ID
            amount: Amount to refund (in smallest unit)
            reason: Refund reason
            coins_to_deduct: Coins to deduct from user
        
        Returns:
            PaymentRefund instance
        
        Raises:
            AppException: Various failure scenarios
        """
        logger.info(
            "Creating refund",
            extra={
                "extra_data": {
                    "payment_order_id": payment_order_id,
                    "amount": amount,
                    "coins": coins_to_deduct,
                    "reason": reason
                }
            }
        )
        
        try:
            # Get payment order
            result = await self.db.execute(
                select(PaymentOrder).where(PaymentOrder.id == payment_order_id)
            )
            payment_order = result.scalar_one_or_none()
            
            if not payment_order:
                raise AppException(
                    message="Payment order not found",
                    error_code=ErrorCode.NOT_FOUND,
                    status_code=404
                )
            
            if not payment_order.provider_payment_id:
                raise AppException(
                    message="No payment ID to refund",
                    error_code=ErrorCode.REFUND_FAILED,
                    status_code=400
                )
            
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
                processed_at=datetime.now(timezone.utc),
                metadata=refund_response.metadata
            )
            
            self.db.add(payment_refund)
            
            # Deduct coins from user (negative transaction)
            await CreditService.add_transaction_async(
                db=self.db,
                user_id=payment_order.user_id,
                transaction_type=TransactionType.REFUND,
                amount=-coins_to_deduct,  # Negative to deduct
                description=f"Refund: {reason}",
                transaction_metadata={
                    "payment_order_id": str(payment_order_id),
                    "refund_id": str(payment_refund.id),
                    "provider_refund_id": refund_response.provider_refund_id
                }
            )
            
            await self.db.commit()
            await self.db.refresh(payment_refund)
            
            log_business_event(
                "payment_refunded",
                user_id=payment_order.user_id,
                order_id=str(payment_order_id),
                refund_id=str(payment_refund.id),
                coins=coins_to_deduct,
                amount=amount,
                reason=reason
            )
            
            logger.info(
                "Refund created successfully",
                extra={
                    "user_id": payment_order.user_id,
                    "extra_data": {
                        "refund_id": str(payment_refund.id),
                        "provider_refund_id": refund_response.provider_refund_id,
                        "coins_deducted": coins_to_deduct
                    }
                }
            )
            
            return payment_refund
            
        except AppException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            
            logger.error(
                f"Failed to create refund: {str(e)}",
                extra={
                    "extra_data": {
                        "payment_order_id": payment_order_id
                    }
                },
                exc_info=True
            )
            
            raise ExternalServiceException(
                service_name="Payment Gateway",
                message=f"Refund failed: {str(e)}",
                error_code=ErrorCode.REFUND_FAILED
            )
    
    async def get_order_status(self, order_id: str) -> Optional[PaymentOrder]:
        """Get payment order by ID"""
        result = await self.db.execute(
            select(PaymentOrder).where(PaymentOrder.id == order_id)
        )
        return result.scalar_one_or_none()