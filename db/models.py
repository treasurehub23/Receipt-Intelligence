from sqlalchemy import  Integer, String, DateTime, Float, Numeric, func
from sqlalchemy.orm import mapped_column, Mapped
from typing import Optional
from db.database import Base
import json
from datetime import datetime
JSON = String  # Use String to store JSON data as tex

class Expense (Base):
    __tablename__ = "expenses"
    id:Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    merchant:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchase_date:Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total:Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    currency:Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    category:Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    original_predicted_category: Mapped[Optional[str]] = mapped_column(
    String(255),
    nullable=True,
)
    
    category_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    merchant_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    purchase_date_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_confidence:Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    line_items:Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_text:Mapped[Optional[str]] = mapped_column(String, nullable=True)

    image_hash:Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    created_at:Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

class User(Base):
    __tablename__ = "users"
    id:Mapped[int] = mapped_column(Integer, unique=True, primary_key=True, autoincrement=True)
    email:Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password:Mapped[str] = mapped_column(String(255), nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)