#!/usr/bin/env python3
"""
End-to-end test of the template with synthetic projects.

1. Generate document contexts from the knowledge model bundle with the dsw-tdk generator
   (profiles empty, minimal, typical, full and edge; projects and KM editor previews).
2. Make them realistic: integration replies get the payloads of the API responses that the
   KM records for each integration (its `testResponse`), with the reply text rendered by the
   integration's item template, or a typed (plain) reply; text answers get Markdown and
   string answers get characters that need escaping (sentinels the checks look for).
3. Render every format of the template with the DSW 5 engine (dsw-tdk, in-process).
4. Check every document: rendered, JSON, schema (with formats), members the schema version
   does not define, text hygiene, an oracle computed independently from the replies, the same
   content in all formats, determinism; and report which mapped answers the corpus reached.

Usage:
    python tools/e2e.py                          # 5 profiles x 8 seeds x 2 variants
    python tools/e2e.py --seeds 30 --jobs 8      # bigger corpus
    python tools/e2e.py --quick                  # a smoke run
Results: output/e2e/report.md (and report.json, contexts/, documents/).
"""
from __future__ import annotations

import argparse
import collections
import copy
import dataclasses
import datetime
import json
import logging
import multiprocessing
import pathlib
import random
import re
import sys
import time
import typing

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

import validate as schemas  # noqa: E402  (tools/validate.py: schema download + cache)

FORMATS = {  # template.json format name -> schema key
    'JSON (DCS 1.0)': '1.0',
    'JSON (DCS 1.1)': '1.1',
    'JSON (DCS 1.2)': '1.2',
    'JSON (DCS 1.3)': '1.3',
    'JSON (OSTrails AP)': 'ostrails',
}
PROFILES = ('empty', 'minimal', 'typical', 'full', 'edge')
TS_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# sentinels injected into replies (see Enricher) and looked for in the documents
MD_BOLD = 'MDBOLD'
MD_LINK = 'https://example.org/mdlink'
ESCAPE_SUFFIX = ' & <i>Co</i> "q"'
ESCAPED = ('&amp;', '&lt;', '&gt;', '&#34;', '&#39;', '&quot;')

ORCID_RE = re.compile(r'^https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')
URL_RE = re.compile(r'^https?://\S+$')


# ----------------------------------------------------------------------------- KM index

def annotation(entity: dict, key: str) -> str | None:
    for a in entity.get('annotations') or []:
        if a['key'] == key:
            return a['value']
    return None


def dig(obj, path: str | None):
    if not path:
        return obj
    for part in path.split('.'):
        obj = obj.get(part) if isinstance(obj, dict) else None
    return obj


class KmIndex:
    """Questions, integrations and fixture payloads of the compiled KM of a context."""

    def __init__(self, km: dict):
        import jinja2.sandbox
        ents = km['entities']
        self.questions: dict[str, dict] = ents['questions']
        self.answers: dict[str, dict] = ents['answers']
        self.integrations: dict[str, dict] = ents['integrations']
        env = jinja2.sandbox.SandboxedEnvironment()
        self.fixtures: dict[str, list[dict]] = {}
        self.item_templates = {}
        for uuid, integ in self.integrations.items():
            body = ((integ.get('testResponse') or {}).get('response') or {}).get('body')
            try:
                items = dig(json.loads(body), integ.get('responseListField')) if body else None
            except ValueError:
                items = None
            if isinstance(items, list) and items:
                self.fixtures[uuid] = [i for i in items[:50] if isinstance(i, dict)]
            try:
                self.item_templates[uuid] = env.from_string(integ.get('responseItemTemplate') or '')
            except Exception:  # noqa: BLE001
                self.item_templates[uuid] = None
        # (question json.key, answer json.value) of every answer (for the coverage report)
        self.answer_keys: set[tuple[str, str]] = set()
        for q in self.questions.values():
            for au in q.get('answerUuids') or []:
                a = self.answers.get(au)
                qk, av = annotation(q, 'json.key'), annotation(a or {}, 'json.value')
                if qk and av:
                    self.answer_keys.add((qk, av))
        self.answer_values = {v for _, v in self.answer_keys}

    def item_value(self, integ_uuid: str, item: dict) -> str:
        tpl = self.item_templates.get(integ_uuid)
        if tpl is not None:
            try:
                return tpl.render(item=item).strip()
            except Exception:  # noqa: BLE001
                pass
        return str(item.get('name') or item.get('id') or 'item')


