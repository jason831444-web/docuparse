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
    currency: str | None = Field(default=None, max_length=8)
    merchant_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list)


class DocumentUpdate(DocumentBase):
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1)


class DocumentRead(DocumentBase):
    id: UUID
    original_filename: str
    stored_file_path: str
    mime_type: str
    confidence_score: Decimal | None = None
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
    recent: list[DocumentRead]
