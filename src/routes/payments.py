import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatus
from database.session_sqlite import get_sqlite_db as get_db
from schemas.payments import PaymentCreate


stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

router = APIRouter()

@router.post("/create-payment/")
async def create_payment(payment: PaymentCreate,
                         db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    amount = sum(item.price_at_payment for item in order.order_items)

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            metadata={"order_id": payment.order.id}
        )

        new = PaymentModel(
            user_id=order.user_id,
            order_id=order.id,
            amount=amount,
            external_payment_id=intent.id,
            status=PaymentStatus.SUCCESSFUL,
        )
        db.add(new)
        db.commit()
        db.refresh(new)

        return {"client_secret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stripe-webhook/")
async def stripe_webhook(request: Request,
                         db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ["STRIPE_ENDPOINT_SECRET"]
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent["metadata"]["order_id"]

        payment = db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()

        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            db.commit()

    return {"status": "success"}


@router.get("/")
async def get_payments(user_id: int,
                       db: Session = Depends(get_db)):
    payments = db.query(PaymentModel).filter(PaymentModel.user_id == user_id).all()
    return payments
