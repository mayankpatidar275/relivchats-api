from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Integer, Enum, Numeric, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import uuid
import enum

class TransactionType(enum.Enum):
    SIGNUP_BONUS = "signup_bonus"
    PURCHASE = "purchase"
    INSIGHT_UNLOCK = "insight_unlock"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction details
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive for credit, negative for debit
    balance_after = Column(Integer, nullable=False)  # Balance snapshot after transaction
    
    # Related entities (for traceability)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    payment_id = Column(String, nullable=True, index=True)  # Stripe payment intent ID
    package_id = Column(UUID(as_uuid=True), ForeignKey("credit_packages.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata
    description = Column(String, nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False)
    transaction_metadata = Column(JSON, nullable=True)  # Store additional context
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="credit_transactions")
    package = relationship("CreditPackage")


class CreditPackage(Base):
    __tablename__ = "credit_packages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Package details
    name = Column(String, nullable=False)  # "Starter", "Popular", "Pro"
    coins = Column(Integer, nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)  # Store as decimal for precision
    
    # Display metadata
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_popular = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Stripe integration
    stripe_price_id = Column(String, nullable=True)  # Stripe Price ID for this package
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())