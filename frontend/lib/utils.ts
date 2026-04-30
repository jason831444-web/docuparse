import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMoney(value?: string | number | null, currency = "USD") {
  if (value === undefined || value === null || value === "") return "No amount";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(value));
}

export function formatDate(value?: string | null) {
  if (!value) return "No date";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

export function formatDateTime(value?: string | null) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

const LABEL_ALIASES: Record<string, string> = {
  syllabus: "Syllabus",
  course_guide: "Course Guide",
  presentation_guide: "Presentation Guide",
  speaking_notes: "Speaking Notes",
  resume_profile: "Resume Profile",
  profile_record: "Profile Record",
  installation_guide: "Installation Guide",
  implementation_schedule: "Implementation Schedule",
  repair_service_receipt: "Repair Service Receipt",
  utility_bill: "Utility Bill",
  meeting_notice: "Meeting Notice",
  instructional_memo: "Instructional Memo",
  presentation: "Presentation",
  repair_service: "Repair Service",
  retail: "Retail",
};

export function titleCaseLabel(value?: string | null): string {
  if (!value) return "Uncategorized";
  if (value.includes(">")) return value.split(">").map((part) => titleCaseLabel(part)).join(" > ");
  const alias = LABEL_ALIASES[value];
  if (alias) return alias;
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function primaryCategoryLabel(document: { category?: string | null; workflow_metadata?: Record<string, unknown> | null }) {
  const interpretation = (document.workflow_metadata?.category_interpretation ?? {}) as Record<string, unknown>;
  const profile = typeof interpretation.profile === "string" ? interpretation.profile : null;
  return titleCaseLabel(document.category || profile || null);
}

function workflowSummaryFields(document: { workflow_metadata?: Record<string, unknown> | null }) {
  const summaries = (document.workflow_metadata?.summaries ?? {}) as Record<string, unknown>;
  return {
    short: typeof summaries.short === "string" ? summaries.short : null,
    detailed: typeof summaries.detailed === "string" ? summaries.detailed : null,
  };
}

export function documentSummaryShort(document: { workflow_metadata?: Record<string, unknown> | null; workflow_summary?: string | null; summary?: string | null }, limit = 120) {
  const summaries = workflowSummaryFields(document);
  const value = summaries.short || document.summary || document.workflow_summary;
  return shortSummary(value, limit);
}

export function documentSummaryDetailed(document: { workflow_metadata?: Record<string, unknown> | null; workflow_summary?: string | null; summary?: string | null }, limit = 500) {
  const summaries = workflowSummaryFields(document);
  const value = summaries.detailed || document.workflow_summary || document.summary;
  return shortSummary(value, limit);
}

export function shortSummary(summary?: string | null, limit = 120) {
  if (!summary) return "No summary available yet.";
  return summary.length > limit ? `${summary.slice(0, limit).trim()}...` : summary;
}
