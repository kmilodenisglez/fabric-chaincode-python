# Dockerfile for Token Chaincode CCAAS
# Build: docker build -t token-chaincode:latest .
# Run: docker run -e CHAINCODE_ID=token_1.0:sha256:hash -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 -p 9999:9999 token-chaincode:latest

FROM python:3.11-slim

LABEL maintainer="fabric-chaincode-python contributors"
LABEL description="Token Chaincode - Hyperledger Fabric Chaincode Service"

# Set working directory
WORKDIR /app

# Copy the parent fabric-chaincode-python source
COPY ../../pyproject.toml ./
COPY ../../src ./src
COPY ../../fabric_protos_python ./fabric_protos_python
COPY ../../requirements.txt ./

# Copy this example
COPY . ./examples/token_chaincode

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables for CCAAS
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the chaincode server
EXPOSE 9999
CMD ["python", "-u", "examples/token_chaincode/main.py"]
