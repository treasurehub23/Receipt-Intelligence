from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
from pdf2image import convert_from_bytes
from preprocessing.image import preprocess_image
import cv2 as cv
import numpy as np
from ocr.easyocr_reader import extract_text
from parsing.total_parser import parse_money
from parsing.items_parser import find_line_items
from parsing import parse_receipt
import time
app = FastAPI()

@app.get("/")
def home():
    return {"message": "I'm aliveeee"}
@app.get("/health")
def health_check():
    return {"status": "healthy"}

class Expense(BaseModel):
    id: int
    amount: float
    description: str


@app.post("/upload")
async def upload_expense(file: UploadFile = File(...)):
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
    start_time = time.perf_counter()
    text = extract_text(preprocessed_image)
    end_time = time.perf_counter()
    print(text["source"])
    print(end_time-start_time)
    parsed_text = parse_receipt(text["source"], default_currency="USD", today=None)
    return parsed_text

