import gzip, json, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_needs as Y

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'techshows.json.gz')
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
SKIP_YT = os.environ.get('SKIP_YT') == '1'

SHOWS = [
 dict(k='cc', n='THE COMPUTER CHRONICLES', y=(1983, 2002), ia='collection:(computerchronicles) OR title:("computer chronicles")', yt=['computer chronicles full episode', 'the computer chronicles 1985', 'the computer chronicles 1990', 'the computer chronicles 1995', 'the computer chronicles 2000'], rx=r'computer chronicles', md=20),
 dict(k='netcafe', n='NET CAFE', y=(1996, 2002), ia='collection:(netcafe) OR title:("net cafe" OR netcafe)', yt=['net cafe kcsm', 'net cafe internet show 1997'], rx=r'net ?cafe', md=20),
 dict(k='tss', n='THE SCREEN SAVERS', y=(1998, 2004), ia='title:("screen savers" OR screensavers)', yt=['the screen savers techtv full episode', 'the screen savers zdtv 1999', 'the screen savers 2002', 'the screen savers 2003', 'the screen savers 2004'], rx=r'screen ?savers', md=20),
 dict(k='cfh', n='CALL FOR HELP', y=(1998, 2004), ia='title:("call for help")', yt=['call for help techtv full episode', 'call for help zdtv leo laporte', 'call for help 2003 techtv'], rx=r'call for help', md=20),
 dict(k='spin', n='SILICON SPIN', y=(1998, 2002), ia='title:("silicon spin")', yt=['silicon spin zdtv', 'silicon spin john c dvorak'], rx=r'silicon spin', md=15),
 dict(k='big', n='BIG THINKERS', y=(1998, 2002), ia='title:("big thinkers")', yt=['big thinkers techtv', 'big thinkers zdtv'], rx=r'big thinkers', md=15),
 dict(k='fresh', n='FRESH GEAR', y=(1998, 2002), ia='title:("fresh gear")', yt=['fresh gear zdtv', 'fresh gear techtv'], rx=r'fresh gear', md=15),
 dict(k='live', n='TECH LIVE', y=(2001, 2002), ia='title:("tech live" OR techlive)', yt=['tech live techtv 2001', 'techlive techtv'], rx=r'tech ?live', md=15),
 dict(k='xp', n='EXTENDED PLAY', y=(1998, 2003), ia='title:("extended play") AND (techtv OR zdtv)', yt=['extended play techtv', 'extended play zdtv'], rx=r'extended play', md=15),
 dict(k='xplay', n='X-PLAY', y=(2003, 2004), ia='title:("x-play" OR xplay)', yt=['x-play g4techtv 2004 full episode', 'x-play 2003 techtv'], rx=r'\bx-?play\b', md=15),
 dict(k='cyber', n='CYBERCRIME', y=(2002, 2004), ia='title:(cybercrime) AND (techtv OR "tech tv")', yt=['cybercrime techtv show'], rx=r'cyber ?crime', md=15),
 dict(k='unscr', n='UNSCREWED', y=(2002, 2004), ia='title:(unscrewed) AND (techtv OR "tech tv")', yt=['unscrewed with martin sargent'], rx=r'unscrewed', md=15),
 dict(k='cnet', n='CNET CENTRAL', y=(1995, 1999), ia='title:("cnet central" OR "c|net central" OR "c-net central")', yt=['cnet central 1996', 'c|net central show', 'cnet central richard hart'], rx=r'c\W?net central', md=15),
 dict(k='tvcom', n='TV.COM', y=(1996, 2000), ia='title:("tv.com") AND (cnet OR show)', yt=['tv.com cnet syndicated show', 'cnet tv.com 1998'], rx=r'\btv\.com\b', md=15),
 dict(k='edge', n='THE NEW EDGE', y=(1996, 2000), ia='title:("the new edge") AND cnet', yt=['the new edge cnet sci fi channel'], rx=r'new edge', md=15),
 dict(k='site', n='THE SITE', y=(1996, 1997), ia='title:("the site") AND (msnbc OR soledad)', yt=['the site msnbc soledad o\'brien', 'msnbc the site 1996', 'the site 1997 msnbc'], rx=r'\bthe site\b', md=15),
 dict(k='duo', n='DIGITAL DUO', y=(1997, 2002), ia='title:("digital duo")', yt=['digital duo pbs', 'digital duo stephen manes'], rx=r'digital duo', md=15),
 dict(k='bowl', n='COMPUTER BOWL', y=(1988, 1995), ia='title:("computer bowl")', yt=['computer bowl', 'the computer bowl 1990'], rx=r'computer bowl', md=20),
 dict(k='ntt', n='THE NEW TECH TIMES', y=(1983, 1986), ia='title:("new tech times")', yt=['new tech times pbs', 'the new tech times 1984'], rx=r'new tech times', md=15),
 dict(k='next', n='THE NEXT STEP', y=(1991, 2000), ia='title:("the next step") AND discovery', yt=['the next step discovery channel 1992', 'the next step discovery channel technology'], rx=r'the next step', md=20),
 dict(k='gpro', n='GAMEPRO TV', y=(1991, 1993), ia='title:("gamepro tv" OR "game pro tv")', yt=['gamepro tv 1991', 'gamepro tv j.d. roth', 'gamepro tv 1992'], rx=r'game ?pro tv', md=15),
 dict(k='vpow', n='VIDEO POWER', y=(1990, 1992), ia='collection:(video_power) OR title:("video power")', yt=['video power 1990 full episode', 'video power stivi paskoski', 'video power 1991 game show'], rx=r'video power', md=15),
 dict(k='narc', n='NICK ARCADE', y=(1992, 1993), ia='collection:(nickarcade) OR title:("nick arcade")', yt=['nick arcade full episode', 'nick arcade 1992'], rx=r'nick arcade', md=20),
 dict(k='star', n='STARCADE', y=(1982, 1984), ia='collection:(starcade) OR title:(starcade)', yt=['starcade full episode', 'starcade 1983 game show'], rx=r'starcade', md=20),
 dict(k='nerds', n='TRIUMPH OF THE NERDS', y=(1996, 1996), ia='title:("triumph of the nerds")', yt=['triumph of the nerds pbs'], rx=r'triumph of the nerds', md=40),
 dict(k='nerds2', n='NERDS 2.0.1', y=(1998, 1998), ia='title:("nerds 2.0.1")', yt=['nerds 2.0.1 pbs'], rx=r'nerds 2\.?0\.?1', md=40),
]
BAD = re.compile(r"(?i)\b(reaction|reacts|review(ed)? \(20|podcast|trailer|teaser|clips?|excerpts?|highlights?|recap|remix|parody|tribute|unboxing|livestream|live stream|twitch|let'?s play|longplay|speedrun|walkthrough|gameplay|playthrough|oakleytapes|mega ?mix|top \d+|ranked|ranking|explained|what happened to|where are they now|documentary about|reunion|this week in tech|twit|the lab with leo|tech ?tv canada|g4 ?tech ?tv canada)\b")
LANG = re.compile(r"(?i)(-|\(|\[|:)\s*(arabic|french|spanish|español|espanol|german|deutsch|chinese|japanese|portuguese|russian|italian)\b|\b(arabic|french|spanish|german|chinese|japanese|portuguese|russian|italian) (version|dub|dubbed|language)\b|\b(doblado|dublado|legendado|subtitulado)\b")
MODERN = re.compile(r'(?<!\d)20(0[5-9]|1\d|2\d)(?!\d)')
DUB = re.compile(r'(?i)^(ar|sp|fr|ch|jp|pt|ru|de|es)_')
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def y2(y):
    y = int(y)
    return y + (1900 if y >= 70 else 2000) if y < 100 else y


