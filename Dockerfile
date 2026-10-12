# ==============================================================================
# Resume RAG Generator — Production Dockerfile
# ==============================================================================
# Compatible with standalone Docker, Docker Compose, and Hugging Face Spaces.
# Runs on Python 3.12-slim with Tectonic TeX Engine for 1-page PDF generation.
# ==============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

# Install system dependencies & Tectonic LaTeX engine
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tar \
    ca-certificates \
    libfontconfig1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Download and install precompiled static Tectonic binary (v0.15.0)
RUN curl -fsSL https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic@0.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz \
    | tar -xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/tectonic \
    && tectonic --version

# Set up working directory
WORKDIR /app

# Create non-root user (UID 1000 for standard security & Hugging Face Spaces compatibility)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/output /app/chroma_db && \
    chown -R user:user /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source code and assets
COPY --chown=user:user src/ /app/src/
COPY --chown=user:user templates/ /app/templates/
COPY --chown=user:user data/ /app/data/
COPY --chown=user:user app.py /app/app.py
COPY --chown=user:user pyproject.toml /app/pyproject.toml

# Switch to non-root user
USER user

# Expose standard Gradio port
EXPOSE 7860

# Run Gradio application
CMD ["python", "app.py"]
