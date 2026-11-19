import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '16'))
PER = int(os.environ.get('PER', '3500'))
BUDGET = float(os.environ.get('BUDGET_MIN', '150')) * 60
T0 = time.time()
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
BASE = 'mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
Q = [
 ('stationid', 'title:("station id" OR "station ids" OR "station ident" OR "station idents" OR "station identification" OR "legal id" OR "legal ids")'),
 ('bumper', 'title:(bumper OR bumpers OR ident OR idents OR interstitial OR interstitials OR "be right back" OR "now back to")'),
 ('promo', 'title:(promo OR promos OR "fall preview" OR "must see tv" OR tgif OR "coming up next" OR "tonight on" OR "sweeps" OR "fall lineup" OR "fall campaign" OR "image campaign")'),
 ('newsbrk', 'title:("news break" OR newsbreak OR "news update" OR "news teaser" OR "news tease" OR "news promo" OR "news open" OR "news opens" OR "news intro" OR newsbrief OR "news brief")'),
 ('psa', 'title:(psa OR psas OR "public service announcement" OR "public service announcements" OR "ad council" OR "the more you know" OR "one to grow on" OR "cbs cares" OR mcgruff OR "this is your brain" OR "smokey bear" OR "smokey the bear" OR "schoolhouse rock" OR "time for timer" OR "in the news" OR "just say no" OR "drug free america" OR "crash test dummies" OR "woodsy owl")'),
 ('signoff', 'title:("sign off" OR "sign-off" OR signoff OR "sign on" OR "sign-on" OR signon OR "national anthem" OR sermonette OR "test pattern" OR "color bars" OR "off the air" OR "end of broadcast day")'),
 ('ebs', 'title:("emergency broadcast" OR "emergency alert" OR "eas test" OR "ebs test" OR "eas alert" OR "weekly test" OR "monthly test")'),
 ('techdiff', 'title:("technical difficulties" OR "please stand by" OR "stand by")'),
 ('cablefill', 'title:(prevue OR "tv guide channel" OR "preview guide" OR "pay-per-view" OR "pay per view" OR barker OR "bulletin board" OR "community calendar" OR "community bulletin" OR "local origination" OR "free preview" OR "request tv" OR "viewer\'s choice" OR "time and temperature" OR "cable guide" OR "classified channel" OR "cable company" OR "cablevision promo" OR "epg")'),
 ('weather', 'title:(weatherstar OR "weather star" OR "local forecast" OR "local on the 8s" OR "weather channel" OR weatherscan)'),
 ('moviech', 'title:("feature presentation" OR "hbo intro" OR "hbo intros" OR "hbo coming attractions" OR "hbo behind the scenes" OR "hbo promo" OR "hbo promos" OR "hbo bumper" OR "hbo bumpers" OR "hbo short" OR "showtime intro" OR "showtime promo" OR "showtime promos" OR "cinemax intro" OR "cinemax promo" OR "cinemax promos" OR "movie channel promo" OR "hbo interstitial" OR "hbo next on")'),
 ('kidint', 'title:("nick at nite promo" OR "nick at nite promos" OR "nickelodeon bumper" OR "nickelodeon bumpers" OR "nickelodeon ident" OR "nickelodeon idents" OR "nickelodeon promo" OR "nickelodeon promos" OR "nick bumpers" OR "nick promos" OR "cartoon network bumper" OR "cartoon network bumpers" OR "cartoon network promo" OR "cartoon network promos" OR groovies OR "disney channel promo" OR "disney channel promos" OR "disney channel bumper" OR "disney channel bumpers" OR dtv OR "mtv ident" OR "mtv idents" OR "mtv id" OR "mtv ids" OR "mtv promo" OR "mtv promos" OR "vh1 promo" OR "vh1 promos" OR "vh1 ident" OR "toonami promo" OR "toonami promos" OR "toonami bumpers" OR "fox kids promo" OR "fox kids promos" OR "fox kids bumpers" OR "kids wb promo" OR "kids wb promos" OR "short films by short people")'),
 ('shortform', 'title:("short attention span theater" OR "lottery drawing" OR "lotto drawing" OR "lottery drawings" OR "farm report" OR "did you know" OR "great moments" OR "sports bloopers" OR horoscope OR "bicentennial minute" OR "minute" OR "newsminute" OR "health minute" OR "consumer tip" OR "trivia break")'),
 ('infomercial', 'title:(infomercial OR infomercials OR "paid programming" OR "paid program" OR ronco OR "k-tel" OR "as seen on tv" OR "amazing discoveries" OR "home shopping" OR qvc OR hsn OR "direct response")'),
 ('infomercial', 'title:("psychic friends" OR thighmaster OR "thigh master" OR "ab roller" OR "tae bo" OR flowbee OR soloflex OR "showtime rotisserie" OR "deal-a-meal" OR "susan powter" OR "carlton sheets" OR "don lapre" OR "hooked on phonics" OR juiceman OR "body by jake" OR "ab isolator" OR "tony robbins" OR "mega memory" OR nordictrack OR "total gym" OR "buns of steel" OR "sweatin to the oldies" OR ginsu OR popeil OR "veg-o-matic" OR "pocket fisherman" OR "miracle blade" OR "ultimate chopper" OR "chef tony" OR "hair club for men" OR proactiv OR "orange glo" OR oxiclean OR "billy mays" OR "time life music" OR "freedom rock" OR "dave del dotto" OR "tom vu" OR "smart mop" OR "topsy tail" OR abflex OR "ab flex" OR "ab doer" OR "tony little" OR bowflex OR healthrider OR "george foreman grill" OR "power juicer" OR "victoria principal" OR "mike levey" OR "amazing discoveries" OR "miss cleo" OR "space bag" OR "smokeless ashtray" OR "spray on hair" OR "glh formula")', 1),
 ('infomercial', 'subject:(infomercial OR infomercials OR "paid programming" OR "direct response")', 1),
 ('telethon', 'title:(telethon)'),
 ('holiday', 'title:("yule log" OR "new year\'s countdown" OR "holiday greetings" OR "season\'s greetings" OR "seasons greetings" OR "christmas greetings" OR "happy holidays from" OR "holiday bumper" OR "holiday bumpers" OR "christmas bumper" OR "christmas bumpers" OR "holiday promo" OR "holiday promos" OR "christmas promo" OR "christmas promos" OR "holiday ident" OR "christmas ident" OR "halloween promo" OR "halloween promos" OR "halloween bumpers")'),
]
LONGOK = {'infomercial', 'telethon', 'cablefill', 'weather', 'holiday', 'signoff'}
BAD = re.compile(r"\b(mock|fake|fan[- ]?made|fanmade|recreat\w*|remake|remastered|custom|concept|parody|reimagin\w*|my own|i made|tribute|ytp|youtube poop|reaction|review|podcast|tutorial|gameplay|walkthrough|let'?s play|minecraft|roblox|scratch|powerpoint|logo history|logo bloopers|effects|sponsored by preview|vocoded|g major|in g major|csupo|klasky|ai generated|upscale\w*|4k|60fps)\b", re.I)
FOREIGN = re.compile(r"\b(uk|u\.k\.|british|britain|bbc\d?|itv|channel 4|channel 5|sky|granada|thames|lwt|tvs|anglia|yorkshire tv|central tv|s4c|rte|rt[eé]|ireland|irish|australia\w*|aussie|sydney|melbourne|brisbane|perth|adelaide|nine network|seven network|network ten|abc australia|atv-?\d+|gtv|tcn|new zealand|tvnz|canada|canadian|cbc|ctv|citytv|global tv|ytv|tvo|toronto|vancouver|montreal|quebec|qu[eé]bec|japan\w*|nhk|fuji tv|tbs japan|korea\w*|kbs|mbc|sbs|china|chinese|cctv|hong kong|tvb|taiwan|india\w*|doordarshan|philippine\w*|gma|abs-cbn|pinoy|german\w*|deutsch\w*|zdf|ard|rtl|sat\.?1|pro ?7|france|french|tf1|antenne 2|canal\+?|ital\w+|rai|mediaset|spain|spanish|espa[nñ]ol\w*|tve|mexic\w+|televisa|azteca|brazil\w*|brasil\w*|globo|sbt|argentin\w+|chile\w*|colombia\w*|venezuel\w+|peru\w*|latino|latin america|portug\w+|dutch|nederland\w*|holland|belgi\w+|vrt|swed\w+|svt|norw\w+|nrk|danish|denmark|finn\w+|finland|yle|mainos\w*|polish|poland|polska|tvp|russia\w*|soviet|ussr|czech\w*|hungar\w+|greek|greece|turk\w+|israel\w*|arab\w*|thai\w*|vietnam\w*|indonesia\w*|malaysia\w*|singapore|univision|telemundo)\b", re.I)
AUS = re.compile(r"\((?:[A-Z]{2,3}-?\d{1,2})\b|\b(TVW|ABQ|ABS-2|ABN|SAS|ATN|GTV|HSV|TCN|NWS|ADS|QTQ|BTQ|TVQ|STW|NBN|WIN TV|Prime Television|Video Hits|Toons On Toast|Agro|Cheez TV|Saturday Disney|Foxtel|Austar|Optus|Europe|RTP|Asia|Nine|Network Ten|Seven)\b")
NOTTV = re.compile(r"\b(home video|coming soon to video|on video(cassette)?|vhs capture|vhs rip|dvd promo|dvd trailer|trailer|theatrical|in theaters|video game|playstation|nintendo power|laserdisc|screener|demo reel|showreel|sales tape|presentation reel|radio)\b", re.I)
old = json.load(gzip.open(os.path.join(OUT, 'raw.json.gz'), 'rt', encoding='utf-8')) if os.path.exists(os.path.join(OUT, 'raw.json.gz')) else []
have = set(x['i'] for x in old)
adsf = os.path.join(OUT, 'ads.json.gz')
adids = set(x[0] for x in json.load(gzip.open(adsf, 'rt', encoding='utf-8'))) if os.path.exists(adsf) else set()
del old
print('existing programs', len(have), 'ads', len(adids), flush=True)
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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor or len(out) > 40000: break
    return out
