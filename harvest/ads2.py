import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '24'))
BUDGET = float(os.environ.get('BUDGET_MIN', '200')) * 60
MAXC = int(os.environ.get('MAXC', '260000'))
MODE = os.environ.get('MODE', 'all')
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
CF = os.path.join(PARTS, 'ads2_cands.json.gz')
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
NETS = ['nbc', 'cbs', 'abc', 'fox', 'upn', '"the wb"', '"kids wb"', '"fox kids"', 'pbs', 'nickelodeon', '"nick at nite"', '"nick jr"', 'snick', 'mtv', 'vh1', '"cartoon network"', 'toonami', '"adult swim"', '"disney channel"', '"toon disney"', 'usa', 'tbs', 'tnt', 'wgn', 'hbo', 'showtime', 'cinemax', 'espn', 'cnn', 'tnn', 'lifetime', '"comedy central"', '"sci-fi channel"', '"family channel"', '"fox family"', 'discovery', 'tlc', 'bet', '"the box"', '"weather channel"', 'amc', 'tcm', '"tv land"', 'boomerang', 'noggin', 'zdtv', 'techtv', 'g4']
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
MODW = re.compile(r"\b(covid|coronavirus|pandemic|vaping|vape|iphone|ipad|android|smartphone|podcast|zoom|facebook|twitter|instagram|tiktok|youtube channel|livestream|webinar|4k|1080p|uhd|streaming|netflix|hulu|obamacare|bitcoin|crypto|uber|lyft|hashtag|selfie|drone|census 20\d\d|fentanyl|opioid|e-cig|face mask|social distanc|vaccin)\b|#\w", re.I)
RETRO = re.compile(r"\b(vhs|betamax|80'?s|90'?s|eighties|nineties|retro|vintage|classic|old school|aircheck|off[- ]air|[wk][a-z]{2,3}-tv|[wk][a-z]{3} ?\d{1,2})\b", re.I)
ADT = re.compile(r'\b(commercials?|ads?|adverts?|advertisements?|tv spots?|spots?|promos?|bumpers?|psa|idents?|station id)\b', re.I)
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
YR = re.compile(r'(?<![\d$#])(198[4-9]|199\d|200[0-4])(?!\d)')
NONUS = re.compile(r'\((jp|uk|eu|pal|au|de|fr|es|it|br|kr)\)|\b(japan|japanese|emirates|boston pizza|tim hortons|canadian tire|jamaica|d&g|philippines|pinoy|india|bollywood)\b', re.I)
def when(title, desc, date, year):
    t = title + ' '
    y = None; src = ''
    m = YR.search(t)
    if m: y = int(m.group(1)); src = 't'
    if not y:
        m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](8[4-9]|9\d|0[0-4])(?!\d)', t)
        if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31: y = int(('19' if m.group(3) >= '84' else '20') + m.group(3)); src = 't'
    if not y:
        m = YR.search(desc[:240])
        if m and not re.search(r'(upload|posted|digitiz|transfer|captur|rip)\w* (on|in)? ?' + m.group(1), desc[:240], re.I): y = int(m.group(1)); src = 'd'
    if not y:
        for v in (date, year):
            m = re.match(r'(198[4-9]|199\d|200[0-4])', str(v or ''))
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
        m = re.search(r'(?<!\d)' + str(y) + r'[-_.](0[1-9]|1[0-2])[-_.](\d\d)(?!\d)', blob)
        if m: mo = int(m.group(1))
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
Y8 = ' OR '.join(str(y) for y in range(1984, 1992)); Y9 = ' OR '.join(str(y) for y in range(1992, 2005)); YE = ' OR '.join(str(y) for y in range(1984, 1988))
NETQ = ' OR '.join(NETS)
CALLS = 'wabc wnbc wcbs wpix wnyw wwor wnet wgn wls wmaq wbbm wfld wttw wpwr ktla kabc knbc kcbs kttv kcal kcop kcet kron kpix kgo ktvu kbhk wsb wxia wagg wtbs wjla wusa wttg wrc wdca kdka wtae wpxi wpvi kyw wcau wphl wtxf wbz wcvb whdh wsbk wlvi wfsb wvit wtnh wjz wbal wmar wbff wkyc wews wjw wuab wxyz wdiv wjbk wkbd kstp wcco kare kmsp ktvi ksdk kmov kplr wtvj wplg wsvn wfor wtvt wfla wtsp wesh wftv wkmg kxas wfaa kdfw ktvt khou kprc ktrk kriv king komo kiro kcpq kusa kmgh kcnc kwgn kpnx ktvk ksaz kutv ksl ktvx kgw koin katu kptv kfmb kgtv knsd wral wtvd wbtv wsoc wcnc wlwt wcpo wkrc wxix wbns wcmh wsyx wish wthr wrtv wttv wtmj wisn witi wdaf kctv kmbc kshb wdsu wwl wvue wsmv wtvf wkrn wreg wmc whbq wave whas wlky wivb wgrz wkbw wten wrgb wnyt whec wokr wham wstm wtvh wixt wnep wbre wgal whp wpmt wtkr wavy wvec wtvr wric wwbt wfmy wghp wxii wyff wspa wlos wis wltx wcsc wciv wtoc wsav wjxt wtlv wala wkrg wbrc wvtm wsfa waff waay wlbt wjtv kark katv kthv kfor kwtv koco kotv ktul kjrh ksat kens kmol kvue ktbc kxan kvia kdbc kob koat krqe kvoa kgun kold klas kvbc ktnv kolo krnv ktvn kxtv kcra kovr ktxl kfsn kjeo kmph kero kget ksby keyt ksbw kntv kicu khq krem kxly kboi ktvb kivi ktvq kulr kxmc kfyr kelo ksfy kwwl kcrg who kcci woi ketv wowt kmtv kake kwch ksnw wibw ktka kode koam kytv kolr wand wics wcia week whoi wmbd wqad whbf kwqc wkow wmtv wisc wbay wfrv wluk wood wotv wzzm wwmt wjrt wnem wlns wilx wtol wtvg wdtn whio wkef wane wpta wkjg wndu wsbt wsjv wfie wtvw wehp wpsd wsil kfvs wlex wkyt wtvq wsaz wowk wchs wtrf wtov wdtv wboy wjac wtaj wicu wjet wsee wgme wcsh wmtw wlbz wabi wcax wptz wvny wmur wjar wpri wlne wggb wwlp wtic'.split()
QX = [
 ('promo', 'title:(promo OR promos OR "fall preview" OR "fall campaign" OR "fall lineup" OR "image campaign" OR "network promo" OR "tv promo" OR "tv promos" OR "program promo" OR "show promo" OR "movie promo" OR "sneak preview" OR "fall season" OR "new season") AND title:(' + Y8 + ')'),
 ('promo', 'title:(' + NETQ + ') AND title:(' + Y8 + ') AND title:(promo OR promos OR preview OR lineup OR "coming up" OR tonight OR "special presentation" OR campaign OR jingle OR premiere OR "this week" OR "next week" OR saturday OR sunday OR friday OR thursday OR wednesday OR tuesday OR monday OR movie)'),
 ('bumper', 'title:(' + NETQ + ') AND title:(' + Y8 + ') AND title:(bumper OR bumpers OR ident OR idents OR id OR ids OR intro OR open OR opening OR logo OR "station break" OR interstitial OR "be right back" OR "up next" OR "top of the hour")'),
 ('bumper', 'title:(bumper OR bumpers OR ident OR idents OR interstitial OR interstitials OR "network id" OR "network ids" OR "network ident") AND title:(' + Y8 + ' OR "80s" OR "1980s" OR eighties)'),
 ('promo', 'title:(' + NETQ + ') AND title:(' + Y9 + ') AND title:(promo OR promos OR "fall preview" OR lineup OR "coming up" OR "special presentation" OR campaign OR "this week on" OR "next week on" OR "tonight on")'),
 ('bumper', 'title:(' + NETQ + ') AND title:(' + Y9 + ') AND title:(bumper OR bumpers OR ident OR idents OR ids OR "station break" OR interstitial OR "be right back" OR "up next")'),
 ('promo', 'title:(promo OR promos OR bumper OR bumpers OR ident OR idents) AND title:("80s" OR "1980s" OR eighties OR "90s" OR "1990s" OR nineties OR vhs OR aircheck OR "off air" OR "off-air")'),
 ('promo', 'subject:("promos" OR "tv promos" OR "network promos" OR "television promos" OR "promo" OR "bumpers" OR "bumper" OR "tv bumpers" OR "idents" OR "ident" OR "continuity" OR "interstitials" OR "station id" OR "station ids" OR "station ident" OR "station identification" OR "sign-off" OR "sign off" OR "signoff" OR "sign-on" OR "psa" OR "psas" OR "public service announcement" OR "public service announcements" OR "aircheck" OR "airchecks")'),
 ('stationid', 'title:(id OR ids OR ident OR idents OR "legal id" OR "station break" OR "sign off" OR "sign-off" OR signoff OR "sign on" OR "sign-on" OR signon OR "station promo" OR "station promos" OR "image promo") AND title:(tv OR channel OR station OR affiliate OR "ch.") AND title:(' + Y8 + ' OR ' + Y9 + ' OR "80s" OR "1980s" OR "90s" OR "1990s")'),
 ('stationid', 'description:("station id" OR "station ids" OR "station identification" OR "legal id" OR "station ident" OR "sign-off" OR "signoff" OR "sign off" OR "end of the broadcast day" OR "end of broadcast day") AND (title:(' + Y8 + ' OR ' + Y9 + ') OR year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31])'),
 ('signoff', 'title:("high flight" OR "star spangled banner sign" OR "broadcast day" OR "late night sign" OR "signing off" OR "signs off" OR "signing on" OR "final sign off" OR "final broadcast" OR "last broadcast" OR "final minutes" OR "last minutes" OR "analog shutdown" OR "morning sign on" OR "overnight sign off" OR "station sign off" OR "tv sign off" OR "tv signoff" OR "tv sign-off")'),
 ('psa', 'title:(psa OR psas OR "public service") AND title:(' + Y8 + ' OR ' + Y9 + ' OR "80s" OR "1980s" OR eighties OR "90s" OR "1990s" OR nineties OR vintage OR classic OR retro OR vhs)'),
 ('psa', 'title:("anti-drug" OR "anti drug" OR "anti-smoking" OR "anti smoking" OR "drunk driving" OR "drinking and driving" OR "seat belt" OR "seat belts" OR seatbelt OR "d.a.r.e." OR "red cross" OR "united way" OR "rock the vote" OR "aids awareness" OR "homefront" OR "latter-day saints" OR "foundation for a better life" OR "say no to drugs" OR "winners don\'t use drugs" OR "keep america beautiful" OR "give a hoot" OR "learn not to burn" OR "stop drop and roll" OR "mr. yuk" OR "missing children" OR "peace corps" OR "big brothers big sisters" OR "be all you can be" OR "fire safety" OR "bicycle safety" OR "stranger danger" OR "child abuse" OR "literacy" OR "library card" OR "vote" OR "recycle" OR "litter" OR "forest fires" OR "wildfires" OR "safety tips" OR "bod squad" OR "nutrition") AND title:(psa OR psas OR commercial OR commercials OR spot OR "public service")'),
 ('psa', 'creator:("ad council" OR "advertising council" OR "partnership for a drug-free america" OR "national crime prevention council" OR "u.s. forest service") AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + Y8 + ' OR ' + Y9 + '))'),
 ('newsbrk', 'title:(news OR newscast OR newsbreak OR newsbrief) AND title:(open OR opens OR intro OR tease OR teaser OR promo OR promos OR update OR break OR brief OR close) AND title:(' + Y8 + ')'),
 ('moviech', 'title:(hbo OR showtime OR cinemax OR "movie channel" OR starz OR encore OR "disney channel" OR tbs OR tnt OR usa OR amc) AND title:(intro OR intros OR "feature presentation" OR "next on" OR "coming up" OR "movie intro" OR "movie open" OR "movie opening" OR "movie bumper" OR "movie bumpers" OR promo OR promos OR bumper OR bumpers) AND title:(' + Y8 + ' OR ' + Y9 + ' OR "80s" OR "1980s" OR "90s" OR "1990s")'),
 ('kidint', 'title:(nickelodeon OR "nick jr" OR "cartoon network" OR "fox kids" OR "kids wb" OR "disney afternoon" OR "saturday morning" OR "pbs kids" OR "abc kids" OR "cbs kids" OR "usa cartoon express" OR "bkn" OR "upn kids" OR "disney channel" OR "toon disney" OR "nick at nite" OR snick) AND title:(bumper OR bumpers OR promo OR promos OR ident OR idents OR interstitial OR interstitials OR "be right back" OR "up next" OR "coming up" OR "station id" OR "shorts")'),
]
for k in range(0, len(CALLS), 60):
    QX.append(('stationid', 'title:(' + ' OR '.join(CALLS[k:k + 60]) + ') AND title:(id OR ids OR ident OR idents OR legal OR promo OR promos OR "sign off" OR "sign-off" OR signoff OR "sign on" OR "sign-on" OR signon OR bumper OR bumpers OR "station break" OR "news open" OR "news intro" OR psa OR "editorial" OR "image campaign" OR jingle OR "hello" OR "turn to" OR "come home")'))
