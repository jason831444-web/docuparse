import { UploadDropzone } from "@/components/upload-dropzone";

export default function UploadPage() {
  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Upload</h1>
        <p className="mt-2 text-muted-foreground">Add an image, PDF, Office file, or structured text document and review the extracted workflow after processing.</p>
      </div>
      <UploadDropzone />
    </main>
  );
}
