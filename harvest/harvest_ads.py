import json, gzip, os, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
F = os.path.join(OUT, 'ads.json.gz')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
old = json.load(gzip.open(F, 'rt', encoding='utf-8')) if os.path.exists(F) else []
have = set(x[0] for x in old)
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:100], e, flush=True); return None
            time.sleep(3 * (k + 1))
items, cursor = [], None
q = 'collection:(vhscommercials OR classic_tv_commercials) AND mediatype:movies'
while True:
    u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year', 'q': q, 'count': 10000, **({'cursor': cursor} if cursor else {})})
    j = get(u)
    if not j: break
    items += j.get('items', []); cursor = j.get('cursor')
    if not cursor: break
items = sorted([x for x in items if x['identifier'] not in have], key=lambda x: x['identifier'])[SHARD::SHARDS]
print('ads to fetch', len(items), 'existing', len(old), flush=True)
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']) + '/files')
    if not j: return None
    fs = [f for f in j.get('result', []) if f.get('name', '').lower().endswith('.mp4')]
    if not fs: return None
    fs.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
    b = fs[0]
    d = secs(b.get('length') or next((x.get('length') for x in fs if x.get('length')), 0))
    if d < 4 or d > 150: return None
    return [it['identifier'], b['name'], round(d, 1), str(it.get('date') or it.get('year') or '')[:10], str(it.get('title') or '')[:120]]
res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, items)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), flush=True)
PF = os.path.join(here, '..', 'parts'); os.makedirs(PF, exist_ok=True)
with gzip.open(os.path.join(PF, 'ads-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(res))
