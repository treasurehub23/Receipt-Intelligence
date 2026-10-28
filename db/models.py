
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import UniqueConstraint
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Float,
    Numeric,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="user",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    expenses: Mapped[list["ExpenseItem"]] = relationship(
        back_populates="user",
        cascade="save-update, merge",
    )


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
    UniqueConstraint(
        "user_id",
        "image_hash",
        name="uq_receipt_user_image_hash",
    ),
)
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    merchant: Mapped[Optional[str]] = mapped_column(String(255))
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    currency: Mapped[Optional[str]] = mapped_column(String(10))

    image_hash: Mapped[Optional[str]] = mapped_column(String(255))
    raw_text: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="receipts")
    items: Mapped[list["ExpenseItem"]] = relationship(
        back_populates="receipt",
        passive_deletes=True,
    )
    status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="completed",
    server_default="completed",
)

class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    receipt_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("receipts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    currency: Mapped[str] = mapped_column(
        String(10), default="NGN", nullable=False
    )

    category: Mapped[Optional[str]] = mapped_column(String(255))
    original_predicted_category: Mapped[Optional[str]] = mapped_column(
        String(255)
    )
    category_confidence: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="expenses")
    receipt: Mapped[Optional["Receipt"]] = relationship(
        back_populates="items"
    )
