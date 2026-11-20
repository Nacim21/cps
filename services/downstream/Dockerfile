FROM python:3.12.7-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app
COPY services/device/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY services/downstream /app/services/downstream
USER 10001:10001
WORKDIR /app/services/downstream
CMD ["python", "-m", "services.downstream.main"]
