import Link from "next/link";
import { ArrowRight, BellRing, CheckCircle2, LoaderCircle, Trash2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { FolderSummary } from "@/types/document";

export function FolderCard({ folder, href, onDelete }: { folder: FolderSummary; href: string; onDelete?: () => void }) {
  return (
    <Card className="h-full min-w-0 overflow-hidden transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
      <CardContent className="space-y-4 p-5">
        <Link href={href} className="block">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="line-clamp-2 break-words text-lg font-semibold leading-snug">{folder.label}</p>
              <p className="text-sm text-muted-foreground">{folder.count} documents</p>
            </div>
            <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
          </div>
        </Link>
        <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
          <span className="flex min-w-0 items-center gap-2"><BellRing className="size-4 shrink-0" /><span className="truncate">{folder.needs_review} review</span></span>
          <span className="flex min-w-0 items-center gap-2"><CheckCircle2 className="size-4 shrink-0" /><span className="truncate">{folder.confirmed} confirmed</span></span>
          <span className="flex min-w-0 items-center gap-2"><LoaderCircle className="size-4 shrink-0" /><span className="truncate">{folder.processing} processing</span></span>
        </div>
        {onDelete && folder.custom && folder.count === 0 ? (
          <Button type="button" variant="outline" size="sm" onClick={onDelete}>
            <Trash2 className="size-4" />
            Delete empty folder
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
