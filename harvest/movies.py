import json, gzip, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'retrotv-sources/1.0 (https://conventionalmemory.io; movie shelf builder)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'all'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
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
        films.append({k: x[k] for k in ('q', 't', 'd', 'bo', 'sl', 'g', 'r', 'rt', 'ia', 'ias', 'tried', 'pia', 'keep', 'why') if k in x})
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
RANK = {'h.264 IA': 0, 'h.264': 1, 'h.264 HD': 2, 'MPEG4': 3, '512Kb MPEG4': 4}
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
        if not d:
            try: big = int(b.get('size') or 0)
            except Exception: big = 0
            if big >= 250000000: out.append([b['name'], 0])
            continue
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
ROM = {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8'}
ARA = {v: k for k, v in ROM.items()}
def swaps(t):
    out = []
    w = t.split()
    a = [ROM.get(x.lower().strip(':,'), x) if x.lower().strip(':,') in ROM and i else x for i, x in enumerate(w)]
    b = [ARA.get(x.strip(':,'), x).upper() if x.strip(':,') in ARA and i else x for i, x in enumerate(w)]
    for c in (a, b):
        if c != w:
            out.append(' '.join(c))
            out.append(' '.join(x for x in c if x.lower() != 'part'))
    if '&' in t: out.append(t.replace('&', 'and'))
    if re.search(r'\band\b', t): out.append(re.sub(r'\band\b', '&', t))
    if '½' in t: out.append(t.replace('½', ' 1/2')); out.append(t.replace('½', ' and a half'))
    if re.search(r'\bvs\.?(\s|$)', t): out.append(re.sub(r'\bvs\.?(\s|$)', r'versus\1', t))
    if '*' in t: out.append(t.replace('*', ''))
    return out
def variants(t):
    prim = [t] + swaps(t)
    sec = []
    parts = [x.strip() for x in re.split(r'\s*:\s+|\s+[–—-]\s+', t) if x.strip()]
    if len(parts) > 1:
        sec.append(parts[0])
        if len(norm(parts[-1]).split()) >= 3: sec.append(parts[-1])
        if len(parts) > 2: sec.append(parts[0] + ' ' + parts[-1]); sec.append(parts[0] + ' ' + parts[1])
        prim.append(' '.join(parts))
    if t.lower().startswith('the '): sec.append(t[4:])
    if t.lower().startswith('a '): sec.append(t[2:])
    out, seen = [], set()
    for k, lst in ((1, prim), (0, sec)):
        for x in lst:
            n = norm(x)
            if n in seen or (not k and len(n) < 4) or not n: continue
            seen.add(n); out.append((x, n, k))
    return out
SEQ = set('2 3 4 5 6 7 8 ii iii iv v vi vii viii part chapter returns'.split())
def consider(f, d, vs, y, pool, dg):
    ident = d.get('identifier')
    if not ident or ident in pool: return
    dg['docs'] = dg.get('docs', 0) + 1
    def no(k):
        dg[k] = dg.get(k, 0) + 1
        if len(dg.setdefault('ex_' + k, [])) < 3: dg['ex_' + k].append(ident)
    t = d.get('title') or ''
    if isinstance(t, list): t = ' '.join(str(x) for x in t)
    t = str(t); tl = t.lower()
    ds = d.get('description') or ''
    if isinstance(ds, list): ds = ' '.join(str(x) for x in ds)
    ds = re.sub(r'<[^>]+>', ' ', str(ds))[:500].lower()
    lang = d.get('language') or ''
    if isinstance(lang, list): lang = ' '.join(str(x) for x in lang)
    lang = str(lang).lower()
    idsp = re.sub(r'[_-](19|20)\d{4,6}$', '', ident)
    idsp = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=(19|20)\d\d)|(?<=\d\d\d\d)(?=[A-Za-z])', ' ', idsp)
    idn = norm(idsp.replace('-', ' ').replace('_', ' ').replace('.', ' '))
    if re.search(FOREIGN, tl + ' ' + idn) or re.search(FOREIGN, ds) or (lang and not re.search(r'eng|english|^en\b', lang)):
        pool[ident] = None; CNT['foreign'] += 1; return no('foreign')
    if re.search(r'[^\x00-\x7f]', t) and len(re.findall(r'[^\x00-\x7f]', t)) > 2:
        pool[ident] = None; CNT['foreign'] += 1; return no('foreign')
    nd = norm(t); hit = None; src = nd; prim = 0; byid = False
    for x, nt, k in vs:
        if nd == nt or nd.startswith(nt + ' ') or (' ' + nt + ' ') in (' ' + nd + ' '): hit = nt; prim = k; break
    if not hit:
        for x, nt, k in vs:
            if idn == nt or idn.startswith(nt + ' ') or (' ' + nt + ' ') in (' ' + idn + ' ') or (len(nt) >= 6 and idn.replace(' ', '').startswith(nt.replace(' ', ''))): hit = nt; prim = k; src = idn; byid = True; break
    if not hit: return no('nohit')
    if byid and hit not in src: src = hit + ' ' + src.replace(' ', '')[len(hit.replace(' ', '')):]
    left = src.replace(hit, ' ', 1)
    if re.search(BAD, left) or re.search(T_PACK, left): return no('bad')
    ys = [int(x) for x in re.findall(r'\b(19\d\d|20\d\d)\b', t if not byid else idsp + ' ' + t)]
    ys = [x for x in ys if 1900 <= x <= 2026]
    dy = str(d.get('year') or '')
    if ys and y and not any(abs(x - y) <= 1 for x in ys): return no('year')
    yok = bool(ys) or (dy.isdigit() and y and abs(int(dy) - y) <= 1)
    if not yok and y and any(abs(int(x) - y) <= 1 for x in re.findall(r'(?<!\d)(19\d\d|20\d\d)(?!\d)', idsp)): yok = True
    if dy.isdigit() and y and not ys and abs(int(dy) - y) > 1 and int(dy) < 2005: return no('year')
    rest = [w for w in left.split() if not re.match(r'^(19|20)\d\d$', w) and w not in OKW]
    after = src.split(hit, 1)[1].split() if hit in src else []
    if after and after[0] in SEQ and not hit.endswith(' ' + after[0]): return no('sequel')
    if len(rest) > (10 if yok and src.startswith(hit) else 2): return no('rest')
    if byid and not yok: return no('idnoyear')
    if not prim and not yok: return no('varnoyear')
    if len(hit.split()) == 1 and not yok and rest: return no('oneword')
    blob = tl + ' ' + idn + ' ' + ds[:300]
    tags = []
    if re.search(T_TAPE, blob): tags.append('tape')
    if re.search(T_TV, blob): tags.append('tv')
    if re.search(T_DVD, blob): tags.append('dvd')
    if re.search(T_HD, blob): tags.append('hd')
    if re.search(T_CAM, tl): tags.append('cam')
    sc = 10 + (8 if yok else 0) + (6 if src == hit or not rest else 0) + min(12, 3 * len(str(int(d.get('downloads') or 0)))) - (4 if byid else 0) - (3 if len(rest) > 2 else 0)
    pool[ident] = [sc, tags, int(d.get('downloads') or 0), yok]
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
TOL = float(os.environ.get('TOL', '0.09')); PASS = int(os.environ.get('PASS', '4')); CAP = int(os.environ.get('CAP', '14'))
T0 = time.time(); BUDGET = float(os.environ.get('BUDGET', '270')) * 60; REDO = os.environ.get('REDO') == '1'
DIAG = int(os.environ.get('DIAG', '45'))
def slugs(n, y):
    w = n.split()
    forms = set()
    for sep in ('-', '.', '_', ''):
        a = sep.join(w); b = sep.join(x.capitalize() for x in w)
        for c in (a, b):
            if len(n.replace(' ', '')) >= 6: forms.add(c + '*')
            if y:
                for s2 in ('-', '.', '_', ''): forms.add(c + s2 + str(y) + '*')
                forms.add(str(y) + '-' + c + '*'); forms.add(str(y) + '.' + c + '*'); forms.add(str(y) + '_' + c + '*')
    return sorted(forms)
