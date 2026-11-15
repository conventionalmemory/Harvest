import gzip, json, os, time, urllib.request, urllib.parse

API = os.environ.get('API') or 'https://en.wikipedia.org/w/api.php'
UA = os.environ.get('UA') or 'ConventionalMemoryTV/1.0 (https://conventionalmemory.io)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', os.environ.get('OUTF') or 'wikipages.json.gz')

def api(**p):
    p.update(format='json', formatversion='2')
    u = API + '?' + urllib.parse.urlencode(p)
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            time.sleep(3 + 4 * k)
    return {}

def search(q):
    d = api(action='query', list='search', srsearch=q, srlimit='3')
    return [x['title'] for x in (d.get('query') or {}).get('search', [])]

T = [x.strip() for x in os.environ.get('PAGES', '').split('|') if x.strip()]
for q in [x.strip() for x in os.environ.get('SEARCH', '').split('|') if x.strip()]:
    d = api(action='query', list='search', srsearch=q, srlimit='25')
    for x in (d.get('query') or {}).get('search', []):
        if x['title'] not in T: T.append(x['title'])
    print('search', q, len(T), flush=True)
for y in (range(1984, 2004) if not os.environ.get('NOSCHED') else []):
    s = '%d–%02d' % (y, (y + 1) % 100)
    for kind in ('Saturday morning', 'weekday', 'Sunday morning'):
        T.append('%s United States network television schedule (%s)' % (s, kind))
res = {}
try:
    res = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
except Exception:
    pass
for i in range(0, len(T), 20):
    chunk = T[i:i + 20]
    d = api(action='query', prop='revisions', rvprop='content', rvslots='main', titles='|'.join(chunk), redirects='1')
    q = d.get('query') or {}
    back = {}
    for r in q.get('normalized', []) + q.get('redirects', []):
        back[r['to']] = back.get(r['from'], r['from'])
    for pg in q.get('pages', []):
        if pg.get('missing'):
            continue
        txt = pg['revisions'][0]['slots']['main']['content']
        src = back.get(pg['title'], pg['title'])
        res[src] = {'page': pg['title'], 'text': txt}
        print('ok', src, '->', pg['title'], len(txt), flush=True)
    time.sleep(.3)
for t in T:
    if t not in res and not t.endswith(')'):
        print('missing', t, search(t))
json.dump(res, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('TOTAL', len(res))
