import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan')
THREADS = int(os.environ.get('THREADS', '16'))
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60
T0 = time.time()
OUTF = os.path.join(OUT, 'nick.json.gz')
GUIDEF = os.path.join(OUT, 'nick_guide.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_nick.json'), encoding='utf-8'))
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('\u2019', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
for s in SHOWS: s['n'] = norm(s['title'])
SHOWS.sort(key=lambda s: -max(len(norm(a)) for a in [s['title']] + s.get('alt', [])))
BYT = {s['title']: s for s in SHOWS}
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
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|nes|snes|sega|genesis|playstation|ps[1-5]|xbox|game ?boy|dos game|pc game|cd-?rom|rom ?hack|emulator|pinball|board game|comic book|comics? scans?|novel|audiobook|audio book|ebook|pdf|soundtrack|ost|theme song|theme music|themes?|intro|intros|opening credits|closing credits|credits|trailer|trailers|teaser|bloopers?|outtakes?|fan ?made|fan-?edit|fanfilm|fan film|amv|ytp|parody|spoof|abridged|review|reviews|reviewed|recap|podcast|reaction|commentary track|interview|panel|convention|comic-?con|q&a|tribute|retrospective|making of|behind the scenes|documentary about|radio|radio show|otr|old time radio|lp|vinyl|cassette|album|sheet music|script|screenplay|toys?|unboxing|action figure|model kit|slideshow|screensaver|wallpaper|test|sample|clip|clips|scene|scenes|excerpt|highlights|supercut|compilation of|mashup|remix|music video|karaoke|cover|lyrics|xxx|porn|adult|hentai|nude)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(reboot|revival|remastered in|netflix|hulu|disney\+|paramount\+|hbo max|prime video|tiktok|twitch|livestream|curse of the shadows|carnival of doom|ghost island)\b"
CTXT = r"\b(episodes?|ep\.?|season|series|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv|television|vhs|betamax|broadcast|aired|airing|syndicat\w*|with commercials|woc|complete|pilot|part \d|19[4-9]\d|200[0-4]|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa network|nick at nite|tv land|a&e|discovery|sci-?fi|comedy central|cnn|espn|tnn|cmt|bet|mtv|vh1|qvc|hsn|lifetime|family channel)\b"
CTXQ = '(subject:(tv OR television OR "tv show" OR "tv series" OR sitcom OR episode OR episodes OR series OR vhs OR broadcast OR "classic tv") OR title:(episode OR episodes OR season OR tv OR series OR vhs OR complete OR pilot OR s01 OR s02 OR s03 OR 1984 OR 1985 OR 1986 OR 1987 OR 1988 OR 1989 OR 1990 OR 1991 OR 1992 OR 1993 OR 1994 OR 1995 OR 1996 OR 1997 OR 1998 OR 1999 OR 2000 OR 2001 OR 2002 OR 2003 OR 2004) OR collection:(classic_tv OR television OR classic_tv_1950s OR classic_tv_1960s OR classic_tv_1970s OR classic_tv_1980s OR classic_tv_1990s OR vhsvault OR vhstvshows OR television_inbox))'
def core(t):
    s = norm(t)
    for _ in range(4):
        s2 = re.sub(r'^(the|a|new|all new|classic|vhs|tv|dvd|beta|tape|recording|\d{1,4}|[wk][a-z]{2,3}( tv)?( \d+)?|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|tnn|cmt|bet|mtv|vh1|cnn|espn|a and e|lifetime|discovery) ', '', s)
        if s2 == s: break
        s = s2
    return s
