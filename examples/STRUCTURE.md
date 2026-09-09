# Examples Directory Structure

This directory organizes all chaincode examples following best practices from Hyperledger Fabric.

## Directory Layout

```
examples/
├── README.md                 # Overview of available examples
├── STRUCTURE.md              # This file
└── ccaas/                    # Complete CCAAS (Chaincode-as-a-Service) example
    ├── README.md             # Setup and usage instructions
    ├── main.py               # Chaincode implementation
    ├── connection.json       # Peer connection configuration
    ├── metadata.json         # CCAAS metadata
    ├── requirements.txt      # Python dependencies
    └── Dockerfile            # Docker build configuration
```

## Example: ccaas/

A production-ready example of Python chaincode deployed as CCAAS with:
- Complete chaincode logic (create, read, update, delete assets)
- Full configuration files for packaging and deployment
- Detailed README with step-by-step instructions
- Docker support for containerized deployment
- Error handling and validation

### Quick Start with this Example

```bash
# 1. See the example structure
cd fabric-chaincode-python/examples/ccaas

# 2. Read detailed instructions
cat README.md

# 3. Follow the setup steps to package, install, and run
```

## Adding New Examples

To add a new example:

1. Create a new folder under `examples/`:
   ```bash
   mkdir examples/my-example
   ```

2. Include these files:
   - `main.py` - Chaincode implementation
   - `README.md` - Setup and usage instructions
   - `requirements.txt` - Python dependencies (optional if using parent repo)
   - `connection.json` - Connection config (if different from default)
   - `metadata.json` - CCAAS metadata (if different from default)
   - `Dockerfile` - Docker build config (optional)

3. Update the main `examples/README.md` to reference your new example

## Integration with Parent Project

Each example can:
- Reference the parent `src/fabric_shim/` for the framework
- Use the parent `requirements.txt` or specify their own
- Operate independently once deployed

## Guidelines for Examples

✅ **DO:**
- Include clear, step-by-step README instructions
- Use realistic asset management logic
- Provide Docker support
- Add error handling and validation
- Test thoroughly before committing
- Document all assumptions and prerequisites

❌ **DON'T:**
- Skip documentation
- Use hardcoded credentials or secrets
- Create incomplete or non-working examples
- Assume user knows all Fabric concepts
- Forget to update the main `examples/README.md`

## Consistency

All examples follow this pattern:
1. Example folder name is descriptive (e.g., `ccaas`, `ledger-api`)
2. Each example is self-contained and runnable
3. README provides complete setup instructions
4. Dockerfile is provided for easy containerization
5. Configuration files are properly documented

---

For more information, see the main repository README.md at the project root.
