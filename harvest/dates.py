import gzip, json, os, re, sys, time, glob, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(here, '..', 'catalog')
sys.path.insert(0, os.path.join(here, '..', 'build'))
UA = {'User-Agent': 'retrotv-sources/1.0 (https://conventionalmemory.io; air date resolver)'}
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
T0 = time.time()
OWN = {'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'movies.json.gz', 'ads.json.gz', 'filler.json.gz', 'sports.json.gz'}
def left(): return BUDGET - (time.time() - T0)
def get(url, tries=4, pause=0, raw=False):
    if os.environ.get('OFFLINE'): return None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read().decode('utf-8', 'replace')
                if pause: time.sleep(pause)
                return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(6 * (k + 1) if e.code == 429 else 3 * (k + 1))
        except Exception:
            time.sleep(3 * (k + 1))
    return None
def load(name):
    p = os.path.join(CAT, name)
    return json.load(gzip.open(p, 'rt', encoding='utf-8')) if os.path.exists(p) else None
def save(name, obj):
    with gzip.open(os.path.join(CAT, name), 'wt', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
def norm(s):
    s = str(s).lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"'", '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    return re.sub(r'^the ', '', s)
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
MN = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
YR = r'(19[3-9]\d|20[0-2]\d)'
def ok(y, m=1, d=1):
    return 1930 <= y <= 2029 and 1 <= m <= 12 and 1 <= d <= 31
def y2(v):
    v = int(v)
    if v >= 100: return v
    return 1900 + v if v >= 30 else 2000 + v
def fmt(y, m=0, d=0):
    return '%04d-%02d-%02d' % (y, m, d) if d else '%04d-%02d' % (y, m) if m else '%04d' % y
R_YMD = re.compile(r'(?<!\d)' + YR + r'[-./ _](\d{1,2})[-./ _](\d{1,2})(?!\d)')
R_MDY = re.compile(r'(?<!\d)(\d{1,2})[-./](\d{1,2})[-./](\d{4}|\d{2})(?!\d)')
R_8 = re.compile(r'(?<!\d)(19[3-9]\d|200\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)')
R_MNDY = re.compile(r'\b' + MN + r'\.?\s*(\d{1,2})(?:st|nd|rd|th)?(?:\s*[-–&]\s*\d{1,2}(?:st|nd|rd|th)?)?,?\s+' + YR + r'\b', re.I)
R_DMNY = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+' + MN + r'\.?,?\s+' + YR + r'\b', re.I)
R_MNY = re.compile(r'\b' + MN + r'\.?,?\s+(?:of\s+)?' + YR + r'\b', re.I)
R_MNDYY = re.compile(r'\b' + MN + r"\.?\s*(\d{1,2})(?:st|nd|rd|th)?,?\s+'?(\d{2})\b", re.I)
R_Y = re.compile(r'(?<![\d#])' + YR + r'(?![\d])')
def find_dates(text):
    out = []; t = str(text or ''); used = []
    def add(y, m, d, span):
        if not ok(y, m or 1, d or 1): return
        if d:
            try: time.strptime('%d-%d-%d' % (y, m, d), '%Y-%m-%d')
            except Exception: return
        for a, b in used:
            if span[0] < b and span[1] > a: return
        used.append(span); out.append((fmt(y, m, d), 'd' if d else 'm' if m else 'y'))
    for m in R_MNDY.finditer(t): add(int(m.group(3)), MON[m.group(1)[:3].lower()], int(m.group(2)), m.span())
    for m in R_DMNY.finditer(t): add(int(m.group(3)), MON[m.group(2)[:3].lower()], int(m.group(1)), m.span())
    for m in R_YMD.finditer(t): add(int(m.group(1)), int(m.group(2)), int(m.group(3)), m.span())
    for m in R_8.finditer(t): add(int(m.group(1)), int(m.group(2)), int(m.group(3)), m.span())
    for m in R_MDY.finditer(t):
        a, b, y = int(m.group(1)), int(m.group(2)), y2(m.group(3))
        if a > 12 and b <= 12: a, b = b, a
        add(y, a, b, m.span())
    for m in R_MNDYY.finditer(t): add(y2(m.group(3)), MON[m.group(1)[:3].lower()], int(m.group(2)), m.span())
    for m in R_MNY.finditer(t): add(int(m.group(2)), MON[m.group(1)[:3].lower()], 0, m.span())
    for m in R_Y.finditer(t): add(int(m.group(1)), 0, 0, m.span())
    return out
def era(ds): return ds and ds[:4] <= '2004'
PR = {'d': 3, 'm': 2, 'y': 1, '': 0}
def best_date(text, latest=True):
    ds = [x for x in find_dates(text) if era(x[0])]
    if not ds: return None
    top = max(PR[p] for _, p in ds)
    c = sorted(set(d for d, p in ds if PR[p] == top))
    return (c[-1] if latest else c[0]), {3: 'd', 2: 'm', 1: 'y'}[top], len(c)
AIRW = re.compile(r'(?i)(aired|air ?date|airdate|airing|broadcast|recorded|taped|telecast|premiered|original(?:ly)? (?:air|shown|broadcast)|shown on|from)\b')
def desc_date(ds):
    t = re.sub(r'<[^>]+>', ' ', str(ds or ''))
    hit = None
    for m in AIRW.finditer(t):
        r = best_date(t[m.start():m.start() + 90])
        if r and (not hit or PR[r[1]] > PR[hit[1]]): hit = r
    return hit
R_SE = [re.compile(r'(?i)\bs(\d{1,2})[\s._-]*e(?:p)?(\d{1,3})\b'), re.compile(r'(?i)(?<![\dx])(\d{1,2})x(\d{2,3})(?!\d)'), re.compile(r'(?i)season\s*(\d{1,2})\D{0,12}?ep(?:isode)?\.?\s*#?(\d{1,3})')]
R_SEASON = re.compile(r'(?i)\b(?:season|series|s)\s*0?(\d{1,2})\b')
R_ABS = re.compile(r'(?i)(?:\bep(?:isode)?\.?\s*#?|#)(\d{1,4})\b')
def se_of(text):
    for rx in R_SE:
        m = rx.search(text)
        if m: return int(m.group(1)), int(m.group(2))
    return None
print('loading', flush=True)
SOURCES = {}
for p in sorted(glob.glob(os.path.join(CAT, '*.json.gz'))):
    b = os.path.basename(p)
    if b in OWN: continue
    j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
    if isinstance(j, list) and j and isinstance(j[0], dict) and 'i' in j[0]: SOURCES[b[:-8]] = j
ITEMS = {}
for sn in sorted(SOURCES, key=lambda s: s == 'raw'):
    for x in SOURCES[sn]:
        if x['i'] not in ITEMS:
            x['_s'] = sn; ITEMS[x['i']] = x
print('items', len(ITEMS), {k: len(v) for k, v in SOURCES.items()}, flush=True)
CATOF = {}
CJ = os.environ.get('CATJSON', '/tmp/catalog.json')
if os.path.exists(CJ):
    try:
        for k, v in json.load(open(CJ)).items():
            for r in v: CATOF[r[0]] = k
    except Exception: pass
print('categorized', len(CATOF), flush=True)
SHOWS = {}
def addshow(name, hint=0, net='', alias=()):
    k = norm(name)
    if len(k) < 3: return
    s = SHOWS.setdefault(k, {'name': name, 'hint': 0, 'net': '', 'n': 0, 'years': collections.Counter()})
    if hint and not s['hint']: s['hint'] = int(hint)
    if net and not s['net']: s['net'] = net
    for a in alias:
        ka = norm(a)
        if len(ka) >= 3 and ka != k: ALIAS.setdefault(ka, k)
ALIAS = {}
for fn in ('shows_primetime.json', 'shows_cable.json'):
    p = os.path.join(here, fn)
    if not os.path.exists(p): continue
    for s in json.load(open(p)):
        h = s.get('first') or 0
        if not h and s.get('original_run'):
            m = re.match(r'(\d{4})', str(s['original_run'])); h = int(m.group(1)) if m else 0
        try: h = int(str(h)[:4])
        except Exception: h = 0
        addshow(s['title'], h, s.get('net', ''), s.get('q') or ())
try:
    import series as SER
    for rx, y in SER.SERIES:
        for alt in rx.pattern.split('(', 2)[-1].rsplit(')', 1)[0].split('|'):
            a = re.sub(r'\\.|[?*+\[\]()^$]', '', alt).strip()
            nm = SER.CANON.get(a.lower())
            if nm: addshow(nm, y, '', [a])
            elif len(a) >= 5: addshow(a.title(), y)
except Exception as e:
    print('series import failed', e)
try:
    import titles as TI
    for k, v in TI.NAMES.items(): addshow(v, 0, '', [k])
except Exception as e:
    print('titles import failed', e)
PFX = collections.Counter()
PFXR = re.compile(r"(?i)^(.{4,48}?)[\s\-–:,.(\[]+(?:s\d{1,2}\s*e\d{1,3}|season\s*\d|series\s*\d|\d{1,2}x\d{2}|ep(?:isode)?\.?\s*#?\d)")
for x in ITEMS.values():
    m = PFXR.match(re.sub(r"^\W+", "", x.get('t') or ''))
    if m:
        nm = re.sub(r"(?i)\b(the complete|complete|full|tv series|tv show|vhs|dvd|rip)\b", " ", m.group(1))
        nm = re.sub(r"\s+", " ", nm).strip(" -–:,.([")
        if 4 <= len(nm) <= 44 and not re.search(r"\d{4}", nm): PFX[nm.lower()] += 1
ndyn = 0
for nm, n in PFX.items():
    if n >= 3 and norm(nm) not in SHOWS and norm(nm) not in ALIAS and len(norm(nm)) >= 5:
        addshow(nm.title()); ndyn += 1
print('dynamic show names', ndyn, flush=True)
GENERIC = {'era', 'classic', 'block', 'other', 'othertoon', 'nickcartoon', 'disneytoon', 'stories', 'wwf', 'wcw', 'ecw', 'awa', 'house show', 'cc', 'toonami', 'animefilm', '', 'news', 'movie', 'special', 'friends', 'lost', 'bob', 'action', 'ed', 'angel', 'coach', 'wings', 'ellen', 'cheers', 'taxi', 'hunter', 'soap', 'dallas', 'dynasty', 'martin', 'amen', 'alice', 'benson', 'webster', 'nova', 'nature', 'cops', 'heat', 'thunder', 'raw', 'nitro', 'smackdown', 'velocity', 'superstars'}
SHORT1 = set()
for k in list(SHOWS):
    if ' ' not in k and len(k) < 9: SHORT1.add(k)
for k in list(ALIAS):
    if ' ' not in k and len(k) < 9: SHORT1.add(k)
NAMEKEYS = sorted(set(list(SHOWS) + list(ALIAS)), key=len, reverse=True)
NRX = re.compile(r'(?<![a-z0-9])(' + '|'.join(re.escape(k) for k in NAMEKEYS) + r')(?![a-z0-9])')
JUNKF = re.compile(r'^(?:(?:vhs|tape|beta|dvd|recording|the|\d{1,4}|[wk][a-z]{2,3}(?: tv)?|abc|cbs|nbc|fox|pbs|hbo|tv)\s+)+')
def strong1(k0, title):
    pat = r"\s*".join(re.escape(w) for w in k0.split(' '))
    return re.search(r"(?i)^\W*(?:the\s+)?" + pat + r"\b['’s]*\s*(?:$|[-–:(\[|,.!?#]|s\d|season|series|ep\b|episode|\d|complete|vol|tv\b|show\b|full|on\b|the\b)", title) is not None
def show_of(x, ntitle):
    t = x.get('t') or ''
    for tag in (x.get('k'), x.get('q') if x['_s'] in ('musthave', 'toons') else None):
        if not tag: continue
        k = norm(tag); k = ALIAS.get(k, k)
        if k in SHOWS and k not in GENERIC and (k in ntitle or (x['_s'] in ('musthave', 'preschool', 'schoolage', 'games', 'toons') and len(k) >= 6)): return k
    core = JUNKF.sub('', ntitle)
    for m in NRX.finditer(ntitle):
        k0 = m.group(1); k = ALIAS.get(k0, k0)
        if ' ' not in k0 or len(k0) < 12 or k in GENERIC:
            if not core.startswith(k0): continue
            if ' ' not in k0 and not strong1(k0, re.sub(r'(?i)^\W*(vhs|tape|dvd)\W+', '', t)): continue
        return k
    return None
EVENTS = ['wrestlemania', 'summerslam', 'royal rumble', 'survivor series', 'king of the ring', 'in your house', 'backlash', 'judgment day', 'unforgiven', 'no mercy', 'armageddon', 'no way out', 'vengeance', 'bad blood', 'fully loaded', 'over the edge', 'rock bottom', 'invasion', 'starrcade', 'great american bash', 'bash at the beach', 'halloween havoc', 'superbrawl', 'slamboree', 'fall brawl', 'spring stampede', 'uncensored', 'road wild', 'hog wild', 'world war 3', 'souled out', 'mayhem', 'new blood rising', 'chi town rumble', 'wrestlewar', 'capital combat', 'beach blast', 'clash of the champions', 'battlebowl', 'barely legal', 'november to remember', 'heat wave', 'living dangerously', 'guilty as charged', 'anarchy rulz', 'hardcore heaven', 'cyberslam', 'wrestlepalooza', 'superclash', 'wrestlerock', 'saturday nights main event', 'the main event', 'the wrestling classic', 'this tuesday in texas', 'st valentines day massacre', 'bunkhouse stampede', 'crockett cup', 'sin', 'greed']
ROM = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23, 'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27, 'xxviii': 28, 'xxix': 29, 'xxx': 30, 'xxxi': 31, 'xxxii': 32, 'xxxiii': 33, 'xxxiv': 34, 'xxxv': 35}
EVD = {}
def wiki_events():
    pages = ['List of WWE pay-per-view and livestreaming supercards', 'List of WWE pay-per-view and WWE Network events', 'List of WCW pay-per-view events', 'List of NWA/WCW closed-circuit events and pay-per-view events', 'List of ECW supercards and pay-per-view events', 'Clash of the Champions', "List of Saturday Night's Main Event shows", "Saturday Night's Main Event", 'List of AWA supercards and pay-per-view events', 'List of WCW Clash of the Champions shows']
    for pg in pages:
        j = get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': pg, 'prop': 'wikitext', 'format': 'json', 'redirects': 1}), pause=1)
        wt = ((j or {}).get('parse') or {}).get('wikitext', {}).get('*', '')
        n = 0
        for row in re.split(r'\n\|-', wt):
            row2 = re.sub(r'\{\{dts\|(?:format=\w+\|)?(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}', lambda m: '%s-%s-%s' % (m.group(1), m.group(2), m.group(3)), row, flags=re.I)
            row2 = re.sub(r'\{\{dts\|([^}|]+)[^}]*\}\}', r'\1', row2, flags=re.I)
            ds = [d for d, p in find_dates(row2) if p == 'd']
            if not ds: continue
            for m in re.finditer(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row2):
                for nm in (m.group(1), m.group(2) or ''):
                    k = norm(re.sub(r'\(.*?\)', '', nm))
                    if not k or len(k) < 3: continue
                    for ev in EVENTS:
                        if k.startswith(ev) or k.startswith('wcw ' + ev) or k.startswith('nwa ' + ev) or k.startswith('wwf ' + ev):
                            rest = k.split(ev, 1)[1].strip().split(' ')[0] if ev in k else ''
                            num = ROM.get(rest) or (int(rest) if rest.isdigit() and len(rest) <= 2 else 0)
                            EVD.setdefault(ev, []).append((ds[0], num)); n += 1
                            break
                break
        print('wiki', pg, len(wt), n, flush=True)
    for ev in EVD: EVD[ev] = sorted(set(EVD[ev]))
def event_date(ntitle, year):
    for ev in EVENTS:
        i = ntitle.find(ev)
        if i < 0 or ev not in EVD: continue
        if ev in ('sin', 'greed', 'invasion', 'vengeance', 'mayhem', 'backlash') and not re.search(r'\b(wcw|wwf|wwe|ppv|pay per view)\b', ntitle): continue
        rest = ntitle[i + len(ev):].strip().split(' ')
        num = ROM.get(rest[0]) if rest and rest[0] else 0
        if not num and rest and rest[0].isdigit() and len(rest[0]) <= 2: num = int(rest[0])
        c = EVD[ev]
        if num:
            h = [d for d, n in c if n == num]
            if len(h) == 1 and (not year or abs(int(h[0][:4]) - year) <= 1): return h[0], ev
        if year:
            h = [d for d, n in c if int(d[:4]) == year]
            if len(h) == 1: return h[0], ev
    return None
print('pass 1', flush=True)
INFO = {}
for i, x in ITEMS.items():
    t = x.get('t') or ''
    nt = norm(t)
    sk = show_of(x, nt)
    a = best_date(t)
    post = sorted(d for d, p in find_dates(t) if p == 'd' and d[:4] > '2004' and d[:4] <= '2026')
    ai = None
    if not a or a[1] != 'd':
        ai = best_date(re.sub(r'[_]', '-', i))
        if ai and ai[1] != 'd': ai = None
    ys = [int(d[:4]) for d, p in find_dates(t) if era(d)]
    if x.get('e'):
        try: ys.append(int(x['e']))
        except Exception: pass
    INFO[i] = {'nt': nt, 'show': sk, 'a': a, 'ai': ai, 'ys': ys, 'post': post[0] if post and not (a and a[1] == 'd') else ''}
    if sk:
        SHOWS[sk]['n'] += 1
        for y in ys: SHOWS[sk]['years'][y] += 1
need = [k for k, s in SHOWS.items() if s['n'] > 0]
need.sort(key=lambda k: -SHOWS[k]['n'])
print('shows referenced', len(need), 'top', [(SHOWS[k]['name'], SHOWS[k]['n']) for k in need[:25]], flush=True)
EPG = load('epguide.json.gz') or {}
def pick_show(k):
    s = SHOWS[k]
    j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(s['name']), pause=0.55)
    best = None
    yrs = s['years']
    for r in j or []:
        sh = r.get('show') or {}
        nk = norm(sh.get('name', ''))
        pm = sh.get('premiered') or ''
        if not pm or pm[:4] > '2004': continue
        net = sh.get('network') or sh.get('webChannel') or {}
        cc = ((net.get('country') or {}).get('code')) or ''
        sc = 0
        if nk == k: sc += 4
        elif nk.startswith(k + ' ') or k.startswith(nk + ' '): sc += 1.5
        else: continue
        if cc == 'US': sc += 2
        elif cc in ('CA', 'GB', 'JP') : sc += 0.3
        py = int(pm[:4]); ey = int((sh.get('ended') or '2030')[:4])
        if s['hint']:
            dh = abs(py - s['hint'])
            sc += 2 if dh <= 1 else 0.5 if dh <= 3 else -2
        if yrs:
            tot = sum(yrs.values()); inr = sum(n for y, n in yrs.items() if py - 1 <= y)
            sc += 1.5 * inr / tot
            if not s['hint']:
                run = sum(n for y, n in yrs.items() if py - 1 <= y <= ey + 1)
                sc += 1.5 * run / tot
        sc += min(1, (r.get('score') or 0) / 20)
        if not best or sc > best[0]: best = (sc, sh)
    if not best or best[0] < 5: return {'miss': 1, 'name': s['name']}
    sh = best[1]
    eps = get('https://api.tvmaze.com/shows/%d/episodes?specials=1' % sh['id'], pause=0.55) or []
    net = sh.get('network') or sh.get('webChannel') or {}
    return {'title': sh.get('name'), 'id': sh['id'], 'premiered': sh.get('premiered'), 'ended': sh.get('ended'), 'network': net.get('name', ''), 'country': ((net.get('country') or {}).get('code')) or '', 'episodes': [[e.get('season') or 0, e.get('number') or 0, e.get('airdate') or '', e.get('name') or ''] for e in eps]}
todo = [k for k in need if k not in EPG]
print('guides cached', len(need) - len(todo), 'to fetch', len(todo), flush=True)
for n, k in enumerate(todo):
    if left() < BUDGET * 0.45: print('guide budget reached at', n, flush=True); break
    EPG[k] = pick_show(k)
    if n % 100 == 0: print('guide', n, k, 'miss' if EPG[k].get('miss') else len(EPG[k]['episodes']), flush=True)
    if n and n % 400 == 0: save('epguide.json.gz', EPG)
save('epguide.json.gz', EPG)
wiki_events()
print('events', {k: len(v) for k, v in EVD.items()}, flush=True)
GIDX = {}
def gidx(k):
    if k in GIDX: return GIDX[k]
    g = EPG.get(k)
    if not g or g.get('miss'): GIDX[k] = None; return None
    by = {}; names = collections.defaultdict(list); order = []; seas = {}
    for s, n, d, nm in g['episodes']:
        if not d: continue
        if n:
            by[(s, n)] = (d, nm); order.append((d, s, n, nm))
            if s not in seas or d < seas[s]: seas[s] = d
        nk = norm(nm)
        if len(nk) >= 9 or (len(nk) >= 6 and ' ' in nk): names[nk].append((d, s, n, nm))
    order.sort()
    uniq = {nk: v[0] for nk, v in names.items() if len(v) == 1 and nk != k and not re.match(r'^(episode|part|pilot|show) ?\d*$', nk)}
    rx = re.compile(r'(?<![a-z0-9])(' + '|'.join(re.escape(x) for x in sorted(uniq, key=len, reverse=True)) + r')(?![a-z0-9])') if uniq else None
    GIDX[k] = {'by': by, 'order': order, 'seas': seas, 'uniq': uniq, 'rx': rx, 'prem': g.get('premiered') or '', 'n': len(order)}
    return GIDX[k]
def ep_match(g, text, ntext, allow_abs=True):
    se = se_of(text)
    if se and se in g['by']:
        d, nm = g['by'][se]; return d, list(se), nm, 'episode', 0.9
    if g['rx']:
        m = g['rx'].search(ntext)
        if m:
            d, s, n, nm = g['uniq'][m.group(1)]; return d, [s, n], nm, 'episode-title', 0.85
    if allow_abs and g['n'] <= 700 and not se:
        m = R_ABS.search(text)
        if m:
            a = int(m.group(1))
            if 1 <= a <= g['n']:
                d, s, n, nm = g['order'][a - 1]; return d, [s, n], nm, 'episode-abs', 0.6
    return None
FILMCAT = {'movie'}
def clean_film(t):
    s = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', t)
    s = re.sub(r'(?i)\b(vhs|dvd|rip|vhsrip|dvdrip|full movie|full film|tv movie|woc|with commercials|w/ ?commercials|recording|broadcast|airing|widescreen|fullscreen|uncut|theatrical|remaster(ed)?|hd|720p|1080p|480p|complete|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b', ' ', s)
    s = re.sub(r'(?i)\b(abc|cbs|nbc|fox|hbo|tbs|tnt|usa|upn|wb|amc|cinemax|showtime|sci-?fi channel|comedy central|lifetime)\b.*$', ' ', s)
    s = re.sub(YR, ' ', s)
    return re.sub(r'\s+', ' ', s).strip(' -–:,.')
FTYPES = {'Q11424', 'Q24862', 'Q506240', 'Q202866', 'Q24869', 'Q229390', 'Q20650540', 'Q17517379', 'Q29168811', 'Q1259759', 'Q336144'}
def film_lookup(args):
    i, title, year = args
    if left() < BUDGET * 0.12: return i, None
    q = clean_film(title)
    if len(q) < 3: return i, None
    j = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbsearchentities', 'search': q, 'language': 'en', 'type': 'item', 'limit': 6, 'format': 'json'}), tries=3)
    ids = [r['id'] for r in (j or {}).get('search', []) if norm(r.get('label', '')) == norm(q)]
    if not ids: return i, None
    j = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(ids[:5]), 'props': 'claims', 'format': 'json'}), tries=3)
    best = None
    for qid in ids[:5]:
        cl = (((j or {}).get('entities') or {}).get(qid) or {}).get('claims') or {}
        ty = set()
        for c in cl.get('P31', []):
            try: ty.add(c['mainsnak']['datavalue']['value']['id'])
            except Exception: pass
        if not (ty & FTYPES): continue
        ds = []
        for c in cl.get('P577', []):
            try:
                v = c['mainsnak']['datavalue']['value']; tm = v['time']; pr = v.get('precision', 9)
                y = int(tm[1:5]); mo = int(tm[6:8]); d = int(tm[9:11])
                ds.append((fmt(y, mo if pr >= 10 and mo else 0, d if pr >= 11 and d else 0)))
            except Exception: pass
        if not ds: continue
        d0 = min(ds)
        if d0[:4] > '2004': continue
        sc = 0 if not year else abs(int(d0[:4]) - year)
        if year and int(d0[:4]) > year + 1: continue
        if best is None or sc < best[0]: best = (sc, d0, qid)
    return i, (best[1], best[2]) if best else None
