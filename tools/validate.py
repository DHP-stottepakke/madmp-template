#!/usr/bin/env python3
"""
Validate rendered maDMP JSON files against the RDA DCS / OSTrails JSON schemas.

The schema is picked from the file name (as produced by tools/check.sh:
...dcs-1.0.json, ...dcs-1.3.json, ...ostrails.json) or given with --schema.
Schemas are downloaded once into .cache/schemas/.

Usage:
    python tools/validate.py output/*.json
    python tools/validate.py --schema 1.2 some.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / '.cache' / 'schemas'
DCS = 'https://raw.githubusercontent.com/RDA-DMP-Common/RDA-DMP-Common-Standard/master/examples/JSON/JSON-schema'
SCHEMAS = {
    '1.0': f'{DCS}/1.0/maDMP-schema-1.0.json',
    '1.1': f'{DCS}/1.1/maDMP-schema-1.1.json',
    '1.2': f'{DCS}/1.2/maDMP-schema-1.2.json',
    '1.3': f'{DCS}/1.3/maDMP-schema-1.3.json',
    'ostrails': 'https://raw.githubusercontent.com/OSTrails/ostrails-madmp-ap/main/ostrails-ap.json',
}


def load_schema(key: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f'{key}.json'
    if not path.exists():
        with urllib.request.urlopen(SCHEMAS[key], timeout=30) as resp:  # noqa: S310
            path.write_bytes(resp.read())
    return json.loads(path.read_text(encoding='utf-8'))


def guess_schema(name: str) -> str | None:
    # only the format suffix counts: check.sh names files <context>.<format>.json, and the
    # context name may itself contain e.g. "1.3" or "ostrails"
    m = re.search(r'\.(?:dcs-(1\.[0-3])|(ostrails))\.json$', name, re.IGNORECASE)
    if not m:
        return None
    return m.group(1) or 'ostrails'


def main(argv: list[str] | None = None) -> int:
    import jsonschema

    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('files', nargs='+')
    p.add_argument('--schema', choices=list(SCHEMAS), help='schema to use for all files')
    args = p.parse_args(argv)

    failed = 0
    for f in args.files:
        key = args.schema or guess_schema(pathlib.Path(f).name)
        if key is None:
            print(f'?    {f}: cannot tell the schema from the name, use --schema')
            failed += 1
            continue
        schema = load_schema(key)
        cls = jsonschema.validators.validator_for(schema)
        errors = sorted(cls(schema).iter_errors(json.loads(pathlib.Path(f).read_text('utf-8'))),
                        key=lambda e: list(e.absolute_path))
        if errors:
            failed += 1
            print(f'FAIL {f} ({key}): {len(errors)} error(s)')
            for e in errors[:20]:
                print(f"     /{'/'.join(map(str, e.absolute_path))}: {e.message[:200]}")
        else:
            print(f'ok   {f} ({key})')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