# typed (plain) replies per integration, as users would type them
PLAIN_VALUES = {
    'ORCID': ['0000-0002-1825-0097', 'https://orcid.org/0000-0002-1825-0097',
              'orcid.org/0000-0001-5109-3700 ', 'Jane Doe', '0000-0002-1825-009'],
    'ROR (organizations)': ['Example Institute & Co.', 'Helse Vest'],
    'ROR (funders)': ['https://www.forskningsradet.no', 'Example Foundation'],
    'DataCite (dataset DOI search)': ['https://doi.org/10.18710/EXAMPLE'],
    'OMICS DI (dataset search)': ['PXD000001'],
    'FAIRsharing (database)': ['Local institutional archive'],
    'FAIRsharing (standard)': ['In-house metadata schema'],
    'Licences (zenodo:spdx)': ['https://creativecommons.org/licenses/by/4.0/', 'CC-BY 4.0'],
}


# ----------------------------------------------------------------------------- generation

@dataclasses.dataclass
class Case:
    name: str
    profile: str
    seed: int
    variant: int
    source: str            # project | km-editor
    no_package: bool       # KM editor without knowledgeModelPackage
    integrations: str      # realistic | generic
    markup: bool           # Markdown / escaping sentinels injected
    injected: dict = dataclasses.field(default_factory=dict)  # path -> {mode, item?, value?}


def plan_cases(seeds: list[int], profiles: list[str], count: int, editor_share: float) -> list[Case]:
    cases = []
    for seed in seeds:
        for profile in profiles:
            for variant in range(count):
                rng = random.Random(f'{seed}/{profile}/{variant}')
                editor = rng.random() < editor_share
                no_pkg = editor and rng.random() < 0.5
                integrations = 'generic' if rng.random() < 0.15 else 'realistic'
                markup = profile != 'empty' and rng.random() < 0.6
                name = f'{profile}-s{seed}-v{variant}' + ('-editor' if editor else '') + \
                       ('-nopkg' if no_pkg else '') + ('-generic' if integrations == 'generic' else '') + \
                       ('-markup' if markup else '')
                cases.append(Case(name, profile, seed, variant, 'km-editor' if editor else 'project',
                                  no_pkg, integrations, markup))
    return cases


class Enricher:
    def __init__(self, case: Case, km: KmIndex):
        self.case, self.km = case, km
        self.rng = random.Random(f'enrich/{case.name}')
        self.n = 0

    def run(self, ctx: dict) -> dict:
        replies = ctx['questionnaire']['replies']
        for path, reply in sorted(replies.items()):
            q = self.km.questions.get(path.split('.')[-1])
            if q is None:
                continue
            value = reply['value']
            if value['type'] == 'IntegrationReply' and self.case.integrations == 'realistic':
                self._integration(path, q, value)
            elif value['type'] == 'StringReply' and self.case.markup:
                self._string(q, value)
        if self.case.no_package:
            ctx['knowledgeModelPackage'] = None
        return ctx

    def _integration(self, path: str, q: dict, value: dict):
        integ_uuid = q.get('integrationUuid')
        integ = self.km.integrations.get(integ_uuid) or {}
        items = self.km.fixtures.get(integ_uuid)
        plain = PLAIN_VALUES.get(integ.get('name'))
        if items and (not plain or self.rng.random() < 0.75):
            item = self.rng.choice(items)
            value['value'] = {'type': 'IntegrationType', 'value': self.km.item_value(integ_uuid, item),
                              'raw': item}
            self.case.injected[path] = {'mode': 'payload', 'integration': integ.get('name'), 'item': item}
        elif plain:
            typed = self.rng.choice(plain)
            value['value'] = {'type': 'PlainType', 'value': typed}
            self.case.injected[path] = {'mode': 'plain', 'integration': integ.get('name'), 'value': typed}

    def _string(self, q: dict, value: dict):
        vt = q.get('valueType')
        if vt == 'TextQuestionValueType':
            self.n += 1
            value['value'] = (f'**{MD_BOLD}{self.n}** {value["value"]}\n\n'
                              f'- see [MDLINK{self.n}]({MD_LINK}{self.n})')
        elif vt == 'StringQuestionValueType' and not q.get('validations') and self.rng.random() < 0.5:
            value['value'] = f'{value["value"]}{ESCAPE_SUFFIX}'


def generate(case: Case, km_path: pathlib.Path, ctx_dir: pathlib.Path, _cache={}) -> Case:
    from dsw.tdk.context import generate as gen
    from dsw.tdk.context import inputs
    from dsw.tdk.context.profiles import PROFILE_BY_NAME
    if 'input' not in _cache:
        _cache['input'] = inputs.input_from_bundle_data(inputs.read_bundle_file(km_path), 0)
    options = gen.Options(profile=PROFILE_BY_NAME[case.profile], variant=case.variant,
                          seed=case.seed, source=case.source)
    ctx = gen.generate_context(_cache['input'], options).context
    if 'km' not in _cache:
        _cache['km'] = KmIndex(ctx['knowledgeModel'])
    ctx = Enricher(case, _cache['km']).run(ctx)
    ctx = gen.finalize(ctx)
    (ctx_dir / f'{case.name}.json').write_text(gen.dumps(ctx), encoding='utf-8')
    return case


