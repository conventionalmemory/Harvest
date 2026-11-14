import gzip, json, os, re, sys, time, random, datetime, collections, urllib.request, urllib.parse, concurrent.futures

MODE = os.environ.get('MODE', 'plan')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'parts')
OUT = os.path.join(ROOT, 'catalog', 'yt_events.json.gz')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
WEB = {'clientName': 'WEB', 'clientVersion': '2.20240726.00.00', 'hl': 'en', 'gl': 'US'}
EMB = {'clientName': 'WEB_EMBEDDED_PLAYER', 'clientVersion': '1.20240723.01.00', 'hl': 'en', 'gl': 'US'}
T0 = time.time()
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
STATS = collections.Counter()

OFFICIAL = {
 'NFL': ('sports', 'nfl'), 'NFLThrowback': ('sports', 'nfl'), 'NFLFilms': ('sports', 'nfl'), 'NBA': ('sports', 'nba'), 'MLB': ('sports', 'mlb'), 'MLBVault': ('sports', 'mlb'),
 'NHL': ('sports', 'nhl'), 'ESPN': ('sports', ''), 'Olympics': ('sports', 'olympics'), 'NASCAR': ('sports', 'racing'), 'NASCARClassics': ('sports', 'racing'), 'INDYCAR': ('sports', 'racing'),
 'IndianapolisMotorSpeedway': ('sports', 'racing'), 'pgatour': ('sports', 'golf'), 'TheMasters': ('sports', 'golf'), 'usga': ('sports', 'golf'), 'TheOpen': ('sports', 'golf'),
 'Wimbledon': ('sports', 'tennis'), 'usopen': ('sports', 'tennis'), 'australianopen': ('sports', 'tennis'), 'rolandgarros': ('sports', 'tennis'), 'TennisTV': ('sports', 'tennis'),
 'TopRankBoxing': ('sports', 'boxing'), 'HBOBoxing': ('sports', 'boxing'), 'ShowtimeSports': ('sports', 'boxing'), 'DAZNBoxing': ('sports', 'boxing'), 'WorldBoxingCouncil': ('sports', 'boxing'),
 'KentuckyDerby': ('sports', 'horse'), 'ChurchillDowns': ('sports', 'horse'), 'NYRA': ('sports', 'horse'),
 'SECNetwork': ('sports', 'ncaaf'), 'ACCDigitalNetwork': ('sports', 'ncaab'), 'bigten': ('sports', 'ncaaf'), 'BigTenNetwork': ('sports', 'ncaaf'), 'Big12Conference': ('sports', 'ncaaf'), 'pac12': ('sports', 'ncaaf'),
 'MarchMadness': ('sports', 'ncaab'), 'NCAA': ('sports', 'ncaab'), 'NotreDameFootball': ('sports', 'ncaaf'), 'ChicagoBulls': ('sports', 'nba'), 'Lakers': ('sports', 'nba'), 'celtics': ('sports', 'nba'),
 'WWEVault': ('wrest', 'wwe'), 'WWE': ('wrest', 'wwe'), 'ImpactWrestling': ('wrest', ''), 'NWA': ('wrest', 'nwa'), 'AWAWrestling': ('wrest', 'awa'), 'GLOWWrestling': ('wrest', 'glow'),
 'cspan': ('news', 'cspan'), 'NASA': ('news', 'launch'), 'NASAKennedy': ('news', 'launch'), 'APArchive': ('news', ''), 'ReaganFoundation': ('news', 'speech'), 'ReaganLibrary': ('news', 'speech'),
 'ClintonLibrary42': ('news', 'speech'), 'WJClibrary42': ('news', 'speech'), 'Bush41Library': ('news', 'speech'), 'GeorgeWBushLibrary': ('news', 'speech'), 'MillerCenter': ('news', 'speech'),
 'NBCNews': ('news', ''), 'ABCNews': ('news', ''), 'CBSNews': ('news', ''), 'CNN': ('news', ''), 'TODAY': ('news', ''), 'CBSSundayMorning': ('news', ''), 'PBSNewsHour': ('news', ''),
 'Oscars': ('block', 'awards'), 'TelevisionAcad': ('block', 'awards'), 'RecordingAcademy': ('block', 'awards'), 'goldenglobes': ('block', 'awards'), 'TheTonyAwards': ('block', 'awards'), 'MTV': ('block', 'awards'),
 'macys': ('block', 'parade'), 'RoseParade': ('block', 'parade'), 'farmaid': ('block', 'concert'), 'LiveAid': ('block', 'concert'), 'MDATelethon': ('block', 'telethon'), 'MissAmerica': ('block', 'pageant'),
}
FULL_ENUM = {'WWEVault', 'MLBVault', 'NFLThrowback', 'NASCARClassics', 'AWAWrestling', 'GLOWWrestling', 'ReaganLibrary', 'ReaganFoundation', 'ClintonLibrary42', 'WJClibrary42', 'Bush41Library', 'MillerCenter'}

