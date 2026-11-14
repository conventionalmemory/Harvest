import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '12'))
QTHREADS = int(os.environ.get('QTHREADS', '6'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
OFFLINE = os.environ.get('OFFLINE') == '1'
FORCE = os.environ.get('FORCE') == '1'
T0 = time.time()
OUTF = os.path.join(OUT, 'eptitle.json.gz')
GF = os.path.join(OUT, 'eptitle_guide.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_eptitle.json'), encoding='utf-8'))
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'").replace('é', 'e')
    s = re.sub(r"[^a-z0-9]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
for k, s in enumerate(SHOWS):
    s['k'] = k
    s['names'] = sorted(set(norm(a) for a in [s['title']] + s.get('alt', [])), key=lambda a: -len(a))
def get(url, tries=4, raw=False):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read().decode('utf-8', 'replace')
                return b if raw else json.loads(b)
        except Exception as e:
            code = getattr(e, 'code', 0)
            if code == 404: return None
            if k == tries - 1:
                print('fail', url[:140], e, flush=True); return None
            time.sleep((8 if code == 429 else 3) * (k + 1))
def loadj(p):
    return json.load(gzip.open(p, 'rt', encoding='utf-8')) if os.path.exists(p) else None
STATE = loadj(GF) or {'guides': {}, 'done': []}
BASE = loadj(os.path.join(OUT, 'epguide.json.gz')) or {}
def tvmaze(s):
    name = s.get('guide') or s['title']
    j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(name)) or []
    time.sleep(0.6)
    best = None
    for r in j:
        sh = r.get('show') or {}
        py = int(str(sh.get('premiered') or '0')[:4] or 0)
        sc = (0 if abs(py - s['py']) <= 1 else 5) + (0 if norm(sh.get('name')) in s['names'] + [norm(name)] else 2)
        if best is None or sc < best[0]: best = (sc, sh)
    if not best or best[0] >= 5: return None
    eps = get('https://api.tvmaze.com/shows/%d/episodes' % best[1]['id']) or []
    time.sleep(0.6)
    return {'title': best[1].get('name'), 'id': best[1]['id'], 'premiered': best[1].get('premiered'), 'episodes': [[e.get('season') or 0, e.get('number') or 0, e.get('airdate') or '', e.get('name') or ''] for e in eps]}
def guide(s):
    g = STATE['guides'].get(s['title'])
    if g: return g
    for key in [norm(s.get('guide') or s['title'])] + s['names'] + [re.sub(r'^the ', '', n) for n in s['names']]:
        b = BASE.get(key)
        if b and b.get('episodes') and abs(int(str(b.get('premiered') or '0')[:4] or 0) - s['py']) <= 1:
            g = {'title': b.get('title'), 'id': b.get('id'), 'premiered': b.get('premiered'), 'episodes': b['episodes']}; break
    if not g and not OFFLINE: g = tvmaze(s)
    if g: STATE['guides'][s['title']] = g
    return g
GEN = {'pilot', 'part 1', 'part 2', 'part one', 'part two', 'episode', 'finale', 'series finale', 'season finale', 'christmas', 'halloween', 'thanksgiving', 'tba', 'the pilot', 'premiere'}
STOP = {'the', 'a', 'an', 'of', 'and', 'in', 'to', 'with', 'one', 'where', 'that', 'on', 'for', 'at', 'is', 'it', 'my', 'your', 'part', 'i', 'ii', '1', '2', 'vs', 'by', 'from', 'or', 'be'}
def eplist(s):
    g = guide(s)
    if not g: return []
    out = []
    for e in g['episodes']:
        se, ep, ad, name = int(e[0] or 0), int(e[1] or 0), str(e[2] or ''), str(e[3] or '')
        if se <= 0 or ep <= 0 or not name: continue
        if s.get('maxs') and se > s['maxs']: continue
        if ad and ad > '2004-12-31': continue
        segs = [x for x in re.split(r'\s+/\s+|\s*;\s+', name) if x.strip()] if s['len'] == 's' else [name]
        for sg in segs:
            sg = re.sub(r'\s*\((\d|part|pt)[^)]*\)\s*$', '', sg, flags=re.I).strip()
            n = norm(sg)
            if not n or n in GEN or re.fullmatch(r'(episode|part|chapter|show) ?\d+', n) or len(n) < 4: continue
            sig = [w for w in n.split() if w not in STOP]
            out.append({'se': [se, ep], 'ep': sg, 'n': n, 'ad': '' if s.get('noad') else ad, 'dist': len(sig) >= 3 or (len(sig) >= 2 and len(n) >= 16)})
    return out
