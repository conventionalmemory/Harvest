import json, gzip, os, re, sys, time, random, glob, collections, datetime, threading, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
here = os.path.dirname(os.path.abspath(__file__))
D = {'__file__': os.path.join(here, 'dated.py')}
exec(compile(open(os.path.join(here, 'dated.py'), encoding='utf-8').read().split("\nif MODE == 'plan':")[0], 'dated_head', 'exec'), D)
norm, get, scrape, S, XCOL, ok_title, sport, find_date, netof, X_FOR = (D[k] for k in ('norm', 'get', 'scrape', 'S', 'XCOL', 'ok_title', 'sport', 'find_date', 'netof', 'X_FOR'))
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RXT, RXC, FIGHT, ERA, YR, MON = D['RXT'], D['RXC'], D['FIGHT'], D['ERA'], D['YR'], D['MON']
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
REBUILD = os.environ.get('REBUILD', '') == '1'
T0 = time.time()
OUTF = os.path.join(OUT, 'sports2.json.gz'); SCHF = os.path.join(OUT, 'sportsched.json.gz'); NOPG = os.path.join(OUT, 'sportsched_nopages.json'); PGF = os.path.join(OUT, 'sportsched_pages.json.gz')
WUA = {'User-Agent': 'sports schedule table builder (github.com/conventionalmemory/harvest)'}
ALIAS = {'niners': '49ers', 'bucs': 'buccaneers', 'cavs': 'cavaliers', 'sixers': '76ers', 'mavs': 'mavericks', 'sonics': 'supersonics', 'blazers': 'trail blazers', 'pitt': 'pittsburgh', 'unc': 'north carolina', 'north carolina state': 'nc state', 'connecticut': 'uconn', 'memphis state': 'memphis'}
def canon(x): return ALIAS.get(x, x)
CITY = {
 'nfl': {'arizona': 'cardinals', 'phoenix': 'cardinals', 'st louis': [('cardinals', 1984, 1987), ('rams', 1995, 2004)], 'atlanta': 'falcons', 'baltimore': 'ravens', 'buffalo': 'bills', 'carolina': 'panthers', 'chicago': 'bears', 'cincinnati': 'bengals', 'cleveland': 'browns', 'dallas': 'cowboys', 'denver': 'broncos', 'detroit': 'lions', 'green bay': 'packers', 'houston': [('oilers', 1984, 1996), ('texans', 2002, 2004)], 'tennessee': [('oilers', 1997, 1998), ('titans', 1999, 2004)], 'indianapolis': 'colts', 'jacksonville': 'jaguars', 'kansas city': 'chiefs', 'los angeles': [('raiders', 1984, 1994), ('rams', 1984, 1994)], 'la': [('raiders', 1984, 1994), ('rams', 1984, 1994)], 'oakland': 'raiders', 'miami': 'dolphins', 'minnesota': 'vikings', 'new england': 'patriots', 'new orleans': 'saints', 'new york': [('giants', 1984, 2004), ('jets', 1984, 2004)], 'ny giants': 'giants', 'ny jets': 'jets', 'philadelphia': 'eagles', 'pittsburgh': 'steelers', 'san diego': 'chargers', 'san francisco': '49ers', 'seattle': 'seahawks', 'tampa bay': 'buccaneers', 'tampa': 'buccaneers', 'washington': 'redskins'},
 'mlb': {'anaheim': 'angels', 'california': 'angels', 'houston': 'astros', 'oakland': 'athletics', 'toronto': 'blue jays', 'atlanta': 'braves', 'milwaukee': 'brewers', 'st louis': 'cardinals', 'arizona': 'diamondbacks', 'montreal': 'expos', 'san francisco': 'giants', 'cleveland': 'indians', 'seattle': 'mariners', 'florida': 'marlins', 'baltimore': 'orioles', 'san diego': 'padres', 'philadelphia': 'phillies', 'pittsburgh': 'pirates', 'texas': 'rangers', 'cincinnati': 'reds', 'boston': 'red sox', 'colorado': 'rockies', 'kansas city': 'royals', 'detroit': 'tigers', 'minnesota': 'twins', 'tampa bay': 'devil rays', 'new york': [('yankees', 1984, 2004), ('mets', 1984, 2004)], 'ny yankees': 'yankees', 'ny mets': 'mets', 'chicago': [('cubs', 1984, 2004), ('white sox', 1984, 2004)], 'chicago cubs': 'cubs', 'los angeles': 'dodgers', 'la dodgers': 'dodgers'},
 'nba': {'boston': 'celtics', 'chicago': 'bulls', 'cleveland': 'cavaliers', 'dallas': 'mavericks', 'denver': 'nuggets', 'detroit': 'pistons', 'golden state': 'warriors', 'houston': 'rockets', 'indiana': 'pacers', 'los angeles': [('lakers', 1984, 2004), ('clippers', 1985, 2004)], 'la lakers': 'lakers', 'la clippers': 'clippers', 'miami': 'heat', 'milwaukee': 'bucks', 'minnesota': 'timberwolves', 'new jersey': 'nets', 'new york': 'knicks', 'orlando': 'magic', 'philadelphia': '76ers', 'phoenix': 'suns', 'portland': 'trail blazers', 'trailblazers': 'trail blazers', 'sacramento': 'kings', 'san antonio': 'spurs', 'seattle': 'supersonics', 'toronto': 'raptors', 'utah': 'jazz', 'washington': [('bullets', 1984, 1997), ('wizards', 1998, 2004)], 'atlanta': 'hawks', 'charlotte': 'hornets', 'vancouver': 'grizzlies', 'memphis': 'grizzlies', 'new orleans': 'hornets'},
}
ABBR = {
 'nfl': {'ari': 'cardinals', 'phx': 'cardinals', 'atl': 'falcons', 'bal': 'ravens', 'buf': 'bills', 'car': 'panthers', 'chi': 'bears', 'cin': 'bengals', 'cle': 'browns', 'dal': 'cowboys', 'den': 'broncos', 'det': 'lions', 'gb': 'packers', 'ind': 'colts', 'jax': 'jaguars', 'jac': 'jaguars', 'kc': 'chiefs', 'oak': 'raiders', 'mia': 'dolphins', 'min': 'vikings', 'ne': 'patriots', 'no': 'saints', 'nyg': 'giants', 'nyj': 'jets', 'phi': 'eagles', 'pit': 'steelers', 'sd': 'chargers', 'sf': '49ers', 'sea': 'seahawks', 'tb': 'buccaneers', 'was': 'redskins', 'wsh': 'redskins', 'stl': 'rams', 'ten': 'titans'},
 'mlb': {'nyy': 'yankees', 'nym': 'mets', 'bos': 'red sox', 'atl': 'braves', 'cle': 'indians', 'stl': 'cardinals', 'ari': 'diamondbacks', 'sf': 'giants', 'hou': 'astros', 'sd': 'padres', 'sea': 'mariners', 'oak': 'athletics', 'min': 'twins', 'ana': 'angels', 'cal': 'angels', 'tex': 'rangers', 'bal': 'orioles', 'chc': 'cubs', 'chw': 'white sox', 'cws': 'white sox', 'lad': 'dodgers', 'la': 'dodgers', 'fla': 'marlins', 'cin': 'reds', 'pit': 'pirates', 'phi': 'phillies', 'mon': 'expos', 'col': 'rockies', 'mil': 'brewers', 'det': 'tigers', 'kc': 'royals', 'tor': 'blue jays', 'tb': 'devil rays'},
 'nba': {'bos': 'celtics', 'chi': 'bulls', 'cle': 'cavaliers', 'dal': 'mavericks', 'den': 'nuggets', 'det': 'pistons', 'gsw': 'warriors', 'hou': 'rockets', 'ind': 'pacers', 'lal': 'lakers', 'lac': 'clippers', 'mia': 'heat', 'mil': 'bucks', 'min': 'timberwolves', 'njn': 'nets', 'nj': 'nets', 'nyk': 'knicks', 'ny': 'knicks', 'orl': 'magic', 'phi': '76ers', 'phx': 'suns', 'pho': 'suns', 'por': 'trail blazers', 'sac': 'kings', 'sas': 'spurs', 'sa': 'spurs', 'sea': 'supersonics', 'tor': 'raptors', 'uta': 'jazz', 'utah': 'jazz', 'was': 'bullets', 'atl': 'hawks', 'cha': 'hornets'},
}
def tfind2(lg, nt, ys=()):
    rx = RXC if lg in ('ncaaf', 'ncaab') else RXT.get(lg)
    found = [(m.start(), [canon(m.group(1))]) for m in (rx.finditer(nt) if rx else [])]
    starts = set(p for p, a in found)
    for city, v in CITY.get(lg, {}).items():
        for m in re.finditer(' ' + city + '(?= )', nt):
            if m.end() in starts or any(p < m.end() and m.start() < p + len(a[0]) for p, a in found): continue
            alts = [v] if isinstance(v, str) else [n for n, a, z in v if not ys or any(a - 1 <= y <= z + 1 for y in ys)]
            if alts: found.append((m.start(), alts))
    if lg == 'mlb':
        m = re.search(r' (?:at|vs|@) (as) | (as) (?:at|vs|@) ', nt)
        if m: found.append((m.start(1) if m.group(1) else m.start(2), ['athletics']))
    if lg in ABBR:
        m = re.search(r' ([a-z]{2,4}) (?:@|at|vs) ([a-z]{2,4}) ', nt)
        if m and m.group(1) in ABBR[lg] and m.group(2) in ABBR[lg]: found += [(m.start(1), [ABBR[lg][m.group(1)]]), (m.start(2), [ABBR[lg][m.group(2)]])]
    found.sort(key=lambda x: (x[0], -len(x[1]))); out = []
    for p, a in found:
        if any(set(a) & set(o) for o in out): continue
        out.append(a)
    return out
def tfind(lg, nt):
    rx = RXC if lg in ('ncaaf', 'ncaab') else RXT.get(lg)
    out = []
    for m in (rx.findall(nt) if rx else []):
        c = canon(m)
        if c not in out: out.append(c)
    return out
MONS = 'january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec'
RD1 = re.compile(r'\b(' + MONS + r')\.?\s+(\d{1,2})(?:\s*[–-]\s*\d{1,2})?(?:,?\s+((?:19|20)\d\d))?', re.I)
RD2 = re.compile(r'\b(\d{1,2})\s+(' + MONS + r')\.?(?:\s+((?:19|20)\d\d))?', re.I)
RD3 = re.compile(r'(?<!\d)((?:19|20)\d\d)-(\d\d)-(\d\d)(?!\d)')
def iso(y, m, d):
    try: return datetime.date(int(y), int(m), int(d)).isoformat()
    except Exception: return None
TZO = {'e': 0, 'c': 1, 'm': 2, 'p': 3}
RTM = re.compile(r'(?<![\d:])(\d{1,2})(?::(\d\d))?\s*([ap])\.?\s?m\.?,?\s*\(?([ecmp])[sd]?t\b', re.I)
RTM0 = re.compile(r'(?<![\d:])(\d{1,2})(?::(\d\d))?\s*([ap])\.?\s?m\b', re.I)
def ptime(text, dz=None):
    m = RTM.search(text); z = m.group(4).lower() if m else dz
    if not m: m = RTM0.search(text)
    if not m or not z or not (0 < int(m.group(1)) <= 12) or int(m.group(2) or 0) > 59: return ''
    h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == 'p' else 0) + TZO[z]
    return '%02d:%02d' % (h % 24, int(m.group(2) or 0))
NETS = r'\b(abc|cbs|nbc|fox|espn2|espn|tnt|tbs|tnn|usa|upn|fx|speedvision|speed)\b'
def pnet(text):
    m = re.search(NETS, text.lower())
    return {'espn2': 'espn', 'speedvision': 'speed'}.get(m.group(1), m.group(1)) if m else ''
def etime(text):
    st = ptime(text)
    if st: return st
    m = re.search(r'(?<![\d:])(\d{1,2}):(\d\d)\s*([ap])?\.?\s?(?:m\b\.?)?', text, re.I)
    if not m or not (0 < int(m.group(1)) <= 12) or int(m.group(2)) > 59: return ''
    h = int(m.group(1)) % 12 + (0 if (m.group(3) or 'p').lower() == 'a' else 12)
    return '%02d:%02d' % (h, int(m.group(2)))
def tvgames(cell):
    out = []; t = cell.lower(); ms = list(re.finditer(NETS, t))
    for n, m in enumerate(ms):
        net = {'espn2': 'espn', 'speedvision': 'speed'}.get(m.group(1), m.group(1))
        seg = t[m.end():ms[n + 1].start() if n + 1 < len(ms) else m.end() + 40]
        g = None; pm = re.match(r'\s*\(([^)]*)\)', seg)
        if pm and 'game' in pm.group(1):
            g = set()
            for a, b in re.findall(r'(\d)(?:\s*[–-]\s*(\d))?', pm.group(1)):
                g |= set(range(int(a), int(b or a) + 1))
        elif pm and not re.search(r'united states|u\.s\.|usa|national|english', pm.group(1)): continue
        out.append((net, g))
    return out
def prune(blocks):
    out = []
    for b in blocks:
        if b[0] == 'h': out.append(['h', b[1], b[2][:120]])
        elif b[0] == 'row':
            if len(b[1]) > 16: continue
            cells = [c[:110 if len(b[1]) > 1 else 320] for c in b[1]]
            if sum(len(c) for c in cells) > 700: continue
            out.append(['row', cells, b[2], b[3]])
        elif len(b[1]) <= 320 or RD1.search(b[1][:320]) or RTM0.search(b[1][:320]):
            t = b[1][:320]
            if RD1.search(t) or RD2.search(t) or RD3.search(t) or RTM0.search(t) or re.search(NETS, t.lower()): out.append(['p', t])
    return out
def pdate(text, yfn=None):
    m = RD3.search(text)
    if m: return iso(m.group(1), m.group(2), m.group(3))
    m = re.search(r'(?<![\d/])(\d{1,2})/(\d{1,2})/((?:19|20)\d\d)(?!\d)', text)
    if m: return iso(m.group(3), m.group(1), m.group(2))
    for rx, mi, di in ((RD1, 1, 2), (RD2, 2, 1)):
        m = rx.search(text)
        if m:
            mo = MON[m.group(mi).lower()[:3]]; y = m.group(3) or (yfn(mo) if yfn else None)
            if y: return iso(y, mo, m.group(di))
    return None
