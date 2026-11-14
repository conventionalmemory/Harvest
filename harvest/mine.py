import json, gzip, os, re, sys, time, random, glob, collections, hashlib, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (archive harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
SEEDS = int(os.environ.get('SEEDS', '14000'))
TOPUP = int(os.environ.get('TOPUP', '300'))
MAXC = int(os.environ.get('MAXC', '260000'))
T0 = time.time()
OUTF = os.path.join(OUT, 'mine.json.gz')
DROPF = os.path.join(here, 'mine_drop.txt')
DROP = set(l.strip() for l in open(DROPF, encoding='utf-8') if l.strip()) if os.path.exists(DROPF) else set()
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=60000):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) >= cap: break
    return out
def hid(u):
    return hashlib.sha1(u.encode('utf-8')).hexdigest()[:10] if u else ''
def sv(v):
    return ' '.join(str(x) for x in v) if isinstance(v, list) else str(v or '')
SHOWS = {}
QMAP = {'rerun': 'rerun', 'kids': 'kids', 'news': 'news', 'late': 'late', 'game': 'game', 'talk': 'talk', 'soap': 'soap', 'music': 'music', 'pub': 'pub', 'movie': 'movie', 'morning': 'morning', 'mag': 'mag', 'cook': 'cook', 'block': 'block', 'prime': 'prime', 'tech': 'tech'}
for p in sorted(glob.glob(os.path.join(here, 'shows_*.json'))):
    try: L = json.load(open(p, encoding='utf-8'))
    except Exception: continue
    if isinstance(L, dict): L = list(L.values())
    mus = 'musictv' in p
    for s in L:
        if not isinstance(s, dict) or not s.get('title'): continue
        yrs = [int(v) for v in re.findall(r'(?<!\d)(19\d\d|20\d\d)(?!\d)', json.dumps([s.get('years'), s.get('original_run'), s.get('run'), s.get('first'), s.get('last'), s.get('or')]))]
        if not yrs: yrs = [int(v) for v in re.findall(r'(?<!\d)(19\d\d|20\d\d)(?!\d)', json.dumps([s.get('first_year'), s.get('last_year')]))]
        q0 = s.get('q'); alts = list(s.get('alt') or []) + (list(q0) if isinstance(q0, list) else [])
        q = QMAP.get(q0 if isinstance(q0, str) else '', '') or QMAP.get(str(s.get('channel_type') or ''), '') or ('music' if mus else 'prime')
        if yrs and max(yrs) < 1984 and q == 'prime': q = 'rerun'
        amb = bool(s.get('ambiguous') or s.get('amb'))
        for nm in [s['title']] + alts:
            n = norm(nm)
            if len(n) < 4: continue
            a2 = amb or len(n) < 7 or (len(n.split()) == 1 and len(n) < 9)
            SHOWS.setdefault(n, {'title': s['title'], 'q': q, 'net': s.get('net') if isinstance(s.get('net'), str) else '', 'y0': min(yrs) if yrs else 0, 'y1': max(yrs) if yrs else 0, 'amb': a2})
