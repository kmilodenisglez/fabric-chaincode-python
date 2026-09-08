# fabric-chaincode-python
Hyperledger Fabric Contract and Chaincode implementation for Python https://wiki.hyperledger.org/display/fabric

## 🚀 Quick Testing

This library has only been tested with python versions 3.8 and 3.9

### Install dependencies
Run the following instructions in terminal:
```bash
cd fabric-chaincode-python/
```

```bash
python -m pip install fabric-protos-python==2.4 grpcio
```

### Export the environment variables

Export the chaincode package ID, ex:
```bash
export CHAINCODE_ID=basic_1.0:f3e2ca5115bba71aa2fd16e35722b420cb29c42594f0fdd6814daedbc2130b80
```

Set the chaincode server address:
```bash
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999
```

### Start chaincode service:
```bash
python main.py 
```