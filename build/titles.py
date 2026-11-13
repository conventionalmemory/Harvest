import re, os
here = os.path.dirname(os.path.abspath(__file__))
DISPLAY = {'a-team': 'THE A-TEAM', 'the a team': 'THE A-TEAM', 'a team': 'THE A-TEAM', 'magnum': 'MAGNUM, P.I.', 'magnum, p.i.': 'MAGNUM, P.I.', 'magnum p.i.': 'MAGNUM, P.I.', 'cosby show': 'THE COSBY SHOW', 'murder, she wrote': 'MURDER, SHE WROTE', 'murder she wrote': 'MURDER, SHE WROTE', 'simpsons': 'THE SIMPSONS', 'x-files': 'THE X-FILES', 'the x-files': 'THE X-FILES', 'next generation': 'STAR TREK: THE NEXT GENERATION', 'star trek: the next generation': 'STAR TREK: THE NEXT GENERATION', 'deep space nine': 'STAR TREK: DEEP SPACE NINE', 'voyager': 'STAR TREK: VOYAGER', 'star trek: voyager': 'STAR TREK: VOYAGER', 'beverly hills, 90210': 'BEVERLY HILLS, 90210', 'beverly hills 90210': 'BEVERLY HILLS, 90210', '90210': 'BEVERLY HILLS, 90210', 'married with children': 'MARRIED... WITH CHILDREN', 'married... with children': 'MARRIED... WITH CHILDREN', 'price is right': 'THE PRICE IS RIGHT', 'the price is right': 'THE PRICE IS RIGHT', 'jeopardy': 'JEOPARDY!', 'wheel of fortune': 'WHEEL OF FORTUNE', 'family feud': 'FAMILY FEUD', 'young and the restless': 'THE YOUNG AND THE RESTLESS', 'bold and the beautiful': 'THE BOLD AND THE BEAUTIFUL', 'days of our lives': 'DAYS OF OUR LIVES', 'golden girls': 'THE GOLDEN GIRLS', 'wonder years': 'THE WONDER YEARS', 'fresh prince': 'THE FRESH PRINCE OF BEL-AIR', 'fresh prince of bel-air': 'THE FRESH PRINCE OF BEL-AIR', 'oprah': 'THE OPRAH WINFREY SHOW', 'tonight show': 'THE TONIGHT SHOW', 'today show': 'TODAY', 'the today show': 'TODAY', 'snl': 'SATURDAY NIGHT LIVE', 'saturday night live': 'SATURDAY NIGHT LIVE', 'tmnt': 'TEENAGE MUTANT NINJA TURTLES', 'ninja turtles': 'TEENAGE MUTANT NINJA TURTLES', 'teenage mutant ninja turtles': 'TEENAGE MUTANT NINJA TURTLES', 'he-man': 'HE-MAN AND THE MASTERS OF THE UNIVERSE', 'he man': 'HE-MAN AND THE MASTERS OF THE UNIVERSE', 'transformers': 'THE TRANSFORMERS', 'smurfs': 'THE SMURFS', 'real ghostbusters': 'THE REAL GHOSTBUSTERS', 'muppet babies': "JIM HENSON'S MUPPET BABIES", 'ducktales': 'DUCKTALES', 'rescue rangers': "CHIP 'N DALE RESCUE RANGERS", 'tiny toon': 'TINY TOON ADVENTURES', 'x-men': 'X-MEN', 'power rangers': 'MIGHTY MORPHIN POWER RANGERS', 'mighty morphin': 'MIGHTY MORPHIN POWER RANGERS', "pee-wee's playhouse": "PEE-WEE'S PLAYHOUSE", 'saved by the bell': 'SAVED BY THE BELL', 'full house': 'FULL HOUSE', 'family matters': 'FAMILY MATTERS', 'home improvement': 'HOME IMPROVEMENT', "america's funniest": "AMERICA'S FUNNIEST HOME VIDEOS", "america's funniest home videos": "AMERICA'S FUNNIEST HOME VIDEOS", 'unsolved mysteries': 'UNSOLVED MYSTERIES', 'knight rider': 'KNIGHT RIDER', 'miami vice': 'MIAMI VICE', 'cheers': 'CHEERS', 'seinfeld': 'SEINFELD', 'frasier': 'FRASIER', 'friends': 'FRIENDS', 'dallas': 'DALLAS', 'dynasty': 'DYNASTY', 'night court': 'NIGHT COURT', 'growing pains': 'GROWING PAINS', "who's the boss": "WHO'S THE BOSS?", 'family ties': 'FAMILY TIES', 'perfect strangers': 'PERFECT STRANGERS', 'murphy brown': 'MURPHY BROWN', 'designing women': 'DESIGNING WOMEN', 'late night with david letterman': 'LATE NIGHT WITH DAVID LETTERMAN', 'late show with david letterman': 'LATE SHOW WITH DAVID LETTERMAN', 'arsenio': 'THE ARSENIO HALL SHOW', 'arsenio hall': 'THE ARSENIO HALL SHOW', 'nightline': 'NIGHTLINE', '20/20': '20/20', '60 minutes': '60 MINUTES', 'entertainment tonight': 'ENTERTAINMENT TONIGHT', 'a current affair': 'A CURRENT AFFAIR', 'inside edition': 'INSIDE EDITION', 'hard copy': 'HARD COPY', 'soul train': 'SOUL TRAIN', 'friday night videos': 'FRIDAY NIGHT VIDEOS', 'yo! mtv raps': 'YO! MTV RAPS', 'headbangers ball': "HEADBANGERS BALL", '120 minutes': '120 MINUTES', 'night tracks': 'NIGHT TRACKS', 'pm magazine': 'PM MAGAZINE', 'hour magazine': 'HOUR MAGAZINE', 'star search': 'STAR SEARCH', 'sesame street': 'SESAME STREET', 'mister rogers': "MISTER ROGERS' NEIGHBORHOOD", 'mr. rogers': "MISTER ROGERS' NEIGHBORHOOD", 'reading rainbow': 'READING RAINBOW', '3-2-1 contact': '3-2-1 CONTACT', 'double dare': 'DOUBLE DARE', 'charlie rose': 'CHARLIE ROSE', 'nova': 'NOVA', 'frontline': 'FRONTLINE', 'nature': 'NATURE', 'austin city limits': 'AUSTIN CITY LIMITS', 'this old house': 'THIS OLD HOUSE', 'joy of painting': 'THE JOY OF PAINTING', 'bob ross': 'THE JOY OF PAINTING', 'new yankee workshop': 'THE NEW YANKEE WORKSHOP', 'frugal gourmet': 'THE FRUGAL GOURMET', 'great chefs': 'GREAT CHEFS', 'yan can cook': 'YAN CAN COOK', 'computer chronicles': 'THE COMPUTER CHRONICLES', 'screen savers': 'THE SCREEN SAVERS', 'screensavers': 'THE SCREEN SAVERS', 'video power': 'VIDEO POWER', 'gamespot': 'GAMESPOT TV', 'x-play': 'X-PLAY', 'xplay': 'X-PLAY', 'attack of the show': 'ATTACK OF THE SHOW!', 'nick arcade': 'NICK ARCADE', 'macneil/lehrer': 'THE MACNEIL/LEHRER NEWSHOUR', 'newshour': 'THE NEWSHOUR', 'larry king live': 'LARRY KING LIVE', 'crossfire': 'CROSSFIRE', 'good morning america': 'GOOD MORNING AMERICA', 'cbs this morning': 'CBS THIS MORNING', 'nbc nightly news': 'NBC NIGHTLY NEWS', 'cbs evening news': 'CBS EVENING NEWS', 'world news tonight': 'ABC WORLD NEWS TONIGHT', 'abc world news': 'ABC WORLD NEWS', 'world news saturday': 'ABC WORLD NEWS SATURDAY', 'world news sunday': 'ABC WORLD NEWS SUNDAY', 'abc world news tonight': 'ABC WORLD NEWS TONIGHT', 'headline news': 'HEADLINE NEWS', 'dateline': 'DATELINE NBC', '48 hours': '48 HOURS', 'primetime live': 'PRIMETIME LIVE', 'meet the press': 'MEET THE PRESS', 'face the nation': 'FACE THE NATION', "macy's thanksgiving": "MACY'S THANKSGIVING DAY PARADE", 'v the series': 'V', 'the cosby': 'THE COSBY SHOW', 'donahue': 'DONAHUE', 'geraldo': 'GERALDO', 'later with': 'LATER WITH BOB COSTAS', 'kids of degrassi street': 'THE KIDS OF DEGRASSI STREET', 'degrassi junior high': 'DEGRASSI JUNIOR HIGH', 'degrassi jr high': 'DEGRASSI JUNIOR HIGH', 'degrassi high': 'DEGRASSI HIGH', 'all dogs go to heaven': 'ALL DOGS GO TO HEAVEN', 'montel': 'THE MONTEL WILLIAMS SHOW', 'maury': 'MAURY', 'jenny jones': 'THE JENNY JONES SHOW', 'rosie o\'donnell': "THE ROSIE O'DONNELL SHOW", 'merv griffin': 'THE MERV GRIFFIN SHOW', 'joan rivers': 'THE JOAN RIVERS SHOW', 'morton downey': 'THE MORTON DOWNEY JR. SHOW', 'pat sajak show': 'THE PAT SAJAK SHOW', 'arsenio hall': 'THE ARSENIO HALL SHOW', 'love connection': 'LOVE CONNECTION', 'hollywood squares': 'HOLLYWOOD SQUARES', 'card sharks': 'CARD SHARKS', 'press your luck': 'PRESS YOUR LUCK', 'super password': 'SUPER PASSWORD', 'sale of the century': 'SALE OF THE CENTURY', 'newlywed game': 'THE NEWLYWED GAME', 'dating game': 'THE DATING GAME', 'joker\'s wild': "THE JOKER'S WILD", '25,000 pyramid': 'THE $25,000 PYRAMID', '100,000 pyramid': 'THE $100,000 PYRAMID', 'where in the world is carmen': 'WHERE IN THE WORLD IS CARMEN SANDIEGO?', 'who wants to be a millionaire': 'WHO WANTS TO BE A MILLIONAIRE', 'general hospital': 'GENERAL HOSPITAL', 'edge of night': 'THE EDGE OF NIGHT', 'guiding light': 'GUIDING LIGHT', 'another world': 'ANOTHER WORLD', 'all my children': 'ALL MY CHILDREN', 'one life to live': 'ONE LIFE TO LIVE', 'as the world turns': 'AS THE WORLD TURNS', 'santa barbara': 'SANTA BARBARA', 'star trek': 'STAR TREK', 'buffy': 'BUFFY THE VAMPIRE SLAYER', 'buffy the vampire': 'BUFFY THE VAMPIRE SLAYER', 'whose line': 'WHOSE LINE IS IT ANYWAY?', 'siskel': 'SISKEL & EBERT', 'scooby': 'SCOOBY-DOO', 'super mario bros': 'THE SUPER MARIO BROS. SUPER SHOW!', 'bill nye': 'BILL NYE THE SCIENCE GUY', 'garfield': 'GARFIELD AND FRIENDS', 'care bears': 'THE CARE BEARS', 'magic school bus': 'THE MAGIC SCHOOL BUS', 'blue\'s clues': "BLUE'S CLUES", 'snick': 'SNICK', 'dinosaurs': 'DINOSAURS', 'sally jessy': 'SALLY JESSY RAPHAEL', 'jerry springer': 'THE JERRY SPRINGER SHOW', 'ricki lake': 'RICKI LAKE', 'live with regis': 'LIVE WITH REGIS AND KATHIE LEE', 'regis & kathie': 'LIVE WITH REGIS AND KATHIE LEE'}
WREST = [('wrestlemania', None), ('summerslam', None), ('royal rumble', None), ('survivor series', None), ('starrcade', None), ('great american bash', None), ('halloween havoc', None), ('clash of the champions', None), ("saturday night's main event", "SATURDAY NIGHT'S MAIN EVENT"), ('monday night raw', 'WWF MONDAY NIGHT RAW'), ('raw is war', 'WWF RAW IS WAR'), ('nitro', 'WCW MONDAY NITRO'), ('thunder', 'WCW THUNDER'), ('smackdown', 'WWF SMACKDOWN!'), ('superstars', 'WWF SUPERSTARS OF WRESTLING'), ('wrestling challenge', 'WWF WRESTLING CHALLENGE'), ('prime time wrestling', 'PRIME TIME WRESTLING'), ('all american wrestling', 'ALL AMERICAN WRESTLING'), ('wcw saturday night', 'WCW SATURDAY NIGHT'), ('worldwide', 'WCW WORLDWIDE'), ('world championship wrestling', 'WORLD CHAMPIONSHIP WRESTLING'), ('georgia championship', 'GEORGIA CHAMPIONSHIP WRESTLING'), ('world class', 'WORLD CLASS CHAMPIONSHIP WRESTLING'), ('awa', 'AWA ALL-STAR WRESTLING'), ('glow', 'G.L.O.W.'), ('gorgeous ladies', 'G.L.O.W.'), ('ecw', 'ECW HARDCORE TV'), ('heat', 'WWF SUNDAY NIGHT HEAT'), ('tuesday night titans', 'TUESDAY NIGHT TITANS'), ('velocity', 'WWE VELOCITY'), ('championship wrestling', 'CHAMPIONSHIP WRESTLING'), ('wwe', 'WWE WRESTLING'), ('wwf', 'WWF WRESTLING'), ('wcw', 'WCW WRESTLING'), ('nwa', 'NWA WRESTLING')]
def _simple(a):
    a = a.replace('\\.', '.').replace(',?', ',').replace('\\b', '').replace("'?", "'").strip()
    if re.search(r'[\\\[\]\(\)\?\*\+\^\$\{\}|]', a) or len(a) < 3: return None
    return a
