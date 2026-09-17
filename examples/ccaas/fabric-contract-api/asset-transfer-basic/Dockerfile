# Dockerfile for asset-transfer-basic (fabric_contract_api high-level API)
# Build from repository root:
#   docker build -f examples/ccaas/fabric-contract-api/asset-transfer-basic/Dockerfile -t asset-transfer-basic-contract-api:latest .

FROM python:3.11-slim

LABEL maintainer="fabric-chaincode-python contributors"
LABEL description="Asset Transfer Basic Chaincode (fabric_contract_api) - Hyperledger Fabric Chaincode Service"

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt \
        && pip install --no-cache-dir "grpcio>=1.83.1" "jsonschema>=4.0.0"

ENV PYTHONUNBUFFERED=1 \
        PYTHONPATH=/app \
        CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999

EXPOSE 9999
CMD ["python", "-u", "examples/ccaas/fabric-contract-api/asset-transfer-basic/main.py"]
