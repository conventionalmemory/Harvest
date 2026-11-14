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
MF = os.path.join(OUT, 'movies.json.gz')
films, seen = [], set()
if os.path.exists(MF) and os.environ.get('REFRESH') != '1':
    for x in json.load(gzip.open(MF, 'rt', encoding='utf-8')):
        films.append({k: x[k] for k in ('q', 't', 'd', 'bo', 'sl', 'g', 'r', 'rt') if k in x})
        if x.get('ia'): seen.add(x['q'])
    HAD = set(seen)
    print('reusing film list', len(films), 'previously matched', len(HAD), flush=True)
else:
    HAD = None
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
    if lang and not re.search(r'eng|english|^en\b', lang): return 'foreign'
    blob = (str(m.get('title', '')) + ' ' + str(m.get('description', ''))[:600] + ' ' + str(m.get('subject', ''))).lower()
    if re.search(FOREIGN, blob): return 'foreign'
    hmax = 0
    groups = {}
    for f in j['files']:
        try: hmax = max(hmax, int(f.get('height') or 0))
        except Exception: pass
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
    return out, hmax, blob
FOREIGN = r"\b(dublado|dublada|doblaje|doblada|doblado|latino|castellano|espa[nñ]ol|subtitulad[oa]|legendado|deutsch|german dub|synchronisiert|fran[cç]ais|\bvf\b|\bvostfr\b|truefrench|italiano|\bita\b|russian|rus dub|hindi|tamil|telugu|urdu|polski|lektor|magyar|szinkron|t[uü]rk[cç]e|arabic dub|dubbed in|en espa|pel[ií]cula completa|filme completo|film complet|ganzer film|film completo)\b"
OKW = set('vhs rip vhsrip full movie film the tape widescreen fullscreen version edition cut theatrical dvd dvdrip tv laserdisc ld ntsc original release woc with commercials broadcast abc cbs nbc fox hbo cinemax showtime tnt tbs usa remastered uncut unrated complete hd sd betamax beta 480p 360p 240p english eng open matte pan scan and letterbox letterboxed directors special extended mp4 avi xvid divx ac3 x264 h264 aac'.split())
T_TAPE = r"\b(vhs|vhsrip|vhs rip|betamax|beta ?max|laser ?disc|\bld ?rip\b|tv ?rip|recorded (from|off)|off[- ]air|videotape|video tape|ced)\b"
T_TV = r"\b(with commercials|w/ ?commercials|woc|broadcast|tv edit|edited for tv|tv version|network (premiere|version|tv))\b"
T_DVD = r"\b(dvd|dvdrip|dvd rip|dvd5|dvd9)\b"
T_HD = r"\b(1080p?|2160p?|4k|uhd|blu-?ray|bdrip|brrip|bd ?rip|remux|hdr|x265|hevc|web-?dl|webrip|720p|hdtv|remaster(ed)?|criterion)\b"
T_CAM = r"\b(cam|camrip|telesync|hdcam|\bts\b)\b"
T_PACK = r"\b(double feature|triple feature|trilogy|collection|box ?set|\d+ (movies|films)|marathon|anthology pack)\b"
CNT = {'foreign': 0}
def search(q, rows=50):
    j = get('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': q, 'fl[]': ['identifier', 'title', 'downloads', 'year', 'language', 'description'], 'rows': rows, 'output': 'json'}, doseq=True), tries=3)
    return (j or {}).get('response', {}).get('docs', [])
def variants(t):
    out = [t]
    if ':' in t: out.append(t.split(':')[0].strip())
    if ' - ' in t: out.append(t.split(' - ')[0].strip())
    if t.lower().startswith('the '): out.append(t[4:])
    return [x for i, x in enumerate(out) if len(norm(x)) >= 4 and x not in out[:i]] or [t]