QONLY = set(x for x in (os.environ.get('QONLY', '') or '').split(',') if x)
Q = [q for q in Q if not QONLY or q[0] in QONLY]
seen = {}
for qq in Q:
    tag, expr = qq[0], qq[1]
    items = scrape('(' + expr + ') AND ' + ('mediatype:movies' if len(qq) > 2 else BASE))
    ok = []
    for it in items:
        t = str(it.get('title') or '')
        if it['identifier'] in have or it['identifier'] in seen: continue
        if BAD.search(t) or FOREIGN.search(t) or AUS.search(t) or NOTTV.search(t): continue
        if re.search(r'[^\x00-\xff‐-‧™]', t): continue
        if re.search(r'(?<!\d)20(0[5-9]|[1-3]\d)(?!\d)', t): continue
        it['q'] = tag; ok.append(it)
    ok.sort(key=lambda x: -(x.get('downloads') or 0))
    for it in ok[:PER]: seen[it['identifier']] = it
    print(tag, 'hits', len(items), 'kept', min(len(ok), PER), 'of', len(ok), 'total', len(seen), flush=True)
cands = list(seen.values())
print('candidates', len(cands), 'already in ads', sum(1 for x in cands if x['identifier'] in adids), flush=True)
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
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'eng|english|^en\b', str(lang).lower()): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    title = str(m.get('title', ''))
    blob = title + ' ' + str(subj) + ' ' + desc[:300]
    if BAD.search(blob) or FOREIGN.search(title + ' ' + str(subj)) or AUS.search(title) or NOTTV.search(title): return None
    up = str(m.get('uploader', '') or m.get('creator', ''))[:40]
    if FOREIGN.search(desc[:300]) and not re.search(r'\b(nbc|cbs|abc|fox|pbs|upn|the wb|nickelodeon|cartoon network|mtv|hbo|[wk][a-z]{3}(-tv)?)\b', title, re.I): return None
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
        if d < 5: continue
        files.append([b['name'], round(d, 1), b.get('format', '')])
    if not files: return None
    files.sort(key=lambda f: f[0])
    tot = sum(f[1] for f in files)
    tag = it['q']
    comp = re.search(r'\b(compilation|collection|mega|ultimate|marathon|hours? of|\d+ hours?)\b', title, re.I)
    if tot > 1200:
        if tag not in LONGOK and (len(files) > 1 or comp or tot > 3600): return None
        if tag in LONGOK and (comp or tot > 4 * 3600): return None
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    return {'i': it['identifier'], 'q': tag, 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:300], 'f': files[:60], 'dl': it.get('downloads') or 0, 'u': up}
res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 2000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
if QONLY and os.path.exists(os.path.join(OUT, 'filler.json.gz')):
    _ids = set(x['i'] for x in res)
    res = res + [x for x in json.load(gzip.open(os.path.join(OUT, 'filler.json.gz'), 'rt', encoding='utf-8')) if x['i'] not in _ids]
