import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (archive harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
T0 = time.time()
OUTF = os.path.join(OUT, 'tvmovies.json.gz')
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[^a-z0-9]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
FILMS = []
_seen = set()
for line in open(os.path.join(here, 'tvmovies_titles.txt'), encoding='utf-8'):
    p = line.rstrip('\n').split('|')
    if len(p) < 3 or (p[0], p[1]) in _seen: continue
    _seen.add((p[0], p[1]))
    FILMS.append({'title': p[0], 'year': int(p[1]), 'ct': p[2], 'net': p[3] if len(p) > 3 else '', 'n': norm(p[0])})
HOSTS = [('Elvira', ["elvira's movie macabre", 'movie macabre', 'elvira mistress of the dark presents']), ('Commander USA', ["commander usa's groovie movies", 'commander usa', 'groovie movies']), ('Joe Bob Briggs', ['monstervision', "joe bob's drive-in theater", 'joe bob briggs drive-in', 'joe bob drive in theater']), ('USA Up All Night', ['usa up all night', 'up all night with rhonda shear', 'up all night with gilbert gottfried']), ('Dr. Paul Bearer', ['dr. paul bearer', 'dr paul bearer', 'creature feature wtog']), ('Count Gore De Vol', ['count gore de vol', 'count gore', 'creature feature wdca']), ('Zacherley', ['zacherley', 'zacherle', 'shock theater zacherley']), ('Son of Ghoul', ['son of ghoul']), ('Big Chuck and Lil John', ['big chuck and lil john', "big chuck and lil' john", 'hoolihan and big chuck']), ('Chiller Theatre', ['chiller theatre', 'chiller theater', 'chilly billy']), ('Creature Features', ['creature features', 'bob wilkins', 'john stanley creature features']), ('Sammy Terry', ['sammy terry', 'nightmare theater']), ('Dr. Shock', ['dr. shock', 'dr shock scream-in', 'mad theater']), ('Sir Graves Ghastly', ['sir graves ghastly']), ('The Ghoul', ['the ghoul show', 'ghoul ron sweed']), ('Morgus', ['morgus the magnificent', 'morgus presents']), ('Dr. Creep', ['dr. creep', 'shock theatre dr creep']), ('Stella', ['saturday night dead', 'stella saturday night dead']), ('Crematia Mortem', ['crematia mortem', "creature feature crematia"]), ('Fritz the Nite Owl', ['fritz the nite owl', 'nite owl theatre']), ('Dr. Madblood', ['doctor madblood', 'dr. madblood']), ('Bowman Body', ['bowman body', 'shock theater bowman']), ('Rhonda Shear', ['rhonda shear']), ('Grampa', ["grampa's monster movies", 'super scary saturday', 'grampa munster tbs']), ('Dr. Gangrene', ['dr. gangrene', 'chiller cinema']), ('Mr. Lobo', ['cinema insomnia']), ('Movie Macabre', ['fright night with seymour', 'seymour fright night', 'larry vincent seymour']), ('Shock Theater', ['shock theater', 'shock theatre']), ('Fright Night', ['fright night wor', 'fright night theater']), ('Thriller Theatre', ['thriller theatre', 'thriller theater']), ('Dialing for Dollars', ['dialing for dollars movie', 'the big money movie', 'money movie']), ('Night Flight', ['night flight usa network movie']), ('Kung Fu Theater', ['kung fu theater', 'kung fu theatre', 'black belt theater', 'black belt theatre', 'drive-in movie wnew']), ('Saturday Nightmares', ['saturday nightmares usa', 'usa saturday nightmares']), ('TNT MonsterVision', ['tnt monstervision', 'monstervision tnt']), ('Mystery Science Theater', [])]
HOSTS = [h for h in HOSTS if h[1]]
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
ROUTES = [
 ('rec', 'title:("with commercials" OR "w/ commercials" OR "original commercials" OR "with original ads" OR "commercials included") AND title:(movie OR film OR premiere OR theater OR theatre OR cinema OR feature OR matinee)'),
 ('rec', 'title:("network premiere" OR "broadcast premiere" OR "television premiere" OR "tv premiere" OR "world television premiere" OR "edited for television" OR "edited for tv" OR "tv edit" OR "tv version" OR "tv cut" OR "television version" OR "television cut" OR "broadcast version" OR "network tv version" OR "network version" OR "abc tv version" OR "nbc tv version" OR "cbs tv version" OR "extended tv" OR "extended television")'),
 ('rec', 'title:("sunday night movie" OR "monday night movie" OR "tuesday night movie" OR "wednesday night movie" OR "thursday night movie" OR "friday night movie" OR "saturday night movie" OR "movie of the week" OR "saturday night at the movies" OR "night at the movies" OR "late movie" OR "late late movie" OR "late show movie" OR "afternoon movie" OR "morning movie" OR "million dollar movie" OR "4:30 movie" OR "the 4:30 movie" OR "early show movie" OR "movie matinee" OR "saturday matinee" OR "sunday matinee" OR "prime movie" OR "movie loft" OR "family film festival" OR "big movie" OR "8 o\'clock movie" OR "eight o\'clock movie" OR "superstation movie")'),
 ('rec', 'title:(tbs OR "superstation" OR tnt OR "usa network" OR wgn OR wor OR wpix OR ktla OR kttv OR wtbs OR amc OR "american movie classics" OR tcm OR "turner classic movies" OR "family channel" OR "disney channel" OR "sci-fi channel" OR "sci fi channel" OR "comedy central" OR fx OR "abc family" OR "fox family" OR lifetime OR "tv land" OR "nick at nite") AND title:(movie OR film OR feature OR presents OR premiere) AND (title:(' + YRS + ' OR vhs OR recording OR recorded OR broadcast OR aired OR airing OR betamax OR tape))',
 ),
 ('rec', 'subject:("with commercials" OR "tv broadcast" OR "off air" OR "off-air" OR "vhs recording" OR "home recording" OR "taped from tv" OR "recorded from tv" OR "tv recording" OR "television broadcast") AND (subject:(movie OR movies OR film OR "feature film") OR title:(movie OR film))'),
 ('premium', 'title:(hbo OR cinemax OR showtime OR "the movie channel" OR starz OR encore OR "home box office" OR "spotlight" OR "z channel" OR "on tv" OR "select tv" OR prism OR "wht") AND (title:(' + YRS + ' OR 1980 OR 1981 OR 1982 OR 1983 OR vhs OR recording OR recorded OR broadcast OR aired OR airing OR betamax OR tape OR bumper OR bumpers OR intro OR "feature presentation") )'),
 ('tvgen', 'subject:("tv movie" OR "tv movies" OR "made for tv" OR "made-for-tv" OR "made for television" OR "television film" OR "television movie" OR "tv film" OR telefilm OR "movie of the week" OR "abc movie of the week" OR "hallmark hall of fame" OR "disney sunday movie" OR "wonderful world of disney" OR "lifetime movie" OR "lifetime original" OR "usa original" OR "hbo original" OR "showtime original" OR "disney channel original movie" OR "dcom")'),
 ('tvgen', 'title:("tv movie" OR "tv-movie" OR "made for tv" OR "made-for-tv" OR "made for television" OR "television movie" OR "tv film" OR telefilm OR "hallmark hall of fame" OR "disney sunday movie" OR "wonderful world of disney" OR "magical world of disney" OR "lifetime movie" OR "lifetime original" OR "usa world premiere movie" OR "world premiere movie" OR "hbo original" OR "showtime original" OR "disney channel original" OR "disney channel premiere" OR "abc afterschool special" OR "cbs schoolbreak")'),
 ('mini', 'title:(miniseries OR "mini-series" OR "mini series" OR "tv miniseries") OR subject:(miniseries OR "mini-series" OR "tv miniseries" OR "television miniseries")'),
]
COLS = ['feature_films', 'SciFi_Horror', 'Film_Noir', 'Comedy_Films', 'moviesandfilms_western', 'Sci-Fi_Horror', 'film_noir', 'publicdomainmovies', 'pd_movies', 'classic_movies', 'classicmovies', 'westerns', 'classic_westerns', 'b_movies', 'drive-in', 'driveinmovies', 'grindhouse', 'kungfumovies', 'martial_arts_films', 'serials', 'movie_serials', 'cinemaserials', 'cliffhanger_serials', 'horrorhosts', 'horror_hosts', 'horrormovies', 'horror_movies', 'scifimovies', 'monstermovies', 'mysterymovies', 'crime_movies', 'war_movies', 'adventure_movies', 'tvmovies', 'tv_movies', 'madefortv', 'madefortvmovies', 'made-for-tv-movies', 'movieoftheweek', 'vhsmovies', 'vhs_movies', 'vhsrips', 'vhs-rips', 'laserdisc', 'laserdiscs', 'laserdisc_archive', 'betamax', 'betamaxarchive', 'tvbroadcastmovies', 'godzilla', 'kaiju', 'abbottandcostello', 'bowery_boys', 'charlie_chan', 'sherlock_holmes_films', 'threestooges', 'east_side_kids', 'roy_rogers', 'gene_autry', 'john_wayne', 'hopalong_cassidy', 'tarzan', 'familyfilms', 'family_films', 'christmasmovies', 'christmas_movies', 'holidaymovies', 'animatedfeatures', 'animated_features']
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=60000, fields='identifier,title,date,year,collection,downloads,language'):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': fields, 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > cap: break
    return out
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblad[ao]|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|german|fran[cç]ais|french dub|vf|vostfr|italiano|ita|nederlands|svenska|norsk|dansk|suomi|polski|lektor|magyar|rom[aâ]n[aă]|t[uü]rk[cç]e|turkish|русск|russian|hindi|tamil|telugu|urdu|arabic|bahasa|tagalog|korean|japanese dub|sub ?esp|subtitulad[ao]|pelicula|pel[ií]cula completa|filme|film complet|ganzer film|film completo|em portugu|en espa|completa en|cap[ií]tulo|episodio|folge|staffel|saison|multi ?sub|dual audio)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|rom ?hack|emulator|audiobook|audio book|ebook|pdf|soundtrack|ost|score suite|theme song|trailer|trailers|teaser|tv spots?|radio spots?|promo|promos|bloopers?|outtakes?|deleted scenes?|fan ?made|fan-?edit|fanedit|fan cut|fan film|amv|ytp|parody|spoof|abridged|review|reviews|reviewed|recap|podcast|reaction|commentary|rifftrax|riff ?trax|mst3k|mystery science theater|interview|interviews|making of|behind the scenes|featurette|documentary about|video essay|analysis|explained|ranked|lost media|stock footage|screen test|clip|clips|scene|scenes|excerpt|excerpts|highlights|opening to|closing to|opening and closing|previews?|menu|dvd menu|bonus|extras|iso|dvd9|dvd5|remux|2160p|4k|uhd|hdr|1080p|1080i|bluray|blu-ray|blu ray|bdrip|brrip|web-?dl|webrip|hdtv|upscale[d]?|ai upscal\w*|60fps|colorized by|sample)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(netflix|hulu|disney\+|paramount\+|hbo max|prime video|tiktok|twitch|livestream|zoom)\b"
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'silent_films', 'short_films', 'prelinger', 'ephemera', 'home_movies', 'stock_footage', 'adultcdroms', 'animationandcartoons', 'classic_cartoons', 'television_inbox', 'tvnews', 'tvarchive'}
TAGS = r"(?i)\[[^\]]*\]|\((?!19\d\d\)|200[0-4]\))[^)]*\)|\b(vhs ?rip|vhsrip|vhs|betamax|beta|laserdisc|ld ?rip|dvd ?rip|dvdrip|dvd|tv ?rip|tvrip|xvid|divx|x264|h264|aac|ac3|mp4|avi|mkv|480p|576p|720p|full ?screen|fullscreen|wide ?screen|widescreen|pan (and|&) scan|open matte|uncut|unrated|theatrical( cut| version)?|director'?s cut|extended( cut| version)?|remastered|restored|hq|hd|sd|full movie|full film|full length|complete movie|complete film|the movie|public domain|pd|english|eng|color|colour|b&w|black and white|technicolor|classic|feature film|feature|film|movie|tv movie|made for tv|television movie|miniseries|mini-series|mini series|with (original )?commercials|w/ ?commercials|commercials included|woc|recorded|recording|broadcast|aired|airing|tape|off[- ]air|original)\b"
def ftitle(t):
    s = re.sub(r'[_.]+', ' ', t)
    s = re.sub(TAGS, ' ', s)
    s = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ' ', s)
    s = re.sub(r'(?<!\d)(19[2-9]\d|200[0-4])(?!\d)', ' ', s)
    s = re.sub(r'\(\s*\)|\[\s*\]', ' ', s)
    s = re.sub(r'(?i)\b(feature presentation|saturday night at the movies|late (late )?movie|afternoon movie|million dollar movie)\b', ' ', s)
    s = re.sub(r"(?i)\b(hbo|cinemax|showtime|the movie channel|starz|encore|tbs|tnt|usa network|usa|wgn|wor|wpix|ktla|kttv|wtbs|amc|tcm|abc|nbc|cbs|fox|upn|the wb|pbs|[wk][a-z]{3}(-tv)?( \d+)?|channel \d+|ch\.? ?\d+|network premiere|broadcast premiere|tv premiere|world premiere|sunday night movie|movie of the week|presents?|superstation|family channel|disney channel|sci-?fi channel)\b", ' ', s)
    s = re.sub(r'\s[-–|:]+\s*$', ' ', re.sub(r'^\s*[-–|:]+\s', ' ', s))
    s = ' '.join(s.split()).strip(' -–|:,.')
    return s
