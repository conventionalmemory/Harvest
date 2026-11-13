import json, gzip, os, re, sys, time, glob, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts')
os.makedirs(OUT, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
THREADS = int(os.environ.get('THREADS', '16')); BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60; T0 = time.time()
SHOWS = json.load(open(os.path.join(here, 'shows_primetime.json'), encoding='utf-8'))
KMAP = {'sitcom': 'prime', 'drama': 'prime', 'variety': 'prime', 'reality': 'prime', 'special': 'prime', 'news': 'news', 'soap': 'soap', 'game': 'game', 'talk': 'talk', 'movie': 'movie'}
TVCOL = 'television OR television_inbox OR classic_tv OR classic_tv_1980s OR classic_tv_1990s OR vhstvshows OR vhsvault OR gorelicktv OR smokesvhsdvrcollection OR sitcoms OR televisionmovies OR vhsnews OR gameshows OR dvdtray OR dvdtray_inbox'
TVSET = set(TVCOL.split(' OR '))
DISQ = 'title:(season OR seasons OR episode OR episodes OR complete OR series OR sitcom OR nbc OR cbs OR abc OR fox OR upn OR vhs OR commercials OR woc OR "tv show" OR pilot OR finale OR s0* OR s1* OR 1x* OR 2x* OR 3x* OR 4x* OR 5x*) OR subject:(television OR sitcom OR "tv series" OR "tv show" OR nbc OR cbs OR abc OR vhs OR commercials OR "tv")'
DISC = re.compile(r"\b(s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|season\s?\d|seasons?|episodes?|ep\.?\s?\d|complete|series|sitcom|nbc|cbs|abc|fox|upn|wb|vhs|commercials|woc|w/o/c|tv show|pilot|finale|syndicat|aired|airing|broadcast|rerun)\b")
JUNK = re.compile(r"\b(trailers?|teasers?|promos?|bumpers?|opening|intro|theme song|theme|soundtrack|ost|review|reviews|reaction|reacts?|podcast|commentary|interview|interviews|panel|q&a|reunion special 20|behind the scenes|bloopers?|outtakes|gag reel|tribute|fan ?made|fan ?edit|fanvid|amv|parody|recap|explained|analysis|ranking|ranked|top \d+|video essay|documentary about|making of|game|gameplay|walkthrough|playthrough|longplay|ps[1-5]|xbox|nintendo|sega|pinball|slot machine|lego|toy|toys|figure|unboxing|audiobook|audio book|book|novel|comic|magazine|script|screenplay|sermon|church|council|selectmen|committee|town meeting|lecture|seminar|conference|webinar|karaoke|cover|remix|live at|concert|album|mixtape|dj|radio|stream|twitch|youtube|tiktok|remaster(ed)?|upscaled?|ai|deepfake|mock|ytp|compilation of clips|clips?|scene|scenes|moments|highlights|best of youtube|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|german|fran[cç]ais|french|italiano|italian|portugu[eê]s|legendado|subtitulado|vostfr|rus|russian|polish|polski|hindi|arabic|turkish|greek|dutch|svenska|suomi|norsk|dansk|magyar|czech|bbc|itv|channel 4|sky one|uk tv|uk|australia|australian|canada only|sub ita|sub esp|sub|subs|subtitle|subtitles|subbed|indonesia|malay|thai|vietsub|tagalog|historical society|museum|middle school|high school|jr|junior|lions club|talk series|live stream|livestream|discord|socials|tell all|cycle \d+|wrestling|ajpw|njpw|army|racing|paranormal|artist|thomas|tank engine|dora|bond|cupid|translation)\b")
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
MODERN = re.compile(r'(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)')
YR = re.compile(r'(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)')
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=30000):
    out, cursor = [], None
    while len(out) < cap:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor: break
    return out
