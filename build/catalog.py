import gzip, json, re, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netmap import NETMAP
from titles import std_title
from series import series_year, series_name
NETRX = [(k, re.compile(r'\b(' + v + r')(?![a-z])')) for k, v in NETMAP.items()]

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'catalog', 'raw.json.gz')
OUT = sys.argv[2] if len(sys.argv) > 2 else 'catalog.json'
items = json.load(gzip.open(RAW, 'rt', encoding='utf-8'))
_have = set(x['i'] for x in items)
for _fn, _force in (('games', 'game'), ('tech', 'tech'), ('musthave', 'kids'), ('toons', 'kids'), ('preschool', 'kids'), ('schoolage', 'kids'), ('wrestling', 'wrest')):
    _p = os.path.join(os.path.dirname(RAW), _fn + '.json.gz')
    if not os.path.exists(_p): continue
    for x in json.load(gzip.open(_p, 'rt', encoding='utf-8')):
        if x['i'] in _have: continue
        _have.add(x['i']); x['force'] = _force
        if x.get('e') and not x.get('y'): x['y'] = str(x['e'])
        items.append(x)

MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def ok_y(y): return 1984 <= y <= 2004
def y2(y):
    y = int(y)
    return y + 1900 if y < 100 and y >= 40 else (y + 2000 if y < 40 else y)
def title_date(t):
    s = t.lower()
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})', s)
    if m and ok_y(int(m.group(3))): return '%04d-%02d-%02d' % (int(m.group(3)), MON[m.group(1)], int(m.group(2)))
    m = re.search(r'\b(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\b', s)
    if m and ok_y(int(m.group(1))) and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{2}|\d{4})\b', s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), y2(m.group(3))
        if ok_y(c) and 1 <= a <= 12 and 1 <= b <= 31: return '%04d-%02d-%02d' % (c, a, b)
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})', s)
    if m and ok_y(int(m.group(2))): return '%04d-%02d' % (int(m.group(2)), MON[m.group(1)])
    return None
def meta_date(d):
    m = re.match(r'^(\d{4})(?:-(\d\d))?(?:-(\d\d))?', d or '')
    if m and ok_y(int(m.group(1))): return '-'.join(x for x in m.groups() if x)
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})', d or '')
    if m and ok_y(y2(m.group(3))): return '%04d-%02d-%02d' % (y2(m.group(3)), int(m.group(1)), int(m.group(2)))
    return None
def pick_date(it):
    td = title_date(it['t'])
    md = meta_date(it['d'])
    if td and len(td) >= len(md or ''): return td
    if md: return md
    m = re.search(r'\b(19[89]\d|200[0-4])\b', it['t'])
    if m: return m.group(1)
    if it.get('y') and re.match(r'^\d{4}$', it['y']) and ok_y(int(it['y'])): return it['y']
    return None

def guess_date(it):
    blob = (it.get('t', '') + ' ' + it.get('ds', '') + ' ' + it.get('s', '')).lower()
    m = re.search(r"\b(circa|c\.|ca\.|around|approx\.?|early|mid|late)?\s*-?(19[89]\d|200[0-4])s?\b", blob)
    if m:
        y = int(m.group(2)); w = m.group(1) or ''
        if m.group(0).rstrip().endswith('s') and y % 10 == 0: y += 2 if w == 'early' else 8 if w == 'late' else 5
        if 1984 <= y <= 2004: return str(y)
    m = re.search(r"(?<![\w'])'?(8|9)0'?s\b", blob)
    if m: return '1987' if m.group(1) == '8' else '1995'
    m = re.search(r"\b(early|mid|late)?[- ]?(eighties|nineties)\b", blob)
    if m: return '1987' if m.group(2) == 'eighties' else '1995'
    cs = ' '.join(it.get('c') or [])
    for k, y in (('1980s', '1987'), ('1990s', '1995'), ('2000s', '2002')):
        if k in cs: return y
    for pat, y in ((r'\b(techtv|tech tv)\b', '2002'), (r'\bzdtv\b', '1999'), (r'\bg4\b', '2003'), (r'\bwwe\b', '2003'), (r'\b(upn|the wb|kids.? wb)\b', '1998'), (r'\bfox kids\b', '1996'), (r'\btoonami\b', '1999'), (r'\b(wcw|nitro)\b', '1997'), (r'\becw\b', '1997'), (r'\bwwf\b', '1992'), (r'\b(nwa|awa|mid-south|world class)\b', '1986'), (r'\b(betamax|beta tape)\b', '1986'), (r'\bdvd\b', '2002'), (r'\b(nicktoons|snick)\b', '1994'), (r'\b(nick jr|playhouse disney)\b', '1999'), (r'\bdisney afternoon\b', '1992')):
        if re.search(pat, blob): return y
    e = it.get('e')
    if e and str(e).isdigit() and 1984 <= int(e) <= 2004: return str(e)
    rawy = re.match(r'(\d{4})', str(it.get('d') or ''))
    if rawy and int(rawy.group(1)) < 1984: return '1984'
    return '1994'