NAMES = {}
def _add(n):
    n = n.strip().lower()
    if not n or len(n) < 3: return
    NAMES.setdefault(n, DISPLAY.get(n, n.upper()))
try:
    from netmap import NETMAP
    for v in NETMAP.values():
        for a in v.split('|'):
            s = _simple(a)
            if s: _add(s)
except Exception:
    pass
QF = os.path.join(here, '..', 'harvest', 'queries2.txt')
if os.path.exists(QF):
    for line in open(QF):
        if '|' in line and not line.startswith(('yr', 'col_', 'movie|', 'weather|')):
            for q in re.findall(r'"([^"]+)"', line): _add(q)
for k in DISPLAY: _add(k)
SHORTOK = {'seinfeld', 'frasier', 'roseanne', 'matlock', 'macgyver', 'airwolf', 'baywatch', 'newhart', 'columbo', 'jeopardy'}
JUNK = re.compile(r"(?i)\b(blank vhs tape|blank|vhs tape\s*\d*|vhs lp|vhs sp|vhs ep|vhs|dvd(-\d+)?|lp|beta(max)?(\s*\d+)?|dvd transfer\s*\d*|transfer\s*\d+|tape\s*\d+(\s*of\s*\d+)?|\d+\s*of\s*\d+|recording|recorded|aircheck|broadcasts?|off[- ]air|with (original )?commercials|w/? ?commercials|commercials|w\.?o\.?c\.?|woc|w/o/c|full episode|full show|\d+ episodes|episodes?|partial|incomplete|complete|original|rips?|iso|ntsc|sd|hd|\d{3,4}p|\d+ ?hrs?|\d+ ?hours?|series|season \d+|s\d+\s*e\d+|\d+x\d+|part \d+|pt\.? ?\d+|disc \d+|random tv|multirecording|footage|unknown|misc|various|block|marathon|edit|upload|source|capture|captured|raw|dub|copy|cable|channel \d+|ch\.? ?\d+)\b")
CALL = re.compile(r'\b[wk][a-z]{2,3}(-?tv|-dt)?(\s*\d{1,2})?\b')
NETW = re.compile(r'\b(nbc|cbs|abc|fox|pbs|hbo|tbs|wtbs|tnt|usa network|usa|mtv|vh-?1|cnn|espn|cinemax|showtime|nick(elodeon)?|disney channel|cartoon network|the box|bet|cmt|tnn|lifetime|a&e|amc|wgn|wor|wpix|upn|wb)\b', re.I)
MONTHS = r'(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)'
DATE = re.compile(r'\b(' + MONTHS + r'\.?\s*\d{1,2}(st|nd|rd|th)?(\s*[-–]\s*\d{1,2})?,?(\s+(19|20)\d\d)?|\d{1,2}(st|nd|rd|th)?\s+' + MONTHS + r'\.?(\s+(19|20)\d\d)?|' + MONTHS + r'\.?,?\s+(19|20)\d\d|(19|20)\d\d\s\d{1,2}\s\d{1,2}|\d{1,4}[./-]\d{1,2}([./-]\d{1,4})?|(19[89]\d|200[0-4]))\b', re.I)
def _clean(s):
    s = re.sub(r'\[[^\]]*\]|\{[^}]*\}|\([^)]*\)', ' ', s)
    s = re.sub(r'[\[\(\{][^\]\)\}]*$', ' ', s)
    s = re.sub(r'(?i)^\s*(cl[a-z]{1,3}\d{3,5}|cc\d{4,6}|ctcn\d{3,5}|ccl\d{3}-\d{2}|[a-z]{2,6}\d{3,6})\s*-\s*', ' ', s)
    s = DATE.sub(' ', s)
    s = JUNK.sub(' ', s)
    s = re.sub(r'[_|•~#*"“”©®™]+', ' ', s)
    s = re.sub(r'(\.\s*){2,}', ' ', s)
    s = re.sub(r'(?i)\b(fantasy |tv )?sit-?com\b.*$|\bblu-?ray\b|\bvhsrip\b|\bep\.?\s*\d+\b|\be\d{1,3}\b', ' ', s)
    s = re.sub(r"(^|\s)'+|'+(\s|$)", ' ', s)
    s = re.sub(r'\s*[-–:;,&/.]+\s*$', '', s)
    s = re.sub(r'^\s*[-–:;,&/.]+\s*', '', s)
    s = re.sub(r'\s+[-–]\s+(?=[-–])', ' ', s)
    s = re.sub(r'(?i)[\s,/-]+\b[wk][a-z]{2,3}(-tv)?(\s*-?\d{1,2})?\s*$', '', re.sub(r'\s+', ' ', s).strip())
    return re.sub(r'\s+', ' ', s).strip(' -–:,.;&/')
