FROM python:3.13.9-alpine3.22

COPY requirements.txt .

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /ml

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

EXPOSE 8001