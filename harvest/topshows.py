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
OUTF = os.path.join(OUT, 'topshows.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_top.json'), encoding='utf-8'))
THIN = {1: 60, 2: 30}
def status(s, c): return 'MISSING' if c[1] == 0 else 'THIN' if c[1] < THIN.get(s['rank'], 12) else 'FOUND'
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
for s in SHOWS: s['n'] = norm(s['title'])
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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language,subject', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > 40000: break
    return out
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|doblada|dublado|dublagem|legendado|portugu[eê]s|brasil|deutsch|german dub|fran[cç]ais|french dub|vf|vostfr|italiano|ita|nederlands|svenska|norsk|dansk|suomi|polski|lektor|magyar|rom[aâ]n[aă]|t[uü]rk[cç]e|русск|hindi|tamil|telugu|urdu|arabic|bahasa|tagalog|sub ?esp|subtitulado|temporada|cap[ií]tulo|episodio|folge|staffel|saison|aflevering|odcinek|mandarin|cantonese|korean dub|japanese dub|dubbed|dub|uk dvd|pal|uk version|australian version|canadian version|bbc|itv|channel 4|sky one|rte)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|nes|snes|sega|genesis|playstation|ps[1-5]|xbox|game ?boy|dos game|pc game|cd-?rom|rom ?hack|emulator|pinball|board game|comic book|comics? scans?|novel|audiobook|audio book|ebook|pdf|soundtrack|ost|theme song|theme music|themes?|intro|intros|opening credits|closing credits|credits|bumper|bumpers|promo|promos|trailer|trailers|teaser|commercial|commercials|ad|ads|bloopers?|outtakes?|fan ?made|fan-?edit|fanfilm|fan film|amv|ytp|parody|spoof|abridged|review|reviews|reviewed|recap|podcast|reaction|commentary track|interview|panel|convention|comic-?con|q&a|tribute|retrospective|making of|behind the scenes|documentary about|radio|radio show|otr|old time radio|lp|vinyl|cassette|album|sheet music|script|screenplay|toys?|unboxing|figure|model kit|slideshow|screensaver|wallpaper|test|sample|clip|clips|scene|scenes|excerpt|highlights|supercut|compilation of|mashup|remix|music video|karaoke|cover|lyrics|special features|bonus features|recreated|recreation|reconstruction|walkthrough|runescape|san andreas|minecraft|roblox|gmod|sims|lego|pooh's adventures|poohs adventures|adventures of|bigger,? longer|banned|predict\w*|predictions?|top \d+|ranked|ranking|explained|theory|theories|tier list|deleted scenes?|reunion|cast of|analysis|essay|iceberg|creepypasta|lost episode|bootleg|drawing|how to draw|fan art|cosplay|meme|memes|edit|edits|shorts|xxx|porn|adult|hentai|nude)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(reboot|revival|remastered in|netflix|hulu|disney\+|paramount\+|hbo max|prime video|youtube|tiktok|twitch|livestream|zoom)\b"
CTXT = r"\b(episodes?|ep\.?|season|series|s\d{1,2}\s?e\d{1,3}|\d{1,2}x\d{2}|tv|television|vhs|betamax|broadcast|aired|airing|syndicat\w*|with commercials|woc|complete|pilot|part \d|19[4-9]\d|200[0-4]|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa network|nick at nite|tv land|a&e|discovery|sci-?fi|comedy central|cnn|espn|tnn|cmt|bet|mtv|vh1|qvc|hsn|lifetime|family channel)\b"
CTXQ = '(subject:(tv OR television OR "tv show" OR "tv series" OR sitcom OR episode OR episodes OR series OR vhs OR broadcast OR "classic tv") OR title:(episode OR episodes OR season OR tv OR series OR vhs OR complete OR pilot OR s01 OR s02 OR s03 OR 1984 OR 1985 OR 1986 OR 1987 OR 1988 OR 1989 OR 1990 OR 1991 OR 1992 OR 1993 OR 1994 OR 1995 OR 1996 OR 1997 OR 1998 OR 1999 OR 2000 OR 2001 OR 2002 OR 2003 OR 2004) OR collection:(classic_tv OR television OR classic_tv_1950s OR classic_tv_1960s OR classic_tv_1970s OR classic_tv_1980s OR classic_tv_1990s OR vhsvault OR vhstvshows OR television_inbox))'
def core(t):
    s = norm(t)
    for _ in range(4):
        s2 = re.sub(r'^(the|a|new|all new|classic|vhs|tv|dvd|beta|tape|recording|s|ep|e|season|episode|\d{1,4}|[wk][a-z]{2,3}( tv)?( \d+)?|nbc|cbs|abc|fox|pbs|hbo|tbs|wgn|usa|tnn|cmt|bet|mtv|vh1|cnn|espn|a and e|lifetime|discovery) ', '', s)
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
        if hit not in amb and (not show.get('ambiguous') or hit != show['n']) and (len(hit.split()) >= 2 or len(hit) >= 9) and re.search(EPCTX, low + ' ') and (c.startswith(re.sub(r'^(the|a) ', '', hit) + ' ') or c == re.sub(r'^(the|a) ', '', hit) or re.search(r'\b(woc|with commercials|w/ ?commercials)\b', low)): return True
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
DATED = ('news', 'talk', 'late', 'mag')
NAMES = {}
for s0 in SHOWS:
    for a0 in [s0['n']] + [norm(b0) for b0 in s0.get('alt', [])]:
        NAMES.setdefault(a0, s0['title']); NAMES.setdefault(re.sub(r'^(the|a) ', '', a0), s0['title'])
