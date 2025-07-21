# NETCONF Memory Leak Analyzer - Docker Image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    valgrind \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 analyzer && \
    chown -R analyzer:analyzer /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R analyzer:analyzer /app

# Switch to non-root user
USER analyzer

# Create directories for outputs
RUN mkdir -p /app/results /app/logs /app/analysis_reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.device.device_connector; print('OK')" || exit 1

# Default command
CMD ["python", "parallel_device_tester.py", "--help"]

# Labels
LABEL name="netconf-memory-analyzer" \
      version="1.0.0" \
      description="Containerized NETCONF memory leak analyzer" \
      maintainer="NETCONF Team <team@example.com>" 