SK = sorted(SHOWS, key=lambda n: -len(n))
SRX = re.compile(r'^(?:the |a |vhs |tv |tape |\d{1,4} |[wk][a-z]{2,3} (?:tv )?(?:\d+ )?|nbc |cbs |abc |fox |pbs |wb |upn |nick |nickelodeon |mtv |hbo )*(' + '|'.join(re.escape(n) for n in SK) + r')(?: (.*))?$') if SK else None
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblada|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|auf deutsch|fran[cç]ais|french dub|en fran|vostfr|italiano|nederlands|dutch|svenska|swedish|norsk|dansk|suomi|polski|polish|magyar|rom[aâ]n[aă]|t[uü]rk[cç]e|turkish|hindi|tamil|telugu|urdu|arabic|bahasa|tagalog|filipino|korean|japanese tv|chinese|mandarin|cantonese|russian|sub ?esp|subtitulado|temporada|cap[ií]tulo|episodio|folge|staffel|saison|aflevering|televisa|telemundo|univision|tv azteca|globo|rtl|zdf|tf1|nhk|tvb)\b"
X_NONUS = r"\b(uk tv|british tv|bbc ?[1234]?|itv|uk channel 4|channel four|sky ?(one|news|sports)|granada|thames|lwt|tyne tees|anglia|ulster|rt[eé] (one|two|news)|australian?|aussie|channel (nine|seven|ten)|abc australia|new zealand|tvnz|canadian?|cbc|ctv|global tv|citytv|ytv|muchmusic|tvontario|ireland|irish|scotland|scottish|wales|welsh)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|let'?s play|playstation|ps[1-5]|xbox|nintendo switch|rom ?hack|emulator|podcast|vlog|vlogs|livestream|live stream|twitch|tiktok|reaction|reacts?|review|unboxing|tutorial|lecture|lectures|seminar|webinar|conference talk|keynote|sermon|sermons|worship service|church service|bible study|city council|county commission|board meeting|school board|planning commission|town hall meeting|public hearing|zoning|selectmen|audiobook|audio book|radio show|old time radio|soundtrack|full album|mixtape|dj set|karaoke|home movies?|wedding|birthday party|graduation|recital|fan ?film|fan ?made|fan ?edit|amv|ytp|parody|remix|compilation of clips|screen recording|test upload|sample|predictions?|conspiracy|theory|theories|explained|documentary about|tribute|interview with|behind the scenes|bloopers|outtakes|commentary|trailer|trailers|teaser|music video|lyrics|cover song|friends of the)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(netflix|hulu|disney\+|paramount\+|hbo max|prime video|youtube original|blu-?ray|bluray|1080p|2160p|4k|remux|web-?dl|webrip|hdtv|x265|hevc)\b"
TVW = r"\b(aired|airing|air ?date|broadcast|telecast|recorded (off|from)|off[- ]air|off the air|taped (off|from)|with (original )?commercials|w/ ?commercials|commercials included|commercial breaks?|woc|tv recording|vhs ?rip|vhs recording|vhs tape|betamax|home recording|aircheck|air check|sign[- ]?off|sign[- ]?on|station id|bumpers?|promos?|[wk][a-z]{2,3}-tv|channel \d{1,2}|nbc|cbs|abc|fox|pbs|upn|the wb|kids'? wb|fox kids|hbo|showtime|cinemax|tbs|tnt|wgn|usa network|nickelodeon|nick at nite|snick|mtv|vh1|cnn|espn|tnn|cmt|bet|a&e|lifetime|discovery channel|tlc|sci-?fi channel|comedy central|cartoon network|toonami|disney channel|family channel|weather channel|qvc|hsn|c-span|court tv|e!|amc|tcm|local news|newscast|primetime|prime time|saturday morning|late night|daytime|syndicat\w*|episode|season|nfl|nba|mlb|nhl|ncaa|super bowl|world series|stanley cup|monday night football|playoffs?|wwf|wcw)\b"
STRONG = r"\b(aired|air ?date|telecast|recorded (off|from)|off[- ]air|taped (off|from)|with (original )?commercials|w/ ?commercials|commercials included|commercial breaks?|woc|tv recording|vhs recording|home recording|aircheck|air check|[wk][a-z]{2,3}-tv|original broadcast|as broadcast|broadcast on)\b"
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def fy(y):
    y = int(y)
    return y if y > 100 else (1900 + y if y >= 84 else 2000 + y if y <= 4 else 0)
def okd(y, m, d):
    return 1984 <= y <= 2004 and 1 <= m <= 12 and 1 <= d <= 31
def find_date(s):
    s = s.lower()
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])[-./ _](\d{1,2})[-./ _](\d{1,2})(?!\d)', s)
    if m and okd(int(m.group(1)), int(m.group(2)), int(m.group(3))): return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(?<!\d)(\d{1,2})[-./](\d{1,2})[-./]((?:19)?[89]\d|(?:20)?0[0-4])(?!\d)', s)
    if m:
        y = fy(m.group(3))
        if y and okd(y, int(m.group(1)), int(m.group(2))): return '%04d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', s)
    if m and okd(int(m.group(3)), MON[m.group(1)], int(m.group(2))): return '%04d-%02d-%02d' % (int(m.group(3)), MON[m.group(1)], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[89]\d|200[0-4])\b', s)
    if m and okd(int(m.group(3)), MON[m.group(2)], int(m.group(1))): return '%04d-%02d-%02d' % (int(m.group(3)), MON[m.group(2)], int(m.group(1)))
    return ''
def find_year(s):
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', s)
    if m and int(m.group(1)) >= 1984: return int(m.group(1))
    m = re.search(r"(?<![\d'])'(8[4-9]|9\d|0[0-4])(?!\d)", s)
    if m: return fy(m.group(1))
    return 0
