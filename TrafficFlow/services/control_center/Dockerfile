FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY services/control_center/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/control_center/app /app/app
COPY services/control_center/static /app/static

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"]