class Doc(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.out = []; s.sk = None; s.skd = 0; s.cells = []; s.rows = []; s.head = None; s.para = None; s.tst = []; s.tid = 0
    def handle_starttag(s, tag, a):
        a = dict(a)
        if s.sk:
            if tag == s.sk: s.skd += 1
            return
        if tag in ('style', 'script') or (tag == 'sup' and 'reference' in (a.get('class') or '')) or (tag == 'span' and 'sortkey' in (a.get('class') or '')):
            s.sk = tag; s.skd = 1; return
        if tag == 'table': s.tid += 1; s.tst.append(s.tid)
        elif tag == 'tr': s.rows.append({'c': [], 'h': [], 't': s.tst[-1] if s.tst else 0})
        elif tag in ('td', 'th'):
            if s.rows: s.cells.append([tag, []])
        elif tag in ('h2', 'h3', 'h4', 'h5'): s.head = [int(tag[1]), []]
        elif tag in ('p', 'li', 'dd', 'dt') and not s.cells: s.para = []
        elif tag == 'br': s.handle_data(' ')
    def handle_endtag(s, tag):
        if s.sk:
            if tag == s.sk:
                s.skd -= 1
                if not s.skd: s.sk = None
            return
        if tag == 'table':
            if s.tst: s.tst.pop()
        elif tag == 'tr':
            if s.rows:
                r = s.rows.pop()
                if r['c']: s.out.append(('row', r['c'], r['t'], sum(r['h']) * 2 > len(r['h'])))
        elif tag in ('td', 'th'):
            if s.cells and s.rows:
                t, buf = s.cells.pop()
                s.rows[-1]['c'].append(' '.join(''.join(buf).split())); s.rows[-1]['h'].append(t == 'th')
        elif tag in ('h2', 'h3', 'h4', 'h5'):
            if s.head: s.out.append(('h', s.head[0], ' '.join(''.join(s.head[1]).split()))); s.head = None
        elif tag in ('p', 'li', 'dd', 'dt'):
            if s.para is not None and not s.cells:
                t = ' '.join(''.join(s.para).split())
                if t: s.out.append(('p', t))
                s.para = None
    def handle_data(s, d):
        if s.sk: return
        if s.cells: s.cells[-1][1].append(d)
        elif s.head: s.head[1].append(d)
        elif s.para is not None: s.para.append(d)
WGAP = float(os.environ.get('WGAP', '0.7'))
WLOCK = threading.Lock(); WNEXT = [0.0]
def wiki(title):
    u = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': title, 'prop': 'text', 'format': 'json', 'formatversion': 2, 'redirects': 1, 'disableeditsection': 1, 'disabletoc': 1, 'maxlag': 5})
    for k in range(8):
        with WLOCK:
            w = WNEXT[0] - time.time()
            WNEXT[0] = max(WNEXT[0], time.time()) + WGAP
        if w > 0: time.sleep(w)
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=WUA), timeout=60) as r:
                j = json.loads(r.read().decode('utf-8', 'replace'))
            if 'parse' not in j:
                if j.get('error', {}).get('code') == 'maxlag': time.sleep(6); continue
                return None
            p = Doc(); p.feed(j['parse']['text']); return p.out
        except urllib.error.HTTPError as e:
            ra = e.headers.get('Retry-After') if e.headers else None
            wait = min(180, int(ra) if ra and ra.isdigit() else 20 * (k + 1))
            if e.code in (429, 503):
                with WLOCK: WNEXT[0] = max(WNEXT[0], time.time() + wait)
            if k == 7: print('wiki fail', title, e, flush=True); return 0
            time.sleep(2)
        except Exception as e:
            if k == 7: print('wiki fail', title, e, flush=True); return 0
            time.sleep(4 * (k + 1))
    return 0
def col(hdr, *names):
    for i, h in enumerate(hdr):
        hl = h.lower()
        if any(n in hl for n in names): return i
    return -1
def nfl_like(blocks, lg, team, season, src):
    ev = []; hdr = None; ht = -1; heads = {}; box = None; boxes = []
    yfn = lambda mo: season if mo >= 7 else season + 1
    for b in blocks:
        if b[0] == 'h':
            for k in [k for k in heads if k >= b[1]]: del heads[k]
            heads[b[1]] = b[2].lower()
            opp = [t for t in tfind(lg, norm(b[2])) if t != team]
            wk = re.match(r'\s*week (\d{1,2})\b', b[2].lower())
            box = {'opp': opp[0] if opp else '', 'wk': int(wk.group(1)) if wk else 0, 'pre': any(re.search(r'pre-?season|exhibition', h) for h in heads.values())}
            boxes.append(box); continue
        if b[0] == 'p':
            if box is None: continue
            t = b[1]; tl = t.lower()
            if tl.startswith('date'):
                d = pdate(t, yfn)
                if d: box['d'] = d
            elif tl.startswith(('game time', 'kickoff', 'time:')):
                st = ptime(t)
                if st: box['st'] = st
            elif tl.startswith(('tv', 'television', 'network')):
                n = pnet(t)
                if n: box['net'] = n
            continue
        cells = b[1]
        if b[3] or (col(cells, 'opponent') >= 0 and col(cells, 'date') >= 0):
            if col(cells, 'opponent') >= 0 and col(cells, 'date') >= 0: hdr = cells; ht = b[2]
            continue
        if not hdr or b[2] != ht or len(cells) < 3: continue
        io, idt, iw, itv, itm = col(hdr, 'opponent'), col(hdr, 'date'), col(hdr, 'week', 'round', 'game'), col(hdr, 'tv', 'network'), col(hdr, 'time', 'kickoff')
        off = len(cells) - len(hdr)
        def cell(i):
            return cells[i] if 0 <= i < len(cells) else ''
        d = pdate(cell(idt), yfn) or (pdate(cell(idt + off), yfn) if off else None)
        if not d: continue
        oc = cell(io) if tfind(lg, norm(cell(io))) else cell(io + off) if off else cell(io)
        opp = [t for t in tfind(lg, norm(oc)) if t != team]
        if not opp: continue
        away = bool(re.match(r'\s*(at|@|vs\.? at)\b', oc.lower()))
        neutral = bool(re.match(r'\s*(vs\.?|n\b)', oc.lower())) and lg == 'ncaaf'
        wk = cell(iw).strip().lower() if iw >= 0 else ''
        e = {'lg': lg, 'd': d, 'a': team if away else opp[0], 'h': opp[0] if away else team, 'se': season, 'src': src, '_t': ht, '_o': opp[0]}
        if neutral: e['n'] = 1
        if wk.isdigit(): e['wk'] = int(wk)
        elif wk: e['rd'] = wk[:24]
        if lg == 'nfl' and any(re.search(r'pre-?season|exhibition', h) for h in heads.values()): e['_pre'] = 1
        tv = pnet(cell(itv)) if itv >= 0 else ''
        if tv: e['net'] = tv
        if itm >= 0:
            st = ptime(cell(itm), 'e' if re.search(r'\b(et|est|edt|eastern)\b', hdr[itm].lower()) else None)
            if st: e['st'] = st
        ev.append(e)
    if lg == 'nfl':
        last = collections.defaultdict(str)
        for e in ev: last[e['_t']] = max(last[e['_t']], e['d'])
        ev = [e for e in ev if not e.get('_pre') and last[e['_t']] >= '%d-09-20' % season and (e['d'][5:7] in ('09', '10', '11', '12', '01', '02') or e['d'] == '1997-08-31') and '%d-08-30' % season < e['d'] < '%d-02-15' % (season + 1)]
        for bx in boxes:
            if bx['pre'] or not (bx.get('st') or bx.get('net')) or not (bx['opp'] or bx.get('d')): continue
            c = [e for e in ev if (not bx['opp'] or e['_o'] == bx['opp']) and (e['d'] == bx['d'] if bx.get('d') else (e.get('wk') == bx['wk'] if bx['wk'] else bool(e.get('rd'))))]
            if len(c) == 1:
                if bx.get('st') and not c[0].get('st'): c[0]['st'] = bx['st']
                if bx.get('net') and not c[0].get('net'): c[0]['net'] = bx['net']
    for e in ev:
        for k in ('_t', '_o', '_pre'): e.pop(k, None)
    return ev
CBB = {'Kentucky Wildcats': 'kentucky', 'Duke Blue Devils': 'duke', 'North Carolina Tar Heels': 'north carolina', 'Kansas Jayhawks': 'kansas', 'Arkansas Razorbacks': 'arkansas', 'Michigan Wolverines': 'michigan', 'Indiana Hoosiers': 'indiana', 'Louisville Cardinals': 'louisville', "UNLV Runnin' Rebels": 'unlv', 'Georgetown Hoyas': 'georgetown', 'Syracuse Orangemen': 'syracuse', 'UCLA Bruins': 'ucla', 'Arizona Wildcats': 'arizona', 'UConn Huskies': 'uconn', 'LSU Tigers': 'lsu', 'Kansas State Wildcats': 'kansas state', 'Michigan State Spartans': 'michigan state', 'Oklahoma Sooners': 'oklahoma'}
CBR = [(r'national championship|championship game|national final', 'championship'), (r'final four|national semi', 'final four'), (r'elite eight|elite 8|regional final', 'elite eight'), (r'sweet sixteen|sweet 16|regional semi', 'sweet sixteen'), (r'second round|2nd round|round of 32', 'second round'), (r'first round|1st round|round of 64', 'first round')]
def cbb(blocks, team, season, src):
    ev = []; hdr = None; ht = -1; tz = None; sect = ''
    yfn = lambda mo: season if mo >= 7 else season + 1
    for b in blocks:
        t = ' '.join(b[1]) if b[0] == 'row' else b[1] if b[0] == 'p' else ''
        m = re.search(r'times? (?:are |listed )?(?:in )?(?:the )?(eastern|central|mountain|pacific)', t.lower())
        if m: tz = m.group(1)[0]
    for b in blocks:
        if b[0] != 'row': continue
        cells = b[1]
        if b[3] or (col(cells, 'opponent') >= 0 and col(cells, 'date') >= 0):
            if col(cells, 'opponent') >= 0 and col(cells, 'date') >= 0: hdr = cells; ht = b[2]
            elif len(cells) == 1: sect = cells[0].lower()
            continue
        if not hdr or b[2] != ht or len(cells) < 3: continue
        io, idt = col(hdr, 'opponent'), col(hdr, 'date')
        if max(io, idt) >= len(cells): continue
        d = pdate(cells[idt], yfn)
        opp = [x for x in tfind('ncaab', norm(re.sub(r'\([^)]*\)', ' ', cells[io]))) if x != team]
        if not d or not opp: continue
        oc = cells[io].lower()
        away = bool(re.match(r'\s*(at|@)\b', oc))
        e = {'lg': 'ncaab', 'd': d, 'a': team if away else opp[0], 'h': opp[0] if away else team, 'se': season + 1, 'src': src}
        if re.match(r'\s*vs', oc): e['n'] = 1
        if 'ncaa' in sect:
            rd = next((v for p, v in CBR if re.search(p, oc)), '')
            e['rd'] = rd or 'ncaa'
        st = ptime(cells[idt], tz)
        if st: e['st'] = st
        itv = col(hdr, 'tv', 'network')
        n = pnet(cells[idt]) or (pnet(cells[itv]) if 0 <= itv < len(cells) and itv != idt else '')
        if n: e['net'] = n
        ev.append(e)
    return ev
def nflpo(blocks, season, src):
    ev = []; hdr = None; ht = -1; rd = ''; d = None
    for b in blocks:
        if b[0] != 'row': continue
        cells = b[1]
        if b[3] or (col(cells, 'away team') >= 0 and col(cells, 'home team') >= 0):
            if col(cells, 'away team') >= 0 and col(cells, 'home team') >= 0: hdr = cells; ht = b[2]; rd = ''; d = None
            continue
        if not hdr or b[2] != ht: continue
        tc = [(i, tfind('nfl', norm(c))) for i, c in enumerate(cells)]
        tc = [(i, t[0]) for i, t in tc if t and not re.search(r'super bowl|round|championship', cells[i].lower())]
        if len(tc) < 2: continue
        if tc[0][0] > 0 and not re.search(r'\d', cells[0][:4]) and len(cells) >= len(hdr) - 1 and cells[0].strip(): rd = cells[0].lower()
        for c in cells:
            x = pdate(c)
            if x: d = x
        if not d or not ('%d-12-20' % season <= d <= '%d-02-15' % (season + 1)): continue
        e = {'lg': 'nfl', 'd': d, 'a': tc[0][1], 'h': tc[1][1], 'se': season, 'src': src, 'rd': re.sub(r'\s+', ' ', rd)[:24]}
        st = next((ptime(c, 'e') for c in cells[tc[1][0] + 1:] if ptime(c, 'e')), '')
        if st: e['st'] = st
        if pnet(cells[-1]): e['net'] = pnet(cells[-1])
        ev.append(e)
    return ev
def hoops(blocks, year, src, ser=''):
    ev = []; heads = {}; skip = False; tv = ''; pend = None; hdr = None; ht = -1
    for b in blocks:
        if b[0] == 'h':
            for k in [k for k in heads if k >= b[1]]: del heads[k]
            heads[b[1]] = b[2]; skip = bool(re.search(r'regular.season series|road to the finals|background', b[2].lower())); tv = ''; pend = None; continue
        if b[0] != 'row': continue
        cells = b[1]; text = ' | '.join(cells); tl = text.lower()
        if b[3]:
            if re.search(r'regular.season series|all-time playoff|previous playoff', tl): skip = True
            if col(cells, 'road team') >= 0 and col(cells, 'home team') >= 0 and col(cells, 'date') >= 0: hdr = cells; ht = b[2]
            continue
        hk = ' / '.join(heads[k] for k in sorted(heads))
        if hdr and b[2] == ht and len(cells) >= len(hdr):
            d = pdate(cells[col(hdr, 'date')], lambda mo: year)
            a = tfind('nba', norm(cells[col(hdr, 'road team')])); h = tfind('nba', norm(cells[col(hdr, 'home team')]))
            g = re.search(r'(\d)', cells[0])
            if d and a and h and d[:4] == str(year):
                e = {'lg': 'nba', 'd': d, 'a': a[0], 'h': h[0], 'y': year, 'src': src, 'hk': hk[:80]}
                if g: e['g'] = int(g.group(1))
                if ser or serof('nba', hk): e['ser'] = ser or serof('nba', hk)
                ev.append(e)
            continue
        if skip or len(cells) != 1: continue
        t = cells[0].strip()
        m = RD1.match(t)
        if m and len(t) < 44:
            d = pdate(t, lambda mo: year)
            pend = {'d': d, 'st': etime(t[m.end():]), 'net': pnet(tv)} if d and d[:4] == str(year) else None
            tv = ''; continue
        m = re.match(r'^(.+?) (\d{2,3}), (.+?) (\d{2,3})\b', t)
        if m and pend:
            a = tfind('nba', norm(m.group(1))); h = tfind('nba', norm(m.group(3)))
            if a and h and a[0] != h[0]:
                e = {'lg': 'nba', 'd': pend['d'], 'a': a[0], 'h': h[0], 'y': year, 'src': src, 'hk': hk[:80]}
                if pend['st']: e['st'] = pend['st']
                if pend['net']: e['net'] = pend['net']
                if ser or serof('nba', hk): e['ser'] = ser or serof('nba', hk)
                ev.append(e)
            pend = None; continue
        if t and len(t) < 40 and not re.search(r'\d', t) and t.lower() not in ('boxscore', 'recap'): tv = t
    return sergames(ev, ser == 'finals')
