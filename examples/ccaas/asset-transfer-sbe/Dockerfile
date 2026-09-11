# Dockerfile for asset-transfer-sbe CCAAS
# Build (from repository root):
# docker build -f examples/ccaas/asset-transfer-sbe/Dockerfile -t asset-transfer-sbe:latest .

FROM python:3.11-slim

LABEL maintainer="fabric-chaincode-python contributors"
LABEL description="Asset Transfer SBE Chaincode - Hyperledger Fabric Chaincode Service"

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt \
	&& pip install --no-cache-dir "grpcio>=1.83.1"

ENV PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app \
	CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999

EXPOSE 9999
CMD ["python", "-u", "examples/ccaas/asset-transfer-sbe/main.py"]
