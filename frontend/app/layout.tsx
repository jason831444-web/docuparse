import type { Metadata } from "next";
import Link from "next/link";
import { FileSearch, LayoutDashboard, Upload } from "lucide-react";
import { Toaster } from "sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "DocuParse",
  description: "OCR document and receipt organization"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b bg-white/85 backdrop-blur">
          <div className="shell flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
                <FileSearch className="size-5" />
              </span>
              DocuParse
            </Link>
            <nav className="flex items-center gap-1 text-sm">
              <Link className="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted" href="/">
                <LayoutDashboard className="size-4" /> Dashboard
              </Link>
              <Link className="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted" href="/documents">
                <FileSearch className="size-4" /> Documents
              </Link>
              <Link className="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted" href="/upload">
                <Upload className="size-4" /> Upload
              </Link>
            </nav>
          </div>
        </header>
        {children}
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