print('pass 2', flush=True)
OUT = {}
films = []
def prec(d): return 'd' if len(d) == 10 else 'm' if len(d) == 7 else 'y'
for i, x in ITEMS.items():
    inf = INFO[i]; t = x.get('t') or ''; nt = inf['nt']; sk = inf['show']
    cat = CATOF.get(i) or (x.get('q') if x.get('q') in ('kids', 'game', 'wrest', 'prime', 'news', 'soap', 'talk', 'movie') else '') or x['_s']
    rec = {'d': '', 'p': '', 'src': 'none', 'show': SHOWS[sk]['name'] if sk else '', 'se': None, 'conf': 0, 'cat': cat}
    a = inf['a']; ai = inf['ai']; A = None
    if x.get('ad') and re.match(r'^\d{4}-\d{2}-\d{2}$', str(x['ad'])) and era(x['ad']): A = (x['ad'], 'd', 'title', 0.9)
    elif a and a[1] == 'd': A = (a[0], 'd', 'title-range' if a[2] > 1 else 'title', 0.75 if a[2] > 1 else 0.95)
    elif ai: A = (ai[0], 'd', 'ident', 0.85)
    B = None
    if not A:
        b = desc_date(x.get('ds'))
        if b and b[1] in ('d', 'm'): B = (b[0], b[1], 'desc', 0.8 if b[1] == 'd' else 0.6)
    md = str(x.get('d') or '')
    M = None
    mm = re.match(r'^(\d{4})-(\d{2})-(\d{2})', md)
    if mm and era(md) and md[:4] >= '1930' and not (mm.group(2) == '01' and mm.group(3) == '01'): M = (md[:10], 'd', 'meta', 0.6)
    elif re.match(r'^\d{4}-\d{2}$', md) and era(md): M = (md[:7], 'm', 'meta', 0.5)
    g = gidx(sk) if sk else None
    fl = x.get('f') or []
    multi = len(fl) > 1
    C = None; files = {}
    if g:
        C = ep_match(g, t, nt)
        if multi or not C:
            for f in fl[:60]:
                base = re.sub(r'\.(ia\.)?mp4$', '', f[0].rsplit('/', 1)[-1])
                r = ep_match(g, base, norm(base), allow_abs=multi)
                if r: files[f[0]] = {'d': r[0], 'p': 'd', 'se': r[1], 'ep': r[2], 'src': r[3]}
            if not C and len(fl) == 1 and files:
                r = list(files.values())[0]; C = (r['d'], r['se'], r['ep'], r['src'], 0.85); files = {}
    for f in fl[:60]:
        if f[0] in files: continue
        fd = best_date(re.sub(r'\.(ia\.)?mp4$', '', f[0].rsplit('/', 1)[-1]))
        if fd and fd[1] == 'd' and multi: files[f[0]] = {'d': fd[0], 'p': 'd', 'src': 'file-title'}
    if A:
        rec.update(d=A[0], p=A[1], src=A[2], conf=A[3])
        if C:
            rec['se'] = C[1]; rec['ep'] = C[2]
            if C[0] != A[0]:
                if C[0] < A[0]: rec['orig'] = C[0]
                else:
                    try: gap = (time.mktime(time.strptime(C[0], '%Y-%m-%d')) - time.mktime(time.strptime(A[0], '%Y-%m-%d'))) / 86400
                    except Exception: gap = 999
                    if gap > 7: rec['alt'] = {'d': C[0], 'src': C[3]}; rec['conf'] = min(rec['conf'], 0.5)
    elif C and not (multi and len(files) > 1):
        rec.update(d=C[0], p='d', src=C[3], se=C[1], ep=C[2], conf=C[4])
        if B and B[1] == 'd' and B[0] > C[0]: rec['orig'] = C[0]; rec.update(d=B[0], src='desc', conf=0.8)
    elif B and not (multi and len(files) > 1):
        rec.update(d=B[0], p=B[1], src=B[2], conf=B[3])
    elif multi and len(files) > 1:
        fds = sorted(v['d'] for v in files.values())
        rec.update(d=fds[0], p='d', src='files', conf=0.8, dmax=fds[-1], nf=len(files), of=len(fl))
    else:
        ev = event_date(nt, (inf['ys'] or [0])[0]) if (cat == 'wrest' or x['_s'] == 'wrestling' or re.search(r'\b(wwf|wwe|wcw|ecw|nwa|awa|wrestl)', nt)) else None
        if ev: rec.update(d=ev[0], p='d', src='event', conf=0.85, show=ev[1].upper())
        elif M and M[1] == 'd' and not (g and g['prem'] and M[0] < g['prem']): rec.update(d=M[0], p=M[1], src=M[2], conf=M[3])
        elif g:
            sm = R_SEASON.search(t)
            sn = int(sm.group(1)) if sm else 0
            if sn and sn in g['seas']: rec.update(d=g['seas'][sn], p='d', src='season', conf=0.6, se=[sn, 0])
            elif a and a[1] in ('m', 'y') and (not g['prem'] or a[0][:4] >= g['prem'][:4]): rec.update(d=a[0], p=a[1], src='title', conf=0.7)
            elif g['prem']: rec.update(d=g['prem'], p='d', src='series', conf=0.5)
        if not rec['d']:
            if a: rec.update(d=a[0], p=a[1], src='title', conf=0.7 if a[1] == 'm' else 0.55)
            elif B: rec.update(d=B[0], p=B[1], src='desc', conf=0.5)
            elif M: rec.update(d=M[0], p=M[1], src='meta', conf=M[3])
            elif sk and SHOWS[sk]['hint'] and SHOWS[sk]['hint'] <= 2004: rec.update(d=str(SHOWS[sk]['hint']), p='y', src='series-hint', conf=0.4)
            elif x.get('e') and str(x['e']).isdigit() and 1930 <= int(x['e']) <= 2004: rec.update(d=str(x['e']), p='y', src='year', conf=0.4)
            elif re.match(r'^\d{4}', md) and era(md) and md[:4] >= '1930': rec.update(d=md[:4], p='y', src='meta', conf=0.35)
            elif str(x.get('y') or '').isdigit() and 1930 <= int(x['y']) <= 2004: rec.update(d=str(x['y']), p='y', src='year', conf=0.3)
    if inf['post'] and rec['p'] != 'd' and x['_s'] in ('raw', 'primetime', 'cable') and re.search(r'(?i)\b(news|tonight|show|live|report|today|morning|late|daily|week)\b', t):
        rec['alt'] = {'d': rec['d'], 'src': rec['src']}; rec.update(d=inf['post'], p='d', src='title-post', conf=0.7)
    if files and (multi or rec['src'] in ('files',)): rec['files'] = files
    if g and rec['d'] and g['prem'] and rec['p'] != 'd' and rec['d'][:4] < g['prem'][:4] and rec['src'] not in ('series',):
        rec['alt'] = {'d': rec['d'], 'src': rec['src']}; rec.update(d=g['prem'], p='d', src='series', conf=0.5)
    if cat in FILMCAT and not sk and len(fl) <= 3:
        films.append((i, t, int(rec['d'][:4]) if rec['d'] else 0))
    OUT[i] = rec