SE1 = re.compile(r'(?<![a-z0-9])s(?:eason)? ?0?(\d{1,2}) ?(?:e|ep|episode) ?0?(\d{1,3})(?!\d)')
SE2 = re.compile(r'(?<![a-z0-9])(\d{1,2})x(\d{2})(?!\d)')
def ses(txt):
    return set((int(a), int(b)) for a, b in SE1.findall(txt)) | set((int(a), int(b)) for a, b in SE2.findall(txt))
def hasname(s, blob):
    b = ' ' + blob + ' '
    return any((' ' + n + ' ') in b for n in s['names'])
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblada|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|fran[cç]ais|french dub|vf|vostfr|italiano|nederlands|svenska|norsk|dansk|suomi|polski|lektor|magyar|t[uü]rk[cç]e|russian|hindi|tamil|arabic|subtitulado|sub ?esp|audio latino)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|rom ?hack|emulator|pinball|comic book|audiobook|audio book|ebook|podcast|review|reviews|reaction|reacts|commentary|recap|explained|ranking|ranked|top \d+|tier list|analysis|essay|theory|theories|trailer|teaser|promo|promos|bumper|bumpers|clip|clips|scene|scenes|fan ?made|fan ?film|fanfic|amv|parody|remix|ytp|soundtrack|ost|theme song|intro|opening|credits|script|transcript|behind the scenes|bloopers|interview|panel|convention|unboxing|toy|toys|figure|figures|lego|minecraft|roblox)\b"
X_EDIT = r"\b(fan ?edit|re ?edited|recut|closing to|opening to|opening and closing|vhs opening|promo|trailer|bloopers|outtakes|behind the scenes|interview with|sub|subs|subbed|subtitulado|rus|4k upscale|remaster test|cam rip|master cut|pokeshipping|fan cut|abridged)\b"
RES_OK = {'season', 'episode', 'ep', 'series', 'part', 'pt', 'tv', 'show', 'complete', 'full', 'hd', 'sd', 'dvd', 'dvdrip', 'vhs', 'vhsrip', 'rip', 'x264', 'x265', 'h264', 'hevc', 'aac', 'mp4', 'mkv', 'avi', '480p', '576p', '720p', '1080p', 'web', 'dl', 'bluray', 'blu', 'ray', 'webrip', 'the', 'a', 'of', 'and', 'with', 'commercials', 'original', 'broadcast', 'aired', 'nbc', 'abc', 'cbs', 'fox', 'wb', 'upn', 'english', 'eng', 'uncut', 'remastered', 'disc', 'disk', 'vol', 'volume', 's', 'e', 'x'}
def residual(nt, names, en):
    t = ' ' + nt + ' '
    for n in sorted(names, key=lambda a: -len(a)): t = t.replace(' ' + n + ' ', ' ')
    t = t.replace(' ' + en + ' ', ' ')
    return [w for w in t.split() if w not in RES_OK and not re.fullmatch(r'\d{1,4}|s\d{1,2}e\d{1,3}|s\d{1,2}|e\d{1,3}|\d{1,2}x\d{2}|(19|20)\d\d', w)]
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(reboot|revival|netflix|hulu|disney\+|youtube|tiktok|twitch|livestream)\b"
def ok_title(t):
    if not t: return False
    low = t.lower() + ' '
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low) or re.search(X_EDIT, low): return False
    return True
def scrape(q, cap=600):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,downloads,language,collection', 'q': q, 'count': 300, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) >= cap: break
    return out
