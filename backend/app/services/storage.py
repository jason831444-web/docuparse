import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}


class LocalStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.upload_dir

    def validate_upload(self, file: UploadFile) -> None:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Only JPG, JPEG, and PNG images are supported.")

    def save_upload(self, file: UploadFile) -> Path:
        self.validate_upload(file)
        suffix = ALLOWED_IMAGE_TYPES[file.content_type or ""]
        destination = self.root / f"{uuid.uuid4()}{suffix}"
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if destination.stat().st_size > max_bytes:
            destination.unlink(missing_ok=True)
            raise ValueError(f"File is larger than {self.settings.max_upload_mb} MB.")
        return destination

    def delete(self, stored_path: str | None) -> None:
        if not stored_path:
            return
        Path(stored_path).unlink(missing_ok=True)

    def public_url(self, stored_path: str) -> str:
        return f"{self.settings.backend_base_url}/uploads/{Path(stored_path).name}"
