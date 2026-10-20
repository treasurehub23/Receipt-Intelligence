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
from app.security import get_current_user
from db.database import get_db
from db.models import Expense
from ocr.easyocr_reader import extract_text
from parsing import parse_receipt
from preprocessing.image import preprocess_image
from app.schemas import (ExpenseCategoryUpdate, ExpenseListResponse, ExpenseOut)
import logging

logger = logging.getLogger(__name__)

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


logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_expense(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    # 1. Validate the uploaded file.
    if file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Invalid file type. Upload a JPEG, PNG, or PDF.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 5 MB limit.",
        )

    # 2. Generate a hash and check for a duplicate belonging to this user.
    image_hash = hashlib.sha256(content).hexdigest()

    existing_expense = db.scalar(
        select(Expense).where(
            Expense.image_hash == image_hash,
            Expense.user_id == user.id,
        )
    )

    if existing_expense is not None:
        logger.info(
            "Duplicate receipt upload detected for user_id=%s",
            user.id,
        )
        return build_expense_response(existing_expense, duplicate=True)

    # 3. Convert the uploaded file into images.
    try:
        if file.content_type == "application/pdf":
            pages = convert_from_bytes(content, dpi=300)

            if not pages:
                raise HTTPException(
                    status_code=400,
                    detail="PDF contains no pages.",
                )

            images = []

            for page in pages:
                page_array = np.array(page.convert("RGB"))
                page_image = cv.cvtColor(
                    page_array,
                    cv.COLOR_RGB2BGR,
                )
                images.append(preprocess_image(page_image))

        else:
            img_array = np.frombuffer(content, np.uint8)
            image = cv.imdecode(img_array, cv.IMREAD_COLOR)

            if image is None:
                raise HTTPException(
                    status_code=400,
                    detail="Could not decode image.",
                )

            images = [preprocess_image(image)]

        # 4. Extract text from every page.
        start_time = time_module.perf_counter()
        page_texts = []
        ocr_sources = []

        for image in images:
            ocr_result = extract_text(image)

            page_texts.append(
                "\n".join(
                    item["text"]
                    for item in ocr_result["text"]
                    if item.get("text", "").strip()
                )
            )

            ocr_sources.append(ocr_result.get("source", "unknown"))

        duration = time_module.perf_counter() - start_time

        logger.info(
            "OCR completed for user_id=%s in %.2f seconds; sources=%s",
            user.id,
            duration,
            ocr_sources,
        )

        raw_text = "\n".join(page_texts)

        if not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Could not read text from this receipt. "
                    "Try uploading a clearer image."
                ),
            )

        # 5. Parse the receipt and classify the expense.
        parsed = parse_receipt(raw_text, default_currency="NGN")

        feature_text = parsed_receipt_to_text(parsed)
        category, category_conf = classify(feature_text)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Receipt processing failed for user_id=%s",
            user.id,
        )
        raise HTTPException(
            status_code=500,
            detail="Receipt processing failed. Please try again.",
        )

    # 6. Build the expense record.
    expense = Expense(
        user_id=user.id,
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
        line_items=[
            item.model_dump(mode="json")
            for item in parsed.line_items
        ],
        raw_text=parsed.raw_text,
    )

    # 7. Save the expense and handle database conflicts.
    db.add(expense)

    try:
        db.commit()
        db.refresh(expense)

    except IntegrityError:
        db.rollback()

        # Check whether this user's receipt was saved concurrently.
        existing_expense = db.scalar(
            select(Expense).where(
                Expense.image_hash == image_hash,
                Expense.user_id == user.id,
            )
        )

        if existing_expense is not None:
            return build_expense_response(
                existing_expense,
                duplicate=True,
            )

        logger.exception(
            "Database integrity error while saving receipt for user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=409,
            detail="Could not save expense because of a database conflict.",
        )

    except Exception:
        db.rollback()

        logger.exception(
            "Database error while saving receipt for user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not save the expense. Please try again.",
        )

    # 8. Return the created expense.
    response = parsed.model_dump(mode="json")
    response["id"] = expense.id
    response["category"] = category
    response["category_confidence"] = category_conf
    response["created_at"] = expense.created_at.isoformat()
    response["duplicate"] = False

    logger.info(
        "Expense created successfully: expense_id=%s user_id=%s",
        expense.id,
        user.id,
    )

    return response
@router.get("", response_model=ExpenseListResponse)
def get_expenses(
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user = Depends(get_current_user)
):
    conditions = get_expense_filters(category, start_date, end_date)

    query = select(Expense).where(Expense.user_id == user.id).order_by(Expense.created_at.desc())
    count_query = select(func.count()).select_from(Expense).where(Expense.user_id == user.id)
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
    user = Depends(get_current_user)
):
    query = select(Expense).where(Expense.id == expense_id, Expense.user_id == user.id)
    expense = db.scalar(query)
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

@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    query = select(Expense).where(Expense.id == expense_id, Expense.user_id == user.id)
    expense = db.scalar(query)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise