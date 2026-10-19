from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
from db.models import Expense
from ocr.easyocr_reader import extract_text
from parsing import parse_receipt
from preprocessing.image import preprocess_image
from app.schemas import (ExpenseCategoryUpdate, ExpenseListResponse, ExpenseOut)

router = APIRouter(prefix="/expenses", tags=["Expenses"])

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



@router.post("/upload")
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

@router.get("", response_model=ExpenseListResponse)
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
    expenses = [ExpenseOut.model_validate(item) for item in items]
    total_pages = (total_count + page_size - 1) // page_size

    return ExpenseListResponse(
        items=expenses,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )



@router.patch("/{expense_id}", response_model=ExpenseOut)
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
