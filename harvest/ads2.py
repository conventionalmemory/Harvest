import json, gzip, os, re, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '24'))
BUDGET = float(os.environ.get('BUDGET_MIN', '200')) * 60
MAXC = int(os.environ.get('MAXC', '140000'))
T0 = time.time()
ns = {'re': re}
for ln in open(os.path.join(here, 'filler.py'), encoding='utf-8'):
    if ln.startswith(('BAD = ', 'FOREIGN = ', 'AUS = ')): exec(ln, ns)
BAD, FOREIGN, AUS = ns['BAD'], ns['FOREIGN'], ns['AUS']
ADF = os.path.join(OUT, 'ads2.json.gz'); FLF = os.path.join(OUT, 'filler2.json.gz')
oldads = json.load(gzip.open(ADF, 'rt', encoding='utf-8')) if os.path.exists(ADF) else []
oldfl = json.load(gzip.open(FLF, 'rt', encoding='utf-8')) if os.path.exists(FLF) else []
have = set()
for fn in glob.glob(os.path.join(OUT, '*.json.gz')):
    b = os.path.basename(fn)
    if b in ('ads2.json.gz', 'filler2.json.gz', 'epguide.json.gz'): continue
    try: j = json.load(gzip.open(fn, 'rt', encoding='utf-8'))
    except Exception: continue
    if isinstance(j, dict): have.update(j.keys())
    else:
        for x in j:
            if isinstance(x, dict) and 'i' in x: have.add(x['i'])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
    del j
mine = set(r[0] for r in oldads) | set(x['i'] for x in oldfl)
print('known ids', len(have), 'own', len(mine), flush=True)
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=30000):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor or len(out) >= cap: break
    return out
