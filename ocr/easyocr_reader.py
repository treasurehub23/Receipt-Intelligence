import easyocr

reader = easyocr.Reader(["en"])


def _group_into_lines(result, y_tolerance_ratio=0.6):
  
    if not result:
        return []

    items = []
    for bbox, text, conf in result:
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        items.append({"text": text, "y": sum(ys) / 4, "x": min(xs), "h": max(ys) - min(ys)})

    items.sort(key=lambda i: i["y"])

    rows = []
    for item in items:
        placed = False
        for row in rows:
            tol = y_tolerance_ratio * max(row["h"], item["h"])
            if abs(item["y"] - row["y"]) <= tol:
                row["items"].append(item)
                row["y"] = sum(i["y"] for i in row["items"]) / len(row["items"])
                row["h"] = max(row["h"], item["h"])
                placed = True
                break
        if not placed:
            rows.append({"y": item["y"], "h": item["h"], "items": [item]})

    lines = []
    for row in rows:
        row_items = sorted(row["items"], key=lambda i: i["x"])
        lines.append("   ".join(i["text"] for i in row_items))
    return lines


def extract_text(image):
    result = reader.readtext(image)
    lines = _group_into_lines(result)
    return {"source": "easyocr", "text": [{"text": line} for line in lines]}