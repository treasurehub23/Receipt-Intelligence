from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import time as time_module
import bcrypt
import cv2 as cv
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from pdf2image import convert_from_bytes
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ocr.groq_reader import read_receipt_with_groq
from ML.classify import classify
#from ML.features import parsed_receipt_to_text
from app.security import get_current_user
from db.database import get_db
from db.models import ExpenseItem, Receipt, User
#from ocr.easyocr_reader import extract_text
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


def build_expense_response(expense: ExpenseItem, *, duplicate: bool = False) -> dict:
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
        conditions.append(ExpenseItem.category == category)
    if start_date:
        conditions.append(
            ExpenseItem.purchase_date >= datetime.combine(start_date, time.min)
        )
    if end_date:
        conditions.append(
            ExpenseItem.purchase_date <= datetime.combine(end_date, time.max)
        )
    return conditions


logger = logging.getLogger(__name__)


# @router.post("/upload")
# async def upload_expense(
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
# ):
#     print("UPLOAD ENDPOINT ENTERED", flush=True)
#     # 1. Validate the uploaded file.
#     accepted_types = {
#         "image/jpeg",
#         "image/png",
#         "image/jpg",
#         "application/pdf",
#     }

#     if file.content_type not in accepted_types:
#         raise HTTPException(
#             status_code=415,
#             detail="Only JPEG, PNG, and PDF files are accepted.",
#         )

#     content = await file.read()

#     if not content:
#         raise HTTPException(
#             status_code=400,
#             detail="The uploaded file is empty.",
#         )

#     if len(content) > 5 * 1024 * 1024:
#         raise HTTPException(
#             status_code=413,
#             detail="File size must not exceed 5 MB.",
#         )

#     # 2. Check whether this user has already uploaded this file.
#     image_hash = hashlib.sha256(content).hexdigest()

#     existing_receipt = db.scalar(
#         select(Receipt).where(
#             Receipt.user_id == user.id,
#             Receipt.image_hash == image_hash,
#         )
#     )

#     if existing_receipt:
#         existing_items = db.scalars(
#             select(ExpenseItem).where(
#                 ExpenseItem.receipt_id == existing_receipt.id,
#                 ExpenseItem.user_id == user.id,
#             )
#         ).all()
#         logger.info("Duplicate receipt check completed")
#         return {
#             "message": "This receipt has already been uploaded.",
#             "receipt": existing_receipt,
#             "items": existing_items,
#         }

#     try:
#         # 3. Convert the uploaded file into images.
#         if file.content_type == "application/pdf":
#             pages = convert_from_bytes(content, dpi=300)

#             if not pages:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="PDF contains no pages.",
#                 )

#             images = []

#             for page in pages:
#                 page_array = np.array(page.convert("RGB"))
#                 page_image = cv.cvtColor(
#                     page_array,
#                     cv.COLOR_RGB2BGR,
#                 )
#                 images.append(preprocess_image(page_image))

#         else:
#             img_array = np.frombuffer(content, np.uint8)
#             image = cv.imdecode(img_array, cv.IMREAD_COLOR)

#             if image is None:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Could not decode image.",
#                 )

#             images = [preprocess_image(image)]

#         # 4. Extract structured receipt data with Groq.
#         start_time = time_module.perf_counter()
#         page_results = []

#         for image in images:
#             success, encoded_image = cv.imencode(".jpg", image)

#             if not success:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Could not prepare receipt image.",
#                 )
#             logger.info("Calling Groq for page %s", len(page_results) + 1)
#             result = read_receipt_with_groq(
#                 encoded_image.tobytes(),
#                 content_type="image/jpeg",
#             )
            
#             print("GROQ RESULT:", repr(result), flush=True)
#             page_results.append(result)
        
#         duration = time_module.perf_counter() - start_time

#         logger.info(
#             "Receipt extraction completed for user_id=%s "
#             "in %.2f seconds across %s page(s)",
#             user.id,
#             duration,
#             len(page_results),
#         )

#         if not page_results:
#             raise HTTPException(
#                 status_code=422,
#                 detail="No receipt data could be extracted.",
#             )

#         # Combine line items from all pages.
#         # Receipt-level details come from the first page.
#         groq_result = page_results[0].copy()
#         groq_result["line_items"] = []
#         print("COMBINED RESULT:", repr(groq_result), flush=True)
#         for page_result in page_results:
#             groq_result["line_items"].extend(
#                 page_result.get("line_items", [])
#             )

