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
- Docker Compose setup with PostgreSQL, FastAPI, Next.js, and optional local GGUF interpretation

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

Backend route handlers stay thin. File storage, OCR, AI understanding, parsing, and export logic live in service modules:

- `backend/app/services/storage.py`
- `backend/app/services/ocr.py`
- `backend/app/services/ai_document_understanding.py`
- `backend/app/services/parser.py`
- `backend/app/services/document_processor.py`
- `backend/app/services/export.py`

The OCR, AI understanding, and parsing interfaces are deliberately modular. A cloud OCR provider, PDF renderer, multimodal model, LLM parser, or trained extraction model can replace the current services without rewriting the API layer.

## Run With Docker

From the repository root, start the full local stack with the backend profile:

```bash
docker compose --profile backend up --build
```

Then open:

- Frontend: http://localhost:3001
- Backend API docs: http://localhost:8001/docs
- Health check: http://localhost:8001/health

The backend container runs Alembic migrations on startup. Uploaded files are stored in a Docker volume.
For GGUF-backed interpretation, place the model file at `models/gguf/gemma-3-4b-it-q4_0.gguf` before starting the backend.

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
pip install -r requirements-llama.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The default local database URL expects PostgreSQL at:

```text
postgresql+psycopg://docuparse:docuparse@localhost:5433/docuparse
```

You can start only PostgreSQL with Docker if desired. The Compose file exposes it on host port `5433` to avoid collisions with an existing local PostgreSQL server:

```bash
docker compose up db
```

### Local Gemma 3 GGUF

The CPU-friendly interpretation path uses `llama-cpp-python` with a local GGUF file. Use the 4B instruction-tuned QAT GGUF as the balanced default:

```text
models/gguf/gemma-3-4b-it-q4_0.gguf
```

Model source:

```text
google/gemma-3-4b-it-qat-q4_0-gguf
```

The local backend env should include:

```dotenv
AI_INTERPRETATION_ENABLED=true
AI_INTERPRETATION_PROVIDER=llama_cpp
AI_INTERPRETATION_MODEL=gguf-local
LLAMA_CPP_MODEL_PATH=../models/gguf/gemma-3-4b-it-q4_0.gguf
LLAMA_CPP_CONTEXT_WINDOW=4096
LLAMA_CPP_THREADS=0
LLAMA_CPP_GPU_LAYERS=0
LLAMA_CPP_MAX_TOKENS=700
LLAMA_CPP_TEMPERATURE=0.1
```

After uploading a non-trivial document, confirm the active path through the document detail API. The provider chain should include:

```text
ai_interpretation_gemma_gguf
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3001 when using Docker, or http://localhost:3000 if you run the frontend dev server without changing its default port.

## Environment Variables

Backend:

- `DATABASE_URL`: SQLAlchemy database URL
- `UPLOAD_DIR`: local directory for uploaded images
- `BACKEND_BASE_URL`: public backend URL used for image links
- `CORS_ORIGINS`: JSON list of allowed frontend origins
- `MAX_UPLOAD_MB`: upload size limit
- `AI_PROVIDER`: `auto`, `local`, or `openai`
- `AI_MODEL`: multimodal model name when using an external provider
- `OPENAI_API_KEY`: optional API key for the OpenAI vision provider
- `AI_INTERPRETATION_PROVIDER`: `llama_cpp`, `gemma`, `openai`, `heuristic`, or `auto`
- `LLAMA_CPP_MODEL_PATH`: local `.gguf` file path for the CPU-friendly interpretation backend
- `LLAMA_CPP_CONTEXT_WINDOW`: llama.cpp context window, default `4096`
- `LLAMA_CPP_THREADS`: llama.cpp CPU thread count; `0` lets llama.cpp choose
- `LLAMA_CPP_GPU_LAYERS`: number of layers to offload; use `0` for CPU-only
- `LLAMA_CPP_MAX_TOKENS`: maximum generated interpretation tokens
- `LLAMA_CPP_TEMPERATURE`: generation temperature
- `AI_PRIMARY_PROVIDER`: primary open-source provider, default `paddleocr_vl`
- `AI_SECONDARY_PROVIDER`: second-pass provider, default `qwen2_5_vl`
- `AI_ENABLE_SECOND_PASS`: enables Qwen refinement when quality gates fail
- `AI_SECOND_PASS_CONFIDENCE_THRESHOLD`: confidence threshold for second-pass refinement
- `AI_MODEL_DIR`: local model cache root, default `models`
- `PADDLEOCR_VL_MODEL_DIR`: optional PaddleOCR-VL model directory
- `PADDLEOCR_VL_LAYOUT_MODEL_DIR`: optional Paddle layout model directory
- `PADDLEOCR_VL_DEVICE`: `cpu`, `gpu`, or runtime-supported device string
- `QWEN2_5_VL_MODEL_NAME`: Hugging Face model id, default `Qwen/Qwen2.5-VL-3B-Instruct`
- `QWEN2_5_VL_MODEL_DIR`: optional local Qwen2.5-VL model directory
- `QWEN2_5_VL_DEVICE`: `auto`, `cpu`, `cuda`, or supported device string

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI base URL, usually `http://localhost:8001/api`

