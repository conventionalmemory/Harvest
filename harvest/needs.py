import json, gzip, os, re, sys, time, glob, random, collections, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts')
os.makedirs(OUT, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'plan'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
FOCUS = [z.strip().lower() for z in os.environ.get('FOCUS', '').split(';') if z.strip()]
THREADS = int(os.environ.get('THREADS', '16')); BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60; T0 = time.time()
OUTF = os.path.join(OUT, 'needs.json.gz'); REPF = os.path.join(OUT, 'needs_report.json')
GUIDEF = os.path.join(here, 'needs_guide.json.gz'); GP = os.path.join(PARTS, 'needs_guide.json.gz'); CP = os.path.join(PARTS, 'needs_cands.json.gz')
SHOWS = json.load(open(os.path.join(here, 'shows_needs.json'), encoding='utf-8'))
QMAP = {'sitcom': 'prime', 'drama': 'prime', 'kids': 'kids', 'soap': 'soap', 'game': 'game', 'talk': 'talk', 'late': 'late', 'news': 'news', 'mag': 'mag', 'doc': 'pub', 'cook': 'cook', 'music': 'music', 'sports': 'sports', 'special': 'prime', 'movie-package': 'movie', 'movie': 'movie', 'relig': 'block', 'gov': 'news', 'morning': 'news', 'variety': 'prime', 'reality': 'prime', 'comedy': 'prime', 'anthology': 'prime', 'wrestling': 'wrest', 'tech': 'tech', 'shopping': 'block', 'fitness': 'block', 'infomercial': 'block', 'court': 'prime'}
OTHERQ = [(r'wrestling|wwf|wcw|nwa|titans|clash of the champions|starrcade|survivor series|royal rumble|summerslam|wrestlemania|wccw|awa|gorgeous ladies|glow', 'wrest'), (r'house of representatives|senate|press club|c-span|white house|hearings|newsfeed', 'news'), (r'shopping|qvc|psychic|amazing discoveries|prevue|body by|bodies in motion|getting fit|it figures|medical television|hour of power|700 club|infomercial', 'block'), (r'motorweek|victory garden|homeworks|shortstories|arts films', 'pub'), (r'star search|house of style|awards|grammy|telethon|pageant|apollo', 'music' if False else 'prime')]
SCRIPTED = {'sitcom', 'drama', 'kids'}
EVENT = {'sports', 'special', 'movie-package', 'movie'}
EPLEN = {'sitcom': 1080, 'drama': 2280, 'kids': 540}
TVCOL = 'television OR television_inbox OR classic_tv OR classic_tv_1980s OR classic_tv_1990s OR vhstvshows OR vhsvault OR gorelicktv OR smokesvhsdvrcollection OR sitcoms OR televisionmovies OR vhsnews OR gameshows OR dvdtray OR dvdtray_inbox OR tvarchive OR saturdaymorningcartoons OR classic_cartoons OR sports'
TVSET = set(TVCOL.split(' OR '))
DISQ = 'title:(season OR seasons OR episode OR episodes OR complete OR series OR nbc OR cbs OR abc OR fox OR pbs OR hbo OR espn OR vhs OR commercials OR woc OR pilot OR finale OR s0* OR s1* OR 1x* OR 2x* OR 3x* OR 4x* OR 5x* OR 198* OR 199* OR 2000 OR 2001 OR 2002 OR 2003 OR 2004) OR subject:(television OR sitcom OR "tv series" OR "tv show" OR nbc OR cbs OR abc OR pbs OR vhs OR commercials OR tv)'
NETRX = {'nbc': 'nbc', 'cbs': 'cbs', 'abc': 'abc', 'fox': 'fox', 'pbs': 'pbs', 'hbo': 'hbo', 'tbs': 'tbs|wtbs|superstation', 'wgn': 'wgn', 'wor': 'wor', 'usa': 'usa network|usa', 'tnt': 'tnt', 'tnn': 'tnn|nashville network', 'bet': 'bet', 'mtv': 'mtv', 'vh1': 'vh1|vh-1', 'cnn': 'cnn', 'espn': 'espn', 'cspan': 'c-span|cspan', 'c-span': 'c-span|cspan', 'a&e': 'a&e|a and e|arts and entertainment', 'discovery': 'discovery', 'disney': 'disney', 'nick': 'nick|nickelodeon', 'nickelodeon': 'nick|nickelodeon', 'nickatnite': 'nick at nite|nickelodeon', 'lifetime': 'lifetime', 'cbn': 'cbn|family channel', 'family': 'family channel|cbn', 'comedy': 'comedy central|comedy channel', 'ha': 'ha!', 'sci-fi': 'sci-fi|sci fi|scifi', 'showtime': 'showtime', 'cinemax': 'cinemax', 'tlc': 'tlc|learning channel', 'food': 'food network|tvfn', 'e!': 'e!', 'amc': 'amc|american movie classics', 'bravo': 'bravo', 'qvc': 'qvc', 'hsn': 'hsn|home shopping', 'tmc': 'movie channel|tmc', 'cartoon': 'cartoon network', 'ppv': 'ppv|pay per view|pay-per-view', 'upn': 'upn', 'g4': 'g4|g4tv|g4techtv|techtv|tech tv', 'cmt': 'cmt|country music television', 'wb': 'wb|kids wb', 'syn': 'syndicat\\w*', 'prevue': 'prevue', 'movietime': 'movietime'}
NETNAMES = {'tnt', 'amc', 'vh-1', 'vh 1', 'vh1', 'hsn', 'qvc', 'turner network television', 'american movie classics', 'home shopping network', 'braves', 'cubs', 'atlanta braves', 'chicago cubs', 'nascar', 'winston cup', 'college basketball', 'college football', 'house of representatives', 'us house of representatives', 'us senate', 'walt disney', 'oscars', 'academy awards', 'world series', 'nba finals', 'usfl', 'hbo movie', 'hbo premiere', 'hbo boxing', 'house session', 'senate session', 'miss america', 'grammy awards', 'super bowl', 'stanley cup', 'ncaa tournament', 'mtv', 'bet', 'nickelodeon', 'cnn', 'espn', 'explorer', 'mystery', 'superman', 'bozo', 'game of the week', 'late show', 'sunday morning', 'beverly hills', 'homicide', 'prime news', 'e news', 'safari', 'invention', 'real world', 'time machine', 'pov'}
JUNK = re.compile(r"\b(opening to|closing to|logos?|idents?|trailers?|teasers?|promos?|bumpers?|theme song|theme music|soundtrack|ost|reviews?|reviewed|reaction|reacts?|podcast|commentary|video essay|explained|analysis|ranking|ranked|top \d+ |fan ?made|fan ?edit|fan ?film|fanvid|amv|ytp|parody|spoof|abridged|recap|gameplay|walkthrough|playthrough|longplay|speedrun|video ?game|pc game|dos game|ps[1-5]|playstation|xbox|nintendo|sega|genesis|snes|nes|game ?boy|gba|amiga|atari|commodore|c64|pinball|slot machine|rom ?hack|emulator|lego|toys?|unboxing|action figures?|audiobook|audio book|ebook|pdf|comic book|comics|novel|screenplay|sheet music|karaoke|remix|lyrics|mixtape|twitch|tiktok|livestream|live stream|upscaled?|deepfake|supercut|mashup|clips?|scenes?|moments|excerpts?|outtakes|gag reel|slideshow|screensaver|wallpaper|rifftrax|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|german dub|fran[cç]ais|french dub|italiano|portugu[eê]s|legendado|subtitulado|vostfr|russian|polski|lektor|hindi|arabic|turkish|svenska|suomi|norsk|dansk|magyar|sub ita|sub esp|subbed|vietsub|tagalog|indonesia|xxx|porn|hentai|sermon|city council|town meeting|selectmen|school committee|board of|webinar|zoom|discord)\b")
JUNKS = re.compile(r"\b(extras|bonus|special features|featurettes?|unauthorized story|behind the camera|interviews?|panel|q&a|convention|comic-?con|reunion|tribute|retrospective|behind the scenes|making of|documentary|bloopers?|cast of|where are they now|true hollywood story|opening|intro|credits|themes?)\b")
JUNKN = re.compile(r"\b(highlights|best of|compilation)\b")
JUNKD = re.compile(r"\b(podcast|gameplay|walkthrough|let's play|longplay|fan ?film|fan ?made|video ?game|radio (show|program|broadcast)|old time radio|audio only|reaction video|public access|community television|community media|city council|school district|chamber of commerce|webinar)\b")
FOREIGN = re.compile(r"\b(parte|quarta|primeira|saison|temporada|staffel|episodio|epis[oó]dio|cap[ií]tulo|folge|piloto|serie tv|vf|pt br|dual audio|dublagem|napisy|aflevering|odcinek|b[oö]l[uü]m)\b")
SPIN = re.compile(r"\b(reboot|revival|remake|new class|college years|animated series|netflix|hulu|disney\+|paramount\+|hbo max|prime video)\b")
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
YR = re.compile(r'(?<!\d)(1[89]\d\d|20[0-3]\d)(?!\d)')
ADS = re.compile(r"\bcommercials?\b")
ADSOK = re.compile(r"\b(with|w/|w|incl\w*|plus|and|&|original|\+)\s+(the\s+)?(original\s+)?(tv\s+)?commercials?\b|\bwoc\b|\bw/c\b")
WEBID = re.compile(r"^(youtube|twitch|bliptv|tiktok|twitter|vimeo|dailymotion|rumble|roosterteeth)[-_]")
BADID = re.compile(r"spank|porn|xxx|xvideos|xhamster|onlyfans|hentai")
MOD2 = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](0[5-9]|[12]\d)\b|\b20(0[5-9]|[12]\d)[01]\d[0-3]\d\b')
TAPE = re.compile(r"\b(vhs|betamax|tape|taped|recorded|recording|commercials|woc|broadcast|aired|airing|rerun|syndicat\w*|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|tbs|wtbs|wgn|tnt|usa network|nick at nite|nickelodeon|tv land|a&e|mtv|vh1|cnn|c-span|tnn|lifetime|discovery|primetime|prime time|off air|off-air)\b")
TAPE2 = re.compile(r"\b(vhs|betamax|commercials|woc|off air|off-air|home recording)\b")
DESCEV = re.compile(r"\b(sitcom|tv series|television series|tv show|television show|television program|tv program|game show|talk show|soap opera|animated series|cartoon series|miniseries|mini-series|nbc|cbs|abc|pbs|hbo|syndicat\w*|vhs|commercials|laugh track|primetime|prime time|aired|broadcast|episodes?)\b")
SE1 = re.compile(r"\bs(?:eason)?\s?(\d{1,2})[\s._-]{0,3}(?:e|ep|episode)\s?(\d{1,3})\b|\b(\d{1,2})x\s?(\d{2,3})\b")
EPN = re.compile(r"\b(?:episode|ep)\.?\s?#?(\d{1,4})\b")
WORDN = {w: i + 1 for i, w in enumerate('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen'.split())}
WORDN.update({w: i + 1 for i, w in enumerate('first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split())})
MULTI = re.compile(r"\bseasons\b|\b(?:s|season)\s?\d{1,2}\s?(?:-|&|and|to|thru|through)\s?(?:s|season)?\s?\d{1,2}\b|complete series|all episodes|all seasons|entire series|full series|complete collection|the complete|complete show")
SEAS = re.compile(r"\bseason\s?(\d{1,2})\b|\bseason\s(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)(?:\sand\sfinal)?\sseason\b|\b(?:s|se)\s?(\d{1,2})\s?(?:e|ep|d|disc)\s?\d{1,3}\b|\bs(\d{1,2})\b|\b(\d{1,2})x\s?\d{2,3}\b")
LEAD = re.compile(r"^(?:\s*(?:\(?\d{1,4}[-./]\d{1,2}(?:[-./]\d{1,4})?\)?|(?:19|20)\d\d|vhs|beta|tape|dvd|tv|the|classic|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|mtv|tnn|tbs|usa|[wk][a-z]{2,3}(?:-tv)?(?:\s?\d{1,2})?)\b[\s\-:,.|]*)*", re.I)
TAIL = re.compile(r"^\s*(?:$|[-:|(\[,#]|\b(?:s\s?\d{1,2}\s?e\s?\d{1,3}|s\s?\d{1,2}\b|d\s?\d{1,2}\b|\d{1,2}x\s?\d{1,3}|\d{1,4}\b|\d{6}\b|\d{8}\b|season|seasons|series|episode|episodes|ep\b|eps\b|the complete|complete|full|sitcom|tv|pilot|finale|premiere|nbc|cbs|abc|fox|upn|wb|pbs|hbo|espn|mtv|tnn|tbs|wgn|usa|vhs|dvd|disc|vol|volume|tape|part|pt|with commercials|w commercials|woc|commercials|on|from|show|special|marathon|block|(?:19[4-9]\d|200[0-4])|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b)", re.I)
STOP = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'to', 'with', 'show', 'by', 'for', 'is', 'it', 'at', 'from', 'md', 'mr', 'tv', 'new'}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
RARE = set('adderly aftermash andersonville andromeda arliss arli$$ avonlea backyardigans ballykissangel berrengers bewitched bodyshaping booknotes boomtown bordertown buzzkill carnivale cavanaughs citykids columbo comicview commish counterstrike crosswits cybercops deadwood eastenders elimidate entourage fastlane felicity foofur futurama geraldo gunsmoke halloweentown hometime hornblower housesmart hughleys inquizition inuyasha kissyfur knightwatch kojak lovejoy mannix mathnet matlock moneyline motorweek mousercise mousercize nightingales nightline overhaulin pictionary pinwheel rockumentary rollergames rollerjam rolonda scattergories seaquest smallville sportscenter sportscentury starrcade summerslam superbook supercarrier tattingers tattletales teknoman tekwar thirtysomething thundercats toonheads torkelsons videopolis wildboyz wintuition witchblade wonderworks wrestlemania youthquake jeopardy donahue montel leeza marilu daria sopranos sportsworld speedweek shortstories homeworks ncis mxc flcl wccw quincy riptide dragnet laramie profiler cinematech starcade'.split()) | {'gamepro tv', 'muppet show', 'gong show', 'daily show', 'elephant show', 'bozo show', 'sinbad show', 'roseanne show', 'norm show', 'weber show', 'ellen show', 'moxy show', 'today show', 'early show', 'gossip show', 'house md', 'mr t', 'mr president', 'mr sunshine', 'mr personality', 'tv 101', 'owl tv', 'tots tv', 'real tv', 'new detectives', 'new dragnet', 'new lassie', 'new zorro', 'new wilderness'}
TREKJUNK = r"hidden frontier|new voyages|phase (ii|2)\b|of gods and men|star trek[\s:._-]*(continues|odyssey|intrepid|horizon|renegades|axanar|aurora|farragut|picard|discovery|lower decks|strange new worlds|prodigy|short treks|online|beyond(?! the farthest)|into darkness|generations|first contact|insurrection|nemesis|the motion picture|(ii|iii|iv|v|vi|vii|viii|ix|x|2|3|4|5|6|7|8|9|10)\b)|axanar|starship (exeter|farragut)|fan (film|series|production|made|cut|edit)|extended cut|wrath of khan|search for spock|voyage home|final frontier|undiscovered country|motion picture|25th anniversary|judgment rites|starfleet (command|academy)|elite force|bridge commander|armada|birth of the federation|final unity|klingon honor guard|hidden evil|dominion wars|captain s chair|captain's chair|omnipedia|encyclopedia|technical manual|interactive|cd ?-?rom|bonus|extras|special features|featurettes?|deleted|trekkies|what we left behind|the captains|captain s summit|chaos on the bridge|center seat|roddenberry|power records|peter pan|audio (drama|book|story|adventure)|read ?-?along|music from|raumschiff|viaje a las estrellas|jornada nas estrelas|patrouille|nouvelle|la s[eé]rie|\bv ?\.?f\b|german|french|italian|spanish|\bdub\b|dubbed|mst3k|cinebinge|\b(video|pc|computer|board|vhs|vcr|card|arcade) game\b|\bgame (footage|play|trailer|show)\b|\bexcerpts?\b|stoked|\bsto\b|barbary coast|trivia|my experience|celebration|\bsaga\b|cast on|hack attack|manic episodes|that time|remember when|\bis bad\b|worst|silliest|dumbest|unethical|\b(the|a) \w+ episodes? of\b|final generation|helped lure|footage|\bspecial\b|anniversary|a captain s log|captain's log|workprints?|\bmovies?\b|\bfilms?\b|box ?set|reactions?|\bnova\b"
TREKOTHER = r"next generation|next gen\b|\btng\b|deep space|\bds9\b|voyager|\bvoy\b|\bent\b|animated|\btas\b|star trek[\s:._-]*enterprise(?![\s._-]*incident)|\benterprise[\s._-]*(s\d|season|\d{1,2}x\d)"
PEAKSJUNK = r"fire walk with me|fwwm|missing pieces|the return|limited event|season (3|three)\b|\bs0?3\b|deleted|log lady|secret diary|autobiography|access guide|festival|twin perfect|explained|georgia coffee|between two worlds|slice of lynch|phenomenon|secrets from another place|postcards from|rewatch|unobscura|\bedit\b|recut|re ?-?cut|murder most foul|missing season|international (version|pilot|ending)|european (version|pilot|ending)|julee cruise|saturday night live|\bsnl\b|bonus|extras|featurettes?|\b(video|pc|computer|board|vhs|vcr|card|arcade) game\b|\bexcerpts?\b|\btapes of\b|\b1992\b|workprints?|unaired|mulholland|reactions?"
HINTS = {'Tuesday Night Titans': {'drop': ['TNT']}, 'Wonderful World of Disney': {'drop': ['Walt Disney']},
    'Star Trek': {'full': 1, 'fam': 1, 'junk': TREKJUNK + '|' + TREKOTHER, 'self': r"\btos\b|sttos|original series", 'ev': r"star trek", 'evq': '"star trek"', 'ids': ['star-trek-tos', 'startrektos', 'st-tos', 'sttos', 'tos-s0', 'tos_s0', 'star-trek-the-original', 'star-trek-original'], 'idsub': ['startrek', 'star-trek', 'star_trek', 'star.trek']},
    'Star Trek: The Animated Series': {'full': 1, 'fam': 1, 'junk': TREKJUNK, 'self': r"animated series|\btas\b|sttas|star trek[\s:._-]*(the[\s._-]*)?animated|animated adventures", 'ev': r"star trek", 'evq': '"animated series" OR "star trek animated" OR tas OR "star trek"', 'ids': ['star-trek-tas', 'startrektas', 'st-tas', 'sttas', 'tas-s0', 'star-trek-animated', 'star-trek-the-animated']},
    'Star Trek: The Next Generation': {'full': 1, 'fam': 1, 'junk': TREKJUNK, 'self': r"next generation|next gen\b|\btng\b|sttng", 'ev': r"star trek|\btng\b", 'evq': '"next generation" OR tng', 'ids': ['star-trek-tng', 'startrektng', 'st-tng', 'sttng', 'tng-s0', 'tng_s0', 'tng-0', 'tng0', 'star-trek-next-gen', 'star.-trek.-tng', 'star.-trek.-the.-next'], 'idsub': ['tng-s', 'tng_s', 'tngs0', 'sttng', 'st-tng', 'nextgeneration', 'next-generation']},
    'Star Trek: Deep Space Nine': {'full': 1, 'fam': 1, 'junk': TREKJUNK, 'self': r"deep space (nine|9)|\bds9\b|stds9|\bds 9\b", 'ev': r"star trek|\bds9\b|\bds 9\b|stds9|deep space (nine|9)", 'evq': '"deep space nine" OR "deep space 9" OR ds9 OR "ds 9"', 'ids': ['star-trek-ds9', 'startrekds9', 'st-ds9', 'stds9', 'ds9-s0', 'ds9_s0', 'ds9-0', 'ds90', 'deep-space-nine', 'deep-space-9', 'deepspacenine', 'deepspace9', 'star.-trek.-ds9', 'star.-trek.-deep'], 'idsub': ['ds9', 'deepspace9', 'deepspacenine', 'deep-space-nine', 'deep-space-9', 'deep_space_nine', 'deep_space_9', 'deep.-space']},
    'Star Trek: Voyager': {'full': 1, 'fam': 1, 'junk': TREKJUNK, 'self': r"star trek[\s:._-]*voyager|\bvoy\b|stvoy|\bvoyager[\s._-]*(s\d|season|\d{1,2}x\d)", 'ev': r"star trek|\bvoy\b", 'evq': '"star trek"', 'ids': ['star-trek-voy', 'startrekvoy', 'st-voy', 'stvoy', 'voy-s0', 'voy_s0', 'voyager-s0', 'voyager_s0', 'star.-trek.-voy'], 'idsub': ['voyager-s', 'voyager_s', 'voyagers0', 'stvoy', 'st-voy', 'voy-s', 'voy_s']},
    'Star Trek: Enterprise': {'full': 1, 'fam': 1, 'junk': TREKJUNK, 'until': '2005-12-31', 'self': r"star trek[\s:._-]*enterprise(?![\s._-]*incident)|\bent\b|stent\b|\benterprise[\s._-]*(s\d|season|\d{1,2}x\d)", 'ev': r"star trek", 'evq': '"star trek"', 'ids': ['star-trek-ent', 'startrekent', 'st-ent', 'stent', 'ent-s0', 'ent_s0', 'enterprise-s0', 'enterprise_s0', 'star.-trek.-ent'], 'idsub': ['enterprise-s', 'enterprise_s', 'enterprises0', 'st-ent', 'ent-s0']},
    'Twin Peaks': {'full': 1, 'pilot0': 1, 'junk': PEAKSJUNK, 'self': r"twin peaks", 'evq': '"twin peaks"', 'ids': ['twinpeaks', 'twin-peaks', 'twin_peaks', 'twin.-peaks', 'tp-s0'], 'idsub': ['twinpeaks', 'twin-peaks', 'twin_peaks', 'twin.peaks', 'twin.-peaks']}}
FILMS = re.compile(r"star trek (generations|first contact|insurrection|nemesis|the motion picture|into darkness|beyond|(ii|iii|iv|v|vi|vii|viii|ix|x)\b)|wrath of khan|search for spock|voyage home|final frontier|undiscovered country|\bpg 13\b|\b\dh \d+m\b|fire walk with me|feature film|theatrical")
REVIEW = re.compile(r"\b(reviews?|reviewed|reviewing|podcasts?|reacts?|reactions?|reactors?|recaps?|riffs?|riffing|rifftrax|mst3k|mistie|commentary|discussion|discuss|discusses|discussing|analysis|video essay|ranking|ranked|watch ?along|rewatch|live ?stream|fan ?films?|fan ?made|fan ?edits?|parody|spoof|music videos?|amv|tribute|trailers?|bloopers|deleted scenes|behind the scenes|making of|documentary|interviews?|convention|panel|gameplay|walkthrough|let's play|longplay|workprints?|bootleg|concert|live at)\b")
ADONLY = re.compile(r"\bcommercials?,|\bcommercial (break|block)s?\b|\bcommercials (and|from|during|block|breaks?|only|compilation)\b|\b(open|close|closing|ending|end credits|intro|outro|sign-?off|sign-?on|station id|ident|promo)$")
ABROAD = re.compile(r"\b(atv|ads|tcn|gtv|qtq|nws|hsv|tvq|sas|ntd|stw|tvw|bcv|nbn|gmv|rtq|tnq|ten|nine|seven)-(\d{1,2})\b|\b(bbc ?[1-4]|bbc one|bbc two|itv[1-4]?|channel 4|channel four|sky one|uk gold|ytv|cbc|ctv|global tv|rte|network ten|nine network|seven network)\b")
UKOK = {'pbs', 'a&e', 'bravo', 'bbca', 'bbc america', 'comedy'}
SEPS = re.compile(r"\s[-–|~]\s|[,;/|~:+]|\band\b|&|\bon\b|\bfrom\b")
CONN = re.compile(r"^\s*(in|of|at|for|to|a|an|the|is|are|was|or|'s|s|that|this|my|your|his|her)\b")
def flat(v): return ' '.join(str(a) for a in v) if isinstance(v, list) else str(v or '')
def norm(s):
    s = s.lower().replace('&', ' and ').replace('’', "'")
    s = re.sub(r"[.'!?,:*]", '', s)
    return re.sub(r'[^a-z0-9$/]+', ' ', s).strip()
def fold(t): return ''.join(ch for ch in unicodedata.normalize('NFKD', t) if not unicodedata.combining(ch))
def norm0(t): return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9]+", ' ', fold(t).lower().replace("'", '').replace('’', ''))).strip()
def clean(t): return re.sub(r'(?<=[a-z0-9]{2})\.(?=[a-z0-9]{2})', ' ', re.sub(r'[_]+', ' ', t.lower().replace('’', "'")))
def bare(t): return re.sub(r'\s*\([^)]*\)', '', t).strip() or t
def sig(n): return [w for w in re.sub(r'^the ', '', n).split() if w not in STOP]
def airdate(t):
    m = re.search(r'\b(19[89]\d|200[0-4])[-./ ](\d{1,2})[-./ ](\d{1,2})\b', t)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[-./](\d{1,2})[-./](19[89]\d|200[0-4]|[89]\d)\b', t)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = int(m.group(3)); y = y + 1900 if y < 100 else y
        return '%d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', t.lower())
    if m: return '%s-%02d-%02d' % (m.group(4), MON[m.group(1)], int(m.group(2)))
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)', t)
    if m: return '%s-%s-%s' % m.groups()
    m = re.search(r'(?<!\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(19[89]\d|200[0-4])(?!\d)', t)
    if m: return '%s-%s-%s' % (m.group(3), m.group(1), m.group(2))
    return ''
