FROM python:3.11-slim

WORKDIR /chaincode

COPY . /chaincode

RUN pip install --no-cache-dir -r requirements.txt

ENV CHAINCODE_ID="example_1.0"
ENV CHAINCODE_SERVER_ADDRESS="0.0.0.0:9999"

CMD ["python", "main.py"]