def bad_title(t):
    low = t.lower() + ' '
    low2 = re.sub(r'(with|w/|w|incl\.?|including|original) ?(original |the )?(commercials?|ads)|commercials included', ' ', low)
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return True
    return bool(re.search(X_FOR, low2) or re.search(X_JUNK, low2) or re.search(X_MOD, low2) or re.search(X_NONUS, low2))
def show_of(t):
    if not SRX: return None
    m = SRX.match(norm(t))
    if not m: return None
    sh = SHOWS[m.group(1)]; rest = m.group(2) or ''
    if sh['amb'] and not re.match(r'(s\d|season|seasons|series|episode|episodes|ep\b|e\d|complete|pilot|vol|volume|disc|tape|vhs|with commercials|woc|nbc|cbs|abc|fox|\d{1,4}\b)', rest) and not re.search(r'\b(with commercials|woc|season \d|episode \d|s\d{1,2} ?e\d)\b', rest): return None
    return sh
CATS = [('late', r"\b(tonight show|letterman|late night with|late show|conan o'?brien|jay leno|johnny carson|arsenio|saturday night live|snl|politically incorrect|daily show|later with|tom snyder)\b"),
        ('soap', r"\b(soap opera|days of our lives|general hospital|all my children|young and the restless|guiding light|as the world turns|one life to live|another world|santa barbara|bold and the beautiful|ryan'?s hope|loving|passions|sunset beach|port charles)\b"),
        ('game', r"\b(game show|jeopardy|wheel of fortune|price is right|family feud|press your luck|card sharks|\$?\d[\d,]* pyramid|pyramid|match game|hollywood squares|let'?s make a deal|password|scrabble|sale of the century|concentration|tic[- ]tac[- ]dough|joker'?s wild|love connection|newlywed game|dating game|supermarket sweep|win,? lose or draw|double dare|legends of the hidden temple|millionaire|weakest link)\b"),
        ('talk', r"\b(talk show|oprah|donahue|geraldo|sally jessy|regis|kathie lee|maury|jerry springer|ricki lake|rosie o'?donnell|montel|jenny jones|joan rivers|the view|dr\.? phil|people'?s court|judge judy|divorce court)\b"),
        ('news', r"\b(news|newscast|newscenter|eyewitness|nightly|nightline|60 minutes|20/20|dateline|48 hours|primetime live|special report|election night|press conference|state of the union|cnn|headline news|c-span|meet the press|face the nation|this week with|today show|good morning america|cbs this morning|weather channel)\b"),
        ('kids', r"\b(cartoons?|saturday morning|nickelodeon|nick jr|snick|disney channel|disney afternoon|fox kids|kids'? wb|toonami|cartoon network|pbs kids|sesame street|mister rogers|barney|animated series|animaniacs|tiny toon|looney tunes|power rangers|ninja turtles|transformers|g\.?i\.? joe|he-man|thundercats|pokemon|rugrats|doug|ren (and|&) stimpy)\b"),
        ('music', r"\b(mtv|vh1|music videos?|headbangers ball|yo! mtv|120 minutes|cmt|tnn|video countdown|top 20 countdown|unplugged|soul train|american bandstand|solid gold|night tracks|friday night videos|grammy|video music awards|concert)\b"),
        ('pub', r"\b(pbs|nova|frontline|masterpiece|american experience|nature|documentary|macneil|newshour|austin city limits|this old house|julia child|frugal gourmet|joy of painting|computer chronicles|wall street week|washington week|firing line|bill moyers)\b"),
        ('movie', r"\b(movie of the week|sunday night movie|monday night movie|tv movie|made[- ]for[- ]tv|miniseries|mini-series|hbo|showtime|cinemax|the movie channel|feature film|late movie|creature feature|svengoolie|elvira|monstervision|up all night)\b"),
        ('sports', r"\b(nfl|nba|mlb|nhl|ncaa|super bowl|world series|stanley cup|playoffs?|monday night football|final four|bowl game|rose bowl|orange bowl|olympics?|boxing|heavyweight|indy 500|daytona 500|nascar|winston cup|wimbledon|u\.?s\.? open|masters|kentucky derby|wrestlemania|wwf|wcw|vs\.?)\b"),
        ('prime', r"\b(sitcom|primetime|prime time|season \d|s\d{1,2}\s?e\d{1,3}|episode|pilot|series finale|series premiere)\b")]
