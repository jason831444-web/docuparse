import base64
import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from app.core.config import get_settings
from app.models.document import DocumentType
from app.services.parser import DocumentParser, ParsedDocument


CATEGORY_MAP = {
    "food_drink": ["coffee", "cafe", "restaurant", "bakery", "pizza", "burger", "tea", "deli"],
    "groceries": ["grocery", "market", "supermarket", "foods", "produce"],
    "transport": ["gas", "fuel", "uber", "lyft", "taxi", "parking", "metro", "transit"],
    "education": ["school", "student", "tuition", "class", "campus", "pta", "teacher"],
    "utilities": ["electric", "water", "internet", "utility", "phone", "bill"],
    "health": ["pharmacy", "clinic", "doctor", "medical", "dental"],
    "retail": ["store", "shop", "target", "walmart", "costco", "purchase"],
    "office": ["office", "printing", "supplies", "stationery"],
}


@dataclass
class AIDocumentUnderstandingResult:
    document_type: DocumentType = DocumentType.other
    title: str | None = None
    merchant_name: str | None = None
    extracted_date: date | None = None
    extracted_amount: Decimal | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    currency: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    cleaned_raw_text: str | None = None
    confidence_score: Decimal | None = None
    extraction_notes: list[str] = field(default_factory=list)
    review_required: bool = False
    provider: str = "heuristic_fallback"
    extraction_provider: str | None = None
    refinement_provider: str | None = None
    provider_chain: list[str] = field(default_factory=list)
    merge_strategy: str = "single_provider"
    field_sources: dict[str, str] = field(default_factory=dict)


class DocumentAIService:
    provider_name = "base"

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        raise NotImplementedError


