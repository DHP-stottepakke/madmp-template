#!/usr/bin/env python3
"""
Local render driver for DSW templates.

Loads a DSW project export (JSON) and renders a Jinja2 template against it
using the official DSW document-worker filters (extract_replies, to_context_obj,
reply_path, ...). Avoids any round-trip through a running DSW instance.

Usage:
    python tools/render.py [--input DSW-norway-export.json] [--template src/madmp.json.j2] [-o out.json]
    python tools/render.py --dump-replies        # print extract_replies output
    python tools/render.py --list-chapters       # print chapter json.key annotations
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Make the vendored dsw.document_worker package importable.
sys.path.insert(0, str(HERE / "dsw_local"))


def _load_ctx(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_context(ctx_dict: dict):
    from dsw.document_worker.templates.filters import to_context_obj
    return to_context_obj(ctx_dict)


def cmd_render(args: argparse.Namespace) -> int:
    import jinja2
    from dsw.document_worker.templates.filters import filters as dsw_filters
    from dsw.document_worker.templates.tests import tests as dsw_tests

    ctx_path = pathlib.Path(args.input)
    tpl_path = pathlib.Path(args.template)
    if not ctx_path.exists():
        print(f"context file not found: {ctx_path}", file=sys.stderr)
        return 2
    if not tpl_path.exists():
        print(f"template not found: {tpl_path}", file=sys.stderr)
        return 2

    ctx_dict = _load_ctx(ctx_path)
    document_ctx = _build_context(ctx_dict)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT)),
        extensions=["jinja2.ext.do"],
        autoescape=False,
        undefined=jinja2.StrictUndefined if args.strict else jinja2.Undefined,
        keep_trailing_newline=True,
    )
    env.filters.update(dsw_filters)
    env.tests.update(dsw_tests)

    # Templates traditionally reference the context as `ctx`.
    rendered = env.get_template(str(tpl_path.relative_to(ROOT))).render(ctx=ctx_dict)

    if args.output:
        pathlib.Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"wrote {args.output} ({len(rendered)} chars)")
    else:
        sys.stdout.write(rendered)
    return 0


def cmd_dump_replies(args: argparse.Namespace) -> int:
    from dsw.document_worker.templates.extraction import extract_replies
    ctx_dict = _load_ctx(pathlib.Path(args.input))
    document_ctx = _build_context(ctx_dict)
    replies = extract_replies(document_ctx)
    out = json.dumps(replies, indent=2, ensure_ascii=False, default=str)
    if args.output:
        pathlib.Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(out + "\n")
    return 0


def cmd_list_chapters(args: argparse.Namespace) -> int:
    ctx_dict = _load_ctx(pathlib.Path(args.input))
    km = ctx_dict["knowledgeModel"]
    for ch_uuid in km["chapterUuids"]:
        ch = km["entities"]["chapters"][ch_uuid]
        anns = {a["key"]: a["value"] for a in ch.get("annotations", [])}
        print(f"  {ch.get('title','?')[:60]:60s}  json.key={anns.get('json.key','MISSING')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", "--ctx", dest="input", default=str(ROOT / "DSW-norway-export.json"),
                   help="path to a DSW project export JSON (default: DSW-norway-export.json)")
    p.add_argument("--template", default=str(ROOT / "src" / "madmp.json.j2"),
                   help="Jinja template to render (default: src/madmp.json.j2)")
    p.add_argument("-o", "--output", default=None,
                   help="write output to this file instead of stdout")
    p.add_argument("--strict", action="store_true",
                   help="use jinja2.StrictUndefined (fail on undefined variables)")
    p.add_argument("--dump-replies", action="store_true",
                   help="dump extract_replies output as JSON and exit")
    p.add_argument("--list-chapters", action="store_true",
                   help="list chapters and their json.key annotations and exit")
    args = p.parse_args(argv)

    if args.list_chapters:
        return cmd_list_chapters(args)
    if args.dump_replies:
        return cmd_dump_replies(args)
    return cmd_render(args)


if __name__ == "__main__":
    raise SystemExit(main())