def _strip_front(s):
    for _ in range(5):
        s2 = re.sub(r'(?i)^\s*(' + CALL.pattern + r'|' + NETW.pattern + r'|\d{1,3})\s*[-–:,]*\s*', '', s)
        if s2 == s: break
        s = s2
    return s.strip(' -–:,.;&/')
def _cut(s, n=40):
    s = s.strip()
    if len(s) > n: s = s[:n].rsplit(' ', 1)[0]
    s = re.sub(r'(?i)(^|[\s,:;-]+)\b(part|pt|vol|volume|no|the|two part|two-part|min|mini|miniseries|and|with|of|a|an)\.?\s*$', '', s)
    return s.strip(' -–:,.;&')
def _episode(rest):
    m = re.search(r'["“]([^"”]{3,40})["”]', rest)
    e = m.group(1) if m else ''
    if not e:
        m = re.match(r'^\s*(?:s\d+\s*e\d+|\d+x\d+|#?\d{1,4})?\s*[-–:]\s*(.+)$', rest, re.I)
        if m: e = m.group(1)
    e = _clean(e)
    e = re.split(r'\s+[-–|]\s+|,\s', e)[0] if e else ''
    if re.search(r'(?i)\b(commercial|tape|vhs|news|promo|bumper|with|w/)\b', e) or not re.search(r'[a-z]{3}', e, re.I): return ''
    if re.search(r'\d', e) or re.search(r'(?i)\b(airing|season|premiere|finale|series|syndicat|rerun|cast|starring)\b', e): return ''
    return e.upper() if 3 <= len(e) <= 28 else ''
