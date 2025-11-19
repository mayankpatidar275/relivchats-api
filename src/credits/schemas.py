from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# Request Schemas
class UnlockInsightsRequest(BaseModel):
    chat_id: UUID
    category_id: UUID


# Response Schemas
class CreditBalanceResponse(BaseModel):
    user_id: str
    balance: int
    
    class Config:
        from_attributes = True


class CreditPackageResponse(BaseModel):
    id: UUID
    name: str
    coins: int
    price_usd: Decimal
    price_inr: Decimal
    description: Optional[str] = None
    is_popular: bool
    sort_order: int
    
    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: int
    balance_after: int
    description: Optional[str] = None
    status: str
    created_at: datetime
    chat_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    transactions: List[CreditTransactionResponse]
    total_count: int
    current_balance: int


class UnlockInsightsResponse(BaseModel):
    success: bool
    job_id: str
    coins_reserved: int = 0
    remaining_balance: int
    total_insights: int
    estimated_time_seconds: Optional[int] = None
    message: str


class InsufficientCreditsError(BaseModel):
    error: str = "insufficient_credits"
    required: int
    available: int
    deficit: int