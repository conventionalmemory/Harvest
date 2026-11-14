import json, gzip, os, re, sys, time, glob, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts')
os.makedirs(OUT, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
FOCUS = [z.strip().lower() for z in os.environ.get('FOCUS', '').split(';') if z.strip()]
THREADS = int(os.environ.get('THREADS', '16')); BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60; T0 = time.time()
SHOWS = json.load(open(os.path.join(here, 'shows_primetime.json'), encoding='utf-8'))
KMAP = {'sitcom': 'prime', 'drama': 'prime', 'variety': 'prime', 'reality': 'prime', 'special': 'prime', 'news': 'news', 'soap': 'soap', 'game': 'game', 'talk': 'talk', 'movie': 'movie'}
TVCOL = 'television OR television_inbox OR classic_tv OR classic_tv_1980s OR classic_tv_1990s OR vhstvshows OR vhsvault OR gorelicktv OR smokesvhsdvrcollection OR sitcoms OR televisionmovies OR vhsnews OR gameshows OR dvdtray OR dvdtray_inbox'
TVSET = set(TVCOL.split(' OR '))
DISQ = 'title:(season OR seasons OR episode OR episodes OR complete OR series OR sitcom OR nbc OR cbs OR abc OR fox OR upn OR vhs OR commercials OR woc OR "tv show" OR pilot OR finale OR s0* OR s1* OR 1x* OR 2x* OR 3x* OR 4x* OR 5x*) OR subject:(television OR sitcom OR "tv series" OR "tv show" OR nbc OR cbs OR abc OR vhs OR commercials OR "tv")'
DISC = re.compile(r"\b(s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|season\s?\d|seasons?|episodes?|ep\.?\s?\d|complete|series|sitcom|nbc|cbs|abc|fox|upn|wb|vhs|commercials|woc|w/o/c|tv show|pilot|finale|syndicat|aired|airing|broadcast|rerun)\b")
JUNK = re.compile(r"\b(trailers?|teasers?|promos?|bumpers?|opening|intro|theme song|theme|soundtrack|ost|review|reviews|reaction|reacts?|podcast|commentary|interview|interviews|panel|q&a|reunion special 20|behind the scenes|bloopers?|outtakes|gag reel|tribute|fan ?made|fan ?edit|fanvid|amv|parody|recap|explained|analysis|ranking|ranked|top \d+|video essay|documentary about|making of|game|gameplay|walkthrough|playthrough|longplay|ps[1-5]|xbox|nintendo|sega|pinball|slot machine|lego|toy|toys|figure|unboxing|audiobook|audio book|book|novel|comic|magazine|script|screenplay|sermon|church|council|selectmen|committee|town meeting|lecture|seminar|conference|webinar|karaoke|cover|remix|live at|concert|album|mixtape|dj|radio|stream|twitch|youtube|tiktok|remaster(ed)?|upscaled?|ai|deepfake|mock|ytp|compilation of clips|clips?|scene|scenes|moments|highlights|best of youtube|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|german|fran[cç]ais|french|italiano|italian|portugu[eê]s|legendado|subtitulado|vostfr|rus|russian|polish|polski|hindi|arabic|turkish|greek|dutch|svenska|suomi|norsk|dansk|magyar|czech|bbc|itv|channel 4|sky one|uk tv|uk|australia|australian|canada only|sub ita|sub esp|sub|subs|subtitle|subtitles|subbed|indonesia|malay|thai|vietsub|tagalog|historical society|museum|middle school|high school|jr|junior|lions club|talk series|live stream|livestream|discord|socials|tell all|cycle \d+|wrestling|ajpw|njpw|army|racing|paranormal|artist|thomas|tank engine|dora|bond|cupid|translation)\b")
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
MODERN = re.compile(r'(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)')
YR = re.compile(r'(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)')
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=30000):
    out, cursor = [], None
    while len(out) < cap:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language,description', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        for it in j.get('items', []):
            it['description'] = ' '.join(flat(it.get('description')).split())[:1500]
            out.append(it)
        cursor = j.get('cursor')
        if not cursor: break
    return out
def norm(s):
    s = s.lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[.'!?,:]", '', s)
    return re.sub(r'[^a-z0-9$/]+', ' ', s).strip()
def flat(v): return ' '.join(str(a) for a in v) if isinstance(v, list) else str(v or '')
def load_have():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if p.endswith('primetime.json.gz') or p.endswith('ads.json.gz') or p.endswith('movies.json.gz'): continue
        try:
            for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
                have.add(x['i'] if isinstance(x, dict) else x[0])
        except Exception as e: print('skip', p, e)
    return have
GP = os.path.join(PARTS, 'guide.json'); GH = os.path.join(here, 'guide_primetime.json')
def norm0(t): return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9]+", ' ', t.lower().replace("'", ''))).strip()
def fetch_guides():
    out = {}
    for sh in SHOWS:
        if not sh.get('guide') or sh['title'] in out: continue
        j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(sh['title'])) or []
        pick = None
        for r in j:
            w = r.get('show') or {}
            py = int((w.get('premiered') or '0000')[:4] or 0)
            if norm0(w.get('name', '')) == norm0(sh['title']) and abs(py - sh.get('start', sh['first'])) <= 1: pick = w; break
        if not pick: print('GUIDE none', sh['title']); continue
        eps = get('https://api.tvmaze.com/shows/%d/episodes' % pick['id']) or []
        rows = [[e['season'], e['number'], e.get('name') or '', e['airdate']] for e in eps if e.get('number') and e.get('airdate') and e['airdate'] <= '2004-08-31' and e['season'] <= sh.get('maxs', 99)]
        out[sh['title']] = rows; print('GUIDE', sh['title'], len(rows), 'episodes', flush=True); time.sleep(1)
    return out
