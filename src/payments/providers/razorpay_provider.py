# src/payments/providers/razorpay_provider.py
import razorpay
import hmac
import hashlib
from typing import Dict, Any, Optional
from ..base import (
    BasePaymentProvider,
    PaymentOrderResponse,
    PaymentVerificationResult,
    RefundResponse,
    PaymentStatus
)

class RazorpayProvider(BasePaymentProvider):
    """Razorpay payment provider implementation"""
    
    def _initialize_client(self):
        self.client = razorpay.Client(
            auth=(
                self.config["key_id"],
                self.config["key_secret"]
            )
        )
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
        Create Razorpay order
        
        Razorpay expects amount in paise (100 paise = 1 INR)
        """
        try:
            order_data = {
                "amount": amount,  # Already in paise
                "currency": currency,
                "receipt": f"rcpt_{user_id}_{package_id}",
                "notes": {
                    "user_id": user_id,
                    "package_id": package_id,
                    **(metadata or {})
                }
            }
            
            razorpay_order = self.client.order.create(data=order_data)
            
            return PaymentOrderResponse(
                order_id=razorpay_order["id"],  # Use as internal ID
                provider_order_id=razorpay_order["id"],
                amount=amount,
                currency=currency,
                metadata={
                    "user_id": user_id,
                    "package_id": package_id,
                    "receipt": order_data["receipt"]
                }
            )
            
        except Exception as e:
            raise Exception(f"Razorpay order creation failed: {str(e)}")
    
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> PaymentVerificationResult:
        """
        Verify Razorpay webhook signature
        
        Razorpay signature: HMAC SHA256 of payload with webhook secret
        """
        try:
            # Verify signature
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                return PaymentVerificationResult(
                    is_valid=False,
                    order_id="",
                    provider_order_id="",
                    payment_id="",
                    amount=0,
                    currency="",
                    status=PaymentStatus.FAILED,
                    metadata={},
                    error_message="Invalid signature"
                )
            
            # Parse payload
            import json
            data = json.loads(payload)
            event = data["event"]
            payment_entity = data["payload"]["payment"]["entity"]
            
            # Map Razorpay status to internal status
            status_map = {
                "captured": PaymentStatus.COMPLETED,
                "authorized": PaymentStatus.PROCESSING,
                "failed": PaymentStatus.FAILED,
                "refunded": PaymentStatus.REFUNDED
            }
            
            return PaymentVerificationResult(
                is_valid=True,
                order_id=payment_entity["order_id"],
                provider_order_id=payment_entity["order_id"],
                payment_id=payment_entity["id"],
                amount=payment_entity["amount"],
                currency=payment_entity["currency"],
                status=status_map.get(payment_entity["status"], PaymentStatus.PENDING),
                metadata={
                    "event": event,
                    "method": payment_entity.get("method"),
                    "email": payment_entity.get("email"),
                    "contact": payment_entity.get("contact"),
                    "notes": payment_entity.get("notes", {})
                }
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
        """Create Razorpay refund"""
        try:
            refund_data = {
                "amount": amount,  # In paise
                "notes": {
                    "reason": reason,
                    **(metadata or {})
                }
            }
            
            refund = self.client.payment.refund(payment_id, refund_data)
            
            return RefundResponse(
                refund_id=refund["id"],
                provider_refund_id=refund["id"],
                amount=refund["amount"],
                status=refund["status"],
                metadata={
                    "payment_id": payment_id,
                    "created_at": refund["created_at"]
                }
            )
            
        except Exception as e:
            raise Exception(f"Razorpay refund failed: {str(e)}")
    
    async def get_payment_status(
        self,
        provider_payment_id: str
    ) -> PaymentStatus:
        """Get Razorpay payment status"""
        try:
            payment = self.client.payment.fetch(provider_payment_id)
            
            status_map = {
                "captured": PaymentStatus.COMPLETED,
                "authorized": PaymentStatus.PROCESSING,
                "failed": PaymentStatus.FAILED,
                "refunded": PaymentStatus.REFUNDED
            }
            
            return status_map.get(payment["status"], PaymentStatus.PENDING)
            
        except Exception as e:
            raise Exception(f"Failed to fetch payment status: {str(e)}")