def consider(f, d, nts, y, pool):
    ident = d.get('identifier')
    if not ident or ident in pool: return
    t = d.get('title') or ''
    if isinstance(t, list): t = ' '.join(str(x) for x in t)
    t = str(t); tl = t.lower()
    ds = d.get('description') or ''
    if isinstance(ds, list): ds = ' '.join(str(x) for x in ds)
    ds = re.sub(r'<[^>]+>', ' ', str(ds))[:500].lower()
    if re.search(BAD, tl) or re.search(T_PACK, tl): return
    lang = d.get('language') or ''
    if isinstance(lang, list): lang = ' '.join(str(x) for x in lang)
    lang = str(lang).lower()
    if re.search(FOREIGN, tl + ' ' + ident.lower().replace('-', ' ').replace('_', ' ')) or re.search(FOREIGN, ds) or (lang and not re.search(r'eng|english|^en\b', lang)):
        pool[ident] = None; CNT['foreign'] += 1; return
    if re.search(r'[^\x00-\x7f]', t) and len(re.findall(r'[^\x00-\x7f]', t)) > 2:
        pool[ident] = None; CNT['foreign'] += 1; return
    nd = norm(t); hit = None
    for nt in nts:
        if nd == nt or nd.startswith(nt + ' ') or (' ' + nt + ' ') in (' ' + nd + ' '): hit = nt; break
    if not hit: return
    ys = [int(x) for x in re.findall(r'\b(19\d\d|20\d\d)\b', t)]
    dy = str(d.get('year') or '')
    if ys and y and not any(abs(x - y) <= 1 for x in ys): return
    yok = bool(ys) or (dy.isdigit() and y and abs(int(dy) - y) <= 1)
    if dy.isdigit() and y and not ys and abs(int(dy) - y) > 1 and int(dy) < 2005: return
    rest = [w for w in nd.replace(hit, ' ', 1).split() if not re.match(r'^(19|20)\d\d$', w) and w not in OKW]
    if len(rest) > 2: return
    if hit != nts[0] and not yok: return
    if len(nts[0].split()) == 1 and not yok and rest: return
    blob = tl + ' ' + ident.lower().replace('-', ' ').replace('_', ' ').replace('.', ' ') + ' ' + ds[:300]
    tags = []
    if re.search(T_TAPE, blob): tags.append('tape')
    if re.search(T_TV, blob): tags.append('tv')
    if re.search(T_DVD, blob): tags.append('dvd')
    if re.search(T_HD, blob): tags.append('hd')
    if re.search(T_CAM, tl): tags.append('cam')
    sc = 10 + (8 if yok else 0) + (6 if nd == hit or not rest else 0) + min(12, 3 * len(str(int(d.get('downloads') or 0))))
    pool[ident] = [sc, tags, int(d.get('downloads') or 0)]
def final(sc, tags):
    if 'tape' in tags and 'hd' not in tags: sc += 50
    elif 'dvd' in tags and 'hd' not in tags: sc += 25
    if 'hd' in tags: sc -= 30
    if 'tv' in tags: sc -= 15
    if 'cam' in tags: sc -= 60
    if 'short' in tags: sc -= 10
    if 'parts' in tags: sc -= 5
    if 'sd' in tags: sc += 6
    return sc
