import json, gzip, os, re, sys, time, random, glob, collections, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
T0 = time.time()
OUTF = os.path.join(OUT, 'gaps.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_gaps.json'), encoding='utf-8'))
EXF = os.path.join(here, 'gaps_extra.json')
EXTRA = json.load(open(EXF, encoding='utf-8')) if os.path.exists(EXF) else []
YR = r"(?<!\d)(19[0-9]\d|20[0-2]\d)(?!\d)"
DEFNEED = r"\b(episodes?|ep\.? ?\d+|season|series|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv|television|vhs|betamax|broadcast|aired|airing|aircheck|syndicat\w*|with commercials|woc|complete|pilot|part \d|talk show|soap opera|19(8[4-9]|9\d)|200[0-4]|nbc|cbs|abc|fox|pbs|tnn|cmt|bet|espn|lifetime)\b"
def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
for s in SHOWS:
    s['S'] = [norm(a) for a in s.get('s', [])]
    s['W'] = [(norm(a.lstrip('^')), a.startswith('^')) for a in s.get('w', [])]
    s['N'] = re.compile(s.get('need') or DEFNEED)
    s['X'] = re.compile(s['x']) if s.get('x') else None
    s['XN'] = [re.compile(a) for a in s.get('xn', [])]
    r = re.findall(r'\d{4}', s['run'])
    a = int(r[0]); b = int(r[1]) if len(r) > 1 else 2030
    s['a'] = a; s['b'] = b
    s['lo'] = 1900 if s.get('old') else max(1984, a); s['hi'] = min(2004, b)
    if s['hi'] < s['lo']: s['hi'] = b
BYT = {s['title']: s for s in SHOWS}
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=60000):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > cap: break
    return out
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblada|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|fran[cç]ais|french dub|vf|vostfr|italiano|nederlands|svenska|norsk|dansk|suomi|polski|lektor|magyar|rom[aâ]n[aă]|t[uü]rk[cç]e|русск|hindi|tamil|telugu|urdu|arabic|bahasa|tagalog|sub ?esp|subtitulado|temporada|cap[ií]tulo|episodio|folge|staffel|saison|aflevering|odcinek|uk version|uk vhs|uk dvd|uk pal|pal vhs|australian version|canadian version|bbc|itv|channel 4|sky one|rte|cbc|ctv|global tv|nine network|seven network|network ten)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|playstation|xbox|rom ?hack|emulator|pinball|board game|comic book|audiobook|audio book|ebook|pdf|soundtrack|ost|theme song|theme music|fan ?made|fan-?edit|fanfilm|fan film|amv|ytp|parody|spoof|abridged|recap|podcast|reaction|commentary track|retrospective|making of|documentary about|radio show|radio broadcast|otr|old time radio|vinyl|cassette|album|sheet music|screenplay|unboxing|slideshow|screensaver|supercut|mashup|remix|karaoke|lyrics|xxx|porn|hentai|nude|bloopers?|outtakes?|trailers?|teaser|tribute|logos?|idents?|audio only|mp3|script|transcript)\b"
X_ADS = r"\b(commercial breaks?|commercial block|commercial compilation|ad breaks?|promos?|bumpers?|station ids?|radio|fm)\b|commercials?\s*(\(|-|:|from|of)|^\s*commercials"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(reboot|revival|netflix|hulu|disney\+|paramount\+|hbo max|prime video|youtube|tiktok|twitch|livestream|zoom)\b"
TAPE = r"\b(vhs|tape|recording|recorded|aircheck|air check|broadcast|commercials|betamax|off.?air|tv|[wk][a-z]{3}(-tv)?)\b"
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'tvnews', 'tvarchive', 'TV', 'democracy_now_vid'}
def core(t):
    s = norm(t)
    for _ in range(4):
        s2 = re.sub(r'^(the|a|new|all new|classic|vhs|tv|dvd|beta|tape|recording|\d{1,4}|[wk][a-z]{2,3}( tv)?( \d+)?|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|tnn|cmt|bet|mtv|vh1|cnn|espn|lifetime|discovery|nbcs|abcs) ', '', s)
        if s2 == s: break
        s = s2
    return s