def seasons(low):
    out = set()
    for m in SEAS.finditer(low):
        g = next(x for x in m.groups() if x)
        out.add(WORDN[g] if g in WORDN else int(g))
    return sorted(out)
def one_season(low):
    if MULTI.search(low): return 0
    ss = seasons(low)
    return ss[0] if len(ss) == 1 and ss[0] > 0 else 0
def prep(sh):
    h = HINTS.get(sh['title'], {})
    raw = [bare(sh['title'])] + [a for a in sh.get('aka', []) if a not in h.get('drop', [])] + h.get('add', [])
    names = []; seenn = set()
    for a in raw:
        n = norm(bare(a)); n0 = re.sub(r'^the ', '', n)
        if not n0 or n0 in seenn or (re.fullmatch(r'[\d ]+', n0) and names): continue
        seenn.add(n0)
        sw = sig(n0)
        if n0 in NETNAMES or n0 in h.get('net', []): lvl = 3
        elif n0 in RARE: lvl = 1
        elif len(sw) <= 1 or len(n0.replace(' ', '')) <= 4: lvl = 2
        elif len(sw) == 2: lvl = 1
        else: lvl = 0
        ws = n0.split()
        rx = re.compile(r"(?<![a-z0-9])(?:the[\W_]+)?" + r"[\W_]*".join("[.'*]?".join(re.escape(ch) for ch in w) for w in ws) + r"(?![a-z0-9])")
        names.append({'n': n0, 'lvl': lvl, 'rx': rx, 'q': ' '.join(re.sub(r'["!:()\[\]{}/\\*?^~+\-]', ' ', bare(a)).split())})
    sh['names'] = names
    sh['y0'], sh['y1'] = sh['years'][0], min(sh['years'][1], 2005 if h.get('until') else 2004)
    sh['remake'] = bool(re.search(r'\((19|20)\d\d\)|\(series\)|\(fox\)', sh['title'].lower())) or bool(h.get('remake'))
    sh['cls'] = 'scripted' if sh['type'] in SCRIPTED else 'event' if sh['type'] in EVENT else 'strip'
    sh['netrx'] = re.compile(r'\b(' + NETRX[sh['net']] + r')\b') if NETRX.get(sh['net']) and sh['net'] != 'syn' else None
    sh['junk'] = re.compile(h['junk']) if h.get('junk') else None
    sh['full'] = bool(h.get('full')); sh['fam'] = bool(h.get('fam')); sh['pilot0'] = bool(h.get('pilot0')); sh['until'] = h.get('until', '2004-12-31'); sh['ids'] = h.get('ids', [])
    sh['selfrx'] = re.compile(h['self']) if h.get('self') else None
    sh['evrx'] = re.compile(h.get('ev') or h.get('self') or 'no evidence rule'); sh['idsub'] = h.get('idsub', []); sh['evq'] = h.get('evq', '')
    q = QMAP.get(sh['type'])
    if not q:
        q = 'prime'
        for pat, v in OTHERQ:
            if re.search(pat, sh['title'].lower()): q = v; break
    sh['q'] = q
    sh['ct'] = 'rerun' if sh['y1'] <= 1983 else sh['type']
