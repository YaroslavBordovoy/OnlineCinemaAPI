from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

from database.models.orders import OrderStatusEnum

class OrderItemSchema(BaseModel):
    id: int
    movie_id: int
    price_at_order: Decimal

class OrderItemResponseSchema(OrderItemSchema):
    order_id: int


class OrderBaseSchema(BaseModel):
    user_id: int
    status: OrderStatusEnum = OrderStatusEnum.PENDING
    items: list[OrderItemResponseSchema]


class OrderCreateSchema(OrderBaseSchema):
    pass


class OrderResponseSchema(OrderBaseSchema):
    id: int
    created_at: datetime
    order_items: list[OrderItemResponseSchema]
    total_amount: Optional[Decimal] = None

class OrderListResponseSchema(BaseModel):
    orders: list[OrderResponseSchema]
