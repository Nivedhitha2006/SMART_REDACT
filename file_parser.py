"""
file_parser.py — Extract plain text from any supported file type
Supported: .txt, .pdf, .docx, .pptx, .xlsx, .xls, .csv
"""

import io
from pathlib import Path


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from uploaded file bytes.

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename:   Original filename (used to detect type)

    Returns:
        Extracted plain text string

    Raises:
        ValueError: If file type is unsupported
        RuntimeError: If extraction fails
    """
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return _parse_txt(file_bytes)
    elif ext == ".pdf":
        return _parse_pdf(file_bytes)
    elif ext in (".docx",):
        return _parse_docx(file_bytes)
    elif ext in (".doc",):
        raise ValueError("Old .doc format is not supported. Please save as .docx and re-upload.")
    elif ext == ".pptx":
        return _parse_pptx(file_bytes)
    elif ext == ".ppt":
        raise ValueError("Old .ppt format is not supported. Please save as .pptx and re-upload.")
    elif ext in (".xlsx", ".xls"):
        return _parse_excel(file_bytes, ext)
    elif ext == ".csv":
        return _parse_csv(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: '{ext}'. "
            "Supported types: .txt, .pdf, .docx, .pptx, .xlsx, .xls, .csv"
        )


# ──────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────

def _parse_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _parse_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n".join(pages).strip()
        if not text:
            raise RuntimeError(
                "PDF appears to be scanned/image-based. "
                "No text could be extracted."
            )
        return text
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {str(e)}")


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        lines = []

        # Body paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text)

        # Tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    lines.append(row_text)

        return "\n".join(lines)
    except ImportError:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {str(e)}")


def _parse_pptx(data: bytes) -> str:
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data))
        lines = []

        for slide_num, slide in enumerate(prs.slides, start=1):
            lines.append(f"--- Slide {slide_num} ---")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            lines.append(text)

        return "\n".join(lines)
    except ImportError:
        raise RuntimeError("python-pptx not installed. Run: pip install python-pptx")
    except Exception as e:
        raise RuntimeError(f"PPTX extraction failed: {str(e)}")


def _parse_excel(data: bytes, ext: str) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(
            io.BytesIO(data),
            read_only=True,
            data_only=True
        )
        lines = []

        for sheet in wb.worksheets:
            lines.append(f"--- Sheet: {sheet.title} ---")
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(
                    str(cell) for cell in row if cell is not None and str(cell).strip()
                )
                if row_text:
                    lines.append(row_text)

        wb.close()
        return "\n".join(lines)
    except ImportError:
        raise RuntimeError("openpyxl not installed. Run: pip install openpyxl")
    except Exception as e:
        raise RuntimeError(f"Excel extraction failed: {str(e)}")


def _parse_csv(data: bytes) -> str:
    try:
        import csv
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(text.splitlines())
        lines = []
        for row in reader:
            row_text = " | ".join(cell.strip() for cell in row if cell.strip())
            if row_text:
                lines.append(row_text)
        return "\n".join(lines)
    except Exception as e:
        raise RuntimeError(f"CSV extraction failed: {str(e)}")