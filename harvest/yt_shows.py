import gzip, json, os, re, sys, time, random, glob, collections, threading, urllib.request, urllib.parse, datetime
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'catalog')
HV = os.path.join(ROOT, 'harvest')
PARTS = os.path.join(ROOT, 'parts')
OUT = os.path.join(CAT, 'yt_shows.json.gz')
MODE = os.environ.get('MODE', 'plan')
SHARD = int(os.environ.get('SHARD', '0'))
SHARDS = int(os.environ.get('SHARDS', '8'))
THREADS = int(os.environ.get('THREADS', '4'))
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
T0 = time.time()
FMODE = os.environ.get('FOCUS', '')
FOCUS = FMODE == '1'
DATED = FMODE == '2'
CHAN = os.environ.get('CHANNELS', '') in ('1', '2')
DEEP = os.environ.get('CHANNELS', '') == '2'
CQ = ['today show', 'today nbc', 'good morning america', 'cbs this morning', 'cbs morning news', 'nightly news', 'world news tonight', 'evening news', 'tonight show', 'letterman', 'conan', 'oprah', 'donahue', 'seinfeld', 'cheers', 'frasier', 'fresh prince', 'friends', 'simpsons', 'wings', 'full episode', 'with commercials']
RUNS = {'Seinfeld': (1989, 1998, 'NBC'), 'Cheers': (1984, 1993, 'NBC'), 'Frasier': (1993, 2004, 'NBC'), 'Wings': (1990, 1997, 'NBC'), 'The Fresh Prince of Bel-Air': (1990, 1996, 'NBC'), 'Friends': (1994, 2004, 'NBC'), 'The Simpsons': (1989, 2004, 'FOX')}
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
DQ = {'Today': ['today show', 'nbc today show', 'nbc today'], 'Good Morning America': ['good morning america', 'abc good morning america'], 'CBS This Morning': ['cbs this morning'], 'CBS Morning News': ['cbs morning news'], 'The Tonight Show Starring Johnny Carson': ['tonight show johnny carson'], 'Late Night with David Letterman': ['late night with david letterman'], 'Late Show with David Letterman': ['late show with david letterman'], 'The Tonight Show with Jay Leno': ['tonight show jay leno'], "Late Night with Conan O'Brien": ['late night with conan o\'brien'], 'Live with Regis and Kathie Lee': ['live with regis and kathie lee'], 'The Oprah Winfrey Show': ['oprah winfrey show'], 'NBC Nightly News': ['nbc nightly news'], 'ABC World News Tonight': ['abc world news tonight'], 'CBS Evening News': ['cbs evening news']}
TOP = ['Seinfeld', 'Cheers', 'Frasier', 'Wings', 'The Fresh Prince of Bel-Air', 'Friends', 'The Simpsons']
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
CTX = {'client': {'clientName': 'WEB', 'clientVersion': '2.20240620.05.00', 'hl': 'en', 'gl': 'US'}}
TODAY = datetime.date.today()
STAT = collections.Counter()
LOCK = threading.Lock()