ADW = 'title:(commercial OR commercials OR "tv spot" OR "tv spots" OR "tv ad" OR "tv ads" OR "television ad" OR advert OR advertisement OR "ad campaign")'
BR = ["mcdonald's", 'mcdonalds', 'burger king', "wendy's", 'pizza hut', "domino's", 'taco bell', 'kfc', 'little caesars', 'subway', 'coca-cola', 'coke', 'pepsi', 'mountain dew', '7up', 'sprite', 'dr pepper', 'budweiser', 'bud light', 'miller lite', 'coors', 'kellogg', "kellogg's", 'general mills', 'post cereal', 'cheerios', 'frosted flakes', 'froot loops', 'lucky charms', 'trix', 'cap n crunch', 'pop-tarts', 'eggo', 'kool-aid', 'capri sun', 'hi-c', 'sunny delight', 'gatorade', 'doritos', 'cheetos', 'pringles', 'oreo', 'chips ahoy', 'snickers', 'm&m', "reese's", 'skittles', 'starburst', 'hershey', 'bubble yum', 'bubblicious', 'big league chew', 'jell-o', 'kraft', 'campbell', 'chef boyardee', 'hot pockets', 'bagel bites', 'lunchables', 'toys r us', 'kay bee', 'kb toys', 'hasbro', 'mattel', 'kenner', 'tonka', 'playskool', 'fisher-price', 'lego', 'barbie', 'hot wheels', 'g.i. joe', 'gi joe', 'transformers', 'he-man', 'my little pony', 'cabbage patch', 'teddy ruxpin', 'nerf', 'super soaker', 'micro machines', 'power wheels', 'tamagotchi', 'furby', 'tickle me elmo', 'pokemon', 'nintendo', 'super nintendo', 'game boy', 'nintendo 64', 'sega', 'sega genesis', 'dreamcast', 'playstation', 'xbox', 'atari', 'colecovision', 'intellivision', 'commodore', 'apple computer', 'macintosh', 'ibm', 'compaq', 'gateway 2000', 'dell', 'windows 95', 'america online', 'aol', 'prodigy', 'compuserve', 'at&t', 'mci', 'sprint', '10-10-321', '1-800-collect', 'radio shack', 'radioshack', 'circuit city', 'best buy', 'sears', 'kmart', 'k-mart', 'walmart', 'wal-mart', 'target', 'jcpenney', 'montgomery ward', 'zayre', 'ames', 'bradlees', 'caldor', 'service merchandise', 'woolworth', 'blockbuster', 'hollywood video', 'columbia house', 'time life', 'k-tel', 'ronco', 'ginsu', 'clapper', 'chia pet', 'life call', 'ford', 'chevrolet', 'chevy', 'dodge', 'chrysler', 'plymouth', 'pontiac', 'oldsmobile', 'buick', 'cadillac', 'toyota', 'honda', 'nissan', 'datsun', 'mazda', 'subaru', 'volkswagen', 'saturn', 'jeep', 'isuzu', 'hyundai', 'levi', "levi's", 'nike', 'reebok', 'la gear', 'british knights', 'gap', 'old navy', 'calvin klein', 'tide', 'crest', 'colgate', 'pert plus', 'head & shoulders', 'irish spring', 'zest', 'old spice', 'gillette', 'duracell', 'energizer', 'kodak', 'polaroid', 'fuji', 'sony', 'panasonic', 'rca', 'zenith', 'magnavox', 'maxell', 'memorex', 'american express', 'visa', 'mastercard', 'discover card', 'state farm', 'allstate', 'geico', 'budget gourmet', 'lean cuisine', 'slim-fast', 'jenny craig', 'weight watchers', 'bowflex', 'soloflex', 'nordictrack', 'thighmaster', 'psychic friends', 'dial-a-joke', '1-900', 'crazy eddie', 'car dealer', 'car dealership', 'furniture store', 'local commercial', 'local commercials', 'movie trailer tv spot', 'tv spot', 'home video commercial', 'vhs commercial', 'soundtrack commercial', 'record offer', 'lottery commercial', 'political ad', 'campaign ad', 'army commercial', 'navy commercial', 'air force commercial', 'marines commercial', 'milk commercial', 'got milk', 'beef commercial', 'california raisins', 'energizer bunny', 'spuds mackenzie', 'joe isuzu', 'noid', 'max headroom coke', 'where\'s the beef', 'wassup', 'taco bell chihuahua', 'pets.com', 'dot com commercial', 'cell phone commercial', 'pager commercial', 'airline commercial', 'cruise commercial', 'disney world commercial', 'disneyland commercial', 'six flags', 'theme park commercial', 'cigarette', 'beer commercial', 'wine cooler', 'bartles', 'zima', 'crystal pepsi', 'surge', 'jolt cola', 'new coke', 'cherry coke', 'slice soda', 'squeezit', 'ecto cooler', 'fruit roll-ups', 'gushers', 'dunkaroos', 'fruit by the foot', 'push pop', 'ring pop', 'bubble tape']
QA = []
for y in range(1984, 2005):
    QA.append(('y%d' % y, ADW + ' AND (title:(%d) OR year:%d OR date:[%d-01-01 TO %d-12-31])' % (y, y, y, y)))
