from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.dependencies import get_jwt_auth_manager
from database.models.accounts import UserModel
from database.models.cart import CartModel, CartItemModel
from database.models.movies import MovieModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from database.session_sqlite import get_sqlite_db as get_db
from schemas.orders import (
    OrderResponseSchema, OrderListResponseSchema, OrderCreateSchema
)
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from exceptions import TokenExpiredError, InvalidTokenError

router = APIRouter()


@router.post(
    "/orders",
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
    except (TokenExpiredError, InvalidTokenError) as e:
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

    movies = (
        db
        .query(MovieModel)
        .filter(
            MovieModel.id.in_(item.movie_id for item in order_data.items)
        )
        .all()
    )
    new_order = OrderModel(
        user_id=user.id,
        total_amount=order_data.total_amount,
        status=OrderStatusEnum.PENDING,
    )

    db.add(new_order)
    db.flush()

    for movie in movies:
        order_item = OrderItemModel(
            order_id=new_order.id,
            movie_id=movie.id,
            price_at_order=Decimal(movie.price)
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    return new_order


@router.get(
    "/orders/",
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
    except (TokenExpiredError, InvalidTokenError) as e:
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