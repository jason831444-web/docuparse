"use client";

import { useCallback, useEffect, useState } from "react";

import { DocumentList } from "@/components/document-list";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { DocumentListResponse } from "@/types/document";

export default function ReviewPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null);

  const load = useCallback(() => {
    api.review().then(setData).catch(() => setData(null));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Needs Review</h1>
        <p className="mt-2 text-muted-foreground">The priority queue for documents that need correction, confirmation, or a second look.</p>
      </div>
      {data?.items.length ? (
        <DocumentList documents={data.items} onChanged={load} returnTo="/review" />
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">No documents currently need review.</CardContent></Card>
      )}
    </main>
  );
}
