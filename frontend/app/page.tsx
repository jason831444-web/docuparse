"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Clock, FileText, ReceiptText, TriangleAlert } from "lucide-react";

import { DocumentCard } from "@/components/document-card";
import { UploadDropzone } from "@/components/upload-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { DocumentStats } from "@/types/document";

export default function DashboardPage() {
  const [stats, setStats] = useState<DocumentStats | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => setStats(null));
  }, []);

  const metrics = [
    { label: "Documents", value: stats?.total ?? 0, icon: FileText },
    { label: "Receipts", value: stats?.receipts ?? 0, icon: ReceiptText },
    { label: "Completed", value: stats?.completed ?? 0, icon: CheckCircle2 },
    { label: "Needs attention", value: stats?.failed ?? 0, icon: TriangleAlert }
  ];

  return (
    <main className="shell py-8">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-normal text-primary">OCR document workspace</p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal">Organize messy receipt and document images into searchable data.</h1>
          <p className="mt-4 max-w-2xl text-muted-foreground">
            Upload images, extract OCR text, review parsed fields, and keep a practical searchable archive for receipts, notices, memos, and general documents.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild><Link href="/upload">Upload image <ArrowRight className="size-4" /></Link></Button>
            <Button asChild variant="outline"><Link href="/documents">Browse documents</Link></Button>
          </div>
        </div>
        <UploadDropzone />
      </section>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-sm text-muted-foreground">{metric.label}</p>
                <p className="mt-1 text-3xl font-semibold">{metric.value}</p>
              </div>
              <metric.icon className="size-8 text-primary" />
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="mt-8">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Recent uploads</CardTitle>
            <Button asChild variant="ghost" size="sm"><Link href="/documents">View all</Link></Button>
          </CardHeader>
          <CardContent>
            {stats?.recent?.length ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {stats.recent.map((document) => <DocumentCard key={document.id} document={document} />)}
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-6 text-muted-foreground">
                <Clock className="size-5" /> Upload your first image to create a searchable document.
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