if MODE == 'plan':
    GUIDE = fetch_guides()
    if not GUIDE and os.path.exists(GH): GUIDE = json.load(open(GH, encoding='utf-8'))
    json.dump(GUIDE, open(GP, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
else:
    GUIDE = json.load(open(GP, encoding='utf-8')) if os.path.exists(GP) else json.load(open(GH, encoding='utf-8')) if os.path.exists(GH) else {}
GENT = {'pilot', 'the pilot', 'finale', 'the finale', 'the reunion', 'the wedding', 'the trip', 'the movie', 'the letter', 'the show', 'the party', 'christmas', 'thanksgiving', 'halloween'}
EP = {}
for _k, _rows in GUIDE.items():
    _t = {}; _own = {norm0(q) for s in SHOWS if s['title'] == _k for q in s['q']}
    for _s, _n, _nm, _d in _rows:
        _z = norm0(_nm)
        if len(_z) >= 8 and _z not in GENT and _z not in _own and len(_z.split()) >= 2: _t[_z] = (_s, _n)
    EP[_k] = {'t': sorted(_t.items(), key=lambda kv: -len(kv[0])), 'd': {(_s, _n): _d for _s, _n, _nm, _d in _rows}, 'maxs': max([r[0] for r in _rows] or [0])}
SE1 = re.compile(r"\bs(?:eason)?\s?(\d{1,2})[\s._-]{0,3}(?:e|ep|episode)\s?(\d{1,3})\b|\b(\d{1,2})x\s?(\d{1,3})\b")
def file_se(sh, text):
    g = EP.get(sh['title'])
    if not g: return None
    low = clean(text)
    m = SE1.search(low)
    if m:
        a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
        return (a, b)
    z = ' ' + norm0(low) + ' '
    for k, v in g['t']:
        p = z.find(' ' + k + ' ')
        if p < 0: continue
        nx = z[p + len(k) + 2:].split(' ')[0]
        if re.fullmatch(r'[ivx]+|\d{1,2}', nx or '-'): continue
        return v
    return None
def ep_key(sh, low):
    g = EP.get(sh['title'])
    if not g: return None
    z = ' ' + norm0(low) + ' '
    for k, v in g['t']:
        p = z.find(' ' + k + ' ')
        if p < 0: continue
        nx = z[p + len(k) + 2:].split(' ')[0]
        if re.fullmatch(r'[ivx]+|\d{1,2}', nx or '-'): continue
        return k
    return None
def guide_ok(sh, low):
    g = EP.get(sh['title'])
    if not g: return None
    se = file_se(sh, low)
    if se: return (se in g['d'])
    return None
BYT = {}
for _s in SHOWS: BYT.setdefault(_s['title'], _s)
STOP = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'to', 'with', 'show', 'by', 'for', 'is', 'it', 'at', 'from', 'md', 'mr'}
def sig(q): return [w for w in norm(q).split() if w not in STOP]
def generic(sh): return bool(sh.get('amb')) or len(sig(sh['q'][0])) <= 2
def start(sh): return sh.get('start', sh['first'])
WORDN = {w: i + 1 for i, w in enumerate('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen'.split())}
WORDN.update({w: i + 1 for i, w in enumerate('first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split())})
MULTI = re.compile(r"\bseasons\b|\b(?:s|season)\s?\d{1,2}\s?(?:-|&|and|to|thru|through)\s?(?:s|season)?\s?\d{1,2}\b|complete series|all episodes|all seasons|entire series|full series|complete collection")
SEAS = re.compile(r"\bseason\s?(\d{1,2})\b|\bseason\s(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)(?:\sand\sfinal)?\sseason\b|\b(?:s|se|y)\s?(\d{1,2})\s?(?:e|ep|d|disc)\s?\d{1,3}\b|\bs(\d{1,2})\b|\b(\d{1,2})x\s?\d{1,3}\b")
def clean(t): return re.sub(r'(?<=[a-z0-9]{2})\.(?=[a-z0-9]{2})', ' ', re.sub(r'[_]+', ' ', t.lower().replace('’', "'")))
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
def item_year(it):
    m = re.match(r'(\d{4})', flat(it.get('date')) or flat(it.get('year')) or '')
    return int(m.group(1)) if m else 0
SPIN = re.compile(r"\b(svu|special victims|criminal intent|trial by jury|golden palace|new class|college years|girl meets world|fuller house|the conners|young sheldon|reboot|revival|frasier 2023|animated series)\b")
FOREIGN = re.compile(r"\b(saison|temporada|staffel|episodio|epis[oó]dio|cap[ií]tulo|folge|parte|piloto|serie tv|vf|fr|ita|lat|pt br|dual audio|dublagem|dub|napisy|lektor|esp|ger|nl|temp|s[eé]rie)\b")
DESCEV = re.compile(r"\b(sitcom|tv series|television series|nbc|cbs|abc|upn|the wb|syndicat\w*|vhs|commercials|laugh track|primetime|prime time)\b")
JUNKD = re.compile(r"\b(podcast|sermon|city council|board of|town meeting|gameplay|walkthrough|let's play|longplay|reviews?|reaction|public access|community television|community media|pastor|ministry|church|webinar|lecture|school district|chamber of commerce|library|nonprofit|non-profit|fundraiser|workshop|expo|home show|contractor|remodeling tips)\b")
TAPE = re.compile(r"\b(vhs|betamax|tape|taped|recorded|recording|commercials|woc|broadcast|aired|airing|nbc|cbs|abc|fox|upn|wb|tgif|must see tv|primetime|prime time)\b")
TAPE2 = re.compile(r"\b(vhs|betamax|commercials|woc|off air|off-air|home recording)\b")
EPN = re.compile(r"\b(?:episode|ep)\.?\s?#?(\d{1,4})\b")
def has_cast(sh, blob): return any(c.lower() in blob for c in sh.get('cast', []))
def year_ok(sh, t):
    ys = [int(y) for y in YR.findall(t)]
    if not ys: return True
    lo, hi = sh['first'], sh['last']
    return any(lo <= y <= max(hi, min(2004, lo + 20)) and y <= 2004 for y in ys) or any(lo <= y <= hi for y in ys)
LEAD = re.compile(r"^(?:\s*(?:\(?\d{1,4}[-./]\d{1,2}(?:[-./]\d{1,4})?\)?|(?:19|20)\d\d|vhs|beta|tape|dvd|tv|the|nbc|cbs|abc|fox|upn|wb|[wk][a-z]{2,3}(?:-tv)?(?:\s?\d{1,2})?)\b[\s\-:,.|]*)*", re.I)
TAIL = re.compile(r"^\s*(?:$|[-:|(\[,#]|\b(?:s\s?\d{1,2}\s?e\s?\d{1,3}|s\s?\d{1,2}\b|y\s?\d{1,2}\s?e\s?\d{1,3}|d\s?\d{1,2}\b|\d{1,2}x\s?\d{1,3}|\d{1,3}\b|season|seasons|series|episode|episodes|ep\b|complete|full|sitcom|tv|pilot|finale|nbc|cbs|abc|fox|upn|wb|vhs|dvd|disc|vol|volume|tape|with commercials|w commercials|woc|commercials|(?:19[89]\d|200[0-4])|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b)", re.I)
DAILY = {'news', 'soap', 'talk'}
MOD2 = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](0[5-9]|[12]\d)\b')
def head(sh, t):
    best = 0
    for low in (clean(t), LEAD.sub('', clean(t))):
        low = low.replace("'", '').replace('&', ' and ').strip()
        for q in sh['q']:
            ws = norm(q).split()
            if ws and ws[0] == 'the': ws = ws[1:]
            if not ws: continue
            m = re.match(r"(?:the[\W_]+)?" + r"[\W_]*".join("[.']?".join(re.escape(ch) for ch in w) for w in ws) + r"(?![a-z0-9])", low)
            if m:
                rest = low[m.end():]
                if not re.match(r'-[a-z]', rest) and TAIL.match(rest.lstrip(" '!?.")): return 2
                best = 1
    return best
def strict(sh, t): return head(sh, t) == 2
def seg(sh, t): return any(head(sh, p) == 2 for p in re.split(r'\s[-|]\s|[,;/|]', t))
def verify(sh, x):
    ds = sorted(f[1] for f in x['f'])
    blob = ((x.get('ds') or '') + ' ' + (x.get('s') or '')).lower()
    return has_cast(sh, blob) or bool(DESCEV.search(blob)) or (len(ds) >= 3 and 1080 <= ds[len(ds) // 2] <= 4200)
def season_ok(sh, low):
    if sh.get('maxs') and any(n > sh['maxs'] for n in seasons(low)) and not MULTI.search(low): return False
    return all(start(sh) + n - 1 <= sh['last'] + 1 for n in seasons(low))
def consider(sh, it, route='t'):
    t = flat(it.get('title')); low = clean(t)
    if not t or NONLAT.search(t) or JUNK.search(low) or FOREIGN.search(low) or SPIN.search(low): return False
    if sh.get('junk') and re.search(sh['junk'], low): return False
    gk = guide_ok(sh, low) if sh.get('guide') else None
    if gk is False and sh.get('guide') == 1: return False
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return False
    if MOD2.search(t) or re.search(r'\b20(0[5-9]|[12]\d)[01]\d[0-3]\d\b', low) or re.search(r'\b(amiga|atari|commodore|c64|ms-dos|nes|snes|genesis|zx spectrum|b[oö]l[uü]m|tvi|kzk)\b', low): return False
    nt = ' ' + norm(low) + ' '
    intitle = any((' ' + norm(q) + ' ') in nt for q in sh['q'])
    if not intitle and gk and any(e in low for e in sh.get('extra', [])): intitle = True
    if not intitle and gk and sh.get('strictg') and len(sig(ep_key(sh, low) or '')) >= 3 and not SE1.search(low): intitle = True
    desc = flat(it.get('description')).lower(); subj = flat(it.get('subject')).lower()
    cols = set(it.get('collection') or []) if isinstance(it.get('collection'), list) else {it.get('collection')}
    iy = item_year(it); mod = iy > 2004 and iy > sh['last']
    inrun = any(sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t)) or (iy and sh['first'] <= iy <= sh['last'])
    cast = has_cast(sh, desc + ' ' + subj + ' ' + low)
    if not intitle:
        if route != 'd' or not sh.get('must'): return False
        nd = ' ' + norm(desc) + ' '
        if not any((' ' + norm(q) + ' ') in nd for q in sh['q']): return False
        if MODERN.search(t) or mod or JUNKD.search(desc): return False
        if not (TAPE.search(low) or cols & TVSET): return False
        if re.search(r'\bcommercials?\b|\bads\b|\bpromos?\b', low): return False
        if generic(sh) and not (cast or (inrun and re.search(r'\b(nbc|cbs|abc|fox|upn|wb|sitcom|commercials)\b', desc))): return False
        return 'd'
    if not year_ok(sh, t) or not season_ok(sh, low): return False
    if MODERN.search(t) and not inrun: return False
    if sh['kind'] in DAILY and not (airdate(t) or any(1984 <= int(y) <= 2004 and sh['first'] <= int(y) <= sh['last'] for y in YR.findall(t))): return False
    strong = bool(seasons(low)) or bool(MULTI.search(low)) or bool(gk)
    if sh.get('strictg') and not (strong or (TAPE2.search(low) and not mod) or (re.search(r'\bfox\b', low) and inrun)): return False
    if gk and not mod and not (generic(sh) and len(sig(sh['q'][0])) <= 1 and head(sh, low) != 2 and not cast and not ep_key(sh, low) and not seg(sh, t)): return 't'
    m = EPN.search(low)
    if m and not seasons(low) and sh['kind'] not in DAILY and sh['kind'] not in ('game', 'reality') and int(m.group(1)) > 30 * (sh['last'] - start(sh) + 1): return False
    weak = bool(DISC.search(low + ' ' + subj)) or bool(cols & TVSET) or bool(inrun) or any(norm(q) in norm(subj) for q in sh['q'])
    dev = cast or bool(DESCEV.search(desc))
    hd = head(sh, low); st = hd == 2
    if sh['kind'] in DAILY: return 't'
    if not strong and not cast and JUNKD.search(desc + ' ' + low): return False
    tape = bool(TAPE.search(low))
    single = len(sig(sh['q'][0])) <= 1
    if generic(sh):
        if single and not st and not cast: return 'b' if not mod and len(low) < 160 and any(re.search(r'\bepisodes? of (the )?' + re.escape(norm(q)) + r'\b|\b' + re.escape(norm(q)) + r' compilation tape\b', norm(low)) for q in sh['q']) else False
        if st and (strong or cast or (weak and (not mod or dev))): return 't'
        if hd and (strong or cast or ((weak or tape) and not mod)): return 't'
        if st and not sh.get('amb') and len(sig(sh['q'][0])) >= 2: return 'v'
        if not hd and (cast or not single) and len(low) < 160 and (TAPE2.search(low) or (tape and not mod and (inrun or cast or cols & TVSET))): return 'b'
        return False
    if strong or cast: return 't'
    if weak and (not mod or dev or st): return 't'
    if st: return 't' if not mod else 'v'
    return False
def fcons(sh, it):
    t = flat(it.get('title')); low = clean(t)
    if not t or NONLAT.search(t) or JUNK.search(low) or FOREIGN.search(low) or SPIN.search(low): return False
    if sh.get('junk') and re.search(sh['junk'], low): return False
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return False
    if MOD2.search(t): return False
    desc = flat(it.get('description')).lower(); subj = flat(it.get('subject')).lower()
    cols = set(it.get('collection') or []) if isinstance(it.get('collection'), list) else {it.get('collection')}
    blob = low + ' ' + clean(desc) + ' ' + subj + ' ' + clean(re.sub(r'[-_.]+', ' ', it.get('identifier') or ''))
    if JUNKD.search(desc) and not SE1.search(low): return False
    if not (SE1.search(blob) or seasons(low) or MULTI.search(blob) or ep_key(sh, low) or cols & TVSET or re.search(r'\bepisodes?\b', blob)): return False
    return 'f'
def named(sh, text):
    z = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', text))) + ' '
    return any((' ' + norm(q) + ' ') in z for q in sh['q'] + sh.get('alt', []))
def hd2(sh, text):
    return max(head(sh, text), head(dict(sh, q=sh['alt']), text) if sh.get('alt') else 0)
def fhead(sh, path):
    return max(hd2(sh, re.sub(r'\.(ia\.)?[a-z0-9]{2,4}$', '', part.lower())) for part in path.split('/'))
def amb1(sh): return bool(sh.get('amb')) and len(sig(sh['q'][0])) <= 1
def fcheck(sh, ident, files, real, text):
    g = EP.get(sh['title'])
    if not g or re.search(r'serieslan|latino|dublado|castellano', ident.lower()): return None
    one = len(files) <= 2; hit = []
    for f in files:
        b = clean(f[0].rsplit('/', 1)[-1])
        if FOREIGN.search(b) or re.search(r'\b(hun|hungarian|dubbed)\b', b) or SPIN.search(clean(f[0])): continue
        v = file_se(sh, b) or (file_se(sh, real) if one else None)
        if v and v in g['d']: hit.append(f)
    if not hit: return None
    ds = sorted(f[1] for f in hit); med = ds[len(ds) // 2]
    if not 900 <= med <= 6000: return None
    need = 2 if amb1(sh) else 1
    if sum(1 for f in hit if fhead(sh, f[0]) >= need) * 2 >= len(hit): return 'name'
    if hd2(sh, real) >= need or hd2(sh, re.sub(r'[-_.]+', ' ', ident)) >= need: return 'name'
    if one and any((' ' + norm(q) + ' ') in (' ' + norm(clean(real)) + ' ') for q in sh['q']) and ep_key(sh, clean(real)) and (med <= 2100 or TAPE.search(clean(real))): return 'name'
    keys = {ep_key(sh, clean(f[0].rsplit('/', 1)[-1])) for f in hit} - {None}
    if len(keys) >= 2 and len(keys) * 2 >= len(hit) and named(sh, text) and sum(1 for f in hit if named(sh, f[0])) * 2 < len(hit): return 'episode titles'
    return None
def fv_ok(sh, x):
    t = x.get('t') or ''
    if sh.get('junk') and re.search(sh['junk'], clean(t)): return None
    if t.startswith(sh['title'] + ' - '): t = t[len(sh['title']) + 3:]
    return fcheck(sh, x['i'], x['f'], t, (x.get('ds') or '') + ' ' + (x.get('s') or ''))
OTHN = sorted({norm(q) for s in SHOWS for q in s['q'] if len(norm(q)) >= 4}, key=len, reverse=True)
OTHR = re.compile(r'^(?:the )?(' + '|'.join(re.escape(o) for o in OTHN) + r') (?:s\d|season \d|\d{1,2}x\d)')
def other_show(sh, name):
    m = OTHR.match(norm(clean(name.rsplit('/', 1)[-1])))
    return bool(m) and m.group(1) not in {norm(q) for q in sh['q']} and not any(norm(q).startswith(m.group(1)) for q in sh['q'])
def desc_eps(sh, x, d):
    g = EP.get(sh['title'])
    if not g: return []
    t = x['t']; z = ' ' + norm0(clean(t + ' . ' + d)) + ' '
    tight = head(sh, t) == 2 and not re.search(r'[|/;]', t)
    names = [norm0(q) for q in sh['q']]; out = set()
    for k, v in g['t']:
        p = z.find(' ' + k + ' ')
        while p >= 0:
            nx = z[p + len(k) + 2:].split(' ')[0]
            if not re.fullmatch(r'[ivx]+|\d{1,2}', nx or '-') and (tight or any(n in z[max(0, p - 120):p] for n in names)): out.add(v); break
            p = z.find(' ' + k + ' ', p + 1)
    if tight:
        for m in SE1.finditer(clean(t + ' . ' + d)):
            v = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
            if v in g['d']: out.add(v)
    if len(out) > sum(f[1] for f in x['f']) / 1200 + 1: return []
    return ['S%02dE%02d' % v for v in sorted(out)]
def load_old():
    F = os.path.join(OUT, 'primetime.json.gz')
    if not os.path.exists(F): return [], []
    keep, drop = [], []
    for x in json.load(gzip.open(F, 'rt', encoding='utf-8')):
        sh = BYT.get(x.get('k'))
        if sh and x.get('fv'):
            if fv_ok(sh, x): keep.append(x)
            else: drop.append(x)
            continue
        r = sh and consider(sh, {'title': x.get('t'), 'collection': x.get('c'), 'subject': x.get('s'), 'description': x.get('ds'), 'date': '' if x.get('ad') else x.get('d')}, 'd' if x.get('r') == 'd' else 't')
        if r in ('b', 'd'): x['r'] = r
        if not r: drop.append(x); continue
        if not post_ok(sh, x): maybe(x, 'files shorter than a normal episode')
        if r == 'v' and not verify(sh, x): maybe(x, 'show match not verified by cast, description or episode lengths')
        keep.append(x)
    return keep, drop
def plan():
    have = load_have(); keep, drop = load_old()
    mine = {x['i'] for x in keep}
    for x in keep: have.add(x['i'])
    print('have', len(have), 'shows', len(SHOWS), 'old kept', len(keep), 'old dropped', len(drop), flush=True)
    def one(sh):
        res = {}
        for q in sh['q']:
            ph = q.replace('"', '')
            base = 'mediatype:movies AND title:("%s")' % ph
            qs = [(base + ' AND (' + DISQ + ' OR collection:(' + TVCOL + '))', 't')] if len(sig(q)) <= 1 else [(base, 't')]
            if len(sig(q)) > 1 or sh.get('must'): qs.append(('mediatype:movies AND subject:("%s")' % ph, 't'))
            if sh.get('must'):
                extra = ' AND (' + ' OR '.join('"%s"' % c for c in sh['cast'][:4]) + ' OR nbc OR cbs OR abc OR fox OR sitcom)' if len(sig(q)) <= 1 and sh.get('cast') else ''
                qs.append(('mediatype:movies AND description:("%s")%s AND (collection:(%s) OR title:(vhs OR tape OR commercials OR nbc OR cbs OR abc OR fox OR upn OR wb OR recorded))' % (ph, extra, TVCOL), 'd'))
            if sh.get('guide') and q == sh['q'][-1] and sh.get('extra'): qs += [('mediatype:movies AND title:("%s")' % e, 't') for e in sh['extra']]
            if sh.get('must'):
                ws = norm(q).split(); pre = []
                for sep in ('-', '_', '.', ''):
                    slug = sep.join(ws)
                    if len(sig(q)) <= 1 or generic(sh): pre += [slug + a + b for a in sorted({sep, '-', '_', ''}) for b in ('s0', 's1', 'season', 'complete', 'tv', 'vhs', 'dvd', '19', '20')]
                    else: pre.append(slug)
                qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(x + '*' for x in sorted(set(pre))) + ')', 'i'))
            if sh.get('guide'):
                ws = norm(q).split()
                extra = ' AND (' + ' OR '.join('"%s"' % c for c in sh['cast'][:5]) + (' OR season OR episode OR episodes OR sitcom OR ' + sh['net'] if sh['guide'] == 1 else '') + ')' if len(sig(q)) <= 1 and sh.get('cast') else ''
                qs.append(('mediatype:movies AND "%s"%s AND NOT title:("%s")' % (ph, extra, ph), 'f'))
                qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(sorted({sep.join(ws) + '*' for sep in ('-', '_', '.', '')})) + ') AND NOT title:("%s")' % ph, 'f'))
                qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(sorted({'*' + sep.join(ws) + '*' for sep in ('-', '_', '')})) + ') AND NOT title:("%s")' % ph, 'f'))
                if q == sh['q'][0]: qs += [('mediatype:movies AND title:("%s")' % a, 'f') for a in sh.get('alt', [])]
            for qq, route in qs:
                hits = scrape(qq); st = [len(hits), 0, 0, 0]
                if sh.get('guide'): DIAG[sh['title']].append((route, qq[:150], st))
                for it in hits:
                    i = it.get('identifier')
                    if not i or i in res: continue
                    if i in mine: st[1] += 1; continue
                    if i in have and not (sh.get('guide') == 1 and route in ('t', 'f')): st[2] += 1; continue
                    if route == 'f':
                        try: r = fcons(sh, it)
                        except Exception as e: print('skip', i, e); r = False
                        if r:
                            if not named(sh, flat(it.get('title'))): it = dict(it, title=(sh['title'] + ' - ' + flat(it.get('title')))[:200], pt=1)
                            res[i] = (it, 'f'); st[3] += 1
                        elif sh.get('guide') and i not in have: DREJ[sh['title']].append((it.get('downloads') or 0, 'f', i, flat(it.get('title'))[:90]))
                        continue
                    if route == 'i':
                        if any((' ' + norm(z) + ' ') in (' ' + norm(clean(flat(it.get('title')))) + ' ') for z in sh['q']): continue
                        it = dict(it, title=(sh['title'] + ' - ' + flat(it.get('title')) + ' (' + re.sub(r'[-_.]+', ' ', re.sub(r'[-_.]?20[012]\d[01]\d[0-3]\d([-_]\d+)*$', '', i)).strip() + ')')[:200], pt=1)
                    try: r = consider(sh, it, 't' if route == 'i' else route)
                    except Exception as e: print('skip', i, e); r = False
                    if r: res[i] = (it, r); st[3] += 1
                    elif sh.get('guide') and i not in have: DREJ[sh['title']].append((it.get('downloads') or 0, route, i, flat(it.get('title'))[:90]))
        return sh, res
    DIAG = collections.defaultdict(list); DREJ = collections.defaultdict(list)
    seen = {}; per = collections.Counter(); perd = collections.Counter(); peri = collections.Counter()
    order = sorted(SHOWS, key=lambda s: (0 if s.get('must') else 1, -len(s['title'])))
    if FOCUS: order = [s for s in order if s['title'].lower() in FOCUS or ('guide' in FOCUS and s.get('guide')) or ('must' in FOCUS and s.get('must'))]
    with ThreadPoolExecutor(6) as ex:
        for sh, res in ex.map(one, order):
            for i, (it, r) in res.items():
                if i in seen:
                    if seen[i]['r'] == 't' or r != 't': continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': sh['title'], 'net': sh['net'], 'kind': sh['kind'], 'first': sh['first'], 'last': sh['last'], 'must': 1 if sh.get('must') else 0, 'r': r}
                if it.get('pt'): seen[i]['pt'] = it['title']; peri[sh['title']] += 1
                if r == 't': per[sh['title']] += 1
                else: perd[sh['title']] += 1
    ups = collections.defaultdict(set); src = [x for x in keep if BYT[x['k']].get('guide') == 1 and (x.get('fv') or len(x.get('se') or []) >= 5)]
    def upl(x):
        j = get('https://archive.org/metadata/' + urllib.parse.quote(x['i']) + '/metadata') or {}
        return x['k'], flat((j.get('result') or {}).get('uploader'))
    with ThreadPoolExecutor(8) as ex:
        for k, u in ex.map(upl, src):
            if u and '@' in u: ups[u].add(k)
    nup = 0
    for n, (u, ks) in enumerate(sorted(ups.items())):
        hits = scrape('mediatype:movies AND uploader:("%s")' % u, 6000); acc = 0
        for it in hits:
            i = it.get('identifier')
            if not i or i in seen or i in mine: continue
            for k in sorted(ks):
                sh = BYT[k]
                try: r = fcons(sh, it)
                except Exception: r = False
                if r:
                    t = flat(it.get('title'))
                    seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k, 'net': sh['net'], 'kind': sh['kind'], 'first': sh['first'], 'last': sh['last'], 'must': 1, 'r': 'f', 'up': 1}
                    if not named(sh, t): seen[i]['pt'] = (k + ' - ' + t)[:200]
                    acc += 1; nup += 1; break
        print('UPLOADER', n, sorted(ks), 'items', len(hits), 'candidates', acc, flush=True)
    print('uploader candidates', nup, 'from', len(ups), 'uploaders of', len(src), 'items', flush=True)
    nrf = 0
    for x in keep:
        sh = BYT[x['k']]
        if (sh.get('must') or sh.get('guide')) and x['i'] not in seen and (60 <= len(x['f']) < min(x.get('nf') or 9999, 500) or (sh['title'] in EP and len(x['f']) <= 2 and not x.get('se') and not x.get('epx') and sum(f[1] for f in x['f']) >= 2400)):
            seen[x['i']] = {'identifier': x['i'], 'downloads': x.get('dl') or 0, 'k': sh['title'], 'net': sh['net'], 'kind': sh['kind'], 'first': sh['first'], 'last': sh['last'], 'must': 1 if sh.get('must') else 0, 'r': x.get('r', 't'), 'rf': 1}; nrf += 1
    print('refresh', nrf, flush=True)
    c = sorted(seen.values(), key=lambda x: (-x['must'], x['r'] != 't', -x['downloads']))
    print('candidates', len(c), 'title', sum(1 for x in c if x['r'] == 't'), 'tape', sum(1 for x in c if x['r'] != 't'), flush=True)
    for sh in SHOWS:
        if sh.get('must'): print('MUSTCAND', per[sh['title']], perd[sh['title']], peri[sh['title']], sh['title'])
    for k, n in per.most_common(60): print('  cand', n, k)
    for k in DIAG:
        for route, qq, st in DIAG[k]: print('DIAGQ', k, '|', route, '| hits %d mine %d elsewhere %d accepted %d |' % tuple(st), qq)
        for dl, route, i, t in sorted(set(DREJ[k]), reverse=True)[:70]: print('DIAGREJ', k, '|', route, '|', dl, '|', i, '|', t)
    json.dump(c, gzip.open(os.path.join(PARTS, 'cands.json.gz'), 'wt', encoding='utf-8'), separators=(',', ':'))
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def airdate(t):
    m = re.search(r'\b(19[89]\d|200[0-4])[-./ ](\d{1,2})[-./ ](\d{1,2})\b', t)
    if m and 1 <= int(m.group(2)) <= 12: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./](19[89]\d|200[0-4]|[89]\d)\b', t)
    if m and 1 <= int(m.group(1)) <= 12:
        y = int(m.group(3)); y = y + 1900 if y < 100 else y
        return '%d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', t.lower())
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(1)], int(m.group(2)))
    return ''
