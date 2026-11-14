import json, gzip, os, re, sys, time, glob, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts')
os.makedirs(OUT, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
FOCUS = [z.strip().lower() for z in os.environ.get('FOCUS', '').split(';') if z.strip()]
THREADS = int(os.environ.get('THREADS', '16')); BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60; T0 = time.time()
OUTF = os.path.join(OUT, 'needs.json.gz'); REPF = os.path.join(OUT, 'needs_report.json')
GUIDEF = os.path.join(here, 'needs_guide.json.gz'); GP = os.path.join(PARTS, 'needs_guide.json.gz'); CP = os.path.join(PARTS, 'needs_cands.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_needs.json'), encoding='utf-8'))
QMAP = {'sitcom': 'prime', 'drama': 'prime', 'kids': 'kids', 'soap': 'soap', 'game': 'game', 'talk': 'talk', 'late': 'late', 'news': 'news', 'mag': 'mag', 'doc': 'pub', 'cook': 'cook', 'music': 'music', 'sports': 'sports', 'special': 'prime', 'movie-package': 'movie', 'movie': 'movie', 'relig': 'block', 'gov': 'news', 'morning': 'news', 'variety': 'prime', 'reality': 'prime', 'comedy': 'prime', 'anthology': 'prime', 'wrestling': 'wrest', 'shopping': 'block', 'fitness': 'block', 'infomercial': 'block', 'court': 'prime'}
OTHERQ = [(r'wrestling|wwf|wcw|nwa|titans|clash of the champions|starrcade|survivor series|royal rumble|summerslam|wrestlemania|wccw|awa|gorgeous ladies|glow', 'wrest'), (r'house of representatives|senate|press club|c-span|white house|hearings|newsfeed', 'news'), (r'shopping|qvc|psychic|amazing discoveries|prevue|body by|bodies in motion|getting fit|it figures|medical television|hour of power|700 club|infomercial', 'block'), (r'motorweek|victory garden|homeworks|shortstories|arts films', 'pub'), (r'star search|house of style|awards|grammy|telethon|pageant|apollo', 'music' if False else 'prime')]
SCRIPTED = {'sitcom', 'drama', 'kids'}
EVENT = {'sports', 'special', 'movie-package', 'movie'}
EPLEN = {'sitcom': 1080, 'drama': 2280, 'kids': 540}
TVCOL = 'television OR television_inbox OR classic_tv OR classic_tv_1980s OR classic_tv_1990s OR vhstvshows OR vhsvault OR gorelicktv OR smokesvhsdvrcollection OR sitcoms OR televisionmovies OR vhsnews OR gameshows OR dvdtray OR dvdtray_inbox OR tvarchive OR saturdaymorningcartoons OR classic_cartoons OR sports'
TVSET = set(TVCOL.split(' OR '))
DISQ = 'title:(season OR seasons OR episode OR episodes OR complete OR series OR nbc OR cbs OR abc OR fox OR pbs OR hbo OR espn OR vhs OR commercials OR woc OR pilot OR finale OR s0* OR s1* OR 1x* OR 2x* OR 3x* OR 4x* OR 5x* OR 198* OR 199* OR 2000 OR 2001 OR 2002 OR 2003 OR 2004) OR subject:(television OR sitcom OR "tv series" OR "tv show" OR nbc OR cbs OR abc OR pbs OR vhs OR commercials OR tv)'
NETRX = {'nbc': 'nbc', 'cbs': 'cbs', 'abc': 'abc', 'fox': 'fox', 'pbs': 'pbs', 'hbo': 'hbo', 'tbs': 'tbs|wtbs|superstation', 'wgn': 'wgn', 'wor': 'wor', 'usa': 'usa network|usa', 'tnt': 'tnt', 'tnn': 'tnn|nashville network', 'bet': 'bet', 'mtv': 'mtv', 'vh1': 'vh1|vh-1', 'cnn': 'cnn', 'espn': 'espn', 'cspan': 'c-span|cspan', 'c-span': 'c-span|cspan', 'a&e': 'a&e|a and e|arts and entertainment', 'discovery': 'discovery', 'disney': 'disney', 'nick': 'nick|nickelodeon', 'nickelodeon': 'nick|nickelodeon', 'nickatnite': 'nick at nite|nickelodeon', 'lifetime': 'lifetime', 'cbn': 'cbn|family channel', 'family': 'family channel|cbn', 'comedy': 'comedy central|comedy channel', 'ha': 'ha!', 'sci-fi': 'sci-fi|sci fi|scifi', 'showtime': 'showtime', 'cinemax': 'cinemax', 'tlc': 'tlc|learning channel', 'food': 'food network|tvfn', 'e!': 'e!', 'amc': 'amc|american movie classics', 'bravo': 'bravo', 'qvc': 'qvc', 'hsn': 'hsn|home shopping', 'tmc': 'movie channel|tmc', 'cartoon': 'cartoon network', 'ppv': 'ppv|pay per view|pay-per-view', 'upn': 'upn', 'wb': 'wb|kids wb', 'syn': 'syndicat\\w*', 'prevue': 'prevue', 'movietime': 'movietime'}
NETNAMES = {'tnt', 'amc', 'vh-1', 'vh 1', 'vh1', 'hsn', 'qvc', 'turner network television', 'american movie classics', 'home shopping network', 'braves', 'cubs', 'atlanta braves', 'chicago cubs', 'nascar', 'winston cup', 'college basketball', 'college football', 'house of representatives', 'us house of representatives', 'us senate', 'walt disney', 'oscars', 'academy awards', 'world series', 'nba finals', 'usfl', 'hbo movie', 'hbo premiere', 'hbo boxing', 'house session', 'senate session', 'miss america', 'grammy awards', 'super bowl', 'stanley cup', 'ncaa tournament', 'mtv', 'bet', 'nickelodeon', 'cnn', 'espn', 'explorer', 'mystery', 'superman', 'bozo', 'game of the week', 'late show', 'sunday morning', 'beverly hills', 'homicide', 'prime news', 'e news', 'safari', 'invention', 'real world', 'time machine', 'pov'}
JUNK = re.compile(r"\b(trailers?|teasers?|promos?|bumpers?|theme song|theme music|soundtrack|ost|reviews?|reviewed|reaction|reacts?|podcast|commentary|video essay|explained|analysis|ranking|ranked|top \d+ |fan ?made|fan ?edit|fan ?film|fanvid|amv|ytp|parody|spoof|abridged|recap|gameplay|walkthrough|playthrough|longplay|speedrun|video ?game|pc game|dos game|ps[1-5]|playstation|xbox|nintendo|sega|genesis|snes|nes|game ?boy|gba|amiga|atari|commodore|c64|pinball|slot machine|rom ?hack|emulator|lego|toys?|unboxing|action figures?|audiobook|audio book|ebook|pdf|comic book|comics|novel|screenplay|sheet music|karaoke|remix|lyrics|mixtape|twitch|tiktok|livestream|live stream|upscaled?|deepfake|supercut|mashup|clips?|scenes?|moments|excerpts?|outtakes|gag reel|slideshow|screensaver|wallpaper|rifftrax|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|german dub|fran[cç]ais|french dub|italiano|portugu[eê]s|legendado|subtitulado|vostfr|russian|polski|lektor|hindi|arabic|turkish|svenska|suomi|norsk|dansk|magyar|sub ita|sub esp|subbed|vietsub|tagalog|indonesia|xxx|porn|hentai|sermon|city council|town meeting|selectmen|school committee|board of|webinar|zoom|discord)\b")
JUNKS = re.compile(r"\b(interviews?|panel|q&a|convention|comic-?con|reunion|tribute|retrospective|behind the scenes|making of|documentary|bloopers?|cast of|where are they now|true hollywood story|opening|intro|credits|themes?)\b")
JUNKN = re.compile(r"\b(highlights|best of|compilation)\b")
JUNKD = re.compile(r"\b(podcast|gameplay|walkthrough|let's play|longplay|fan ?film|fan ?made|video ?game|radio (show|program|broadcast)|old time radio|audio only|reaction video|public access|community television|community media|city council|school district|chamber of commerce|webinar)\b")
FOREIGN = re.compile(r"\b(saison|temporada|staffel|episodio|epis[oó]dio|cap[ií]tulo|folge|piloto|serie tv|vf|pt br|dual audio|dublagem|napisy|aflevering|odcinek|b[oö]l[uü]m)\b")
SPIN = re.compile(r"\b(reboot|revival|remake|new class|college years|animated series|netflix|hulu|disney\+|paramount\+|hbo max|prime video)\b")
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
YR = re.compile(r'(?<!\d)(19[4-9]\d|20[0-3]\d)(?!\d)')
MOD2 = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](0[5-9]|[12]\d)\b|\b20(0[5-9]|[12]\d)[01]\d[0-3]\d\b')
TAPE = re.compile(r"\b(vhs|betamax|tape|taped|recorded|recording|commercials|woc|broadcast|aired|airing|rerun|syndicat\w*|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|tbs|wtbs|wgn|tnt|usa network|nick at nite|nickelodeon|tv land|a&e|mtv|vh1|cnn|c-span|tnn|lifetime|discovery|primetime|prime time|off air|off-air)\b")
TAPE2 = re.compile(r"\b(vhs|betamax|commercials|woc|off air|off-air|home recording)\b")
DESCEV = re.compile(r"\b(sitcom|tv series|television series|tv show|television show|television program|tv program|game show|talk show|soap opera|animated series|cartoon series|miniseries|mini-series|nbc|cbs|abc|pbs|hbo|syndicat\w*|vhs|commercials|laugh track|primetime|prime time|aired|broadcast|episodes?)\b")
SE1 = re.compile(r"\bs(?:eason)?\s?(\d{1,2})[\s._-]{0,3}(?:e|ep|episode)\s?(\d{1,3})\b|\b(\d{1,2})x\s?(\d{2,3})\b")
EPN = re.compile(r"\b(?:episode|ep)\.?\s?#?(\d{1,4})\b")
WORDN = {w: i + 1 for i, w in enumerate('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen'.split())}
WORDN.update({w: i + 1 for i, w in enumerate('first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split())})
MULTI = re.compile(r"\bseasons\b|\b(?:s|season)\s?\d{1,2}\s?(?:-|&|and|to|thru|through)\s?(?:s|season)?\s?\d{1,2}\b|complete series|all episodes|all seasons|entire series|full series|complete collection|the complete|complete show")
SEAS = re.compile(r"\bseason\s?(\d{1,2})\b|\bseason\s(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)(?:\sand\sfinal)?\sseason\b|\b(?:s|se)\s?(\d{1,2})\s?(?:e|ep|d|disc)\s?\d{1,3}\b|\bs(\d{1,2})\b|\b(\d{1,2})x\s?\d{2,3}\b")
LEAD = re.compile(r"^(?:\s*(?:\(?\d{1,4}[-./]\d{1,2}(?:[-./]\d{1,4})?\)?|(?:19|20)\d\d|vhs|beta|tape|dvd|tv|the|classic|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|mtv|tnn|tbs|usa|[wk][a-z]{2,3}(?:-tv)?(?:\s?\d{1,2})?)\b[\s\-:,.|]*)*", re.I)
TAIL = re.compile(r"^\s*(?:$|[-:|(\[,#]|\b(?:s\s?\d{1,2}\s?e\s?\d{1,3}|s\s?\d{1,2}\b|d\s?\d{1,2}\b|\d{1,2}x\s?\d{1,3}|\d{1,4}\b|season|seasons|series|episode|episodes|ep\b|eps\b|the complete|complete|full|sitcom|tv|pilot|finale|premiere|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|mtv|tnn|tbs|wgn|usa|vhs|dvd|disc|vol|volume|tape|part|pt|with commercials|w commercials|woc|commercials|on|from|show|special|marathon|block|(?:19[4-9]\d|200[0-4])|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b)", re.I)
STOP = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'to', 'with', 'show', 'by', 'for', 'is', 'it', 'at', 'from', 'md', 'mr', 'tv', 'new'}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
RARE = set('adderly aftermash andersonville andromeda arliss arli$$ avonlea backyardigans ballykissangel berrengers bewitched bodyshaping booknotes boomtown bordertown buzzkill carnivale cavanaughs citykids columbo comicview commish counterstrike crosswits cybercops deadwood eastenders elimidate entourage fastlane felicity foofur futurama geraldo gunsmoke halloweentown hometime hornblower housesmart hughleys inquizition inuyasha kissyfur knightwatch kojak lovejoy mannix mathnet matlock moneyline motorweek mousercise mousercize nightingales nightline overhaulin pictionary pinwheel rockumentary rollergames rollerjam rolonda scattergories seaquest smallville sportscenter sportscentury starrcade summerslam superbook supercarrier tattingers tattletales teknoman tekwar thirtysomething thundercats toonheads torkelsons videopolis wildboyz wintuition witchblade wonderworks wrestlemania youthquake jeopardy donahue montel leeza marilu daria sopranos sportsworld speedweek shortstories homeworks ncis mxc flcl wccw quincy riptide dragnet laramie profiler'.split()) | {'muppet show', 'gong show', 'daily show', 'elephant show', 'bozo show', 'sinbad show', 'roseanne show', 'norm show', 'weber show', 'ellen show', 'moxy show', 'today show', 'early show', 'gossip show', 'house md', 'mr t', 'mr president', 'mr sunshine', 'mr personality', 'tv 101', 'owl tv', 'tots tv', 'real tv', 'new detectives', 'new dragnet', 'new lassie', 'new zorro', 'new wilderness'}
HINTS = {'Tuesday Night Titans': {'drop': ['TNT']}, 'Wonderful World of Disney': {'drop': ['Walt Disney']}}
ADONLY = re.compile(r"\bcommercials?,|\bcommercial (break|block)s?\b|\bcommercials (and|from|during|block|breaks?|only|compilation)\b|\b(open|close|closing|ending|end credits|intro|outro|sign-?off|sign-?on|station id|ident|promo)$")
ABROAD = re.compile(r"\b(atv|ads|tcn|gtv|qtq|nws|hsv|tvq|sas|ntd|stw|tvw|bcv|nbn|gmv|rtq|tnq|ten|nine|seven)-(\d{1,2})\b|\b(bbc ?[1-4]|bbc one|bbc two|itv[1-4]?|channel 4|channel four|sky one|uk gold|ytv|cbc|ctv|global tv|rte|network ten|nine network|seven network)\b")
UKOK = {'pbs', 'a&e', 'bravo', 'bbca', 'bbc america', 'comedy'}
SEPS = re.compile(r"\s[-–|~]\s|[,;/|~:+]|\band\b|&|\bon\b|\bfrom\b")
CONN = re.compile(r"^\s*(in|of|at|for|to|a|an|the|is|are|was|or|'s|s|that|this|my|your|his|her)\b")
def flat(v): return ' '.join(str(a) for a in v) if isinstance(v, list) else str(v or '')
def norm(s):
    s = s.lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[.'!?,:*]", '', s)
    return re.sub(r'[^a-z0-9$/]+', ' ', s).strip()
def norm0(t): return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9]+", ' ', t.lower().replace("'", '').replace('’', ''))).strip()
def clean(t): return re.sub(r'(?<=[a-z0-9]{2})\.(?=[a-z0-9]{2})', ' ', re.sub(r'[_]+', ' ', t.lower().replace('’', "'")))
def bare(t): return re.sub(r'\s*\([^)]*\)', '', t).strip() or t
def sig(n): return [w for w in re.sub(r'^the ', '', n).split() if w not in STOP]
def airdate(t):
    m = re.search(r'\b(19[89]\d|200[0-4])[-./ ](\d{1,2})[-./ ](\d{1,2})\b', t)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./](19[89]\d|200[0-4]|[89]\d)\b', t)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = int(m.group(3)); y = y + 1900 if y < 100 else y
        return '%d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', t.lower())
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(1)], int(m.group(2)))
    return ''
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
def prep(sh):
    h = HINTS.get(sh['title'], {})
    raw = [bare(sh['title'])] + [a for a in sh.get('aka', []) if a not in h.get('drop', [])] + h.get('add', [])
    names = []; seenn = set()
    for a in raw:
        n = norm(bare(a)); n0 = re.sub(r'^the ', '', n)
        if not n0 or n0 in seenn or (re.fullmatch(r'[\d ]+', n0) and names): continue
        seenn.add(n0)
        sw = sig(n0)
        if n0 in NETNAMES or n0 in h.get('net', []): lvl = 3
        elif n0 in RARE: lvl = 1
        elif len(sw) <= 1 or len(n0.replace(' ', '')) <= 4: lvl = 2
        elif len(sw) == 2: lvl = 1
        else: lvl = 0
        ws = n0.split()
        rx = re.compile(r"(?<![a-z0-9])(?:the[\W_]+)?" + r"[\W_]*".join("[.'*]?".join(re.escape(ch) for ch in w) for w in ws) + r"(?![a-z0-9])")
        names.append({'n': n0, 'lvl': lvl, 'rx': rx, 'q': ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', bare(a)).split())})
    sh['names'] = names
    sh['y0'], sh['y1'] = sh['years'][0], sh['years'][1]
    sh['remake'] = bool(re.search(r'\((19|20)\d\d\)|\(series\)|\(fox\)', sh['title'].lower())) or bool(h.get('remake'))
    sh['cls'] = 'scripted' if sh['type'] in SCRIPTED else 'event' if sh['type'] in EVENT else 'strip'
    sh['netrx'] = re.compile(r'\b(' + NETRX[sh['net']] + r')\b') if NETRX.get(sh['net']) and sh['net'] != 'syn' else None
    sh['junk'] = re.compile(h['junk']) if h.get('junk') else None
    q = QMAP.get(sh['type'])
    if not q:
        q = 'prime'
        for pat, v in OTHERQ:
            if re.search(pat, sh['title'].lower()): q = v; break
    sh['q'] = q
    sh['ct'] = 'rerun' if sh['y1'] <= 1983 else sh['type']
for _s in SHOWS: prep(_s)
BYT = {s['title']: s for s in SHOWS}
def get(url, tries=4, raw=False):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            code = getattr(e, 'code', 0)
            if code == 404: return None
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep((8 if code == 429 else 3) * (k + 1))
def scrape(q, cap=20000):
    out, cursor = [], None
    while len(out) < cap:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language,description', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        for it in j.get('items', []):
            it['description'] = ' '.join(flat(it.get('description')).split())[:800]
            out.append(it)
        cursor = j.get('cursor')
        if not cursor: break
    return out
def load_ids():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if p.endswith('needs.json.gz') or p.endswith('movies.json.gz'): continue
        try:
            d = json.load(gzip.open(p, 'rt', encoding='utf-8'))
            if isinstance(d, list):
                for x in d:
                    if isinstance(x, dict) and x.get('i'): have.add(x['i'])
                    elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
        except Exception as e: print('skip', p, e)
    return have
def load_guide(p):
    try: return json.load(gzip.open(p, 'rt', encoding='utf-8'))
    except Exception: return {}
def fetch_guides(G, todo):
    def one(sh):
        best = None
        for nm in [bare(sh['title'])] + sh.get('aka', [])[:2]:
            j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(nm)) or []
            time.sleep(0.6)
            names = {norm0(bare(sh['title']))} | {norm0(a) for a in sh.get('aka', [])}
            for r in j:
                w = r.get('show') or {}
                py = int((w.get('premiered') or '0000')[:4] or 0)
                if norm0(w.get('name', '')) in names and abs(py - sh['y0']) <= 1: best = w; break
            if best: break
        if not best: return sh['title'], {'miss': 1}
        w = get('https://api.tvmaze.com/shows/%d?embed[]=episodes&embed[]=cast' % best['id']) or {}
        time.sleep(0.6)
        emb = w.get('_embedded') or {}
        rows = [[e['season'], e['number'], e.get('name') or '', e['airdate']] for e in emb.get('episodes', []) if e.get('number') and e.get('airdate') and e['airdate'] <= '2004-08-31']
        cast = []
        for c in emb.get('cast', []):
            n = (c.get('person') or {}).get('name')
            if n and n not in cast: cast.append(n)
        return sh['title'], {'id': best['id'], 'eps': rows, 'cast': cast[:8], 'lang': best.get('language') or ''}
    with ThreadPoolExecutor(2) as ex:
        for n, (k, g) in enumerate(ex.map(one, todo)):
            G[k] = g
            if n % 50 == 0: print('guide', n, len(todo), round((time.time() - T0) / 60, 1), 'min', flush=True)
    return G
GUIDE = load_guide(GP) or load_guide(GUIDEF)
GENT = {'pilot', 'the pilot', 'finale', 'the finale', 'the reunion', 'the wedding', 'the trip', 'the movie', 'the letter', 'the show', 'the party', 'christmas', 'thanksgiving', 'halloween'}
EP = {}
def build_ep():
    EP.clear()
    for k, g in GUIDE.items():
        rows = g.get('eps') or []
        t = {}
        for s, n, nm, d in rows:
            z = norm0(nm)
            if len(z) >= 9 and z not in GENT and len(z.split()) >= 2 and not re.fullmatch(r'(episode|show|part|chapter|week|day) ?#?\d+.*', z): t[z] = (s, n)
        EP[k] = {'t': sorted(t.items(), key=lambda kv: -len(kv[0])), 'd': {(s, n): d for s, n, nm, d in rows}, 'maxs': max([r[0] for r in rows] or [0]), 'cast': [c.lower() for c in g.get('cast', []) if len(c.split()) >= 2], 'n': len(rows)}
build_ep()
def ep_title(sh, low):
    g = EP.get(sh['title'])
    if not g or not g['t']: return None
    z = ' ' + norm0(low) + ' '
    for k, v in g['t']:
        if (' ' + k + ' ') in z: return v
    return None
def file_se(sh, text):
    low = clean(text)
    m = SE1.search(low)
    if m: return (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
    return ep_title(sh, low)
def has_cast(sh, blob):
    g = EP.get(sh['title'])
    return bool(g) and any(c in blob for c in g['cast'])
def find(sh, t):
    low = clean(t).replace('&', ' and ')
    lead = LEAD.sub('', low)
    best = None
    for nm in sh['names']:
        hd = -1
        for src in (low, lead):
            m = nm['rx'].match(src.strip())
            if m:
                rest = src.strip()[m.end():]
                ok = not re.match(r'-[a-z]', rest) and TAIL.match(rest.lstrip(" '!?.*"))
                hd = max(hd, 2 if ok else 1)
        if hd == 1 and CONN.match(rest): hd = 0
        if hd < 2 and nm['rx'].search(low):
            for part in SEPS.split(low):
                part = LEAD.sub('', part.strip()); m = nm['rx'].match(part)
                if m and TAIL.match(part[m.end():].lstrip(" '!?.*")) and not re.match(r'-[a-z]', part[m.end():]): hd = max(hd, 0.5)
            hd = max(hd, 0)
        if hd < 0: continue
        key = (-nm['lvl'], hd, len(nm['n']))
        if not best or key > best[0]: best = (key, nm, hd)
    return (best[1], best[2]) if best else (None, -1)
def strip_names(sh, low):
    for nm in sh['names']: low = nm['rx'].sub(' ', low)
    return low
def consider(sh, it, route='t'):
    t = flat(it.get('title')); low = clean(t)
    if not t or NONLAT.search(t) or FOREIGN.search(low): return None
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return None
    nm, hd = find(sh, t)
    ident = it.get('identifier') or ''
    desc = flat(it.get('description')).lower(); subj = flat(it.get('subject')).lower()
    if not nm:
        if route == 't': return None
        blob = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', ident)) + ' ' + subj + ' ' + desc) + ' '
        nm = next((x for x in sh['names'] if x['lvl'] <= 1 and (' ' + x['n'] + ' ') in blob), None)
        if not nm: return None
        hd = -1
    rest = strip_names(sh, low)
    if JUNK.search(rest) or SPIN.search(rest) or MOD2.search(t) or ADONLY.search(low.strip()): return None
    if ABROAD.search(low) and sh['net'] not in UKOK and '(uk)' not in sh['title'].lower(): return None
    if sh['cls'] == 'scripted' and JUNKS.search(rest): return None
    if sh['type'] != 'sports' and sh['q'] != 'wrest' and JUNKN.search(rest) and not TAPE2.search(low): return None
    if sh['junk'] and sh['junk'].search(low): return None
    cols = it.get('collection') or []
    cols = set(cols) if isinstance(cols, list) else {cols}
    if cols & {'podcasts', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'community_media'}: return None
    y0, y1 = sh['y0'], sh['y1']
    ys = [int(y) for y in YR.findall(t)]
    ad = airdate(t)
    if ad: ys.append(int(ad[:4]))
    hi = max(y1 + 1, 2004) if not sh['remake'] else y1 + 1
    inrun = any(y0 <= y <= y1 + 1 for y in ys)
    inera = any(max(y0, 1984) <= y <= min(hi, 2004) for y in ys)
    if ys and not (inrun or inera): return None
    m = re.match(r'(\d{4})', flat(it.get('date')) or flat(it.get('year')) or '')
    iy = int(m.group(1)) if m else 0
    yt = ident.startswith('youtube-') or 'youtube' in subj[:40]
    mod = iy > 2004 or (yt and not iy)
    dated = inrun or inera or (iy and not yt and max(y0, 1984) <= iy <= min(hi, 2004)) or (iy and y0 <= iy <= y1)
    ss = seasons(low)
    g = EP.get(sh['title'])
    if g and g['maxs'] and ss and not MULTI.search(low) and any(n > g['maxs'] + 1 for n in ss): return None
    if sh['cls'] == 'scripted' and not g and ss and any(y0 + n - 1 > y1 + 1 for n in ss) and not MULTI.search(low): return None
    se = bool(ss) or bool(MULTI.search(low)) or bool(SE1.search(low))
    ept = bool(ep_title(sh, rest)) if sh['cls'] == 'scripted' else False
    cast = has_cast(sh, desc + ' ' + subj + ' ' + low)
    netw = bool(sh['netrx'] and sh['netrx'].search(rest + ' ' + subj + ' ' + desc[:300]))
    tape = bool(TAPE.search(rest)); tvcol = bool(cols & TVSET); dev = bool(DESCEV.search(desc + ' ' + subj))
    ctx = tape or tvcol or netw
    lvl = nm['lvl']
    if JUNKD.search(desc) and not (cast or ept): return None
    if sh['remake'] and not (inrun or cast or ept or (iy and y0 <= iy <= y1 + 1)): return None
    if route != 't' and hd < 0:
        if route == 'u': return ('y', 'u') if (se or dated or tape) and not mod else ('m', 'show named outside the title only')
        if not (tape or tvcol or se): return None
        if mod and not (inera or inrun): return None
        return ('d', 'd')
    if sh['cls'] == 'scripted':
        m2 = EPN.search(low)
        if m2 and not ss and int(m2.group(1)) > 32 * (y1 - y0 + 1) + 10: return None
        strong = se or ept or cast
        if mod and not (strong or inrun): return None
        if lvl >= 2:
            if (cast or ept) and hd >= 0.5: return ('y', 't')
            if hd == 2 and se and (ctx or dev or inrun): return ('y', 't')
            if hd == 2 and inrun and (ctx or dev): return ('y', 't')
            if hd == 2 and (se or inrun or netw or (tvcol and dev)): return ('m', 'one-word title; show not confirmed')
            if hd == 0.5 and (inrun or inera) and ctx: return ('m', 'one-word title in a list of programs')
            return None
        if hd == 2:
            if strong or inrun or ctx or dev: return ('y', 't')
            if lvl == 0: return ('y', 't') if not mod else ('m', 'no episode, year or network evidence')
            return ('m', 'no episode, year or network evidence')
        if hd == 1:
            if strong: return ('y', 't')
            if (inrun or inera) and ctx: return ('y', 't')
            if ctx or inrun or dev: return ('y', 't') if lvl == 0 else ('m', 'title continues past the show name')
            return ('m', 'title continues past the show name') if lvl == 0 else None
        if hd == 0.5:
            if strong or ((inrun or inera) and ctx): return ('y', 't')
            if ctx or inrun or inera: return ('m', 'listed with other programs')
            return ('m', 'listed with other programs') if lvl == 0 else None
        if cast or ept: return ('y', 't')
        if lvl == 0:
            if (se or inrun or inera) and ctx: return ('y', 't')
            return ('m', 'show name inside a longer title') if ctx or se or inrun else None
        return None
    if sh['cls'] == 'strip':
        if mod and not (inrun or inera): return None
        if lvl >= 2:
            if cast and hd >= 1: return ('y', 't')
            if hd == 2 and dated and (ctx or dev): return ('y', 't')
            if hd == 2 and (dated or netw or (se and ctx)): return ('m', 'one-word title; show not confirmed')
            if hd == 0.5 and (inrun or inera) and ctx: return ('m', 'one-word title in a list of programs')
            return None
        if hd == 2:
            if dated or ctx or se or cast: return ('y', 't')
            if dev: return ('y', 't') if lvl == 0 else ('m', 'no date or network evidence')
            return ('m', 'no date or network evidence')
        if hd == 1:
            if dated and (ctx or lvl == 0 or dev): return ('y', 't')
            if dated or ctx or cast: return ('y', 't') if lvl == 0 else ('m', 'title continues past the show name')
            return ('m', 'title continues past the show name') if lvl == 0 else None
        if hd == 0.5:
            if inrun or inera: return ('y', 't')
            return ('m', 'listed with other programs') if dated or ctx else None
        if lvl == 0:
            if (inrun or inera) and ctx: return ('y', 't')
            return ('m', 'show name inside a longer title') if dated or ctx else None
        return None
    if mod and not (inrun or inera): return None
    if lvl >= 2:
        if (inrun or inera) and hd >= 0.5 and (netw or (hd == 2 and tape)): return ('y', 't')
        if sh['type'] == 'sports' and (inrun or inera) and re.search(r'\b(vs|versus|at|game|nlcs|alcs|playoffs?|bowl)\b|@', low): return ('y', 't')
        if hd == 2 and (inrun or inera): return ('m', 'short name with a year only')
        return None
    if not dated: return ('m', 'no broadcast year') if hd == 2 and (ctx or dev) else None
    if hd >= 0.5 or ctx: return ('y', 't')
    return ('m', 'name inside a longer title')
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
REJ = collections.Counter()
def rej(c, why):
    REJ[why] += 1; REJ[(c['k'], why)] += 1
    return None
def maybe(x, why):
    if x.get('why') and why in x['why']: return
    x['keep'] = 'maybe'; x['why'] = (x['why'] + '; ' if x.get('why') else '') + why
def fname(sh, path):
    z = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', path))) + ' '
    return any((' ' + nm['n'] + ' ') in z for nm in sh['names'])
def stamp(sh, x):
    t = x['t']; low = clean(t); y0, y1 = sh['y0'], sh['y1']
    ad = airdate(t) or airdate((x.get('ds') or '')[:200])
    if ad and not (y0 <= int(ad[:4]) <= max(y1 + 1, 2004)): ad = ''
    sn = one_season(low)
    ys = [int(y) for y in YR.findall(t) if y0 <= int(y) <= max(y1 + 1, 2004)]
    dy = re.match(r'(\d{4})', x.get('d') or '')
    dy = int(dy.group(1)) if dy and y0 <= int(dy.group(1)) <= min(max(y1 + 1, 2004), 2004) else 0
    sey = min([int(r[2][:4]) for r in x.get('se', []) if r[2]] or [0])
    if ad: e = int(ad[:4])
    elif sey: e = sey
    elif sn and sh['cls'] == 'scripted' and y0 + sn - 1 <= y1 + 1: e = min(y0 + sn - 1, y1)
    elif ys: e = ys[0]
    elif dy: e = dy
    else: e = y0 if sh['cls'] == 'scripted' or y0 >= 1984 else max(y0, 1984)
    if ad: x['d'] = ad
    x['ad'] = ad; x['e'] = min(e, 2004); x['y'] = str(x['e'])
    if sn: x['sn'] = sn
def meta(c):
    if BUDGET and time.time() - T0 > BUDGET: return rej(c, 'budget')
    j = get('https://archive.org/metadata/' + urllib.parse.quote(c['identifier']))
    if not j or not j.get('files'): return rej(c, 'nometa')
    if j.get('is_dark'): return rej(c, 'dark')
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return rej(c, 'restricted')
    if str(m.get('mediatype', 'movies')) != 'movies': return rej(c, 'mediatype')
    lang = flat(m.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return rej(c, 'lang')
    sh = BYT[c['k']]
    groups = {}; other = 0
    lenby = {f.get('name'): secs(f.get('length')) for f in j['files'] if secs(f.get('length') or 0) > 0}
    for f in j['files']:
        if f.get('original') and secs(f.get('length') or 0) > 0: lenby.setdefault(f['original'], secs(f['length']))
    for f in j['files']:
        n = f.get('name', '').lower()
        if n.endswith('.mp4'):
            key = f.get('original') if f.get('source') == 'derivative' else f['name']
            groups.setdefault(key, []).append(f)
        elif re.search(r'\.(mkv|avi|mpg|mpeg|m4v|mov|ts|vob|iso|ogv|webm|wmv)$', n): other += 1
    files = []; hb = 0
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 5)); b = g[0]
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0)) or lenby.get(key, 0)
        sz = float(b.get('size') or 0)
        if d < 240: continue
        if FOREIGN.search(clean(b['name'])): continue
        if sz and sz / 1e6 / (d / 60) > 60: hb += 1; continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files: return rej(c, 'no mp4 (other video only)' if other else 'no playable files' if not hb else 'bitrate too high')
    if max(f[1] for f in files) < 600: return rej(c, 'under 10 minutes')
    files.sort(key=lambda f: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', f[0])])
    title = flat(m.get('title'))[:200]
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', flat(m.get('description'))).split())
    subj = ';'.join(m['subject']) if isinstance(m.get('subject'), list) else flat(m.get('subject'))
    col = m.get('collection', []); col = [col] if isinstance(col, str) else col
    it = {'identifier': c['identifier'], 'title': title, 'description': desc[:1500], 'subject': subj, 'collection': col, 'date': m.get('date'), 'year': m.get('year'), 'language': m.get('language')}
    v = consider(sh, it, c.get('r', 't'))
    if not v: return rej(c, 'rejected on full details')
    blob = (desc[:1500] + ' ' + subj).lower()
    x = {'i': c['identifier'], 'q': sh['q'], 't': title, 'd': flat(m.get('date')), 'y': '', 'c': col[:4], 's': subj[:200], 'ds': desc[:400], 'f': files[:500], 'dl': c.get('downloads') or 0, 'k': sh['title'], 'e': 0, 'net': sh['net'] if sh['net'] != 'syn' else '', 'ct': sh['ct'], 'pri': sh['pri'], 'ad': '', 'r': c.get('r', 't'), 'nf': len(files)}
    named = sum(1 for f in files if fname(sh, f[0]))
    g = EP.get(sh['title']); se = []; nse = 0
    one = len(files) <= 2
    for n, f in enumerate(x['f']):
        b = f[0].rsplit('/', 1)[-1]
        w = file_se(sh, b) or (file_se(sh, strip_names(sh, clean(title))) if one else None)
        if not w: continue
        nse += 1
        if g and g['d']:
            if w in g['d']: se.append([n, 'S%02dE%02d' % w, g['d'][w]])
        else: se.append([n, 'S%02dE%02d' % w, ''])
    if se: x['se'] = se
    ds = sorted(f[1] for f in files); med = ds[len(ds) // 2]
    if v[0] == 'd':
        ok = named * 2 >= len(files) or (len(se) >= 2 and len(se) * 2 >= len(files) and g and g['t'] and g['d']) or (has_cast(sh, blob) and sh['cls'] == 'scripted')
        if ok and sh['cls'] == 'scripted' and med < EPLEN[sh['type']] * 0.7: ok = False
        if ok: x['t'] = (sh['title'] + ' - ' + title)[:200] if find(sh, title)[1] < 0 else title
        elif TAPE2.search(clean(title)) and len(files) <= 6: maybe(x, 'show named in the description of a tape; not confirmed')
        else: return rej(c, 'description match not confirmed by files')
    elif v[0] == 'm':
        if named * 2 >= len(files) and (nse * 2 >= len(files) or has_cast(sh, blob)) and len(files) >= 2: pass
        elif len(se) >= 3 and len(se) * 2 >= len(files) and g and g['d'] and g['t']: pass
        else: maybe(x, v[1])
    if sh['cls'] == 'scripted' and med < EPLEN[sh['type']] * 0.75: maybe(x, 'files shorter than a normal episode')
    if g and g['d'] and nse >= 3 and not se and sh['cls'] == 'scripted': maybe(x, 'episode numbers do not match the episode guide')
    if JUNKD.search(blob) and not se: maybe(x, 'description suggests it is not a broadcast')
    stamp(sh, x)
    return x
def recheck(x):
    sh = BYT.get(x.get('k'))
    if not sh: return 'show no longer listed'
    t = x['t']
    if t.startswith(sh['title'] + ' - ') and x.get('r') in ('d', 'u'): return ''
    it = {'identifier': x['i'], 'title': t, 'description': x.get('ds'), 'subject': x.get('s'), 'collection': x.get('c'), 'date': '' if x.get('ad') else x.get('d')}
    v = consider(sh, it, x.get('r', 't'))
    if not v: return 'no longer passes the title rules'
    return ''
def plan():
    global GUIDE
    old = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    have = load_ids(); mine = {x['i'] for x in old}
    order = sorted(SHOWS, key=lambda s: (s['pri'], -len(s['title'])))
    if FOCUS:
        prev = {}
        try: prev = {r['title']: r for r in json.load(open(REPF, encoding='utf-8')).get('shows', [])}
        except Exception: pass
        def want(s):
            if s['title'].lower() in FOCUS or ('pri%d' % s['pri']) in FOCUS: return True
            st = (prev.get(s['title']) or {}).get('status', 'MISSING')
            return ('missing' in FOCUS and st == 'MISSING') or ('thin' in FOCUS and st in ('MISSING', 'THIN'))
        order = [s for s in order if want(s)]
    todo = [s for s in order if s['title'] not in GUIDE and (s['cls'] == 'scripted' or s['type'] in ('game', 'talk', 'late', 'soap', 'mag', 'doc', 'cook', 'music', 'other', 'news'))]
    print('have', len(have), 'mine', len(mine), 'shows', len(order), 'guides to fetch', len(todo), flush=True)
    fetch_guides(GUIDE, todo)
    with gzip.open(GP, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
    build_ep()
    print('guides', sum(1 for g in GUIDE.values() if g.get('eps')), 'with episodes', sum(1 for g in GUIDE.values() if g.get('miss')), 'not found', flush=True)
    DIAG = collections.defaultdict(list); DREJ = collections.defaultdict(list)
    def one(sh):
        res = {}
        yrs = ' OR '.join(str(y) for y in range(max(sh['y0'], 1980), min(max(sh['y1'] + 1, 2004), 2004) + 1))
        for nm in sh['names']:
            ph = nm['q'].replace('"', '')
            base = 'mediatype:movies AND title:("%s")' % ph
            qs = []
            if nm['lvl'] >= 2: qs.append((base + ' AND (' + DISQ + ' OR collection:(' + TVCOL + ') OR title:(' + yrs + '))', 't'))
            else:
                qs.append((base, 't'))
                qs.append(('mediatype:movies AND subject:("%s")' % ph, 't'))
                ws = nm['n'].replace('/', ' ').split()
                if len(''.join(ws)) >= 8:
                    qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(sorted({sep.join(ws) + '*' for sep in ('-', '_', '.', '')})) + ') AND NOT title:("%s")' % ph, 'i'))
                qs.append(('mediatype:movies AND "%s" AND NOT title:("%s") AND (collection:(%s) OR title:(vhs OR tape OR commercials OR recorded OR episodes OR season OR complete OR series))' % (ph, ph, TVCOL), 'd'))
            for qq, route in qs:
                hits = scrape(qq); st = [len(hits), 0, 0, 0, 0]
                for it in hits:
                    i = it.get('identifier')
                    if not i or i in res: continue
                    if i in mine: st[1] += 1; continue
                    if i in have: st[2] += 1; continue
                    try: v = consider(sh, it, 'd' if route == 'i' else route)
                    except Exception as e: print('skip', i, repr(e)); v = None
                    if v:
                        res[i] = (it, v, nm); st[3 if v[0] == 'y' else 4] += 1
                    elif len(DREJ[sh['title']]) < 400: DREJ[sh['title']].append((it.get('downloads') or 0, route, i, flat(it.get('title'))[:90]))
                DIAG[sh['title']].append((route, st, qq[:120]))
        return sh, res
    seen = {}; per = collections.Counter()
    def rank(v, nm): return (0 if v[0] == 'y' else 1 if v[0] == 'm' else 2, nm['lvl'], -len(nm['n']))
    def add(sh, i, it, v, nm, up=0):
        r = rank(v, nm)
        if i in seen and seen[i]['rk'] <= r: return
        seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': sh['title'], 'pri': sh['pri'], 'r': 'u' if up else v[1] if v[0] != 'm' else 't', 'rk': r}
    with ThreadPoolExecutor(6) as ex:
        for n, (sh, res) in enumerate(ex.map(one, order)):
            for i, (it, v, nm) in res.items(): add(sh, i, it, v, nm)
            if n % 50 == 0: print('search', n, len(order), len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    src = sorted([x for x in old if x.get('nf', 1) >= 4 and x.get('keep') != 'maybe' and x.get('r') != 'u'], key=lambda x: (x.get('pri', 3), -x.get('nf', 1)))[:1200]
    ups = collections.Counter()
    def upl(x):
        j = get('https://archive.org/metadata/' + urllib.parse.quote(x['i']) + '/metadata') or {}
        return flat((j.get('result') or {}).get('uploader'))
    with ThreadPoolExecutor(8) as ex:
        for u in ex.map(upl, src):
            if u and '@' in u: ups[u] += 1
    nup = 0
    for n, (u, cnt) in enumerate(ups.most_common(300)):
        hits = scrape('mediatype:movies AND uploader:("%s")' % u, 8000); acc = 0
        if len(hits) >= 8000: continue
        for it in hits:
            i = it.get('identifier')
            if not i or i in seen or i in mine or i in have: continue
            t = flat(it.get('title'))
            for sh in order:
                nm, hd = find(sh, t)
                if not nm or hd < 0.5 or nm['lvl'] >= 2: continue
                try: v = consider(sh, it, 't')
                except Exception: v = None
                if v:
                    add(sh, i, it, v, nm, up=1 if v[0] == 'y' else 0); acc += 1; nup += 1; break
        print('UPLOADER', n, 'packs', cnt, 'items', len(hits), 'candidates', acc, flush=True)
    print('uploader candidates', nup, 'from', len(ups), 'uploaders', flush=True)
    for c in seen.values(): per[c['k']] += 1; c.pop('rk')
    cands = sorted(seen.values(), key=lambda x: (x['pri'], x['r'] != 't', -x['downloads']))
    print('candidates', len(cands), 'by route', sorted(collections.Counter(c['r'] for c in cands).items()), 'by pri', sorted(collections.Counter(c['pri'] for c in cands).items()), flush=True)
    for sh in order:
        k = sh['title']
        print('PLAN pri%d %-9s cand %5d | %s' % (sh['pri'], sh['type'], per[k], k))
        for route, st, qq in DIAG[k]: print('  Q %s hits %d mine %d elsewhere %d yes %d maybe %d | %s' % ((route,) + tuple(st) + (qq,)))
        for dl, route, i, t in sorted(set(DREJ[k]), reverse=True)[:6 if sh['pri'] > 1 else 12]: print('  REJ %s %6d | %s | %s' % (route, dl, i[:40], t))
    with gzip.open(CP, 'wt', encoding='utf-8') as f: json.dump(cands, f, separators=(',', ':'))
def run_meta():
    cands = json.load(gzip.open(CP, 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    def safe(c):
        try: return meta(c)
        except Exception as e:
            print('error', c['identifier'], repr(e), flush=True); return rej(c, 'error')
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(safe, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'needs-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res), 'of', len(cands))
    print('REJECT', sorted(((k, v) for k, v in REJ.items() if isinstance(k, str)), key=lambda kv: -kv[1]))
    per = collections.defaultdict(list)
    for k, v in REJ.items():
        if isinstance(k, tuple): per[k[0]].append('%s %d' % (k[1], v))
    for k in sorted(per): print('REJSHOW', k, '|', '; '.join(sorted(per[k])))
def hours(L): return round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
def merge():
    old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    other = load_ids(); old = []
    for x in old0:
        why = 'held in another catalog file' if x['i'] in other else recheck(x)
        if why: print('DROP', x['k'], '|', x['i'], '|', x['t'][:80], '|', why)
        else: old.append(x)
    have = {x['i'] for x in old}; add = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'needs-[0-9]*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have and x['i'] not in other: have.add(x['i']); add.append(x)
    res = old + add
    for x in res:
        sh = BYT[x['k']]; x['q'] = sh['q']; x['pri'] = sh['pri']; x['ct'] = sh['ct']
    with gzip.open(OUTF, 'wt', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    if GUIDE:
        with gzip.open(GUIDEF, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
    print('merged old', len(old0), 'kept', len(old), 'added', len(add), 'total', len(res), 'hours', hours(res), 'maybe', sum(1 for x in res if x.get('keep')))
    by = collections.defaultdict(list)
    for x in res: by[x['k']].append(x)
    rows = []
    for sh in sorted(SHOWS, key=lambda s: (s['pri'], s['title'])):
        L = by.get(sh['title'], []); sure = [x for x in L if not x.get('keep')]
        g = EP.get(sh['title']) or {}
        eps = set()
        loose = 0
        for x in sure:
            got = {r[1] for r in x.get('se', [])}
            eps |= got
            if not got: loose += sum(1 for f in x['f'] if f[1] >= EPLEN.get(sh['type'], 900) * 0.75)
        n = len(eps) + loose
        ge = g.get('n', 0)
        if not L: st = 'MISSING'
        elif not sure: st = 'MAYBE'
        elif sh['cls'] == 'scripted': st = 'FOUND' if n >= max(4, min(20, 0.15 * ge)) else 'THIN'
        else: st = 'FOUND' if n >= 5 else 'THIN'
        rows.append({'title': sh['title'], 'pri': sh['pri'], 'type': sh['type'], 'net': sh['net'], 'years': sh['years'], 'guide_episodes': ge, 'items': len(L), 'maybe': len(L) - len(sure), 'files': sum(len(x['f']) for x in L), 'hours': hours(L), 'episodes': len(eps), 'other_files': loose, 'status': st})
    tot = {}
    for p in (1, 2, 3):
        R = [r for r in rows if r['pri'] == p]
        tot[str(p)] = {'shows': len(R), **{s.lower(): sum(1 for r in R if r['status'] == s) for s in ('FOUND', 'THIN', 'MAYBE', 'MISSING')}, 'items': sum(r['items'] for r in R), 'hours': sum(r['hours'] for r in R)}
    json.dump({'updated': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'items': len(res), 'hours': hours(res), 'priority': tot, 'shows': rows}, open(REPF, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('PRIORITY TABLE')
    for p in ('1', '2', '3'): print('  pri', p, tot[p])
    print('SHOW TABLE')
    for r in rows: print('  %-7s pri%d %-9s items %4d maybe %4d files %5d hours %5d eps %4d/%-4d other %4d | %s' % (r['status'], r['pri'], r['type'], r['items'], r['maybe'], r['files'], r['hours'], r['episodes'], r['guide_episodes'], r['other_files'], r['title']))
    print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
    print('categories', sorted(collections.Counter(x['q'] for x in res).items()))
    print('maybe reasons', collections.Counter(x.get('why') for x in res if x.get('keep')).most_common(12))
    random.seed(len(res))
    for label, L in (('NEW', add), ('ALL', res), ('MAYBE', [x for x in res if x.get('keep')])):
        for x in random.sample(L, min(60, len(L))): print('SAMPLE', label, x['q'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:40], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', len(x.get('se') or []), 'eps', '|', x['e'], '|', x.get('why', ''))
if MODE == 'plan': plan()
elif MODE == 'meta': run_meta()
else: merge()
