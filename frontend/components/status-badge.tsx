import { Badge } from "@/components/ui/badge";
import type { ProcessingStatus } from "@/types/document";

const colors: Record<ProcessingStatus, string> = {
  uploaded: "border-amber-300 bg-amber-50 text-amber-800",
  queued: "border-sky-300 bg-sky-50 text-sky-800",
  processing: "border-blue-300 bg-blue-50 text-blue-800",
  ready: "border-emerald-300 bg-emerald-50 text-emerald-800",
  needs_review: "border-amber-300 bg-amber-50 text-amber-800",
  completed: "border-emerald-300 bg-emerald-50 text-emerald-800",
  failed: "border-red-300 bg-red-50 text-red-800"
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  return <Badge className={colors[status]}>{status.replace("_", " ")}</Badge>;
}
