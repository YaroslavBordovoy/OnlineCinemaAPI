from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.dependencies import get_jwt_auth_manager
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.models.cart import CartModel, CartItemModel
from database.models.movies import MovieModel
from database.models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from database.session_sqlite import get_sqlite_db as get_db
from schemas.orders import (
    OrderResponseSchema, OrderListResponseSchema
)
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from exceptions import TokenExpiredError, InvalidTokenError

router = APIRouter()

def get_cart_for_user(db: Session, user_id: int) -> CartModel:
    return db.query(CartModel).join(CartItemModel).join(MovieModel).filter_by(user_id=user_id).first()



@router.get(
    "/orders/",
    response_model=OrderListResponseSchema
)
def get_orders(
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")
    except (TokenExpiredError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(UserModel).filter_by(id=token_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )
    orders = db.query(OrderModel).join(OrderItemModel).filter_by(user_id=token_user_id).all()
    return orders


@router.post(
    "/orders/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED
)
def place_order(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")
    except (TokenExpiredError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(UserModel).filter_by(id=token_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )

    cart = get_cart_for_user(db, user.id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty."
        )

    movies = [cart_item.movie for cart_item in cart.cart_items]

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available movies in your cart."
        )

    purchased_movie_ids = [
        order_item.movie_id
        for order_item in db.query(OrderItemModel)
        .join(OrderModel)
        .filter(OrderModel.user_id == user.id, OrderModel.status == OrderStatusEnum.PAID)
        .all()
    ]
    movies_to_order = [movie for movie in movies if movie.id not in purchased_movie_ids]

    if not movies_to_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All movies in your cart have already been purchased."
        )

    pending_movie_ids = [
        order_item.movie_id
        for order_item in db.query(OrderItemModel)
        .join(OrderModel)
        .filter(OrderModel.user_id == user.id, OrderModel.status == OrderStatusEnum.PENDING)
        .all()
    ]
    for movie in movies_to_order:
        if movie.id in pending_movie_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The movie '{movie.name}' already has a pending order."
            )

    total_amount = sum(movie.price for movie in movies_to_order)
    decimal_total_amount = Decimal(total_amount)

    new_order = OrderModel(
        user_id=user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=decimal_total_amount,
    )
    db.add(new_order)
    db.flush()

    for movie in movies_to_order:
        order_item = OrderItemModel(
            order_id=new_order.id,
            movie_id=movie.id,
            price_at_order=Decimal(movie.price)
        )
        db.add(order_item)

    for cart_item in cart.cart_items:
        db.delete(cart_item)

    db.commit()
    db.refresh(new_order)

    return new_order


@router.get(
    "/order/all",
    response_model=OrderListResponseSchema
)
def get_all_orders(
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[OrderStatusEnum] = None,
):
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")
    except (TokenExpiredError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(UserModel).join(UserGroupModel).filter_by(id=token_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )

    if user.group != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )

    query = db.query(OrderModel)

    if user_id:
        query = query.filter(OrderModel.user_id == user_id)

    if start_date:
        query = query.filter(OrderModel.created_at >= start_date)

    if end_date:
        query = query.filter(OrderModel.created_at <= end_date)

    if status_filter:
        query = query.filter(OrderModel.status == status_filter)

    orders = query.join(OrderItemModel).all()

    return orders
