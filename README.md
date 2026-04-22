# DocuParse

DocuParse is a production-minded MVP for organizing receipt and document images with OCR. Users upload JPG or PNG files, the backend stores the original image, runs Tesseract OCR, extracts useful structured fields with honest heuristics, and exposes a searchable document workspace for review, editing, deletion, and export.

## Features

- Image upload for receipts, notices, documents, memos, and notes
- Tesseract OCR with OpenCV/Pillow preprocessing
- Heuristic extraction for title, merchant, date, total amount, currency, category, and tags
- Search across title, merchant, and raw OCR text
- Filters for document type, category, date range, and amount range
- Sort by created date, extracted date, amount, or title
- Editable document detail page with image preview and raw OCR text
- Re-run OCR/parsing for an uploaded document
- Export all documents as CSV
- Export one document as JSON
- Docker Compose setup with PostgreSQL, FastAPI, and Next.js

## Tech Stack

Frontend:

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn-style UI primitives
- React Hook Form
- Sonner toasts

Backend:

- FastAPI
- Python 3.11
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Tesseract OCR, pytesseract, Pillow, OpenCV

## Architecture

```text
DocuParse/
  frontend/       Next.js web app
  backend/        FastAPI API, OCR/parser services, SQLAlchemy models
  infra/          infrastructure notes
  docker-compose.yml
  README.md
```

Backend route handlers stay thin. File storage, OCR, parsing, and export logic live in service modules:

- `backend/app/services/storage.py`
- `backend/app/services/ocr.py`
- `backend/app/services/parser.py`
- `backend/app/services/document_processor.py`
- `backend/app/services/export.py`

The OCR and parsing interfaces are deliberately modular. A cloud OCR provider, PDF renderer, LLM parser, or trained extraction model can replace the current services without rewriting the API layer.

## Run With Docker

From the repository root:

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3001
- Backend API docs: http://localhost:8001/docs
- Health check: http://localhost:8001/health

The backend container runs Alembic migrations on startup. Uploaded files are stored in a Docker volume.

## Local Development

### Backend

Install system Tesseract first:

```bash
# macOS
brew install tesseract
```

Create a Python environment and install dependencies:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The default local database URL expects PostgreSQL at:

```text
postgresql+psycopg://docuparse:docuparse@localhost:5432/docuparse
```

You can start only PostgreSQL with Docker if desired. The Compose file exposes it on host port `5433` to avoid collisions with an existing local PostgreSQL server:

```bash
docker compose up db
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Environment Variables

Backend:

- `DATABASE_URL`: SQLAlchemy database URL
- `UPLOAD_DIR`: local directory for uploaded images
- `BACKEND_BASE_URL`: public backend URL used for image links
- `CORS_ORIGINS`: JSON list of allowed frontend origins
- `MAX_UPLOAD_MB`: upload size limit

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI base URL, usually `http://localhost:8000/api`

## OCR And Parsing

The current pipeline is:

1. Validate JPG/PNG upload.
2. Store the original image in local storage.
3. Preprocess the image with grayscale, denoising, and adaptive thresholding.
4. Extract text and confidence data with Tesseract.
5. Parse structured fields with regular expressions and keyword heuristics.
6. Save raw OCR text and extracted fields to PostgreSQL.
7. Let the user manually correct fields in the document detail page.

The parser is intentionally transparent. It uses:

- Date regexes for common formats
- Amount regexes with priority for lines containing `total`, `amount due`, or `balance`
- Keyword/category inference
- Title guessing from meaningful top lines
- Receipt merchant guessing from top OCR lines

This is a practical baseline, not fake intelligence.

## API Overview

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/stats`
- `GET /api/documents/{id}`
- `PATCH /api/documents/{id}`
- `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/reprocess`
- `GET /api/documents/export/csv`
- `GET /api/documents/{id}/export/json`

List query parameters include `search`, `document_type`, `category`, `date_from`, `date_to`, `amount_min`, `amount_max`, `sort_by`, `order`, `page`, and `page_size`.

## Screenshots

Add portfolio screenshots here after running the app locally:

- Dashboard with upload area
- Searchable document list
- Document detail editor with image preview

## Future Improvements

- PDF upload and page rendering
- Background processing queue for OCR
- Per-user vaults and authentication
- Full-text PostgreSQL search indexes
- LLM-based extraction and summarization behind the parser interface
- Important-information highlights
- Expense analytics and category charts
- Cloud object storage
- Batch upload and pagination controls
