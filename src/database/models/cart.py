import datetime

from sqlalchemy import DATETIME, UniqueConstraint, func, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class CartModel(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="cart",
        uselist=False
    )
    cart_items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User: {self.user}>"

class CartItemModel(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id"), nullable=False)
    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="cart_items")
    added_at: Mapped[datetime] = mapped_column(DATETIME, nullable=False, default=func.current_date())

    __table_args__ = (
        UniqueConstraint("cart_id", "movie_id", name="unique_cart_movie"),
    )

    def __repr__(self) -> str:
        return f"<Cart: {self.cart_id}>, Movie: {self.movie}, Added: {self.added_at}>"