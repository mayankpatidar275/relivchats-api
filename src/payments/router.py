# src/payments/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..auth.dependencies import get_current_user_id
from .service import PaymentService
from .schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderStatusResponse
)
from .base import PaymentProvider
from ..config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    """Dependency for PaymentService"""
    provider_configs = {
        "razorpay": {
            "key_id": settings.RAZORPAY_KEY_ID,
            "key_secret": settings.RAZORPAY_KEY_SECRET,
            "webhook_secret": settings.RAZORPAY_WEBHOOK_SECRET
        },
        "stripe": {
            "secret_key": settings.STRIPE_SECRET_KEY,
            "webhook_secret": settings.STRIPE_WEBHOOK_SECRET
        }
    }
    return PaymentService(db, provider_configs)

@router.post("/orders", response_model=CreateOrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    user_id: str = Depends(get_current_user_id),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Create a payment order
    
    Creates an order with the specified payment provider and returns
    the necessary details for the frontend to complete the payment.
    """
    try:
        # Get package details (you'll need to fetch from credit_packages table)
        from ..credits.service import CreditService
        credit_service = CreditService(payment_service.db)
        package = await credit_service.get_package(request.package_id)
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Determine amount based on currency and provider
        if request.provider == PaymentProvider.RAZORPAY:
            # Razorpay: INR in paise
            amount = int(package.price_inr * 100)
            currency = "INR"
        else:
            # Stripe: USD in cents
            amount = int(package.price_usd * 100)
            currency = "USD"
        
        order = await payment_service.create_order(
            user_id=user_id,
            package_id=str(package.id),
            amount=amount,
            currency=currency,
            coins=package.coins,
            provider=request.provider,
            idempotency_key=request.idempotency_key
        )
        
        return CreateOrderResponse(
            order_id=str(order.id),
            provider_order_id=order.provider_order_id,
            amount=order.amount,
            currency=order.currency,
            coins=order.coins,
            provider=order.provider,
            client_secret=order.metadata.get("client_secret"),
            checkout_url=order.metadata.get("checkout_url")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Handle Razorpay webhook"""
    try:
        payload = await request.body()
        headers = dict(request.headers)
        
        success = await payment_service.process_webhook(
            provider=PaymentProvider.RAZORPAY,
            payload=payload,
            signature=x_razorpay_signature,
            headers=headers
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        return {"status": "ok"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Handle Stripe webhook"""
    try:
        payload = await request.body()
        headers = dict(request.headers)
        
        success = await payment_service.process_webhook(
            provider=PaymentProvider.STRIPE,
            payload=payload,
            signature=stripe_signature,
            headers=headers
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        return {"status": "ok"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    user_id: str = Depends(get_current_user_id),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Get payment order status"""
    order = await payment_service.get_order_status(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return OrderStatusResponse(
        order_id=str(order.id),
        status=order.status,
        provider=order.provider,
        amount=order.amount,
        currency=order.currency,
        coins=order.coins,
        created_at=order.created_at,
        completed_at=order.completed_at
    )