import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (catalog harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog')
PARTS = os.path.join(here, '..', 'parts')
os.makedirs(OUT, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
THREADS = int(os.environ.get('THREADS', '16'))
BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60
T0 = time.time()
WF = os.path.join(OUT, 'wrestling.json.gz')
RAWF = os.path.join(OUT, 'raw.json.gz')

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:140], e, flush=True)
                return None
            time.sleep(4 * (k + 1))

def scrape(q, fields='identifier,title,date,year,downloads', pages=80):
    out, cursor = [], None
    for _ in range(pages):
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': fields, 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor: break
    return out

def S(v):
    if isinstance(v, list): return ' '.join(str(x) for x in v)
    return str(v or '')

PPV = [
 ('wrestlemania', r"wrestle ?mania"), ('summerslam', r"summer ?slam"), ('royal rumble', r"royal rumble"), ('survivor series', r"survivor series"),
 ('king of the ring', r"king of the ring"), ('in your house', r"in your house"), ('backlash', r"backlash"), ('judgment day', r"judge?ment day"),
 ('unforgiven', r"unforgiven"), ('no mercy', r"no mercy"), ('armageddon', r"armageddon"), ('no way out', r"no way out"), ('vengeance', r"vengeance"),
 ('bad blood', r"bad blood"), ('fully loaded', r"fully loaded"), ('wrestling classic', r"the wrestling classic|wwf wrestling classic"), ('this tuesday in texas', r"tuesday in texas"),
 ('over the edge', r"over the edge"), ('rock bottom', r"rock bottom"), ("st. valentine's day massacre", r"valentine'?s day massacre"), ('invasion', r"\binvasion\b"),
 ('starrcade', r"starrcade"), ('great american bash', r"great american bash"), ('bash at the beach', r"bash at the beach"), ('halloween havoc', r"halloween havoc"),
 ('superbrawl', r"super ?brawl"), ('slamboree', r"slamboree"), ('fall brawl', r"fall brawl"), ('spring stampede', r"spring stampede"), ('uncensored', r"uncensored"),
 ('road wild', r"road wild|hog wild"), ('world war 3', r"world war (3|iii)"), ('souled out', r"souled out"), ('mayhem', r"\bmayhem\b"), ('new blood rising', r"new blood rising"),
 ('sin', r"wcw sin\b"), ('greed', r"wcw greed\b"), ('chi-town rumble', r"chi-?town rumble"), ('wrestlewar', r"wrestle ?war"), ('capital combat', r"capital combat"),
 ('beach blast', r"beach blast"), ('crockett cup', r"crockett cup"), ('bunkhouse stampede', r"bunkhouse stampede"), ('battlebowl', r"battle ?bowl"),
 ('clash of the champions', r"clash of (the )?champions"), ('barely legal', r"barely legal"), ('november to remember', r"november to remember"), ('heat wave', r"heat ?wave"),
 ('living dangerously', r"living dangerously"), ('guilty as charged', r"guilty as charged"), ('anarchy rulz', r"anarchy rulz"), ('hardcore heaven', r"hardcore heaven"),
 ('cyberslam', r"cyber ?slam"), ('wrestlepalooza', r"wrestlepalooza"), ('superclash', r"super ?clash"), ('wrestlerock', r"wrestle ?rock"),
 ("saturday night's main event", r"saturday night'?s main event|\bsnme\b"), ('the main event', r"the main event"), ('supershow', r"supershow"),
]
SHOWS = [
 ('raw', r"monday night raw|raw is war|\bwwf raw\b|\bwwe raw\b|\braw\b"), ('smackdown', r"smack ?down"), ('heat', r"sunday night heat|\bwwf heat\b|\bwwe heat\b"),
 ('shotgun', r"shotgun saturday"), ('livewire', r"live ?wire"), ('mania', r"wwf mania\b"), ('action zone', r"action zone"), ('velocity', r"velocity"),
 ('jakked/metal', r"jakked|wwf metal"), ('wrestling spotlight', r"wrestling spotlight"), ('superstars', r"superstars"), ('wrestling challenge', r"wrestling challenge"),
 ('prime time wrestling', r"prime ?time wrestling"), ('all-american wrestling', r"all[- ]american wrestling"), ('tuesday night titans', r"tuesday night titans|\btnt\b(?=.*wwf)"),
 ('house show', r"madison square garden|\bmsg\b|boston garden|spectrum|maple leaf gardens|house show|meadowlands|capital centre|los angeles sports arena"),
 ('coliseum video', r"coliseum video|coliseum home video"), ('nitro', r"nitro"), ('thunder', r"wcw thunder|thunder"), ('wcw saturday night', r"wcw saturday night|saturday night"),
 ('wcw worldwide', r"world ?wide"), ('wcw pro', r"wcw pro\b"), ('wcw power hour', r"power hour"), ('wcw main event', r"wcw main event"),
 ('world championship wrestling', r"world championship wrestling"), ('ecw hardcore tv', r"hardcore tv"), ('ecw on tnn', r"ecw on tnn"),
 ('awa', r"\bawa\b|all[- ]star wrestling"), ('wccw', r"\bwccw\b|world class"), ('uswa', r"\buswa\b"), ('memphis', r"memphis|\bcwa\b"), ('mid-south/uwf', r"mid[- ]south|\buwf\b|\bmsw\b"),
 ('florida', r"championship wrestling from florida|\bcwf\b"), ('georgia', r"georgia championship"), ('mid-atlantic', r"mid-atlantic|jim crockett|\bjcp\b"),
 ('stampede', r"stampede wrestling"), ('gwf', r"\bgwf\b|global wrestling"), ('smoky mountain', r"smoky mountain|\bsmw\b"), ('pro wrestling usa', r"pro wrestling usa"),
 ('glow', r"gorgeous ladies|\bglow\b"), ('poww', r"\bpoww\b|powerful women"), ('lpwa', r"\blpwa\b"), ('tna', r"\btna\b|total nonstop"), ('roh', r"ring of honor|\broh\b"),
]
PROMO = [('wwf', r"\bwwf\b|\bwwe\b|world wrestling federation|world wrestling entertainment"), ('wcw', r"\bwcw\b|\bnwa\b"), ('ecw', r"\becw\b|extreme championship")]
PPVRX = [(n, re.compile(p)) for n, p in PPV]
SHOWRX = [(n, re.compile(p)) for n, p in SHOWS]
PROMORX = [(n, re.compile(p)) for n, p in PROMO]
WR = re.compile(r"\b(wwf|wwe|wcw|ecw|awa|wccw|uswa|gwf|wrestl\w*|nitro|starrcade|summer ?slam|royal rumble|survivor series|king of the ring|in your house|halloween havoc|great american bash|bash at the beach|super ?brawl|slamboree|fall brawl|spring stampede|clash of (the )?champions|smack ?down|raw is war|monday night raw|coliseum video|saturday night'?s main event|tuesday night titans|hardcore tv|november to remember|barely legal|guilty as charged|anarchy rulz|hardcore heaven|cyber ?slam|souled out|road wild|hog wild|chi-?town rumble|capital combat|beach blast|bunkhouse stampede|crockett|battle ?bowl|world class championship|smoky mountain|mid-south|superclash|gorgeous ladies|ring of honor|total nonstop|sunday night heat|shotgun saturday|nwa (world|pro|main|power|tbs|starrcade|clash|wcw|jcp|tna|wrestl)|tna (impact|wrestling|weekly|ppv|nwa)|world championship wrestling)\b")
X = re.compile(r"\b(n64|nintendo|playstation|ps[1-5x]|psx|xbox|gamecube|dreamcast|sega|genesis|snes|\bnes\b|game ?boy|gameplay|longplay|walkthrough|play ?through|let'?s play|video ?game|\brom\b|emulat\w*|arcade|2k\d\d|svr|here comes the pain \(|caw\b|mod(s|ded)?\b|efed|e-fed|fire pro|backyard|podcast|shoot interview|shoot with|kayfabe commentaries|timeline:|youshoot|(?<!in )review|reaction|reacts|tribute|\bamv\b|music video|\bmv\b|theme songs?|entrance themes?|soundtrack|\bost\b|titantron|promo pics|photos?|magazine|figures?|toys?|unboxing|ncaa|olympics?|high school|collegiate|college wrestling|freestyle|greco|sumo|arm ?wrestling|mud wrestling|oil wrestling|bikini|catfight|mixed wrestling|session|aew|\bnxt\b|ecw on sci-?fi|wwe ecw|lucha libre|\baaa\b|cmll|njpw|ajpw|new japan(?! supershow)|all japan|\bnoah\b|puroresu|joshi|fmw|michinoku|dragon gate|zero-?one|big japan|espa[nñ]ol|latino|castellano|deutsch|german|fran[cç]ais|french|italiano|\bitalia\b|portugu[eê]s|dublado|arabic|hindi|russian|polski|xpw|czw|deathmatch|wwc\b|rebellion|insurrextion|fan ?made|fantasy|custom|recreat\w*|animation|animated|cartoon|hulk hogan'?s rock|parody|spoof|sex|nude|xxx)\b")
CORE = re.compile(r"\b(wwf|wwe|wcw|ecw|wccw|uswa|gwf|msw|wrestl\w*|wrestle ?mania|summer ?slam|starrcade|royal rumble|survivor series|king of the ring|in your house|clash of (the )?champions|halloween havoc|great american bash|bash at the beach|super ?brawl|slamboree|smack ?down|raw is war|monday night raw|monday nitro|wcw nitro|nitro hour|coliseum video|saturday night'?s main event|tuesday night titans|world class championship|smoky mountain|mid[- ]south|superclash|gorgeous ladies|ring of honor|total nonstop|sunday night heat|shotgun saturday|world championship wrestling|nwa (world|pro|main|power|tbs|starrcade|clash|wcw|jcp|tna)|awa (all|champ|super|wrestl|on espn|tv)|hulk hogan|ric flair|n\.?w\.?o\b)\b")
POD = re.compile(r"\b(wrestling mayhem show|mat men|reliving the war|wrestling bios|wrestling @random|off topic|observer|newsletter|\bpwi\b|illustrated|bonus content|who killed wcw|dark side of the ring|worst year of our lives|botchamania|wrestling with (?!shadows)|whatculture|cultaholic|watch ?along|retrospective|ranking|top \d+|twitch|brawlhalla|discord|stream(ed|ing)?|\bvod\b|why we fight|wildlife|panda|pancrase|uwfi|shoot wrestling|\bmma\b|\bufc\b|pride fc|k-1|situation update|masters commission|talent show|let'?s watch)\b")
ERA = re.compile(r"\b(wwf|wcw|nitro|prime ?time wrestling|tuesday night titans|wrestling challenge|superstars of wrestling|in your house|clash of (the )?champions|halloween havoc|super ?brawl|slamboree|fall brawl|spring stampede|uncensored|bash at the beach|souled out|road wild|hog wild|world war (3|iii)|wrestle ?war|chi-?town rumble|capital combat|beach blast|bunkhouse stampede|crockett cup|battle ?bowl|awa|wccw|world class|uswa|smoky mountain|gwf|global wrestling|mid-south|uwf|coliseum video|hardcore tv|ecw on tnn|barely legal|november to remember|heat ?wave|living dangerously|guilty as charged|anarchy rulz|hardcore heaven|cyber ?slam|wrestlepalooza|shotgun saturday|livewire|action zone|all[- ]american wrestling|georgia championship|championship wrestling from florida|mid-atlantic|jim crockett|world championship wrestling|pro wrestling usa|super ?clash|wrestle ?rock|lpwa|poww|gorgeous ladies|tuesday in texas|wrestling classic|valentine'?s day massacre|rock bottom|over the edge|fully loaded|sunday night heat|jakked|new blood rising|power hour|saturday night'?s main event|stampede wrestling|memphis wrestling)\b")
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
ROM = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20, 'x-seven': 17, 'x7': 17, 'x8': 18, 'x-8': 18}

