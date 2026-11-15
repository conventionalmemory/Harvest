import gzip, json, os, sys, time, random, datetime, threading, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USED = os.path.join(ROOT, 'catalog', 'ia_used.json.gz')
OUT = os.path.join(ROOT, 'catalog', 'ia_health.json.gz')
PARTS = os.path.join(ROOT, 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'check')
SHARD, SHARDS = int(os.environ.get('SHARD', '0')), int(os.environ.get('SHARDS', '1'))
SLICE = (os.environ.get('SLICE', '') or 'day').strip()
THREADS = int(os.environ.get('THREADS', '10'))
BUDGET = float(os.environ.get('BUDGET_MIN', '50')) * 60
T0 = time.time(); LOCK = threading.Lock(); ST = {'ok': 0, 'dead': 0, 'miss': 0, 'err': 0}
UA = {'User-Agent': 'Mozilla/5.0 (retrotv link check)'}
def h(s):
    v = 7
    for ch in s: v = (v * 31 + ord(ch)) & 0xffffffff
    return v
def meta(i):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request('https://archive.org/metadata/' + urllib.parse.quote(i), headers=UA), timeout=40) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404): return {}
            time.sleep(3 + k * 5)
        except Exception: time.sleep(2 + k * 4)
    return None
def one(item):
    i, files = item
    if time.time() - T0 > BUDGET: return None
    j = meta(i)
    if j is None:
        with LOCK: ST['err'] += 1
        return None
    if not j.get('files') or j.get('is_dark') or str((j.get('metadata') or {}).get('access-restricted-item', '')).lower() == 'true':
        with LOCK: ST['dead'] += 1
        return [i, 'dead', []]
    names = set(f.get('name', '') for f in j['files'])
    miss = [f for f in files if f not in names]
    with LOCK: ST['miss' if miss else 'ok'] += 1
    return [i, 'miss' if miss else 'ok', miss]
def check():
    U = json.load(gzip.open(USED, 'rt', encoding='utf-8'))
    items = sorted(U.items())
    dow = datetime.datetime.utcnow().weekday()
    if SLICE == 'day': items = [x for x in items if h(x[0]) % 7 == dow]
    items = [x for x in items if h(x[0] + '#') % SHARDS == SHARD]
    print('checking', len(items), 'slice', SLICE, flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for r in ex.map(one, items):
            if r: res.append(r)
    json.dump(res, gzip.open(os.path.join(PARTS, 'iah-%d.json.gz' % SHARD), 'wt', encoding='utf-8'))
    print('done', ST, flush=True)
def merge():
    old = json.load(gzip.open(OUT, 'rt', encoding='utf-8')) if os.path.exists(OUT) else {'items': {}}
    it = old.get('items', {})
    today = datetime.date.today().isoformat()
    n = 0
    for fn in sorted(os.listdir(PARTS)):
        if not (fn.startswith('iah-') and fn.endswith('.json.gz')): continue
        for i, s, miss in json.load(gzip.open(os.path.join(PARTS, fn), 'rt', encoding='utf-8')):
            n += 1
            if s == 'ok': it.pop(i, None)
            else:
                prev = it.get(i)
                it[i] = [s, miss, prev[2] if prev else today, today, (prev[4] + 1) if prev else 1]
    U = json.load(gzip.open(USED, 'rt', encoding='utf-8'))
    it = {k: v for k, v in it.items() if k in U}
    json.dump({'t': today, 'checked': n, 'items': it}, gzip.open(OUT, 'wt', encoding='utf-8'), separators=(',', ':'))
    print('merged', n, 'bad now', len(it), sum(1 for v in it.values() if v[0] == 'dead'), 'dead', flush=True)
if MODE == 'check': check()
elif MODE == 'merge': merge()
