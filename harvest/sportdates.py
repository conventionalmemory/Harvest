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
OUTF = os.path.join(OUT, 'sports2.json.gz'); SCHF = os.path.join(OUT, 'sportsched.json.gz'); NOPG = os.path.join(OUT, 'sportsched_nopages.json')
WUA = {'User-Agent': 'sports schedule table builder (github.com/conventionalmemory/harvest)'}
ALIAS = {'niners': '49ers', 'bucs': 'buccaneers', 'cavs': 'cavaliers', 'sixers': '76ers', 'mavs': 'mavericks', 'sonics': 'supersonics', 'blazers': 'trail blazers', 'pitt': 'pittsburgh', 'unc': 'north carolina', 'north carolina state': 'nc state', 'connecticut': 'uconn', 'memphis state': 'memphis'}
def canon(x): return ALIAS.get(x, x)
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
def pdate(text, yfn=None):
    m = RD3.search(text)
    if m: return iso(m.group(1), m.group(2), m.group(3))
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
    ev = []; hdr = None; ht = -1
    yfn = lambda mo: season if mo >= 7 else season + 1
    for b in blocks:
        if b[0] != 'row': continue
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
        e = {'lg': lg, 'd': d, 'a': team if away else opp[0], 'h': opp[0] if away else team, 'se': season, 'src': src}
        if neutral: e['n'] = 1
        if wk.isdigit(): e['wk'] = int(wk)
        elif wk: e['rd'] = wk[:24]
        tv = pnet(cell(itv)) if itv >= 0 else ''
        if tv: e['net'] = tv
        if itm >= 0:
            st = ptime(cell(itm), 'e' if re.search(r'\b(et|est|edt|eastern)\b', hdr[itm].lower()) else None)
            if st: e['st'] = st
        ev.append(e)
    return ev
