FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       default-libmysqlclient-dev \
       curl \
       ca-certificates \
       wget \
       gnupg \
       apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install uvicorn[standard] \
    && pip install pymysql==1.1.0

# Install Playwright browsers
RUN playwright install --with-deps

# Copy project
COPY . /app

# Create non-root user
RUN useradd -m appuser \
    && chown -R appuser:appuser /app
RUN chmod +x /app/entrypoint.sh || true \
    && sed -i 's/\r$//' /app/entrypoint.sh || true \
    && sed -i '1s/^\xEF\xBB\xBF//' /app/entrypoint.sh || true
USER appuser

# Environment variables
ENV DJANGO_SETTINGS_MODULE=firewallbackend.settings \
    PYTHONPATH=/app

# Collect static at build-time to speed up container start (safe even if empty)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Use entrypoint to run migrations then start ASGI server
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "firewallbackend.asgi:application"]