#         if not groq_result["line_items"]:
#             raise HTTPException(
#                 status_code=422,
#                 detail="No line items could be extracted from this receipt.",
#             )

#         # Preserve the structured extraction for debugging.
#         raw_text = json.dumps(
#             groq_result,
#             ensure_ascii=False,
#             default=str,
#         )

#         # 5. Convert extracted receipt fields.
#         date_value = groq_result.get("purchase_date")
#         purchase_date = None

#         if date_value:
#             try:
#                 purchase_date = datetime.strptime(
#                     date_value,
#                     "%Y-%m-%d",
#                 ).date()
#             except (ValueError, TypeError):
#                 raise HTTPException(
#                     status_code=422,
#                     detail="Receipt date could not be interpreted.",
#                 )

#         purchase_datetime = (
#             datetime.combine(purchase_date, time.min)
#             if purchase_date is not None
#             else None
#         )

#         merchant = groq_result.get("merchant")
#         currency = groq_result.get("currency")
#         total_value = groq_result.get("total")

#         receipt_total = (
#             Decimal(str(total_value))
#             if total_value is not None
#             else None
#         )

#         # 6. Create the receipt and its expense items.
#         receipt = Receipt(
#             user_id=user.id,
#             merchant=merchant,
#             purchase_date=purchase_datetime,
#             total=receipt_total,
#             currency=currency,
#             image_hash=image_hash,
#             raw_text=raw_text,
#         )

#         db.add(receipt)

#         # Obtain the receipt ID before creating its items.
#         db.flush()

#         expense_items = []

#         for line_item in groq_result["line_items"]:
#             description = line_item.get("description")
#             quantity_value = line_item.get("quantity")
#             item_total_value = line_item.get("total_price")

#             # Ignore incomplete line items.
#             if (
#                 not description
#                 or quantity_value is None
#                 or item_total_value is None
#             ):
#                 continue

#             try:
#                 quantity = Decimal(str(quantity_value))
#                 line_total = Decimal(str(item_total_value))
#             except (ValueError, TypeError, InvalidOperation):
#                 continue

#             if (
#                 not quantity.is_finite()
#                 or not line_total.is_finite()
#                 or quantity <= 0
#                 or line_total < 0
#             ):
#                 continue

#             unit_price = (
#                 line_total / quantity
#             ).quantize(Decimal("0.01"))

#             # Classify each item, not the entire receipt.
#             category, category_conf = classify(description)

#             expense_item = ExpenseItem(
#                 user_id=user.id,
#                 receipt_id=receipt.id,
#                 description=description,
#                 quantity=quantity,
#                 unit_price=unit_price,
#                 total_price=line_total,
#                 purchase_date=purchase_datetime,
#                 currency=currency or "NGN",
#                 category=category,
#                 original_predicted_category=category,
#                 category_confidence=float(category_conf),
#             )

#             expense_items.append(expense_item)

#         if not expense_items:
#             raise HTTPException(
#                 status_code=422,
#                 detail="No valid expense items could be extracted.",
#             )

#         db.add_all(expense_items)

#         # Save the receipt and all its items together.
#         db.commit()

#         db.refresh(receipt)

#         for item in expense_items:
#             db.refresh(item)

#         logger.info(
#             "Receipt saved for user_id=%s, receipt_id=%s, items=%s",
#             user.id,
#             receipt.id,
#             len(expense_items),
#         )

#         return {
#             "message": "Receipt uploaded and processed successfully.",
#             "receipt": receipt,
#             "items": expense_items,
#         }

#     except HTTPException:
#         db.rollback()
#         raise

#     except IntegrityError:
#         db.rollback()
#         logger.exception(
#             "Database integrity error for user_id=%s",
#             user.id,
#         )
#         raise HTTPException(
#             status_code=409,
#             detail="The receipt could not be saved because of a data conflict.",
#         )

#     except Exception:
#         db.rollback()
#         logger.exception(
#             "Receipt processing failed for user_id=%s",
#             user.id,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail="Receipt processing failed. Please try again.",
#         )

#     finally:
#         await file.close()

