from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant: str | None = None
    purchase_date: datetime | None = None
    total: Decimal | None = None
    currency: str | None = None
    category: str | None = None
    category_confidence: float | None = None
    original_predicted_category: str | None = None
    line_items: list | None = None
    created_at: datetime

class ExpenseListResponse(BaseModel):
    items: list[ExpenseOut]
    total: int 
    page: int
    page_size: int
    total_pages: int | None

class CategoryBreakdown(BaseModel):
    category: str 
    total: Decimal
    count: int

class MonthBreakdown(BaseModel):
    year: int
    month: int
    total: Decimal
    count: int

class AnalyticsSummary(BaseModel):
    total_spend: Decimal | None
    expense_count: int
    by_category: list[CategoryBreakdown]
    by_month: list[MonthBreakdown]


class ExpenseCategoryUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=255)

class RegisterUserRequest(BaseModel):
    email: EmailStr = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)

class RegisterUserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

