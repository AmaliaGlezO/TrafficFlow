FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY services/dashboard/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/dashboard/app /app/app
COPY services/dashboard/static /app/static

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
