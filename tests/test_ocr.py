import cv2 as cv
import numpy as np

from preprocessing.image import preprocess_image
from ocr.easyocr_reader import extract_text


def test_ocr_returns_text():
    
    img_array = np.frombuffer(open("/var/www/Receipt-Intelligence/images/X00016469612.jpg", "rb").read(), np.uint8)
    image = cv.imdecode(img_array, cv.IMREAD_COLOR)
    processed_image = preprocess_image(image)

    result = extract_text(processed_image)

    assert isinstance(result, dict)
    assert "text" in result
    assert isinstance(result["text"], list)
    assert len(result["text"]) > 0