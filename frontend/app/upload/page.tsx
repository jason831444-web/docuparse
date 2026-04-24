import { UploadDropzone } from "@/components/upload-dropzone";
import { Card, CardContent } from "@/components/ui/card";

export default function UploadPage() {
  return (
    <main className="shell py-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-primary">Ingestion Workspace</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal">Upload and analyze documents</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Drop in a file, let DocuParse classify and organize it, then review the original, extracted text, and AI result side by side.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          {["uploading", "processing", "ready", "needs_review", "confirmed", "failed"].map((status) => (
            <span key={status} className="rounded-full border bg-white px-3 py-1 text-muted-foreground">
              {status.replace("_", " ")}
            </span>
          ))}
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <UploadDropzone />
        <div className="grid gap-4">
          <Card>
            <CardContent className="p-5">
              <p className="text-sm font-semibold">What happens after upload</p>
              <ol className="mt-4 space-y-4 text-sm text-muted-foreground">
                <li>
                  <span className="font-medium text-foreground">1. Read the file correctly</span>
                  <p className="mt-1">DocuParse chooses the right path for images, PDFs, Office files, and structured text.</p>
                </li>
                <li>
                  <span className="font-medium text-foreground">2. Interpret the document meaning</span>
                  <p className="mt-1">AI-first interpretation classifies the document profile and shapes the summary, fields, and review hints.</p>
                </li>
                <li>
                  <span className="font-medium text-foreground">3. Organize it automatically</span>
                  <p className="mt-1">The document appears in its category folder, file-type view, and review queue if corrections are recommended.</p>
                </li>
              </ol>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="grid gap-3 p-5 text-sm text-muted-foreground">
              <div className="rounded-lg border bg-white p-4">
                <p className="font-medium text-foreground">Original</p>
                <p className="mt-1">Preview the uploaded file exactly as it came in.</p>
              </div>
              <div className="rounded-lg border bg-white p-4">
                <p className="font-medium text-foreground">Extracted Text</p>
                <p className="mt-1">Inspect the normalized text layer kept for transparency, debugging, and correction.</p>
              </div>
              <div className="rounded-lg border bg-white p-4">
                <p className="font-medium text-foreground">AI Result</p>
                <p className="mt-1">Review category, workflow summary, key fields, warnings, and suggested next actions.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
