FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY services/data_generator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/data_generator /app/services/data_generator
COPY data/reference /app/datos/referencia

ENV PYTHONPATH=/app

CMD ["python", "-m", "services.data_generator"]
