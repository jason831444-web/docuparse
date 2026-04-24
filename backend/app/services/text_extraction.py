import csv
import json
import re
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path
from typing import Any


class TextExtractionService:
    def extract(self, path: Path, extension: str) -> tuple[str, list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        content = self._read_text(path, warnings)
        if extension == "json":
            return self._json_text(content, warnings)
        if extension == "csv":
            return self._csv_text(content, warnings)
        if extension in {"html", "htm"}:
            return self._html_text(content, warnings)
        if extension == "xml":
            return self._xml_text(content, warnings)
        return self._plain_text(content), [{"type": extension, "content": self._plain_text(content)}], warnings

    def _read_text(self, path: Path, warnings: list[str]) -> str:
        data = path.read_bytes()
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        warnings.append("Could not confidently decode text; replacement characters were used.")
        return data.decode("utf-8", errors="replace")

    def _plain_text(self, content: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in content.splitlines()]
        return "\n".join(line for line in lines if line)

    def _json_text(self, content: str, warnings: list[str]) -> tuple[str, list[dict[str, Any]], list[str]]:
        try:
            payload = json.loads(content)
            lines = list(self._flatten_json(payload))
            text = "\n".join(lines) if lines else json.dumps(payload, ensure_ascii=False, indent=2)
            return text, [{"type": "json", "content": payload}], warnings
        except json.JSONDecodeError as exc:
            warnings.append(f"JSON parsing failed; indexed as plain text: {exc.msg}.")
            text = self._plain_text(content)
            return text, [{"type": "json_parse_failed", "content": text}], warnings

    def _flatten_json(self, value: Any, prefix: str = ""):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self._flatten_json(child, f"{prefix}.{key}" if prefix else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value[:200]):
                yield from self._flatten_json(child, f"{prefix}[{index}]")
        else:
            label = (prefix or "value").replace("_", " ")
            yield f"{label}: {value}"

    def _csv_text(self, content: str, warnings: list[str]) -> tuple[str, list[dict[str, Any]], list[str]]:
        try:
            sample = content[:4096]
            dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        except csv.Error:
            dialect = csv.excel
            warnings.append("CSV dialect could not be detected; default comma parsing was used.")
        reader = csv.reader(StringIO(content), dialect)
        rows = []
        for index, row in enumerate(reader):
            if index >= 500:
                warnings.append("CSV extraction limited to the first 500 rows.")
                break
            rows.append([cell.strip() for cell in row])
        text = "\n".join(" | ".join(cell for cell in row if cell) for row in rows if any(row))
        return text, [{"type": "csv_rows", "rows": rows[:100]}], warnings

    def _html_text(self, content: str, warnings: list[str]) -> tuple[str, list[dict[str, Any]], list[str]]:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n")
        except Exception as exc:
            warnings.append(f"HTML parser unavailable; fallback tag stripping used: {exc}.")
            text = re.sub(r"<[^>]+>", "\n", content)
        normalized = self._plain_text(text)
        return normalized, [{"type": "html_text", "content": normalized}], warnings

    def _xml_text(self, content: str, warnings: list[str]) -> tuple[str, list[dict[str, Any]], list[str]]:
        try:
            root = ET.fromstring(content)
            lines = []
            for element in root.iter():
                text = (element.text or "").strip()
                if text:
                    lines.append(f"{self._local_name(element.tag)}: {text}")
            normalized = "\n".join(lines)
            return normalized, [{"type": "xml_text", "content": normalized}], warnings
        except ET.ParseError as exc:
            warnings.append(f"XML parsing failed; indexed as plain text: {exc}.")
            normalized = self._plain_text(content)
            return normalized, [{"type": "xml_parse_failed", "content": normalized}], warnings

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