MUST = ["The Simpsons", "Seinfeld", "Friends", "Cheers", "Home Improvement", "Wings", "Frasier", "Married... with Children", "Roseanne", "The Fresh Prince of Bel-Air", "Full House", "Family Matters", "Saved by the Bell", "Salute Your Shorts", "Are You Afraid of the Dark?", "Clarissa Explains It All", "Hey Dude", "The Adventures of Pete & Pete", "Rugrats", "Doug", "Rocko's Modern Life", "The Ren & Stimpy Show", "He-Man and the Masters of the Universe", "Teenage Mutant Ninja Turtles", "Batman: The Animated Series", "X-Men", "Pokémon", "Mummies Alive!", "The Computer Chronicles", "Net Cafe"]
NEAR = ["MacGyver", "Magnum, P.I.", "ER", "Matlock", "Dawson's Creek", "Melrose Place", "Beverly Hills, 90210", "Who's the Boss?", "A Different World", "Three's Company", "Columbo", "Gunsmoke", "Dynasty", "Touched by an Angel", "The Daily Show", "SportsCenter", "The People's Court", "Step by Step", "Boy Meets World", "The Cosby Show", "Family Ties", "Growing Pains", "The Golden Girls", "Night Court", "ALF", "Mad About You", "NewsRadio", "The Drew Carey Show", "Everybody Loves Raymond", "King of the Hill", "The X-Files", "NYPD Blue", "Law & Order", "Quantum Leap", "Star Trek: The Next Generation", "Buffy the Vampire Slayer", "Twin Peaks", "Northern Exposure", "Murder, She Wrote", "Miami Vice", "Knight Rider", "The A-Team", "Airwolf", "Animaniacs", "Tiny Toon Adventures", "Gargoyles", "DuckTales", "Chip 'n Dale Rescue Rangers", "TaleSpin", "Darkwing Duck", "The Transformers", "G.I. Joe: A Real American Hero", "ThunderCats", "Spider-Man", "Freaks and Geeks", "My So-Called Life", "Mystery Science Theater 3000", "Baywatch", "Walker, Texas Ranger", "Hill Street Blues", "St. Elsewhere", "L.A. Law", "Moonlighting", "Dallas", "Knots Landing", "Designing Women", "Murphy Brown", "Coach", "Empty Nest", "Perfect Strangers", "Blossom", "Martin", "Living Single", "In Living Color", "Kenan & Kel", "All That", "Hangin' with Mr. Cooper", "Sister, Sister", "Moesha", "The Nanny", "Spin City", "Just Shoot Me!", "3rd Rock from the Sun", "Will & Grace", "That '70s Show", "Malcolm in the Middle", "Sabrina the Teenage Witch", "Charmed", "7th Heaven", "Xena: Warrior Princess", "Hercules: The Legendary Journeys", "Highlander", "Sliders", "Star Trek: Deep Space Nine", "Star Trek: Voyager", "Babylon 5", "Unsolved Mysteries", "Rescue 911", "COPS", "America's Most Wanted"]
EXTRA = [
 ("The Tonight Show Starring Johnny Carson", "late", "nbc", 1962, 1992, "date", ["johnny carson", "tonight show carson"]),
 ("Late Night with David Letterman", "late", "nbc", 1982, 1993, "date", ["late night letterman", "letterman late night"]),
 ("Late Show with David Letterman", "late", "cbs", 1993, 2015, "date", ["late show letterman"]),
 ("The Tonight Show with Jay Leno", "late", "nbc", 1992, 2014, "date", ["jay leno tonight show", "tonight show leno"]),
 ("Late Night with Conan O'Brien", "late", "nbc", 1993, 2009, "date", ["conan o'brien late night", "late night conan"]),
 ("The Arsenio Hall Show", "late", "syn", 1989, 1994, "date", ["arsenio hall show"]),
 ("Today", "morning", "nbc", 1952, 2030, "date", ["today show", "nbc today"]),
 ("Good Morning America", "morning", "abc", 1975, 2030, "date", ["good morning america"]),
 ("CBS This Morning", "morning", "cbs", 1987, 1999, "date", ["cbs this morning"]),
 ("CBS Morning News", "morning", "cbs", 1982, 2030, "date", ["cbs morning news"]),
 ("Donahue", "talk", "syn", 1970, 1996, "date", ["donahue", "phil donahue show"]),
 ("The Oprah Winfrey Show", "talk", "syn", 1986, 2011, "date", ["oprah winfrey show", "oprah show"]),
 ("Geraldo", "talk", "syn", 1987, 1998, "date", ["geraldo"]),
 ("Sally Jessy Raphael", "talk", "syn", 1983, 2002, "date", ["sally jessy raphael"]),
 ("The Jenny Jones Show", "talk", "syn", 1991, 2003, "date", ["jenny jones show"]),
 ("Ricki Lake", "talk", "syn", 1993, 2004, "date", ["ricki lake show", "ricki lake"]),
 ("The Jerry Springer Show", "talk", "syn", 1991, 2018, "date", ["jerry springer show", "jerry springer"]),
 ("The Montel Williams Show", "talk", "syn", 1991, 2008, "date", ["montel williams show", "montel williams"]),
 ("Maury", "talk", "syn", 1991, 2022, "date", ["maury povich show", "maury"]),
 ("Live with Regis and Kathie Lee", "talk", "syn", 1988, 2000, "date", ["regis and kathie lee", "live with regis"]),
 ("The Rosie O'Donnell Show", "talk", "syn", 1996, 2002, "date", ["rosie o'donnell show"]),
 ("Days of Our Lives", "soap", "nbc", 1965, 2030, "date", ["days of our lives"]),
 ("Another World", "soap", "nbc", 1964, 1999, "date", ["another world"]),
 ("Santa Barbara", "soap", "nbc", 1984, 1993, "date", ["santa barbara"]),
 ("The Young and the Restless", "soap", "cbs", 1973, 2030, "date", ["young and the restless"]),
 ("As the World Turns", "soap", "cbs", 1956, 2010, "date", ["as the world turns"]),
 ("Guiding Light", "soap", "cbs", 1952, 2009, "date", ["guiding light"]),
 ("General Hospital", "soap", "abc", 1963, 2030, "date", ["general hospital"]),
 ("All My Children", "soap", "abc", 1970, 2011, "date", ["all my children"]),
 ("One Life to Live", "soap", "abc", 1968, 2012, "date", ["one life to live"]),
 ("The Price Is Right", "game", "cbs", 1972, 2030, "date", ["price is right"]),
 ("Wheel of Fortune", "game", "syn", 1975, 2030, "date", ["wheel of fortune"]),
 ("Jeopardy!", "game", "syn", 1984, 2030, "date", ["jeopardy"]),
 ("Family Feud", "game", "syn", 1976, 2030, "date", ["family feud"]),
 ("Judge Judy", "talk", "syn", 1996, 2021, "date", ["judge judy"]),
 ("Divorce Court", "talk", "syn", 1984, 1993, "date", ["divorce court"]),
 ("Emeril Live", "cook", "cab", 1997, 2007, "ep", ["emeril live"]),
 ("Good Eats", "cook", "cab", 1999, 2012, "ep", ["good eats"]),
 ("The Frugal Gourmet", "cook", "pbs", 1983, 1997, "ep", ["frugal gourmet"]),
 ("Yan Can Cook", "cook", "pbs", 1982, 2030, "ep", ["yan can cook"]),
 ("Iron Chef", "cook", "cab", 1999, 2004, "ep", ["iron chef"]),
 ("The Weather Channel", "weather", "cab", 1982, 2030, "date", ["weather channel", "local forecast", "weatherstar", "local on the 8s"]),
 ("QVC", "block", "cab", 1986, 2030, "date", ["qvc"]),
 ("Home Shopping Network", "block", "cab", 1985, 2030, "date", ["home shopping network", "home shopping club", "hsn"]),
 ("Video Soul", "music", "cab", 1981, 1996, "date", ["video soul"]),
 ("Soul Train", "music", "syn", 1971, 2006, "ep", ["soul train"]),
 ("Showtime at the Apollo", "music", "syn", 1987, 2008, "ep", ["showtime at the apollo", "it's showtime at the apollo"]),
 ("ComicView", "late", "cab", 1992, 2008, "ep", ["comicview", "comic view"]),
 ("Rap City", "music", "cab", 1989, 2008, "date", ["rap city"]),
 ("Nashville Now", "music", "cab", 1983, 1993, "date", ["nashville now"]),
 ("Hee Haw", "music", "syn", 1969, 1993, "ep", ["hee haw"]),
 ("Grand Ole Opry Live", "music", "cab", 1985, 2030, "date", ["grand ole opry live", "opry live"]),
 ("Bits and Bytes", "tech", "pbs", 1983, 1984, "ep", ["bits and bytes"]),
 ("The Screen Savers", "tech", "cab", 1998, 2005, "date", ["screen savers"]),
 ("Call for Help", "tech", "cab", 1998, 2004, "date", ["call for help"]),
 ("Beyond 2000", "pub", "cab", 1985, 1999, "ep", ["beyond 2000"]),
 ("The Joy of Painting", "pub", "pbs", 1983, 1994, "ep", ["joy of painting", "bob ross"]),
 ("This Old House", "pub", "pbs", 1979, 2030, "ep", ["this old house"]),
 ("NOVA", "pub", "pbs", 1974, 2030, "ep", ["nova pbs", "pbs nova"]),
 ("Frontline", "pub", "pbs", 1983, 2030, "ep", ["frontline pbs", "pbs frontline"]),
 ("Nature", "pub", "pbs", 1982, 2030, "ep", ["pbs nature"]),
 ("Biography", "pub", "cab", 1987, 2030, "ep", ["a&e biography", "biography a&e"]),
 ("Modern Marvels", "pub", "cab", 1993, 2030, "ep", ["modern marvels"]),
 ("Local News", "news", "", 1984, 2004, "date", ["eyewitness news", "action news", "newscast", "news at 11", "news at 10", "news at 6", "newscenter", "channel 2 news", "channel 4 news", "channel 5 news", "channel 7 news"]),
 ("NBC Nightly News", "news", "nbc", 1970, 2030, "date", ["nbc nightly news"]),
 ("ABC World News Tonight", "news", "abc", 1978, 2030, "date", ["world news tonight"]),
 ("CBS Evening News", "news", "cbs", 1962, 2030, "date", ["cbs evening news"]),
]
BADT = re.compile(r"(?i)\b(reaction|reacts?|review|recap|clips?|scenes?|best of|moments|compilation|trailer|promo|promos|opening|intro|theme song|bloopers|behind the scenes|interview|explained|top \d+|ranking|ranked|podcast|commentary|tribute|parody|edit|amv|mashup|remix|deleted|ending|outro|credits|teaser|preview|every time|supercut|funniest|highlights|montage|unboxing|gameplay|longplay|walkthrough|speedrun|cover|lyrics|karaoke|shorts?|tiktok|meme|fan ?made|restored in 4k|60 ?fps|upscale[d]?|ai |sub español|subtitulado|latino|dublado|legendado|español|castellano|deutsch|fran[cç]ais|italiano|hindi|tagalog|vostfr|ger sub|napisy|türkçe|عربي|partial|rus eng|eng rus|x264|x265|ac3|learn english|talk \|\||watch ?along|first time watching|breakdown|analysis|retrospective|rewatch)\b")
BADCH = re.compile(r"(?i)^classic loveline$|speedrun")
FORX = re.compile(r"(?i)\b(bbc ?[1-4]|bbc one|bbc two|bbc news|itv ?[1-4]?|sky news|tvnz|nine network|seven network|network ten|channel 4 uk|cbbc|citv)\b")
DATEX = re.compile(r"(?i)\b(cardiology|vsu|australian today|today (show )?australia|gmtv|canada am|(?<!with )(?<!w )(?<!w/)(?<!w/ )(?<!original )(?<!some )commercials? (from|aired|during|block)|^commercials)\b")
PARTX = re.compile(r"(?i)\b(part|pt\.?)\s*([1-9]|one|two|three)\s*(of|/)\s*\d|\[\s*\d\s*/\s*\d\s*\]|\(\s*\d\s*/\s*\d\s*\)")
LATEY = re.compile(r'\b(200[5-9]|20[12]\d)\b|\b\d{1,2}[./]\d{1,2}[./](0[5-9]|[12]\d)\b')
OFFX = re.compile(r"(?i)(official|studios?|television|entertainment|network|pictures|classics|vault|archive|archives|museum|library|university|pbs|nbc|cbs|abc|fox|warner|paramount|sony|universal|disney|mgm|lionsgate|shout|filmrise|hasbro|mattel|wildbrain|nelvana|dhx|9 story|cookie jar|nickelodeon|cartoon network|a&e|history|discovery|c-span|associated press|ap archive)")
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def nz(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r"[’'`]", '', s)
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', s)).strip()


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


def inner(ep, body, tries=4):
    b = dict(body); b['context'] = CTX
    st, raw = http('https://www.youtube.com/youtubei/v1/' + ep + '?prettyPrint=false', json.dumps(b).encode(), {'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com', 'X-YouTube-Client-Name': '1', 'X-YouTube-Client-Version': CTX['client']['clientVersion']}, tries)
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
    return {'vid': vid, 't': txt(v.get('title')), 'ch': txt(ow), 'chid': chid, 'dur': secs(txt(v.get('lengthText'))), 'views': views(txt(v.get('viewCountText'))), 'age': age_years(txt(v.get('publishedTimeText'))), 'ver': 1 if 'VERIFIED' in badges.upper() else 0, 'live': 1 if live else 0}