def ok_title(t):
    if not t: return False
    low = t.lower() + ' '
    low = re.sub(r'(with|w/|w|incl\.?|including|original) ?(original |the )?(commercials?|ads)|commercials included', ' ', low)
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    return True
def film_match(f, title, y):
    nt = ' ' + norm(title) + ' '
    if (' ' + f['n'] + ' ') not in nt: return False
    c = norm(ftitle(title))
    words = len(f['n'].split())
    ys = [int(v) for v in re.findall(r'(?<!\d)(19\d\d|200\d)(?!\d)', title)]
    my = re.match(r'(\d{4})', str(y or ''))
    if my: ys.append(int(my.group(1)))
    yok = any(abs(v - f['year']) <= 1 for v in ys)
    if ys and not yok and any(1900 < v <= 2004 for v in ys) and not any(v > 2004 for v in ys):
        if words < 4: return False
    starts = c.startswith(f['n']) or c.startswith('the ' + f['n']) or re.sub(r'^(stephen kings?|alex haleys?|louis lamours?|kenny rogers as|rodgers and hammersteins|frank herberts|robin cooks|peter benchleys) ', '', c).startswith(re.sub(r'^(stephen kings?|alex haleys?|louis lamours?|kenny rogers as|rodgers and hammersteins|frank herberts|robin cooks|peter benchleys) ', '', f['n']))
    if words >= 4: return True
    if not starts: return False
    rest = c[c.find(f['n']) + len(f['n']):].strip()
    if words >= 2: return yok or not rest or bool(re.match(r'^(part|pt|episode|ep|chapter|disc|tape|night|vol|\d)', rest))
    return yok and (not rest or bool(re.match(r'^(part|pt|episode|ep|chapter|disc|tape|night|vol|\d)', rest)))
