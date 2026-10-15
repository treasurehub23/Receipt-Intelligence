from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import time as time_module
import bcrypt
import cv2 as cv
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from pdf2image import convert_from_bytes
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ML.classify import classify
from ML.features import parsed_receipt_to_text
from db.database import get_db
from db.models import Expense, User
from ocr.easyocr_reader import extract_text
from parsing import parse_receipt
from preprocessing.image import preprocess_image
from schemas import (
    AnalyticsSummary,
    CategoryBreakdown,
    ExpenseCategoryUpdate,
    ExpenseListResponse,
    ExpenseOut,
    MonthBreakdown,
    RegisterUserRequest,
    RegisterUserResponse,
)

app = FastAPI()
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ACCEPTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
}


def build_expense_response(expense: Expense, *, duplicate: bool = False) -> dict:
    """Return the common response fields for a saved expense."""
    response = {
        "id": expense.id,
        "merchant": expense.merchant,
        "purchase_date": expense.purchase_date,
        "total": expense.total,
        "currency": expense.currency,
        "category": expense.category,
        "category_confidence": expense.category_confidence,
        "created_at": expense.created_at,
    }
    if duplicate:
        response["duplicate"] = True
    return response


def get_expense_filters(
    category: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list:
    """Build shared filters for expense listing and analytics."""
    conditions = []
    if category:
        conditions.append(Expense.category == category)
    if start_date:
        conditions.append(
            Expense.purchase_date >= datetime.combine(start_date, time.min)
        )
    if end_date:
        conditions.append(
            Expense.purchase_date <= datetime.combine(end_date, time.max)
        )
    return conditions


@app.get("/")
def home():
    return {"message": "I'm aliveeee"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_expense(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Upload a JPEG, PNG, or PDF.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB limit")

    image_hash = hashlib.sha256(content).hexdigest()
    existing_expense = db.scalar(
        select(Expense).where(Expense.image_hash == image_hash)
    )
    if existing_expense is not None:
        return build_expense_response(existing_expense, duplicate=True)

    if file.content_type == "application/pdf":
        pages = convert_from_bytes(content, dpi=300)
        if not pages:
            raise HTTPException(status_code=400, detail="PDF contains no pages")

        # Process every PDF page instead of accidentally keeping only the last.
        images = []
        for page in pages:
            page_array = np.array(page.convert("RGB"))
            page_image = cv.cvtColor(page_array, cv.COLOR_RGB2BGR)
            images.append(preprocess_image(page_image))
    else:
        img_array = np.frombuffer(content, np.uint8)
        image = cv.imdecode(img_array, cv.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Could not decode image")
        images = [preprocess_image(image)]

    print("Image received.")
    start_time = time_module.perf_counter()
    page_texts = []
    ocr_sources = []
    for image in images:
        ocr_result = extract_text(image)
        page_texts.append("\n".join(item["text"] for item in ocr_result["text"]))
        ocr_sources.append(ocr_result.get("source", "unknown"))
    print("OCR sources:", ocr_sources)
    print("OCR duration:", time_module.perf_counter() - start_time)

    raw_text = "\n".join(page_texts)
    parsed = parse_receipt(raw_text, default_currency="NGN")
    feature_text = parsed_receipt_to_text(parsed)
    category, category_conf = classify(feature_text)

    expense = Expense(
        merchant=parsed.merchant,
        purchase_date=parsed.purchase_date,
        total=parsed.total,
        currency=parsed.currency,
        merchant_confidence=parsed.confidence.merchant,
        purchase_date_confidence=parsed.confidence.purchase_date,
        total_confidence=parsed.confidence.total,
        currency_confidence=parsed.confidence.currency,
        category=category,
        category_confidence=category_conf,
        original_predicted_category=category,
        image_hash=image_hash,
        line_items=[item.model_dump(mode="json") for item in parsed.line_items],
        raw_text=parsed.raw_text,
    )

    db.add(expense)
    try:
        db.commit()
        db.refresh(expense)
    except IntegrityError:
        db.rollback()
        # A concurrent request may have inserted the same file after our lookup.
        existing_expense = db.scalar(
            select(Expense).where(Expense.image_hash == image_hash)
        )
        if existing_expense is not None:
            return build_expense_response(existing_expense, duplicate=True)
        raise HTTPException(
            status_code=409,
            detail="Could not save expense because of a database conflict",
        )

    response = parsed.model_dump(mode="json")
    response["id"] = expense.id
    response["category"] = category
    response["category_confidence"] = category_conf
    response["created_at"] = expense.created_at.isoformat()
    response["duplicate"] = False
    return response


@app.get("/expenses", response_model=ExpenseListResponse)
def get_expenses(
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    conditions = get_expense_filters(category, start_date, end_date)

    query = select(Expense).order_by(Expense.created_at.desc())
    count_query = select(func.count()).select_from(Expense)
    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)

    total_count = db.scalar(count_query) or 0
    offset = (page - 1) * page_size
    items = db.scalars(query.offset(offset).limit(page_size)).all()
    total_pages = (total_count + page_size - 1) // page_size

    return ExpenseListResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/analytics/summary", response_model=AnalyticsSummary)
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


@app.patch("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense_category(
    expense_id: int,
    payload: ExpenseCategoryUpdate,
    db: Session = Depends(get_db),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    new_category = payload.category.strip()
    if not new_category:
        raise HTTPException(status_code=422, detail="Category cannot be empty")

    # Keep the first classifier prediction for later evaluation/training.
    if expense.original_predicted_category is None:
        expense.original_predicted_category = expense.category

    expense.category = new_category
    try:
        db.commit()
        db.refresh(expense)
    except Exception:
        db.rollback()
        raise

    return expense

@app.post("/auth/register", response_model=RegisterUserResponse)
def register_user(
    payload: RegisterUserRequest,
    db: Session = Depends(get_db),
):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Hash the password
    hashed_password = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()

    # Create new user
    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return RegisterUserResponse(
        id=new_user.id,
        email=new_user.email,
        created_at=new_user.created_at,
    )


@app.post("/auth/login")
def login_user(
    payload: RegisterUserRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not bcrypt.checkpw(payload.password.encode(), user.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful", "user_id": user.id}