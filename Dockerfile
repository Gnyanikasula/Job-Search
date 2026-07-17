# ── Job Search Pipeline — HuggingFace Spaces Docker image ────────────────────
# HF Spaces requirement: app must listen on port 7860 (Streamlit)
# FastAPI runs internally on 8000 (not exposed externally)
FROM python:3.12-slim

# Playwright browsers install to a shared path both root and appuser can read
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
# SQLite DB location (writable by appuser)
ENV DB_PATH=/app/data/jobs.db

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0 libx11-xcb1 libxcb-dri3-0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium to the shared browsers path, then make it world-readable
RUN mkdir -p /opt/pw-browsers \
    && playwright install chromium \
    && chmod -R a+rX /opt/pw-browsers

# Copy application
COPY . .

# Create writable data dir + non-root user (HF runs as non-root)
RUN mkdir -p /app/data \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# HF Spaces requires port 7860
EXPOSE 7860

CMD ["python", "start.py"]
