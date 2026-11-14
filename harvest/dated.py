import json, gzip, os, re, sys, time, random, glob, collections, datetime, urllib.parse, urllib.request
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
OUTF = os.path.join(OUT, 'dated.json.gz')
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
ERA = '(date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + ') OR description:(' + YRS + '))'
NOTV = 'NOT collection:(tvarchive OR tvnews OR TV-CSPAN OR TV-CSPAN2 OR podcasts OR community_media)'
def norm(s):
    s = (s or '').lower().replace('&', ' and ').replace('’', "'").replace('u.s.', 'us')
    s = re.sub(r"[^a-z0-9@]+", ' ', s.replace("'", ''))
    return ' ' + ' '.join(s.split()) + ' '
NFL = ['49ers', 'niners', 'bears', 'bengals', 'bills', 'broncos', 'browns', 'buccaneers', 'bucs', 'cardinals', 'chargers', 'chiefs', 'colts', 'cowboys', 'dolphins', 'eagles', 'falcons', 'giants', 'jaguars', 'jets', 'lions', 'oilers', 'packers', 'panthers', 'patriots', 'raiders', 'rams', 'ravens', 'redskins', 'saints', 'seahawks', 'steelers', 'texans', 'titans', 'vikings']
NBA = ['76ers', 'sixers', 'bucks', 'bulls', 'cavaliers', 'cavs', 'celtics', 'clippers', 'grizzlies', 'hawks', 'heat', 'hornets', 'jazz', 'kings', 'knicks', 'lakers', 'magic', 'mavericks', 'mavs', 'nets', 'nuggets', 'pacers', 'pistons', 'raptors', 'rockets', 'spurs', 'suns', 'supersonics', 'sonics', 'timberwolves', 'trail blazers', 'blazers', 'warriors', 'bullets', 'wizards']
MLB = ['angels', 'astros', 'athletics', 'blue jays', 'braves', 'brewers', 'cardinals', 'cubs', 'diamondbacks', 'dodgers', 'expos', 'giants', 'indians', 'mariners', 'marlins', 'mets', 'orioles', 'padres', 'phillies', 'pirates', 'rangers', 'reds', 'red sox', 'rockies', 'royals', 'tigers', 'twins', 'white sox', 'yankees', 'devil rays']
NHL = ['bruins', 'sabres', 'flames', 'blackhawks', 'red wings', 'oilers', 'whalers', 'kings', 'north stars', 'canadiens', 'devils', 'islanders', 'rangers', 'flyers', 'penguins', 'nordiques', 'blues', 'maple leafs', 'canucks', 'capitals', 'jets', 'sharks', 'lightning', 'senators', 'panthers', 'mighty ducks', 'stars', 'avalanche', 'coyotes', 'hurricanes', 'predators', 'thrashers', 'blue jackets', 'wild']
COL = ['notre dame', 'ohio state', 'michigan state', 'michigan', 'penn state', 'nebraska', 'oklahoma state', 'oklahoma', 'texas a and m', 'texas tech', 'texas', 'alabama', 'auburn', 'lsu', 'florida state', 'florida', 'miami', 'georgia tech', 'georgia', 'tennessee', 'clemson', 'usc', 'ucla', 'washington state', 'washington', 'oregon state', 'oregon', 'stanford', 'colorado', 'kansas state', 'kansas', 'missouri', 'iowa state', 'iowa', 'wisconsin', 'minnesota', 'illinois', 'indiana', 'purdue', 'northwestern', 'syracuse', 'boston college', 'pittsburgh', 'pitt', 'west virginia', 'virginia tech', 'virginia', 'nc state', 'north carolina state', 'north carolina', 'unc', 'duke', 'wake forest', 'maryland', 'kentucky', 'louisville', 'arkansas', 'ole miss', 'mississippi state', 'south carolina', 'vanderbilt', 'byu', 'utah', 'arizona state', 'arizona', 'army', 'navy', 'air force', 'georgetown', 'villanova', 'st johns', 'uconn', 'connecticut', 'unlv', 'houston', 'memphis state', 'memphis', 'cincinnati', 'marquette', 'depaul', 'temple', 'umass', 'seton hall', 'providence', 'gonzaga', 'tulsa', 'smu', 'tcu', 'baylor', 'rutgers', 'fresno state', 'hawaii', 'east carolina', 'colorado state', 'tulane', 'xavier', 'dayton', 'loyola', 'princeton', 'harvard', 'yale']
def rx(names): return re.compile(r' (' + '|'.join(sorted((re.escape(n) for n in names), key=len, reverse=True)) + r')(?= )')
RXT = {'nfl': rx(NFL), 'nba': rx(NBA), 'mlb': rx(MLB), 'nhl': rx(NHL)}
RXC = rx(COL)
FIGHT = rx(['tyson', 'holyfield', 'sugar ray leonard', 'leonard', 'hagler', 'hearns', 'duran', 'chavez', 'de la hoya', 'foreman', 'lennox lewis', 'bowe', 'whitaker', 'trinidad', 'roy jones', 'hopkins', 'mayweather', 'pacquiao', 'camacho', 'spinks', 'larry holmes', 'holmes', 'buster douglas', 'morrison', 'moorer', 'mosley', 'vargas', 'gatti', 'barrera', 'morales', 'hamed', 'pryor', 'arguello', 'mancini', 'mcgirt', 'meldrick taylor', 'terry norris', 'toney', 'benn', 'eubank', 'cooney', 'tucker', 'ruddock', 'mercer', 'tua', 'golota', 'klitschko', 'rahman', 'byrd', 'tszyu', 'judah', 'forrest', 'quartey', 'mcclellan', 'nunn', 'kalambay', 'curry', 'starling', 'breland', 'mccallum', 'jackson', 'qawi', 'cokes', 'tarver', 'calzaghe'])
X_FOR = r"\b(castellano|espa[nñ]ol|latino|doblaje|dublado|legendado|portugu[eê]s|deutsch|fran[cç]ais|vostfr|italiano|nederlands|svenska|polski|русск|hindi|tamil|urdu|arabic|bahasa|tagalog|subtitulado|bbc|itv|channel 4|sky sports|sky news|rte|cbc|tsn|hockey night in canada|sportsnet|cfl|grey cup|premier league|la liga|bundesliga|serie a|uefa|fifa|cricket|rugby|afl|nrl|gaa|tagesschau|kbs|nhk|zdf|ard|heute|telediario|noticias|noticiero|noticiario|telejornal|jornal|journal de|tf1|france 2|rai|tg1|tg2|televisa|vremya|cctv|doordarshan|wwos|gtv|tcn|nws|qtq|hsv|gts|bkn|abn|tvw|stw|nine network|channel nine|seven network|ten network|a current affair australia|granada|thames|anglia|ulster|grampian|central news|calendar news|look north|reporting scotland|ntv|ctv|global news|citytv|cfto|cbmt|radio canada|seven news|nine news|ten news|national nine|tvq|btq|qtq|itn|ten eyewitness|seven nightly|local news sample: c[a-z]{3}\b|news at ten|bbc news)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|speedrun|nes|snes|sega|genesis|playstation|ps[1-5]|xbox|game ?boy|n64|nintendo|arcade|dos game|pc game|rom|emulator|madden|nba jam|nba live|nba 2k|nhl hitz|blitz|tecmo|ea sports|pinball|board game|trading cards?|card pack|comic|novel|audiobook|ebook|pdf|magazine|program scan|scans?|ticket stub|soundtrack|theme song|theme music|intro|intros|news opens?|show opens?|opening credits|closing credits|credits|how to|g4tv|halftime|half time show|marching band|power rangers|parade|bumpers?|promos?|trailers?|teaser|bloopers?|outtakes?|follies|fan ?made|fan-?edit|parody|spoof|review|recap|podcast|reaction|rewatch|retrospective|tribute|documentary|making of|behind the scenes|yearbook|nfl films|highlights?|highlight reel|top \d+|greatest moments|best of|plays of|mixtape|compilation|supercut|montage|mashup|remix|music video|karaoke|lyrics|radio|radio broadcast|radio call|audio only|audio|press conference|interview|xxx|porn|adult|wwf|wwe|wcw|ecw|nwa|awa|wrestlemania|summerslam|royal rumble|wrestling|special olympics|simulation|simulated|sim|what if|photos?|slideshow|screensaver|wallpaper)\b"
X_ADS = r"\bcommercials?\b|\bads?\b"
OK_ADS = r"(with|w/|w|incl\w*|original|and) ?(original |orig\.? )?(commercials|ads)|commercials included|\bwoc\b"
MON = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
MN = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?'
YR = r'(19[89]\d|200[0-4])'
def mk(y, m, d):
    try:
        y, m, d = int(y), int(m), int(d)
        if y < 100: y += 1900 if y >= 84 else 2000
        if not (1984 <= y <= 2004): return None
        return datetime.date(y, m, d).isoformat()
    except Exception: return None
