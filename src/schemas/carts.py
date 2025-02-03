from decimal import Decimal

from pydantic import BaseModel

from schemas.orders import OrderResponseSchema


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: list[OrderResponseSchema]
    price: Decimal

    model_config = {"from_attributes": True}
