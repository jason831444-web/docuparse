"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, Search, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

import { DocumentCard } from "@/components/document-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { DocumentListResponse, DocumentType } from "@/types/document";

const types: Array<"" | DocumentType> = ["", "receipt", "notice", "document", "memo", "other"];

export default function DocumentsPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: "",
    document_type: "",
    category: "",
    date_from: "",
    date_to: "",
    amount_min: "",
    amount_max: "",
    sort_by: "created_at",
    order: "desc"
  });

  const params = useMemo(() => {
    const next = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) next.set(key, value);
    });
    return next;
  }, [filters]);

  useEffect(() => {
    setLoading(true);
    const handle = window.setTimeout(() => {
      api
        .list(params)
        .then(setData)
        .catch((error) => toast.error(error instanceof Error ? error.message : "Could not load documents"))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [params]);

  function setFilter(key: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <main className="shell py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Documents</h1>
          <p className="mt-2 text-muted-foreground">Search OCR text and filter by type, category, date, or amount.</p>
        </div>
        <Button asChild variant="outline">
          <a href={api.exportCsvUrl()}><Download className="size-4" /> Export CSV</a>
        </Button>
      </div>

      <Card className="mb-6">
        <CardContent className="grid gap-3 p-5 lg:grid-cols-[1.5fr_repeat(4,1fr)]">
          <label className="relative">
            <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
            <Input className="pl-9" placeholder="Search title, merchant, OCR text" value={filters.search} onChange={(event) => setFilter("search", event.target.value)} />
          </label>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.document_type} onChange={(event) => setFilter("document_type", event.target.value)}>
            {types.map((type) => <option key={type || "all"} value={type}>{type || "All types"}</option>)}
          </select>
          <Input placeholder="Category" value={filters.category} onChange={(event) => setFilter("category", event.target.value)} />
          <Input type="date" value={filters.date_from} onChange={(event) => setFilter("date_from", event.target.value)} />
          <Input type="date" value={filters.date_to} onChange={(event) => setFilter("date_to", event.target.value)} />
          <Input type="number" min="0" step="0.01" placeholder="Min amount" value={filters.amount_min} onChange={(event) => setFilter("amount_min", event.target.value)} />
          <Input type="number" min="0" step="0.01" placeholder="Max amount" value={filters.amount_max} onChange={(event) => setFilter("amount_max", event.target.value)} />
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.sort_by} onChange={(event) => setFilter("sort_by", event.target.value)}>
            <option value="created_at">Created</option>
            <option value="extracted_date">Date</option>
            <option value="extracted_amount">Amount</option>
            <option value="title">Title</option>
          </select>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.order} onChange={(event) => setFilter("order", event.target.value)}>
            <option value="desc">Newest/highest first</option>
            <option value="asc">Oldest/lowest first</option>
          </select>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <SlidersHorizontal className="size-4" /> {data?.total ?? 0} results
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-44 animate-pulse rounded-lg bg-muted" />)}
        </div>
      ) : data?.items.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.items.map((document) => <DocumentCard key={document.id} document={document} />)}
        </div>
      ) : (
        <Card>
          <CardContent className="p-10 text-center text-muted-foreground">No documents match those filters.</CardContent>
        </Card>
      )}
    </main>
  );
}
