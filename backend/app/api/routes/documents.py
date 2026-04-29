from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import CategoryFolder, Document, DocumentType, ProcessingStatus
from app.schemas.document import (
    ActivitySummary,
    BulkDocumentRequest,
    CategoryFolderCreate,
    DocumentListResponse,
    DocumentRead,
    DocumentStats,
    DocumentUpdate,
    FolderSummary,
)
from app.services.export import document_to_json, documents_to_csv
from app.services.category_taxonomy import category_path_for, clean_tags_for_context, display_label, normalize_category, path_matches_document
from app.services.persistence_safety import sanitize_for_postgres
from app.services.queue_service import get_document_queue
from app.services.storage import get_storage_service
from app.services.workflow_enrichment import DocumentWorkflowEnrichmentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_read(document: Document) -> DocumentRead:
    storage = get_storage_service()
    return DocumentRead.model_validate(
        {**document.__dict__, "file_url": storage.public_url(document.stored_file_path)}
    )


def _search_filter(search: str):
    terms = [term for term in search.strip().split() if term]
    if not terms:
        return None
    searchable_fields = [
        Document.title,
        Document.summary,
        Document.workflow_summary,
        Document.merchant_name,
        Document.raw_text,
        Document.original_filename,
        Document.category,
    ]
    per_term = []
    for term in terms:
        needle = f"%{term}%"
        per_term.append(or_(*(func.coalesce(field, "").ilike(needle) for field in searchable_fields)))
    return and_(*per_term)


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
        search_filter = _search_filter(search)
        if search_filter is not None:
            filters.append(search_filter)
    if document_type:
        filters.append(Document.document_type == document_type)
    category_filter = None
    if category:
        category_filter = category
        normalized_category = normalize_category(category)
        if ">" not in category and normalized_category:
            filters.append(Document.category == normalized_category)
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
    documents = list(db.scalars(stmt).all())
    if category_filter and ">" in category_filter:
        all_stmt = select(Document).order_by(asc(sort_column) if order == "asc" else desc(sort_column))
        if where_clause is not None:
            all_stmt = all_stmt.where(where_clause)
        documents = [document for document in db.scalars(all_stmt).all() if path_matches_document(document, category_filter)]
        total = len(documents)
        documents = documents[(page - 1) * page_size : page * page_size]
    else:
        total = db.scalar(count_stmt) or 0
    items = [_to_read(document) for document in documents]
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


@router.post("/categories", response_model=FolderSummary, status_code=status.HTTP_201_CREATED)
def create_category_folder(payload: CategoryFolderCreate, db: Session = Depends(get_db)) -> FolderSummary:
    category = normalize_category(payload.category or payload.label)
    if not category:
        raise HTTPException(status_code=400, detail="Category folder name is required.")
    parent = normalize_category(payload.parent)
    value = f"{parent}>{category}" if parent else category
    existing = db.scalar(select(CategoryFolder).where(CategoryFolder.value == value))
    if existing:
        return FolderSummary(
            label=existing.label,
            value=existing.value,
            count=0,
            parent=existing.parent,
            depth=1 if existing.parent else 0,
            category=existing.category,
            custom=True,
        )
    folder = CategoryFolder(
        value=value,
        label=f"{display_label(parent)} > {display_label(category)}" if parent else display_label(category),
        parent=parent,
        category=category,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return FolderSummary(label=folder.label, value=folder.value, count=0, parent=folder.parent, depth=1 if folder.parent else 0, category=folder.category, custom=True)


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


@router.post("/bulk/download")
def bulk_download_originals(payload: BulkDocumentRequest, db: Session = Depends(get_db)) -> Response:
    documents = db.scalars(select(Document).where(Document.id.in_(payload.ids)).order_by(Document.created_at)).all()
    if not documents:
        raise HTTPException(status_code=404, detail="No matching documents found.")
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        used: set[str] = set()
        for document in documents:
            path = Path(document.stored_file_path)
            if not path.exists():
                continue
            name = document.original_filename or path.name
            if name in used:
                stem = Path(name).stem
                suffix = Path(name).suffix
                name = f"{stem}-{document.id}{suffix}"
            used.add(name)
            archive.write(path, arcname=name)
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=docuparse-originals.zip"},
    )


@router.post("/bulk/delete")
def bulk_delete_documents(payload: BulkDocumentRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    documents = db.scalars(select(Document).where(Document.id.in_(payload.ids))).all()
    storage = get_storage_service()
    deleted = 0
    for document in documents:
        storage.delete(document.stored_file_path)
        db.delete(document)
        deleted += 1
    db.commit()
    return {"deleted": deleted}


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
    values = sanitize_for_postgres(payload.model_dump(exclude_unset=True))
    if "category" in values:
        values["category"] = normalize_category(values.get("category"))
    if "tags" in values:
        values["tags"] = clean_tags_for_context(
            values.get("tags") or [],
            category=values.get("category") or document.category,
            document_type=getattr(document.document_type, "value", str(document.document_type)),
            key_dates=document.key_dates,
            follow_up_required=document.follow_up_required,
            urgency_level=document.urgency_level,
        )
    for key, value in values.items():
        setattr(document, key, value)
    workflow = DocumentWorkflowEnrichmentService().enrich(document, document.raw_text)
    document.workflow_summary = workflow.workflow_summary
    document.action_items = workflow.action_items
    document.warnings = workflow.warnings
    document.key_dates = workflow.key_dates
    document.urgency_level = workflow.urgency_level
    document.follow_up_required = workflow.follow_up_required
    document.workflow_metadata = sanitize_for_postgres(workflow.workflow_metadata or None)
    document.tags = clean_tags_for_context(
        document.tags,
        category=document.category,
        profile=(workflow.workflow_metadata or {}).get("content_profile") if workflow.workflow_metadata else None,
        document_type=getattr(document.document_type, "value", str(document.document_type)),
        key_dates=workflow.key_dates,
        follow_up_required=workflow.follow_up_required,
        urgency_level=workflow.urgency_level,
    )
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
    if by != "category":
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
            result.append(
                FolderSummary(
                    label=display_label(str(value)),
                    value=str(value),
                    count=count or 0,
                    needs_review=needs_review or 0,
                    confirmed=confirmed or 0,
                    processing=processing or 0,
                )
            )
        return result

    documents = db.scalars(select(Document)).all()
    grouped: dict[str, dict] = {}
    for document in documents:
        path = category_path_for(document)
        row = grouped.setdefault(
            path.value,
            {
                "label": path.label,
                "value": path.value,
                "count": 0,
                "needs_review": 0,
                "confirmed": 0,
                "processing": 0,
                "parent": path.parent,
                "depth": path.depth,
                "category": path.category,
                "custom": False,
            },
        )
        row["count"] += 1
        if document.processing_status == ProcessingStatus.needs_review:
            row["needs_review"] += 1
        if document.processing_status == ProcessingStatus.confirmed:
            row["confirmed"] += 1
        if document.processing_status in {ProcessingStatus.processing, ProcessingStatus.queued}:
            row["processing"] += 1

    for folder in db.scalars(select(CategoryFolder).order_by(CategoryFolder.value)).all():
        grouped.setdefault(
            folder.value,
            {
                "label": folder.label,
                "value": folder.value,
                "count": 0,
                "needs_review": 0,
                "confirmed": 0,
                "processing": 0,
                "parent": folder.parent,
                "depth": 1 if folder.parent else 0,
                "category": folder.category,
                "custom": True,
            },
        )

    return [
        FolderSummary(**row)
        for row in sorted(grouped.values(), key=lambda item: (-item["count"], item["label"]))
    ]