def strs(o, out):
    if isinstance(o, dict):
        for v in o.values(): strs(v, out)
    elif isinstance(o, list):
        for v in o: strs(v, out)
    elif isinstance(o, str): out.append(o)
    return out


def lk_to(v, chid, ch):
    vid = v.get('contentId')
    if not vid or v.get('contentType') not in (None, 'LOCKUP_CONTENT_TYPE_VIDEO'): return None
    md = (v.get('metadata') or {}).get('lockupMetadataViewModel') or {}
    ss = strs(v, [])
    dur = 0; vw = 0; age = -1
    for x in ss:
        if not dur and re.match(r'^\d{1,2}(:\d\d){1,2}$', x): dur = secs(x)
        if not vw and re.match(r'^[\d,.]+[KMB]? views?$', x): vw = views(x)
        if age < 0 and re.search(r'\d+ (year|month|week|day|hour|minute)s? ago', x): age = age_years(x)
    return {'vid': vid, 't': txt((md.get('title') or {}).get('content') or ''), 'ch': ch, 'chid': chid, 'dur': dur, 'views': vw, 'age': age, 'ver': 0, 'live': 1 if 'LIVE' in ss else 0}


def channel_search(chid, ch, q, pages=3):
    out = []; seen = set()
    d = inner('browse', {'browseId': chid, 'params': 'EgZzZWFyY2jyBgQKAloA', 'query': q})
    for _ in range(pages):
        if not d: break
        got = 0
        for v in walk(d, 'videoRenderer', []):
            x = vr_to(v)
            if x and x['vid'] not in seen:
                x['ch'] = x['ch'] or ch; x['chid'] = x['chid'] or chid
                seen.add(x['vid']); out.append(x); got += 1
        for v in walk(d, 'lockupViewModel', []):
            x = lk_to(v, chid, ch)
            if x and x['vid'] not in seen: seen.add(x['vid']); out.append(x); got += 1
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or not got or left() < 120: break
        time.sleep(0.3 + random.random() * 0.5)
        d = inner('browse', {'continuation': tk[-1]})
    return out


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


def channel_flat(chid, ch, limit=3000, cap=300):
    box = []
    def work():
        out = []
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'playlistend': limit, 'socket_timeout': 20, 'retries': 2, 'extractor_retries': 1}) as y:
                r = y.extract_info('https://www.youtube.com/channel/' + chid + '/videos', download=False)
            for e in (r or {}).get('entries') or []:
                if not e or not e.get('id'): continue
                out.append({'vid': e['id'], 't': e.get('title') or '', 'ch': ch or (r.get('channel') or ''), 'chid': chid, 'dur': int(e.get('duration') or 0), 'views': int(e.get('view_count') or 0), 'age': -1, 'ver': 1 if r.get('channel_is_verified') else 0, 'live': 1 if e.get('live_status') in ('is_live', 'is_upcoming') else 0})
        except Exception as ex:
            with LOCK: STAT['flatfail'] += 1
        box.append(out)
    th = threading.Thread(target=work, daemon=True)
    th.start(); th.join(cap)
    if not box:
        with LOCK: STAT['flatslow'] += 1
        return []
    return box[0]


def channel_videos(chid, ch, maxpages=40, limit=3000, cap=300):
    out = channel_flat(chid, ch, limit, cap)
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
        for v in walk(d, 'lockupViewModel', []):
            x = lk_to(v, chid, ch)
            if x: x['ver'] = ver; out.append(x); got += 1
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or not got or left() < 120: break
        time.sleep(0.3 + random.random() * 0.5)
        d = inner('browse', {'continuation': tk[-1]})
    return out


