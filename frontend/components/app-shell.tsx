"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BellRing,
  FileHeart,
  FileSearch,
  Files,
  FolderKanban,
  LayoutDashboard,
  LogIn,
  Search,
  Settings,
  Upload,
  UserPlus
} from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/documents", label: "All Documents", icon: Files },
  { href: "/categories", label: "Categories", icon: FolderKanban },
  { href: "/file-types", label: "File Types", icon: FileSearch },
  { href: "/review", label: "Needs Review", icon: BellRing },
  { href: "/favorites", label: "Favorites", icon: FileHeart },
  { href: "/settings", label: "Settings", icon: Settings }
];

const authItems = [
  { href: "/login", label: "Login", icon: LogIn },
  { href: "/signup", label: "Signup", icon: UserPlus }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/signup");

  if (isAuthPage) {
    return (
      <>
        <div className="border-b bg-white/80 backdrop-blur">
          <div className="shell flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-3 font-semibold tracking-normal">
              <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
                <FileSearch className="size-5" />
              </span>
              DocuParse
            </Link>
            <div className="flex items-center gap-2">
              {authItems.map((item) => (
                <Link key={item.href} href={item.href} className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
        {children}
      </>
    );
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      <div className="grid min-h-screen lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="border-r bg-white/80 px-5 py-6 backdrop-blur">
          <Link href="/" className="mb-8 flex items-center gap-3 font-semibold tracking-normal">
            <span className="grid size-10 place-items-center rounded-md bg-primary text-primary-foreground">
              <FileSearch className="size-5" />
            </span>
            <div>
              <p>DocuParse</p>
              <p className="text-xs font-normal text-muted-foreground">AI document workflows</p>
            </div>
          </Link>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                    active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-8 rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">
            Browse by category or file type, then confirm or correct the AI result when needed.
          </div>
        </aside>
        <div className="min-w-0">
          <header className="sticky top-0 z-20 border-b bg-[hsl(var(--background))/0.86] backdrop-blur">
            <div className="shell flex h-16 items-center gap-4">
              <div className="relative max-w-xl flex-1">
                <Search className="pointer-events-none absolute left-3 top-3.5 size-4 text-muted-foreground" />
                <Input className="pl-9" placeholder="Search title, summary, merchant, OCR text" readOnly />
              </div>
              <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground">Login</Link>
              <Link href="/signup" className="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground">Start free</Link>
            </div>
          </header>
          {children}
        </div>
      </div>
    </div>
  );
}
