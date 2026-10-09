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
    total: int
    page: int
    page_size: int