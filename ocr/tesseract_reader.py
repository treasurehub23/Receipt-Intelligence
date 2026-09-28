import pytesseract

def extract_text(image):
    text = pytesseract.image_to_string(image)
    return {"source": "tesseract", "text" : text}