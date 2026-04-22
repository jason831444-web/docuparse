import { UploadDropzone } from "@/components/upload-dropzone";

export default function UploadPage() {
  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Upload</h1>
        <p className="mt-2 text-muted-foreground">Add a document image and review the extracted fields after OCR finishes.</p>
      </div>
      <UploadDropzone />
    </main>
  );
}
