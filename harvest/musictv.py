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
OUTF = os.path.join(OUT, 'musictv.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_musictv.json'), encoding='utf-8'))
BLOB = {'MTV', 'VH1', 'Music video blocks', 'MTV VJs'}
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('\u2019', "'")
    s = re.sub(r"[^a-z0-9$]+", ' ', s.replace("'", ''))
    return ' '.join(s.split())
PAIRS = []
for k, s in enumerate(SHOWS):
    s['rx'] = re.compile(s['need']) if s.get('need') else None
    for nm in [s['title']] + s.get('alt', []):
        n = norm(nm)
        if n: PAIRS.append((n, k))
PAIRS.sort(key=lambda p: -len(p[0]))
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
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|playstation|xbox|rom ?hack|emulator|pinball|audiobook|ebook|pdf|podcast|reaction|reacts?|review|reviews|reviewed|recap|fan ?made|fan-?edit|fan film|amv|ytp|parody|spoof|karaoke|lyrics|lyric video|cover version|remix|mashup|mixtape|dj mix|dj set|full album|audio only|audio|radio show|radio broadcast|fm radio|vinyl|cassette|sheet music|tab|tutorial|lesson|how to|unboxing|slideshow|screensaver|wallpaper|test|sample|promos|bumpers|idents|ids|commercials only|commercial compilation|ad break|logo history|ident history|documentary about|retrospective|tribute band|fancam|bootleg audio|soundboard|xxx|porn|adult|hentai|nude|beavis|butt-?head|liquid television|jackass|real world|road rules|daria|celebrity deathmatch|aeon flux|cribs|punk'?d|osbournes|pimp my ride|jersey shore|teen mom|the hills|laguna beach|ridiculousness|catfish|top of the pops|totp|muchmusic|much music|much more music|mtv europe|mtv uk|mtv asia|mtv latino|mtv latin america|mtv brasil|mtv brazil|mtv japan|mtv india|mtv italia|mtv germany|mtv base|mtv russia|mtv nordic|mtv australia|mtv canada|mtv espa[nñ]a|mtv france|mtv polska|viva|the chart show|smash hits|rage abc|countdown abc|rockpalast|musikladen|formel eins|sanremo|eurovision)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(netflix|hulu|tiktok|twitch|livestream|zoom|vevo|spotify|pluto tv|mtv classic 20\d\d)\b"
def ok_title(t):
    if not t: return False
    low = t.lower() + ' '
    if re.search(r'[^\x00-\xff\u2010-\u2027\u2122]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    return True
def which(text, only=None):
    nt = ' ' + norm(text) + ' '; low = text.lower()
    for n, k in PAIRS:
        if only is not None and k != only: continue
        if (' ' + n + ' ') not in nt: continue
        s = SHOWS[k]
        if s['rx'] and not s['rx'].search(low): continue
        return k
    return None
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def airdate(t):
    low = t.lower()
    m = re.search(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-]((19)?(8[4-9]|9\d)|(20)?0[0-4])(?!\d)', low)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = int(m.group(3)); y = y if y > 100 else (1900 + y if y >= 84 else 2000 + y)
        return '%04d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?<!\d)(19(8[4-9]|9\d)|200[0-4])[./-](\d{1,2})[./-](\d{1,2})(?!\d)', low)
    if m and 1 <= int(m.group(3)) <= 12 and 1 <= int(m.group(4)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(3)), int(m.group(4)))
    m = re.search(r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.? (\d{1,2})(st|nd|rd|th)?,? (19(8[4-9]|9\d)|200[0-4])\b', low)
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(1)[:3]], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})(st|nd|rd|th)? (jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?,? (19(8[4-9]|9\d)|200[0-4])\b', low)
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(3)[:3]], int(m.group(1)))
    m = re.search(r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?,? (19(8[4-9]|9\d)|200[0-4])\b', low)
    if m: return '%s-%02d' % (m.group(2), MON[m.group(1)[:3]])
    return ''
def era(s, title, d, y, desc=''):
    oy = [int(v) for v in re.findall(r'\d{4}', s.get('run', ''))]
    lo = max(1984, oy[0] if oy else 1984); hi = min(2004, oy[-1] if len(oy) > 1 else 2004)
    mo = re.search(r'(?<!\d)(\d{1,2})(st|nd|rd|th)\b', title.lower())
    if mo and s.get('ord') and lo <= s['ord'] + int(mo.group(1)) <= hi: return s['ord'] + int(mo.group(1))
    for src in (title, desc[:300]):
        ad = airdate(src)
        ys = ([int(ad[:4])] if ad else []) + [int(v) for v in re.findall(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', src)]
        ys = [v for v in ys if lo <= v <= hi]
        if ys: return ys[0]
    m = re.search(r"(?<!\d)'?(8[4-9]|9\d)(?!\d)", title)
    if m and lo <= 1900 + int(m.group(1)) <= hi and re.search(r"'\d\d|\b(mtv|vh1|awards|vma)\b", title.lower()): return 1900 + int(m.group(1))
    if oy and len(oy) > 1 and oy[0] >= 1984 and oy[-1] - oy[0] <= 2: return oy[0]
    ys = [int(v) for v in re.findall(r'^(19[89]\d|200[0-4])', str(d or '')[:4])] + [int(v) for v in re.findall(r'^(19[89]\d|200[0-4])', str(y or '')[:4])]
    ys = [v for v in ys if lo <= v <= hi]
    return ys[0] if ys else ''
def qtitle(t):
    return ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', t).split())
def known():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) in ('musictv.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz'): continue
        try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        for x in (j if isinstance(j, list) else []):
            if isinstance(x, dict):
                if x.get('i'): have.add(x['i'])
                ia = x.get('ia')
                if isinstance(ia, list) and ia and isinstance(ia[0], str): have.add(ia[0])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    return have
if MODE == 'plan':
    have = known()
    if os.path.exists(OUTF): have |= set(x['i'] for x in json.load(gzip.open(OUTF, 'rt', encoding='utf-8')))
    print('known', len(have), 'shows', len(SHOWS), flush=True)
    jobs = []
    for k, s in enumerate(SHOWS):
        names = [s['title']] + s.get('alt', [])
        for a in range(0, len(names), 20):
            jobs.append((k, 0, 'mediatype:movies AND title:(' + ' OR '.join('"' + qtitle(n) + '"' for n in names[a:a + 20]) + ')'))
        for q in s.get('q', []): jobs.append((k, 1, 'mediatype:movies AND ' + q))
    def find(j): return j[0], j[1], scrape(j[2])
    seen = {}; hits = collections.Counter()
    with ThreadPoolExecutor(8) as ex:
        for n, (k, loose, items) in enumerate(ex.map(find, jobs)):
            s = SHOWS[k]
            for it in items:
                i = it['identifier']
                if i in have or i in seen: continue
                t = it.get('title'); t = ' '.join(t) if isinstance(t, list) else str(t or '')
                lang = it.get('language'); lang = ' '.join(lang) if isinstance(lang, list) else str(lang or '')
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                if not ok_title(t): continue
                k2 = which(t)
                if k2 is None:
                    if not (loose and s['title'] in BLOB): continue
                    k2 = k
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': k2}; hits[k2] += 1
            if n % 20 == 0: print('search', n, len(jobs), len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    print('per show', [(SHOWS[k]['title'], n) for k, n in hits.most_common()])
    print('no candidates', [s['title'] for k, s in enumerate(SHOWS) if not hits[k]])
    with gzip.open(os.path.join(PARTS, 'musictv_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
    if not ok_title(title): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:400]).lower()
    if re.search(X_FOR, blob): return None
    if re.search(r'\b(podcast|fan ?made|video ?game|gameplay|radio (show|program|broadcast)|audio only|mtv europe|mtv uk|muchmusic|top of the pops)\b', blob): return None
    if set(col) & {'podcasts', 'audio', 'opensource_audio', 'radioprograms', 'community_media', 'newsandpublicaffairs'}: return None
    k = which(title)
    if k is None and SHOWS[it['k']]['title'] in BLOB: k = which(title + ' ' + str(subj) + ' ' + desc[:300], it['k'])
    if k is None: return None
    s = SHOWS[k]
    dy = re.match(r'(\d{4})', str(m.get('date') or ''))
    e = era(s, title, m.get('date'), m.get('year'), desc)
    if it['identifier'].startswith('youtube-') and not re.search(r'(19[89]\d|200[0-4])', title) and not e: return None
    r = {'i': it['identifier'], 'q': 'music', 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': s['title'], 'e': e, 'net': s.get('net', ''), 'ct': s['ct']}
    ad = airdate(title) or airdate(desc[:200])
    if ad: r['ad'] = ad
    return r
def keep(x):
    s = BYT.get(x.get('k'))
    return bool(s) and ok_title(x['t'])
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'musictv_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'musictv-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
old = [x for x in old0 if keep(x)]
print('refiltered existing', len(old0), '->', len(old))
have = set(x['i'] for x in old) | known(); add = []
for p in sorted(glob.glob(os.path.join(PARTS, 'musictv-*.json.gz'))):
    for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
        if x['i'] not in have: have.add(x['i']); add.append(x)
res = old + add
with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res), 'exact dates', sum(1 for x in res if len(x.get('ad', '')) == 10))
bt = collections.defaultdict(list)
for x in res: bt[x['ct']].append(x)
print('TYPE TABLE')
for t in sorted(bt): print('  %-10s items %5d  hours %6d' % (t, len(bt[t]), hrs(bt[t])))
bs = collections.defaultdict(list)
for x in res: bs[x['k']].append(x)
print('SHOW TABLE')
for s in SHOWS:
    n = len(bs[s['title']]); print('  %-8s %5d items %5d h  %s' % ('FOUND' if n >= 10 else 'THIN' if n else 'MISSING', n, hrs(bs[s['title']]), s['title']))
print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
random.seed(7)
for x in random.sample(res, min(60, len(res))): print('SAMPLE', x['ct'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', '|', x['e'], '|', x.get('ad', ''))