def qs(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', t).split())
def catfiles():
    skip = {'eptitle.json.gz', 'eptitle_guide.json.gz', 'epguide.json.gz', 'dates.json.gz', 'adsdates.json.gz', 'ads.json.gz', 'filler.json.gz', 'nick_guide.json.gz'}
    return [p for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))) if os.path.basename(p) not in skip]
def coverage(EP):
    have = set(); cov = collections.defaultdict(set)
    allnames = sorted(set(n for s in SHOWS for n in s['names']), key=lambda a: -len(a))
    rx = re.compile(r'(?<![a-z0-9])(' + '|'.join(re.escape(n) for n in allnames) + r')(?![a-z0-9])')
    byname = collections.defaultdict(list)
    for s in SHOWS:
        for n in s['names']: byname[n].append(s)
    for p in catfiles():
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception as e:
            print('skip', os.path.basename(p), e); continue
        if isinstance(L, dict): L = list(L.values())
        n = 0
        for x in L:
            if not isinstance(x, dict) or 'i' not in x: continue
            have.add(x['i'])
            t = norm(str(x.get('t') or '') + ' ' + str(x.get('k') or '') + ' ' + str(x.get('i') or ''))
            m = rx.search(t)
            if not m: continue
            fl = x.get('f') or []
            if isinstance(fl, list) and fl and isinstance(fl[0], str): fl = [fl]
            names = [norm(str(f[0])) for f in fl if isinstance(f, (list, tuple)) and f]
            texts = [t] + names
            t0 = re.sub(r'^(the|a) ', '', norm(str(x.get('t') or '')))
            for s in byname[m.group(1)]:
                eps = EP.get(s['k']) or []
                if not eps: continue
                if s.get('amb') and str(x.get('k') or '') != s['title'] and not any(t0.startswith(re.sub(r'^(the|a) ', '', n) + ' ') or t0 == n for n in s['names']): continue
                idx = {tuple(e['se']) for e in eps}
                for tx in texts:
                    for se in ses(tx):
                        if se in idx: cov[s['k']].add(se)
                blob = ' ' + ' | '.join(texts) + ' '
                for e in eps:
                    if tuple(e['se']) in cov[s['k']]: continue
                    if len(e['n']) >= 8 and (' ' + e['n'] + ' ') in blob: cov[s['k']].add(tuple(e['se']))
                n += 1
        print('scanned', os.path.basename(p), len(L), 'show items', n, flush=True)
    return have, cov
def table(EP, cov, new=None):
    print('COVERAGE TABLE  show | episodes | covered elsewhere | new here | still missing | flag')
    for s in SHOWS:
        eps = set(tuple(e['se']) for e in EP.get(s['k']) or [])
        c = set(cov.get(s['k']) or ()) & eps
        nw = (set(new.get(s['k']) or ()) & eps) - c if new else set()
        miss = len(eps) - len(c) - len(nw)
        flag = 'NOGUIDE' if not eps else 'FOUND' if miss <= len(eps) * 0.1 else 'THIN' if (len(c) + len(nw)) >= len(eps) * 0.4 else 'MISSING'
        print('  %-40s %4d %4d %4d %4d  %s' % (s['title'][:40], len(eps), len(c), len(nw), miss, flag))