# @router.get("", response_model=ExpenseListResponse)
# def get_expenses(
#     db: Session = Depends(get_db),
#     start_date: date | None = Query(default=None),
#     end_date: date | None = Query(default=None),
#     category: str | None = Query(default=None),
#     page: int = Query(default=1, ge=1),
#     page_size: int = Query(default=10, ge=1, le=100),
#     user=Depends(get_current_user),
# ):
#     conditions = get_expense_filters(
#         category,
#         start_date,
#         end_date,
#     )

#     query = (
#         select(ExpenseItem)
#         .where(ExpenseItem.user_id == user.id)
#         .order_by(ExpenseItem.created_at.desc())
#     )

#     count_query = (
#         select(func.count())
#         .select_from(ExpenseItem)
#         .where(ExpenseItem.user_id == user.id)
#     )

#     if conditions:
#         query = query.where(*conditions)
#         count_query = count_query.where(*conditions)

#     total_count = db.scalar(count_query) or 0
#     offset = (page - 1) * page_size

#     items = db.scalars(
#         query.offset(offset).limit(page_size)
#     ).all()

#     expenses = [
#         ExpenseOut.model_validate(item)
#         for item in items
#     ]

#     total_pages = (total_count + page_size - 1) // page_size

#     return ExpenseListResponse(
#         items=expenses,
#         total=total_count,
#         page=page,
#         page_size=page_size,
#         total_pages=total_pages,
#     )
@router.post("/upload")
async def upload_expense(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    print("UPLOAD ENDPOINT ENTERED", flush=True)

    # 1. Validate the uploaded file.
    accepted_types = {
        "image/jpeg",
        "image/png",
        "image/jpg",
        "application/pdf",
    }

    if file.content_type not in accepted_types:
        raise HTTPException(
            status_code=415,
            detail="Only JPEG, PNG, and PDF files are accepted.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 5 MB.",
        )

    # 2. Hash the original file and check for duplicates.
    image_hash = hashlib.sha256(content).hexdigest()

    existing_receipt = db.scalar(
        select(Receipt).where(
            Receipt.user_id == user.id,
            Receipt.image_hash == image_hash,
        )
    )

    if existing_receipt:
        existing_items = db.scalars(
            select(ExpenseItem).where(
                ExpenseItem.receipt_id == existing_receipt.id,
                ExpenseItem.user_id == user.id,
            )
        ).all()

        return {
            "message": "This receipt has already been uploaded.",
            "receipt": existing_receipt,
            "items": existing_items,
        }

    try:
        # 3. Prepare the images that will be sent to Groq.
        # JPEG and PNG files are sent directly, without preprocessing.
        if file.content_type == "application/pdf":
            pages = convert_from_bytes(content, dpi=200)

            if not pages:
                raise HTTPException(
                    status_code=400,
                    detail="PDF contains no pages.",
                )

            images_to_process = []

            for page in pages:
                buffer = io.BytesIO()
                page.convert("RGB").save(buffer, format="JPEG")
                images_to_process.append(
                    (buffer.getvalue(), "image/jpeg")
                )

        else:
            images_to_process = [
                (content, file.content_type)
            ]

        # 4. Send each image directly to Groq.
        start_time = time_module.perf_counter()
        page_results = []

        for page_number, (image_bytes, content_type) in enumerate(
            images_to_process,
            start=1,
        ):
            print(
                f"Sending page {page_number} directly to Groq",
                flush=True,
            )

            result = read_receipt_with_groq(
                image_bytes,
                content_type=content_type,
            )

            print(
                f"Groq result for page {page_number}: {result!r}",
                flush=True,
            )

            if not isinstance(result, dict):
                raise HTTPException(
                    status_code=502,
                    detail="Groq returned an invalid response.",
                )

            page_results.append(result)

        duration = time_module.perf_counter() - start_time

        logger.info(
            "Groq extraction completed for user_id=%s "
            "in %.2f seconds",
            user.id,
            duration,
        )

        if not page_results:
            raise HTTPException(
                status_code=422,
                detail="No receipt data could be extracted.",
            )

        # 5. Combine line items from all pages.
        # Receipt-level fields are taken from the first page.
        groq_result = page_results[0].copy()
        groq_result["line_items"] = []

        for page_result in page_results:
            items = page_result.get("line_items", [])

            if isinstance(items, list):
                groq_result["line_items"].extend(items)

        print("COMBINED RESULT:", repr(groq_result), flush=True)

        if not groq_result["line_items"]:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No line items could be extracted from this receipt. "
                    "Check the Groq response and prompt."
                ),
            )

        # 6. Convert the receipt-level fields.
        date_value = groq_result.get("purchase_date")
        purchase_date = None

        if date_value:
            try:
                purchase_date = datetime.strptime(
                    date_value,
                    "%Y-%m-%d",
                ).date()
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=422,
                    detail="Receipt date must use YYYY-MM-DD format.",
                )

        purchase_datetime = (
            datetime.combine(purchase_date, time.min)
            if purchase_date is not None
            else None
        )

        merchant = groq_result.get("merchant")
        currency = groq_result.get("currency")
        total_value = groq_result.get("total")

        try:
            receipt_total = (
                Decimal(str(total_value))
                if total_value is not None
                else None
            )
        except (ValueError, TypeError, InvalidOperation):
            raise HTTPException(
                status_code=422,
                detail="Receipt total is invalid.",
            )

        if receipt_total is not None and (
            not receipt_total.is_finite() or receipt_total < 0
        ):
            raise HTTPException(
                status_code=422,
                detail="Receipt total must be a valid non-negative amount.",
            )

        raw_text = json.dumps(
            groq_result,
            ensure_ascii=False,
            default=str,
        )

        # 7. Save the receipt and its expense items in one transaction.
        receipt = Receipt(
            user_id=user.id,
            merchant=merchant,
            purchase_date=purchase_datetime,
            total=receipt_total,
            currency=currency,
            image_hash=image_hash,
            raw_text=raw_text,
        )

        db.add(receipt)
        db.flush()

        expense_items = []

        for line_item in groq_result["line_items"]:
            if not isinstance(line_item, dict):
                continue

            description = line_item.get("description")
            quantity_value = line_item.get("quantity")
            item_total_value = line_item.get("total_price")

            if (
                not isinstance(description, str)
                or not description.strip()
                or quantity_value is None
                or item_total_value is None
            ):
                continue

            try:
                quantity = Decimal(str(quantity_value))
                line_total = Decimal(str(item_total_value))
            except (ValueError, TypeError, InvalidOperation):
                continue

            if (
                not quantity.is_finite()
                or not line_total.is_finite()
                or quantity <= 0
                or line_total < 0
            ):
                continue

            # If your quantity column is Integer, validate that
            # quantity is whole before assigning it.
            if quantity != quantity.to_integral_value():
                continue

            quantity = int(quantity)

            unit_price = (
                line_total / Decimal(quantity)
            ).quantize(Decimal("0.01"))

            # Classify each item individually.
            category, category_conf = classify(description.strip())

            expense_item = ExpenseItem(
                user_id=user.id,
                receipt_id=receipt.id,
                description=description.strip(),
                quantity=quantity,
                unit_price=unit_price,
                total_price=line_total,
                purchase_date=purchase_datetime,
                currency=currency or "NGN",
                category=category,
                original_predicted_category=category,
                category_confidence=float(category_conf),
            )

            expense_items.append(expense_item)

        if not expense_items:
            raise HTTPException(
                status_code=422,
                detail="Groq returned no valid expense items.",
            )

        db.add_all(expense_items)
        db.commit()

        db.refresh(receipt)

        for item in expense_items:
            db.refresh(item)

        logger.info(
            "Receipt saved: user_id=%s receipt_id=%s item_count=%s",
            user.id,
            receipt.id,
            len(expense_items),
        )

        return {
            "message": "Receipt uploaded and processed successfully.",
            "receipt": receipt,
            "items": expense_items,
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        logger.exception(
            "Database integrity error for user_id=%s",
            user.id,
        )
        raise HTTPException(
            status_code=409,
            detail="A data conflict prevented the receipt from being saved.",
        )

    except Exception:
        db.rollback()
        logger.exception(
            "Receipt processing failed for user_id=%s",
            user.id,
        )
        raise HTTPException(
            status_code=500,
            detail="Receipt processing failed. Please try again.",
        )

    finally:
        await file.close()

@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense_category(
    expense_id: int,
    payload: ExpenseCategoryUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    query = select(ExpenseItem).where(ExpenseItem.id == expense_id, ExpenseItem.user_id == user.id)
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
    query = select(ExpenseItem).where(ExpenseItem.id == expense_id, ExpenseItem.user_id == user.id)
    expense = db.scalar(query)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise