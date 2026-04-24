import Link from "next/link";
import { Calendar, DollarSign, FileType2, Star, Tag } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { documentSummaryShort, formatDate, formatMoney, primaryCategoryLabel, titleCaseLabel } from "@/lib/utils";
import type { DocumentRecord } from "@/types/document";

export function DocumentCard({ document }: { document: DocumentRecord }) {
  return (
    <Link href={`/documents/${document.id}`}>
        <Card className="h-full transition hover:-translate-y-0.5 hover:shadow-md">
          <CardContent className="space-y-4 p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="truncate font-semibold">{document.title || document.original_filename}</h3>
                  {document.is_favorite ? <Star className="size-4 fill-amber-400 text-amber-400" /> : null}
                </div>
                <p className="mt-1 truncate text-sm text-muted-foreground">{documentSummaryShort(document, 88)}</p>
              </div>
              <StatusBadge status={document.processing_status} />
            </div>
          <div className="flex flex-wrap gap-2">
            <Badge className="bg-accent text-accent-foreground">{primaryCategoryLabel(document)}</Badge>
            <Badge variant="outline">{titleCaseLabel(document.document_type)}</Badge>
            {document.source_file_type ? <Badge variant="outline">{document.source_file_type.toUpperCase()}</Badge> : null}
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
            <span className="flex items-center gap-2"><Calendar className="size-4" />{formatDate(document.extracted_date)}</span>
            <span className="flex items-center gap-2"><DollarSign className="size-4" />{formatMoney(document.extracted_amount, document.currency || "USD")}</span>
            <span className="flex items-center gap-2"><FileType2 className="size-4" />{titleCaseLabel(document.source_file_type || document.mime_type)}</span>
          </div>
          <div className="text-sm text-muted-foreground flex items-center gap-2"><Tag className="size-4" />{document.tags.slice(0, 3).join(", ") || "No tags"}</div>
        </CardContent>
      </Card>
    </Link>
  );
}