def sergames(ev, single=False):
    if single and ev:
        top = collections.Counter(frozenset((e['a'], e['h'])) for e in ev).most_common(1)[0][0]
        ev = [e for e in ev if frozenset((e['a'], e['h'])) == top]
    seen = {}; out = []
    for e in ev:
        k = (e['d'], frozenset((e['a'], e['h'])))
        if k in seen:
            for f in ('g', 'ser', 'st', 'net'):
                if e.get(f) and not seen[k].get(f): seen[k][f] = e[f]
            continue
        seen[k] = e; out.append(e)
    by = collections.defaultdict(list)
    for e in out: by[(frozenset((e['a'], e['h'])), e.get('ser', ''))].append(e)
    for k, L in by.items():
        L.sort(key=lambda e: e['d'])
        if len(L) <= 7 and sum(1 for e in L if e.get('g')) < len(L):
            for n, e in enumerate(L): e['g'] = n + 1
    return out
def series(blocks, lg, year, src, ser=''):
    ev = []; heads = {}; hdr = None; ht = -1; cur = None; tvs = []
    yfn = lambda mo: year
    for b in blocks:
        if b[0] == 'row' and len(b[1]) == 2 and b[1][0].strip().lower() in ('television', 'tv', 'network', 'networks', 'broadcast', 'tv network'):
            tg = tvgames(b[1][1])
            if tg: tvs.append(tg)
        if b[0] == 'h':
            for k in [k for k in heads if k >= b[1]]: del heads[k]
            heads[b[1]] = b[2]; continue
        text = ' | '.join(b[1]) if b[0] == 'row' else b[1]
        if b[0] == 'row' and (b[3] or (col(b[1], 'date') >= 0 and col(b[1], 'game', 'score') >= 0)):
            hdr = b[1]; ht = b[2]; continue
        if b[0] == 'p' and len(text) > 160: continue
        d = pdate(text, yfn)
        if not d or d[:4] != str(year): continue
        st = []
        for lv in sorted(heads, reverse=True):
            st = tfind(lg, norm(heads[lv]))
            if len(st) >= 2: break
        hk = ' / '.join(heads[k] for k in sorted(heads))
        cells = b[1] if b[0] == 'row' else [text]
        isc = col(hdr, 'score', 'result') if hdr and b[0] == 'row' and b[2] == ht else -1
        rt = tfind(lg, norm(cells[isc] if 0 <= isc < len(cells) else text))[:2]
        if len(rt) < 2:
            if len(st) >= 2 and all(t in st for t in rt): rt = rt + [t for t in st[:2] if t not in rt]
            else: continue
        elif len(st) >= 2 and set(rt) != set(st[:2]):
            if not (set(rt) <= set(st)): continue
        g = None
        if b[0] == 'row' and cells and cells[0].strip().rstrip('*').isdigit() and 1 <= int(cells[0].strip().rstrip('*')) <= 7: g = int(cells[0].strip().rstrip('*'))
        m = re.search(r'\bgame (\d)\b', text.lower())
        if g is None and m: g = int(m.group(1))
        e = {'lg': lg, 'd': d, 'a': rt[0], 'h': rt[1], 'y': year, 'src': src, 'hk': hk[:80]}
        if g: e['g'] = g
        st = ptime(text)
        if st: e['st'] = st
        s2 = ser or serof(lg, hk)
        if s2: e['ser'] = s2
        ev.append(e)
    out = sergames(ev, ser in ('ws', 'alcs', 'nlcs', 'finals'))
    pairs = []
    for e in out:
        k = (frozenset((e['a'], e['h'])), e.get('ser', ''))
        if k not in pairs: pairs.append(k)
    if tvs and (len(tvs) == len(pairs) or len(tvs) == 1):
        for e in out:
            tg = tvs[pairs.index((frozenset((e['a'], e['h'])), e.get('ser', '')))] if len(tvs) == len(pairs) else tvs[0]
            hit = [n for n, g in tg if g and e.get('g') in g] or ([n for n, g in tg if g is None] if len(set(n for n, g in tg if g is None)) == 1 and not any(g for n, g in tg) else [])
            if len(set(hit)) == 1 and not e.get('net'): e['net'] = hit[0]
    return out
def serof(lg, hk):
    h = hk.lower()
    if lg == 'mlb':
        for a, b in (('world series', 'ws'), ('american league championship', 'alcs'), ('national league championship', 'nlcs'), ('american league division', 'alds'), ('national league division', 'nlds'), ('alcs', 'alcs'), ('nlcs', 'nlcs'), ('alds', 'alds'), ('nlds', 'nlds')):
            if a in h: return b
    if lg in ('nba', 'nhl'):
        if re.search(r'stanley cup finals?|nba finals', h): return 'finals'
        if re.search(r'conference finals?', h): return 'cf'
        if re.search(r'semifinals?|division finals?', h): return 'sf'
        if re.search(r'first round|division semifinals?|quarterfinals?|preliminary', h): return 'r1'
    return ''
NFLT = {'Arizona Cardinals': (1994, 2004), 'Phoenix Cardinals': (1988, 1993), 'St. Louis Cardinals (NFL)': (1984, 1987), 'Atlanta Falcons': 0, 'Baltimore Ravens': (1996, 2004), 'Buffalo Bills': 0, 'Carolina Panthers': (1995, 2004), 'Chicago Bears': 0, 'Cincinnati Bengals': 0, 'Cleveland Browns': 0, 'Dallas Cowboys': 0, 'Denver Broncos': 0, 'Detroit Lions': 0, 'Green Bay Packers': 0, 'Houston Oilers': (1984, 1996), 'Tennessee Oilers': (1997, 1998), 'Tennessee Titans': (1999, 2004), 'Houston Texans': (2002, 2004), 'Indianapolis Colts': 0, 'Jacksonville Jaguars': (1995, 2004), 'Kansas City Chiefs': 0, 'Los Angeles Raiders': (1984, 1994), 'Oakland Raiders': (1995, 2004), 'Los Angeles Rams': (1984, 1994), 'St. Louis Rams': (1995, 2004), 'Miami Dolphins': 0, 'Minnesota Vikings': 0, 'New England Patriots': 0, 'New Orleans Saints': 0, 'New York Giants': 0, 'New York Jets': 0, 'Philadelphia Eagles': 0, 'Pittsburgh Steelers': 0, 'San Diego Chargers': 0, 'San Francisco 49ers': 0, 'Seattle Seahawks': 0, 'Tampa Bay Buccaneers': 0, 'Washington Redskins': 0}
CFB = {'Notre Dame Fighting Irish': 'notre dame', 'Ohio State Buckeyes': 'ohio state', 'Michigan Wolverines': 'michigan', 'Penn State Nittany Lions': 'penn state', 'Nebraska Cornhuskers': 'nebraska', 'Oklahoma Sooners': 'oklahoma', 'Texas Longhorns': 'texas', 'Alabama Crimson Tide': 'alabama', 'Auburn Tigers': 'auburn', 'LSU Tigers': 'lsu', 'Florida State Seminoles': 'florida state', 'Florida Gators': 'florida', 'Miami Hurricanes': 'miami', 'Georgia Bulldogs': 'georgia', 'Tennessee Volunteers': 'tennessee', 'Clemson Tigers': 'clemson', 'USC Trojans': 'usc', 'UCLA Bruins': 'ucla', 'Washington Huskies': 'washington', 'Colorado Buffaloes': 'colorado', 'Texas A&M Aggies': 'texas a and m', 'Michigan State Spartans': 'michigan state', 'Iowa Hawkeyes': 'iowa', 'Wisconsin Badgers': 'wisconsin', 'Arkansas Razorbacks': 'arkansas', 'BYU Cougars': 'byu', 'Syracuse Orangemen': 'syracuse', 'Virginia Tech Hokies': 'virginia tech', 'Kansas State Wildcats': 'kansas state', 'Army Cadets': 'army', 'Navy Midshipmen': 'navy', 'West Virginia Mountaineers': 'west virginia', 'Pittsburgh Panthers': 'pittsburgh', 'Boston College Eagles': 'boston college', 'Oregon Ducks': 'oregon', 'Arizona State Sun Devils': 'arizona state', 'Georgia Tech Yellow Jackets': 'georgia tech', 'North Carolina Tar Heels': 'north carolina', 'Oklahoma State Cowboys': 'oklahoma state', 'Stanford Cardinal': 'stanford', 'Arizona Wildcats': 'arizona', 'Illinois Fighting Illini': 'illinois', 'Purdue Boilermakers': 'purdue', 'South Carolina Gamecocks': 'south carolina', 'Ole Miss Rebels': 'ole miss', 'Air Force Falcons': 'air force', 'Kansas Jayhawks': 'kansas', 'Missouri Tigers': 'missouri', 'Texas Tech Red Raiders': 'texas tech', 'Maryland Terrapins': 'maryland', 'Virginia Cavaliers': 'virginia', 'Kentucky Wildcats': 'kentucky', 'Louisville Cardinals': 'louisville', 'Washington State Cougars': 'washington state', 'Minnesota Golden Gophers': 'minnesota', 'Northwestern Wildcats': 'northwestern', 'Indiana Hoosiers': 'indiana', 'Houston Cougars': 'houston', 'Baylor Bears': 'baylor', 'TCU Horned Frogs': 'tcu', 'Mississippi State Bulldogs': 'mississippi state', 'Vanderbilt Commodores': 'vanderbilt', 'Utah Utes': 'utah', 'Fresno State Bulldogs': 'fresno state', 'Iowa State Cyclones': 'iowa state', 'Oregon State Beavers': 'oregon state', 'NC State Wolfpack': 'nc state', 'Wake Forest Demon Deacons': 'wake forest', 'Duke Blue Devils': 'duke', 'Rutgers Scarlet Knights': 'rutgers', 'Temple Owls': 'temple', 'Cincinnati Bearcats': 'cincinnati', 'Memphis Tigers': 'memphis', 'Tulane Green Wave': 'tulane', 'East Carolina Pirates': 'east carolina', 'Colorado State Rams': 'colorado state', 'Hawaii Rainbow Warriors': 'hawaii', 'SMU Mustangs': 'smu', 'Tulsa Golden Hurricane': 'tulsa'}
BOXERS = ['Mike Tyson', 'Evander Holyfield', 'Lennox Lewis', 'Riddick Bowe', 'George Foreman', 'Larry Holmes', 'Michael Spinks', 'Sugar Ray Leonard', 'Marvelous Marvin Hagler', 'Thomas Hearns', 'Roberto Durán', 'Julio César Chávez', 'Oscar De La Hoya', 'Pernell Whitaker', 'Félix Trinidad', 'Roy Jones Jr.', 'Bernard Hopkins', 'Floyd Mayweather Jr.', 'Héctor Camacho', 'Buster Douglas', 'Michael Moorer', 'Shane Mosley', 'Arturo Gatti', 'Marco Antonio Barrera', 'Érik Morales', 'Naseem Hamed', 'James Toney', 'Kostya Tszyu', 'Manny Pacquiao', 'Meldrick Taylor', 'Terry Norris', 'Tommy Morrison', 'Ray Mancini', 'Gerry Cooney', 'Aaron Pryor', 'Mike McCallum', 'Iran Barkley', 'Donald Curry', 'Mark Breland', 'Donovan Ruddock', 'Ray Mercer', 'Andrew Golota', 'Hasim Rahman', 'Antonio Tarver', 'Fernando Vargas', 'Zab Judah', 'Micky Ward', 'Vinny Paz', 'Julian Jackson', 'Gerald McClellan', 'Nigel Benn', 'Chris Eubank', 'Michael Nunn', 'Ike Quartey', 'Vernon Forrest', 'Wladimir Klitschko', 'Vitali Klitschko', 'David Tua', 'Chris Byrd', 'John Ruiz', 'Azumah Nelson', 'Alexis Argüello', 'Tony Tucker', 'Tim Witherspoon', 'Trevor Berbick', 'Pinklon Thomas', 'Frank Bruno', 'Barry McGuigan', 'Michael Carbajal', 'Humberto González', 'Johnny Tapia', 'Prince Charles Williams', 'Virgil Hill', 'Bobby Czyz', 'Dwight Muhammad Qawi', 'Simon Brown (boxer)', 'Buddy McGirt', 'Winky Wright', 'Ricardo Mayorga', 'Diego Corrales', 'José Luis Castillo', 'Juan Manuel Márquez', 'Kevin Kelley', 'Junior Jones', 'Oliver McCall', 'Bruce Seldon', 'Frans Botha', 'Peter McNeeley', 'Greg Page (boxer)', 'Carl Williams (boxer)', 'Tyrell Biggs', 'James Smith (boxer)', 'Mitch Green', 'Marvis Frazier', 'Henry Akinwande', 'Shannon Briggs', 'Michael Grant (boxer)', 'Montell Griffin', 'Greg Haugen', 'Edwin Rosario', 'Livingstone Bramble', 'Rocky Lockridge', 'Wilfredo Gómez', 'Jeff Fenech', 'Mike Weaver (boxer)']
OLY = [('1984-02-08', '1984-02-19', 'winter', 'sarajevo'), ('1984-07-28', '1984-08-12', 'summer', 'los angeles'), ('1988-02-13', '1988-02-28', 'winter', 'calgary'), ('1988-09-17', '1988-10-02', 'summer', 'seoul'), ('1992-02-08', '1992-02-23', 'winter', 'albertville'), ('1992-07-25', '1992-08-09', 'summer', 'barcelona'), ('1994-02-12', '1994-02-27', 'winter', 'lillehammer'), ('1996-07-19', '1996-08-04', 'summer', 'atlanta'), ('1998-02-07', '1998-02-22', 'winter', 'nagano'), ('2000-09-15', '2000-10-01', 'summer', 'sydney'), ('2002-02-08', '2002-02-24', 'winter', 'salt lake'), ('2004-08-13', '2004-08-29', 'summer', 'athens')]
NCAAB = {1984: '04-02', 1985: '04-01', 1986: '03-31', 1987: '03-30', 1988: '04-04', 1989: '04-03', 1990: '04-02', 1991: '04-01', 1992: '04-06', 1993: '04-05', 1994: '04-04', 1995: '04-03', 1996: '04-01', 1997: '03-31', 1998: '03-30', 1999: '03-29', 2000: '04-03', 2001: '04-02', 2002: '04-01', 2003: '04-07', 2004: '04-05'}
GOLF = [('masters', '%d Masters Tournament'), ('us open golf', '%d U.S. Open (golf)'), ('british open', '%d Open Championship'), ('pga championship', '%d PGA Championship')]
TENNIS = [('australian open', '%d Australian Open'), ('french open', '%d French Open'), ('wimbledon', '%d Wimbledon Championships'), ('us open tennis', '%d US Open (tennis)')]
def infodate(blocks, year):
    for b in blocks:
        if b[0] == 'row' and len(b[1]) == 2 and b[1][0].strip().lower() in ('date', 'dates'):
            t = b[1][1].replace('–', '-').replace('—', '-')
            ds = []
            m = re.search(r'(\d{1,2})\s+(' + MONS + r')[a-z]*\s*-\s*(\d{1,2})\s+(' + MONS + r')', t, re.I)
            if m: return iso(year, MON[m.group(2).lower()[:3]], m.group(1)), iso(year, MON[m.group(4).lower()[:3]], m.group(3))
            m = re.search(r'(' + MONS + r')[a-z]*\.?\s+(\d{1,2})\s*-\s*(' + MONS + r')[a-z]*\.?\s+(\d{1,2})', t, re.I)
            if m: return iso(year, MON[m.group(1).lower()[:3]], m.group(2)), iso(year, MON[m.group(3).lower()[:3]], m.group(4))
            m = re.search(r'(' + MONS + r')[a-z]*\.?\s+(\d{1,2})\s*-\s*(\d{1,2})', t, re.I)
            if m: return iso(year, MON[m.group(1).lower()[:3]], m.group(2)), iso(year, MON[m.group(1).lower()[:3]], m.group(3))
            m = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\s+(' + MONS + r')', t, re.I)
            if m: return iso(year, MON[m.group(3).lower()[:3]], m.group(1)), iso(year, MON[m.group(3).lower()[:3]], m.group(2))
            d = pdate(t, lambda mo: year)
            if d: return d, d
    return None, None