def text_date(s, lo=1980, hi=2004):
    s = s or ''
    ok = lambda y: lo <= y <= hi
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])[-./](\d{1,2})[-./](\d{1,2})(?!\d)', s)
    if m and ok(int(m.group(1))) and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', s)
    if m and ok(int(m.group(3))): return '%s-%02d-%02d' % (m.group(3), MON[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'(?i)\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[89]\d|200[0-4])\b', s)
    if m and ok(int(m.group(3))): return '%s-%02d-%02d' % (m.group(3), MON[m.group(2).lower()], int(m.group(1)))
    m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](19[89]\d|200[0-4]|[89]\d|0[0-4])(?!\d)', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31 and ok(y2(m.group(3))): return '%d-%02d-%02d' % (y2(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[89]\d|200[0-4])\b', s)
    if m and ok(int(m.group(2))): return '%s-%02d' % (m.group(2), MON[m.group(1).lower()])
    m = re.search(r'(?<!\d)(198\d|199\d|200[0-4])(?!\d)', s)
    if m and ok(int(m.group(1))): return m.group(1)
    return ''


def fit_date(d, S):
    if not d: return ''
    y = int(d[:4])
    if S['y'][0] - 1 <= y <= S['y'][1] + 1: return d
    return ''


def ep_title(t, S):
    e = re.sub(r'(?i)\bthe\s+(?=' + S['rx'] + ')', ' ', t)
    e = re.sub(r'(?i)' + S['rx'], ' ', e)
    e = re.sub(r'(?i)re-?digiti[sz]ation project:?\s*', ' ', e)
    e = re.sub(r'(?i)\b(full episode|full show|episode|ep\.?|season \d+|s\d+e\d+|zdtv|techtv|tech tv|g4techtv|g4|pbs|kcsm|msnbc|cnet|1080p|720p|hd|vhs|rip|complete|original broadcast|with commercials|w/ commercials)\b', ' ', e)
    e = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', e)
    e = re.sub(r'(?<!\d)(19[89]\d|200[0-4])[-./]\d{1,2}[-./]\d{1,2}(?!\d)', ' ', e)
    e = re.sub(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b', ' ', e)
    e = re.sub(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?,?', ' ', e)
    e = re.sub(r'[|_~]+', ' ', e)
    e = re.sub(r'\s*-\s*(-\s*)+', ' - ', e)
    e = re.sub(r'\s+', ' ', e).strip(' -:,.#|"\'')
    e = re.sub(r'^\d{3,4}[A-Z]?\b\s*[-:]?\s*', '', e).strip(' -:,.')
    if re.fullmatch(r'[-\d/.,\s#]*', e): e = ''
    return e[:60]


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True)
                return None
            time.sleep(3 * (k + 1))


def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor or len(out) > 20000: break
    return out


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
WHY = collections.Counter()


def ia_meta(arg):
    it, S = arg
    i = it['identifier']
    if DUB.match(i) or i.lower().startswith(('oakleytapes', 'youtube-', 'tobacco_')): WHY['skipid'] += 1; return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(i))
    if not j or not j.get('files') or j.get('is_dark'): WHY['dark'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': WHY['restricted'] += 1; return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en', str(lang)): WHY['lang'] += 1; return None
    title = m.get('title', '')
    if isinstance(title, list): title = ' '.join(title)
    title = str(title)
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = re.sub(r'<[^>]+>', ' ', str(desc))
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    if S['k'] != 'cc' and not re.search(S['rx'], (title + ' ' + i.replace('_', ' ').replace('-', ' ')).lower()) and not set(col) & {'netcafe', 'video_power', 'nickarcade', 'starcade'}: WHY['nomatch'] += 1; return None
    if LANG.search(title) or (S['k'] != 'cc' and BAD.search(title)): WHY['bad'] += 1; return None
    if MODERN.search(title) and not re.search(r'(19[89]\d|200[0-4])', title): WHY['modern'] += 1; return None
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
        du = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if du < 120: continue
        files.append([b['name'], round(du)])
    if not files: WHY['nofiles'] += 1; return None
    files.sort(key=lambda f: f[0])
    if len(files) > 1:
        a, z = min(f[1] for f in files), max(f[1] for f in files)
        if z / max(a, 1) < 1.15 and z >= S['md'] * 60 and S['k'] in ('cc', 'netcafe', 'bowl', 'ntt', 'duo', 'site'):
            files = [sorted(files, key=lambda f: ('raw' in f[0].lower(), f[0]))[0]]
    tot = sum(f[1] for f in files)
    if tot < S['md'] * 60: WHY['short'] += 1; return None
    if tot > 4 * 3600: WHY['long'] += 1; return None
    md = str(m.get('date') or '')
    d = ''
    mm = re.match(r'(\d{4})-(\d{2})-(\d{2})', md)
    if mm and not (mm.group(2) == '01' and mm.group(3) == '01'): d = fit_date(mm.group(0), S)
    if not d or len(d) < 10:
        td = fit_date(text_date(title), S) or fit_date(text_date(desc[:800]), S)
        if len(td) > len(d): d = td
    if not d:
        mm = re.match(r'(\d{4})', md)
        d = fit_date(mm.group(1), S) if mm else ''
    if not d and str(m.get('year', '')).isdigit(): d = fit_date(str(m.get('year')), S)
    ep = ep_title(title, S) if S['k'] != 'cc' or re.search(S['rx'], title.lower()) else title.strip()[:60]
    ep = re.sub(r'(?i)\s*-\s*(english)$', '', ep)
    return {'i': i, 'src': 'ia', 'show': S['k'], 'n': S['n'], 'ep': ep, 'ad': d, 'dq': 0 if d else 1, 't': title[:160], 'f': files[:24]}


