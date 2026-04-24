import Link from "next/link";
import { ArrowRight, BellRing, CheckCircle2, LoaderCircle } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { FolderSummary } from "@/types/document";

export function FolderCard({ folder, href }: { folder: FolderSummary; href: string }) {
  return (
    <Link href={href}>
      <Card className="h-full transition hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-lg font-semibold">{folder.label}</p>
              <p className="text-sm text-muted-foreground">{folder.count} documents</p>
            </div>
            <ArrowRight className="size-4 text-muted-foreground" />
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
            <span className="flex items-center gap-2"><BellRing className="size-4" />{folder.needs_review} review</span>
            <span className="flex items-center gap-2"><CheckCircle2 className="size-4" />{folder.confirmed} confirmed</span>
            <span className="flex items-center gap-2"><LoaderCircle className="size-4" />{folder.processing} processing</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
