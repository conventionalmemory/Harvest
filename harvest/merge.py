import json, gzip, os, glob
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog')
for name, pat in (('raw.json.gz', 'parts/shard-*.json.gz'), ('ads.json.gz', 'parts/ads-*.json.gz')):
    F = os.path.join(OUT, name)
    parts = sorted(glob.glob(os.path.join(here, '..', pat)))
    if not parts: continue
    old = json.load(gzip.open(F, 'rt', encoding='utf-8')) if os.path.exists(F) else []
    key = (lambda x: x['i']) if name == 'raw.json.gz' else (lambda x: x[0])
    have = set(key(x) for x in old)
    add = []
    for p in parts:
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if key(x) not in have: have.add(key(x)); add.append(x)
    with gzip.open(F, 'wt', encoding='utf-8') as f:
        json.dump(old + add, f, ensure_ascii=False, separators=(',', ':'))
    print(name, 'old', len(old), 'added', len(add), 'total', len(old) + len(add))
