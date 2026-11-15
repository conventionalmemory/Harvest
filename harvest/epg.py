import json, gzip, os, re, time, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'epguide.json.gz')
WANT = json.load(open(os.path.join(ROOT, 'harvest', 'epg_want.json')))
UA = {'User-Agent': 'ConventionalMemoryTV/1.0 (https://conventionalmemory.io)'}
def get(u):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(5 + 5 * k)
        except Exception:
            time.sleep(3 + 3 * k)
    return None
def key(x):
    x = str(x).lower().replace('&', ' and ').replace("'", '')
    return re.sub(r'[^a-z0-9]+', ' ', x).strip()
G = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
n = 0
for name in WANT:
    k = key(name)
    if k in G and not G[k].get('miss'): continue
    q = re.sub(r'\b(sbtb tnc)\b', 'saved by the bell the new class', name.lower())
    j = get('https://api.tvmaze.com/singlesearch/shows?' + urllib.parse.urlencode({'q': q, 'embed': 'episodes'}))
    time.sleep(0.6)
    if not j or not (j.get('_embedded') or {}).get('episodes'):
        G[k] = {'miss': 1, 'name': name}; continue
    pre = j.get('premiered') or ''
    if pre and pre > '2005-12-31': G[k] = {'miss': 1, 'name': name, 'why': 'late'}; continue
    eps = [[e.get('season'), e.get('number') or 0, e.get('airdate') or '', e.get('name') or ''] for e in j['_embedded']['episodes']]
    G[k] = {'title': j.get('name'), 'id': j.get('id'), 'premiered': pre, 'ended': j.get('ended'), 'network': ((j.get('network') or j.get('webChannel') or {}) or {}).get('name'), 'episodes': eps}
    n += 1
    print('ok', name, '->', j.get('name'), pre, len(eps), flush=True)
json.dump(G, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('added', n)
