import io
from PIL import Image
import pytesseract
import PyPDF2
import platform

# For Windows, point pytesseract to the absolute executable path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_bytes: io.BytesIO) -> str:
    """
    Extract text from an image using Tesseract OCR.
    Ensure tesseract is installed on the host machine.
    """
    try:
        img = Image.open(image_bytes)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""

def extract_text_from_pdf(pdf_bytes: io.BytesIO) -> str:
    """
    Extract text from a PDF file.
    """
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