def y2(y):
    y = int(y)
    if y >= 100: return y
    return 1900 + y if y >= 30 else 2000 + y

def dates(s):
    out = []
    for m in re.finditer(r"(?<!\d)((?:19|20)\d\d)[.\-/ _](\d{1,2})[.\-/ _](\d{1,2})(?!\d)", s):
        out.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"(?<!\d)((?:19|20)\d\d)(\d\d)(\d\d)(?!\d)", s):
        out.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"(?<!\d)(\d{1,2})[.\-/_](\d{1,2})[.\-/_](\d{4}|\d{2})(?!\d)", s):
        a, b, y = int(m.group(1)), int(m.group(2)), y2(m.group(3))
        if a > 12 and b <= 12: a, b = b, a
        out.append((y, a, b))
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d\d)\b", s):
        out.append((int(m.group(3)), MON[m.group(1)], int(m.group(2))))
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+((?:19|20)\d\d)\b", s):
        out.append((int(m.group(3)), MON[m.group(2)], int(m.group(1))))
    return [(y, mo, d) for y, mo, d in out if 1 <= mo <= 12 and 1 <= d <= 31]

def years(s):
    return [int(y) for y in re.findall(r"(?<!\d)((?:19[5-9]|20[0-2])\d)(?!\d)", s)]

