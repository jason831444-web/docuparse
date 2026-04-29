"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { FolderCard } from "@/components/folder-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { FolderSummary } from "@/types/document";

export default function CategoriesPage() {
  const [folders, setFolders] = useState<FolderSummary[]>([]);
  const [label, setLabel] = useState("");
  const [parent, setParent] = useState("");

  useEffect(() => {
    load();
  }, []);

  function load() {
    api.categories().then(setFolders).catch(() => setFolders([]));
  }

  async function createFolder() {
    if (!label.trim()) return;
    try {
      await api.createCategory({ label, parent: parent || null });
      setLabel("");
      setParent("");
      toast.success("Category folder added");
      load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not add category");
    }
  }

  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Category Folders</h1>
        <p className="mt-2 text-muted-foreground">AI-organized folders built from document meaning, not just file type.</p>
      </div>
      <Card className="mb-6">
        <CardContent className="grid gap-3 p-5 md:grid-cols-[1fr_1fr_auto]">
          <Input placeholder="New category folder" value={label} onChange={(event) => setLabel(event.target.value)} />
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={parent} onChange={(event) => setParent(event.target.value)}>
            <option value="">Top level</option>
            {["receipt", "document", "memo", "notice", "presentation"].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <Button type="button" onClick={createFolder}>Add folder</Button>
        </CardContent>
      </Card>
      {folders.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {folders.map((folder) => <FolderCard key={folder.value} folder={folder} href={`/categories/${encodeURIComponent(folder.value)}`} />)}
        </div>
      ) : (
        <Card><CardContent className="p-10 text-center text-muted-foreground">Categories will appear automatically as documents are analyzed.</CardContent></Card>
      )}
    </main>
  );
}
