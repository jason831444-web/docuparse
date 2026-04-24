from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentType, ProcessingStatus


class DocumentBase(BaseModel):
    document_type: DocumentType = DocumentType.other
    title: str | None = Field(default=None, max_length=255)
    raw_text: str | None = None
    extracted_date: date | None = None
    extracted_amount: Decimal | None = Field(default=None, ge=0)
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    merchant_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None


class DocumentUpdate(DocumentBase):
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1)


class DocumentRead(DocumentBase):
    id: UUID
    original_filename: str
    stored_file_path: str
    mime_type: str
    source_file_type: str | None = None
    extraction_method: str | None = None
    ingestion_metadata: dict | None = None
    confidence_score: Decimal | None = None
    ai_document_type: DocumentType | None = None
    ai_confidence_score: Decimal | None = None
    ai_extraction_notes: str | None = None
    review_required: bool = False
    extraction_provider: str | None = None
    refinement_provider: str | None = None
    provider_chain: str | None = None
    merge_strategy: str | None = None
    field_sources: dict[str, str] | None = None
    workflow_summary: str | None = None
    action_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    key_dates: list[str] = Field(default_factory=list)
    urgency_level: str | None = None
    follow_up_required: bool = False
    workflow_metadata: dict | None = None
    processing_status: ProcessingStatus
    preview_image_path: str | None = None
    processing_error: str | None = None
    created_at: datetime
    updated_at: datetime
    file_url: str

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int
    page_size: int


class DocumentStats(BaseModel):
    total: int
    receipts: int
    notices: int
    completed: int
    processing: int
    failed: int
    needs_review: int = 0
    queued: int = 0
    recent: list[DocumentRead]
