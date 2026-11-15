import gzip, json, os, re, sys, time, random, datetime, collections, urllib.request, urllib.parse, concurrent.futures
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_events as Y

MODE = os.environ.get('MODE', 'plan')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'parts')
OUT = os.path.join(ROOT, 'catalog', 'capitol.json.gz')
USED = os.path.join(ROOT, 'catalog', 'yt_used.txt.gz')
T0 = time.time()
BUDGET = float(os.environ.get('BUDGET_MIN', '200')) * 60
STATS = collections.Counter()

CHANS = {
 'cspan': ('C-SPAN', 'search'), 'ReaganLibrary': ('Reagan Library', 'all'), 'ReaganFoundation': ('Reagan Foundation', 'all'),
 'Bush41Library': ('George H.W. Bush Presidential Library', 'all'), 'GeorgeBushLibrary41': ('George Bush Presidential Library', 'all'),
 'ClintonLibrary42': ('Clinton Presidential Library', 'all'), 'WJClibrary42': ('William J. Clinton Presidential Library', 'all'),
 'GeorgeWBushLibrary': ('George W. Bush Presidential Library', 'all'), 'BushCenter': ('George W. Bush Presidential Center', 'all'),
 'MillerCenter': ('Miller Center', 'all'), 'USNationalArchives': ('US National Archives', 'all'), 'ClintonFoundation': ('Clinton Foundation', 'all'),
 'CarterCenter': ('The Carter Center', 'all'), 'NixonFoundation': ('Richard Nixon Foundation', 'all'), 'ussenatehistory': ('U.S. Senate Historical Office', 'all'),
}
TOPICS = ['house', 'senate', 'hearing', 'address', 'speech', 'press conference', 'news conference', 'campaign', 'convention', 'debate', 'briefing', 'supreme court',
          'booknotes', 'call-in', 'rally', 'floor', 'vote', 'funeral', 'inauguration', 'summit', 'interview', 'testimony', 'remarks', 'governor', 'budget']
GEN = ['c-span {y}', 'cspan {y}', 'c-span {y} house floor', 'c-span {y} senate floor', 'c-span {y} hearing', 'c-span {y} speech', 'c-span {y} press conference', 'c-span {y} campaign',
       'house of representatives floor {y}', 'senate floor debate {y}', 'congressional hearing {y} full', 'senate hearing {y} full', 'house hearing {y} full', 'white house press briefing {y}',
       'presidential press conference {y}', 'national press club {y}', 'campaign speech {y} full', 'booknotes {y}', 'washington journal {y}', 'president remarks {y} full', 'senate confirmation hearing {y}',
       'governor state of the state {y}', 'mayor inaugural address {y}']