def series(blocks, lg, year, src, ser=''):
    ev = []; heads = {}; hdr = None; ht = -1; cur = None; nets = set()
    yfn = lambda mo: year
    for b in blocks:
        if b[0] == 'row' and len(b[1]) == 2 and b[1][0].strip().lower() in ('television', 'tv', 'network', 'networks', 'broadcast', 'tv network'):
            nets |= set({'espn2': 'espn'}.get(v, v) for v in re.findall(NETS, b[1][1].lower()))
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
    seen = {}; out = []
    for e in ev:
        k = (e['d'], frozenset((e['a'], e['h'])))
        if k in seen:
            if e.get('g') and not seen[k].get('g'): seen[k]['g'] = e['g']
            if e.get('ser') and not seen[k].get('ser'): seen[k]['ser'] = e['ser']
            if e.get('st') and not seen[k].get('st'): seen[k]['st'] = e['st']
            continue
        seen[k] = e; out.append(e)
    by = collections.defaultdict(list)
    for e in out: by[(frozenset((e['a'], e['h'])), e.get('ser', ''))].append(e)
    for k, L in by.items():
        L.sort(key=lambda e: e['d'])
        if len(L) <= 7 and sum(1 for e in L if e.get('g')) < len(L):
            for n, e in enumerate(L): e['g'] = n + 1
    if len(nets) == 1:
        for e in out: e['net'] = list(nets)[0]
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
    ev = []; hdr = None; ht = -1; head = ''
    yfn = lambda mo: year
    for b in blocks:
        if b[0] == 'h': head = b[2]; continue
        if b[0] == 'row':
            cells = b[1]
            if b[3] or (col(cells, 'date') >= 0 and col(cells, 'race', 'event') >= 0):
                if col(cells, 'date') >= 0: hdr = cells; ht = b[2]
                continue
            if hdr and b[2] == ht:
                idt, ir, itr, itv = col(hdr, 'date'), col(hdr, 'race', 'event'), col(hdr, 'track', 'venue', 'location', 'site', 'circuit'), col(hdr, 'tv', 'network', 'television')
                if 0 <= idt < len(cells) and 0 <= ir < len(cells):
                    d = pdate(cells[idt], yfn)
                    if d and re.search(r'\d{3}|shootout|winston|clash|all.star', cells[ir].lower()):
                        e = {'lg': 'racing', 'd': d, 'k': norm(cells[ir]).strip(), 'y': year, 'src': src}
                        if 0 <= itr < len(cells) and itr != ir: e['tr'] = norm(cells[itr]).strip()[:60]
                        if 0 <= itv < len(cells) and pnet(cells[itv]): e['net'] = pnet(cells[itv])
                        ev.append(e)
        elif b[0] == 'p' and head and re.search(r'\d{3}\b', head):
            m = re.search(r'\b(?:was|were) (?:held|run|ran|contested|scheduled)[^.]{0,40}?\bon\b', b[1]) or re.search(r'\b(?:held|run) on\b', b[1])
            if m:
                d = pdate(b[1][m.start():m.start() + 120], yfn)
                if d: ev.append({'lg': 'racing', 'd': d, 'k': norm(head).strip(), 'y': year, 'src': src})
    seen = set(); out = []
    for e in ev:
        if sr: e['sr'] = sr
        if (e['k'], e['d']) not in seen: seen.add((e['k'], e['d'])); out.append(e)
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
            nick = tfind('nfl', norm(t))[0]
            jobs.append(('nfl', '%d %s season' % (y, t.replace(' (NFL)', '')), nick, y))
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
        if y == 1995: jobs.append(('race', '1995 NASCAR SuperTruck Series', y, 'truck'))
        jobs.append(('info', '%d Major League Baseball All-Star Game' % y, 'mlb', 'all star game', y)); jobs.append(('info', '%d NBA All-Star Game' % y, 'nba', 'all star game', y))
        for k, p in GOLF: jobs.append(('info', p % y, 'golf', k, y))
        for k, p in TENNIS: jobs.append(('info', p % y, 'tennis', k, y))
    for n in BOXERS: jobs.append(('box', n))
    jobs.append(('nohit', 'List of Major League Baseball no-hitters'))
    prev = []
    if os.path.exists(SCHF):
        prev = [e for e in json.load(gzip.open(SCHF, 'rt', encoding='utf-8')) if e.get('src')]
    kind = {j[1]: j[0] for j in jobs}; old2 = collections.defaultdict(list)
    for e in prev:
        if kind.get(e['src']) in ('nfl', 'ser', 'race') and e.get('v') != 2: old2[e['src']].append(e)
    prev = [e for e in prev if e['src'] not in old2]
    done = set(e['src'] for e in prev) | set(json.load(open(NOPG)) if os.path.exists(NOPG) else [])
    alljobs = len(jobs); jobs = [j for j in jobs if j[1] not in done]
    print('pages', alljobs, 'already have', alljobs - len(jobs), 'to fetch', len(jobs), 'refetch for tv and time', len(old2), 'kept events', len(prev), flush=True)
    stat = collections.Counter(); zero = []
    def run(j):
        time.sleep(random.random() * .4)
        b = wiki(j[1])
        if b == 0: return j, 0
        if b is None: return j, None
        if j[0] == 'nfl': return j, nfl_like(b, 'nfl', j[2], j[3], j[1])
        if j[0] == 'cfb': return j, nfl_like(b, 'ncaaf', j[2], j[3], j[1])
        if j[0] == 'ser': return j, series(b, j[2], j[3], j[1], j[4])
        if j[0] == 'bowl': return j, bowls(b, j[2], j[1])
        if j[0] == 'race': return j, races(b, j[2], j[1], j[3])
        if j[0] == 'box': return j, boxrec(b, re.sub(r'\s*\(.*\)', '', j[1]), j[1])
        if j[0] == 'nohit': return j, nohit(b, j[1])
        if j[0] == 'info':
            a, z = infodate(b, j[4])
            return j, ([{'lg': j[2], 'k': j[3], 'y': j[4], 'd': a, 'd2': z, 'src': j[1]}] if a else [])
    ev = list(prev); nopg = set(json.load(open(NOPG)) if os.path.exists(NOPG) else [])
    with ThreadPoolExecutor(3) as ex:
        for n, (j, r) in enumerate(ex.map(run, jobs)):
            if r == 0: stat[j[0] + '_failed'] += 1; zero.append('FAILED ' + j[1]); ev += old2.get(j[1], []); continue
            if r is None: stat[j[0] + '_missing'] += 1; zero.append('MISSING ' + j[1]); nopg.add(j[1]); ev += old2.get(j[1], []); continue
            if not r and old2.get(j[1]): stat[j[0] + '_zero_kept_old'] += 1; ev += old2[j[1]]; continue
            if not r: stat[j[0] + '_zero'] += 1; zero.append('ZERO ' + j[1]); nopg.add(j[1])
            if j[0] in ('nfl', 'ser', 'race'):
                for e in r: e['v'] = 2
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
    sn = {'ws': 'WORLD SERIES', 'alcs': 'ALCS', 'nlcs': 'NLCS', 'alds': 'ALDS', 'nlds': 'NLDS', 'finals': 'NBA FINALS' if lg == 'nba' else 'STANLEY CUP FINALS', 'cf': 'CONFERENCE FINALS', 'sf': 'PLAYOFFS', 'r1': 'PLAYOFFS'}.get(e.get('ser', ''), 'PLAYOFFS')
    return '%d %s%s: %s AT %s' % (y, sn, ' GAME %d' % e['g'] if e.get('g') else '', a, h)
