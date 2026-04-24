from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentType, ProcessingStatus
from app.schemas.document import ActivitySummary, DocumentListResponse, DocumentRead, DocumentStats, DocumentUpdate, FolderSummary
from app.services.export import document_to_json, documents_to_csv
from app.services.queue_service import get_document_queue
from app.services.storage import get_storage_service
from app.services.workflow_enrichment import DocumentWorkflowEnrichmentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_read(document: Document) -> DocumentRead:
    storage = get_storage_service()
    return DocumentRead.model_validate(
        {**document.__dict__, "file_url": storage.public_url(document.stored_file_path)}
    )


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(file: Annotated[UploadFile, File(...)], db: Session = Depends(get_db)) -> DocumentRead:
    storage = get_storage_service()
    try:
        stored_path = storage.save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = Document(
        original_filename=file.filename or "upload",
        stored_file_path=str(stored_path),
        mime_type=file.content_type or "application/octet-stream",
        processing_status=ProcessingStatus.uploaded,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document = get_document_queue().enqueue(db, document)
    return _to_read(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    search: str | None = None,
    document_type: DocumentType | None = None,
    category: str | None = None,
    source_file_type: str | None = None,
    processing_status: ProcessingStatus | None = None,
    is_favorite: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    sort_by: str = Query(default="updated_at", pattern="^(created_at|updated_at|extracted_date|extracted_amount|title)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DocumentListResponse:
    filters = []
    if search:
        needle = f"%{search}%"
        filters.append(or_(Document.title.ilike(needle), Document.raw_text.ilike(needle), Document.merchant_name.ilike(needle)))
    if document_type:
        filters.append(Document.document_type == document_type)
    if category:
        filters.append(Document.category == category)
    if source_file_type:
        filters.append(Document.source_file_type == source_file_type)
    if processing_status:
        filters.append(Document.processing_status == processing_status)
    if is_favorite is not None:
        filters.append(Document.is_favorite == is_favorite)
    if date_from:
        filters.append(Document.extracted_date >= date_from)
    if date_to:
        filters.append(Document.extracted_date <= date_to)
    if amount_min is not None:
        filters.append(Document.extracted_amount >= amount_min)
    if amount_max is not None:
        filters.append(Document.extracted_amount <= amount_max)

    where_clause = and_(*filters) if filters else None
    count_stmt = select(func.count()).select_from(Document)
    stmt = select(Document)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
        stmt = stmt.where(where_clause)

    sort_column = getattr(Document, sort_by)
    stmt = stmt.order_by(asc(sort_column) if order == "asc" else desc(sort_column))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    total = db.scalar(count_stmt) or 0
    items = [_to_read(document) for document in db.scalars(stmt).all()]
    return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=DocumentStats)
def get_stats(db: Session = Depends(get_db)) -> DocumentStats:
    recent_uploads = db.scalars(select(Document).order_by(desc(Document.created_at)).limit(5)).all()
    recent_updated = db.scalars(select(Document).order_by(desc(Document.updated_at)).limit(5)).all()
    recent_review = db.scalars(
        select(Document).where(Document.processing_status == ProcessingStatus.needs_review).order_by(desc(Document.updated_at)).limit(5)
    ).all()
    pinned = db.scalars(select(Document).where(Document.is_favorite.is_(True)).order_by(desc(Document.updated_at)).limit(6)).all()
    category_overview = _folder_summary_rows(db, by="category")
    file_type_overview = _folder_summary_rows(db, by="source_file_type")
    return DocumentStats(
        total=db.scalar(select(func.count()).select_from(Document)) or 0,
        receipts=db.scalar(select(func.count()).select_from(Document).where(Document.document_type == DocumentType.receipt)) or 0,
        notices=db.scalar(select(func.count()).select_from(Document).where(Document.document_type == DocumentType.notice)) or 0,
        completed=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status.in_([ProcessingStatus.completed, ProcessingStatus.ready]))) or 0,
        confirmed=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status == ProcessingStatus.confirmed)) or 0,
        processing=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status.in_([ProcessingStatus.processing, ProcessingStatus.queued]))) or 0,
        failed=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status == ProcessingStatus.failed)) or 0,
        needs_review=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status == ProcessingStatus.needs_review)) or 0,
        queued=db.scalar(select(func.count()).select_from(Document).where(Document.processing_status == ProcessingStatus.queued)) or 0,
        recent=[_to_read(document) for document in recent_uploads],
        recent_updated=[_to_read(document) for document in recent_updated],
        recent_review=[_to_read(document) for document in recent_review],
        pinned=[_to_read(document) for document in pinned],
        category_overview=[row.model_dump() for row in category_overview],
        file_type_overview=[row.model_dump() for row in file_type_overview],
    )