def dates_in(s):
    s = (s or '').lower(); out = []
    for m in re.finditer(r'(?<!\d)' + YR + r'[-_./ ](\d{1,2})[-_./ ](\d{1,2})(?!\d)', s):
        d = mk(m.group(1), m.group(2), m.group(3))
        if d: out.append((m.start(), d))
    for m in re.finditer(r'(?<![\d.])(\d{1,2})[-_./](\d{1,2})[-_./]((?:19|20)\d{2}|[89]\d|0[0-4])(?![\d])', s):
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12 and b <= 12: a, b = b, a
        d = mk(y, a, b)
        if d: out.append((m.start(), d))
    for m in re.finditer(r'(?<!\d)' + YR + r'(0[1-9]|1[0-2])([0-3]\d)(?!\d)', s):
        d = mk(m.group(1), m.group(2), m.group(3))
        if d: out.append((m.start(), d))
    for m in re.finditer(r'\b' + MN + r'\s*(\d{1,2})(?:st|nd|rd|th)?,?\s*' + r"((?:19|20)\d{2}|'\d{2})(?!\d)", s):
        d = mk(m.group(3).strip("'"), MON[m.group(1)], m.group(2))
        if d: out.append((m.start(), d))
    for m in re.finditer(r'(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s*' + MN + r',?\s*((?:19|20)\d{2})(?!\d)', s):
        d = mk(m.group(3), MON[m.group(2)], m.group(1))
        if d: out.append((m.start(), d))
    out.sort()
    return out
BADY = r'(?<!\d)(19[0-7]\d|198[0-3]|200[5-9]|20[1-3]\d)(?!\d)'
SB = {'xviii': '1984-01-22', 'xix': '1985-01-20', 'xx': '1986-01-26', 'xxi': '1987-01-25', 'xxii': '1988-01-31', 'xxiii': '1989-01-22', 'xxiv': '1990-01-28', 'xxv': '1991-01-27', 'xxvi': '1992-01-26', 'xxvii': '1993-01-31', 'xxviii': '1994-01-30', 'xxix': '1995-01-29', 'xxx': '1996-01-28', 'xxxi': '1997-01-26', 'xxxii': '1998-01-25', 'xxxiii': '1999-01-31', 'xxxiv': '2000-01-30', 'xxxv': '2001-01-28', 'xxxvi': '2002-02-03', 'xxxvii': '2003-01-26', 'xxxviii': '2004-02-01'}
SBN = dict(zip(range(18, 39), SB.values()))
DAYT = {1984: '02-19', 1985: '02-17', 1986: '02-16', 1987: '02-15', 1988: '02-14', 1989: '02-19', 1990: '02-18', 1991: '02-17', 1992: '02-16', 1993: '02-14', 1994: '02-20', 1995: '02-19', 1996: '02-18', 1997: '02-16', 1998: '02-15', 1999: '02-14', 2000: '02-20', 2001: '02-18', 2002: '02-17', 2003: '02-16', 2004: '02-15'}
def indy(y):
    if y == 1986: return '1986-05-31'
    if y == 1997: return '1997-05-27'
    d = datetime.date(y, 5, 31)
    while d.weekday() != 0: d -= datetime.timedelta(1)
    return (d - datetime.timedelta(1)).isoformat()
