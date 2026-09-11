# Examples

This directory contains example implementations of Hyperledger Fabric Python chaincodes.

## Available Examples

### [ccaas/asset-transfer-basic](./ccaas/asset-transfer-basic/)

A complete, ready-to-run example of a Python chaincode deployed as a **Chaincode-as-a-Service (CCAAS)**.

**Features:**
- Asset management (create, read, update, delete)
- Ledger initialization with sample data
- Full end-to-end setup instructions
- Docker deployment support
- Production-ready error handling

**Quick Links:**
- [README](./ccaas/asset-transfer-basic/README.md) - Detailed setup and usage guide
- [main.py](./ccaas/asset-transfer-basic/main.py) - Chaincode implementation
- [Dockerfile](./ccaas/asset-transfer-basic/Dockerfile) - Docker build configuration

### [ccaas/asset-transfer-sbe](./ccaas/asset-transfer-sbe/)

State-based-endorsement style asset transfer sample aligned with Fabric naming and function set.

**Quick Links:**
- [README](./ccaas/asset-transfer-sbe/README.md)
- [main.py](./ccaas/asset-transfer-sbe/main.py)
- [Dockerfile](./ccaas/asset-transfer-sbe/Dockerfile)

## What is CCAAS?

**Chaincode-as-a-Service (CCAAS)** is a deployment model for Hyperledger Fabric chaincodes where:
- The chaincode runs as an independent service/process
- The peer connects to it via gRPC
- You have full control over the runtime environment
- Perfect for integrating with external systems, databases, or microservices

## Getting Started

1. **Choose an Example:** Start with `ccaas/asset-transfer-basic` for a complete working example
2. **Follow Setup Instructions:** Each example has a README with step-by-step instructions
3. **Test on Local Network:** Use Fabric's `test-network-nano-bash` for testing
4. **Adapt for Your Use Case:** Modify the chaincode logic for your specific needs

## Common Tasks

### Create a New Example
1. Create a new folder under `examples/`
2. Copy the structure from `ccaas/asset-transfer-basic/`
3. Modify `main.py` for your chaincode logic
4. Update README with your specific instructions

### Deploy to Production
- Use Docker containers for consistent deployment
- Configure TLS in `connection.json` (`"tls_required": true`)
- Set appropriate network policies and firewall rules
- Use a process manager (systemd, supervisor, etc.) to keep the service running

### Integrate with External Systems
- The chaincode can make HTTP requests, database calls, etc.
- Use the ledger for immutable records
- Return results via the Response object

## Requirements

- Python 3.10+
- Hyperledger Fabric network (test network or production)
- Peer CLI for lifecycle management
- Docker (optional, for containerized deployment)

## Related Documentation

- [Fabric Python Chaincode API](../src/fabric_shim/)
- [Hyperledger Fabric Official Docs](https://hyperledger-fabric.readthedocs.io/)
- [CCAAS Architecture](https://hyperledger-fabric.readthedocs.io/en/latest/cc_service.html)

## Contributing

If you create new examples or improvements, please consider contributing back to the repository. Follow the same structure and include comprehensive documentation.

---

**Note:** Examples are designed to demonstrate concepts and work with Fabric v2.5+. Always test thoroughly before deploying to production.
