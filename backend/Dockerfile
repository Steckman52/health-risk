FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        cmake && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /backend

COPY ./backend .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level" , "info"]

EXPOSE 8000