def match(f):
    nts = [norm(v) for v in variants(f['t'])]
    if len(nts[0]) < 2: return f
    y = int(f['d'][:4]) if f['d'][:4].isdigit() else 0
    pool = {}
    tq = f['t'].replace('"', '')
    for d in search('title:("%s") AND mediatype:movies' % tq, 60): consider(f, d, nts, y, pool)
    live = lambda: [k for k, v in pool.items() if v]
    if len(live()) < 4 and y:
        for d in search('"%s" %d AND mediatype:movies' % (tq, y), 40): consider(f, d, nts, y, pool)
    if not any('tape' in pool[k][1] for k in live()):
        for d in search('"%s" AND (vhs OR laserdisc OR betamax) AND mediatype:movies' % tq, 30): consider(f, d, nts, y, pool)
    if not live():
        for d in search('"%s" AND ("full movie" OR "full film") AND mediatype:movies' % tq, 30): consider(f, d, nts, y, pool)
        for v in variants(f['t'])[1:]:
            for d in search('title:("%s") AND mediatype:movies' % v.replace('"', ''), 40): consider(f, d, nts, y, pool)
    order = sorted(live(), key=lambda k: -final(pool[k][0], pool[k][1]))
    rt = (f.get('rt') or 0) * 60
    out = []
    for ident in order[:9]:
        r = files_of(ident)
        if r == 'foreign': CNT['foreign'] += 1; continue
        if not r: continue
        fs, hmax, blob = r
        if not fs: continue
        sc, tags, dl = pool[ident]; tags = list(tags)
        if re.search(T_TAPE, blob) and 'tape' not in tags: tags.append('tape')
        if re.search(T_HD, blob) and 'hd' not in tags and 'tape' not in tags: tags.append('hd')
        if hmax >= 700 and 'hd' not in tags: tags.append('hd')
        if 0 < hmax <= 576 and 'hd' not in tags: tags.append('sd')
        big = sorted(fs, key=lambda x: -x[1])[0]
        tot = sum(x[1] for x in fs); pick = None
        if rt:
            if abs(big[1] - rt) <= 0.06 * rt: pick = [big]
            elif 0.78 * rt <= big[1] < 0.94 * rt and ('tv' in tags or 'tape' in tags): pick = [big]; tags.append('short')
            elif 2 <= len(fs) <= 6 and abs(tot - rt) <= 0.06 * rt and big[1] < 0.9 * rt: pick = fs; tags.append('parts')
        else:
            if 3600 <= big[1] <= 4 * 3600: pick = [big]
            elif 2 <= len(fs) <= 6 and 3600 <= tot <= 4 * 3600: pick = fs; tags.append('parts')
        if not pick: continue
        out.append([ident, pick, final(sc, tags), tags])
        if len(out) >= 6: break
    out.sort(key=lambda c: -c[2])
    if out:
        f['ias'] = out; f['ia'] = [out[0][0], out[0][1]]
    return f
res = []
with ThreadPoolExecutor(int(os.environ.get('THREADS', '12'))) as ex:
    for n, r in enumerate(ex.map(match, films)):
        res.append(r)
        if n % 250 == 0: print('match', n, sum(1 for x in res if x.get('ia')), flush=True)
with gzip.open(os.path.join(OUT, 'movies.json.gz'), 'wt', encoding='utf-8') as fo:
    json.dump(res, fo, ensure_ascii=False, separators=(',', ':'))
have = [x for x in res if x.get('ia')]
top = lambda x: x['ias'][0][3]
print('films total', len(res))
print('with any candidate', len(have))
print('tape/LD chosen', sum(1 for x in have if 'tape' in top(x) and 'hd' not in top(x)))
print('dvd chosen', sum(1 for x in have if 'dvd' in top(x) and 'tape' not in top(x) and 'hd' not in top(x)))
print('hd only', sum(1 for x in have if all('hd' in c[3] for c in x['ias'])))
print('hd chosen', sum(1 for x in have if 'hd' in top(x)))
print('plain sd chosen', sum(1 for x in have if not set(top(x)) & {'tape', 'dvd', 'hd'}))
print('foreign rejected', CNT['foreign'])
print('candidates per film', {k: sum(1 for x in have if len(x['ias']) == k) for k in range(1, 7)})
if HAD is not None:
    print('newly matched', sum(1 for x in have if x['q'] not in HAD), 'lost', sum(1 for x in res if x['q'] in HAD and not x.get('ia')))
import random
random.seed(7)
for x in random.sample(have, min(80, len(have))):
    c = x['ias'][0]
    print('SAMPLE', x['t'], x['d'][:4], int(x.get('rt') or 0), '->', c[0], round(sum(p[1] for p in c[1]) / 60), c[2], ','.join(c[3]), '| alts', len(x['ias']) - 1)