def classify(title, desc, sh, ad):
    low = title.lower()
    if sh: return sh['q']
    for q, rx in CATS:
        if re.search(rx, low):
            if q == 'sports' and not ad: return 'block'
            return q
    return 'block'
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'tvnews', 'tv', 'tvarchive', 'prelinger', 'us_government', 'gov', 'democracy_now', 'stream_only', 'deemphasize', 'no-preview', 'samples_only'}
GENERIC = {'opensource_movies', 'opensource', 'community', 'opensource_media', 'television', 'moviesandfilms', 'feature_films', 'movies', 'additional_collections', 'additional_collections_video', 'animationandcartoons', 'cultural_academic_films', 'ephemera', 'classic_tv', 'classic_cartoons', 'vintage_cartoons', 'sports', 'youtube', 'social-media-video', 'mirrortube', 'archiveteam', 'internetarchive', 'vlogs', 'educationalfilms', 'artsandmusicvideos', 'home_movies', 'newsandpublicaffairs'}
def load_have():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) == 'mine.json.gz': continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(L, dict): have |= set(L); continue
        for x in L:
            if isinstance(x, dict):
                if x.get('i'): have.add(x['i'])
                ia = x.get('ia')
                if isinstance(ia, list) and ia and isinstance(ia[0], str): have.add(ia[0])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    return have
