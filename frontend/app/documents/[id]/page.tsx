"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { AlertTriangle, Bot, Download, FileText, Loader2, RefreshCw, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { WorkflowPanel } from "@/components/workflow-panel";
import { api } from "@/lib/api";
import type { DocumentRecord, DocumentType, DocumentUpdate } from "@/types/document";

const documentTypes: DocumentType[] = ["receipt", "notice", "document", "memo", "other"];

function toForm(document: DocumentRecord): DocumentUpdate & { tags_text: string } {
  return {
    title: document.title ?? "",
    document_type: document.document_type,
    raw_text: document.raw_text ?? "",
    extracted_date: document.extracted_date ?? "",
    extracted_amount: document.extracted_amount ?? "",
    subtotal: document.subtotal ?? "",
    tax: document.tax ?? "",
    currency: document.currency ?? "",
    merchant_name: document.merchant_name ?? "",
    category: document.category ?? "",
    tags: document.tags,
    summary: document.summary ?? "",
    tags_text: document.tags.join(", ")
  } as DocumentUpdate & { tags_text: string };
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const form = useForm<DocumentUpdate & { tags_text: string }>();

  useEffect(() => {
    api
      .get(params.id)
      .then((item) => {
        setDocument(item);
        form.reset(toForm(item));
      })
      .catch((error) => toast.error(error instanceof Error ? error.message : "Could not load document"))
      .finally(() => setLoading(false));
  }, [form, params.id]);

  async function onSubmit(values: DocumentUpdate & { tags_text: string }) {
    setSaving(true);
    const { tags_text, ...fields } = values;
    const payload: DocumentUpdate = {
      ...fields,
      title: values.title || null,
      raw_text: values.raw_text || null,
      extracted_date: values.extracted_date || null,
      extracted_amount: values.extracted_amount || null,
      subtotal: values.subtotal || null,
      tax: values.tax || null,
      currency: values.currency || null,
      merchant_name: values.merchant_name || null,
      category: values.category || null,
      summary: values.summary || null,
      tags: tags_text.split(",").map((tag) => tag.trim()).filter(Boolean)
    };
    try {
      const updated = await api.update(params.id, payload);
      setDocument(updated);
      form.reset(toForm(updated));
      toast.success("Document saved");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  async function reprocess() {
    setSaving(true);
    try {
      const updated = await api.reprocess(params.id);
      setDocument(updated);
      form.reset(toForm(updated));
      toast.success("OCR reprocessed");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Reprocess failed");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this document and uploaded image?")) return;
    try {
      await api.remove(params.id);
      toast.success("Document deleted");
      router.push("/documents");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Delete failed");
    }
  }

  if (loading) {
    return <main className="shell py-8"><div className="h-96 animate-pulse rounded-lg bg-muted" /></main>;
  }

  if (!document) {
    return <main className="shell py-8"><Card><CardContent className="p-10">Document not found.</CardContent></Card></main>;
  }
  const isImage = document.mime_type.startsWith("image/");

  return (
    <main className="shell py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-3 flex flex-wrap gap-2">
            <StatusBadge status={document.processing_status} />
            <Badge>{document.document_type}</Badge>
            {document.category ? <Badge className="bg-accent text-accent-foreground">{document.category}</Badge> : null}
          </div>
          <h1 className="text-3xl font-semibold tracking-normal">{document.title || document.original_filename}</h1>
          <p className="mt-2 text-muted-foreground">{document.original_filename}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline"><a href={api.exportJsonUrl(document.id)}><Download className="size-4" /> JSON</a></Button>
          <Button variant="outline" onClick={reprocess} disabled={saving}><RefreshCw className="size-4" /> Reprocess</Button>
          <Button variant="destructive" onClick={remove}><Trash2 className="size-4" /> Delete</Button>
        </div>
      </div>

      {document.processing_error ? (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-800">{document.processing_error}</CardContent>
        </Card>
      ) : null}

      <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="space-y-6">
          <Card>
            <CardHeader><CardTitle>{isImage ? "Image preview" : "File preview"}</CardTitle></CardHeader>
            <CardContent>
              {isImage ? (
                <div className="relative h-[620px] max-h-[70vh] w-full rounded-md border bg-white">
                  <Image
                    src={document.file_url}
                    alt={document.original_filename}
                    fill
                    unoptimized
                    className="object-contain"
                  />
                </div>
              ) : (
                <div className="flex min-h-56 flex-col items-center justify-center rounded-md border bg-white p-6 text-center">
                  <FileText className="mb-3 size-10 text-primary" />
                  <p className="font-semibold">{document.original_filename}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{document.mime_type}</p>
                  <Button asChild variant="outline" className="mt-4"><a href={document.file_url}>Open original</a></Button>
                </div>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Extracted text</CardTitle></CardHeader>
            <CardContent>
              <Textarea className="min-h-96 font-mono text-xs" {...form.register("raw_text")} />
            </CardContent>
          </Card>
        </section>

        <section className="space-y-6">
          <WorkflowPanel document={document} />
          <Card className={document.review_required ? "border-amber-300 bg-amber-50/40" : ""}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="size-5 text-primary" />
                AI understanding
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Predicted type</p>
                  <p className="mt-1 font-semibold capitalize">{document.ai_document_type || "Unavailable"}</p>
                </div>
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Confidence</p>
                  <p className="mt-1 font-semibold">
                    {document.ai_confidence_score ? `${Math.round(Number(document.ai_confidence_score) * 100)}%` : "Unavailable"}
                  </p>
                </div>
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Review</p>
                  <p className="mt-1 font-semibold">{document.review_required ? "Recommended" : "Looks usable"}</p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Primary provider</p>
                  <p className="mt-1 font-semibold">{document.extraction_provider || "Unavailable"}</p>
                </div>
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Second pass</p>
                  <p className="mt-1 font-semibold">{document.refinement_provider || "Not used"}</p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">File type</p>
                  <p className="mt-1 font-semibold uppercase">{document.source_file_type || "unknown"}</p>
                </div>
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Extraction method</p>
                  <p className="mt-1 break-words font-semibold">{document.extraction_method || "Unavailable"}</p>
                </div>
                <div className="rounded-md border bg-white p-3">
                  <p className="text-xs text-muted-foreground">Route</p>
                  <p className="mt-1 break-words font-semibold">
                    {typeof document.ingestion_metadata?.route === "string" ? document.ingestion_metadata.route : "Unavailable"}
                  </p>
                </div>
              </div>
              <div className="rounded-md border bg-white p-3">
                <p className="text-xs text-muted-foreground">Provider chain</p>
                <p className="mt-1 break-words font-semibold">{document.provider_chain || "Unavailable"}</p>
                {document.merge_strategy ? <p className="mt-1 text-xs text-muted-foreground">{document.merge_strategy}</p> : null}
              </div>
              {document.review_required ? (
                <div className="flex gap-2 rounded-md border border-amber-300 bg-amber-100/60 p-3 text-sm text-amber-900">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                  Check the highlighted extraction before using this document data.
                </div>
              ) : null}
              {document.ai_extraction_notes ? (
                <div className="rounded-md border bg-white p-3 text-sm text-muted-foreground whitespace-pre-line">
                  {document.ai_extraction_notes}
                </div>
              ) : null}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Structured fields</CardTitle></CardHeader>
            <CardContent className="grid gap-4">
              <label className="grid gap-2 text-sm font-medium">Title<Input {...form.register("title")} /></label>
              <label className="grid gap-2 text-sm font-medium">
                Type
                <select className="h-10 rounded-md border bg-white px-3 text-sm" {...form.register("document_type")}>
                  {documentTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">Date<Input type="date" {...form.register("extracted_date")} /></label>
                <label className="grid gap-2 text-sm font-medium">Amount<Input type="number" min="0" step="0.01" {...form.register("extracted_amount")} /></label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">Subtotal<Input type="number" min="0" step="0.01" {...form.register("subtotal")} /></label>
                <label className="grid gap-2 text-sm font-medium">Tax<Input type="number" min="0" step="0.01" {...form.register("tax")} /></label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium">Currency<Input placeholder="USD" {...form.register("currency")} /></label>
                <label className="grid gap-2 text-sm font-medium">Merchant<Input {...form.register("merchant_name")} /></label>
              </div>
              <label className="grid gap-2 text-sm font-medium">Category<Input {...form.register("category")} /></label>
              <label className="grid gap-2 text-sm font-medium">Tags<Input placeholder="receipt, groceries" {...form.register("tags_text")} /></label>
              <label className="grid gap-2 text-sm font-medium">Summary<Textarea className="min-h-28" {...form.register("summary")} /></label>
              <div className="flex justify-end">
                <Button type="submit" disabled={saving}>
                  {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                  Save changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>
      </form>
    </main>
  );
}
