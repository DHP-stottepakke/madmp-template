# Local template test environment

Renders the template locally against a DSW 5 document context (metamodel 19.0),
with [`dsw-tdk`](https://pypi.org/project/dsw-tdk/), which uses the same engine
(`dsw-templating`) as the DSW 5 document worker. No running DSW instance is needed.

## Setup (one-time)

```bash
bash tools/setup.sh
```

This creates `.venv/` and installs `dsw-tdk` 5.0.0 and `jsonschema`.

## Usage

```bash
. .venv/bin/activate

# render all formats for a context and validate them against their schemas
bash tools/check.sh path/to/context.json            # outputs in output/

# render one format
dsw-tdk render . -c path/to/context.json -F "JSON (DCS 1.2)" -o out.json

# render with a translation (once locales/*.po exist)
dsw-tdk render . -c path/to/context.json -F "JSON (DCS 1.2)" --po locales/nb.po -o out.json

# validate a rendered file (schema from the file name, or --schema 1.0|1.1|1.2|1.3|ostrails)
python tools/validate.py --schema 1.2 out.json

# dump what src/_mapping.j2 sees (extract_replies output)
python tools/replies.py path/to/context.json -o replies.json

# list chapters with their json.key annotations / walk the whole KM
python tools/replies.py path/to/context.json --list-chapters
python tools/walk_km.py path/to/context.json
```

Document contexts contain project data and stay out of git: keep them outside
the repository or under a gitignored name. `output/` and `.cache/` (downloaded
schemas) are gitignored.
