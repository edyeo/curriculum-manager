"""Source Loader — file/url/text → raw_text"""
from pathlib import Path
from typing import Literal

MAX_CHARS = 128_000  # ~32K tokens


def load(source_type: Literal["file", "url", "text"], source: str) -> str:
    if source_type == "text":
        return _truncate(source)
    if source_type == "file":
        return _load_file(source)
    if source_type == "url":
        return _load_url(source)
    raise ValueError(f"Unknown source_type: {source_type}")


def _truncate(text: str) -> str:
    return text[:MAX_CHARS]


def _load_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.suffix.lower() == ".pdf":
        return _truncate(_load_pdf(p))
    return _truncate(p.read_text(encoding="utf-8"))


def _load_pdf(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        raise RuntimeError("PyMuPDF required for PDF. Install: pip install pymupdf")
    doc = fitz.open(str(path))
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _load_url(url: str) -> str:
    import httpx
    from bs4 import BeautifulSoup

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return _truncate(soup.get_text(separator="\n", strip=True))
