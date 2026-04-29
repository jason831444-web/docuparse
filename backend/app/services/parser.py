import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from rapidfuzz import fuzz

from app.models.document import DocumentType


DATE_PATTERNS = [
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
    "%b %d, %Y",
    "%B %d, %Y",
]

CATEGORY_KEYWORDS = {
    "profile_record": ["name:", "id:", "student id", "major:", "age:", "department:", "dob:"],
    "invoice": ["invoice", "invoice number", "vendor", "bill to", "invoice date", "due date", "amount due", "total due"],
    "course_guide": ["syllabus", "course code", "office hours", "grading", "required materials", "instructor"],
    "presentation_guide": ["presentation guide", "speaker notes", "talk track", "slide guidance", "rehearse"],
    "repair_service": ["repair", "service work", "labor", "parts", "maintenance", "technician", "brake"],
    "groceries": ["grocery", "market", "foods", "supermarket", "trader", "whole foods"],
    "dining": ["restaurant", "cafe", "coffee", "pizza", "burger", "bar", "bakery"],
    "transportation": ["gas", "fuel", "uber", "lyft", "parking", "metro", "taxi"],
    "utilities": ["electric", "water", "internet", "phone", "utility", "bill"],
    "health": ["pharmacy", "clinic", "doctor", "medical", "dentist"],
    "office": ["office", "stationery", "printing", "supplies"],
    "notice": ["notice", "announcement", "meeting", "deadline", "reminder"],
}


@dataclass
class ParsedDocument:
    document_type: DocumentType = DocumentType.other
    title: str | None = None
    extracted_date: date | None = None
    extracted_amount: Decimal | None = None
    currency: str | None = None
    merchant_name: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)