def ok_title(t, s=None):
    if not t: return False
    low = t.lower() + ' '
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    if s is not None:
        if s['ct'] not in ('weather', 'shopping') and re.search(X_ADS, low): return False
        if s['X'] and s['X'].search(low): return False
        if s['ct'] != 'mag' and re.search(r'\b(reviews?|reviewed)\b', low): return False
    return True
def tyears(title):
    ys = [int(v) for v in re.findall(YR, title)]
    for m in re.finditer(r'(?<!\d)\d{1,2}[./-]\d{1,2}[./-](\d\d)(?!\d)', title):
        v = int(m.group(1)); ys.append(1900 + v if v >= 30 else 2000 + v)
    return ys
def match(s, title):
    nt = ' ' + norm(title) + ' '; c = core(title); low = title.lower() + ' ' + ' '.join(str(v) for v in tyears(title))
    for p in s['S']:
        if (' ' + p + ' ') in nt: return True
    for p, lead in s['W']:
        if lead:
            if not (c == p or c.startswith(p + ' ')): continue
        elif (' ' + p + ' ') not in nt: continue
        if s['N'].search(low): return True
    return False
def era(s, title, d, y):
    ys = tyears(title)
    inr = [v for v in ys if s['lo'] <= v <= s['hi']]
    if inr: return inr[0], 't'
    if [v for v in ys if v != s['a']]: return None, 'x'
    if s.get('s1'):
        m = re.search(r'(?i)\bseason (\d{1,2})\b|\bs(\d{1,2})\s?e\d{1,3}\b', title) if s.get('half') else None
        if m:
            v = s['s1'] + int(next(g for g in m.groups() if g)) // 2
            return (v, 's') if s['lo'] <= v <= s['hi'] else (None, 'x')
        m = re.search(r'(?i)\bs(\d{1,2})\s?e\d{1,3}\b|\bseason (\d{1,2})\b|(?<!\d)(\d{1,2})x\d{2}(?!\d)', title)
        if m:
            v = s['s1'] + int(next(g for g in m.groups() if g)) - 1
            return (v, 's') if s['lo'] <= v <= s['hi'] else (None, 'x')
    for f in (d, y):
        m = re.match(r'(\d{4})', str(f or ''))
        if m and s['lo'] <= int(m.group(1)) <= s['hi'] and int(m.group(1)) <= 2004: return int(m.group(1)), 'd'
    if s.get('open'): return None, 'x'
    lo = max(1984, s['a']); hi = min(2004, s['b'])
    if hi < lo: return '', 'g'
    return (lo + hi) // 2, 'g'
