#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
FABRIC_PROTOS_REPO="${FABRIC_PROTOS_REPO:-https://github.com/hyperledger/fabric-protos.git}"
FABRIC_PROTOS_REF="${FABRIC_PROTOS_REF:-8a4c79c6c507fecbf38c21a89ec8938661dc913a}"
FABRIC_PROTOS_SRC="${FABRIC_PROTOS_SRC:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_LOCAL_SRC="$(cd "$REPO_ROOT/.." && pwd)/fabric-protos"

check_imports() {
  "$PYTHON_BIN" - <<'PY'
import importlib
required = [
    "fabric_protos.peer.chaincode_pb2",
    "fabric_protos.peer.chaincode_shim_pb2",
    "fabric_protos.common.common_pb2",
]
for mod in required:
    importlib.import_module(mod)
print("fabric_protos import check: OK")
PY
}

install_from_local_src() {
  local src="$1"
  if [[ ! -d "$src" ]]; then
    return 1
  fi
  if [[ ! -d "$src/bindings/python" ]]; then
    return 1
  fi

  echo "Installing official bindings from local fabric-protos source: $src"
  make -C "$src" pythonbindings
  "$PYTHON_BIN" -m pip install --upgrade "$src/bindings/python"
}

install_from_pypi() {
  echo "Trying PyPI package hyperledger-fabric-protos"
  "$PYTHON_BIN" -m pip install --upgrade hyperledger-fabric-protos
}

install_from_git_checkout() {
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' RETURN

  echo "Cloning official fabric-protos and building python bindings"
  git clone "$FABRIC_PROTOS_REPO" "$tmp_dir/fabric-protos"
  git -C "$tmp_dir/fabric-protos" checkout "$FABRIC_PROTOS_REF"

  make -C "$tmp_dir/fabric-protos" pythonbindings
  "$PYTHON_BIN" -m pip install --upgrade "$tmp_dir/fabric-protos/bindings/python"
}

if check_imports >/dev/null 2>&1; then
  echo "fabric_protos is already available"
  exit 0
fi

if [[ -n "$FABRIC_PROTOS_SRC" ]]; then
  if install_from_local_src "$FABRIC_PROTOS_SRC"; then
    check_imports
    exit 0
  fi
  echo "Provided FABRIC_PROTOS_SRC is invalid: $FABRIC_PROTOS_SRC"
  echo "Falling back to alternate installation methods"
fi

if install_from_local_src "$DEFAULT_LOCAL_SRC"; then
  check_imports
  exit 0
fi

if install_from_pypi; then
  if check_imports >/dev/null 2>&1; then
    echo "fabric_protos installed from PyPI"
    exit 0
  fi
  echo "PyPI package installed but does not include generated modules for this version"
fi

install_from_git_checkout
check_imports