def oembed(vid):
    st, raw = http('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + vid, safe=''), tries=3, timeout=15)
    return st


def player(vid):
    if STAT['inner_player_403'] > 40 and STAT['inner_player_403'] > STAT['inner_player_200']: return {}
    d = inner('player', {'videoId': vid}, 1)
    if not d: return {}
    ps = d.get('playabilityStatus') or {}
    vd = d.get('videoDetails') or {}
    mf = (d.get('microformat') or {}).get('playerMicroformatRenderer') or {}
    r = {'status': ps.get('status', ''), 'emb': ps.get('playableInEmbed'), 'reason': (ps.get('reason') or '')[:60]}
    if vd:
        r['dur'] = int(vd.get('lengthSeconds') or 0); r['views'] = int(vd.get('viewCount') or 0); r['livec'] = 1 if vd.get('isLiveContent') else 0
        r['desc'] = (vd.get('shortDescription') or '')[:600]
    if mf:
        r['up'] = (mf.get('uploadDate') or mf.get('publishDate') or '')[:10]
        ac = mf.get('availableCountries')
        if ac is not None: r['us'] = 1 if 'US' in ac else 0
        r['safe'] = mf.get('isFamilySafe')
    return r


def load_shows():
    S = {}
    def add(title, q, net, y0, y1, kind, al, rank, tier):
        k = nzk(title)
        if not k: return
        if k in S:
            S[k]['al'] |= set(nz(a) for a in al if a)
            if tier < S[k]['tier']: S[k]['tier'] = tier
            if rank < S[k]['rank']: S[k]['rank'] = rank
            return
        S[k] = {'title': title, 'k': k, 'q': q or 'prime', 'net': net or '', 'y0': y0 or 0, 'y1': y1 or 0, 'kind': kind or '', 'al': set([nz(title)] + [nz(a) for a in al if a]), 'rank': rank, 'tier': tier}
    def yrs(x):
        y0 = x.get('first') or x.get('first_year') or (x.get('years') or [0, 0])[0]
        y1 = x.get('last') or x.get('last_year') or (x.get('years') or [0, 0])[-1]
        for f in ('run', 'original_run', 'or'):
            m = re.match(r'(\d{4})\D*(\d{4})?', str(x.get(f) or ''))
            if m and not y0: y0 = int(m.group(1)); y1 = int(m.group(2) or 2004)
        return int(y0 or 0), int(y1 or 0)
    for fn in ('shows_top', 'shows_primetime', 'shows_drama', 'shows_cult', 'shows_nick', 'shows_gaps', 'shows_docs', 'shows_toons3', 'shows_cable'):
        p = os.path.join(HV, fn + '.json')
        if not os.path.exists(p): continue
        try: L = json.load(open(p))
        except Exception: continue
        if isinstance(L, dict): L = list(L.values())
        for i, x in enumerate(L):
            if not isinstance(x, dict) or not x.get('title'): continue
            y0, y1 = yrs(x)
            al = []
            for f in ('alt', 'q', 's', 'aliases'):
                v = x.get(f)
                if isinstance(v, list): al += [a for a in v if isinstance(a, str)]
            q = x.get('q') if isinstance(x.get('q'), str) else ('game' if x.get('kind') == 'game' else 'prime')
            kind = x.get('kind') or ('drama' if fn == 'shows_drama' else '')
            rank = x.get('rank') or (1000 + i if fn != 'shows_top' else i + 1)
            add(x['title'], q, x.get('net'), y0, y1, kind, al, rank, 3 if x.get('must') else 4)
    for i, t in enumerate(MUST): add(t, None, None, 0, 0, '', [], i, 1)
    for i, t in enumerate(NEAR): add(t, None, None, 0, 0, '', [], 100 + i, 2)
    for i, (t, q, net, y0, y1, kind, al) in enumerate(EXTRA):
        add(t, q, net, y0, y1, kind, al, 300 + i, 2)
        S[nzk(t)]['q'] = q; S[nzk(t)]['kind'] = kind
    S[nzk('Today')]['al'] -= {'today'}
    S[nzk('Today')]['al'] |= {'today show', 'nbc today', 'today on nbc', 'the today show', 'today nbc', 'nbc news today'}
    S[nzk('Good Morning America')]['al'].discard('gma')
    S[nzk('CBS This Morning')]['al'].discard('cbs morning news')
    S[nzk('The Simpsons')]['smax'] = 15
    S[nzk('Pokémon')]['smax'] = 7
    S[nzk('Pokémon')]['al'] |= {'pokemon'}
    S[nzk('X-Men')]['al'] |= {'x men the animated series', 'x men animated series'}
    S[nzk('X-Men')]['al'].discard('x men')
    S[nzk('The Computer Chronicles')]['al'] |= {'computer chronicles'}
    S[nzk('He-Man and the Masters of the Universe')]['al'] |= {'he man', 'he man official'}
    S[nzk('Teenage Mutant Ninja Turtles')]['al'] |= {'tmnt 1987', 'teenage mutant ninja turtles 1987'}
    for k in ('er', 'doug', 'friends', 'wings', 'cheers', 'coach', 'martin', 'dallas', 'dynasty', 'today', 'nature', 'biography', 'maury', 'geraldo', 'donahue', 'columbo', 'matlock', 'roseanne', 'frasier', 'seinfeld', 'rugrats', 'charmed', 'sliders', 'highlander', 'blossom', 'nova', 'frontline', 'gunsmoke', 'airwolf', 'alf', 'cops', 'qvc', 'gargoyles', 'animaniacs', 'ducktales', 'talespin', 'thundercats', 'macgyver', 'moonlighting', 'baywatch', 'moesha', 'jeopardy', 'family matters', 'full house', 'home improvement', 'step by step'):
        if k in S: S[k]['amb'] = 1
    return S


def load_guides(S):
    G = {}
    for fn in ('epguide.json.gz', 'nick_guide.json.gz', 'eptitle_guide.json.gz'):
        p = os.path.join(CAT, fn)
        if not os.path.exists(p): continue
        try: d = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(d, dict): continue
        for key, v in d.items():
            if not isinstance(v, dict): continue
            eps = v.get('episodes') or v.get('eps') or []
            k = nzk(v.get('title') or key)
            if k in S and eps and len(eps) > len(G.get(k, [])):
                G[k] = [e for e in eps if isinstance(e, list) and len(e) >= 4]
    return G


def coverage(S):
    cov = collections.Counter(); se = collections.defaultdict(set)
    al = sorted(((a, k) for k, s in S.items() for a in s['al'] if len(a) >= 4), key=lambda x: -len(x[0]))
    idx = collections.defaultdict(list)
    for a, k in al: idx[a.split(' ')[0]].append((a, k))
    for p in sorted(glob.glob(os.path.join(CAT, '*.json.gz'))):
        b = os.path.basename(p)
        if b.startswith(('yt_', 'dates', 'epguide', 'adsdates', 'ads', 'filler', 'movies', 'nick_guide', 'eptitle_guide', 'sportsched', 'openarch', 'sports', 'dated', 'wrestling', 'musictv')): continue
        try: L = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if not isinstance(L, list): continue
        for x in L:
            if not isinstance(x, dict): continue
            k = nzk(str(x.get('k') or ''))
            if k not in S:
                t = nz(str(x.get('t') or '')); t2 = re.sub(r'^the ', '', t); k = None
                for a, kk in idx.get(t2.split(' ')[0] if t2 else '', []) + idx.get('the', []):
                    if t.startswith(a + ' ') or t == a or t2.startswith(a + ' '): k = kk; break
                if not k: continue
            fs = x.get('f') or []
            n = sum(1 for f in fs if isinstance(f, list) and len(f) > 1 and f[1] >= 600) or 1
            cov[k] += n
            for f in fs:
                m = re.search(r'(?i)s(\d{1,2})\s*[ ._-]?\s*e(\d{1,3})|(\d{1,2})x(\d{2})\b|season\s*(\d+)\D{1,12}episode\s*(\d+)', str(f[0]) if isinstance(f, list) else '')
                if m:
                    g = [int(v) for v in m.groups() if v]
                    se[k].add((g[0], g[1]))
            sv = x.get('se')
            if isinstance(sv, list) and len(sv) == 2 and all(isinstance(v, int) for v in sv): se[k].add((sv[0], sv[1]))
            elif isinstance(sv, dict):
                for v in sv.values():
                    if isinstance(v, list) and len(v) >= 2: se[k].add((v[0], v[1]))
    return cov, se


def plan():
    S = load_shows(); G = load_guides(S); cov, se = coverage(S)
    tasks = []
    fk = {nzk(x): (0 if x in TOP else 1) for x in MUST + TOP}
    for k, s in S.items():
        if FOCUS and k not in fk: continue
        if DATED and not (s['kind'] == 'date' or s['title'] in RUNS): continue
        eps = G.get(k, [])
        if s.get('smax'): eps = [e for e in eps if e[0] <= s['smax']]
        eps = [e for e in eps if e[0] and str(e[2])[:4] <= '2004' and (not e[2] or str(e[2])[:4] >= '1960')]
        have = cov.get(k, 0); need = len(eps) or (150 if s['tier'] <= 2 else 40)
        ratio = min(1.0, have / max(1, need))
        dk = s['kind'] == 'date' or DATED
        if s['tier'] >= 3 and ratio >= 0.6 and not dk: continue
        if s['tier'] >= 4 and s['rank'] > 1400 and ratio >= 0.25: continue
        miss = [e for e in eps if (e[0], e[1]) not in se.get(k, set())] if eps else []
        if eps and not miss and s['tier'] > 1 and not dk: continue
        if eps and len(se.get(k, ())) < 5 and have >= len(eps) * 0.8 and s['tier'] > 1 and not dk: continue
        t = s['title']; qs = [t + ' full episode', t + ' full episodes', t + ' season 1 episode 1', t + ' complete episode ' + (str(s['y0']) if s['y0'] else '')]
        if s['kind'] == 'date':
            ys = range(max(1984, s['y0'] or 1984), min(2004, s['y1'] or 2004) + 1)
            qs = [t + ' ' + str(y) + ' full' for y in ys] + [t + ' full episode ' + str(y) for y in list(ys)[::3]]
            if s['q'] in ('news', 'morning', 'weather', 'block'): qs += [a + ' ' + str(y) for a in list(s['al'])[:6] for y in ys]
        elif s['tier'] <= 2 and eps:
            seas = sorted(set(e[0] for e in eps))
            qs += [t + ' season ' + str(n) + ' full episode' for n in seas] + [t + ' s%02d' % n for n in seas]
        epq = []
        if s['tier'] <= 2 and s['kind'] != 'date':
            for e in miss[:700]:
                et = nz(str(e[3]))
                if len(et) >= 6 and not re.match(r'^(episode|part|pilot|show|chapter)\b', et): epq.append(t + ' ' + str(e[3]))
        pri = s['tier']
        if FOCUS:
            pri = fk[k]; qs = [t + ' full episode', t + ' full episodes'] + [t + ' season ' + str(n) + ' full episode' for n in sorted(set(e[0] for e in eps))]; epq = []
            for e in miss[:900]:
                epq += [t + ' s%02de%02d' % (e[0], e[1]), t + ' season %d episode %d' % (e[0], e[1])]
                et = nz(str(e[3]))
                if len(et) >= 5 and not re.match(r'^(episode|part|pilot|show|chapter)\b', et): epq.append(t + ' ' + str(e[3]) + ' full episode')
        if DATED:
            epq = []
            if t in RUNS:
                y0, y1, nw = RUNS[t]; pri = 0
                qs = [t + ' with commercials', t + ' original broadcast', t + ' ' + nw + ' original airing']
                for y in range(y0, y1 + 1):
                    qs += [t + ' %d with commercials' % y, t + ' %d original broadcast' % y, t + ' ' + nw + ' %d full episode' % y]
                    epq += [t + ' ' + mo + ' %d' % y for mo in MONTHS]
            else:
                ys = range(max(1984, s['y0'] or 1984), min(2004, s['y1'] or 2004) + 1)
                pri = 0 if s['q'] == 'morning' else 1 if t in DQ else 2
                if t in DQ:
                    qs = [a + ' %d' % y for a in DQ[t] for y in ys] + [a + ' %d full' % y for a in DQ[t][:1] for y in ys]
                    epq = [a + ' ' + mo + ' %d' % y for a in DQ[t] for y in ys for mo in MONTHS]
        tasks.append({'must': 1 if k in fk else 0, 'pri': pri, 'foc': 1 if FOCUS or (DATED and t in RUNS) else 0, 'k': k, 'title': t, 'q': s['q'], 'net': s['net'], 'y0': s['y0'], 'y1': s['y1'], 'kind': s['kind'], 'al': sorted(s['al']), 'amb': s.get('amb', 0), 'tier': s['tier'], 'rank': s['rank'], 'have': have, 'need': need, 'eps': eps, 'cov': sorted(se.get(k, set())), 'qs': [q.strip() for q in qs], 'epq': epq})
    tasks.sort(key=lambda t: (t['pri'], t['tier'], t['rank']))
    os.makedirs(PARTS, exist_ok=True)
    json.dump(tasks, gzip.open(os.path.join(PARTS, 'yt_plan.json.gz'), 'wt', encoding='utf-8'))
    print('shows in lists', len(S), 'guides', len(G), 'tasks', len(tasks), 'queries', sum(len(t['qs']) + len(t['epq']) for t in tasks))
    print('NEED LIST (tier, show, have files, guide episodes, covered se, queries)')
    for t in tasks[:260]:
        print(' ', t['tier'], t['title'][:44].ljust(44), str(t['have']).rjust(5), str(len(t['eps'])).rjust(5), str(len(t['cov'])).rjust(5), str(len(t['qs']) + len(t['epq'])).rjust(5))


def pdate(s):
    s = s.lower()
    m = re.search(r'\b(19[5-9]\d|200\d)[-./ ](\d{1,2})[-./ ](\d{1,2})\b', s)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./]((?:19)?[5-9]\d|200\d|0[0-4])\b', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = m.group(3); y = y if len(y) == 4 else ('19' + y if y[0] in '56789' else '20' + y)
        return '%s-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[5-9]\d|200\d)\b', s)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1)], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(19[5-9]\d|200\d)\b', s)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(2)], int(m.group(1)))
    m = re.search(r'air ?date:?\s+(\d{1,2}) (\d{1,2}) ([5-9]\d|0[0-4])\b', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31: return '%s-%02d-%02d' % (('19' if m.group(3)[0] in '56789' else '20') + m.group(3), int(m.group(1)), int(m.group(2)))
    return ''


def durok(t, d):
    q, kind = t['q'], t['kind']
    if q in ('kids',): return 600 <= d <= 1900 or 2300 <= d <= 3000
    if q in ('late',): return 2100 <= d <= 6600
    if q in ('talk', 'soap', 'game', 'cook', 'tech'): return 1080 <= d <= 3900
    if q in ('morning', 'news', 'weather', 'block'): return 600 <= d <= 4 * 3600
    if q in ('music',): return 1200 <= d <= 7200
    if q in ('pub',): return 1300 <= d <= 7500
    if kind in ('sitcom',): return 1140 <= d <= 1900 or 2500 <= d <= 3300
    if kind in ('drama',): return 2280 <= d <= 3720 or 5000 <= d <= 6200
    return 1140 <= d <= 1900 or 2280 <= d <= 3720


def bytitle(eps, n, hit):
    rest = (' ' + n + ' ').replace(' ' + hit + ' ', ' ', 1)
    best = None
    for et, e in eps['ti']:
        if ((' ' + rest + ' ').find(' ' + et + ' ') >= 0 or (' ' + n + ' ').find(' ' + et + ' ') >= 0) and (not best or len(et) > len(best[0])): best = (et, e)
    return best[1] if best else None


def match(t, c, M):
    T = c['t']; n = nz(T)
    if c['live'] or c['dur'] < 500: return None
    if BADT.search(T) or PARTX.search(T): return None
    if BADCH.search(c.get('ch') or '') or FORX.search(T): return None
    if re.search(r'[^\x00-\x7f]', re.sub(r'[’‘“”–—…é·•|®™]', '', T)): return None
    hit = None
    for a in sorted(t['al'], key=lambda a: -len(a)):
        if len(a) < 2: continue
        if (' ' + n + ' ').find(' ' + a + ' ') >= 0: hit = a; break
    if not hit: return None
    if LATEY.search(T) and not re.search(r'\b(19[5-9]\d|200[0-4])\b', T): return None
    if ' ' not in hit and len(hit) <= 11:
        n2 = re.sub(r'^the ', '', n)
        if not (n2.startswith(hit + ' ') or n2 == hit or re.search(r'(^| )' + re.escape(hit) + r' (s ?\d|season|series \d|episode|ep \d|\d{1,3}x\d|\d)', n) or re.search(r'[:|\-] *' + re.escape(hit) + r'\b', T.lower())): return None
    if not durok(t, c['dur']): return None
    r = {'se': None, 'ep': '', 'ad': '', 'e': 0}
    if t.get('must') and t['q'] != 'kids':
        if 2400 <= c['dur'] <= 3300: r['m'] = 'double length'
        elif not 1080 <= c['dur'] <= 1900: return None
    m = re.search(r'(?i)\bs(?:eason)?\s*(\d{1,2})\s*[,:._|(-]?\s*\(?e(?:p(?:isode)?)?\s*\.?\s*(\d{1,3})\b|\b(\d{1,2})x(\d{2})\b', T)
    eps = M.get(t['k'])
    if m and eps is not None:
        g = [int(v) for v in m.groups() if v]
        e = eps['se'].get((g[0], g[1]))
        if e and len(nz(str(e[3]))) >= 4 and (' ' + n + ' ').find(' ' + nz(str(e[3])) + ' ') < 0:
            b = bytitle(eps, n, hit)
            if b: e = b
        if e: r['se'] = [e[0], e[1]]; r['ep'] = e[3]; r['ad'] = str(e[2] or '')
        elif eps['se']: return None
        else: r['se'] = g[:2]
    elif eps is not None and eps['ti']:
        e = bytitle(eps, n, hit)
        if e: r['se'] = [e[0], e[1]]; r['ep'] = e[3]; r['ad'] = str(e[2] or '')
    if not r['ad'] and t['kind'] != 'date':
        d0 = pdate(T)
        if d0 and '1960-01-01' <= d0 <= '2004-12-31':
            r['ad'] = d0
            e = eps['ad'].get(d0) if eps is not None and not r['se'] else None
            if e: r['se'] = [e[0], e[1]]; r['ep'] = e[3]
        elif d0 and d0 > '2004-12-31': return None
    if t['kind'] == 'date':
        if DATEX.search(T): return None
        d = pdate(T)
        if not d or not ('1984-01-01' <= d <= '2004-12-31'): return None
        r['ad'] = d
    elif not r['se']:
        dok = bool(r['ad'] and eps is not None and eps['ad'] and min(eps['ad']) <= r['ad'])
        hard = t['amb'] or eps is not None and eps['se'] and t['tier'] <= 2
        if not t.get('foc') and not dok and hard: return None
        if (t.get('foc') or dok and hard) and eps is not None and eps['se']: r['m'] = 'episode not identified'
        if (t.get('amb') or t['title'] in RUNS) and t.get('must') and not r['ad'] and not (c.get('ver') or c.get('off')) and not re.search(r'(?i)with (original )?(commercials|ads)|original (broadcast|airing)|\b(nbc|abc|cbs|fox|nick|nickelodeon|pbs)\b.*\b(19[89]\d|200[0-4])\b|\b(19[89]\d|200[0-4])\b.*\b(nbc|abc|cbs|fox|nick|nickelodeon|pbs)\b', T): return None
        if not re.search(r'(?i)full episode|complete episode|\bepisode\s*\d+|\bep\.?\s*\d+|\b(19[89]\d|200[0-4])\b', T): return None
    if t['amb'] and not r['se'] and t['kind'] != 'date' and not t.get('foc') and not r.get('m'): return None
    y = r['ad'][:4] if r['ad'] else ''
    if not y:
        m2 = re.search(r'\b(19[89]\d|200[0-4])\b', T)
        y = m2.group(1) if m2 else ''
    if y and not ('1984' <= y <= '2004') and not (r['ad'] and y < '1984'): return None
    r['e'] = int(y) if y else (t['y0'] if 1984 <= (t['y0'] or 0) <= 2004 else 0)
    tg = tight(t, T, r['ep'], c.get('ch') or '', 1 if c.get('ver') or c.get('off') or OFFX.search(c.get('ch') or '') else 0)
    if tg == 'junk': return None
    if tg == 'maybe' and not r.get('m'): r['m'] = 'title has extra words'
    return r


STOPW = set('full episode episodes season series complete entire hd hq tv show the a an and of in on at to with from by for original broadcast uncut unedited commercials commercial classic classics sitcom cartoon cartoons animated animation vhs dvd rip part pt finale premiere pilot nbc abc cbs fox pbs upn wb nick nickelodeon nickelodeons disney disneys espn espns usa tnt tbs syndicated syndication rerun reruns english eng dub dubbed version remastered 1080p 720p 480p 4k s e ep vol volume disc tape aired air date airdate year all new retro vintage rare 80s 90s 1980s 1990s lifetime lifetimes hgtv cnn bbc mtv vh1 hbo discovery channel tlc cable network presents'.split())
NEXTW = set('season series episode episodes ep full complete tv show the pilot s e vol volume part classic uncut original hd with cartoon sitcom nbc abc cbs fox vhs dvd hawaii'.split())
MONW = set('january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday'.split())
JUNKT = re.compile(r"(?i)\b(web ?series|speedrun\w*|any ?%|(?<!with )(?<!w )(?<!w/)(?<!w/ )(?<!original )(?<!some )(?<!nbc )(?<!abc )(?<!cbs )(?<!fox )commercials? (aired|during|block|breaks? compilation)|bumpers|icons unearthed|mystery dungeon|studio tour|search for reptar|gmod|minecraft|roblox|fortnite|playstation|nintendo|game ?boy|n64|gamecube|dreamcast|pc game|video ?game|first time (watching|reaction|seeing|viewing)|for the first time|we watch(ed)?|re-?watch(ed|ing)?|revisited|ruminations|rundown|after ?show|afterbuzz|play ?through|let'?s play|the game|hit (and|&) run|script reading|table read|discuss(es|ed|ing|ion)?|analy[sz](ing|ed|is)|facts about|weird facts|radio|un episodio|joined by|check out|grades|watch ?along|my thoughts|breakdown|deep dive|drinking game|ft\.|feat\.|(?<!no )commercial breaks|road rage|tapped out|nes|snes|ps[1-5]|xbox|arcade|play it through|let'?s watch|live ?stream|sermon|school project|stage production|decoded|reviews|then and now|ranking every|every episode|iceberg|theory|theories)\b")
JUNKM = re.compile(r"(?i)\b((?<!with )(?<!w/ )(?<!w )(?<!original )(?<!and )commercials|facts|secrets|cast update|then (and|&|vs\.?) now|where are they now|still alive|tournament|watch(es|ing) every|watches|inside looks?|notes about nothing|featurette|making of|beginner|guide|reboot|revival|reunion|reunite[sd]?|sandbox|ep(isode)?\.? ?\d+ ?[:\-] ?(the )?(seinfeld|cheers|frasier|friends|wings|simpsons|rugrats|roseanne|doug)\b)\b")
JUNKC = re.compile(r"(?i)(react|podcast|gaming|commentary|rewatch|reviews?\b|plays\b|after ?show)")


def tight(t, T, ept, ch, off):
    if t['kind'] == 'date': return ''
    if JUNKT.search(T) or JUNKC.search(ch or ''): return 'junk'
    strict = t.get('must') and (t.get('amb') or t['title'] in RUNS)
    if strict:
        jm = JUNKM.search(T)
        if jm and not set(nz(jm.group(0)).split()) & set(nz(ept or '').split()): return 'junk'
    n = ' ' + nz(T) + ' '; hit = ''
    for a in sorted(t['al'], key=lambda a: (0 if strict and t['k'] in a else 1, -len(a))):
        if len(a) >= 2 and n.find(' ' + a + ' ') >= 0: hit = a; break
    if not hit: return ''
    i = n.find(' ' + hit + ' '); ew = set(nz(ept or '').split())
    pre = re.sub(r'\b(s ?\d{1,2} ?e ?\d{1,3}|season \d{1,2}|series \d{1,2}|episode \d{1,3}|ep \d{1,3}|\d{1,2}x\d{2,3}|s\d{1,2}|e\d{1,3})\b', ' ', n[:i])
    pre = [w for w in pre.split() if w not in STOPW and w not in ew and not w.isdigit()]
    post = n[i + len(hit) + 1:].split()
    short = len(hit.split()) <= 2 or t.get('amb')
    raw = re.sub(r"[’'`]", '', T.lower().replace('&', ' and '))
    m = re.search(r'[^a-z0-9]+'.join(re.escape(w) for w in hit.split()), raw)
    b4 = raw[:m.start()].rstrip()[-1:] if m else ''; af = raw[m.end():].lstrip()[:1] if m else ''
    one = len(nzk(hit).split()) == 1 or t.get('amb')
    if not off and not t.get('amb') and nzk(ch or '') and nzk(ch or '') in (t['k'], nzk(hit)): off = 1
    if strict and ept:
        sig = set(w for w in ew if len(w) >= 3 and w not in STOPW)
        ws = [w for w in re.sub(r'\b(s ?\d{1,2} ?e ?\d{1,3}|season \d{1,2}|series \d{1,2}|episode \d{1,3}|ep \d{1,3}|\d{1,2}x\d{2,3}|s\d{1,2}|e\d{1,3})\b', ' ', n.replace(' ' + hit + ' ', ' ', 1)).split() if w not in STOPW and not w.isdigit()]
        if sig and not (sig & set(ws)) and len(ws) >= 2: return 'junk'
    if pre:
        if strict and not off: return 'junk'
        if short and not (b4 and b4 in '|-:•–"(['): return 'junk'
        if one and t.get('amb') and not off: return 'junk'
        if not off and (short or len(pre) >= 3): return 'maybe'
    if t.get('amb') and not off and i > 0 and nzk(n.strip()).find(nzk(hit)) != 0: return 'maybe'
    if one and post:
        w = post[0]
        if not (w in NEXTW or w in MONW or w in ew or w.isdigit() or re.match(r'^(s\d{1,2}(e\d{1,3})?|e\d{1,3}|\d{1,2}x\d{2,3}|19\d\d|200\d)$', w) or (af and af in ('|-:•–("[#/' if t.get('amb') else '|-:•–("[#/,.'))): return 'junk'
    return ''


def build_M(tasks):
    M = {}
    for t in tasks:
        eps = t['eps']
        if not eps: M[t['k']] = None if t['kind'] == 'date' else {'se': {}, 'ti': [], 'ad': {}}; continue
        cnt = collections.Counter(nz(str(e[3])) for e in eps)
        ti = []
        for e in eps:
            et = nz(str(e[3]))
            if len(et) >= 7 and cnt[et] == 1 and (len(et.split()) >= 2 or t.get('foc')) and not re.match(r'^(episode|part|pilot|show|chapter) ', et): ti.append((et, e))
        dc = collections.Counter(str(e[2]) for e in eps)
        M[t['k']] = {'se': {(e[0], e[1]): e for e in eps}, 'ti': ti, 'ad': {} if t['kind'] == 'date' else {str(e[2]): e for e in eps if re.match(r'\d{4}-\d\d-\d\d$', str(e[2])) and dc[str(e[2])] == 1}}
    return M


def stable(c):
    off = 1 if c.get('ver') or (OFFX.search(c.get('ch') or '') and c.get('views', 0) >= 200) else 0
    if c.get('ver'): return 1, 'verified channel'
    if c.get('inh') and c['age'] >= 4 and c.get('views', 0) >= 500: return off, 'channel of long-standing uploads, %d views' % c['views']
    if c['age'] >= 4 and c.get('views', 0) >= 1500: return off, 'up %d years, %d views' % (int(c['age']), c['views'])
    if off and c['age'] >= 1: return 1, 'rights-holder style channel'
    return off, ''


def run_search():
    tasks = json.load(gzip.open(os.path.join(PARTS, 'yt_plan.json.gz'), 'rt', encoding='utf-8'))
    M = build_M(tasks)
    byk = {t['k']: t for t in tasks}
    jobs = []
    for i, t in enumerate(tasks):
        for j, q in enumerate(t['qs']): jobs.append((t.get('pri', t['tier']), j, t['k'], q, 2))
        for j, q in enumerate(t['epq']): jobs.append((t.get('pri', t['tier']) + 0.5, j, t['k'], q, 1))
    jobs.sort(key=lambda x: (x[0], x[1]))
    jobs = [j for n, j in enumerate(jobs) if n % SHARDS == SHARD]
    acc = {}; seen = set(); chan = collections.Counter(); chname = {}; chver = {}
    cks = {}; cage = {}
    if CHAN:
        jobs = []
        try: old = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
        except Exception: old = []
        cc = collections.Counter(); pr = collections.Counter(); kk = collections.defaultdict(collections.Counter); ag = collections.defaultdict(list)
        for x in old:
            if not x.get('chid') or not (x.get('ad') or x.get('se')): continue
            cc[x['chid']] += 1; chname[x['chid']] = x['ch']; kk[x['chid']][x['k']] += 1
            if x['q'] in ('morning', 'late', 'news') or x['k'] in RUNS: pr[x['chid']] += 1
            if x.get('agey') is not None: ag[x['chid']].append(x['agey'])
            if x.get('off') and str(x.get('why', '')).startswith('verified'): chver[x['chid']] = 1
        if DEEP:
            dq = collections.Counter()
            for x in old:
                if x.get('chid') and x.get('ad') and x['q'] in ('morning', 'late', 'news', 'talk'): dq[x['chid']] += 1
            cl = [c for c, n in dq.most_common(int(os.environ.get('CHMAX', '48'))) if n >= 8]
        else:
            cl = sorted((c for c in cc if cc[c] >= 3 or pr[c]), key=lambda c: (-min(pr[c], 1), -cc[c], c))[:int(os.environ.get('CHMAX', '420'))]
        cl = [c for n, c in enumerate(cl) if n % SHARDS == SHARD]
        byt = {t['title']: t for t in tasks}
        for c in cl:
            cks[c] = [k for k, n in kk[c].most_common(6)]
            if DEEP:
                yq = []
                for k, n in kk[c].most_common(12):
                    t = byt.get(k)
                    if not t or t['kind'] != 'date': continue
                    al = DQ.get(k, [t['title']])[0]
                    yq += [al + ' %d' % y for y in range(max(1984, t['y0'] or 1984), min(2004, t['y1'] or 2004) + 1)]
                cks[c] = cks[c] + yq
            a = sorted(ag[c]); cage[c] = a[len(a) // 2] if a else -1
        print('channel list', len(cl), 'channel queries', sum(len(v) for v in cks.values()))
        print('channel list', len(cl))
    print('shard', SHARD, 'queries', len(jobs))
    def take(k, c, src):
        t = byk[k]; r = match(t, c, M)
        if not r: return False
        off, why = stable(c)
        if not why:
            STAT['unstable'] += 1
            if c['age'] >= 0 and c['age'] < 1 and c.get('views', 0) < 300: return False
            why = 'maybe: up %s years, %d views' % (('%d' % int(c['age'])) if c['age'] >= 0 else '?', c.get('views', 0)); c = dict(c, maybe=1)
        if r.get('m'): why = 'maybe: ' + r['m'] + '; ' + re.sub(r'^maybe: ', '', why); c = dict(c, maybe=1)
        key = c['vid']
        if key in acc: return True
        acc[key] = dict(c, k=k, r=r, off=off, why=why, src=src)
        return True
    def one(job):
        if left() < BUDGET * 0.45: return
        _, _, k, q, pages = job
        res = search(q, pages)
        with LOCK:
            STAT['queries'] += 1; STAT['results'] += len(res)
            for c in res:
                chname[c['chid']] = c['ch']
                if c['ver']: chver[c['chid']] = 1
                if (k, c['vid']) in seen: continue
                seen.add((k, c['vid']))
                if take(k, c, 'q'): chan[c['chid']] += 1
        time.sleep(0.5 + random.random())
    with ThreadPoolExecutor(THREADS) as ex: list(ex.map(one, jobs))
    print('after queries: accepted', len(acc), 'stat', dict(STAT))
    alidx = sorted(((a, t['k']) for t in tasks for a in t['al'] if len(a) >= 5), key=lambda x: -len(x[0]))
    aw = collections.defaultdict(list)
    for a, k in alidx: aw[a.split(' ')[0]].append((a, k))
    def amatch(n):
        best = None
        for w in set(n.split()):
            for a, k in aw.get(w, ()):
                if (not best or len(a) > len(best[0])) and n.find(' ' + a + ' ') >= 0: best = (a, k)
        return best[1] if best else None
    tops = [c for c, n in chan.most_common(400) if c and (n >= 3 or chver.get(c))]
    tops = [c for i, c in enumerate(sorted(tops)) if True][:60]
    if CHAN: tops = list(cks)
    print('channels to enumerate', len(tops))
    def enum(chid):
        if left() < BUDGET * 0.22: return
        vs = []
        if CHAN:
            sv = set()
            for q in CQ + cks.get(chid, []):
                if left() < BUDGET * 0.22: break
                for c in channel_search(chid, chname.get(chid, ''), q, 2 if DEEP and re.search(r' \d{4}$', q) else 3):
                    if c['vid'] not in sv: sv.add(c['vid']); vs.append(c)
                time.sleep(0.3 + random.random() * 0.4)
            with LOCK: STAT['chan_search_videos'] += len(vs)
        vs += [c for c in (channel_videos(chid, chname.get(chid, ''), 40, 20000, 1500) if DEEP else channel_videos(chid, chname.get(chid, ''))) if not CHAN or c['vid'] not in sv]
        ages = sorted(c['age'] for c in vs if c['age'] >= 0) or sorted(c['age'] for c in acc.values() if c['chid'] == chid and c['age'] >= 0)
        med = ages[len(ages) // 2] if ages else cage.get(chid, -1)
        for c in vs:
            if c['age'] < 0: c['age'] = med; c['inh'] = 1
            if chver.get(chid): c['ver'] = 1
        got = 0
        with LOCK:
            STAT['chan_enum'] += 1; STAT['chan_videos'] += len(vs)
            for c in vs:
                k = amatch(' ' + nz(c['t']) + ' ')
                if k and take(k, c, 'ch'): got += 1
        print('  channel', (chname.get(chid, '') or chid)[:40], 'videos', len(vs), 'accepted', got)
    with ThreadPoolExecutor(max(2, THREADS // 2)) as ex: list(ex.map(enum, tops))
    items = list(acc.values())
    best = {}
    for c in items:
        r = c['r']; ek = (c['k'], tuple(r['se']) if r['se'] else (r['ad'] or c['vid']))
        sc = (c['off'] * 3 + (0 if c.get('maybe') else 2) + (1 if c['age'] >= 4 else 0) + min(2, c['views'] / 5e5), c['dur'])
        if ek not in best or sc > best[ek][0]: best[ek] = (sc, c)
    items = [v[1] for v in best.values()]
    print('distinct episodes', len(items))
    def det(c):
        if left() < 90: c['oe'] = -1; return
        c['oe'] = oembed(c['vid'])
        if c['oe'] == 200 and left() > 300:
            c['pl'] = player(c['vid'])
        time.sleep(0.2 + random.random() * 0.4)
    with ThreadPoolExecutor(THREADS) as ex: list(ex.map(det, items))
    print('stat', dict(STAT), 'oembed', dict(collections.Counter(c.get('oe') for c in items)), 'player', dict(collections.Counter((c.get('pl') or {}).get('status', 'none') for c in items)))
    os.makedirs(PARTS, exist_ok=True)
    json.dump(items, gzip.open(os.path.join(PARTS, 'yt-%d.json.gz' % SHARD), 'wt', encoding='utf-8'))


def merge():
    tasks = json.load(gzip.open(os.path.join(PARTS, 'yt_plan.json.gz'), 'rt', encoding='utf-8'))
    byk = {t['k']: t for t in tasks}
    old = []
    if os.path.exists(OUT):
        try: old = json.load(gzip.open(OUT, 'rt', encoding='utf-8'))
        except Exception: old = []
    cand = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'yt-*.json.gz'))):
        try: cand += json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception as e: print('bad part', p, e)
    rej = collections.Counter(); new = {}
    for c in cand:
        t = byk.get(c['k'])
        if not t: continue
        pl = c.get('pl') or {}
        if c.get('oe') != 200: rej['oembed_%s' % c.get('oe')] += 1; continue
        if pl.get('emb') is False: rej['noembed'] += 1; continue
        if pl.get('us') == 0: rej['region'] += 1; continue
        if pl.get('safe') is False: rej['age'] += 1; continue
        if pl.get('livec'): rej['live'] += 1; continue
        r = c['r']
        if r['se'] and (r['se'][0], r['se'][1]) in set(map(tuple, t['cov'])): rej['covered'] += 1; continue
        dur = pl.get('dur') or c['dur']
        up = pl.get('up') or ''
        if up and up > str(TODAY - datetime.timedelta(days=365)) and not c['off']: rej['recent'] += 1; continue
        ad = r['ad'] if re.match(r'\d{4}-\d\d-\d\d$', r['ad'] or '') else ''
        if ad and not c['off'] and r['se'] and not ('1960-01-01' <= ad <= '2004-12-31'): rej['range'] += 1; continue
        it = {'i': 'yt:' + c['vid'], 'vid': c['vid'], 't': c['t'], 'ch': c['ch'], 'chid': c['chid'], 'off': c['off'], 'dur': dur, 'up': up, 'views': pl.get('views') or c['views'], 'q': 'rerun' if t['q'] == 'prime' and (t['y1'] and t['y1'] < 1984) else t['q'], 'k': t['title'], 'ad': ad, 'e': int(ad[:4]) if ad else r['e'], 'net': t['net'], 'ct': 'yt', 'why': c['why']}
        if c.get('maybe'): it['keep'] = 'maybe'
        if r['se']: it['se'] = r['se']; it['ep'] = r['ep']
        if not up and c['age'] >= 0: it['agey'] = round(c['age'], 1)
        ek = (it['k'], tuple(it.get('se') or ()) or it['ad'] or it['vid'])
        sc = (it['off'], 0 if it.get('keep') else 1, it['views'])
        if ek not in new or sc > new[ek][0]: new[ek] = (sc, it)
    out = {}
    M = build_M(tasks); byt = {t['title']: t for t in tasks}; purged = 0
    for it in old:
        t = byt.get(it['k'])
        if t:
            r = match(dict(t, foc=1) if str(it.get('why', '')).startswith('maybe: episode not identified') else t, {'t': it['t'], 'dur': it['dur'], 'live': 0, 'ch': it.get('ch'), 'off': it.get('off')}, M)
            if not r: purged += 1; continue
            if r.get('m') and not it.get('keep'): it['keep'] = 'maybe'; it['why'] = 'maybe: ' + str(r['m']) + '; ' + str(it.get('why', ''))
            if r['ad'] and not it.get('ad') and re.match(r'\d{4}-\d\d-\d\d$', r['ad']): it['ad'] = r['ad']; it['e'] = int(r['ad'][:4])
            if r['se'] and not it.get('se'):
                it['se'] = r['se']; it['ep'] = r['ep']
                if str(it.get('why', '')).startswith('maybe: episode not identified'):
                    w = re.sub(r'^maybe: episode not identified(; )?', '', it['why'])
                    if w and not w.startswith('maybe') and not re.match(r'up [0-3] years', w): it['why'] = w; it.pop('keep', None)
                    else: it['why'] = 'maybe: ' + re.sub(r'^maybe: ', '', w or 'upload age unknown')
        ek = (it['k'], tuple(it.get('se') or ()) or it.get('ad') or it['vid'])
        if ek in out and (out[ek].get('off', 0), 0 if out[ek].get('keep') else 1, out[ek].get('views', 0)) >= (it.get('off', 0), 0 if it.get('keep') else 1, it.get('views', 0)): continue
        out[ek] = it
    print('purged from previous', purged)
    for ek, (sc, it) in new.items():
        if ek not in out or (it['off'], 0 if it.get('keep') else 1, it['views']) > (out[ek].get('off', 0), 0 if out[ek].get('keep') else 1, out[ek].get('views', 0)): out[ek] = it
    chn = collections.Counter(x.get('chid') or x['ch'] for x in out.values() if x.get('se') or x.get('ad'))
    promoted = 0
    for it in out.values():
        m = re.match(r'maybe: up (\d+) years, (\d+) views$', str(it.get('why', '')))
        n = chn[it.get('chid') or it['ch']]
        if it.get('keep') == 'maybe' and m and int(m.group(1)) >= 4 and int(m.group(2)) >= 150 and n >= 5 and (it.get('se') or it.get('ad')):
            it.pop('keep'); it['why'] = 'up %s years, %s views, channel with %d similar uploads' % (m.group(1), m.group(2), n); promoted += 1
    print('promoted by channel history', promoted)
    items = sorted(out.values(), key=lambda x: (x['k'], x.get('se') or [0, 0], x.get('ad') or ''))
    json.dump(items, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('candidates', len(cand), 'rejected', dict(rej), 'previous', len(old), 'total', len(items), 'hours', round(sum(x['dur'] for x in items) / 3600))
    print('official share', round(100 * sum(1 for x in items if x['off']) / max(1, len(items))), '%')
    print('PER CATEGORY', dict(collections.Counter(x['q'] for x in items)))
    print('PER YEAR', sorted(collections.Counter(x['e'] for x in items).items()))
    ch = collections.Counter(x['ch'] for x in items)
    print('PER CHANNEL (top 60)')
    for c, n in ch.most_common(60): print(' ', str(n).rjust(5), c[:50], 'off' if any(x['off'] for x in items if x['ch'] == c) else '')
    per = collections.defaultdict(lambda: [0, 0])
    for x in items: per[x['k']][0 if x['off'] else 1] += 1
    print('PER SHOW (tier, show, guide eps, already covered, yt official, yt other, flag)')
    for t in tasks:
        a, b = per.get(t['title'], [0, 0]); ne = len(t['eps'])
        left_ = max(0, ne - len(t['cov']) - a - b) if ne else -1
        if t['tier'] <= 2 or a + b:
            print(' ', t['tier'], t['title'][:42].ljust(42), str(ne).rjust(5), str(len(t['cov'])).rjust(5), str(a).rjust(5), str(b).rjust(5), ' FOUND' if a + b >= 20 else ' THIN' if a + b else ' MISSING', ('still missing %d' % left_) if left_ >= 0 else '')
    random.seed(7)
    print('SAMPLES')
    for x in random.sample(items, min(80, len(items))):
        print(' ', x['i'], '|', x['k'][:28], '|', x.get('se'), '|', x['ad'], '|', x['dur'] // 60, 'min |', x['ch'][:26], '|', 'off' if x['off'] else '', '|', x['t'][:70])


def probe():
    print('== yt-dlp')
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'skip_download': True}) as y:
            r = y.extract_info('ytsearch5:computer chronicles full episode', download=False)
            for e in r.get('entries', [])[:5]: print('  flat', e.get('id'), e.get('duration'), (e.get('title') or '')[:60], e.get('channel'))
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as y:
            try:
                r = y.extract_info('https://www.youtube.com/watch?v=' + (r['entries'][0]['id']), download=False)
                print('  info', r.get('upload_date'), r.get('playable_in_embed'), r.get('age_limit'), r.get('view_count'), r.get('channel'), r.get('channel_is_verified'))
            except Exception as e: print('  info fail', str(e)[:200])
    except Exception as e: print('  yt-dlp fail', str(e)[:200])
    print('== innertube search')
    res = search('computer chronicles full episode', 2)
    print('  results', len(res))
    for c in res[:8]: print('  ', c)
    print('== innertube browse')
    if res and res[0]['chid']:
        vs = channel_videos(res[0]['chid'], res[0]['ch'], 3)
        print('  channel videos', len(vs)); [print('  ', c) for c in vs[:4]]
    for chid, q in (('UCBR8-60-B28hp2BmDPdntcQ', 'today'),) + tuple((x, 'today show') for x in os.environ.get('PROBE_CH', 'UC4LibjxwJ2SIwpGSUo41yOQ,UCn6Dg8imByAYiCTO10WybzQ').split(',') if x):
        d = inner('browse', {'browseId': chid, 'params': 'EgZ2aWRlb3PyBgQKAjoA'})
        ks = collections.Counter()
        def keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.endswith(('Renderer', 'ViewModel')): ks[k] += 1
                    keys(v)
            elif isinstance(o, list):
                for v in o: keys(v)
        keys(d or {})
        print('  videos tab', chid, 'keys', ks.most_common(12))
        lk = walk(d or {}, 'lockupViewModel', [])
        if lk: print('  lockup sample', json.dumps(lk[0])[:1500])
        vs = channel_videos(chid, '', 2)
        print('  channel_videos', len(vs), vs[:3])
        cs = channel_search(chid, '', q, 2)
        print('  channel_search', q, len(cs)); [print('    ', c) for c in cs[:6]]
    print('== oembed / player')
    for c in res[:4]:
        print('  ', c['vid'], 'oembed', oembed(c['vid']), 'player', player(c['vid']))
    st, raw = http('https://www.youtube.com/feeds/videos.xml?channel_id=' + (res[0]['chid'] if res else 'UCBR8-60-B28hp2BmDPdntcQ'))
    print('== rss', st, len(raw))
    print('stat', dict(STAT))


if MODE == 'probe': probe()
elif MODE == 'plan': plan()
elif MODE == 'search':
    run_search()
    sys.stdout.flush()
    os._exit(0)
elif MODE == 'merge': merge()
