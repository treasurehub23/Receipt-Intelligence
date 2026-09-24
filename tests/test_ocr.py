import cv2 as cv

from preprocessing.image import preprocess_image
from ocr.reader import extract_text


def test_ocr_returns_text():
    image = cv.imread("/var/www/Receipt-Intelligence/twenty/X00016469612.jpg")

    processed_image = preprocess_image(image)

    result = extract_text(processed_image)

    assert isinstance(result, list)
    assert len(result) > 0