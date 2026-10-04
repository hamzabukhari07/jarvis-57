"""
core/file_reader.py — ZEZO Unified Multi-Format File Ingestion Engine

Architecture & Extraction Ladder:
1. Text / Code (.txt, .py, .js, .json, .csv, .md, .yaml, etc.) → Direct read (encoding fallback)
2. Office (.docx, .xlsx, .pptx) + HTML, EPUB → Microsoft MarkItDown
3. Simple PDF → MarkItDown
4. Scanned / Complex PDF (quality check fallback) → Gemini REST Multimodal Document API → Lazy Docling
5. Images (.png, .jpg, .webp, etc.) → Gemini Multimodal Vision / Live
6. Archives (.zip, .tar, .7z) → Structure inspection & recursive reader
7. Truncation Guard → Default 64KB (65,536 chars) limit with notice

Architect: Hamza Bukhari
"""

from __future__ import annotations

import base64
import io
import logging
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Mute noisy document parser loggers to prevent audio thread lag and terminal flooding
for _noisy_mod in (
    "pdfminer", "pdfminer.psparser", "pdfminer.pdfinterp", "pdfminer.cmapdb",
    "pdfminer.pdfpage", "pdfminer.pdfdocument", "pypdf", "pdfplumber",
    "fitz", "markitdown", "docx", "pptx", "openpyxl"
):
    logging.getLogger(_noisy_mod).setLevel(logging.WARNING)

# Text & Code Extensions
TEXT_CODE_EXTS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml",
    ".csv", ".tsv", ".xml", ".log", ".ini", ".toml", ".html", ".htm", ".css",
    ".scss", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
    ".java", ".kt", ".swift", ".sql", ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ".r", ".lua", ".dockerfile", ".env", ".cfg", ".rst", ".tex"
}

# Modern Office & Document Extensions supported by MarkItDown
OFFICE_EXTS = {
    ".docx", ".xlsx", ".pptx", ".pdf", ".epub", ".odt", ".ods", ".odp", ".rtf"
}

# Image Extensions
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".svg", ".ico"
}

# Archive Extensions
ARCHIVE_EXTS = {
    ".zip", ".tar", ".gz", ".tar.gz", ".tgz", ".bz2", ".7z", ".rar"
}

# Legacy Office Formats requiring conversion
LEGACY_OFFICE_EXTS = {
    ".doc", ".xls", ".ppt"
}

DEFAULT_MAX_CHARS = 65536  # 64 KB


def _norm_token(s: str) -> str:
    return re.sub(r"[\s_\-]+", "", s.lower())


def _get_desktop() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Desktop"


def _get_downloads() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_DOWNLOAD_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Downloads"


def _get_documents() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_DOCUMENTS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Documents"


def _get_pictures() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_PICTURES_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Pictures"


def _get_music() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_MUSIC_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Music"


def _get_videos() -> Path:
    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_VIDEOS_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Videos"


def fuzzy_find_in_dir(parent: Path, target_name: str) -> Path | None:
    """Finds an existing child file/folder inside parent using exact, case-insensitive, or normalized fuzzy matching."""
    if not parent.exists() or not parent.is_dir() or not target_name:
        return None

    direct = parent / target_name
    if direct.exists():
        return direct

    target_norm = _norm_token(target_name)
    if not target_norm:
        return None

    try:
        children = list(parent.iterdir())
    except Exception:
        return None

    # 1. Exact case-insensitive match
    for child in children:
        if child.name.lower() == target_name.lower():
            return child

    # 2. Normalized token match (ignores spaces, underscores, hyphens, case)
    for child in children:
        if _norm_token(child.name) == target_norm:
            return child

    # 3. Normalized substring match (prioritizing exact prefix/stem match)
    matches = []
    for child in children:
        child_norm = _norm_token(child.name)
        if target_norm in child_norm or child_norm in target_norm:
            matches.append(child)

    if matches:
        if Path(target_name).suffix:
            file_matches = [p for p in matches if p.is_file()]
            if file_matches:
                file_matches.sort(key=lambda p: len(p.name))
                return file_matches[0]
            return None
        matches.sort(key=lambda p: (not p.is_dir(), len(p.name)))
        return matches[0]

    return None