def derby(y):
    d = datetime.date(y, 5, 1)
    while d.weekday() != 5: d += datetime.timedelta(1)
    return d.isoformat()
def event_date(nt):
    if ' super bowl ' in nt:
        m = re.search(r' super bowl ([xvi]{2,7}) ', nt)
        if m and m.group(1) in SB: return SB[m.group(1)]
        m = re.search(r' super bowl (\d{2}) ', nt)
        if m and int(m.group(1)) in SBN: return SBN[int(m.group(1))]
        return None
    ys = re.findall(r'(?<!\d)' + YR + r'(?!\d)', nt)
    if len(set(ys)) != 1 or re.search(r' (practice|qualifying|qualifications|time trials|pole day|carb day|bump day|twin 125s?|duels?|busch clash|shootout|preview|pre race|prerace|trials) ', nt): return None
    y = int(ys[0])
    if y not in DAYT: return None
    if ' daytona 500 ' in nt: return '%d-%s' % (y, DAYT[y])
    if re.search(r' (indy|indianapolis) 500 ', nt): return indy(y)
    if ' kentucky derby ' in nt: return derby(y)
    return None
def find_date(title, ident, dfield, desc):
    tl = (title or '').lower()
    ds = dates_in(tl)
    if ds: return ds[0][1], 'title'
    ev = event_date(norm(title))
    if ev: return ev, 'event'
    if re.search(BADY, tl): return None, ''
    ty = set(int(v) for v in re.findall(r'(?<!\d)' + YR + r'(?!\d)', tl))
    def fits(d): return not ty or int(d[:4]) in ty or (int(d[5:7]) <= 2 and int(d[:4]) - 1 in ty)
    ds = [d for _, d in dates_in((ident or '').lower()) if fits(d)]
    if ds: return ds[0], 'ident'
    df = str(dfield or '')[:10]
    if re.match(r'^' + YR + r'-\d\d-\d\d$', df) and not df.endswith('-01-01') and mk(df[:4], df[5:7], df[8:10]) and fits(df): return df, 'meta'
    dl = (desc or '').lower()[:800]
    ds = [(p, d) for p, d in dates_in(dl) if fits(d)]
    if ds:
        for pos, d in ds:
            if re.search(r'(aired|air date|airdate|broadcast|recorded|taped|telecast|originally|from|dated?|played)\W{0,25}$', dl[max(0, pos - 40):pos]): return d, 'desc'
        if len(set(d for _, d in ds)) == 1: return ds[0][1], 'desc'
    return None, ''
NETRX = r'\b(abc|cbs|nbc|fox|espn2|espn|tbs|wtbs|tnt|usa network|usa|hbo|showtime|wgn|wor|upn|pbs|cnn|msg|sportschannel|prime ticket|nesn|comedy central|qvc|hsn)\b'
def netof(title, desc):
    for s in (title, (desc or '')[:300]):
        m = re.search(NETRX, (s or '').lower())
        if m: return {'wtbs': 'tbs', 'usa network': 'usa', 'espn2': 'espn'}.get(m.group(1), m.group(1))
    return ''
VS = r' (vs|versus|v|at|@) '
def teams(nt):
    r = {}
    for lg, x in RXT.items():
        f = set(x.findall(nt))
        if f: r[lg] = f
    return r
