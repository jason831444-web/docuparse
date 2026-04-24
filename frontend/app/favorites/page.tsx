"use client";

import { useEffect, useState } from "react";

import { DocumentRow } from "@/components/document-row";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { DocumentListResponse } from "@/types/document";

export default function FavoritesPage() {
  const [data, setData] = useState<DocumentListResponse | null>(null);

  useEffect(() => {
    api.favorites().then(setData).catch(() => setData(null));
  }, []);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Favorites</h1>
        <p className="mt-2 text-muted-foreground">Pinned documents stay close at hand for repeated review, approval, or export.</p>
      </div>
      {data?.items.length ? (
        <div className="space-y-3">
          {data.items.map((document) => <DocumentRow key={document.id} document={document} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">Pin documents from the detail page to keep them here.</CardContent></Card>
      )}
    </main>
  );
}
