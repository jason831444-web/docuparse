import Link from "next/link";
import { Calendar, DollarSign, Tag } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { formatDate, formatMoney } from "@/lib/utils";
import type { DocumentRecord } from "@/types/document";

export function DocumentCard({ document }: { document: DocumentRecord }) {
  return (
    <Link href={`/documents/${document.id}`}>
      <Card className="h-full transition hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{document.title || document.original_filename}</h3>
              <p className="mt-1 truncate text-sm text-muted-foreground">{document.merchant_name || document.original_filename}</p>
            </div>
            <StatusBadge status={document.processing_status} />
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge>{document.document_type}</Badge>
            {document.category ? <Badge className="bg-accent text-accent-foreground">{document.category}</Badge> : null}
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
            <span className="flex items-center gap-2"><Calendar className="size-4" />{formatDate(document.extracted_date)}</span>
            <span className="flex items-center gap-2"><DollarSign className="size-4" />{formatMoney(document.extracted_amount, document.currency || "USD")}</span>
            <span className="flex items-center gap-2"><Tag className="size-4" />{document.tags.slice(0, 2).join(", ") || "No tags"}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