def sport(title, desc, ad):
    nt = norm(title); nd = norm((desc or '')[:300]); mo = int(ad[5:7]) if ad else 0
    wd = datetime.date(int(ad[:4]), int(ad[5:7]), int(ad[8:10])).weekday() if ad else -1
    if ' super bowl ' in nt: return 'nfl', 'SUPER BOWL'
    if ' monday night football ' in nt or ' mnf ' in nt: return 'nfl', 'MONDAY NIGHT FOOTBALL'
    if ' world series ' in nt and ' college ' not in nt and ' little league ' not in nt and ' poker ' not in nt: return 'mlb', 'WORLD SERIES'
    if ' nba finals ' in nt: return 'nba', 'NBA FINALS'
    if ' stanley cup ' in nt: return 'nhl', 'STANLEY CUP PLAYOFFS'
    if re.search(r' (sportscenter|sports center) ', nt): return 'studio', 'SPORTSCENTER'
    if re.search(r' (olympics|olympic games|winter olympics|summer olympics|olympic) ', nt): return 'olympics', 'OLYMPIC GAMES'
    if re.search(r' (indy 500|indianapolis 500|daytona 500|winston cup|nascar|busch series|busch grand national|brickyard 400|coca cola 600|talladega 500|southern 500|cart|indycar|indy car) ', nt): return 'racing', 'AUTO RACING'
    if re.search(r' (kentucky derby|preakness|belmont stakes|breeders cup) ', nt): return 'horse', 'HORSE RACING'
    if re.search(r' (wimbledon|french open|australian open|davis cup) ', nt) or (' us open ' in nt and (' tennis ' in nt + nd or mo in (8, 9))): return 'tennis', 'TENNIS'
    if re.search(r' (pga championship|british open|ryder cup|players championship|pga tour|skins game|pga) ', nt) or (' masters ' in nt and re.search(r' (golf|augusta|final round|tournament|cbs) ', nt + nd)) or (' us open ' in nt and (' golf ' in nt + nd or mo == 6)): return 'golf', 'GOLF'
    fs = set(FIGHT.findall(nt))
    if (re.search(r' (boxing|fight night|title fight|heavyweight|welterweight|middleweight|lightweight|tuesday night fights|world championship boxing|boxing after dark) ', nt) or len(fs) >= 2 or (fs and re.search(VS, nt) and re.search(r' (boxing|hbo|showtime|ppv|pay per view|fight|rounds?|closed circuit|tvko) ', nt + nd))) and (re.search(VS, nt) or len(fs) >= 1 or ' boxing ' in nt): return 'boxing', 'BOXING'
    if re.search(r' (nfl|afc championship|nfc championship|afc wild card|nfc wild card|afc divisional|nfc divisional|afc playoff|nfc playoff|pro bowl|nfl draft|nfl today|nfl live) ', nt): return 'nfl', 'NFL FOOTBALL'
    if re.search(r' (mlb|alcs|nlcs|alds|nlds|major league baseball|game of the week) ', nt) or (' all star game ' in nt and ' baseball ' in nt + nd): return 'mlb', 'MLB BASEBALL'
    if re.search(r' (nba|nba playoffs|nba on nbc|nba on cbs|nba on tbs|nba on tnt|nba all star) ', nt): return 'nba', 'NBA BASKETBALL'
    if re.search(r' (nhl|nhl playoffs|nhl on) ', nt): return 'nhl', 'NHL HOCKEY'
    if re.search(r' (rose|orange|sugar|fiesta|cotton|citrus|peach|gator|holiday|liberty|sun|independence|aloha|alamo|outback|hall of fame|copper|freedom|bluebonnet|cherry|california|las vegas|motor city|insight|music city|humanitarian|carquest|blockbuster|john hancock) bowl ', nt): return 'ncaaf', 'COLLEGE FOOTBALL'
    if re.search(r' (final four|ncaa tournament|march madness|ncaa basketball|college basketball|big east tournament|acc tournament|sec tournament|big ten tournament|nit|elite eight|sweet sixteen|sweet 16|ncaa championship game|national championship game) ', nt) and not ' hockey ' in nt: return 'ncaab', 'COLLEGE BASKETBALL'
    if re.search(r' (college football|ncaa football|army navy|kickoff classic|sec championship|big 12 championship) ', nt): return 'ncaaf', 'COLLEGE FOOTBALL'
    tm = teams(nt); has_vs = bool(re.search(VS, nt)); ctx = nt + nd
    two = [lg for lg, f in tm.items() if len(f) >= 2]
    one = [lg for lg, f in tm.items() if len(f) >= 1]
    def pick(c):
        if len(c) == 1: return c[0]
        for lg, w in (('nfl', r' (football|nfl|touchdown|quarterback) '), ('nba', r' (basketball|nba) '), ('mlb', r' (baseball|mlb|innings?|pitcher) '), ('nhl', r' (hockey|nhl|puck) ')):
            if lg in c and re.search(w, ctx): return lg
        return None
    if two and not (has_vs or re.search(r' (football|nfl|basketball|nba|baseball|mlb|hockey|nhl|playoffs?|finals|game) ', ctx)): two = []
    lg = pick(two) if two else (pick(one) if one and (has_vs or re.search(r' (game|playoffs?|finals|championship|series|opening day|opener|full broadcast|original broadcast) ', nt)) and re.search(r' (football|nfl|basketball|nba|baseball|mlb|hockey|nhl|playoffs?|finals) ', ctx) else None)
    if lg: return lg, {'nfl': 'NFL FOOTBALL', 'nba': 'NBA BASKETBALL', 'mlb': 'MLB BASEBALL', 'nhl': 'NHL HOCKEY'}[lg]
    cs = set(RXC.findall(nt))
    if len(cs) >= 2 and has_vs and not tm:
        if ' basketball ' in ctx: return 'ncaab', 'COLLEGE BASKETBALL'
        if ' football ' in ctx: return 'ncaaf', 'COLLEGE FOOTBALL'
        if ' hockey ' in ctx or ' baseball ' in ctx or ' lacrosse ' in ctx or ' soccer ' in ctx or ' volleyball ' in ctx: return None
        if mo in (9, 10) or (mo in (11, 12, 1) and (wd == 5 or ad[5:] in ('01-01', '01-02'))): return 'ncaaf', 'COLLEGE FOOTBALL'
        if mo in (11, 12, 1, 2, 3, 4): return 'ncaab', 'COLLEGE BASKETBALL'
    return None
def late(title, ad):
    r = late1(title, ad)
    if r and r[0] != 'SATURDAY NIGHT LIVE' and datetime.date(int(ad[:4]), int(ad[5:7]), int(ad[8:10])).weekday() > 4: return None
    return r
