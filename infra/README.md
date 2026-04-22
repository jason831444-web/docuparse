# Infra Notes

The MVP infrastructure is intentionally small:

- PostgreSQL stores document metadata, OCR text, and parsed fields.
- FastAPI stores uploaded images in a mounted local volume.
- Next.js runs as a separate web container and talks to the backend through `NEXT_PUBLIC_API_BASE_URL`.

The storage boundary lives in `backend/app/services/storage.py`, so S3, GCS, or Azure Blob can be added later without changing route logic.