def tape(title):
    if title.count('|') < 1 or re.search(X_FOR, title.lower() + ' ') or re.search(X_MOD, title.lower() + ' '): return []
    if re.search(r'(?i)\b(promo|promos|split screen|credits|commercial break|bumpers?|trailer|fan ?made|youtube)\b', title): return []
    out = []
    for seg in title.split('|'):
        n = re.sub(r' x \d+$', '', norm(seg)).strip()
        n = re.sub(r'^(the|a) ', '', n)
        if n in NAMES and NAMES[n] not in out: out.append(NAMES[n])
    return out
def yr_ok(s, title):
    ys = [int(v) for v in re.findall(r'(?<!\d)(19[2-9]\d|200[0-4])(?!\d)', title)]
    if any(v < s['years'][0] for v in ys): return False
    m = re.search(r'(?i)\bseason\s*(\d{1,2})\b|\bs(\d{1,2})\s?e\d', title)
    if m:
        n = int(m.group(1) or m.group(2))
        if n and (s['years'][0] + n - 1 > 2004 or n > s['years'][1] - s['years'][0] + 2): return False
    return True
def subj_ok(s, subj):
    if isinstance(subj, str): subj = re.split(r'[;,]', subj)
    tags = set(norm(v) for v in (subj or []))
    return bool(tags & set([s['n']] + [norm(a) for a in s.get('alt', [])]))
def keep(x):
    if x.get('ct') == 'tape': return bool(tape(x['t']))
    s = BYT.get(x['k'])
    if re.match(r'(twitch|bliptv|podcast)', x['i'].lower()): return False
    if x.get('via') and not match(s, x['t']) and not re.search(r'(?i)\bs\d{1,2}\s?e\d{1,3}\b|\b\d{1,2}x\d{2}\b', x['t']): return False
    if not s or not ok_title(x['t']) or not (match(s, x['t']) or x.get('via')) or not yr_ok(s, x['t']): return False
    if s['q'] in DATED and not era(s, x['t'], x.get('d'), x.get('y')): return False
    if set(x.get('c') or []) & XCOL: return False
    if re.match(r'^[a-z]{4,10}-[A-Z]', x['i']) and not re.search(r'(19[4-9]\d|200[0-4])', x['t']): return False
    dy = re.match(r'(\d{4})', str(x.get('d') or ''))
    if x['i'].startswith('youtube-') and dy and int(dy.group(1)) >= 2005 and not re.search(r'(19[4-9]\d|200[0-4])', x['t']): return False
    return True
