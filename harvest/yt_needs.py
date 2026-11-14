import gzip, json, os, re, sys, time, random, glob, collections, threading, urllib.request, urllib.parse, datetime
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'catalog')
HV = os.path.join(ROOT, 'harvest')
PARTS = os.path.join(ROOT, 'parts')
OUT = os.path.join(CAT, 'yt_needs.json.gz')
REP = os.path.join(CAT, 'yt_needs_report.json')
MODE = os.environ.get('MODE', 'plan')
SHARD = int(os.environ.get('SHARD', '0'))
SHARDS = int(os.environ.get('SHARDS', '6'))
THREADS = int(os.environ.get('THREADS', '4'))
BUDGET = float(os.environ.get('BUDGET_MIN', '60') or 60) * 60
PRI = os.environ.get('PRI', '1') or '1'
ONLY = [x.strip() for x in (os.environ.get('ONLY', '') or '').split('|') if x.strip()]
DEEP = int(os.environ.get('DEEP', '0') or 0)
RUN = os.environ.get('GITHUB_RUN_ID', '')
T0 = time.time()
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
CTX = {'client': {'clientName': 'WEB', 'clientVersion': '2.20240620.05.00', 'hl': 'en', 'gl': 'US'}}
TODAY = datetime.date.today()
STAT = collections.Counter()
LOCK = threading.Lock()
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
DATEK = set('talk game news late soap mag morning gov relig music sports special'.split())
SKIPK = set(['movie-package'])
QMAP = {'sitcom': 'prime', 'drama': 'prime', 'kids': 'kids', 'doc': 'pub', 'cook': 'pub', 'game': 'game', 'talk': 'talk', 'soap': 'soap', 'late': 'late', 'news': 'news', 'mag': 'news', 'morning': 'news', 'gov': 'news', 'music': 'music', 'relig': 'talk', 'sports': 'sports', 'special': 'prime', 'other': 'prime'}
NETW = {'nbc': ['nbc'], 'abc': ['abc'], 'cbs': ['cbs'], 'fox': ['fox'], 'pbs': ['pbs'], 'hbo': ['hbo'], 'mtv': ['mtv'], 'vh1': ['vh1', 'vh 1'], 'nick': ['nick', 'nickelodeon'], 'nickelodeon': ['nick', 'nickelodeon'], 'discovery': ['discovery'], 'a&e': ['a and e', 'ae'], 'tnn': ['tnn', 'nashville network'], 'bet': ['bet'], 'usa': ['usa network', 'usa'], 'espn': ['espn'], 'cnn': ['cnn'], 'tbs': ['tbs'], 'tnt': ['tnt'], 'disney': ['disney'], 'lifetime': ['lifetime'], 'showtime': ['showtime'], 'c-span': ['c span', 'cspan'], 'upn': ['upn'], 'wb': ['wb'], 'syn': ['syndicated', 'syndication'], 'comedy central': ['comedy central'], 'food network': ['food network'], 'tlc': ['tlc'], 'hgtv': ['hgtv'], 'e!': ['e entertainment'], 'sci-fi': ['sci fi', 'scifi'], 'cartoon network': ['cartoon network'], 'family': ['family channel', 'fox family', 'abc family'], 'history': ['history channel'], 'techtv': ['techtv', 'zdtv', 'tech tv']}
BADT = re.compile(r"(?i)\b(reaction|reacts?|reacting|reviewed|best of|compilation|trailer|promo|promos|theme song|bloopers|behind the scenes|explained|top \d+|ranking|ranked|podcast|amv|mashup|teaser|every time|supercut|funniest|montage|unboxing|gameplay|longplay|walkthrough|speedrun|lyrics|karaoke|tiktok|meme|fan ?made|restored in 4k|60 ?fps|upscaled?|ai |sub español|subtitulado|latino|dublado|legendado|español|castellano|deutsch|fran[cç]ais|italiano|hindi|tagalog|vostfr|ger sub|napisy|türkçe|dubbed|doblaje|doblado|rus eng|eng rus|x264|x265|ac3|learn english|watch ?along|first time watching|breakdown|analysis|retrospective|rewatch|full movie|ost|audiobook|asmr|tv spots?|bumpers?|commercials? (break|block)s?|sign ?off|sneak peek|blu ?ray|dvd (menu|unboxing)|all episodes|episodes? \d+ ?(-|to|thru|through|&|and) ?\d+)\b")
PARTX = re.compile(r"(?i)\b(part|pt\.?)\s*([1-9]|one|two|three)\s*(of|/)\s*\d|\[\s*\d\s*/\s*\d\s*\]|\(\s*\d\s*/\s*\d\s*\)|\b\d\s*/\s*\d\s*$")
JUNKT = re.compile(r"(?i)\b(web ?series|icons unearthed|gmod|minecraft|roblox|fortnite|playstation|nintendo|game ?boy|n64|gamecube|dreamcast|pc game|video ?game|for the first time|we watch(ed)?|re-?watch(ed|ing)?|revisited|rundown|after ?show|afterbuzz|play ?through|let'?s play|script reading|table read|discuss(es|ed|ing|ion)?|analy[sz](ing|ed|is)|facts about|weird facts|un episodio|joined by|check out|watch ?along|my thoughts|deep dive|drinking game|ft\.|feat\.|ps[1-5]|xbox|let'?s watch|live ?stream|sermon|school project|stage production|decoded|reviews|then (and|&|vs\.?) now|where are they now|ranking every|every episode|iceberg|cast update|still alive|making of|featurette|reboot|fan ?film|fan ?fiction|audio only|audio drama|old time radio|otr|cosplay|comic ?con|q ?& ?a|unreleased|animatic|storyboard|lost media|creepypasta|ytp|poop|tier list|how to|tutorial|collection review|lego|rom ?hack|emulator|ep(isode)?s? ?\d+ ?- ?\d+|vol(ume)?\.? ?\d+|disc \d+|24/7|non ?stop)\b")
JUNKC = re.compile(r"(?i)(react|podcast|gaming|gamer|commentary|rewatch|reviews?\b|plays\b|after ?show|longplay|\bfm\b|radio)")
SOFTJ = re.compile(r"(?i)\b(hours?|hrs?|vs\.?|versus|mix|mega ?mix|convention|panel|reunion|reunite[sd]?|toy|toys|figure|figures|pitch|mod|mods|genesis|sega|nes|snes|arcade|radio|trivia|quiz|theory|theories|the game|revival|cover|theme|edit|ending|opening|credits|preview|intro|outro|shorts?|scenes?|interview|tribute|deleted|review|clips?|moments|parody|german|french|polish|russian|arabic|partial|marathon|remix|highlights|commentary|recap|soundtrack)\b")
LATEY = re.compile(r'\b(200[5-9]|20[12]\d)\b|\b\d{1,2}[./]\d{1,2}[./](0[5-9]|[12]\d)\b')
OFFX = re.compile(r"(?i)(official|\bpbs\b|\bnbc\b|\bcbs\b|\babc\b|\bfox\b|warner|paramount|sony pictures|universal|disney|\bmgm\b|lionsgate|shout! ?(studios|factory)|shout ?factory|filmrise|hasbro|mattel|wildbrain|nelvana|9 story|cookie jar|nickelodeon|cartoon network|a&e|history channel|discovery|c-span|associated press|ap archive|\bbbc\b|\bitv\b|britbox|\bhbo\b|showtime|\bmtv\b|comedy central|\bbet\b|national geographic|smithsonian|american archive|library of congress|museum|university|public (television|media|broadcasting)|\bwgbh\b|\bwttw\b|\bwnet\b|\bkqed\b|\bopb\b|buzzr|fremantle|carsey|norman lear|stephen j\. cannell|cannell|peanuts|jim henson|henson|sesame|scholastic|dhx|cinedigm|multicom|mill creek|kino|questar|janson|echo bridge|vision films|grand ole opry|circle|opry|tv land|me-?tv|antenna tv|decades|the film detective|classic media|dreamworks|\bamc\b|ifc|sundance|food network|hgtv|\btlc\b|travel channel|court tv|\bcnn\b|\bespn\b|\bnfl\b|\bnba\b|\bmlb\b|\bnhl\b|\bwwe\b|nascar)")
STOPW = set('full episode episodes season series complete entire hd hq tv show the a an and of in on at to with from by for original broadcast uncut unedited commercials commercial classic classics sitcom cartoon cartoons animated animation vhs dvd rip part pt finale premiere pilot nbc abc cbs fox pbs upn wb nick nickelodeon nickelodeons disney disneys espn espns usa tnt tbs syndicated syndication rerun reruns english eng version remastered 1080p 720p 480p 4k s e ep vol volume disc tape aired air date airdate year all new retro vintage rare 80s 90s 1980s 1990s lifetime lifetimes hgtv cnn bbc mtv vh1 hbo discovery channel tlc cable network presents free watch online starring stars hosted host game western drama comedy crime detective mystery kids children childrens family tvshow television official'.split())
NEXTW = set('season series episode episodes ep full complete tv show the pilot s e vol volume part classic uncut original hd with cartoon sitcom nbc abc cbs fox pbs vhs dvd premiere finale starring hosted aired air airdate broadcast from on game'.split())
MONW = set('january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday'.split())
SEP = re.compile(r'(?i)\bs(?:eason|eries)?\s*(\d{1,2})\s*[,:._|(/-]?\s*\(?(?:e|ep|eps|episode)\s*\.?\s*#?\s*(\d{1,3})\b|\b(\d{1,2})x(\d{2})\b')
FULLX = re.compile(r'(?i)full episode|complete episode|entire episode|full show|full broadcast|\bepisode\s*#?\d+|\bep\.?\s*#?\d+|\(\s*full\s*\)|\bfull\b')
SERX = r'\b(s ?\d{1,2} ?e ?\d{1,3}|season \d{1,2}|series \d{1,2}|episode \d{1,3}|ep \d{1,3}|\d{1,2}x\d{2,3}|s\d{1,2}|e\d{1,3})\b'