def late1(title, ad):
    nt = norm(title)
    if re.search(r' (monologue|top ten list|top 10 list|musical guest performance|performs|performance|sketch|sketches|clip|clips|segment|bit|cold open) ', nt): return None
    if ' tonight show ' in nt or ' johnny carson ' in nt or (' leno ' in nt and ' jay ' in nt):
        if ad < '1989-01-01': return None
        if ' leno ' in nt or ad >= '1992-05-25': return 'THE TONIGHT SHOW WITH JAY LENO', 'nbc'
        return 'THE TONIGHT SHOW STARRING JOHNNY CARSON', 'nbc'
    if ' letterman ' in nt:
        if ad < '1989-01-01': return None
        if ad >= '1993-08-30' or (' late show ' in nt and ad >= '1993-08-01'): return 'LATE SHOW WITH DAVID LETTERMAN', 'cbs'
        if ad <= '1993-06-26': return 'LATE NIGHT WITH DAVID LETTERMAN', 'nbc'
        return None
    if ' conan ' in nt and (' late night ' in nt or ' obrien ' in nt): return ("LATE NIGHT WITH CONAN O'BRIEN", 'nbc') if ad >= '1993-09-13' else None
    if ' arsenio ' in nt: return ('THE ARSENIO HALL SHOW', 'syn') if '1989-01-03' <= ad <= '1994-05-27' else None
    if ' saturday night live ' in nt or ' snl ' in nt:
        d = datetime.date(int(ad[:4]), int(ad[5:7]), int(ad[8:10]))
        return ('SATURDAY NIGHT LIVE', 'nbc') if d.weekday() in (5, 6) else None
    if ' politically incorrect ' in nt: return ('POLITICALLY INCORRECT', 'abc' if ad >= '1997-01-05' else 'cc') if '1993-07-25' <= ad <= '2002-07-05' else None
    if ' daily show ' in nt: return ('THE DAILY SHOW', 'cc') if ad >= '1996-07-22' else None
    if ' later ' in nt and (' costas ' in nt or ' greg kinnear ' in nt or ' later with ' in nt): return ('LATER', 'nbc') if ad >= '1988-08-22' else None
    if ' tom snyder ' in nt or ' late late show ' in nt:
        if ad < '1995-01-09': return None
        return ('THE LATE LATE SHOW WITH TOM SNYDER', 'cbs') if ad < '1999-03-30' and ' kilborn ' not in nt else ('THE LATE LATE SHOW WITH CRAIG KILBORN', 'cbs')
    return None
CALLX = {'WITH', 'WEEK', 'WAR', 'WILL', 'WHAT', 'WHEN', 'WERE', 'WANT', 'WELL', 'WEST', 'WILD', 'KING', 'KISS', 'KIDS', 'WAS', 'WHO', 'WHY', 'WIN', 'WINS', 'WON', 'WAY', 'WORK', 'WORD', 'WIDE', 'WALL', 'WAVE', 'WEB', 'KEY', 'KEN', 'KIM', 'KID', 'WOC', 'WTC', 'WWF', 'WWE', 'WCW', 'WWII', 'WMD', 'KKK', 'WHO', 'WAKE', 'WASH', 'WED', 'WEDS', 'KAY', 'KARL', 'KATE', 'KIRK', 'KURT', 'WADE', 'WALT', 'WARD', 'WEEKS', 'KOPS', 'WORLD', 'KGB', 'WHITE', 'WOMEN', 'WOMAN', 'WARS', 'WIRE', 'WOLF', 'KEEP', 'KILL', 'KNOW', 'KOBE'}
def news(title, raw):
    nt = norm(title)
    if re.search(r' (world news now|up to the minute|nightwatch|news overnight|nightline|today show|good morning america|this morning|early show|sunrise|60 minutes|20 20|dateline|48 hours|primetime live|entertainment tonight|inside edition|hard copy|a current affair|weekend update|not necessarily the news|daily show|news radio|newsradio|bad news bears|action news team|fake news|parody|spoof) ', nt): return None
    if ' world news tonight ' in nt or ' abc world news ' in nt: return 'ABC WORLD NEWS TONIGHT', 'abc', 'network', ''
    if ' nightly news ' in nt: return 'NBC NIGHTLY NEWS', 'nbc', 'network', ''
    if ' cbs evening news ' in nt or (' evening news ' in nt and ' rather ' in nt): return 'CBS EVENING NEWS', 'cbs', 'network', ''
    if ' headline news ' in nt: return 'HEADLINE NEWS', 'cnn', 'cable', ''
    if re.search(r' (election night|election coverage|election returns|decision 8[48]|decision 9[26]|decision 200[04]|campaign 8[48]|campaign 9[26]|vote 8[48]|vote 9[26]) ', nt): return 'ELECTION NIGHT COVERAGE', netof(title, ''), 'special', ''
    if ' cnn ' in nt: return 'CNN', 'cnn', 'cable', ''
    m = None
    for c in re.findall(r'\b([WK][A-Z]{2,3})(?:-TV)?\b', raw):
        if c not in CALLX: m = c; break
    loc = re.search(r' (eyewitness news|action news|newscenter|news center|newswatch|newscast|news at (5|6|10|11|noon|five|six|ten|eleven|nine|9)|(5|6|10|11) (pm|oclock) news|nightcast|nightbeat|channel \d+ news|news \d+|newschannel \d+|local news|late news|evening news|noon news|news update|news brief) ', nt)
    if loc or (m and ' news ' in nt): return 'LOCAL NEWS', netof(title, ''), 'local', m or ''
    if re.search(r' (breaking news|special report|news coverage|live coverage|news bulletin|news special) ', nt) and (' news ' in nt or m or netof(title, '')): return 'NEWS SPECIAL REPORT', netof(title, ''), 'special', m or ''
    return None
def shop(title):
    nt = norm(title)
    if ' qvc ' in nt: return 'QVC'
    if ' hsn ' in nt or ' home shopping network ' in nt or ' home shopping club ' in nt: return 'HOME SHOPPING NETWORK'
    if ' shop at home ' in nt: return 'SHOP AT HOME'
    if ' valuevision ' in nt or ' value vision ' in nt or ' home shopping ' in nt: return 'HOME SHOPPING'
    return None
def ok_title(t):
    if not t: return False
    low = t.lower() + ' '
    if re.search(r'[^\x00-\xff‐-‧™]', t) or re.search(r'[ãõçñ]', low): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low): return False
    if re.search(X_ADS, low) and not re.search(OK_ADS, low): return False
    return True
