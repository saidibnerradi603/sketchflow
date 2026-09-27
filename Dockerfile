FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and project metadata
COPY README.md pyproject.toml ./
COPY src ./src

# Railway dynamically assigns $PORT
ENV PORT=8000
CMD ["sh", "-c", "uvicorn sketchflow.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
