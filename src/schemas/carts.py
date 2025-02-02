from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel, EmailStr


class CartItemBaseSchema(BaseModel):
    movie_id: int
    cart_id: int


class CartItemCreateSchema(CartItemBaseSchema):
    added_at: date


class CartItemResponseSchema(CartItemBaseSchema):
    name: str
    added_at: date

    class Config:
        arbitrary_types_allowed = True


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    cart_items: List[CartItemResponseSchema]
    price: Decimal

    model_config = {"from_attributes": True}
