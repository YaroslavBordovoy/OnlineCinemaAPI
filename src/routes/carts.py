import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from database.models.accounts import UserModel, UserGroupModel
from database.models.cart import CartModel
from database.models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from database.models.payments import PaymentModel, PaymentStatus
from exceptions import BaseSecurityError
from schemas.carts import (
    CartResponseSchema,
)
from config import get_jwt_auth_manager

from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface


router = APIRouter()

@router.get(
    "/",
    response_model=CartResponseSchema,
)
def get_cart(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user = db.query(UserModel).join(UserGroupModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found.")

    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()
    cart_items = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.cart_id == cart.id).all()

    return CartResponseSchema(
        id=cart.id,
        user_id=user.id,
        cart_items=cart_items,
        price=sum(item.total_amount for item in cart_items),
    )

@router.post(
    "/pay-all/",
)
def pay_cart(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user = db.query(UserModel).join(UserGroupModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found.")

    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()
    cart_items = (
        db
        .query(OrderModel)
        .filter(OrderModel.cart_id == cart.id)
        .filter(OrderModel.status == OrderStatusEnum.PENDING)
        .all()
    )


    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No order in cart or all paid"
        )

    total_amount = sum(item.total_amount for item in cart_items)

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount), currency="usd", metadata={"cart_id": cart.id}
        )
        for order in cart_items:
            new = PaymentModel(
                user_id=order.user_id,
                order_id=order.id,
                amount=order.total_amount,
                external_payment_id=intent.id,
                status=PaymentStatus.SUCCESSFUL,
            )
            db.add(new)
        db.commit()

        return {"client_secret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
