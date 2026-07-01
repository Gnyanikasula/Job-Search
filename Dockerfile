# ── Job Search Pipeline — HuggingFace Spaces Docker image ────────────────────
# HF Spaces requirement: app must listen on port 7860 (Streamlit)
# FastAPI runs internally on 8000 (not exposed externally)
FROM python:3.12-slim

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg ca-certificates \
    # Chromium runtime deps
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0 libx11-xcb1 libxcb-dri3-0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium (needed for Phase 3 scrapers)
RUN playwright install chromium --with-deps

# Copy application
COPY . .

# Create data directory for SQLite (will be ephemeral on HF free tier)
RUN mkdir -p /app/data

# HuggingFace Spaces runs as non-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# HF Spaces requires port 7860
EXPOSE 7860

# Start script handles both FastAPI (8000) and Streamlit (7860)
CMD ["python", "start.py"]
