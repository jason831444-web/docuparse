"use client";

import { useEffect, useState } from "react";

import { FolderCard } from "@/components/folder-card";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { FolderSummary } from "@/types/document";

export default function CategoriesPage() {
  const [folders, setFolders] = useState<FolderSummary[]>([]);

  useEffect(() => {
    api.categories().then(setFolders).catch(() => setFolders([]));
  }, []);

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Category Folders</h1>
        <p className="mt-2 text-muted-foreground">AI-organized folders built from document meaning, not just file type.</p>
      </div>
      {folders.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {folders.map((folder) => <FolderCard key={folder.value} folder={folder} href={`/categories/${folder.value}`} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">Categories will appear automatically as documents are analyzed.</CardContent></Card>
      )}
    </main>
  );
}
