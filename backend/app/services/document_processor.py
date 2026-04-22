from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.services.ai_document_understanding import get_document_ai_service
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
            ai_result = get_document_ai_service().analyze(
                Path(document.stored_file_path),
                raw_text,
                parsed,
                document.original_filename,
            )
            document.raw_text = raw_text
            document.confidence_score = ai_result.confidence_score or Decimal(str(round(confidence, 3)))
            document.ai_document_type = ai_result.document_type
            document.ai_confidence_score = ai_result.confidence_score
            document.ai_extraction_notes = self._notes(ai_result.extraction_notes)
            document.review_required = ai_result.review_required
            document.summary = ai_result.summary
            document.extraction_provider = ai_result.extraction_provider or ai_result.provider
            document.refinement_provider = ai_result.refinement_provider
            document.provider_chain = "+".join(ai_result.provider_chain) if ai_result.provider_chain else ai_result.provider
            document.merge_strategy = ai_result.merge_strategy
            document.field_sources = ai_result.field_sources or None
            document.document_type = ai_result.document_type or parsed.document_type
            document.title = ai_result.title or parsed.title
            document.extracted_date = ai_result.extracted_date or parsed.extracted_date
            document.extracted_amount = ai_result.extracted_amount or parsed.extracted_amount
            document.subtotal = ai_result.subtotal
            document.tax = ai_result.tax
            document.currency = ai_result.currency or parsed.currency
            document.merchant_name = ai_result.merchant_name or parsed.merchant_name
            document.category = ai_result.category or parsed.category
            document.tags = ai_result.tags or parsed.tags
            document.processing_status = ProcessingStatus.completed
        except Exception as exc:
            document.processing_status = ProcessingStatus.failed
            document.processing_error = str(exc)
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    def _notes(self, notes: list[str]) -> str | None:
        if not notes:
            return None
        return "\n".join(dict.fromkeys(note for note in notes if note))
