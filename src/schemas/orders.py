from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

from database.models.orders import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    id: int
    order_id: int
    price_at_order: Decimal


class OrderBaseSchema(BaseModel):
    user_id: int
    status: OrderStatusEnum = OrderStatusEnum.PENDING
    total_amount: Optional[Decimal] = None


class OrderResponseSchema(OrderBaseSchema):
    id: int
    created_at: datetime
    order_items: list[OrderItemResponseSchema]
    items: list[OrderItemResponseSchema]

class OrderListResponseSchema(BaseModel):
    orders: list[OrderResponseSchema]
