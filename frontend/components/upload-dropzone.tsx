"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      toast.error("Upload a JPG, JPEG, or PNG image.");
      return;
    }
    setUploading(true);
    try {
      const document = await api.upload(file);
      toast.success("Document processed");
      router.push(`/documents/${document.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div
      className={cn(
        "flex min-h-72 flex-col items-center justify-center rounded-lg border border-dashed bg-white p-8 text-center transition",
        dragging && "border-primary bg-emerald-50"
      )}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        void handleFiles(event.dataTransfer.files);
      }}
    >
      <div className="mb-4 grid size-14 place-items-center rounded-md bg-secondary">
        {uploading ? <Loader2 className="size-7 animate-spin" /> : <FileUp className="size-7 text-primary" />}
      </div>
      <h2 className="text-xl font-semibold">Upload a receipt, notice, or note</h2>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">
        DocuParse stores the image, runs Tesseract OCR, extracts useful fields, and opens the result for review.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(event) => void handleFiles(event.target.files)}
      />
      <Button className="mt-5" onClick={() => inputRef.current?.click()} disabled={uploading}>
        {uploading ? <Loader2 className="size-4 animate-spin" /> : <FileUp className="size-4" />}
        Select image
      </Button>
      <p className="mt-3 text-xs text-muted-foreground">Accepted formats: JPG, JPEG, PNG</p>
    </div>
  );
}