def match(f):
    if time.time() - T0 > BUDGET or (((f.get('tried') or 0) >= PASS or f.get('ia')) and not REDO): return f
    f['tried'] = PASS
    vs = variants(f['t'])
    if not vs or len(vs[0][1]) < 2: return f
    y = int(f['d'][:4]) if f['d'][:4].isdigit() else 0
    pool = {}; dg = {}
    mm = ' AND mediatype:movies'
    def run(q, rows=50):
        dd = search(q, rows)
        dg['q'] = dg.get('q', 0) + 1
        for d in dd: consider(f, d, vs, y, pool, dg)
    live = lambda: [k for k, v in pool.items() if v]
    tq = f['t'].replace('"', '')
    for x, n, k in vs[:6]: run('title:("%s")' % x.replace('"', '') + mm, 60)
    if f.get('pia'): run('identifier:"%s"' % f['pia'], 1)
    if y:
        run('"%s" %d' % (tq, y) + mm, 50)
        run('title:("%s") AND year:%d' % (tq, y) + mm, 50)
        run('title:(%s) AND title:(%d)' % (re.sub(r'[^A-Za-z0-9 ]+', ' ', tq), y) + mm, 50)
    for x, n, k in [v for v in vs if v[2]][:2]:
        sl = slugs(n, y)
        for a in range(0, len(sl), 20): run('identifier:(%s)' % ' OR '.join(sl[a:a + 20]) + mm, 60)
    run('subject:("%s")' % tq + mm, 40)
    if not any('tape' in pool[k][1] for k in live()): run('"%s" AND (vhs OR laserdisc OR betamax OR vhsrip)' % tq + mm, 40)
    if len(live()) < 3: run('"%s" AND ("full movie" OR "full film")' % tq + mm, 30)
    order = sorted(live(), key=lambda k: -final(pool[k][0], pool[k][1]))
    rt = (f.get('rt') or 0) * 60
    out = []
    for ident in order[:CAP + 10]:
        r = files_of(ident)
        if r == 'foreign': CNT['foreign'] += 1; dg['m_foreign'] = dg.get('m_foreign', 0) + 1; continue
        if not r: dg['m_gone'] = dg.get('m_gone', 0) + 1; continue
        fs, hmax, blob = r
        if not fs: dg['m_nomp4'] = dg.get('m_nomp4', 0) + 1; continue
        sc, tags, dl, yok = pool[ident]; tags = list(tags)
        if re.search(T_TAPE, blob) and 'tape' not in tags: tags.append('tape')
        if re.search(T_HD, blob) and 'hd' not in tags and 'tape' not in tags: tags.append('hd')
        if hmax >= 700 and 'hd' not in tags: tags.append('hd')
        if 0 < hmax <= 576 and 'hd' not in tags: tags.append('sd')
        big = sorted(fs, key=lambda x: -x[1])[0]
        tot = sum(x[1] for x in fs); pick = None; why = ''
        if not big[1]:
            if yok and len(fs) == 1: pick = [big]; tags.append('maybe'); why = 'runtime unknown'
        elif rt:
            if abs(big[1] - rt) <= TOL * rt: pick = [big]
            elif 0.78 * rt <= big[1] < 0.94 * rt and ('tv' in tags or 'tape' in tags): pick = [big]; tags.append('short')
            elif 2 <= len(fs) <= 6 and abs(tot - rt) <= TOL * rt and big[1] < 0.9 * rt: pick = [x for x in fs if x[1]]; tags.append('parts')
        else:
            if 3600 <= big[1] <= 4 * 3600: pick = [big]
            elif 2 <= len(fs) <= 6 and 3600 <= tot <= 4 * 3600: pick = [x for x in fs if x[1]]; tags.append('parts')
        if not pick and rt and 2400 <= big[1] and abs(big[1] - rt) <= 0.25 * rt: pick = [big]; tags.append('maybe'); why = 'runtime %d min vs listed %d' % (round(big[1] / 60), round(rt / 60))
        if not pick:
            dg['m_runtime'] = dg.get('m_runtime', 0) + 1
            if len(dg.setdefault('ex_runtime', [])) < 3: dg['ex_runtime'].append('%s %d/%d' % (ident, round(big[1] / 60), round(rt / 60)))
            continue
        c = [ident, pick, final(sc, tags) - (25 if why else 0), tags]
        if why: c.append(why)
        out.append(c)
        if len(out) >= CAP: break
    got = {c[0] for c in out}
    for c in f.get('ias') or []:
        if c[0] not in got: out.append(c)
    out.sort(key=lambda c: -c[2])
    out = out[:CAP]
    if not out or not any('maybe' not in c[3] for c in out):
        if (f.get('sl') or 0) >= DIAG: print('DIAG', f['t'], f['d'][:4], int(f.get('rt') or 0), 'cands', len(order), json.dumps(dg, ensure_ascii=False)[:900], flush=True)
    if not out: return f
    f.pop('ias', None); f.pop('ia', None)
    f.pop('keep', None); f.pop('why', None)
    f['ias'] = out
    sure = [c for c in out if 'maybe' not in c[3]]
    if sure: f['ia'] = [sure[0][0], sure[0][1]]
    else: f['keep'] = 'maybe'; f['why'] = out[0][4] if len(out[0]) > 4 else 'doubtful match'
    return f
