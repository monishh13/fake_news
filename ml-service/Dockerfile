FROM python:3.10-slim

# Install system dependencies for Tesseract OCR
RUN apt-get update && apt-get install -y tesseract-ocr g++ build-essential libgl1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy model
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
