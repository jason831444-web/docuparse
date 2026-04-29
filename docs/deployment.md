# Production Docker Deployment

This deployment keeps the current DocuParse architecture intact: PostgreSQL for metadata, FastAPI for API/uploads/processing, Next.js for the web UI, and nginx as the public reverse proxy.

## Services

- `db`: PostgreSQL 16 with a persistent `postgres_data` Docker volume.
- `backend`: FastAPI on port `8000` inside the Docker network. It runs Alembic migrations on startup, stores uploads in `uploaded_files`, and loads Gemma from a read-only host mount.
- `frontend`: Next.js production server on port `3000` inside the Docker network.
- `proxy`: nginx public entrypoint. It routes `/` to the frontend and `/api`, `/uploads`, and `/health` to the backend.

## Required Environment

Create `.env.prod` from `.env.prod.example` on the server:

```bash
cp .env.prod.example .env.prod
```

Set at minimum:

- `POSTGRES_PASSWORD`: a long random password.
- `PUBLIC_BASE_URL`: the public origin, for example `https://docuparse.example.com`.
- `CORS_ORIGINS`: JSON list containing the public origin, for example `["https://docuparse.example.com"]`.
- `GEMMA_MODEL_DIR_ON_HOST`: absolute server path for the Gemma model files.
- `GEMMA_DEVICE`: `auto`, `cpu`, `cuda`, or another device string supported by the installed torch runtime.

The compose file sets `GEMMA_MODEL_DIR=/models/gemma` inside the backend container. Do not bake model weights into the image.
If `POSTGRES_PASSWORD` contains URL-reserved characters such as `@`, `/`, `:`, or `#`, URL-encode it before using this compose file because it is interpolated into `DATABASE_URL`.

## Gemma Model Location

Place the current Gemma Hugging Face snapshot on the server filesystem, for example:

```text
/srv/docuparse/models/gemma-4-E4B-it/
  config.json
  tokenizer.json
  model-*.safetensors
  ...
```

Then set:

```dotenv
GEMMA_MODEL_DIR_ON_HOST=/srv/docuparse/models/gemma-4-E4B-it
GEMMA_MODEL_NAME=google/gemma-4-E4B-it
AI_INTERPRETATION_PROVIDER=gemma
```

The backend mount is read-only:

```text
${GEMMA_MODEL_DIR_ON_HOST}:/models/gemma:ro
```

## Start The Stack

Build and start:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Watch startup logs:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f db backend frontend proxy
```

Run migrations manually when needed:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend alembic upgrade head
```

The backend container also runs `alembic upgrade head` before starting uvicorn.

## Health And Availability Checks

Backend through nginx:

```bash
curl -fsS http://127.0.0.1/health
curl -fsS http://127.0.0.1/api/documents?page_size=1
```

Frontend through nginx:

```bash
curl -fsSI http://127.0.0.1/
```

For a real public domain, replace `http://127.0.0.1` with `PUBLIC_BASE_URL`.

## Persistence Checks

Create a document through the deployed API:

```bash
UPLOAD_RESPONSE="$(curl -fsS -X POST http://127.0.0.1/api/documents/upload \
  -F "file=@backend/eval/corpus/student_profile_note.txt")"
printf '%s\n' "$UPLOAD_RESPONSE"
DOC_ID="$(printf '%s' "$UPLOAD_RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl -fsS "http://127.0.0.1/api/documents/$DOC_ID"
```

Restart the stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod restart
```

Confirm the database still has documents:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec db \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from documents;"'
```

Confirm uploads are still present:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend \
  python -c "from pathlib import Path; print(len(list(Path('/app/uploads').glob('*'))))"
```

## Gemma-Backed Evaluation

Run the strict Gemma API evaluation harness from a checkout on the server. This uses the deployed backend URL and preserves existing Gemma provider-chain validation.

```bash
cd backend
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/run_quality_eval.py \
  --mode gemma \
  --backend-url http://127.0.0.1 \
  --label prod-gemma-smoke \
  --poll-timeout 900 \
  --upload-timeout 900 \
  --cleanup
```

The report fails if Gemma mode is requested but the final provider chain does not prove Gemma participation.

## Notes And Risks

- TLS is not terminated by `infra/nginx.prod.conf`. Put this stack behind a server TLS proxy/load balancer or extend nginx with certificates before exposing it directly.
- `INSTALL_AI_DEPS=true` installs heavy AI packages into the backend image. GPU servers may need a CUDA-specific base image or torch wheel strategy.
- The nginx upload limit is `64m`; keep it aligned with `MAX_UPLOAD_MB`.
- `PROCESSING_MODE` remains `inline`, matching the current app architecture. Large Gemma inference can keep upload requests open for a long time.