EVENTS = ['iran contra hearings 1987', 'oliver north testimony 1987', 'bork confirmation hearing 1987', 'kennedy confirmation hearing 1987', 'scalia confirmation hearing 1986', 'rehnquist confirmation hearing 1986',
          'souter confirmation hearing 1990', 'thomas confirmation hearing 1991', 'anita hill testimony 1991', 'ginsburg confirmation hearing 1993', 'breyer confirmation hearing 1994', 'tower nomination hearing 1989',
          'keating five hearings', 'gulf war resolution debate january 1991', 'house debate persian gulf 1991', 'senate debate persian gulf 1991', 'jim wright resignation speech 1989', 'gingrich sworn in speaker 1995',
          'contract with america 1995 house', 'government shutdown 1995 house floor', 'nafta debate house 1993', 'gore perot nafta debate 1993', 'clinton health care address congress 1993', 'hillary clinton health care testimony 1993',
          'tobacco executives testimony 1994', 'whitewater hearings 1995', 'waco hearings 1995', 'ruby ridge hearings 1995', 'house impeachment debate december 1998', 'senate impeachment trial clinton 1999',
          'kenneth starr testimony 1998', 'clinton grand jury testimony 1998', 'bush address joint session september 20 2001', 'iraq war resolution debate 2002', 'patriot act debate 2001', '9/11 commission hearing 2004',
          'condoleezza rice 9/11 commission testimony', 'abu ghraib hearing 2004', 'bush v gore oral arguments 2000', 'florida recount coverage 2000', 'challenger hearings 1986', 'savings and loan hearings 1989',
          'house bank scandal 1992', 'line item veto debate', 'balanced budget amendment debate 1995', 'flag burning amendment debate', 'brady bill debate 1993', 'crime bill debate 1994', 'welfare reform debate 1996',
          'reagan farewell address 1989', 'reagan address iran contra 1987', 'bush address to the nation 1990', 'clinton oval office address', 'clinton press conference 1993', 'reagan press conference 1987', 'bush press conference 1991',
          'perot press conference 1992', 'dukakis speech 1988', 'dole speech 1996', 'jesse jackson speech 1988', 'gore speech 2000', 'bush campaign rally 2000', 'kerry speech 2004', 'dean scream speech 2004',
          'iowa caucus 1988', 'new hampshire primary 1992', 'presidential debate 1984 full', 'vice presidential debate 1988 full', 'presidential debate 1992 full', 'presidential debate 1996 full', 'presidential debate 2000 full', 'presidential debate 2004 full',
          'democratic national convention 1984 full', 'republican national convention 1988 full', 'democratic national convention 1992 full', 'republican national convention 1996 full', 'democratic national convention 2000 full', 'republican national convention 2004 full',
          'prime minister questions 1990', 'prime minister questions 1995', 'house of commons c-span 1989', 'national governors association 1990', 'national prayer breakfast 1995', 'state funeral 2004 reagan capitol',
          'nixon funeral 1994', 'thurgood marshall funeral 1993', 'tip oneill funeral 1994', 'national press club luncheon 1990', 'c-span call in 1990', 'c-span road to the white house 1992', 'c-span america and the courts',
          'mcnamara hearing', 'ollie north', 'poindexter testimony', 'mcfarlane testimony', 'ames spy hearing 1994', 'hanssen 2001 hearing', 'enron hearing 2002', 'worldcom hearing 2002', 'trent lott 2002', 'tom daschle 2001 speech']
JUNK = re.compile(r"(?i)\b(reaction|reacts?|review|podcast|documentary|anniversary|years later|years ago|explained|remembering|tribute|recap|highlights?|clips?|trailer|teaser|#shorts|shorts|lecture|professor|historian|oral history|american history tv|reel america|lectures in history|q ?& ?a\b|after words|in depth|book tv|booktv|history bookshelf|then and now|flashback|looking back|look back|throwback|this day in|on this day|retrospective|parody|snl|saturday night live|skit|sketch|cartoon|animated|meme|remix|compilation|best of|top \d+|funniest|worst|exposed|destroys|rant|vlog|unboxing|minecraft|roblox|game ?play|speedrun|ai voice|ai generated|deepfake|colorized|restored|4k|upscaled?|60 ?fps|lyrics|music video|official video)\b")
FOREIGN = re.compile(r"(?i)[^\x00-\x7f]{4,}|\b(español|espanol|deutsch|français|francais|italiano|legendado|dublado|latino|subtitulado|untertitel)\b")
KINDS = [('house', r'\b(house (floor|session|of representatives|debate|vote|proceedings)|floor of the house|house votes?)\b'), ('senate', r'\b(senate (floor|session|debate|vote|proceedings)|floor of the senate|senate votes?)\b'),
         ('hearing', r'\b(hearings?|testimony|testifies|testify|confirmation|subcommittee|committee)\b'), ('debate', r'\b(debate|debates)\b'), ('convention', r'\bconvention\b'), ('presser', r'\b(press conference|news conference|press briefing|briefing)\b'),
         ('booknotes', r'\bbooknotes\b'), ('callin', r'\b(call-in|call in|washington journal|viewers? calls?)\b'), ('funeral', r'\b(funeral|memorial service|lying in state|state funeral)\b'),
         ('inauguration', r'\b(inaugurat\w*|sworn in|swearing[- ]in|oath of office)\b'), ('sotu', r'\b(state of the union|joint session|address to congress|address before)\b'), ('commons', r"\b(prime minister'?s questions|house of commons|parliament)\b"),
         ('campaign', r'\b(campaign|rally|stump|caucus|primary|nomination|acceptance speech)\b'), ('speech', r'\b(address|speech|remarks|speaks|delivers|statement|oval office|farewell)\b')]
