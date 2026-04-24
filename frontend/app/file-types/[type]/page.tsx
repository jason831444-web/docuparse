"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { DocumentRow } from "@/components/document-row";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { titleCaseLabel } from "@/lib/utils";
import type { DocumentListResponse } from "@/types/document";

export default function FileTypeFolderPage() {
  const params = useParams<{ type: string }>();
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const type = useMemo(() => decodeURIComponent(params.type), [params.type]);

  useEffect(() => {
    const query = new URLSearchParams();
    query.set("source_file_type", type);
    query.set("sort_by", "updated_at");
    query.set("order", "desc");
    api.list(query).then(setData).catch(() => setData(null));
  }, [type]);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">{titleCaseLabel(type)}</h1>
        <p className="mt-2 text-muted-foreground">Documents grouped by source file type and extraction path.</p>
      </div>
      {data?.items.length ? (
        <div className="space-y-3">
          {data.items.map((document) => <DocumentRow key={document.id} document={document} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">No documents for this file type yet.</CardContent></Card>
      )}
    </main>
  );
}