def ok_title(t):
    if not t: return False
    low = t.lower() + ' '
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    return True
EPCTX = r"\b(episodes?|ep\.? ?\d+|seasons?|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv series|tv show|complete series|the series|pilot|sitcom|with commercials|woc|syndicat\w*)\b"
SEPW = r'^(\d+|s\d+e?\d*|ep\d*|e\d+|episodes?|season|seasons|series|complete|pilot|part|pt|vol|volume|disc|tape|vhs|dvd|tv|show|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|gsn|aande|woc|with|w|19\d\d|200[0-4])$'
def match(show, title):
    amb = set(norm(a) for a in show.get('ambalt', []))
    names = [show['n']] + [norm(a) for a in show.get('alt', [])]
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
        if re.match(SEPW, rest.split()[0]): return True
        last = sn.split()[-1]; i = low.find(last)
        tail = low[i + len(last):] if i >= 0 else 'x'
        if tail.startswith('..') or re.match(r"^['!?.)]*\s*[-–:|(\[#]", tail): return True
    return False
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio'}

X_MORE = r"\b(annotated|japanese dub|dub|dvd extras?|bonus features?|secret galaxy|surprise|song videos?|banned|edited|i ain.?t afraid|rinse repeat|opening (and|&|to)|closing to|nicktoons broadcast|full broadcast archive|lost city of gold|the movie|marathon|iceberg|explained|ranked|ranking|every episode|top \d+|worst|best of youtube|theory|theories|analysis|essay|lost media|creepypasta|react\w*|unboxing|stream)\b"
ADS = r"\b(commercials?|bumpers?|promos?|ads?)\b"
ADOK = r"(with|w/|w|and|\+|&|incl\w*|plus)\s*(original\s+|some\s+|the\s+)?(commercials|bumpers|promos|ads)|commercials included|\bwoc\b|\bblock\b|full (broadcast|tape|recording|episode)"
def ok_title2(t):
    if not ok_title(t): return False
    low = t.lower()
    if re.search(X_MORE, low): return False
    if re.search(ADS, low) and not re.search(ADOK, low): return False
    return True
def ekey(name):
    k = norm(name)
    k = re.sub(r'^the tale of (the )?', '', k)
    k = re.sub(r' part (\d|one|two|three|i+)$', '', k)
    return k
def load_guide():
    if os.path.exists(GUIDEF): return json.load(gzip.open(GUIDEF, 'rt', encoding='utf-8'))
    return {}
GUIDE = load_guide()
for s in SHOWS:
    if s.get('episodes') and not GUIDE.get(s['title']): GUIDE[s['title']] = s['episodes']
def gidx(title):
    g = GUIDE.get(title) or []
    by = {}
    for ep in g:
        by.setdefault(ekey(ep['name']), []).append(ep)
    return g, by
PART = {'1': 1, 'one': 1, 'i': 1, '2': 2, 'two': 2, 'ii': 2, '3': 3, 'three': 3, 'iii': 3}
def epfind(title, text):
    g, by = gidx(title)
    if not g: return None
    nt = ' ' + norm(text) + ' '
    best = None
    for k, eps in by.items():
        tale = ' tale of the ' + k + ' ' in nt or ' tale of ' + k + ' ' in nt or ' tale of a ' + k + ' ' in nt
        if not tale and (len(k) < 9 or ' ' not in k): continue
        if (' ' + k + ' ') in nt and (not best or len(k) > len(best[0])): best = (k, eps)
    if best:
        eps = best[1]
        if len(eps) > 1:
            m = re.search(r' (?:part|pt) (\d|one|two|three|i+) ', nt)
            if m:
                n = PART.get(m.group(1))
                eps = [ep for ep in eps if PART.get((re.search(r'part (\w+)$', norm(ep['name'])) or [0, ''])[1]) == n] or eps
        return eps[0]
    m = re.search(r'(?<![a-z0-9])s(\d{1,2})[ ._-]?e(\d{1,3})(?!\d)|(?<!\d)(\d{1,2})x(\d{2})(?!\d)|season (\d{1,2}) (?:episode|ep) (\d{1,3})', text.lower().replace('_', ' '))
    if m:
        v = [int(x) for x in m.groups() if x]
        for ep in g:
            if ep['s'] == v[0] and ep['e'] == v[1]: return ep
    return None