with gzip.open(os.path.join(OUT, 'filler.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump([{k: v for k, v in x.items() if k != 'u'} for x in res], f, ensure_ascii=False, separators=(',', ':'))
def yr(x):
    for v in (x['d'], x['y'], x['t']):
        m = re.search(r'(19[89]\d|200[0-4])', str(v))
        if m: return m.group(1)
    return '?'
bt = collections.defaultdict(lambda: [0, 0.0, 0]); by = collections.defaultdict(lambda: [0, 0.0])
for x in res:
    d = sum(f[1] for f in x['f']); b = bt[x['q']]; b[0] += 1; b[1] += d; b[2] += 1 if x['i'] in adids else 0
    y = by[yr(x)]; y[0] += 1; y[1] += d
print('done', len(res))
print('TAG count hours also_in_ads')
for k in sorted(bt, key=lambda k: -bt[k][0]): print(' ', k, bt[k][0], round(bt[k][1] / 3600, 1), bt[k][2])
print('YEAR count hours')
for k in sorted(by): print(' ', k, by[k][0], round(by[k][1] / 3600, 1))
ups = collections.Counter(x.get('u', '') for x in res)
print('UPLOADERS')
random.seed(3)
for u, n in ups.most_common(12):
    ex = [x['t'][:60] for x in res if x.get('u', '') == u]
    print(' ', n, hash(u) % 100000, '|', ' ## '.join(random.sample(ex, min(4, len(ex)))))
random.seed(7)
print('SAMPLE')
for x in random.sample(res, min(60, len(res))): print(' ', x['q'], '|', yr(x), '|', round(sum(f[1] for f in x['f'])), 's |', len(x['f']), 'f |', x['t'][:90])
