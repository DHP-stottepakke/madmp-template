#!/usr/bin/env python3
"""
Inspect what the mapping sees: the extract_replies output of a document context.

Uses the filters of dsw-templating (the engine of DSW 5), so the shape is the same
as in src/_mapping.j2.

Usage:
    python tools/replies.py CONTEXT.json [-o replies.json] [--version 1|2]
    python tools/replies.py CONTEXT.json --list-chapters
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('context', help='document context JSON (metamodel 19.0)')
    p.add_argument('-o', '--output', help='write to this file instead of stdout')
    p.add_argument('--version', default='1', choices=['1', '2'],
                   help='extract_replies version (the mapping uses 1)')
    p.add_argument('--list-chapters', action='store_true',
                   help='list chapters and their json.key annotations')
    args = p.parse_args(argv)

    ctx = json.loads(pathlib.Path(args.context).read_text(encoding='utf-8'))

    if args.list_chapters:
        km = ctx['knowledgeModel']
        for ch_uuid in km['chapterUuids']:
            ch = km['entities']['chapters'][ch_uuid]
            anns = {a['key']: a['value'] for a in ch.get('annotations', [])}
            print(f"  {ch.get('title', '?')[:60]:60s}  json.key={anns.get('json.key', 'MISSING')}")
        return 0

    from dsw.templating.extraction import extract_replies
    from dsw.templating.filters import to_context_obj

    replies = extract_replies(to_context_obj(ctx), {'version': args.version})
    out = json.dumps(replies, indent=2, ensure_ascii=False, default=str)
    if args.output:
        pathlib.Path(args.output).write_text(out + '\n', encoding='utf-8')
        print(f'wrote {args.output}', file=sys.stderr)
    else:
        sys.stdout.write(out + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
