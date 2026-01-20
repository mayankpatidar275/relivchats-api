# src/payments/models.py
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from ..database import Base
from .base import PaymentProvider, PaymentStatus

class PaymentOrder(Base):
    """Payment orders table - tracks all payment attempts"""
    __tablename__ = "payment_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    package_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Provider details
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    provider_order_id = Column(String, unique=True, index=True)
    provider_payment_id = Column(String, index=True)
    
    # Amount details
    amount = Column(Integer, nullable=False)  # In smallest unit (paise/cents)
    currency = Column(String(3), nullable=False)
    coins = Column(Integer, nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    
    # Idempotency
    idempotency_key = Column(String, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))

    # Metadata
    payment_order_metadata = Column(JSON)

    # Webhook tracking
    webhook_received_at = Column(DateTime(timezone=True))
    webhook_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<PaymentOrder {self.id} - {self.status}>"

class PaymentRefund(Base):
    """Payment refunds table"""
    __tablename__ = "payment_refunds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Provider details
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    provider_refund_id = Column(String, unique=True, index=True)
    provider_payment_id = Column(String)
    
    # Amount details
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    coins_refunded = Column(Integer, nullable=False)
    
    # Refund details
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True))
    
    # Metadata
    payment_refund_metadata = Column(JSON)
    
    def __repr__(self):
        return f"<PaymentRefund {self.id} - {self.amount}>"