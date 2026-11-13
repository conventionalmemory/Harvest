import json, gzip, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'retrotv-sources/1.0 (https://conventionalmemory.io; movie shelf builder)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
Y0, Y1 = int(os.environ.get('Y0', '1972')), int(os.environ.get('Y1', '2004'))
PER = int(os.environ.get('PER', '220'))
def get(url, tries=5, accept='application/json'):
    for k in range(tries):
        try:
            h = dict(UA); h['Accept'] = accept
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(4 * (k + 1))
Q = '''SELECT ?film ?label (MIN(?date) AS ?d) (MAX(?sl) AS ?links) (MAX(?b) AS ?bo) (MAX(?du) AS ?dur) (SAMPLE(?rl) AS ?rating) (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres) WHERE {
 ?film wdt:P31 wd:Q11424; wdt:P495 wd:Q30; wdt:P577 ?date; wikibase:sitelinks ?sl; rdfs:label ?label FILTER(lang(?label)="en")
 FILTER(?date >= "%d-01-01T00:00:00Z"^^xsd:dateTime && ?date < "%d-01-01T00:00:00Z"^^xsd:dateTime)
 FILTER(?sl >= 6)
 FILTER NOT EXISTS { ?film wdt:P31 wd:Q506240 }
 FILTER NOT EXISTS { ?film wdt:P136 wd:Q93204 }
 OPTIONAL{?film wdt:P2142 ?b}
 OPTIONAL{?film wdt:P2047 ?du}
 OPTIONAL{?film wdt:P1657 ?r. ?r rdfs:label ?rl FILTER(lang(?rl)="en")}
 OPTIONAL{?film wdt:P136 ?g. ?g rdfs:label ?gl FILTER(lang(?gl)="en")}
} GROUP BY ?film ?label ORDER BY DESC(?links) LIMIT %d'''
films, seen = [], set()
for y in range(Y0, Y1 + 1):
    j = get('https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(Q % (y, y + 1, PER)), accept='application/sparql-results+json')
    rows = (j or {}).get('results', {}).get('bindings', [])
    n = 0
    for r in rows:
        fid = r['film']['value'].rsplit('/', 1)[-1]
        if fid in seen: continue
        seen.add(fid); n += 1
        v = lambda k: r.get(k, {}).get('value', '')
        try: bo = float(v('bo') or 0)
        except Exception: bo = 0
        try: du = float(v('dur') or 0)
        except Exception: du = 0
        try: sl = int(float(v('links') or 0))
        except Exception: sl = 0
        films.append({'q': fid, 't': v('label'), 'd': v('d')[:10], 'bo': bo, 'sl': sl, 'g': [g for g in v('genres').split('|') if g][:6], 'r': v('rating'), 'rt': du})
    print('year', y, 'films', n, flush=True)
    time.sleep(2)
def norm(s):
    s = s.lower().replace('&', 'and')
    s = re.sub(r"[’'`]", '', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()
BAD = r'\b(trailers?|teasers?|opening|closing|promo|soundtrack|ost|review|behind the scenes|making of|commentary|tv spots?|featurette|scenes?|clips?|music video|fan ?made|fan ?edit|parody|reaction|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|fran[cç]ais|italiano|russian|hindi|tamil|soundtracks?|audio ?book|novel|book|comic|game|gameplay|walkthrough|lego|minecraft|toy|toys|interview|premiere|press|outtakes|deleted|bloopers?|karaoke|sing ?along|ep\s?\d|episode)\b'
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
def files_of(ident):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(ident))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    lang = str(m.get('language', '')).lower()
    if lang and not re.search(r'eng|english', lang): return None
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    out = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 120: continue
        out.append([b['name'], round(d)])
    out.sort(key=lambda f: f[0])
    return out
def match(f):
    nt = norm(f['t'])
    if len(nt) < 2: return f
    y = int(f['d'][:4]) if f['d'][:4].isdigit() else 0
    q = 'title:("%s") AND mediatype:movies' % f['t'].replace('"', '')
    j = get('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': q, 'fl[]': ['identifier', 'title', 'downloads', 'year'], 'rows': 40, 'output': 'json'}, doseq=True))
    docs = (j or {}).get('response', {}).get('docs', [])
    cands = []
    for d in docs:
        t = str(d.get('title') or '')
        if isinstance(d.get('title'), list): t = ' '.join(d['title'])
        tl = t.lower()
        if re.search(BAD, tl): continue
        nd = norm(t)
        if not (nd == nt or nd.startswith(nt + ' ') or (' ' + nt + ' ') in (' ' + nd + ' ')): continue
        ys = [int(x) for x in re.findall(r'\b(19\d\d|20\d\d)\b', t)]
        if ys and y and not any(abs(x - y) <= 1 for x in ys): continue
        rest = nd.replace(nt, ' ', 1).split()
        if len([w for w in rest if not re.match(r'^(19|20)\d\d$', w) and w not in ('vhs', 'rip', 'full', 'movie', 'film', 'the', 'tape', 'widescreen', 'fullscreen', 'version', 'edition', 'cut', 'theatrical', 'dvd', 'tv', 'laserdisc', 'ld', 'ntsc', 'original', 'release', 'woc', 'with', 'commercials', 'broadcast', 'abc', 'cbs', 'nbc', 'fox', 'hbo', 'cinemax', 'showtime', 'tnt', 'tbs', 'usa', 'version', 'remastered', 'uncut', 'complete', 'hd', 'sd')]) > 3: continue
        cands.append((-(d.get('downloads') or 0), d['identifier']))
    cands.sort()
    need = max(3600, 0.7 * (f['rt'] or 90) * 60)
    for _, ident in cands[:4]:
        fs = files_of(ident)
        if not fs: continue
        tot = sum(x[1] for x in fs)
        big = [x for x in fs if x[1] >= need]
        if big:
            f['ia'] = [ident, [big[0]]]; return f
        if need <= tot <= 4.5 * 3600 and len(fs) <= 6:
            f['ia'] = [ident, fs]; return f
    return f
res = []
with ThreadPoolExecutor(int(os.environ.get('THREADS', '12'))) as ex:
    for n, r in enumerate(ex.map(match, films)):
        res.append(r)
        if n % 250 == 0: print('match', n, sum(1 for x in res if x.get('ia')), flush=True)
with gzip.open(os.path.join(OUT, 'movies.json.gz'), 'wt', encoding='utf-8') as fo:
    json.dump(res, fo, ensure_ascii=False, separators=(',', ':'))
print('done films', len(res), 'playable', sum(1 for x in res if x.get('ia')))