res, seen = [], set()
if os.path.exists(OUT):
    for x in json.load(gzip.open(OUT, 'rt', encoding='utf-8')):
        if x['i'] not in seen: seen.add(x['i']); res.append(x)
print('existing', len(res), flush=True)
T0 = time.time()
jobs = []
for S in SHOWS:
    items = scrape('(' + S['ia'] + ') AND mediatype:movies')
    n = 0
    for it in items:
        if it['identifier'] in seen: continue
        seen.add(it['identifier']); jobs.append((it, S)); n += 1
    print('ia', S['k'], len(items), 'new', n, flush=True)
with ThreadPoolExecutor(12) as ex:
    for r in ex.map(ia_meta, jobs):
        if r: res.append(r)
print('ia done', len(res), dict(WHY), round((time.time() - T0) / 60, 1), 'min', flush=True)
json.dump(res, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if not SKIP_YT:
    yseen = set(x['vid'] for x in res if x.get('vid'))
    have_key = set((x['show'], x['ep'].lower(), x['ad']) for x in res)
    order = SHOWS[:]
    random.shuffle(order)
    for S in order:
        if Y.left() < 300: break
        cands = []
        try:
            for p in Y.search_playlists(S['yt'][0])[:4]:
                if not re.search(S['rx'], (p.get('t') or '').lower()): continue
                cands += Y.playlist_videos(p['pid'], maxpages=10)
                time.sleep(0.5 + random.random())
        except Exception as e:
            print('pl fail', S['k'], e, flush=True)
        for q in S['yt']:
            if Y.left() < 300: break
            try: cands += Y.search(q, pages=2)
            except Exception: pass
            time.sleep(0.6 + random.random())
        n = 0
        for c in cands:
            t = c.get('t') or ''
            low = t.lower()
            dur = c.get('dur') or 0
            if not c.get('vid') or c['vid'] in yseen or c.get('live'): continue
            if dur < S['md'] * 60 or dur > 4 * 3600: continue
            if not re.search(S['rx'], low) or BAD.search(t) or LANG.search(t): continue
            if MODERN.search(t) and not re.search(r'(19[89]\d|200[0-4])', t): continue
            d = fit_date(text_date(t), S)
            yrs = [int(v) for v in re.findall(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', t)]
            if yrs and not d: continue
            ep = ep_title(t, S)
            key = (S['k'], ep.lower(), d)
            if ep and key in have_key: continue
            have_key.add(key)
            yseen.add(c['vid'])
            res.append({'i': 'yt:' + c['vid'], 'src': 'yt', 'vid': c['vid'], 'show': S['k'], 'n': S['n'], 'ep': ep, 'ad': d, 'dq': 0 if d else 1, 't': t[:160], 'ch': c.get('ch', ''), 'dur': dur, 'views': c.get('views', 0)})
            n += 1
        print('yt', S['k'], 'cands', len(cands), 'added', n, 'left', round(Y.left() / 60), 'min', flush=True)
        json.dump(res, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

json.dump(res, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
c = collections.Counter(x['show'] for x in res)
h = collections.Counter()
for x in res: h[x['show']] += (x.get('dur') or sum(f[1] for f in x.get('f', []))) / 3600
for S in SHOWS: print('show', S['n'], c[S['k']], round(h[S['k']]), 'h', flush=True)
print('total', len(res), 'dated', sum(1 for x in res if x['ad']), 'day-dated', sum(1 for x in res if len(x['ad']) == 10))