def match2(show, title):
    if show.get('loose'):
        nt = ' ' + norm(title) + ' '
        if not any((' ' + norm(x) + ' ') in nt for x in [show['title']] + show.get('alt', [])): return False
    elif not match(show, title): return False
    low = title.lower()
    if show.get('need') and not re.search(show['need'], low): return False
    if show.get('loose') and not re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)|(?<!\d)\d{1,2}[./-]\d{1,2}[./-]([89]\d|0[0-4])(?!\d)', low): return False
    if show.get('ms'):
        for m in re.finditer(r'(?:season|series|s)\s?0?(\d{1,2})(?!\d)', low):
            if int(m.group(1)) > show['ms'] and int(m.group(1)) < 30: return False
    return True
def era(s, title, d, y):
    oy = [int(v) for v in re.findall(r'\d{4}', s.get('run', ''))]
    ys = [int(v) for v in re.findall(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', title)]
    m2 = re.search(r'(?<!\d)\d{1,2}[./-]\d{1,2}[./-]([89]\d|0[0-4])(?!\d)', title)
    if m2: ys.insert(0, (1900 if m2.group(1)[0] in '89' else 2000) + int(m2.group(1)))
    lo = max(1984, oy[0] if oy else 1984); hi = min(2004, oy[-1] if len(oy) > 1 else 2004)
    ys = [v for v in ys if lo <= v <= hi]
    if ys: return ys[0]
    if s.get('ms'):
        m = re.search(r'(?:season|s)\s?0?(\d{1,2})(?!\d)', title.lower())
        if m and oy: return min(hi, oy[0] + int(m.group(1)) - 1)
    return lo if oy else ''
def qtitle(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-.,]', ' ', t).split())
def known_ids():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) in ('nick.json.gz', 'nick_guide.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz'): continue
        try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(j, dict): continue
        for x in j:
            if isinstance(x, dict):
                if x.get('i'): have.add(x['i'])
                ia = x.get('ia')
                if isinstance(ia, list) and ia and isinstance(ia[0], str): have.add(ia[0])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    return have
def tvmaze(s):
    oy = [int(v) for v in re.findall(r'\d{4}', s.get('run', ''))]
    j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(s['title']), tries=3) or []
    for r in j:
        sh = r.get('show') or {}
        if norm(sh.get('name')) != s['n'] and norm(sh.get('name')) not in [norm(a) for a in s.get('alt', [])]: continue
        py = int(str(sh.get('premiered') or '0000')[:4] or 0)
        if not oy or not (oy[0] - 3 <= py <= oy[-1]): continue
        eps = get('https://api.tvmaze.com/shows/%d/episodes?specials=1' % sh['id'], tries=3) or []
        out = [{'s': e.get('season') or 0, 'e': e.get('number') or 0, 'name': e.get('name') or '', 'airdate': e.get('airdate') or ''} for e in eps if e.get('number')]
        if out: return out
    return None
