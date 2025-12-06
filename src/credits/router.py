# src/credits/router.py
"""
Credits API - Payment and transaction management
Endpoints:
- GET /credits/balance
- GET /credits/transactions
- GET /credits/packages
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user_id
from ..database import get_async_db 
from . import schemas
from .service import CreditService

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=schemas.CreditBalanceResponse)
async def get_credit_balance(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db),  # ← AsyncSession
):
    """Get user's current credit balance (async)"""
    try:
        balance = await CreditService.get_balance_async(db, user_id)
    except Exception as exc:
        # Let your global exception handler deal with NotFoundException etc.
        raise exc

    return schemas.CreditBalanceResponse(
        user_id=user_id,
        balance=balance
    )


@router.get("/transactions", response_model=schemas.TransactionHistoryResponse)
async def get_transaction_history(
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    """Get user's transaction history with pagination (async)"""
    # Note: You don't have an async version of get_transaction_history yet.
    # Since it's a simple SELECT and not performance-critical, we can run it
    # efficiently using async + scalar results.

    from sqlalchemy import desc, select

    from .models import CreditTransaction

    # Total count
    total_result = await db.execute(
        select(CreditTransaction).where(CreditTransaction.user_id == user_id)
    )
    total_count = len(total_result.scalars().all())  # or use scalar(count()) if you add it

    # Paginated transactions
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()

    # Current balance (reuse async method)
    current_balance = await CreditService.get_balance_async(db, user_id)

    return schemas.TransactionHistoryResponse(
        transactions=[
            schemas.CreditTransactionResponse.from_orm(t) for t in transactions
        ],
        total_count=total_count,
        current_balance=current_balance,
    )


@router.get("/packages", response_model=list[schemas.CreditPackageResponse])
async def get_credit_packages(
    db: AsyncSession = Depends(get_async_db),
):
    """Get available credit packages (public endpoint - async)"""
    from .models import CreditPackage

    result = await db.execute(
        select(CreditPackage)
        .where(CreditPackage.is_active.is_(True))
        .order_by(CreditPackage.sort_order)
    )
    packages = result.scalars().all()

    return [schemas.CreditPackageResponse.from_orm(p) for p in packages]