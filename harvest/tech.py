import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog')
os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '14'))
LIMIT = int(os.environ.get('LIMIT', '40000'))
RAWF = os.path.join(OUT, 'raw.json.gz')
have = set()
if os.path.exists(RAWF):
    have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8')))
print('existing raw', len(have), flush=True)
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
BASE = ' AND mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
OPEN = ' AND mediatype:movies'
NOT = ' AND NOT title:("opening to" OR "closing to" OR trailer OR speedrun OR longplay OR "let\'s play" OR walkthrough OR gameplay OR podcast OR lecture)'
def T(*n): return 'title:(' + ' OR '.join('"%s"' % x for x in n) + ')'
HW = 'title:(apple OR macintosh OR microsoft OR windows OR ibm OR commodore OR amiga OR atari OR tandy OR compaq OR intel OR nextstep OR novell OR lotus OR wordperfect OR borland OR adobe OR aol OR compuserve OR prodigy OR netscape OR multimedia OR modem OR computer OR computers OR internet OR software OR bbs OR "cd-rom" OR "cd-i" OR 3do OR "personal computer" OR "home computer" OR "america online" OR "radio shack" OR "silicon graphics" OR "os/2")'
KIND = 'title:(vhs OR promo OR promotional OR dealer OR "sales video" OR "training video" OR "video guide" OR "how to" OR tutorial OR introduction OR "getting started" OR "video magazine" OR infomercial OR episode OR "user group" OR "users group" OR documentary OR special)'
Q = [
 ('cc', 'collection:(computerchronicles)', 0),
 ('cc', T('computer chronicles'), 0),
 ('netcafe', T('net cafe', 'netcafe'), 0),
 ('col', 'collection:(computersandtechvideos)', 1),
 ('col', 'collection:(G4_Icons OR video_power OR g4tv OR g4video OR techtv OR zdtv OR techtvarchive OR thescreensavers OR g4techtv OR nickarcade OR starcade)', 0),
 ('techtv', T('screen savers', 'screensavers', 'call for help', 'silicon spin', 'big thinkers', 'fresh gear', 'extended play', 'x-play', 'xplay', 'gamespot tv', 'techlive', 'tech live', 'tech tv', 'techtv', 'zdtv', 'internet tonight', 'unscrewed', 'titans of tech', 'cybercrime'), 0),
 ('g4', T('g4tv', 'g4 tv', 'g4 icons', 'g4 filter', 'g4 pulse', 'g4 players', 'g4 arena', 'g4 blister', 'g4 cheat', 'cinematech', 'game makers', 'g4 portal', 'attack of the show', 'g4techtv', 'electric playground', 'gamer.tv', 'game nation'), 0),
 ('games', T('video power', 'nick arcade', 'starcade', 'gamepro tv', 'game pro tv', 'nintendo power previews', 'nintendo power preview', 'nintendo power video', 'sega video magazine', 'sega channel', 'nintendo world championships', 'blockbuster video world game', 'donkey kong country exposed', 'play it loud', 'video game special', 'video games special', 'video game report', 'game players gametape', 'gametape', 'power team'), 1),
 ('pctv', T('pctv', 'pc-tv', 'computer man', 'personal computer show', 'high tech heroes', 'computer bowl', 'user friendly', 'cnet central', 'tv.com', 'the new edge', 'cnet tv', 'cyberia', 'bits and bytes', 'bits & bytes', 'famous computer cafe', 'computer show', 'computer talk', 'mac tv', 'mactv', 'macintosh tv', 'amiga world', 'amiga video magazine', 'the pc show', 'byte by byte', 'computer currents', 'computer corner', 'computing today', 'the computer hour', 'world of computers'), 1),
 ('doc', T('triumph of the nerds', 'nerds 2.0.1', 'machine that changed the world', 'code rush', 'revolution os', 'hackers wizards of the electronic age', 'unauthorized access', 'life on the internet', 'the information age', 'information superhighway', 'virtual reality', 'cyberspace', 'world wide web', 'computer animation', 'the mind\'s eye', 'beyond the mind\'s eye', 'gate to the mind\'s eye', 'odyssey into the mind\'s eye', 'computer dreams', 'state of the art of computer animation', 'computer animation festival', 'computer animation showcase', 'the internet show', 'internet for dummies', 'computers for dummies', 'pcs for dummies', 'windows for dummies'), 1),
 ('sci', T('beyond 2000', 'beyond tomorrow', 'scientific american frontiers', 'science and technology week', 'future watch', 'futurewatch', 'tech 2000', 'next wave', 'the next step', 'invention discovery'), 1),
 ('sci', '(' + T("newton's apple", 'nova', '3-2-1 contact', 'square one') + ') AND title:(computer OR computers OR robot OR robots OR internet OR chip OR hacker OR technology OR "video game" OR "artificial intelligence")', 1),
 ('show', T('comdex', 'consumer electronics show', 'summer ces', 'winter ces', 'electronic entertainment expo', 'macworld', 'apple expo', 'pc expo', 'world of commodore', 'amiga expo', 'amiexpo', 'west coast computer faire', 'siggraph', 'internet world', 'wwdc', 'windows 95 launch', 'windows 95 video guide', 'windows 95 video', 'windows 98 launch', 'windows xp launch', 'e3 1995', 'e3 1996', 'e3 1997', 'e3 1998', 'e3 1999', 'e3 2000', 'e3 2001', 'e3 2002', 'e3 2003', 'e3 2004', 'ces 1984', 'ces 1985', 'ces 1986', 'ces 1987', 'ces 1988', 'ces 1989', 'ces 1990', 'ces 1991', 'ces 1992', 'ces 1993', 'ces 1994', 'ces 1995'), 1),
 ('promo', HW + ' AND ' + KIND, 1),
 ('promo', HW + ' AND collection:(vhsvault OR vhsinstructionals OR vhstvshows OR television)', 1),
 ('access', 'title:("user group" OR "users group" OR "computer club" OR "computer users")', 1),
 ('subj', 'subject:("computer chronicles" OR techtv OR zdtv OR "tech tv" OR g4tv OR "computer show" OR "computer history" OR "vintage computer" OR "retro computing" OR "personal computers" OR "home computers" OR "computer television")', 1),
 ('gv', 'collection:(gamevideos OR videogamelibrary) AND title:(episode OR "tv show" OR "tv special" OR "promo tape" OR "video magazine" OR "preview tape" OR "promotional vhs")', 1),
]
BAD = re.compile(r"(?i)\b(commodore 64 demo|c64 demo|amiga demo:|demo capture|oakleytapes|cutscenes?|b-roll|shakycam|livestreams?|canada|canadian|\(uk\)|uk vhs|\buk\b|mean machines|- (spanish|arabic|french|german|chinese|japanese|portuguese|russian)|terminator|treehouse of horror|c-?span|game tapes raw|press kit|e3 20\d\d trailer|speedrun|longplay|long play|let'?s play|walkthrough|playthrough|gameplay|game play footage|demoscene|demo scene|\bdemo\s?party|c64 demo|amiga demo\b(?!.*(tape|vhs))|cracktro|chiptune|podcast|lecture|lectures|course|seminar|webinar|keynote 20(0[5-9]|[1-9]\d)|defcon|def con|ccc congress|\bted\b|tedx|youtube|twitch|livestream|live stream|reaction|review \(20|unboxing|tomorrow'?s world|the computer programme|making the most of the micro|micro live|\bbbc\b|\bitv\b|channel 4|gamesmaster|games master|bad influence|video & arcade top 10|video and arcade top 10|anime unleashed|robot wars|deutsch|español|espanol|français|francais|italiano|português|nederlands|svenska|polski|русск|trailer|opening to|closing to|commercials? (compilation|block|break)|soundtrack|ost\b|music video|xxx|porn)\b")
MOD = re.compile(r'(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)')
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
SHOWS = [('COMPUTER CHRONICLES', r'computer chronicles|^cc\d'), ('NET CAFE', r'net ?cafe|internet cafe'), ('SCREEN SAVERS', r'screen ?savers'), ('CALL FOR HELP', r'call for help'), ('TECHTV/ZDTV OTHER', r'techtv|tech tv|zdtv|silicon spin|big thinkers|fresh gear|tech ?live|internet tonight|unscrewed'), ('EXTENDED PLAY/X-PLAY', r'extended play|x-?play'), ('GAMESPOT TV', r'gamespot'), ('G4', r'\bg4|icons|cinematech|attack of the show|judgment day|filter|cheat!'), ('ELECTRIC PLAYGROUND', r'electric playground'), ('VIDEO POWER', r'video power'), ('NICK ARCADE', r'nick arcade'), ('STARCADE', r'starcade'), ('GAMEPRO TV', r'game ?pro'), ('NINTENDO TAPES', r'nintendo'), ('SEGA TAPES', r'\bsega\b'), ('BITS AND BYTES', r'bits (and|&) bytes'), ('PCTV/CNET/OTHER SHOWS', r'pctv|pc-tv|cnet|computer man|personal computer show|high tech heroes|computer bowl|user friendly|new edge|cyberia|computer show|mac ?tv'), ('DOCUMENTARY', r'triumph of the nerds|nerds 2|machine that changed|code rush|revolution os|hacker|documentary|mind.s eye|computer animation|computer dreams'), ('BEYOND 2000/SCIENCE', r'beyond 2000|beyond tomorrow|scientific american|newton.s apple|\bnova\b|future ?watch|next step'), ('TRADE SHOWS', r'comdex|\bces\b|consumer electronics|\be3\b|macworld|siggraph|pc expo|world of commodore|ami ?expo|wwdc'), ('APPLE', r'apple|macintosh|\bmac\b'), ('MICROSOFT/WINDOWS', r'microsoft|windows|ms-dos'), ('IBM', r'\bibm\b|os/2'), ('COMMODORE/AMIGA', r'commodore|amiga'), ('ATARI', r'atari'), ('ONLINE/INTERNET', r'internet|aol|america online|compuserve|prodigy|world wide web|netscape|bbs|bulletin board'), ('USER GROUP', r'users? group|computer club')]

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True)
                return None
            time.sleep(3 * (k + 1))