GOVW = re.compile(r"(?i)\b(president\w*|senat\w*|congress\w*|house of representatives|house floor|capitol|white house|governor|mayor|supreme court|justice|secretary|committee|hearings?|testimony|c-?span|campaign|candidate|convention|caucus|primary|reagan|bush|clinton|gore|dole|perot|dukakis|mondale|quayle|cheney|kerry|edwards|lieberman|gingrich|o'?neill|jim wright|foley|hastert|byrd|daschle|lott|kemp|buchanan|nader|jackson|ferraro|white house|pentagon|state department|fbi|cia|nasa|federal|attorney general|ambassador|prime minister|parliament|united nations|press club|nomination|impeach\w*|iran-?contra|budget|legislat\w*|lawmakers|politic\w*|election)\b")

def resolve_all():
    ch = {}
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for h, c in zip(CHANS, ex.map(Y.resolve, CHANS)):
            if c: ch[h] = c
    for h in [h for h in CHANS if h not in ch]:
        c = Y.findch(CHANS[h][0])
        if c: ch[h] = c
    print('channels resolved', sorted(ch.items()), 'missing', [h for h in CHANS if h not in ch], flush=True)
    return ch

def enum(chid, h):
    out = []
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'playlistend': 9000}) as yd:
            r = yd.extract_info('https://www.youtube.com/channel/' + chid + '/videos', download=False)
        for e in (r or {}).get('entries') or []:
            if e and e.get('id'): out.append({'vid': e['id'], 't': e.get('title') or '', 'ch': (r or {}).get('channel') or h, 'chid': chid, 'dur': int(e.get('duration') or 0), 'ver': 1, 'ago': '', 'vc': str(e.get('view_count') or ''), 'sn': (e.get('description') or '')[:400], 'src': 'a:' + h})
    except Exception as ex:
        STATS['enumfail'] += 1; print('enum fail', h, str(ex)[:200], flush=True)
    return out

def probe_site():
    for u in ('https://www.c-span.org/', 'https://www.c-span.org/video/?1185-1/state-union-address', 'https://www.c-span.org/about/copyright-policy/'):
        try:
            rq = urllib.request.Request(u, headers={'User-Agent': Y.UA, 'Accept': 'text/html'})
            with urllib.request.urlopen(rq, timeout=25) as r:
                b = r.read().decode('utf-8', 'replace')
                print('site', r.status, len(b), u, re.findall(r'https?://[^"\' ]+\.(?:m3u8|mp4)[^"\' ]*', b)[:3], re.findall(r'standalone[^"\' ]{0,80}', b)[:2], flush=True)
        except urllib.error.HTTPError as e: print('site', e.code, u, flush=True)
        except Exception as e: print('site err', u, str(e)[:120], flush=True)

def years_in(t):
    return [int(y) for y in re.findall(r'(?<!\d)(19[0-9]\d|20[0-3]\d)(?!\d)', t or '')]

def pre(r):
    t = r['t']
    if not t or FOREIGN.search(t): return 'foreign'
    if JUNK.search(t): return 'junk'
    if r['dur'] and (r['dur'] < 600 or r['dur'] > 11 * 3600): return 'length'
    ys = years_in(t)
    if ys and not any(1984 <= y <= 2004 for y in ys): return 'era'
    if any(y > 2004 for y in ys): return 'era'
    return ''