def nz(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r"[’'`]", '', s)
    s = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', s)).strip()
    return re.sub(r'\b([a-z]) (?=[a-z]\b)', r'\1', s)


def nzk(s):
    return re.sub(r'^the ', '', nz(s))


def left():
    return BUDGET - (time.time() - T0)


def http(url, data=None, headers=None, tries=4, timeout=25):
    h = {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}
    if headers: h.update(headers)
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code in (400, 401, 403, 404): return e.code, b''
            time.sleep(2 + a * 4 + random.random() * 3)
        except Exception as e:
            last = str(e)[:60]
            time.sleep(1.5 + a * 3 + random.random() * 2)
    with LOCK: STAT['httpfail'] += 1
    return last if isinstance(last, int) else 0, b''


def inner(ep, body):
    b = dict(body); b['context'] = CTX
    st, raw = http('https://www.youtube.com/youtubei/v1/' + ep + '?prettyPrint=false', json.dumps(b).encode(), {'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com', 'X-YouTube-Client-Name': '1', 'X-YouTube-Client-Version': CTX['client']['clientVersion']})
    with LOCK: STAT['inner_' + ep.split('/')[0] + '_' + str(st)] += 1
    if st != 200: return None
    try: return json.loads(raw)
    except Exception: return None


def walk(o, key, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: out.append(v)
            else: walk(v, key, out)
    elif isinstance(o, list):
        for v in o: walk(v, key, out)
    return out


def txt(o):
    if not o: return ''
    if isinstance(o, str): return o
    if 'simpleText' in o: return o['simpleText']
    if 'content' in o and isinstance(o['content'], str): return o['content']
    return ''.join(r.get('text', '') for r in o.get('runs', []))


def secs(s):
    p = [int(x) for x in re.findall(r'\d+', s or '')]
    if not p or ':' not in (s or ''): return 0
    v = 0
    for x in p: v = v * 60 + x
    return v


def views(s):
    m = re.search(r'([\d,.]+)\s*([KMB]?)', (s or '').replace('No views', '0'))
    if not m: return 0
    try: v = float(m.group(1).replace(',', ''))
    except Exception: return 0
    return int(v * {'': 1, 'K': 1e3, 'M': 1e6, 'B': 1e9}[m.group(2)])


def age_years(s):
    m = re.search(r'(\d+)\s+(year|month|week|day|hour|minute)', s or '')
    if not m: return -1
    n = int(m.group(1)); u = m.group(2)
    return n if u == 'year' else n / 12 if u == 'month' else n / 52 if u == 'week' else 0


def vr_to(v):
    vid = v.get('videoId')
    if not vid: return None
    ow = v.get('ownerText') or v.get('longBylineText') or v.get('shortBylineText') or {}
    chid = ''
    for r in ow.get('runs', []):
        chid = (((r.get('navigationEndpoint') or {}).get('browseEndpoint') or {}).get('browseId')) or chid
    badges = json.dumps(v.get('ownerBadges') or [])
    live = 'LIVE' in json.dumps(v.get('badges') or []) or 'upcomingEventData' in v
    dur = secs(txt(v.get('lengthText'))) or int(v.get('lengthSeconds') or 0)
    vw = views(txt(v.get('viewCountText'))); ag = age_years(txt(v.get('publishedTimeText')))
    info = txt(v.get('videoInfo'))
    if info:
        vw = vw or views(info.split('•')[0]); ag = ag if ag >= 0 else age_years(info)
    return {'vid': vid, 't': txt(v.get('title')), 'ch': txt(ow), 'chid': chid, 'dur': dur, 'views': vw, 'age': ag, 'ver': 1 if 'VERIFIED' in badges.upper() else 0, 'live': 1 if live else 0}


def search(q, pages=2, params='EgQQARgC'):
    out = []
    d = inner('search', {'query': q, 'params': params})
    for _ in range(pages):
        if not d: break
        for v in walk(d, 'videoRenderer', []):
            x = vr_to(v)
            if x: out.append(x)
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or left() < 120: break
        time.sleep(0.4 + random.random() * 0.6)
        d = inner('search', {'continuation': tk[0]})
    return out


def search_playlists(q):
    out = []
    d = inner('search', {'query': q, 'params': 'EgIQAw=='})
    if not d: return out
    for p in walk(d, 'playlistRenderer', []):
        if p.get('playlistId'): out.append({'pid': p['playlistId'], 't': txt(p.get('title')), 'n': int(re.sub(r'\D', '', str(p.get('videoCount') or '0')) or 0), 'ch': txt(p.get('longBylineText') or p.get('shortBylineText'))})
    for p in walk(d, 'lockupViewModel', []):
        if 'PLAYLIST' not in str(p.get('contentType')) or not p.get('contentId'): continue
        md = (p.get('metadata') or {}).get('lockupMetadataViewModel') or {}
        bt = ' '.join(txt(x) for x in walk(p, 'thumbnailBadgeViewModel', []) if isinstance(x, dict) and x.get('text')) or ' '.join(str(x.get('text')) for x in walk(p, 'thumbnailBadgeViewModel', []) if isinstance(x, dict))
        m = re.search(r'(\d[\d,]*)\s+(videos|episodes|lessons)', bt)
        out.append({'pid': p['contentId'], 't': txt(md.get('title')), 'n': int(m.group(1).replace(',', '')) if m else 0, 'ch': ''})
    return out


def playlist_videos(pid, maxpages=12):
    out = []
    if not pid.startswith(('PL', 'OL', 'UU', 'FL')): return out
    d = inner('browse', {'browseId': 'VL' + pid})
    for _ in range(maxpages):
        if not d: break
        got = 0
        for v in walk(d, 'playlistVideoRenderer', []):
            x = vr_to(v)
            if x: out.append(x); got += 1
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or not got or left() < 120: break
        time.sleep(0.3 + random.random() * 0.5)
        d = inner('browse', {'continuation': tk[-1]})
    if out: return out
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'playlistend': 1200}) as y:
            r = y.extract_info('https://www.youtube.com/playlist?list=' + pid, download=False)
        for e in (r or {}).get('entries') or []:
            if not e or not e.get('id'): continue
            out.append({'vid': e['id'], 't': e.get('title') or '', 'ch': e.get('channel') or e.get('uploader') or '', 'chid': e.get('channel_id') or '', 'dur': int(e.get('duration') or 0), 'views': int(e.get('view_count') or 0), 'age': -1, 'ver': 0, 'live': 0})
    except Exception as ex:
        with LOCK: STAT['plfail'] += 1
    return out


