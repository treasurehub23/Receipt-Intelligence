import easyocr

reader = easyocr.Reader(["en"])


def extract_text(image):
    result = reader.readtext(image)

    return {"source": "easyocr", "text":[
        {
            "text": text        }
        for bounding_boxes, text, confidence in result
    ]}


