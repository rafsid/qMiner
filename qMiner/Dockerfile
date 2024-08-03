FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

COPY . .

EXPOSE 5000

CMD ["uvicorn", "qminer:asgi_app", "--host", "0.0.0.0", "--port", "5000"]