# ----------------------------------------------------------------------------- rendering

_TDK = {}


def _tdk():
    if 'core' not in _TDK:
        from dsw.tdk.core import TDKCore
        logging.disable(logging.WARNING)
        core = TDKCore(logger=logging.getLogger('e2e'))
        core.load_local(template_dir=ROOT)
        _TDK['core'] = core
    return _TDK['core']


def render(job: tuple[list[str], str, str | None]) -> list[dict]:
    """Render contexts in all formats; returns one record per document."""
    from dsw.tdk.core import RenderOptions
    from dsw.tdk.context.document import DocumentOptions
    from dsw.tdk.render import render_settings
    files, out_dir, language = job
    core = _tdk()
    formats = [f for f in core.safe_project.safe_template.formats if f.name in FORMATS]
    options = RenderOptions(force=True, settings=render_settings(),
                            document=DocumentOptions(language=language, with_locale=language is not None))
    results = []
    for r in core.render_batch(context_files=[pathlib.Path(f) for f in files], formats=formats,
                               output_dir=pathlib.Path(out_dir), options=options):
        results.append({'context': r.context_file.stem, 'format': r.format_spec.name,
                        'output': str(r.output) if r.output else None, 'error': r.error,
                        'ms': r.duration_ms})
    return results


# ----------------------------------------------------------------------------- oracle

class Oracle:
    """Expected content of a document, from the replies (independent of the template code)."""

    def __init__(self, ctx: dict, case: Case):
        from dsw.templating.extraction import extract_replies
        from dsw.templating.filters import to_context_obj
        self.ctx, self.case = ctx, case
        self.dc = to_context_obj(ctx)
        self.r = extract_replies(self.dc, {'version': '1'})
        self.owner = ctx['project'] or ctx['knowledgeModelEditor']

    def plain(self, obj) -> str:
        if not obj or not obj.get('_path'):
            return ''
        reply = self.dc.questionnaire.replies.get(obj['_path'])
        return (reply.markdown_plain if reply else '').strip()

    def get(self, *keys):
        obj = self.r
        for k in keys:
            obj = obj.get(k) if isinstance(obj, dict) else None
        return obj

    def payload(self, obj):
        return obj.get('_raw') if isinstance(obj, dict) else None

    # --- expectations
    def title(self):
        t = self.get('administrativeInformation', 'dmpTitle')
        return ((t or {}).get('_value') or '').strip() or self.owner['name'].strip()

    def contributors(self) -> list[dict]:
        out = []
        for c in self.get('administrativeInformation', 'contributors') or []:
            name = ((c.get('name') or {}).get('_value') or '').strip()
            if not name or not c.get('roles'):
                continue
            orcid = None
            o = c.get('orcid')
            if o and o.get('_raw') and o['_raw'].get('orcid-id'):
                orcid = o['_raw']['orcid-id']
            elif o and o.get('_value') and not o.get('_raw'):
                m = re.fullmatch(r'(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])',
                                 o['_value'].strip(), re.IGNORECASE)
                orcid = m.group(1).upper() if m else None
            aff = c.get('affiliation') or {}
            ror = None
            if aff.get('_raw') and str(aff['_raw'].get('id', '')).startswith('https://ror.org/'):
                names = [n['value'] for n in aff['_raw'].get('names') or [] if 'ror_display' in (n.get('types') or [])]
                ror = (aff['_raw']['id'], names[0].strip() if names else None)
            out.append({'name': name, 'orcid': orcid, 'ror': ror,
                        'email': (c.get('email') or {}).get('_value')})
        return out

    def dataset_titles(self) -> list[str]:
        titles = []
        for ds in self.get('archivingPublishingChapter', 'distributions') or []:
            titles.append(((ds.get('dataset') or {}).get('_value') or '').strip() or '(unnamed dataset)')
        lhd = self.get('archivingPublishingChapter', 'listHaveDelete')
        if lhd and lhd.get('_value') == 'certainDataWas':
            for it in lhd.get('specifyListDelete') or []:
                titles.append(self.plain(it.get('briefDescriptionSet')) or 'Data scheduled for deletion')
        return titles

    def dataset_ids(self) -> dict[int, tuple[str, str]]:
        """Expected dataset_id of archived datasets with a PID, by index."""
        out = {}
        for i, ds in enumerate(self.get('archivingPublishingChapter', 'distributions') or []):
            hba = ds.get('hasBeenArchived') or {}
            epi = hba.get('enterPersistentIdentifier') if hba.get('_value') == 'trustworthyResearchData' else None
            if not epi:
                continue
            if epi.get('_value') == 'importDoiInformation' and self.payload(epi.get('doiSearch2')):
                doi = self.payload(epi['doiSearch2']).get('id')
                if doi:
                    out[i] = (doi if doi.startswith('http') else f'https://doi.org/{doi}', 'doi')
            elif epi.get('_value') == 'importInformationOmics' and self.payload(epi.get('omicsDiSearch')):
                raw = self.payload(epi['omicsDiSearch'])
                if raw.get('id') and raw.get('source'):
                    out[i] = (f'https://www.omicsdi.org/dataset/{raw["source"]}/{raw["id"]}', 'url')
            elif epi.get('_value') == 'enterLinkReference' and (epi.get('linkReference') or {}).get('_value'):
                link = epi['linkReference']['_value'].strip()
                out[i] = (link, 'doi' if 'doi.org' in link else 'url')
        return out

    def licenses(self) -> dict[int, str]:
        """Expected license_ref of datasets whose license is picked from the licence integration."""
        out = {}
        for i, ds in enumerate(self.get('archivingPublishingChapter', 'distributions') or []):
            ld = ds.get('licenseDataset') or {}
            raw = self.payload(ld.get('license')) if ld.get('_value') == 'dataAvailableUnder' else None
            if raw and (raw.get('props') or {}).get('url'):
                out[i] = raw['props']['url'].strip()
        return out

    def ethical_issues(self) -> str:
        legal = self.get('legalEthicalAspectsChapter') or {}
        yes = (legal.get('requiresEthicalApproval') or {}).get('_value') is True
        yes |= (legal.get('personalCollectedProcessed') or {}).get('_value') in ('yes', 'uncertain')
        yes |= (legal.get('sensitiveInformationThan') or {}).get('_value') in ('yes', 'uncertain')
        return 'yes' if yes else 'no'

    def version(self) -> str | None:
        q = self.ctx['questionnaire']
        vs = q.get('versions') or []
        chosen = next((v for v in vs if v['uuid'] == q.get('versionUuid')), None)
        if chosen is None and vs:
            chosen = max(vs, key=lambda v: v['createdAt'])
        return chosen['name'] if chosen else None

    def dmp_id(self):
        if self.ctx['project']:
            return {'identifier': f'{self.ctx["config"]["clientUrl"]}/projects/{self.owner["uuid"]}', 'type': 'url'}
        return {'identifier': self.owner['uuid'], 'type': 'other'}

    def project(self):
        res = self.get('researchProjectChapter') or {}
        def v(k):
            return ((res.get(k) or {}).get('_value') or '').strip() or None
        return {'title': v('name') or self.owner['name'].strip(), 'start': v('startDate'), 'end': v('endDate')}

    def answered_values(self) -> collections.Counter:
        """(json.key, json.value) of every answered options question."""
        seen = collections.Counter()

        def walk(o, key=None):
            if isinstance(o, dict):
                if '_label' in o and '_value' in o and key:
                    seen[(key, o['_value'])] += 1
                for k, v in o.items():
                    if not k.startswith('_'):
                        walk(v, k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
        walk(self.r)
        return seen


# ----------------------------------------------------------------------------- checks

class Findings:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, check: str, severity: str, case: str, fmt: str | None, path: str, msg: str):
        self.items.append({'check': check, 'severity': severity, 'context': case, 'format': fmt,
                           'path': path, 'message': msg[:300]})


