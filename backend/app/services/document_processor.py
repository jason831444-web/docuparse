from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.services.ai_document_understanding import LocalDocumentAIService, get_document_ai_service
from app.services.category_interpretation import CategoryInterpretation
from app.services.document_router import LightweightDocumentRouter
from app.services.document_interpretation_service import DocumentInterpretationService
from app.services.file_ingestion import FileIngestionService, NormalizedDocument
from app.services.ocr import OCRService
from app.services.parser import DocumentParser
from app.services.quality_evaluation import DocumentQualityEvaluator, QualityEvaluation
from app.services.workflow_enrichment import DocumentWorkflowEnrichmentService


class DocumentProcessor:
    def __init__(self, ocr: OCRService | None = None, parser: DocumentParser | None = None) -> None:
        self.ocr = ocr or OCRService()
        self.parser = parser or DocumentParser()
        self.ingestion = FileIngestionService(ocr=self.ocr)
        self.quality = DocumentQualityEvaluator()
        self.router = LightweightDocumentRouter()
        self.lightweight_ai = LocalDocumentAIService()
        self.category_interpreter = DocumentInterpretationService()
        self.workflow_enrichment = DocumentWorkflowEnrichmentService()

    def process(self, db: Session, document: Document) -> Document:
        document.processing_status = ProcessingStatus.processing
        document.processing_error = None
        db.add(document)
        db.commit()
        db.refresh(document)
        try:
            stored_path = Path(document.stored_file_path)
            normalized = self.ingestion.ingest(stored_path, document.original_filename, document.mime_type)
            raw_text = normalized.normalized_text
            parsed = self.parser.parse(raw_text, document.original_filename)
            extraction_quality = self.quality.evaluate_extraction(normalized, parsed)
            route = self.router.route(normalized, parsed, extraction_quality)
            analysis_path = normalized.primary_image_path or stored_path
            if route.heavy_ai_required and normalized.primary_image_path:
                ai_result = get_document_ai_service().analyze(
                    analysis_path,
                    raw_text,
                    parsed,
                    document.original_filename,
                )
            else:
                ai_result = self.lightweight_ai.analyze(analysis_path, raw_text, parsed, document.original_filename)
                ai_result.extraction_provider = normalized.extraction_method or route.route_label
                ai_result.provider = ai_result.extraction_provider
                ai_result.provider_chain = [normalized.extraction_method or route.route_label, "heuristic_fallback"]
                ai_result.merge_strategy = route.route_label
            structured_quality = self.quality.evaluate_structured_result(document, ai_result, extraction_quality)
            ingestion_notes = self._ingestion_notes(normalized, route)

            document.raw_text = raw_text
            document.mime_type = normalized.mime_type or document.mime_type
            document.source_file_type = normalized.source_file_type
            document.extraction_method = normalized.extraction_method
            document.ingestion_metadata = self._ingestion_metadata(normalized, route, extraction_quality, structured_quality)
            document.confidence_score = ai_result.confidence_score or self._confidence(normalized)
            document.ai_document_type = ai_result.document_type
            document.ai_confidence_score = ai_result.confidence_score
            quality_notes = self._quality_notes(extraction_quality, structured_quality)
            document.ai_extraction_notes = self._notes(ingestion_notes + quality_notes + ai_result.extraction_notes)
            document.review_required = (
                ai_result.review_required
                or route.review_required
                or extraction_quality.review_required
                or structured_quality.review_required
                or bool(normalized.extraction_warnings)
            )
            document.summary = ai_result.summary
            document.extraction_provider = ai_result.extraction_provider or ai_result.provider
            document.refinement_provider = ai_result.refinement_provider
            provider_chain = self._provider_chain(normalized, route, ai_result.provider_chain or [ai_result.provider])
            document.provider_chain = "+".join(provider_chain)
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
            interpretation = self.category_interpreter.interpret(document, ai_result.cleaned_raw_text or raw_text)
            provider_chain = self._provider_chain(
                normalized,
                route,
                ai_result.provider_chain or [ai_result.provider],
                interpretation.provider_chain,
            )
            document.provider_chain = "+".join(provider_chain)
            document.title = self._apply_title_hint(document.title, interpretation)
            document.category = self._apply_category_hint(document.category, interpretation)
            document.document_type = self._refined_document_type(document.document_type, interpretation)
            if interpretation.summary_hint:
                document.summary = interpretation.summary_hint
            document.tags = self._merge_tags(document.tags, interpretation)
            document.ai_extraction_notes = self._notes(
                (ingestion_notes + quality_notes + ai_result.extraction_notes)
                + self._interpretation_notes(interpretation)
            )
            document.ingestion_metadata = self._ingestion_metadata(
                normalized,
                route,
                extraction_quality,
                structured_quality,
                interpretation,
            )
            workflow = self.workflow_enrichment.enrich(document, ai_result.cleaned_raw_text or raw_text, interpretation)
            document.workflow_summary = workflow.workflow_summary
            document.action_items = workflow.action_items
            document.warnings = workflow.warnings
            document.key_dates = workflow.key_dates
            document.urgency_level = workflow.urgency_level
            document.follow_up_required = workflow.follow_up_required
            document.workflow_metadata = workflow.workflow_metadata or None
            document.review_required = document.review_required or bool(workflow.warnings)
            document.processing_status = ProcessingStatus.needs_review if document.review_required else ProcessingStatus.ready
        except Exception as exc:
            document.processing_status = ProcessingStatus.failed
            document.processing_error = str(exc)
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    def _confidence(self, normalized: NormalizedDocument) -> Decimal | None:
        if normalized.ocr_confidence is None:
            return Decimal("0.850")
        return Decimal(str(round(normalized.ocr_confidence, 3)))

    def _ingestion_notes(self, normalized: NormalizedDocument, route) -> list[str]:
        notes = list(normalized.extraction_warnings)
        notes.extend(f"Route: {route.route_label} - {reason}" for reason in route.reasons)
        if route.heavy_ai_required:
            notes.append("Heavy AI extraction was selected for this document.")
        else:
            notes.append("Heavy AI extraction was skipped because direct/lightweight extraction was sufficient.")
        return notes

    def _ingestion_metadata(
        self,
        normalized: NormalizedDocument,
        route,
        extraction_quality: QualityEvaluation,
        structured_quality: QualityEvaluation,
        interpretation: CategoryInterpretation | None = None,
    ) -> dict:
        metadata = {
            "source_file_type": normalized.source_file_type,
            "mime_type": normalized.mime_type,
            "extraction_method": normalized.extraction_method,
            "route": route.route_label,
            "processing_path": route.processing_path.value,
            "route_confidence": route.confidence,
            "route_reasons": route.reasons,
            "heavy_ai_required": route.heavy_ai_required,
            "partial_support": normalized.partial_support,
            "extraction_warnings": normalized.extraction_warnings,
            "file_metadata": normalized.file_metadata,
            "page_images": [str(path) for path in normalized.rendered_image_paths],
            "raw_block_count": len(normalized.raw_extracted_blocks),
            "quality_gates": {
                extraction_quality.stage: {
                    "score": extraction_quality.score,
                    "sufficient": extraction_quality.sufficient,
                    "review_required": extraction_quality.review_required,
                    "escalation_recommended": extraction_quality.escalation_recommended,
                    "reasons": extraction_quality.reasons,
                },
                structured_quality.stage: {
                    "score": structured_quality.score,
                    "sufficient": structured_quality.sufficient,
                    "review_required": structured_quality.review_required,
                    "escalation_recommended": structured_quality.escalation_recommended,
                    "reasons": structured_quality.reasons,
                },
            },
        }
        if interpretation:
            metadata["category_interpretation"] = {
                "category": interpretation.category,
                "profile": interpretation.profile,
                "subtype": interpretation.subtype,
                "title_hint": interpretation.title_hint,
                "summary_hint": interpretation.summary_hint,
                "key_fields": interpretation.key_fields,
                "warnings": interpretation.warnings,
                "workflow_hints": interpretation.workflow_hints,
                "reasons": interpretation.reasons,
                "confidence": interpretation.confidence,
                "provider": interpretation.provider,
                "provider_chain": interpretation.provider_chain,
                "refinement_status": interpretation.refinement_status,
                "diagnostics": interpretation.diagnostics,
                "ai_assisted": interpretation.ai_assisted,
            }
        return metadata

    def _provider_chain(
        self,
        normalized: NormalizedDocument,
        route,
        ai_chain: list[str],
        interpretation_chain: list[str] | None = None,
    ) -> list[str]:
        values = [normalized.extraction_method, route.route_label, *ai_chain, *(interpretation_chain or [])]
        return list(dict.fromkeys(value for value in values if value))

    def _notes(self, notes: list[str]) -> str | None:
        if not notes:
            return None
        return "\n".join(dict.fromkeys(note for note in notes if note))

    def _quality_notes(self, extraction_quality: QualityEvaluation, structured_quality: QualityEvaluation) -> list[str]:
        return [
            f"Quality gate {extraction_quality.stage}: score={extraction_quality.score}, sufficient={extraction_quality.sufficient}.",
            f"Quality gate {structured_quality.stage}: score={structured_quality.score}, sufficient={structured_quality.sufficient}.",
        ]

    def _interpretation_notes(self, interpretation: CategoryInterpretation) -> list[str]:
        return [
            f"Category interpretation: profile={interpretation.profile}, category={interpretation.category}, confidence={interpretation.confidence}."
        ] + list(interpretation.reasons) + list(interpretation.diagnostics)

    def _apply_title_hint(self, current_title: str | None, interpretation: CategoryInterpretation) -> str | None:
        if not interpretation.title_hint:
            return current_title
        if not current_title or current_title.lower() in {"untitled document", "profile note"}:
            return interpretation.title_hint
        if current_title.lower().startswith(("page ", "slide ")):
            return interpretation.title_hint
        if interpretation.profile in {"profile_record", "resume_profile"} and current_title != interpretation.title_hint:
            return interpretation.title_hint
        return current_title

    def _apply_category_hint(self, current_category: str | None, interpretation: CategoryInterpretation) -> str | None:
        specific_profiles = {
            "syllabus",
            "course_guide",
            "presentation_guide",
            "speaking_notes",
            "resume_profile",
            "profile_record",
            "repair_service_receipt",
            "utility_bill",
            "meeting_notice",
            "instructional_memo",
            "invoice",
        }
        if interpretation.profile in specific_profiles:
            return interpretation.profile
        return interpretation.category or current_category

    def _refined_document_type(self, current_type, interpretation: CategoryInterpretation):
        profile = interpretation.profile
        if profile in {"syllabus", "course_guide", "resume_profile", "profile_record", "invoice", "utility_bill"}:
            return type(current_type).document
        if profile in {"presentation_guide", "speaking_notes", "instructional_memo"}:
            return type(current_type).memo
        if profile == "meeting_notice":
            return type(current_type).notice
        if profile in {"repair_service_receipt", "receipt"}:
            return type(current_type).receipt
        return current_type

    def _merge_tags(self, current_tags: list[str], interpretation: CategoryInterpretation) -> list[str]:
        tags = list(current_tags or [])
        for value in [interpretation.profile, interpretation.category, interpretation.subtype]:
            if value and value not in {"generic_document", "other", "document", "notice"}:
                tags.append(value)
        return list(dict.fromkeys(tags))
