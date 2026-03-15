import io
import os
import shutil
import platform
from PIL import Image
import pytesseract
import PyPDF2

# Determine tesseract executable path.
# On Windows, this defaults to the standard installer location.
# You can also override it by setting the environment variable TESSERACT_CMD.
def _find_tesseract_cmd() -> str:
    if "TESSERACT_CMD" in os.environ and os.environ["TESSERACT_CMD"].strip():
        return os.environ["TESSERACT_CMD"].strip()

    if platform.system() == "Windows":
        return r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # On macOS/Linux assume it's on the PATH.
    return "tesseract"

_tesseract_cmd = _find_tesseract_cmd()
_tesseract_available = shutil.which(_tesseract_cmd) is not None

if _tesseract_available:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
else:
    print(
        "Warning: Tesseract OCR not found. "
        f"Searched for '{_tesseract_cmd}'. "
        "Install Tesseract OCR and/or set the TESSERACT_CMD environment variable. "
        "OCR image uploads will be skipped."
    )


def extract_text_from_image(image_bytes: io.BytesIO) -> str:
    """Extract text from an image using Tesseract OCR."""
    if not _tesseract_available:
        return ""

    try:
        img = Image.open(image_bytes)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        # If something goes wrong during OCR, return an empty string and log for debugging.
        print(f"Error during OCR: {e}")
        return ""


def extract_text_from_pdf(pdf_bytes: io.BytesIO) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_bytes)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error during PDF extraction: {e}")
        return ""