def find_show(low, loose=False):
    for m in NRX.finditer(low):
        k = m.group(1)
        if ' ' not in k and k not in SHORTOK and not (loose and len(k) > 5):
            core = _strip_front(_clean(low))
            if not core.startswith(k) and not core.startswith('the ' + k): continue
        return k, m.end()
    return None, 0
def news_title(low):
    for k in ('nbc nightly news', 'cbs evening news', 'abc world news tonight', 'world news tonight', 'abc world news', 'world news saturday', 'world news sunday', 'headline news', 'nightline', '20/20', '60 minutes', '48 hours', 'dateline', 'primetime live', 'larry king live', 'crossfire', 'macneil/lehrer', 'newshour', 'meet the press', 'face the nation', 'good morning america', 'cbs this morning', 'today show', 'early today', 'world news now', 'nightwatch'):
        if k in low: return DISPLAY.get(k, k.upper())
    sp = re.search(r'\b(special report|special coverage|election|inaugura|coverage|bulletin|breaking|declar|war\b|attack|address|speech|crisis|shuttle|explosion|9/11|september 11|earthquake|hurricane|verdict|funeral|remembers)', low)
    if re.search(r'\bcnn\b', low): return 'HEADLINE NEWS' if 'headline' in low else 'CNN SPECIAL REPORT' if sp else 'CNN NEWS'
    for nw in ('nbc', 'cbs', 'abc'):
        if sp and re.search(r'\b' + nw + r' news\b', low): return nw.upper() + ' NEWS SPECIAL REPORT'
    m = re.search(r'\b(\d{1,2})\s*(?::\d\d)?\s*(pm|p\.m\.|am|a\.m\.|o\'?clock)\b', low) or re.search(r'news at (\d{1,2})\b', low)
    h = m.group(1) if m else ''
    brand = 'EYEWITNESS NEWS' if 'eyewitness' in low else 'ACTION NEWS' if 'action news' in low else 'NEWSCENTER' if 'newscenter' in low else 'NEWS'
    if re.search(r'\b(morning|sunrise|daybreak|good morning)\b', low) and not h: return brand + ' THIS MORNING' if brand == 'NEWS' else brand
    if h and h in ('5', '6', '10', '11', '12', '4'): return brand + ' AT ' + h
    if re.search(r'\b(special report|election|inauguration|coverage|bulletin|breaking)\b', low): return 'SPECIAL REPORT'
    return brand