@router.get("/activity", response_model=ActivitySummary)
def get_activity(db: Session = Depends(get_db)) -> ActivitySummary:
    return ActivitySummary(
        recent_uploads=[_to_read(document) for document in db.scalars(select(Document).order_by(desc(Document.created_at)).limit(8)).all()],
        recent_edits=[_to_read(document) for document in db.scalars(select(Document).order_by(desc(Document.updated_at)).limit(8)).all()],
        recent_needs_review=[_to_read(document) for document in db.scalars(
            select(Document).where(Document.processing_status == ProcessingStatus.needs_review).order_by(desc(Document.updated_at)).limit(8)
        ).all()],
        favorites=[_to_read(document) for document in db.scalars(
            select(Document).where(Document.is_favorite.is_(True)).order_by(desc(Document.updated_at)).limit(8)
        ).all()],
    )


@router.get("/categories", response_model=list[FolderSummary])
def list_categories(db: Session = Depends(get_db)) -> list[FolderSummary]:
    return _folder_summary_rows(db, by="category")


@router.get("/file-types", response_model=list[FolderSummary])
def list_file_types(db: Session = Depends(get_db)) -> list[FolderSummary]:
    return _folder_summary_rows(db, by="source_file_type")


@router.get("/review", response_model=DocumentListResponse)
def list_needs_review(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DocumentListResponse:
    stmt = (
        select(Document)
        .where(Document.processing_status == ProcessingStatus.needs_review)
        .order_by(desc(Document.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total = db.scalar(select(func.count()).select_from(Document).where(Document.processing_status == ProcessingStatus.needs_review)) or 0
    return DocumentListResponse(items=[_to_read(document) for document in db.scalars(stmt).all()], total=total, page=page, page_size=page_size)


@router.get("/favorites", response_model=DocumentListResponse)
def list_favorites(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DocumentListResponse:
    stmt = (
        select(Document)
        .where(Document.is_favorite.is_(True))
        .order_by(desc(Document.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total = db.scalar(select(func.count()).select_from(Document).where(Document.is_favorite.is_(True))) or 0
    return DocumentListResponse(items=[_to_read(document) for document in db.scalars(stmt).all()], total=total, page=page, page_size=page_size)


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)) -> Response:
    documents = db.scalars(select(Document).order_by(desc(Document.created_at))).all()
    return Response(
        documents_to_csv(list(documents)),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=docuparse-documents.csv"},
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_read(document)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(document_id: UUID, payload: DocumentUpdate, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, key, value)
    workflow = DocumentWorkflowEnrichmentService().enrich(document, document.raw_text)
    document.workflow_summary = workflow.workflow_summary
    document.action_items = workflow.action_items
    document.warnings = workflow.warnings
    document.key_dates = workflow.key_dates
    document.urgency_level = workflow.urgency_level
    document.follow_up_required = workflow.follow_up_required
    document.workflow_metadata = workflow.workflow_metadata or None
    document.review_required = document.review_required or bool(workflow.warnings)
    if document.processing_status not in {ProcessingStatus.processing, ProcessingStatus.queued, ProcessingStatus.failed, ProcessingStatus.confirmed}:
        document.processing_status = ProcessingStatus.needs_review if document.review_required else ProcessingStatus.ready
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_read(document)


@router.post("/{document_id}/confirm", response_model=DocumentRead)
def confirm_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.review_required = False
    document.processing_status = ProcessingStatus.confirmed
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_read(document)


@router.post("/{document_id}/needs-review", response_model=DocumentRead)
def mark_document_needs_review(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.review_required = True
    document.processing_status = ProcessingStatus.needs_review
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_read(document)


@router.post("/{document_id}/favorite", response_model=DocumentRead)
def toggle_favorite(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.is_favorite = not document.is_favorite
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_read(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, db: Session = Depends(get_db)) -> Response:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    get_storage_service().delete(document.stored_file_path)
    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/reprocess", response_model=DocumentRead)
def reprocess_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document = get_document_queue().enqueue(db, document)
    return _to_read(document)


@router.get("/{document_id}/export/json")
def export_document_json(document_id: UUID, db: Session = Depends(get_db)) -> Response:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        document_to_json(document),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=document-{document.id}.json"},
    )


def _folder_summary_rows(db: Session, by: str) -> list[FolderSummary]:
    field = getattr(Document, by)
    rows = db.execute(
        select(
            field,
            func.count(Document.id),
            func.count().filter(Document.processing_status == ProcessingStatus.needs_review),
            func.count().filter(Document.processing_status == ProcessingStatus.confirmed),
            func.count().filter(Document.processing_status.in_([ProcessingStatus.processing, ProcessingStatus.queued])),
        )
        .where(field.is_not(None))
        .group_by(field)
        .order_by(desc(func.count(Document.id)), asc(field))
    ).all()
    result: list[FolderSummary] = []
    for value, count, needs_review, confirmed, processing in rows:
        if not value:
            continue
        label = str(value).replace("_", " ").title()
        result.append(
            FolderSummary(
                label=label,
                value=str(value),
                count=count or 0,
                needs_review=needs_review or 0,
                confirmed=confirmed or 0,
                processing=processing or 0,
            )
        )
    return result
