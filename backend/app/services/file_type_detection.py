import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}
TEXT_EXTENSIONS = {"txt", "md", "csv", "json", "xml", "html", "htm"}
OFFICE_EXTENSIONS = {"docx", "xlsx", "pptx"}
PARTIAL_EXTENSIONS = {"doc", "xls", "ppt", "rtf", "odt", "ods", "odp", "epub", "eml", "msg"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS | OFFICE_EXTENSIONS | PARTIAL_EXTENSIONS | {"pdf"}


@dataclass(frozen=True)
class DetectedFileType:
    extension: str
    mime_type: str
    family: str
    supported: bool
    partial: bool = False
    warning: str | None = None


class FileTypeDetector:
    def detect(self, path: Path, original_filename: str = "", declared_mime: str | None = None) -> DetectedFileType:
        suffix = self._extension(original_filename or path.name)
        header = self._header(path)
        magic_type = self._magic_type(header)
        if magic_type:
            family, extension, mime_type = magic_type
            if suffix in OFFICE_EXTENSIONS and self._is_office_zip(path, suffix):
                family, extension, mime_type = self._office_type(suffix)
            return DetectedFileType(extension, mime_type, family, True)

        if suffix in OFFICE_EXTENSIONS and self._is_office_zip(path, suffix):
            family, extension, mime_type = self._office_type(suffix)
            return DetectedFileType(extension, mime_type, family, True)

        mime_type = declared_mime or mimetypes.guess_type(original_filename or path.name)[0] or "application/octet-stream"
        if suffix in IMAGE_EXTENSIONS:
            return DetectedFileType(suffix, mime_type, "image", True)
        if suffix == "pdf":
            return DetectedFileType(suffix, "application/pdf", "pdf", True)
        if suffix in TEXT_EXTENSIONS:
            return DetectedFileType(suffix, mime_type, self._text_family(suffix), True)
        if suffix in OFFICE_EXTENSIONS:
            return DetectedFileType(suffix, mime_type, "office", True)
        if suffix in PARTIAL_EXTENSIONS:
            return DetectedFileType(
                suffix,
                mime_type,
                "partial",
                True,
                partial=True,
                warning=f"{suffix.upper()} support is best-effort in this MVP.",
            )
        return DetectedFileType(
            suffix or "unknown",
            mime_type,
            "unknown",
            False,
            warning="Unsupported file type.",
        )

    def allowed_extensions(self) -> set[str]:
        return set(SUPPORTED_EXTENSIONS)

    def _extension(self, filename: str) -> str:
        return Path(filename).suffix.lower().lstrip(".")

    def _header(self, path: Path) -> bytes:
        try:
            with path.open("rb") as handle:
                return handle.read(16)
        except OSError:
            return b""

    def _magic_type(self, header: bytes) -> tuple[str, str, str] | None:
        if header.startswith(b"%PDF"):
            return ("pdf", "pdf", "application/pdf")
        if header.startswith(b"\xff\xd8\xff"):
            return ("image", "jpg", "image/jpeg")
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ("image", "png", "image/png")
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return ("image", "webp", "image/webp")
        if header.startswith(b"BM"):
            return ("image", "bmp", "image/bmp")
        if header.startswith((b"II*\x00", b"MM\x00*")):
            return ("image", "tiff", "image/tiff")
        return None

    def _is_office_zip(self, path: Path, suffix: str) -> bool:
        if suffix not in OFFICE_EXTENSIONS:
            return False
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return False
        if suffix == "docx":
            return any(name.startswith("word/") for name in names)
        if suffix == "xlsx":
            return any(name.startswith("xl/") for name in names)
        if suffix == "pptx":
            return any(name.startswith("ppt/") for name in names)
        return False

    def _office_type(self, suffix: str) -> tuple[str, str, str]:
        return {
            "docx": ("office", "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "xlsx": ("office", "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "pptx": ("office", "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        }[suffix]

    def _text_family(self, suffix: str) -> str:
        if suffix == "csv":
            return "tabular"
        if suffix in {"html", "htm", "xml"}:
            return "markup"
        return "text"
