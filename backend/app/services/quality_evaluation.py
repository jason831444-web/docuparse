import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.document import Document, DocumentType
from app.services.ai_document_understanding import AIDocumentUnderstandingResult
from app.services.file_ingestion import NormalizedDocument
from app.services.parser import ParsedDocument


@dataclass
class QualityEvaluation:
    stage: str
    score: float
    sufficient: bool
    review_required: bool
    escalation_recommended: bool = False
    reasons: list[str] = field(default_factory=list)


class DocumentQualityEvaluator:
    """Quality gates for deciding escalation and review status."""

    def evaluate_extraction(self, normalized: NormalizedDocument, parsed: ParsedDocument) -> QualityEvaluation:
        reasons: list[str] = []
        score = 0.45
        text = normalized.normalized_text or ""
        lines = [line for line in text.splitlines() if line.strip()]
        line_count = len(lines)
        lowered = text.lower()

        if len(text.strip()) >= 120:
            score += 0.18
        elif len(text.strip()) < 40:
            reasons.append("Very little text was extracted.")
            score -= 0.18

        if line_count >= 4:
            score += 0.08
        if normalized.ocr_confidence is not None:
            if normalized.ocr_confidence >= 0.75:
                score += 0.16
            elif normalized.ocr_confidence < 0.55:
                reasons.append("OCR confidence is low.")
                score -= 0.16

        if normalized.partial_support:
            reasons.append("File format support is partial.")
            score -= 0.25

        if normalized.extraction_warnings:
            reasons.extend(normalized.extraction_warnings)
            score -= min(0.18, len(normalized.extraction_warnings) * 0.06)

        if parsed.extracted_date:
            score += 0.05
        if parsed.document_type == DocumentType.receipt and parsed.extracted_amount:
            score += 0.08
            merchant_present = bool(parsed.merchant_name)
            amount_pattern_count = len(re.findall(r"\b\d{1,6}(?:,\d{3})*\.\d{2}\b", text))
            receipt_keywords = sum(keyword in lowered for keyword in ["total", "subtotal", "tax", "receipt", "change", "visa"])
            noise_lines = sum(1 for line in lines if self._is_noisy_line(line))
            noise_ratio = (noise_lines / line_count) if line_count else 0.0
            receipt_complete = merchant_present and parsed.extracted_date is not None and parsed.extracted_amount is not None
            if receipt_complete:
                score += 0.10
            if amount_pattern_count >= 3:
                score += 0.05
            if receipt_keywords >= 3:
                score += 0.05
            if noise_ratio > 0.35:
                reasons.append("Receipt text looks noisy.")
                score -= 0.10

        score = self._clamp(score)
        escalation = bool(normalized.primary_image_path and (score < 0.72 or parsed.document_type == DocumentType.other))
        if parsed.document_type == DocumentType.receipt:
            receipt_complete = bool(parsed.merchant_name and parsed.extracted_date and parsed.extracted_amount)
            if receipt_complete and score >= 0.72:
                escalation = False
                reasons.append("Receipt fields are already usable without heavy vision extraction.")
        sufficient = score >= 0.58 and bool(text.strip())
        return QualityEvaluation(
            stage="post_ingestion",
            score=score,
            sufficient=sufficient,
            review_required=score < 0.62 or normalized.partial_support,
            escalation_recommended=escalation,
            reasons=reasons or ["Extracted content passed the first quality gate."],
        )

    def evaluate_structured_result(
        self,
        document: Document,
        ai_result: AIDocumentUnderstandingResult,
        extraction_quality: QualityEvaluation,
    ) -> QualityEvaluation:
        reasons: list[str] = []
        score = float(ai_result.confidence_score or Decimal("0.70"))

        if ai_result.review_required:
            reasons.append("Extractor requested manual review.")
            score -= 0.08
        if ai_result.extraction_notes:
            reasons.extend(ai_result.extraction_notes[:4])

        if ai_result.document_type == DocumentType.receipt:
            if not ai_result.extracted_amount:
                reasons.append("Receipt amount is missing.")
                score -= 0.18
            if not ai_result.extracted_date:
                reasons.append("Receipt date is missing.")
                score -= 0.10
            if not ai_result.merchant_name:
                reasons.append("Receipt merchant is missing.")
                score -= 0.08
        elif ai_result.document_type in {DocumentType.notice, DocumentType.document, DocumentType.memo}:
            if not ai_result.title:
                reasons.append("Document title is weak or missing.")
                score -= 0.08

        if extraction_quality.review_required:
            score -= 0.05

        score = self._clamp(score)
        review_required = score < 0.64 or bool(reasons and ai_result.review_required)
        return QualityEvaluation(
            stage="post_structured_extraction",
            score=score,
            sufficient=score >= 0.58,
            review_required=review_required,
            escalation_recommended=False,
            reasons=reasons or ["Structured extraction passed the second quality gate."],
        )

    def _clamp(self, score: float) -> float:
        return max(0.0, min(0.99, round(score, 3)))

    def _is_noisy_line(self, line: str) -> bool:
        token_count = len(line.split())
        symbol_count = len(re.findall(r"[^A-Za-z0-9\s.,:/$%-]", line))
        return (token_count <= 2 and symbol_count >= 2) or bool(re.search(r"(.)\1{4,}", line))