def post_ok(sh, x):
    ds = [f[1] for f in x['f']]
    if not ds: return False
    if x.get('q') == 'prime' and sh['kind'] in ('sitcom', 'drama') and x.get('r', 't') == 't':
        if sorted(ds)[len(ds) // 2] < 600: return False
        if len(ds) == 1 and ds[0] < 1080: return False
    return True
REJ = collections.Counter(); REJS = collections.defaultdict(list)
def rej(c, why):
    REJ[why] += 1
    if c.get('must'):
        REJ[(c['k'], why)] += 1
        if len(REJS[(c['k'], why)]) < 6: REJS[(c['k'], why)].append(c['identifier'])
    return None
def meta(c):
    if BUDGET and time.time() - T0 > BUDGET: return rej(c, 'budget')
    j = get('https://archive.org/metadata/' + urllib.parse.quote(c['identifier']))
    if not j or not j.get('files'): return rej(c, 'nometa')
    if j.get('is_dark'): return rej(c, 'dark')
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return rej(c, 'restricted')
    lang = flat(m.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return rej(c, 'lang')
    cap = 60 if c.get('must') else 30; hb = 0; nomp4 = sum(1 for f in j['files'] if re.search(r'\.(mkv|avi|mpg|mpeg|m4v|mov|ts|vob|iso|ogv|webm)$', f.get('name', '').lower()))
    groups = {}; alt = {}; fmts = collections.Counter(); est = 0
    lenby = {f.get('name'): secs(f.get('length')) for f in j['files'] if secs(f.get('length') or 0) > 0}
    for f in j['files']:
        if f.get('original') and secs(f.get('length') or 0) > 0: lenby.setdefault(f['original'], secs(f['length']))
    for f in j['files']:
        n = f.get('name', '').lower()
        if n.endswith(('.mp4', '.m4v')):
            key = f.get('original') if f.get('source') == 'derivative' else f['name']
            groups.setdefault(key, []).append(f); fmts[f.get('format', '')] += 1
        elif n.endswith(('.mkv', '.mov', '.webm')) and f.get('source') != 'derivative': alt[f['name']] = f
    files = []; hbf = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 5)); b = g[0]
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0)) or lenby.get(key, 0)
        sz = float(b.get('size') or 0)
        if not d and sz >= 4e7 and c.get('must'): d = min(7200, max(1200, sz / 1e6 / 5 * 60)); est += 1
        if d < 240: continue
        if sz and sz / 1e6 / (d / 60) > cap: hbf.append([b['name'], round(d), b.get('format', '')]); continue
        if sz and sz / 1e6 / (d / 60) > 30: c['hb'] = 1
        files.append([b['name'], round(d), b.get('format', '')])
    why = ''
    if not files and hbf: files = hbf; c['hb'] = 2; why = 'very high bitrate files only'
    if not files and alt:
        for n, f in alt.items():
            if n in groups: continue
            d = secs(f.get('length') or 0)
            if d >= 240: files.append([n, round(d), f.get('format', '')])
        if files: why = 'no mp4; mkv/mov/webm originals only (may not play in every browser)'
    if est and not why: why = 'running time missing from the listing; estimated from file size'
    if not files:
        if fmts: REJ['fmt ' + ' / '.join(sorted(fmts))[:80]] += 1
        if BYT[c['k']].get('guide'): print('NOFILES', c['k'], '|', c['identifier'], '|', len(j['files']), sorted(collections.Counter(f.get('name', '').rsplit('.', 1)[-1].lower()[:6] for f in j['files']).items()), [(f.get('name', '')[-40:], f.get('format'), f.get('length'), f.get('size')) for f in j['files'] if f.get('name', '').lower().endswith(('.mp4', '.m4v', '.mkv', '.avi', '.mpg', '.mpeg', '.iso', '.vob', '.ts', '.wmv', '.flv', '.rm', '.zip', '.rar', '.7z'))][:4], flush=True)
        return rej(c, 'nomp4_other' if nomp4 else 'nofiles')
    if sum(f[1] for f in files) < 900: return rej(c, 'short')
    files.sort(key=lambda f: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', f[0])])
    sh = BYT[c['k']]; fwhy = ''
    if c.get('r') == 'f':
        fwhy = fcheck(sh, c['identifier'], files, flat(m.get('title')), flat(m.get('description')) + ' ' + flat(m.get('subject')))
        if not fwhy: return rej(c, 'files do not match the episode guide')
        c = dict(c, r='t')
        if not named(sh, flat(m.get('title'))): c['pt'] = (sh['title'] + ' - ' + flat(m.get('title')))[:200]
        else: c.pop('pt', None)
    t = c.get('pt') or flat(m.get('title'))[:200]; desc = ' '.join(flat(m.get('description')).split())[:400]
    x = {'i': c['identifier'], 'q': KMAP.get(c['kind'], 'prime'), 't': t, 'd': '', 'y': '', 'c': [], 's': flat(m.get('subject')).replace(' ', ' ')[:200], 'ds': desc, 'f': files[:500 if sh.get('guide') or sh.get('must') else 60], 'dl': c.get('downloads') or 0, 'k': c['k'], 'e': 0, 'net': c['net'], 'ad': '', 'r': c.get('r', 't'), 'nf': len(files)}
    col = m.get('collection', []); x['c'] = ([col] if isinstance(col, str) else col)[:4]
    x['d'] = flat(m.get('date'))
    if c.get('hb'): x['hb'] = c['hb']
    if why: maybe(x, why)
    if fwhy: x['fv'] = 1
    if fwhy and fwhy != 'name': maybe(x, 'show identified from ' + fwhy + ' only')
    if x['r'] == 'v':
        if not verify(sh, x): maybe(x, 'show match not verified by cast, description or episode lengths'); rej(c, 'verify_kept')
        x['r'] = 't'
    if not stamp(sh, x): return rej(c, 'stamp')
    if not post_ok(sh, x): maybe(x, 'files shorter than a normal episode'); rej(c, 'postok_kept')
    allf = list(x['f'])
    tag(sh, x)
    if sh.get('guide') and not x['f']: x['f'] = allf[:60]; maybe(x, 'no file matched the episode guide'); rej(c, 'tagempty_kept')
    if sh.get('guide') and len(x['f']) <= 2 and not x.get('se'):
        eps = desc_eps(sh, x, ' '.join(flat(m.get('description')).split())[:6000]); x['epx'] = 1
        if eps: x['eps'] = eps
    return x
def maybe(x, why):
    x['keep'] = 'maybe'; x['why'] = (x.get('why') + '; ' if x.get('why') and why not in x['why'] else '') + why if not (x.get('why') and why in x['why']) else x['why']
def tag(sh, x):
    g = EP.get(sh['title'])
    if not g: return
    one = len(x['f']) <= 2; se = []; keep = []; sn = x.get('sn') or one_season(clean(x['t']))
    loose = amb1(sh) and not (head(sh, x['t']) == 2 or seg(sh, x['t']))
    qs = [norm(q) for q in sh['q']]
    rows = []
    for f in x['f']:
        v = file_se(sh, f[0]) or (file_se(sh, x['t']) if one else None)
        if not v and sn and f[1] < 2400:
            m = re.search(r"(?:\bepisode|\bep|\be)\.?\s?(\d{1,2})\b|^\D{0,3}(\d{1,2})\b", clean(f[0].rsplit('/', 1)[-1]))
            base = norm(clean(f[0].rsplit('/', 1)[-1].rsplit('.', 1)[0]))
            if m and (any(q in base for q in qs) or re.match(r'(s\d{1,2} ?)?(episode|ep|e)? ?\d{1,2}\b', base)): v = (sn, int(m.group(1) or m.group(2)))
        if v and loose and fhead(sh, f[0]) < 2 and not ep_key(sh, clean(f[0].rsplit('/', 1)[-1])): v = None
        if sh.get('fjunk') and re.search(sh['fjunk'], clean(f[0])): continue
        if other_show(sh, f[0]): continue
        rows.append((f, v))
    anyv = any(v and v in g['d'] for f, v in rows)
    for f, v in rows:
        if v and v[0] > g['maxs']: continue
        if anyv and len(rows) > 2 and not (v and v in g['d']) and not any(q in norm(clean(f[0])) for q in qs): continue
        keep.append(f)
        if v and v in g['d']: se.append([len(keep) - 1, 'S%02dE%02d' % v, g['d'][v]])
    if sh.get('strictg') and not anyv and len(rows) > 2 and not any(any(q in norm(clean(f[0])) for q in qs) for f, v in rows): keep = []
    x['f'] = keep
    if se:
        x['se'] = se; y = int(min(r[2] for r in se)[:4])
        if 1984 <= y <= 2004 and not x.get('ad'): x['e'] = y; x['y'] = str(y)
        if len(keep) == 1 and not x.get('ad'): x['ad'] = se[0][2]; x['d'] = se[0][2]
    else: x.pop('se', None)
def stamp(sh, x):
    t = x['t']; low = clean(t)
    ad = airdate(t) or airdate((x.get('ds') or '')[:200])
    if ad and not (sh['first'] <= int(ad[:4]) <= sh['last'] + 1): ad = ''
    sn = one_season(low) if x.get('r', 't') == 't' else 0
    ys = [int(y) for y in YR.findall(t) if sh['first'] <= int(y) <= sh['last'] and 1984 <= int(y) <= 2004]
    dy = re.match(r'(\d{4})', '' if x.get('ad') and not ad else (x.get('d') or ''))
    dy = int(dy.group(1)) if dy and sh['first'] <= int(dy.group(1)) <= sh['last'] and 1984 <= int(dy.group(1)) <= 2004 else 0
    if ad: e = int(ad[:4])
    elif sn and start(sh) + sn - 1 <= sh['last'] + 1: e = min(start(sh) + sn - 1, sh['last'])
    elif ys: e = ys[0]
    elif dy: e = dy
    else: e = max(sh['first'], 1984) if sh['last'] >= 1984 else 0
    if not e or e > 2004: return False
    e = max(e, 1984)
    if ad: x['d'] = ad
    x['ad'] = ad; x['e'] = e; x['y'] = str(e)
    if sn: x['sn'] = sn
    else: x.pop('sn', None)
    return True
def run_meta():
    c = json.load(gzip.open(os.path.join(PARTS, 'cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'items', len(c), flush=True); res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, c)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), flush=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'pt-%d.json.gz' % SHARD), 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res))
    print('REJ', sorted((k, v) for k, v in REJ.items() if isinstance(k, str)))
    for k, v in sorted(((k, v) for k, v in REJ.items() if not isinstance(k, str)), key=lambda kv: -kv[1])[:160]: print('REJSHOW', v, k[0], '|', k[1], '|', ' '.join(REJS[k]))
def merge():
    F = os.path.join(OUT, 'primetime.json.gz')
    keep, drop = load_old()
    rawids = {x['i'] for x in json.load(gzip.open(os.path.join(OUT, 'raw.json.gz'), 'rt', encoding='utf-8')) if isinstance(x, dict)} if os.path.exists(os.path.join(OUT, 'raw.json.gz')) else set()
    print('old in raw dropped', sum(1 for x in keep if x['i'] in rawids))
    keep = [x for x in keep if x['i'] not in rawids or x.get('sup')]
    for x in keep: stamp(BYT[x['k']], x)
    mine = {x['i'] for x in keep}; have = mine | load_have(); add = []; old = {x['i']: n for n, x in enumerate(keep)}; nref = 0
    got2 = collections.defaultdict(set); discs = collections.defaultdict(set)
    R = collections.defaultdict(lambda: [0, 0, 0])
    keys = [(sh, [' ' + norm(q) + ' ' for q in sh['q']]) for sh in SHOWS]
    seenr = set()
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))):
        if p.endswith('primetime.json.gz') or p.endswith('ads.json.gz'): continue
        try: rows = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        for x in rows:
            if not isinstance(x, dict) or x.get('i') in seenr or not x.get('f'): continue
            nt = ' ' + norm(clean(x.get('t', ''))) + ' '
            for sh, qs in keys:
                if any(q in nt for q in qs) and consider(sh, {'title': x.get('t'), 'collection': x.get('c'), 'subject': x.get('s'), 'description': x.get('ds'), 'date': ''}) == 't':
                    if sh.get('guide') and sh['title'] in EP:
                        for f in x['f']:
                            w = file_se(sh, f[0]) or (file_se(sh, x.get('t', '')) if len(x['f']) <= 2 else None)
                            if w and w in EP[sh['title']]['d']: got2[sh['title']].add('S%02dE%02d' % w)
                    seenr.add(x['i']); v = R[sh['title']]; v[0] += 1; v[1] += len(x['f']); v[2] += sum(f[1] for f in x['f'] if len(f) > 1 and isinstance(f[1], (int, float)))
                    break
    for p in sorted(glob.glob(os.path.join(PARTS, 'pt-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] in old and x.get('epx') and not keep[old[x['i']]].get('epx'):
                keep[old[x['i']]]['epx'] = 1
                if x.get('eps'): keep[old[x['i']]]['eps'] = x['eps']
            if x['i'] in old and len(x['f']) > len(keep[old[x['i']]]['f']):
                o = keep[old[x['i']]]
                for kk in ('t', 'r', 'sup', 'fv'):
                    if kk in o: x[kk] = o[kk]
                keep[old[x['i']]] = x; nref += 1
            if x['i'] in mine: continue
            if x['i'] in have:
                if BYT[x['k']].get('guide') != 1: continue
                x['sup'] = 1
            have.add(x['i']); mine.add(x['i']); add.append(x)
    allx = keep + add
    for x in allx:
        if BYT[x['k']].get('guide'):
            f0 = list(x['f']); tag(BYT[x['k']], x)
            if not x['f'] and f0: x['f'] = f0[:60]; maybe(x, 'no file matched the episode guide')
    allx = [x for x in allx if x['f']]
    print('kept as maybe', sum(1 for x in allx if x.get('keep') == 'maybe'), sorted(collections.Counter(x.get('why') for x in allx if x.get('keep') == 'maybe').items(), key=lambda kv: -kv[1])[:8])
    if not allx: print('nothing to write'); return
    json.dump(allx, gzip.open(F, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    hrs = lambda xs: round(sum(sum(f[1] for f in x['f']) for x in xs) / 3600)
    print('old kept', len(keep), 'old purged', len(drop), 'refreshed', nref, 'added', len(add), 'total', len(allx), 'hours', hrs(allx))
    print('== PURGED per show')
    for k, n in collections.Counter(x['k'] for x in drop).most_common(): print('PURGED', n, k)
    for x in drop[:400:8]: print('PURGEDSAMPLE', x['k'], '|', x['t'][:90])
    for x in allx:
        if x.get('fv'): print('FV', x['k'], '|', x['i'], '|', x['t'][:80], '|', len(x['f']), len(x.get('se') or []), '|', x.get('why') or '', '|', x['f'][0][0][-60:])
    print('per net', sorted(collections.Counter(x['net'] for x in allx).items()))
    print('per net hours', sorted((n, hrs([x for x in allx if x['net'] == n])) for n in set(x['net'] for x in allx)))
    print('per cat', sorted(collections.Counter(x['q'] for x in allx).items()))
    print('per year', sorted(collections.Counter(x['e'] for x in allx).items()))
    print('per season', sorted(collections.Counter(x.get('sn', 0) for x in allx).items()))
    print('routes', sorted(collections.Counter(x.get('r', 't') for x in allx).items()), 'exact dates', sum(1 for x in allx if x.get('ad')))
    T = collections.defaultdict(lambda: [0, 0, 0, 0, collections.Counter()])
    for x in allx:
        v = T[x['k']]
        if x.get('r', 't') == 't':
            v[0] += 1; v[1] += len(x['f']); v[2] += sum(f[1] for f in x['f'])
            if x.get('sn'): v[4][x['sn']] += len(x['f'])
        else: v[3] += 1
    print('== MUST table (flag | title | net | items | episode files | hours | tape items | other catalogs items | other catalogs files | other catalogs hours | seasons)')
    done = set()
    for s in SHOWS:
        if not s.get('must') or s['title'] in done: continue
        done.add(s['title']); v = T[s['title']]; r = R[s['title']]
        flag = 'FOUND' if v[1] + r[1] >= 20 else 'THIN' if v[1] or v[3] or r[1] else 'MISSING'
        print('MUST', flag, '|', s['title'], '|', s['net'], '|', v[0], '|', v[1], '|', round(v[2] / 3600, 1), '|', v[3], '|', r[0], '|', r[1], '|', round(r[2] / 3600, 1), '|', ' '.join('S%d:%d' % kv for kv in sorted(v[4].items())))
    for k, g in EP.items():
        got = collections.Counter(); tp = set()
        for x in allx:
            if x['k'] == k:
                for r in x.get('se', []): got[r[1]] += 1
                tp.update(x.get('eps') or [])
                if x.get('sn') and not x.get('se') and any(f[1] >= 3600 for f in x['f']): discs[k].add(x['sn'])
        bys = collections.defaultdict(list)
        for (a, b) in sorted(g['d']): bys[a].append(b)
        for z in got2[k]: got[z] += 0
        ntp = sum(1 for z in tp if not got[z] and z not in got2[k])
        for z in tp: got2[k].add(z)
        tot = sum(1 for (a, b) in g['d'] if got['S%02dE%02d' % (a, b)])
        both = sum(1 for (a, b) in g['d'] if got['S%02dE%02d' % (a, b)] or 'S%02dE%02d' % (a, b) in got2[k])
        print('== GUIDE', k, 'episodes tagged here', tot, 'with other catalogs and tape descriptions', both, 'only in tape descriptions', ntp, 'of', len(g['d']), 'disc packs for seasons', sorted(discs[k]))
        for a in sorted(bys):
            miss = [b for b in bys[a] if not got['S%02dE%02d' % (a, b)] and 'S%02dE%02d' % (a, b) not in got2[k]]
            print('GUIDESEASON', k, 'S%02d' % a, 'FOUND' if not miss else 'PARTIAL' if len(miss) < len(bys[a]) else 'DISCS' if a in discs[k] else 'MISSING', len(bys[a]) - len(miss), '/', len(bys[a]), 'missing', ' '.join(str(b) for b in miss))
    if GUIDE: json.dump(GUIDE, open(GH, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('== all shows with items (items files hours tape title)')
    for k, v in sorted(T.items(), key=lambda kv: -kv[1][1]): print('SHOW', v[0], v[1], round(v[2] / 3600, 1), v[3], BYT[k]['net'], BYT[k]['kind'], k)
    for net in ('nbc', 'cbs', 'abc', 'fox', 'wb', 'upn', 'syn'):
        print('== ZERO', net, ' ; '.join(sorted(set(s['title'] for s in SHOWS if s['net'] == net and s['title'] not in T and not R[s['title']][1]))))
        print('== ELSEWHERE ONLY', net, ' ; '.join(sorted(set('%s (%d)' % (s['title'], R[s['title']][1]) for s in SHOWS if s['net'] == net and s['title'] not in T and R[s['title']][1]))))
    random.seed(11)
    for x in random.sample(allx, min(60, len(allx))): print('SAMPLE', x['net'], x['e'], x.get('sn', '-'), x.get('r', 't'), x['k'], '|', x['t'][:80], '|', len(x['f']), sum(f[1] for f in x['f']) // 60)
{'plan': plan, 'meta': run_meta, 'merge': merge}[MODE]()