def channel_videos(chid, ch, maxpages=40):
    out = []
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'playlistend': 6000}) as y:
            r = y.extract_info('https://www.youtube.com/channel/' + chid + '/videos', download=False)
        for e in (r or {}).get('entries') or []:
            if not e or not e.get('id'): continue
            out.append({'vid': e['id'], 't': e.get('title') or '', 'ch': ch or (r.get('channel') or ''), 'chid': chid, 'dur': int(e.get('duration') or 0), 'views': int(e.get('view_count') or 0), 'age': -1, 'ver': 1 if r.get('channel_is_verified') else 0, 'live': 1 if e.get('live_status') in ('is_live', 'is_upcoming') else 0})
    except Exception as ex:
        with LOCK: STAT['flatfail'] += 1
    if out: return out
    d = inner('browse', {'browseId': chid, 'params': 'EgZ2aWRlb3PyBgQKAjoA'})
    ver = 0
    if d and 'VERIFIED' in json.dumps(walk(d, 'badges', []))[:4000].upper(): ver = 1
    for _ in range(maxpages):
        if not d: break
        got = 0
        for v in walk(d, 'videoRenderer', []):
            x = vr_to(v)
            if x:
                x['ch'] = x['ch'] or ch; x['chid'] = x['chid'] or chid; x['ver'] = x['ver'] or ver
                out.append(x); got += 1
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or not got or left() < 120: break
        time.sleep(0.3 + random.random() * 0.5)
        d = inner('browse', {'continuation': tk[-1]})
    return out