def resolve(schema: dict, root: dict) -> dict:
    seen = 0
    while isinstance(schema, dict) and '$ref' in schema and seen < 20:
        ref = schema['$ref']
        node = root
        for part in ref.lstrip('#/').split('/'):
            node = node[part]
        schema = {**node, **{k: v for k, v in schema.items() if k != '$ref'}}
        seen += 1
    return schema


def declared(schema: dict, root: dict) -> tuple[dict, bool]:
    """Properties a schema declares (through allOf/anyOf/oneOf) and whether others are open."""
    schema = resolve(schema, root)
    props = dict(schema.get('properties') or {})
    open_ = bool(schema.get('patternProperties')) or isinstance(schema.get('additionalProperties'), dict)
    for comb in ('allOf', 'anyOf', 'oneOf'):
        for sub in schema.get(comb) or []:
            p, o = declared(sub, root)
            props.update(p)
            open_ |= o
    return props, open_


def undeclared(schema: dict, inst, root: dict, path: str = '') -> list[str]:
    schema = resolve(schema, root)
    out = []
    if isinstance(inst, dict):
        props, open_ = declared(schema, root)
        for k, v in inst.items():
            if k in props:
                out += undeclared(props[k], v, root, f'{path}/{k}')
            elif not open_:
                out.append(f'{path}/{k}')
    elif isinstance(inst, list):
        items = schema.get('items')
        if isinstance(items, dict):
            for i, v in enumerate(inst):
                out += undeclared(items, v, root, f'{path}/{i}')
    return out


def strings(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f'{path}/{i}')
    elif isinstance(o, str):
        yield path, o


