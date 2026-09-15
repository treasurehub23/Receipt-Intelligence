from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
import cv2 as cv
import numpy as np
import easyocr
from pdf2image import convert_from_bytes
app = FastAPI()


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
        
    print("File received")
    reader = easyocr.Reader(["en"])
    result = reader.readtext(image)   
    print(type(result)) 
    return [{"bounding_boxes": [[int(x), int(y)] for x, y in bounding_boxes], "text": text, "confidence_scores": float(confidence_scores)} for bounding_boxes, text, confidence_scores in result] 