def oembed(vid):
    st, raw = http('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + vid, safe=''), tries=3, timeout=15)
    return st


def base_title(t):
    return re.sub(r'\s+', ' ', re.sub(r'\([^)]*\)', ' ', t)).strip()


def load_shows():
    L = json.load(open(os.path.join(HV, 'shows_yt_needs.json'), encoding='utf-8'))
    S = {}
    for x in L:
        if x.get('type') in SKIPK: continue
        bt = base_title(x['title'])
        hint = re.search(r'\((\d{4})', x['title'])
        k = nzk(bt) + ('|' + hint.group(1) if hint else '')
        if not nzk(bt) or k in S: continue
        ys = x.get('years') or []
        al = set()
        for a in [bt] + [base_title(a) for a in x.get('aka') or []]:
            for part in re.split(r'\s+/\s+', a):
                n = nz(part)
                if len(n) >= 2: al.add(n); al.add(re.sub(r'^the ', '', n))
        al = set(a for a in al if len(a) >= 2 and not a.isdigit() or a in ('2020',))
        words = min(len(nzk(a).split()) for a in al) if al else 9
        kind = 'date' if x.get('type') in DATEK else 'ep'
        S[k] = {'k': k, 'title': x['title'], 'bt': bt, 'type': x.get('type') or 'other', 'kind': kind, 'q': QMAP.get(x.get('type'), 'prime'), 'net': x.get('net') or '', 'y0': ys[0] if ys else 0, 'y1': ys[-1] if ys else 0, 'hint': int(hint.group(1)) if hint else 0, 'pri': x.get('pri') or 3, 'al': sorted(al), 'amb': 2 if words <= 1 else 1 if words == 2 else 0}
        if re.search(r'(?i)wrestl|wwf|\bwcw\b|\bnwa\b|clash of the champions|titans', x['title']): S[k]['q'] = 'wrest'
    return S


def tvget(url):
    for a in range(5):
        st, raw = http(url, tries=1, timeout=20)
        if st == 200:
            try: return json.loads(raw)
            except Exception: return None
        if st == 404: return None
        time.sleep(1.5 + a * 2.5 + random.random())
    with LOCK: STAT['tvfail'] += 1
    return None


def guide_ok(g, s):
    if not g or g.get('miss') or not g.get('episodes'): return False
    try: py = int(str(g.get('premiered') or '')[:4])
    except Exception: return False
    y0 = s['hint'] or s['y0']
    if not y0: return g.get('country') == 'US'
    if s['hint']: return abs(py - y0) <= 1
    if abs(py - y0) <= 2: return True
    return False


def fetch_guide(s):
    best = None
    for name in [s['bt']] + [a for a in s['al'] if a != nz(s['bt']) and len(a) > 5][:1]:
        j = tvget('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(name))
        time.sleep(0.4)
        for r in j or []:
            sh = r.get('show') or {}
            nk = nzk(sh.get('name', ''))
            pm = sh.get('premiered') or ''
            if not pm: continue
            net = sh.get('network') or sh.get('webChannel') or {}
            cc = ((net.get('country') or {}).get('code')) or ''
            sc = 0
            if nk in [nzk(a) for a in s['al']]: sc += 4
            elif any(nk.startswith(nzk(a) + ' ') for a in s['al']): sc += 1.5
            else: continue
            if cc == 'US': sc += 1
            dh = abs(int(pm[:4]) - (s['hint'] or s['y0'] or int(pm[:4])))
            sc += 2 if dh <= 1 else 1 if dh <= 2 else -3
            if not best or sc > best[0]: best = (sc, sh)
        if best and best[0] >= 5: break
    if not best or best[0] < 5: return {'miss': 1}
    sh = best[1]
    eps = tvget('https://api.tvmaze.com/shows/%d/episodes' % sh['id']) or []
    time.sleep(0.4)
    net = sh.get('network') or sh.get('webChannel') or {}
    return {'title': sh.get('name'), 'id': sh['id'], 'premiered': sh.get('premiered'), 'ended': sh.get('ended'), 'network': net.get('name', ''), 'country': ((net.get('country') or {}).get('code')) or '', 'episodes': [[e.get('season') or 0, e.get('number') or 0, e.get('airdate') or '', e.get('name') or ''] for e in eps]}


def selected(S):
    pri = set(int(x) for x in re.findall(r'\d', PRI)) or {1, 2, 3}
    only = set(nzk(base_title(x)) for x in ONLY)
    return [s for s in S.values() if (s['k'].split('|')[0] in only if only else s['pri'] in pri)]


def plan():
    S = load_shows(); sel = selected(S)
    EPG = {}
    p = os.path.join(CAT, 'epguide.json.gz')
    if os.path.exists(p):
        try: EPG = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: EPG = {}
    prev = collections.Counter()
    if os.path.exists(OUT):
        try:
            for it in json.load(gzip.open(OUT, 'rt', encoding='utf-8')): prev[it['k']] += 1
        except Exception: pass
    G = {}
    todo = []
    for s in sel:
        if s['kind'] != 'ep': continue
        g = None
        for key in set([s['k'].split('|')[0]] + [nzk(a) for a in s['al']] + [re.sub(r'[^a-z0-9]+', ' ', a.lower()).strip() for a in [s['bt']]]):
            c = EPG.get(key) or EPG.get(re.sub(r'^the ', '', key))
            if guide_ok(c, s): g = c; break
        if g: G[s['k']] = g
        else: todo.append(s)
    print('selected shows', len(sel), 'episode kind', sum(1 for s in sel if s['kind'] == 'ep'), 'guides cached', len(G), 'to fetch', len(todo), flush=True)
    def one(s):
        if time.time() - T0 > 18 * 60: return
        g = fetch_guide(s)
        if guide_ok(g, s):
            with LOCK: G[s['k']] = g
    with ThreadPoolExecutor(3) as ex: list(ex.map(one, todo))
    print('guides total', len(G), 'stat', dict(STAT), flush=True)
    tasks = []
    for s in sel:
        g = G.get(s['k'])
        eps = [e for e in (g or {}).get('episodes', []) if e[0] and e[1]] if g else []
        t = dict(s); bt = s['bt']
        t['eps'] = eps
        t['gid'] = (g or {}).get('id', 0)
        ys = list(range(max(1984, s['y0'] or 1984), min(2004, s['y1'] or 2004) + 1)) or [0]
        nw = s['net'].upper() if s['net'] in ('nbc', 'abc', 'cbs', 'fox', 'pbs', 'hbo', 'mtv', 'bet', 'tnn', 'espn', 'cnn', 'tbs', 'tnt', 'usa') else ''
        qs = []; epq = []; plq = []
        names = [bt] + [a for a in (x for x in s['al'] if x != nz(bt) and x != nzk(bt)) if len(a) >= 5][:1]
        if s['kind'] == 'ep':
            for nm in names:
                qs += [nm + ' full episode', nm + ' full episodes', nm + ' episode ' + (str(s['y0']) if s['y0'] else ''), nm + ' ' + (nw or 'tv series') + ' ' + (str(s['y0']) if s['y0'] else '')]
            seas = sorted(set(e[0] for e in eps if str(e[2])[:4] <= '2004'))[:16]
            qs += [bt + ' season %d full episode' % n for n in seas]
            if s['pri'] <= 2: qs += [bt + ' s%02d' % n for n in seas] + [bt + ' season %d episode 1' % n for n in seas]
            if not seas: qs += [bt + ' season 1 episode 1', bt + ' s01e01', bt + ' pilot episode', bt + ' ' + str(s['y0'] or '') + ' episode 1']
            cap = DEEP or (400 if s['pri'] == 1 else 150 if s['pri'] == 2 else 40)
            pool = [e for e in eps if str(e[2])[:4] <= '2004']
            if len(pool) > cap:
                random.seed(s['k']); pool = sorted(random.sample(pool, cap))
            for e in pool:
                et = nz(str(e[3]))
                if len(et) >= 5 and not re.match(r'^(episode|part|pilot|show|chapter)\b', et): epq.append(bt + ' ' + str(e[3]))
                elif s['pri'] == 1: epq.append(bt + ' season %d episode %d' % (e[0], e[1]))
            plq = [bt + ' full episodes', bt + ' season 1'] if s['pri'] <= 2 else [bt + ' full episodes']
        else:
            for nm in names:
                qs += [nm + ' full episode', nm + ' full show', nm + ' ' + (nw + ' ' if nw else '') + 'full broadcast']
                qs += [nm + ' %d' % y for y in ys if y] + [nm + ' %d full' % y for y in ys if y]
            if s['pri'] <= 2:
                step = 1 if s['pri'] == 1 else 3
                epq = [bt + ' ' + mo + ' %d' % y for y in ys if y for mo in MONTHS[::step]]
            plq = [bt + ' full episodes'] if s['pri'] <= 2 else []
        t['qs'] = [re.sub(r'\s+', ' ', q).strip() for q in qs]; t['epq'] = epq; t['plq'] = plq
        t['prev'] = prev.get(s['title'], 0)
        tasks.append(t)
    tasks.sort(key=lambda t: (t['pri'], t['title'].lower()))
    os.makedirs(PARTS, exist_ok=True)
    json.dump({'tasks': tasks, 'all': {k: {x: s[x] for x in ('title', 'pri', 'type', 'kind')} for k, s in S.items()}}, gzip.open(os.path.join(PARTS, 'ytn_plan.json.gz'), 'wt', encoding='utf-8'))
    print('tasks', len(tasks), 'queries', sum(len(t['qs']) + len(t['epq']) + len(t['plq']) for t in tasks))
    print('PLAN (pri, kind, amb, show, years, guide eps, queries, previous items)')
    for t in tasks[:700]:
        print(' ', t['pri'], t['kind'].ljust(4), t['amb'], t['title'][:44].ljust(44), t['y0'], t['y1'], str(len(t['eps'])).rjust(5), str(len(t['qs']) + len(t['epq'])).rjust(5), str(t['prev']).rjust(5))


def pdate(s):
    s = s.lower()
    m = re.search(r'\b(19[5-9]\d|20[0-2]\d)[-./ ](\d{1,2})[-./ ](\d{1,2})\b', s)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./]((?:19)?[5-9]\d|20[0-2]\d|[0-2]\d)\b', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = m.group(3); y = y if len(y) == 4 else ('19' + y if y[0] in '56789' else '20' + y)
        return '%s-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[5-9]\d|20[0-2]\d)\b', s)
    if m and 1 <= int(m.group(2)) <= 31: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1)], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[5-9]\d|20[0-2]\d)\b', s)
    if m and 1 <= int(m.group(1)) <= 31: return '%s-%02d-%02d' % (m.group(3), MON[m.group(2)], int(m.group(1)))
    return ''


