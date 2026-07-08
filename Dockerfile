FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source code including static files
COPY backend/ .

# Port that Cloud Run / Container listens to
EXPOSE 8080

# Environment variables defaults
ENV PORT=8080
ENV ENVIRONMENT=production
ENV DATABASE_URL=sqlite+aiosqlite:///./stadium_saathi.db

# Run using Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
