FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and project configuration
COPY src ./src
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Railway automatically assigns $PORT
ENV PORT=8000
CMD uvicorn sketchflow.main:app --host 0.0.0.0 --port ${PORT}