def have_ids():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) == 'tvmovies.json.gz': continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(L, dict): have |= set(L); continue
        for x in L:
            if isinstance(x, dict):
                if x.get('i'): have.add(x['i'])
                ia = x.get('ia')
                if isinstance(ia, list) and ia and isinstance(ia[0], str): have.add(ia[0])
                for a in x.get('ias') or []:
                    if isinstance(a, list) and a and isinstance(a[0], str): have.add(a[0])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    return have
def tstr(it, k='title'):
    t = it.get(k); return ' '.join(str(v) for v in t) if isinstance(t, list) else str(t or '')
if MODE == 'plan':
    have = have_ids()
    old = set(x['i'] for x in json.load(gzip.open(OUTF, 'rt', encoding='utf-8'))) if os.path.exists(OUTF) else set()
    print('known', len(have), 'own', len(old), 'films', len(FILMS), 'hosts', len(HOSTS), flush=True)
    seen = {}; stat = collections.Counter(); rawc = collections.Counter()
    def add(it, route, extra=None):
        i = it['identifier']
        if i in have or i in old: stat['have'] += 1; return
        if i in seen:
            if route in ('list', 'host') and seen[i]['r'] not in ('list', 'host'): seen[i].update({'r': route, **(extra or {})})
            return
        t = tstr(it)
        lang = tstr(it, 'language')
        if lang and not re.search(r'(?i)eng|english|^en\b', lang): stat['lang'] += 1; return
        if not ok_title(t): stat['title'] += 1; return
        cs = it.get('collection') or []
        if isinstance(cs, str): cs = [cs]
        if set(cs) & XCOL: stat['xcol'] += 1; return
        seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'r': route, **(extra or {})}; stat['ok_' + route] += 1
    cl = scrape('mediatype:collection AND (identifier:(' + ' OR '.join(COLS) + ') OR title:("feature films" OR "public domain movies" OR "classic movies" OR "b movies" OR "drive-in" OR "horror hosts" OR "tv movies" OR "made for tv" OR westerns OR "film noir" OR serials OR "kung fu" OR "vhs rips" OR "vhs movies" OR laserdisc))', fields='identifier,title,item_count')
    cl = [c for c in cl if not re.search(r'(?i)trailer|poster|podcast|radio|audio|book|magazine|comic|soundtrack|fav-|adult|xxx|porn|erotic', c['identifier'] + ' ' + tstr(c))]
    if not cl: cl = [{'identifier': c, 'item_count': 100} for c in COLS]
    cl.sort(key=lambda c: -(c.get('item_count') or 0))
    print('COLLECTIONS FOUND', [(c['identifier'], c.get('item_count')) for c in cl[:120]], flush=True)
    use = [c['identifier'] for c in cl if (c.get('item_count') or 0) >= 20 and (c['identifier'] in COLS or (c.get('item_count') or 0) <= 30000)][:90]
    print('using collections', use, flush=True)
    def do_col(c):
        return c, scrape('mediatype:movies AND collection:(' + c + ')', cap=40000)
    with ThreadPoolExecutor(6) as ex:
        for c, items in ex.map(do_col, use):
            rawc['col:' + c] = len(items)
            for it in items: add(it, 'col', {'col': c})
    print('after collections', len(seen), dict(stat), flush=True)
    def do_route(k):
        return k, scrape('mediatype:movies AND (' + ROUTES[k][1] + ')')
    with ThreadPoolExecutor(5) as ex:
        for k, items in ex.map(do_route, range(len(ROUTES))):
            rawc['route:%d:%s' % (k, ROUTES[k][0])] = len(items)
            for it in items: add(it, ROUTES[k][0])
    print('after routes', len(seen), dict(stat), flush=True)
    def do_host(k):
        name, phr = HOSTS[k]
        q = ' OR '.join('"' + re.sub(r'["!:()\[\]{}/\\*?^~+]', ' ', p) + '"' for p in phr)
        return k, scrape('mediatype:movies AND (title:(' + q + ') OR subject:(' + q + '))')
    with ThreadPoolExecutor(8) as ex:
        for k, items in ex.map(do_host, range(len(HOSTS))):
            rawc['host:' + HOSTS[k][0]] = len(items)
            for it in items: add(it, 'host', {'host': HOSTS[k][0]})
    print('after hosts', len(seen), dict(stat), flush=True)
    def do_film(k):
        f = FILMS[k]
        q = ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', f['title']).split())
        return k, scrape('mediatype:movies AND title:("' + q + '")', cap=3000)
    fh = collections.Counter()
    with ThreadPoolExecutor(10) as ex:
        for k, items in ex.map(do_film, range(len(FILMS))):
            f = FILMS[k]
            for it in items:
                if film_match(f, tstr(it), it.get('year') or it.get('date')):
                    n0 = len(seen); add(it, 'list', {'k': k})
                    if len(seen) > n0 or (it['identifier'] in seen and seen[it['identifier']].get('k') == k): fh[k] += 1
            if k % 100 == 0: print('films', k, len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    print('raw counts', sorted(rawc.items(), key=lambda x: -x[1])[:140])
    print('stats', dict(stat))
    print('list films with candidates', sum(1 for k in range(len(FILMS)) if fh[k]), 'of', len(FILMS))
    print('list films without candidates', [FILMS[k]['title'] for k in range(len(FILMS)) if not fh[k]])
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), collections.Counter(c['r'] for c in cands), flush=True)
    with gzip.open(os.path.join(PARTS, 'tvmovies_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
NETS = [('hbo', r'\bhbo\b|home box office'), ('cinemax', r'\bcinemax\b'), ('showtime', r'\bshowtime\b'), ('tmc', r'the movie channel'), ('starz', r'\bstarz\b|\bencore\b'), ('tbs', r'\bw?tbs\b|superstation'), ('tnt', r'\btnt\b'), ('usa', r'usa network|\busa up all night|\busa\b'), ('wgn', r'\bwgn\b'), ('amc', r'\bamc\b|american movie classics'), ('tcm', r'\btcm\b|turner classic'), ('abc', r'\babc\b'), ('nbc', r'\bnbc\b'), ('cbs', r'\bcbs\b'), ('fox', r'\bfox\b'), ('pbs', r'\bpbs\b'), ('disney', r'disney channel|wonderful world of disney|disney sunday'), ('lifetime', r'\blifetime\b'), ('family', r'family channel|fox family|abc family'), ('scifi', r'sci-?fi channel')]
def bcast_year(title, desc):
    m = re.search(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-]((19)?[89]\d|(20)?0[0-4])(?!\d)', title)
    if m:
        y = m.group(3); y = int(y) if len(y) == 4 else (1900 + int(y) if y[0] in '89' else 2000 + int(y))
        return y
    m = re.search(r'(?i)(aired|airing|broadcast|recorded|taped|from|circa|c\.)\D{0,24}(19[89]\d|200[0-4])', title + ' ' + desc[:300])
    if m: return int(m.group(2))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? (19[89]\d|200[0-4])', title + ' ' + desc[:300])
    if m: return int(m.group(2))
    return ''
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): REJ['nofiles'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': REJ['restricted'] += 1; return None
    if str(m.get('mediatype', 'movies')) != 'movies': return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en\b', str(lang)): REJ['lang'] += 1; return None
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []; hi = 0
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 300: continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (d / 60) > 30: hi += 1; continue
        if re.search(r'(?i)trailer|sample|preview|bonus|extra|featurette|commentary|interview', b['name']): continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files: REJ['noplay' if not hi else 'bitrate'] += 1; return None
    files.sort(key=lambda f: f[0])
    title = m.get('title', ''); title = ' '.join(title) if isinstance(title, list) else str(title)
    if not ok_title(title): REJ['title'] += 1; return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    if set(col) & XCOL: REJ['xcol'] += 1; return None
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:600]).lower()
    if re.search(X_FOR, blob[:len(title) + len(str(subj)) + 200]): REJ['foreign'] += 1; return None
    if re.search(r'\b(podcast|fan ?film|fan ?made|fan ?edit|video ?game|gameplay|radio (show|program|broadcast)|old time radio|audio only|silent film|silent movie|home movie|stock footage|newsreel|educational film|industrial film|short film|short subject|cartoon short|music video|concert|sermon|lecture|webinar|trailer compilation|trailers)\b', blob): REJ['kind'] += 1; return None
    r = it['r']
    tot = sum(f[1] for f in files); longest = max(f[1] for f in files)
    if len(files) > 12 and r != 'list' and r != 'mini': REJ['pack'] += 1; return None
    my = re.match(r'(\d{4})', str(m.get('year') or m.get('date') or ''))
    tys = [int(v) for v in re.findall(r'(?<!\d)(19[1-9]\d|200\d|201\d|202\d)(?!\d)', title)]
    ry = ''
    k = ''; ct = ''; net = ''; host = it.get('host', ''); tv = 0
    rec = bool(re.search(r"(?i)with (original )?commercials|w/ ?commercials|commercials included|\bwoc\b|off[- ]air|taped (from|off)|recorded (from|off)|tv recording|vhs recording|home recording|original broadcast|as (it )?aired|network premiere|broadcast premiere|tv broadcast|bumpers?|station id", title + ' ' + str(subj) + ' ' + desc[:300]))
    for nk, rx in NETS:
        if re.search(rx, (title + ' ' + str(subj)).lower()): net = nk; break
    if r == 'list':
        f = FILMS[it['k']]
        if not film_match(f, title, m.get('year') or m.get('date')): REJ['listmatch'] += 1; return None
        k = f['title']; ct = f['ct']; ry = f['year']; net = f['net'] or net
        if ct not in ('miniseries',) and longest < 2700 and tot < 4200: REJ['short'] += 1; return None
    else:
        k = ftitle(title)
        if len(k) < 2 or len(k) > 90: REJ['ktitle'] += 1; return None
        cand = [v for v in tys if 1915 <= v <= 2004]
        if cand: ry = cand[0]
        elif my and 1915 <= int(my.group(1)) <= 2004 and not it['identifier'].startswith('youtube-'): ry = int(my.group(1))
        if any(v > 2004 for v in tys) and not cand: REJ['modern'] += 1; return None
        if r == 'host':
            ct = 'hosted'; tv = 1
            if longest < 2700 and tot < 3600: REJ['short'] += 1; return None
            if not re.search(r'(?i)' + '|'.join(re.escape(p) for hn, ph in HOSTS if hn == host for p in ph), title + ' ' + str(subj) + ' ' + desc[:200]): REJ['hostmatch'] += 1; return None
        elif r == 'premium':
            ct = 'premium'; tv = 1
            if not re.search(r'(?i)\b(hbo|cinemax|showtime|the movie channel|starz|encore|home box office|z channel|prism|select ?tv|on ?tv|spotlight)\b', title): REJ['premmatch'] += 1; return None
            if longest < 3600 and tot < 4200: REJ['short'] += 1; return None
        elif r == 'mini':
            ct = 'miniseries'
            if tot < 7200: REJ['short'] += 1; return None
            if not ry: REJ['noyear'] += 1; return None
        elif r == 'tvgen':
            ct = 'miniseries' if re.search(r'miniseries|mini-series|mini series', blob) and tot >= 7200 else 'tvmovie'
            if longest < 3600 and tot < 4200: REJ['short'] += 1; return None
            if not ry: REJ['noyear'] += 1; return None
        elif r == 'rec':
            tv = 1; ct = 'feature'
            if longest < 3600 and tot < 4500: REJ['short'] += 1; return None
            if tot > 5 * 3600: REJ['long'] += 1; return None
            if not re.search(r'(?i)movie|film|premiere|theat|cinema|feature|matinee|presents', title + ' ' + str(subj)): REJ['notmovie'] += 1; return None
        else:
            if not ry: REJ['noyear'] += 1; return None
            if ry < 1930: REJ['old'] += 1; return None
            ct = 'classic' if ry < 1984 else 'feature'
            if longest < (2700 if ry < 1984 else 3600): REJ['short'] += 1; return None
            if tot > 4.5 * 3600 and len(files) < 6: REJ['long'] += 1; return None
            if rec: tv = 1
        if ct in ('classic', 'feature', 'tvmovie') and re.search(r'(?i)\b(christmas|santa|xmas|thanksgiving|halloween special|easter)\b', k): ct = 'holiday'
        elif ct in ('classic', 'feature') and re.search(r'(?i)\b(disney|animated|cartoon feature|family film|children\'?s film)\b', title + ' ' + str(subj)): ct = 'kidsfilm'
    if ry and ry > 2004: REJ['modern'] += 1; return None
    e = bcast_year(title, desc) if (tv or rec) else ''
    if rec: tv = 1
    q = 0
    lowt = (title + ' ' + ' '.join(f[0] for f in files[:3])).lower()
    if tv: q += 6
    if re.search(r'vhs|betamax|laserdisc|\bld\b|tv ?rip|16mm|35mm tv print', lowt): q += 4
    if re.search(r'dvd', lowt): q += 2
    if re.search(r'720p|hd\b', lowt): q -= 3
    q += min(3, (it.get('downloads') or 0) / 3000)
    return {'i': it['identifier'], 'q': 'movie', 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': k[:90], 'e': e, 'net': net, 'ct': ct, 'ry': ry, 'rt': round((tot if len(files) <= 12 else longest) / 60), 'tv': tv, 'host': host, 'sc': round(q, 1), 'r': r}
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'tvmovies_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 2000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'tvmovies-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('rejects', sorted(REJ.items(), key=lambda x: -x[1]))
    print('shard done', len(res)); sys.exit(0)
def keep(x):
    if not ok_title(x['t']): return False
    if x.get('ry') and int(x['ry']) > 2004: return False
    if x['ct'] not in ('tvmovie', 'miniseries', 'feature', 'classic', 'hosted', 'premium', 'kidsfilm', 'holiday'): return False
    if x['rt'] < (45 if x['ct'] in ('classic', 'hosted') or x.get('tv') else 60) and x['ct'] != 'miniseries': return False
    return True
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
have = have_ids()
allx = {}
for x in old0:
    if keep(x) and x['i'] not in have: allx[x['i']] = x
n0 = len(allx)
for p in sorted(glob.glob(os.path.join(PARTS, 'tvmovies-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in allx and x['i'] not in have and keep(x): allx[x['i']] = x
best = {}; multi = collections.defaultdict(list)
for x in allx.values():
    if x['ct'] in ('hosted',) or (x.get('tv') and x['ct'] in ('feature', 'premium')):
        key = ('rec', x['i'])
    else:
        key = (norm(x['k']), str(x.get('ry') or ''))
    multi[key].append(x)
res = []
dropped = 0
for key, L in multi.items():
    L.sort(key=lambda x: (-x.get('sc', 0), -x.get('dl', 0)))
    if key[0] != 'rec' and L[0]['ct'] == 'miniseries':
        res.append(L[0]); dropped += len(L) - 1
    else:
        res.append(L[0]); dropped += len(L) - 1
res.sort(key=lambda x: x['i'])
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(x['rt'] for x in L) / 60)
print('kept from previous', n0, 'pool', len(allx), 'duplicate copies dropped', dropped, 'total', len(res), 'hours', hrs(res))
bt = collections.defaultdict(list)
for x in res: bt[x['ct']].append(x)
print('TYPE TABLE')
for t in sorted(bt): print('  %-10s items %5d  hours %6d  off-air %5d' % (t, len(bt[t]), hrs(bt[t]), sum(1 for x in bt[t] if x.get('tv'))))
print('ROUTES', sorted(collections.Counter(x.get('r') for x in res).items()))
print('RELEASE DECADES', sorted(collections.Counter((str(x['ry'])[:3] + '0s') if x.get('ry') else 'none' for x in res).items()))
print('BROADCAST YEARS', sorted(collections.Counter(str(x['e']) if x.get('e') else 'none' for x in res).items()))
print('NETWORKS', collections.Counter(x.get('net') or '-' for x in res).most_common(25))
print('HOSTS', collections.Counter(x['host'] for x in res if x.get('host')).most_common(40))
lf = collections.Counter(x['k'] for x in res if x.get('r') == 'list')
print('LIST FILMS FOUND', len(lf), 'of', len(FILMS))
print('LIST FILMS MISSING', [f['title'] for f in FILMS if not lf[f['title']]])
random.seed(11)
for x in random.sample(res, min(80, len(res))): print('SAMPLE', x['ct'], '|', x['k'][:50], '|', x.get('ry'), '|', x['t'][:70], '|', x['i'][:34], '|', x['rt'], 'min', '|', len(x['f']), 'f', '|tv' if x.get('tv') else '|', x.get('e'), '|', x.get('net'), '|', x.get('host'))
