import json, os, re, sys, time, urllib.parse, urllib.request
UA = {'User-Agent': 'retrotv-sources logo harvester (https://github.com/conventionalmemory/harvest)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); IMG = os.path.join(OUT, 'logos'); os.makedirs(IMG, exist_ok=True)
API = 'https://commons.wikimedia.org/w/api.php'
WANT = json.load(open(os.path.join(here, 'logos_want.json')))
PER = int(os.environ.get('PER', '8'))
def get(params, tries=4):
    u = API + '?' + urllib.parse.urlencode(dict(params, format='json', formatversion=2))
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if k == tries - 1: print('fail', u[:140], e, flush=True); return {}
            time.sleep(3 * (k + 1))
def fetch(url, fn, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            open(fn, 'wb').write(b); return len(b)
        except Exception as e:
            if k == tries - 1: print('dlfail', url[:140], e, flush=True); return 0
            time.sleep(3 * (k + 1))
def clean(s):
    return re.sub(r'<[^>]+>', '', str(s or '')).strip()[:300]
LOGOW = re.compile(r'logo|wordmark|ident|\bid\b|bug', re.I)
NOPE = re.compile(r'\b(building|studio|tower|truck|van|headquarters|hq|office|camera|microphone|photo|staff|anchor|people|street|sign at|signage|map|coverage|screenshot|screen ?shot)\b', re.I)
out = []
for w in WANT:
    seen, cand = set(), []
    for q in w['q']:
        j = get({'action': 'query', 'list': 'search', 'srnamespace': 6, 'srsearch': q, 'srlimit': 25})
        for h in (j.get('query') or {}).get('search', []):
            t = h['title']
            if t in seen or not re.search(r'\.(svg|png|gif|jpe?g)$', t, re.I): continue
            seen.add(t); cand.append(t)
        time.sleep(.3)
    rows = []
    for k in range(0, len(cand), 20):
        j = get({'action': 'query', 'titles': '|'.join(cand[k:k + 20]), 'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 480})
        for pg in (j.get('query') or {}).get('pages', []):
            ii = (pg.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata') or {}
            lic = clean((em.get('LicenseShortName') or {}).get('value'))
            desc = clean((em.get('ImageDescription') or {}).get('value'))
            art = clean((em.get('Artist') or {}).get('value'))
            cr = clean((em.get('Credit') or {}).get('value'))
            t = pg['title']
            score = (3 if LOGOW.search(t) else 0) + (2 if LOGOW.search(desc) else 0) + (2 if re.search(r'public domain|pd|cc0', lic, re.I) else 0) - (4 if NOPE.search(t + ' ' + desc[:120]) else 0)
            key = re.sub(r'[^A-Z0-9]', '', w['k'].upper())
            if key and key[:3] in re.sub(r'[^A-Z0-9]', '', t.upper()): score += 2
            rows.append({'title': t, 'url': ii.get('thumburl') or ii.get('url'), 'orig': ii.get('url'), 'page': ii.get('descriptionurl'), 'w': ii.get('width'), 'h': ii.get('height'), 'mime': ii.get('mime'), 'license': lic, 'artist': art, 'credit': cr, 'desc': desc, 'score': score})
        time.sleep(.3)
    rows.sort(key=lambda r: -r['score'])
    keep = [r for r in rows if r['score'] >= 3][:PER]
    for i, r in enumerate(keep):
        fn = '%s__%d.png' % (re.sub(r'[^A-Za-z0-9]+', '_', w['k']), i)
        n = fetch(r['url'], os.path.join(IMG, fn)) if r['url'] else 0
        if n: r['file'] = fn; r['bytes'] = n
        time.sleep(.2)
    keep = [r for r in keep if r.get('file')]
    print(w['k'], len(cand), 'cands', len(keep), 'kept', [r['title'][5:60] for r in keep], flush=True)
    out.append({'k': w['k'], 'files': keep})
json.dump(out, open(os.path.join(OUT, 'logos.json'), 'w'), ensure_ascii=False, indent=0)
print('done', sum(len(x['files']) for x in out), 'files')
