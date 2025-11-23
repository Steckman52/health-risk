FROM python:3.13.9-alpine3.22

COPY requirements.txt .

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /app

COPY . .

ENTRYPOINT ["python", "-u", "main.py"]