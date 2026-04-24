import os

from app.db.session import SessionLocal
from app.services.document_worker import DocumentWorker


def main() -> None:
    poll_seconds = float(os.getenv("WORKER_POLL_SECONDS", "2"))
    DocumentWorker().run_forever(SessionLocal, poll_seconds=poll_seconds)


if __name__ == "__main__":
    main()