def identifiers(o, path=''):
    if isinstance(o, dict):
        if 'identifier' in o and 'type' in o:
            yield path, o
        for k, v in o.items():
            yield from identifiers(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from identifiers(v, f'{path}/{i}')


KNOWN_DEVIATIONS = [
    # documented in src/_mapping.j2: a license without starting date is kept
    (re.compile(r"/license/\d+$"), re.compile(r"'start_date' is a required property")),
]


def check_document(f: Findings, case: Case, fmt: str, doc: dict, oracle: Oracle, validators: dict):
    key = FORMATS[fmt]
    schema, validator = validators[key]
    minor = 2 if key == 'ostrails' else int(key.split('.')[1])
    # schema (with formats)
    for e in validator.iter_errors(doc):
        p = '/' + '/'.join(map(str, e.absolute_path))
        known = any(rp.search(p) and rm.search(e.message) for rp, rm in KNOWN_DEVIATIONS)
        f.add('schema' if not known else 'schema-known-deviation', 'info' if known else 'error',
              case.name, fmt, p, e.message)
    for p in undeclared(schema, doc, schema):
        f.add('undeclared-member', 'error', case.name, fmt, p, f'not defined by schema {key}')
    dmp = doc.get('dmp', {})
    # hygiene
    for p, s in strings(dmp, '/dmp'):
        if s == '':
            f.add('hygiene-empty', 'error', case.name, fmt, p, 'empty string')
        if re.search(r'\b(None|Undefined)\b', s) or s in ('null', 'undefined'):
            f.add('hygiene-undefined', 'error', case.name, fmt, p, repr(s[:120]))
        if any(e in s for e in ESCAPED):
            f.add('hygiene-html-escaped', 'error', case.name, fmt, p, repr(s[:120]))
        if f'**{MD_BOLD}' in s or f']({MD_LINK}' in s or '[MDLINK' in s:
            f.add('hygiene-markdown', 'error', case.name, fmt, p, repr(s[:160]))
        if s != s.strip() and not p.endswith('/identifier'):
            f.add('hygiene-whitespace', 'error', case.name, fmt, p, repr(s[:80]))
    realistic = case.integrations == 'realistic'
    for p, ident in identifiers(dmp, '/dmp'):
        i, t = str(ident.get('identifier')), ident.get('type')
        bad = None
        if t == 'doi' and not i.startswith('https://doi.org/10.'):
            bad = 'doi identifier is not a https://doi.org/10.* URL'
        elif t == 'url' and not URL_RE.match(i):
            bad = 'url identifier is not a URL'
        elif t == 'orcid' and not ORCID_RE.match(i):
            bad = 'orcid identifier is not https://orcid.org/<iD>'
        elif t == 'ror' and not i.startswith('https://ror.org/'):
            bad = 'ror identifier is not https://ror.org/*'
        if bad:
            # generic payloads ({id, name}) carry no real identifiers: informative only
            f.add('identifier-format', 'error' if realistic else 'info',
                  case.name, fmt, p, f'{bad}: {i[:120]!r}')
    for di, ds in enumerate(dmp.get('dataset') or []):
        for xi, dist in enumerate(ds.get('distribution') or []):
            for li, lic in enumerate(dist.get('license') or []):
                ref = str(lic.get('license_ref'))
                if not URL_RE.match(ref):
                    # a badge = the rendered reply of an integration payload (a template bug);
                    # other text = a license typed by the user that is not a URL (input quality)
                    markdown = ref.startswith('![')
                    f.add('license-ref-not-url', 'error' if markdown else 'warning', case.name, fmt,
                          f'/dmp/dataset/{di}/distribution/{xi}/license/{li}', repr(ref[:160]))
    # oracle
    def expect(name, path, got, want):
        if got != want:
            f.add(f'oracle-{name}', 'error', case.name, fmt, path, f'expected {want!r}, got {got!r}'[:300])

    expect('title', '/dmp/title', dmp.get('title'), oracle.title())
    expect('ethical-issues', '/dmp/ethical_issues_exist', dmp.get('ethical_issues_exist'), oracle.ethical_issues())
    expect('dmp-id', '/dmp/dmp_id', dmp.get('dmp_id'), oracle.dmp_id())
    expect('created', '/dmp/created', dmp.get('created'),
           datetime.datetime.fromisoformat(oracle.owner['createdAt']).strftime(TS_FORMAT))
    expect('modified', '/dmp/modified', dmp.get('modified'),
           datetime.datetime.fromisoformat(oracle.owner['updatedAt']).strftime(TS_FORMAT))
    expect('version', '/dmp/version', dmp.get('version'), oracle.version() if key == 'ostrails' else None)
    expect('language', '/dmp/language', dmp.get('language'), case.injected.get('_language', 'eng'))
    if 'contact' not in dmp:
        f.add('oracle-contact', 'error', case.name, fmt, '/dmp/contact', 'no contact')
    contribs = oracle.contributors()
    got = dmp.get('contributor') or []
    expect('contributor-names', '/dmp/contributor', [c.get('name') for c in got], [c['name'] for c in contribs])
    if len(got) == len(contribs):
        for ci, (g, w) in enumerate(zip(got, contribs)):
            cid = g.get('contributor_id') or {}
            want = ({'identifier': f'https://orcid.org/{w["orcid"]}', 'type': 'orcid'} if w['orcid'] else 'other')
            have = cid if cid.get('type') == 'orcid' else cid.get('type')
            expect('orcid', f'/dmp/contributor/{ci}/contributor_id', have, want)
            if w['ror'] and minor >= 2 and w['ror'][1]:
                expect('affiliation', f'/dmp/contributor/{ci}/affiliation', g.get('affiliation'),
                       [{'affiliation_id': {'identifier': w['ror'][0], 'type': 'ror'}, 'name': w['ror'][1]}])
            if minor < 2 and 'affiliation' in g:
                f.add('version-gating', 'error', case.name, fmt, f'/dmp/contributor/{ci}/affiliation', 'affiliation before DCS 1.2')
    datasets = dmp.get('dataset') or []
    expect('dataset-titles', '/dmp/dataset', [d.get('title') for d in datasets], oracle.dataset_titles())
    if len(datasets) == len(oracle.dataset_titles()):
        for di, want in oracle.dataset_ids().items():
            d = datasets[di].get('dataset_id') or {}
            expect('dataset-id', f'/dmp/dataset/{di}/dataset_id', (d.get('identifier'), d.get('type')), want)
        for di, want in oracle.licenses().items():
            refs = [l.get('license_ref') for x in datasets[di].get('distribution') or [] for l in x.get('license') or []]
            if refs:
                expect('license-ref', f'/dmp/dataset/{di}/distribution/0/license/0', refs[0], want)
    proj = oracle.project()
    projects = dmp.get('project') or []
    if projects:
        expect('project-title', '/dmp/project/0/title', projects[0].get('title'), proj['title'])
        expect('project-start', '/dmp/project/0/start', projects[0].get('start'), proj['start'])
        expect('project-end', '/dmp/project/0/end', projects[0].get('end'), proj['end'])
    elif minor >= 1 or (proj['start'] and proj['end']):
        f.add('oracle-project', 'error', case.name, fmt, '/dmp/project', 'no project')


def summary_of(doc: dict) -> dict:
    dmp = doc.get('dmp', {})
    return {'title': dmp.get('title'), 'contributors': [c.get('name') for c in dmp.get('contributor') or []],
            'datasets': [d.get('title') for d in dmp.get('dataset') or []],
            'ethical': dmp.get('ethical_issues_exist'), 'description': dmp.get('ethical_issues_description'),
            'costs': len(dmp.get('cost') or [])}


# ----------------------------------------------------------------------------- report

def write_report(out: pathlib.Path, f: Findings, stats: dict, coverage: dict, examples: int):
    by_check = collections.defaultdict(list)
    for it in f.items:
        by_check[(it['severity'], it['check'])].append(it)
    order = {'error': 0, 'warning': 1, 'info': 2}
    lines = ['# End-to-end test report', '',
             f'- generated: {stats["when"]}',
             f'- contexts: {stats["contexts"]} ({", ".join(f"{k}: {v}" for k, v in stats["by_profile"].items())})',
             f'- KM editor previews: {stats["editors"]} (without package: {stats["nopkg"]}); '
             f'generic integration payloads: {stats["generic"]}; with Markdown/escaping sentinels: {stats["markup"]}',
             f'- documents: {stats["documents"]} rendered, {stats["render_failures"]} failed; '
             f'render time {stats["render_s"]:.1f} s ({stats["jobs"]} jobs)',
             f'- integration replies injected: {stats["payloads"]} payloads, {stats["plains"]} typed', '',
             '## Findings', '',
             '| severity | check | count | contexts | formats |', '|---|---|---:|---:|---|']
    for (sev, check), items in sorted(by_check.items(), key=lambda kv: (order[kv[0][0]], -len(kv[1]))):
        fmts = sorted({i['format'] or '-' for i in items})
        lines.append(f'| {sev} | {check} | {len(items)} | {len({i["context"] for i in items})} | '
                     f'{", ".join(x.replace("JSON ", "") for x in fmts)} |')
    if not by_check:
        lines.append('| - | none | 0 | 0 | - |')
    for (sev, check), items in sorted(by_check.items(), key=lambda kv: (order[kv[0][0]], -len(kv[1]))):
        lines += ['', f'### {sev}: {check}', '']
        seen = set()
        shown = 0
        for it in items:
            sig = (re.sub(r'/\d+', '/#', it['path']), it['message'][:60])
            if sig in seen:
                continue
            seen.add(sig)
            lines.append(f'- `{it["context"]}` {it["format"] or ""} `{it["path"]}`: {it["message"]}')
            shown += 1
            if shown >= examples:
                break
        if len(items) > shown:
            lines.append(f'- … {len(items) - shown} more (report.json)')
    lines += ['', '## Coverage of mapped answers', '',
              f'{coverage["reached"]} of {coverage["total"]} answer values the mapping refers to were selected '
              'in at least one context.', '']
    if coverage['missing']:
        lines.append('Never selected: ' + ', '.join(f'`{k}={v}`' for k, v in coverage['missing']))
    rare = sorted(coverage['counts'].items(), key=lambda kv: kv[1])[:12]
    lines += ['', 'Least selected (contexts): ' + ', '.join(f'`{k}` {n}' for k, n in rare)]
    lines += ['', '| integration question | payload | typed |', '|---|---:|---:|']
    for k, (p, t) in sorted(coverage['integrations'].items()):
        lines.append(f'| {k} | {p} | {t} |')
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out / 'report.json').write_text(json.dumps({'stats': stats, 'coverage': coverage, 'findings': f.items},
                                                indent=1, ensure_ascii=False, default=str), encoding='utf-8')


