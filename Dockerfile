FROM python:3.11-slim
WORKDIR /app
COPY custom_exporter.py .
RUN pip install --no-cache-dir prometheus-client requests
CMD ["python", "custom_exporter.py"]