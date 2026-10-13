from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ExpenseOut(BaseModel):
    model_congig = ConfigDict(from_attributes=True)

    id:int
    merchant:Optional[str]
    purchase_date:Optional[datetime]
    total:Optional[Decimal]
    currency:Optional[str]
    category:Optional[str]
    line_items:Optional[list]
    created_at:datetime

class ExpenseListResponse(BaseModel):
    items: list[ExpenseOut]
    total: int | None
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
    total_spend: Decimal
    expense_count: int
    by_category: list[CategoryBreakdown]
    by_month: list[MonthBreakdown]
 