# ── Stage 1: Base image ───────────────────────────────────────────────────────
FROM python:3.11-slim

# Security: run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set working directory
WORKDIR /app

# Copy dependency manifest first (layer-cache optimisation)
COPY requirements.txt .

# Install dependencies (no cache saves image size)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app.py .

# Switch to non-root user
USER appuser

# Expose Flask port
EXPOSE 5000

# Health check (Docker will mark container unhealthy if this fails)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run the application
CMD ["python", "app.py"]