MONTHS = 'january february march april may june july august september october november december'.split()
MON3 = {m[:3]: i + 1 for i, m in enumerate(MONTHS)}
ROM = {'XVIII': 18, 'XIX': 19, 'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24, 'XXV': 25, 'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29, 'XXX': 30, 'XXXI': 31, 'XXXII': 32, 'XXXIII': 33, 'XXXIV': 34, 'XXXV': 35, 'XXXVI': 36, 'XXXVII': 37, 'XXXVIII': 38,
       'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17}
SB = dict(zip(range(18, 39), '1984-01-22 1985-01-20 1986-01-26 1987-01-25 1988-01-31 1989-01-22 1990-01-28 1991-01-27 1992-01-26 1993-01-31 1994-01-30 1995-01-29 1996-01-28 1997-01-26 1998-01-25 1999-01-31 2000-01-30 2001-01-28 2002-02-03 2003-01-26 2004-02-01'.split()))
WM = dict(zip(range(1, 21), '1985-03-31 1986-04-07 1987-03-29 1988-03-27 1989-04-02 1990-04-01 1991-03-24 1992-04-05 1993-04-04 1994-03-20 1995-04-02 1996-03-31 1997-03-23 1998-03-29 1999-03-28 2000-04-02 2001-04-01 2002-03-17 2003-03-30 2004-03-14'.split()))
def yz(a, b, s): return dict(zip(map(str, range(a, b + 1)), s.split()))
PPV = {
 'royal rumble': yz(1988, 2004, '01-24 01-15 01-21 01-19 01-19 01-24 01-22 01-22 01-21 01-19 01-18 01-24 01-23 01-21 01-20 01-19 01-25'),
 'summerslam': yz(1988, 2004, '08-29 08-28 08-27 08-26 08-31 08-30 08-29 08-27 08-18 08-03 08-30 08-22 08-27 08-19 08-25 08-24 08-15'),
 'survivor series': yz(1987, 2004, '11-26 11-24 11-23 11-22 11-27 11-25 11-24 11-23 11-19 11-17 11-09 11-15 11-14 11-19 11-18 11-17 11-16 11-14'),
 'starrcade': yz(1984, 2000, '11-22 11-28 11-27 11-26 12-26 12-13 12-16 12-29 12-28 12-27 12-27 12-27 12-29 12-28 12-27 12-19 12-17'),
 'halloween havoc': yz(1989, 2000, '10-28 10-27 10-27 10-25 10-24 10-23 10-29 10-27 10-26 10-25 10-24 10-29'),
 'indianapolis 500': yz(1984, 2004, '05-27 05-26 05-31 05-24 05-29 05-28 05-27 05-26 05-24 05-30 05-29 05-28 05-26 05-27 05-24 05-30 05-28 05-27 05-26 05-25 05-30'),
 'daytona 500': yz(1984, 2004, '02-19 02-17 02-16 02-15 02-14 02-19 02-18 02-17 02-16 02-14 02-20 02-19 02-18 02-16 02-15 02-14 02-20 02-18 02-17 02-16 02-15'),
 'kentucky derby': yz(1984, 2004, '05-05 05-04 05-03 05-02 05-07 05-06 05-05 05-04 05-02 05-01 05-07 05-06 05-04 05-03 05-02 05-01 05-06 05-05 05-04 05-03 05-01'),
 'live aid': {'1985': '07-13'}, 'state of the union': {},
}
ALIAS = {'indy 500': 'indianapolis 500', 'indianapolis 500': 'indianapolis 500', 'daytona 500': 'daytona 500', 'kentucky derby': 'kentucky derby', 'royal rumble': 'royal rumble', 'summerslam': 'summerslam', 'summer slam': 'summerslam', 'survivor series': 'survivor series', 'starrcade': 'starrcade', 'halloween havoc': 'halloween havoc', 'live aid': 'live aid'}

def post(path, body, tries=4):
    data = json.dumps(body).encode()
    for k in range(tries):
        try:
            rq = urllib.request.Request('https://www.youtube.com/youtubei/v1/' + path + '?prettyPrint=false', data=data, headers={'User-Agent': UA, 'Content-Type': 'application/json', 'Accept-Language': 'en-US,en;q=0.9', 'Origin': 'https://www.youtube.com'})
            with urllib.request.urlopen(rq, timeout=30) as r: return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            STATS['posterr'] += 1; time.sleep(1.5 * (k + 1) + random.random())
    return None

def get(url, tries=3, raw=False):
    for k in range(tries):
        try:
            rq = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9', 'Cookie': 'CONSENT=YES+1; SOCS=CAI'})
            with urllib.request.urlopen(rq, timeout=30) as r:
                b = r.read(); return (r.status, b) if raw else b.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if raw: return (e.code, b'')
            if e.code in (401, 403, 404): return None
            time.sleep(1.5 * (k + 1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    return (0, b'') if raw else None

def walk(o, key, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: out.append(v)
            else: walk(v, key, out)
    elif isinstance(o, list):
        for v in o: walk(v, key, out)
    return out

def txt(x):
    if not x: return ''
    if 'simpleText' in x: return x['simpleText']
    return ''.join(r.get('text', '') for r in x.get('runs', []))

def secs(s):
    try:
        p = [int(x) for x in s.split(':')]
        return sum(v * 60 ** i for i, v in enumerate(reversed(p)))
    except Exception: return 0

def vr(v, src):
    vid = v.get('videoId')
    if not vid: return None
    own = v.get('ownerText') or v.get('longBylineText') or v.get('shortBylineText') or {}
    chid = ''
    for r in own.get('runs', []):
        chid = (((r.get('navigationEndpoint') or {}).get('browseEndpoint') or {}).get('browseId')) or chid
    dur = secs(txt(v.get('lengthText'))) or int(v.get('lengthSeconds') or 0)
    ver = any('VERIFIED' in json.dumps(b) for b in v.get('ownerBadges', []))
    info = txt(v.get('videoInfo'))
    return {'vid': vid, 't': txt(v.get('title')), 'ch': txt(own), 'chid': chid, 'dur': dur, 'ver': 1 if ver else 0, 'ago': txt(v.get('publishedTimeText')) or info, 'vc': txt(v.get('viewCountText')) or info, 'src': src}

def conts(j):
    return [c.get('token') for c in walk(j, 'continuationCommand', []) if c.get('token')]

def search(q, pages=2, long=True, src=''):
    out = []; body = {'context': {'client': WEB}, 'query': q, 'params': 'EgQQARgC' if long else 'EgIQAQ%3D%3D'}
    j = post('search', body)
    for p in range(pages):
        if not j: break
        for v in walk(j, 'videoRenderer', []):
            r = vr(v, src or 'q:' + q)
            if r: out.append(r)
        ct = conts(j)
        if not ct or p + 1 >= pages: break
        j = post('search', {'context': {'client': WEB}, 'continuation': ct[-1]})
    STATS['searches'] += 1
    return out

def resolve(handle):
    h = get('https://www.youtube.com/@' + handle)
    if not h: return None
    m = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', h) or re.search(r'channel/(UC[\w-]{22})', h)
    return m.group(1) if m else None

def chsearch(chid, q, handle, pages=2):
    out = []; j = post('browse', {'context': {'client': WEB}, 'browseId': chid, 'params': 'EgZzZWFyY2jyBgQKAloA', 'query': q})
    for p in range(pages):
        if not j: break
        for v in walk(j, 'videoRenderer', []):
            r = vr(v, 'c:' + handle)
            if r:
                r['chid'] = r['chid'] or chid; r['ch'] = r['ch'] or handle; out.append(r)
        ct = conts(j)
        if not ct or p + 1 >= pages: break
        j = post('browse', {'context': {'client': WEB}, 'continuation': ct[-1]})
    STATS['chsearches'] += 1
    return out

def uploads(chid, handle, maxpages=120):
    out = []; j = post('browse', {'context': {'client': WEB}, 'browseId': 'VLUU' + chid[2:]})
    for p in range(maxpages):
        if not j: break
        got = 0
        for v in walk(j, 'playlistVideoRenderer', []):
            r = vr(v, 'u:' + handle)
            if r:
                r['chid'] = chid; r['ch'] = r['ch'] or handle; out.append(r); got += 1
        ct = conts(j)
        if not ct or not got: break
        j = post('browse', {'context': {'client': WEB}, 'continuation': ct[-1]})
    STATS['enum'] += 1
    return out

def oembed(vid):
    st, _ = get('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + vid, safe=''), raw=True)
    return st

def player(vid):
    j = post('player', {'context': {'client': WEB}, 'videoId': vid, 'contentCheckOk': True, 'racyCheckOk': True}, tries=2)
    e = post('player', {'context': {'client': EMB, 'thirdParty': {'embedUrl': 'https://www.example.org/'}}, 'videoId': vid}, tries=2)
    return j, e

def norm(s): return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()

DPAT = [
 (re.compile(r'\b(' + '|'.join(MONTHS) + r'|' + '|'.join(m[:3] for m in MONTHS) + r')[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d\d)\b', re.I), 'mdy'),
 (re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(MONTHS) + r'|' + '|'.join(m[:3] for m in MONTHS) + r')[a-z]*\.?,?\s+((?:19|20)\d\d)\b', re.I), 'dmy'),
 (re.compile(r'\b((?:19|20)\d\d)[-./](\d{1,2})[-./](\d{1,2})\b'), 'ymd'),
 (re.compile(r'\b(\d{1,2})[-./](\d{1,2})[-./]((?:19|20)\d\d)\b'), 'mdY'),
 (re.compile(r'\b(\d{1,2})[-./](\d{1,2})[-./](\d\d)\b'), 'mdy2'),
]
def mk(y, m, d):
    try:
        y, m, d = int(y), int(m), int(d)
        if y < 100: y += 1900 if y >= 84 else 2000
        if not (1984 <= y <= 2004): return None
        return datetime.date(y, m, d).isoformat()
    except Exception: return None

def dates_in(s):
    out = []
    for rx, kind in DPAT:
        for m in rx.finditer(s or ''):
            g = m.groups()
            if kind == 'mdy': d = mk(g[2], MON3[g[0][:3].lower()], g[1])
            elif kind == 'dmy': d = mk(g[2], MON3[g[1][:3].lower()], g[0])
            elif kind == 'ymd': d = mk(g[0], g[1], g[2])
            elif kind == 'mdY': d = mk(g[2], g[0], g[1])
            else: d = mk(g[2], g[0], g[1]) if int(g[2]) >= 84 or int(g[2]) <= 4 else None
            if d: out.append((m.start(), d))
    return out

def event_date(t):
    low = ' ' + norm(t) + ' '; up = (t or '').upper()
    m = re.search(r'SUPER ?BOWL\s+([IVX]{1,7}|\d{1,2})\b', up)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else ROM.get(m.group(1))
        if n in SB: return SB[n], 'event'
    m = re.search(r'WRESTLEMANIA\s+(X-?SEVEN|X8|2000|[IVX]{1,5}|\d{1,2})\b', up)
    if m:
        g = m.group(1); n = {'X-SEVEN': 17, 'XSEVEN': 17, 'X8': 18, '2000': 16}.get(g) or (int(g) if g.isdigit() else ROM.get(g))
        if n in WM: return WM[n], 'event'
    ys = re.findall(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', t or '')
    for a, k in ALIAS.items():
        if ' ' + a + ' ' in low and ys:
            d = PPV[k].get(ys[0])
            if d: return ys[0] + '-' + d, 'event'
    return None, ''

JUNK = re.compile(r"(?i)\b(highlights?|recap|top \d+|best of|mic'?d up|reaction|react|podcast|review|breakdown|analysis|explained|documentary|film study|trailer|promo|preview|press conference|interview|every (touchdown|goal|play)|all (touchdowns|goals)|condensed|in \d+ minutes|mini[- ]?movie|shorts?|simulation|madden|2k\d\d|video game|gameplay|remix|tribute|compilation|countdown|ranking|facts|story of|what happened|the truth|a football life|hard knocks|sound fx|america'?s game|nfl films presents|upscaled|60 ?fps|ai upscale)\b")
FULLW = re.compile(r"(?i)full (game|match|fight|race|event|show|episode|broadcast|ceremony|telecast|replay|coverage|ppv|pay)|complete (game|broadcast|show|race|fight|telecast|ceremony)|original (broadcast|telecast)|entire (game|show|broadcast)|\b(nbc|cbs|abc|espn|tnt|tbs|fox|cnn|usa network|hbo|ppv) (broadcast|telecast|coverage|feed)\b|with (original )?commercials|\bw/ ?commercials")
LG = [
 ('nfl', r"\b(nfl|super ?bowl|afc championship|nfc championship|monday night football|wild ?card|divisional playoff|pro bowl|(cowboys|49ers|packers|bears|giants|redskins|steelers|raiders|broncos|dolphins|bills|chiefs|eagles|patriots|jets|vikings|rams|colts|browns|bengals|oilers|titans|saints|falcons|buccaneers|seahawks|chargers|lions|cardinals|jaguars|panthers|ravens|texans) (vs|at|@)\b)", 60),
 ('nba', r"\b(nba|bulls|lakers|celtics|pistons|knicks|jazz|rockets|spurs|sonics|supersonics|suns|blazers|pacers|magic|heat|76ers|sixers|bucks|hawks|cavaliers|warriors|kings|nets|mavericks|nuggets|clippers|timberwolves|raptors|grizzlies|hornets|bullets|wizards)\b.*\b(vs|at|@|finals|playoffs|game \d|all[- ]star)\b", 60),
 ('mlb', r"\b(mlb|world series|alcs|nlcs|alds|nlds|all[- ]star game|no[- ]hitter|perfect game|(yankees|red sox|braves|dodgers|giants|cubs|mets|cardinals|phillies|orioles|blue jays|twins|athletics|a's|reds|pirates|astros|rangers|mariners|indians|tigers|royals|white sox|brewers|padres|expos|angels|marlins|rockies|diamondbacks|devil rays) (vs|at|@)\b)", 60),
 ('nhl', r"\b(nhl|stanley cup|(red wings|bruins|canadiens|maple leafs|rangers|islanders|flyers|penguins|blackhawks|oilers|flames|canucks|avalanche|devils|sabres|capitals|blues|stars|north stars|whalers|nordiques|kings|sharks|ducks|lightning|panthers|senators|jets|coyotes|hurricanes|predators|wild|blue jackets|thrashers) (vs|at|@)\b)", 60),
 ('ncaaf', r"\b(rose bowl|orange bowl|sugar bowl|fiesta bowl|cotton bowl|citrus bowl|bowl game|iron bowl|army[- ]navy|ohio state (vs|at)|michigan (vs|at)|notre dame (vs|at)|college football|ncaa football|sec championship|national championship game)\b", 60),
 ('ncaab', r"\b(final four|ncaa (tournament|championship|basketball)|march madness|elite eight|sweet 16|sweet sixteen|college basketball|big east tournament|acc tournament)\b", 50),
 ('olympics', r"\b(olympic|olympics|opening ceremony|closing ceremony|dream team)\b", 30),
 ('boxing', r"\b(boxing|title fight|heavyweight|welterweight|middleweight|tyson|holyfield|leonard|hagler|hearns|duran|de la hoya|chavez|foreman|lewis|bowe|trinidad|jones jr|whitaker|mayweather|pacquiao) \b.*\b(vs\.?|v)\b", 12),
 ('racing', r"\b(daytona 500|indy 500|indianapolis 500|winston cup|nascar|brickyard 400|coca[- ]cola 600|southern 500|talladega|bristol|cart|indycar|grand prix)\b", 60),
 ('golf', r"\b(masters|u\.?s\.? open|british open|open championship|pga championship|ryder cup|final round)\b.*\b(golf|round|masters|open|pga)\b", 60),
 ('tennis', r"\b(wimbledon|u\.?s\.? open|french open|roland garros|australian open)\b.*\b(final|semifinal|semi-final|vs)\b", 50),
 ('horse', r"\b(kentucky derby|preakness|belmont stakes|breeders'? cup)\b", 8),
]
WR = re.compile(r"(?i)\b(wwf|wwe|wcw|nwa|ecw|awa|wccw|world class|mid[- ]south|uwf|smw|smoky mountain|uswa|glow|gwf|wrestlemania|royal rumble|summerslam|survivor series|king of the ring|in your house|starrcade|halloween havoc|great american bash|bash at the beach|clash of the champions|nitro|thunder|monday night raw|raw is war|\braw\b|smackdown|superstars|prime time wrestling|saturday night'?s main event|wrestling challenge|hardcore tv|world championship wrestling|worldwide|saturday night)\b")
EV = [
 ('awards', 'block', r"\b(academy awards|oscars|emmy awards|emmys|grammy awards|grammys|golden globe|tony awards|video music awards|vmas|kids'? choice awards|american music awards|people'?s choice|country music awards|cma awards|espy)\b", 40),
 ('parade', 'block', r"\b(thanksgiving day parade|macy'?s parade|rose parade|tournament of roses)\b", 40),
 ('newyear', 'block', r"\b(new year'?s (eve|rockin)|rockin'? eve|times square (ball|countdown)|millennium (coverage|celebration)|y2k coverage|2000 today)\b", 30),
 ('telethon', 'block', r"\b(telethon|comic relief|hands across america)\b", 40),
 ('concert', 'block', r"\b(live aid|farm aid|woodstock '?9[49]|woodstock 199[49]|freddie mercury tribute|concert for new york|america: a tribute to heroes)\b", 30),
 ('july4', 'block', r"\b(capitol fourth|fourth of july|july 4th|macy'?s fireworks|liberty weekend)\b", 30),
 ('pageant', 'block', r"\b(miss america|miss usa|miss universe|miss teen usa)\b", 40),
 ('inauguration', 'news', r"\b(inauguration|inaugural address|swearing[- ]in)\b", 10),
 ('sotu', 'news', r"\b(state of the union)\b", 20),
 ('convention', 'news', r"\b(democratic national convention|republican national convention|\bdnc\b|\brnc\b|convention (speech|coverage|address))\b", 15),
 ('debate', 'news', r"\b(presidential debate|vice presidential debate|debate)\b.*\b(19[89]\d|200[0-4])\b", 40),
 ('election', 'news', r"\b(election night|election coverage|decision '?\d\d|vote '?\d\d|campaign '?\d\d)\b", 30),
 ('launch', 'news', r"\b(sts-?\d{1,3}[a-z]?|space shuttle|shuttle (launch|landing)|challenger|columbia|discovery|atlantis|endeavour)\b.*\b(launch|landing|coverage|disaster|explosion|mission|liftoff)\b", 8),
 ('royal', 'news', r"\b(royal wedding|funeral of (princess )?diana|diana'?s funeral|princess diana)\b", 30),
 ('breaking', 'news', r"\b(challenger (disaster|explosion)|berlin wall|gulf war|desert storm|o\.?j\.? simpson|bronco chase|verdict|oklahoma city bombing|columbine|9/11|september 11|sept\.? 11|world trade center|waco|rodney king|l\.?a\.? riots|hurricane andrew|loma prieta|northridge earthquake|tiananmen|reagan (shot|funeral)|nixon funeral|jfk jr|bush v\.? gore|recount|impeachment|iran[- ]contra|clarence thomas|anita hill)\b", 15),
 ('speech', 'news', r"\b(address to the nation|oval office address|farewell address|press conference|remarks|speech)\b", 8),
 ('newscast', 'news', r"\b(nightly news|evening news|world news tonight|nightline|cnn headline|headline news|newscast|news at (5|6|10|11)|eyewitness news|action news|newscenter)\b", 15),
]

def classify(t, hint):
    low = (t or '').lower()
    if WR.search(low) and not re.search(r'\b(nfl|nba|mlb|nhl)\b', low):
        m = WR.search(low); return 'wrest', norm(m.group(1)).replace(' ', '') or 'wrest', 20
    for ct, rx, mn in LG:
        if re.search(rx, low): return 'sports', ct, mn
    for ct, q, rx, mn in EV:
        if re.search(rx, low): return q, ct, mn
    if hint and hint[0] in ('sports', 'wrest'): return hint[0], hint[1] or 'other', 40
    if hint and hint[0] in ('news', 'block'): return hint[0], hint[1] or 'other', 8
    return None, None, 0

def kname(t):
    s = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', t or '')
    s = re.sub(r'(?i)\b(full (game|match|fight|race|event|show|episode|broadcast|ceremony|telecast|replay|coverage)|classic (game|match)|complete|original broadcast|nfl throwback|nfl classic|hd|hq|720p|1080p|480p|remastered|upscaled|wwe vault|vault)\b', ' ', s)
    s = re.sub(r'\s*[|•·]\s*', ' - ', s); s = re.sub(r'\s+', ' ', s).strip(' -:|,.')
    return s.upper()[:90]

def have_index():
    days = collections.defaultdict(set); ids = set()
    for fn in ('sports', 'dated', 'wrestling', 'raw', 'openarch'):
        p = os.path.join(ROOT, 'catalog', fn + '.json.gz')
        if not os.path.exists(p): continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        for x in L:
            if isinstance(x, dict):
                d = str(x.get('ad') or ''); q = x.get('q') or ('wrest' if fn == 'wrestling' else '')
                if len(d) == 10: days[d].add('wrest' if fn == 'wrestling' else q)
            elif isinstance(x, list) and len(x) > 2 and fn == 'sports':
                d = str(x[2] or '')
                if len(d) == 10: days[d].add('sports')
    return days

def queries():
    Q = []
    for y in range(1984, 2005):
        s = str(y)
        for a in ('nfl full game', 'nba full game', 'mlb full game', 'nhl full game', 'world series game', 'nba finals game', 'stanley cup finals game', 'nfc championship', 'afc championship', 'monday night football', 'nba playoffs full game', 'alcs game', 'nlcs game',
                  'rose bowl full game', 'orange bowl full game', 'sugar bowl full game', 'college football full game', 'final four full game', 'ncaa championship game', 'college basketball full game', 'boxing full fight', 'daytona 500 full race', 'indy 500 full race', 'winston cup full race',
                  'masters final round', 'us open golf final round', 'wimbledon final full match', 'us open tennis final full', 'kentucky derby full broadcast', 'mlb all-star game', 'nba all-star game',
                  'wwf full show', 'wcw full show', 'wwf superstars', 'wwf prime time wrestling', 'wwf wrestling challenge', "saturday night's main event", 'wcw saturday night', 'world championship wrestling', 'nwa wrestling full', 'awa wrestling full', 'world class championship wrestling',
                  'academy awards full', 'emmy awards full', 'grammy awards full', 'golden globe awards full', 'tony awards full', 'mtv video music awards full', "macy's thanksgiving day parade", 'rose parade', "new year's rockin eve", 'state of the union address', 'election night coverage',
                  'presidential debate full', 'democratic national convention', 'republican national convention', 'space shuttle launch coverage', 'breaking news coverage', 'nbc nightly news', 'cbs evening news', 'abc world news tonight', 'miss america pageant', 'telethon', 'fourth of july special'):
            Q.append(a + ' ' + s if not a[0].isdigit() else s + ' ' + a)
        if y >= 1993: Q.append('wwf monday night raw ' + s)
        if y >= 1995 and y <= 2001: Q += ['wcw monday nitro ' + s, 'ecw hardcore tv ' + s]
        if y >= 1998 and y <= 2001: Q.append('wcw thunder ' + s)
        if y >= 1999: Q.append('wwf smackdown ' + s)
        if y in (1984, 1988, 1992, 1994, 1996, 1998, 2000, 2002, 2004): Q += ['olympics opening ceremony ' + s, 'olympics closing ceremony ' + s, 'olympics ' + s + ' full broadcast']
    for n, d in SB.items():
        Q.append('super bowl ' + [k for k, v in ROM.items() if v == n][0] + ' full game')
    for n in range(1, 21): Q.append('wrestlemania ' + str(n) + ' full show')
    for k in ('royal rumble', 'summerslam', 'survivor series', 'king of the ring', 'starrcade', 'halloween havoc', 'great american bash', 'bash at the beach', 'clash of the champions', 'in your house', 'superbrawl', 'slamboree', 'fall brawl', 'november to remember', 'barely legal', 'heat wave'):
        for y in range(1985, 2005): Q.append(k + ' ' + str(y) + ' full')
    Q += ['challenger disaster live coverage', 'berlin wall live coverage 1989', 'gulf war coverage january 16 1991', 'oj simpson bronco chase live coverage', 'oj simpson verdict live coverage', 'oklahoma city bombing live coverage', 'princess diana death coverage', 'princess diana funeral full coverage',
          'columbine live coverage', '2000 election night coverage', 'september 11 2001 live coverage nbc', 'september 11 2001 live coverage cbs', 'september 11 2001 live coverage abc', 'september 11 2001 live coverage cnn', 'september 11 2001 as it happened', 'live aid 1985 full broadcast', 'farm aid 1985 full',
          'reagan inauguration 1985', 'bush inauguration 1989', 'clinton inauguration 1993', 'clinton inauguration 1997', 'bush inauguration 2001', 'royal wedding 1986 coverage', 'hands across america 1986', 'liberty weekend 1986', 'tiananmen square coverage 1989', 'loma prieta earthquake world series coverage',
          'rodney king verdict riots live coverage', 'waco siege live coverage', 'hurricane andrew coverage', 'northridge earthquake live coverage', 'reagan funeral 2004 coverage', 'nixon funeral 1994', 'clinton impeachment coverage', 'bush v gore coverage', 'y2k millennium coverage abc 2000', 'dream team 1992 full game']
    return list(dict.fromkeys(Q))

def probe():
    print('probe search'); r = search('super bowl xxxi full game', pages=1); print(len(r), r[:2])
    print('probe resolve'); c = resolve('WWEVault'); print(c)
    if c:
        u = uploads(c, 'WWEVault', maxpages=2); print('uploads', len(u), u[:2])
        s = chsearch(c, '1997', 'WWEVault', pages=1); print('chsearch', len(s), s[:2])
    vid = (r[0]['vid'] if r else 'dQw4w9WgXcQ')
    print('oembed', oembed(vid)); j, e = player(vid)
    print('player web', json.dumps((j or {}).get('playabilityStatus'))[:300], list(((j or {}).get('microformat') or {}).get('playerMicroformatRenderer', {}).keys())[:20])
    print('player emb', json.dumps((e or {}).get('playabilityStatus'))[:300])
    print('videoDetails', json.dumps({k: v for k, v in ((j or {}).get('videoDetails') or {}).items() if k in ('lengthSeconds', 'viewCount', 'author', 'channelId', 'isLiveContent', 'title')})[:400])
    h = get('https://www.youtube.com/watch?v=' + vid) or ''
    print('watch html', len(h), re.findall(r'"(uploadDate|publishDate)":"([^"]+)"', h)[:2], re.findall(r'itemprop="(?:uploadDate|datePublished)" content="([^"]+)"', h)[:2])
    print(dict(STATS))

def plan():
    os.makedirs(PARTS, exist_ok=True)
    probe()
    cands = {}
    def add(L):
        for r in L:
            if r and r['vid'] not in cands: cands[r['vid']] = r
    chids = {}
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for h, c in zip(OFFICIAL, ex.map(resolve, OFFICIAL)):
            if c: chids[h] = c
    print('resolved', len(chids), 'of', len(OFFICIAL), 'missing', [h for h in OFFICIAL if h not in chids])
    jobs = []
    for h, c in chids.items():
        if h in FULL_ENUM: jobs.append(('u', h, c, ''))
        else:
            qs = [str(y) for y in range(1984, 2005)] + ['full game', 'full broadcast', 'classic', 'full race', 'full fight', 'full match', 'full show', 'full episode', 'original broadcast']
            if OFFICIAL[h][0] in ('news', 'block'): qs = [str(y) for y in range(1984, 2005)] + ['full', 'archive', 'coverage', 'address', 'ceremony']
            for q in qs: jobs.append(('c', h, c, q))
    def run(j):
        if time.time() - T0 > BUDGET * 0.55: return []
        if j[0] == 'u': return uploads(j[2], j[1])
        return chsearch(j[2], j[3], j[1])
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for j, L in zip(jobs, ex.map(run, jobs)):
            for r in L: r['offh'] = j[1]
            add(L)
    print('official candidates', len(cands), dict(STATS))
    Q = queries(); random.Random(7).shuffle(Q)
    def rq(q):
        if time.time() - T0 > BUDGET * 0.9: return []
        return search(q, pages=2)
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for L in ex.map(rq, Q): add(L)
    print('all candidates', len(cands), dict(STATS))
    offids = set(chids.values()); keep = []
    drop = collections.Counter()
    for r in cands.values():
        t = r['t']; hint = OFFICIAL.get(r.get('offh') or '') if r.get('offh') else None
        if r['chid'] in offids:
            hh = [h for h, c in chids.items() if c == r['chid']]; r['offh'] = hh[0]; hint = OFFICIAL[hh[0]]
        q, ct, mn = classify(t, hint)
        if not q: drop['class'] += 1; continue
        if JUNK.search(t) and not FULLW.search(t): drop['junk'] += 1; continue
        if r['dur'] and r['dur'] < mn * 60: drop['short'] += 1; continue
        if not r['dur']: drop['nodur'] += 1; continue
        ys = re.findall(r'(?<!\d)(19[0-9]\d|20[0-2]\d)(?!\d)', t)
        if ys and not any(1984 <= int(y) <= 2004 for y in ys) and not dates_in(t): drop['year'] += 1; continue
        r['q'] = q; r['ct'] = ct; keep.append(r)
    print('kept', len(keep), 'dropped', dict(drop))
    json.dump({'cands': keep, 'off': chids}, gzip.open(os.path.join(PARTS, 'yt_cands.json.gz'), 'wt', encoding='utf-8'))

def meta_one(r):
    if time.time() - T0 > BUDGET: return None
    vid = r['vid']; j, e = player(vid)
    ps = (j or {}).get('playabilityStatus') or {}; pe = (e or {}).get('playabilityStatus') or {}
    vd = (j or {}).get('videoDetails') or (e or {}).get('videoDetails') or {}
    mf = ((j or {}).get('microformat') or {}).get('playerMicroformatRenderer') or {}
    up = (mf.get('uploadDate') or mf.get('publishDate') or '')[:10]
    desc = vd.get('shortDescription') or txt(mf.get('description')) or ''
    emb = None
    if pe.get('status'): emb = pe.get('status') == 'OK'
    elif ps.get('status') == 'OK' and 'playableInEmbed' in ps: emb = bool(ps.get('playableInEmbed'))
    oe = oembed(vid)
    if oe in (401, 403, 404): emb = False
    elif emb is None and oe == 200: emb = True
    st = ps.get('status') or pe.get('status') or ''
    if (not up or not desc) and st != 'OK':
        h = get('https://www.youtube.com/watch?v=' + vid, tries=1) or ''
        m = re.search(r'"(?:uploadDate|publishDate)":"(\d{4}-\d\d-\d\d)', h) or re.search(r'itemprop="(?:uploadDate|datePublished)" content="(\d{4}-\d\d-\d\d)', h)
        if m: up = up or m.group(1)
        m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', h)
        if m and not desc:
            try: desc = json.loads('"' + m.group(1) + '"')
            except Exception: pass
    cn = mf.get('availableCountries')
    return {'vid': vid, 'st': st, 'pe': pe.get('status') or '', 'reason': (ps.get('reason') or pe.get('reason') or '')[:80], 'emb': emb, 'oe': oe, 'up': up, 'desc': desc[:3000], 'views': int(vd.get('viewCount') or 0), 'dur': int(vd.get('lengthSeconds') or 0) or r['dur'],
            'live': bool(vd.get('isLiveContent')), 'fam': mf.get('isFamilySafe'), 'us': (None if cn is None else 'US' in cn), 'author': vd.get('author') or r['ch'], 'chid': vd.get('channelId') or r['chid'], 't': vd.get('title') or r['t']}

def meta():
    S = int(os.environ.get('SHARD', '0')); N = int(os.environ.get('SHARDS', '1'))
    d = json.load(gzip.open(os.path.join(PARTS, 'yt_cands.json.gz'), 'rt', encoding='utf-8'))
    C = [r for i, r in enumerate(sorted(d['cands'], key=lambda r: r['vid'])) if i % N == S]
    out = []
    with concurrent.futures.ThreadPoolExecutor(int(os.environ.get('THREADS', '6'))) as ex:
        for r, m in zip(C, ex.map(meta_one, C)):
            if m: r = dict(r); r['m'] = m; out.append(r)
    c = collections.Counter((r['m']['st'], r['m']['pe'], r['m']['emb'], r['m']['oe']) for r in out)
    print('shard', S, len(C), 'done', len(out), c.most_common(12), dict(STATS))
    json.dump(out, gzip.open(os.path.join(PARTS, 'yt-%d.json.gz' % S), 'wt', encoding='utf-8'))

def merge():
    d = json.load(gzip.open(os.path.join(PARTS, 'yt_cands.json.gz'), 'rt', encoding='utf-8')); off = d['off']; offids = {v: k for k, v in off.items()}
    rows = []
    for fn in sorted(os.listdir(PARTS)):
        if re.match(r'yt-\d+\.json\.gz$', fn): rows += json.load(gzip.open(os.path.join(PARTS, fn), 'rt', encoding='utf-8'))
    prev = {}
    if os.path.exists(OUT):
        try: prev = {x['i']: x for x in json.load(gzip.open(OUT, 'rt', encoding='utf-8'))}
        except Exception: prev = {}
    days = have_index(); today = datetime.date.today(); old = (today - datetime.timedelta(days=4 * 365)).isoformat()
    rej = collections.Counter(); items = dict(prev); samples = []
    for r in rows:
        m = r['m']; t = m['t'] or r['t']
        if m['st'] not in ('OK', '') and m['pe'] != 'OK': rej['status:' + m['st']] += 1; continue
        if m['emb'] is False or m['emb'] is None: rej['noembed'] += 1; continue
        if m['live'] and m['dur'] == 0: rej['live'] += 1; continue
        if m['fam'] is False: rej['age'] += 1; continue
        if m['us'] is False: rej['region'] += 1; continue
        hint = OFFICIAL.get(offids.get(m['chid'], ''))
        q, ct, mn = classify(t, hint)
        if not q: rej['class'] += 1; continue
        if m['dur'] < mn * 60: rej['short'] += 1; continue
        if JUNK.search(t) and not FULLW.search(t): rej['junk'] += 1; continue
        isoff = 1 if (m['chid'] in offids or r.get('ver')) else 0
        why = ''
        if m['chid'] in offids: why = 'official channel'
        elif r.get('ver'): why = 'verified channel'
        elif m['up'] and m['up'] <= old and m['views'] >= 1500: why = 'up since ' + m['up'][:4] + ', ' + str(m['views']) + ' views'
        else: rej['notdurable'] += 1; continue
        ad, src = event_date(t)
        if not ad:
            dt = dates_in(t)
            if dt: ad, src = dt[0][1], 'title'
        if not ad:
            dd = dates_in(m['desc'][:600])
            dd = [x for x in dd if not m['up'] or x[1] < m['up']]
            if dd: ad, src = dd[0][1], 'desc'
        if not ad: rej['nodate'] += 1; continue
        if not ('1984-01-01' <= ad <= '2004-12-31'): rej['range'] += 1; continue
        if re.search(r'(?i)[^\x00-\x7f]{6,}|\b(español|espanol|deutsch|français|italiano|sub ?ita|legendado|dublado|latino|commentary in)\b', t): rej['foreign'] += 1; continue
        it = {'i': 'yt:' + r['vid'], 'vid': r['vid'], 't': t, 'ch': m['author'], 'chid': m['chid'], 'off': isoff, 'dur': m['dur'], 'up': m['up'], 'views': m['views'], 'q': q, 'k': kname(t), 'ad': ad, 'as': src, 'e': int(ad[:4]), 'net': '', 'ct': ct, 'why': why}
        nm = re.search(r'(?i)\b(nbc|cbs|abc|espn|tnt|tbs|fox|cnn|usa network|hbo|pbs|c-span)\b', t)
        if nm: it['net'] = nm.group(1).lower().replace(' network', '')
        if q in days.get(ad, ()): it['dd'] = 1
        items[it['i']] = it
    L = sorted(items.values(), key=lambda x: (x['ad'], x['i']))
    best = {}
    for x in L:
        key = (x['ad'], x['q'], x['ct'], ' '.join(sorted(set(w for w in norm(x['k']).split() if len(w) > 3))[:6]))
        o = best.get(key)
        if not o or (x['off'], x['dur'], x['views']) > (o['off'], o['dur'], o['views']): best[key] = x
    L = sorted(best.values(), key=lambda x: (x['ad'], x['i']))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(L, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('rows', len(rows), 'rejected', dict(rej))
    print('TOTAL', len(L), 'hours', round(sum(x['dur'] for x in L) / 3600), 'official', sum(x['off'] for x in L), 'share', round(100 * sum(x['off'] for x in L) / max(1, len(L))), '%')
    print('days', len(set(x['ad'] for x in L)), 'new days vs archive', len(set(x['ad'] for x in L if not x.get('dd'))))
    for nm, f in (('q', lambda x: x['q']), ('ct', lambda x: x['q'] + '/' + x['ct']), ('year', lambda x: x['e']), ('channel', lambda x: x['ch']), ('datesrc', lambda x: x['as'])):
        c = collections.Counter(f(x) for x in L)
        print(nm, sorted(c.items()) if nm == 'year' else c.most_common(60))
    cy = collections.defaultdict(collections.Counter)
    for x in L: cy[x['q'] + '/' + x['ct']][x['e']] += 1
    for k in sorted(cy): print(k, ' '.join('%d:%d' % (y, n) for y, n in sorted(cy[k].items())))
    rnd = random.Random(3); S = rnd.sample(L, min(80, len(L)))
    for x in S: print('SAMPLE', x['ad'], x['q'], x['ct'], x['off'], x['dur'] // 60, 'min', x['up'], x['views'], '|', x['ch'][:24], '|', x['t'][:90], '|', x['why'])

if __name__ == '__main__':
    if MODE == 'probe': probe()
    elif MODE == 'plan': plan()
    elif MODE == 'meta': meta()
    elif MODE == 'merge': merge()
