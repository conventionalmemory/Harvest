import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog')
os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '14'))
LIMIT = int(os.environ.get('LIMIT', '60000'))
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
BASE = 'mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
QUERIES = [
 ('col', 'collection:(sportstelevision OR vhssports OR sports OR sportsvideos OR classicsports OR nfl-games OR nflgames OR mlb-games OR nba-games OR nhl-games OR boxing OR boxingvideos OR nascar OR olympics OR collegefootball OR collegebasketball OR wrestlingtelevision_sports)'),
 ('nfl', 'title:("super bowl" OR "monday night football" OR "sunday night football" OR "nfl on" OR "nfl football" OR nfl OR "afc championship" OR "nfc championship" OR "pro bowl" OR "wild card" OR "divisional playoff" OR "thanksgiving day game")'),
 ('nfl', 'title:(cowboys OR 49ers OR packers OR steelers OR redskins OR giants OR bears OR broncos OR raiders OR dolphins OR bills OR eagles OR vikings OR patriots OR chiefs OR browns OR oilers OR rams OR saints OR seahawks OR bengals OR colts OR jets OR falcons OR lions OR chargers OR buccaneers OR cardinals OR ravens OR titans OR jaguars OR panthers) AND title:(vs OR "vs." OR at OR versus OR game OR week)'),
 ('mlb', 'title:("world series" OR "all-star game" OR "all star game" OR alcs OR nlcs OR alds OR nlds OR "game of the week" OR "major league baseball" OR mlb OR "baseball tonight" OR "sunday night baseball" OR "no-hitter" OR "perfect game" OR "opening day")'),
 ('mlb', 'title:(yankees OR "red sox" OR mets OR dodgers OR cubs OR "white sox" OR braves OR cardinals OR orioles OR tigers OR twins OR royals OR athletics OR mariners OR angels OR rangers OR "blue jays" OR indians OR brewers OR astros OR reds OR pirates OR phillies OR expos OR padres OR rockies OR marlins OR diamondbacks) AND title:(vs OR "vs." OR at OR versus OR game)'),
 ('nba', 'title:("nba finals" OR "nba on nbc" OR "nba on tnt" OR "nba on tbs" OR "nba on cbs" OR "nba playoffs" OR "nba all-star" OR "nba all star" OR nba OR "eastern conference finals" OR "western conference finals")'),
 ('nba', 'title:(bulls OR lakers OR celtics OR pistons OR knicks OR jazz OR rockets OR spurs OR suns OR sonics OR supersonics OR "trail blazers" OR blazers OR pacers OR heat OR magic OR hornets OR cavaliers OR bucks OR 76ers OR sixers OR nets OR hawks OR warriors OR kings OR mavericks OR nuggets OR clippers OR timberwolves OR raptors OR grizzlies OR bullets OR wizards) AND title:(vs OR "vs." OR at OR versus OR game)'),
 ('nhl', 'title:("stanley cup" OR nhl OR "hockey night" OR "nhl on" OR "nhl all-star" OR "wales conference" OR "campbell conference" OR oilers OR canadiens OR "maple leafs" OR bruins OR "red wings" OR blackhawks OR penguins OR flyers OR islanders OR whalers OR nordiques OR "north stars" OR avalanche OR devils OR sabres OR canucks OR flames) AND title:(vs OR "vs." OR at OR game OR final OR finals OR cup OR nhl)'),
 ('ncaa', 'title:("rose bowl" OR "orange bowl" OR "sugar bowl" OR "fiesta bowl" OR "cotton bowl" OR "citrus bowl" OR "holiday bowl" OR "gator bowl" OR "peach bowl" OR "college football" OR "final four" OR "ncaa tournament" OR "ncaa championship" OR "march madness" OR "ncaa basketball" OR "ncaa football" OR "college basketball" OR "big east" OR "army navy" OR "army-navy" OR "notre dame" OR "iron bowl")'),
 ('olym', 'title:(olympics OR olympic OR "winter games" OR "summer games" OR "goodwill games" OR "opening ceremony" OR "closing ceremony")'),
 ('box', 'title:(boxing OR "tyson vs" OR "holyfield" OR "top rank" OR "tuesday night fights" OR "fight night" OR "hbo boxing" OR "world championship boxing" OR "showtime championship boxing" OR "heavyweight championship" OR "leonard vs" OR "hagler" OR "de la hoya" OR "foreman vs" OR "lewis vs")'),
 ('race', 'title:("indy 500" OR "indianapolis 500" OR "daytona 500" OR nascar OR "winston cup" OR "busch series" OR "brickyard 400" OR "coca-cola 600" OR "talladega" OR "cart racing" OR "indycar" OR "formula one" OR "grand prix")'),
 ('golf', 'title:("the masters" OR "masters tournament" OR "u.s. open" OR "us open" OR "pga championship" OR "british open" OR "ryder cup" OR "pga tour" OR "skins game" OR wimbledon OR "french open" OR "australian open" OR "davis cup")'),
 ('misc', 'title:("wide world of sports" OR sportscenter OR "sports center" OR "abc sports" OR "cbs sports" OR "nbc sports" OR "espn" OR "kentucky derby" OR "preakness" OR "belmont stakes" OR "world cup" OR "mls cup" OR "wnba" OR "arena football" OR "xfl" OR "usfl" OR "little league world series" OR "figure skating" OR "tour de france" OR "sports saturday" OR "sportsworld" OR "prime ticket" OR "sportschannel")'),
 ('subj', 'subject:("nfl" OR "nba" OR "mlb" OR "nhl" OR "super bowl" OR "world series" OR "monday night football" OR "ncaa" OR "boxing" OR "nascar" OR "olympics" OR "espn" OR "sports broadcast" OR "full game" OR "college football" OR "college basketball" OR "baseball game" OR "football game" OR "basketball game" OR "hockey game")'),
]
NOT = ' AND NOT title:(highlights OR highlight OR documentary OR trailer OR "video game" OR gameplay OR madden OR "nba jam" OR "nba live" OR "nfl blitz" OR playstation OR nintendo OR sega OR genesis OR snes OR n64 OR "longplay" OR "let\'s play" OR podcast OR "home movie" OR camcorder OR promo OR commercial OR commercials OR bloopers OR wrestling OR wwf OR wcw OR wwe)'
SKIP = re.compile(r"\b(nwa|awa|xpw|bjw|fmw|njpw|ajpw|czw|roh|tna|onita|lucha|hunchback|senior olympics|special olympics|junior olympics|science olympiad|exhibition|qtq|nws-?9|gtv-?9|atn-?7|tcn-?9|hsv-?7|varsity|jv|homecoming|alumni game|scrimmage|highlights?|documentary|trailer|video ?game|gameplay|madden|nba jam|nba live|nba 2k|nfl blitz|tecmo|playstation|ps[12]|xbox|nintendo|sega|genesis|snes|n64|gamecube|dreamcast|arcade|longplay|let'?s play|walkthrough|speedrun|rom|emulator|podcast|radio|audio only|home movies?|home video|camcorder|little league(?! world)|high school|hs football|pee ?wee|youth|recital|promo|commercials?|bumpers?|bloopers?|follies|greatest|best of|top \d+|countdown|year in review|season in review|team video|yearbook|nfl films|super bowl shuffle|how to|instructional|workout|fitness|aerobics|wrestl|wwf|wcw|wwe|ecw|ufc fan|fan ?made|simulation|sim\b|cpu vs|mock|parody|reaction|review|unboxing|trading cards?|interview|press conference|draft|pre-?game show only|soundtrack|music video|episode|sitcom|cartoon|movie|film)\b", re.I)
FOREIGN = re.compile(r"\b(bbc|itv|sky sports|channel 4|rte|cbc|tsn|sportsnet|hockey night in canada|fuji|nhk|tbs japan|televisa|tv azteca|globo|rai|tf1|canal\+?|zdf|ard|sat\.?1|eurosport|premier league|premiership|la liga|serie a|bundesliga|fa cup|uefa|champions league|copa|libertadores|mundial|futbol|f[uú]tbol|calcio|fu[sß]ball|cricket|rugby|afl|vfl|nrl|sumo|npb|k-?1|pride fc|espa[nñ]ol|deutsch|fran[cç]ais|italiano|portugu[eê]s|russian|japanese|japan|korean|chinese|brasil|brazil|argentina|mexico|england|scotland|ireland|australia|australian|new zealand|germany|france|italy|spain|uk)\b", re.I)
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
MN = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?'
DIM = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def ok(y, m, d):
    if y < 100: y += 1900
    if not (1984 <= y <= 2004 and 1 <= m <= 12 and 1 <= d <= DIM[m]): return None
    if m == 1 and d == 1: return None
    return '%04d-%02d-%02d' % (y, m, d)