print('films to look up', len(films), 'time left min', round(left() / 60), flush=True)
fres = {}
if films and left() > BUDGET * 0.15:
    with ThreadPoolExecutor(5) as ex:
        for n, (i, r) in enumerate(ex.map(film_lookup, films)):
            if r: fres[i] = r
            if n % 500 == 0: print('film', n, len(fres), flush=True)
for i, (d, qid) in fres.items():
    rec = OUT[i]
    rec['rel'] = d; rec['wd'] = qid
    if not rec['d'] or rec['src'] in ('year', 'meta', 'series-hint') and rec['p'] == 'y' and d[:4] <= rec['d'][:4]:
        if not rec['d'] or d[:4] == rec['d'][:4]: rec.update(d=d, p=prec(d), src='film', conf=0.75)
    elif rec['d'] and rec['d'] < d[:len(rec['d'])]:
        rec['alt'] = {'d': rec['d'], 'src': rec['src']}; rec.update(d=d, p=prec(d), src='film', conf=0.5)
for i, rec in OUT.items():
    if not rec.get('se'): rec.pop('se', None)
save('dates.json.gz', OUT)
print('dates written', len(OUT), flush=True)
ADS = load('ads.json.gz') or []
FIL = load('filler.json.gz') or []
AD = {}
need_meta = []
for r in ADS:
    i, f, secs, d, title = r[:5]
    a = best_date(title, latest=False) or best_date(re.sub(r'\.(ia\.)?mp4$', '', str(f)), latest=False)
    md = str(d or '')
    if a and a[1] == 'd': AD[i] = {'d': a[0], 'p': 'd', 'src': 'title'}
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', md) and era(md) and md[:4] >= '1930' and md[5:] != '01-01': AD[i] = {'d': md, 'p': 'd', 'src': 'meta'}
    elif a and a[1] == 'm': AD[i] = {'d': a[0], 'p': 'm', 'src': 'title'}
    else:
        AD[i] = {'d': a[0], 'p': 'y', 'src': 'title'} if a else ({'d': md[:4], 'p': 'y', 'src': 'meta'} if re.match(r'^\d{4}', md) and era(md) and md[:4] >= '1930' else {'d': '', 'p': '', 'src': 'none'})
        need_meta.append(i)
