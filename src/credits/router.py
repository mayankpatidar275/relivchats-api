"""
Credits API - Payment and transaction management
Endpoints:
- GET /credits/balance
- GET /credits/transactions
- GET /credits/packages
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Annotated

from ..database import get_db
from ..auth.dependencies import get_current_user_id
from . import schemas
from .service import CreditService

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=schemas.CreditBalanceResponse)
def get_credit_balance(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get user's current credit balance"""
    service = CreditService(db)
    balance = service.get_balance(user_id)
    
    return schemas.CreditBalanceResponse(
        user_id=user_id,
        balance=balance
    )


@router.get("/transactions", response_model=schemas.TransactionHistoryResponse)
def get_transaction_history(
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get user's transaction history with pagination"""
    service = CreditService(db)
    transactions, total = service.get_transaction_history(user_id, limit, offset)
    current_balance = service.get_balance(user_id)
    
    return schemas.TransactionHistoryResponse(
        transactions=[
            schemas.CreditTransactionResponse.from_orm(t) 
            for t in transactions
        ],
        total_count=total,
        current_balance=current_balance
    )


@router.get("/packages", response_model=list[schemas.CreditPackageResponse])
def get_credit_packages(
    db: Session = Depends(get_db)
):
    """Get available credit packages (public endpoint)"""
    service = CreditService(db)
    packages = service.get_packages(active_only=True)
    
    return [schemas.CreditPackageResponse.from_orm(p) for p in packages]