CHN = {'CARTOON NETWORK', 'NICKELODEON', 'DISNEY CHANNEL', 'THE DISNEY CHANNEL', 'FOX KIDS', 'TOON DISNEY', 'NICK JR', 'NICK JR.', 'KIDS WB', "KIDS' WB", 'USA NETWORK', 'COMEDY CENTRAL', 'LIFETIME', 'TNT', 'TBS', 'HBO', 'SHOWTIME', 'CINEMAX', 'MTV', 'VH1', 'A&E', 'AMC', 'SCI-FI CHANNEL', 'SCI FI CHANNEL', 'NICK AT NITE', 'ABC', 'CBS', 'NBC', 'FOX', 'PBS', 'SATURDAY MORNING CARTOONS', 'SATURDAY MORNING', 'AFTERNOON CARTOONS', 'CABLE', 'TELEVISION', 'TV', 'NETWORK', 'PROMOS', 'COMMERCIALS', 'MOVIE', 'SUNDAY NIGHT MOVIE', 'SUNDAY MOVIE', 'CBS SATURDAY MORNING', 'NBC SATURDAY MORNING', 'ABC SATURDAY MORNING', 'CBS SATURDAY CARTOONS', 'FOX KIDS SATURDAY', 'THE BOX', 'BET', 'TNN', 'CMT', 'WGN', 'WTBS', 'SUPERSTATION'}
for _k in [k for k, v in NAMES.items() if v in CHN or k in ('up all night', 'night flight', 'the box', 'much music', 'vj', 'saturday morning cartoons', 'kids wb', "kids' wb", 'nick jr', 'tnbc', 'snick', 'one saturday morning', 'disney afternoon', 'usa cartoon express', 'cartoon express', 'nick at nite', 'dic', 'filmation', 'rankin', 'jim henson', 'muppet', 'kidsongs', 'peanuts', 'looney tunes', 'bugs bunny')]:
    NAMES.pop(_k, None)
