FROM python:3.11-slim

WORKDIR /app

COPY worker.py .

RUN pip install --no-cache-dir flask transformers torch

EXPOSE 5000

CMD ["python", "worker.py"]