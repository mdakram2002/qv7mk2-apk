FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/app ./app
COPY data ./data
ENV DATA_DIR=/app/data/processed CORS_ORIGINS=http://localhost:8080
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