def plan():
    os.makedirs(PARTS, exist_ok=True)
    probe_site()
    ch = resolve_all(); cands = {}
    def add(L):
        for r in L:
            if r and r.get('vid') and r['vid'] not in cands: cands[r['vid']] = r
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for h, L in zip([h for h in ch if CHANS[h][1] == 'all'], ex.map(lambda h: enum(ch[h], h), [h for h in ch if CHANS[h][1] == 'all'])):
            print('enumerated', h, len(L), flush=True); add(L)
    jobs = []
    for h in [h for h in ch if CHANS[h][1] == 'search']:
        for y in range(1984, 2005):
            jobs.append((h, str(y)))
            for tp in TOPICS: jobs.append((h, tp + ' ' + str(y)))
    def cs(j):
        if time.time() - T0 > BUDGET * 0.4: return []
        return Y.chsearch(ch[j[0]], j[1], j[0], pages=3)
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for L in ex.map(cs, jobs): add(L)
    print('after channel search', len(cands), dict(Y.STATS), flush=True)
    Q = [g.format(y=y) for y in range(1984, 2005) for g in GEN] + EVENTS
    random.Random(5).shuffle(Q)
    def sq(q):
        if time.time() - T0 > BUDGET * 0.85: return []
        return Y.search(q, pages=2, long=False, src='q:' + q)
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for L in ex.map(sq, Q): add(L)
    print('after search', len(cands), dict(Y.STATS), flush=True)
    used = set()
    if os.path.exists(USED): used = set(l.strip().replace('yt:', '') for l in gzip.open(USED, 'rt', encoding='utf-8') if l.strip())
    off = set(ch.values()); keep = []; drop = collections.Counter()
    for r in cands.values():
        if r['vid'] in used: drop['have'] += 1; continue
        w = pre(r)
        if w: drop[w] += 1; continue
        r['off'] = 1 if r.get('chid') in off else 0
        keep.append(r)
    print('kept', len(keep), 'dropped', dict(drop), flush=True)
    json.dump({'cands': keep, 'ch': ch}, gzip.open(os.path.join(PARTS, 'cap_cands.json.gz'), 'wt', encoding='utf-8'))

def describe(vid):
    d = Y.post('next', {'context': {'client': Y.WEB}, 'videoId': vid})
    if not d: return '', ''
    out = []
    for a in Y.walk(d, 'attributedDescription', []):
        if isinstance(a, dict): out.append(str(a.get('content') or ''))
    for a in Y.walk(d, 'description', []):
        if isinstance(a, dict): out.append(Y.txt(a))
    dt = ''
    for a in Y.walk(d, 'dateText', []):
        if isinstance(a, dict): dt = Y.txt(a) or dt
    return re.sub(r'\s+', ' ', ' '.join(x for x in out if x))[:2000], dt

def meta_one(r):
    if time.time() - T0 > BUDGET: return None
    oe = Y.oembed(r['vid'])
    if oe != 200: return {'oe': oe}
    ds, dt = ('', '')
    if not Y.dates_in(r['t']): ds, dt = describe(r['vid'])
    return {'oe': oe, 'ds': ds, 'dt': dt}

def meta():
    S = int(os.environ.get('SHARD', '0')); N = int(os.environ.get('SHARDS', '1'))
    d = json.load(gzip.open(os.path.join(PARTS, 'cap_cands.json.gz'), 'rt', encoding='utf-8'))
    C = [r for i, r in enumerate(sorted(d['cands'], key=lambda r: r['vid'])) if i % N == S]
    out = []
    with concurrent.futures.ThreadPoolExecutor(int(os.environ.get('THREADS', '6'))) as ex:
        for r, m in zip(C, ex.map(meta_one, C)):
            if m: r = dict(r); r['m'] = m; out.append(r)
    print('shard', S, len(C), 'done', len(out), collections.Counter(r['m']['oe'] for r in out).most_common(8), dict(Y.STATS), flush=True)
    json.dump(out, gzip.open(os.path.join(PARTS, 'cap-%d.json.gz' % S), 'wt', encoding='utf-8'))

def kind(t, ds):
    low = (t or '').lower()
    for k, rx in KINDS:
        if re.search(rx, low): return k
    low = (ds or '')[:300].lower()
    for k, rx in KINDS:
        if re.search(rx, low): return k
    return 'other'

