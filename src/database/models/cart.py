import datetime

from sqlalchemy import DATETIME, UniqueConstraint, func, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.accounts import UserModel
from database.models.base import Base
from database.models.movies import MovieModel


class CartModel(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel")
    cart_items: Mapped[list["OrderModel"]] = relationship(
        "OrderModel", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<id: {self.id}, user_id: {self.user_id}, cart_items: {self.cart_items}>"