def has(s, pat): return re.search(pat, s) is not None
X_JUNK = r"\b(opening to|closing to|opening and closing|trailers?|teasers?|bumpers?|promo reel|home movies?|camcorder|family video|wedding|funeral|sermon|lecture|conference|seminar|webinar|instructional|workout|aerobics|karaoke|mock|fan ?made|fanmade|reupload|longplay|gameplay|playthrough|speedrun|walkthrough|let's play|unboxing|review of|reaction|podcast|audiobook|slideshow|screensaver|test pattern only|ident|idents|logos?|intros?|outros?|theme songs?|credits only|blooper reel|remaster(ed)?|fan remaster|restored|restoration|upscaled?|ai enhanced|colorized|storybook|making of|behind the scenes|sing along|singalong)\b"
X_FOREIGN = r"(castellano|español|espanol|deutsch|français|francais|italiano|português|portugues|nederlands|svenska|suomi|mainoks|русск|日本|telenovela|doblaje|dublado|latino|brasil|globo|\brai\b|\bzdf\b|\bard\b|\bbbc\b|\bitv\b|\bcbc\b|\bctv\b|\btvo\b|australia|tvnz|\btf1\b|antenne|\bbritish\b|\(uk\)|\buk\b|canad|bulgar|polsk|czech|magyar|türk|greek|hindi|tamil|korea|chinese|mandarin|cantonese|tagalog|filipino|japan|anime|mexic|argentin|chile|venezuel|colombia|perú|\bperu\b|german|france|italy|italian|spain|spanish|dutch|holland|sweden|swedish|norw|denmark|danish|finland|finnish|russia|poland|hungar|portugal|brazil|india\b|china|philippin|europe|\bnhk\b|\bsbs\b|\by los\b|\bdel universo|\bcap[ií]tulo|\bepisodio|\btemporada|\bla serie\b|\bdoblado|\bversi[oó]n|januari|februari|maart|augustus|\bmei\b|\bjuni\b|\bjuli\b)"
X_FOREIGN_T = r"\b(home and away|neighbours|blue peter|grange hill|top of the pops|winnipeg|calgary|edmonton|bbc\d?|noche|desenhos|pel[ií]cula|dibujos|cap[ií]tulo|epis[oó]dio|svtplay|melodifestivalen|juste pour rire|jurasico|vcd|vhsrip|dvdrip|polka|exorcism|fmw|ajpw|njpw|all japan|new japan|hello! morning|morning musume|anime|subbed|dubbed|melbourne|sydney|brisbane|adelaide|australia|australian|national nine|nine news|seven news|seven late news|ten news|brookside|coronation street|eastenders|emmerdale|t4|toggo|verein|itv|bbc|cbbc|ceefax|tvb|cbc|ctv|toronto|vancouver|montreal|ontario|qu[eé]bec|new zealand|channel 4:|vhs pal|pal vhs|\(pal\)|pal version|secam|uk tv|british tv|irish tv|rt[eé])\b"
X_MODERN = r"\b(moments|clips|reviewed|retrospective|out of context|speedrun|in \d+:\d\d|toy|toys|lego|interview|longplay|netflix|batchelor|amazing facts|all grown up|da vinci|tower prep|special unit 2|galaxy force|back to the sewer|toei|vortexx|monsters unleashed|fusion reborn|voices only|abridged|crystal|legendary defender|static cling|wwdc|siggraph|session \d+|kindergarten|chouans|scholastic|scrimmage|tape \d{3,}|continuity|promos|promo|pokimane|twitch|livestream|live stream|stream vod|youtube|tiktok|podcast|reaction|let'?s play|remaster(ed)?|upscaled?|4k|ai upscale|fan ?edit|fan ?made|fanvid|deepfake|recreation|recreated|reupload|re-upload|mock|parody|ytp)\b"
X_SPORT = r"\b(nfl|nba|mlb|nhl|super bowl|world series|olympics?|ncaa|football|baseball|basketball|hockey|soccer|fifa|nascar|indy ?500|golf|tennis|stanley cup|playoffs?|bowl game)\b"
X_ADULT = r"\b(xxx|porn|nude|nudity|erotic|playboy|sex|strip|stripper|fetish|hentai)\b"
X_ADS = r"\b(commercials? (compilation|block|break)s?|tv commercials|vintage commercials|commercial compilation|ads from|commercials from|commercials of|commercials \d|\d+ commercials|commercial breaks?)\b|^commercials\b"
X_OTHER = r"\b(700 club|praise the lord|\btbn\b|c-span|cspan|qvc|home shopping|infomercial|paid program|church|mass\b|telethon)\b"

