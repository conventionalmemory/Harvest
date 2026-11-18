import json, gzip, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
OUTF = os.path.join(OUT, 'offair.json.gz')
BUDGET = float(os.environ.get('BUDGET_MIN', '150')) * 60; T0 = time.time()
SHOWS = json.load(open(os.path.join(here, 'shows_offair.json'), encoding='utf-8'))
ONLY = [x.strip().lower() for x in (os.environ.get('ONLY', '') or '').split('|') if x.strip()]
TAPEQ = '(vhs OR woc OR commercials OR "off air" OR "off-air" OR recorded OR recording OR broadcast OR tape OR taped OR "news at" OR "11pm" OR "10pm" OR tgif OR "prime time" OR primetime OR lineup OR block)'
VID = re.compile(r'(?i)\.(mp4|mkv|avi|mpe?g|ogv|webm|mov|m4v|wmv|flv|ts|vob)$')


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))


def scrape(q, cap=3000):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads', 'q': q, 'count': 1000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) >= cap: break
    return out


def secs(v):
    try:
        if isinstance(v, str) and ':' in v:
            p = [float(x) for x in v.split(':')]; t = 0
            for x in p: t = t * 60 + x
            return int(t)
        return int(float(v))
    except Exception: return 0


def sv(v):
    return ' '.join(str(x) for x in v) if isinstance(v, list) else str(v or '')


def queries(s):
    nm = s['title']; alts = [nm] + list(s.get('aka') or [])
    ys = list(range(s['years'][0], s['years'][1] + 1))
    net = s.get('net') or ''
    qs = []
    for a in alts:
        ph = '"%s"' % a.replace('"', '')
        if s.get('amb'):
            qs.append('mediatype:movies AND %s AND (%s) AND (%s)' % (ph, net or 'tv', ' OR '.join(str(y) for y in ys)))
            qs.append('mediatype:movies AND title:(%s) AND %s' % (ph, TAPEQ))
        else:
            qs.append('mediatype:movies AND %s AND %s' % (ph, TAPEQ))
            qs.append('mediatype:movies AND %s AND (%s)' % (ph, ' OR '.join(str(y) for y in ys)))
    return qs


def meta(ident):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(ident, safe=''))
    if not j or not isinstance(j.get('metadata'), dict): return None
    m = j['metadata']; files = []
    for f in j.get('files') or []:
        n = f.get('name') or ''
        if not VID.search(n) or f.get('source') == 'derivative' and not n.endswith('.mp4'): continue
        d = secs(f.get('length'))
        if d < 600: continue
        files.append([n, d, f.get('format') or ''])
    return {'i': ident, 't': sv(m.get('title'))[:300], 'd': sv(m.get('date'))[:20], 'ds': re.sub(r'<[^>]+>', ' ', sv(m.get('description')))[:3000], 's': sv(m.get('subject'))[:600], 'c': (m.get('collection') if isinstance(m.get('collection'), list) else [m.get('collection')])[:4], 'up': '', 'f': files[:80]}


def main():
    prev = {}
    if os.path.exists(OUTF):
        try:
            for x in json.load(gzip.open(OUTF, 'rt', encoding='utf-8')): prev[x['i']] = x
        except Exception: prev = {}
    sel = [s for s in SHOWS if not ONLY or s['title'].lower() in ONLY]
    hits = {}
    for s in sel:
        if time.time() - T0 > BUDGET * .4: break
        n0 = 0
        for q in queries(s):
            for it in scrape(q):
                h = hits.setdefault(it['identifier'], {'k': set(), 'dl': it.get('downloads') or 0})
                h['k'].add(s['title']); n0 += 1
        print('search', s['title'], n0, flush=True)
    todo = [i for i in hits if i not in prev]
    print('items', len(hits), 'new', len(todo), flush=True)
    res = dict(prev)
    def one(i):
        if time.time() - T0 > BUDGET: return
        m = meta(i)
        if m: res[i] = m
    with ThreadPoolExecutor(8) as ex: list(ex.map(one, todo))
    for i, h in hits.items():
        if i in res: res[i]['k'] = sorted(set(res[i].get('k') or []) | h['k']); res[i]['dl'] = h['dl']
    L = [x for x in res.values() if x.get('f')]
    L.sort(key=lambda x: x['i'])
    json.dump(L, gzip.open(OUTF, 'wt', encoding='utf-8'))
    print('saved', len(L), 'with video;', len(res) - len(L), 'without', flush=True)


main()
