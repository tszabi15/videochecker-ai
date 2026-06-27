FROM python:3.11-slim

# Install system dependencies (FFmpeg, libpq, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged system user and group named celeryuser
RUN groupadd -r celeryuser && useradd -r -g celeryuser -d /app -s /sbin/nologin celeryuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Grant celeryuser proper ownership and read/write permissions to /app and /tmp/videochecker
RUN mkdir -p /tmp/videochecker && chmod 777 /tmp/videochecker && chown -R celeryuser:celeryuser /app /tmp/videochecker

USER celeryuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