def ad_meta(i):
    if left() < 240: return i, None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(i) + '/metadata', tries=3)
    m = (j or {}).get('result') or {}
    ds = m.get('description', '')
    if isinstance(ds, list): ds = ' '.join(ds)
    txt = re.sub(r'<[^>]+>', ' ', str(ds))
    r = desc_date(txt)
    if not r:
        r2 = best_date(txt[:300])
        if r2 and r2[1] in ('d', 'm') and r2[2] == 1: r = r2
    return i, r
print('ads', len(ADS), 'need description', len(need_meta), 'time left min', round(left() / 60), flush=True)
if need_meta and left() > 600:
    with ThreadPoolExecutor(14) as ex:
        for n, (i, r) in enumerate(ex.map(ad_meta, need_meta)):
            if r and PR[r[1]] > PR[AD[i]['p']] and (not AD[i]['d'] or r[0][:4] == AD[i]['d'][:4] or AD[i]['src'] == 'meta'):
                AD[i] = {'d': r[0], 'p': r[1], 'src': 'desc'}
            if n % 1000 == 0: print('admeta', n, flush=True)
for x in FIL:
    i = x['i']
    if i in AD and AD[i]['p'] == 'd': continue
    a = best_date(x.get('t') or '', latest=False)
    b = desc_date(x.get('ds'))
    md = str(x.get('d') or '')
    c = None
    if a and a[1] == 'd': c = {'d': a[0], 'p': 'd', 'src': 'title'}
    elif b and b[1] == 'd': c = {'d': b[0], 'p': 'd', 'src': 'desc'}
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', md) and era(md) and md[:4] >= '1930' and md[5:] != '01-01': c = {'d': md, 'p': 'd', 'src': 'meta'}
    elif a: c = {'d': a[0], 'p': a[1], 'src': 'title'}
    elif b: c = {'d': b[0], 'p': b[1], 'src': 'desc'}
    elif re.match(r'^\d{4}', md) and era(md) and md[:4] >= '1930': c = {'d': md[:4], 'p': 'y', 'src': 'meta'}
    else: c = {'d': '', 'p': '', 'src': 'none'}
    fd = {}
    for f in (x.get('f') or [])[:60]:
        r = best_date(re.sub(r'\.(ia\.)?mp4$', '', f[0]), latest=False)
        if r and len(x['f']) > 1: fd[f[0]] = {'d': r[0], 'p': r[1]}
    if fd: c['files'] = fd
    if i not in AD or PR[c['p']] > PR[AD[i]['p']]: AD[i] = c