if MODE == 'plan':
    EP = {}
    for s in SHOWS:
        EP[s['k']] = eplist(s)
        print('guide', s['title'], len(EP[s['k']]), 'titles', flush=True)
    with gzip.open(GF, 'wt', encoding='utf-8') as f: json.dump(STATE, f, ensure_ascii=False, separators=(',', ':'))
    have, cov = coverage(EP)
    table(EP, cov)
    done = set(STATE.get('done') or []) if not FORCE else set()
    todo = []
    for s in SHOWS:
        seen = set()
        for e in EP[s['k']]:
            key = '%d|%d|%d|%s' % (s['k'], e['se'][0], e['se'][1], e['n'])
            if tuple(e['se']) in cov[s['k']] or key in done or key in seen: continue
            seen.add(key); todo.append((s, e, key))
    print('episodes to search', len(todo), 'already searched', len(done), flush=True)
    if OFFLINE:
        print('offline: stop before search'); sys.exit(0)
    def find(a):
        s, e, key = a
        if time.time() - T0 > BUDGET: return a, None
        ctx = ' OR '.join('"' + qs(n) + '"' for n in [s['title']] + s.get('alt', []))
        if e['dist'] and not s.get('amb'):
            q = 'mediatype:movies AND title:("%s")' % qs(e['ep'])
        else:
            q = 'mediatype:movies AND title:("%s") AND (title:(%s) OR subject:(%s) OR description:(%s) OR collection:(%s))' % (qs(e['ep']), ctx, ctx, ctx, ctx)
        r = scrape(q)
        if e['dist'] and not s.get('amb') and len(r) >= 600:
            r = scrape('mediatype:movies AND title:("%s") AND (title:(%s) OR subject:(%s) OR description:(%s))' % (qs(e['ep']), ctx, ctx, ctx))
        return a, r
    cands = {}; nq = 0; hits = collections.Counter(); newdone = []
    with ThreadPoolExecutor(QTHREADS) as ex:
        for (s, e, key), items in ex.map(find, todo):
            if items is None: continue
            nq += 1; newdone.append(key)
            for it in items:
                i = it['identifier']
                if i in have: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                if not ok_title(t): continue
                nt = ' ' + norm(t) + ' '
                if (' ' + e['n'] + ' ') not in nt: continue
                c = cands.setdefault(i, {'identifier': i, 'downloads': it.get('downloads') or 0, 'm': []})
                if len(c['m']) < 12: c['m'].append([s['k'], e['se'][0], e['se'][1], e['ep'], e['ad']])
                hits[s['k']] += 1
            if nq % 500 == 0: print('searched', nq, 'of', len(todo), 'candidates', len(cands), round((time.time() - T0) / 60, 1), 'min', flush=True)
    print('searched', nq, 'of', len(todo), 'candidates', len(cands))
    npk = 0
    def pack(s):
        if time.time() - T0 > BUDGET or ('P|%d' % s['k']) in done: return s, None
        ctx = ' OR '.join('"' + qs(n) + '"' for n in [s['title']] + s.get('alt', []))
        return s, scrape('mediatype:movies AND (title:(%s) OR subject:(%s))' % (ctx, ctx), cap=3000)
    with ThreadPoolExecutor(3) as ex:
        for s, items in ex.map(pack, SHOWS):
            if items is None: continue
            newdone.append('P|%d' % s['k']); n0 = npk
            for it in items:
                i = it['identifier']
                if i in have: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                if not ok_title(t): continue
                c = cands.setdefault(i, {'identifier': i, 'downloads': it.get('downloads') or 0, 'm': []})
                c.setdefault('pk', [])
                if s['k'] not in c['pk']: c['pk'].append(s['k']); npk += 1
            print('pack route', s['title'], 'items', len(items), 'new candidates', npk - n0, flush=True)
    print('pack candidates', npk, 'total candidates', len(cands))
    print('candidate hits per show', [(SHOWS[k]['title'], n) for k, n in hits.most_common()])
    cl = sorted(cands.values(), key=lambda x: x['identifier'])
    with gzip.open(os.path.join(PARTS, 'eptitle_cands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump({'cands': cl, 'done': newdone, 'cov': {str(k): sorted(list(v)) for k, v in cov.items()}}, f, separators=(',', ':'))
    sys.exit(0)
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
LEN = {'h': (17 * 60, 33 * 60), 'd': (36 * 60, 66 * 60), 's': (8 * 60, 33 * 60), 'm': (60 * 60, 125 * 60)}
def fits(s, d):
    lo, hi = LEN[s['len']]
    return lo <= d <= hi or (s['len'] in ('h', 'd') and 2 * lo <= d <= 2 * hi)
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    if str(m.get('mediatype', 'movies')) != 'movies': return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en\b', str(lang)): return None
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 60: continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (d / 60) > 30: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files: return None
    files.sort(key=lambda f: f[0])
    title = m.get('title', ''); title = ' '.join(title) if isinstance(title, list) else str(title)
    if not ok_title(title): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:600]).lower()
    if re.search(X_FOR, blob): return None
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast)|old time radio|audio only|audio commentary)\b', blob): return None
    nt = norm(title); nsub = norm(str(subj) + ' ' + ' '.join(col) + ' ' + it['identifier']); ndesc = norm(desc[:1200])
    tse = ses(nt)
    if it.get('pk'):
        r = packmeta(it, files, title, nt, nsub, ndesc, m, col, subj, desc)
        if r or not it.get('m'): return r
    best = None
    for k, se, ep, name, ad in it['m']:
        s = SHOWS[k]; en = norm(name)
        if (' ' + en + ' ') not in (' ' + nt + ' '): continue
        strong = hasname(s, nt) or hasname(s, nsub)
        weak = hasname(s, ndesc) or (se, ep) in tse
        res = residual(nt, s['names'], en); hit = (se, ep) in tse
        dist = len([w for w in en.split() if w not in STOP]) >= 3 or (len([w for w in en.split() if w not in STOP]) >= 2 and len(en) >= 16)
        if s.get('amb'):
            if not strong and not (hit and hasname(s, ndesc)): continue
        elif s.get('intitle'):
            if not hasname(s, nt): continue
        elif not strong and not weak: continue
        if not hit:
            if len(res) > (3 if dist else 1): continue
            if not dist and not strong and not (weak and not res and len(en.split()) >= 2): continue
            if not dist and len(res) > 0 and not hasname(s, nt): continue
        byname = [f for f in files if (' ' + en + ' ') in (' ' + norm(f[0]) + ' ') and fits(s, f[1])]
        fit = [f for f in files if fits(s, f[1])]
        pick = byname[:1] if byname else fit[:1] if len(fit) == 1 else None
        if not pick: continue
        sc = (2 if strong else 0) + (1 if (se, ep) in tse else 0) + len(en) / 100.0
        if best is None or sc > best[0]: best = (sc, s, se, ep, name, ad, pick)
    if not best: return None
    sc, s, se, ep, name, ad, pick = best
    return {'i': it['identifier'], 'q': s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:300], 'f': pick, 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': int(ad[:4]) if ad[:4].isdigit() and 1984 <= int(ad[:4]) <= 2004 else '', 'net': s['net'], 'ct': 'eptitle', 'se': [se, ep], 'ep': name, 'ad': ad}
