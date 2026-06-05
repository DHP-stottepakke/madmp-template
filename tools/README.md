# Local template test environment

Renders DSW Jinja2 templates locally against a project export, without needing
a running DSW instance.

## Setup (one-time)

```bash
bash tools/setup.sh
```

This creates a `.venv/` and installs Jinja2, Markdown, MarkupSafe, python-dateutil.

## Usage

```bash
. .venv/bin/activate

# render the default template (src/madmp.json.j2) against DSW-norway-export.json
python tools/render.py -o out.json

# render against a specific project export
python tools/render.py --input LiesFaultProjectExport.json -o out.json

# render a specific template
python tools/render.py --template src/madmp.ttl.j2 -o out.ttl

# dump the extract_replies output (for understanding the data shape)
python tools/render.py --dump-replies -o replies.json

# list chapter json.key annotations
python tools/render.py --list-chapters

# fail fast on undefined variables (useful during development)
python tools/render.py --strict
```

`--input` is the primary flag for the project export JSON.
`--ctx` remains available as a backward-compatible alias.

## How it works

`tools/dsw_local/dsw/document_worker/` contains a minimal vendored subset of the
official DSW `dsw-document-worker` package (model + templates/filters +
extraction). The driver in `tools/render.py`:

1. Loads `DSW-norway-export.json` (a normal DSW project export).
2. Builds a `DocumentContext` via the `to_context_obj` filter.
3. Renders the requested template with all DSW filters registered (including
   `extract_replies`, `to_context_obj`, `reply_path`, `find_reply`,
   `reply_str_value`, `markdown`, ...).

The export JSON contains exactly the keys the document worker expects
(`config`, `knowledgeModel`, `project`, `report`, `document`,
`knowledgeModelPackage`, `organization`, `users`, `groups`, `metamodelVersion`),
so no transformation is needed.

## Refreshing the vendored DSW code

```bash
BASE=https://raw.githubusercontent.com/ds-wizard/engine-tools/develop/packages/dsw-document-worker/dsw/document_worker
DEST=tools/dsw_local/dsw/document_worker
for f in consts.py utils.py exceptions.py \
         model/context.py model/utils.py \
         templates/extraction.py templates/filters.py templates/tests.py; do
  curl -sS -o "$DEST/$f" "$BASE/$f"
done
```

The `__init__.py` files under `dsw_local/dsw/document_worker/` and
`.../templates/` are intentionally stubs (the upstream `__init__.py` imports
`cli`, `handlers`, `formats`, `templates`, which pull heavy worker deps that we
don't need for rendering).
