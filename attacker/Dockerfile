FROM python:3.12.7-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app
COPY attacker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY attacker /app/attacker
USER 10001:10001
WORKDIR /app/attacker
CMD ["python", "-m", "attacker.unauthorized_read"]
