import type { ActivitySummary, DocumentListResponse, DocumentRecord, DocumentStats, DocumentUpdate, FolderSummary } from "@/types/document";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers }
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  stats: () => request<DocumentStats>("/documents/stats", { cache: "no-store" }),
  activity: () => request<ActivitySummary>("/documents/activity", { cache: "no-store" }),
  list: (params: URLSearchParams) => request<DocumentListResponse>(`/documents?${params.toString()}`, { cache: "no-store" }),
  categories: () => request<FolderSummary[]>("/documents/categories", { cache: "no-store" }),
  fileTypes: () => request<FolderSummary[]>("/documents/file-types", { cache: "no-store" }),
  review: () => request<DocumentListResponse>("/documents/review", { cache: "no-store" }),
  favorites: () => request<DocumentListResponse>("/documents/favorites", { cache: "no-store" }),
  get: (id: string) => request<DocumentRecord>(`/documents/${id}`, { cache: "no-store" }),
  upload: (file: File) => {
    const data = new FormData();
    data.append("file", file);
    return request<DocumentRecord>("/documents/upload", { method: "POST", body: data });
  },
  update: (id: string, payload: DocumentUpdate) =>
    request<DocumentRecord>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: async (id: string) => {
    const response = await fetch(`${API_BASE}/documents/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Could not delete document");
  },
  reprocess: (id: string) => request<DocumentRecord>(`/documents/${id}/reprocess`, { method: "POST" }),
  confirm: (id: string) => request<DocumentRecord>(`/documents/${id}/confirm`, { method: "POST" }),
  markNeedsReview: (id: string) => request<DocumentRecord>(`/documents/${id}/needs-review`, { method: "POST" }),
  toggleFavorite: (id: string) => request<DocumentRecord>(`/documents/${id}/favorite`, { method: "POST" }),
  exportCsvUrl: () => `${API_BASE}/documents/export/csv`,
  exportJsonUrl: (id: string) => `${API_BASE}/documents/${id}/export/json`
};
