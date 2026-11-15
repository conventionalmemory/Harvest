import gzip, json, os, re, time, urllib.request, urllib.parse, collections

API = 'https://en.wikipedia.org/w/api.php'
UA = 'ConventionalMemoryTV/1.0 (https://conventionalmemory.io)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'wiki_shows.json.gz')

def api(**p):
    p.update(format='json', formatversion='2')
    u = API + '?' + urllib.parse.urlencode(p)
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            time.sleep(3 + 4 * k)
    return {}

def members(cat):
    out = []; cont = {}
    while True:
        d = api(action='query', list='categorymembers', cmtitle='Category:' + cat, cmlimit='500', cmnamespace='0', **cont)
        out += [m['title'] for m in (d.get('query') or {}).get('categorymembers', [])]
        if 'continue' not in d: break
        cont = {'cmcontinue': d['continue']['cmcontinue']}
    return out

def cats(titles):
    res = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]; cont = {}
        while True:
            d = api(action='query', prop='categories|pageprops', titles='|'.join(chunk), cllimit='max', clshow='!hidden', ppprop='disambiguation', redirects='1', **cont)
            for pg in (d.get('query') or {}).get('pages', []):
                r = res.setdefault(pg['title'], [])
                r += [c['title'][9:] for c in pg.get('categories', [])]
            if 'continue' not in d: break
            cont = {k: v for k, v in d['continue'].items()}
        time.sleep(.2)
    return res

pages = collections.defaultdict(dict)
for y in range(1984, 2005):
    for kind in ('debuts', 'endings'):
        L = members('%d American television series %s' % (y, kind))
        print(y, kind, len(L), flush=True)
        for t in L: pages[t]['debut' if kind == 'debuts' else 'end'] = y
C = cats(sorted(pages))
rows = []
for t, v in pages.items():
    cs = C.get(t, [])
    dy = v.get('debut'); ey = v.get('end')
    for c in cs:
        m = re.match(r'(\d{4}) American television series debuts', c)
        if m and not dy: dy = int(m.group(1))
        m = re.match(r'(\d{4}) American television series endings', c)
        if m and not ey: ey = int(m.group(1))
    rows.append({'page': t, 'title': re.sub(r'\s*\((19|20)\d\d (TV series|American TV series|game show|talk show)\)$|\s*\((American )?(TV|television) (series|program|programme|show)\)$|\s*\((19|20)\d\d (film|TV program)\)$', '', t), 'debut': dy, 'end': ey, 'cats': cs})
json.dump(rows, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('TOTAL', len(rows))
cc = collections.Counter(c for r in rows for c in r['cats'] if 'original programming' in c or 'syndicat' in c.lower())
print(cc.most_common(60))