def norm(s):
    s = s.lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[.'!?,:]", '', s)
    return re.sub(r'[^a-z0-9$/]+', ' ', s).strip()
def flat(v): return ' '.join(v) if isinstance(v, list) else str(v or '')
def load_have():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if p.endswith('primetime.json.gz') or p.endswith('ads.json.gz') or p.endswith('movies.json.gz'): continue
        try:
            for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
                have.add(x['i'] if isinstance(x, dict) else x[0])
        except Exception as e: print('skip', p, e)
    return have
def year_ok(sh, t):
    ys = [int(y) for y in YR.findall(t)]
    if not ys: return True
    lo, hi = sh['first'], sh['last']
    return any(lo <= y <= max(hi, min(2004, lo + 20)) and y <= 2004 for y in ys) or any(lo <= y <= hi for y in ys)
LEAD = re.compile(r"^(?:\s*(?:\(?\d{1,4}[-./]\d{1,2}(?:[-./]\d{1,4})?\)?|(?:19|20)\d\d|vhs|beta|tape|dvd|tv|the|nbc|cbs|abc|fox|upn|wb|[wk][a-z]{2,3}(?:-tv)?(?:\s?\d{1,2})?)\b[\s\-:,.|]*)*", re.I)
TAIL = re.compile(r"^\s*(?:$|[-:|(\[,]|\b(?:s\d{1,2}\s?e\d{1,3}|s\d{1,2}\b|\d{1,2}x\d{2}|season|seasons|series|episode|episodes|ep\b|complete|full|sitcom|tv|pilot|finale|nbc|cbs|abc|fox|upn|wb|vhs|dvd|with commercials|w commercials|woc|commercials|(?:19[89]\d|200[0-4])|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b)", re.I)
DAILY = {'news', 'soap', 'talk'}
MOD2 = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](0[5-9]|[12]\d)\b')
def strict(sh, t):
    low = LEAD.sub('', t.lower().replace('’', "'")).strip()
    for q in sorted(sh['q'], key=len, reverse=True):
        ql = q.lower()
        for cand in (ql, ql[4:] if ql.startswith('the ') else ql):
            if low.startswith(cand):
                rest = low[len(cand):]
                if rest[:1].isalnum(): continue
                if TAIL.match(rest.lstrip(" '!?.")): return True
    return False
def season_ok(sh, t):
    m = re.search(r'\b(?:season|s)\s?(\d{1,2})\b', t.lower())
    return not m or sh['first'] + int(m.group(1)) - 1 <= sh['last'] + 1
def consider(sh, it):
    t = flat(it.get('title')); low = t.lower()
    if not t or NONLAT.search(t) or JUNK.search(low): return False
    nt = ' ' + norm(t) + ' '
    if not any((' ' + norm(q) + ' ') in nt for q in sh['q']): return False
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return False
    if not year_ok(sh, t): return False
    if MODERN.search(t) and not any(sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t)): return False
    if MOD2.search(t) or not season_ok(sh, t): return False
    if sh['kind'] in DAILY and not (airdate(t) or any(1984 <= int(y) <= 2004 and sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t))): return False
    if sh.get('amb') and not strict(sh, t): return False
    if sh.get('amb'):
        cols = set(it.get('collection') or []) if isinstance(it.get('collection'), list) else {it.get('collection')}
        blob = low + ' ' + flat(it.get('subject')).lower()
        if not (DISC.search(blob) or cols & TVSET): return False
        rest = nt
        for q in sh['q']: rest = rest.replace(' ' + norm(q) + ' ', ' ', 1)
        if len(norm(sh['q'][0])) <= 8 and not DISC.search(low) and len(rest.split()) > 6: return False
    return True
def plan():
    have = load_have(); print('have', len(have), 'shows', len(SHOWS), flush=True)
    def one(sh):
        res = {}
        for q in sh['q']:
            ph = q.replace('"', '')
            base = 'mediatype:movies AND title:("%s")' % ph
            qs = [base + ' AND (' + DISQ + ' OR collection:(' + TVCOL + '))'] if sh.get('amb') else [base]
            if sh.get('must'): qs.append('mediatype:movies AND subject:("%s")' % ph)
            for qq in qs:
                for it in scrape(qq):
                    i = it.get('identifier')
                    if not i or i in have or i in res: continue
                    if consider(sh, it): res[i] = it
        return sh, res
    seen = {}; per = collections.Counter()
    order = sorted(SHOWS, key=lambda s: (0 if s.get('must') else 1, -len(s['title'])))
    with ThreadPoolExecutor(6) as ex:
        for sh, res in ex.map(one, order):
            n = 0
            for i, it in res.items():
                if i in seen: continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': sh['title'], 'net': sh['net'], 'kind': sh['kind'], 'first': sh['first'], 'last': sh['last'], 'must': 1 if sh.get('must') else 0}; n += 1
            per[sh['title']] = n
    c = sorted(seen.values(), key=lambda x: (-x['must'], -x['downloads']))
    print('candidates', len(c), flush=True)
    for sh in SHOWS:
        if sh.get('must'): print('MUSTCAND', per[sh['title']], sh['title'])
    for k, n in per.most_common(60): print('  cand', n, k)
    print('zero-candidate shows', len([1 for s in SHOWS if not per[s['title']]]))
    json.dump(c, gzip.open(os.path.join(PARTS, 'cands.json.gz'), 'wt', encoding='utf-8'), separators=(',', ':'))
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def airdate(t):
    m = re.search(r'\b(19[89]\d|200[0-4])[-./ ](\d{1,2})[-./ ](\d{1,2})\b', t)
    if m and 1 <= int(m.group(2)) <= 12: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./](19[89]\d|200[0-4]|[89]\d)\b', t)
    if m and 1 <= int(m.group(1)) <= 12:
        y = int(m.group(3)); y = y + 1900 if y < 100 else y
        return '%d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', t.lower())
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(1)], int(m.group(2)))
    return ''
