FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir mediapipe==0.10.14 && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./
COPY BIOMECHANICS_KNOWLEDGE.md .

RUN mkdir -p media/videos media/annotated

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
