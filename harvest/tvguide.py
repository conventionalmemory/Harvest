import gzip, json, os, re, time, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'parts', 'tvguide.json.gz')
UA = 'ConventionalMemoryRetroTV/1.0 (https://github.com/conventionalmemory/Harvest)'
def get(u, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(3 + 3 * k)
    return b''
QS = ['(title:("tv guide") OR subject:("tv guide")) AND (chicago OR illinois OR wisconsin OR rockford OR milwaukee OR madison)',
      'title:("tv guide") AND year:[1984 TO 2004]',
      '(title:("tv week") OR title:("tv listings") OR title:("tv magazine") OR title:("tv times")) AND (chicago OR rockford OR illinois)',
      '(rockford register star OR "register star") AND (tv OR television)',
      '(wrex OR wtvo OR wifr OR wqrf) AND (listings OR schedule OR guide)']
items = {}
for q in QS:
    for page in range(1, 6):
        u = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': q, 'fl[]': ['identifier', 'title', 'date', 'year', 'description'], 'rows': 500, 'page': page, 'output': 'json'}, doseq=True)
        try: j = json.loads(get(u) or b'{}')
        except Exception: j = {}
        docs = (j.get('response') or {}).get('docs') or []
        for d in docs: items.setdefault(d['identifier'], d)
        if len(docs) < 500: break
print('items', len(items), flush=True)
KEEPRE = re.compile(r'(?i)\b(wrex|wtvo|wifr|wqrf|rockford|freeport)\b|\(\s*(13|17|23|39)\s*\)|^\s*(13|17|23|39)\s+[A-Z]')
res = {}
T0 = time.time()
for n, (i, d) in enumerate(sorted(items.items())):
    if time.time() - T0 > float(os.environ.get('BUDGET_MIN', '80')) * 60: break
    t = str(d.get('title') or ''); ds = str(d.get('description') or '')[:400]
    if not re.search(r'(?i)tv|television|guide|listing', t + ' ' + ds): continue
    try: files = json.loads(get('https://archive.org/metadata/' + urllib.parse.quote(i) + '/files') or b'{}').get('result') or []
    except Exception: files = []
    txt = [f['name'] for f in files if f['name'].endswith('_djvu.txt')][:3]
    rec = {'t': t[:200], 'd': str(d.get('date') or d.get('year') or ''), 'ds': ds, 'n': [f['name'] for f in files][:40], 'hits': []}
    for f in txt:
        b = get('https://archive.org/download/' + urllib.parse.quote(i) + '/' + urllib.parse.quote(f))
        s = b.decode('utf-8', 'replace')
        rec['rf'] = rec.get('rf', 0) + len(re.findall(r'(?i)\b(wrex|wtvo|wifr|wqrf|rockford)\b', s))
        lines = s.splitlines()
        for k, l in enumerate(lines):
            if KEEPRE.search(l): rec['hits'].append(' | '.join(x.strip() for x in lines[max(0, k - 1):k + 2])[:300])
        rec['hits'] = rec['hits'][:4000]
    res[i] = rec
    if n % 20 == 0: print(n, i, rec.get('rf', 0), len(rec['hits']), flush=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, gzip.open(OUT, 'wt', encoding='utf-8'))
print('done', len(res), sorted(((v.get('rf', 0), k) for k, v in res.items()), reverse=True)[:30], flush=True)
