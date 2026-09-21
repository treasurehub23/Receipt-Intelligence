import easyocr

reader = easyocr.Reader(["en"])


def extract_text(image):
    result = reader.readtext(image)

    return [
        {
            "text": text        }
        for bounding_boxes, text, confidence in result
    ]  