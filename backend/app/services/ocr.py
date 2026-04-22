from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image


class OCRService:
    """Tesseract-backed OCR service. Swap this class for cloud OCR or a vision model later."""

    def extract_text(self, image_path: Path) -> tuple[str, float]:
        processed = self._preprocess(image_path)
        text = pytesseract.image_to_string(processed)
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
        confidences = [
            float(value)
            for value in data.get("conf", [])
            if value not in ("-1", -1) and str(value).strip()
        ]
        avg_confidence = max(0.0, min(1.0, (sum(confidences) / len(confidences) / 100) if confidences else 0.0))
        return text.strip(), avg_confidence

    def _preprocess(self, image_path: Path) -> Image.Image:
        image = cv2.imread(str(image_path))
        if image is None:
            return Image.open(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        threshold = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        return Image.fromarray(np.asarray(threshold))
