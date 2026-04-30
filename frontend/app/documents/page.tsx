"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, Grid2X2, Rows3, Search } from "lucide-react";
import { toast } from "sonner";

import { DocumentList } from "@/components/document-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { DocumentListResponse, FolderSummary, ProcessingStatus } from "@/types/document";

const statuses: Array<"" | ProcessingStatus> = ["", "processing", "ready", "needs_review", "confirmed", "failed"];

export default function DocumentsPage() {
  return (
    <Suspense fallback={<DocumentsSkeleton />}>
      <DocumentsContent />
    </Suspense>
  );
}

function DocumentsSkeleton() {
  return (
    <main className="shell py-8">
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-28 animate-pulse rounded-lg bg-muted" />)}
      </div>
    </main>
  );
}

function DocumentsContent() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"grid" | "list">("list");
  const [categories, setCategories] = useState<FolderSummary[]>([]);
  const [filters, setFilters] = useState({
    search: searchParams.get("search") ?? "",
    category: "",
    source_file_type: "",
    processing_status: "",
    sort_by: "updated_at",
    order: "desc"
  });

  useEffect(() => {
    const search = searchParams.get("search") ?? "";
    setFilters((current) => current.search === search ? current : { ...current, search });
  }, [searchParams]);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  const params = useMemo(() => {
    const next = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) next.set(key, value);
    });
    return next;
  }, [filters]);

  const loadDocuments = useCallback(() => {
    setLoading(true);
    const handle = window.setTimeout(() => {
      api.list(params).then(setData).catch((error) => toast.error(error instanceof Error ? error.message : "Could not load documents")).finally(() => setLoading(false));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [params]);

  useEffect(() => loadDocuments(), [loadDocuments]);

  function setFilter(key: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <main className="shell py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">All Documents</h1>
          <p className="mt-2 text-muted-foreground">Search, filter, sort, review, and confirm the full document library.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline"><a href={api.exportCsvUrl()}><Download className="size-4" /> Export CSV</a></Button>
          <div className="flex rounded-md border bg-white p-1">
            <Button type="button" variant={view === "list" ? "default" : "ghost"} size="sm" onClick={() => setView("list")}><Rows3 className="size-4" /></Button>
            <Button type="button" variant={view === "grid" ? "default" : "ghost"} size="sm" onClick={() => setView("grid")}><Grid2X2 className="size-4" /></Button>
          </div>
        </div>
      </div>

      <Card className="mb-6">
        <CardContent className="grid gap-3 p-5 lg:grid-cols-[1.5fr_repeat(4,1fr)]">
          <label className="relative">
            <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
            <Input className="pl-9" placeholder="Search title, merchant, summary, OCR text" value={filters.search} onChange={(event) => setFilter("search", event.target.value)} />
          </label>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.category} onChange={(event) => setFilter("category", event.target.value)}>
            <option value="">All categories</option>
            {categories.map((folder) => (
              <option key={folder.value} value={folder.category || folder.value}>
                {folder.label}
              </option>
            ))}
          </select>
          <Input placeholder="File type" value={filters.source_file_type} onChange={(event) => setFilter("source_file_type", event.target.value)} />
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.processing_status} onChange={(event) => setFilter("processing_status", event.target.value)}>
            {statuses.map((status) => <option key={status || "all"} value={status}>{status ? status.replace("_", " ") : "All statuses"}</option>)}
          </select>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={filters.order} onChange={(event) => setFilter("order", event.target.value)}>
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </select>
        </CardContent>
      </Card>

      {loading ? (
        <div className={view === "grid" ? "grid gap-4 lg:grid-cols-2" : "space-y-3"}>
          {Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-28 animate-pulse rounded-lg bg-muted" />)}
        </div>
      ) : data?.items.length ? (
        <DocumentList documents={data.items} view={view} onChanged={() => api.list(params).then(setData)} returnTo="/documents" />
      ) : (
        <Card>
          <CardContent className="p-10 text-center text-muted-foreground">No documents match those filters yet.</CardContent>
        </Card>
      )}
    </main>
  );
}
