from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.services.ocr import OCRService
from app.services.parser import DocumentParser


class DocumentProcessor:
    def __init__(self, ocr: OCRService | None = None, parser: DocumentParser | None = None) -> None:
        self.ocr = ocr or OCRService()
        self.parser = parser or DocumentParser()

    def process(self, db: Session, document: Document) -> Document:
        document.processing_status = ProcessingStatus.processing
        document.processing_error = None
        db.add(document)
        db.commit()
        db.refresh(document)
        try:
            raw_text, confidence = self.ocr.extract_text(Path(document.stored_file_path))
            parsed = self.parser.parse(raw_text, document.original_filename)
            document.raw_text = raw_text
            document.confidence_score = Decimal(str(round(confidence, 3)))
            document.document_type = parsed.document_type
            document.title = parsed.title
            document.extracted_date = parsed.extracted_date
            document.extracted_amount = parsed.extracted_amount
            document.currency = parsed.currency
            document.merchant_name = parsed.merchant_name
            document.category = parsed.category
            document.tags = parsed.tags
            document.processing_status = ProcessingStatus.completed
        except Exception as exc:
            document.processing_status = ProcessingStatus.failed
            document.processing_error = str(exc)
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
