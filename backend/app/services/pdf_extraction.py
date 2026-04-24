from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.ocr import OCRService


@dataclass
class PdfExtractionResult:
    text: str = ""
    blocks: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    rendered_page_images: list[Path] = field(default_factory=list)
    ocr_confidence: float | None = None
    extraction_method: str = "pdf_text_extract"


class PdfExtractionService:
    def __init__(self, ocr: OCRService | None = None) -> None:
        self.ocr = ocr or OCRService()
        self.settings = get_settings()

    def extract(self, path: Path) -> PdfExtractionResult:
        result = PdfExtractionResult()
        text, page_count, warnings = self._extract_text(path)
        result.warnings.extend(warnings)
        result.metadata["page_count"] = page_count

        if len(text.strip()) >= 80:
            result.text = text
            result.blocks = [{"type": "pdf_text", "content": text[:20000]}]
            return result

        result.warnings.append("PDF text layer was sparse; OCR was attempted on rendered pages.")
        rendered = self._render_pages(path, max_pages=self.settings.pdf_ocr_max_pages)
        result.rendered_page_images = rendered
        if not rendered:
            result.text = text
            result.extraction_method = "pdf_partial_text_extract"
            result.warnings.append("PDF pages could not be rendered for OCR in this environment.")
            return result

        ocr_texts = []
        confidences = []
        for index, image_path in enumerate(rendered, start=1):
            page_text, confidence = self.ocr.extract_text(image_path)
            confidences.append(confidence)
            if page_text.strip():
                ocr_texts.append(f"Page {index}\n{page_text.strip()}")
        result.text = "\n\n".join(ocr_texts).strip()
        result.blocks = [{"type": "pdf_page_ocr", "page": index + 1, "image_path": str(image), "content": ocr_texts[index] if index < len(ocr_texts) else ""} for index, image in enumerate(rendered)]
        result.ocr_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        result.extraction_method = "pdf_scanned_page_ocr"
        if page_count and len(rendered) < page_count:
            result.warnings.append(f"OCR was limited to the first {len(rendered)} of {page_count} PDF pages.")
        if not result.text:
            result.warnings.append("No readable text was extracted from the scanned PDF.")
        return result

    def _extract_text(self, path: Path) -> tuple[str, int | None, list[str]]:
        warnings: list[str] = []
        try:
            from pypdf import PdfReader
        except Exception as exc:
            return "", None, [f"PDF text extraction dependency is unavailable: {exc}."]

        try:
            reader = PdfReader(str(path))
            page_texts = []
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    page_texts.append(f"Page {index}\n{text.strip()}")
            return "\n\n".join(page_texts), len(reader.pages), warnings
        except Exception as exc:
            return "", None, [f"PDF text extraction failed: {exc}."]

    def _render_pages(self, path: Path, max_pages: int) -> list[Path]:
        try:
            import fitz
        except Exception:
            return []

        output_dir = self.settings.upload_dir / "rendered_pages"
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered: list[Path] = []
        try:
            document = fitz.open(path)
            for page_index in range(min(len(document), max_pages)):
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                output_path = output_dir / f"{path.stem}-page-{page_index + 1}.png"
                pixmap.save(output_path)
                rendered.append(output_path)
            document.close()
        except Exception:
            return rendered
        return rendered