for _s in SHOWS: prep(_s)
BYT = {s['title']: s for s in SHOWS}
def gettext(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read(4000000).decode('utf-8', 'replace')
        except Exception as e:
            if getattr(e, 'code', 0) in (403, 404) or k == tries - 1:
                print('fail', url[:110], e, flush=True); return ''
            time.sleep(4 * (k + 1))
def ziplist(ident, name):
    h = gettext('https://archive.org/download/' + urllib.parse.quote(ident) + '/' + urllib.parse.quote(name) + '/')
    out = []
    for row in re.split(r'<tr', h):
        m = re.search(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', row)
        if not m or not re.search(r'\.(mp4|m4v|mkv|avi|mpg|mpeg|mov|ts|wmv|webm)$', m.group(2).strip().lower()): continue
        z = re.search(r'id="size"[^>]*>\s*(\d+)', row)
        sz = int(z.group(1)) if z else max([int(v) for v in re.findall(r'(?<![\d:-])(\d{6,})(?![\d:-])', re.sub(r'<a [^>]*>', ' ', row))] or [0])
        out.append((urllib.parse.unquote(m.group(2).strip()).replace('&amp;', '&'), sz))
    print('ZIPLIST %s | %s | %d bytes of listing | %d video files | %s\n' % (ident, name, len(h), len(out), ' ## '.join(n for n, z in out[:4]) or re.sub(r'\s+', ' ', h[:300])), end='', flush=True)
    return out
def get(url, tries=4, raw=False):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            code = getattr(e, 'code', 0)
            if code == 404: return None
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep((8 if code == 429 else 3) * (k + 1))
def scrape(q, cap=20000):
    out, cursor = [], None
    while len(out) < cap:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language,description', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        for it in j.get('items') or []:
            if not isinstance(it, dict) or not it.get('identifier'): continue
            it['description'] = ' '.join(flat(it.get('description')).split())[:800]
            out.append(it)
        cursor = j.get('cursor')
        if not cursor: break
    return out
def load_ids(rows=None):
    have = {}
    for p in sorted(glob.glob(os.path.join(OUT, '*.json.gz'))):
        if p.endswith('needs.json.gz') or p.endswith('movies.json.gz'): continue
        try:
            d = json.load(gzip.open(p, 'rt', encoding='utf-8'))
            if isinstance(d, list):
                for x in d:
                    if isinstance(x, dict) and x.get('i'):
                        f = x.get('f') if isinstance(x.get('f'), list) else []
                        have[x['i']] = max(have.get(x['i'], 0), len(f))
                        if rows is not None and f and x.get('t') and isinstance(f[0], list): rows.append(x)
                    elif isinstance(x, list) and x and isinstance(x[0], str): have.setdefault(x[0], 0)
        except Exception as e: print('skip', p, e)
    return have
def load_guide(p):
    try: return json.load(gzip.open(p, 'rt', encoding='utf-8'))
    except Exception: return {}
def fetch_guides(G, todo):
    def one(sh):
        best = None
        for nm in [bare(sh['title'])] + sh.get('aka', [])[:2]:
            j = get('https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(nm)) or []
            time.sleep(0.6)
            names = {norm0(bare(sh['title']))} | {norm0(a) for a in sh.get('aka', [])}
            for r in j:
                w = r.get('show') or {}
                py = int((w.get('premiered') or '0000')[:4] or 0)
                if norm0(w.get('name', '')) in names and abs(py - sh['y0']) <= 1: best = w; break
            if best: break
        if not best: return sh['title'], {'miss': 1, 'u': sh['until']}
        w = get('https://api.tvmaze.com/shows/%d?embed[]=episodes&embed[]=cast' % best['id']) or {}
        time.sleep(0.6)
        emb = w.get('_embedded') or {}
        rows = [[e['season'], e['number'], e.get('name') or '', e['airdate'], e.get('runtime') or 0] for e in emb.get('episodes', []) if e.get('number') and e.get('airdate') and e['airdate'] <= sh['until']]
        cast = []
        for c in emb.get('cast', []):
            n = (c.get('person') or {}).get('name')
            if n and n not in cast: cast.append(n)
        return sh['title'], {'id': best['id'], 'eps': rows, 'cast': cast[:8], 'lang': best.get('language') or '', 'u': sh['until']}
    with ThreadPoolExecutor(2) as ex:
        for n, (k, g) in enumerate(ex.map(one, todo)):
            G[k] = g
            if n % 50 == 0: print('guide', n, len(todo), round((time.time() - T0) / 60, 1), 'min', flush=True)
    return G
GUIDE = load_guide(GP) or load_guide(GUIDEF)
GENT = {'pilot', 'the pilot', 'finale', 'the finale', 'the reunion', 'the wedding', 'the trip', 'the movie', 'the letter', 'the show', 'the party', 'christmas', 'thanksgiving', 'halloween'}
EP = {}
def build_ep():
    EP.clear()
    for k, g in GUIDE.items():
        rows = g.get('eps') or []
        t = {}
        for r in rows:
            s, n, nm = r[0], r[1], r[2]
            z = norm0(nm)
            if len(z) >= 9 and z not in GENT and len(z.split()) >= 2 and not re.fullmatch(r'(episode|show|part|chapter|week|day) ?#?\d+.*', z): t[z] = (s, n)
        EP[k] = {'t': sorted(t.items(), key=lambda kv: -len(kv[0])), 'd': {(r[0], r[1]): r[3] for r in rows}, 'names': {(r[0], r[1]): r[2] for r in rows}, 'maxs': max([r[0] for r in rows] or [0]), 'cast': [c.lower() for c in g.get('cast', []) if len(c.split()) >= 2], 'n': len(rows)}
        sh = BYT.get(k)
        if not sh or not sh['full']: continue
        by = {}
        for r in rows:
            nm = r[2]; m = PARTRX.search(nm); part = 0
            if m:
                pp = (m.group(1) or m.group(2) or m.group(3)).lower(); part = PNUM.get(pp) or int(pp); nm = nm[:m.start()]
            z = norm0(nm)
            if not z: continue
            d0 = by.setdefault(z, {})
            if part in d0: part = max(d0) + 1 if max(d0) else 2
            if part and 0 in d0: d0[1] = d0.pop(0)
            if not part and d0: part = max(d0) + 1
            d0[part] = (r[0], r[1])
        for z in list(by):
            z2 = re.sub(r'^(the|a|an) ', '', z)
            if z2 != z and len(z2) >= 8 and len(z2.split()) >= 2 and z2 not in by: by[z2] = by[z]
        rts = sorted(r[4] for r in rows if len(r) > 4 and r[4]); typ = rts[len(rts) // 2] if rts else 0
        split = {}; cur = collections.Counter()
        for r in rows:
            cur[r[0]] += 1; split[(r[0], cur[r[0]])] = (r[0], r[1])
            if typ and len(r) > 4 and r[4] and r[4] >= typ * 1.7: cur[r[0]] += 1; split[(r[0], cur[r[0]])] = (r[0], r[1])
        smax = collections.Counter()
        for r in rows: smax[r[0]] = max(smax[r[0]], r[1])
        eprx = re.compile(r"(?<![a-z0-9])(?:" + '|'.join(r"[\W_]+".join("[.'’]?".join(re.escape(ch) for ch in w) for w in z.split()) for z in sorted(by, key=len, reverse=True) if len(z) >= 4) + r")(?![a-z0-9])") if by else None
        EP[k].update({'by': by, 'keys': sorted(by, key=len, reverse=True), 'split': split, 'order': [(r[0], r[1]) for r in rows], 'smax': smax, 'eprx': eprx})
PARTRX = re.compile(r"[\s,:;-]*\(?\b(?:part|pt)\.?\s*(\d|i{1,3}|one|two|three)\)?\s*$|\s*\((\d)\)\s*$|(?<=[a-z.])\s+(i{1,3})\s*$", re.I)
FULLMIN = {'drama': 2280, 'kids': 1200, 'sitcom': 1080}
FULLTYP = {'drama': 2700, 'kids': 1440, 'sitcom': 1320}
NOISE = set('hd hq full episode episodes ep vhs dvd rip tv version uncut extended remastered widescreen fullscreen english eng part pt season series complete the and for with from star trek rerun broadcast original aired commercials ads woc web tvrip dvdrip bluray'.split())
SERTOK = {'tng', 'ds9', 'voy', 'tos', 'ent', 'tas', 'generation', 'nine', '9', 'voyager', 'enterprise', 'trek', 'peaks'}
GUARD = r"(?:^|\s)(?:\d{1,3}|tng|ds9|voy|tos|ent|tas|generation|nine|9|voyager|enterprise|trek|peaks)\s+"

PNUM = {'i': 1, 'ii': 2, 'iii': 3, 'one': 1, 'two': 2, 'three': 3}
QTAG = re.compile(r"\b(dvd|dvdrip|bluray|blu ray|bdrip|brrip|webrip|web dl|hdtv|sdtv|tvrip|vhsrip|x264|x265|h264|h 264|hevc|xvid|divx|aac|ac3|dts|480p|576p|720p|1080p|2160p|remastered|remaster|upscale|\d{3,4}mb)\b")
SEM = re.compile(r"\bs(?:eason)?\s?(\d{1,2})[\s._-]{0,3}(?:e|ep|episode)\s?(\d{1,3})(?:(?:\s?[-&+]\s?|\s?and\s?)(?:e|ep)?(\d{1,3})|e(\d{1,3}))?(?!\d)|(?<![a-z0-9])(\d{1,2})x(\d{2,3})(?:\s?[-&+]\s?(\d{2,3}))?(?!\d)")
FAMORDER = ['Star Trek: The Next Generation', 'Star Trek: Deep Space Nine', 'Star Trek: Voyager', 'Star Trek: Enterprise', 'Star Trek: The Animated Series', 'Star Trek']
PREFIX = re.compile(r"^(?:(?:star trek|the next generation|next generation|next gen|tng|deep space nine|deep space 9|ds9|voyager|voy|enterprise|ent|the original series|original series|tos|the animated series|animated series|tas|twin peaks|st|the complete series|complete series|season \d+|series \d+|episode \d+|ep \d+|disc \d+|vol \d+|\d+)\s+)+")
def series_of(sh, path):
    if not sh['fam']: return [sh]
    low = re.sub(r'[._]+', ' ', path.lower())
    for part in (low.rsplit('/', 1)[-1], low):
        hit = [o for o in (BYT.get(k) for k in FAMORDER) if o and o['selfrx'] and o['selfrx'].search(part)]
        if hit: return hit
    return [sh]
def parse_full(sh, text, dur, ctx):
    G = EP.get(sh['title'])
    if not G or 'by' not in G: return [], ''
    b = re.sub(r'\.(ia\.)?[a-z0-9]{2,4}$', '', text.rsplit('/', 1)[-1], flags=re.I)
    low = re.sub(r'[._]+', ' ', fold(b).lower().replace('’', "'"))
    ses = []
    for m in SEM.finditer(low):
        if m.group(1): a, b1, b2 = int(m.group(1)), int(m.group(2)), m.group(3) or m.group(4)
        else: a, b1, b2 = int(m.group(5)), int(m.group(6)), m.group(7)
        ses.append((a, b1))
        if b2 and int(b2) == b1 + 1: ses.append((a, b1 + 1))
    rem = SEM.sub(' ', low)
    m = QTAG.search(rem)
    if m and m.start() > 6: rem = rem[:m.start()]
    z0 = norm0(rem)
    z = PREFIX.sub('', z0 + ' ').strip()
    tk = G['by'].get(z); more = []; key = z if tk else ''
    zq = norm0(re.sub(r"[;:()\[\],|~&+]| - |--", ' qqsep ', rem)).split()
    def lone(k):
        for i, tok in enumerate(zq):
            if tok != k: continue
            prev = zq[i - 1] if i else 'qqsep'; nxt = zq[i + 1] if i + 1 < len(zq) else 'qqsep'
            if prev == 'qqsep' or prev.isdigit() or prev in SERTOK or nxt in ('qqsep', 'part', 'pt', 'parts'): return True
        return False
    if not tk:
        zz = ' ' + z + ' '
        for k in G['keys']:
            if len(k) < 4 or (' ' + k + ' ') not in zz: continue
            if ' ' not in k and (not ses or len(k) < 6) and not lone(k): continue
            if ' ' in k and len(k) < 8 and not ses and not re.search(GUARD + re.escape(k) + r'(?:\s|$)', z0): continue
            pos = zz.find(' ' + k + ' '); after = zz[pos + len(k) + 1:pos + len(k) + 12]
            if not tk: tk = G['by'][k]; key = k
            more.append((G['by'][k], after))
            zz = zz.replace(' ' + k + ' ', ' | ', 1)
            if ses: break
    if tk and len(more) > 1 and not ses:
        out = set()
        for d, after in more:
            pm = re.match(r"\s*(?:part|pt|parts)?\s*(\d|i{1,3}|one|two|three)\b(?:\s*(?:and|,)?\s*(\d|ii|two)\b)?", after)
            ps = [PNUM.get(q) or (int(q) if q.isdigit() else 0) for q in (pm.groups() if pm else ()) if q]
            ps = [q for q in ps if q in d]
            out |= {d[q] for q in ps} if ps else {d[min(d)]}
        return sorted(out), 't'
    long = dur >= (2400 if sh['type'] == 'kids' else 4200)
    valid = [w for w in ses if w in G['d']]
    if tk:
        vals = sorted(tk.values())
        hit = sorted({w for w in valid if w in vals})
        if hit: return (vals if long and len(vals) == 2 else hit), 't'
        if valid:
            nz = norm0(G['names'][valid[0]])
            if key and (key in nz or nz in key): return valid, 't'
        pm = re.search(r"(?:part|pt)\s*(\d|i{1,3}|one|two|three)\b|\((\d)\)|\s(i{1,3})\s*$", rem)
        if pm:
            pp = pm.group(1) or pm.group(2) or pm.group(3); part = PNUM.get(pp) or int(pp)
            if part in tk: return [tk[part]], 't'
        if len(vals) == 1 or long: return vals, 't'
        return [vals[0]], 't'
    if ses and ctx.get('shift') and all(w[0] == 1 for w in ses): ses = [(1, w[1] + 1) for w in ses]; valid = [w for w in ses if w in G['d']]
    zw = {w for w in z.split() if w not in NOISE and not w.isdigit() and len(w) > 2}
    def fits(out):
        return not zw or any(zw & set(norm0(G['names'][w]).split()) for w in out)
    if ses and any(w[0] in ctx.get('split', ()) for w in ses):
        out = sorted({G['split'][w] for w in ses if w in G['split']})
        if out and fits(out): return out, 'n'
    if valid: return (valid, 'n') if fits(valid) else ([], '')
    if ses:
        out = sorted({G['split'][w] for w in ses if w in G['split']} | {G['order'][w[1] - 1] for w in ses if w[0] == 1 and w not in G['split'] and 0 < w[1] <= len(G['order'])})
        if out and fits(out): return out, 'n'
    if sh['pilot0'] and not ses:
        if re.search(r'\bpilot\b', low): return [G['order'][0]], 't'
        am = re.search(r'\b(?:episode|ep|e)\s?#?(\d{1,2})\b', low)
        if am and int(am.group(1)) < len(G['order']): return [G['order'][int(am.group(1))]], 'n'
    return [], ''
def tag_full(sh, x):
    files = x['f']; rows = []
    ctx = {'shift': False, 'split': set()}
    if sh['pilot0']: ctx['shift'] = any(re.search(r'\bs0?1\s?e00\b|(?<![a-z0-9])1x00\b', re.sub(r'[._]+', ' ', f[0].lower())) for f in files)
    G0 = EP.get(sh['title']) or {}
    if G0.get('smax'):
        for f in files:
            for m in SEM.finditer(re.sub(r'[._]+', ' ', f[0].rsplit('/', 1)[-1].lower())):
                a, b1 = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(5)), int(m.group(6)))
                if G0['smax'].get(a) and b1 > G0['smax'][a]: ctx['split'].add(a)
    title = x['t'][len(sh['title']) + 3:] if x['t'].startswith(sh['title'] + ' - ') else x['t']
    hows = []
    for n, f in enumerate(files):
        if f[1] < FULLMIN[sh['type']]: continue
        for s2 in series_of(sh, f[0]):
            ws, how = parse_full(s2, f[0], f[1], ctx if s2 is sh else {})
            if not ws and len(files) <= 2: ws, how = parse_full(s2, title, f[1], ctx if s2 is sh else {})
            G = EP.get(s2['title']) or {}
            base = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', f[0].rsplit('/', 1)[-1]))) + ' '
            sure = how == 't' or any((' ' + nm['n'] + ' ') in base for nm in s2['names'] if nm['lvl'] <= 1) or bool(s2['selfrx'] and s2['selfrx'].search(base))
            for w in ws:
                if w in G.get('d', {}):
                    rows.append([n, 'S%02dE%02d' % w, G['d'][w], G['names'][w]] + ([s2['title']] if s2 is not sh else [])); hows.append(sure)
    if rows and sum(hows) * 2 < len(hows): rows = [r for r, h in zip(rows, hows) if h]
    if rows: x['se'] = rows
    else: x.pop('se', None)
    return rows
build_ep()
def ep_title(sh, low):
    g = EP.get(sh['title'])
    if not g or not g['t']: return None
    z = ' ' + norm0(low) + ' '
    for k, v in g['t']:
        if (' ' + k + ' ') in z: return v
    return None
def file_se(sh, text):
    low = clean(text)
    m = SE1.search(low)
    if m: return (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
    return ep_title(sh, low)
def has_cast(sh, blob):
    g = EP.get(sh['title'])
    return bool(g) and any(c in blob for c in g['cast'])
def find(sh, t):
    low = clean(t).replace('&', ' and ')
    lead = LEAD.sub('', low)
    best = None
    for nm in sh['names']:
        hd = -1
        for src in (low, lead):
            m = nm['rx'].match(src.strip())
            if m:
                rest = src.strip()[m.end():]
                ok = not re.match(r'-[a-z]', rest) and TAIL.match(rest.lstrip(" '!?.*"))
                hd = max(hd, 2 if ok else 1)
        if hd == 1 and CONN.match(rest): hd = 0
        if hd < 2 and nm['rx'].search(low):
            for part in SEPS.split(low):
                part = LEAD.sub('', part.strip()); m = nm['rx'].match(part)
                if m and TAIL.match(part[m.end():].lstrip(" '!?.*")) and not re.match(r'-[a-z]', part[m.end():]): hd = max(hd, 0.5)
            hd = max(hd, 0)
        if hd < 0: continue
        key = (-nm['lvl'], hd, len(nm['n']))
        if not best or key > best[0]: best = (key, nm, hd)
    return (best[1], best[2]) if best else (None, -1)
def strip_names(sh, low):
    for nm in sh['names']: low = nm['rx'].sub(' ', low)
    return low
def consider(sh, it, route='t'):
    t = flat(it.get('title')); low = clean(t)
    if not t or NONLAT.search(t) or FOREIGN.search(low): return None
    lang = flat(it.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return None
    nm, hd = find(sh, t)
    ident = it.get('identifier') or ''
    desc = flat(it.get('description')).lower(); subj = flat(it.get('subject')).lower()
    if not nm:
        if route == 't': return None
        blob = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', ident)) + ' ' + subj + ' ' + desc) + ' '
        nm = next((x for x in sh['names'] if x['lvl'] <= 1 and (' ' + x['n'] + ' ') in blob), None)
        if sh['full']:
            identc = norm(clean(re.sub(r'[-_.]+', ' ', ident)))
            ok = sh['evrx'].search(low + ' ' + identc) or (sh['selfrx'] and sh['selfrx'].search(subj + ' ' + identc)) or any((' ' + x['n'] + ' ') in (' ' + norm(subj) + ' ' + identc + ' ') for x in sh['names'] if x['lvl'] <= 1)
            d3 = desc[:300]
            if not ok and route in ('e', 'f'): ok = (sh['selfrx'] if route == 'f' and sh['selfrx'] else sh['evrx']).search(d3) and (route == 'f' or re.search(r'\b(episodes?|season|s\d{1,2}\s?e\d{1,2})\b', d3)) and not FILMS.search(re.sub(r'[\W_]+', ' ', fold(d3)))
            if REVIEW.search(d3): ok = False
            nm = sh['names'][0] if ok else None
        if not nm: return None
        hd = -1
    rest = strip_names(sh, low); rest0 = rest; eptf = False
    if sh['full']:
        if ident.startswith(('youtube-', 'bliptv-')) and not SE1.search(low): return None
        if (EP.get(sh['title']) or {}).get('eprx'):
            eptf = bool(EP[sh['title']]['eprx'].search(fold(rest))); rest = EP[sh['title']]['eprx'].sub(' ', fold(rest))
        if sh['junk'] and sh['junk'].search(re.sub(r'[\W_]+', ' ', fold(low))): return None
        if REVIEW.search(rest) or REVIEW.search(subj): return None
    if JUNK.search(rest) or SPIN.search(rest) or MOD2.search(t) or ADONLY.search(low.strip()) or BADID.search(ident.lower()): return None
    if ADS.search(low) and not ADSOK.search(low): return None
    if sh['cls'] == 'scripted' and WEBID.search(ident.lower()) and not SE1.search(low): return None
    if ABROAD.search(low) and sh['net'] not in UKOK and '(uk)' not in sh['title'].lower(): return None
    if sh['cls'] == 'scripted' and JUNKS.search(rest): return None
    if sh['type'] != 'sports' and sh['q'] != 'wrest' and JUNKN.search(rest) and not TAPE2.search(low): return None
    if sh['junk'] and sh['junk'].search(low): return None
    cols = it.get('collection') or []
    cols = set(cols) if isinstance(cols, list) else {cols}
    if cols & {'podcasts', 'audio', 'opensource_audio', 'radioprograms', 'oldtimeradio', 'community_media'}: return None
    y0, y1 = sh['y0'], sh['y1']
    ys = [int(y) for y in YR.findall(t)]
    ad = airdate(t)
    if ad: ys.append(int(ad[:4]))
    top = y1 if y1 >= 2004 else y1 + 1
    hi = max(top, 2004) if not sh['remake'] else top
    lo = y0 if sh['cls'] == 'scripted' or sh['ct'] == 'rerun' or sh['type'] in ('special', 'movie-package', 'movie') else max(y0, 1984)
    inrun = any(lo <= y <= top for y in ys)
    inera = any(lo <= y <= min(hi, 2004) for y in ys)
    if ys and not (inrun or inera): return None
    m = re.match(r'(\d{4})', flat(it.get('date')) or flat(it.get('year')) or '')
    iy = int(m.group(1)) if m else 0
    yt = ident.startswith('youtube-') or 'youtube' in subj[:40]
    mod = iy > max(top, 2004) or (yt and not iy)
    dated = inrun or inera or (iy and not yt and max(y0, 1984) <= iy <= min(hi, 2004)) or (iy and lo <= iy <= top)
    ss = seasons(low)
    g = EP.get(sh['title'])
    if g and g['maxs'] and ss and not MULTI.search(low) and any(n > g['maxs'] for n in ss): return None
    if not (g and g['maxs']) and ss and any(y0 + n - 1 > top for n in ss) and not MULTI.search(low): return None
    se = bool(ss) or bool(MULTI.search(low)) or bool(SE1.search(low)) or bool(re.search(r'\bcomplete\b', low))
    ept = (eptf or bool(ep_title(sh, rest0))) if sh['cls'] == 'scripted' else False
    cast = has_cast(sh, desc + ' ' + subj + ' ' + low)
    netw = bool(sh['netrx'] and sh['netrx'].search(rest + ' ' + subj + ' ' + desc[:300]))
    tape = bool(TAPE.search(rest)); tvcol = bool(cols & TVSET); dev = bool(DESCEV.search(desc + ' ' + subj))
    ctx = tape or tvcol or netw
    lvl = nm['lvl']
    if JUNKD.search(desc) and not (cast or ept): return None
    if sh['remake'] and not (inrun or cast or ept or (iy and y0 <= iy <= top)): return None
    if route != 't' and hd < 0:
        if sh['full']: return ('d', route) if not (mod and ys and not inrun) else None
        if route == 'u': return ('y', 'u') if (se or dated or tape) and not mod else ('m', 'show named outside the title only')
        if not (tape or tvcol or se): return None
        if mod and not (inera or inrun): return None
        if not (' ' + nm['n'] + ' ') in (' ' + norm(clean(re.sub(r'[-_.]+', ' ', ident)) + ' ' + subj + ' ' + desc[:400]) + ' '): return None
        return ('d', 'd')
    if sh['cls'] == 'scripted':
        m2 = EPN.search(low)
        if m2 and not ss and int(m2.group(1)) > 32 * (y1 - y0 + 1) + 10: return None
        strong = se or ept or cast
        if mod and not (strong or inrun): return ('m', 'no episode, year or network evidence') if hd == 2 and lvl <= 1 else None
        if lvl >= 2:
            if sh['full']: return ('d', 't') if hd >= 0.5 and (sh['evrx'].search(low + ' ' + norm(clean(re.sub(r'[-_.]+', ' ', ident)))) or (se and eptf)) else None
            if (cast or ept) and hd >= 0.5: return ('y', 't')
            if hd == 2 and se and (ctx or dev or inrun): return ('y', 't')
            if hd == 2 and inrun and (ctx or dev): return ('y', 't')
            if hd == 2 and (se or inrun or netw or (tvcol and dev)): return ('m', 'one-word title; show not confirmed')
            if hd == 0.5 and (inrun or inera) and ctx: return ('m', 'one-word title in a list of programs')
            return None
        if hd == 2:
            if strong or inrun or ctx or dev: return ('y', 't')
            if lvl == 0: return ('y', 't') if not mod else ('m', 'no episode, year or network evidence')
            return ('m', 'no episode, year or network evidence')
        if hd == 1:
            if strong: return ('y', 't')
            if (inrun or inera) and ctx: return ('y', 't')
            if ctx or inrun or dev: return ('y', 't') if lvl == 0 else ('m', 'title continues past the show name')
            return ('m', 'title continues past the show name') if lvl == 0 else None
        if hd == 0.5:
            if strong or ((inrun or inera) and ctx): return ('y', 't')
            if ctx or inrun or inera: return ('m', 'listed with other programs')
            return ('m', 'listed with other programs') if lvl == 0 else None
        if cast or ept: return ('y', 't')
        if lvl == 0:
            if (se or inrun or inera) and ctx: return ('y', 't')
            return ('m', 'show name inside a longer title') if ctx or se or inrun else None
        return None
    if sh['cls'] == 'strip':
        if mod and not (inrun or inera): return None
        if lvl >= 2:
            if lvl == 3 and hd >= 0.5 and ad and y0 <= int(ad[:4]) <= min(hi, 2004): return ('y', 't')
            if cast and hd >= 1: return ('y', 't')
            if hd == 2 and dated and (ctx or dev): return ('y', 't')
            if hd == 2 and (dated or netw or (se and ctx)): return ('m', 'one-word title; show not confirmed')
            if hd == 0.5 and (inrun or inera) and ctx: return ('m', 'one-word title in a list of programs')
            return None
        if hd == 2:
            if dated or ctx or se or cast: return ('y', 't')
            if dev: return ('y', 't') if lvl == 0 else ('m', 'no date or network evidence')
            return ('m', 'no date or network evidence')
        if hd == 1:
            if dated and (ctx or lvl == 0 or dev): return ('y', 't')
            if dated or ctx or cast: return ('y', 't') if lvl == 0 else ('m', 'title continues past the show name')
            return ('m', 'title continues past the show name') if lvl == 0 else None
        if hd == 0.5:
            if inrun or inera: return ('y', 't')
            return ('m', 'listed with other programs') if dated or ctx else None
        if lvl == 0:
            if (inrun or inera) and ctx: return ('y', 't')
            return ('m', 'show name inside a longer title') if dated or ctx else None
        return None
    if mod and not (inrun or inera): return None
    if lvl >= 2:
        if (inrun or inera) and hd >= 0.5 and (netw or (hd == 2 and tape)): return ('y', 't')
        if sh['type'] == 'sports' and (inrun or inera) and re.search(r'\b(vs|versus|at|game|nlcs|alcs|playoffs?|bowl)\b|@', low): return ('y', 't')
        if hd == 2 and (inrun or inera): return ('m', 'short name with a year only')
        return None
    if not dated: return ('m', 'no broadcast year') if hd == 2 and (ctx or dev) else None
    if hd >= 0.5 or ctx: return ('y', 't')
    return ('m', 'name inside a longer title')
def trim_seasons(sh, x):
    if sh['cls'] != 'scripted' or sh['full']: return 0
    g = EP.get(sh['title']) or {}
    maxs = g.get('maxs') or 0
    def late(f):
        m = SE1.search(clean(f[0].rsplit('/', 1)[-1]))
        if not m: return False
        sn = int(m.group(1) or m.group(3))
        return sn > maxs if maxs else sh['y0'] + sn - 1 > 2004
    keepf = [f for f in x['f'] if not late(f)]
    n = len(x['f']) - len(keepf)
    if n: x['f'] = keepf
    return n
def trim_full(sh, x):
    x['f'] = [f for f in x['f'] if f[1] >= FULLMIN[sh['type']]]
    if not x['f']: return set()
    ver = {r[0] for r in tag_full(sh, x)}
    pack = len(ver) * 10 >= len(x['f']) * 6
    maxs = (EP.get(sh['title']) or {}).get('maxs', 99)
    def extra(f):
        low = re.sub(r'[._]+', ' ', f[0].lower())
        if pack or (sh['junk'] and sh['junk'].search(re.sub(r'[\W_]+', ' ', fold(low)))): return True
        return any(int(m.group(1) or m.group(5)) > maxs for m in SEM.finditer(low))
    keepf = [f for n, f in enumerate(x['f']) if n in ver or not extra(f)]
    if len(keepf) < len(x['f']):
        x['f'] = keepf; ver = {r[0] for r in tag_full(sh, x)}
    return ver
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
REJ = collections.Counter(); NOF = collections.Counter()
def rej(c, why):
    REJ[why] += 1; REJ[(c['k'], why)] += 1
    if BYT[c['k']]['full'] and why != 'no playable files': print('REJID %s | %s | %s\n' % (c['k'], why, c['identifier']), end='', flush=True)
    return None
def maybe(x, why):
    if x.get('why') and why in x['why']: return
    x['keep'] = 'maybe'; x['why'] = (x['why'] + '; ' if x.get('why') else '') + why
def fname(sh, path):
    z = ' ' + norm(clean(re.sub(r'[-_.]+', ' ', path))) + ' '
    return any((' ' + nm['n'] + ' ') in z for nm in sh['names'])
def stamp(sh, x):
    t = x['t']; low = clean(t); y0, y1 = sh['y0'], sh['y1']
    ad = airdate(t) or airdate((x.get('ds') or '')[:200])
    if ad and not (y0 <= int(ad[:4]) <= max(y1 + 1, 2004)): ad = ''
    sn = one_season(low)
    ys = [int(y) for y in YR.findall(t) if y0 <= int(y) <= max(y1 + 1, 2004)]
    dy = re.match(r'(\d{4})', x.get('d') or '')
    dy = int(dy.group(1)) if dy and y0 <= int(dy.group(1)) <= min(max(y1 + 1, 2004), 2004) else 0
    sey = min([int(r[2][:4]) for r in x.get('se', []) if r[2]] or [0])
    if ad: e = int(ad[:4])
    elif sey: e = sey
    elif sn and sh['cls'] == 'scripted' and y0 + sn - 1 <= y1 + 1: e = min(y0 + sn - 1, y1)
    elif ys: e = ys[0]
    elif dy: e = dy
    else: e = y0 if sh['cls'] == 'scripted' or y0 >= 1984 else max(y0, 1984)
    if ad: x['d'] = ad
    x['ad'] = ad; x['e'] = min(e, 2004); x['y'] = str(x['e'])
    if sn: x['sn'] = sn
def meta(c):
    if BUDGET and time.time() - T0 > BUDGET: return rej(c, 'budget')
    j = get('https://archive.org/metadata/' + urllib.parse.quote(c['identifier']))
    if not j or not j.get('files'): return rej(c, 'nometa')
    if j.get('is_dark'): return rej(c, 'dark')
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return rej(c, 'restricted')
    if str(m.get('mediatype', 'movies')) != 'movies': return rej(c, 'mediatype')
    lang = flat(m.get('language')).lower()
    if lang and not re.search(r'eng|english|^en$', lang): return rej(c, 'lang')
    sh = BYT[c['k']]
    groups = {}; other = 0; alt = []
    lenby = {f.get('name'): secs(f.get('length')) for f in j['files'] if secs(f.get('length') or 0) > 0}
    for f in j['files']:
        if f.get('original') and secs(f.get('length') or 0) > 0: lenby.setdefault(f['original'], secs(f['length']))
    for f in j['files']:
        n = f.get('name', '').lower()
        if n.endswith('.mp4'):
            key = f.get('original') if f.get('source') == 'derivative' else f['name']
            groups.setdefault(key, []).append(f)
        elif re.search(r'\.(mkv|avi|mpg|mpeg|m4v|mov|ts|vob|iso|ogv|webm|wmv)$', n):
            other += 1
            if f.get('source') != 'derivative' and re.search(r'\.(mkv|m4v|mov|webm|avi)$', n): alt.append(f)
    files = []; hb = 0; est = 0
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 5)); b = g[0]
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0)) or lenby.get(key, 0)
        sz = float(b.get('size') or 0)
        if not d and sh['full'] and sz >= 6e7: d = FULLTYP[sh['type']]; est += 1
        elif not d and sz >= 4e7: d = min(7200, max(1200, sz / 1e6 / 5 * 60)); est += 1
        if d < 240: continue
        if FOREIGN.search(clean(b['name'])): continue
        if sz and sz / 1e6 / (d / 60) > 60: hb += 1; continue
        files.append([b['name'], round(d), b.get('format', '')])
    why0 = ''; whyz = ''
    if not files:
        for f in [f for f in j['files'] if f.get('name', '').lower().endswith('.zip') and float(f.get('size') or 0) >= 5e7][:40 if sh['full'] else 12]:
            for inner, sz in ziplist(c['identifier'], f['name']):
                if sz and sz < 4e7: continue
                files.append([f['name'] + '/' + inner, FULLTYP.get(sh['type']) or (min(7200, max(1200, sz / 1e6 / 5 * 60)) if sz else 1800), 'zip ' + inner.rsplit('.', 1)[-1].lower()]); est += 1
        if files: whyz = 'episodes are inside zip archives; running times not listed'
    if not files and alt:
        for f in alt:
            sz = float(f.get('size') or 0)
            d = secs(f.get('length') or 0) or ((FULLTYP.get(sh['type']) or min(7200, max(1200, sz / 1e6 / 5 * 60))) if sz >= 6e7 else 0)
            if d >= 240 and not FOREIGN.search(clean(f['name'])): files.append([f['name'], round(d), f.get('format', '')])
        if files: why0 = 'no mp4 files; other video formats only (may not play in a browser)'
    if not files:
        NOF[sh['title']] += 1
        if sh['full'] or NOF[sh['title']] <= 3: print('NOFILES', sh['title'], '|', c['identifier'], '|', flat(m.get('title'))[:60], '|', sorted(collections.Counter(f.get('name', '').rsplit('.', 1)[-1].lower()[:6] for f in j['files']).items()), [(f.get('name', '')[-40:], f.get('format'), f.get('length'), f.get('size')) for f in j['files'] if re.search(r'\.(mp4|m4v|mkv|avi|mpg|mpeg|iso|vob|ts|wmv|flv|rm|zip|rar|7z|ogv|webm|mov)$', f.get('name', '').lower())][:3], flush=True)
        return rej(c, 'no mp4 (other video only)' if other else 'no playable files' if not hb else 'bitrate too high')
    if max(f[1] for f in files) < 600: return rej(c, 'under 10 minutes')
    files.sort(key=lambda f: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', f[0])])
    title = flat(m.get('title'))[:200]
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', flat(m.get('description'))).split())
    subj = ';'.join(m['subject']) if isinstance(m.get('subject'), list) else flat(m.get('subject'))
    col = m.get('collection', []); col = [col] if isinstance(col, str) else col
    it = {'identifier': c['identifier'], 'title': title, 'description': desc[:400 if sh['full'] else 1500], 'subject': subj[:200] if sh['full'] else subj, 'collection': col, 'date': m.get('date'), 'year': m.get('year'), 'language': m.get('language')}
    v = consider(sh, it, c.get('r', 't'))
    if not v: return rej(c, 'rejected on full details')
    blob = (desc[:1500] + ' ' + subj).lower()
    x = {'i': c['identifier'], 'q': sh['q'], 't': title, 'd': flat(m.get('date')), 'y': '', 'c': col[:4], 's': subj[:200], 'ds': desc[:400], 'f': files[:1500 if sh['full'] else 500], 'dl': c.get('downloads') or 0, 'k': sh['title'], 'e': 0, 'net': sh['net'] if sh['net'] != 'syn' else '', 'ct': sh['ct'], 'pri': sh['pri'], 'ad': '', 'r': c.get('r', 't'), 'nf': len(files)}
    if c.get('held'): x['sup'] = 1
    if trim_seasons(sh, x):
        files = x['f']
        if not files or max(f[1] for f in files) < 600: return rej(c, 'later seasons only')
    if est and not whyz: x['est'] = est; maybe(x, 'running time not listed; estimated from file size')
    if why0: x['alt'] = 1; maybe(x, why0)
    if whyz: x['zip'] = 1; maybe(x, whyz)
    named = sum(1 for f in files if fname(sh, f[0]))
    g = EP.get(sh['title']); se = []; nse = 0
    one = len(files) <= 2
    if sh['full']:
        if v[0] == 'd' and find(sh, title)[1] < 0: x['t'] = (sh['title'] + ' - ' + title)[:200]
        ver = trim_full(sh, x)
        if not x['f']: return rej(c, 'no episode-length files')
        files = x['f']; se = x.get('se', []); nse = len(ver)
        if v[0] == 'd' and not (ver and len(ver) * 2 >= len(files)): return rej(c, 'files do not match the episode guide')
        if not ver:
            nm0, hd0 = find(sh, title)
            if not nm0 or nm0['lvl'] >= 2 or len(files) >= 3: return rej(c, 'files do not match the episode guide')
            maybe(x, 'no file matched the episode guide')
        elif v[0] == 'm' and len(ver) * 2 < len(files): maybe(x, v[1])
        if est: x['est'] = est; maybe(x, 'running time not listed; usual episode length assumed')
        if why0: x['alt'] = 1; maybe(x, why0)
        if whyz: x['zip'] = 1; x.pop('why', None); maybe(x, whyz)
        print('KEPT %s | %s | %d files %d matched | %s\n' % (sh['title'], x['i'], len(x['f']), len(ver), x.get('why', '')), end='', flush=True)
        stamp(sh, x)
        return x
    for n, f in enumerate(x['f']):
        b = f[0].rsplit('/', 1)[-1]
        w = file_se(sh, b) or (file_se(sh, strip_names(sh, clean(title))) if one else None)
        if not w: continue
        nse += 1
        if g and g['d']:
            if w in g['d']: se.append([n, 'S%02dE%02d' % w, g['d'][w], g['names'][w]])
        else: se.append([n, 'S%02dE%02d' % w, '', ''])
    if se: x['se'] = se
    ds = sorted(f[1] for f in files); med = ds[len(ds) // 2]
    if v[0] == 'd':
        ok = named * 2 >= len(files) or (len(se) >= 2 and len(se) * 2 >= len(files) and g and g['t'] and g['d'])
        if ok and sh['cls'] == 'scripted' and med < EPLEN[sh['type']] * 0.7: ok = False
        tl = clean(title)
        if ok: x['t'] = (sh['title'] + ' - ' + title)[:200] if find(sh, title)[1] < 0 else title
        elif TAPE2.search(tl) and len(files) <= 6 and (airdate(title) or any(1984 <= int(y) <= 2004 for y in YR.findall(title))) and not re.search(r'\b(opening|closing|previews?|trailers?|full vhs|vhs rip|home video)\b', tl): maybe(x, 'show named in the description of a tape; not confirmed')
        else: return rej(c, 'description match not confirmed by files')
    elif v[0] == 'm':
        if named * 2 >= len(files) and (nse * 2 >= len(files) or has_cast(sh, blob)) and len(files) >= 2: pass
        elif len(se) >= 3 and len(se) * 2 >= len(files) and g and g['d'] and g['t']: pass
        else: maybe(x, v[1])
    if sh['cls'] == 'scripted' and med < EPLEN[sh['type']] * 0.75: maybe(x, 'files shorter than a normal episode')
    if g and g['d'] and nse >= 3 and not se and sh['cls'] == 'scripted': maybe(x, 'episode numbers do not match the episode guide')
    if JUNKD.search(blob) and not se: maybe(x, 'description suggests it is not a broadcast')
    stamp(sh, x)
    return x
def recheck(x):
    sh = BYT.get(x.get('k'))
    if not sh: return 'show no longer listed'
    t = x['t']
    if t.startswith(sh['title'] + ' - ') and x.get('r') in ('d', 'u', 'e', 'i', 'f'):
        if sh['full'] or x['r'] == 'd': return '' if consider(sh, {'identifier': x['i'], 'title': t[len(sh['title']) + 3:], 'description': x.get('ds'), 'subject': x.get('s'), 'collection': x.get('c'), 'date': '' if x.get('ad') else x.get('d')}, x['r']) else 'no longer passes the title rules'
        return 'junk words in the title' if sh['junk'] and sh['junk'].search(clean(t[len(sh['title']) + 3:])) else ''
    it = {'identifier': x['i'], 'title': t, 'description': x.get('ds'), 'subject': x.get('s'), 'collection': x.get('c'), 'date': x.get('d')}
    v = consider(sh, it, x.get('r', 't'))
    if not v: return 'no longer passes the title rules'
    return ''
def plan():
    global GUIDE
    old = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    have = load_ids(); mine = {x['i'] for x in old}
    order = sorted(SHOWS, key=lambda s: (s['pri'], -len(s['title'])))
    oldk = collections.Counter(x['k'] for x in old)
    if FOCUS:
        prev = {}
        try: prev = {r['title']: r for r in json.load(open(REPF, encoding='utf-8')).get('shows', [])}
        except Exception: pass
        def want(s):
            if s['title'].lower() in FOCUS or ('pri%d' % s['pri']) in FOCUS or ('full' in FOCUS and s['full']): return True
            st = (prev.get(s['title']) or {}).get('status', 'MISSING')
            return ('missing' in FOCUS and st == 'MISSING') or ('thin' in FOCUS and st in ('MISSING', 'THIN')) or ('maybe' in FOCUS and st == 'MAYBE')
        order = [s for s in order if want(s)]
    todo = [s for s in order if (s['title'] not in GUIDE or (GUIDE[s['title']].get('u') != s['until'] and not s['full'])) and (s['cls'] == 'scripted' or s['type'] in ('game', 'talk', 'late', 'soap', 'mag', 'doc', 'cook', 'music', 'other', 'news'))]
    print('have', len(have), 'mine', len(mine), 'shows', len(order), 'guides to fetch', len(todo), flush=True)
    fetch_guides(GUIDE, todo)
    with gzip.open(GP, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
    build_ep()
    print('guides', sum(1 for g in GUIDE.values() if g.get('eps')), 'with episodes', sum(1 for g in GUIDE.values() if g.get('miss')), 'not found', flush=True)
    DIAG = collections.defaultdict(list); DREJ = collections.defaultdict(list)
    fams = [s for s in SHOWS if s['fam']]
    def one(sh):
        res = {}; xres = []
        yrs = ' OR '.join(str(y) for y in range(max(sh['y0'], 1980), min(max(sh['y1'] + 1, 2004), 2004) + 1))
        for nm in sh['names']:
            ph = nm['q'].replace('"', '')
            base = 'mediatype:movies AND title:("%s")' % ph
            qs = []
            if nm['lvl'] >= 2: qs.append((base + ' AND (' + DISQ + ' OR collection:(' + TVCOL + ') OR title:(' + yrs + '))', 't'))
            else:
                qs.append((base, 't'))
                qs.append(('mediatype:movies AND subject:("%s")' % ph, 't'))
                ws = nm['n'].replace('/', ' ').split()
                if len(''.join(ws)) >= 8:
                    qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(sorted({sep.join(ws) + '*' for sep in ('-', '_', '.', '')})) + ') AND NOT title:("%s")' % ph, 'i'))
                qs.append(('mediatype:movies AND "%s" AND NOT title:("%s") AND (collection:(%s) OR title:(vhs OR tape OR commercials OR recorded OR episodes OR season OR complete OR series))' % (ph, ph, TVCOL), 'd'))
            if nm is sh['names'][0] and sh['ids']: qs.append(('mediatype:movies AND identifier:(' + ' OR '.join(x + '*' for x in sh['ids']) + ')', 'i'))
            if nm is sh['names'][0] and sh['idsub']: qs.append(('mediatype:movies AND identifier:(' + ' OR '.join('*' + x + '*' for x in sh['idsub']) + ')', 'i'))
            if sh['full'] and nm['lvl'] <= 1: qs.append(('mediatype:movies AND "%s" AND NOT title:("%s")' % (ph, ph), 'd'))
            if nm is sh['names'][0] and sh['full']:
                G = EP.get(sh['title']) or {}
                tl = sorted({re.sub(r'["\\()\[\]{}:!?*^~/]', ' ', PARTRX.sub('', n2)).strip() for n2 in G.get('names', {}).values()})
                tl = [t2 for t2 in tl if len(t2) >= 10 and len(t2.split()) >= 2]
                for b0 in range(0, len(tl), 8): qs.append(('mediatype:movies AND title:(' + ' OR '.join('"%s"' % t2 for t2 in tl[b0:b0 + 8]) + ')', 'e'))
                ta = sorted({re.sub(r'["\\()\[\]{}:!?*^~/]', ' ', PARTRX.sub('', n2)).strip() for n2 in G.get('names', {}).values()})
                ta = [t2 for t2 in ta if len(t2) >= 3]
                if sh['evq']:
                    for b0 in range(0, len(ta), 10): qs.append(('mediatype:movies AND (' + ' OR '.join('"%s"' % t2 for t2 in ta[b0:b0 + 10]) + ') AND (' + sh['evq'] + ')', 'f'))
            for qq, route in qs:
                try: hits = scrape(qq, 8000 if nm['lvl'] >= 2 else 20000)
                except Exception as e: print('search error', repr(e), qq[:100], flush=True); hits = []
                st = [len(hits), 0, 0, 0, 0]
                for it in hits:
                    i = it.get('identifier')
                    if not i or i in res: continue
                    if i in mine: st[1] += 1; continue
                    if i in have:
                        st[2] += 1
                        if not (sh['full'] or have[i] in (30, 60)): continue
                    try: v = consider(sh, it, 'd' if route == 'i' else route)
                    except Exception as e: print('skip', i, repr(e)); v = None
                    if v:
                        res[i] = (it, v, nm); st[3 if v[0] == 'y' else 4] += 1
                        continue
                    if sh['fam']:
                        for o in fams:
                            if o is sh: continue
                            try: v = consider(o, it, 'd' if route in ('i', 'e', 'f') else route)
                            except Exception: v = None
                            if v:
                                xres.append((o, i, it, v, find(o, flat(it.get('title')))[0] or o['names'][0])); break
                        if v: continue
                    if len(DREJ[sh['title']]) < 2000: DREJ[sh['title']].append((it.get('downloads') or 0, route, i, flat(it.get('title'))[:90]))
                DIAG[sh['title']].append((route, st, qq[:120]))
        return sh, res, xres
    seen = {}; per = collections.Counter()
    def rank(v, nm): return (0 if v[0] == 'y' else 1 if v[0] == 'm' else 2, nm['lvl'], -len(nm['n']))
    def add(sh, i, it, v, nm, up=0):
        r = rank(v, nm)
        if i in seen and seen[i]['rk'] <= r: return
        seen[i] = {'identifier': i, 'downloads': it.get('downloads') or 0, 'k': sh['title'], 'pri': sh['pri'], 'r': 'u' if up else v[1] if v[0] != 'm' else 't', 'rk': r}
        if i in have: seen[i]['held'] = 1
    with ThreadPoolExecutor(20) as ex:
        for n, (sh, res, xres) in enumerate(ex.map(one, order)):
            for i, (it, v, nm) in res.items(): add(sh, i, it, v, nm)
            for o, i, it, v, nm in xres:
                if i not in mine: add(o, i, it, v, nm)
            if n % 50 == 0: print('search', n, len(order), len(seen), round((time.time() - T0) / 60, 1), 'min', flush=True)
    want = {s['title'] for s in order}
    fulls = [s for s in order if s['full']]
    if fulls:
        cols = scrape('mediatype:collection AND (title:("star trek") OR title:("deep space nine") OR title:("twin peaks") OR identifier:(*startrek* OR *star-trek* OR *ds9* OR *twinpeaks* OR *twin-peaks*))', 300)
        ncol = 0
        for col in [c2 for c2 in cols if not c2['identifier'].startswith(('fav-', 'ArchiveIt'))][:60]:
            ct = flat(col.get('title')); hits = scrape('mediatype:movies AND collection:(%s)' % col['identifier'], 4000); acc = 0
            for it in hits:
                i = it.get('identifier')
                if not i or i in seen or i in mine: continue
                it = dict(it, subject=flat(it.get('subject')) + ' ; ' + ct)
                for o in fulls:
                    try: v = consider(o, it, 't') or consider(o, it, 'd')
                    except Exception: v = None
                    if v:
                        add(o, i, it, v, find(o, flat(it.get('title')))[0] or o['names'][0]); acc += 1; ncol += 1; break
            print('COLLECTION', col['identifier'], '|', ct[:60], '| items', len(hits), 'candidates', acc, flush=True)
        print('collection candidates', ncol, 'from', len(cols), 'collections', flush=True)
    src = sorted([x for x in old if x['k'] in want and x.get('nf', 1) >= 4 and x.get('keep') != 'maybe' and x.get('r') != 'u'], key=lambda x: (x.get('pri', 3), -x.get('nf', 1)))[:1200]
    ups = collections.Counter()
    def upl(x):
        j = get('https://archive.org/metadata/' + urllib.parse.quote(x['i']) + '/metadata') or {}
        return flat((j.get('result') or {}).get('uploader'))
    with ThreadPoolExecutor(8) as ex:
        for u in ex.map(upl, src):
            if u and '@' in u: ups[u] += 1
    nup = 0
    for n, (u, cnt) in enumerate(ups.most_common(300)):
        hits = scrape('mediatype:movies AND uploader:("%s")' % u, 8000); acc = 0
        if len(hits) >= 8000: continue
        for it in hits:
            i = it.get('identifier')
            if not i or i in seen or i in mine: continue
            t = flat(it.get('title'))
            for sh in order:
                if i in have and not (sh['full'] or have[i] in (30, 60)): continue
                nm, hd = find(sh, t)
                if not nm or hd < 0.5 or nm['lvl'] >= 2: continue
                try: v = consider(sh, it, 't')
                except Exception: v = None
                if v:
                    add(sh, i, it, v, nm, up=1 if v[0] == 'y' else 0); acc += 1; nup += 1; break
        print('UPLOADER', n, 'packs', cnt, 'items', len(hits), 'candidates', acc, flush=True)
    print('uploader candidates', nup, 'from', len(ups), 'uploaders', flush=True)
    for c in seen.values(): per[c['k']] += 1; c.pop('rk')
    cands = sorted(seen.values(), key=lambda x: (x['pri'], x['r'] != 't', -x['downloads']))
    print('candidates', len(cands), 'by route', sorted(collections.Counter(c['r'] for c in cands).items()), 'by pri', sorted(collections.Counter(c['pri'] for c in cands).items()), flush=True)
    for sh in order:
        k = sh['title']
        print('PLAN pri%d %-9s cand %5d | %s' % (sh['pri'], sh['type'], per[k], k))
        for route, st, qq in DIAG[k]: print('  Q %s hits %d mine %d elsewhere %d yes %d maybe %d | %s' % ((route,) + tuple(st) + (qq,)))
        for dl, route, i, t in sorted(set(DREJ[k]), key=lambda r: (r[1] != 't', -r[0]))[:150 if sh['full'] else 6 if sh['pri'] > 1 else 12]: print('  REJ %s %6d | %s | %s' % (route, dl, i[:40], t))
    for c in cands:
        if BYT[c['k']]['full']: print('CAND', c['k'], '|', c['r'], '| held' if c.get('held') else '|', c['identifier'])
    with gzip.open(CP, 'wt', encoding='utf-8') as f: json.dump(cands, f, separators=(',', ':'))
def run_meta():
    cands = json.load(gzip.open(CP, 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
    res = []
    def safe(c):
        try: return meta(c)
        except Exception as e:
            print('error', c['identifier'], repr(e), flush=True); return rej(c, 'error')
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(safe, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'needs-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res), 'of', len(cands))
    print('REJECT', sorted(((k, v) for k, v in REJ.items() if isinstance(k, str)), key=lambda kv: -kv[1]))
    per = collections.defaultdict(list)
    for k, v in REJ.items():
        if isinstance(k, tuple): per[k[0]].append('%s %d' % (k[1], v))
    for k in sorted(per): print('REJSHOW', k, '|', '; '.join(sorted(per[k])))
def hours(L): return round(sum(sum(f[1] for f in x['f']) for x in L) / 3600)
def merge():
    old0 = json.load(gzip.open(OUTF, 'rt', encoding='utf-8')) if os.path.exists(OUTF) else []
    held = []; other = load_ids(held); old = []
    def dup(x): return x['i'] in other and not (x.get('sup') and len(x['f']) > other[x['i']] and (x.get('se') or not BYT[x['k']]['full']))
    for x in old0:
        why = 'held in another catalog file' if dup(x) else recheck(x)
        if why: print('DROP', x['k'], '|', x['i'], '|', x['t'][:80], '|', why)
        else: old.append(x)
    have = {x['i'] for x in old}; add = []
    for p in sorted(glob.glob(os.path.join(PARTS, 'needs-[0-9]*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in have and not dup(x): have.add(x['i']); add.append(x)
    res = old + add
    for x in res:
        sh = BYT[x['k']]; x['q'] = sh['q']; x['pri'] = sh['pri']; x['ct'] = sh['ct']
        f0 = [f[0] for f in x['f']]
        if trim_seasons(sh, x):
            if not x['f']: x['drop'] = 1; print('DROP', x['k'], '|', x['i'], '|', x['t'][:80], '| later seasons only')
            pos = {f[0]: n for n, f in enumerate(x['f'])}
            x['se'] = [[pos[f0[r[0]]]] + r[1:] for r in x.get('se', []) if r[0] < len(f0) and f0[r[0]] in pos]
            if not x['se']: x.pop('se')
        if sh['full']:
            f0 = list(x['f']); trim_full(sh, x)
            if not x['f']: x['f'] = f0
            if not x.get('se') and not x.get('keep'): maybe(x, 'no file matched the episode guide')
            if x.get('se') and x.get('why') == 'no file matched the episode guide': x.pop('keep'); x.pop('why')
            nv = len({r[0] for r in x.get('se', [])})
            if (not nv and (len(x['f']) >= 3 or x.get('r') != 't')) or (x.get('r') != 't' and nv * 2 < len(x['f'])): x['drop'] = 1; print('DROP', x['k'], '|', x['i'], '|', x['t'][:80], '| files do not match the episode guide')
    res = [x for x in res if not x.pop('drop', 0)]
    fulls = sorted([s for s in SHOWS if s['full']], key=lambda s: -len(s['title']))
    cov = {s['title']: {'held': {}, 'new': {}, 'est': {}} for s in fulls}
    def credit(x, where):
        for r in x.get('se', []):
            k = r[4] if len(r) > 4 else x['k']
            if k in cov: cov[k][where].setdefault(r[1], []).append(x['i'])
    for x in res:
        if BYT[x['k']]['full'] and not x.get('keep'): credit(x, 'new')
        elif BYT[x['k']]['full'] and (x.get('est') or x.get('alt')) and x.get('se'): credit(x, 'est')
    quick = re.compile('|'.join(sorted({re.escape(nm['n']) for s in fulls for nm in s['names'] if nm['lvl'] <= 1}, key=len, reverse=True)) or 'no full shows')
    for x in held:
        t = flat(x.get('t')); low = clean(t)
        if not quick.search(norm(low)) or NONLAT.search(t) or FOREIGN.search(low): continue
        for sh in fulls:
            nm, hd = find(sh, t)
            if not nm or nm['lvl'] >= 2 or (sh['junk'] and (sh['junk'].search(low) or sh['junk'].search(re.sub(r'[\W_]+', ' ', fold(low))))) or JUNK.search(strip_names(sh, low)): continue
            y = {'i': x['i'], 't': t, 'k': sh['title'], 'f': [f for f in x['f'] if isinstance(f, list) and len(f) > 1 and isinstance(f[0], str) and isinstance(f[1], (int, float)) and f[1] >= FULLMIN[sh['type']]]}
            if y['f'] and tag_full(sh, y):
                credit(y, 'held'); print('HELD', sh['title'], '|', x['i'], '|', t[:70], '|', len(x['f']), 'files', len(y['se']), 'episodes')
            break
    coverage = {}
    print('COVERAGE TABLE')
    for sh in sorted(fulls, key=lambda s: s['title']):
        g = EP.get(sh['title']) or {}; c = cov[sh['title']]
        codes = ['S%02dE%02d' % w for w in g.get('order', [])]
        got = set(c['held']) | set(c['new'])
        miss = [k for k in codes if k not in got]
        soft = [k for k in miss if k in c['est']]
        per = collections.OrderedDict()
        for k in codes:
            v = per.setdefault(k[:3], [0, 0]); v[1] += 1; v[0] += k in got
        coverage[sh['title']] = {'episodes': len(codes), 'held_elsewhere': len(set(c['held']) & set(codes)), 'in_this_file': len(set(c['new']) & set(codes)), 'covered': len(codes) - len(miss), 'seasons': {k: '%d/%d' % tuple(v) for k, v in per.items()}, 'missing': [[k, g['names'][(int(k[1:3]), int(k[4:6]))]] for k in miss], 'missing_but_in_doubtful_items': soft}
        print('  COVER %-32s episodes %3d held elsewhere %3d here %3d covered %3d missing %3d | %s' % (sh['title'], len(codes), len(set(c['held']) & set(codes)), len(set(c['new']) & set(codes)), len(codes) - len(miss), len(miss), ' '.join('%s %d/%d' % (k, v[0], v[1]) for k, v in per.items())))
        if not codes: print('  COVER', sh['title'], 'no episode guide loaded')
        for k in miss: print('    MISSING', sh['title'], k, '|', g['names'][(int(k[1:3]), int(k[4:6]))], '| only in an item kept as maybe (no running time listed or no mp4)' if k in soft else '')
        only = [k for k in codes if k in c['new'] and k not in c['held']]
        print('    NEWLY COVERED', sh['title'], len(only), ' '.join(only))
    with gzip.open(OUTF, 'wt', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    if GUIDE:
        with gzip.open(GUIDEF, 'wt', encoding='utf-8') as f: json.dump(GUIDE, f, ensure_ascii=False, separators=(',', ':'))
    print('merged old', len(old0), 'kept', len(old), 'added', len(add), 'total', len(res), 'hours', hours(res), 'maybe', sum(1 for x in res if x.get('keep')))
    by = collections.defaultdict(list)
    for x in res: by[x['k']].append(x)
    rows = []
    for sh in sorted(SHOWS, key=lambda s: (s['pri'], s['title'])):
        L = by.get(sh['title'], []); sure = [x for x in L if not x.get('keep')]
        g = EP.get(sh['title']) or {}
        eps = set()
        loose = 0
        for x in sure:
            got = {r[1] for r in x.get('se', [])}
            eps |= got
            if not got: loose += sum(1 for f in x['f'] if f[1] >= EPLEN.get(sh['type'], 900) * 0.75)
        n = len(eps) + loose
        ge = g.get('n', 0)
        if sh['full'] and ge: st = 'FOUND' if coverage[sh['title']]['covered'] >= ge else 'THIN'
        elif not L: st = 'MISSING'
        elif not sure: st = 'MAYBE'
        elif sh['cls'] == 'scripted': st = 'FOUND' if n >= max(4, min(20, 0.15 * ge)) else 'THIN'
        else: st = 'FOUND' if n >= 5 else 'THIN'
        rows.append({'title': sh['title'], 'pri': sh['pri'], 'type': sh['type'], 'net': sh['net'], 'years': sh['years'], 'guide_episodes': ge, 'items': len(L), 'maybe': len(L) - len(sure), 'files': sum(len(x['f']) for x in L), 'hours': hours(L), 'episodes': len(eps), 'other_files': loose, 'status': st})
    tot = {}
    for p in (0, 1, 2, 3):
        R = [r for r in rows if r['pri'] == p]
        tot[str(p)] = {'shows': len(R), **{s.lower(): sum(1 for r in R if r['status'] == s) for s in ('FOUND', 'THIN', 'MAYBE', 'MISSING')}, 'items': sum(r['items'] for r in R), 'hours': sum(r['hours'] for r in R)}
    json.dump({'updated': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'items': len(res), 'hours': hours(res), 'priority': tot, 'coverage': coverage, 'shows': rows}, open(REPF, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('PRIORITY TABLE')
    for p in ('0', '1', '2', '3'): print('  pri', p, tot[p])
    print('SHOW TABLE')
    for r in rows: print('  %-7s pri%d %-9s items %4d maybe %4d files %5d hours %5d eps %4d/%-4d other %4d | %s' % (r['status'], r['pri'], r['type'], r['items'], r['maybe'], r['files'], r['hours'], r['episodes'], r['guide_episodes'], r['other_files'], r['title']))
    print('era years', sorted(collections.Counter(str(x['e']) for x in res).items()))
    print('categories', sorted(collections.Counter(x['q'] for x in res).items()))
    print('maybe reasons', collections.Counter(x.get('why') for x in res if x.get('keep')).most_common(12))
    random.seed(len(res))
    for x in res:
        if BYT[x['k']]['full']: print('FULL', x['k'], '|', x['i'], '|', x['t'][:70], '|', len(x['f']), 'files', len(x.get('se') or []), 'episodes', '| sup' if x.get('sup') else '|', x.get('why', ''))
    for label, L in (('NEW', add), ('ALL', res), ('MAYBE', [x for x in res if x.get('keep')])):
        for x in random.sample(L, min(60, len(L))): print('SAMPLE', label, x['q'], '|', x['k'], '|', x['t'][:80], '|', x['i'][:40], '|', round(sum(f[1] for f in x['f']) / 60), 'min', '|', len(x['f']), 'files', len(x.get('se') or []), 'eps', '|', x['e'], '|', x.get('why', ''))
if MODE == 'plan': plan()
elif MODE == 'meta': run_meta()
else: merge()