def boxrec(blocks, name, src):
    ev = []; hdr = None; ht = -1
    for b in blocks:
        if b[0] != 'row': continue
        cells = b[1]
        if col(cells, 'opponent') >= 0 and col(cells, 'date') >= 0: hdr = cells; ht = b[2]; continue
        if not hdr or b[2] != ht: continue
        io, idt = col(hdr, 'opponent'), col(hdr, 'date')
        if max(io, idt) >= len(cells): continue
        d = pdate(cells[idt])
        if not d or not ('1984' <= d[:4] <= '2004'): continue
        ev.append({'lg': 'boxing', 'd': d, 'a': norm(name).strip(), 'h': norm(cells[io]).strip(), 'src': src})
    return ev
def races(blocks, year, src, sr=''):
    ev = []; hdr = None; ht = -1; head = ''; ltr = ''
    yfn = lambda mo: year
    for b in blocks:
        if b[0] == 'h': head = re.sub(r'^(round \d+|exhibition|non.points( race)?)\s*[:–-]?\s*', '', re.sub(r'\s*\([^)]*\)\s*$', '', b[2]), flags=re.I); continue
        if b[0] == 'row':
            cells = b[1]
            if b[3] or (col(cells, 'date') >= 0 and col(cells, 'race', 'event', 'name') >= 0):
                if col(cells, 'date') >= 0 and col(cells, 'race', 'event', 'name') >= 0: hdr = cells; ht = b[2]; ltr = ''
                continue
            if hdr and b[2] == ht and len(cells) >= 2:
                idt, ir, itr, itv = col(hdr, 'date'), col(hdr, 'race', 'event', 'name'), col(hdr, 'track', 'venue', 'circuit', 'site', 'location'), col(hdr, 'tv', 'network', 'television')
                ict = col(hdr, 'location', 'city')
                short = len(hdr) - len(cells)
                d = pdate(cells[idt], yfn) if 0 <= idt < len(cells) and not short else None
                if not d and short > 0 and idt == len(hdr) - 1: d = pdate(cells[-1], yfn)
                if not d or not (0 <= ir < len(cells)) or not cells[ir].strip() or pdate(cells[ir], yfn) or re.search(r'cancel', cells[ir], re.I): continue
                e = {'lg': 'racing', 'd': d, 'k': norm(cells[ir]).strip(), 'y': year, 'src': src}
                if not short and 0 <= itr < len(cells) and itr != ir: ltr = (norm(re.sub(r'^[ORS] ', '', cells[itr])).strip() + (' ' + norm(cells[ict]).strip() if 0 <= ict < len(cells) and ict not in (itr, ir, idt) else ''))[:80]
                if ltr: e['tr'] = ltr
                if cells[0].strip().isdigit() and not short: e['rn'] = int(cells[0].strip())
                if not short and 0 <= itv < len(cells) and pnet(cells[itv]): e['net'] = pnet(cells[itv])
                ev.append(e)
        elif b[0] == 'p' and head:
            m = re.search(r'\b(?:was|were) (?:held|run|ran|contested|scheduled)\b', b[1], re.I)
            if m and m.start() < 90:
                m2 = re.search(r'\bbut (?:was|were)? ?(?:held|run|ran|postponed|moved|delayed|pushed)\b', b[1], re.I)
                d = pdate(b[1][m2.start():m2.start() + 60], yfn) if m2 else None
                d = d or pdate(b[1][m.start():m.start() + 70], yfn)
                if d:
                    e = {'lg': 'racing', 'd': d, 'k': norm(head).strip(), 'y': year, 'src': src}
                    t = re.search(r'\bat (?:the )?([A-Z][A-Za-z\'’. -]{3,50}?)(?:\.|,| in | and |$)', b[1][m.end():m.end() + 120])
                    if t: e['tr'] = norm(t.group(1)).strip()[:60]
                    n = pnet(' '.join(re.findall(r'(?:aired|broadcast|televised|shown) (?:live )?(?:on|by) ([A-Za-z0-9]+)', b[1])))
                    if n: e['net'] = n
                    ev.append(e)
    seen = {}; out = []
    late = {}
    for e in ev:
        e['k'] = re.sub(r'^(round \d+|exhibition|non points( race)?) ', '', e['k'])
        late[e['k']] = max(late.get(e['k'], ''), e['d'])
    for e in ev:
        if e['d'] < late[e['k']] and (datetime.date.fromisoformat(late[e['k']]) - datetime.date.fromisoformat(e['d'])).days <= 3: e['d'] = late[e['k']]
    for e in ev:
        if sr: e['sr'] = sr
        k = (e['k'], e['d'])
        if k in seen:
            for f in ('tr', 'net', 'rn'):
                if e.get(f) and not seen[k].get(f): seen[k][f] = e[f]
            continue
        seen[k] = e; out.append(e)
    return out
def bowls(blocks, season, src):
    ev = []
    yfn = lambda mo: season if mo >= 7 else season + 1
    for b in blocks:
        if b[0] != 'row' or b[3]: continue
        text = ' | '.join(b[1]); m = re.search(r"([A-Z][A-Za-z.&'’ ]{2,30}? Bowl)\b", text)
        d = pdate(text, yfn)
        if m and d and (d[:7] >= '%d-12' % season and d[:7] <= '%d-01' % (season + 1)):
            name = norm(re.sub(r'^(the|\d{4})\s+', '', m.group(1), flags=re.I)).strip()
            ev.append({'lg': 'ncaaf', 'd': d, 'k': name, 'se': season, 'tm': tfind('ncaaf', norm(text))[:2], 'src': src})
    seen = set(); out = []
    for e in ev:
        if (e['k'], e['d']) not in seen: seen.add((e['k'], e['d'])); out.append(e)
    return out
def nohit(blocks, src):
    ev = []
    for b in blocks:
        if b[0] != 'row' or b[3]: continue
        text = ' | '.join(b[1]); d = pdate(text)
        if d and '1984' <= d[:4] <= '2004':
            tm = tfind('mlb', norm(text))
            if tm: ev.append({'lg': 'mlb', 'd': d, 'k': 'no hitter', 'who': norm(text)[:160], 'tm': tm[:2], 'src': src})
    return ev
