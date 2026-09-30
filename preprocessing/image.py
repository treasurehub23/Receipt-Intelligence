import cv2 as cv


def preprocess_image(image):
    if image.ndim == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv.cvtColor(image, cv.COLOR_BGRA2GRAY)
    else:
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