"""Run OCR once on each real receipt image and save the raw text to disk.

This is a one-time step so label_real_receipts.py (and later, your Day 5
eval) never has to re-run slow OCR - everything downstream reads from
these .txt files instead.

Usage:
    python dump_ocr.py --images-dir path/to/your/receipt/images --out-dir receipts_ocr

Expects image files (.jpg/.jpeg/.png) in --images-dir. Writes one .txt
per image, named after the image (receipt1.jpg -> receipt1.txt).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2 as cv
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # reach your project root

from preprocessing.image import preprocess_image
from ocr.easyocr_reader import extract_text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", default = "/var/www/Receipt-Intelligence/images", help="directory containing receipt images")
    ap.add_argument("--out-dir", default="receipts_ocr", help="directory for extracted text files")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in Path(args.images_dir).iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    print(f"{len(images)} images found in {args.images_dir}")

    for path in images:
        out_path = out_dir / f"{path.stem}.txt"
        if out_path.exists():
            print(f"  skip {path.name} (already done)")
            continue

        img_array = np.frombuffer(path.read_bytes(), np.uint8)
        image = cv.imdecode(img_array, cv.IMREAD_COLOR)
        preprocessed = preprocess_image(image)

        result = extract_text(preprocessed)
        raw_text = "\n".join(item["text"] for item in result["text"])

        out_path.write_text(raw_text, encoding="utf-8")
        print(f"  {path.name} -> {out_path.name} ({len(raw_text)} chars)")

    print(f"\nDone. OCR text saved to {out_dir}/")


if __name__ == "__main__":
    main()