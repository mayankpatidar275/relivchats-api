# src/payments/providers/stripe_provider.py
import stripe
from typing import Dict, Any, Optional
from ..base import (
    BasePaymentProvider,
    PaymentOrderResponse,
    PaymentVerificationResult,
    RefundResponse,
    PaymentStatus
)

class StripeProvider(BasePaymentProvider):
    """Stripe payment provider implementation"""
    
    def _initialize_client(self):
        stripe.api_key = self.config["secret_key"]
        self.webhook_secret = self.config["webhook_secret"]
    
    async def create_order(
        self,
        amount: int,
        currency: str,
        user_id: str,
        package_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentOrderResponse:
        """
        Create Stripe PaymentIntent
        
        Stripe expects amount in cents (100 cents = 1 USD)
        """
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,  # Already in cents
                currency=currency.lower(),  # Stripe requires lowercase
                metadata={
                    "user_id": user_id,
                    "package_id": package_id,
                    **(metadata or {})
                },
                automatic_payment_methods={"enabled": True}
            )
            
            return PaymentOrderResponse(
                order_id=payment_intent.id,
                provider_order_id=payment_intent.id,
                amount=amount,
                currency=currency,
                client_secret=payment_intent.client_secret,
                metadata={
                    "user_id": user_id,
                    "package_id": package_id
                }
            )
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe order creation failed: {str(e)}")
    
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> PaymentVerificationResult:
        """
        Verify Stripe webhook signature
        
        Stripe uses stripe.Webhook.construct_event for verification
        """
        try:
            # Verify and construct event
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            event_type = event["type"]
            
            # Handle different event types
            if event_type == "payment_intent.succeeded":
                payment_intent = event["data"]["object"]
                
                return PaymentVerificationResult(
                    is_valid=True,
                    order_id=payment_intent["id"],
                    provider_order_id=payment_intent["id"],
                    payment_id=payment_intent["id"],
                    amount=payment_intent["amount"],
                    currency=payment_intent["currency"].upper(),
                    status=PaymentStatus.COMPLETED,
                    metadata={
                        "event_type": event_type,
                        "user_id": payment_intent["metadata"].get("user_id"),
                        "package_id": payment_intent["metadata"].get("package_id"),
                        "payment_method": payment_intent.get("payment_method")
                    }
                )
            
            elif event_type == "payment_intent.payment_failed":
                payment_intent = event["data"]["object"]
                
                return PaymentVerificationResult(
                    is_valid=True,
                    order_id=payment_intent["id"],
                    provider_order_id=payment_intent["id"],
                    payment_id=payment_intent["id"],
                    amount=payment_intent["amount"],
                    currency=payment_intent["currency"].upper(),
                    status=PaymentStatus.FAILED,
                    metadata={
                        "event_type": event_type,
                        "error_message": payment_intent.get("last_payment_error", {}).get("message")
                    }
                )
            
            elif event_type == "charge.refunded":
                charge = event["data"]["object"]
                
                return PaymentVerificationResult(
                    is_valid=True,
                    order_id=charge["payment_intent"],
                    provider_order_id=charge["payment_intent"],
                    payment_id=charge["id"],
                    amount=charge["amount_refunded"],
                    currency=charge["currency"].upper(),
                    status=PaymentStatus.REFUNDED,
                    metadata={
                        "event_type": event_type,
                        "refund_reason": charge.get("refund_reason")
                    }
                )
            
            # Other events
            return PaymentVerificationResult(
                is_valid=True,
                order_id="",
                provider_order_id="",
                payment_id="",
                amount=0,
                currency="",
                status=PaymentStatus.PENDING,
                metadata={"event_type": event_type, "unhandled": True}
            )
            
        except stripe.error.SignatureVerificationError as e:
            return PaymentVerificationResult(
                is_valid=False,
                order_id="",
                provider_order_id="",
                payment_id="",
                amount=0,
                currency="",
                status=PaymentStatus.FAILED,
                metadata={},
                error_message=f"Invalid signature: {str(e)}"
            )
        except Exception as e:
            return PaymentVerificationResult(
                is_valid=False,
                order_id="",
                provider_order_id="",
                payment_id="",
                amount=0,
                currency="",
                status=PaymentStatus.FAILED,
                metadata={},
                error_message=f"Webhook verification failed: {str(e)}"
            )
    
    async def create_refund(
        self,
        payment_id: str,
        amount: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RefundResponse:
        """Create Stripe refund"""
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_id,
                amount=amount,  # In cents
                reason=reason,
                metadata=metadata or {}
            )
            
            return RefundResponse(
                refund_id=refund.id,
                provider_refund_id=refund.id,
                amount=refund.amount,
                status=refund.status,
                metadata={
                    "payment_intent": payment_id,
                    "reason": refund.reason,
                    "created": refund.created
                }
            )
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe refund failed: {str(e)}")
    
    async def get_payment_status(
        self,
        provider_payment_id: str
    ) -> PaymentStatus:
        """Get Stripe payment status"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(provider_payment_id)
            
            status_map = {
                "succeeded": PaymentStatus.COMPLETED,
                "processing": PaymentStatus.PROCESSING,
                "requires_payment_method": PaymentStatus.PENDING,
                "requires_confirmation": PaymentStatus.PENDING,
                "requires_action": PaymentStatus.PENDING,
                "canceled": PaymentStatus.FAILED
            }
            
            return status_map.get(payment_intent.status, PaymentStatus.PENDING)
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to fetch payment status: {str(e)}")