def resolve_path(raw: str | Path) -> Path:
    """
    Universal path resolver for ZEZO.
    Handles:
      - Absolute paths
      - Shorthands (desktop, downloads, documents, pictures, music, videos, home)
      - Nested relative paths (e.g., 'desktop/Spider-Man/Hamza Bukhari Resume.pdf')
      - Fuzzy directory/file name matching at each folder level
      - Windows hallucinated username remapping (e.g. C:\\Users\\xyz\\Desktop -> C:\\Users\\current\\Desktop)
    """
    shortcuts: dict[str, Path] = {
        "desktop":   _get_desktop(),
        "downloads": _get_downloads(),
        "documents": _get_documents(),
        "pictures":  _get_pictures(),
        "music":     _get_music(),
        "videos":    _get_videos(),
        "home":      Path.home(),
    }

    raw_str = str(raw or "").strip().strip('"').strip("'")
    if not raw_str:
        return Path.cwd()

    # Direct shortcut exact match
    lower = raw_str.lower()
    if lower in shortcuts:
        return shortcuts[lower]

    # Convert Windows backslashes
    clean_parts = [p for p in raw_str.replace("\\", "/").split("/") if p and p != "."]
    if not clean_parts:
        return Path.cwd()

    first_part = clean_parts[0].lower()
    if first_part in shortcuts:
        curr = shortcuts[first_part]
        # Step through remaining components with recursive fuzzy match
        for part in clean_parts[1:]:
            cand = curr / part
            if cand.exists():
                curr = cand
            else:
                fuzzy = fuzzy_find_in_dir(curr, part)
                if fuzzy:
                    curr = fuzzy
                else:
                    curr = cand
        return curr

    # Expand user ~
    p = Path(raw_str).expanduser()
    if p.is_absolute() and p.exists():
        return p

    # Auto-remap hallucinated Windows usernames (e.g. C:\Users\xyz\Desktop\... -> C:\Users\<Current>\Desktop\...)
    parts = [part.lower() for part in p.parts]
    for key in ("desktop", "downloads", "documents", "pictures", "music", "videos"):
        if key in parts:
            idx = parts.index(key)
            subpath = Path(*p.parts[idx:])
            remapped = Path.home() / subpath
            if remapped.exists():
                return remapped
            # Try fuzzy resolve starting from shortcut
            root = shortcuts.get(key, Path.home() / key)
            curr = root
            for part in p.parts[idx+1:]:
                cand = curr / part
                if cand.exists():
                    curr = cand
                else:
                    fuzzy = fuzzy_find_in_dir(curr, part)
                    if fuzzy:
                        curr = fuzzy
                    else:
                        curr = cand
            if curr.exists():
                return curr

    if p.exists():
        return p.resolve()

    # If it's relative without shortcut prefix, check common directories (Desktop, Downloads, Documents, CWD)
    for root_dir in (_get_desktop(), _get_downloads(), _get_documents(), Path.cwd(), Path.home()):
        curr = root_dir
        for part in clean_parts:
            cand = curr / part
            if cand.exists():
                curr = cand
            else:
                fuzzy = fuzzy_find_in_dir(curr, part)
                if fuzzy:
                    curr = fuzzy
                else:
                    curr = cand
        if curr.exists():
            return curr

    return p


class ReadResult(NamedTuple):
    text: str
    engine: str
    file_type: str
    is_truncated: bool
    original_len: int


def _read_text_direct(path: Path) -> str:
    """Read plain text/code files using robust encoding fallback ladder."""
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {e}")
    # Raw binary fallback decode with replacement
    return path.read_bytes().decode("utf-8", errors="replace")


def _extract_pdf_annotations(path: Path) -> list[str]:
    """Extract embedded URI links / annotations directly from PDF object stream."""
    links: set[str] = set()
    try:
        data = path.read_bytes()
        # 1. Regex search for PDF URI annotations: /URI (http...) or /URI <hex>
        for m in re.finditer(rb'/URI\s*\((https?://[^)]+)\)', data, re.IGNORECASE):
            try:
                url = m.group(1).decode("utf-8", errors="ignore").strip()
                if url:
                    links.add(url)
            except Exception:
                pass
        for m in re.finditer(rb'/URI\s*<([0-9a-fA-F]+)>', data):
            try:
                decoded = bytes.fromhex(m.group(1).decode("ascii")).decode("utf-8", errors="ignore").strip()
                if decoded.startswith("http"):
                    links.add(decoded)
            except Exception:
                pass
    except Exception:
        pass
    return sorted(list(links))


