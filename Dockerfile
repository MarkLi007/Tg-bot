FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY .env.example ./
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python","-m","src.main"]