def durfit(t, d):
    ty = t['type']
    def rng(*rs):
        return any(a <= d <= b for a, b in rs)
    if ty == 'sitcom': return 1 if rng((1140, 1900)) else 2 if rng((2500, 3300)) else 0
    if ty == 'drama': return 1 if rng((2280, 3720)) else 2 if rng((4900, 6300)) else 3 if rng((1260, 1900)) else 0
    if ty == 'kids': return 1 if rng((600, 1900), (2300, 3600)) else 0
    if ty in ('doc',): return 1 if rng((1200, 7500)) else 0
    if ty in ('cook',): return 1 if rng((1140, 1900), (2400, 3600)) else 0
    if ty in ('game', 'talk', 'soap', 'relig'): return 1 if rng((1080, 3900)) else 0
    if ty in ('late',): return 1 if rng((1200, 6600)) else 0
    if ty in ('news', 'mag', 'morning', 'gov'): return 1 if rng((900, 4 * 3600)) else 0
    if ty in ('music',): return 1 if rng((1200, 7500)) else 0
    if ty in ('sports',): return 1 if rng((1500, 5 * 3600)) else 0
    if ty in ('special',): return 1 if rng((1200, 4 * 3600)) else 0
    return 1 if rng((1140, 1900), (2280, 3900), (4900, 7500)) else 0


def bytitle(G, n, hit):
    rest = (' ' + n + ' ').replace(' ' + hit + ' ', '  ', 1)
    best = None
    for et, e in G['ti']:
        if rest.find(' ' + et + ' ') >= 0 and (not best or len(et) > len(best[0])): best = (et, e)
    return best[1] if best else None


def build_M(tasks):
    M = {}
    for t in tasks:
        eps = t.get('eps') or []
        if not eps: M[t['k']] = None; continue
        cnt = collections.Counter(nz(str(e[3])) for e in eps)
        als = set(t['al'])
        ti = []
        for e in eps:
            et = nz(str(e[3]))
            if len(et) >= 6 and cnt[et] == 1 and (len(et.split()) >= 2 or len(et) >= 8) and et not in als and et not in STOPW and not re.match(r'^(episode|part|pilot|show|chapter|season|the pilot|series) ?\d*$', et) and not re.match(r'^(episode|show|chapter) ', et): ti.append((et, e))
        dc = collections.Counter(str(e[2]) for e in eps)
        M[t['k']] = {'se': {(e[0], e[1]): e for e in eps}, 'ti': ti, 'ad': {str(e[2]): e for e in eps if re.match(r'\d{4}-\d\d-\d\d$', str(e[2])) and dc[str(e[2])] == 1}}
    return M


def rawpat(a):
    return '[^a-z0-9]+'.join('[^a-z0-9]*'.join(re.escape(ch) for ch in w) for w in a.split())


def match(t, c, M):
    T = c['t']
    if c.get('live') or not c.get('dur'): return None, 'live'
    if re.search(r'[^\x00-\x7f]', re.sub(r'[’‘“”–—…é·•|®™½]', '', T)): return None, 'nonascii'
    n = nz(T); pn = ' ' + n + ' '
    hit = ''
    for a in sorted(t['al'], key=lambda a: -len(a)):
        if pn.find(' ' + a + ' ') >= 0: hit = a; break
    if not hit: return None, 'noname'
    G = M.get(t['k'])
    raw = re.sub(r"[’'`]", '', T.lower().replace('&', ' and '))
    mm = re.search(r'(?<![a-z0-9])' + rawpat(hit) + r'(?![a-z0-9])', raw)
    Ts = (raw[:mm.start()] + ' ~ ' + raw[mm.end():]) if mm else raw
    bt0 = bytitle(G, n, hit) if G else None
    Tj = Ts
    if bt0 is not None:
        me = re.search(r'(?<![a-z0-9])' + rawpat(nz(str(bt0[3]))) + r'(?![a-z0-9])', Ts)
        if me: Tj = Ts[:me.start()] + ' ~ ' + Ts[me.end():]
    if BADT.search(Tj) or PARTX.search(Tj): return None, 'badword'
    if JUNKT.search(Tj) or JUNKC.search(c.get('ch') or ''): return None, 'junk'
    if SOFTJ.search(re.sub(r'(?i)\b(vs\.?|versus|figure|pitch|the game|hours?)\b', ' ', Tj) if t['type'] in ('sports', 'special') else Tj): return None, 'junk'
    df = durfit(t, c['dur'])
    if not df: return None, 'duration'
    y0 = t['hint'] or t['y0'] or 1950; y1 = t['y1'] or 2004
    if t['hint'] and not t['y1']: y1 = t['hint'] + 8
    hi = min(y1 + 1, 2004) if t['kind'] == 'date' else y1 + 1
    ys = [int(y) for y in re.findall(r'(?<![\d$#])(19[4-9]\d|20[0-2]\d)(?![\d,]*\d)', Ts)]
    yin = [y for y in ys if y0 - 1 <= y <= hi]; yout = [y for y in ys if not (y0 - 1 <= y <= hi)]
    d0 = pdate(Ts)
    r = {'se': None, 'ep': '', 'ad': '', 'e': 0}
    strong = 0
    ms = SEP.search(Ts)
    g = [int(v) for v in ms.groups() if v] if ms else None
    off = 1 if c.get('ver') or c.get('off') or OFFX.search(c.get('ch') or '') else 0
    if G:
        e = G['se'].get((g[0], g[1])) if g else None
        bt = bt0
        if bt is not None and bt is not e:
            if e and len(nz(str(e[3]))) >= 4 and pn.find(' ' + nz(str(e[3])) + ' ') >= 0: bt = e
            e = bt
        if e is None and d0 and d0 in G['ad']: e = G['ad'][d0]; bt = e
        if e is not None:
            if str(e[2])[:4] > '2004': return None, 'post2004'
            r['se'] = [e[0], e[1]]; r['ep'] = e[3]; r['ad'] = str(e[2] or '') if re.match(r'\d{4}-\d\d-\d\d$', str(e[2] or '')) else ''
            strong = 2 if bt is e else 1
            if strong == 1:
                ew = set(nz(str(e[3])).split())
                rest = [w for w in re.sub(SERX, ' ', pn.replace(' ' + hit + ' ', ' ', 1)).split() if w not in STOPW and not w.isdigit() and w not in MONW]
                if len(nz(str(e[3]))) >= 5 and not re.match(r'^episode', nz(str(e[3]))) and any(len(w) >= 4 for w in rest) and not (ew & set(rest)): r['m'] = 'episode title differs from guide'
        elif g:
            r['se'] = g[:2]; r['m'] = 'episode number not in guide'
    elif g:
        r['se'] = g[:2]; strong = 0.5
    if not r['ad'] and d0:
        dy = int(d0[:4])
        if y0 - 1 <= dy <= hi and d0 <= '2004-12-31' and d0 >= '1950-01-01':
            r['ad'] = d0; strong = max(strong, 1.5)
        elif t['kind'] == 'date' or dy > 2004: return None, 'date outside run'
    if strong < 1 and yout and not yin: return None, 'year outside run'
    if LATEY.search(Ts) and not yin and strong < 2: return None, 'late year'
    nws = NETW.get(t['net'], [t['net']] if t['net'] else [])
    netw = any(pn.find(' ' + w + ' ') >= 0 for w in nws if w)
    full = bool(FULLX.search(T)) or c.get('pl')
    i = pn.find(' ' + hit + ' ')
    ew = set(nz(str(r['ep'] or '')).split())
    pre = [w for w in re.sub(SERX, ' ', pn[:i]).split() if w not in STOPW and w not in ew and not w.isdigit() and w not in MONW]
    post = pn[i + len(hit) + 1:].split()
    b4 = raw[:mm.start()].rstrip()[-1:] if mm else ''; af = raw[mm.end():].lstrip()[:1] if mm else ''
    pos = not pre or (b4 and b4 in '|-:•–"([')
    nxt = True
    if post:
        w = post[0]
        nxt = bool(w in NEXTW or w in MONW or w in ew or w.isdigit() or re.match(r'^(s\d{1,2}(e\d{1,3})?|e\d{1,3}|ep\d{1,3}|\d{1,2}x\d{2,3}|19\d\d|200\d)$', w) or (af and af in '|-:•–("[#/,.'))
    amb = t['amb']
    if t['kind'] == 'date':
        if not r['ad']:
            if not (yin and full and pos and nxt): return None, 'undated'
            r['m'] = 'year only'
        elif amb == 2:
            if not (pos and nxt): return None, 'position'
            if pre or not (full or netw or off): r['m'] = 'common name'
        elif amb == 1:
            if not pos and not nxt: return None, 'position'
            if not pos or not nxt: r['m'] = 'title has extra words'
        elif not pos: r['m'] = 'title has extra words'
    elif amb:
        if strong >= 2:
            if not pos and not nxt and amb == 2: r['m'] = 'title has extra words'
        else:
            if not pos or not nxt: return None, 'position'
            if strong >= 1:
                if amb == 2 and not (yin or netw or off or r['ad'] and strong == 1.5): r.setdefault('m', 'common name')
            elif r['se'] and not r.get('m'):
                if amb == 2 and not (yin or netw): r['m'] = 'common name, no episode guide'
            elif yin and full:
                if amb == 2: r['m'] = 'common name'
            elif full and amb == 1:
                r.setdefault('m', 'episode not identified')
            elif r.get('m') and amb == 1: pass
            else: return None, 'unidentified'
    else:
        if strong < 1 and not r['se']:
            if not (full or yin or netw):
                if not (pos and nxt): return None, 'unidentified'
                r['m'] = 'episode not identified'
            elif not pos: r['m'] = 'title has extra words'
            elif G and not off and not r.get('m'): r['m'] = 'episode not identified'
    if df == 2 and strong < 2: r.setdefault('m', 'double length')
    if df == 3:
        if strong < 2: return None, 'duration'
        r.setdefault('m', 'short for the show')
    y = r['ad'][:4] if r['ad'] else str(yin[0]) if yin else ''
    r['e'] = int(y) if y else (t['y0'] if 1984 <= (t['y0'] or 0) <= 2004 else 0)
    return r, ''


