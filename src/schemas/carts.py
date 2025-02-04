from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel, EmailStr

from schemas.orders import OrderResponseSchema


class CartItemBaseSchema(BaseModel):
    movie_id: int

class CartItemCreateSchema(CartItemBaseSchema):
    added_at: date

class CartItemResponseSchema(CartItemBaseSchema):
    name: str
    added_at: date

    model_config = {"arbitrary_types_allowed": True}

class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: list[OrderResponseSchema]
    price: Decimal

    model_config = {"from_attributes": True}


class CartItemDetailResponseSchema(CartItemBaseSchema):
    id: int
    name: str
    year: int
    price: Decimal
    genres: List[str]

    model_config = {"from_attributes": True}