def build():
    jobs = []
    for y in range(1984, 2005):
        for t, span in NFLT.items():
            if span and not (span[0] <= y <= span[1]): continue
            if t == 'Cleveland Browns' and 1996 <= y <= 1998: continue
            nick = tfind('nfl', norm(t))[0]
            jobs.append(('nfl', '%d %s season' % (y, t), nick, y))
        jobs.append(('nflpo', '%d–%s NFL playoffs' % (y, str(y + 1) if y == 1999 else str(y + 1)[2:]), y))
        if y >= 1984:
            for t, sch in CBB.items():
                if y - 1 >= 1983: jobs.append(('cbb', "%d–%s %s men's basketball team" % (y - 1, str(y) if y == 2000 else str(y)[2:], t), sch, y - 1))
        for t, sch in CFB.items():
            jobs.append(('cfb', '%d %s football team' % (y, t), sch, y))
        if y != 1994: jobs.append(('ser', '%d World Series' % y, 'mlb', y, 'ws'))
        if y != 1994:
            jobs.append(('ser', '%d American League Championship Series' % y, 'mlb', y, 'alcs')); jobs.append(('ser', '%d National League Championship Series' % y, 'mlb', y, 'nlcs'))
        if y >= 1995:
            jobs.append(('ser', '%d American League Division Series' % y, 'mlb', y, 'alds')); jobs.append(('ser', '%d National League Division Series' % y, 'mlb', y, 'nlds'))
        jobs.append(('ser', '%d NBA playoffs' % y, 'nba', y, '')); jobs.append(('ser', '%d NBA Finals' % y, 'nba', y, 'finals'))
        jobs.append(('ser', '%d Stanley Cup playoffs' % y, 'nhl', y, '')); jobs.append(('ser', '%d Stanley Cup Finals' % y, 'nhl', y, 'finals'))
        jobs.append(('bowl', '%d–%s NCAA football bowl games' % (y, str(y + 1) if y == 1999 else str(y + 1)[2:]), y))
        jobs.append(('race', '%d NASCAR Winston Cup Series' % y, y, ''))
        jobs.append(('race', '%d NASCAR Busch Series' % y, y, 'busch'))
        if y >= 1995: jobs.append(('race', '%d NASCAR Craftsman Truck Series' % y, y, 'truck'))
        jobs.append(('race', '%d CART season' % y if y < 2004 else '2004 Champ Car season', y, 'cart'))
        if y == 1995: jobs.append(('race', '1995 NASCAR SuperTruck Series', y, 'truck'))
        jobs.append(('info', '%d Major League Baseball All-Star Game' % y, 'mlb', 'all star game', y)); jobs.append(('info', '%d NBA All-Star Game' % y, 'nba', 'all star game', y))
        for k, p in GOLF: jobs.append(('info', p % y, 'golf', k, y))
        for k, p in TENNIS: jobs.append(('info', p % y, 'tennis', k, y))
    for n in BOXERS: jobs.append(('box', n))
    jobs.append(('nohit', 'List of Major League Baseball no-hitters'))
    prev = []
    if os.path.exists(SCHF):
        prev = [e for e in json.load(gzip.open(SCHF, 'rt', encoding='utf-8')) if e.get('src')]
    def isrep(j): return j[0] in ('ser', 'race', 'nfl', 'nflpo', 'cbb') or (j[0] == 'info' and j[3] == 'all star game')
    jobs.sort(key=lambda j: (('nflpo', 'ser', 'race', 'info', 'nfl', 'cbb').index(j[0]) if isrep(j) else 9))
    titles = set(j[1] for j in jobs)
    prev = [e for e in prev if e['src'] in titles]
    REP = set(j[1] for j in jobs if isrep(j)); old2 = collections.defaultdict(list)
    pages = json.load(gzip.open(PGF, 'rt', encoding='utf-8')) if os.path.exists(PGF) else {}
    for e in prev:
        if e['src'] in REP: old2[e['src']].append(e)
    prev = [e for e in prev if e['src'] not in old2]
    gone = set(json.load(open(NOPG)) if os.path.exists(NOPG) else [])
    done = set(e['src'] for e in prev) | set(t for t in gone if t not in REP) | set(pages.get('_missing', {}))
    alljobs = len(jobs); jobs = [j for j in jobs if j[1] not in done]
    print('pages', alljobs, 'kept as parsed', alljobs - len(jobs), 'to parse', len(jobs), 'of them cached', sum(1 for j in jobs if j[1] in pages), 'kept events', len(prev), flush=True)
    stat = collections.Counter(); zero = []
    FB = float(os.environ.get('FETCH_BUDGET_MIN', '150')) * 60
    def run(j):
        b = pages.get(j[1])
        if b is None:
            if time.time() - T0 > FB: return j, 0
            time.sleep(random.random() * .4)
            b = wiki(j[1])
            if b == 0: return j, 0
            if b is None: pages.setdefault('_missing', {})[j[1]] = 1; return j, None
            b = prune(b)
            if j[1] in REP: pages[j[1]] = b
        if j[0] == 'ser' and j[2] == 'nba': return j, hoops(b, j[3], j[1], j[4])
        if j[0] == 'nfl': return j, nfl_like(b, 'nfl', j[2], j[3], j[1])
        if j[0] == 'nflpo': return j, nflpo(b, j[2], j[1])
        if j[0] == 'cbb': return j, cbb(b, j[2], j[3], j[1])
        if j[0] == 'cfb': return j, nfl_like(b, 'ncaaf', j[2], j[3], j[1])
        if j[0] == 'ser': return j, series(b, j[2], j[3], j[1], j[4])
        if j[0] == 'bowl': return j, bowls(b, j[2], j[1])
        if j[0] == 'race': return j, races(b, j[2], j[1], j[3])
        if j[0] == 'box': return j, boxrec(b, re.sub(r'\s*\(.*\)', '', j[1]), j[1])
        if j[0] == 'nohit': return j, nohit(b, j[1])
        if j[0] == 'info':
            a, z = infodate(b, j[4])
            e = {'lg': j[2], 'k': j[3], 'y': j[4], 'd': a, 'd2': z, 'src': j[1]}
            if j[3] == 'all star game':
                tg = [n for x in b if x[0] == 'row' and len(x[1]) == 2 and x[1][0].strip().lower() in ('television', 'tv', 'network') for n, g in tvgames(x[1][1])]
                tv = ''
                for x in b:
                    if x[0] != 'row' or len(x[1]) != 1: continue
                    t = x[1][0].strip()
                    if RD1.match(t) and len(t) < 44 and pdate(t, lambda mo: j[4]) == a:
                        if etime(t[RD1.match(t).end():]): e['st'] = etime(t[RD1.match(t).end():])
                        if pnet(tv): tg = [pnet(tv)] + tg
                    elif len(t) < 40 and not re.search(r'\d', t): tv = t
                if tg: e['net'] = tg[0]
            return j, ([e] if a else [])
    ev = list(prev); nopg = set(json.load(open(NOPG)) if os.path.exists(NOPG) else [])
    with ThreadPoolExecutor(3) as ex:
        for n, (j, r) in enumerate(ex.map(run, jobs)):
            if r == 0: stat[j[0] + '_failed'] += 1; zero.append('FAILED ' + j[1]); ev += old2.get(j[1], []); continue
            if r is None: stat[j[0] + '_missing'] += 1; zero.append('MISSING ' + j[1]); nopg.add(j[1]); ev += old2.get(j[1], []); continue
            if not r and old2.get(j[1]): stat[j[0] + '_zero_kept_old'] += 1; ev += old2[j[1]]; continue
            if not r: stat[j[0] + '_zero'] += 1; zero.append('ZERO ' + j[1]); nopg.add(j[1])
            if r: nopg.discard(j[1])
            if j[1] in REP:
                for e in r: e['v'] = 3
            stat[j[0] + '_pages'] += 1; stat[j[0] + '_events'] += len(r); ev += r
            if n % 200 == 0: print('sched', n, len(ev), round((time.time() - T0) / 60, 1), 'min', flush=True)
    for a, z, s, c in OLY:
        ev.append({'lg': 'olympics', 'k': 'opening ceremony', 'd': a, 's': s, 'city': c, 'y': int(a[:4])}); ev.append({'lg': 'olympics', 'k': 'closing ceremony', 'd': z, 's': s, 'city': c, 'y': int(z[:4])})
    for y, md in NCAAB.items():
        d = datetime.date(y, int(md[:2]), int(md[3:]))
        ev.append({'lg': 'ncaab', 'k': 'championship', 'd': d.isoformat(), 'y': y}); ev.append({'lg': 'ncaab', 'k': 'final four', 'd': (d - datetime.timedelta(2)).isoformat(), 'y': y})
    for y in range(1984, 2005):
        d = datetime.date.fromisoformat(D['derby'](y))
        ev.append({'lg': 'horse', 'k': 'preakness', 'd': (d + datetime.timedelta(14)).isoformat(), 'y': y}); ev.append({'lg': 'horse', 'k': 'belmont', 'd': (d + datetime.timedelta(35)).isoformat(), 'y': y})
    print('SCHED STATS', sorted(stat.items()))
    print('TV AND TIME', sorted(collections.Counter(e['lg'] + ('_net' if e.get('net') else '') + ('_st' if e.get('st') else '') for e in ev).items()))
    random.seed(5)
    for z in random.sample(zero, min(60, len(zero))): print(' ', z)
    by = collections.defaultdict(list)
    for e in ev: by[e['lg']].append(e)
    for lg, L in sorted(by.items()):
        print('LEAGUE', lg, len(L), 'events', sorted(collections.Counter(e['d'][:4] for e in L).items()))
        for e in random.sample(L, min(8, len(L))): print('   ', json.dumps(e, ensure_ascii=False)[:230])
    with gzip.open(SCHF, 'wt', encoding='utf-8') as f: json.dump(ev, f, ensure_ascii=False, separators=(',', ':'))
    json.dump(sorted(nopg), open(NOPG, 'w'), ensure_ascii=False)
    with gzip.open(PGF, 'wt', encoding='utf-8') as f: json.dump(pages, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print('page cache', len(pages), 'pages', round(os.path.getsize(PGF) / 1e6, 1), 'MB', flush=True)
    return ev
PSCH = os.path.join(PARTS, 'sportsched.json.gz')
def load_sched():
    if os.path.exists(PSCH) and not (REBUILD and MODE == 'plan'): return json.load(gzip.open(PSCH, 'rt', encoding='utf-8'))
    if os.path.exists(SCHF) and not REBUILD: ev = json.load(gzip.open(SCHF, 'rt', encoding='utf-8'))
    else: ev = build()
    if MODE == 'plan':
        with gzip.open(PSCH, 'wt', encoding='utf-8') as f: json.dump(ev, f, ensure_ascii=False, separators=(',', ':'))
    return ev
class Sched:
    def __init__(s, ev):
        s.pair = collections.defaultdict(list); s.one = collections.defaultdict(list); s.key = collections.defaultdict(list); s.box = []; s.race = collections.defaultdict(list); s.ser = collections.defaultdict(list)
        seen = {}
        for e in ev:
            lg = e['lg']
            if 'a' in e and lg != 'boxing':
                if lg in ('nba', 'nhl') and e['d'][5:7] < '04': continue
                if lg == 'nfl' and e['d'][5:7] in ('07', '08') and e['d'] != '1997-08-31': continue
                k = (lg, e['d'], frozenset((e['a'], e['h'])))
                if k in seen:
                    for fk in ('net', 'st'):
                        if e.get(fk) and not seen[k].get(fk): seen[k][fk] = e[fk]
                    continue
                seen[k] = e
                s.pair[(lg, frozenset((e['a'], e['h'])))].append(e); s.one[(lg, e['a'])].append(e); s.one[(lg, e['h'])].append(e)
                if e.get('ser'): s.ser[(lg, e['ser'], int(e['d'][:4]))].append(e)
            elif lg == 'boxing': s.box.append(e)
            elif lg == 'racing': s.race[e['y']].append(e)
            else: s.key[(lg, e.get('k'), e.get('y') or e.get('se'))].append(e)
ROUND = [(r' (wild ?card|wildcard) ', 'wild'), (r' (divisional|division playoff|divisional playoff) ', 'div'), (r' (afc|nfc) (championship|title game|champ) ', 'conf'), (r' conference championship ', 'conf')]
def rd_ok(e, rd):
    r = (e.get('rd') or '').lower()
    if rd == 'wild': return 'wild' in r
    if rd == 'div': return 'div' in r
    if rd == 'conf': return 'conf' in r or 'champ' in r
    return False
def label(e, lg):
    a, h = e['a'].upper(), e['h'].upper()
    y = e.get('se') or e.get('y') or int(e['d'][:4])
    if lg == 'nfl':
        if e.get('wk'): return '%d NFL WEEK %d: %s AT %s' % (y, e['wk'], a, h)
        return '%d NFL %s: %s AT %s' % (y, (e.get('rd') or 'PLAYOFF').upper(), a, h)
    if lg == 'ncaaf': return '%d COLLEGE FOOTBALL: %s %s %s' % (y, a, 'VS' if e.get('n') else 'AT', h)
    if lg == 'ncaab': return '%d %s: %s %s %s' % (y, ('NCAA ' + e['rd'].upper() if e.get('rd') and e['rd'] != 'ncaa' else 'NCAA TOURNAMENT' if e.get('rd') else 'COLLEGE BASKETBALL'), a, 'VS' if e.get('n') else 'AT', h)
    sn = {'ws': 'WORLD SERIES', 'alcs': 'ALCS', 'nlcs': 'NLCS', 'alds': 'ALDS', 'nlds': 'NLDS', 'finals': 'NBA FINALS' if lg == 'nba' else 'STANLEY CUP FINALS', 'cf': 'CONFERENCE FINALS', 'sf': 'PLAYOFFS', 'r1': 'PLAYOFFS'}.get(e.get('ser', ''), 'PLAYOFFS')
    return '%d %s%s: %s AT %s' % (y, sn, ' GAME %d' % e['g'] if e.get('g') else '', a, h)
WOMEN = r' (women|womens|ladies|graf|navratilova|evert|seles|hingis|williams|sabatini|sanchez|davenport|capriati|henin|clijsters|pierce|novotna|mandlikova|martinez) '
MEN = r' (men|mens|gentlemen|sampras|agassi|becker|edberg|lendl|mcenroe|connors|wilander|courier|federer|roddick|hewitt|ivanisevic|rafter|kuerten|chang|stich|cash|kafelnikov|safin|muster|bruguera|korda|krajicek|moya|costa|ferrero|gaudio|philippoussis|nalbandian) '
DOCRX = r' (nfl films|season in review|year in review|greatest games|nfl yearbook|team yearbook|highlight film|world series film|hardwood classics|sportscentury|this week in baseball|game of the week|inside the nfl|nfl follies|football follies|nba superstars|nfl s greatest|greatest moments|nfl presents|road to the super bowl|nfl crunch course|super bloopers|baseball s greatest|super bowl highlights|the movie|championship video|official video|first \d+ years|nascar video|the history of|unauthorized history|classic confrontations|video magazine|thrills and spills) '
REBX = r' (marathon|rebroadcast|re broadcast|re air|re aired|reair|reairing|espn classic|classic sports network|nfl network|mlb network|nba tv|encore presentation) '
RSTOP = set('nascar series cup grand national craftsman truck trucks race full raw feed satellite the at of presented by and winston busch bgn nbs ncts nwcs supertruck international speedway raceway motor classic original broadcast'.split())
def racefind(SC, nt, ys, sr, ctx, net):
    c = []
    for y in ys:
        L = [e for e in SC.race.get(y, []) if (sr is None and e.get('sr') != 'cart') or e.get('sr', '') == sr]
        if sr == 'cart':
            rn = re.search(r' (?:round|rd|rnd) (\d{1,2}) ', nt)
            words = set(w for w in nt.split() if len(w) > 3 and not w.isdigit() and w not in RSTOP and w not in ('cart', 'espn', 'round', 'indycar', 'champ', 'world', 'grand', 'prix', 'indy', 'full', 'race', 'broadcast', 'ppg'))
            ov = lambda e: len(words & set((e['k'] + ' ' + e.get('tr', '')).split()))
            cc = [e for e in L if rn and e.get('rn') == int(rn.group(1)) and (ov(e) or not words)]
            if not cc:
                mx = max([ov(e) for e in L] or [0])
                cc = [e for e in L if mx and ov(e) == mx]
            c += cc; continue
        hits = []
        for e in L:
            k = e['k']; kt = k.split()
            v = [k] + ([' '.join(kt[1:])] if kt[0] == 'the' and len(kt) >= 3 else []) + ([' '.join(kt[-3:])] if len(kt) >= 4 and not kt[-1].isdigit() else [])
            hl = max([len(x) for x in v if len(x) >= 7 and (' ' + x + ' ') in nt] or [0])
            if hl: hits.append((hl, e))
        if hits:
            mx = max(h[0] for h in hits); c += [e for l, e in hits if l == mx]; continue
        g = re.search(r' ([a-z]+) at the glen ', nt)
        if g:
            cc = [e for e in L if e['k'].endswith('at the glen')]
            if cc: c += cc; continue
        best = 0; cc = []
        for m in re.finditer(r'(?= ((?:[a-z0-9]+ ){1,4})([1-9]\d\d)(?:k|s)? )', nt):
            num = m.group(2); seq = m.group(1).split(); W = set(w for w in seq if w not in RSTOP and not w.isdigit() and len(w) > 2)
            for e in L:
                kt = e['k'].replace('125s', '125').split()
                if num not in [t.rstrip('k') for t in kt]: continue
                sc = 2 * len(W & set(kt)) + (10 if (' ' + seq[-1] + ' ' + num) in (' ' + ' '.join(t.rstrip('k') for t in kt) + ' ') and not seq[-1].isdigit() else 0) + (1 if W & set(e.get('tr', '').split()) else 0)
                if sc > best: best = sc; cc = [e]
                elif sc == best and sc: cc.append(e)
        c += cc
    if sr is None and len(set(e['d'] for e in c)) > 1: c = [e for e in c if not e.get('sr')] or c
    def narrow(c, fn):
        if len(set(e['d'] for e in c)) > 1:
            c2 = [e for e in c if fn(e)]
            if c2: return c2
        return c
    TW = ('speedway', 'international', 'motor', 'raceway', 'superspeedway', 'park', 'motorsports', 'fairgrounds', 'state', 'road', 'course', 'north', 'south', 'city', 'downs', 'mile')
    for tx in (nt, ctx):
        c = narrow(c, lambda e: e.get('tr') and any((' ' + w + ' ') in tx for w in e['tr'].split() if len(w) > 3 and w not in TW))
    mon = re.search(r' (' + MONS + r') ', nt)
    if mon: c = narrow(c, lambda e: int(e['d'][5:7]) == MON[mon.group(1)[:3]])
    if net: c = narrow(c, lambda e: e.get('net') == net)
    return c
def resolve(SC, title, desc='', ctx=''):
    nt = norm(title)
    for a, b in ((' n l c s ', ' nlcs '), (' a l c s ', ' alcs '), (' n l d s ', ' nlds '), (' a l d s ', ' alds '), (' final 4 ', ' final four ')): nt = nt.replace(a, b)
    r = sport(title, desc, '1994-06-18') or sport(title, desc, '1994-10-15')
    if not r and re.search(r' (?:[a-z]+ ){1,2}[1-9]\d\dk? ', nt) and re.search(r' (nascar|winston cup|busch|craftsman truck|speedway|raceway) ', nt + norm(desc[:200])) and not re.search(r' (indy|indianapolis|daytona) 500 ', nt): r = ('racing', 'AUTO RACING')
    if not r: return None, 'nosport'
    lg = r[0]
    if lg == 'ncaaf' and re.search(r' (ncaa championship|ncaa finals?|final four|regional|regionals|region|ncaa tournament|basketball|semi ?finals?|semi|sweet 16|sweet sixteen|elite 8|elite eight|midwest|mideast|southeast|2nd rd|1st rd|second round|first round) ', nt) and not re.search(r' (football|bowl) ', nt): lg = 'ncaab'
    if lg == 'golf' and ' us open ' in nt and (re.search(MEN, nt) or re.search(WOMEN, nt) or re.search(r' (tennis|qf|sf|quarter ?finals?|semi ?finals?|mens|womens|flushing) ', nt)): lg = 'tennis'
    ys = sorted(set(int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)))
    m = re.search(r' (19[89]\d|200[0-3]) (\d\d) ', nt)
    if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100: ys = [int(m.group(1)) + 1] if lg in ('ncaab', 'nba', 'nhl') else sorted(set(ys) | {int(m.group(1)), int(m.group(1)) + 1})
    if not ys:
        m = re.search(r' (?:playoffs?|finals|nba|nfl|mlb|ws|world series|alcs|nlcs|alds|nlds) (8[4-9]|9\d|0[0-4]) ', nt)
        if m: ys = [int(('19' if m.group(1) > '50' else '20') + m.group(1))]
    if not ys: return None, 'noyear'
    if re.search(REBX, nt): return None, 'rebroadcast'
    for n, w in enumerate(('one', 'two', 'three', 'four', 'five', 'six', 'seven')): nt = nt.replace(' game ' + w + ' ', ' game %d ' % (n + 1))
    rg = re.search(r' r(\d) ?g(\d) ', nt)
    g = re.search(r' (?:game|gm|g) ?(\d)(?: |$)', nt); g = int(rg.group(2)) if rg else int(g.group(1)) if g else None
    wk = re.search(r' (?:week|wk) ?(\d{1,2}) ', nt); wk = int(wk.group(1)) if wk else None
    mon = re.search(r' (' + MONS + r') ', nt); mon = MON[mon.group(1)[:3]] if mon else None
    def one(c, why):
        ds = set(e['d'] for e in c)
        if len(ds) == 1: return c[0], None
        return None, why + ('_none' if not c else '_multi')
    T = tfind2(lg, nt, ys)
    if len(T) < 2 and ctx:
        T2 = tfind2(lg, norm(ctx), ys)
        if len(T2) <= 2:
            for a in T2:
                if len(T) < 2 and not any(set(a) & set(o) for o in T): T.append(a)
    tm = [a[0] for a in T]
    def pairs():
        c = []
        if len(T) >= 2:
            for a in T[0]:
                for b in T[1]: c += SC.pair.get((lg, frozenset((a, b))), [])
        return c
    def ones():
        return [e for a in (T[0] if T else []) for e in SC.one.get((lg, a), [])]
    if lg in ('nfl', 'ncaaf'):
        if lg == 'ncaaf':
            b = re.search(r' ([a-z]+(?: [a-z]+)?) bowl ', nt)
            if b and len(tm) < 2:
                name = b.group(1).split()[-1] + ' bowl'; c = []
                for (lg2, k, se), L in SC.key.items():
                    if lg2 == 'ncaaf' and k and k.endswith(name) and any(int(e['d'][:4]) in ys for e in L): c += [e for e in L if int(e['d'][:4]) in ys]
                c = [e for e in c if not tm or not e.get('tm') or set(tm) <= set(e['tm'])]
                e, why = one(c, 'bowl')
                if e: return {'ad': e['d'], 'ev': '%s %s' % (e['d'][:4] if e['d'][5:7] == '01' else e['se'], e['k'].upper()), 'ct': 'ncaaf', 'row': e}, None
                return None, why
        if not tm: return None, 'noteam'
        rd = next((v for p, v in ROUND if re.search(p, nt)), None)
        if len(tm) >= 2: c = pairs()
        else: c = ones() if (wk or rd) else []
        if len(tm) < 2 and not (wk or rd): return None, 'oneteam'
        c = [e for e in c if e['se'] in ys or int(e['d'][:4]) in ys]
        if wk and any(e.get('wk') == wk and e['se'] in ys for e in c): c = [e for e in c if e.get('wk') == wk and e['se'] in ys]
        elif wk and len(tm) < 2: c = []
        if rd: c = [e for e in c if rd_ok(e, rd)]
        if mon and len(set(e['d'] for e in c)) > 1: c = [e for e in c if int(e['d'][5:7]) == mon]
        if len(set(e['d'] for e in c)) > 1 and len(ys) == 1:
            c2 = [e for e in c if e['se'] == ys[0]]
            if c2: c = c2
        if len(set(e['d'] for e in c)) > 1 and len(T) >= 2 and re.search(r' (at|@) ', nt):
            c2 = [e for e in c if e['a'] in T[0]]
            if c2: c = c2
        e, why = one(c, lg + ('_wk' if wk else '_rd' if rd else '_pair'))
        if e: return {'ad': e['d'], 'ev': label(e, lg), 'ct': lg, 'row': e, 'net': e.get('net', '')}, None
        return None, why
    if lg in ('mlb', 'nba', 'nhl'):
        if ' all star ' in nt:
            if re.search(r' (slam dunk|dunk contest|three point|3 point|rookie|saturday|weekend|skills|legends|home run derby|celebrity|shootout|old timers) ', nt): return None, 'allstar_side'
            for y in ys:
                L = SC.key.get((lg, 'all star game', y))
                if L: return {'ad': L[0]['d'], 'ev': '%d %s ALL-STAR GAME' % (y, lg.upper()), 'ct': lg, 'row': L[0]}, None
            return None, 'allstar_none'
        if lg == 'mlb' and re.search(r' (no hitter|no hit|perfect game) ', nt):
            c = [e for (l2, k, y), L in SC.key.items() if l2 == 'mlb' and k == 'no hitter' for e in L if int(e['d'][:4]) in ys and (not tm or set(tm) & set(e['tm'])) and any(w in e['who'] for w in nt.split() if len(w) > 4 and w not in ('hitter', 'perfect', 'pitches', 'throws', 'against'))]
            e, why = one(c, 'nohit')
            if e: return {'ad': e['d'], 'ev': '%s NO-HITTER: %s' % (e['d'][:4], ' VS '.join(t.upper() for t in e['tm'])), 'ct': 'mlb', 'row': e}, None
            return None, why
        ser = None
        if lg == 'mlb':
            for p, v in ((r' (world series|ws) ', 'ws'), (r' (alcs|american league championship|al championship) ', 'alcs'), (r' (nlcs|national league championship|nl championship) ', 'nlcs'), (r' (alds|american league division|al division) ', 'alds'), (r' (nlds|national league division|nl division) ', 'nlds')):
                if re.search(p, nt): ser = v; break
        elif re.search(r' (ecf|wcf|conference finals?|east finals?|eastern finals?|west finals?|western finals?|r3) ', nt) or (rg and rg.group(1) == '3'): ser = 'cf'
        elif re.search(r' (nba finals|stanley cup finals?|cup finals?) ', nt) or (' finals ' in nt and ' conference ' not in nt and ' division ' not in nt): ser = 'finals'
        elif re.search(r' (ecsf|wcsf|conference semi ?finals?|semi ?finals?|semis|second round|2nd round|r2) ', nt) or (rg and rg.group(1) == '2'): ser = 'sf'
        elif re.search(r' (first round|1st round|opening round|r1) ', nt) or (rg and rg.group(1) == '1'): ser = 'r1'
        if not g: return None, lg + '_nogame'
        c = []
        if len(T) >= 2: c = [e for e in pairs() if int(e['d'][:4]) in ys and e.get('g') == g and (not ser or not e.get('ser') or e['ser'] == ser)]
        elif ser:
            for y in ys: c += [e for e in SC.ser.get((lg, ser, y), []) if e.get('g') == g and (not T or e['a'] in T[0] or e['h'] in T[0])]
            if (ser in ('alds', 'nlds') or (lg != 'mlb' and ser != 'finals')) and not T: c = []
        else: return None, lg + '_noseries'
        e, why = one(c, lg + '_ser')
        if e: return {'ad': e['d'], 'ev': label(e, lg), 'ct': lg, 'row': e}, None
        return None, why
    if lg == 'boxing':
        fs = [f for f in dict.fromkeys(FIGHT.findall(nt))]
        if len(fs) < 2: return None, 'box_one'
        c = [e for e in SC.box if int(e['d'][:4]) in ys and any((' ' + e['a'] + ' ').find(' ' + f + ' ') >= 0 for f in fs) and any((' ' + e['h'] + ' ').find(' ' + f + ' ') >= 0 for f in fs if (' ' + e['a'] + ' ').find(' ' + f + ' ') < 0)]
        e, why = one(c, 'box')
        if e: return {'ad': e['d'], 'ev': '%s BOXING: %s VS %s' % (e['d'][:4], e['a'].upper(), e['h'].upper()), 'ct': 'boxing', 'row': e}, None
        return None, why
    if lg == 'racing':
        if re.search(r' (qualifying|happy hour|practice|pole day|time trials|awards banquet|awards ceremony|rain out|rainout) ', nt) or (re.search(r' qualifiers? ', nt) and not re.search(r' (twin|gatorade) 125', nt)): return None, 'race_session'
        nd = nt + norm(desc[:200])
        sr = None
        for tx in (nt, nd):
            if re.search(r' (cart|indycar|indy car|champ car) ', tx) and not re.search(r' (nascar|busch|winston cup) ', tx): sr = 'cart'
            elif re.search(r' (truck|trucks|supertruck|ncts|cts) ', tx): sr = 'truck'
            elif re.search(r' (busch grand national|busch series|busch gn|bgn|grand national|nbs|bgns) ', tx): sr = 'busch'
            elif re.search(r' (winston cup|nextel cup|cup series|nwcs) ', tx): sr = ''
            elif re.search(r' (busch north|bgnn|modified|modifieds|southwest tour|winston west|featherlite|dash series|arca|irl|formula one|formula 1|nhra|imsa|trans am|iroc|winter heat|late model|sprint car|world of outlaws) ', tx): return None, 'race_otherseries'
            if sr is not None: break
        c = racefind(SC, nt, ys, sr, norm(desc[:200]), netof(title, ''))
        if not c and not re.search(r' [1-9]\d\dk?s? ', nt) and sr != 'cart': return None, 'race_noname'
        e, why = one(c, 'race')
        if e: return {'ad': e['d'], 'ev': '%s %s' % (e['d'][:4], e['k'].upper()), 'ct': 'racing', 'row': e}, None
        return None, why
    if lg == 'golf':
        k = 'masters' if ' masters ' in nt else 'pga championship' if ' pga championship ' in nt else 'british open' if ' british open ' in nt or ' open championship ' in nt else 'us open golf' if ' us open ' in nt else None
        if not k or re.search(r' (highlights|preview|practice|par 3|skins|senior|lpga|womens|vhs|video|film|dvd) ', nt): return None, 'golf_nokey'
        rn = re.search(r' (first|1st|second|2nd|third|3rd|final|fourth|4th) round ', nt) or re.search(r' round (\d) ', nt)
        off = 3
        if rn: off = {'first': 0, '1st': 0, '1': 0, 'second': 1, '2nd': 1, '2': 1, 'third': 2, '3rd': 2, '3': 2}.get(rn.group(1), 3)
        for y in ys:
            L = SC.key.get(('golf', k, y))
            if L:
                d = (datetime.date.fromisoformat(L[0]['d']) + datetime.timedelta(off)).isoformat()
                return {'ad': d, 'ev': '%d %s %s' % (y, k.replace(' golf', '').upper(), ['FIRST ROUND', 'SECOND ROUND', 'THIRD ROUND', 'FINAL ROUND'][off]), 'ct': 'golf', 'row': L[0]}, None
        return None, 'golf_none'
    if lg == 'tennis':
        k = 'wimbledon' if ' wimbledon ' in nt else 'french open' if ' french open ' in nt or ' roland garros ' in nt else 'australian open' if ' australian open ' in nt else 'us open tennis' if ' us open ' in nt else None
        if not k or not re.search(r' finals? ', nt) or re.search(r' (semi ?finals?|quarter ?finals?|doubles|juniors?) ', nt): return None, 'tennis_nofinal'
        w, mn = bool(re.search(WOMEN, nt)), bool(re.search(MEN, nt))
        if w == mn: return None, 'tennis_gender'
        for y in ys:
            L = SC.key.get(('tennis', k, y))
            if L and L[0].get('d2'):
                d = datetime.date.fromisoformat(L[0]['d2'])
                if w: d -= datetime.timedelta(1)
                return {'ad': d.isoformat(), 'ev': '%d %s %s FINAL' % (y, k.replace(' tennis', '').upper(), "WOMEN'S" if w else "MEN'S"), 'ct': 'tennis', 'row': L[0]}, None
        return None, 'tennis_none'
    if lg == 'olympics':
        k = 'opening ceremony' if re.search(r' opening ceremon', nt) else 'closing ceremony' if re.search(r' closing ceremon', nt) else None
        if re.search(r' opening ', nt) and re.search(r' closing ', nt): return None, 'oly_both'
        dn = re.search(r' day (\d{1,2}) ', nt)
        if not k and dn and 1 <= int(dn.group(1)) <= 17:
            c = [e for y in ys for e in SC.key.get(('olympics', 'opening ceremony', y), [])]
            if len(c) > 1: c = [e for e in c if (' ' + e['s'] + ' ') in nt or (' ' + e['city'] + ' ') in nt]
            if len(c) == 1:
                d = (datetime.date.fromisoformat(c[0]['d']) + datetime.timedelta(int(dn.group(1)) - 1)).isoformat()
                return {'ad': d, 'ev': '%s %s OLYMPICS DAY %d' % (d[:4], c[0]['s'].upper(), int(dn.group(1))), 'ct': 'olympics', 'row': c[0]}, None
        if not k: return None, 'oly_nocer'
        c = [e for y in ys for e in SC.key.get(('olympics', k, y), [])]
        if len(c) > 1: c = [e for e in c if (' ' + e['s'] + ' ') in nt or (' ' + e['city'] + ' ') in nt]
        e, why = one(c, 'oly')
        if e: return {'ad': e['d'], 'ev': '%s %s OLYMPICS %s' % (e['d'][:4], e['s'].upper(), k.upper()), 'ct': 'olympics', 'row': e}, None
        return None, why
    if lg == 'ncaab' and len(T) == 2 and not re.search(r' (womens|women|nit|hockey|baseball|softball) ', nt):
        c = [e for e in pairs() if e.get('se') in ys or int(e['d'][:4]) in ys]
        rd = next((v for p, v in CBR if re.search(' (' + p + ')', nt)), None)
        if not rd and re.search(r' (midwest|mideast|southeast|east|west|south|regional|region) (semi ?finals?|semis?) ', nt): rd = 'sweet sixteen'
        if not rd and re.search(r' (midwest|mideast|southeast|east|west|south|regional|region) finals? ', nt): rd = 'elite eight'
        if not rd and re.search(r' (2nd|second) (rd|round) ', nt): rd = 'second round'
        if not rd and re.search(r' (1st|first) (rd|round) ', nt): rd = 'first round'
        if rd: c = [e for e in c if e.get('rd') == rd]
        elif re.search(r' (ncaa|tournament|regional|regionals) ', nt) and any(e.get('rd') for e in c): c = [e for e in c if e.get('rd')]
        if mon and len(set(e['d'] for e in c)) > 1: c = [e for e in c if int(e['d'][5:7]) == mon]
        if len(set(e['d'] for e in c)) > 1 and re.search(r' (at|@) ', nt):
            c2 = [e for e in c if e['a'] in T[0] and not e.get('n')]
            if c2: c = c2
        e, why = one(c, 'ncaab_pair')
        if e: return {'ad': e['d'], 'ev': label(e, lg), 'ct': lg, 'row': e}, None
    if lg == 'ncaab':
        k = 'final four' if re.search(r' (final four|national semi ?finals?) ', nt) and not re.search(r' (national championship|championship game|title game) ', nt) else 'championship' if re.search(r' (national championship|championship game|title game|ncaa championship|ncaa final|ncaa finals) ', nt) else None
        if not k or re.search(r' (big east|acc|sec|big ten|big 8|big eight|pac 10|conference|nit|womens|women|regional|hockey|football) ', nt): return None, 'ncaab_nokey'
        for y in ys:
            L = SC.key.get(('ncaab', k, y))
            if L: return {'ad': L[0]['d'], 'ev': '%d NCAA %s' % (y, 'FINAL FOUR' if k == 'final four' else 'CHAMPIONSHIP GAME'), 'ct': 'ncaab', 'row': L[0]}, None
        return None, 'ncaab_none'
    if lg == 'horse':
        k = 'preakness' if ' preakness ' in nt else 'belmont' if ' belmont stakes ' in nt else None
        if not k: return None, 'horse_nokey'
        for y in ys:
            L = SC.key.get(('horse', k, y))
            if L: return {'ad': L[0]['d'], 'ev': '%d %s STAKES' % (y, k.upper()), 'ct': 'horse', 'row': L[0]}, None
        return None, 'horse_none'
    return None, 'other_' + lg
