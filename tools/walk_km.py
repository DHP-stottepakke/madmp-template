"""Pre-flight: walk the KM in DSW-norway-export.json and print json.key/value tree."""
import json, sys, pathlib

src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'DSW-norway-export.json')
d = json.loads(src.read_text())
print(f"file: {src}")
print(f"metamodel: {d.get('metamodelVersion')}")
km = d['knowledgeModel'] if 'knowledgeModel' in d else d
ents = km['entities']
chs, qs = ents['chapters'], ents['questions']
ans, chc = ents['answers'], ents['choices']


def ann(e, k):
    for a in (e.get('annotations') or []):
        if a['key'] == k:
            return a['value']
    return None


def walk_q(q, indent=2):
    pad = '  ' * indent
    qkey = ann(q, 'json.key') or '<NO KEY>'
    qtype = q.get('questionType', '?')
    title = (q.get('title') or '?')[:55]
    print(f"{pad}{qkey:35s} [{qtype:18s}] {title}")
    for au in q.get('answerUuids') or []:
        a = ans.get(au)
        if not a:
            continue
        aval = ann(a, 'json.value') or '<no val>'
        print(f"{pad}    A val={aval!r}: {(a.get('label') or '')[:45]}")
        for fu in a.get('followUpUuids') or []:
            if fu in qs:
                walk_q(qs[fu], indent + 2)
    for cu in q.get('choiceUuids') or []:
        c = chc.get(cu)
        if not c:
            continue
        cval = ann(c, 'json.value') or '<no val>'
        print(f"{pad}    CH val={cval!r}: {(c.get('label') or '')[:45]}")
    for fu in q.get('itemTemplateQuestionUuids') or []:
        if fu in qs:
            walk_q(qs[fu], indent + 1)


for cu in km['chapterUuids']:
    c = chs[cu]
    ckey = ann(c, 'json.key') or '<NO KEY>'
    print(f"\n=== CHAPTER {ckey} : {c.get('title')} ===")
    for qu in c.get('questionUuids') or []:
        if qu in qs:
            walk_q(qs[qu])