QA.append(('dec', 'title:(commercial OR commercials OR ads OR adverts) AND title:("80s" OR "1980s" OR eighties OR "90s" OR "1990s" OR nineties OR "early 2000s" OR "2000s" OR vintage OR retro OR classic OR old OR vhs)'))
QA.append(('hol', 'title:(commercial OR commercials OR ad OR ads OR spot) AND title:(christmas OR xmas OR halloween OR "super bowl" OR superbowl OR thanksgiving OR "back to school" OR easter OR "4th of july" OR "fourth of july" OR valentine OR "new year" OR olympics OR "world series" OR "black friday" OR "holiday")'))
QA.append(('subj', 'subject:("commercials" OR "tv commercials" OR "television commercials" OR "vintage commercials" OR "80s commercials" OR "90s commercials" OR "retro commercials" OR "classic commercials" OR "old commercials" OR "tv ads" OR "tv spots" OR "commercial" OR "advertising")'))
for k in range(0, len(BR), 14):
    QA.append(('br%d' % (k // 14), 'title:(commercial OR commercials OR ad OR ads OR spot OR advert OR promo) AND title:(' + ' OR '.join('"%s"' % b for b in BR[k:k + 14]) + ')'))
NETS = ['nbc', 'cbs', 'abc', 'fox', 'upn', '"the wb"', '"kids wb"', '"fox kids"', 'pbs', 'nickelodeon', '"nick at nite"', '"nick jr"', 'snick', 'mtv', 'vh1', '"cartoon network"', 'toonami', '"adult swim"', '"disney channel"', '"toon disney"', 'usa', 'tbs', 'tnt', 'wgn', 'hbo', 'showtime', 'cinemax', 'espn', 'cnn', 'tnn', 'lifetime', '"comedy central"', '"sci-fi channel"', '"family channel"', '"fox family"', 'a&e', 'discovery', 'tlc', 'bet', '"the box"', '"weather channel"', 'amc', 'tcm', '"tv land"', 'boomerang', 'noggin', 'zdtv', 'techtv', 'g4']
QF = [
 ('promo', 'title:(promo OR promos OR "fall preview" OR "fall lineup" OR "fall campaign" OR "image campaign" OR "must see tv" OR tgif OR "coming up next" OR "tonight on" OR "this fall" OR "sweeps" OR "movie of the week" OR "world premiere movie" OR "season premiere" OR "series premiere" OR "next week on" OR "stay tuned") AND title:(' + ' OR '.join(NETS) + ')'),
 ('bumper', 'title:(bumper OR bumpers OR ident OR idents OR interstitial OR interstitials OR "be right back" OR "now back to" OR "we\'ll be right back" OR "station break" OR "commercial bumper" OR "act break" OR "up next") AND title:(' + ' OR '.join(NETS) + ')'),
 ('kidint', 'title:(toonami OR "cartoon cartoon fridays" OR "cartoon network city" OR "powerhouse bumpers" OR "nick bumpers" OR "nickelodeon bumpers" OR "nick promos" OR "snick bumpers" OR "nick jr face" OR "one saturday morning" OR "fox kids bumpers" OR "kids wb bumpers" OR "disney afternoon bumpers" OR "tnbc" OR "saturday morning bumpers" OR "abc saturday morning" OR "cbs saturday morning" OR "usa cartoon express" OR "nick in the afternoon" OR "u-pick" OR "zoog disney" OR "playhouse disney bumpers" OR "pbs kids bumpers")'),
 ('psa', 'title:(psa OR psas OR "public service announcement" OR "public service announcements" OR "ad council" OR "the more you know" OR "one to grow on" OR "cbs cares" OR mcgruff OR "this is your brain on drugs" OR "partnership for a drug" OR "smokey bear" OR "woodsy owl" OR "crash test dummies" OR "buckle up" OR "just say no" OR "drug free america" OR "stay in school" OR "knowing is half the battle" OR "time for timer" OR "schoolhouse rock" OR "reading is fundamental" OR "united negro college fund" OR "take a bite out of crime" OR "friends don\'t let friends" OR "only you can prevent")'),
 ('stationid', 'title:("station id" OR "station ids" OR "station ident" OR "station idents" OR "station identification" OR "legal id" OR "legal ids" OR "station promo" OR "station promos" OR "station break" OR "channel id" OR "affiliate id" OR "local id")'),
 ('newsbrk', 'title:("news open" OR "news opens" OR "news intro" OR "news intros" OR "news tease" OR "news teaser" OR "news teases" OR "news break" OR newsbreak OR "news update" OR "news promo" OR "news promos" OR "news brief" OR "eyewitness news open" OR "action news open" OR "newscenter open" OR "news theme" OR "special report open" OR "weather open")'),
 ('signoff', 'title:("sign off" OR "sign-off" OR signoff OR "sign on" OR "sign-on" OR signon OR "national anthem" OR sermonette OR "test pattern" OR "color bars" OR "off the air" OR "end of broadcast day" OR "start of broadcast day" OR "closedown")'),
 ('ebs', 'title:("emergency broadcast system" OR "emergency broadcast" OR "emergency alert system" OR "eas test" OR "ebs test" OR "eas alert" OR "weekly test" OR "monthly test" OR "tornado warning" OR "severe thunderstorm warning")'),
 ('techdiff', 'title:("technical difficulties" OR "please stand by" OR "experiencing technical" OR "trouble slide" OR "we\'ll be back")'),
 ('cablefill', 'title:(prevue OR "prevue guide" OR "prevue channel" OR "tv guide channel" OR "preview guide" OR "pay-per-view" OR "pay per view" OR "ppv promo" OR barker OR "request tv" OR "viewer\'s choice" OR "channel lineup" OR "cable lineup" OR "cable tv promo" OR "free preview" OR "local origination" OR "cable ad" OR "cable ads" OR "local cable" OR "cablevision" OR "tci" OR "comcast" OR "time warner cable" OR "cox cable" OR "continental cablevision" OR "direct tv" OR directv OR primestar OR "dish network")'),
 ('moviech', 'title:("feature presentation" OR "hbo intro" OR "hbo intros" OR "hbo opening" OR "hbo coming attractions" OR "hbo next on" OR "hbo promo" OR "hbo promos" OR "hbo bumper" OR "hbo bumpers" OR "hbo in space" OR "showtime intro" OR "showtime promo" OR "showtime promos" OR "cinemax intro" OR "cinemax promo" OR "cinemax promos" OR "movie channel promo" OR "starz promo" OR "encore promo" OR "tonight on hbo" OR "coming to hbo" OR "this month on")'),
 ('vidstore', 'title:("coming soon to video" OR "coming soon to videocassette" OR "vhs previews" OR "vhs preview" OR "vhs trailers" OR "video store" OR "blockbuster video" OR "now available on videocassette" OR "home video trailer" OR "home video promo" OR "vhs promo" OR "vhs opening" OR "fbi warning")'),
 ('trailer', 'title:("tv spot" OR "tv spots" OR "tv trailer" OR "television spot" OR "teaser tv") AND (year:[1984 TO 2004] OR title:(' + ' OR '.join(str(y) for y in range(1984, 2005)) + '))'),
 ('weather', 'title:(weatherstar OR "weather star" OR "local forecast" OR "local on the 8s" OR "weather channel promo" OR "weather bumper" OR "weather update" OR weatherscan)'),
 ('holiday', 'title:("holiday greetings" OR "season\'s greetings" OR "seasons greetings" OR "christmas greetings" OR "happy holidays from" OR "holiday bumper" OR "holiday bumpers" OR "christmas bumper" OR "christmas bumpers" OR "holiday promo" OR "holiday promos" OR "christmas promo" OR "christmas promos" OR "halloween promo" OR "halloween bumpers" OR "new year\'s countdown")'),
 ('adbreak', 'title:("commercial break" OR "commercial breaks" OR "commercial block" OR "commercial blocks" OR "ad break" OR "ad breaks" OR "commercials from" OR "block of commercials" OR "commercials and promos" OR "commercials & promos" OR "promos and commercials")'),
]
NOTAD = re.compile(r"\b(radio|podcast|print ad|magazine ad|newspaper|billboard|jingle only|audio only|soundtrack|behind the scenes|making of|outtakes?|bloopers?|banned|uncensored|nsfw|review|reaction|ranking|top \d+|history of|documentary|analysis|explained|commentary|interview|lecture|presentation|slideshow|gameplay|longplay|walkthrough|pilot|episode|full movie|full show)\b", re.I)
COMP = re.compile(r"\b(compilation|collection|mega|ultimate|marathon|hours? of|\d+ ?hours?|\d+ ?hrs?|volume|vol\.?|part \d+|block|blocks|break|breaks|reel|tape|montage|mix|pack|bundle|various|assorted|misc|lot of|\d{2,} commercials)\b", re.I)
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
YR = re.compile(r'(?<![\d$#])(19[89]\d|200[0-4])(?!\d)')
def when(title, desc, date, year):
    t = title + ' '
    y = None; src = ''
    m = YR.search(t)
    if m: y = int(m.group(1)); src = 't'
    if not y:
        m = YR.search(desc[:240])
        if m and not re.search(r'(upload|posted|digitiz|transfer|captur|rip)\w* (on|in)? ?' + m.group(1), desc[:240], re.I): y = int(m.group(1)); src = 'd'
    if not y:
        for v in (date, year):
            m = re.match(r'(19[89]\d|200[0-4])', str(v or ''))
            if m and 1984 <= int(m.group(1)) <= 2004: y = int(m.group(1)); src = 'm'; break
    dec = ''
    if not y:
        low = (t + ' ' + desc[:200]).lower()
        if re.search(r"\b(19)?80'?s\b|eighties", low): dec = '80s'
        elif re.search(r"\b(19)?90'?s\b|nineties", low): dec = '90s'
        elif re.search(r"early 2000'?s|\b2000'?s\b", low): dec = '00s'
    if not y: return '', dec, ''
    mo = 0
    blob = (t + ' ' + desc[:240]).lower()
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,? (\d{1,2},? )?' + str(y), blob) or re.search(r'\b' + str(y) + r'[ ,/-]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', blob)
    if m: mo = MON[m.group(1)]
    if not mo:
        m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](' + str(y) + '|' + str(y)[2:] + r')(?!\d)', blob)
        if m and 1 <= int(m.group(1)) <= 12: mo = int(m.group(1))
    if not mo and src == 'm':
        m = re.match(r'\d{4}-(\d\d)-(\d\d)', str(date or ''))
        if m and not (m.group(1) == '01' and m.group(2) == '01'): mo = int(m.group(1))
    if not mo:
        if re.search(r'christmas|xmas|santa', blob): mo = 12
        elif re.search(r'halloween', blob): mo = 10
        elif re.search(r'thanksgiving', blob): mo = 11
        elif re.search(r'super ?bowl', blob): mo = 1
        elif re.search(r'back to school', blob): mo = 8
        elif re.search(r'easter', blob): mo = 4
    return ('%d-%02d' % (y, mo)) if mo else str(y), '', src
seen = {}
def take(tag, items):
    n = 0
    for it in items:
        i = it['identifier']; t = str(it.get('title') or '')
        if i in have or i in mine or i in seen: continue
        if BAD.search(t) or FOREIGN.search(t) or AUS.search(t): continue
        if re.search(r'[^\x00-\xff‐-‧™]', t): continue
        if re.search(r'(?<!\d)20(0[5-9]|[1-3]\d)(?!\d)', t): continue
        it['q'] = tag; seen[i] = it; n += 1
    return n
for tag, q in QA:
    items = scrape('(' + q + ') AND mediatype:movies')
    print('ad', tag, 'hits', len(items), 'new', take('ad', items), 'total', len(seen), flush=True)
for tag, q in QF:
    items = scrape('(' + q + ') AND mediatype:movies')
    print('fill', tag, 'hits', len(items), 'new', take(tag, items), 'total', len(seen), flush=True)
cands = list(seen.values())
def pri(it):
    t = str(it.get('title') or '')
    s = 0
    if YR.search(t): s += 4
    m = YR.search(t)
    if m and (int(m.group(1)) <= 1988 or int(m.group(1)) >= 2001): s += 3
    if it['q'] != 'ad': s += 2
    return -s, -(it.get('downloads') or 0)
cands.sort(key=pri); cands = cands[:MAXC]
print('candidates', len(cands), flush=True)
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
rej = collections.Counter()
def meta(it):
    if time.time() - T0 > BUDGET: rej['budget'] += 1; return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): rej['nometa'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': rej['restricted'] += 1; return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'eng|english|^en\b', str(lang).lower()): rej['lang'] += 1; return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    title = str(m.get('title', ''))
    blob = title + ' ' + str(subj) + ' ' + desc[:300]
    if BAD.search(blob) or FOREIGN.search(title + ' ' + str(subj)) or AUS.search(title): rej['badforeign'] += 1; return None
    if FOREIGN.search(desc[:300]) and not re.search(r'\b(nbc|cbs|abc|fox|pbs|upn|the wb|nickelodeon|cartoon network|mtv|hbo|[wk][a-z]{3}(-tv)?)\b', title, re.I): rej['foreigndesc'] += 1; return None
    if re.search(r'(?<!\d)20(0[5-9]|[1-3]\d)(?!\d)', title): rej['modern'] += 1; return None
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
    if not files: rej['nofile'] += 1; return None
    files.sort(key=lambda f: f[0])
    tot = sum(f[1] for f in files)
    ds, dec, src = when(title, desc, m.get('date'), m.get('year'))
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    up = str(m.get('uploader', '') or m.get('creator', ''))[:40]
    tag = it['q']
    base = {'i': it['identifier'], 't': title[:200], 'd': ds, 'y': ds[:4], 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:300], 'dl': it.get('downloads') or 0, 'u': up, 'dec': dec, 'src': src}
    if tag == 'ad':
        if NOTAD.search(title): rej['notad'] += 1; return None
        if not ds and not dec: rej['undated'] += 1; return None
        singles = [f for f in files if 5 <= f[1] <= 125]
        if len(files) == 1 and singles:
            if COMP.search(title) and files[0][1] > 70: rej['compshort'] += 1; return None
            return ('ad', [[it['identifier'], files[0][0], files[0][1], ds, title[:120], dec]])
        if len(files) > 1 and len(singles) >= max(2, len(files) * .8) and len(files) <= 400:
            rows = []
            for f in singles[:200]:
                stem = re.sub(r'\.(ia\.)?mp4$', '', f[0].split('/')[-1]); stem = re.sub(r'[_]+', ' ', stem)
                fd, fdec, _ = when(stem, '', '', '')
                rows.append([it['identifier'], f[0], f[1], fd or ds, (stem if len(stem) > 12 else title[:80] + ' - ' + stem)[:120], fdec or dec])
            return ('ad', rows)
        if len(files) <= 3 and 126 <= tot <= 900:
            base.update(q='adbreak', f=files); return ('fl', base)
        rej['adlen'] += 1; return None
    if tag == 'adbreak':
        if not (120 <= tot <= 900) or len(files) > 4: rej['breaklen'] += 1; return None
        if not ds and not dec: rej['undated'] += 1; return None
        base.update(q='adbreak', f=files); return ('fl', base)
    lim = 3600 if tag in ('cablefill', 'weather', 'signoff') else 900
    if tot > lim and len(files) == 1: rej['long'] += 1; return None
    if len(files) > 1:
        files = [f for f in files if f[1] <= 600][:60]
        if not files: rej['long'] += 1; return None
    if tag == 'trailer' and not ds: rej['undated'] += 1; return None
    base.update(q=tag, f=files); return ('fl', base)
ads, fl = [], []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r:
            if r[0] == 'ad': ads += r[1]
            else: fl.append(r[1])
        if n % 4000 == 0: print('meta', n, len(ads), len(fl), round((time.time() - T0) / 60, 1), 'min', flush=True)
print('rejected', dict(rej), flush=True)
allads = oldads + ads
allfl = oldfl + [{k: v for k, v in x.items() if k != 'u'} for x in fl]
with gzip.open(ADF, 'wt', encoding='utf-8') as f: json.dump(allads, f, ensure_ascii=False, separators=(',', ':'))
with gzip.open(FLF, 'wt', encoding='utf-8') as f: json.dump(allfl, f, ensure_ascii=False, separators=(',', ':'))
print('ads rows new', len(ads), 'total', len(allads), 'items', len(set(r[0] for r in allads)), '| filler new', len(fl), 'total', len(allfl))
by = collections.Counter(); bm = collections.Counter(); bd = collections.Counter()
for r in allads:
    y = r[3][:4] if r[3] else ('dec:' + (r[5] if len(r) > 5 else ''))
    by[y] += 1
    if len(r[3]) >= 7: bm[r[3][:4]] += 1
print('ADS YEAR rows with_month')
for k in sorted(by): print(' ', k, by[k], bm.get(k, 0))
ft = collections.defaultdict(lambda: collections.Counter())
for x in allfl: ft[x['q']][x.get('y') or ('dec:' + x.get('dec', '')) or '?'] += 1
print('FILLER TYPE total | per year')
for k in sorted(ft, key=lambda k: -sum(ft[k].values())): print(' ', k, sum(ft[k].values()), '|', ' '.join('%s:%d' % (y, n) for y, n in sorted(ft[k].items())))
ups = collections.Counter(x.get('u', '') for x in fl)
print('UPLOADERS (filler, hashed)')
for u, n in ups.most_common(10): print(' ', n, hash(u) % 100000)
random.seed(7)
print('SAMPLE ADS')
for r in random.sample(ads, min(80, len(ads))): print(' ', r[3] or r[5], '|', round(r[2]), 's |', r[4][:90])
print('SAMPLE FILLER')
for x in random.sample(fl, min(80, len(fl))): print(' ', x['q'], '|', x['d'] or x.get('dec', '') or '?', '|', round(sum(f[1] for f in x['f'])), 's |', len(x['f']), 'f |', x['t'][:90])