class LocalDocumentAIService(DocumentAIService):
    """Production-safe local baseline for AI-style document understanding.

    It combines OCR text, image-quality signals, layout-aware receipt fields, and
    classification/category scoring. A stronger multimodal model can replace or
    augment this service without changing the processor or API routes.
    """

    provider_name = "heuristic_fallback"

    def __init__(self) -> None:
        self.parser = DocumentParser()

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        lines = self._clean_lines(raw_text)
        text = "\n".join(lines)
        quality_notes, image_quality = self._image_quality(image_path)
        document_type, type_confidence = self._classify(text, filename, parsed.document_type)
        subtotal = self._amount_near_label(lines, ["subtotal", "sub total"])
        tax = self._amount_near_label(lines, ["tax", "sales tax", "hst", "gst", "vat"])
        total = self._amount_near_label(lines, ["grand total", "total", "amount due", "balance"])
        if total is None and document_type == DocumentType.receipt:
            total = parsed.extracted_amount or self._largest_amount(text)

        category = self._infer_category(text, document_type) or self._normalize_category(parsed.category)
        title = self._title(lines, document_type, parsed, filename)
        confidence = self._confidence(type_confidence, image_quality, raw_text, total, document_type)
        notes = quality_notes + self._field_notes(document_type, total, parsed.extracted_date or self.parser._extract_date(text), lines)
        review_required = confidence < Decimal("0.62") or bool(notes)
        tags = self._tags(text, category, document_type, parsed.tags)

        field_sources = {
            "document_type": self.provider_name,
            "title": self.provider_name,
            "merchant_name": self.provider_name,
            "extracted_date": "ocr_parser",
            "extracted_amount": self.provider_name,
            "subtotal": self.provider_name,
            "tax": self.provider_name,
            "category": self.provider_name,
            "summary": self.provider_name,
        }
        return AIDocumentUnderstandingResult(
            document_type=document_type,
            title=title,
            merchant_name=self._merchant(lines, parsed) if document_type == DocumentType.receipt else parsed.merchant_name,
            extracted_date=parsed.extracted_date or self.parser._extract_date(text),
            extracted_amount=total,
            subtotal=subtotal,
            tax=tax,
            currency="USD" if any(value is not None for value in [total, subtotal, tax]) else parsed.currency,
            category=category,
            tags=tags,
            summary=self._summary(lines, document_type),
            cleaned_raw_text=text or raw_text,
            confidence_score=confidence,
            extraction_notes=notes,
            review_required=review_required,
            provider=self.provider_name,
            extraction_provider=self.provider_name,
            provider_chain=[self.provider_name],
            field_sources=field_sources,
        )

    def _clean_lines(self, raw_text: str) -> list[str]:
        lines = []
        for line in raw_text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned:
                lines.append(cleaned)
        return lines

    def _image_quality(self, image_path: Path) -> tuple[list[str], Decimal]:
        notes: list[str] = []
        try:
            with Image.open(image_path) as image:
                grayscale = image.convert("L")
                width, height = image.size
                brightness = ImageStat.Stat(grayscale).mean[0]
                edge_strength = ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES)).mean[0]
        except Exception:
            return ["Image quality could not be evaluated."], Decimal("0.55")

        score = Decimal("0.86")
        if width < 700 or height < 700:
            notes.append("Image resolution is low; field extraction may be incomplete.")
            score -= Decimal("0.15")
        if brightness < 50:
            notes.append("Image is dark; review OCR and extracted fields.")
            score -= Decimal("0.12")
        if edge_strength < 3:
            notes.append("Image appears soft or low contrast; manual review is recommended.")
            score -= Decimal("0.14")
        return notes, max(Decimal("0.25"), min(Decimal("0.95"), score))

    def _classify(self, text: str, filename: str, fallback: DocumentType) -> tuple[DocumentType, Decimal]:
        haystack = f"{filename}\n{text}".lower()
        scores = {
            DocumentType.receipt: self._score(haystack, ["receipt", "subtotal", "tax", "total", "change", "visa", "mastercard", "cashier"]),
            DocumentType.notice: self._score(haystack, ["notice", "announcement", "effective date", "deadline", "meeting", "reminder"]),
            DocumentType.memo: self._score(haystack, ["memo", "note", "minutes", "action item", "todo"]),
            DocumentType.document: self._score(haystack, ["invoice", "statement", "agreement", "policy", "form", "reference"]),
            DocumentType.other: 1,
        }
        winner, score = max(scores.items(), key=lambda item: item[1])
        if score < 3 and fallback != DocumentType.other:
            return fallback, Decimal("0.58")
        confidence = Decimal(str(min(0.93, 0.45 + (score * 0.08))))
        return winner, confidence

    def _score(self, haystack: str, keywords: list[str]) -> int:
        return sum(2 if keyword in haystack else 0 for keyword in keywords)

    def _amount_near_label(self, lines: list[str], labels: list[str]) -> Decimal | None:
        for line in lines:
            if any(self._has_label(line, label) for label in labels):
                amount = self._last_amount(line)
                if amount is not None:
                    return amount
        return None

    def _has_label(self, line: str, label: str) -> bool:
        escaped = re.escape(label).replace("\\ ", r"\s+")
        return re.search(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])", line, flags=re.IGNORECASE) is not None

    def _last_amount(self, text: str) -> Decimal | None:
        matches = re.findall(r"(?:USD|US\$|\$)?\s*([0-9]{1,6}(?:,[0-9]{3})*(?:\.[0-9]{2}))", text, flags=re.IGNORECASE)
        return self._to_decimal(matches[-1]) if matches else None

    def _largest_amount(self, text: str) -> Decimal | None:
        amounts = [value for value in (self._to_decimal(match) for match in re.findall(r"([0-9]{1,6}(?:,[0-9]{3})*\.[0-9]{2})", text)) if value is not None]
        return max(amounts) if amounts else None

    def _to_decimal(self, value: str | None) -> Decimal | None:
        if not value:
            return None
        try:
            return Decimal(value.replace(",", "")).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None

    def _infer_category(self, text: str, document_type: DocumentType) -> str | None:
        lowered = text.lower()
        best_category = None
        best_score = 0
        for category, keywords in CATEGORY_MAP.items():
            score = sum(2 if keyword in lowered else 0 for keyword in keywords)
            if score > best_score:
                best_category = category
                best_score = score
        if best_category:
            return best_category
        if document_type == DocumentType.receipt:
            return "retail"
        if document_type == DocumentType.notice:
            return "notice"
        return "other"

    def _normalize_category(self, category: str | None) -> str | None:
        if not category:
            return None
        return {
            "dining": "food_drink",
            "transportation": "transport",
            "groceries": "groceries",
            "utilities": "utilities",
            "office": "office",
            "health": "health",
        }.get(category, category)

    def _title(self, lines: list[str], document_type: DocumentType, parsed: ParsedDocument, filename: str) -> str:
        if document_type == DocumentType.receipt:
            merchant = self._merchant(lines, parsed)
            return f"{merchant} receipt" if merchant else "Receipt"
        return parsed.title or (lines[0][:120] if lines else filename.rsplit(".", 1)[0])

    def _merchant(self, lines: list[str], parsed: ParsedDocument) -> str | None:
        if parsed.merchant_name:
            return parsed.merchant_name
        for line in lines[:7]:
            cleaned = re.sub(r"[^A-Za-z0-9 &'.,-]", "", line).strip(" ,-")
            if len(cleaned) >= 3 and not re.search(r"\b(receipt|invoice|date|cashier|total|subtotal|tax)\b", cleaned, re.IGNORECASE):
                return cleaned[:120]
        return None

    def _summary(self, lines: list[str], document_type: DocumentType) -> str | None:
        if not lines:
            return None
        if document_type == DocumentType.receipt:
            return "Receipt with merchant, date, totals, and tax fields extracted when visible."
        body = " ".join(lines[:8])
        return body[:500]

    def _field_notes(self, document_type: DocumentType, total: Decimal | None, extracted_date: date | None, lines: list[str]) -> list[str]:
        notes: list[str] = []
        if document_type == DocumentType.receipt and total is None:
            notes.append("No clear receipt total was found.")
        if extracted_date is None:
            notes.append("No reliable date was found.")
        if len(lines) < 3:
            notes.append("Very little text was detected.")
        return notes

    def _confidence(
        self,
        type_confidence: Decimal,
        image_quality: Decimal,
        raw_text: str,
        total: Decimal | None,
        document_type: DocumentType,
    ) -> Decimal:
        score = (type_confidence * Decimal("0.45")) + (image_quality * Decimal("0.35"))
        score += Decimal("0.12") if len(raw_text.strip()) > 80 else Decimal("0.03")
        if document_type != DocumentType.receipt or total is not None:
            score += Decimal("0.08")
        return max(Decimal("0.20"), min(Decimal("0.97"), score)).quantize(Decimal("0.001"))

    def _tags(self, text: str, category: str | None, document_type: DocumentType, fallback_tags: list[str]) -> list[str]:
        category_names = set(CATEGORY_MAP) | {"notice", "other"}
        tags = {tag for tag in fallback_tags if tag not in category_names}
        tags.add(document_type.value)
        if category:
            tags.add(category)
        if re.search(r"\b(due|deadline|expires|effective|urgent)\b", text, re.IGNORECASE):
            tags.add("review")
        return sorted(tags)


