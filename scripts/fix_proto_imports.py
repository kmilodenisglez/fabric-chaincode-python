#!/usr/bin/env python3
"""Fix generated proto imports to reference the fabric_protos_python package.

This script rewrites top-level imports like `from peer import xyz` to
`from fabric_protos_python.peer import xyz` so the generated code works when
packaged under the `fabric_protos_python` package.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / 'fabric_protos_python'

TOP_PKGS = ['peer', 'common', 'msp', 'orderer', 'gateway', 'gossip', 'discovery', 'ledger', 'transientstore']
PATTERN = re.compile(r'from\s+({})\s+import'.format('|'.join(TOP_PKGS)))


def fix_file(p: Path):
    text = p.read_text(encoding='utf-8')
    new_text = PATTERN.sub(lambda m: f'from fabric_protos_python.{m.group(1)} import', text)
    if new_text != text:
        p.write_text(new_text, encoding='utf-8')
        print('Patched', p)


def main():
    files = list(PROTO_DIR.rglob('*.py'))
    for f in files:
        fix_file(f)


if __name__ == '__main__':
    main()
