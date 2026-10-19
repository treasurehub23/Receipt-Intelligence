from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session      
from app.schemas import AnalyticsSummary, CategoryBreakdown, MonthBreakdown
from db.database import get_db
from db.models import Expense
from sqlalchemy import select, func, extract
from datetime import date
from decimal import Decimal
from expenses import get_expense_filters

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/analytics/summary", response_model=AnalyticsSummary)
def get_expense_summary(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    conditions = get_expense_filters(category, start_date, end_date)

    total_query = select(func.sum(Expense.total), func.count(Expense.id))
    if conditions:
        total_query = total_query.where(*conditions)
    total_spend, expense_count = db.execute(total_query).one()
    total_spend = Decimal("0.00") if total_spend is None else total_spend

    category_query = (
        select(
            Expense.category,
            func.sum(Expense.total),
            func.count(Expense.id),
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.total).desc())
    )
    if conditions:
        category_query = category_query.where(*conditions)

    category_results = [
        CategoryBreakdown(
            category=category or "Uncategorized",
            total=total if total is not None else Decimal("0.00"),
            count=count,
        )
        for category, total, count in db.execute(category_query).all()
    ]

    year_expr = extract("year", Expense.purchase_date)
    month_expr = extract("month", Expense.purchase_date)
    month_query = (
        select(
            year_expr,
            month_expr,
            func.sum(Expense.total),
            func.count(Expense.id),
        )
        .where(Expense.purchase_date.is_not(None))
        .group_by(year_expr, month_expr)
        .order_by(year_expr.desc(), month_expr.desc())
    )
    if conditions:
        month_query = month_query.where(*conditions)

    by_month = [
        MonthBreakdown(
            year=int(year),
            month=int(month),
            total=total if total is not None else Decimal("0.00"),
            count=count,
        )
        for year, month, total, count in db.execute(month_query).all()
    ]

    return AnalyticsSummary(
        total_spend=total_spend,
        expense_count=expense_count,
        by_category=category_results,
        by_month=by_month,
    )