def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        if 'items' not in j: print('query error', str(j)[:200], flush=True)
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor or len(out) > 60000: break
    return out

seen = {}
for tag, expr, yr in Q:
    items = scrape('(' + expr + ')' + (BASE if yr else OPEN) + NOT)
    n = 0
    for it in items:
        i = it['identifier']
        t = str(it.get('title') or '')
        if i in seen or i in have: continue
        if BAD.search(t) or NONLAT.search(t): continue
        it['q'] = tag
        seen[i] = it
        n += 1
    print(tag, len(items), 'new', n, 'total', len(seen), flush=True)
PRI = {'cc': 0, 'netcafe': 0, 'techtv': 1, 'g4': 1, 'games': 1, 'pctv': 1, 'doc': 1, 'col': 2, 'show': 2, 'sci': 3, 'subj': 3, 'access': 3, 'gv': 4, 'promo': 5}
cands = sorted(seen.values(), key=lambda x: (PRI.get(x['q'], 9), -(x.get('downloads') or 0)))[:LIMIT]
print('candidates', len(cands), flush=True)

def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception:
        return 0

def ok_y(y): return 1984 <= y <= 2004
def y2(y):
    y = int(y)
    return y + (1900 if y >= 84 else 2000) if y < 100 else y
def text_date(s):
    s = s or ''
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])[-./](\d{1,2})[-./](\d{1,2})(?!\d)', s)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', s)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'(?i)\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[89]\d|200[0-4])\b', s)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(2).lower()], int(m.group(1)))
    m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](19[89]\d|200[0-4]|[89]\d|0[0-4])(?!\d)', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31 and ok_y(y2(m.group(3))): return '%d-%02d-%02d' % (y2(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[89]\d|200[0-4])\b', s)
    if m: return '%s-%02d' % (m.group(2), MON[m.group(1).lower()])
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', s)
    if m: return m.group(1)
    return ''
