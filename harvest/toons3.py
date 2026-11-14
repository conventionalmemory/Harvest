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
OUTF = os.path.join(OUT, 'toons3.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_toons3.json'), encoding='utf-8'))
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
BLK = {'title': 'Cartoon block', 'net': '', 'original_run': '1984-2004', 'q': 'kids', 'ct': 'block', 'block': True}
SHOWS.append(BLK)
for s in SHOWS:
    s['n'] = norm(s['alt'][0]) if '(' in s['title'] and s.get('alt') else norm(s['title'])
    s['qn'] = (s.get('alt', []) if '(' in s['title'] else [s['title']] + s.get('alt', []))
RQW = {s['title']: set(w for r in s.get('req', []) for w in norm(r).split()) for s in SHOWS}
BYT = {}
for s in SHOWS: BYT.setdefault(s['title'], s)
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > 40000: break
    return out
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblada|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|fran[cç]ais|french dub|vf|vostfr|italiano|ita|nederlands|svenska|norsk|dansk|suomi|polski|lektor|magyar|rom[aâ]n[aă]|t[uü]rk[cç]e|русск|hindi|tamil|telugu|urdu|arabic|bahasa|tagalog|sub ?esp|subtitulado|temporada|cap[ií]tulo|episodio|folge|staffel|saison|aflevering|odcinek|uk version|australian version|canadian version|bbc|itv|channel 4|sky one|rte)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|nes|snes|sega|genesis|playstation|ps[1-5]|xbox|game ?boy|dos game|pc game|cd-?rom|rom ?hack|emulator|pinball|board game|comic book|comics? scans?|novel|audiobook|audio book|ebook|pdf|soundtrack|ost|theme song|theme music|themes?|intro|intros|opening credits|closing credits|credits|bumper|bumpers|promo|promos|trailer|trailers|teaser|commercial|commercials|ad|ads|bloopers?|outtakes?|fan ?made|fan-?edit|fanfilm|fan film|amv|ytp|parody|spoof|abridged|review|reviews|reviewed|recap|podcast|reaction|commentary track|interview|panel|convention|comic-?con|q&a|tribute|retrospective|making of|behind the scenes|documentary about|radio|radio show|otr|old time radio|lp|vinyl|cassette|album|sheet music|script|screenplay|toys?|unboxing|figure|model kit|slideshow|screensaver|wallpaper|test|sample|clip|clips|scene|scenes|excerpt|highlights|supercut|compilation of|mashup|remix|music video|karaoke|cover|lyrics|xxx|porn|adult|hentai|nude)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(reboot|revival|remastered in|netflix|hulu|disney\+|paramount\+|hbo max|prime video|youtube|tiktok|twitch|livestream|zoom)\b"
CTXT = r"\b(episodes?|ep\.?|season|series|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv|television|vhs|betamax|broadcast|aired|airing|syndicat\w*|with commercials|woc|complete|pilot|part \d|19[4-9]\d|200[0-4]|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa network|nick at nite|tv land|a&e|discovery|sci-?fi|comedy central|cnn|espn|tnn|cmt|bet|mtv|vh1|qvc|hsn|lifetime|family channel)\b"
CTXQ = '(subject:(tv OR television OR "tv show" OR "tv series" OR sitcom OR episode OR episodes OR series OR vhs OR broadcast OR "classic tv") OR title:(episode OR episodes OR season OR tv OR series OR vhs OR complete OR pilot OR s01 OR s02 OR s03 OR 1984 OR 1985 OR 1986 OR 1987 OR 1988 OR 1989 OR 1990 OR 1991 OR 1992 OR 1993 OR 1994 OR 1995 OR 1996 OR 1997 OR 1998 OR 1999 OR 2000 OR 2001 OR 2002 OR 2003 OR 2004) OR collection:(classic_tv OR television OR classic_tv_1950s OR classic_tv_1960s OR classic_tv_1970s OR classic_tv_1980s OR classic_tv_1990s OR vhsvault OR vhstvshows OR television_inbox))'
def core(t):
    s = norm(t)
    for _ in range(4):
        s2 = re.sub(r'^(the|a|new|all new|classic|vhs|tv|dvd|beta|tape|recording|\d{1,4}|[wk][a-z]{2,3}( tv)?( \d+)?|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|tnn|cmt|bet|mtv|vh1|cnn|espn|a and e|lifetime|discovery) ', '', s)
        if s2 == s: break
        s = s2
    return s