if MODE == 'plan':
    have = known_ids()
    old = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    have |= set(x['i'] for x in old)
    print('known', len(have), 'shows', len(SHOWS), flush=True)
    for s in SHOWS:
        if not s.get('guide'): continue
        g = tvmaze(s)
        if g:
            emb = s.get('episodes') or []
            if emb and abs(len(g) - len(emb)) > 6: print('guide size differs', s['title'], len(g), len(emb))
            GUIDE[s['title']] = g
        print('guide', s['title'], len(GUIDE.get(s['title']) or []), 'tvmaze' if g else 'embedded', flush=True)
    with gzip.open(GUIDEF, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
    jobs = []
    for k, s in enumerate(SHOWS):
        names = [s['title']] + s.get('alt', [])
        q = 'mediatype:movies AND title:(' + ' OR '.join('"' + qtitle(a) + '"' for a in names) + ')'
        if s.get('ambiguous'): q += ' AND ' + CTXQ
        jobs.append((k, q, 0))
        if s.get('guide') or s.get('priority'):
            jobs.append((k, 'mediatype:movies AND (' + ' OR '.join('"' + qtitle(a) + '"' for a in names) + ')', 1))
        if s.get('wide'):
            jobs.append((k, 'mediatype:movies AND (' + ' OR '.join('"' + qtitle(a) + '"' for a in names) + ')', 3))
        if s.get('priority'):
            g, by = gidx(s['title'])
            keys = sorted(set('tale of the ' + k2 for k2 in by) | set('tale of ' + k2 for k2 in by))
            for n in range(0, len(keys), 12):
                jobs.append((k, 'mediatype:movies AND title:(' + ' OR '.join('"' + x + '"' for x in keys[n:n + 12]) + ')', 2))
    BLK = next((k for k, s in enumerate(SHOWS) if s['title'] == 'SNICK'), None)
    def find(job): return job, scrape(job[1])
    seen = {}; hits = collections.Counter()
    with ThreadPoolExecutor(8) as ex:
        for (k, q, mode), items in ex.map(find, jobs):
            s = SHOWS[k]
            for it in items:
                i = it['identifier']
                if i in have or i in seen: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\\b', lang): continue
                if not ok_title2(t): continue
                kk = k
                if mode == 0:
                    if not match2(s, t): continue
                elif mode == 3:
                    if not match(s, t): continue
                elif mode == 2:
                    if not epfind(s['title'], t): continue
                else:
                    if not match2(s, t) and not epfind(s['title'], t):
                        if BLK is not None and re.search(r'(?i)snick|nickelodeon|nick\\b', t) and re.search(ADOK + r'|\\bvhs\\b|recording|199\\d|200[0-4]', t.lower()): kk = BLK
                        else: continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': SHOWS[kk]['title'], 'm': mode}; hits[SHOWS[kk]['title']] += 1
    for col in ('nickelodeon', 'nickelodeon-archive', 'nick-archive', 'snick', 'nickelodeonvhs', 'nick-at-nite', 'tnbc', 'saturday-morning-tv'):
        n = 0
        for it in scrape('mediatype:movies AND collection:(' + col + ')'):
            i = it['identifier']
            if i in have or i in seen: continue
            t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
            if not ok_title2(t): continue
            s = next((s for s in SHOWS if match2(s, t)), None)
            if not s: continue
            seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': s['title'], 'm': 0}; hits[s['title']] += 1; n += 1
        print('collection', col, n, flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    print('candidate shows', hits.most_common())
    print('no candidates', [s['title'] for s in SHOWS if not hits[s['title']]])
    with gzip.open(os.path.join(PARTS, 'nick_cands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump({'cands': cands, 'guide': GUIDE}, f, separators=(',', ':'))
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

def keep(x):
    s = BYT.get(x['k'])
    if not s or not ok_title2(x['t']): return False
    if not match2(s, x['t']) and not (x.get('se') and s.get('guide')) and not x.get('blk') and not (x.get('w') and match(s, x['t'])): return False
    if set(x.get('c') or []) & XCOL: return False
    dy = re.match(r'(\d{4})', str(x.get('d') or ''))
    if x['i'].startswith('youtube-') and dy and int(dy.group(1)) >= 2005 and not re.search(r'(19[4-9]\d|200[0-4]|s\d+\s?e\d+)', x['t'].lower()): return False
    return True
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
    files = files[:60]
    title = m.get('title', ''); title = ' '.join(title) if isinstance(title, list) else str(title)
    s = BYT[it['k']]
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:500]).lower()
    if re.search(X_FOR, blob): return None
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast)|old time radio|audio only)\b', blob): return None
    wide = 0
    if it.get('m') == 3 and not match2(s, title):
        if not s.get('need') or not re.search(s['need'], blob) or not match(s, title): return None
        wide = 1
    se = {}
    if s.get('guide'):
        single = epfind(s['title'], title) if len(files) <= 2 else None
        for f in files:
            ep = epfind(s['title'], f[0]) or single
            if ep: se[f[0]] = [ep['s'], ep['e'], ep.get('airdate') or '', ep['name']]
    e = era(s, title, m.get('date'), m.get('year'))
    if se:
        ys = sorted(v[2][:4] for v in se.values() if v[2][:4].isdigit())
        if ys and 1984 <= int(ys[0]) <= 2004: e = int(ys[0])
    r = {'i': it['identifier'], 'q': s.get('q', 'kids'), 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files, 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'net': s.get('net', ''), 'ct': s['ct']}
    if se: r['se'] = se
    if wide: r['w'] = 1
    if s['title'] == 'SNICK' and it.get('m') == 1: r['blk'] = 1
    return r
