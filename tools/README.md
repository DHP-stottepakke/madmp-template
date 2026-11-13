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

## End-to-end test with synthetic projects

```bash
python tools/e2e.py                    # 5 profiles x 8 seeds x 2 variants (~80 projects)
python tools/e2e.py --seeds 30 --jobs 8
python tools/e2e.py --quick            # smoke run
```

`tools/e2e.py` generates synthetic projects from `../research.data.no.norway-generic_1.2.1.km`
(`--km` for another bundle) with the dsw-tdk generator (profiles empty, minimal, typical,
full, edge; a few KM editor previews), and makes them realistic: integration replies get
the payloads of the API responses recorded in the KM (`testResponse` of each integration,
with the reply text rendered by its item template) or a typed reply; text answers get
Markdown and string answers characters that need escaping. Copies of typical, full and edge
projects are filtered by selected question tags, as DSW does it (each tag of the KM and a
pair of tags, with and without untagged questions; the questions without a selected tag are
removed from the KM, their replies stay in the questionnaire); `--no-tags` skips them. It renders every format and
checks each document: schema (with formats), members the schema version does not define,
text hygiene (escaped HTML, Markdown left over, `None`/`Undefined`, empty strings), an
oracle computed from the replies (title, contributors and ORCID iDs, affiliations, dataset
titles and PIDs, license references, ethical issues, dates, project, OSTrails version,
language), the same content in all formats, and determinism. It also reports which answers
the mapping refers to were never selected. Results go to `output/e2e/report.md`
(`report.json`, `contexts/`, `documents/`); the exit code is 1 when there are errors.

Document contexts contain project data and stay out of git: keep them outside
the repository or under a gitignored name. `output/` and `.cache/` (downloaded
schemas) are gitignored.
