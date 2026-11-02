from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx


ALLOWED_SUFFIXES = {".txt", ".md", ".csv", ".json", ".geojson", ".pdf", ".docx"}
INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "reveal your prompt",
)


@dataclass(frozen=True)
class ExtractedSource:
    name: str
    media_type: str
    sha256: str
    text: str
    untrusted_instruction_count: int
    pii_redactions: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mediaType": self.media_type,
            "sha256": self.sha256,
            "text": self.text,
            "untrustedInstructionCount": self.untrusted_instruction_count,
            "piiRedactions": self.pii_redactions,
        }


def extract_bytes(name: str, content: bytes, media_type: str, max_bytes: int) -> ExtractedSource:
    if len(content) > max_bytes:
        raise ValueError(f"Source exceeds {max_bytes} byte limit")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported source type: {suffix or 'unknown'}")
    _validate_magic(suffix, content)
    if suffix == ".pdf":
        text = _extract_pdf(content)
    elif suffix == ".docx":
        text = _extract_docx(content)
    else:
        text = content.decode("utf-8", errors="replace")
        if suffix in {".json", ".geojson"}:
            json.loads(text)
    text, redactions = _redact_pii(text)
    lowered = text.lower()
    injection_count = sum(lowered.count(pattern) for pattern in INJECTION_PATTERNS)
    # Evidence is stored as untrusted quoted content; suspicious instructions
    # remain visible for audit but cannot enter system/developer prompts.
    return ExtractedSource(
        name=Path(name).name,
        media_type=media_type or "application/octet-stream",
        sha256=hashlib.sha256(content).hexdigest(),
        text=text[:200_000],
        untrusted_instruction_count=injection_count,
        pii_redactions=redactions,
    )


async def fetch_public_url(url: str, max_bytes: int) -> ExtractedSource:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP(S) URLs are accepted")
    await _assert_public_host(parsed.hostname)
    async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
        response = await client.get(url, headers={"User-Agent": "MetroPulse/1.0"})
        if 300 <= response.status_code < 400:
            raise ValueError("Redirecting source URLs are not accepted")
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get("content-type", "text/plain").split(";")[0]
        suffix = _suffix_for_content_type(content_type) or Path(parsed.path).suffix or ".txt"
        return extract_bytes(
            Path(parsed.path).name or f"remote-source{suffix}",
            content,
            content_type,
            max_bytes,
        )


async def _assert_public_host(hostname: str) -> None:
    addresses = await __import__("asyncio").to_thread(socket.getaddrinfo, hostname, None)
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
        ):
            raise ValueError("Source URL resolves to a non-public address")


def _validate_magic(suffix: str, content: bytes) -> None:
    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        raise ValueError("PDF extension does not match file content")
    if suffix == ".docx" and not content.startswith(b"PK"):
        raise ValueError("DOCX extension does not match file content")


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF extraction dependency is unavailable") from exc
    reader = PdfReader(BytesIO(content))
    if len(reader.pages) > 200:
        raise ValueError("PDF exceeds 200 page limit")
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("DOCX extraction dependency is unavailable") from exc
    document = Document(BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _redact_pii(text: str) -> tuple[str, int]:
    patterns = (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)"),
    )
    count = 0
    for pattern in patterns:
        text, replacements = pattern.subn("[REDACTED]", text)
        count += replacements
    return text, count


def _suffix_for_content_type(content_type: str) -> str:
    return {
        "text/plain": ".txt",
        "text/markdown": ".md",
        "text/csv": ".csv",
        "application/json": ".json",
        "application/geo+json": ".geojson",
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }.get(content_type, "")

