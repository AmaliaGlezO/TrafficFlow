FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY services/receiver/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/receiver /app/services/receiver

ENV PYTHONPATH=/app

CMD ["python", "-m", "services.receiver"]
