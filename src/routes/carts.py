from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from database.models.accounts import UserModel, UserGroupModel
from database.models.cart import CartModel, CartItemModel
from database.models.payments import PaymentStatus, PaymentModel
from exceptions import BaseSecurityError
from schemas.carts import (
    CartItemResponseSchema,
    CartResponseSchema,
    CartItemDetailResponseSchema,
)
from config import get_jwt_auth_manager

from database.models.movies import MovieModel
from database.models.orders import OrderItemModel, OrderModel, OrderStatusEnum
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager

router = APIRouter()


@router.delete(
    "/delete/{cart_item_id}/",
    summary="Remove movie from cart",
    description="<h3>Remove a specific movie from the user's shopping cart</h3>",
    responses={
        404: {"description": "Movie not found in cart."},
        400: {"description": "Movie already purchased."},
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
        db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id, CartItemModel.id == cart_item_id).first()
    )

    if not existing_item:
        raise HTTPException(status_code=404, detail="Movie not found in cart")

    purchased_item = db.query(OrderItemModel).filter(OrderItemModel.movie_id == existing_item.movie_id).first()

    if purchased_item:
        raise HTTPException(status_code=400, detail="Movie already purchased.")

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

    cart_items = cart.cart_items

    if not cart_items:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    try:
        for item in cart_items:
            db.delete(item)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart"
        )

    return {"detail": "All items removed from cart"}


@router.get(
    "/{cart_id}/",
    response_model=CartResponseSchema,
    summary="Get cart item",
    description="<h3>Fetch detailed information about a specific cart by its unique ID. "
                "This endpoint retrieves all available details for the cart, such as "
                "its id, user name, list of cart_item_responses and total price. If the cart with the given "
                "ID is not found, a 404 error will be returned.</h3>",
    responses={
        404: {
            "description": "Cart not found.",
            "content": {"application/json": {"example": {"detail": "Cart with the given ID was not found."}}},
        },
        401: {"description": "Unauthorized - User is not authenticated."},
    },
)
def get_cart(
        cart_id: int,
        db: Session = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    cart_items = db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).all()

    cart_item_responses = []
    total_price = Decimal(0)

    for item in cart_items:
        movie = db.query(MovieModel).filter(MovieModel.id == item.movie_id).first()

        if movie:
            cart_item_responses.append(
                CartItemResponseSchema(
                    cart_id=cart.id,
                    name=movie.name,
                    added_at=item.added_at,
                    movie_id=movie.id,
                )
            )
        total_price += movie.price

    return CartResponseSchema(
        id=cart.id, user_id=user.id, email=user.email, cart_items=cart_item_responses, price=total_price
    )


@router.get(
    "/items/{item_id}/",
    response_model=CartItemDetailResponseSchema,
    summary="Get cart item details",
    description="<h3>Fetch detailed information about a specific cart item. "
                "This endpoint retrieves all available details for the cart, such as "
                "its name, released year, price and list of genres ",
    responses={
        401: {"description": "Unauthorized - User is not authenticated."},
    },
)
def get_item_details(
        item_id: int,
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
    print(cart)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found."
        )

    cart_item = db.query(CartItemModel).filter(CartItemModel.id == item_id, CartItemModel.cart_id == cart.id).first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found."
        )

    movie = db.query(MovieModel).filter(MovieModel.id == cart_item.movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

    return CartItemDetailResponseSchema(
        id=cart_item.id,
        movie_id=movie.id,
        name=movie.name,
        year=movie.year,
        price=movie.price,
        genres=[genre.name for genre in movie.genres]
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access is forbidden."
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None or user.group.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this resource."
        )

    carts = db.query(CartModel).all()
    carts_list = []

    for cart in carts:
        cart_item_responses = []
        total_price = Decimal(0)

        cart_items = db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).all()

        for item in cart_items:
            movie = db.query(MovieModel).filter(MovieModel.id == item.movie_id).first()
            if movie:
                cart_item_responses.append(
                    CartItemResponseSchema(
                        name=movie.name,
                        added_at=item.added_at,
                        movie_id=movie.id,
                    )
                )
                total_price += movie.price

        carts_list.append(
            CartResponseSchema(
                id=cart.id,
                user_id=cart.user_id,
                email=cart.user.email,
                cart_items=cart_item_responses,
                price=total_price,
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
            amount=int(total_amount * 100), currency="usd", metadata={"cart_id": cart.id}
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