def best_date(title, mdate, myear, desc):
    md = str(mdate or '')
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', md)
    if m and ok_y(int(m.group(1))) and not (m.group(2) == '01' and m.group(3) == '01'): return m.group(0)
    td = text_date(title)
    if len(td) >= 7: return td
    dd = text_date(desc[:600])
    if len(dd) == 10: return dd
    if td: return td
    m = re.match(r'(\d{4})', md)
    if m and ok_y(int(m.group(1))): return m.group(1)
    if str(myear).isdigit() and ok_y(int(myear)): return str(myear)
    if dd: return dd
    return ''

RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
WHY = collections.Counter()
def why(k):
    WHY[k] += 1
    return None
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j: return why('fetch')
    if not j.get('files') or j.get('is_dark'): return why('dark')
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return why('restricted')
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en', str(lang)): return why('lang')
    title = str(m.get('title', ''))
    if isinstance(m.get('title'), list): title = ' '.join(m['title'])
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = re.sub(r'<[^>]+>', ' ', str(desc))
    if BAD.search(title) or BAD.search(it['identifier'].replace('_', ' ').replace('-', ' ')) or NONLAT.search(title): return why('bad')
    if re.match(r'(?i)(ar|sp|fr|ch|jp|pt|ru|de)_cc', it['identifier']): return why('lang')
    d = best_date(title, m.get('date'), m.get('year'), desc)
    if not d or d[:4] < '1984': return why('nodate')
    if MOD.search(title) and len(d) < 7: return why('modern')
    vids = [f for f in j['files'] if f.get('name', '').lower().endswith('.mp4')]
    groups = {}
    for f in vids:
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        du = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if du < 60: continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (du / 60) > 30: continue
        files.append([b['name'], round(du), b.get('format', '')])
    if not files: return why('nofiles:' + ','.join(sorted(set(str(f.get('format')) for f in j['files']))[:6])[:60] if random.random() < .02 else 'nofiles')
    if sum(f[1] for f in files) < 600: return why('short')
    if sum(f[1] for f in files) > 6 * 3600 and it['q'] not in ('cc', 'techtv', 'g4'): return why('long')
    files.sort(key=lambda f: f[0])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    return {'i': it['identifier'], 'q': it['q'], 't': title[:200], 'd': d, 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': ' '.join(desc.split())[:400], 'f': files[:60], 'dl': it.get('downloads') or 0}

res = []
T0 = time.time()
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
with gzip.open(os.path.join(OUT, 'tech.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(res), flush=True)
print('dropped', dict(WHY))
py = collections.Counter(x['d'][:4] for x in res)
print('per year', ' '.join('%s:%d' % (y, py[y]) for y in sorted(py)))
print('1984-1995', sum(v for y, v in py.items() if '1984' <= y <= '1995'), '1996-2004', sum(v for y, v in py.items() if y >= '1996'))
print('per query', dict(collections.Counter(x['q'] for x in res)))
print('date precision', dict(collections.Counter({4: 'year', 7: 'month', 10: 'day'}.get(len(x['d']), 'other') for x in res)))
sc = collections.Counter()
for x in res:
    low = x['t'].lower()
    if x['q'] == 'cc':
        sc['COMPUTER CHRONICLES'] += 1
        continue
    for name, pat in SHOWS:
        if re.search(pat, low):
            sc[name] += 1
            break
    else:
        sc['OTHER'] += 1
for k, v in sc.most_common(): print('show', k, v)
random.seed(7)
for x in random.sample(res, min(45, len(res))): print('sample', x['q'], x['d'], round(sum(f[1] for f in x['f']) / 60), 'min |', x['t'][:90], '|', x['i'][:50])
old = [x for x in res if x['d'][:4] <= '1995']
for x in random.sample(old, min(25, len(old))): print('early', x['q'], x['d'], round(sum(f[1] for f in x['f']) / 60), 'min |', x['t'][:90], '|', x['i'][:50])
