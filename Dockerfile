FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg xvfb xauth && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install --with-deps chromium

COPY src/ ./
COPY BIOMECHANICS_KNOWLEDGE.md .

RUN mkdir -p media/videos media/annotated media/reports

ENV PYTHONPATH=/app
EXPOSE 10000

CMD ["sh", "/app/bin/service_entrypoint.sh"]
