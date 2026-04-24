"use client";

import { useEffect, useState } from "react";

import { DocumentRow } from "@/components/document-row";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { DocumentListResponse } from "@/types/document";

export default function ReviewPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null);

  useEffect(() => {
    api.review().then(setData).catch(() => setData(null));
  }, []);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Needs Review</h1>
        <p className="mt-2 text-muted-foreground">The priority queue for documents that need correction, confirmation, or a second look.</p>
      </div>
      {data?.items.length ? (
        <div className="space-y-3">
          {data.items.map((document) => <DocumentRow key={document.id} document={document} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">No documents currently need review.</CardContent></Card>
      )}
    </main>
  );
}
