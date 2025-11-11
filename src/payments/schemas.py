# src/payments/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .base import PaymentProvider, PaymentStatus

class CreateOrderRequest(BaseModel):
    """Request to create a payment order"""
    package_id: str = Field(..., description="Credit package ID")
    provider: PaymentProvider = Field(..., description="Payment provider")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")

class CreateOrderResponse(BaseModel):
    """Response from creating a payment order"""
    order_id: str
    provider_order_id: str
    amount: int
    currency: str
    coins: int
    provider: PaymentProvider
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None

class OrderStatusResponse(BaseModel):
    """Payment order status"""
    order_id: str
    status: PaymentStatus
    provider: PaymentProvider
    amount: int
    currency: str
    coins: int
    created_at: datetime
    completed_at: Optional[datetime] = None