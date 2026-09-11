FROM python:3.11-slim

WORKDIR /app

# Build with repository root as context, for example:
# docker build -f examples/ccaas/asset-transfer-basic/Dockerfile -t asset-transfer-basic:latest .
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "grpcio>=1.83.1"

ENV CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 9999
CMD ["python", "-u", "examples/ccaas/asset-transfer-basic/main.py"]
