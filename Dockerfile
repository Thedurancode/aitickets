FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg for yt-dlp video processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY mcp_server/ ./mcp_server/
COPY templates/ ./templates/

# Create uploads directory
RUN mkdir -p uploads

# Expose ports
EXPOSE 8000 3001

# Default to running the main API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