def extract_links_and_socials(text: str, extra_urls: list[str] | None = None) -> dict[str, list[str]]:
    """Extract structured social media, portfolios, github, linkedin, email, and web links from text and annotations."""
    urls: set[str] = set(extra_urls or [])

    # URL regex matching http, https, www, or raw domain formats
    url_pattern = r'(?:https?://|www\.)[^\s<>"\'\)\]\}]+'
    for u in re.findall(url_pattern, text):
        clean_u = u.rstrip(".,;:)\"\'")
        urls.add(clean_u)

    # Social specific matches (even without http/https, e.g. github.com/username)
    social_text_patterns = [
        r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?',
        r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9_.-]+',
        r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+',
        r'(?:https?://)?(?:www\.)?behance\.net/[A-Za-z0-9_.-]+',
        r'(?:https?://)?(?:www\.)?dribbble\.com/[A-Za-z0-9_.-]+',
        r'(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?[A-Za-z0-9_.-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/(?:@[A-Za-z0-9_.-]+|c/[A-Za-z0-9_.-]+|channel/[A-Za-z0-9_.-]+)',
        r'(?:https?://)?youtu\.be/[A-Za-z0-9_-]+',
        r'(?:https?://)?(?:www\.)?reddit\.com/(?:u|user|r)/[A-Za-z0-9_]+',
    ]
    for sp in social_text_patterns:
        for match in re.findall(sp, text, re.IGNORECASE):
            urls.add(match.strip())

    categorized: dict[str, set[str]] = {
        "github": set(),
        "linkedin": set(),
        "twitter": set(),
        "portfolio": set(),
        "youtube": set(),
        "reddit": set(),
        "design": set(),
        "other_links": set(),
        "emails": set(),
        "phones": set(),
    }

    # Extract emails
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    for em in re.findall(email_pattern, text):
        categorized["emails"].add(em.strip())

    # Extract phone numbers
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    for ph in re.findall(phone_pattern, text):
        if len(ph.strip()) >= 10:
            categorized["phones"].add(ph.strip())

    for u in urls:
        u_lower = u.lower()
        if "github.com" in u_lower:
            categorized["github"].add(u)
        elif "linkedin.com" in u_lower:
            categorized["linkedin"].add(u)
        elif "twitter.com" in u_lower or "x.com" in u_lower:
            categorized["twitter"].add(u)
        elif "youtube.com" in u_lower or "youtu.be" in u_lower:
            categorized["youtube"].add(u)
        elif "reddit.com" in u_lower:
            categorized["reddit"].add(u)
        elif "behance.net" in u_lower or "dribbble.com" in u_lower:
            categorized["design"].add(u)
        elif any(ext in u_lower for ext in (".dev", ".me", ".io", ".app", ".site", "portfolio", "vercel.app", "netlify.app")):
            categorized["portfolio"].add(u)
        else:
            categorized["other_links"].add(u)

    return {k: sorted(list(v)) for k, v in categorized.items() if v}


def format_links_summary(links_dict: dict[str, list[str]]) -> str:
    """Format extracted links into an elegant markdown section."""
    if not links_dict:
        return ""
    lines = ["\n\n## 🔗 Extracted Links, Profiles & Contact Info:"]
    if "github" in links_dict:
        lines.append(f"- **GitHub:** {', '.join(links_dict['github'])}")
    if "linkedin" in links_dict:
        lines.append(f"- **LinkedIn:** {', '.join(links_dict['linkedin'])}")
    if "portfolio" in links_dict:
        lines.append(f"- **Portfolio / Website:** {', '.join(links_dict['portfolio'])}")
    if "twitter" in links_dict:
        lines.append(f"- **Twitter / X:** {', '.join(links_dict['twitter'])}")
    if "youtube" in links_dict:
        lines.append(f"- **YouTube:** {', '.join(links_dict['youtube'])}")
    if "reddit" in links_dict:
        lines.append(f"- **Reddit:** {', '.join(links_dict['reddit'])}")
    if "design" in links_dict:
        lines.append(f"- **Design (Behance / Dribbble):** {', '.join(links_dict['design'])}")
    if "emails" in links_dict:
        lines.append(f"- **Email:** {', '.join(links_dict['emails'])}")
    if "phones" in links_dict:
        lines.append(f"- **Phone:** {', '.join(links_dict['phones'])}")
    if "other_links" in links_dict:
        lines.append(f"- **Other Links:** {', '.join(links_dict['other_links'][:10])}")
    return "\n".join(lines)