X_ESSAY = r"\b(secret galaxy|the history of|history of the|the failure of|untold history|a rant|rant on|annotated|nerdist|opening and closing|opening to|closing to|score suite|ai upscale[d]?|4k ai|colon movie|movie film for theaters|w/ commentary|with commentary|reacts?|my reaction|guide to|explained|ranked|ranking|top \d+|every episode|iceberg|lost media|analysis|video essay|parte|ilustre|vs the world|for pb|iso files?|dvd iso|bluray iso|\[iso\])\b"
BRIT = r'\b(bbc|itv|channel 4|sky one|rte|uk version)\b'
NAMES = sorted(set(n.lower() for s0 in SHOWS for n in s0['qn']), key=lambda n: -len(n))
NAMERX = re.compile('|'.join(re.escape(n) for n in NAMES))
X_ADULT = r"\b(south park|family guy|beavis|butt-?head|duckman|aqua teen|cowboy bebop|trigun|ninja scroll|hentai|amv|abridged|ytp|youtube poop|fandub|fan dub|parody|creepypasta|theory|goanimate|vyond)\b"
BLKRX = r"\b(saturday morning|sat\.? ?am cartoons|fox kids|kids'? ?wb|disney afternoon|one saturday morning|cartoon express|toonami|cartoon network|nicktoons|nickelodeon|after ?school cartoons|weekday cartoons|cartoon block|cartoons? with commercials|tnbc|abc kids|cbs kids|nbc saturday|usa cartoon)\b"
BLKCTX = r"\b(commercials|woc|w/c|vhs|recorded|recording|aired|airing|broadcast|block|bumpers?|tape)\b"
def blk_ok(t):
    low = t.lower()
    return bool(re.search(BLKRX, low) and re.search(BLKCTX, low) and re.search(r'(?<!\d)(198[4-9]|199\d|200[0-4])(?!\d)|(?<!\d)\d{1,2}[./-]\d{1,2}[./-](8[4-9]|9\d|0[0-4])(?!\d)', low) and not re.search(X_ADULT, low) and not re.search(X_FOR, low) and not re.search(r'(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|adult swim|commercials only|only commercials|commercial (break|block|compilation)s?( only)?$|bumpers only|promos only', low))