def seed_items():
    S = {}
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        b = os.path.basename(p)
        if b in ('dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'ads.json.gz', 'openarch.json.gz', 'movies.json.gz', 'mine.json.gz', 'nick_guide.json.gz'): continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(L, list): continue
        for x in L:
            if not isinstance(x, dict) or not x.get('i') or not x.get('t'): continue
            t = x['t']; low = t.lower()
            if bad_title(t): continue
            T = sum(f[1] for f in (x.get('f') or []) if isinstance(f, list) and len(f) > 1 and isinstance(f[1], (int, float)))
            sc = 0
            if re.search(STRONG, low) or re.search(STRONG, str(x.get('ds') or '').lower()[:300]): sc += 3
            if find_date(low): sc += 2
            if T >= 2 * 3600 and len(x.get('f') or []) <= 3: sc += 2
            if re.search(r'\b(vhs|betamax|tape)\b', low): sc += 1
            if x.get('ad'): sc += 2
            if sc >= 2: S[x['i']] = sc
    return S
if MODE == 'plan':
    have = load_have()
    S = seed_items()
    print('known', len(have), 'good seeds', len(S), 'shows', len(SHOWS), flush=True)
    random.seed(11)
    ids = sorted(S, key=lambda i: (-S[i], random.random()))[:SEEDS]
    def upof(i):
        if time.time() - T0 > 55 * 60: return None
        j = get('https://archive.org/metadata/' + urllib.parse.quote(i) + '/metadata', tries=2)
        m = (j or {}).get('result') or {}
        col = m.get('collection') or []
        if isinstance(col, str): col = [col]
        return i, str(m.get('uploader') or ''), col
    ups = collections.Counter(); cols = collections.Counter(); upx = collections.defaultdict(list)
    with ThreadPoolExecutor(24) as ex:
        for n, r in enumerate(ex.map(upof, ids)):
            if not r: continue
            i, u, col = r
            if u: ups[u] += S[i]; upx[u].append(i)
            for c in col:
                if c not in GENERIC and c not in XCOL and not c.startswith('fav-'): cols[c] += S[i]
            if n % 2000 == 0: print('seed meta', n, len(ups), len(cols), round((time.time() - T0) / 60, 1), 'min', flush=True)
    if os.path.exists(OUTF):
        prev = json.load(gzip.open(OUTF, 'rt', encoding='utf-8'))
        pu = collections.Counter(x.get('up') for x in prev if x.get('up'))
        known = set(hid(u) for u in ups); one = {}
        for x in prev:
            if x.get('up') and pu[x['up']] >= 5 and x['up'] not in known: one.setdefault(x['up'], x['i'])
        with ThreadPoolExecutor(24) as ex:
            for r in ex.map(upof, list(one.values())[:3000]):
                if r and r[1]: ups[r[1]] += pu[hid(r[1])]
        print('uploaders carried from previous output', len(one), flush=True)
    for u in list(ups):
        if hid(u) in DROP: del ups[u]
    top = [u for u, n in ups.most_common(TOPUP) if n >= 6]
    print('UPLOADER LEADERBOARD (score, seed items)')
    for u, n in ups.most_common(120): print('  %5d %4d  %s' % (n, len(upx[u]), hid(u)))
    print('COLLECTION LEADERBOARD')
    for c, n in cols.most_common(120): print('  %5d  %s' % (n, c))
    found = set()
    for q in ('title:(vhs OR betamax OR "video tape" OR videotape OR "tape collection" OR "tape archive")', 'title:(aircheck OR airchecks OR "off air" OR "tv recordings" OR "television recordings" OR "home recordings" OR "with commercials" OR "commercial breaks")', 'title:("local news" OR newscasts OR "tv archive" OR "television archive" OR "broadcast archive")', 'identifier:(*vhs* OR *aircheck* OR *tvrecord* OR *offair* OR *tapes*)'):
        for it in scrape('mediatype:collection AND ' + q, cap=5000):
            found.add(it['identifier'])
    found = set(c for c in found if c not in GENERIC and c not in XCOL and not c.startswith('fav-') and c not in DROP)
    selc = sorted(set([c for c, n in cols.most_common(400) if n >= 10 and c not in DROP]) | found)
    print('uploaders selected', len(top), 'collections selected', len(selc), 'of which by search', len(found), flush=True)
    def listing(job):
        kind, v = job
        q = 'mediatype:movies AND ' + ('uploader:"%s"' % v if kind == 'u' else 'collection:(%s)' % v)
        return kind, v, scrape(q, cap=40000)
    seen = {}; per = collections.Counter(); tot = collections.Counter()
    jobs = [('u', u) for u in top] + [('c', c) for c in selc]
    with ThreadPoolExecutor(8) as ex:
        for n, (kind, v, items) in enumerate(ex.map(listing, jobs)):
            key = kind + ':' + (hid(v) if kind == 'u' else v); tot[key] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: continue
                t = sv(it.get('title'))
                lang = sv(it.get('language'))
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                if not t or bad_title(t): continue
                cs = it.get('collection') or []
                if isinstance(cs, str): cs = [cs]
                if set(cs) & XCOL: continue
                low = t.lower()
                hint = bool(find_year(low) or find_date(low) or re.search(TVW, low) or show_of(t))
                trusted = kind == 'u' and ups[v] >= 40 or kind == 'c' and (cols[v] >= 40 or re.search(r'vhs|aircheck|tape|offair|tvrecord', v))
                if not hint and not trusted: continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'src': key, 'w': (2 if hint else 0) + (1 if trusted else 0)}; per[key] += 1
            if n % 25 == 0: print('listing', n, 'of', len(jobs), 'cands', len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    cands = sorted(seen.values(), key=lambda x: (-x['w'], -(x['downloads'] or 0)))[:MAXC]
    cands.sort(key=lambda x: x['identifier'])
    print('candidates', len(seen), 'kept', len(cands), flush=True)
    print('LISTING TABLE (source, listed, candidates)')
    for k, n in per.most_common(150): print('  %6d %6d  %s' % (tot[k], n, k))
    with gzip.open(os.path.join(PARTS, 'mine_cands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(cands, f, separators=(',', ':'))
    sys.exit(0)
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
def judge(title, desc, subj, col, m):
    low = title.lower(); blob = (title + ' ' + subj + ' ' + desc[:600]).lower()
    if bad_title(title): return None, 'title'
    if re.search(X_FOR, blob) or re.search(X_NONUS, (title + ' ' + subj + ' ' + desc[:200]).lower()): return None, 'foreign'
    if re.search(X_JUNK, (title + ' ' + subj).lower()): return None, 'junk'
    if set(col) & XCOL: return None, 'collection'
    sh = show_of(title)
    ad = find_date(low) or find_date(desc[:300])
    e = int(ad[:4]) if ad else (find_year(low) or find_year(desc[:400]) or find_year(subj))
    if not e and sh and sh['y1'] >= 1984 and sh['y0'] <= 2004 and sh['y0']: e = max(sh['y0'], 1984)
    if not e: return None, 'noyear'
    my = re.match(r'(\d{4})', str(m.get('date') or m.get('year') or ''))
    tv = bool(re.search(TVW, blob))
    if not tv and not sh: return None, 'notv'
    if sh and sh['y0'] and e < sh['y0'] - 1: sh = None
    if not sh and not re.search(STRONG, blob) and not re.search(TVW, low): return None, 'weak'
    return (sh, ad, e), ''
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): REJ['nometa'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': REJ['restricted'] += 1; return None
    if str(m.get('mediatype', 'movies')) != 'movies': REJ['type'] += 1; return None
    lang = sv(m.get('language'))
    if lang and not re.search(r'(?i)eng|english|^en\b', lang): REJ['lang'] += 1; return None
    title = sv(m.get('title'))
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', sv(m.get('description'))).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(str(x) for x in subj)
    subj = str(subj)
    r, why = judge(title, desc, subj, col, m)
    if not r: REJ[why] += 1; return None
    sh, ad, e = r
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
        if sz and sz / 1e6 / (d / 60) > 30 and b.get('format') != 'h.264 IA': continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 600: REJ['short'] += 1; return None
    files.sort(key=lambda f: f[0])
    q = classify(title, desc, sh, ad)
    return {'i': it['identifier'], 'q': q, 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': subj[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': sh['title'] if sh else '', 'e': e, 'net': sh['net'] if sh else '', 'ct': 'mine', 'up': hid(str(m.get('uploader') or '')), 'ad': ad, 'src': it.get('src', '')}
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'mine_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []; cnt = collections.Counter()
    with ThreadPoolExecutor(THREADS) as ex:
        for n, (it, r) in enumerate(zip(cands, ex.map(meta, cands))):
            cnt[it.get('src', '')] += 1
            if r: res.append(r)
            if n % 2000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'mine-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump({'res': res, 'cnt': dict(cnt)}, f, ensure_ascii=False, separators=(',', ':'))
    print('rejections', sorted(REJ.items(), key=lambda kv: -kv[1]))
    print('shard done', len(res)); sys.exit(0)
have0 = load_have()
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
def rekeep(x):
    if x['i'] in have0 or x.get('up') in DROP or x.get('src', '')[2:] in DROP: return False
    r, why = judge(x['t'], x.get('ds', ''), x.get('s', ''), x.get('c') or [], {'date': x.get('d'), 'year': x.get('y')})
    return bool(r)
old = [x for x in old0 if rekeep(x)]
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []; cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(PARTS, 'mine-*.json.gz'))):
    j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
    for k, n in j.get('cnt', {}).items(): cnt[k] += n
    for x in j.get('res', []):
        if x['i'] not in have and rekeep(x): have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res), 'with exact date', sum(1 for x in res if x.get('ad')), 'with show', sum(1 for x in res if x.get('k')))