def mania_year(low):
    m = re.search(r"wrestle ?mania[\s\-:]*(x-seven|x-?[78]|[ivx]{1,5}|\d{1,2}|2000)\b", low)
    if not m: return None
    v = m.group(1)
    if v == '2000': return 2000
    n = ROM.get(v) if not v.isdigit() else int(v)
    if not n: return None
    return 1984 + n

def era(title, ident, desc, mdate):
    low = (title + ' ' + ident.replace('_', ' ').replace('-', ' ')).lower()
    lowt = (title + ' ' + ident).lower()
    ds = dates(lowt)
    ad = ''
    for y, mo, d in ds:
        if 1984 <= y <= 2004:
            ad = '%04d-%02d-%02d' % (y, mo, d); break
    y4 = years(lowt)
    if y4 and not any(1984 <= y <= 2004 for y in y4) and not (mania_year(low) and 1985 <= mania_year(low) <= 2004): return None, ''
    if not y4 and ds and any(not (1984 <= y <= 2004) for y, _, _ in ds): return None, ''
    ys = y4 + [y for y, _, _ in ds]
    my = mania_year(low)
    if my:
        if 1985 <= my <= 2004: return my, ad
        if not any(1984 <= y <= 2004 for y in ys): return None, ''
    good = [y for y in ys if 1984 <= y <= 2004]
    if good: return (int(ad[:4]) if ad else good[0]), ad
    if ys: return None, ''
    dl = (desc or '').lower()[:3000]
    dd = dates(dl)
    dgood = [(y, mo, d) for y, mo, d in dd if 1984 <= y <= 2004]
    dyears = years(dl)
    if ERA.search(low):
        if dgood: return dgood[0][0], '%04d-%02d-%02d' % dgood[0]
        g = [y for y in dyears if 1984 <= y <= 2004]
        return (g[0] if g else 0), ''
    if dgood and not any(y >= 2005 for y in dyears):
        return dgood[0][0], '%04d-%02d-%02d' % dgood[0]
    g = [y for y in dyears if 1984 <= y <= 2004]
    if g and not any(y >= 2005 for y in dyears): return g[0], ''
    m = re.match(r"((?:19|20)\d\d)", mdate or '')
    if m and 1984 <= int(m.group(1)) <= 2004:
        ad2 = ''
        m2 = re.match(r"(\d{4})-(\d\d)-(\d\d)", mdate or '')
        if m2 and not (m2.group(2) == '01' and m2.group(3) == '01'): ad2 = m2.group(0)
        return int(m.group(1)), ad2
    return None, ''