def ok_title(t, brit=False):
    if not t: return False
    low = t.lower() + ' '
    if re.search(X_ADULT, low): return False
    low = re.sub(r'(with|w/|w|incl\.?|including|original) ?(original |the )?(commercials?|ads)|commercials included|adult swim', ' ', low)
    low = NAMERX.sub(' ', low.replace('_', ' '))
    if re.search(X_ESSAY, low): return False
    if brit: low = re.sub(BRIT, ' ', low)
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    return True
EPCTX = r"\b(episodes?|ep\.? ?\d+|seasons?|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv series|tv show|complete series|the series|pilot|sitcom|with commercials|woc|syndicat\w*)\b"
SEPW = r'^(\d+|s\d+e?\d*|ep\d*|e\d+|episodes?|season|seasons|series|complete|pilot|part|pt|vol|volume|disc|tape|vhs|dvd|tv|show|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|gsn|aande|woc|with|w|19\d\d|200[0-4])$'
def match(show, title):
    if show.get('block'): return blk_ok(title)
    if show.get('x') and re.search(show['x'], title.lower()): return False
    if show.get('loose'):
        nt0 = ' ' + norm(title) + ' '
        return any((' ' + h + ' ') in nt0 for h in [norm(a) for a in show['qn']])
    amb = set(norm(a) for a in show.get('ambalt', []))
    names = [norm(a) for a in show['qn']]
    nt = ' ' + norm(title) + ' '
    c = core(title); low = title.lower()
    for hit in names:
        if (' ' + hit + ' ') not in nt: continue
        if hit not in amb and (not show.get('ambiguous') or hit != show['n']) and (len(hit.split()) >= 2 or len(hit) >= 9): return True
        sn = re.sub(r'^(the|a) ', '', hit)
        c2 = c if (c.startswith(sn + ' ') or c == sn) else re.sub(r'^(the|a) ', '', nt.strip())
        if not c2.startswith(sn + ' ') and c2 != sn: continue
        rest = c2[len(sn):].strip()
        if not rest: return True
        if re.match(SEPW, rest.split()[0]) or rest.split()[0] in RQW.get(show['title'], ()) or rest.split()[0] in ('mtv', 'nick', 'nickelodeon', 'upn', 'wb', 'tnt', 'toonami', 'snick', 'animated', 'cartoon', 'full'): return True
        last = sn.split()[-1]; i = low.find(last)
        tail = low[i + len(last):] if i >= 0 else 'x'
        if tail.startswith('..') or re.match(r"^['!?.)]*\s*[-–:|(\[#]", tail): return True
    return False
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio'}
def keep(x):
    s = BYT.get(x['k'])
    if not s: return False
    if s.get('block'): return blk_ok(x['t'])
    if x.get('via') == 'ep':
        b0 = ' ' + norm(x['t'] + ' ' + x.get('s', '') + ' ' + x.get('ds', '')) + ' '
        if not ok_title(x['t']) or (s.get('x') and re.search(s['x'], x['t'].lower())): return False
        return any((' ' + h + ' ') in b0 for h in [norm(a) for a in s['qn']])
    if not ok_title(x['t'], s.get('brit')) or not match(s, x['t']): return False
    if s.get('ct') == 'anime' or s.get('net') in ('cn',):
        b1 = (x['t'] + ' ' + x.get('s', '') + ' ' + x.get('ds', '')).lower()
        if re.search(r'\b(subbed|subtitled|english sub|eng sub|\bsubs?\b|raw|japanese audio|jpn|jap audio|original japanese)\b', b1) and not re.search(r'\b(dub|dubbed|english audio|dual audio)\b', b1): return False
    if s.get('req'):
        blob = (x['t'] + ' ' + x.get('s', '') + ' ' + x.get('ds', '') + ' ' + str(x.get('d', ''))[:4] + ' ' + str(x.get('y', ''))).lower()
        if not any(r in blob for r in s['req']): return False
    my = re.match(r'(\d{4})', str(x.get('y') or x.get('d') or ''))
    oy = [int(v) for v in re.findall(r'\d{4}', s.get('original_run', ''))]
    if my and oy and 1900 <= int(my.group(1)) <= 2004 and int(my.group(1)) < oy[0] - 1 and not re.search(r'(?<!\d)(19[6-9]\d|200[0-4])(?!\d)', x['t']): return False
    if set(x.get('c') or []) & XCOL: return False
    if re.match(r'^[a-z]{4,10}-[A-Z]', x['i']) and not re.search(r'(19[4-9]\d|200[0-4])', x['t']): return False
    dy = re.match(r'(\d{4})', str(x.get('d') or ''))
    if x['i'].startswith('youtube-') and dy and int(dy.group(1)) >= 2005 and not re.search(r'(19[4-9]\d|200[0-4])', x['t']): return False
    return True
