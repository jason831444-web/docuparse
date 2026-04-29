import { Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney, titleCaseLabel } from "@/lib/utils";
import type { DocumentRecord } from "@/types/document";

type WorkflowMetadata = Record<string, unknown> & {
  receipt?: Record<string, unknown>;
  utilities?: Record<string, unknown>;
  notice?: Record<string, unknown>;
  health?: Record<string, unknown>;
  office?: Record<string, unknown>;
  spend?: Record<string, unknown>;
  generic?: Record<string, unknown>;
};

function metadata(document: DocumentRecord): WorkflowMetadata {
  return (document.workflow_metadata ?? {}) as WorkflowMetadata;
}

function text(value: unknown): string | null {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : null;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function contextLabel(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const context = value as Record<string, unknown>;
  const label = text(context.label);
  const confidence = text(context.confidence);
  if (!label) return null;
  return confidence ? `${label} (${confidence})` : label;
}

function workflowMode(document: DocumentRecord) {
  return String(metadata(document).workflow_mode ?? document.category ?? document.document_type ?? "other");
}

function ListBlock({ title, items, tone = "neutral" }: { title: string; items: string[]; tone?: "neutral" | "warning" }) {
  if (!items.length) return null;
  return (
    <div className={tone === "warning" ? "rounded-md border border-amber-300 bg-amber-50 p-3" : "rounded-md border bg-white p-3"}>
      <p className="mb-2 text-xs font-medium uppercase tracking-normal text-muted-foreground">{title}</p>
      <ul className="space-y-1 text-sm">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function ValueGrid({ values }: { values: Array<[string, string | null | undefined]> }) {
  const present = values.filter(([, value]) => value);
  if (!present.length) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {present.map(([label, value]) => (
        <div key={label} className="rounded-md border bg-white p-3">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-1 font-semibold">{value}</p>
        </div>
      ))}
    </div>
  );
}

function ReceiptModule({ document }: { document: DocumentRecord }) {
  const receipt = metadata(document).receipt ?? {};
  return (
    <div className="space-y-3">
      <ValueGrid values={[
        ["Merchant confidence", text(receipt.merchant_confidence)],
        ["Context hint", contextLabel(receipt.category_context)],
        ["Expected total", receipt.expected_total ? formatMoney(text(receipt.expected_total), document.currency || "USD") : null],
        ["Total validation", receipt.suspicious_total ? "Needs review" : "Looks consistent"],
      ]} />
      <ListBlock title="Top item lines" items={stringList(receipt.top_item_lines)} />
      <ListBlock title="Receipt validation" items={stringList(receipt.receipt_quality_flags)} tone="warning" />
    </div>
  );
}

function UtilitiesModule({ document }: { document: DocumentRecord }) {
  const utilities = metadata(document).utilities ?? {};
  return <ValueGrid values={[
    ["Provider", text(utilities.provider)],
    ["Amount due", utilities.amount_due ? formatMoney(text(utilities.amount_due), document.currency || "USD") : null],
    ["Due date", text(utilities.due_date)],
    ["Billing period", text(utilities.billing_period)],
    ["Payment urgency", text(utilities.payment_urgency)],
  ]} />;
}

function NoticeModule({ document }: { document: DocumentRecord }) {
  const notice = metadata(document).notice ?? {};
  return <ValueGrid values={[
    ["Deadline", text(notice.deadline)],
    ["Notice type", text(notice.notice_type_hint)],
    ["Actionable summary", text(notice.actionable_summary)],
  ]} />;
}

function HealthModule({ document }: { document: DocumentRecord }) {
  const health = metadata(document).health ?? {};
  return <ValueGrid values={[
    ["Provider / pharmacy", text(health.provider_or_pharmacy)],
    ["Date", text(health.visit_or_purchase_date)],
    ["Privacy", health.privacy_sensitive ? "Sensitive document" : null],
    ["Claim summary", text(health.claim_summary)],
  ]} />;
}

function OfficeModule({ document }: { document: DocumentRecord }) {
  const office = metadata(document).office ?? {};
  return (
    <div className="space-y-3">
      <ValueGrid values={[
        ["Reimbursement", office.reimbursement_ready ? "Ready" : "Needs review"],
        ["Business summary", text(office.business_expense_summary)],
      ]} />
      <ListBlock title="Expense hints" items={stringList(office.expense_type_hints)} />
    </div>
  );
}

function SpendModule({ document }: { document: DocumentRecord }) {
  const spend = metadata(document).spend ?? {};
  return (
    <div className="space-y-3">
      <ValueGrid values={[
        ["Merchant summary", text(spend.merchant_summary)],
        ["Context hint", contextLabel(spend.category_context)],
        ["Spend note", text(spend.category_spend_note)],
        ["Interpretation", text(spend.spending_interpretation)],
      ]} />
      <ListBlock title="Item highlights" items={stringList(spend.item_highlights)} />
    </div>
  );
}

function GenericModule({ document }: { document: DocumentRecord }) {
  const generic = metadata(document).generic ?? {};
  return (
    <div className="space-y-3">
      <ValueGrid values={[
        ["Heading quality", text(generic.heading_quality)],
        ["Follow-up", generic.follow_up_hint ? "Possible follow-up needed" : "No obvious follow-up"],
      ]} />
      <ListBlock title="Key entities" items={stringList(generic.key_entities)} />
    </div>
  );
}

function TypeSpecificModule({ document }: { document: DocumentRecord }) {
  const mode = workflowMode(document);
  if (document.document_type === "receipt") return <ReceiptModule document={document} />;
  if (mode === "utilities") return <UtilitiesModule document={document} />;
  if (mode === "education" || mode === "notice" || document.document_type === "notice") return <NoticeModule document={document} />;
  if (mode === "health") return <HealthModule document={document} />;
  if (mode === "office") return <OfficeModule document={document} />;
  if (["food_drink", "groceries", "retail", "transport"].includes(mode)) return <SpendModule document={document} />;
  return <GenericModule document={document} />;
}

export function WorkflowPanel({ document }: { document: DocumentRecord }) {
  const urgency = document.urgency_level ?? "low";
  return (
    <Card className={document.follow_up_required ? "border-amber-300 bg-amber-50/40" : ""}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="size-5 text-primary" />
          Workflow assistant
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge>{titleCaseLabel(workflowMode(document))}</Badge>
          <Badge className={urgency === "high" ? "border-red-300 bg-red-50 text-red-800" : urgency === "medium" ? "border-amber-300 bg-amber-50 text-amber-800" : "border-emerald-300 bg-emerald-50 text-emerald-800"}>
            {urgency} urgency
          </Badge>
          {document.follow_up_required ? <Badge className="border-amber-300 bg-amber-50 text-amber-800">follow-up</Badge> : null}
        </div>
        {document.workflow_summary ? <p className="rounded-md border bg-white p-3 text-sm">{document.workflow_summary}</p> : null}
        <div className="grid gap-3">
          <ListBlock title="Action items" items={document.action_items} />
          <ListBlock title="Warnings" items={document.warnings} tone="warning" />
          <ListBlock title="Key dates" items={document.key_dates} />
        </div>
        <TypeSpecificModule document={document} />
      </CardContent>
    </Card>
  );
}
