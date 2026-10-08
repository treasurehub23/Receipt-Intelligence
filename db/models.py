from sqlalchemy import Column, Integer, String, DateTime, Float, Numeric, func
from sqlalchemy.orm import mapped_column, Mapped
from typing import Optional
from db.database import Base
import json
JSON = String  # Use String to store JSON data as tex

class Expense (Base):
    __tablename__ = "expenses"
    id:Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    merchant:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchase_date:Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    total:Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    currency:Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    category:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    merchant_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    purchase_date_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    line_items:Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_text:Mapped[Optional[str]] = mapped_column(String, nullable=True)

    image_hash:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at:Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)