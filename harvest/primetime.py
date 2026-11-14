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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language,description', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        for it in j.get('items', []):
            it['description'] = ' '.join(flat(it.get('description')).split())[:1500]
            out.append(it)
        cursor = j.get('cursor')
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
BYT = {}
for _s in SHOWS: BYT.setdefault(_s['title'], _s)
STOP = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'to', 'with', 'show', 'by', 'for', 'is', 'it', 'at', 'from', 'md', 'mr'}
def sig(q): return [w for w in norm(q).split() if w not in STOP]
def generic(sh): return bool(sh.get('amb')) or len(sig(sh['q'][0])) <= 2
def start(sh): return sh.get('start', sh['first'])
WORDN = {w: i + 1 for i, w in enumerate('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen'.split())}
WORDN.update({w: i + 1 for i, w in enumerate('first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split())})
MULTI = re.compile(r"\bseasons\b|\b(?:s|season)\s?\d{1,2}\s?(?:-|&|and|to|thru|through)\s?(?:s|season)?\s?\d{1,2}\b|complete series|all episodes|all seasons|entire series|full series|complete collection")
SEAS = re.compile(r"\bseason\s?(\d{1,2})\b|\bseason\s(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)(?:\sand\sfinal)?\sseason\b|\b(?:s|se|y)\s?(\d{1,2})\s?(?:e|ep|d|disc)\s?\d{1,3}\b|\bs(\d{1,2})\b|\b(\d{1,2})x\s?\d{1,3}\b")
def clean(t): return re.sub(r'(?<=[a-z0-9]{2})\.(?=[a-z0-9]{2})', ' ', re.sub(r'[_]+', ' ', t.lower().replace('’', "'")))
def seasons(low):
    out = set()
    for m in SEAS.finditer(low):
        g = next(x for x in m.groups() if x)
        out.add(WORDN[g] if g in WORDN else int(g))
    return sorted(out)
def one_season(low):
    if MULTI.search(low): return 0
    ss = seasons(low)
    return ss[0] if len(ss) == 1 and ss[0] > 0 else 0
def item_year(it):
    m = re.match(r'(\d{4})', flat(it.get('date')) or flat(it.get('year')) or '')
    return int(m.group(1)) if m else 0
SPIN = re.compile(r"\b(svu|special victims|criminal intent|trial by jury|golden palace|new class|college years|girl meets world|fuller house|the conners|young sheldon|reboot|revival|frasier 2023|animated series)\b")
FOREIGN = re.compile(r"\b(saison|temporada|staffel|episodio|epis[oó]dio|cap[ií]tulo|folge|parte|piloto|serie tv|vf|fr|ita|lat|pt br|dual audio|dublagem|dub|napisy|lektor|esp|ger|nl|temp|s[eé]rie)\b")
DESCEV = re.compile(r"\b(sitcom|tv series|television series|nbc|cbs|abc|upn|the wb|syndicat\w*|vhs|commercials|laugh track|primetime|prime time)\b")
JUNKD = re.compile(r"\b(podcast|sermon|city council|board of|town meeting|gameplay|walkthrough|let's play|longplay|reviews?|reaction|public access|community television|community media|pastor|ministry|church|webinar|lecture|school district|chamber of commerce|library|nonprofit|non-profit|fundraiser|workshop|expo|home show|contractor|remodeling tips)\b")
TAPE = re.compile(r"\b(vhs|betamax|tape|taped|recorded|recording|commercials|woc|broadcast|aired|airing|nbc|cbs|abc|fox|upn|wb|tgif|must see tv|primetime|prime time)\b")
TAPE2 = re.compile(r"\b(vhs|betamax|commercials|woc|off air|off-air|home recording)\b")
EPN = re.compile(r"\b(?:episode|ep)\.?\s?#?(\d{1,4})\b")
def has_cast(sh, blob): return any(c.lower() in blob for c in sh.get('cast', []))
def year_ok(sh, t):
    ys = [int(y) for y in YR.findall(t)]
    if not ys: return True
    lo, hi = sh['first'], sh['last']
    return any(lo <= y <= max(hi, min(2004, lo + 20)) and y <= 2004 for y in ys) or any(lo <= y <= hi for y in ys)
LEAD = re.compile(r"^(?:\s*(?:\(?\d{1,4}[-./]\d{1,2}(?:[-./]\d{1,4})?\)?|(?:19|20)\d\d|vhs|beta|tape|dvd|tv|the|nbc|cbs|abc|fox|upn|wb|[wk][a-z]{2,3}(?:-tv)?(?:\s?\d{1,2})?)\b[\s\-:,.|]*)*", re.I)
TAIL = re.compile(r"^\s*(?:$|[-:|(\[,#]|\b(?:s\s?\d{1,2}\s?e\s?\d{1,3}|s\s?\d{1,2}\b|y\s?\d{1,2}\s?e\s?\d{1,3}|d\s?\d{1,2}\b|\d{1,2}x\s?\d{1,3}|\d{1,3}\b|season|seasons|series|episode|episodes|ep\b|complete|full|sitcom|tv|pilot|finale|nbc|cbs|abc|fox|upn|wb|vhs|dvd|disc|vol|volume|tape|with commercials|w commercials|woc|commercials|(?:19[89]\d|200[0-4])|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b)", re.I)
DAILY = {'news', 'soap', 'talk'}
MOD2 = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](0[5-9]|[12]\d)\b')
def head(sh, t):
    best = 0
    for low in (clean(t), LEAD.sub('', clean(t))):
        low = low.replace("'", '').replace('&', ' and ').strip()
        for q in sh['q']:
            ws = norm(q).split()
            if ws and ws[0] == 'the': ws = ws[1:]
            if not ws: continue
            m = re.match(r"(?:the[\W_]+)?" + r"[\W_]*".join("[.']?".join(re.escape(ch) for ch in w) for w in ws) + r"(?![a-z0-9])", low)
            if m:
                rest = low[m.end():]
                if not re.match(r'-[a-z]', rest) and TAIL.match(rest.lstrip(" '!?.")): return 2
                best = 1
    return best
def strict(sh, t): return head(sh, t) == 2
def verify(sh, x):
    ds = sorted(f[1] for f in x['f'])
    blob = ((x.get('ds') or '') + ' ' + (x.get('s') or '')).lower()
    return has_cast(sh, blob) or bool(DESCEV.search(blob)) or (len(ds) >= 3 and 1080 <= ds[len(ds) // 2] <= 4200)
def season_ok(sh, low):
    return all(start(sh) + n - 1 <= sh['last'] + 1 for n in seasons(low))
def consider(sh, it, route='t'):
    t = flat(it.get('title')); low = clean(t)
    if not t or NONLAT.search(t) or JUNK.search(low) or FOREIGN.search(low) or SPIN.search(low): return False
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return False
    if MOD2.search(t): return False
    nt = ' ' + norm(low) + ' '
    intitle = any((' ' + norm(q) + ' ') in nt for q in sh['q'])
    desc = flat(it.get('description')).lower(); subj = flat(it.get('subject')).lower()
    cols = set(it.get('collection') or []) if isinstance(it.get('collection'), list) else {it.get('collection')}
    iy = item_year(it); mod = iy > 2004 and iy > sh['last']
    inrun = any(sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t)) or (iy and sh['first'] <= iy <= sh['last'])
    cast = has_cast(sh, desc + ' ' + subj + ' ' + low)
    if not intitle:
        if route != 'd' or not sh.get('must'): return False
        nd = ' ' + norm(desc) + ' '
        if not any((' ' + norm(q) + ' ') in nd for q in sh['q']): return False
        if MODERN.search(t) or mod or JUNKD.search(desc): return False
        if not (TAPE.search(low) or cols & TVSET): return False
        if generic(sh) and not (cast or (inrun and re.search(r'\b(nbc|cbs|abc|fox|upn|wb|sitcom|commercials)\b', desc))): return False
        return 'd'
    if not year_ok(sh, t) or not season_ok(sh, low): return False
    if MODERN.search(t) and not inrun: return False
    if sh['kind'] in DAILY and not (airdate(t) or any(1984 <= int(y) <= 2004 and sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t))): return False
    strong = bool(seasons(low)) or bool(MULTI.search(low))
    m = EPN.search(low)
    if m and not seasons(low) and sh['kind'] not in DAILY and sh['kind'] not in ('game', 'reality') and int(m.group(1)) > 30 * (sh['last'] - start(sh) + 1): return False
    weak = bool(DISC.search(low + ' ' + subj)) or bool(cols & TVSET) or bool(inrun) or any(norm(q) in norm(subj) for q in sh['q'])
    dev = cast or bool(DESCEV.search(desc))
    hd = head(sh, low); st = hd == 2
    if sh['kind'] in DAILY: return 't'
    if not strong and not cast and JUNKD.search(desc + ' ' + low): return False
    tape = bool(TAPE.search(low))
    if generic(sh):
        if st and (strong or cast or (weak and (not mod or dev))): return 't'
        if hd and (strong or cast or ((weak or tape) and not mod)): return 't'
        if st and not sh.get('amb') and len(sig(sh['q'][0])) >= 2: return 'v'
        if not hd and len(low) < 160 and (TAPE2.search(low) or (tape and not mod and (inrun or cast or cols & TVSET))): return 'b'
        return False
    if strong or cast: return 't'
    if weak and (not mod or dev or st): return 't'
    if st: return 't' if not mod else 'v'
    return False
def load_old():
    F = os.path.join(OUT, 'primetime.json.gz')
    if not os.path.exists(F): return [], []
    keep, drop = [], []
    for x in json.load(gzip.open(F, 'rt', encoding='utf-8')):
        sh = BYT.get(x.get('k'))
        r = sh and consider(sh, {'title': x.get('t'), 'collection': x.get('c'), 'subject': x.get('s'), 'description': x.get('ds'), 'date': '' if x.get('ad') else x.get('d')}, 'd' if x.get('r') == 'd' else 't')
        if r in ('b', 'd'): x['r'] = r
        if r and post_ok(sh, x) and (r != 'v' or verify(sh, x)): keep.append(x)
        else: drop.append(x)
    return keep, drop
def plan():
    have = load_have(); keep, drop = load_old()
    for x in keep: have.add(x['i'])
    print('have', len(have), 'shows', len(SHOWS), 'old kept', len(keep), 'old dropped', len(drop), flush=True)
    def one(sh):
        res = {}
        for q in sh['q']:
            ph = q.replace('"', '')
            base = 'mediatype:movies AND title:("%s")' % ph
            qs = [(base + ' AND (' + DISQ + ' OR collection:(' + TVCOL + '))', 't')] if len(sig(q)) <= 1 else [(base, 't')]
            if len(sig(q)) > 1 or sh.get('must'): qs.append(('mediatype:movies AND subject:("%s")' % ph, 't'))
            if sh.get('must'):
                extra = ' AND (' + ' OR '.join('"%s"' % c for c in sh['cast'][:4]) + ' OR nbc OR cbs OR abc OR fox OR sitcom)' if len(sig(q)) <= 1 and sh.get('cast') else ''
                qs.append(('mediatype:movies AND description:("%s")%s AND (collection:(%s) OR title:(vhs OR tape OR commercials OR nbc OR cbs OR abc OR fox OR upn OR wb OR recorded))' % (ph, extra, TVCOL), 'd'))
            for qq, route in qs:
                for it in scrape(qq):
                    i = it.get('identifier')
                    if not i or i in have or i in res: continue
                    r = consider(sh, it, route)
                    if r: res[i] = (it, r)
        return sh, res
    seen = {}; per = collections.Counter(); perd = collections.Counter()
    order = sorted(SHOWS, key=lambda s: (0 if s.get('must') else 1, -len(s['title'])))
    with ThreadPoolExecutor(6) as ex:
        for sh, res in ex.map(one, order):
            for i, (it, r) in res.items():
                if i in seen:
                    if seen[i]['r'] == 't' or r != 't': continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': sh['title'], 'net': sh['net'], 'kind': sh['kind'], 'first': sh['first'], 'last': sh['last'], 'must': 1 if sh.get('must') else 0, 'r': r}
                if r == 't': per[sh['title']] += 1
                else: perd[sh['title']] += 1
    c = sorted(seen.values(), key=lambda x: (-x['must'], x['r'] != 't', -x['downloads']))
    print('candidates', len(c), 'title', sum(1 for x in c if x['r'] == 't'), 'tape', sum(1 for x in c if x['r'] != 't'), flush=True)
    for sh in SHOWS:
        if sh.get('must'): print('MUSTCAND', per[sh['title']], perd[sh['title']], sh['title'])
    for k, n in per.most_common(60): print('  cand', n, k)
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
def post_ok(sh, x):
    ds = [f[1] for f in x['f']]
    if not ds: return False
    if x.get('q') == 'prime' and sh['kind'] in ('sitcom', 'drama') and x.get('r', 't') == 't':
        if sorted(ds)[len(ds) // 2] < 600: return False
        if len(ds) == 1 and ds[0] < 1080: return False
    return True
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
    sh = BYT[c['k']]
    t = flat(m.get('title'))[:200]; desc = ' '.join(flat(m.get('description')).split())[:400]
    x = {'i': c['identifier'], 'q': KMAP.get(c['kind'], 'prime'), 't': t, 'd': '', 'y': '', 'c': [], 's': flat(m.get('subject')).replace(' ', ' ')[:200], 'ds': desc, 'f': files[:60], 'dl': c.get('downloads') or 0, 'k': c['k'], 'e': 0, 'net': c['net'], 'ad': '', 'r': c.get('r', 't'), 'nf': len(files)}
    col = m.get('collection', []); x['c'] = ([col] if isinstance(col, str) else col)[:4]
    x['d'] = flat(m.get('date'))
    if x['r'] == 'v':
        if not verify(sh, x): return None
        x['r'] = 't'
    if not stamp(sh, x) or not post_ok(sh, x): return None
    return x
def stamp(sh, x):
    t = x['t']; low = clean(t)
    ad = airdate(t) or airdate((x.get('ds') or '')[:200])
    if ad and not (sh['first'] <= int(ad[:4]) <= sh['last'] + 1): ad = ''
    sn = one_season(low) if x.get('r', 't') == 't' else 0
    ys = [int(y) for y in YR.findall(t) if sh['first'] <= int(y) <= sh['last'] and 1984 <= int(y) <= 2004]
    dy = re.match(r'(\d{4})', '' if x.get('ad') and not ad else (x.get('d') or ''))
    dy = int(dy.group(1)) if dy and sh['first'] <= int(dy.group(1)) <= sh['last'] and 1984 <= int(dy.group(1)) <= 2004 else 0
    if ad: e = int(ad[:4])
    elif sn and start(sh) + sn - 1 <= sh['last'] + 1: e = min(start(sh) + sn - 1, sh['last'])
    elif ys: e = ys[0]
    elif dy: e = dy
    else: e = max(sh['first'], 1984) if sh['last'] >= 1984 else 0
    if not e or e > 2004: return False
    e = max(e, 1984)
    if ad: x['d'] = ad
    x['ad'] = ad; x['e'] = e; x['y'] = str(e)
    if sn: x['sn'] = sn
    else: x.pop('sn', None)
    return True
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
    keep, drop = load_old()
    rawids = {x['i'] for x in json.load(gzip.open(os.path.join(OUT, 'raw.json.gz'), 'rt', encoding='utf-8')) if isinstance(x, dict)} if os.path.exists(os.path.join(OUT, 'raw.json.gz')) else set()
    print('old in raw dropped', sum(1 for x in keep if x['i'] in rawids))
    keep = [x for x in keep if x['i'] not in rawids]
    for x in keep: stamp(BYT[x['k']], x)
    have = {x['i'] for x in keep} | load_have(); add = []
    R = collections.defaultdict(lambda: [0, 0, 0])
    keys = [(sh, [' ' + norm(q) + ' ' for q in sh['q']]) for sh in SHOWS]
    seenr = set()
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))):
        if p.endswith('primetime.json.gz') or p.endswith('ads.json.gz'): continue
        try: rows = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        for x in rows:
            if not isinstance(x, dict) or x.get('i') in seenr or not x.get('f'): continue
            nt = ' ' + norm(clean(x.get('t', ''))) + ' '
            for sh, qs in keys:
                if any(q in nt for q in qs) and consider(sh, {'title': x.get('t'), 'collection': x.get('c'), 'subject': x.get('s'), 'description': x.get('ds'), 'date': ''}) == 't':
                    seenr.add(x['i']); v = R[sh['title']]; v[0] += 1; v[1] += len(x['f']); v[2] += sum(f[1] for f in x['f'] if len(f) > 1 and isinstance(f[1], (int, float)))
                    break
    for p in sorted(glob.glob(os.path.join(PARTS, 'pt-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have: have.add(x['i']); add.append(x)
    allx = keep + add
    if not allx: print('nothing to write'); return
    json.dump(allx, gzip.open(F, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    hrs = lambda xs: round(sum(sum(f[1] for f in x['f']) for x in xs) / 3600)
    print('old kept', len(keep), 'old purged', len(drop), 'added', len(add), 'total', len(allx), 'hours', hrs(allx))
    print('== PURGED per show')
    for k, n in collections.Counter(x['k'] for x in drop).most_common(): print('PURGED', n, k)
    for x in drop[:400:8]: print('PURGEDSAMPLE', x['k'], '|', x['t'][:90])
    print('per net', sorted(collections.Counter(x['net'] for x in allx).items()))
    print('per net hours', sorted((n, hrs([x for x in allx if x['net'] == n])) for n in set(x['net'] for x in allx)))
    print('per cat', sorted(collections.Counter(x['q'] for x in allx).items()))
    print('per year', sorted(collections.Counter(x['e'] for x in allx).items()))
    print('per season', sorted(collections.Counter(x.get('sn', 0) for x in allx).items()))
    print('routes', sorted(collections.Counter(x.get('r', 't') for x in allx).items()), 'exact dates', sum(1 for x in allx if x.get('ad')))
    T = collections.defaultdict(lambda: [0, 0, 0, 0, collections.Counter()])
    for x in allx:
        v = T[x['k']]
        if x.get('r', 't') == 't':
            v[0] += 1; v[1] += len(x['f']); v[2] += sum(f[1] for f in x['f'])
            if x.get('sn'): v[4][x['sn']] += len(x['f'])
        else: v[3] += 1
    print('== MUST table (flag | title | net | items | episode files | hours | tape items | other catalogs items | other catalogs files | other catalogs hours | seasons)')
    done = set()
    for s in SHOWS:
        if not s.get('must') or s['title'] in done: continue
        done.add(s['title']); v = T[s['title']]; r = R[s['title']]
        flag = 'FOUND' if v[1] + r[1] >= 20 else 'THIN' if v[1] or v[3] or r[1] else 'MISSING'
        print('MUST', flag, '|', s['title'], '|', s['net'], '|', v[0], '|', v[1], '|', round(v[2] / 3600, 1), '|', v[3], '|', r[0], '|', r[1], '|', round(r[2] / 3600, 1), '|', ' '.join('S%d:%d' % kv for kv in sorted(v[4].items())))
    print('== all shows with items (items files hours tape title)')
    for k, v in sorted(T.items(), key=lambda kv: -kv[1][1]): print('SHOW', v[0], v[1], round(v[2] / 3600, 1), v[3], BYT[k]['net'], BYT[k]['kind'], k)
    for net in ('nbc', 'cbs', 'abc', 'fox', 'wb', 'upn', 'syn'):
        print('== ZERO', net, ' ; '.join(sorted(set(s['title'] for s in SHOWS if s['net'] == net and s['title'] not in T and not R[s['title']][1]))))
        print('== ELSEWHERE ONLY', net, ' ; '.join(sorted(set('%s (%d)' % (s['title'], R[s['title']][1]) for s in SHOWS if s['net'] == net and s['title'] not in T and R[s['title']][1]))))
    random.seed(11)
    for x in random.sample(allx, min(60, len(allx))): print('SAMPLE', x['net'], x['e'], x.get('sn', '-'), x.get('r', 't'), x['k'], '|', x['t'][:80], '|', len(x['f']), sum(f[1] for f in x['f']) // 60)
{'plan': plan, 'meta': run_meta, 'merge': merge}[MODE]()
