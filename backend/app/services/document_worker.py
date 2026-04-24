import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.services.document_processor import DocumentProcessor


class DocumentWorker:
    """Small local worker scaffold for deployment-style processing."""

    def __init__(self, processor: DocumentProcessor | None = None) -> None:
        self.processor = processor or DocumentProcessor()

    def process_document(self, db: Session, document_id: UUID) -> Document | None:
        document = db.get(Document, document_id)
        if not document:
            return None
        return self.processor.process(db, document)

    def process_next(self, db: Session) -> Document | None:
        document = db.scalars(
            select(Document)
            .where(Document.processing_status == ProcessingStatus.queued)
            .order_by(Document.created_at)
            .limit(1)
        ).first()
        if not document:
            return None
        return self.processor.process(db, document)

    def run_forever(self, db_factory, poll_seconds: float = 2.0) -> None:
        while True:
            with db_factory() as db:
                self.process_next(db)
            time.sleep(poll_seconds)