# ----------------------------------------------------------------------------- main

def chunks(items, n):
    n = max(1, n)
    return [items[i::n] for i in range(n) if items[i::n]]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--km', default=str(ROOT.parent / 'research.data.no.norway-generic_1.2.1.km'),
                   help='knowledge model bundle (.km)')
    p.add_argument('--seeds', type=int, default=8, help='number of seeds')
    p.add_argument('--seed-start', type=int, default=1)
    p.add_argument('--count', type=int, default=2, help='variants per profile and seed')
    p.add_argument('--profiles', nargs='+', default=list(PROFILES), choices=PROFILES)
    p.add_argument('--editor-share', type=float, default=0.05, help='share of KM editor previews (the rest are projects)')
    p.add_argument('--jobs', type=int, default=max(1, multiprocessing.cpu_count() - 1))
    p.add_argument('--out', default=str(ROOT / 'output' / 'e2e'))
    p.add_argument('--examples', type=int, default=8, help='examples per check in report.md')
    p.add_argument('--quick', action='store_true', help='2 seeds, 1 variant')
    args = p.parse_args(argv)
    if args.quick:
        args.seeds, args.count = 2, 1

    import shutil
    out = pathlib.Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    ctx_dir, doc_dir = out / 'contexts', out / 'documents'
    ctx_dir.mkdir(parents=True)
    doc_dir.mkdir()
    km_path = pathlib.Path(args.km)

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    cases = plan_cases(seeds, args.profiles, args.count, args.editor_share)
    print(f'generating {len(cases)} contexts ...', flush=True)
    t0 = time.monotonic()
    with multiprocessing.Pool(args.jobs) as pool:
        cases = pool.starmap(generate, [(c, km_path, ctx_dir) for c in cases])
    print(f'  {time.monotonic() - t0:.1f} s', flush=True)

    # locale pass: a few contexts copied and rendered with a document language
    locale_cases = []
    for c, lang, want in zip([c for c in cases if c.profile in ('typical', 'full')][:3],
                             ('nb', 'nn', 'de'), ('nob', 'nno', 'deu')):
        lc = copy.deepcopy(c)
        lc.name = f'{c.name}-lang-{lang}'
        lc.injected['_language'] = want
        (ctx_dir / f'{lc.name}.json').write_text((ctx_dir / f'{c.name}.json').read_text('utf-8'), 'utf-8')
        locale_cases.append((lc, lang))

    print(f'rendering {len(cases) + len(locale_cases)} contexts x {len(FORMATS)} formats ...', flush=True)
    t0 = time.monotonic()
    files = [str(ctx_dir / f'{c.name}.json') for c in cases]
    jobs = [(chunk, str(doc_dir), None) for chunk in chunks(files, args.jobs * 3)]
    jobs += [([str(ctx_dir / f'{lc.name}.json')], str(doc_dir), lang) for lc, lang in locale_cases]
    # determinism: the first contexts once more, into another directory
    again_dir = out / 'documents-again'
    again_dir.mkdir()
    again = files[:: max(1, len(files) // 10)][:10]
    jobs.append((again, str(again_dir), None))
    with multiprocessing.Pool(args.jobs) as pool:
        results = [r for batch in pool.imap_unordered(render, jobs) for r in batch]
    render_s = time.monotonic() - t0
    print(f'  {render_s:.1f} s', flush=True)

    findings = Findings()
    validators = {}
    import jsonschema
    for key in set(FORMATS.values()):
        schema = schemas.load_schema(key)
        cls = jsonschema.validators.validator_for(schema)
        validators[key] = (schema, cls(schema, format_checker=cls.FORMAT_CHECKER))

    all_cases = {c.name: c for c in cases} | {lc.name: lc for lc, _ in locale_cases}
    docs: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    again_docs = {}
    failures = 0
    for r in results:
        if r['error']:
            failures += 1
            findings.add('render', 'error', r['context'], r['format'], '', r['error'])
            continue
        path = pathlib.Path(r['output'])
        if path.parent == again_dir:
            again_docs[(r['context'], r['format'])] = path.read_bytes()
            continue
        try:
            docs[r['context']][r['format']] = json.loads(path.read_text('utf-8'))
        except ValueError as e:
            findings.add('json', 'error', r['context'], r['format'], '', str(e))

    print('checking ...', flush=True)
    coverage_values = collections.Counter()
    integ_cov = collections.defaultdict(lambda: [0, 0])
    km_index = None
    for name, by_fmt in sorted(docs.items()):
        case = all_cases[name]
        ctx = json.loads((ctx_dir / f'{name}.json').read_text('utf-8'))
        if km_index is None:
            km_index = KmIndex(ctx['knowledgeModel'])
        oracle = Oracle(ctx, case)
        for fmt, doc in by_fmt.items():
            check_document(findings, case, fmt, doc, oracle, validators)
        # same content in every format
        sums = {fmt: summary_of(doc) for fmt, doc in by_fmt.items()}
        ref_fmt = 'JSON (DCS 1.2)' if 'JSON (DCS 1.2)' in sums else next(iter(sums))
        for fmt, s in sums.items():
            for k, v in s.items():
                if v != sums[ref_fmt][k]:
                    findings.add('cross-format', 'error', name, fmt, f'/dmp/{k}',
                                 f'differs from {ref_fmt}: {v!r} vs {sums[ref_fmt][k]!r}'[:300])
        if '-lang-' not in name:
            for k in oracle.answered_values():
                coverage_values[k] += 1
            for path, inj in case.injected.items():
                if path.startswith('_'):
                    continue
                qkey = annotation(km_index.questions[path.split('.')[-1]], 'json.key')
                integ_cov[qkey][0 if inj['mode'] == 'payload' else 1] += 1
    for (name, fmt), content in again_docs.items():
        first = doc_dir / pathlib.Path(next(r['output'] for r in results
                                            if r['context'] == name and r['format'] == fmt
                                            and r['output'] and pathlib.Path(r['output']).parent == doc_dir)).name
        if first.read_bytes() != content:
            findings.add('determinism', 'error', name, fmt, '', 'second render differs')

    mapping = (ROOT / 'src' / '_mapping.j2').read_text('utf-8')
    # answers the mapping compares with: a json.value literal in the mapping that also occurs
    # next to the question's json.key (e.g. `ds.retention._value == "fixedPeriod"`)
    literals = set(re.findall(r'"([A-Za-z][A-Za-z0-9_]*)"', mapping))
    mapped = sorted((k, v) for (k, v) in km_index.answer_keys
                    if v in literals and re.search(rf'\b{re.escape(k)}\b', mapping))
    missing = [(k, v) for (k, v) in mapped if not coverage_values.get((k, v))]
    coverage = {'total': len(mapped), 'reached': len(mapped) - len(missing), 'missing': missing,
                'counts': {f'{k}={v}': coverage_values.get((k, v), 0) for k, v in mapped},
                'integrations': {k: tuple(v) for k, v in integ_cov.items()}}
    stats = {'when': datetime.datetime.now().isoformat(timespec='seconds'), 'contexts': len(cases),
             'by_profile': dict(collections.Counter(c.profile for c in cases)),
             'editors': sum(c.source == 'km-editor' for c in cases), 'nopkg': sum(c.no_package for c in cases),
             'generic': sum(c.integrations == 'generic' for c in cases), 'markup': sum(c.markup for c in cases),
             'documents': len(results) - failures, 'render_failures': failures, 'render_s': render_s,
             'jobs': args.jobs,
             'payloads': sum(i['mode'] == 'payload' for c in cases for k, i in c.injected.items() if not k.startswith('_')),
             'plains': sum(i['mode'] == 'plain' for c in cases for k, i in c.injected.items() if not k.startswith('_'))}
    write_report(out, findings, stats, coverage, args.examples)

    counts = collections.Counter(i['severity'] for i in findings.items)
    checks = collections.Counter(i['check'] for i in findings.items if i['severity'] == 'error')
    print(f'{stats["documents"]} documents, {counts["error"]} errors, {counts["warning"]} warnings, '
          f'{counts["info"]} known deviations')
    for c, n in checks.most_common():
        print(f'  {n:6d}  {c}')
    print(f'coverage: {coverage["reached"]}/{coverage["total"]} mapped answers reached')
    print(f'report: {out / "report.md"}')
    return 1 if counts['error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
