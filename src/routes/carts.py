from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from database.models.accounts import UserModel
from database.models.cart import CartModel, CartItemModel
from schemas.carts import (
    CartItemCreateSchema,
    CartItemResponseSchema,
    CartResponseSchema,
)
from config import get_jwt_auth_manager

from database.models.movies import MovieModel
from database.models.orders import OrderItemModel
from security.http import get_token
from security.jwt_interface import JWTAuthManagerInterface


router = APIRouter()


@router.post(
    "/items/",
    response_model=CartItemResponseSchema,
    summary="Add movie to cart",
    description="<h3>Add a movie to the user's shopping cart.</h3>",
    responses={
        400: {
            "description": "Bad Request - Movie already in cart or movie cannot be added.",
            "content": {"application/json": {"example": {"detail": "Movie already in cart."}}},
        },
        404: {
            "description": "Not Found - Cart not found.",
            "content": {"application/json": {"example": {"detail": "Cart not found."}}},
        },
        401: {
            "description": "Unauthorized - User is not authenticated.",
            "content": {"application/json": {"example": {"detail": "Could not validate credentials."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def add_movie_to_cart(
    cart_item: CartItemCreateSchema,
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
        db.query(CartItemModel)
        .filter(CartItemModel.cart_id == cart.id, CartItemModel.movie_id == cart_item.movie_id)
        .first()
    )
    if existing_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Movie already in cart")

    purchased_item = db.query(OrderItemModel).filter(OrderItemModel.movie_id == cart_item.movie_id).first()

    if purchased_item:
        raise HTTPException(status_code=400, detail="Movie already purchased.")

    new_cart_item = CartItemModel(
        cart_id=cart.id,
        movie_id=cart_item.movie_id,
        added_at=cart_item.added_at,
    )
    db.add(new_cart_item)
    db.commit()

    movie = db.query(MovieModel).filter(MovieModel.id == cart_item.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return CartItemResponseSchema(
        cart_id=new_cart_item.cart_id, movie_id=new_cart_item.movie_id, name=movie.name, added_at=new_cart_item.added_at
    )


@router.delete(
    "/items/{item_id}/",
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

    db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).delete()
    db.commit()

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
    print(cart_item_responses)

    return CartResponseSchema(
        id=cart.id, user_id=user.id, email=user.email, cart_items=cart_item_responses, price=total_price
    )
