"""PDF text extraction utilities for credit agreements."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("PyPDF2 not installed. PDF extraction will not be available. Install with: pip install PyPDF2")


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        Extracted text content as a string.
        
    Raises:
        ImportError: If PyPDF2 is not installed.
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If PDF extraction fails.
    """
    if not PDF_SUPPORT:
        raise ImportError(
            "PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2"
        )
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        text_parts = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            logger.info(f"Extracting text from PDF: {len(pdf_reader.pages)} pages")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                    logger.debug(f"Extracted text from page {page_num}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    continue
        
        full_text = "\n\n".join(text_parts)
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from the PDF")
        
        logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
        return full_text
        
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e