def era(s, title, d, y):
    y0, y1 = s['years']
    ys = [int(v) for v in re.findall(r'(?<!\d)(19[5-9]\d|200[0-4])(?!\d)', title)]
    ys = [v for v in ys if y0 <= v <= y1]
    if ys: return ys[0]
    m2 = re.search(r'(?i)(?:s|season\s*)(\d{1,2})', title)
    if m2 and 0 < int(m2.group(1)) <= y1 - y0 + 1: return y0 + int(m2.group(1)) - 1
    for v in (d, y):
        m3 = re.match(r'(\d{4})', str(v or ''))
        if m3 and y0 <= int(m3.group(1)) <= y1: return int(m3.group(1))
    return y0 if y1 - y0 <= 2 else ''
def itemfiles(x):
    f = x.get('f') or []
    if x.get('ia') and not f: f = x['ia'][1]
    return [g for g in f if isinstance(g, list) and len(g) > 1 and isinstance(g[1], (int, float)) and g[1] >= 300]
def allitems():
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))):
        b = os.path.basename(p)
        if b in ('ads.json.gz', 'filler.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'movies.json.gz'): continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(L, list): continue
        for x in L:
            if isinstance(x, dict) and x.get('i'): yield b, x
            elif isinstance(x, list) and len(x) > 3 and isinstance(x[3], list): yield b, {'i': x[0], 't': x[1], 'f': x[3]}
def coverage():
    cov = {s['title']: [0, 0, 0] for s in SHOWS}; ids = set()
    names = [(s, [s['n']] + [norm(a) for a in s.get('alt', [])]) for s in SHOWS]
    names.sort(key=lambda p: -len(p[0]['n']))
    for b, x in allitems():
        ids.add(x['i'])
        if x.get('ct') == 'tape':
            for k2 in x.get('shows') or []:
                if k2 in cov: c = cov[k2]; c[0] += 1; c[1] += 1; c[2] += 1500
            continue
        t = str(x.get('t') or ''); nt = ' ' + norm(t) + ' '; kk = norm(str(x.get('k') or ''))
        for s, ns in names:
            if kk == s['n'] or (any((' ' + h + ' ') in nt for h in ns) and ok_title(t) and match(s, t)):
                fs = itemfiles(x); c = cov[s['title']]; c[0] += 1; c[1] += len(fs); c[2] += sum(g[1] for g in fs); break
    return cov, ids
def table(cov, tag):
    print(tag + ' COVERAGE (rank, show, net, years, items, episode files, hours, status)')
    for s in sorted(SHOWS, key=lambda s: (s['rank'], s['title'])):
        c = cov[s['title']]
        print('  %s %d | %-46s | %-5s | %d-%d | %4d | %5d | %5d | %s' % (tag, s['rank'], s['title'][:46], s['net'], s['years'][0], s['years'][1], c[0], c[1], round(c[2] / 3600), status(s, c)))
    n = collections.Counter(status(s, cov[s['title']]) for s in SHOWS)
    print(tag, 'SUMMARY', dict(n), flush=True)
def qtitle(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', t).split())
if MODE == 'plan':
    cov, have = coverage()
    table(cov, 'BEFORE')
    rej = os.path.join(here, 'topshows_seen.json.gz')
    if os.path.exists(rej): have |= set(json.load(gzip.open(rej, 'rt')))
    TARGET = set(k for k, s in enumerate(SHOWS) if status(s, cov[s['title']]) != 'FOUND' or os.environ.get('ALL'))
    print('known', len(have), 'shows', len(SHOWS), 'targets', len(TARGET), flush=True)
    def find(k):
        s = SHOWS[k]
        if k not in TARGET: return k, [dict(x, tp=1) for x in scrape('mediatype:movies AND title:("' + qtitle(s['title']) + '")') if '|' in str(x.get('title'))]
        q = 'mediatype:movies AND title:(' + ' OR '.join('"' + qtitle(a) + '"' for a in [s['title']] + s.get('alt', [])) + ')'
        if s.get('ambiguous'): q += ' AND ' + CTXQ
        a = scrape(q)
        q2 = 'mediatype:movies AND subject:(' + ' OR '.join('"' + qtitle(b) + '"' for b in [s['title']] + s.get('alt', [])) + ') AND ' + CTXQ
        ids = set(x['identifier'] for x in a)
        return k, a + [dict(x, via=1) for x in scrape(q2) if x['identifier'] not in ids]
    seen = {}; hits = collections.Counter(); raw = collections.Counter(); rejs = collections.defaultdict(list); tapes = [0]
    with ThreadPoolExecutor(10) as ex:
        for k, items in ex.map(find, range(len(SHOWS))):
            s = SHOWS[k]; raw[k] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                via = 0
                if tape(t):
                    seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k, 'tp': 1}; tapes[0] += 1
                    continue
                if it.get('tp'): continue
                if not yr_ok(s, t):
                    if len(rejs[k]) < 4: rejs[k].append(t[:60])
                    continue
                if not ok_title(t) or not match(s, t):
                    if it.get('via') and ok_title(t) and subj_ok(s, it.get('subject')) and re.search(EPCTX, t.lower() + ' '): via = 1
                    else:
                        if len(rejs[k]) < 4: rejs[k].append(t[:60])
                        continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k, 'via': via}; hits[k] += 1
            if k % 100 == 0: print('search', k, len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    cols = set()
    for pat in ('classic_tv*', 'classictv*', 'classic-tv*'):
        for it in scrape('mediatype:collection AND identifier:(' + pat + ')'): cols.add(it['identifier'])
    cols = sorted(c for c in cols if 'commercial' not in c and not c.startswith('fav-')) + ['vhstvshows', 'television_inbox', 'vhsvault']
    order = sorted(TARGET, key=lambda k: -len(SHOWS[k]['n']))
    n = 0
    for it in scrape('mediatype:movies AND collection:(' + ' OR '.join(cols) + ')'):
        i = it['identifier']
        if i in have or i in seen: continue
        t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
        if not ok_title(t): continue
        nt = ' ' + norm(t) + ' '
        k = next((k for k in order if (' ' + SHOWS[k]['n'] + ' ') in nt and match(SHOWS[k], t)), None)
        if k is None: continue
        seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k}; hits[k] += 1; n += 1
    print('collection sweep added', n, flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    print('top candidate shows', [(SHOWS[k]['title'], n) for k, n in hits.most_common(80)])
    print('raw/kept/rejected samples', [(SHOWS[k]['title'], raw[k], hits[k], rejs[k]) for k in sorted(TARGET) if hits[k] < 12])
    print('tape recordings', tapes[0])
    print('no candidates', [SHOWS[k]['title'] for k in sorted(TARGET) if not hits[k]])
    with gzip.open(os.path.join(PARTS, 'top_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
    tp = tape(title) if it.get('tp') else []
    if it.get('tp') and (not tp or sum(f[1] for f in files) < 1200): return None
    subj0 = m.get('subject', '')
    via = 1 if it.get('via') and subj_ok(s, subj0) else 0
    if not tp and (not ok_title(title) or not (match(s, title) or via)): return None
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
    e = era(s, title, m.get('date'), m.get('year'))
    if tp:
        md = re.search(r'(?<!\d)((?:19[89]\d|200[0-4])-\d\d-\d\d)(?!\d)', title); my = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', title)
        return {'i': it['identifier'], 'q': 'block', 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': tp[0], 'e': int(my.group(1)) if my else '', 'net': '', 'ct': 'tape', 'shows': tp, 'ad': md.group(1) if md else ''}
    return {'i': it['identifier'], 'q': s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'net': s['net'], 'ct': 'rerun' if s['years'][1] < 1984 else 'top', 'via': via}
def meta2(it):
    r = meta(it)
    return r if r and keep(r) else None
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'top_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta2, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'top-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
for x in old:
    if x.get('ct') != 'tape': x['e'] = era(BYT[x['k']], x['t'], x.get('d'), x.get('y'))
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'top-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res))
cov, _ = coverage()
table(cov, 'AFTER')
bs = collections.Counter(x['k'] for x in res if x.get('ct') != 'tape')
tp = [x for x in res if x.get('ct') == 'tape']
print('TAPES', len(tp), 'hours', hrs(tp), 'dated', sum(1 for x in tp if x.get('ad')), 'years', sorted(collections.Counter(str(x['e']) for x in tp).items()))
print('TAPE SHOWS', collections.Counter(k for x in tp for k in x['shows']).most_common(80))
print('NEW ITEMS PER SHOW', bs.most_common())
print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(7)
for x in random.sample(res, min(60, len(res))): print('SAMPLE', x['q'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'])