BADW = r' (highlights?|condensed|recap|preview|pregame|pre game|postgame|post game|halftime|radio|audio|simulation|simulated|coaches film|all 22|press conference|interview|trailer|promo|commercials?|mix|tribute|top 10|plays of|mic d up|bloopers|parade|rally|celebration|documentary|every touchdown|every play|all touchdowns) '
LGK = {'nfl': 'NFL FOOTBALL', 'nba': 'NBA BASKETBALL', 'mlb': 'MLB BASEBALL', 'nhl': 'NHL HOCKEY', 'ncaaf': 'COLLEGE FOOTBALL', 'ncaab': 'COLLEGE BASKETBALL', 'boxing': 'BOXING', 'racing': 'AUTO RACING', 'golf': 'GOLF', 'tennis': 'TENNIS', 'olympics': 'OLYMPIC GAMES', 'horse': 'HORSE RACING'}
def classify(SC, title, ident, dfield, desc):
    nt = norm(title)
    if re.search(DOCRX, nt) and not re.search(r' (trailer|promo|commercial|podcast|video game|gameplay|madden|reaction|review of) ', nt) and not re.search(X_FOR, title.lower()) and not re.search(r'[^\x00-\xff]', title):
        yy = re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt) or re.findall(r'^' + YR, str(dfield or ''))
        if yy and not re.search(r'(?<!\d)(19[0-7]\d|198[0-3]|200[5-9]|20[1-3]\d)(?!\d)', nt): return {'ct': 'sportsdoc', 'k': 'SPORTS FILMS', 'ad': '', 'ev': '', 'e': int(yy[0]), 'min': 1200, 'net': ''}, None
    if not ok_title(title): return None, 'junk'
    if re.search(GAMEX, nt) or re.search(FORX, nt): return None, 'junk'
    if re.search(BADW, nt): return None, 'badword'
    if find_date(title, ident, dfield, desc)[0]: return None, 'dated'
    r, why = resolve(SC, title, desc)
    if not r:
        if why in ('nosport', 'noyear'): return None, why
        r0 = sport(title, desc, '1994-06-18') or sport(title, desc, '1994-10-15')
        ys = [int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)]
        if not r0 or not ys: return None, why
        ct0 = 'tennis' if str(why).startswith('tennis') else r0[0]
        return {'ct': ct0, 'k': LGK.get(ct0, 'SPORTS'), 'ad': '', 'ev': '', 'e': ys[0], 'min': 2400, 'net': netof(title, desc) or known_net(ct0, nt, '', ys[0]), 'keep': 'maybe', 'why': 'outside 1984-2004' if max(ys) < 1984 else 'day unresolved: ' + str(why)}, None
    return {'ct': r['ct'], 'k': LGK.get(r['ct'], 'SPORTS'), 'ad': r['ad'], 'ev': r['ev'], 'e': int(r['ad'][:4]), 'min': 2400, 'net': netof(title, '') or r['row'].get('net') or r.get('net') or netof(title, desc) or known_net(r['ct'], nt, r['ad'], 0), 'st': r['row'].get('st', ''), 'row': r['row']}, None