class DocumentParser:
    """Heuristic parser. This is the extension point for an LLM or trained extractor later."""

    def parse(self, raw_text: str, filename: str = "") -> ParsedDocument:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        joined = "\n".join(lines)
        doc_type = self._guess_document_type(joined, filename)
        amount = self._extract_amount(joined) if doc_type == DocumentType.receipt else None
        category = self._guess_category(joined)
        return ParsedDocument(
            document_type=doc_type,
            title=self._guess_title(lines, doc_type, filename),
            extracted_date=self._extract_date(joined),
            extracted_amount=amount,
            currency="USD" if amount is not None else None,
            merchant_name=self._guess_merchant(lines) if doc_type == DocumentType.receipt else None,
            category=category,
            tags=self._guess_tags(joined, category, doc_type),
        )

    def _guess_document_type(self, text: str, filename: str) -> DocumentType:
        haystack = f"{filename}\n{text}".lower()
        receipt_score = sum(keyword in haystack for keyword in ["receipt", "subtotal", "total", "tax", "change", "visa"])
        invoice_score = sum(keyword in haystack for keyword in ["invoice", "invoice number", "invoice #", "vendor", "bill to", "amount due", "total due"])
        presentation_score = sum(keyword in haystack for keyword in ["presentation", "slide", "speaker notes", "speaking notes", "talk track", "rehearse", "script"])
        notice_score = sum(keyword in haystack for keyword in ["notice", "announcement", "effective date", "deadline", "meeting"])
        memo_score = sum(keyword in haystack for keyword in ["memo", "note", "reminder", "todo"])
        if invoice_score >= 2:
            return DocumentType.document
        if presentation_score >= 2:
            return DocumentType.presentation
        if receipt_score >= 2:
            return DocumentType.receipt
        if notice_score >= 1:
            return DocumentType.notice
        if memo_score >= 1:
            return DocumentType.memo
        return DocumentType.document if len(text) > 250 else DocumentType.other

    def _extract_date(self, text: str) -> date | None:
        candidates = re.findall(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|[A-Z][a-z]+ \d{1,2}, \d{4})\b", text)
        for candidate in candidates:
            normalized = candidate.replace("-", "/") if re.match(r"\d{1,2}-\d{1,2}-", candidate) else candidate
            for pattern in DATE_PATTERNS:
                try:
                    return datetime.strptime(normalized, pattern).date()
                except ValueError:
                    continue
        return None

    def _extract_amount(self, text: str) -> Decimal | None:
        priority_lines = [
            line for line in text.splitlines()
            if re.search(r"\b(total|amount due|balance|grand total)\b", line, flags=re.IGNORECASE)
        ]
        for line in priority_lines + [text]:
            matches = re.findall(r"(?:USD|\$)?\s*([0-9]{1,6}(?:,[0-9]{3})*(?:\.[0-9]{2}))", line)
            if matches:
                return max(Decimal(value.replace(",", "")) for value in matches)
        return None

    def _guess_title(self, lines: list[str], doc_type: DocumentType, filename: str) -> str:
        text = "\n".join(lines)
        if doc_type == DocumentType.receipt:
            merchant = self._guess_merchant(lines)
            return f"{merchant} receipt" if merchant else "Receipt"
        if self._looks_like_profile_record(text):
            return self._profile_title(text) or "Profile Note"
        candidates: list[tuple[int, str]] = []
        for index, line in enumerate(lines[:12]):
            cleaned = re.sub(r"\s+", " ", line).strip(":- ")
            if not cleaned:
                continue
            score = self._score_title_candidate(cleaned, index=index, text=text)
            if score > 0:
                candidates.append((score, cleaned))
        if candidates:
            candidates.sort(key=lambda item: (-item[0], len(item[1])))
            return candidates[0][1]
        return filename.rsplit(".", 1)[0] if filename else "Untitled document"

    def _score_title_candidate(self, value: str, index: int, text: str) -> int:
        lowered = value.lower()
        if self._is_placeholder_title(value):
            return -100
        if len(value) < 4 or len(value) > 120:
            return -40
        if re.search(r"^\d+([./-]\d+)*$", value):
            return -40

        score = 30 - (index * 2)
        if re.search(r"\b[A-Z]{2,5}[- ]?\d{3,4}[A-Z]?\b", value):
            score += 30
        if any(keyword in lowered for keyword in ["syllabus", "course guide", "presentation", "speaker", "resume", "profile", "guide", "invoice", "statement", "bill"]):
            score += 20
        if re.match(r"^[A-Z][A-Za-z0-9&,'./() -]{4,}$", value):
            score += 10
        if ":" in value:
            score -= 8
        if re.match(r"^(course description|overview|summary|introduction|objectives?)\s*:", lowered):
            score -= 30
        if re.match(r"^(this|these|students|you will|in this course|the purpose of)\b", lowered):
            score -= 35
        if len(value.split()) > 12:
            score -= 18
        if value.endswith("."):
            score -= 14
        if self._looks_like_sentence(value):
            score -= 22
        if text and value.lower() == text.splitlines()[0].strip().lower() and self._looks_like_sentence(value):
            score -= 8
        return score

    def _looks_like_sentence(self, value: str) -> bool:
        lowered = value.lower().strip()
        return (
            len(lowered.split()) >= 8
            and bool(re.search(r"\b(is|are|will|introduces|provides|covers|describes|contains)\b", lowered))
        )

    def _guess_merchant(self, lines: list[str]) -> str | None:
        for line in lines[:6]:
            cleaned = self._clean_merchant_candidate(line)
            if len(cleaned) >= 3 and not re.search(r"\b(total|receipt|date|cashier|invoice)\b", cleaned, re.IGNORECASE):
                return cleaned[:120]
        return None

    def _clean_merchant_candidate(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 &'.:/,-]", " ", value)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-/|")
        cleaned = re.sub(r"\s*[-/|]\s*(?:work\s+order|service\s+receipt|receipt|invoice|statement)\b.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:work\s+order|service\s+receipt|receipt|invoice|statement)\b.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" .,:;-/|")
        if re.match(r"^(?:acct|account|ticket|customer|date|bike|invoice\s+(?:number|#)|vendor|bill to)\b", cleaned, flags=re.IGNORECASE):
            return ""
        return cleaned

    def _profile_title(self, text: str) -> str | None:
        match = re.search(r"^name\s*:\s*([A-Za-z][A-Za-z .'-]{1,80})$", text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return f"{match.group(1).strip()} Profile"
        return None

    def _guess_category(self, text: str) -> str | None:
        lowered = text.lower()
        if self._looks_like_profile_record(text):
            return "profile_record"
        if self._looks_like_syllabus(text):
            return "course_guide"
        if self._looks_like_presentation_guide(text):
            return "presentation_guide"
        best: tuple[str | None, int] = (None, 0)
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(100 for keyword in keywords if keyword in lowered)
            score += max((fuzz.partial_ratio(keyword, lowered) for keyword in keywords), default=0)
            if score > best[1]:
                best = (category, score)
        return best[0] if best[1] >= 80 else None

    def _guess_tags(self, text: str, category: str | None, doc_type: DocumentType) -> list[str]:
        tags = {doc_type.value}
        if category:
            tags.add(category)
        if category == "presentation_guide":
            tags.add("presentation_guide")
            lowered = text.lower()
            if "script" in lowered:
                tags.add("script")
            if any(term in lowered for term in ["speaking notes", "speaker notes", "talk track"]):
                tags.add("speaking_notes")
        if re.search(r"\b(deadline|due|expires|effective)\b", text, flags=re.IGNORECASE):
            tags.add("time-sensitive")
        return sorted(tags)

    def _is_placeholder_title(self, value: str) -> bool:
        lowered = value.lower()
        return bool(
            re.fullmatch(r"(page|slide)\s+\d+", lowered)
            or lowered in {"page", "slide", "table of contents", "contents"}
        )

    def _looks_like_profile_record(self, text: str) -> bool:
        lowered = text.lower()
        signals = ["name:", "id:", "student id", "major:", "age:", "department:", "dob:"]
        return sum(signal in lowered for signal in signals) >= 2

    def _looks_like_syllabus(self, text: str) -> bool:
        lowered = text.lower()
        signals = ["syllabus", "course code", "semester", "instructor", "office hours", "grading", "required materials"]
        return sum(signal in lowered for signal in signals) >= 2

    def _looks_like_presentation_guide(self, text: str) -> bool:
        lowered = text.lower()
        signals = ["presentation", "slide", "audience", "speaker", "rehearse", "talk track", "speaking notes"]
        return sum(signal in lowered for signal in signals) >= 2