QE = [('e84', 'title:(' + YE + ') AND (description:(commercial OR commercials OR "tv spot" OR advertisement OR "tv ad") OR subject:(commercial OR commercials OR advertising OR advertisement OR ads OR "tv ads"))')]
for k in range(0, len(BR), 20):
    QE.append(('eb%d' % (k // 20), 'title:(' + YE + ') AND title:(' + ' OR '.join('"%s"' % b for b in BR[k:k + 20]) + ')'))
KIDN = r"nickelodeon|nick jr|nick at nite|nicktoons|snick|cartoon network|toonami|cartoon cartoon|fox kids|kids'? ?wb|disney afternoon|one saturday morning|saturday morning|pbs kids|tnbc|cartoon express|toon disney|zoog|playhouse disney|boomerang|noggin"
MOVN = r"hbo|showtime|cinemax|the movie channel|starz|encore|feature presentation"
KW = [
 ('signoff', re.compile(r"\bsign[- ]?(off|on)s?\b|\bsign(ing|s) (off|on)\b|\bnational anthem\b|\bsermonette\b|\btest pattern\b|\bcolor bars\b|\bbroadcast day\b|\bhigh flight\b|\boff the air\b|\bfinal (broadcast|minutes)\b", re.I)),
 ('stationid', re.compile(r"\b(?i:station (id|ids|ident|idents|identification|identifications|promo|promos)|legal ids?|(channel|affiliate|local) ids?)\b|\b[WK][A-Z]{2,3}(-TV)?( TV)?( Channel)?[- ]?\d{0,2} (ID|IDs|Ident|Idents)\b")),
 ('psa', re.compile(r"\bpsas?\b|\bpublic service\b|\bad council\b|\bthe more you know\b|\bone to grow on\b|\bcbs cares\b|\bmcgruff\b|\bbrain on drugs\b|\bdrug[- ]free\b|\bsmokey (the )?bear\b|\bwoodsy\b|\bcrash test dumm\w+\b|\bbuckle up\b|\bjust say no\b|\banti[- ](drug|smoking|drugs)\b|\bdrunk driving\b|\btime for timer\b|\bbod squad\b", re.I)),
 ('newsbrk', re.compile(r"\bnews ?(casts?)? (opens?|opening|intros?|teases?|teasers?|breaks?|updates?|promos?|briefs?|themes?|close)\b|\bnews ?(break|brief)s?\b|\bspecial report\b", re.I)),
 ('moviech', re.compile(r"\b(" + MOVN + r")\b.*\b(intros?|opening|opens?|promos?|bumpers?|idents?|next on|coming|tonight|presentation|preview|this month)\b|\bfeature presentation\b", re.I)),
 ('kidint', re.compile(r"\b(" + KIDN + r")\b.*\b(bumpers?|promos?|idents?|ids?|interstitials?|shorts?|be right back|up next|coming up|station break|commercial break)\b|\b(bumpers?|promos?|idents?|interstitials?)\b.*\b(" + KIDN + r")\b", re.I)),
 ('bumper', re.compile(r"\bbumpers?\b|\bidents?\b|\binterstitials?\b|\bbe right back\b|\bstation break\b|\bnetwork ids?\b|\bup next\b|\bnow back to\b", re.I)),
 ('promo', re.compile(r"\bpromos?\b|\bfall (preview|lineup|campaign|season)\b|\bimage campaign\b|\btonight on\b|\bcoming up\b|\bnext week on\b|\bthis (week|fall) on\b|\bmust see tv\b|\btgif\b|\bseason premiere\b|\bseries premiere\b|\bsneak preview\b|\bworld premiere\b|\blineup\b|\bstay tuned\b", re.I)),
]
ADWORD = re.compile(r'\b(commercials?|adverts?|advertisements?|tv spots?|tv ads?|ads)\b', re.I)
def kind(t):
    for k, r in KW:
        if r.search(t): return k
    return ''
NETRX = [('NBC', r'nbc'), ('CBS', r'cbs'), ('ABC', r'abc'), ('Fox', r'fox(?! kids| family)'), ('UPN', r'upn'), ('The WB', r"(the )?wb|kids'? ?wb"), ('PBS', r'pbs'), ('Nickelodeon', r'nickelodeon|nick jr\.?|nick at nite|nicktoons|snick'), ('MTV', r'mtv'), ('VH1', r'vh-?1'), ('Cartoon Network', r'cartoon network|toonami|adult swim'), ('Disney Channel', r'disney channel|toon disney|zoog disney|playhouse disney'), ('Fox Kids', r'fox kids'), ('Fox Family', r'fox family|family channel'), ('USA', r'usa network|usa cartoon express'), ('TBS', r'w?tbs|superstation'), ('TNT', r'tnt'), ('WGN', r'wgn'), ('HBO', r'hbo'), ('Showtime', r'showtime'), ('Cinemax', r'cinemax'), ('ESPN', r'espn2?'), ('CNN', r'cnn|headline news'), ('TNN', r'tnn|nashville network'), ('Lifetime', r'lifetime'), ('Comedy Central', r'comedy central|ha!'), ('Sci-Fi Channel', r'sci-?fi channel'), ('Discovery', r'discovery channel'), ('TLC', r'tlc|learning channel'), ('BET', r'bet'), ('The Weather Channel', r'weather channel'), ('AMC', r'amc'), ('TV Land', r'tv land'), ('A&E', r'a&e'), ('Syndication', r'syndicated|syndication')]
NETRX = [(n, re.compile(r'(?<![\w&])(' + r + r')(?![\w&])', re.I)) for n, r in NETRX]
CALLRX = re.compile(r"(?<![\w'])([WK][A-Z]{3}|[WK][A-Z]{2})(?:-(?:TV|DT|LP|CA|\d{1,2})\b| ?-? ?(?:TV|Channel|Ch\.?|NewsCenter|News|Eyewitness|Action|Newswatch) ?\d{0,2}\b| \d{1,2}\b)")
CALLSET = set(c.upper() for c in CALLS)
def netst(t):
    net = next((n for n, r in NETRX if r.search(t)), '')
    m = CALLRX.search(t); st = m.group(1) if m else ''
    if not st:
        st = next((w for w in re.findall(r'\b[WK][A-Z]{2,3}\b', t) if w in CALLSET), '')
    if not st:
        m = re.search(r'[(/]([WK][A-Z]{3})\b', t); st = m.group(1) if m else ''
    if st in ('WWF', 'WCW', 'KISS', 'KIDS', 'WAR', 'WHO', 'WAS', 'WITH', 'WHAT', 'WHEN', 'KID', 'KEY', 'WAY', 'WIN', 'WEB'): st = ''
    return net, st
def exact(t):
    m = re.search(r'(?<!\d)(198[4-9]|199\d|200[0-4])[-_./ ](0?[1-9]|1[0-2])[-_./ ](0?[1-9]|[12]\d|3[01])(?!\d)', t)
    if m: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(?<!\d)(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])[-/.]((?:19)?(?:8[4-9]|9\d)|(?:20)?0[0-4])(?!\d)', t)
    if m:
        y = m.group(3); y = y if len(y) == 4 else ('19' if y >= '84' else '20') + y
        return '%s-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?,? (198[4-9]|199\d|200[0-4])\b', t, re.I)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)? (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,? (198[4-9]|199\d|200[0-4])\b', t, re.I)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(2).lower()], int(m.group(1)))
    return ''
JUNK = re.compile(r"\b(tv-?dx|dx-?tv|teleclub|eurosport|avslutning|sendeschluss|sendestart|testbild|nightcore|anthem of (?!the united states|america|the usa|the u\.s)\w+|himno|hino nacional|comerciales|comercial|comerciais|propagandas?|reklam\w*|publicit\w+|werbung|pubblicit\w+|hindi|tamil|telugu|zee tv|belarus\w*|ukrain\w*|albania\w*|morocc\w*|benin|romania\w*|bulgaria\w*|serbia\w*|croatia\w*|sloven\w+|slovak\w*|austria\w*|switzerland|iran\w*|iraq\w*|egypt\w*|nigeria\w*|kenya\w*|south africa\w*|pakistan\w*|bangladesh\w*|sri lanka\w*|screen ?record\w*|screencast|test upload|test video)\b", re.I)
JUNKF = re.compile(r"\b(mixtape|dj set|music video|lyric video|karaoke|amv|vlog|unboxing|speedrun|fnaf|roblox|sermon(?!ette)|church service|city council|board meeting|school board|commission meeting|town hall|press conference|webcast|vice news|shoot interview|fictional|alternate history)\b", re.I)
WRES = re.compile(r"\b(wrestl\w+|wwf|wwe|wcw|ecw|nwa)\b", re.I)
USHINT = re.compile(r"\b(nbc|cbs|abc|fox|pbs|upn|wb|nickelodeon|hbo|mtv|usa|american|u\.s\.)\b|\b[WK][A-Z]{2,3}(-TV)?\b")
def junk(t, q):
    if JUNK.search(t) or JUNKF.search(t): return True
    if NONUS.search(t) or FOREIGN.search(t): return True
    if WRES.search(t) and not netst(t)[0]: return True
    if re.search(r'\bclose-? ?downs?\b', t, re.I) and not netst(t)[1]: return True
    if q == 'signoff' and re.search(r'\bnational anthem\b', t, re.I) and not re.search(r'sign|star[- ]spangled|united states|usa|u\.s\.|america|[WK][A-Z]{2,3}', t): return True
    return False
seen = {}
def take(tag, items):
    n = 0
    for it in items:
        i = it['identifier']; t = str(it.get('title') or '')
        if i in have or i in mine or i in seen: continue
        if BAD.search(t) or FOREIGN.search(t) or AUS.search(t) or NONUS.search(t): continue
        if re.search(r'[^\x00-\xff‐-‧™]', t): continue
        if re.search(r'(?<!\d)20(0[5-9]|[1-3]\d)(?!\d)', t): continue
        if JUNK.search(t): continue
        if tag not in ('ad', 'adc') and junk(t, tag): continue
        if tag == 'adc':
            k = kind(t)
            if not ADT.search(t) and not k: continue
            if k and not ADWORD.search(t): it['q'] = k; seen[i] = it; n += 1; continue
        it['q'] = tag; seen[i] = it; n += 1
    return n
FT = []
for y in list(range(1984, 1990)) + list(range(2001, 2005)):
    FT.append(('ft%d' % y, '("%d commercial" OR "%d commercials" OR "commercial %d" OR "commercials %d" OR "%d tv commercial" OR "%d tv ad" OR "%d ad" OR "commercials from %d" OR "aired %d" OR "%d tv spot")' % ((y,) * 10)))
QA += FT
GEN = re.compile(r'^(opensource|community|fav-|folksoundomy|additional_collections|deemphasizedmovies|movies$|television$|youtubearchive|vintage_?software|opensource_media|stream_only|podcasts|audio)', re.I)
def colscan():
    ids = sorted(set(r[0] for r in oldads)); random.seed(11); random.shuffle(ids); ids = ids[:1500]
    ids += sorted(set(x['i'] for x in oldfl if x['q'] in ('promo', 'bumper', 'stationid', 'signoff', 'psa', 'kidint', 'moviech', 'newsbrk')))
    cc = collections.Counter(); uu = collections.Counter()
    def one(i):
        j = get('https://archive.org/metadata/' + urllib.parse.quote(i) + '/metadata')
        m = (j or {}).get('result') or {}
        c = m.get('collection', []); c = [c] if isinstance(c, str) else c
        return [x for x in c if not GEN.search(x)], str(m.get('uploader') or '')
    with ThreadPoolExecutor(THREADS) as ex:
        for cs, u in ex.map(one, ids):
            cc.update(cs)
            if u: uu[u] += 1
    cols = [c for c, n in cc.most_common(90) if n >= 4]; ups = [u for u, n in uu.most_common(160) if n >= 3]
    print('route collections', len(cols), [(c, cc[c]) for c in cols[:40]], flush=True)
    print('route uploaders', len(ups), [n for u, n in uu.most_common(40)], flush=True)
    return cols, ups
def plan():
    if oldads:
        cols, ups = colscan()
        for k, c in enumerate(cols):
            items = scrape('collection:"%s" AND mediatype:movies' % c, 60000)
            print('ad col', c, 'hits', len(items), 'new', take('adc', items), 'total', len(seen), flush=True)
        for k, u in enumerate(ups):
            items = scrape('uploader:"%s" AND mediatype:movies' % u, 60000)
            print('ad up', k, 'hits', len(items), 'new', take('adc', items), 'total', len(seen), flush=True)
    for k, (tag, q) in enumerate(QX):
        items = scrape('(' + q + ') AND mediatype:movies')
        n = 0
        for it in items: it['x'] = 1
        print('thin', k, tag, 'hits', len(items), 'new', take(tag, items), 'total', len(seen), flush=True)
    for tag, q in QE:
        items = scrape('(' + q + ') AND mediatype:movies')
        for it in items: it['x'] = 1
        print('early', tag, 'hits', len(items), 'new', take('ad', items), 'total', len(seen), flush=True)
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
        m = YR.search(t)
        if m: s += 4
        if m and int(m.group(1)) <= 1991: s += 4
        if it['q'] in ('promo', 'bumper', 'stationid', 'signoff', 'psa', 'kidint', 'moviech', 'newsbrk'): s += 5
        elif it['q'] not in ('ad', 'adc'): s += 1
        if it.get('x'): s += 3
        if exact(t): s += 2
        if any(netst(t)): s += 2
        return -s, -(it.get('downloads') or 0)
    cands.sort(key=pri); cands = cands[:MAXC]
    print('candidates', len(cands), collections.Counter(c['q'] for c in cands).most_common(), flush=True)
    with gzip.open(CF, 'wt', encoding='utf-8') as f: json.dump([[c['identifier'], c['q'], c.get('downloads') or 0] for c in cands], f)
    return cands
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
def meta(c):
    it = {'identifier': c[0], 'q': c[1], 'downloads': c[2]}
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
    k = kind(title)
    if tag in ('promo', 'bumper', 'kidint', 'psa', 'stationid', 'newsbrk', 'signoff', 'moviech', 'holiday') and k: tag = k
    elif tag in ('ad', 'adc') and k and not ADWORD.search(title): tag = k
    if JUNK.search(title) or (tag not in ('ad', 'adc') and junk(title, tag)): rej['junk'] += 1; return None
    hasad = bool(ADT.search(title))
    maybe = ''
    if not ds:
        my = 0
        for v in (m.get('date'), m.get('year')):
            mm = re.match(r'(\d{4})', str(v or ''))
            if mm: my = max(my, int(mm.group(1)))
        if MODW.search(title) or MODW.search(desc[:200]): rej['modernword'] += 1; return None
        if 0 < my < 1984 and not dec: rej['pre84'] += 1; return None
        if tag not in ('ad', 'adc') and my >= 2005 and not (dec or RETRO.search(title)): rej['moderndate'] += 1; return None
        maybe = 'no date in title or description' + ('; item date %d' % my if my else '')
        if not dec: dec = '80s' if re.search(r'\b(atari|colecovision|intellivision|betamax|cabbage patch|teddy ruxpin|new coke|spuds|max headroom|zayre|crazy eddie)\b', title, re.I) else '90s'
    net, st = netst(title); dt = exact(title)
    if dt and ds and dt[:4] != ds[:4]: dt = ''
    base = {'i': it['identifier'], 't': title[:200], 'd': ds, 'y': ds[:4], 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:300], 'dl': it.get('downloads') or 0, 'u': up, 'dec': dec, 'src': src}
    if net: base['net'] = net
    if st: base['st'] = st
    if dt: base['dt'] = dt
    if tag in ('ad', 'adc') and not hasad:
        if len(files) != 1 or not (5 <= files[0][1] <= 125): rej['notadword'] += 1; return None
        maybe = (maybe + '; ' if maybe else '') + 'no commercial word in title'
    if tag not in ('ad', 'adc') and src == 'm' and 'community_media' in col:
        maybe = (maybe + '; ' if maybe else '') + 'year from item date only'
    if maybe: base['keep'] = 'maybe'; base['why'] = maybe
    if tag in ('ad', 'adc'):
        if NOTAD.search(title): rej['notad'] += 1; return None
        if NONUS.search(title): rej['nonus'] += 1; return None
        singles = [f for f in files if 5 <= f[1] <= 125]
        if len(files) == 1 and singles:
            if COMP.search(title) and files[0][1] > 70: rej['compshort'] += 1; return None
            return ('ad', [[it['identifier'], files[0][0], files[0][1], ds, title[:120], dec] + (['maybe', maybe] if maybe else [])])
        if len(files) > 1 and len(singles) >= max(2, len(files) * .8) and len(files) <= 400:
            rows = []
            for f in singles[:400]:
                stem = re.sub(r'\.(ia\.)?mp4$', '', f[0].split('/')[-1]); stem = re.sub(r'[_]+', ' ', stem)
                fd, fdec, _ = when(stem, '', '', '')
                rows.append([it['identifier'], f[0], f[1], fd or ds, (stem if len(stem) > 12 else title[:80] + ' - ' + stem)[:120], fdec or dec] + (['maybe', maybe] if maybe and not fd else []))
            return ('ad', rows)
        if tag == 'ad' and len(files) <= 3 and 126 <= tot <= 900:
            base.update(q='adbreak', f=files); return ('fl', base)
        rej['adlen'] += 1; return None
    if tag == 'adbreak':
        if not (120 <= tot <= 900) or len(files) > 4: rej['breaklen'] += 1; return None
        base.update(q='adbreak', f=files); return ('fl', base)
    lim = 3600 if tag in ('cablefill', 'weather', 'signoff') else 900
    if tot > lim and len(files) == 1: rej['long'] += 1; return None
    if len(files) > 1:
        files = [f for f in files if f[1] <= 600][:60]
        if not files: rej['long'] += 1; return None
    base.update(q=tag, f=files); return ('fl', base)