LTAG = {'nfl': 'nfl', 'nba': 'nba', 'mlb': 'mlb', 'nhl': 'nhl', 'racing': 'nascar', 'ncaaf': 'college football', 'ncaab': 'ncaa basketball'}
GAMEX = r' (madden|nba live|playstation|ps2|ps3|ps 2|ps 3|xbox|nintendo|how to install|rebuilt mod|video game|gameplay|nba 2k\d*|nhl 2004 rebuilt|tournament of legends|qb club|quarterback club|nfl 2k\d*|nfl 2 k \d|ncaa football (19|20)\d\d|nascar thunder|nascar heat|tiger woods pga tour|action pc|retro replay|lets just|lets play|going buoy|nfl blitz|nfl gameday|nfl fever|nba jam|nba street|triple play|mvp baseball|high heat|mirror match|historic team tournament|playthrough|longplay|talking dog) '
def fdate(nm, ctx):
    ds = D['dates_in'](nm)
    if ds: return ds[0][1]
    d = pdate(nm)
    if d and '1960' < d < '2006': return d
    y1 = set(re.findall(r'(?<!\d)' + YR + r'(?!\d)', nm))
    m = re.search(r'\b(' + MONS + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?![\d:])', nm, re.I)
    if m and len(y1) == 1 and not re.search(r'(?<!\d)(19[0-7]\d|198[0-3]|200[5-9]|20[1-3]\d)(?!\d)', nm):
        d = iso(list(y1)[0], MON[m.group(1).lower()[:3]], m.group(2))
        if d: return d
    nm = re.sub(r'\s*/\s*', '/', nm)
    ys = set(re.findall(r'(?<!\d)((?:19|20)\d\d)(?!\d)', nm + ' ' + ctx))
    for a, z in re.findall(r'(?<!\d)((?:19|20)\d\d)\s*[-–]\s*((?:19|20)\d\d)(?!\d)', ctx): ys |= set(str(y) for y in range(int(a), int(z) + 1))
    for m in re.finditer(r'(?<!\d)((?:19|20)\d\d)[ ./-](\d{1,2})[ ./-](\d{1,2})(?!\d)', nm):
        d = iso(m.group(1), m.group(2), m.group(3))
        if d and '1960' < d < '2006': return d
    for m in re.finditer(r'(?<!\d)(?=(\d{1,2})[ ./-](\d{1,2})[ ./-]((?:19|20)\d\d|\d\d)(?!\d))', nm):
        y = m.group(3)
        if len(y) == 2:
            y = ('19' if int(y) >= 60 else '20') + y
            if y not in ys: continue
        d = iso(y, m.group(1), m.group(2))
        if d and '1960' < d < '2006': return d
    return None
ONET = {(1984, 'winter'): 'abc', (1984, 'summer'): 'abc', (1988, 'winter'): 'abc', (1988, 'summer'): 'nbc', (1992, 'winter'): 'cbs', (1992, 'summer'): 'nbc', (1994, 'winter'): 'cbs', (1996, 'summer'): 'nbc', (1998, 'winter'): 'cbs', (2000, 'summer'): 'nbc', (2002, 'winter'): 'nbc', (2004, 'summer'): 'nbc'}
def known_net(ct, nt, ad, e):
    y = int(ad[:4]) if ad else int(e or 0)
    if ct == 'nfl' and ' super bowl ' in nt and ad: return SBNET.get(ad, '')
    if ct == 'racing' and ' daytona 500 ' in nt and ad and ad[5:7] == '02': return 'cbs' if y <= 2000 else 'fox' if y in (2001, 2003) else 'nbc'
    if ct == 'racing' and re.search(r' (indy|indianapolis) 500 ', nt) and ad and ad[5:7] == '05': return 'abc'
    if ct == 'horse' and ' kentucky derby ' in nt: return 'abc' if y <= 2000 else 'nbc'
    if ct == 'ncaab' and ad and ad[5:7] in ('03', '04') and re.search(r' (ncaa|sweet 16|sweet sixteen|elite 8|elite eight|final four|final 4|regional|regionals|national championship|national semi ?finals?) ', nt) and not re.search(r' (nit|women|womens|softball|baseball|hockey|football) ', nt):
        if y >= 1991 or re.search(r' (final four|final 4|championship|national semi ?finals?) ', nt): return 'cbs'
    if ct == 'olympics':
        se = 'winter' if ' winter ' in nt else 'summer' if ' summer ' in nt else ''
        c = set(v for (yy, ss), v in ONET.items() if yy == y and (not se or ss == se))
        if len(c) == 1: return list(c)[0]
    if ct == 'golf': return 'cbs' if ' masters ' in nt else ('abc' if y <= 1994 else 'nbc') if ' us open ' in nt else ('abc' if y <= 1990 else 'cbs') if ' pga championship ' in nt else 'abc' if re.search(r' (british open|open championship) ', nt) else ''
    if ct == 'tennis' and re.search(r' finals? ', nt): return 'nbc' if re.search(r' (wimbledon|french open|roland garros) ', nt) else 'cbs' if ' us open ' in nt else 'espn' if ' australian open ' in nt else ''
    return ''
FORX = r' (etapa|juego|finales nba|foreign telecasts?|en espanol|radio coverage|radio broadcasts?|radio network|les classiques|narracion|swedish commentary|uk vhs|german commentary|french commentary|spanish commentary|comentarios|relato) '
SBNET = dict(zip(D['SB'].values(), 'cbs abc nbc cbs abc nbc cbs abc cbs nbc nbc abc nbc fox nbc fox abc cbs fox abc cbs'.split()))
def rowat(SC, lg, d, nt):
    if lg in ('nfl', 'ncaaf', 'ncaab', 'mlb', 'nba', 'nhl'):
        c = [e for a in tfind2(lg, nt, (int(d[:4]),)) for t in a for e in SC.one.get((lg, t), []) if e['d'] == d]
        if c: return c[0], label(c[0], lg)
        if ' all star ' in nt:
            for e in SC.key.get((lg, 'all star game', int(d[:4])), []):
                if e['d'] == d: return e, '%s %s ALL-STAR GAME' % (d[:4], lg.upper())
    if lg == 'racing':
        c = [e for e in SC.race.get(int(d[:4]), []) if e['d'] == d]
        c2 = [e for e in c if (' ' + e['k'] + ' ') in nt] or (c if len(c) == 1 and re.search(r' [1-9]\d\dk? ', nt) and c[0]['k'].split()[-1].rstrip('k') in nt.split() else [])
        if len(c2) == 1:
            e = c2[0]; return e, '%s %s' % (d[:4], e['k'].upper())
    return None, ''