def dates_in(s):
    out = []
    s = s or ''
    for m in re.finditer(r'(?<!\d)(19[89]\d|200[0-4])[.\-/ _](\d{1,2})[.\-/ _](\d{1,2})(?!\d)', s):
        out.append(ok(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r'(?<!\d)(\d{1,2})[.\-/](\d{1,2})[.\-/]((?:19)?[89]\d|200[0-4])(?!\d)', s):
        out.append(ok(int(m.group(3)), int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r'\b' + MN + r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', s, re.I):
        out.append(ok(int(m.group(3)), MON[m.group(1).lower()[:3]], int(m.group(2))))
    for m in re.finditer(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+' + MN + r',?\s+(19[89]\d|200[0-4])\b', s, re.I):
        out.append(ok(int(m.group(3)), MON[m.group(2).lower()[:3]], int(m.group(1))))
    for m in re.finditer(r'(?<!\d)(19[89]\d|200[0-4])(0[1-9]|1[0-2])([0-3]\d)(?!\d)', s):
        out.append(ok(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return [d for d in out if d]

def pick_date(title, desc, mdate):
    for src, tag in ((title, 't'), (desc, 'd')):
        ds = dates_in(src)
        if ds: return ds[0], tag
    m = re.match(r'(19[89]\d|200[0-4])-(\d\d)-(\d\d)', str(mdate or ''))
    if m:
        d = ok(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d: return d, 'm'
    return None, ''

LG = [('ncaa', r"\b(ncaa|college (football|basketball|world series)|(?<!super )(?<!pro )bowl\b(?! xx)(?! [ivxl]+\b)|final four|march madness|big east|big ten|regional (semi)?final|army.navy)\b"),
      ('nfl', r"\b(nfl|super ?bowl|monday night football|sunday night football|afc|nfc|pro bowl|cowboys|49ers|packers|steelers|redskins|broncos|raiders|dolphins|bills|eagles|vikings|patriots|chiefs|browns|oilers|rams|saints|seahawks|bengals|colts|jets|falcons|lions|chargers|buccaneers|ravens|titans|jaguars|usfl|xfl)\b"),
      ('mlb', r"\b(mlb|world series|alcs|nlcs|alds|nlds|baseball|yankees|red sox|mets|dodgers|cubs|white sox|braves|orioles|tigers|twins|royals|athletics|mariners|angels|blue jays|indians|brewers|astros|reds|pirates|phillies|expos|padres|rockies|marlins|diamondbacks)\b"),
      ('nba', r"\b(nba|bulls|lakers|celtics|pistons|knicks|jazz|rockets|spurs|suns|sonics|supersonics|blazers|pacers|hornets|cavaliers|bucks|76ers|sixers|nets|hawks|warriors|mavericks|nuggets|clippers|timberwolves|raptors|grizzlies|bullets|wizards|wnba)\b"),
      ('nhl', r"\b(nhl|stanley cup|hockey|canadiens|maple leafs|bruins|red wings|blackhawks|penguins|flyers|islanders|whalers|nordiques|north stars|avalanche|devils|sabres|canucks|flames)\b"),
      ('olympics', r"\b(olympics?|winter games|summer games|goodwill games)\b"),
      ('boxing', r"\b(boxing|fights?|heavyweight|tyson|holyfield|top rank)\b"),
      ('racing', r"\b(indy|indianapolis 500|daytona|nascar|winston cup|busch|brickyard|talladega|cart|formula one|grand prix|racing)\b"),
      ('golf', r"\b(golf|masters|pga|ryder cup|british open|skins game)\b"),
      ('tennis', r"\b(tennis|wimbledon|french open|australian open|davis cup|u\.?s\.? open)\b"),
      ('espn', r"\b(sportscenter|sports center|espn|wide world of sports|abc sports|cbs sports|nbc sports)\b")]
SPORT = re.compile('|'.join(p for _, p in LG), re.I)

def league(low):
    for n, p in LG:
        if re.search(p, low): return n
    return 'other'

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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,description,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor: break
    return out

def txt(v):
    if isinstance(v, list): v = ' '.join(str(x) for x in v)
    return str(v or '')

seen = {}
st = collections.Counter()
for tag, expr in QUERIES:
    items = scrape('(' + expr + ') AND ' + BASE + NOT)
    n = 0
    for it in items:
        i = it['identifier']
        if i in seen: continue
        t = txt(it.get('title')); low = t.lower(); desc = txt(it.get('description'))[:600]
        if SKIP.search(low): st['skip'] += 1; continue
        if FOREIGN.search(low) or re.search(r'[^\x00-ɏ‐-‧]', t): st['foreign'] += 1; continue
        lang = txt(it.get('language')).lower()
        if lang and not re.search(r'eng|english', lang): st['lang'] += 1; continue
        if not SPORT.search(low): st['nosport'] += 1; continue
        d, how = pick_date(t, desc, it.get('date'))
        if not d: st['nodate'] += 1; continue
        seen[i] = {'i': i, 't': t, 'd': d, 'how': how, 'q': tag, 'dl': it.get('downloads') or 0}
        n += 1
    print(tag, len(items), 'kept', n, 'total', len(seen), flush=True)
print('scrape stats', dict(st), flush=True)
cands = sorted(seen.values(), key=lambda x: -x['dl'])[:LIMIT]
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

RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['i']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
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
        files.append([b['name'], round(d)])
    if not files: return None
    files.sort(key=lambda f: f[0])
    tot = sum(f[1] for f in files)
    if tot < 1200 or tot > 12 * 3600: return None
    lg = league(it['t'].lower())
    if lg == 'other': return None
    return [it['i'], it['t'][:160], it['d'], files[:30], lg, it['dl'], it['how']]

res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), flush=True)
res.sort(key=lambda r: (r[2], -r[5]))
how = collections.Counter(r[6] for r in res)
out = [r[:6] for r in res]
with gzip.open(os.path.join(OUT, 'sports.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(out), 'distinct dates', len(set(r[2] for r in out)), 'distinct month-days', len(set(r[2][5:] for r in out)))
print('date source', dict(how))
print('by year', dict(sorted(collections.Counter(r[2][:4] for r in out).items())))
print('days by year', dict(sorted(collections.Counter(d[:4] for d in set(r[2] for r in out)).items())))
print('by league', dict(collections.Counter(r[4] for r in out).most_common()))
random.seed(4)
for r in random.sample(res, min(45, len(res))):
    print('SAMPLE', r[2], r[6], r[4], round(sum(f[1] for f in r[3]) / 60), 'min |', r[1][:110])
