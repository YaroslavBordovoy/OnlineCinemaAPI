from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.dependencies import get_jwt_auth_manager
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.models.cart import CartModel, CartItemModel
from database.models.movies import MovieModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from database.session_sqlite import get_sqlite_db as get_db
from schemas.orders import (
    OrderResponseSchema, OrderListResponseSchema, OrderCreateSchema
)
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from exceptions import BaseSecurityError

router = APIRouter()


@router.post(
    "/",
    response_model=OrderResponseSchema
)
def create_order(
        order_data: OrderCreateSchema,
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        payload_user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    if order_data.user_id != payload_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to perform this operation."
        )

    user = db.query(UserModel).filter(UserModel.id == order_data.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or user not found.")

    new_order = OrderModel(
        user_id=user.id,
        total_amount=order_data.total_amount,
        status=OrderStatusEnum.PENDING,
    )

    db.add(new_order)
    db.flush()

    for order_item in order_data.items:
        movie = db.query(MovieModel).filter(MovieModel.id == order_item.movie_id).first()
        if not movie:
            pass
            # ToDO check movie
        else:
            item = OrderItemModel(
                order_id=new_order.id,
                movie_id=order_item.movie_id,
                price_at_order=Decimal(movie.price)
            )
            db.add(item)

    db.commit()
    db.refresh(new_order)

    return new_order


@router.get(
    "/",
    response_model=OrderListResponseSchema
)
def get_orders(
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or user not found."
        )

    orders = db.query(OrderModel).filter(OrderModel.user_id == user.id).all()

    return orders

@router.get(
    "/all/",
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
    except BaseSecurityError as e:
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
