import cv2 as cv
import numpy as np


def preprocess_image(image):
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

    denoised = cv.GaussianBlur(gray, (5, 5), 0)

    threshold = cv.threshold(
        denoised,
        0,
        255,
        cv.THRESH_BINARY + cv.THRESH_OTSU
    )[1]

    upscaled = cv.resize(
        threshold,
        None,
        fx=2,
        fy=2,
        interpolation=cv.INTER_CUBIC
    )

    return upscaled