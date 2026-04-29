"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { DocumentList } from "@/components/document-list";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { titleCaseLabel } from "@/lib/utils";
import type { DocumentListResponse } from "@/types/document";

export default function CategoryFolderPage() {
  const params = useParams<{ slug: string }>();
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const category = useMemo(() => decodeURIComponent(params.slug), [params.slug]);

  const load = useCallback(() => {
    const query = new URLSearchParams();
    query.set("category", category);
    query.set("sort_by", "updated_at");
    query.set("order", "desc");
    api.list(query).then(setData).catch(() => setData(null));
  }, [category]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">{titleCaseLabel(category)}</h1>
        <p className="mt-2 text-muted-foreground">Documents automatically organized into this AI category folder.</p>
      </div>
      {data?.items.length ? (
        <DocumentList documents={data.items} onChanged={load} returnTo={`/categories/${encodeURIComponent(category)}`} />
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">No documents in this category yet.</CardContent></Card>
      )}
    </main>
  );
}
