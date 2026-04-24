"use client";

import { useEffect, useState } from "react";

import { FolderCard } from "@/components/folder-card";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { FolderSummary } from "@/types/document";

export default function FileTypesPage() {
  const [folders, setFolders] = useState<FolderSummary[]>([]);

  useEffect(() => {
    api.fileTypes().then(setFolders).catch(() => setFolders([]));
  }, []);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">File Types</h1>
        <p className="mt-2 text-muted-foreground">Browse the library by how documents were read, separate from their interpreted meaning.</p>
      </div>
      {folders.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {folders.map((folder) => <FolderCard key={folder.value} folder={folder} href={`/file-types/${folder.value}`} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">File-type folders will appear as documents are uploaded.</CardContent></Card>
      )}
    </main>
  );
}