class OpenAIVisionDocumentAIService(DocumentAIService):
    """Optional legacy multimodal provider. Kept for extension, not used by the default open-source chain."""

    provider_name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI package is not installed.") from exc
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.local_fallback = LocalDocumentAIService()

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        try:
            payload = self._call_model(image_path, raw_text, filename)
            result = self._normalize(payload, parsed, raw_text)
            result.provider = self.provider_name
            result.extraction_provider = self.provider_name
            result.provider_chain = [self.provider_name]
            return result
        except Exception as exc:
            fallback = self.local_fallback.analyze(image_path, raw_text, parsed, filename)
            fallback.extraction_notes.append(f"Vision AI provider failed; used local extraction fallback: {exc}")
            fallback.review_required = True
            return fallback

    def _call_model(self, image_path: Path, raw_text: str, filename: str) -> dict[str, Any]:
        image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        prompt = (
            "Analyze this document image directly. Return only JSON with: document_type, title, "
            "merchant_name, extracted_date as YYYY-MM-DD or null, extracted_amount, subtotal, tax, "
            "currency, category, tags, summary, cleaned_raw_text, confidence_score between 0 and 1, "
            "review_required, and extraction_notes. Supported document_type values are receipt, "
            "notice, document, memo, other. Prefer categories like food_drink, transport, education, "
            "utilities, retail, groceries, health, office, notice, other. OCR text is supplied only "
            f"as auxiliary context. Filename: {filename}. OCR text:\n{raw_text[:6000]}"
        )
        response = self.client.chat.completions.create(
            model=self.settings.ai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _normalize(self, payload: dict[str, Any], parsed: ParsedDocument, raw_text: str) -> AIDocumentUnderstandingResult:
        doc_type_value = payload.get("document_type") or parsed.document_type.value
        try:
            doc_type = DocumentType(doc_type_value)
        except ValueError:
            doc_type = parsed.document_type

        return AIDocumentUnderstandingResult(
            document_type=doc_type,
            title=payload.get("title") or parsed.title,
            merchant_name=payload.get("merchant_name") or parsed.merchant_name,
            extracted_date=self._parse_date(payload.get("extracted_date")) or parsed.extracted_date,
            extracted_amount=self._decimal(payload.get("extracted_amount")) or parsed.extracted_amount,
            subtotal=self._decimal(payload.get("subtotal")),
            tax=self._decimal(payload.get("tax")),
            currency=payload.get("currency") or parsed.currency,
            category=payload.get("category") or parsed.category,
            tags=[str(tag) for tag in payload.get("tags", [])] or parsed.tags,
            summary=payload.get("summary"),
            cleaned_raw_text=payload.get("cleaned_raw_text") or raw_text,
            confidence_score=self._decimal(payload.get("confidence_score")),
            extraction_notes=[str(note) for note in payload.get("extraction_notes", [])],
            review_required=bool(payload.get("review_required", False)),
            provider=self.provider_name,
            extraction_provider=self.provider_name,
            provider_chain=[self.provider_name],
        )

    def _decimal(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value)).quantize(Decimal("0.001"))
        except (InvalidOperation, ValueError):
            return None

    def _parse_date(self, value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


class PaddleOCRVLDocumentAIService(DocumentAIService):
    provider_name = "paddleocr_vl"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_normalizer = LocalDocumentAIService()
        try:
            from paddleocr import PaddleOCRVL
        except Exception as exc:
            raise RuntimeError(
                "PaddleOCR-VL runtime is not installed. Install backend/requirements-ai.txt "
                "and configure PaddleOCR-VL model directories."
            ) from exc

        kwargs: dict[str, Any] = {
            "pipeline_version": "v1.5",
            "device": self.settings.paddleocr_vl_device,
            "engine": self.settings.paddleocr_vl_engine,
        }
        if self.settings.paddleocr_vl_model_dir:
            kwargs["vl_rec_model_dir"] = str(self.settings.paddleocr_vl_model_dir)
        if self.settings.paddleocr_vl_layout_model_dir:
            kwargs["layout_detection_model_dir"] = str(self.settings.paddleocr_vl_layout_model_dir)
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        self.pipeline = PaddleOCRVL(**kwargs)

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        try:
            output = self.pipeline.predict(str(image_path))
            provider_text = self._extract_text(output)
            merged_text = "\n".join(part for part in [provider_text, raw_text] if part.strip())
            provider_parsed = DocumentParser().parse(merged_text or raw_text, filename)
            result = self.local_normalizer.analyze(image_path, merged_text or raw_text, provider_parsed, filename)
            result.provider = self.provider_name
            result.extraction_provider = self.provider_name
            result.provider_chain = [self.provider_name]
            result.merge_strategy = "paddleocr_vl_structured_output_normalized"
            result.field_sources.update({key: self.provider_name for key in result.field_sources})
            result.extraction_notes.append("PaddleOCR-VL primary extraction completed.")
            if provider_text:
                result.cleaned_raw_text = provider_text
            return result
        except Exception as exc:
            raise RuntimeError(f"PaddleOCR-VL inference failed: {exc}") from exc

    def _extract_text(self, output: Any) -> str:
        fragments: list[str] = []
        for item in output or []:
            json_payload = getattr(item, "json", None)
            markdown_payload = getattr(item, "markdown", None)
            if isinstance(markdown_payload, dict):
                texts = markdown_payload.get("markdown_texts")
                if isinstance(texts, list):
                    fragments.extend(str(text) for text in texts)
                elif isinstance(texts, str):
                    fragments.append(texts)
            self._walk_json(json_payload, fragments)
        return "\n".join(fragment.strip() for fragment in fragments if fragment and fragment.strip())

    def _walk_json(self, value: Any, fragments: list[str]) -> None:
        if isinstance(value, dict):
            for key in ["block_content", "rec_text", "text", "content"]:
                content = value.get(key)
                if isinstance(content, str):
                    fragments.append(content)
            for nested in value.values():
                self._walk_json(nested, fragments)
        elif isinstance(value, list):
            for nested in value:
                self._walk_json(nested, fragments)


class Qwen25VLDocumentAIService(DocumentAIService):
    provider_name = "qwen2_5_vl"

    def __init__(self) -> None:
        self.settings = get_settings()
        try:
            import torch
            from qwen_vl_utils import process_vision_info
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        except Exception as exc:
            raise RuntimeError(
                "Qwen2.5-VL runtime is not installed. Install backend/requirements-ai.txt "
                "and download Qwen2.5-VL weights."
            ) from exc

        self.torch = torch
        self.process_vision_info = process_vision_info
        model_ref = str(self.settings.qwen2_5_vl_model_dir or self.settings.qwen2_5_vl_model_name)
        device_map = "auto" if self.settings.qwen2_5_vl_device == "auto" else {"": self.settings.qwen2_5_vl_device}
        self.processor = AutoProcessor.from_pretrained(model_ref, min_pixels=256 * 28 * 28, max_pixels=1024 * 28 * 28)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_ref,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map=device_map,
        )

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        prompt = self._prompt(raw_text, parsed, filename)
        messages = [{"role": "user", "content": [{"type": "image", "image": str(image_path)}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = self.process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(self.model.device)
        generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids, strict=False)
        ]
        output_text = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        payload = self._extract_json(output_text)
        result = OpenAIVisionDocumentAIService._normalize(self, payload, parsed, raw_text)
        result.provider = self.provider_name
        result.extraction_provider = self.provider_name
        result.provider_chain = [self.provider_name]
        result.extraction_notes.append("Qwen2.5-VL refinement completed.")
        return result

    def _prompt(self, raw_text: str, parsed: ParsedDocument, filename: str) -> str:
        return (
            "Refine this document extraction. Return only JSON with keys: document_type, title, "
            "merchant_name, extracted_date, extracted_amount, subtotal, tax, currency, category, "
            "tags, summary, cleaned_raw_text, confidence_score, review_required, extraction_notes. "
            "Use document_type receipt, notice, document, memo, or other. Fill missing fields only "
            "when visible or strongly supported. "
            f"Filename: {filename}. Prior parser type: {parsed.document_type.value}. OCR text:\n{raw_text[:6000]}"
        )

    def _extract_json(self, output_text: str) -> dict[str, Any]:
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", output_text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def _decimal(self, value: Any) -> Decimal | None:
        return OpenAIVisionDocumentAIService._decimal(self, value)

    def _parse_date(self, value: Any) -> date | None:
        return OpenAIVisionDocumentAIService._parse_date(self, value)


class HybridOpenSourceDocumentAIService(DocumentAIService):
    provider_name = "hybrid_open_source"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_fallback = LocalDocumentAIService()

    def analyze(
        self,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str = "",
    ) -> AIDocumentUnderstandingResult:
        notes: list[str] = []
        primary = self._run_provider(self.settings.ai_primary_provider, image_path, raw_text, parsed, filename, notes)
        if primary is None:
            primary = self.local_fallback.analyze(image_path, raw_text, parsed, filename)
            primary.extraction_notes.extend(notes)
            primary.provider_chain = [self.settings.ai_primary_provider + "_unavailable", "heuristic_fallback"]
            primary.merge_strategy = "primary_unavailable_heuristic_fallback"

        final = primary
        should_refine, reasons = self._should_refine(primary)
        if self.settings.ai_enable_second_pass and should_refine:
            secondary = self._run_provider(self.settings.ai_secondary_provider, image_path, raw_text, parsed, filename, notes)
            if secondary:
                final = self._merge(primary, secondary, reasons)
            else:
                final.extraction_notes.extend(notes)
                final.provider_chain = self._dedupe(final.provider_chain + [self.settings.ai_secondary_provider + "_unavailable"])
        else:
            final.extraction_notes.extend(reasons)

        if not final.provider_chain:
            final.provider_chain = [final.provider or final.extraction_provider or "unknown"]
        final.extraction_provider = final.extraction_provider or final.provider_chain[0]
        final.refinement_provider = final.refinement_provider
        final.review_required = final.review_required or self._requires_review(final)
        return final

    def _run_provider(
        self,
        provider_name: str,
        image_path: Path,
        raw_text: str,
        parsed: ParsedDocument,
        filename: str,
        notes: list[str],
    ) -> AIDocumentUnderstandingResult | None:
        try:
            provider = self._provider(provider_name)
            return provider.analyze(image_path, raw_text, parsed, filename)
        except Exception as exc:
            notes.append(f"{provider_name} unavailable or failed: {exc}")
            return None

    def _provider(self, provider_name: str) -> DocumentAIService:
        normalized = provider_name.lower()
        if normalized == "paddleocr_vl":
            return PaddleOCRVLDocumentAIService()
        if normalized == "qwen2_5_vl":
            return Qwen25VLDocumentAIService()
        if normalized in {"heuristic", "heuristic_fallback", "local"}:
            return self.local_fallback
        if normalized == "openai":
            return OpenAIVisionDocumentAIService()
        raise ValueError(f"Unsupported AI provider: {provider_name}")

    def _should_refine(self, result: AIDocumentUnderstandingResult) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        threshold = Decimal(str(self.settings.ai_second_pass_confidence_threshold))
        confidence = result.confidence_score or Decimal("0")
        if confidence < threshold:
            reasons.append(f"Primary confidence {confidence} is below second-pass threshold {threshold}.")
        if result.document_type == DocumentType.receipt:
            if result.extracted_amount is None:
                reasons.append("Receipt total is missing.")
            if result.extracted_date is None:
                reasons.append("Receipt date is missing.")
            if not result.merchant_name:
                reasons.append("Receipt merchant is missing.")
        elif result.document_type in {DocumentType.notice, DocumentType.document, DocumentType.memo}:
            if not result.title:
                reasons.append("Document title is missing.")
            if not result.summary:
                reasons.append("Document summary is missing.")
        if not result.category or result.category == "other":
            reasons.append("Category is missing or weak.")
        if result.review_required:
            reasons.append("Primary extraction requested manual review.")
        if any("unavailable" in provider for provider in result.provider_chain):
            reasons.append("Configured primary provider was unavailable; second-pass fallback is warranted.")
        return bool(reasons), reasons

    def _requires_review(self, result: AIDocumentUnderstandingResult) -> bool:
        should_refine, _ = self._should_refine(result)
        return should_refine

    def _merge(
        self,
        primary: AIDocumentUnderstandingResult,
        secondary: AIDocumentUnderstandingResult,
        reasons: list[str],
    ) -> AIDocumentUnderstandingResult:
        merged = primary
        merged.provider_chain = self._dedupe(primary.provider_chain + secondary.provider_chain)
        merged.refinement_provider = secondary.extraction_provider or secondary.provider
        merged.merge_strategy = "primary_authoritative_secondary_fill_missing"
        merged.extraction_notes.extend(f"Second pass triggered: {reason}" for reason in reasons)
        merged.extraction_notes.extend(secondary.extraction_notes)

        for field_name in [
            "title",
            "merchant_name",
            "extracted_date",
            "extracted_amount",
            "subtotal",
            "tax",
            "currency",
            "category",
            "summary",
            "cleaned_raw_text",
        ]:
            primary_value = getattr(merged, field_name)
            secondary_value = getattr(secondary, field_name)
            if self._is_empty(primary_value) and not self._is_empty(secondary_value):
                setattr(merged, field_name, secondary_value)
                merged.field_sources[field_name] = secondary.extraction_provider or secondary.provider

        if (secondary.confidence_score or Decimal("0")) > (merged.confidence_score or Decimal("0")):
            merged.confidence_score = secondary.confidence_score
        if len(secondary.tags) > len(merged.tags):
            merged.tags = sorted(set(merged.tags) | set(secondary.tags))
        merged.review_required = self._requires_review(merged)
        return merged

    def _is_empty(self, value: Any) -> bool:
        return value is None or value == "" or value == []

    def _dedupe(self, providers: list[str]) -> list[str]:
        return list(dict.fromkeys(provider for provider in providers if provider))


def get_document_ai_service() -> DocumentAIService:
    return HybridOpenSourceDocumentAIService()