XCOL = {'community_media', 'podcasts', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'tvarchive', 'tvnews'}
def classify(title, ident, dfield, desc):
    if not ok_title(title): return None
    ad, src = find_date(title, ident, dfield, desc)
    if not ad: return None
    r = late(title, ad)
    if r: return {'q': 'late', 'ct': 'late', 'k': r[0], 'net': r[1], 'ad': ad, 'as': src, 'min': 1200}
    s = shop(title)
    if s: return {'q': 'block', 'ct': 'shopping', 'k': s, 'net': '', 'ad': ad, 'as': src, 'min': 600}
    r = news(title, title)
    if r: return {'q': 'news', 'ct': 'news_' + r[2], 'k': r[0], 'net': r[1], 'ad': ad, 'as': src, 'min': 600, 'st': r[3]}
    r = sport(title, desc, ad)
    if r: return {'q': 'sports', 'ct': r[0], 'k': r[1], 'net': netof(title, desc), 'ad': ad, 'as': src, 'min': 1200 if r[0] == 'studio' else 1800}
    return None
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, cap=200000):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,collection,downloads,language,description', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > cap: break
    return out
def T(*a): return 'title:(' + ' OR '.join('"%s"' % x if ' ' in x or "'" in x else x for x in a) + ')'
GAME = 'title:(vs OR versus OR game OR nfl OR nba OR mlb OR nhl OR football OR basketball OR baseball OR hockey OR playoffs OR playoff OR finals OR championship OR series OR broadcast)'
QUERIES = [
 ('nfl', T('nfl', 'super bowl', 'monday night football', 'afc championship', 'nfc championship', 'pro bowl', 'wild card', 'divisional playoff')),
 ('nfl teams', T('49ers', 'bengals', 'broncos', 'browns', 'buccaneers', 'chargers', 'chiefs', 'colts', 'cowboys', 'dolphins', 'falcons', 'jaguars', 'packers', 'patriots', 'raiders', 'redskins', 'seahawks', 'steelers', 'vikings', 'oilers')),
 ('nfl teams2', T('bears', 'bills', 'cardinals', 'eagles', 'giants', 'jets', 'lions', 'panthers', 'rams', 'ravens', 'saints', 'titans', 'texans') + ' AND ' + GAME),
 ('nba', T('nba', 'nba finals', 'nba playoffs', 'nba all-star')),
 ('nba teams', T('celtics', 'lakers', 'knicks', 'pistons', 'sixers', '76ers', 'cavaliers', 'mavericks', 'nuggets', 'pacers', 'spurs', 'supersonics', 'sonics', 'timberwolves', 'trail blazers', 'clippers', 'raptors', 'grizzlies')),
 ('nba teams2', T('bulls', 'bucks', 'hawks', 'heat', 'hornets', 'jazz', 'kings', 'magic', 'nets', 'rockets', 'suns', 'warriors', 'bullets', 'wizards') + ' AND ' + GAME),
 ('mlb', T('mlb', 'world series', 'alcs', 'nlcs', 'alds', 'nlds', 'major league baseball', 'all-star game', 'game of the week')),
 ('mlb teams', T('yankees', 'red sox', 'mets', 'dodgers', 'cubs', 'white sox', 'braves', 'phillies', 'orioles', 'astros', 'expos', 'padres', 'mariners', 'blue jays', 'brewers', 'marlins', 'devil rays', 'diamondbacks')),
 ('mlb teams2', T('angels', 'athletics', 'indians', 'pirates', 'rangers', 'reds', 'rockies', 'royals', 'tigers', 'twins') + ' AND ' + GAME),
 ('nhl', T('nhl', 'stanley cup')),
 ('nhl teams', T('bruins', 'canadiens', 'maple leafs', 'red wings', 'blackhawks', 'flyers', 'penguins', 'islanders', 'canucks', 'nordiques', 'whalers', 'sabres', 'north stars', 'mighty ducks', 'blue jackets', 'thrashers')),
 ('nhl teams2', T('flames', 'devils', 'blues', 'capitals', 'sharks', 'lightning', 'senators', 'stars', 'avalanche', 'coyotes', 'hurricanes', 'predators', 'wild') + ' AND ' + GAME),
 ('college', T('college football', 'ncaa football', 'college basketball', 'ncaa basketball', 'final four', 'ncaa tournament', 'march madness', 'rose bowl', 'orange bowl', 'sugar bowl', 'fiesta bowl', 'cotton bowl', 'citrus bowl', 'peach bowl', 'gator bowl', 'holiday bowl', 'liberty bowl', 'sun bowl', 'army navy', 'big east tournament', 'acc tournament', 'sec championship')),
 ('college teams', T('notre dame', 'ohio state', 'michigan', 'penn state', 'nebraska', 'oklahoma', 'alabama', 'auburn', 'lsu', 'florida state', 'miami', 'georgia', 'tennessee', 'clemson', 'usc', 'ucla', 'syracuse', 'duke', 'north carolina', 'kentucky', 'kansas', 'georgetown', 'villanova', 'unlv', 'indiana', 'arkansas', 'texas', 'florida', 'washington', 'colorado', 'wisconsin', 'iowa', 'louisville', 'uconn', 'arizona', 'maryland', 'virginia tech', 'west virginia', 'boston college', 'byu') + ' AND title:(vs OR versus) AND ' + ERA),
 ('olympics', T('olympics', 'olympic games', 'winter games', 'summer games') + ' AND ' + ERA),
 ('boxing', T('boxing', 'tyson', 'holyfield', 'hagler', 'hearns', 'duran', 'de la hoya', 'foreman', 'lennox lewis', 'bowe', 'whitaker', 'trinidad', 'roy jones', 'title fight', 'heavyweight championship', 'tuesday night fights', 'boxing after dark') + ' AND ' + ERA),
 ('golf tennis', T('masters', 'u.s. open', 'us open', 'pga championship', 'british open', 'ryder cup', 'pga tour', 'skins game', 'wimbledon', 'french open', 'australian open', 'davis cup') + ' AND ' + ERA),
 ('racing', T('indy 500', 'indianapolis 500', 'daytona 500', 'winston cup', 'nascar', 'busch series', 'brickyard 400', 'coca-cola 600', 'talladega', 'indycar', 'kentucky derby', 'preakness', 'belmont stakes', "breeders' cup")),
 ('full games', 'title:("full game" OR "original broadcast" OR "complete game" OR "full broadcast" OR "complete broadcast" OR "with commercials" OR "original commercials" OR woc) AND (title:(football OR basketball OR baseball OR hockey OR boxing OR golf OR tennis OR racing OR nfl OR nba OR mlb OR nhl OR ncaa) OR subject:(football OR basketball OR baseball OR hockey OR sports OR nfl OR nba OR mlb OR nhl OR ncaa))'),
 ('sports subj', 'subject:(nfl OR nba OR mlb OR nhl OR "college football" OR "college basketball" OR sports) AND title:(vs OR versus) AND ' + ERA),
 ('sportscenter', T('sportscenter', 'sports center', 'nfl today', 'nfl live', 'nba on nbc', 'nba on tnt', 'nfl on cbs', 'nfl on fox', 'nfl on nbc')),
 ('late1', T('tonight show', 'johnny carson', 'jay leno')),
 ('late2', T('letterman', 'late show with', 'late night with', 'conan o brien', "conan o'brien")),
 ('late3', T('arsenio hall', 'arsenio', 'saturday night live', 'snl', 'politically incorrect', 'daily show', 'later with', 'bob costas', 'tom snyder', 'late late show', 'craig kilborn')),
 ('netnews', T('world news tonight', 'nightly news', 'evening news', 'headline news', 'election night', 'election coverage') + ' AND ' + NOTV),
 ('cnn', T('cnn') + ' AND ' + ERA + ' AND ' + NOTV),
 ('local news', T('newscast', 'eyewitness news', 'action news', 'newscenter', 'newswatch', 'news at', 'local news', 'late news', 'noon news', 'nightcast', 'newschannel') + ' AND ' + ERA + ' AND ' + NOTV),
 ('news', 'title:(news) AND ' + ERA + ' AND ' + NOTV + ' AND (subject:(news OR newscast OR television OR tv OR vhs OR aircheck OR broadcast) OR collection:(vhsvault OR television OR newsandpublicaffairs OR television_inbox OR sept_11_tv_archive OR 911))'),
 ('specials', T('breaking news', 'special report', 'news coverage', 'live coverage', 'news bulletin', 'news special') + ' AND ' + ERA + ' AND ' + NOTV),
 ('shopping', T('qvc', 'hsn', 'home shopping network', 'home shopping club', 'home shopping', 'shop at home', 'valuevision')),
]
def known():
    have = set()
    for p in glob.glob(os.path.join(OUT, '*.json.gz')):
        if os.path.basename(p) in ('dated.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz'): continue
        try: j = json.load(gzip.open(p, 'rt', encoding='utf-8'))
        except Exception: continue
        if isinstance(j, dict): have |= set(j.keys()); continue
        for x in j:
            if isinstance(x, dict) and x.get('i'): have.add(x['i'])
            elif isinstance(x, list) and x and isinstance(x[0], str): have.add(x[0])
            if isinstance(x, dict) and isinstance(x.get('ia'), list) and x['ia'] and isinstance(x['ia'][0], str): have.add(x['ia'][0])
    return have
