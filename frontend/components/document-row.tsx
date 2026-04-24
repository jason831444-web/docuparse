import Link from "next/link";
import { Star } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { documentSummaryShort, formatDateTime, primaryCategoryLabel, titleCaseLabel } from "@/lib/utils";
import type { DocumentRecord } from "@/types/document";

export function DocumentRow({ document }: { document: DocumentRecord }) {
  return (
    <Link
      href={`/documents/${document.id}`}
      className="grid gap-3 rounded-lg border bg-white px-4 py-4 transition hover:border-primary/40 hover:shadow-sm lg:grid-cols-[minmax(0,2.2fr)_1fr_0.9fr_0.9fr]"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="truncate font-semibold">{document.title || document.original_filename}</p>
          {document.is_favorite ? <Star className="size-4 fill-amber-400 text-amber-400" /> : null}
        </div>
        <p className="mt-1 truncate text-sm text-muted-foreground">{documentSummaryShort(document, 140)}</p>
      </div>
      <div className="flex flex-wrap gap-2 lg:justify-self-start">
        <Badge className="bg-accent text-accent-foreground">{primaryCategoryLabel(document)}</Badge>
        <Badge variant="outline">{titleCaseLabel(document.source_file_type || document.document_type)}</Badge>
      </div>
      <div className="text-sm text-muted-foreground">
        <p>{formatDateTime(document.updated_at)}</p>
        <p className="mt-1 truncate">{document.original_filename}</p>
      </div>
      <div className="flex items-start justify-between gap-3 lg:justify-self-end">
        <StatusBadge status={document.processing_status} />
      </div>
    </Link>
  );
}