CAT = [
 ('wrest', r"\b(wwf|wcw|wrestl|awa|nwa|ecw|g\.?l\.?o\.?w|wrestlemania|summerslam|royal rumble|survivor series|starrcade|great american bash|clash of the champions|saturday night's main event|nitro|monday night raw)\b"),
 ('cook', r"\b(frugal gourmet|julia child|yan can|great chefs|justin wilson|graham kerr|galloping gourmet|jacques p[eé]pin|martha stewart|food network|two fat ladies|molto mario|earl peyroux|nathalie dupree|cooking|cookin'|chef|cuisine|this old house|bob vila|victory garden|joy of painting|bob ross)\b"),
 ('tech', r"(computer chronicles|net cafe|techtv|tech tv|zdtv|screen savers|screensavers|call for help|\bg4\b|x-play|xplay|attack of the show|gamespot|electric playground|video power|nick arcade|game masters|gamesmaster|bits and bytes)"),
 ('weather', r"(weather channel|weatherstar|local forecast|local on the 8s)"),
 ('music', r"\b(mtv|vh1|vh-1|music video|video countdown|friday night videos|soul train|american bandstand|solid gold|headbangers|120 minutes|yo! mtv|night tracks|club mtv|dance party usa|the box|much ?music|night flight|cmt|countdown|top 20 video|top 40 video|hot tracks|video hits|rock video)\b"),
 ('kids', r"\b(cartoons?|saturday morning|nickelodeon|nick jr|nick at nite|snick|fox kids|disney afternoon|kids ?wb|ducktales|transformers|g\.?i\.? ?joe|he-man|she-ra|smurfs|muppet babies|ninja turtles|tmnt|power rangers|thundercats|care bears|my little pony|pee-?wee|sesame street|mister rogers|mr\. rogers|reading rainbow|3-2-1 contact|double dare|pinwheel|you can't do that on television|tiny toons?|animaniacs|garfield|inspector gadget|voltron|silverhawks|bravestarr|real ghostbusters|talespin|gummi bears|alvin and the chipmunks|scooby|flintstones|jetsons|looney tunes|bugs bunny|disney channel|cartoon network|cartoon express|doug|rugrats|ren (and|&) stimpy|rocko|eureeka|today's special|zoobilee|shining time|barney|lamb chop|wishbone|bill nye|beakman|ghostwriter|legends of the hidden temple|guts|figure it out|all that|kenan|clarissa|are you afraid|salute your shorts|hey dude|mighty morphin|x-men|batman: the animated|spider-man|sonic the hedgehog|super mario|captain n|winnie the pooh|teddy ruxpin|gobots|jem\b|dungeons (and|&) dragons|mr\. t|alf tales|popeye|woody woodpecker|tom and jerry|pink panther)\b"),
 ('late', r"\b(tonight show|letterman|arsenio|late night with|late show|johnny carson|jay leno|conan o'?brien|saturday night live|\bsnl\b|into the night|pat sajak show|dennis miller|jon stewart show|chevy chase show|politically incorrect|later with bob costas|friday night videos)\b"),
 ('talk', r"\b(donahue|oprah|geraldo|sally jessy|joan rivers|live with regis|regis (and|&) kathie|morton downey|jenny jones|montel|ricki lake|jerry springer|rosie o'?donnell|maury|richard bey|charles perez|gordon elliott|vicki lawrence|jane whitney|mike and maty|home show|sonya live|dinah)\b"),
 ('morning', r"\b(good morning america|today show|the today show|cbs this morning|cbs morning news|morning news|early today|nbc news at sunrise|world news this morning|cbs morning)\b"),
 ('mag', r"\b(entertainment tonight|a current affair|inside edition|hard copy|access hollywood|e! news|showbiz today|pm magazine|evening magazine|that's incredible|real people|ripley's believe it or not)\b"),
 ('news', r"\b(news|newscast|eyewitness|action news|nightline|headline news|cnn|world news|nightly news|evening news|news at|60 minutes|20/20|dateline|48 hours|primetime live)\b"),
 ('game', r"\b(wheel of fortune|jeopardy|price is right|family feud|press your luck|card sharks|hollywood squares|pyramid|sale of the century|concentration|win, lose or draw|supermarket sweep|newlywed game|dating game|scrabble|match game|joker's wild|tic tac dough|lingo|american gladiators|star search|wordplay|chain reaction|body language|super password|password plus|blockbusters|break the bank|catch phrase|classic concentration|let's make a deal|love connection|the challengers|trump card|now you see it|bumper stumpers|lip service|studs|personals|the big spin|name that tune|jackpot|the joker|wipeout|press your|game show)\b"),
 ('soap', r"\b(general hospital|days of our lives|young and the restless|all my children|one life to live|as the world turns|guiding light|santa barbara|another world|bold and the beautiful|search for tomorrow|ryan's hope|port charles|sunset beach|dark shadows)\b"),
 ('movie', r"\b(movie|monstervision|up all night|commander usa|creature feature|creature double feature|chiller theat|shock theat|elvira|joe bob|drive-in|miniseries|mini-series|hbo|showtime|cinemax|the movie channel|million dollar movie|4:30 movie|late movie|sunday night movie|saturday night movie|movie of the week|world premiere movie|movie loft|svengoolie|sammy terry|dr\. shock|son of svengoolie)\b"),
 ('prime', r"\b(primetime|prime time|tgif|must see tv|cheers|seinfeld|simpsons|married with children|full house|family matters|roseanne|cosby|alf\b|golden girls|who's the boss|growing pains|family ties|miami vice|moonlighting|star trek|x-files|90210|melrose place|murder,? she wrote|dallas|dynasty|knight rider|a-team|magnum|night court|perfect strangers|step by step|home improvement|wonder years|quantum leap|america's funniest|in living color|mad about you|frasier|fresh prince|saved by the bell|boy meets world|newsradio|3rd rock|living single|murphy brown|designing women|empty nest|macgyver|21 jump street|highway to heaven|love boat|fantasy island|hill street blues|l\.a\. law|thirtysomething|twin peaks|northern exposure|nypd blue|law & order|dr\. quinn|touched by an angel|baywatch|babylon 5|seaquest|lois & clark|head of the class|facts of life|diff'rent strokes|silver spoons|webster|punky brewster|small wonder|mr\. belvedere|charles in charge|a different world|doogie howser|major dad|evening shade|sister,? sister|hangin' with mr\. cooper|the nanny|ellen|drew carey|everybody loves raymond|king of the hill|that '70s show|dawson's creek|buffy|picket fences|chicago hope|walker,? texas ranger|amen|227|hunter|matlock|jake and the fatman|in the heat of the night|scarecrow|remington steele|cagney|airwolf|v the series|misfits of science|the equalizer|spenser|st\. elsewhere|night rider|benson|newhart|kate & allie|mama's family|dear john|coach|wings|the simpsons|beverly hills|sitcom|friends|unsolved mysteries|rescue 911|america's most wanted|cops)\b"),
]
COLCAT = [('game', {'gameshows', 'gameshows_miscellaneous', 'gameshow_jeopardy', 'gameshow_tpir'}), ('wrest', {'wrestlingtelevision'}), ('tech', {'computersandtechvideos', 'video_power', 'G4_Icons'}), ('kids', {'vhskids', 'childrenstelevision', 'saturdaymorningcartoons', 'dvdkids'}), ('music', {'musictelevision', 'musicvideobin', 'groove_tv'}), ('news', {'vhsnews', 'vhsnews_1980s', 'vhsnews_1990s', 'vhsnews_2000s', 'newsandpublicaffairs'}), ('movie', {'vhsmovies'})]
TVCOLS = {'television', 'television_inbox', 'classic_tv', 'classic_tv_1980s', 'classic_tv_1990s', 'vhstvshows', 'gorelicktv', 'smokesvhsdvrcollection'}
PUB = r"\b(nova|frontline|nature|charlie rose|austin city limits|macneil|lehrer|newshour|wall \$treet week|washington week|mystery!|masterpiece theatre|american experience|great performances|antiques roadshow|national geographic|cosmos|ken burns|wonderworks|square one|3-2-1 contact|newton's apple|the french chef|firing line|adam smith's money world|nightly business report|p\.o\.v\.|american masters|eyes on the prize|the civil war|pbs)\b"
XCOLS = {'usgovfilms', 'FedFlix', 'us_congress', 'miscellaneous-japanese-tv', 'sveriges_television', 'podcasts', 'mosaic'}
ACCESS = {'community_media', 'foxborocableaccess', 'somervillecommunityaccesstelevision', 'wcca_tv', 'ltcmediacenter', 'amherstmediaarchives', 'alternative_views', 'democracy_now_vid', 'marmia', 'waycross', 'elainesmitha', 'community_media_inbox'}
CAPS = {'access': 150, 'news': 350, 'block': 330, 'kids': 520, 'game': 420, 'music': 220, 'tech': 200, 'wrest': 120, 'movie': 160, 'pub': 160, 'prime': 400, 'soap': 120}
HOL = [('x', r"\b(christmas|xmas|holiday special|santa|rudolph|frosty|grinch|nutcracker|yule|noel)\b"), ('t', r"\b(thanksgiving|turkey day)\b"), ('h', r"\b(halloween|great pumpkin|trick or treat)\b"), ('n', r"\b(new year'?s eve|new year'?s rockin|year in review|countdown of 19\d\d)\b")]
NET = r"\b(nbc|cbs|abc|fox|wb|upn)\b"
QMAP = {'sit1': 'prime', 'sit2': 'prime', 'dra1': 'prime', 'dra2': 'prime', 'dra3': 'prime', 'sit3': 'rerun', 'game1': 'game', 'game2': 'game', 'soap': 'soap', 'talk': 'talk', 'late': 'late', 'kids1': 'kids', 'kids2': 'kids', 'kids3': 'kids', 'wrest': 'wrest', 'cook': 'cook'}
AMBIG = {'go', 'debt', 'greed', 'angel', 'hunter', 'the city', 'loving', 'capitol', 'generations', 'passions', 'the joker', 'time machine', 'shuffle', 'personals', 'studs', 'monsters', 'werewolf', 'millennium', 'profiler', 'the pretender', 'alice', 'taxi', 'benson', 'arthur', 'jackpot', 'wordplay', 'lingo', 'blockbusters', 'renegade', 'highlander', 'sliders', 'cops', 'the commish', 'matlock', 'columbo', 'jag', 'hunter', 'the mole', 'scrabble', 'boggle', 'pictionary', 'trivial pursuit', 'scattergories', 'main event', 'livewire', 'awa', 'dumbo', 'barney', 'wishbone', 'digimon', 'pokemon', 'catdog', 'the tick', 'vicki!', 'leeza', 'the view', 'dinah', 'angel', 'early edition', 'dark skies', 'earth 2', 'stingray', 'monsters', 'v the series', 'automan', 'manimal', 'riptide', 'blue thunder', 'street hawk', 'crime story', 'wiseguy', 'mike hammer', 'body language', 'think fast', 'fun house', 'finders keepers', 'the challengers', 'trump card', 'go', 'chain reaction', 'high rollers', 'sweethearts', 'now you see it', 'remote control', 'greed', 'twenty one', 'family challenge', 'debt', 'emeril', 'hometime', 'home again', 'good eats'}
EXTRA = collections.defaultdict(set)
QF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'retrotv-sources', 'harvest', 'queries2.txt')
if os.path.exists(QF):
    for line in open(QF):
        if '|' not in line: continue
        tag, expr = line.strip().split('|', 1)
        if tag not in QMAP or not expr.startswith('title:('): continue
        for q in re.findall(r'"([^"]+)"', expr):
            n = q.lower().strip()
            if n in AMBIG or len(n) < 5: continue
            EXTRA[QMAP[tag]].add(n)