def meta2(it):
    r = meta(it)
    return r if r and keep(r) else None
if MODE == 'meta':
    j = json.load(gzip.open(os.path.join(PARTS, 'nick_cands.json.gz'), 'rt', encoding='utf-8'))
    GUIDE.update(j.get('guide') or {})
    cands = j['cands'][SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta2, cands)):
            if r: res.append(r)
            if n % 500 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'nick-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
cf = os.path.join(PARTS, 'nick_cands.json.gz')
if os.path.exists(cf):
    GUIDE.update(json.load(gzip.open(cf, 'rt', encoding='utf-8')).get('guide') or {})
    with gzip.open(GUIDEF, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'nick-[0-9]*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res))
bs = collections.defaultdict(list)
for x in res: bs[x['k']].append(x)
print('SHOW TABLE')
for s in sorted(SHOWS, key=lambda s: -len(bs[s['title']])):
    L = bs[s['title']]; nf = sum(len(x['f']) for x in L)
    print('  %-8s %4d items %5d files %5d h  %s [%s]' % ('FOUND' if nf >= 10 else 'THIN' if nf else 'MISSING', len(L), nf, hrs(L), s['title'], s['ct']))
print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
ELSE = collections.defaultdict(set)
for p in glob.glob(os.path.join(OUT, '*.json.gz')):
    if os.path.basename(p) in ('nick.json.gz', 'nick_guide.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz'): continue
    try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
    except Exception: continue
    if isinstance(j, dict): continue
    for x in j:
        if not isinstance(x, dict) or not x.get('t'): continue
        for s in SHOWS:
            if not s.get('guide') or not (match(s, x['t']) or (s.get('priority') and epfind(s['title'], x['t']))): continue
            single = epfind(s['title'], x['t'])
            for f in x.get('f') or []:
                ep = epfind(s['title'], f[0]) or (single if len(x['f']) <= 2 else None)
                if ep: ELSE[s['title']].add((ep['s'], ep['e']))
            break
for s in SHOWS:
    if not s.get('guide'): continue
    g = GUIDE.get(s['title']) or []
    got = collections.defaultdict(list)
    for x in bs[s['title']]:
        for fn, v in (x.get('se') or {}).items(): got[(v[0], v[1])].append(x['i'])
    nf = sum(1 for ep in g if got.get((ep['s'], ep['e'])))
    ne = sum(1 for ep in g if not got.get((ep['s'], ep['e'])) and (ep['s'], ep['e']) in ELSE[s['title']])
    print('CHECKLIST', s['title'], 'episodes', len(g), 'found here', nf, 'only in other catalogs', ne, 'missing', len(g) - nf - ne)
    for ep in g:
        k = (ep['s'], ep['e'])
        st = 'FOUND' if got.get(k) else 'ELSEWHERE' if k in ELSE[s['title']] else 'MISSING'
        print('  %-9s S%02dE%02d %-10s %-44s %d copies %s' % (st, ep['s'], ep['e'], ep.get('airdate') or '', ep['name'][:44], len(got.get(k, [])), (got.get(k) or [''])[0][:40]))
random.seed(7)
for x in random.sample(res, min(60, len(res))): print('SAMPLE', x['ct'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'], '|', len(x.get('se') or {}), 'matched')
