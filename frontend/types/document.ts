export type DocumentType = "receipt" | "notice" | "document" | "memo" | "other";
export type ProcessingStatus = "uploaded" | "queued" | "processing" | "ready" | "needs_review" | "confirmed" | "completed" | "failed";

export interface FolderSummary {
  label: string;
  value: string;
  count: number;
  needs_review: number;
  confirmed: number;
  processing: number;
}

export interface DocumentRecord {
  id: string;
  original_filename: string;
  stored_file_path: string;
  mime_type: string;
  source_file_type: string | null;
  extraction_method: string | null;
  ingestion_metadata: Record<string, unknown> | null;
  document_type: DocumentType;
  title: string | null;
  raw_text: string | null;
  extracted_date: string | null;
  extracted_amount: string | null;
  subtotal: string | null;
  tax: string | null;
  currency: string | null;
  merchant_name: string | null;
  category: string | null;
  tags: string[];
  summary: string | null;
  confidence_score: string | null;
  ai_document_type: DocumentType | null;
  ai_confidence_score: string | null;
  ai_extraction_notes: string | null;
  review_required: boolean;
  extraction_provider: string | null;
  refinement_provider: string | null;
  provider_chain: string | null;
  merge_strategy: string | null;
  field_sources: Record<string, string> | null;
  workflow_summary: string | null;
  action_items: string[];
  warnings: string[];
  key_dates: string[];
  urgency_level: "low" | "medium" | "high" | null;
  follow_up_required: boolean;
  workflow_metadata: Record<string, unknown> | null;
  is_favorite: boolean;
  processing_status: ProcessingStatus;
  preview_image_path: string | null;
  processing_error: string | null;
  created_at: string;
  updated_at: string;
  file_url: string;
}

export interface DocumentListResponse {
  items: DocumentRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentStats {
  total: number;
  receipts: number;
  notices: number;
  completed: number;
  processing: number;
  failed: number;
  needs_review: number;
  queued: number;
  confirmed: number;
  recent: DocumentRecord[];
  recent_updated: DocumentRecord[];
  recent_review: DocumentRecord[];
  pinned: DocumentRecord[];
  category_overview: FolderSummary[];
  file_type_overview: FolderSummary[];
}

export type DocumentUpdate = Pick<
  DocumentRecord,
  | "document_type"
  | "title"
  | "raw_text"
  | "extracted_date"
  | "extracted_amount"
  | "subtotal"
  | "tax"
  | "currency"
  | "merchant_name"
  | "category"
  | "tags"
  | "summary"
> & {
  confidence_score?: string | null;
  processing_status?: ProcessingStatus;
  is_favorite?: boolean;
};

export interface ActivitySummary {
  recent_uploads: DocumentRecord[];
  recent_edits: DocumentRecord[];
  recent_needs_review: DocumentRecord[];
  favorites: DocumentRecord[];
}