def packmeta(it, files, title, nt, nsub, ndesc, m, col, subj, desc):
    out = []
    for k in it.get('pk') or []:
        s = SHOWS[k]
        if not (hasname(s, nt) or hasname(s, nsub)): continue
        if s.get('amb') and not any(re.sub(r'^(the|a) ', '', nt).startswith(re.sub(r'^(the|a) ', '', n) + ' ') or nt == n for n in s['names']): continue
        eps = EPX.get(k)
        if eps is None:
            eps = EPX[k] = eplist(s)
        if not eps: continue
        idx = {}
        for e in eps: idx.setdefault(tuple(e['se']), e)
        covd = COV.get(k, set()); fe = {}; used = set()
        for f in files:
            if not fits(s, f[1]): continue
            nf = norm(re.sub(r'\.(ia\.)?mp4$', '', f[0].split('/')[-1]))
            cand = [x for x in ses(nf) if x in idx]
            e = idx[cand[0]] if len(cand) == 1 else None
            if not e:
                best = None
                for x in eps:
                    if len(x['n']) >= 6 and (' ' + x['n'] + ' ') in (' ' + nf + ' ') and (best is None or len(x['n']) > len(best['n'])): best = x
                e = best
            if not e or tuple(e['se']) in covd or tuple(e['se']) in used: continue
            used.add(tuple(e['se'])); fe[f[0]] = [e['se'][0], e['se'][1], e['ad'], e['ep']]
        if not fe: continue
        keep = [f for f in files if f[0] in fe][:60]
        fe = {f[0]: fe[f[0]] for f in keep}
        ys = sorted(int(v[2][:4]) for v in fe.values() if v[2][:4].isdigit())
        out.append({'i': it['identifier'], 'q': s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:300], 'f': keep, 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': ys[0] if ys and 1984 <= ys[0] <= 2004 else '', 'net': s.get('net', ''), 'ct': 'pack', 'fe': fe, 'pk': 1})
    return max(out, key=lambda x: len(x['fe'])) if out else None
EPX = {}; COV = {}
if MODE == 'meta':
    P = json.load(gzip.open(os.path.join(PARTS, 'eptitle_cands.json.gz'), 'rt', encoding='utf-8'))
    COV = {int(k): set(tuple(v) for v in L) for k, L in (P.get('cov') or {}).items()}
    cands = P['cands'][SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'eptitle-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
BYT = {s['title']: s for s in SHOWS}
def still_ok(x):
    if x.get('pk'): return True
    s = BYT[x['k']]; nt = norm(x['t']); en = norm(x['ep']); hit = tuple(x['se']) in ses(nt)
    strong = hasname(s, nt) or hasname(s, norm(str(x.get('s') or '') + ' ' + ' '.join(x.get('c') or []) + ' ' + x['i']))
    sig = [w for w in en.split() if w not in STOP]; dist = len(sig) >= 3 or (len(sig) >= 2 and len(en) >= 16)
    weak = hasname(s, norm(str(x.get('ds') or '')))
    if s.get('amb') and not strong and not hit: return False
    if s.get('intitle') and not hasname(s, nt): return False
    if hit: return True
    res = residual(nt, s['names'], en)
    if len(res) > (3 if dist else 1): return False
    if not dist and not strong and not (weak and not res and len(en.split()) >= 2): return False
    if not dist and res and not hasname(s, nt): return False
    return True
old = [x for x in (loadj(OUTF) or []) if x.get('k') in BYT and ok_title(x['t']) and still_ok(x)]
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'eptitle-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
per = collections.defaultdict(list)
for x in res:
    if not x.get('pk'): per[(x['k'], x['se'][0], x['se'][1])].append(x)
keep = set(x['i'] for x in res if x.get('pk'))
for key, L in per.items():
    L.sort(key=lambda x: -(x.get('dl') or 0))
    for x in L[:3]: keep.add(x['i'])
res = [x for x in res if x['i'] in keep]
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
PF = os.path.join(PARTS, 'eptitle_cands.json.gz')
P = loadj(PF) or {'done': [], 'cov': {}}
STATE['done'] = sorted(set(STATE.get('done') or []) | set(P.get('done') or []))
with gzip.open(GF, 'wt', encoding='utf-8') as f: json.dump(STATE, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'kept', len(res), 'hours', hrs(res), 'searched episodes so far', len(STATE['done']))
EP = {s['k']: eplist(s) for s in SHOWS}
cov = {int(k): set(tuple(v) for v in L) for k, L in (P.get('cov') or {}).items()}
new = collections.defaultdict(set)
for x in res:
    if x.get('pk'):
        for v in x['fe'].values(): new[BYT[x['k']]['k']].add((v[0], v[1]))
    else: new[BYT[x['k']]['k']].add((x['se'][0], x['se'][1]))
table(EP, cov, new)
print('per show new episodes', sorted(((s['title'], len(new[s['k']])) for s in SHOWS if new[s['k']]), key=lambda a: -a[1]))
print('air years', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(11)
for x in random.sample(res, min(80, len(res))):
    if x.get('pk'): print('SAMPLE PACK', x['k'], '|', len(x['fe']), 'episodes', sorted('S%02dE%02d' % (v[0], v[1]) for v in x['fe'].values())[:6], '|', x['t'][:70], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min')
    else: print('SAMPLE', x['k'], '|', 'S%02dE%02d' % tuple(x['se']), x['ep'][:40], '|', x['t'][:70], '|', x['i'][:36], '|', round(x['f'][0][1] / 60), 'min', '|', x['ad'])
print('pack items', sum(1 for x in res if x.get('pk')), 'pack episode files', sum(len(x['fe']) for x in res if x.get('pk')))