def tag(low):
    ppv = ''
    for n, rx in PPVRX:
        if rx.search(low): ppv = n; break
    show = ''
    for n, rx in SHOWRX:
        if rx.search(low): show = n; break
    promo = ''
    for n, rx in PROMORX:
        if rx.search(low): promo = n; break
    if ppv and (promo or CORE.search(low)): return 'ppv:' + ppv, ppv
    if show: return show, ''
    return promo or 'other', ''

def title_ok(t, ident):
    low = (t + ' ').lower()
    if not WR.search(low) and not WR.search(ident.lower().replace('-', ' ').replace('_', ' ')): return False
    if X.search(low) or POD.search(low): return False
    if re.search(r"[^\x00-\xff‐-‧™]", t): return False
    if re.search(r"\b(straight outta|eazy-?e|dr\.? dre|ice cube|n\.w\.a)\b", low): return False
    return True

SHOWW = re.compile(r"\b(raw|nitro|smack ?down|velocity|ptw|snme|wcwsn|wcw sn|hardcore tv|prime ?time|superstars|thunder|sunday night heat|clash|ppv|house show|msg|boston garden|spectrum)\b")

def showdate(t, ident):
    low = (t + ' ' + ident.replace('-', ' ').replace('_', ' ')).lower()
    if not SHOWW.search(low): return False
    tl = (t + ' ').lower()
    if X.search(tl) or POD.search(tl) or re.search(r"[^\x00-\xff\u2010-\u2027\u2122]", t): return False
    return any(1984 <= y <= 2004 for y, _, _ in dates((t + ' ' + ident).lower()))

have = set()
if os.path.exists(RAWF):
    have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8')))
old = json.load(gzip.open(WF, 'rt', encoding='utf-8')) if os.path.exists(WF) else []
UPL = collections.Counter(x.get('u', '') for x in old)
if os.environ.get('FRESH') == '1': old = []
have |= set(x['i'] for x in old)
print('known ids', len(have), 'existing wrestling', len(old), flush=True)

def phrases(ps):
    return 'title:(' + ' OR '.join('"%s"' % p for p in ps) + ')'