save('adsdates.json.gz', AD)
print('adsdates written', len(AD), flush=True)
def table(name, rows, key):
    tb = collections.defaultdict(collections.Counter)
    for r in rows: tb[key(r)][r['p'] or 'none'] += 1
    print('== ' + name)
    for k in sorted(tb, key=lambda k: -sum(tb[k].values())):
        c = tb[k]; tot = sum(c.values())
        print('  %-14s total %6d  day %6d (%3d%%)  month %5d  year %6d  none %5d' % (str(k)[:14], tot, c['d'], 100 * c['d'] // max(1, tot), c['m'], c['y'], c['none']))
vals = list(OUT.values())
for i, r in OUT.items(): r['_f'] = ITEMS[i]['_s']
table('by source file', vals, lambda r: r['_f'])
table('by category', vals, lambda r: r['cat'])
table('by src', vals, lambda r: r['src'])
ser = [r for r in vals if r['cat'] in ('prime', 'kids', 'rerun', 'soap', 'game', 'talk', 'late')]
dd = sum(1 for r in ser if r['p'] == 'd')
print('series-category day precision: %d of %d (%d%%)' % (dd, len(ser), 100 * dd // max(1, len(ser))))
ddx = sum(1 for r in ser if r['p'] == 'd' and r['src'] not in ('series', 'season'))
print('  of which exact (not series/season bound): %d (%d%%)' % (ddx, 100 * ddx // max(1, len(ser))))
table('commercials and filler', list(AD.values()), lambda r: r['src'])
miss = collections.Counter()
for i, r in OUT.items():
    sk = INFO[i]['show']
    if sk and (EPG.get(sk) or {}).get('miss'): miss[SHOWS[sk]['name']] += 1
print('== series without a guide (top 100):', miss.most_common(100))
nos = collections.Counter(re.sub(r'[^a-z ]', '', INFO[i]['nt'])[:22] for i, r in OUT.items() if not INFO[i]['show'] and r['cat'] in ('prime', 'kids', 'rerun', 'soap', 'game', 'talk', 'late') and r['p'] != 'd')
print('== unidentified series-category titles lacking day dates (top 60):', nos.most_common(60))
print('guides', sum(1 for v in EPG.values() if not v.get('miss')), 'misses', sum(1 for v in EPG.values() if v.get('miss')))
random.seed(7)
print('== samples')
for i in random.sample(list(OUT), min(90, len(OUT))):
    r = OUT[i]
    print('  [%s/%s] %s -> %s %s conf=%s show=%s%s%s' % (r['_f'], r['cat'], (ITEMS[i].get('t') or '')[:70], r['d'] or '-', r['src'], r['conf'], r['show'][:24], ' se=%s' % r['se'] if r.get('se') else '', ' files=%d' % len(r['files']) if r.get('files') else ''))
print('== ad samples')
for i in random.sample(list(AD), min(25, len(AD))): print('  ', i[:50], AD[i].get('d'), AD[i].get('src'))