def era(s, title, d, y):
    oy = [int(v) for v in re.findall(r'\d{4}', s.get('original_run', ''))]
    ys = [int(v) for v in re.findall(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', title)]
    m2 = re.search(r'(?<!\d)\d{1,2}[./-]\d{1,2}[./-]([89]\d|0[0-4])(?!\d)', title)
    if m2: ys.insert(0, (1900 if m2.group(1)[0] in '89' else 2000) + int(m2.group(1)))
    if not ys: ys = [int(v) for v in re.findall(r'^(19[89]\d|200[0-4])', str(d or '')[:4])] + [int(v) for v in re.findall(r'^(19[89]\d|200[0-4])', str(y or '')[:4])]
    lo = max(1984, oy[0] if oy else 1984); hi = min(2004, oy[-1] if len(oy) > 1 else 2004)
    ys = [v for v in ys if lo <= v <= hi]
    if ys: return ys[0]
    if oy and oy[0] >= 1984 and len(oy) > 1 and oy[-1] - oy[0] <= 2: return oy[0]
    return ''
def qtitle(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', t).split())
def allitems():
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))):
        n = os.path.basename(p)
        if n in ('dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'ads.json.gz', 'filler.json.gz', 'movies.json.gz', 'sports.json.gz', 'nick_guide.json.gz'): continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(L, list): continue
        for x in L:
            if isinstance(x, dict) and x.get('t'): yield x
def coverage(tag):
    idx = {}
    for k, s0 in enumerate(SHOWS):
        if s0.get('block'): continue
        for a in s0['qn']: idx.setdefault(norm(a), k)
    rx = re.compile(r'(?<![a-z0-9$])(' + '|'.join(re.escape(n) for n in sorted(idx, key=lambda n: -len(n))) + r')(?![a-z0-9$])')
    ci = collections.Counter(); cf = collections.Counter(); ch = collections.Counter()
    for x in allitems():
        nt = norm(x['t']); ks = set(idx[m.group(1)] for m in rx.finditer(nt))
        for k in ks:
            s0 = SHOWS[k]
            if not ok_title(x['t']) or not match(s0, x['t']): continue
            if s0.get('req'):
                blob = (x['t'] + ' ' + str(x.get('s', '')) + ' ' + str(x.get('ds', '')) + ' ' + str(x.get('d', ''))[:4]).lower()
                if not any(r in blob for r in s0['req']): continue
            fl = x.get('f') or []
            ci[k] += 1; cf[k] += len(fl); ch[k] += sum(f[1] for f in fl if isinstance(f, list) and len(f) > 1) / 3600
    print('COVERAGE', tag)
    st = collections.Counter()
    for k, s0 in enumerate(SHOWS):
        if s0.get('block'): continue
        flag = 'MISSING' if not ci[k] else 'THIN' if cf[k] < 15 else 'FOUND'; st[flag] += 1
        print('  %-8s %4d items %5d files %5d h  %-5s %s' % (flag, ci[k], cf[k], round(ch[k]), s0.get('net', ''), s0['title']))
    print('COVERAGE COUNTS', tag, dict(st), flush=True)
    return cf
if MODE == 'plan':
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(L, dict): have |= set(L); continue
        for x in L:
            if isinstance(x, dict):
                if x.get('i'): have.add(x['i'])
                ia = x.get('ia')
                if isinstance(ia, list) and ia and isinstance(ia[0], str): have.add(ia[0])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    print('known', len(have), 'shows', len(SHOWS), flush=True)
    COV = coverage('before')
    if os.environ.get('COVONLY'): sys.exit(0)
    def find(k):
        s = SHOWS[k]
        if s.get('block'):
            got = []
            for q in ('title:("saturday morning cartoons" OR "saturday morning" OR "fox kids" OR "kids wb" OR "disney afternoon" OR "one saturday morning" OR "cartoon express" OR "toonami" OR "after school cartoons" OR "weekday cartoons" OR "cartoon block" OR "cartoons with commercials" OR "nicktoons" OR "abc kids" OR "cbs kids" OR "tnbc")', 'subject:("saturday morning cartoons" OR "saturday morning" OR "fox kids" OR "kids wb" OR "disney afternoon" OR "toonami") AND (title:(commercials OR vhs OR recording OR broadcast OR block) OR description:("with commercials" OR "original commercials"))', 'description:("saturday morning cartoons" OR "fox kids" OR "kids wb" OR "disney afternoon") AND description:("commercials") AND title:(vhs OR tape OR recording OR 1984 OR 1985 OR 1986 OR 1987 OR 1988 OR 1989 OR 1990 OR 1991 OR 1992 OR 1993 OR 1994 OR 1995 OR 1996 OR 1997 OR 1998 OR 1999 OR 2000 OR 2001 OR 2002 OR 2003 OR 2004)'):
                got += scrape('mediatype:movies AND ' + q)
            return k, got
        names = s['qn']
        q = 'mediatype:movies AND title:(' + ' OR '.join('"' + qtitle(a) + '"' for a in names) + ')'
        if s.get('ambiguous') and not s.get('loose'): q += ' AND ' + CTXQ
        got = scrape(q)
        if COV[k] < 15 or s.get('loose'):
            ws = [w for w in qtitle(names[0]).split() if len(w) > 2 and w.lower() not in ('the', 'and', 'with', 'for')]
            if len(ws) >= 2 and not s.get('ambiguous'): got += scrape('mediatype:movies AND title:(' + ' AND '.join(ws) + ')')
            got += scrape('mediatype:movies AND subject:(' + ' OR '.join('"' + qtitle(a) + '"' for a in names) + ')')
        return k, got
    seen = {}; hits = collections.Counter(); raw = collections.Counter()
    with ThreadPoolExecutor(10) as ex:
        for k, items in ex.map(find, range(len(SHOWS))):
            s = SHOWS[k]; raw[k] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                if not ok_title(t, s.get('brit')) or not match(s, t): continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k}; hits[k] += 1
            if k % 100 == 0: print('search', k, len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    order = sorted(range(len(SHOWS)), key=lambda k: -len(SHOWS[k]['n']))
    EPG = {}
    try: EPG = json.load(gzip.open(os.path.join(OUT, 'epguide.json.gz'), 'rt', encoding='utf-8'))
    except Exception as e: print('no epguide', e)
    eps = []
    for k, s0 in enumerate(SHOWS):
        if s0.get('block') or COV[k] + hits[k] * 3 >= 40: continue
        g = None
        for a in s0['qn']:
            g = EPG.get(a.lower()) or EPG.get(norm(a))
            if g: break
        if not g or not isinstance(g, dict): continue
        py = str(g.get('premiered') or '')[:4]
        if not py.isdigit() or abs(int(py) - s0['first_year']) > 2: continue
        for e in g.get('episodes') or []:
            if len(e) < 4 or not e[3]: continue
            ne = norm(e[3])
            if len(ne) < 12 or len(ne.split()) < 2 or re.match(r'^(episode|part|chapter|pilot) ', ne): continue
            eps.append((k, e))
        if len(set(x[0] for x in eps)) >= 70: break
    print('episode-title lookups', len(eps), 'shows', len(set(x[0] for x in eps)), flush=True)
    def efind(a):
        k, e = a
        return k, e, scrape('mediatype:movies AND title:("' + qtitle(e[3]) + '")')
    ne_add = 0
    with ThreadPoolExecutor(10) as ex:
        for k, e, items in ex.map(efind, eps):
            s0 = SHOWS[k]; ne = ' ' + norm(e[3]) + ' '
            for it in items[:400]:
                i = it['identifier']
                if i in have or i in seen: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                if ne not in ' ' + norm(t) + ' ' or not ok_title(t): continue
                if s0.get('x') and re.search(s0['x'], t.lower()): continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k, 'ep': e}; hits[k] += 1; ne_add += 1
    print('episode-title candidates', ne_add, flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    ct = collections.Counter()
    for k, n in hits.items(): ct[SHOWS[k]['q']] += n
    print('candidates per type', sorted(ct.items()))
    print('top candidate shows', [(SHOWS[k]['title'], n) for k, n in hits.most_common(60)])
    print('no candidates', [s['title'] for k, s in enumerate(SHOWS) if not hits[k]])
    with gzip.open(os.path.join(PARTS, 'toons3_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    if str(m.get('mediatype', 'movies')) != 'movies': return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en\b', str(lang)): return None
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
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 600: return None
    files.sort(key=lambda f: f[0])
    title = m.get('title', ''); title = ' '.join(title) if isinstance(title, list) else str(title)
    s = SHOWS[it['k']]
    if not it.get('ep') and (not (s.get('block') or ok_title(title, s.get('brit'))) or not match(s, title)): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:500]).lower()
    if re.search(X_FOR, re.sub(BRIT, ' ', blob) if s.get('brit') else blob): return None
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast)|old time radio|audio only)\b', blob): return None
    orr = s.get('original_run', '')
    e = era(s, title, m.get('date'), m.get('year'))
    oy = [int(v) for v in re.findall(r'\d{4}', orr)]
    net = s.get('net', ''); ad = ''
    if s.get('block'):
        if sum(f[1] for f in files) < 1500: return None
        b2 = (title + ' ' + desc[:300]).lower()
        for nn, rx in (('fox', r'fox kids|\bfox\b'), ('wb', r"kids'? ?wb|\bwb\b"), ('abc', r'\babc\b|one saturday morning'), ('cbs', r'\bcbs\b'), ('nbc', r'\bnbc\b|tnbc'), ('upn', r'\bupn\b'), ('cn', r'cartoon network|toonami'), ('nick', r'nickelodeon|nicktoons|\bnick\b'), ('usa', r'cartoon express|usa network'), ('syn', r'disney afternoon|syndicat'), ('disney', r'disney channel|toon disney')):
            if re.search(rx, b2): net = nn; break
        m3 = re.search(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-]((?:19)?(?:8[4-9]|9\d)|(?:20)?0[0-4])(?!\d)', title)
        if m3 and 1 <= int(m3.group(1)) <= 12 and 1 <= int(m3.group(2)) <= 31:
            yy = int(m3.group(3)) % 100; ad = '%04d-%02d-%02d' % ((1900 if yy >= 84 else 2000) + yy, int(m3.group(1)), int(m3.group(2)))
        else:
            m4 = re.search(r'(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?,? ((?:198[4-9]|199\d|200[0-4]))', title)
            if m4: ad = '%s-%02d-%02d' % (m4.group(3), ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].index(m4.group(1).lower()[:3]) + 1, int(m4.group(2)))
        if not e:
            m5 = re.search(r'(?<!\d)(198[4-9]|199\d|200[0-4])(?!\d)', title + ' ' + desc[:200])
            e = int(m5.group(1)) if m5 else ''
    extra = {'ad': ad} if ad else {}
    if it.get('ep'): extra.update({'via': 'ep', 'se': it['ep'][:3], 'ad': str(it['ep'][2] or '')})
    return {**extra, 'i': it['identifier'], 'q': 'rerun_x' if False else s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'net': net, 'ct': s.get('ct', 'satam'), 'or': orr}