def plan():
    seen = {}
    def add(items, why):
        n = 0
        for it in items:
            i = it.get('identifier')
            if not i or i in seen or i in have: continue
            t = S(it.get('title'))
            loose = why.startswith(('desc', 'uploader', 'wcol', 'extra'))
            if not title_ok(t, i) and not showdate(t, i) and not (loose and not X.search((t + ' ').lower()) and not POD.search((t + ' ').lower()) and not re.search(r"[^\x00-\xff\u2010-\u2027\u2122]", t)): continue
            lowt = (t + ' ' + i).lower()
            ys = years(lowt) + [y for y, _, _ in dates(lowt)]
            my = mania_year(lowt.replace('-', ' ').replace('_', ' '))
            if ys and not any(1984 <= y <= 2004 for y in ys) and not (my and 1985 <= my <= 2004): continue
            it['title'] = t; it['why'] = why
            seen[i] = it; n += 1
        print(why[:70].ljust(70), len(items), 'new', n, 'total', len(seen), flush=True)
    cols = scrape('mediatype:collection AND (title:(wrestling OR wrestlemania OR wwf OR wwe OR wcw OR ecw OR nwa OR awa OR coliseum OR "pay per view" OR ppv OR nitro OR raw OR smackdown) OR subject:(wrestling OR wwf OR wwe OR wcw OR ecw))', fields='identifier,title')
    cids = []
    for c in cols:
        t = S(c.get('title')).lower(); i = c.get('identifier', '')
        if re.search(r"(japan|puroresu|lucha|podcast|radio|magazine|game|rom|book|comic|photo|audio|music|amateur|ncaa|olympic|arm wrest|sumo)", t + ' ' + i.lower()): continue
        if not re.search(r"(wrestl|wwf|wwe|wcw|ecw|\bnwa\b|\bawa\b|coliseum|ppv|pay per view|nitro|smackdown)", t + ' ' + i.lower()): continue
        cids.append(i)
    cids = sorted(set(cids + ['wrestlingtelevision', 'vhssports', 'sportstelevision']))
    print('collections', len(cids), cids[:80], flush=True)
    for k in range(0, len(cids), 15):
        add(scrape('mediatype:movies AND collection:(' + ' OR '.join(cids[k:k + 15]) + ')'), 'collections %d' % k)
    add(scrape('mediatype:movies AND subject:(wrestling OR wwf OR wwe OR wcw OR ecw OR "pro wrestling" OR "professional wrestling" OR nitro OR wrestlemania OR "monday night raw" OR smackdown)'), 'subject wrestling')
    add(scrape('mediatype:movies AND subject:(awa OR wccw OR uswa OR "world class" OR "smoky mountain" OR "mid-south" OR "jim crockett" OR starrcade OR "clash of the champions" OR "coliseum video" OR "prime time wrestling" OR ppv OR "pay per view" OR "pay-per-view")'), 'subject territories')
    add(scrape('mediatype:movies AND title:(wwf OR wwe OR wcw OR ecw OR wccw OR uswa OR gwf)'), 'title promos')
    add(scrape('mediatype:movies AND title:(wrestling OR wrestlemania OR summerslam OR starrcade OR nitro OR smackdown OR slamboree OR superbrawl)'), 'title words')
    add(scrape('mediatype:movies AND title:(awa OR nwa OR tna OR roh OR glow) AND (title:(wrestling OR impact OR championship OR clash OR starrcade OR superclash OR honor) OR subject:wrestling OR description:wrestling)'), 'title short promos')
    groups = {
     'wwf weekly': ['monday night raw', 'raw is war', 'sunday night heat', 'shotgun saturday night', 'livewire', 'action zone', 'wrestling challenge', 'prime time wrestling', 'all-american wrestling', 'all american wrestling', 'tuesday night titans', "saturday night's main event", 'saturday nights main event', 'the main event', 'superstars of wrestling', 'wwf superstars', 'wwe velocity', 'wwf jakked', 'wwf metal', 'wrestling spotlight', 'wwf mania', 'wwf championship wrestling', 'wwe confidential', 'wwe bottom line', 'wwe afterburn', 'wwf attitude'],
     'wwf house': ['madison square garden', 'boston garden', 'philadelphia spectrum', 'maple leaf gardens', 'house show', 'coliseum video', 'coliseum home video', 'wwf home video', 'wwe home video', 'silver vision'],
     'wwf ppv 1': ['royal rumble', 'survivor series', 'king of the ring', 'in your house', 'wrestling classic', 'this tuesday in texas', 'tuesday in texas', 'over the edge', 'rock bottom', "st. valentine's day massacre", 'fully loaded', 'bad blood', 'badd blood'],
     'wwf ppv 2': ['backlash', 'judgment day', 'unforgiven', 'no mercy', 'armageddon', 'no way out', 'vengeance', 'invasion'],
     'wcw weekly': ['monday nitro', 'wcw nitro', 'wcw thunder', 'wcw saturday night', 'wcw worldwide', 'wcw pro', 'wcw power hour', 'wcw main event', 'world championship wrestling', 'nwa world wide', 'nwa pro', 'nwa main event', 'wcw prime'],
     'wcw ppv 1': ['clash of the champions', 'clash of champions', 'great american bash', 'bash at the beach', 'halloween havoc', 'fall brawl', 'spring stampede', 'uncensored', 'road wild', 'hog wild', 'world war 3', 'souled out', 'new blood rising', 'wrestlewar', 'wrestle war'],
     'wcw ppv 2': ['chi-town rumble', 'capital combat', 'beach blast', 'crockett cup', 'bunkhouse stampede', 'battlebowl', 'wcw mayhem', 'wcw sin', 'wcw greed', 'supershow', 'starrcade', 'superbrawl', 'slamboree'],
     'ecw': ['hardcore tv', 'ecw on tnn', 'barely legal', 'november to remember', 'heat wave', 'heatwave', 'living dangerously', 'guilty as charged', 'anarchy rulz', 'hardcore heaven', 'cyberslam', 'wrestlepalooza', 'extreme championship wrestling', 'eastern championship wrestling'],
     'territories': ['all-star wrestling', 'all star wrestling', 'championship wrestling on espn', 'superclash', 'wrestlerock', 'world class championship wrestling', 'world class wrestling', 'memphis wrestling', 'mid-south wrestling', 'universal wrestling federation', 'championship wrestling from florida', 'georgia championship wrestling', 'mid-atlantic championship wrestling', 'stampede wrestling', 'global wrestling federation', 'smoky mountain wrestling', 'pro wrestling usa', 'gorgeous ladies of wrestling', 'powerful women of wrestling', 'southwest championship wrestling', 'continental championship wrestling', 'pacific northwest wrestling', 'portland wrestling', 'international championship wrestling', 'american wrestling association', 'windy city wrestling', 'texas all-star wrestling', 'central states wrestling', 'deep south wrestling', 'southern championship wrestling', 'uswa championship wrestling', 'cwa championship wrestling', 'wow women of wrestling', 'womens extreme wrestling'],
     'late era': ['tna impact', 'tna weekly', 'nwa tna', 'total nonstop action', 'ring of honor', 'world wrestling all-stars', 'wwa the inception', 'xwf', 'heroes of wrestling', 'memphis championship wrestling', 'ohio valley wrestling', 'mlw underground'],
     'generic': ['pro wrestling', 'professional wrestling', 'wrestling ppv', 'wrestling pay per view', 'wrestling vhs', 'championship wrestling', 'wrestling superstars', 'wrestling tape', 'wrestling compilation', 'steel cage', 'battle royal', 'tag team championship', 'heavyweight championship'],
    }
    for name, ps in groups.items():
        add(scrape('mediatype:movies AND ' + phrases(ps)), 'phrases ' + name)
    add(scrape('mediatype:movies AND description:("world wrestling federation" OR "world championship wrestling" OR "extreme championship wrestling" OR "monday nitro" OR "monday night raw" OR "wrestlemania" OR "wwf superstars" OR "prime time wrestling" OR "wcw saturday night" OR "clash of the champions" OR "coliseum video" OR "american wrestling association" OR "world class championship wrestling" OR "mid-south wrestling" OR "jim crockett promotions" OR "smoky mountain wrestling" OR "pro wrestling" OR "professional wrestling")'), 'desc wrestling')
    add(scrape('mediatype:movies AND (title:(k81 OR "chasing that w" OR "hallo riched" OR msw OR wcwsn OR ptw OR snme) OR description:(k81 OR "chasing that w"))'), 'desc uploaders marks')
    ups = [u for u, n in UPL.most_common(2000) if u and n >= 2]
    print('uploaders', len(ups), flush=True)
    for u in ups:
        items = scrape('mediatype:movies AND uploader:"%s"' % u.replace('"', ''), pages=8)
        good = sum(1 for it in items if title_ok(S(it.get('title')), it.get('identifier', '')))
        trusted = len(items) <= 4000 and good >= 0.5 * max(1, len(items))
        if trusted:
            for it in items: it['tr'] = 1
        add(items, ('uploader ' if trusted else 'strict ') + u.split('@')[0][:6] + ' %d/%d' % (good, len(items)))
    xf = os.path.join(here, 'wrestling_extra.txt')
    if os.path.exists(xf):
        for line in open(xf):
            line = line.strip()
            if line: add(scrape('mediatype:movies AND (' + line + ')'), 'extra ' + line)
    cands = sorted(seen.values(), key=lambda x: -(x.get('downloads') or 0))
    with gzip.open(os.path.join(PARTS, 'wcands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(cands, f, ensure_ascii=False, separators=(',', ':'))
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
REJ = collections.Counter()
ERAS = []

def meta(it):
    if BUDGET and time.time() - T0 > BUDGET: return None
    ident = it['identifier']
    j = get('https://archive.org/metadata/' + urllib.parse.quote(ident))
    if not j or not j.get('files') or j.get('is_dark'):
        REJ['nofiles'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true':
        REJ['restricted'] += 1; return None
    lang = S(m.get('language')).lower()
    if lang and not re.search(r"eng|english|^en\b|und|zxx|mul|no linguistic", lang):
        REJ['lang'] += 1; return None
    title = S(m.get('title')) or it.get('title', '')
    desc = ' '.join(S(m.get('description')).split())
    subj = S(m.get('subject')) if not isinstance(m.get('subject'), list) else ';'.join(str(x) for x in m.get('subject'))
    low = (title + ' ' + ident.replace('-', ' ').replace('_', ' ')).lower()
    tl = (title + ' ').lower()
    if X.search(tl) or POD.search(tl) or re.search(r"[^\x00-\xff\u2010-\u2027\u2122]", title):
        REJ['title'] += 1; return None
    if not it.get('tr') and not CORE.search(low) and not CORE.search((subj + ' ' + desc[:500]).lower()):
        REJ['notwrestling'] += 1; return None
    if it.get('tr') and not CORE.search(low) and not CORE.search((subj + ' ' + desc[:500]).lower()) and re.search(r"\b(nba|nfl|mlb|nhl|football|basketball|baseball|hockey|boxing|episode|season \d|s\d\de\d\d|movie|film|trailer|commercials?|news|concert|live at)\b", (title + ' ' + subj).lower()):
        REJ['trustjunk'] += 1; return None
    if POD.search((subj + ' ' + desc[:300]).lower()) and not ERA.search(low):
        REJ['podcast'] += 1; return None
    if re.search(r"\b(video ?game|gameplay|longplay|podcast|backyard|fan ?made|e-?fed|shoot interview)\b", (subj + ' ' + desc[:400]).lower()):
        REJ['descjunk'] += 1; return None
    e, ad = era(title, ident, desc, S(m.get('date')))
    if e is None:
        REJ['era'] += 1
        if len(ERAS) < 400: ERAS.append(title[:80] + ' | ' + ident[:40] + ' | ' + S(m.get('date'))[:10])
        return None
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
        if sz and sz / 1e6 / (d / 60) > 40: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 900:
        REJ['short'] += 1; return None
    files.sort(key=lambda f: f[0])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    k, _ = tag(low)
    return {'i': ident, 'q': 'wrest', 't': title[:200], 'd': S(m.get('date')), 'y': S(m.get('year')), 'c': col[:4], 's': subj[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': k, 'e': e, 'ad': ad, 'u': S(m.get('uploader'))[:80]}

def run_meta():
    cands = json.load(gzip.open(os.path.join(PARTS, 'wcands.json.gz'), 'rt', encoding='utf-8'))
    cands = [c for c in cands if c['identifier'] not in have][SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'w-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res), 'rejects', dict(REJ), flush=True)
    random.seed(SHARD)
    for x in random.sample(ERAS, min(25, len(ERAS))): print('  era-reject', x)

def merge():
    allx = []
    for x in old:
        tl = (x['t'] + ' ').lower(); low = (x['t'] + ' ' + x['i'].replace('-', ' ').replace('_', ' ')).lower()
        if X.search(tl) or POD.search(tl): continue
        if not CORE.search(low) and not CORE.search((x.get('s', '') + ' ' + x.get('ds', '')).lower()): continue
        x['k'] = tag(low)[0]; allx.append(x)
    ids = set(x['i'] for x in allx); add = 0
    for p in sorted(glob.glob(os.path.join(PARTS, 'w-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] in ids: continue
            ids.add(x['i']); allx.append(x); add += 1
    with gzip.open(WF, 'wt', encoding='utf-8') as f:
        json.dump(allx, f, ensure_ascii=False, separators=(',', ':'))
    hrs = sum(sum(f[1] for f in x['f']) for x in allx) / 3600
    print('added', add, 'total', len(allx), 'hours', round(hrs), flush=True)
    print('exact dates', sum(1 for x in allx if x.get('ad')), 'distinct', len(set(x['ad'] for x in allx if x.get('ad'))))
    print('per year', sorted(collections.Counter(x['e'] for x in allx).items()))
    kc = collections.Counter(x['k'] for x in allx)
    print('per tag', kc.most_common(120))
    promo = collections.Counter()
    for x in allx:
        low = x['t'].lower()
        p = 'other'
        for n, rx in PROMORX:
            if rx.search(low): p = n; break
        if p == 'other' and not x['k'].startswith('ppv:') and x['k'] not in ('wwf', 'wcw', 'ecw', 'other'): p = x['k']
        promo[p] += 1
    print('per promotion', promo.most_common(60))
    pv = collections.defaultdict(set)
    for x in allx:
        if x['k'].startswith('ppv:'): pv[x['k'][4:]].add(x['e'])
    print('ppv coverage')
    R = lambda a, b: list(range(a, b + 1))
    EXP = {'wrestlemania': R(1985, 2004), 'summerslam': R(1988, 2004), 'royal rumble': R(1988, 2004), 'survivor series': R(1987, 2004), 'king of the ring': R(1993, 2002), 'in your house': R(1995, 1999), 'backlash': R(1999, 2004), 'judgment day': [1998] + R(2000, 2004), 'unforgiven': R(1998, 2004), 'no mercy': R(1999, 2004), 'armageddon': [1999, 2000, 2002, 2003, 2004], 'no way out': [1998] + R(2000, 2004), 'vengeance': R(2001, 2004), 'bad blood': [1997, 2003, 2004], 'fully loaded': R(1998, 2000), 'wrestling classic': [1985], 'this tuesday in texas': [1991], 'over the edge': [1998, 1999], 'rock bottom': [1998], "st. valentine's day massacre": [1999], 'invasion': [2001], 'starrcade': R(1984, 2000), 'great american bash': R(1985, 1992) + R(1995, 2000) + [2004], 'bash at the beach': R(1994, 2000), 'halloween havoc': R(1989, 2000), 'superbrawl': R(1991, 2001), 'slamboree': R(1993, 2000), 'fall brawl': R(1993, 2000), 'spring stampede': [1994] + R(1997, 2000), 'uncensored': R(1995, 2000), 'road wild': R(1996, 1999), 'world war 3': R(1995, 1998), 'souled out': R(1997, 2000), 'mayhem': [1999, 2000], 'new blood rising': [2000], 'sin': [2001], 'greed': [2001], 'chi-town rumble': [1989], 'wrestlewar': R(1989, 1992), 'capital combat': [1990], 'beach blast': [1992, 1993], 'crockett cup': R(1986, 1988), 'bunkhouse stampede': [1988], 'battlebowl': [1993], 'clash of the champions': R(1988, 1997), 'barely legal': [1997], 'november to remember': R(1993, 2000), 'heat wave': R(1994, 2000), 'living dangerously': R(1998, 2000), 'guilty as charged': R(1999, 2001), 'anarchy rulz': [1999, 2000], 'hardcore heaven': R(1994, 2000), 'cyberslam': R(1996, 2000), 'wrestlepalooza': [1995, 1997, 1998], 'superclash': [1985, 1986, 1988, 1990], 'wrestlerock': [1986], "saturday night's main event": R(1985, 1992), 'the main event': R(1988, 1991), 'supershow': R(1991, 1993)}
    fy = my = 0
    for n, _ in PPV:
        got = sorted(y for y in pv.get(n, []) if y)
        miss = [y for y in EXP.get(n, []) if y not in got]
        fy += len(EXP.get(n, [])) - len(miss); my += len(miss)
        print('  ', n.ljust(30), len([1 for x in allx if x['k'] == 'ppv:' + n]), 'found', got, 'missing', miss)
    print('ppv event-years found', fy, 'missing', my)
    wk = collections.defaultdict(collections.Counter)
    for x in allx:
        if not x['k'].startswith('ppv:') and x['e']: wk[x['k']][x['e']] += 1
    print('weekly by year')
    for k, c in sorted(wk.items(), key=lambda kv: -sum(kv[1].values())):
        print('  ', k.ljust(30), sum(c.values()), sorted(c.items()))
    uc = collections.Counter(x.get('u', '').split('@')[0][:6] for x in allx)
    print('uploader prefixes', uc.most_common(40))
    random.seed(11)
    print('samples')
    for x in random.sample(allx, min(60, len(allx))):
        print('  ', x['e'], x['ad'] or '-', x['k'].ljust(24)[:24], round(sum(f[1] for f in x['f']) / 60), 'min', len(x['f']), 'f |', x['t'][:90], '|', x['i'][:40])

if MODE == 'plan': plan()
elif MODE == 'meta': run_meta()
elif MODE == 'merge': merge()
