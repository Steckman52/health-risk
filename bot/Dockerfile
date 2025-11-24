FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        cmake && \
    rm -rf /var/lib/apt/lists/*
COPY ../requirements.txt .

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /app

COPY . .

ENTRYPOINT ["python", "-u", "main.py"]