def _get_pdf_page_count(path: Path) -> int:
    """Fast lightweight page counter for PDF quality evaluation."""
    try:
        data = path.read_bytes()
        pages = len(re.findall(rb"/Type\s*/Page\b", data))
        return max(1, pages)
    except Exception:
        return 1


def _is_scanned_pdf(content: str, page_count: int) -> bool:
    """Detect if a PDF is scanned (image-based) vs native text-based."""
    if not content or len(content.strip()) < 50:
        return True
    # If average characters per page is below 100, it is likely scanned / graphic
    if page_count > 0 and (len(content.strip()) / page_count) < 100:
        return True
    return False


def _read_with_markitdown(path: Path) -> str | None:
    """Extract markdown from Office & PDF using Microsoft MarkItDown."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(path))
        if result and result.text_content:
            return result.text_content.strip()
    except ImportError:
        pass
    except Exception as e:
        print(f"[FileReader] MarkItDown error on {path.name}: {e}")
    return None


def _read_with_pdfplumber(path: Path) -> str | None:
    """Local text-layer PDF extraction via pdfplumber (free, offline).

    Runs before the paid Gemini path so native PDFs never spend a cloud call and
    never depend on MarkItDown being installed. Returns None for scanned PDFs
    (no text layer), which then fall through to Gemini OCR.
    """
    try:
        import pdfplumber
        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    pages.append(txt)
        out = "\n\n".join(pages).strip()
        if out:
            print(f"[FileReader] [PDFPLUMBER] Extracted {len(out):,} characters from '{path.name}'.")
            return out
    except ImportError:
        pass
    except Exception as e:
        print(f"[FileReader] pdfplumber error on {path.name}: {e}")
    return None


def _read_office_local(path: Path, ext: str) -> str | None:
    """Local Office text extraction via the installed python-docx / openpyxl / python-pptx.

    Used when MarkItDown is not installed, so .docx/.xlsx/.pptx still read offline
    instead of falling through to a raw binary decode that yields garbage.
    """
    try:
        if ext == ".docx":
            import docx
            doc = docx.Document(str(path))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        parts.append(" | ".join(cells))
            out = "\n".join(parts).strip()
        elif ext in (".xlsx", ".xlsm"):
            import openpyxl
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            lines: list[str] = []
            for ws in wb.worksheets:
                lines.append(f"# Sheet: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    vals = ["" if v is None else str(v) for v in row]
                    if any(vals):
                        lines.append("\t".join(vals))
            wb.close()
            out = "\n".join(lines).strip()
        elif ext == ".pptx":
            from pptx import Presentation
            prs = Presentation(str(path))
            lines = []
            for i, slide in enumerate(prs.slides, 1):
                lines.append(f"# Slide {i}")
                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text_frame.text.strip():
                        lines.append(shape.text_frame.text.strip())
            out = "\n".join(lines).strip()
        else:
            return None
        if out:
            print(f"[FileReader] [OFFICE_LOCAL] Extracted {len(out):,} characters from '{path.name}'.")
            return out
    except ImportError:
        pass
    except Exception as e:
        print(f"[FileReader] local Office reader error on {path.name}: {e}")
    return None


# Inline base64 uploads above this size exceed the socket write timeout on slow
# links, so larger documents go through the resumable Files API upload instead.
_INLINE_LIMIT_BYTES = 2 * 1024 * 1024


def _extract_via_files_api(path: Path, prompt: str) -> str | None:
    """Extract a large document by uploading it to the Gemini Files API first.

    Inline base64 uploads of multi-MB files hit the socket write timeout on slow
    connections — that is what broke the scanned-PDF path. The Files API uses a
    resumable upload and returns a reference the REST models generate from. The
    Live rung is skipped because it cannot carry documents.
    """
    try:
        from core import gemini
        cl = gemini.client(timeout_ms=300_000)
        uploaded = cl.files.upload(file=str(path))
        resp = gemini.call([prompt, uploaded], tier=gemini.SMART,
                           timeout_ms=180_000, allow_live=False)
        if resp is not None:
            text = (getattr(resp, "text", None) or "").strip()
            if text:
                print(f"[FileReader] [FILES_API] Extracted {len(text):,} characters from '{path.name}'.")
                return text
    except Exception as e:
        print(f"[FileReader] Files API error on {path.name}: {e}")
    return None


def _read_with_gemini_rest(path: Path, instruction: str = "",
                           allow_live: bool = True) -> str | None:
    """One-shot multimodal document/image extraction via the canonical ladder.

    Routed through ``core.gemini.call()`` instead of a raw client with hardcoded,
    now-retired model names. Documents pass ``allow_live=False`` because the Live
    realtime session cannot carry them (a multi-MB PDF closes it with 1006).
    Files larger than ``_INLINE_LIMIT_BYTES`` use the Files API to avoid inline
    upload timeouts.
    """
    try:
        from core import gemini
        from google.genai import types as gtypes

        prompt = instruction or (
            "Read and extract all text, structure, tables, and content from this document. "
            "Format the output as clean GitHub-flavored Markdown. Preserve mathematical formulas and tables."
        )

        # Large documents: resumable Files API upload (inline base64 times out).
        if path.stat().st_size > _INLINE_LIMIT_BYTES:
            text = _extract_via_files_api(path, prompt)
            if text:
                return text

        data_bytes = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            if path.suffix.lower() == ".pdf":
                mime = "application/pdf"
            elif path.suffix.lower() in IMAGE_EXTS:
                mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            else:
                mime = "application/octet-stream"

        part = gtypes.Part.from_bytes(data=data_bytes, mime_type=mime)
        resp = gemini.call([prompt, part], tier=gemini.SMART, timeout_ms=120_000,
                           allow_live=allow_live)
        if resp is not None:
            text = (getattr(resp, "text", None) or "").strip()
            if text:
                return text
    except Exception as e:
        print(f"[FileReader] Gemini multimodal error: {e}")
    return None


def _read_with_groq_vision(path: Path, instruction: str = "") -> str | None:
    """Free-tier multimodal image understanding via Groq (Llama 4 Scout / Qwen3-VL).

    Preferred over the paid Gemini REST vision path for dropped images when a
    Groq API key is configured. Returns None when Groq is unavailable so the
    caller can fall through to Gemini.
    """
    try:
        from memory.config_manager import get_groq_api_key, get_groq_vision_model
        if not get_groq_api_key():
            return None
        # Groq's free tier has no multimodal model today; only attempt when the
        # user has explicitly configured one, so we never waste a failed call.
        if not get_groq_vision_model():
            return None
        from core.llm_client import call_groq_vision

        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

        prompt = instruction or (
            "Read and extract all text, structure, tables, and visual content from this image. "
            "Format the output as clean GitHub-flavored Markdown. If it is a photo or diagram, "
            "describe it precisely and transcribe any visible text verbatim."
        )
        result = call_groq_vision(path.read_bytes(), mime, prompt)
        if result:
            print(f"[FileReader] [GROQ_VISION] Extracted {len(result):,} characters from '{path.name}'.")
            return result
    except Exception as e:
        print(f"[FileReader] Groq vision error on {path.name}: {e}")
    return None


def _read_with_docling_lazy(path: Path) -> str | None:
    """Lazy fallback for complex layout & tables using Docling (if installed)."""
    try:
        # Strict lazy import so docling is never loaded during cold startup
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        conv_res = converter.convert(str(path))
        doc = conv_res.document
        return doc.export_to_markdown()
    except ImportError:
        return None
    except Exception as e:
        print(f"[FileReader] Docling lazy OCR error: {e}")
        return None


def _read_archive_structure(path: Path) -> str:
    """Inspect and list the structure and files inside an archive."""
    ext = path.suffix.lower()
    lines = [f"# Archive: {path.name}", f"File Size: {path.stat().st_size:,} bytes", ""]
    lines.append("## Archive Contents:")

    try:
        if ext == ".zip":
            import zipfile
            with zipfile.ZipFile(path, "r") as z:
                for info in z.infolist()[:100]:
                    lines.append(f"- `{info.filename}` ({info.file_size:,} bytes)")
                if len(z.infolist()) > 100:
                    lines.append(f"\n... and {len(z.infolist()) - 100} more files.")
        elif ext in (".tar", ".gz", ".tgz", ".bz2"):
            import tarfile
            with tarfile.open(path, "r:*") as t:
                members = t.getmembers()
                for m in members[:100]:
                    lines.append(f"- `{m.name}` ({m.size:,} bytes)")
                if len(members) > 100:
                    lines.append(f"\n... and {len(members) - 100} more files.")
        elif ext == ".7z":
            try:
                import py7zr
                with py7zr.SevenZipFile(path, mode="r") as z:
                    for name in z.getnames()[:100]:
                        lines.append(f"- `{name}`")
            except ImportError:
                lines.append("Note: py7zr not installed. Run `pip install py7zr` for .7z inspection.")
        else:
            lines.append(f"Format {ext} supported for extraction.")
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to read archive: {e}"


def read_file(
    file_path: str | Path,
    max_chars: int = DEFAULT_MAX_CHARS,
    instruction: str = "",
) -> ReadResult:
    """
    Universal entry point to read and extract text from any file format.
    
    Returns ReadResult(text, engine, file_type, is_truncated, original_len).
    """
    # [ZEZO-INGESTION-DIAGNOSTIC] Verified runtime entrypoint
    path = resolve_path(file_path)
    if not path.exists() or not path.is_file():
        return ReadResult(
            text=f"Error: File '{file_path}' does not exist.",
            engine="none",
            file_type="missing",
            is_truncated=False,
            original_len=0
        )

    ext = path.suffix.lower()
    extracted_text = ""
    engine_used = "direct"
    detected_type = "text"

    # 1. Legacy Formats Guide
    if ext in LEGACY_OFFICE_EXTS:
        modern = ".docx" if ext == ".doc" else (".xlsx" if ext == ".xls" else ".pptx")
        msg = (
            f"Unsupported legacy format '{ext}'. "
            f"Please save or export the file as modern format '{modern}' for optimal AI processing."
        )
        return ReadResult(text=msg, engine="legacy_rejection", file_type="legacy", is_truncated=False, original_len=len(msg))

    # 2. Text / Code
    if ext in TEXT_CODE_EXTS or not ext:
        detected_type = "code" if ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".rs", ".go"} else "text"
        extracted_text = _read_text_direct(path)
        engine_used = "direct_read"

    # 3. Archives
    elif ext in ARCHIVE_EXTS:
        detected_type = "archive"
        extracted_text = _read_archive_structure(path)
        engine_used = "archive_inspector"

    # 4. Images
    elif ext in IMAGE_EXTS:
        detected_type = "image"
        # Free tier first: Groq vision, then paid Gemini REST, then metadata.
        groq_res = _read_with_groq_vision(path, instruction)
        if groq_res:
            extracted_text = groq_res
            engine_used = "groq_vision"
        else:
            gem_res = _read_with_gemini_rest(path, instruction)
            if gem_res:
                extracted_text = gem_res
                engine_used = "gemini_vision"
            else:
                extracted_text = f"Image file '{path.name}' ({path.stat().st_size:,} bytes) ready for visual analysis."
                engine_used = "image_metadata"

    # 5. Office & PDF
    elif ext in OFFICE_EXTS:
        detected_type = "document" if ext != ".pdf" else "pdf"

        if ext == ".pdf":
            # Local text first (fast & free): pdfplumber (<150ms), else MarkItDown, else pay for OCR.
            local_text = _read_with_pdfplumber(path) or _read_with_markitdown(path)
            page_cnt = _get_pdf_page_count(path)
            scanned = local_text is None or _is_scanned_pdf(local_text, page_cnt)
            extracted_len = len(local_text.strip()) if local_text else 0
            print(f"[FileReader] [PDF_SCAN] '{path.name}': is_scanned={scanned} (chars={extracted_len}, pages={page_cnt})")

            # PDF Quality Check
            if scanned:
                print(f"[FileReader] [GEMINI_REST] Invoking Gemini REST Document API for scanned PDF: {path.name}")
                # Fallback 1: Gemini Multimodal Document REST API (REST only — Live cannot carry PDFs)
                gem_doc = _read_with_gemini_rest(path, instruction, allow_live=False)
                if gem_doc:
                    extracted_text = gem_doc
                    engine_used = "gemini_document_api"
                    print(f"[FileReader] [OK] Gemini REST Document API extracted {len(gem_doc):,} characters.")
                else:
                    # Fallback 2: Lazy Docling
                    print(f"[FileReader] [DOCLING] Invoking Lazy Docling OCR fallback for: {path.name}")
                    docling_text = _read_with_docling_lazy(path)
                    if docling_text:
                        extracted_text = docling_text
                        engine_used = "docling_lazy"
                        print(f"[FileReader] [OK] Docling OCR extracted {len(docling_text):,} characters.")
                    else:
                        extracted_text = local_text or "Could not extract text from scanned PDF."
                        engine_used = "markitdown_low_quality"
            else:
                extracted_text = local_text
                engine_used = "pdfplumber"
                print(f"[FileReader] [OK] Local PDF text extracted {len(local_text):,} characters.")
        else:
            # Local text first (free): MarkItDown, else python-docx/openpyxl/python-pptx.
            local_text = _read_with_markitdown(path) or _read_office_local(path, ext)
            if local_text:
                extracted_text = local_text
                engine_used = "office_local"
                print(f"[FileReader] [OK] Local extraction yielded {len(local_text):,} characters from '{path.name}'.")
            else:
                # Fallback to direct read or raw decode
                extracted_text = _read_text_direct(path)
                engine_used = "fallback_direct"
                print(f"[FileReader] [WARN] Fallback direct read extracted {len(extracted_text):,} characters from '{path.name}'.")

    # 6. Unknown extension
    else:
        detected_type = "unknown"
        # Attempt MarkItDown
        md_try = _read_with_markitdown(path)
        if md_try:
            extracted_text = md_try
            engine_used = "markitdown_unknown"
        else:
            try:
                extracted_text = _read_text_direct(path)
                engine_used = "direct_unknown"
            except Exception:
                extracted_text = f"Unsupported file format '{ext}'. Cannot read content directly."
                engine_used = "unsupported"

    # 7. Extract links, PDF annotations & social profiles
    if extracted_text and detected_type in ("document", "pdf", "text", "code", "unknown"):
        extra_pdf_urls = _extract_pdf_annotations(path) if ext == ".pdf" else []
        links_data = extract_links_and_socials(extracted_text, extra_urls=extra_pdf_urls)
        links_summary = format_links_summary(links_data)
        if links_summary and "Extracted Links, Profiles & Contact Info" not in extracted_text:
            extracted_text += links_summary

    orig_len = len(extracted_text)
    is_trunc = False

    # Apply 64KB truncation guard
    if max_chars > 0 and orig_len > max_chars:
        print(f"[FileReader] [TRUNCATED] Guard triggered: {orig_len:,} chars exceeds limit of {max_chars:,} chars.")
        extracted_text = (
            extracted_text[:max_chars]
            + f"\n\n[TRUNCATED: Showing first {max_chars:,} of {orig_len:,} characters. "
            f"Target specific sections or search for details.]"
        )
        is_trunc = True

    print(f"[FileReader] [DONE] Completed '{path.name}' | Type: {detected_type} | Engine: {engine_used} | Output: {len(extracted_text):,} chars (truncated: {is_trunc})")

    return ReadResult(
        text=extracted_text,
        engine=engine_used,
        file_type=detected_type,
        is_truncated=is_trunc,
        original_len=orig_len
    )
