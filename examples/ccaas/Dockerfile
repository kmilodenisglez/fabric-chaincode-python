FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone or copy the fabric-chaincode-python repository
# For this example, we assume the parent repository is mounted
COPY ../ /fabric-chaincode-python/

# Set working directory to the repository root
WORKDIR /fabric-chaincode-python

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure gRPC version is correct for generated code
RUN pip install --no-cache-dir "grpcio>=1.83.1"

# Set environment variables for CCAAS
ENV CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999
ENV PYTHONUNBUFFERED=1

# Expose the chaincode server port
EXPOSE 9999

# Start the chaincode server
CMD ["python", "examples/ccaas-basic/main.py"]
