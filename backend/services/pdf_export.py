"""PDF generation with a pure-Python fallback when WeasyPrint's native stack is absent."""

import logging
import textwrap
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Tuple

logger = logging.getLogger("ats_resume_scorer")

try:
    from weasyprint import HTML as _WeasyHTML
except Exception as exc:  # WeasyPrint may be installed while GTK/Pango DLLs are missing.
    _WeasyHTML = None
    logger.warning("WeasyPrint unavailable; reports will use the built-in PDF renderer: %s", exc)


class _ReportTextParser(HTMLParser):
    """Extract readable report text and heading hierarchy from rendered HTML."""

    BLOCK_TAGS = {"address", "article", "blockquote", "dd", "div", "dl", "dt", "footer", "header", "li", "main", "ol", "p", "section", "table", "tr", "ul"}
    HEADING_SIZES = {"h1": 17, "h2": 13, "h3": 11}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: List[Tuple[str, int, bool]] = []
        self.parts: List[str] = []
        self.skip_depth = 0
        self.heading_size = 10
        self.in_heading = False
        self.in_list_item = False

    def _flush(self) -> None:
        value = " ".join(" ".join(self.parts).split()).strip()
        self.parts.clear()
        if value:
            self.lines.append((value, self.heading_size, self.in_heading))

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("style", "script", "head", "title"):
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in self.HEADING_SIZES:
            self._flush()
            self.heading_size = self.HEADING_SIZES[tag]
            self.in_heading = True
        elif tag == "li":
            self._flush()
            self.parts.append("• ")
            self.in_list_item = True
        elif tag in {"br", "hr"}:
            self._flush()
        elif tag in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script", "head", "title"):
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in self.HEADING_SIZES:
            self._flush()
            self.heading_size = 10
            self.in_heading = False
        elif tag == "li":
            self._flush()
            self.in_list_item = False
        elif tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(data)


def _html_lines(html: str) -> List[Tuple[str, int, bool]]:
    parser = _ReportTextParser()
    parser.feed(html)
    parser.close()
    parser._flush()
    return parser.lines


def _wrap_lines(lines: Iterable[Tuple[str, int, bool]], width: int = 94) -> List[Tuple[str, int, bool]]:
    wrapped: List[Tuple[str, int, bool]] = []
    for text, size, bold in lines:
        safe = text.encode("ascii", "replace").decode("ascii")
        if not safe:
            continue
        char_width = max(35, int(width * 10 / max(size, 1)))
        for part in textwrap.wrap(safe, width=char_width, break_long_words=True, break_on_hyphens=False) or [""]:
            wrapped.append((part, size, bold))
    return wrapped


def _fallback_pdf(html_docs: Dict[str, str]) -> bytes:
    """Create a compact, searchable PDF using only Python's standard library."""
    report_lines: List[Tuple[str, int, bool]] = []
    labels = {
        "summary": "Score Summary",
        "skill_report": "Skill Validation and Content Analysis",
        "jd_report": "Job Description Match Analysis",
        "recommendations": "Recommendations and Project Plans",
    }
    for name, html in html_docs.items():
        if not html:
            raise ValueError(f"{name} HTML is empty")
        if report_lines:
            report_lines.append(("", 10, False))
        report_lines.append((f"ATS Resume Vision - {labels.get(name, name.replace('_', ' ').title())}", 16, True))
        report_lines.extend(_html_lines(html))

    wrapped = _wrap_lines(report_lines)
    page_lines: List[List[Tuple[str, int, bool]]] = [[]]
    y = 790
    for line in wrapped:
        size = line[1]
        leading = max(13, size + 4)
        if y - leading < 48:
            page_lines.append([])
            y = 790
        page_lines[-1].append(line)
        y -= leading

    def pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_ids = [5 + index * 2 for index in range(len(page_lines))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    for index, lines in enumerate(page_lines):
        page_id = 5 + index * 2
        content_id = page_id + 1
        commands = []
        y = 790
        for line, size, bold in lines:
            font = "F2" if bold else "F1"
            commands.append(f"BT /{font} {size} Tf 1 0 0 1 50 {y} Tm ({pdf_text(line)}) Tj ET")
            y -= max(13, size + 4)
        stream = "\n".join(commands).encode("ascii", "replace")
        objects.append((
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii"))
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n% ATS Resume Vision\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def generate_combined_pdf(html_docs: Dict[str, str]) -> bytes:
    if not html_docs:
        raise ValueError("No report sections were provided")
    for name, html in html_docs.items():
        if not html:
            raise ValueError(f"{name} HTML is empty")

    if _WeasyHTML is not None:
        try:
            documents = []
            for name, html in html_docs.items():
                logger.info("Rendering PDF section %s with WeasyPrint", name)
                documents.append(_WeasyHTML(string=html).render())
            first_doc = documents[0]
            for other_doc in documents[1:]:
                first_doc.pages.extend(other_doc.pages)
            pdf_bytes = first_doc.write_pdf()
            if pdf_bytes.startswith(b"%PDF-"):
                return pdf_bytes
            raise ValueError("WeasyPrint returned an invalid PDF")
        except Exception:
            logger.exception("WeasyPrint could not render the report; using built-in PDF renderer")

    pdf_bytes = _fallback_pdf(html_docs)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Built-in PDF renderer returned an invalid PDF")
    logger.info("PDF generated with built-in renderer (%d bytes)", len(pdf_bytes))
    return pdf_bytes
