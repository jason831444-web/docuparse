"use client";

import { Folder, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, titleCaseLabel } from "@/lib/utils";
import type { FolderSummary } from "@/types/document";

export function CategorySelector({
  value,
  folders,
  onChange,
}: {
  value: string;
  folders: FolderSummary[];
  onChange: (value: string) => void;
}) {
  const normalizedValue = value || "";
  const shownFolders = folders.slice(0, 18);
  const activeFolder = folders.find((folder) => (folder.category || folder.value) === normalizedValue || folder.value === normalizedValue);

  return (
    <div className="space-y-3">
      <div className="flex min-w-0 flex-wrap gap-2 rounded-lg border bg-white p-2">
        {shownFolders.map((folder) => {
          const selectionValue = folder.category || folder.value;
          const active = normalizedValue === selectionValue || normalizedValue === folder.value;
          return (
            <button
              key={folder.value}
              type="button"
              onClick={() => onChange(selectionValue)}
              className={cn(
                "flex min-h-9 max-w-full items-center gap-2 rounded-md border px-3 py-2 text-sm transition",
                active ? "border-primary bg-primary text-primary-foreground" : "bg-muted/40 text-muted-foreground hover:border-primary/40 hover:bg-white hover:text-foreground"
              )}
              title={folder.label}
            >
              <Folder className="size-4 shrink-0" />
              <span className="truncate">{folder.label}</span>
              <span className="text-xs opacity-75">{folder.count}</span>
            </button>
          );
        })}
        {!shownFolders.length ? (
          <div className="px-2 py-2 text-sm text-muted-foreground">Categories will appear after documents are processed.</div>
        ) : null}
      </div>
      <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
        <Input
          value={normalizedValue}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Type a category, e.g. implementation_schedule"
        />
        <Button type="button" variant="outline" onClick={() => activeFolder && onChange(activeFolder.category || activeFolder.value)} disabled={!activeFolder}>
          <Plus className="size-4" />
          {activeFolder ? titleCaseLabel(activeFolder.category || activeFolder.value) : "Select"}
        </Button>
      </div>
    </div>
  );
}