CAT = list(CAT)
for name in ['rerun']:
    CAT.insert([x[0] for x in CAT].index('prime'), (name, r"\b(xxnonexx)\b"))
for name, names in EXTRA.items():
    alt = '|'.join(re.escape(x) for x in sorted(names, key=len, reverse=True))
    k = [x[0] for x in CAT].index(name)
    CAT.insert(k + 1, (name, r"(?<![\w])(" + alt + r")(?![\w])"))
for n, p in CAT:
    re.compile(p)

def clean_title(t):
    s = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', t)
    s = re.sub(r"(?i)\b(with|w/|w)\s*(original\s+)?commercials\b|\bw\.?o\.?c\.?\b|\bwoc\b|\bvhs\b|\brecording\b|\bfull broadcast\b|\boriginal broadcast\b|\bbroadcast\b|\boff[- ]air\b|\bcomplete\b|\buncut\b|\b60 ?fps\b|\b\d{3,4}p\b|\bh\.?264\b|\bx264\b|\bdvd\b|\brip\b|\bblank\b|\btape\b|\bincomplete\b|\bpartial\b|\bpart \d+\b|\bdisc \d+\b|\b\d+ hours?\b", ' ', s)
    s = re.sub(r'\b(19[89]\d|200[0-4])\b', ' ', s)
    s = re.sub(r'\b\d{1,2}[\-/.]\d{1,2}[\-/.]\d{2,4}\b|\b\d{4}[\-/.]\d{1,2}[\-/.]\d{1,2}\b', ' ', s)
    s = re.sub(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?,?', ' ', s)
    s = re.sub(r'[_|•~#*]+', ' ', s)
    s = re.sub(r'\s*[-:,;&]+\s*$', '', re.sub(r'^\s*[-:,;&]+\s*', '', s))
    s = re.sub(r'^\s*\d{1,2}[\-/.]\d{1,2}\b', ' ', s)
    s = re.sub(r'^\s*\d{2,5}\s+', ' ', s)
    s = re.sub(r'(?i)\bepisode\s*#?\d+\b|\bep\.?\s*\d+\b|\bseason \d+\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -:,.')
    s = s.upper()
    if len(s) > 34: s = s[:34].rsplit(' ', 1)[0]
    return s or None

CANON = {'price is right': 'THE PRICE IS RIGHT', 'jeopardy': 'JEOPARDY!', 'tonight show': 'THE TONIGHT SHOW', 'late show': 'LATE SHOW', 'today show': 'TODAY', 'the today show': 'TODAY', 'oprah': 'THE OPRAH WINFREY SHOW', 'donahue': 'DONAHUE', 'geraldo': 'GERALDO', 'letterman': 'LATE NIGHT WITH DAVID LETTERMAN', 'arsenio': 'THE ARSENIO HALL SHOW', 'johnny carson': 'THE TONIGHT SHOW', 'snl': 'SATURDAY NIGHT LIVE', 'cosby': 'THE COSBY SHOW', 'simpsons': 'THE SIMPSONS', 'the simpsons': 'THE SIMPSONS', '90210': 'BEVERLY HILLS, 90210', 'beverly hills': 'BEVERLY HILLS, 90210', 'cheers': 'CHEERS', 'alf': 'ALF'}
GENERIC = {'ellen', 'alf', 'amen', 'coach', 'wings', 'friends', 'cops', 'hunter', 'benson', 'webster', 'matlock', 'cheers', 'dallas', 'dynasty', 'extra', '227', 'buffy', 'martin', 'roseanne', 'cosby', 'magnum', 'newhart', 'scarecrow', 'cagney', 'airwolf', 'oprah', 'donahue', 'geraldo', 'montel', 'maury', 'dinah', 'lingo', 'jackpot', 'studs', 'personals', 'wipeout', 'the joker', 'the challengers', 'doug', 'guts', 'garfield', 'popeye', 'barney', 'wishbone', 'arthur', 'cuisine', 'chef', 'cooking', 'go', 'pyramid', 'concentration', 'scrabble', 'loving', 'capitol', 'generations', 'passions'}
def core_of(low):
    s = low.strip()
    for _ in range(4):
        s2 = re.sub(r"^\s*(\(?\d{1,4}[\-/.]\d{1,2}([\-/.]\d{2,4})?\)?|\d{4}|vhs|beta|tv|tape|recording|[kw][a-z]{2,3}(-tv)?(\s*\d+)?|abc|cbs|nbc|fox|wb|upn|channel \d+)\b[\s\-:,.]*", '', s)
        if s2 == s: break
        s = s2
    return s
def show_title(cat, low, clean):
    pat = dict(CAT).get(cat)
    if not pat or cat in ('kids', 'music', 'news', 'movie', 'block', 'weather', 'tech', 'wrest'): return clean
    m = re.search(pat, low)
    if not m: return clean
    core = core_of(low)
    nm = m.group(1)
    if not (core.startswith(nm) or core.startswith('the ' + nm)): return clean
    pat = dict(CAT).get(cat)
    if not pat or cat in ('kids', 'music', 'news', 'movie', 'block', 'weather', 'tech', 'wrest'): return clean
    m = re.search(pat, low)
    if not m: return clean
    name = CANON.get(nm, nm.upper())
    if cat == 'late':
        for k2, v2 in (('conan', "LATE NIGHT WITH CONAN O'BRIEN"), ('leno', 'THE TONIGHT SHOW WITH JAY LENO'), ('carson', 'THE TONIGHT SHOW'), ('arsenio', 'THE ARSENIO HALL SHOW'), ('letterman', 'LATE NIGHT WITH DAVID LETTERMAN')):
            if k2 in low: name = v2; break
    if cat == 'late' and 'letterman' in low and ('late show' in low or re.search(r'199[3-9]|200', low)): name = 'LATE SHOW WITH DAVID LETTERMAN'
    if clean and clean.startswith(name.replace('THE ', '', 1)[:6]) and not re.search(r'\d', clean): return clean
    ep = re.search(r'(?i)s\d+\s*e\d+\s*[-:]\s*([^\[(]+)', low)
    if ep:
        e = re.sub(r'\s+', ' ', ep.group(1)).strip(' -:').upper()
        if e and len(name) + len(e) < 40: return name + ': ' + e
    return name
def nat(s): return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]
stats = collections.Counter(); out = collections.defaultdict(list); seen = set()
for it in items:
    t = it['t']; low = (t + ' ').lower(); blob = (t + ' ' + it.get('s', '') + ' ' + it.get('ds', '')[:200]).lower()
    if it['i'].lower().startswith(('tobacco_', 'oakleytapes_')) and not has(low, r'(saturday night live|tonight show|late show|late night|entertainment tonight|today show|letterman|leno|conan)'):
        stats['excluded'] += 1; continue
    if re.search(r'[^\x00-\xff\u2010-\u2027\u2122]|[ãõçñÃÕÇÑ]', t) or re.search(r'(?<!\d)20(0[5-9]|[1-3]\d)(?!\d)', t) or has(low, X_JUNK) or has(blob, X_FOREIGN) or has(low, X_FOREIGN_T) or has(low, X_MODERN) or has(low, X_SPORT) or has(blob, X_ADULT) or has(low, X_OTHER):
        stats['excluded'] += 1; continue
    if (has(low, X_ADS) or (has(low, r'\bcommercials?\b') and not has(low, r'(with|w/|w)\s*(original\s+)?commercials|commercials included|woc'))) and not has(low, r'(christmas|thanksgiving|holiday)'):
        stats['adcomp'] += 1; continue
    date = pick_date(it)
    if it.get('force'):
        if it.get('ad'): date = it['ad']
        elif it.get('e') and 1984 <= int(it['e']) <= 2004 and not (date and date[:4] == str(it['e'])): date = str(it['e'])
        elif it['force'] == 'kids':
            sy = series_year(low + ' ' + str(it.get('q', '')))
            dy = int(date[:4]) if date else 0
            if sy:
                if sy > 2004: date = None
                elif not dy or dy < sy: date = str(max(sy, 1984))
            elif not date:
                rawy = re.match(r'(\d{4})', str(it.get('d') or ''))
                date = '1984' if (it.get('k') == 'classic' or (rawy and int(rawy.group(1)) < 1984)) else None
    if not date: date = guess_date(it); stats['guessed'] += 1
    files = [f for f in it['f'] if not re.search(r'(?i)(sample|trailer|preview|thumb)', f[0])]
    files.sort(key=lambda f: nat(f[0]))
    if not files: continue
    durs = [f[1] for f in files]; T = sum(durs)
    split = len(files) >= 3 and all(900 <= d <= 4000 for d in durs) and not all(re.match(r'(?i)^(.*/)?vts_\d+_\d+', f[0]) for f in files)
    grp = False
    if it.get('force') and not split and len(files) >= 2:
        files = [f for f in files if 240 <= f[1] <= 6000]
        if len(files) >= 2: split = True; grp = sorted(f[1] for f in files)[len(files) // 2] < 1000; durs = [f[1] for f in files]; T = sum(durs)
    if split:
        files = [f for f in files if f[1] >= (240 if grp else 900)]
    elif T < 1080 or T > 8 * 3600:
        stats['dur'] += 1; continue
    cat = it.get('force')
    core = core_of(low)
    cs0 = set() if cat else set(it.get('c') or [])
    if cs0 & XCOLS or it['i'].lower().startswith(('org.c-span', 'gov.')):
        stats['excluded'] += 1; continue
    if cat: pass
    elif it['i'].lower().startswith(('cpb-aacip', 'aapb')) or has(low, PUB) or 'open_mind' in cs0: cat = 'pub'
    elif cs0 & ACCESS or it['i'].lower().startswith('cunytv') or has(low, r'\b(selectmen|school committee|town meeting|planning board|board of selectmen|city council|community access|public access|cable access|access tv|access television)\b'): cat = 'access'
    for name, pat in ([] if cat else CAT):
        m = re.search(pat, low)
        if not m: continue
        if m.group(1) in GENERIC and not (core.startswith(m.group(1)) or core.startswith('the ' + m.group(1))): continue
        cat = name; break
    if not cat and has(blob, r'\b(cartoon|nickelodeon|saturday morning)\b'): cat = 'kids'
    if not cat:
        cs = set(it.get('c') or [])
        for name, cols in COLCAT:
            if cs & cols: cat = name; break
    if not cat:
        tvish = has(blob, r'\b(aired|airing|broadcast|recorded off|off[- ]air|w/ ?commercials|with commercials|with original commercials|woc|tv recording|television|episode|[wk][a-z]{2,3}-tv|channel \d+|local news)\b')
        if it['q'] in ('broadcast', 'desc', 'local', 'holiday') or has(low, r'commercials|woc|w/o/c|broadcast'): cat = 'block'
        elif cs & TVCOLS: cat = 'block'
        elif 'vhsvault' in cs and tvish: cat = 'block'
        else: stats['nocat'] += 1; continue
    if cat == 'movie' and T < 4200 and not split: cat = 'block'
    fl = ''.join(k for k, p in HOL if has(low, p))
    if split: fl += 'sg' if grp else 's'
    if cat == 'movie': fl += 'm'
    net = re.search(NET, low)
    net = net.group(1) if net else ''
    if not net and cat in ('prime', 'rerun', 'game', 'talk', 'soap', 'late', 'morning', 'mag', 'news'):
        core = core_of(low)
        for k, rx in NETRX:
            m2 = rx.search(low)
            if m2 and (m2.start() < 12 or core.startswith(m2.group(1))): net = k; break
        if cat == 'talk': net = 'abc' if 'the view' in low else 'syn'
        elif cat in ('game', 'mag') and not net: net = 'syn'
    title = std_title(cat, t, late_show=str(date) >= '1993-08-30')
    if cat == 'kids' and not re.search(r'(?i)\b(block|saturday morning|snick|toonami|fox kids|kids.? ?wb|nickelodeon|cartoon network|disney channel|with commercials|w/ ?commercials|woc)\b', t):
        _sy, _sn = series_name(low)
        if _sn:
            if _sy > 2004 or re.search(r'(?i)\b(movie|film)\b', t) and T > 4000: stats['excluded'] += 1; continue
            title = _sn
            if _sy and str(date)[:4] < str(_sy): date = str(max(_sy, 1984))
    if cat in ('block', 'prime', 'news') and re.match(r'(THE TONIGHT SHOW|LATE NIGHT WITH|LATE SHOW WITH|SATURDAY NIGHT LIVE|THE LATE LATE SHOW|THE ARSENIO)', title or ''): cat = 'late'
    if cat == 'news' and not re.search(r'NEWS|REPORT|NIGHTLINE|20/20|60 MINUTES|48 HOURS|DATELINE|PRIMETIME|CROSSFIRE|LARRY KING|MEET THE PRESS|FACE THE NATION|THIS WEEK|TODAY|MORNING', title or ''): cat = 'access'
    if not title: continue
    if it['i'] in seen: continue
    seen.add(it['i'])
    rec = [it['i'], title, date, [[f[0], f[1]] for f in files[:40]]]
    if fl or net: rec += ['', fl]
    if net: rec.append(net)
    out[cat].append((it.get('dl', 0), rec))
    stats[cat] += 1
res = {}
for k, v in out.items():
    v.sort(key=lambda x: -x[0])
    keep = [r for _, r in v]
    res[k] = keep
FLF = os.path.join(os.path.dirname(RAW), 'filler.json.gz')
if os.path.exists(FLF):
    paid, bb = [], []
    for x in json.load(gzip.open(FLF, 'rt', encoding='utf-8')):
        low = x['t'].lower()
        if x['q'] not in ('infomercial', 'cablefill') or has(low, X_FOREIGN_T) or has(low, X_MODERN) or re.search(r'[^\x00-\xff]', x['t']): continue
        fs = sorted([f for f in x['f'] if f[1] >= 300], key=lambda f: nat(f[0]))[:8]
        T2 = sum(f[1] for f in fs)
        date = pick_date(x)
        if not date or T2 < (1200 if x['q'] == 'infomercial' else 600) or T2 > 4 * 3600: continue
        if x['q'] == 'infomercial': paid.append([x['i'], 'PAID PROGRAMMING', date, [[f[0], f[1]] for f in fs], '', 'c'])
        else: bb.append([x['i'], 'PREVIEW CHANNEL' if re.search(r'prevue|preview|pay.per.view|ppv|guide', low) else 'COMMUNITY BULLETIN BOARD', date, [[f[0], f[1]] for f in fs], '', 'c'])
    res['paid'] = paid; res['bboard'] = bb
    print('paid', len(paid), 'bboard', len(bb))
SPF = os.path.join(os.path.dirname(RAW), 'sports.json.gz')
if os.path.exists(SPF):
    from titles import _clean, _cut
    LG = r"\b(nfl|nba|mlb|nhl|ncaa|super bowl|world series|stanley cup|finals|playoffs?|bowl|all-star|olympics?|boxing|indy 500|daytona|nascar|winston cup|masters|u\.?s\.? open|wimbledon|monday night football|final four|championship|game \d)\b"
    SJ = r"(penguins!|grouchland|tsunami|survivor|ea sports|channel 5|channel five|parade|highlights|bloopers|video game|documentary)"
    sp = []; seen2 = set()
    for i, t, d, files, lg, dl in json.load(gzip.open(SPF, 'rt', encoding='utf-8')):
        low = t.lower()
        if i in seen2 or re.search(SJ, low) or has(low, X_FOREIGN_T) or has(low, X_MODERN): continue
        dated = re.search(r'\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? (19|20)\d\d', low)
        if not (re.search(LG, low) and (dated or re.search(r'\b(vs\.?|at|game|finals|bowl|series)\b', low))): continue
        fs = sorted([f for f in files if f[1] >= 600], key=lambda f: nat(f[0]))[:12]
        if sum(f[1] for f in fs) < 3000: continue
        seen2.add(i)
        from titles import DATE
        ti = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', t); ti = DATE.sub(' ', ti); ti = re.sub(r'(?i)\b(vhs( tape)?|dvd transfer \d+|woc|with commercials|full game|full broadcast|original broadcast|\d{8})\b|\b[wk][a-z]{3}(-tv)?\b(?=\s*-)', ' ', ti)
        ti = _cut(re.sub(r'\s+', ' ', re.sub(r'^[\s\-–:,.]+|[\s\-–:,.]+$', '', re.sub(r'\s[-–]\s[-–\s]*', ' - ', ti))).upper(), 44) or lg.upper()
        if len(ti) < 6: ti = (lg.upper() + ' ' + ti).strip()
        sp.append([i, ti, d, [[f[0], f[1]] for f in fs], '', 'm'])
    res['sports'] = sp
    print('sports', len(sp), 'days', len(set(x[2] for x in sp)))
json.dump(res, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(dict(stats))
print({k: len(v) for k, v in res.items()})
import os; print('bytes', os.path.getsize(OUT))