def S(v): return ' '.join(str(a) for a in v) if isinstance(v, list) else str(v or '')
if MODE == 'plan':
    have = known()
    if os.path.exists(OUTF): have |= set(x['i'] for x in json.load(gzip.open(OUTF, 'rt', encoding='utf-8')))
    print('known', len(have), 'queries', len(QUERIES), flush=True)
    seen = {}; stat = collections.defaultdict(collections.Counter); nod = collections.defaultdict(list)
    def run(k): return k, scrape(QUERIES[k][1])
    with ThreadPoolExecutor(6) as ex:
        for k, items in ex.map(run, range(len(QUERIES))):
            name = QUERIES[k][0]; stat[name]['raw'] = len(items)
            for it in items:
                i = it['identifier']
                if i in have or i in seen: stat[name]['x_have'] += 1; continue
                lang = S(it.get('language'))
                if lang and not re.search(r'(?i)eng|english|^en\b', lang): continue
                col = it.get('collection') or []
                if isinstance(col, str): col = [col]
                if set(col) & XCOL: continue
                t = S(it.get('title')); desc = ' '.join(re.sub(r'<[^>]+>', ' ', S(it.get('description'))).split())
                c = classify(t, i, S(it.get('date')), desc)
                if not c:
                    if not ok_title(t): stat[name]['x_junk'] += 1
                    elif find_date(t, i, S(it.get('date')), desc)[0]: stat[name]['x_noclass'] += 1
                    elif late(t, '1994-06-18') or sport(t, desc, '1994-06-18') or news(t, t) or shop(t):
                        stat[name]['x_nodate'] += 1
                        if len(nod[name]) < 400: nod[name].append(t[:90] + ' | ' + S(it.get('date'))[:10])
                    continue
                seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0}
                stat[name]['kept'] += 1; stat[name][c['k']] += 1
            print('query', name, dict(stat[name].most_common(8)), 'total', len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    random.seed(3)
    for name in nod:
        for t in random.sample(nod[name], min(10, len(nod[name]))): print('NODATE', name, '|', t)
    cands = sorted(seen.values(), key=lambda x: x['identifier'])
    print('candidates', len(cands), flush=True)
    with gzip.open(os.path.join(PARTS, 'dated_cands.json.gz'), 'wt', encoding='utf-8') as f:
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
REJ = collections.Counter()
def meta(it):
    r = meta1(it)
    if isinstance(r, str): REJ[r] += 1; return None
    return r
def meta1(it):
    if time.time() - T0 > BUDGET: return 'budget'
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return 'dark'
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return 'restricted'
    if str(m.get('mediatype', 'movies')) != 'movies': return 'mediatype'
    lang = S(m.get('language'))
    if lang and not re.search(r'(?i)eng|english|^en\b', lang): return 'lang'
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
    if not files: return 'nomp4'
    files.sort(key=lambda f: f[0])
    title = S(m.get('title'))
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', S(m.get('description'))).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    if set(col) & XCOL: return 'col'
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    blob = (title + ' ' + str(subj) + ' ' + desc[:500]).lower()
    if re.search(X_FOR, blob): return 'foreign'
    if re.search(r'\b(podcast|fan ?film|fan ?made|video ?game|gameplay|radio (show|program|broadcast|call)|audio only|simulation)\b', blob): return 'junk'
    c = classify(title, it['identifier'], S(m.get('date')), desc)
    if not c: return 'noclass'
    tot = sum(f[1] for f in files)
    if tot < c['min']: return 'short_' + c['q']
    if tot > 14 * 3600: return 'long'
    if c['q'] in ('sports', 'late', 'news') and len(files) > 12: return 'manyfiles'
    r = {'i': it['identifier'], 'q': c['q'], 't': title[:200], 'd': S(m.get('date')), 'y': S(m.get('year')), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': c['k'], 'e': int(c['ad'][:4]), 'net': c['net'], 'ct': c['ct'], 'ad': c['ad'], 'as': c['as']}
    if c.get('st'): r['st'] = c['st']
    return r
def keep(x):
    c = classify(x['t'], x['i'], x.get('d'), x.get('ds'))
    if not c: return False
    for a in ('q', 'k', 'net', 'ct', 'ad', 'as'): x[a] = c[a]
    x['e'] = int(c['ad'][:4])
    return sum(f[1] for f in x['f']) >= c['min']
if MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'dated_cands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'dated-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res), 'rejected', REJ.most_common()); sys.exit(0)
if MODE == 'merge':
    old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    old = [x for x in old0 if keep(x)]
    print('refiltered existing', len(old0), '->', len(old))
    have = set(x['i'] for x in old) | known(); add = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'dated-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have: have.add(x['i']); add.append(x)
    res = old + add
    with gzip.open(OUTF, 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    hrs = lambda L: round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
    print('merged old', len(old), 'added', len(add), 'total', len(res), 'hours', hrs(res))
    print('CATEGORY TABLE')
    for q in sorted(set(x['q'] for x in res)):
        L = [x for x in res if x['q'] == q]; print('  %-7s items %5d hours %6d' % (q, len(L), hrs(L)))
    print('TYPE TABLE')
    for t, n in collections.Counter(x['ct'] for x in res).most_common(): print('  %-13s items %5d hours %6d days %5d' % (t, n, hrs([x for x in res if x['ct'] == t]), len(set(x['ad'] for x in res if x['ct'] == t))))
    print('SHOW TABLE')
    for k, n in collections.Counter(x['k'] for x in res).most_common():
        ys = collections.Counter(x['ad'][:4] for x in res if x['k'] == k)
        print('  %5d  %-42s %s' % (n, k, ' '.join('%s:%d' % (y[2:], ys[y]) for y in sorted(ys))))
    WANT = ['SUPER BOWL', 'MONDAY NIGHT FOOTBALL', 'NFL FOOTBALL', 'NBA BASKETBALL', 'NBA FINALS', 'MLB BASEBALL', 'WORLD SERIES', 'NHL HOCKEY', 'STANLEY CUP PLAYOFFS', 'COLLEGE FOOTBALL', 'COLLEGE BASKETBALL', 'OLYMPIC GAMES', 'BOXING', 'GOLF', 'TENNIS', 'AUTO RACING', 'HORSE RACING', 'SPORTSCENTER', 'THE TONIGHT SHOW STARRING JOHNNY CARSON', 'THE TONIGHT SHOW WITH JAY LENO', 'LATE NIGHT WITH DAVID LETTERMAN', 'LATE SHOW WITH DAVID LETTERMAN', "LATE NIGHT WITH CONAN O'BRIEN", 'THE ARSENIO HALL SHOW', 'SATURDAY NIGHT LIVE', 'POLITICALLY INCORRECT', 'THE DAILY SHOW', 'LATER', 'THE LATE LATE SHOW WITH TOM SNYDER', 'THE LATE LATE SHOW WITH CRAIG KILBORN', 'ABC WORLD NEWS TONIGHT', 'NBC NIGHTLY NEWS', 'CBS EVENING NEWS', 'CNN', 'HEADLINE NEWS', 'LOCAL NEWS', 'NEWS SPECIAL REPORT', 'ELECTION NIGHT COVERAGE', 'QVC', 'HOME SHOPPING NETWORK', 'SHOP AT HOME']
    bs = collections.Counter(x['k'] for x in res)
    print('COVERAGE')
    for k in WANT: print('  %-8s %5d  %s' % ('FOUND' if bs[k] >= 20 else 'THIN' if bs[k] else 'MISSING', bs[k], k))
    sb = sorted(set(x['ad'] for x in res if x['k'] == 'SUPER BOWL'))
    print('super bowls found', sb, 'missing', sorted(set(SB.values()) - set(sb)))
    print('YEAR TABLE', sorted(collections.Counter(x['ad'][:4] for x in res).items()))
    print('distinct days', len(set(x['ad'] for x in res)), 'of 7671')
    print('date source', collections.Counter(x['as'] for x in res).most_common())
    print('networks', collections.Counter(x['net'] for x in res).most_common(20))
    random.seed(7)
    for x in random.sample(res, min(80, len(res))): print('SAMPLE', x['ct'], '|', x['k'], '|', x['ad'], x['as'], '|', x['net'], '|', x['t'][:80], '|', x['i'][:36], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files')
