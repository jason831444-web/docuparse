import enum
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentType(str, enum.Enum):
    receipt = "receipt"
    notice = "notice"
    document = "document"
    memo = "memo"
    other = "other"


class ProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    ready = "ready"
    needs_review = "needs_review"
    completed = "completed"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_file_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ingestion_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"), default=DocumentType.other)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extracted_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    ai_document_type: Mapped[DocumentType | None] = mapped_column(Enum(DocumentType, name="document_type"), nullable=True)
    ai_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    ai_extraction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    refinement_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_chain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merge_strategy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_sources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    workflow_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    key_dates: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    urgency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    workflow_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.uploaded,
        index=True,
    )
    preview_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