if MODE == 'merge':
    by = {}
    for fn in sorted(os.listdir(PARTS)):
        if fn.startswith('movies-') and fn.endswith('.json.gz'):
            for x in json.load(gzip.open(os.path.join(PARTS, fn), 'rt', encoding='utf-8')): by[x['q']] = x
    print('part films', len(by), flush=True)
    work = []
    films = [by.get(x['q'], x) for x in films]
elif MODE == 'shard':
    work = sorted([x for x in films if not x.get('ia') or REDO], key=lambda x: (-(x.get('sl') or 0), -(x.get('bo') or 0), x['q']))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'films', len(work), flush=True)
else:
    work = films
done = []
with ThreadPoolExecutor(int(os.environ.get('THREADS', '12'))) as ex:
    for n, r in enumerate(ex.map(match, work)):
        done.append(r)
        if n % 100 == 0: print('match', n, sum(1 for x in done if x.get('ia')), flush=True)
if MODE == 'shard':
    with gzip.open(os.path.join(PARTS, 'movies-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as fo:
        json.dump([x for x in done if x.get('tried') == PASS], fo, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(done), 'with copy', sum(1 for x in done if x.get('ia')), 'maybe only', sum(1 for x in done if x.get('ias') and not x.get('ia')), 'foreign rejected', CNT['foreign'])
    raise SystemExit(0)
res = films
with gzip.open(os.path.join(OUT, 'movies.json.gz'), 'wt', encoding='utf-8') as fo:
    json.dump(res, fo, ensure_ascii=False, separators=(',', ':'))
print('tried', sum(1 for x in res if x.get('tried')), 'untried', sum(1 for x in res if not x.get('tried')))
have = [x for x in res if x.get('ias')]
top = lambda x: x['ias'][0][3]
print('films total', len(res))
print('tried this pass', sum(1 for x in res if x.get('tried') == PASS))
print('with any candidate', len(have), 'sure', sum(1 for x in have if x.get('ia')), 'maybe only', sum(1 for x in have if not x.get('ia')))
print('tape/LD chosen', sum(1 for x in have if 'tape' in top(x) and 'hd' not in top(x)))
print('dvd chosen', sum(1 for x in have if 'dvd' in top(x) and 'tape' not in top(x) and 'hd' not in top(x)))
print('hd only', sum(1 for x in have if all('hd' in c[3] for c in x['ias'])))
print('hd chosen', sum(1 for x in have if 'hd' in top(x)))
print('plain sd chosen', sum(1 for x in have if not set(top(x)) & {'tape', 'dvd', 'hd'}))
print('foreign rejected', CNT['foreign'])
print('candidates per film', {k: sum(1 for x in have if len(x['ias']) == k) for k in range(1, 15)})
if HAD is not None:
    print('newly matched', sum(1 for x in have if x['q'] not in HAD), 'lost', sum(1 for x in res if x['q'] in HAD and not x.get('ia')))
import random
random.seed(7)
new = [x for x in have if HAD is not None and x['q'] not in HAD and x.get('ia')]
for x in sorted(new, key=lambda x: -(x.get('sl') or 0))[:150]:
    c = x['ias'][0]
    print('NEW', x.get('sl'), x['t'], x['d'][:4], int(x.get('rt') or 0), '->', c[0], round(sum(p[1] for p in c[1]) / 60), c[2], ','.join(c[3]), '| alts', len(x['ias']) - 1)
miss = sorted([x for x in res if not x.get('ia')], key=lambda x: -(x.get('sl') or 0))
print('MISSING top', ' / '.join('%s (%s)' % (x['t'], x['d'][:4]) for x in miss[:120]))
for x in random.sample(have, min(60, len(have))):
    c = x['ias'][0]
    print('SAMPLE', x['t'], x['d'][:4], int(x.get('rt') or 0), '->', c[0], round(sum(p[1] for p in c[1]) / 60), c[2], ','.join(c[3]), '| alts', len(x['ias']) - 1)
