from sqlalchemy import Column, Integer, String, DateTime, Float, func
from sqlachemy.orm import mapped_column, Mapped
from typing import Optional
from database import Base

class Expense (Base):
    __tablname__ = "expenses"
    id:Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    merchant:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchase_date:Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    total:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency:Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    category:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    merchant_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    purchase_date_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at:Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)