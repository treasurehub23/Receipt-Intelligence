from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session      
from app.schemas import AnalyticsSummary, CategoryBreakdown, MonthBreakdown, SpendingInsights
from db.database import get_db
from db.models import User, Receipt, ExpenseItem
from sqlalchemy import select, func, extract
from datetime import date, timedelta
from decimal import Decimal
from app.routes.expenses import get_expense_filters
from app.security import get_current_user
import calendar

router = APIRouter( tags=["Analytics"])

@router.get("/analytics/summary", response_model=AnalyticsSummary)
def get_expense_summary(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user = Depends(get_current_user)
):
    conditions = get_expense_filters(category, start_date, end_date)

    total_query = select(func.sum(ExpenseItem.total_price), func.count(ExpenseItem.id)).where(ExpenseItem.user_id == user.id)
    if conditions:
        total_query = total_query.where(*conditions)
    total_spend, expense_count = db.execute(total_query).one()
    total_spend = Decimal("0.00") if total_spend is None else total_spend

    category_query = (
        select(
            ExpenseItem.category,
            func.sum(ExpenseItem.total_price),
            func.count(ExpenseItem.id),
        )
        .group_by(ExpenseItem.category)
        .order_by(func.sum(ExpenseItem.total_price).desc())
    )
    category_query = category_query.where(ExpenseItem.user_id == user.id)
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

    year_expr = extract("year", ExpenseItem.purchase_date)
    month_expr = extract("month", ExpenseItem.purchase_date)
    month_query = (
        select(
            year_expr,
            month_expr,
            func.sum(ExpenseItem.total_price),
            func.count(ExpenseItem.id),
        )
        .where(ExpenseItem.purchase_date.is_not(None))
        .group_by(year_expr, month_expr)
        .order_by(year_expr.desc(), month_expr.desc())
    )
    month_query = month_query.where(ExpenseItem.user_id == user.id)
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


@router.get("/analytics/insights", response_model=SpendingInsights)
def get_spending_insights(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()

    # Current month: first day through today.
    current_start = today.replace(day=1)
    current_end = today + timedelta(days=1)  # exclusive

    # Previous month, using the same number of days where possible.
    previous_last_day = current_start - timedelta(days=1)
    previous_start = previous_last_day.replace(day=1)

    previous_end_day = min(
        today.day,
        calendar.monthrange(
            previous_last_day.year,
            previous_last_day.month,
        )[1],
    )
    previous_end = previous_start.replace(
        day=previous_end_day
    ) + timedelta(days=1)  # exclusive

    def spend_between(start_date: date, end_date: date) -> Decimal:
        query = (
            select(func.coalesce(func.sum(ExpenseItem.total_price), 0))
            .select_from(ExpenseItem)
            .outerjoin(Receipt, ExpenseItem.receipt_id == Receipt.id)
            .where(
                ExpenseItem.user_id == user.id,
                ExpenseItem.purchase_date >= start_date,
                ExpenseItem.purchase_date < end_date,
                # Include standalone expenses, but exclude pending receipts.
                (
                    (ExpenseItem.receipt_id.is_(None))
                    | (Receipt.status == "completed")
                ),
            )
        )
        return Decimal(str(db.scalar(query) or 0))

    current_spend = spend_between(current_start, current_end)
    previous_spend = spend_between(previous_start, previous_end)

    if previous_spend > 0:
        percentage_change = float(
            (current_spend - previous_spend)
            / previous_spend
            * Decimal("100")
        )
        if current_spend > previous_spend:
            direction = "increased"
        elif current_spend < previous_spend:
            direction = "decreased"
        else:
            direction = "unchanged"
    else:
        percentage_change = None
        direction = "no_previous_spending"

    top_category_query = (
        select(
            ExpenseItem.category,
            func.sum(ExpenseItem.total_price).label("category_total"),
        )
        .select_from(ExpenseItem)
        .outerjoin(Receipt, ExpenseItem.receipt_id == Receipt.id)
        .where(
            ExpenseItem.user_id == user.id,
            ExpenseItem.purchase_date >= current_start,
            ExpenseItem.purchase_date < current_end,
            (
                (ExpenseItem.receipt_id.is_(None))
                | (Receipt.status == "completed")
            ),
        )
        .group_by(ExpenseItem.category)
        .order_by(func.sum(ExpenseItem.total_price).desc())
        .limit(1)
    )

    top_category_result = db.execute(top_category_query).first()

    return SpendingInsights(
        current_period_start=current_start,
        current_period_end=today,
        previous_period_start=previous_start,
        previous_period_end=previous_end - timedelta(days=1),
        current_spend=current_spend,
        previous_spend=previous_spend,
        percentage_change=percentage_change,
        spending_direction=direction,
        top_category=(
            (top_category_result[0] or "Uncategorized")
            if top_category_result
            else None
        ),
        top_category_spend=(
            Decimal(str(top_category_result[1] or 0))
            if top_category_result
            else Decimal("0.00")
        ),
    )