def look(cands, k):
    ads, fl = [], []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r:
                if r[0] == 'ad': ads += r[1]
                else: fl.append(r[1])
            if n % 4000 == 0: print('meta', n, len(ads), len(fl), round((time.time() - T0) / 60, 1), 'min', flush=True)
    print('rejected', dict(rej), flush=True)
    with gzip.open(os.path.join(PARTS, 'ads2-%d.json.gz' % k), 'wt', encoding='utf-8') as f: json.dump({'ads': ads, 'fl': fl, 'rej': dict(rej)}, f, ensure_ascii=False)
    return ads, fl
if MODE == 'plan':
    plan(); sys.exit(0)
if MODE == 'meta':
    cands = json.load(gzip.open(CF, 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'candidates', len(cands), flush=True)
    look(cands, SHARD); sys.exit(0)
if MODE == 'merge':
    ads, fl = [], []; tot = collections.Counter()
    for fn in sorted(glob.glob(os.path.join(PARTS, 'ads2-[0-9]*.json.gz'))):
        j = json.load(gzip.open(fn, 'rt', encoding='utf-8'))
        ads += j['ads']; fl += j['fl']; tot.update(j['rej'])
        print('part', os.path.basename(fn), len(j['ads']), len(j['fl']), flush=True)
    print('rejected', dict(tot), flush=True)
else:
    ads, fl = look([[c['identifier'], c['q'], c.get('downloads') or 0] for c in plan()], 0)
def fixrow(r):
    d = r[3]
    if d and not ('1984' <= d[:4] <= '2004'): return None
    if NONUS.search(r[4]) or JUNK.search(r[4]): return None
    if d and len(d) < 7:
        nd, _, _ = when(r[4], '', '', '')
        if nd[:4] == d[:4] and len(nd) >= 7: r = r[:3] + [nd] + r[4:]
    return r
def fixfl(x):
    if not ((x.get('d') and '1984' <= x['d'][:4] <= '2004') or (not x.get('d') and x.get('dec'))): return None
    if junk(x['t'], x['q']): return None
    k = kind(x['t'])
    if x['q'] in ('promo', 'bumper', 'kidint', 'psa', 'stationid', 'newsbrk', 'signoff', 'moviech', 'holiday') and k: x['q'] = k
    net, st = netst(x['t']); dt = exact(x['t'])
    if net: x['net'] = net
    if st: x['st'] = st
    if dt and (not x.get('d') or dt[:4] == x['d'][:4]): x['dt'] = dt
    return x
got = set(); allfl = []
for x in oldfl + [{k: v for k, v in x.items() if k != 'u'} for x in fl]:
    x = fixfl(x)
    if x and x['i'] not in got: got.add(x['i']); allfl.append(x)
adk = set(); dd = []
for r in oldads + ads:
    if (r[0], r[1]) in adk or r[0] in got: continue
    adk.add((r[0], r[1])); dd.append(r)
ads = [r for r in ads if r[0] not in got]
allads = [x for x in (fixrow(r) for r in dd) if x]
print('purged ads', len(oldads) + len(ads) - len(allads), 'filler', len(oldfl) + len(fl) - len(allfl), flush=True)
with gzip.open(ADF, 'wt', encoding='utf-8') as f: json.dump(allads, f, ensure_ascii=False, separators=(',', ':'))
with gzip.open(FLF, 'wt', encoding='utf-8') as f: json.dump(allfl, f, ensure_ascii=False, separators=(',', ':'))
print('ads rows new', len(ads), 'total', len(allads), 'items', len(set(r[0] for r in allads)), '| filler new', len(fl), 'total', len(allfl))
by = collections.Counter(); bm = collections.Counter(); bd = collections.Counter()
for r in allads:
    y = r[3][:4] if r[3] else ('dec:' + (r[5] if len(r) > 5 else '') + (' maybe' if len(r) > 6 else ''))
    by[y] += 1
    if len(r[3]) >= 7: bm[r[3][:4]] += 1
print('ADS YEAR rows with_month')
for k in sorted(by): print(' ', k, by[k], bm.get(k, 0))
print('TAGGED filler net', sum(1 for x in allfl if x.get('net')), 'station', sum(1 for x in allfl if x.get('st')), 'exact date', sum(1 for x in allfl if x.get('dt')), 'maybe', sum(1 for x in allfl if x.get('keep')), '| ads maybe', sum(1 for r in allads if len(r) > 6))
ft = collections.defaultdict(lambda: collections.Counter())
for x in allfl: ft[x['q']][x.get('y') or ('dec:' + x.get('dec', '') + ('?' if x.get('keep') else '')) or '?'] += 1
print('FILLER TYPE total | per year')
for k in sorted(ft, key=lambda k: -sum(ft[k].values())): print(' ', k, sum(ft[k].values()), '|', ' '.join('%s:%d' % (y, n) for y, n in sorted(ft[k].items())))
random.seed(7)
print('SAMPLE ADS')
for r in random.sample(ads, min(80, len(ads))): print(' ', r[3] or r[5], '|', round(r[2]), 's |', r[4][:90])
print('SAMPLE FILLER')
fl = [x for x in fl if x['i'] in got]
for x in random.sample(fl, min(60, len(fl))) + [z for q in ('promo', 'bumper', 'stationid', 'signoff', 'psa') for z in random.sample([w for w in fl if w['q'] == q], min(25, len([w for w in fl if w['q'] == q])))]: print(' ', x['q'], '|', x['d'] or x.get('dec', '') or '?', '|', round(sum(f[1] for f in x['f'])), 's |', len(x['f']), 'f |', x['t'][:90])