def stable(c):
    off = 1 if c.get('ver') or (OFFX.search(c.get('ch') or '') and c.get('views', 0) >= 200) else 0
    if c.get('ver'): return 1, 'verified channel'
    if c['age'] >= 4 and c.get('views', 0) >= 1000: return off, 'up %d years, %d views' % (int(c['age']), c['views'])
    if off and c['age'] >= 1: return 1, 'rights-holder style channel'
    return off, ''


def run_search():
    P = json.load(gzip.open(os.path.join(PARTS, 'ytn_plan.json.gz'), 'rt', encoding='utf-8'))
    tasks = P['tasks']
    M = build_M(tasks)
    byk = {t['k']: t for t in tasks}
    jobs = []
    for t in tasks:
        short = t['type'] in ('sitcom', 'kids', 'cook', 'game')
        for j, q in enumerate(t['qs']):
            jobs.append((t['pri'], j, t['k'], q, 2, 'EgQQARgC'))
            if short and j < 2: jobs.append((t['pri'], j + 0.5, t['k'], q, 1, 'EgIQAQ=='))
        for j, q in enumerate(t['plq']): jobs.append((t['pri'], j + 0.7, t['k'], q, 0, 'pl'))
        for j, q in enumerate(t['epq']): jobs.append((t['pri'] + 0.5, j, t['k'], q, 1, 'EgIQAQ==' if short else 'EgQQARgC'))
    jobs.sort(key=lambda x: (x[0], x[1], x[2]))
    jobs = [j for n, j in enumerate(jobs) if n % SHARDS == SHARD]
    print('shard', SHARD, 'queries', len(jobs), flush=True)
    acc = {}; seen = set(); chan = collections.Counter(); chname = {}; chver = {}; rejs = collections.Counter(); rsamp = collections.defaultdict(list); perq = collections.Counter(); pls = set()
    def take(k, c, src):
        t = byk[k]; r, why0 = match(t, c, M)
        if not r:
            rejs[why0] += 1
            if why0 not in ('noname', 'live') and len(rsamp[why0]) < 400: rsamp[why0].append((t['title'], c['t'], c['dur'] // 60))
            return False
        off, why = stable(c)
        if not why:
            if 0 <= c['age'] < 1 and c.get('views', 0) < 300 and not off: rejs['too new'] += 1; return False
            why = 'maybe: up %s years, %d views' % (('%d' % int(c['age'])) if c['age'] >= 0 else '?', c.get('views', 0)); c = dict(c, maybe=1)
        if r.get('m'): why = 'maybe: ' + r['m'] + '; ' + re.sub(r'^maybe: ', '', why); c = dict(c, maybe=1)
        if c['vid'] in acc: return True
        acc[c['vid']] = dict(c, k=k, r=r, off=off, why=why, src=src)
        return True
    def one(job):
        if left() < BUDGET * 0.42: return
        _, _, k, q, pages, params = job
        t = byk[k]
        if params == 'pl':
            if left() < BUDGET * 0.5: return
            cand = []
            for p in search_playlists(q)[:8]:
                pn = ' ' + nz(p['t']) + ' '
                if p['pid'] in pls or not any(pn.find(' ' + a + ' ') >= 0 for a in t['al']): continue
                if BADT.search(p['t']) or JUNKT.search(p['t']) or LATEY.search(p['t']): continue
                cand.append(p)
            for p in cand[:4]:
                with LOCK:
                    if p['pid'] in pls: continue
                    pls.add(p['pid'])
                vs = playlist_videos(p['pid'])
                got = 0
                with LOCK:
                    STAT['playlists'] += 1; STAT['playlist_videos'] += len(vs)
                    for c in vs:
                        c['pl'] = 1
                        chname[c['chid']] = c['ch']
                        if (k, c['vid']) in seen: continue
                        seen.add((k, c['vid']))
                        if take(k, c, 'pl'): chan[c['chid']] += 1; got += 1; perq[k] += 1
                print('  playlist', t['title'][:30], '|', p['t'][:50], '| videos', len(vs), 'accepted', got, flush=True)
                time.sleep(0.5 + random.random())
            return
        res = search(q, pages, params)
        with LOCK:
            STAT['queries'] += 1; STAT['results'] += len(res)
            for c in res:
                chname[c['chid']] = c['ch']
                if c['ver']: chver[c['chid']] = 1
                if (k, c['vid']) in seen: continue
                seen.add((k, c['vid']))
                if take(k, c, 'q'): chan[c['chid']] += 1; perq[k] += 1
        time.sleep(0.3 + random.random() * 0.6)
    with ThreadPoolExecutor(THREADS) as ex: list(ex.map(one, jobs))
    print('after queries: accepted', len(acc), 'stat', dict(STAT), 'rejected', dict(rejs), flush=True)
    alidx = sorted(((a, t['k']) for t in tasks for a in t['al'] if len(a) >= 5), key=lambda x: -len(x[0]))
    tops = [c for c, n in chan.most_common(300) if c and (n >= 4 or chver.get(c) and n >= 2)][:45]
    print('channels to enumerate', len(tops), flush=True)
    def enum(chid):
        if left() < BUDGET * 0.2: return
        vs = channel_videos(chid, chname.get(chid, ''))
        ages = sorted(c['age'] for c in acc.values() if c['chid'] == chid and c['age'] >= 0)
        med = ages[len(ages) // 2] if ages else -1
        got = 0
        with LOCK:
            STAT['chan_enum'] += 1; STAT['chan_videos'] += len(vs)
            for c in vs:
                if c['age'] < 0: c['age'] = med
                if chver.get(chid): c['ver'] = 1
                pn = ' ' + nz(c['t']) + ' '
                for a, k in alidx:
                    if pn.find(' ' + a + ' ') >= 0:
                        if (k, c['vid']) not in seen:
                            seen.add((k, c['vid']))
                            if take(k, c, 'ch'): got += 1
                        break
        print('  channel', (chname.get(chid, '') or chid)[:40], 'videos', len(vs), 'accepted', got, flush=True)
    with ThreadPoolExecutor(max(2, THREADS // 2)) as ex: list(ex.map(enum, tops))
    items = list(acc.values())
    ages = collections.defaultdict(list)
    for c in items:
        if c['age'] >= 0: ages[c['chid']].append(c['age'])
    for c in items:
        if c['age'] < 0 and ages.get(c['chid']):
            a = sorted(ages[c['chid']]); c['age'] = a[len(a) // 2]; c['inh'] = 1
            off, why = stable(c)
            if why and c.get('maybe') and not c['r'].get('m'): c.pop('maybe'); c['why'] = why + ' (channel age)'; c['off'] = off
    best = {}
    for c in items:
        r = c['r']; ek = (c['k'], tuple(r['se']) if r['se'] else (r['ad'] or c['vid']))
        sc = (c['off'] * 3 + (0 if c.get('maybe') else 2) + (1 if c['age'] >= 4 else 0) + min(2, c['views'] / 5e5), c['dur'])
        best.setdefault(ek, []).append((sc, c))
    items = []
    for ek, L in best.items():
        L.sort(key=lambda x: x[0], reverse=True)
        items += [x[1] for x in L[:2]]
    print('distinct episodes', len(best), 'kept with alternates', len(items), flush=True)
    def det(c):
        if left() < 60: c['oe'] = -1; return
        c['oe'] = oembed(c['vid'])
        time.sleep(0.15 + random.random() * 0.3)
    with ThreadPoolExecutor(THREADS) as ex: list(ex.map(det, items))
    print('stat', dict(STAT), 'oembed', dict(collections.Counter(c.get('oe') for c in items)), flush=True)
    print('PER SHOW (accepted by search)')
    for t in tasks:
        n = sum(1 for c in items if c['k'] == t['k'])
        if n or t['pri'] == 1: print(' ', t['pri'], t['title'][:44].ljust(44), n)
    random.seed(SHARD)
    print('REJECT SAMPLES')
    for why0, L in rsamp.items():
        for x in random.sample(L, min(len(L), 14 if why0 not in ('duration', 'badword') else 6)): print('  ', why0.ljust(18), '|', x[0][:26], '|', x[2], 'min |', x[1][:90])
    os.makedirs(PARTS, exist_ok=True)
    json.dump(items, gzip.open(os.path.join(PARTS, 'ytn-%d.json.gz' % SHARD), 'wt', encoding='utf-8'))


def rank(it):
    return (0 if it.get('keep') else 1, 1 if it.get('ad') else 0, it.get('off', 0), it.get('views', 0))


def merge():
    P = json.load(gzip.open(os.path.join(PARTS, 'ytn_plan.json.gz'), 'rt', encoding='utf-8'))
    tasks = P['tasks']; ALL = P['all']
    byk = {t['k']: t for t in tasks}; byt = {t['title']: t for t in tasks}
    M = build_M(tasks)
    old = []
    if os.path.exists(OUT):
        try: old = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
        except Exception: old = []
    other = set(); osek = set()
    for p in sorted(glob.glob(os.path.join(CAT, 'yt_*.json.gz'))):
        if os.path.basename(p) == 'yt_needs.json.gz': continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(L, list): continue
        for x in L:
            if not isinstance(x, dict): continue
            if x.get('vid'): other.add(x['vid'])
            if x.get('keep'): continue
            if x.get('se') and x.get('ad'): osek.add((nzk(str(x.get('k'))), tuple(x['se'])))
    cand = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'ytn-*.json.gz'))):
        try: cand += json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception as e: print('bad part', p, e)
    rej = collections.Counter(); out = {}
    def put(it):
        ek = (it['k'], tuple(it.get('se') or ()) or it.get('ad') or it['vid'])
        if ek in out and out[ek]['vid'] != it['vid']:
            a = out[ek]
            if rank(it) > rank(a): out[ek] = it; it = a
            ek = (it['k'], 'alt', tuple(it.get('se') or ()) or it.get('ad') or it['vid'])
            if ek in out and rank(out[ek]) >= rank(it): return
        out[ek] = it
    purged = 0
    for it in old:
        if it['vid'] in other: rej['in other catalog'] += 1; continue
        t = byt.get(it['k'])
        if t:
            r, why0 = match(t, {'t': it['t'], 'dur': it['dur'], 'live': 0, 'ch': it.get('ch'), 'off': it.get('off'), 'pl': 1}, M)
            if not r: purged += 1; continue
            w = re.sub(r'^maybe: ', '', str(it.get('why', ''))).split('; ')[-1]
            sm = re.match(r'up (\?|\d+) years, (\d+) views', w)
            st_ok = not sm or (sm.group(1) != '?' and int(sm.group(1)) >= 4 and (int(sm.group(2)) >= 1000 or 'similar uploads' in w))
            it['ad'] = r['ad'] if re.match(r'\d{4}-\d\d-\d\d$', r['ad'] or '') else ''
            it['e'] = int(it['ad'][:4]) if it['ad'] else r['e']
            it.pop('se', None); it.pop('ep', None)
            if r['se']: it['se'] = r['se']; it['ep'] = r['ep']
            if r.get('m'): it['keep'] = 'maybe'; it['why'] = 'maybe: ' + r['m'] + '; ' + w
            elif st_ok: it.pop('keep', None); it['why'] = w
            else: it['keep'] = 'maybe'; it['why'] = 'maybe: ' + w
        elif BADT.search(it['t']) or JUNKT.search(it['t']) or JUNKC.search(it.get('ch') or ''): purged += 1; continue
        put(it)
    print('purged from previous', purged)
    for c in cand:
        t = byk.get(c['k'])
        if not t: continue
        if c.get('oe') != 200: rej['oembed_%s' % c.get('oe')] += 1; continue
        if c['vid'] in other: rej['in other catalog'] += 1; continue
        r = c['r']
        ad = r['ad'] if re.match(r'\d{4}-\d\d-\d\d$', r['ad'] or '') else ''
        if r['se'] and (nzk(t['bt']), tuple(r['se'])) in osek: rej['episode in other catalog'] += 1; continue
        q = t['q']
        if q == 'prime' and t['y1'] and t['y1'] < 1984: q = 'rerun'
        it = {'i': 'yt:' + c['vid'], 'vid': c['vid'], 't': c['t'], 'ch': c['ch'], 'chid': c['chid'], 'off': c['off'], 'dur': c['dur'], 'up': '', 'views': c['views'], 'q': q, 'k': t['title'], 'ad': ad, 'e': int(ad[:4]) if ad else r['e'], 'net': t['net'], 'ct': 'yt', 'why': c['why']}
        if c.get('maybe'): it['keep'] = 'maybe'
        if r['se']: it['se'] = r['se']; it['ep'] = r['ep']
        if c['age'] >= 0: it['agey'] = round(c['age'], 1)
        put(it)
    chn = collections.Counter(x.get('chid') or x['ch'] for x in out.values() if x.get('se') or x.get('ad'))
    promoted = 0
    for it in out.values():
        m = re.match(r'maybe: up (\d+) years, (\d+) views$', str(it.get('why', '')))
        n = chn[it.get('chid') or it['ch']]
        if it.get('keep') == 'maybe' and m and int(m.group(1)) >= 4 and int(m.group(2)) >= 150 and n >= 5 and (it.get('se') or it.get('ad')):
            it.pop('keep'); it['why'] = 'up %s years, %s views, channel with %d similar uploads' % (m.group(1), m.group(2), n); promoted += 1
    print('promoted by channel history', promoted)
    items = sorted(out.values(), key=lambda x: (x['k'], x.get('se') or [0, 0], x.get('ad') or '', x['vid']))
    seenv = set(); items = [x for x in items if not (x['vid'] in seenv or seenv.add(x['vid']))]
    json.dump(items, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    use = lambda x: bool(x.get('ad')) or bool(x.get('off') and x.get('se'))
    firm = [x for x in items if not x.get('keep')]
    print('candidates', len(cand), 'rejected', dict(rej), 'previous', len(old), 'total', len(items), 'firm', len(firm), 'maybe', len(items) - len(firm), 'dated or official with episode', sum(1 for x in items if use(x)), 'of which firm', sum(1 for x in firm if use(x)), 'hours', round(sum(x['dur'] for x in items) / 3600))
    print('official share', round(100 * sum(1 for x in items if x['off']) / max(1, len(items))), '%')
    print('PER CATEGORY', dict(collections.Counter(x['q'] for x in items)))
    print('PER YEAR', sorted(collections.Counter(x['e'] for x in items).items()))
    ch = collections.Counter(x['ch'] for x in items)
    print('PER CHANNEL (top 60)')
    for c, n in ch.most_common(60): print(' ', str(n).rjust(5), c[:50], 'off' if any(x['off'] for x in items if x['ch'] == c) else '')
    per = collections.defaultdict(lambda: [0, 0, 0, 0])
    for x in items:
        p = per[x['k']]
        p[1 if x.get('keep') else 0] += 1
        if use(x) and not x.get('keep'): p[2] += 1
        if x.get('off'): p[3] += 1
    tmeta = {s['title']: s for s in ALL.values()}
    rows = []
    for title, s in sorted(tmeta.items(), key=lambda kv: (kv[1]['pri'], kv[0].lower())):
        a, b, u, o = per.get(title, [0, 0, 0, 0])
        rows.append({'title': title, 'pri': s['pri'], 'type': s['type'], 'firm': a, 'maybe': b, 'usable': u, 'official': o, 'guide': len((byt.get(title) or {}).get('eps') or []), 'searched': 1 if title in byt else 0})
    print('PER SHOW (pri, show, guide eps, firm, maybe, firm dated or official, flag)')
    for r in rows:
        if r['searched'] or r['firm'] + r['maybe']:
            print(' ', r['pri'], r['title'][:44].ljust(44), str(r['guide']).rjust(5), str(r['firm']).rjust(5), str(r['maybe']).rjust(5), str(r['usable']).rjust(5), ' FOUND' if r['usable'] >= 20 else ' THIN' if r['firm'] + r['maybe'] else ' MISSING')
    pp = {}
    for p in (1, 2, 3):
        R = [r for r in rows if r['pri'] == p]
        pp[str(p)] = {'shows': len(R), 'with_usable': sum(1 for r in R if r['usable']), 'with_20_usable': sum(1 for r in R if r['usable'] >= 20), 'with_any': sum(1 for r in R if r['firm'] + r['maybe']), 'firm': sum(r['firm'] for r in R), 'maybe': sum(r['maybe'] for r in R), 'usable': sum(r['usable'] for r in R)}
    print('PER PRIORITY', pp)
    rep = {'run': RUN, 'date': str(TODAY), 'total': len(items), 'firm': len(firm), 'maybe': len(items) - len(firm), 'usable': sum(1 for x in items if use(x)), 'usable_firm': sum(1 for x in firm if use(x)), 'hours': round(sum(x['dur'] for x in items) / 3600), 'official': sum(1 for x in items if x['off']), 'rejected': dict(rej), 'priority': pp, 'shows': rows}
    json.dump(rep, open(REP, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    random.seed(7)
    print('SAMPLES FIRM')
    for x in random.sample(firm, min(90, len(firm))):
        print(' ', x['i'], '|', x['k'][:26], '|', x.get('se'), '|', x['ad'], '|', x['dur'] // 60, 'min |', x['ch'][:24], '|', 'off' if x['off'] else '', '|', x['t'][:80])
    mb = [x for x in items if x.get('keep')]
    print('SAMPLES MAYBE')
    for x in random.sample(mb, min(60, len(mb))):
        print(' ', x['i'], '|', x['k'][:26], '|', x.get('se'), '|', x['ad'], '|', x['dur'] // 60, 'min |', x['ch'][:24], '|', x['why'][:40], '|', x['t'][:70])


def probe():
    print('== search')
    res = search('night court full episode', 1)
    print('  results', len(res)); [print('  ', c) for c in res[:5]]
    res2 = search('night court full episode', 1, 'EgIQAQ==')
    print('  unfiltered', len(res2)); [print('  ', c) for c in res2[:3]]
    print('== playlists')
    pl = search_playlists('night court full episodes')
    print('  playlists', len(pl)); [print('  ', p) for p in pl[:8]]
    d = inner('search', {'query': 'night court full episodes', 'params': 'EgIQAw=='})
    if d:
        ks = collections.Counter()
        def keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.endswith(('Renderer', 'ViewModel')): ks[k] += 1
                    keys(v)
            elif isinstance(o, list):
                for v in o: keys(v)
        keys(d); print('  keys', dict(ks))
        lv = walk(d, 'lockupViewModel', [])
        if lv: print('  lockup', json.dumps(lv[0])[:1800])
    for p in pl[:3]:
        vs = playlist_videos(p['pid'])
        print('  playlist', p['pid'], len(vs)); [print('    ', c) for c in vs[:3]]
    print('== channel')
    if res and res[0]['chid']:
        vs = channel_videos(res[0]['chid'], res[0]['ch'], 2)
        print('  channel videos', len(vs)); [print('  ', c) for c in vs[:3]]
    print('== oembed')
    for c in res[:3]: print('  ', c['vid'], oembed(c['vid']))
    print('== guide')
    S = load_shows()
    for k in ('night court', 'la law', 'hunter', 'wings'):
        if k in S:
            g = fetch_guide(S[k]); print('  ', k, {x: g.get(x) for x in ('title', 'premiered', 'country', 'miss')}, len(g.get('episodes', [])), guide_ok(g, S[k]))
    print('stat', dict(STAT))


if MODE == 'probe': probe()
elif MODE == 'plan': plan()
elif MODE == 'search': run_search()
elif MODE == 'merge': merge()
