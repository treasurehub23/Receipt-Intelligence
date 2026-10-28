from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    receipt_id: int | None = None
    description: str | None
    quantity: float | None = None
    unit_price: Decimal | None = None
    total_price: Decimal
    purchase_date: datetime | None = None
    currency: str
    category: str | None = None
    original_predicted_category: str | None = None
    category_confidence: float | None = None
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



class ExpenseUpdate(BaseModel):
    category: str | None = Field(
        default=None, min_length=1, max_length=255
    )
    purchase_date: datetime | None = None
    description: str | None = Field(
        default=None, min_length=1, max_length=500
    )
    unit_price: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    quantity: int | None = Field(
        default=None, gt=0, alias="quantity"
    )

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value):
        if value is None:
            raise ValueError("Category cannot be null.")

        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Category cannot be empty or whitespace.")

        return value
    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value):
        if value is None:
            raise ValueError("Description cannot be null.")

        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Description cannot be empty or whitespace.")

        return value
    
class RegisterUserRequest(BaseModel):
    email: EmailStr = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)

class RegisterUserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

