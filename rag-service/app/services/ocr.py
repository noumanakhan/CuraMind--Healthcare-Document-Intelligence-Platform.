import abc
import io
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("rag_service.ocr")


class OCRProvider(abc.ABC):
    @abc.abstractmethod
    def extract_text_from_image(self, image_bytes: bytes, filename: Optional[str] = None) -> str:
        """Extract full text from scanned image or image-only PDF page."""
        pass


class MockOCRProvider(OCRProvider):
    """
    Safe no-op OCR provider for tests and environments without a real OCR engine.
    """
    def extract_text_from_image(self, image_bytes: bytes, filename: Optional[str] = None) -> str:
        # Returning invented clinical facts in mock mode can contaminate the index.
        return ""


class TesseractOCRProvider(OCRProvider):
    """
    Real OCR provider using pytesseract wrapping local Tesseract OCR engine.
    """
    def __init__(self):
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
        except ImportError:
            self.pytesseract = None
            self.Image = None
            logger.warning("pytesseract or PIL not installed. Falling back to mock OCR.")

    def extract_text_from_image(self, image_bytes: bytes, filename: Optional[str] = None) -> str:
        if not self.pytesseract or not self.Image:
            return MockOCRProvider().extract_text_from_image(image_bytes, filename)
        try:
            image = self.Image.open(io.BytesIO(image_bytes))
            text = self.pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return ""


def get_ocr_provider() -> OCRProvider:
    if settings.OCR_PROVIDER == "tesseract":
        return TesseractOCRProvider()
    return MockOCRProvider()