WOMEN = r' (women|womens|ladies|graf|navratilova|evert|seles|hingis|williams|sabatini|sanchez|davenport|capriati|henin|clijsters|pierce|novotna|mandlikova|martinez) '
MEN = r' (men|mens|gentlemen|sampras|agassi|becker|edberg|lendl|mcenroe|connors|wilander|courier|federer|roddick|hewitt|ivanisevic|rafter|kuerten|chang|stich|cash|kafelnikov|safin|muster|bruguera|korda|krajicek|moya|costa|ferrero|gaudio|philippoussis|nalbandian) '
DOCRX = r' (nfl films|season in review|year in review|greatest games|nfl yearbook|team yearbook|highlight film|world series film|hardwood classics|sportscentury|this week in baseball|game of the week|inside the nfl|nfl follies|football follies|nba superstars|nfl s greatest|greatest moments|nfl presents|road to the super bowl|nfl crunch course|super bloopers|baseball s greatest|super bowl highlights) '
def resolve(SC, title, desc=''):
    nt = norm(title)
    r = sport(title, desc, '1994-06-18') or sport(title, desc, '1994-10-15')
    if not r and re.search(r' (?:[a-z]+ ){1,2}(?:1[025][05]|[2-6][05]0) ', nt) and re.search(r' (nascar|winston cup|busch|craftsman truck|speedway|raceway) ', nt + norm(desc[:200])) and not re.search(r' (indy|indianapolis|daytona) 500 ', nt): r = ('racing', 'AUTO RACING')
    if not r: return None, 'nosport'
    lg = r[0]
    ys = sorted(set(int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)))
    m = re.search(r' (19[89]\d|200[0-3]) (\d\d) ', nt)
    if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100: ys = sorted(set(ys) | {int(m.group(1)), int(m.group(1)) + 1})
    if not ys: return None, 'noyear'
    for n, w in enumerate(('one', 'two', 'three', 'four', 'five', 'six', 'seven')): nt = nt.replace(' game ' + w + ' ', ' game %d ' % (n + 1))
    g = re.search(r' (?:game|gm|g) ?(\d)(?: |$)', nt); g = int(g.group(1)) if g else None
    wk = re.search(r' (?:week|wk) ?(\d{1,2}) ', nt); wk = int(wk.group(1)) if wk else None
    mon = re.search(r' (' + MONS + r') ', nt); mon = MON[mon.group(1)[:3]] if mon else None
    def one(c, why):
        ds = set(e['d'] for e in c)
        if len(ds) == 1: return c[0], None
        return None, why + ('_none' if not c else '_multi')
    if lg in ('nfl', 'ncaaf'):
        tm = tfind(lg, nt)
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
        if len(tm) >= 2: c = [e for e in SC.pair.get((lg, frozenset(tm[:2])), [])]
        else: c = [e for e in SC.one.get((lg, tm[0]), [])] if (wk or rd) else []
        if len(tm) < 2 and not (wk or rd): return None, 'oneteam'
        c = [e for e in c if e['se'] in ys or int(e['d'][:4]) in ys]
        if wk: c = [e for e in c if e.get('wk') == wk and e['se'] in ys]
        if rd: c = [e for e in c if rd_ok(e, rd)]
        if mon and len(set(e['d'] for e in c)) > 1: c = [e for e in c if int(e['d'][5:7]) == mon]
        if len(set(e['d'] for e in c)) > 1 and len(ys) == 1:
            c2 = [e for e in c if e['se'] == ys[0]]
            if c2: c = c2
        if len(set(e['d'] for e in c)) > 1 and len(tm) >= 2:
            m2 = re.search(re.escape(tm[0]) + r' (at|@) ' , nt)
            pos = [nt.find(' ' + t + ' ') for t in tm[:2]]
            if re.search(r' (at|@) ', nt) and min(pos) >= 0:
                first = tm[0] if pos[0] < pos[1] else tm[1]
                c2 = [e for e in c if e['a'] == first]
                if c2: c = c2
        e, why = one(c, lg + ('_wk' if wk else '_rd' if rd else '_pair'))
        if e: return {'ad': e['d'], 'ev': label(e, lg), 'ct': lg, 'row': e, 'net': e.get('net', '')}, None
        return None, why
    if lg in ('mlb', 'nba', 'nhl'):
        tm = tfind(lg, nt)
        if ' all star ' in nt:
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
            for p, v in ((r' world series ', 'ws'), (r' (alcs|american league championship|al championship) ', 'alcs'), (r' (nlcs|national league championship|nl championship) ', 'nlcs'), (r' (alds|american league division|al division) ', 'alds'), (r' (nlds|national league division|nl division) ', 'nlds')):
                if re.search(p, nt): ser = v; break
        elif re.search(r' (nba finals|stanley cup finals?|cup finals?) ', nt) or (' finals ' in nt and ' conference ' not in nt and ' division ' not in nt): ser = 'finals'
        if not g: return None, lg + '_nogame'
        c = []
        if len(tm) >= 2: c = [e for e in SC.pair.get((lg, frozenset(tm[:2])), []) if int(e['d'][:4]) in ys and e.get('g') == g and (not ser or not e.get('ser') or e['ser'] == ser)]
        elif ser:
            for y in ys: c += [e for e in SC.ser.get((lg, ser, y), []) if e.get('g') == g and (not tm or tm[0] in (e['a'], e['h']))]
            if ser in ('alds', 'nlds') and not tm: c = []
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
        if re.search(r' (qualifying|happy hour|practice|pole day|time trials|awards banquet|awards ceremony|rain out|rainout) ', nt): return None, 'race_session'
        m = re.search(r' ((?:[a-z]+ ){1,3}(?:1[025][05]|[2-6][05]0)k?) ', nt)
        if not m: return None, 'race_noname'
        nd = nt + norm(desc[:200])
        sr = None
        for tx in (nt, nd):
            if re.search(r' (truck|trucks|supertruck) ', tx): sr = 'truck'
            elif re.search(r' (busch grand national|busch series|busch gn|bgn|grand national) ', tx): sr = 'busch'
            elif re.search(r' (winston cup|nextel cup|cup series) ', tx): sr = ''
            if sr is not None: break
        words = m.group(1).split(); c = []
        for y in ys:
            for n in (3, 2):
                key = ' '.join(words[-n:]) if len(words) >= n else None
                cc = [e for e in SC.race.get(y, []) if key and (' ' + key + ' ') in (' ' + e['k'] + ' ')]
                if sr is not None: cc = [e for e in cc if e.get('sr', '') == sr]
                elif len(set(e['d'] for e in cc)) > 1: cc = [e for e in cc if not e.get('sr')] or cc
                if cc: c += cc; break
        if len(set(e['d'] for e in c)) > 1:
            c2 = [e for e in c if e.get('tr') and any((' ' + w + ' ') in nt for w in e['tr'].split() if len(w) > 3 and w not in ('speedway', 'international', 'motor', 'raceway', 'superspeedway', 'park', 'motorsports', 'fairgrounds', 'state', 'road', 'course', 'north', 'south', 'city'))]
            if c2: c = c2
        if len(set(e['d'] for e in c)) > 1 and mon:
            c2 = [e for e in c if int(e['d'][5:7]) == mon]
            if c2: c = c2
        e, why = one(c, 'race')
        if e: return {'ad': e['d'], 'ev': '%s %s' % (e['d'][:4], e['k'].upper()), 'ct': 'racing', 'row': e}, None
        return None, why
    if lg == 'golf':
        k = 'masters' if ' masters ' in nt else 'pga championship' if ' pga championship ' in nt else 'british open' if ' british open ' in nt or ' open championship ' in nt else 'us open golf' if ' us open ' in nt else None
        if not k or re.search(r' (highlights|preview|practice|par 3|skins|senior|lpga|womens) ', nt): return None, 'golf_nokey'
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
        if not k: return None, 'oly_nocer'
        c = [e for y in ys for e in SC.key.get(('olympics', k, y), [])]
        if len(c) > 1: c = [e for e in c if (' ' + e['s'] + ' ') in nt or (' ' + e['city'] + ' ') in nt]
        e, why = one(c, 'oly')
        if e: return {'ad': e['d'], 'ev': '%s %s OLYMPICS %s' % (e['d'][:4], e['s'].upper(), k.upper()), 'ct': 'olympics', 'row': e}, None
        return None, why
    if lg == 'ncaab':
        k = 'final four' if re.search(r' (final four|national semifinals?) ', nt) else 'championship' if re.search(r' (national championship|championship game|title game|ncaa championship|ncaa final|ncaa finals) ', nt) else None
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
    if re.search(BADW, nt): return None, 'badword'
    if find_date(title, ident, dfield, desc)[0]: return None, 'dated'
    r, why = resolve(SC, title, desc)
    if not r:
        if why in ('nosport', 'noyear'): return None, why
        r0 = sport(title, desc, '1994-06-18') or sport(title, desc, '1994-10-15')
        ys = [int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)]
        if not r0 or not ys: return None, why
        return {'ct': r0[0], 'k': LGK.get(r0[0], 'SPORTS'), 'ad': '', 'ev': '', 'e': ys[0], 'min': 2400, 'net': netof(title, desc), 'keep': 'maybe', 'why': 'day unresolved: ' + str(why)}, None
    return {'ct': r['ct'], 'k': LGK.get(r['ct'], 'SPORTS'), 'ad': r['ad'], 'ev': r['ev'], 'e': int(r['ad'][:4]), 'min': 2400, 'net': r['row'].get('net') or r.get('net') or netof(title, desc), 'st': r['row'].get('st', ''), 'row': r['row']}, None