for _k in ('dinosaurs', 'angel', 'hunter', 'martin', 'coach', 'wings', 'ellen', 'amen', 'taxi', 'soap', 'hotel', 'fame', 'sisters', 'nurses', 'legacy', 'popular', 'felicity', 'charmed', 'enterprise', 'friends', 'cops', 'cosby', 'eve', 'ink', 'roc', 'lost', 'duet', 'go', 'debt', 'greed', 'monsters', 'thunder', 'heat', 'nature', 'nova'):
    NAMES.pop(_k, None)
NLIST = sorted(NAMES.items(), key=lambda x: -len(x[0]))
NRX = re.compile(r'(?<![a-z0-9])(' + '|'.join(re.escape(k) for k, _ in NLIST) + r')(?![a-z0-9])')
def std_title(cat, t, late_show=False):
    low = (t or '').lower()
    low = low.replace('&amp;', '&').replace('’', "'").replace('‘', "'")
    if cat == 'news':
        k0, _ = find_show(low)
        if k0 and not re.search(r'\bnews\b', low): return NAMES[k0]
        if not re.search(r'\b(cnn|news|report|tonight|nightline|20/20|minutes|hours|dateline|crossfire|morning|today)\b', low):
            c = _cut(_strip_front(_clean(t)).upper(), 36)
            return c or 'NEWS'
        return news_title(low)
    if cat == 'wrest':
        for k, v in WREST:
            if re.search(r'(?<![a-z])' + re.escape(k) + r'(?![a-z])', low):
                if v: return v
                m = re.search(re.escape(k) + r'\s*(\d{1,2}|[ivx]{1,5}|\d{4})?', low)
                return (k.upper() + (' ' + m.group(1).upper() if m and m.group(1) else '')).strip()
        return 'PRO WRESTLING'
    if cat == 'late' or re.search(r'\b(letterman|leno|carson|conan|arsenio)\b', low):
        for k2, v2 in (('conan', "LATE NIGHT WITH CONAN O'BRIEN"), ('leno', 'THE TONIGHT SHOW WITH JAY LENO'), ('carson', 'THE TONIGHT SHOW STARRING JOHNNY CARSON'), ('arsenio', 'THE ARSENIO HALL SHOW'), ('letterman', 'LATE NIGHT WITH DAVID LETTERMAN'), ('kilborn', 'THE LATE LATE SHOW WITH CRAIG KILBORN'), ('snyder', 'THE LATE LATE SHOW WITH TOM SNYDER'), ('saturday night live', 'SATURDAY NIGHT LIVE'), ('snl', 'SATURDAY NIGHT LIVE'), ('tonight show', 'THE TONIGHT SHOW'), ('mad tv', 'MADTV'), ('politically incorrect', 'POLITICALLY INCORRECT'), ('nightline', 'NIGHTLINE')):
            if re.search(r'(?<![a-z])' + k2 + r'(?![a-z])', low):
                if k2 == 'letterman' and (late_show or 'late show' in low): return 'LATE SHOW WITH DAVID LETTERMAN'
                return v2
    k, end = find_show(low, cat in ('talk', 'late', 'game', 'soap', 'mag', 'morning'))
    if k:
        name = NAMES[k]
        ep = _episode(low[end:]) if cat not in ('news', 'music', 'late', 'talk', 'game', 'morning', 'mag') else ''
        if ep and ep.lower() != k and not ep.lower().startswith(k): return _cut(name + ': ' + ep, 44)
        return name
    c = _strip_front(_clean(t))
    c = re.split(r'\s+[-–|]\s+', c)[0] if re.search(r'\s[-–|]\s', c) and len(c) > 26 else c
    if cat == 'movie': c = re.sub(r'(?i)\b(upn|wb|fox|abc|cbs|nbc|tbs|wtbs|tnt|hbo|usa|amc|tmc|cinemax|showtime)\s?\d{0,2}\b|\b[wk][a-z]{2,3}(-tv)?\s?\d{0,2}\b(?=\s*$)|\b(an )?(abc|cbs|nbc) novel for television\b', ' ', c)
    c = _cut(c.upper(), 40)
    if cat == 'music' and len(c) < 10: return 'MUSIC VIDEOS'
    if cat == 'music' and (not c or len(c) < 4 or re.search(r'(?i)\b(mtv|vh-?1|videos?)\b', c) and len(c) < 12): return 'MUSIC VIDEOS'
    if cat == 'kids' and (not c or len(c) < 4 or re.search(r'(?i)^(saturday morning|cartoons?|afternoon cartoons)', c)): return 'CARTOONS'
    if cat == 'movie': c = re.sub(r'(?i)\b((abc|cbs|nbc|fox|tbs|tnt|usa)\s+)?(sunday|monday|tuesday|wednesday|thursday|friday|saturday)\s+(night\s+)?(at the\s+)?movies?\b|\b(abc|cbs|nbc|fox)\s+movie( of the week)?\b|\btv movie\b|\bfull movie\b|\bminiseries\b', ' ', c)
    c = re.sub(r'\s+', ' ', c).strip(' -–:,.;&')
    if c in CHN: c = ''
    if not c or len(c) < 3: return {'kids': 'CARTOONS', 'music': 'MUSIC VIDEOS', 'movie': 'MOVIE', 'game': 'GAME SHOW', 'talk': 'TALK SHOW', 'late': 'LATE NIGHT', 'access': 'COMMUNITY CALENDAR', 'pub': 'PUBLIC AFFAIRS'}.get(cat, 'SPECIAL')
    return c