bt = collections.defaultdict(list)
for x in res: bt[x['q']].append(x)
print('CATEGORY TABLE')
for t in sorted(bt, key=lambda t: -len(bt[t])): print('  %-8s items %6d  hours %7d' % (t, len(bt[t]), hrs(bt[t])))
print('YEAR TABLE', sorted(collections.Counter(x['e'] for x in res).items()))
ks = collections.Counter(x['k'] for x in res if x['k'])
print('TOP SHOWS', ks.most_common(80))
bs = collections.defaultdict(list)
for x in res: bs[x.get('src', '')].append(x)
random.seed(5)
print('SOURCE TABLE (kept, looked up, keep %, hours, source) with samples')
for k in sorted(bs, key=lambda k: -len(bs[k]))[:140]:
    L = bs[k]; n = cnt.get(k, 0)
    print('  %6d %6d %4s %6d  %s' % (len(L), n, (str(round(100 * len(L) / n)) + '%') if n else '-', hrs(L), k))
    for x in random.sample(L, min(3, len(L))): print('        ', x['q'], '|', x['t'][:70], '|', x['e'], x.get('ad', ''))
low = [(k, n, len(bs.get(k, []))) for k, n in cnt.items() if n >= 40 and len(bs.get(k, [])) / n < 0.03]
print('LOW YIELD SOURCES', [(k, n, g) for k, n, g in sorted(low, key=lambda z: -z[1])[:80]])
with open(os.path.join(PARTS, 'mine_low.txt'), 'w', encoding='utf-8') as f:
    for k, n, g in low: f.write(k[2:] + '\n')
random.seed(7)
for x in random.sample(res, min(80, len(res))): print('SAMPLE', x['q'], '|', x['k'][:24], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'], x.get('ad', ''))