LTAG = {'nfl': 'nfl', 'nba': 'nba', 'mlb': 'mlb', 'nhl': 'nhl', 'racing': 'nascar', 'ncaaf': 'college football', 'ncaab': 'ncaa basketball'}
GAMEX = r' (madden|nba live|playstation|ps2|ps3|ps 2|ps 3|xbox|nintendo|how to install|rebuilt mod|video game|gameplay|nba 2k\d*|nhl 2004 rebuilt|tournament of legends) '
def fdate(nm, ctx):
    ds = D['dates_in'](nm)
    if ds: return ds[0][1]
    d = pdate(nm)
    if d and '1960' < d < '2006': return d
    ys = set(re.findall(r'(?<!\d)((?:19|20)\d\d)(?!\d)', nm + ' ' + ctx))
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
def rowat(SC, lg, d, nt):
    if lg in ('nfl', 'ncaaf', 'mlb', 'nba', 'nhl'):
        c = [e for t in tfind(lg, nt) for e in SC.one.get((lg, t), []) if e['d'] == d]
        if c: return c[0], label(c[0], lg)
    if lg == 'racing':
        c = [e for e in SC.race.get(int(d[:4]), []) if e['d'] == d]
        c2 = [e for e in c if (' ' + e['k'] + ' ') in nt]
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
            r0 = sport(nm, '', '1994-06-18') or sport(nm, '', '1994-10-15') or sport(gt, str(x.get('s') or ''), '1994-06-18') or sport(gt, str(x.get('s') or ''), '1994-10-15')
            lg = r0[0] if r0 else 'sports'
            rg = sport(gt, str(x.get('s') or ''), '1994-06-18') or sport(gt, str(x.get('s') or ''), '1994-10-15')
            cb = 'ncaab' if re.search(r' basketball ', norm(ctx)) else 'ncaaf' if re.search(r' football ', norm(ctx)) else ''
            if lg in ('ncaaf', 'ncaab') and cb and not re.search(r' (basketball|football|bowl) ', nt): lg = cb
            ys = [int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)]
            base = {'ct': lg, 'k': LGK.get(lg, 'SPORTS'), 'e': ys[0] if ys else x.get('e') or (gy[0] if gy else 0), 'net': netof(nm, '') or (list(gn)[0] if len(gn) == 1 else ''), 'nm': nm}
            if re.search(DOCRX, nt) or (not multi and re.search(DOCRX, norm(gt))):
                rec = dict(base, ct='sportsdoc', k='SPORTS FILMS'); key = ('doc', nt)
            else:
                d = fdate(nm, ctx) or (fdate(x['i'].replace('-', ' ').replace('_', ' '), ctx) if not multi else None)
                if d:
                    row, ev = rowat(SC, lg, d, ' ' + nt + ' ')
                    rec = dict(base, ad=d, ev=ev or nt.strip().upper()[:90], e=int(d[:4]), **{'as': 'fname'})
                    if row: rec['row'] = row
                    key = (d, rec['ev'] if row else ' '.join(re.sub(r' (part|pt|disc|tape|cd|dvd) ?\d+( of \d+)? | \d of \d | (1st|2nd|first|second) half ', ' ', nt + ' ').split()))
                else:
                    r, why = resolve(SC, nm, gt)
                    if not r and why == 'nosport' and lg in LTAG: r, why = resolve(SC, nm + ' ' + LTAG[lg], gt)
                    if not r and why == 'noyear' and len(gy) == 1: r, why = resolve(SC, '%d %s %s' % (gy[0], nm, LTAG.get(lg, '')), gt)
                    if r:
                        rec = dict(base, ct=r['ct'], k=LGK.get(r['ct'], 'SPORTS'), ad=r['ad'], ev=r['ev'], e=int(r['ad'][:4]), row=r['row'], **{'as': 'sched'}); key = (r['ad'], r['ev'])
                    else:
                        rec = dict(base, keep='maybe', why='day unresolved: ' + str(why))
                        key = ('', ' '.join(re.sub(r' (part|pt|disc|tape|cd|dvd|vts) ?\d+( \d+)?( of \d+)? | \d of \d | (1st|2nd|first|second) half | \d $', ' ', nt + ' ').split()))
            if rec.get('row'):
                if rec['row'].get('net'): rec['net'] = rec['row']['net']
                if rec['row'].get('st'): rec['st'] = rec['row']['st']
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
        b = wiki(t.strip())
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
    PB = float(os.environ.get('PLAN_BUDGET_MIN', '140')) * 60
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
        if c and c['ct'] == x['ct'] and (c['ad'] or '') == x.get('ad', ''):
            if c.get('net'): x['net'] = c['net']
            if c.get('st'): x['st'] = c['st']
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
    if os.path.exists(PSCH):
        with gzip.open(SCHF, 'wt', encoding='utf-8') as f: json.dump(json.load(gzip.open(PSCH, 'rt', encoding='utf-8')), f, ensure_ascii=False, separators=(',', ':'))
    hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
    dated = [x for x in res if x.get('ad')]
    print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res), 'dated', len(dated), 'sportsdoc', len(res) - len(dated))
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