def minefiles(SC):
    p = os.path.join(OUT, 'mine.json.gz')
    if not os.path.exists(p): return [], collections.Counter()
    out = []; C = collections.Counter()
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if not isinstance(x, dict) or x.get('ct') != 'sportsundated' or not x.get('f'): continue
        C['items'] += 1
        gt = x.get('t') or ''; ctx = gt + ' ' + str(x.get('s') or ''); multi = len(x['f']) > 1
        gy = sorted(set(int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', norm(gt))))
        gn = set({'wtbs': 'tbs', 'usa network': 'usa', 'espn2': 'espn'}.get(v, v) for v in re.findall(D['NETRX'], gt.lower()))
        groups = {}
        for f in x['f']:
            C['files'] += 1
            nm = ' '.join(re.sub(r'\.ia$', '', re.sub(r'\.[A-Za-z0-9]{2,4}$', '', f[0])).replace('_', ' ').split())
            if not multi or not re.search(r'[A-Za-z]{4}', nm): nm = gt if not multi else nm
            nt = norm(nm)
            if re.search(GAMEX, nt) or re.search(GAMEX, norm(gt)): C['x_videogame'] += 1; continue
            if re.search(BADW, nt): C['x_badword'] += 1; continue
            if re.search(FORX, nt) or re.search(FORX, norm(gt)) or re.search(X_FOR, nm.lower()) or re.search(X_FOR, gt.lower()): C['x_foreign_or_radio'] += 1; continue
            r0 = sport(nm, '', '1994-06-18') or sport(nm, '', '1994-10-15') or sport(gt, str(x.get('s') or ''), '1994-06-18') or sport(gt, str(x.get('s') or ''), '1994-10-15')
            lg = r0[0] if r0 else 'sports'
            if not r0:
                hit = [l for l in ('nfl', 'nba', 'mlb', 'nhl') if RXT[l].search(norm(ctx)) or RXT[l].search(nt)]
                if len(hit) == 1: lg = hit[0]
                elif 'nfl' in hit and re.search(r' (week|wk) ?\d', nt + norm(ctx)): lg = 'nfl'
            if lg == 'mlb' and re.search(r' (softball|college|ncaa|little league|poker|numismatics) ', nt + norm(ctx)): lg = 'sports'
            if re.search(r' numismatics ', nt): C['x_badword'] += 1; continue
            rg = sport(gt, str(x.get('s') or ''), '1994-06-18') or sport(gt, str(x.get('s') or ''), '1994-10-15')
            cb = 'ncaab' if re.search(r' basketball ', norm(ctx)) else 'ncaaf' if re.search(r' football ', norm(ctx)) else ''
            if lg in ('ncaaf', 'ncaab') and cb and not re.search(r' (basketball|football|bowl) ', nt): lg = cb
            ys = [int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)]
            base = {'ct': lg, 'k': LGK.get(lg, 'SPORTS'), 'e': ys[0] if ys else x.get('e') or (gy[0] if gy else 0), 'net': netof(nm, '') or (list(gn)[0] if len(gn) == 1 else ''), 'nm': nm}
            if re.search(DOCRX, nt) or (not multi and re.search(DOCRX, norm(gt))) or re.search(r' (highlight films?|season in reviews?|documentaries|vhs tape documentar(y|ies)) ', norm(gt)) or re.search(r' (world series|super bowl|nba finals|stanley cup) (video|vhs|home video) ', nt):
                rec = dict(base, ct='sportsdoc', k='SPORTS FILMS'); key = ('doc', nt)
            else:
                reb = bool(re.search(REBX, nt))
                d = None if reb else (fdate(nm, ctx) or (fdate(x['i'].replace('-', ' ').replace('_', ' '), ctx) if not multi else None))
                evd = None if d or reb else D['event_date'](nt)
                if d or evd:
                    row, ev = rowat(SC, lg, d or evd, ' ' + nt + ' ')
                    rec = dict(base, ad=d or evd, ev=ev or nt.strip().upper()[:90], e=int((d or evd)[:4]), **{'as': 'fname' if d else 'event'})
                    if row: rec['row'] = row
                    key = (d or evd, rec['ev'] if row else ' '.join(re.sub(r' (part|pt|disc|tape|cd|dvd) ?\d+( of \d+)? | \d of \d | (1st|2nd|first|second) half ', ' ', nt + ' ').split()))
                else:
                    r, why = resolve(SC, nm, gt, gt)
                    if not r and why == 'nosport' and lg in LTAG: r, why = resolve(SC, nm + ' ' + LTAG[lg], gt, gt)
                    if not r and why == 'noyear' and len(gy) == 1: r, why = resolve(SC, '%d %s %s' % (gy[0], nm, LTAG.get(lg, '')), gt, gt)
                    if not r and why in ('allstar_none', 'nba_nogame', 'mlb_nogame', 'noteam'):
                        for lw in ('mlb', 'nba', 'nhl', 'nfl'):
                            if (' ' + lw + ' ') in norm(gt) and (' ' + lw + ' ') not in nt:
                                r2, w2 = resolve(SC, nm + ' ' + lw, gt, gt)
                                if r2: r, why = r2, w2
                    if r:
                        rec = dict(base, ct=r['ct'], k=LGK.get(r['ct'], 'SPORTS'), ad=r['ad'], ev=r['ev'], e=int(r['ad'][:4]), row=r['row'], **{'as': 'sched'}); key = (r['ad'], r['ev'])
                    else:
                        rec = dict(base, keep='maybe', why='day unresolved: ' + str(why))
                        key = ('', ' '.join(re.sub(r' (part|pt|disc|tape|cd|dvd|vts) ?\d+( \d+)?( of \d+)? | \d of \d | (1st|2nd|first|second) half | \d $', ' ', nt + ' ').split()))
            oy = re.findall(r'(?<!\d)(19[0-7]\d|198[0-3]|200[5-9]|20[1-3]\d)(?!\d)', nm)
            if (rec.get('ad') and not ('1984' <= rec['ad'][:4] <= '2004')) or (not rec.get('ad') and rec['ct'] != 'sportsdoc' and oy and not ys):
                rec['keep'] = 'maybe'; rec['why'] = 'outside 1984-2004'
                if not rec.get('ad'): rec['e'] = int(oy[0])
            if rec.get('row'):
                if rec['row'].get('net') and not netof(nm, ''): rec['net'] = rec['row']['net']
                if rec['row'].get('st'): rec['st'] = rec['row']['st']
            if not rec.get('net'): rec['net'] = known_net(rec['ct'], nt, rec.get('ad', ''), rec.get('e'))
            if key in groups: groups[key]['f'].append(f)
            else: rec['f'] = [f]; groups[key] = rec
        for key, rec in groups.items():
            tot = sum(f[1] for f in rec['f'])
            if tot < 1200: C['x_short'] += 1; continue
            if not rec.get('ad') and rec['ct'] != 'sportsdoc' and tot < 2400: C['x_short_undated'] += 1; continue
            r = {'i': x['i'], 'q': 'sports', 't': (rec['nm'] if multi else gt)[:200], 'd': x.get('d', ''), 'y': x.get('y', ''), 'c': x.get('c', []), 's': x.get('s', ''), 'ds': (x.get('ds') or '')[:400], 'f': sorted(rec['f'], key=lambda f: f[0]), 'dl': x.get('dl', 0), 'k': rec['k'], 'e': rec['e'], 'net': rec['net'], 'ct': rec['ct'], 'up': x.get('up', ''), 'src': 'mine'}
            if multi: r['gt'] = gt[:200]
            if rec.get('ad'):
                r['ad'] = rec['ad']; r['as'] = rec['as']; r['ev'] = rec['ev']
                if rec.get('row'): r['sr'] = json.dumps({k: v for k, v in rec['row'].items() if k not in ('hk', 'who')}, ensure_ascii=False)[:200]
            if rec.get('st'): r['st'] = rec['st']
            if rec.get('keep'): r['keep'] = rec['keep']; r['why'] = rec['why']
            C['out_' + ('doc' if rec['ct'] == 'sportsdoc' else rec.get('as') or 'maybe')] += 1
            if rec.get('keep'): C['why ' + rec['why']] += 1
            if rec.get('keep') and rec.get('ad'): C['out_dated_but_maybe'] += 1
            out.append(r)
    return out, C
def known():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) in ('sports2.json.gz', 'sportsched.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'nick_guide.json.gz'): continue
        try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(j, dict): have |= set(j.keys()); continue
        for x in j:
            if isinstance(x, dict) and x.get('i'): have.add(x['i'])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
            if isinstance(x, dict) and isinstance(x.get('ia'), list) and x['ia'] and isinstance(x['ia'][0], str): have.add(x['ia'][0])
    return have
def T(*a): return 'title:(' + ' OR '.join('"%s"' % x if ' ' in x or "'" in x else x for x in a) + ')'
SPORTQ = ('nfl', 'nfl teams', 'nfl teams2', 'nba', 'nba teams', 'nba teams2', 'mlb', 'mlb teams', 'mlb teams2', 'nhl', 'nhl teams', 'nhl teams2', 'college', 'college teams', 'olympics', 'boxing', 'golf tennis', 'racing', 'full games', 'sports subj', 'networks', 'games', 'fighters', 'golf2')
EXTRA = [
 ('playoff words', T('wild card', 'divisional playoff', 'afc championship', 'nfc championship', 'alcs', 'nlcs', 'alds', 'nlds', 'world series', 'stanley cup', 'nba finals', 'conference finals', 'eastern conference', 'western conference', 'bowl', 'final four', 'no-hitter', 'perfect game', 'opening ceremony', 'closing ceremony', 'preakness', 'belmont stakes')),
 ('nfl films', T('nfl films', 'season in review', 'year in review', 'greatest games', 'nfl yearbook', 'highlight film', 'world series film', 'hardwood classics', 'sportscentury', 'this week in baseball', 'inside the nfl', 'football follies', 'road to the super bowl')),
 ('weeks', 'title:(week) AND title:(nfl OR football OR ' + ' OR '.join('"%s"' % t if ' ' in t else t for t in D['NFL']) + ')'),
 ('college2', 'title:(' + ' OR '.join('"%s"' % t for t in CFB.values() if len(t) > 4) + ') AND title:(vs OR versus OR at OR bowl OR football)'),
]
if MODE == 'probe':
    for t in os.environ.get('PROBE', '').split('|'):
        t, _, hs = t.partition('>')
        b = wiki(t.strip())
        if hs and b:
            on = 0
            for x in b:
                if not on and x[0] == 'h' and x[2].lower().startswith(hs.strip().lower()): on = 1
                if on:
                    on += 1
                    print('  RAW', x[0], x[2] if x[0] != 'p' else '', '*' if x[0] == 'row' and x[3] else '', (' | '.join(c[:70] for c in x[1]) if x[0] == 'row' else str(x[1 if x[0] == 'p' else 2])[:240])[:420])
                    if on > 60: break
            continue
        print('PROBE', t, 'blocks', len(b) if b else b, flush=True)
        n = 0; lim = int(os.environ.get('PROBE_MAX', '170'))
        for x in b or []:
            if x[0] == 'h': print('  H%d %s' % (x[1], x[2][:90])); continue
            txt = ' | '.join(c[:int(os.environ.get('PROBE_CELL', '46'))] for c in x[1]) if x[0] == 'row' else x[1][:200]
            if x[0] == 'row' and x[3]: print('  HDR t%d %s' % (x[2], txt[:330])); continue
            if not (RD1.search(txt) or RD2.search(txt) or RD3.search(txt) or RTM0.search(txt) or re.search(NETS, txt.lower())): continue
            n += 1
            if n > lim: continue
            print('  %s %s' % ('ROW t%d' % x[2] if x[0] == 'row' else 'P', txt[:330]))
        print('  shown', min(n, lim), 'of', n, flush=True)
    sys.exit(0)
if MODE == 'plan':
    SC = Sched(load_sched())
    have = known()
    old = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    have |= set(x['i'] for x in old)
    if os.environ.get('ONLY', '') == '1':
        with gzip.open(os.path.join(PARTS, 'sports2_cands.json.gz'), 'wt', encoding='utf-8') as f: json.dump([], f)
        print('tables only', flush=True); sys.exit(0)
    Q = [(n, 'mediatype:movies AND ' + q) for n, q in D['Q0'] if n in SPORTQ] + [(n, 'mediatype:movies AND ' + q) for n, q in EXTRA]
    print('known', len(have), 'queries', len(Q), flush=True)
    seen = {}; stat = collections.defaultdict(collections.Counter); why = collections.Counter(); ex_why = collections.defaultdict(list)
    PB = float(os.environ.get('PLAN_BUDGET_MIN', '290')) * 60
    def run(k): return k, (scrape(Q[k][1]) if time.time() - T0 < PB else None)
    with ThreadPoolExecutor(6) as ex:
        for k, items in ex.map(run, range(len(Q))):
            name = Q[k][0]
            if items is None: stat[name]['skipped_budget'] = 1; print('query', name, 'skipped: time budget', flush=True); continue
            stat[name]['raw'] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: stat[name]['x_have'] += 1; continue
                lang = S(it.get('language'))
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                cl = it.get('collection') or []
                if isinstance(cl, str): cl = [cl]
                if set(cl) & XCOL: continue
                t = S(it.get('title')); desc = ' '.join(re.sub(r'<[^>]+>', ' ', S(it.get('description'))).split())
                c, w = classify(SC, t, i, S(it.get('date')), desc)
                if not c:
                    why[w] += 1
                    if len(ex_why[w]) < 600: ex_why[w].append(t[:100])
                    continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0}
                stat[name]['kept'] += 1; stat[name][c['ct']] += 1
                if c.get('keep'): stat[name]['maybe'] += 1
            print('query', name, dict(stat[name].most_common(8)), 'total', len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    print('UNRESOLVED', why.most_common())
    random.seed(3)
    for w, n in why.most_common():
        if w in ('junk', 'nosport', 'dated', 'badword'): continue
        for t in random.sample(ex_why[w], min(12, len(ex_why[w]))): print('WHY', w, '|', t)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    with gzip.open(os.path.join(PARTS, 'sports2_cands.json.gz'), 'wt', encoding='utf-8') as f: json.dump(cands, f, separators=(',', ':'))
    sys.exit(0)
REJ = collections.Counter()
def meta(it):
    r = meta1(it)
    if isinstance(r, str): REJ[r] += 1; return None
    return r
def meta1(it):
    if time.time() - T0 > BUDGET: return 'budget'
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return 'dark'
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return 'restricted'
    if str(m.get('mediatype', 'movies')) != 'movies': return 'mediatype'
    lang = S(m.get('language'))
    if lang and not re.search(r'(?i)eng|english|^en\b', lang): return 'lang'
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []; hb = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 60: continue
        sz = float(b.get('size') or 0)
        br = sz / 1e6 / (d / 60) if sz else 0
        if br > 30 and not (b.get('format') == 'h.264 IA' or br <= 60): continue
        if br > 30: hb.append(1)
        files.append([b['name'], round(d), b.get('format', '')])
    if not files: return 'nomp4'
    files.sort(key=lambda f: f[0])
    title = S(m.get('title'))
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', S(m.get('description'))).split())
    cl = m.get('collection', [])
    if isinstance(cl, str): cl = [cl]
    if set(cl) & XCOL: return 'col'
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:500]).lower()
    if re.search(X_FOR, blob): return 'foreign'
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast|call)|audio only|simulation)\b', blob): return 'junk'
    c, w = classify(SC, title, it['identifier'], S(m.get('date')), desc)
    if not c: return 'noclass_' + str(w)
    tot = sum(f[1] for f in files)
    if tot < c['min']: return 'short'
    if tot > 14 * 3600: return 'long'
    if len(files) > 12 and c['ct'] != 'sportsdoc': return 'manyfiles'
    r = {'i': it['identifier'], 'q': 'sports', 't': title[:200], 'd': S(m.get('date')), 'y': S(m.get('year')), 'c': cl[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': c['k'], 'e': c['e'], 'net': c['net'], 'ct': c['ct']}
    if c['ad']: r['ad'] = c['ad']; r['as'] = 'sched'; r['ev'] = c['ev']; r['sr'] = json.dumps({k: v for k, v in c['row'].items() if k not in ('hk', 'who')}, ensure_ascii=False)[:200]
    if c.get('st'): r['st'] = c['st']
    if c.get('keep'): r['keep'] = c['keep']; r['why'] = c['why']
    if hb: r['hb'] = 1
    return r
if MODE == 'meta':
    SC = Sched(load_sched())
    cands = json.load(gzip.open(os.path.join(PARTS, 'sports2_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 500 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'sports2-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res), 'rejected', REJ.most_common()); sys.exit(0)
if MODE == 'merge':
    SC = Sched(load_sched())
    old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    old = []
    for x in old0:
        if x.get('src') == 'mine': continue
        c, w = classify(SC, x['t'], x['i'], x.get('d'), x.get('ds'))
        if not c:
            if w in ('junk', 'badword', 'dated'): continue
            old.append(x); continue
        for k in ('ad', 'as', 'ev', 'sr', 'st', 'keep', 'why'): x.pop(k, None)
        x.update(ct=c['ct'], k=c['k'], e=c['e'], net=c['net'])
        if c['ad']: x.update(ad=c['ad'], ev=c['ev'], sr=json.dumps({k: v for k, v in c['row'].items() if k not in ('hk', 'who')}, ensure_ascii=False)[:200], **{'as': 'sched'})
        if c.get('st'): x['st'] = c['st']
        if c.get('keep'): x.update(keep=c['keep'], why=c['why'])
        old.append(x)
    print('refiltered existing', len(old0), '->', len(old))
    have = set(x['i'] for x in old) | known(); add = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'sports2-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have: have.add(x['i']); add.append(x)
    mine, MC = minefiles(SC)
    print('MINE', sorted(MC.items()))
    print('MINE identifiers', len(set(x['i'] for x in mine)), 'entries', len(mine), 'dated', sum(1 for x in mine if x.get('ad')), 'days', len(set(x['ad'] for x in mine if x.get('ad'))), 'with st', sum(1 for x in mine if x.get('st')), 'with net', sum(1 for x in mine if x.get('net')))
    random.seed(11)
    for x in random.sample(mine, min(50, len(mine))): print('MINESAMPLE', x['ct'], '|', x.get('ad', '') or x['e'], x.get('st', ''), x.get('net', ''), '|', x.get('ev', '') or x.get('why', ''), '|', x['t'][:70], '|', x['i'][:30], '|', round(sum(f[1] for f in x['f']) / 60), 'min |', x.get('sr', '')[:120])
    res = old + add + mine
    with gzip.open(OUTF, 'wt', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    ext = []
    for fn in ('sports.json.gz', 'dated.json.gz'):
        pth = os.path.join(OUT, fn)
        if not os.path.exists(pth): continue
        for x in json.load(gzip.open(pth, 'rt', encoding='utf-8')):
            if isinstance(x, list) and len(x) > 4 and re.match(r'\d{4}-\d\d-\d\d$', str(x[2])): i, t, d, lg = x[0], x[1], x[2], {'ncaa': 'ncaab'}.get(x[4], x[4])
            elif isinstance(x, dict) and x.get('q') == 'sports' and x.get('ad'): i, t, d, lg = x['i'], x['t'], x['ad'], x.get('ct', '')
            else: continue
            row, ev = rowat(SC, lg, d, norm(t))
            net = (row or {}).get('net') or known_net(lg, norm(t), d, d[:4])
            if net or (row and row.get('st')): ext.append({'i': i, 'ad': d, 'ev': ev, 'net': net, 'st': (row or {}).get('st', '')})
    with gzip.open(os.path.join(OUT, 'sports2_times.json.gz'), 'wt', encoding='utf-8') as f: json.dump(ext, f, ensure_ascii=False, separators=(',', ':'))
    print('TIMES for already dated sports items', len(ext), 'with st', sum(1 for x in ext if x['st']), 'with net', sum(1 for x in ext if x['net']))
    hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
    dated = [x for x in res if x.get('ad')]
    print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res), 'dated', len(dated), 'undated', len(res) - len(dated))
    print('METHOD', sorted(collections.Counter((x.get('src') or 'search') + ':' + (x.get('as') or ('doc' if x['ct'] == 'sportsdoc' else 'maybe' if x.get('keep') else 'none')) for x in res).items()))
    print('FIELDS dated', len(dated), 'with net', sum(1 for x in dated if x.get('net')), 'with st', sum(1 for x in dated if x.get('st')), 'year-only maybe', sum(1 for x in res if x.get('keep')), 'docs', sum(1 for x in res if x['ct'] == 'sportsdoc'), 'identifiers', len(set(x['i'] for x in res)))
    print('NET BY LEAGUE', sorted(collections.Counter(x['ct'] + ':' + ('net' if x.get('net') else '-') + ('+st' if x.get('st') else '') for x in dated).items()))
    print('LEAGUE TABLE')
    for t, n in collections.Counter(x['ct'] for x in res).most_common():
        L = [x for x in res if x['ct'] == t]; ys = collections.Counter((x.get('ad') or str(x['e']))[:4] for x in L)
        print('  %-10s items %5d hours %6d days %5d  %s' % (t, n, hrs(L), len(set(x['ad'] for x in L if x.get('ad'))), ' '.join('%s:%d' % (y[2:], ys[y]) for y in sorted(ys))))
    print('YEAR TABLE', sorted(collections.Counter(x['ad'][:4] for x in dated).items()))
    days = set(x['ad'] for x in dated); prev = set()
    for fn in ('dated.json.gz', 'sports.json.gz'):
        p = os.path.join(OUT, fn)
        if not os.path.exists(p): continue
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if isinstance(x, dict) and x.get('q') == 'sports' and x.get('ad'): prev.add(x['ad'])
            elif isinstance(x, list) and len(x) > 2 and re.match(r'\d{4}-\d\d-\d\d$', str(x[2])): prev.add(x[2])
    print('distinct days', len(days), 'new days not in earlier sports sets', len(days - prev), 'earlier days', len(prev))
    print('networks', collections.Counter(x['net'] for x in res).most_common(12), 'with start time', sum(1 for x in res if x.get('st')))
    random.seed(7)
    for x in random.sample(dated, min(80, len(dated))): print('SAMPLE', x['ct'], '|', x['ad'], '|', x['ev'], '|', x['t'][:70], '|', x['i'][:30], '|', round(sum(f[1] for f in x['f']) / 60), 'min |', x.get('sr', '')[:150])
    print('undated kept as maybe', sum(1 for x in res if x.get('keep')), collections.Counter(x.get('why') for x in res if x.get('keep')).most_common(12))
    for x in random.sample([x for x in res if not x.get('ad')], min(15, len(res) - len(dated))): print('DOC', x['e'], '|', x['t'][:80], '|', round(sum(f[1] for f in x['f']) / 60), 'min')
