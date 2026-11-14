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
OUTF = os.path.join(OUT, 'drama.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_drama.json'), encoding='utf-8'))
TVCOL = r'^(classic_?-?tv|television|vhsvault|vhstvshows|tvarchive|tv_|.*_tv$|.*television.*|.*tvshows.*)'
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
def disc(title, cols, blob=''):
    low = title.lower()
    if re.search(EPCTX, low) or re.search(r'(?<!\d)(19[5-9]\d|200[0-4])(?!\d)', low) or re.search(r'\b(disc|dvd|vol(ume)?\.? ?\d|part \d|vhs)\b', low): return True
    if any(re.match(TVCOL, c) for c in (cols or [])): return True
    return bool(blob and re.search(r'\b(tv series|television series|episodes?|season \d|aired|nbc|cbs|abc|fox|syndicat\w*)\b', blob))
XCOL = {'community_media', 'podcasts', 'newsandpublicaffairs', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio'}
def keep(x):
    s = BYT.get(x['k'])
    if not s or not ok_title(x['t']) or not match(s, x['t']) or not disc(x['t'], x.get('c'), (x.get('s', '') + ' ' + x.get('ds', '')).lower()): return False
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
if MODE == 'plan':
    RAWF = os.path.join(OUT, 'raw.json.gz')
    have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8'))) if os.path.exists(RAWF) else set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) in ('raw.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz'): continue
        try: rows = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        for x in rows if isinstance(rows, list) else []:
            if isinstance(x, dict) and x.get('i'): have.add(x['i'])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    rej = os.path.join(here, 'drama_seen.json.gz')
    if os.path.exists(rej): have |= set(json.load(gzip.open(rej, 'rt')))
    print('known', len(have), 'shows', len(SHOWS), flush=True)
    def find(k):
        s = SHOWS[k]
        q = 'mediatype:movies AND title:(' + ' OR '.join('"' + qtitle(a) + '"' for a in [s['title']] + s.get('alt', [])) + ')'
        if s.get('ambiguous') or len(s['n']) < 12: q += ' AND ' + CTXQ
        return k, scrape(q)
    seen = {}; hits = collections.Counter(); raw = collections.Counter(); why = collections.defaultdict(collections.Counter); smp = collections.defaultdict(list)
    with ThreadPoolExecutor(10) as ex:
        for k, items in ex.map(find, range(len(SHOWS))):
            s = SHOWS[k]; raw[k] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: why[k]['known'] += 1; continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): why[k]['lang'] += 1; continue
                cl = it.get('collection'); cl = cl if isinstance(cl, list) else [cl] if cl else []
                if not ok_title(t): why[k]['title'] += 1; smp[k, 'T'].append(t[:70]); continue
                if not match(s, t): why[k]['match'] += 1; smp[k, 'M'].append(t[:70]); continue
                if s.get('ambiguous') and not disc(t, cl): why[k]['disc'] += 1; continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k}; hits[k] += 1
            if k % 100 == 0: print('search', k, len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    cols = set()
    for pat in ('classic_tv*', 'classictv*', 'classic-tv*'):
        for it in scrape('mediatype:collection AND identifier:(' + pat + ')'): cols.add(it['identifier'])
    cols = sorted(c for c in cols if 'commercial' not in c and not c.startswith('fav-'))
    print('collections', cols, flush=True)
    order = sorted(range(len(SHOWS)), key=lambda k: -len(SHOWS[k]['n']))
    if cols:
        n = 0
        for it in scrape('mediatype:movies AND collection:(' + ' OR '.join(cols) + ')'):
            i = it['identifier']
            if i in have or i in seen: continue
            t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
            if not ok_title(t): continue
            k = next((k for k in order if match(SHOWS[k], t)), None)
            if k is None: continue
            seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k}; hits[k] += 1; n += 1
        print('collection sweep added', n, flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    ct = collections.Counter()
    for k, n in hits.items(): ct[SHOWS[k]['q']] += n
    print('candidates per type', sorted(ct.items()))
    print('top candidate shows', [(SHOWS[k]['title'], n) for k, n in hits.most_common(60)])
    for k, s in enumerate(SHOWS): print('PLAN %-40s raw %5d new %4d %s' % (s['title'][:40], raw[k], hits[k], dict(why[k])))
    random.seed(3)
    for k, s in enumerate(SHOWS):
        for w in 'TM':
            for t in random.sample(smp[k, w], min(3, len(smp[k, w]))): print('REJ', w, '|', s['title'][:24], '|', t)
    print('no candidates', [s['title'] for k, s in enumerate(SHOWS) if not hits[k]])
    with gzip.open(os.path.join(PARTS, 'drama_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
        if d < 600: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 600: return None
    files.sort(key=lambda f: f[0])
    title = m.get('title', ''); title = ' '.join(title) if isinstance(title, list) else str(title)
    s = SHOWS[it['k']]
    if not ok_title(title) or not match(s, title): return None
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
    orr = s.get('original_run', '')
    e = era(s, title, m.get('date'), m.get('year'))
    return {'i': it['identifier'], 'q': s['q'], 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'net': s.get('net', ''), 'ct': 'rerun' if s['q'] == 'rerun' else 'drama', 'or': orr, 'fy': s['first_year'], 'ly': s['last_year']}
def meta2(it):
    r = meta(it)
    return r if r and keep(r) else None
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'drama_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta2, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'drama-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
for x in old: x['e'] = era(BYT[x['k']], x['t'], x.get('d'), x.get('y'))
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'drama-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res))
bt = collections.defaultdict(list)
for x in res: bt[x['ct']].append(x)
print('TYPE TABLE')
for t in sorted(bt): print('  %-11s items %5d  hours %6d  shows %3d' % (t, len(bt[t]), hrs(bt[t]), len(set(x['k'] for x in bt[t]))))
bs = collections.Counter(x['k'] for x in res)
print('SHOW TABLE')
for k, n in bs.most_common(): print('  %4d  %s' % (n, k))
print('ZERO', [s['title'] for s in SHOWS if not bs[s['title']]])
for s in SHOWS:
    n = bs[s['title']]; fl = sum(len(x['f']) for x in res if x['k'] == s['title'])
    print('STATUS %-8s %4d items %5d files  %s [%s %s]' % ('FOUND' if fl >= 20 else 'THIN' if fl else 'MISSING', n, fl, s['title'], s.get('net', ''), s['original_run']))
print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(7)
for x in random.sample(res, min(60, len(res))): print('SAMPLE', x['ct'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'])
