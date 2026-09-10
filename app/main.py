from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
import cv2 as cv
import numpy as np
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
    accepted_types = ["image/jpeg", "image/png", "image/jpg"]

    if file.content_type not in accepted_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are accepted.")


    content = await file.read()  # Read the file content (you can process it as needed)

    max_Size = 5 * 1024 * 1024  
    if len(content) > max_Size:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 5MB.")
    nparray = np.frombuffer(content, np.uint8)
    image = cv.imdecode(nparray, cv.IMREAD_COLOR)
    # image = cv.resize(image, (120, 120))
    # print(image.shape)

    # cv.imwrite("screenshot.png", image)
    return {"id": 1, "amount": 100.0, "description": "Sample expense uploaded successfully."}