def meta2(it):
    r = meta(it)
    return r if r and keep(r) else None
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'toons3_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta2, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'toons3-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
for x in old:
    if not BYT[x['k']].get('block'): x['e'] = era(BYT[x['k']], x['t'], x.get('d'), x.get('y')) or x.get('e', '')
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'toons3-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res))
coverage('after')
bt = collections.defaultdict(list)
for x in res: bt[x['q']].append(x)
print('TYPE TABLE')
for t in sorted(bt): print('  %-11s items %5d  hours %6d  shows %3d' % (t, len(bt[t]), hrs(bt[t]), len(set(x['k'] for x in bt[t]))))
bs = collections.Counter(x['k'] for x in res)
print('SHOW TABLE')
fs = collections.Counter(); hs = collections.Counter()
for x in res: fs[x['k']] += len(x['f']); hs[x['k']] += sum(f[1] for f in x['f']) / 3600
for s in sorted(SHOWS, key=lambda s: -fs[s['title']]): print('  %-8s %4d items %5d files %5d h  %s' % ('MISSING' if not bs[s['title']] else 'THIN' if fs[s['title']] < 10 else 'FOUND', bs[s['title']], fs[s['title']], round(hs[s['title']]), s['title']))
print('COUNTS', collections.Counter('MISSING' if not bs[s['title']] else 'THIN' if fs[s['title']] < 10 else 'FOUND' for s in SHOWS))
print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(7)
for x in random.sample(res, min(80, len(res))): print('SAMPLE', x['q'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'])

print('NETWORK TABLE', sorted(collections.Counter(x.get('net', '') for x in res).items()))
print('CT TABLE', sorted(collections.Counter(x.get('ct', '') for x in res).items()))
print('BLOCKS dated', sum(1 for x in res if x['k'] == 'Cartoon block' and x.get('ad')), 'of', sum(1 for x in res if x['k'] == 'Cartoon block'))
print('EP ROUTE', sum(1 for x in res if x.get('via') == 'ep'))
