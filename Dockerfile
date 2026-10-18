FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SHABD_ENGINE=compact OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
COPY backend/requirements-runtime.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
EXPOSE 8000
CMD ["python", "-m", "backend.serve"]
