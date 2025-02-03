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
from database import get_db
from schemas.orders import OrderResponseSchema, OrderListResponseSchema, OrderCreateSchema, OrderItemResponseSchema
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from exceptions import BaseSecurityError

router = APIRouter()


@router.post("/", response_model=OrderResponseSchema)
def create_order(
    order_data: OrderCreateSchema,
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        payload_user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    if order_data.user_id != payload_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="You do not have permission to perform this operation."
        )

    user = db.query(UserModel).filter(UserModel.id == order_data.user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found.")

    orders = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.user_id == user.id).all()

    valid_items = []
    movies_ids = set()

    for order in orders:
        for item in order.order_items:
            movies_ids.add(item.movie_id)

    total_price = Decimal(0)

    for order_item in order_data.items:
        movie = db.query(MovieModel).filter(MovieModel.id == order_item.movie_id).first()

        if not movie:
            pass
            # ToDO send email movie unavailable

        if movie.id in movies_ids:
            pass
            # ToDo send email can't buy same movie more than one time

        else:
            item = OrderItemModel(movie_id=order_item.movie_id, price_at_order=Decimal(movie.price))
            valid_items.append(item)
            total_price += Decimal(movie.price)
            movies_ids.add(order_item.movie_id)

    if not valid_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid movies found")

    new_order = OrderModel(
        user_id=user.id,
        total_amount=total_price,
        status=OrderStatusEnum.PENDING,
    )

    db.add(new_order)
    db.flush()

    for order_item in valid_items:
        order_item.order_id = new_order.id
        db.add(order_item)

    db.commit()
    db.refresh(new_order)
    items = db.query(OrderItemModel).filter_by(order_id=new_order.id).all()

    return OrderResponseSchema(
        id=new_order.id,
        user_id=new_order.user_id,
        created_at=new_order.created_at,
        status=new_order.status,
        total_amount=new_order.total_amount,
        order_items=items,
    )


@router.get("/", response_model=OrderListResponseSchema)
def get_orders(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found.")

    orders = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.user_id == user.id).all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orders not found.")

    # items = db.query(OrderItemModel).filter_by(order_id=new_order.id).all()

    return OrderListResponseSchema(
        orders=orders,
    )


@router.get("/all/", response_model=OrderListResponseSchema)
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user = db.query(UserModel).join(UserGroupModel).filter(UserModel.id == token_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or not active.")

    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    query = db.query(OrderModel).join(OrderItemModel)

    if user_id:
        query = query.filter(OrderModel.user_id == user_id)

    if start_date:
        query = query.filter(OrderModel.created_at >= start_date)

    if end_date:
        query = query.filter(OrderModel.created_at <= end_date)

    if status_filter:
        query = query.filter(OrderModel.status == status_filter)

    orders = query.all()

    return OrderListResponseSchema(
        orders=orders,
    )


@router.get("/{order_id}/", response_model=OrderResponseSchema)
def get_order(
    order_id: int,
    token: str = Depends(get_token),
    jwt_manager=Depends(get_jwt_auth_manager),
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

    order = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.user_id != user.id and user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    return order


@router.post(
    "/{order_id}/to-cart",
)
def order_to_cart(
    order_id: int,
    token: str = Depends(get_token),
    jwt_manager=Depends(get_jwt_auth_manager),
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

    order = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.user_id != user.id and user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    cart = db.query(CartModel).join(CartItemModel).filter(CartModel.user_id == user.id).first()

    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")

    total_amount = Decimal("0")

    purchased_movies = [item.movie_id for item in cart.cart_items]
    for order_item in order.order_items:
        movie = db.query(MovieModel).filter(MovieModel.id == order_item.movie_id).first()

        if not movie or order_item.movie_id in purchased_movies:
            db.delete(order_item)
            # ToDo send email about not valid movie

        else:
            cart_item = CartItemModel(
                cart_id=cart.id,
                movie_id=order_item.movie_id,
            )
            db.add(cart_item)
            total_amount += order_item.price

    order.total_amount = total_amount

    db.commit()

    return {"detail": "Orders added to cart"}
