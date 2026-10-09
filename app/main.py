from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Query
from pdf2image import convert_from_bytes
from preprocessing.image import preprocess_image
import cv2 as cv
import numpy as np
from ocr.easyocr_reader import extract_text
from parsing import parse_receipt
from ML.features import parsed_receipt_to_text
from ML.classify import classify
import time as time_module
from db.database import get_db
from db.models import Expense
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from schemas import ExpenseOut
from datetime import datetime, date, timedelta, time
app = FastAPI()

@app.get("/")
def home():
    return {"message": "I'm aliveeee"}
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_expense(file: UploadFile = File(...), db: Session = Depends(get_db)):
    accepted_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    content = await file.read()
    max_Size = 5 * 1024 * 1024 
    if len(content) > max_Size:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 5MB.")
    
    if file.content_type not in accepted_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are accepted.")
    elif file.content_type == "application/pdf":
        images = convert_from_bytes(content, dpi=300)
        for img in images:
    
            open_cv_image = np.array(img)
            image= cv.cvtColor(open_cv_image, cv.COLOR_BGR2RGB)
    else:
        img_array = np.frombuffer(content, np.uint8)
        image = cv.imdecode(img_array, cv.IMREAD_COLOR)

    preprocessed_image = preprocess_image(image)

    print("Image received.")
    start_time = time_module.perf_counter()
    ocr_result = extract_text(preprocessed_image)
    end_time = time_module.perf_counter()
    print(ocr_result["source"])
    print(end_time-start_time)
    raw_text = "\n".join(item["text"] for item in ocr_result["text"])
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
        # mode="json" matters here: LineItem.price is a Decimal, and the
        # plain .model_dump() leaves it as Decimal, which the JSON column's
        # serializer can't handle. mode="json" converts it to a string first.
        line_items=[li.model_dump(mode="json") for li in parsed.line_items],
        raw_text=parsed.raw_text,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    response = parsed.model_dump(mode="json")
   
    response["id"] = expense.id
    response["category"] = category
    response["category_confidence"] = category_conf
    response["created_at"] = str(expense.created_at)
    return response


@app.get("expenses")
def get_expenses(db: Session = Depends(get_db)):
    expenses = db.query(Expense).all()
    return 