def qtitle(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', t).split())
def tstr(v):
    return ' '.join(v) if isinstance(v, list) else str(v or '')
def ids(p):
    try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
    except Exception: return set()
    out = set()
    rows = j if isinstance(j, list) else (j.get('items') or j.get('rows') or [])
    for x in rows:
        if isinstance(x, dict):
            for k in ('i', 'ia', 'identifier'):
                if isinstance(x.get(k), str): out.add(x[k])
        elif isinstance(x, list) and x and isinstance(x[0], str): out.add(x[0])
    return out
YQ = ' OR '.join(str(v) for v in range(1984, 2005))
if MODE == 'plan':
    have = set(); mine = ids(OUTF)
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))): have |= ids(p)
    print('known', len(have), 'already in gaps', len(mine), 'shows', len(SHOWS), 'extra', len(EXTRA), flush=True)
    def find(k):
        s = SHOWS[k]; res = []
        st = [qtitle(a) for a in s.get('s', [])]; wk = [qtitle(a.lstrip('^')) for a in s.get('w', [])]
        if st: res += [(x, 't') for x in scrape('mediatype:movies AND title:(' + ' OR '.join('"' + a + '"' for a in st) + ')')]
        if wk:
            ctx = 'title:(' + YQ + ' OR tv OR vhs OR episode OR season OR nbc OR cbs OR abc OR fox OR pbs OR aircheck OR broadcast' + ''.join(' OR ' + w for w in s.get('wq', [])) + ') OR subject:(tv OR television OR vhs OR "tv show" OR "talk show" OR "soap opera")'
            res += [(x, 't') for x in scrape('mediatype:movies AND title:(' + ' OR '.join('"' + a + '"' for a in wk) + ') AND (' + ctx + ')')]
        if st:
            ph = ' OR '.join('"' + a + '"' for a in st)
            res += [(x, 'm') for x in scrape('mediatype:movies AND (subject:(' + ph + ') OR description:(' + ph + '))', 30000)]
            cols = [c['identifier'] for c in scrape('mediatype:collection AND title:(' + ph + ')', 500) if not c['identifier'].startswith('fav-')]
            if cols:
                print('collections for', s['title'], cols[:20], flush=True)
                res += [(x, 'c') for x in scrape('mediatype:movies AND collection:(' + ' OR '.join(cols[:20]) + ')', 30000)]
        return k, res
    seen = {}; hits = collections.Counter(); raw = collections.Counter(); route = collections.Counter(); WHY = collections.defaultdict(collections.Counter)
    def why(k, r): WHY[k][r] += 1
    def take(k, it, via):
        s = SHOWS[k]; i = it['identifier']
        if i in seen: return
        if i in have or i in mine: return why(k, 'known')
        t = tstr(it.get('title')); lang = tstr(it.get('language'))
        if lang and not re.search(r'(?i)eng|english|^en\b', lang): return why(k, 'lang')
        col = it.get('collection') or []
        if isinstance(col, str): col = [col]
        if set(col) & XCOL: return why(k, 'col')
        if not ok_title(t, s): return why(k, 'title')
        if via in ('t', 'q') and not match(s, t): return why(k, 'nomatch')
        e, how = era(s, t, it.get('date'), it.get('year'))
        if how == 'x': return why(k, 'era')
        if via == 'x' and not match(s, t) and (how == 'g' or not all(r.search(t) for r in s['XN'])): return why(k, 'loose')
        if via == 'm':
            if match(s, t): via = 't'
            elif how not in ('t', 'd') or not re.search(r'\b(vhs|tape|recording|recorded|aircheck|air check|off.?air|betamax)\b', t.lower()): return why(k, 'mention')
        seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k, 'v': via}; hits[k] += 1; route[via] += 1
    with ThreadPoolExecutor(8) as ex:
        for k, res in ex.map(find, range(len(SHOWS))):
            raw[k] = len(res)
            for it, via in res: take(k, it, via)
            raw[k] += 0
            if k % 25 == 0: print('search', k, len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    for xq in EXTRA:
        k = next((n for n, s in enumerate(SHOWS) if s['title'] == xq['k']), None)
        if k is None: continue
        res = scrape('mediatype:movies AND (' + xq['q'].replace('YQ', YQ) + ')', 30000); n0 = hits[k]; raw[k] += len(res)
        for it in res: take(k, it, xq.get('via', 'q'))
        print('extra', xq['k'], '|', xq['q'][:90], '| raw', len(res), 'kept', hits[k] - n0, flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), 'by route', sorted(route.items()), flush=True)
    ct = collections.Counter()
    for k, n in hits.items(): ct[SHOWS[k]['ct']] += n
    print('candidates per type', sorted(ct.items()))
    print('CANDIDATES PER SHOW')
    for k, s in enumerate(SHOWS): print('  %5d raw %6d  %s [%s] %s' % (hits[k], raw[k], s['title'], s['ct'], dict(WHY[k].most_common(5))))
    with gzip.open(os.path.join(PARTS, 'gaps_cands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(cands, f, separators=(',', ':'))
    sys.exit(0)
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'h.264 HD': 2, 'MPEG4': 3, '512Kb MPEG4': 4}
LIM = {'weather': 420, 'shopping': 420, 'morning': 600, 'overnight': 600, 'soul': 600}
REJ = collections.Counter()
def meta(it):
    r = meta0(it)
    if isinstance(r, str): REJ[SHOWS[it['k']]['ct'] + ':' + r] += 1; return None
    return r
def meta0(it):
    if time.time() - T0 > BUDGET: return 'budget'
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return 'dark'
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return 'restricted'
    if str(m.get('mediatype', 'movies')) != 'movies': return 'type'
    lang = tstr(m.get('language', ''))
    if lang and not re.search(r'(?i)eng|english|^en\b', lang): return 'lang'
    s0 = SHOWS[it['k']]
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
    if not files: return 'nofile'
    lim = LIM.get(s0['ct'], 1020)
    if sum(f[1] for f in files) < lim or max(f[1] for f in files) < lim: return 'short'
    files.sort(key=lambda f: f[0])
    title = tstr(m.get('title', ''))
    s = SHOWS[it['k']]; via = it.get('v', 't')
    if not ok_title(title, s): return 'title'
    if via in ('t', 'q') and not match(s, title): return 'nomatch'
    if via == 'x' and not match(s, title) and not all(r.search(title) for r in s['XN']): return 'loose'
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(str(x) for x in desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    if set(col) & XCOL: return 'col'
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(str(x) for x in subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:500]).lower()
    if re.search(X_FOR, blob): return 'foreign'
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast)|old time radio|audio only)\b', blob): return 'junk'
    if via == 'm':
        nb = ' ' + norm(str(subj) + ' ' + desc) + ' '
        if not any((' ' + p + ' ') in nb for p in s['S']): return 'mention'
    e, how = era(s, title, m.get('date'), m.get('year'))
    if how == 'x': return 'era'
    r = {'i': it['identifier'], 'q': s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'ct': s['ct'], 'v': via}
    if how == 'g': r['g'] = 1
    return r
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'gaps_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'gaps-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); print('REJECTED', sorted(REJ.items())); sys.exit(0)
def keep(x):
    s = BYT.get(x['k'])
    if not s or not ok_title(x['t'], s): return False
    if x.get('v', 't') in ('t', 'q') and not match(s, x['t']): return False
    if x.get('v') == 'x' and not match(s, x['t']) and not all(r.search(x['t']) for r in s['XN']): return False
    if x.get('v') == 'm' and not re.search(r'\b(vhs|tape|recording|recorded|aircheck|air check|off.?air|betamax)\b', x['t'].lower()): return False
    if max(f[1] for f in x['f']) < LIM.get(s['ct'], 1020): return False
    return era(s, x['t'], x.get('d'), x.get('y'))[1] != 'x'
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
for x in old:
    e, how = era(BYT[x['k']], x['t'], x.get('d'), x.get('y')); x['e'] = e
    if how == 'g': x['g'] = 1
    else: x.pop('g', None)
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'gaps-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res), 'guessed year', sum(1 for x in res if x.get('g')))
print('routes', sorted(collections.Counter(x.get('v', 't') for x in res).items()))
bt = collections.defaultdict(list)
for x in res: bt[x['ct']].append(x)
print('TYPE TABLE')
for t in sorted(bt): print('  %-10s items %5d  hours %6d  shows %3d  guessed %5d' % (t, len(bt[t]), hrs(bt[t]), len(set(x['k'] for x in bt[t])), sum(1 for x in bt[t] if x.get('g'))))
print('CATEGORY TABLE', sorted(collections.Counter(x['q'] for x in res).items()))
print('TYPE BY YEAR')
print('  %-10s ' % 'type' + ' '.join('%4s' % str(y)[2:] for y in range(1984, 2005)) + '  n/a')
for t in sorted(bt):
    c = collections.Counter(x['e'] for x in bt[t])
    print('  %-10s ' % t + ' '.join('%4d' % c[y] for y in range(1984, 2005)) + ' %4d' % sum(n for y, n in c.items() if not isinstance(y, int) or not 1984 <= y <= 2004))
bs = collections.Counter(x['k'] for x in res)
print('SHOW TABLE')
for k, n in bs.most_common(): print('  %4d  %s [%s]' % (n, k, BYT[k]['ct']))
print('ZERO', [s['title'] + ' [' + s['ct'] + ']' for s in SHOWS if not bs[s['title']]])
print('YEAR TABLE', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(7)
for x in random.sample(res, min(60, len(res))): print('SAMPLE', x['ct'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'], 'g' if x.get('g') else '', x.get('v', ''))
