# src/payments/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

class PaymentProvider(str, Enum):
    RAZORPAY = "razorpay"
    STRIPE = "stripe"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

@dataclass
class PaymentOrderResponse:
    """Standardized response for order creation"""
    order_id: str  # Internal order ID
    provider_order_id: str  # Provider's order ID
    amount: int  # Amount in smallest currency unit
    currency: str
    client_secret: Optional[str] = None  # For Stripe
    checkout_url: Optional[str] = None  # For hosted checkouts
    metadata: Dict[str, Any] = None

@dataclass
class PaymentVerificationResult:
    """Standardized webhook verification result"""
    is_valid: bool
    order_id: str
    provider_order_id: str
    payment_id: str
    amount: int
    currency: str
    status: PaymentStatus
    metadata: Dict[str, Any]
    error_message: Optional[str] = None

@dataclass
class RefundResponse:
    """Standardized refund response"""
    refund_id: str
    provider_refund_id: str
    amount: int
    status: str
    metadata: Dict[str, Any]

class BasePaymentProvider(ABC):
    """Abstract base class for payment providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize provider-specific client"""
        pass
    
    @abstractmethod
    async def create_order(
        self,
        amount: int,
        currency: str,
        user_id: str,
        package_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentOrderResponse:
        """
        Create a payment order
        
        Args:
            amount: Amount in smallest currency unit (paise for INR, cents for USD)
            currency: Currency code (INR, USD)
            user_id: User identifier
            package_id: Credit package ID
            metadata: Additional metadata
        
        Returns:
            PaymentOrderResponse with provider details
        """
        pass
    
    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> PaymentVerificationResult:
        """
        Verify webhook signature and extract payment details
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature from headers
            headers: All webhook headers
        
        Returns:
            PaymentVerificationResult with parsed details
        """
        pass
    
    @abstractmethod
    async def create_refund(
        self,
        payment_id: str,
        amount: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RefundResponse:
        """
        Create a refund
        
        Args:
            payment_id: Provider payment ID
            amount: Amount to refund (partial or full)
            reason: Refund reason
            metadata: Additional metadata
        
        Returns:
            RefundResponse with refund details
        """
        pass
    
    @abstractmethod
    async def get_payment_status(
        self,
        provider_payment_id: str
    ) -> PaymentStatus:
        """Get current payment status from provider"""
        pass