def meta(c):
    if BUDGET and time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(c['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    lang = flat(m.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return None
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9)); b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 240: continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (d / 60) > 30: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 900: return None
    files.sort(key=lambda f: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', f[0])])
    t = flat(m.get('title'))[:200]; desc = ' '.join(flat(m.get('description')).split())[:400]
    ad = airdate(t) or airdate(desc[:200])
    ys = [int(y) for y in YR.findall(t) if c['first'] <= int(y) <= c['last'] and 1984 <= int(y) <= 2004]
    dy = re.match(r'(\d{4})', flat(m.get('date')) or flat(m.get('year')) or '')
    e = int(ad[:4]) if ad else ys[0] if ys else int(dy.group(1)) if dy and c['first'] <= int(dy.group(1)) <= c['last'] and 1984 <= int(dy.group(1)) <= 2004 else 0
    if not e:
        sm = re.search(r'\b(?:s|season\s?)(\d{1,2})\b', t.lower())
        e = c['first'] + int(sm.group(1)) - 1 if sm and c['first'] + int(sm.group(1)) - 1 <= c['last'] else max(c['first'], 1984) if c['last'] >= 1984 else 0
    if not e or e > 2004: return None
    e = max(e, 1984)
    col = m.get('collection', []); col = [col] if isinstance(col, str) else col
    return {'i': c['identifier'], 'q': KMAP.get(c['kind'], 'prime'), 't': t, 'd': ad or flat(m.get('date')), 'y': str(e), 'c': col[:4], 's': flat(m.get('subject')).replace(' ', ' ')[:200], 'ds': desc, 'f': files[:60], 'dl': c.get('downloads') or 0, 'k': c['k'], 'e': e, 'net': c['net'], 'ad': ad}
def run_meta():
    c = json.load(gzip.open(os.path.join(PARTS, 'cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'items', len(c), flush=True); res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, c)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), flush=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'pt-%d.json.gz' % SHARD), 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res))
def merge():
    F = os.path.join(OUT, 'primetime.json.gz')
    old = []
    have = set(); add = []
    rawc = collections.Counter()
    RP = os.path.join(OUT, 'raw.json.gz')
    if os.path.exists(RP):
        musts = [(sh['title'], [' ' + norm(q) + ' ' for q in sh['q']]) for sh in SHOWS if sh.get('must')]
        for x in json.load(gzip.open(RP, 'rt', encoding='utf-8')):
            nt = ' ' + norm(x.get('t', '')) + ' '
            for ti, qs in musts:
                if any(q in nt for q in qs): rawc[ti] += 1
    for p in sorted(glob.glob(os.path.join(PARTS, 'pt-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have: have.add(x['i']); add.append(x)
    allx = old + add
    json.dump(allx, gzip.open(F, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('old', len(old), 'added', len(add), 'total', len(allx), 'hours', round(sum(sum(f[1] for f in x['f']) for x in allx) / 3600))
    print('per net', sorted(collections.Counter(x['net'] for x in allx).items()))
    print('per cat', sorted(collections.Counter(x['q'] for x in allx).items()))
    print('per year', sorted(collections.Counter(x['e'] for x in allx).items()))
    print('exact dates', sum(1 for x in allx if x.get('ad')))
    per = collections.Counter(x['k'] for x in allx); eps = collections.Counter()
    for x in allx: eps[x['k']] += len(x['f'])
    print('== MUST table (title | items | files)')
    for s in SHOWS:
        if s.get('must'): print('MUST', s['title'], '|', per[s['title']], '|', eps[s['title']], '| already in main catalog raw:', rawc[s['title']], '' if per[s['title']] + rawc[s['title']] >= 5 else '<< THIN')
    print('== all shows with items')
    for k, n in per.most_common(): print('SHOW', n, eps[k], k)
    print('== ZERO', ' ; '.join(s['title'] for s in SHOWS if not per[s['title']]))
    random.seed(11)
    for x in random.sample(allx, min(70, len(allx))): print('SAMPLE', x['net'], x['e'], x['k'], '|', x['t'][:80], '|', len(x['f']), sum(f[1] for f in x['f']) // 60)
{'plan': plan, 'meta': run_meta, 'merge': merge}[MODE]()
