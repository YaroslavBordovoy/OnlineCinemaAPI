import json
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from database.models.accounts import UserModel, UserGroupModel
from database.models.cart import CartModel, CartItemModel
from database.models.payments import PaymentModel, PaymentStatus
from exceptions import BaseSecurityError
from schemas.carts import (
    CartResponseSchema,
)
from config import get_jwt_auth_manager

from database.models.orders import OrderItemModel, OrderModel, OrderStatusEnum
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager

router = APIRouter()


@router.delete(
    "/delete/{cart_item_id}/",
    summary="Remove order from cart",
    description="<h3>Remove a specific order from the user's shopping cart</h3>",
    responses={
        404: {"description": "Order not found in cart."},
        400: {"description": "Order already purchased."},
        401: {"description": "Unauthorized - User is not authenticated."},
    },
    status_code=status.HTTP_200_OK,
)
def remove_movie_from_cart(
    cart_item_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    cart = db.query(CartModel).filter(CartModel.user_id == user_id).first()

    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    existing_item = (
        db.query(OrderModel)
        .filter(
            OrderModel.cart_id == cart.id,
            OrderModel.id == cart_item_id,
            OrderModel.status == OrderStatusEnum.PENDING,
        )
        .first()
    )

    if not existing_item:
        raise HTTPException(status_code=404, detail="Order not found in cart")

    db.delete(existing_item)
    db.commit()

    return {"detail": "Movie deleted successfully."}


@router.delete(
    "/clear/",
    summary="Clear all items from cart",
    description="<h3>Clear all items from the user's shopping cart</h3>",
    responses={
        404: {"description": "Cart not found."},
        401: {"description": "Unauthorized - User is not authenticated."},
    },
    status_code=status.HTTP_200_OK,
)
def clear_cart(
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    cart = db.query(CartModel).filter(CartModel.user_id == user_id).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_items = (
        db.query(OrderModel)
        .filter(
            OrderModel.cart_id == cart.id,
            OrderModel.status == OrderStatusEnum.PENDING,
        )
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        for item in cart_items:
            db.delete(item)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear cart")

    return {"detail": "All items removed from cart"}


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


@router.get(
    "/admin/detail/",
    summary="Get all carts",
    description="Admins can view the contents of users' carts for analysis or troubleshooting.",
)
def get_all_carts(
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access is forbidden.")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None or user.group.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view this resource."
        )

    carts = db.query(CartModel).all()
    carts_list = []

    for cart in carts:
        cart_items = db.query(OrderModel).filter(OrderModel.cart_id == cart.id).all()

        carts_list.append(
            CartResponseSchema(
                id=cart.id,
                user_id=user.id,
                cart_items=cart_items,
                price=sum(item.total_amount for item in cart_items),
            )
        )

    return carts_list


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
        db.query(OrderModel)
        .filter(OrderModel.cart_id == cart.id)
        .filter(OrderModel.status == OrderStatusEnum.PENDING)
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No order in cart or all paid")

    total_amount = sum(item.total_amount for item in cart_items)

    try:
        order_ids = [order.id for order in cart_items]
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100), currency="usd", metadata={"order_ids": json.dumps(order_ids)}
        )

        for order in cart_items:
            new_payment = PaymentModel(
                user_id=order.user_id,
                order_id=order.id,
                amount=order.total_amount,
                external_payment_id=intent.id,
                status=PaymentStatus.SUCCESSFUL,
            )
            db.add(new_payment)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong."
            )

        return {"client_secret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
