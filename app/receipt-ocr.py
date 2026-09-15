import pytesseract as tesseract
import cv2 as cv
import os
from pdf2image import convert_from_path
import numpy as np

pdf_path = "/var/www/Receipt-Intelligence/app/test.pdf"  # Replace with your PDF file path
images = convert_from_path(pdf_path, dpi=300) # 300 DPI is optimal for OCR

# 2. Loop through each page
for image in images:
    # 3. Convert the PIL image to an OpenCV NumPy array (RGB)
    open_cv_image = np.array(image)
    img= cv.cvtColor(open_cv_image, cv.COLOR_BGR2RGB)

    text = tesseract.image_to_string(img, config='--psm 4')  # You can adjust the PSM mode based on your needs

print(text)

# image = cv.imread("/var/www/Receipt-Intelligence/app/images.jpeg")
# print("Image loaded successfully.")
# print(type(image))
# text = tesseract.image_to_string(image, config='--psm 11')
# print(text)