import io
import logging

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_INSTALLED = True
except ImportError:
    WEASYPRINT_INSTALLED = False

logger = logging.getLogger('ats_resume_scorer')

import logging
from weasyprint import HTML

logger = logging.getLogger("ats_resume_scorer")

def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    if not WEASYPRINT_INSTALLED:
        raise ImportError("WeasyPrint is not installed.")

    try:
        logger.info(f"Received {len(html_docs)} HTML documents")

        documents = []

        for name, html_str in html_docs.items():
            logger.info(f"Rendering {name}")

            if not html_str:
                raise ValueError(f"{name} HTML is empty")

            doc = HTML(string=html_str).render()
            documents.append(doc)

        logger.info("All documents rendered successfully")

        first_doc = documents[0]

        for other_doc in documents[1:]:
            first_doc.pages.extend(other_doc.pages)

        logger.info("Writing PDF...")

        pdf_bytes = first_doc.write_pdf()

        logger.info("PDF generated successfully")

        return pdf_bytes

    except Exception:
        logger.exception("PDF generation failed")
        raise