## AI, OCR, And Parsing

The current pipeline is:

1. Validate JPG/PNG upload.
2. Store the original image in local storage.
3. Preprocess the image with grayscale, denoising, and adaptive thresholding.
4. Extract text and confidence data with Tesseract.
5. Run the AI document-understanding service on the image plus OCR context.
6. Parse structured fields with regular expressions and keyword heuristics as fallback.
7. Merge AI extraction with OCR/parser fallback fields.
8. Save raw OCR text, AI metadata, review warnings, and extracted fields to PostgreSQL.
9. Let the user manually correct fields in the document detail page.

The parser is intentionally transparent. It uses:

- Date regexes for common formats
- Amount regexes with priority for lines containing `total`, `amount due`, or `balance`
- Keyword/category inference
- Title guessing from meaningful top lines
- Receipt merchant guessing from top OCR lines

The default AI orchestration is:

1. Try `paddleocr_vl` as the primary document understanding provider.
2. Evaluate confidence and missing fields.
3. Run `qwen2_5_vl` only when refinement is needed, such as low confidence, missing receipt total/date/merchant, missing title/summary, weak category, or unavailable primary provider.
4. Merge secondary fields only into missing or weak primary fields.
5. Fall back to the local OCR/heuristic provider when optional model runtimes or weights are not installed.

The local fallback combines OCR text, image-quality signals, document classification scoring, receipt total/subtotal/tax extraction, category inference, summary generation, and review warnings. Provider traceability is stored on each document as `extraction_provider`, `refinement_provider`, `provider_chain`, `merge_strategy`, and `field_sources`.

## Optional Open-Source Model Setup

The CPU-friendly text interpretation path is Gemma 3 GGUF through llama.cpp. The heavier PaddleOCR-VL, Qwen2.5-VL, and HF/Transformers dependencies are still available for comparison and experimentation, but they are not the default CPU-oriented deployment path. To enable those heavier runtimes:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-ai.txt
python scripts/download_models.py --model all --target models
```

Then configure `.env`:

```bash
AI_PRIMARY_PROVIDER=paddleocr_vl
AI_SECONDARY_PROVIDER=qwen2_5_vl
AI_ENABLE_SECOND_PASS=true
AI_SECOND_PASS_CONFIDENCE_THRESHOLD=0.80
PADDLEOCR_VL_MODEL_DIR=models/paddleocr_vl
QWEN2_5_VL_MODEL_DIR=models/qwen2_5_vl
QWEN2_5_VL_DEVICE=auto
```

For Docker, mount the model directory into the backend container and pass the same environment variables. The Compose file already creates `/app/models` as a persistent volume.

Model size planning:

- `PaddlePaddle/PaddleOCR-VL-1.5`: about 1.8 GiB of weights
- `Qwen/Qwen2.5-VL-3B-Instruct`: about 7.0 GiB of weights
- Runtime packages and caches need additional disk space

GPU is optional for integration testing but recommended for practical Qwen2.5-VL inference. CPU inference may be very slow. Apple Silicon MPS can help for PyTorch/Qwen, but PaddleOCR runtime support depends on the installed Paddle package and device backend.

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
