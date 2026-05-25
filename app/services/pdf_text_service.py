import fitz
from fastapi import HTTPException, status


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    try:
        pdf_document = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )

        pages_text = []

        for page in pdf_document:
            pages_text.append(page.get_text())

        pdf_document.close()

        text = "\n".join(pages_text).strip()

        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract readable text from PDF"
            )

        return text

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract text from PDF"
        )