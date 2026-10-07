FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Seed demo users + sample docs on first start, then serve
CMD ["sh", "-c", "python -m scripts.seed && uvicorn app.server:app --host 0.0.0.0 --port 8000"]