def merge():
    d = json.load(gzip.open(os.path.join(PARTS, 'cap_cands.json.gz'), 'rt', encoding='utf-8')); ch = d['ch']; offn = {v: k for k, v in ch.items()}
    rows = []
    for fn in sorted(os.listdir(PARTS)):
        if re.match(r'cap-\d+\.json\.gz$', fn): rows += json.load(gzip.open(os.path.join(PARTS, fn), 'rt', encoding='utf-8'))
    prev = {}
    if os.path.exists(OUT):
        try: prev = {x['i']: x for x in json.load(gzip.open(OUT, 'rt', encoding='utf-8'))}
        except Exception: prev = {}
    rej = collections.Counter(); items = dict(prev)
    for r in rows:
        m = r['m']; t = r['t']
        if m['oe'] != 200: rej['noembed:' + str(m['oe'])] += 1; continue
        if not r['dur']: rej['nodur'] += 1; continue
        ds = m.get('ds') or r.get('sn') or ''
        if JUNK.search(ds[:200]) and not r.get('off'): rej['descjunk'] += 1; continue
        ad, src = '', ''
        dt = Y.dates_in(t)
        if dt: ad, src = dt[0][1], 'title'
        ys = [y for y in years_in(t) if 1984 <= y <= 2004]
        if not ad:
            dd = [x[1] for x in Y.dates_in(ds[:700])]
            mt = [x for x in dd if ys and int(x[:4]) in ys]
            if mt: ad, src = mt[0], 'desc+title'
            elif dd and r.get('off') and offn.get(r.get('chid'), '') != 'cspan' and not re.search(r'(?i)\b(years|anniversary|remember|recalls?|looks? back|reflect)', ds[:300]): ad, src = dd[0], 'desc'
        if not ad: rej['nodate'] += 1; continue
        if not ('1984-01-01' <= ad <= '2004-12-31'): rej['range'] += 1; continue
        if not r.get('off') and not GOVW.search(t + ' ' + ds[:300]): rej['notgovword'] += 1; continue
        k = kind(t, ds)
        if k == 'other' and not r.get('off') and not re.search(r'(?i)c-?span', t + ' ' + r.get('ch', '') + ' ' + ds[:300]): rej['notgov'] += 1; continue
        vw = int(re.sub(r'[^0-9]', '', (r.get('vc') or '').split(' view')[0]) or 0)
        items['yt:' + r['vid']] = {'i': 'yt:' + r['vid'], 'vid': r['vid'], 't': t, 'ch': r.get('ch', ''), 'chid': r.get('chid', ''), 'off': r.get('off', 0), 'dur': r['dur'], 'views': vw, 'ad': ad, 'as': src, 'e': int(ad[:4]), 'ct': k, 'cs': 1 if re.search(r'(?i)c-?span', t + ' ' + r.get('ch', '') + ' ' + ds[:400]) else 0, 'src': r.get('src', '')}
    best = {}
    for x in sorted(items.values(), key=lambda x: (x['ad'], x['i'])):
        key = (x['ad'], x['ct'], ' '.join(sorted(set(w for w in Y.norm(x['t']).split() if len(w) > 3 and not w.isdigit()))[:5]))
        o = best.get(key)
        if not o or (x['off'], x['dur'], x['views']) > (o['off'], o['dur'], o['views']): best[key] = x
    L = sorted(best.values(), key=lambda x: (x['ad'], x['i']))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(L, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('rows', len(rows), 'rejected', dict(rej))
    print('TOTAL', len(L), 'hours', round(sum(x['dur'] for x in L) / 3600), 'official', sum(x['off'] for x in L), 'c-span', sum(x['cs'] for x in L), 'days', len(set(x['ad'] for x in L)))
    for nm, f in (('kind', lambda x: x['ct']), ('year', lambda x: x['e']), ('channel', lambda x: x['ch']), ('datesrc', lambda x: x['as'])):
        c = collections.Counter(f(x) for x in L)
        print(nm, sorted(c.items()) if nm == 'year' else c.most_common(40))
    hy = collections.Counter()
    for x in L: hy[x['e']] += x['dur']
    print('hours by year', sorted((y, round(s / 3600)) for y, s in hy.items()))
    for x in random.Random(4).sample(L, min(100, len(L))): print('SAMPLE', x['ad'], x['ct'], x['off'], x['cs'], x['dur'] // 60, 'min', '|', x['ch'][:24], '|', x['t'][:90], '|', x['as'])

if __name__ == '__main__':
    if MODE == 'plan': plan()
    elif MODE == 'meta': meta()
    elif MODE == 'merge': merge()
