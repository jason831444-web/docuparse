from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.document import Document, ProcessingStatus
from app.services.ai_document_understanding import get_document_ai_service
from app.services.document_processor import DocumentProcessor
from scripts.generate_eval_corpus import generate_corpus, load_spec


DEFAULT_SPEC = ROOT / "eval" / "specs" / "eval_documents.json"
DEFAULT_CORPUS = ROOT / "eval" / "corpus"
DEFAULT_REPORTS = ROOT / "eval" / "reports"


@dataclass
class EvalIssue:
    severity: str
    code: str
    message: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DocuParse quality evaluation on a representative corpus.")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--label", default="manual")
    parser.add_argument("--compare-to", type=Path, default=None)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec(args.spec)
    generate_corpus(args.spec, args.corpus_dir)

    processor = DocumentProcessor()
    results = []
    for item in spec["documents"]:
        path = args.corpus_dir / item["filename"]
        results.append(evaluate_document(processor, item, path))

    report = build_report(spec, results, args.label)
    if args.compare_to:
        report["comparison"] = compare_reports(args.compare_to, report)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = args.output_dir / f"{timestamp}-{args.label}.json"
    md_path = args.output_dir / f"{timestamp}-{args.label}.md"
    latest_path = args.output_dir / "latest.json"
    latest_md_path = args.output_dir / "latest.md"
    json_path.write_text(json.dumps(report, indent=2, default=json_safe), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    latest_path.write_text(json.dumps(report, indent=2, default=json_safe), encoding="utf-8")
    latest_md_path.write_text(render_markdown_report(report), encoding="utf-8")
    print(f"Wrote JSON report: {json_path}")
    print(f"Wrote Markdown report: {md_path}")
    print(render_terminal_summary(report))


def evaluate_document(processor: DocumentProcessor, item: dict[str, Any], path: Path) -> dict[str, Any]:
    document = Document(
        original_filename=item["filename"],
        stored_file_path=str(path),
        mime_type=item.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        tags=[],
        action_items=[],
        warnings=[],
        key_dates=[],
        processing_status=ProcessingStatus.uploaded,
    )
    actual: dict[str, Any] = {}
    issues: list[EvalIssue] = []

    try:
        normalized = processor.ingestion.ingest(path, document.original_filename, document.mime_type)
        raw_text = normalized.normalized_text
        parsed = processor.parser.parse(raw_text, document.original_filename)
        extraction_quality = processor.quality.evaluate_extraction(normalized, parsed)
        route = processor.router.route(normalized, parsed, extraction_quality)
        analysis_path = normalized.primary_image_path or path
        if route.heavy_ai_required and normalized.primary_image_path:
            ai_result = get_document_ai_service().analyze(analysis_path, raw_text, parsed, document.original_filename)
        else:
            ai_result = processor.lightweight_ai.analyze(analysis_path, raw_text, parsed, document.original_filename)
            ai_result.extraction_provider = normalized.extraction_method or route.route_label
            ai_result.provider = ai_result.extraction_provider
            ai_result.provider_chain = [normalized.extraction_method or route.route_label, "heuristic_fallback"]
            ai_result.merge_strategy = route.route_label
        structured_quality = processor.quality.evaluate_structured_result(document, ai_result, extraction_quality)
        ingestion_notes = processor._ingestion_notes(normalized, route)

        document.raw_text = raw_text
        document.mime_type = normalized.mime_type or document.mime_type
        document.source_file_type = normalized.source_file_type
        document.extraction_method = normalized.extraction_method
        document.ingestion_metadata = processor._ingestion_metadata(normalized, route, extraction_quality, structured_quality)
        document.confidence_score = ai_result.confidence_score or processor._confidence(normalized)
        document.ai_document_type = ai_result.document_type
        document.ai_confidence_score = ai_result.confidence_score
        quality_notes = processor._quality_notes(extraction_quality, structured_quality)
        document.ai_extraction_notes = processor._notes(ingestion_notes + quality_notes + ai_result.extraction_notes)
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
        provider_chain = processor._provider_chain(normalized, route, ai_result.provider_chain or [ai_result.provider])
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

        interpretation = processor.category_interpreter.interpret(document, ai_result.cleaned_raw_text or raw_text)
        provider_chain = processor._provider_chain(
            normalized,
            route,
            ai_result.provider_chain or [ai_result.provider],
            interpretation.provider_chain,
        )
        document.provider_chain = "+".join(provider_chain)
        document.title = processor._apply_title_hint(document.title, interpretation)
        document.category = processor._apply_category_hint(document.category, interpretation)
        document.document_type = processor._refined_document_type(document.document_type, interpretation)
        if interpretation.summary_hint:
            document.summary = interpretation.summary_hint
        document.tags = processor._merge_tags(document.tags, interpretation, document.document_type)
        document.ai_extraction_notes = processor._notes(
            (ingestion_notes + quality_notes + ai_result.extraction_notes) + processor._interpretation_notes(interpretation)
        )
        document.ingestion_metadata = processor._ingestion_metadata(
            normalized,
            route,
            extraction_quality,
            structured_quality,
            interpretation,
        )
        workflow = processor.workflow_enrichment.enrich(document, ai_result.cleaned_raw_text or raw_text, interpretation)
        document.workflow_summary = workflow.workflow_summary
        document.action_items = workflow.action_items
        document.warnings = workflow.warnings
        document.key_dates = workflow.key_dates
        document.urgency_level = workflow.urgency_level
        document.follow_up_required = workflow.follow_up_required
        document.workflow_metadata = workflow.workflow_metadata or None
        document.review_required = document.review_required or bool(workflow.warnings)
        document.processing_status = ProcessingStatus.needs_review if document.review_required else ProcessingStatus.ready

        actual = extract_actual(document, interpretation, normalized, route)
        issues.extend(run_quality_checks(item, actual))
    except Exception as exc:
        actual = {
            "status": "failed",
            "error": str(exc),
            "provider_chain": document.provider_chain,
            "title": document.title,
        }
        issues.append(EvalIssue("fail", "runtime_failure", f"Pipeline raised an exception: {exc}"))

    score = score_issues(issues)
    return {
        "id": item["id"],
        "filename": item["filename"],
        "format": item["format"],
        "expectations": item.get("expectations", {}),
        "actual": actual,
        "issues": [asdict(issue) for issue in issues],
        "score": score,
    }


def extract_actual(document: Document, interpretation, normalized, route) -> dict[str, Any]:
    summaries = (document.workflow_metadata or {}).get("summaries", {})
    interpretation_meta = ((document.ingestion_metadata or {}).get("category_interpretation") or {})
    return {
        "status": document.processing_status.value if document.processing_status else None,
        "title": document.title,
        "broad_type": getattr(document.document_type, "value", str(document.document_type)),
        "category": document.category,
        "profile": interpretation.profile,
        "subtype": interpretation.subtype,
        "summary_short": summaries.get("short"),
        "summary_detailed": summaries.get("detailed") or document.workflow_summary,
        "action_items": document.action_items or [],
        "warnings": document.warnings or [],
        "important_points": (document.workflow_metadata or {}).get("important_points", []),
        "review_focus": (document.workflow_metadata or {}).get("review_focus", []),
        "tags": document.tags or [],
        "provider_chain": document.provider_chain,
        "route": route.route_label,
        "extraction_method": normalized.extraction_method,
        "processing_path": (document.ingestion_metadata or {}).get("processing_path"),
        "review_required": document.review_required,
        "merchant_name": document.merchant_name,
        "extracted_amount": str(document.extracted_amount) if document.extracted_amount is not None else None,
        "extracted_date": document.extracted_date.isoformat() if document.extracted_date else None,
        "interpretation_provider_chain": interpretation_meta.get("provider_chain", []),
        "refinement_status": interpretation_meta.get("refinement_status"),
    }


def run_quality_checks(item: dict[str, Any], actual: dict[str, Any]) -> list[EvalIssue]:
    issues: list[EvalIssue] = []
    expectations = item.get("expectations", {})
    title = actual.get("title") or ""
    profile = (actual.get("profile") or "").strip()
    category = (actual.get("category") or "").strip()
    broad_type = (actual.get("broad_type") or "").strip()
    summary_short = actual.get("summary_short") or ""
    summary_detailed = actual.get("summary_detailed") or ""
    combined_summary = f"{summary_short}\n{summary_detailed}\n" + "\n".join(actual.get("important_points") or [])

    if actual.get("status") == "failed":
        return issues
    if not actual.get("provider_chain"):
        issues.append(EvalIssue("fail", "provider_chain_missing", "Provider chain is missing after successful processing."))
    if not profile:
        issues.append(EvalIssue("fail", "profile_missing", "Interpretation profile is missing."))

    if expectations.get("generic_not_allowed") and profile in {"generic_document", "", None}:
        issues.append(EvalIssue("fail", "generic_profile", "Document stayed generic even though stronger evidence was expected."))
    if expectations.get("expected_profiles") and profile not in expectations["expected_profiles"]:
        issues.append(EvalIssue("fail", "profile_mismatch", f"Expected one of {expectations['expected_profiles']}, got {profile or 'none'}."))    
    if expectations.get("expected_categories") and category not in expectations["expected_categories"]:
        issues.append(EvalIssue("warn", "category_mismatch", f"Expected category near {expectations['expected_categories']}, got {category or 'none'}."))    
    if expectations.get("expected_broad_types") and broad_type not in expectations["expected_broad_types"]:
        issues.append(EvalIssue("warn", "broad_type_mismatch", f"Expected broad type near {expectations['expected_broad_types']}, got {broad_type or 'none'}."))    

    if not title:
        issues.append(EvalIssue("fail", "title_missing", "Title is missing."))
    if re.fullmatch(r"(page|slide)\s+\d+", title.strip(), flags=re.IGNORECASE):
        issues.append(EvalIssue("fail", "title_placeholder", "Title is still a placeholder heading."))
    if looks_like_sentence(title):
        issues.append(EvalIssue("warn", "title_body_like", "Title looks like a body sentence rather than a document name."))
    for pattern in expectations.get("title_forbidden_patterns", []):
        if re.search(pattern, title, flags=re.IGNORECASE):
            issues.append(EvalIssue("fail", "title_forbidden_pattern", f"Title matches forbidden pattern `{pattern}`."))

    if not summary_short:
        issues.append(EvalIssue("fail", "summary_short_missing", "Short summary is missing."))
    if not summary_detailed:
        issues.append(EvalIssue("fail", "summary_detailed_missing", "Detailed summary is missing."))
    if is_generic_summary(summary_detailed):
        issues.append(EvalIssue("warn", "summary_generic", "Detailed summary still sounds generic."))
    if has_malformed_summary(summary_detailed):
        issues.append(EvalIssue("fail", "summary_malformed", "Detailed summary has malformed joins or dangling phrasing."))
    if expectations.get("summary_keywords"):
        matched = sum(1 for keyword in expectations["summary_keywords"] if keyword.lower() in combined_summary.lower())
        required = min(2, len(expectations["summary_keywords"]))
        if matched < required:
            issues.append(EvalIssue("warn", "summary_keyword_coverage", "Summary and highlights are not surfacing enough expected central details."))

    action_items = actual.get("action_items") or []
    if expectations.get("require_action_items") and not action_items:
        issues.append(EvalIssue("warn", "action_items_missing", "No action items were produced for a document that should surface review cues."))
    for item_text in action_items:
        if len(item_text) > 110:
            issues.append(EvalIssue("warn", "action_item_too_long", f"Action item is too long: `{item_text[:80]}...`"))
        if looks_like_raw_fragment(item_text):
            issues.append(EvalIssue("warn", "action_item_raw_fragment", f"Action item still looks too close to copied source text: `{item_text}`"))

    stale_tag = conflicting_tag(profile, actual.get("tags") or [])
    if stale_tag:
        issues.append(EvalIssue("warn", "stale_conflicting_tag", f"Tag `{stale_tag}` conflicts with the stronger final interpretation `{profile}`."))
    if profile == "generic_document" and category not in {"other", "", None}:
        issues.append(EvalIssue("warn", "generic_profile_specific_category", "Category is specific but profile stayed generic."))
    if profile in {"syllabus", "course_guide"} and broad_type == "notice":
        issues.append(EvalIssue("warn", "broad_type_outdated", "Broad type still reads like notice even though the interpreted document is a course guide."))
    return issues


def looks_like_sentence(value: str) -> bool:
    lowered = value.lower().strip()
    return len(lowered.split()) >= 8 and bool(re.search(r"\b(is|are|will|introduces|provides|covers|describes|contains)\b", lowered))


def is_generic_summary(value: str) -> bool:
    lowered = value.lower()
    return any(
        phrase in lowered
        for phrase in [
            "generic document",
            "this is a document",
            "this is a generic",
            "document with general information",
        ]
    )


def has_malformed_summary(value: str) -> bool:
    return bool(
        re.search(r",\s*and\.$", value)
        or re.search(r";\s*and\b", value)
        or re.search(r"\band\.\s*$", value)
        or re.search(r"\.\s*\.\s*", value)
    )


def looks_like_raw_fragment(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith(("review ", "check ", "confirm ")) and len(value.split()) <= 8:
        return False
    return (
        len(value.split()) > 14
        or value.count(":") >= 2
        or ";" in value
        or bool(re.search(r"\b(attendance|policy|students should|late work|must submit|academic integrity)\b", lowered))
    )


def conflicting_tag(profile: str, tags: list[str]) -> str | None:
    conflicts = {
        "syllabus": {"notice", "generic_document", "other"},
        "course_guide": {"notice", "generic_document", "other"},
        "presentation_guide": {"notice", "generic_document", "other"},
        "resume_profile": {"notice", "generic_document", "other"},
        "profile_record": {"notice", "generic_document", "other"},
        "repair_service_receipt": {"utilities", "generic_document", "other"},
        "utility_bill": {"repair_service", "generic_document", "other"},
        "invoice": {"generic_document", "notice", "other"},
    }
    for tag in tags:
        if tag in conflicts.get(profile, set()):
            return tag
    return None


def score_issues(issues: list[EvalIssue]) -> int:
    score = 100
    for issue in issues:
        score -= 18 if issue.severity == "fail" else 7
    return max(0, score)


def build_report(spec: dict[str, Any], results: list[dict[str, Any]], label: str) -> dict[str, Any]:
    issue_counts = Counter()
    severity_counts = Counter()
    status_counts = Counter(result["actual"].get("status", "unknown") for result in results)
    for result in results:
        for issue in result["issues"]:
            issue_counts[issue["code"]] += 1
            severity_counts[issue["severity"]] += 1
    avg_score = round(sum(result["score"] for result in results) / len(results), 2) if results else 0.0
    problematic = sorted(results, key=lambda entry: (len(entry["issues"]), -entry["score"]), reverse=True)[:5]
    return {
        "label": label,
        "generated_at": datetime.now().isoformat(),
        "spec_version": spec.get("version"),
        "documents_total": len(results),
        "average_score": avg_score,
        "status_counts": dict(status_counts),
        "severity_counts": dict(severity_counts),
        "issue_counts": dict(issue_counts.most_common()),
        "problem_documents": [
            {
                "id": entry["id"],
                "filename": entry["filename"],
                "score": entry["score"],
                "issue_codes": [issue["code"] for issue in entry["issues"]],
            }
            for entry in problematic
        ],
        "results": results,
    }


def compare_reports(previous_path: Path, current_report: dict[str, Any]) -> dict[str, Any]:
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    prev_by_id = {entry["id"]: entry for entry in previous.get("results", [])}
    improved = []
    regressed = []
    unchanged = []
    for entry in current_report.get("results", []):
        prior = prev_by_id.get(entry["id"])
        if not prior:
            continue
        delta = entry["score"] - prior.get("score", 0)
        if delta > 0:
            improved.append({"id": entry["id"], "delta": delta})
        elif delta < 0:
            regressed.append({"id": entry["id"], "delta": delta})
        else:
            unchanged.append(entry["id"])
    return {
        "previous_average_score": previous.get("average_score"),
        "current_average_score": current_report.get("average_score"),
        "average_score_delta": round(current_report.get("average_score", 0) - previous.get("average_score", 0), 2),
        "improved_documents": improved,
        "regressed_documents": regressed,
        "unchanged_documents": unchanged,
        "previous_issue_counts": previous.get("issue_counts", {}),
        "current_issue_counts": current_report.get("issue_counts", {}),
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# DocuParse Quality Report ({report['label']})",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Documents: `{report['documents_total']}`",
        f"- Average score: `{report['average_score']}`",
        f"- Status counts: `{report['status_counts']}`",
        f"- Severity counts: `{report['severity_counts']}`",
        "",
        "## Top Issue Patterns",
        "",
    ]
    for code, count in list(report.get("issue_counts", {}).items())[:10]:
        lines.append(f"- `{code}`: {count}")
    lines.extend(["", "## Most Problematic Documents", ""])
    for problem in report.get("problem_documents", []):
        lines.append(
            f"- `{problem['filename']}` score `{problem['score']}` issues `{', '.join(problem['issue_codes']) or 'none'}`"
        )
    if report.get("comparison"):
        cmp = report["comparison"]
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                f"- Previous average score: `{cmp['previous_average_score']}`",
                f"- Current average score: `{cmp['current_average_score']}`",
                f"- Delta: `{cmp['average_score_delta']}`",
                f"- Improved docs: `{cmp['improved_documents']}`",
                f"- Regressed docs: `{cmp['regressed_documents']}`",
            ]
        )
    lines.extend(["", "## Per-Document Results", ""])
    for result in report.get("results", []):
        lines.append(f"### `{result['filename']}`")
        lines.append("")
        lines.append(f"- Score: `{result['score']}`")
        lines.append(f"- Profile: `{result['actual'].get('profile')}`")
        lines.append(f"- Category: `{result['actual'].get('category')}`")
        lines.append(f"- Broad type: `{result['actual'].get('broad_type')}`")
        lines.append(f"- Title: `{result['actual'].get('title')}`")
        lines.append(f"- Provider chain: `{result['actual'].get('provider_chain')}`")
        if result["issues"]:
            lines.append("- Issues:")
            for issue in result["issues"]:
                lines.append(f"  - [{issue['severity']}] `{issue['code']}` {issue['message']}")
        else:
            lines.append("- Issues: none")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_terminal_summary(report: dict[str, Any]) -> str:
    summary = [
        f"Average score: {report['average_score']}",
        f"Status counts: {report['status_counts']}",
        f"Severity counts: {report['severity_counts']}",
        "Top issue patterns:",
    ]
    for code, count in list(report.get("issue_counts", {}).items())[:8]:
        summary.append(f"  - {code}: {count}")
    return "\n".join(summary)


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == "__main__":
    main()
