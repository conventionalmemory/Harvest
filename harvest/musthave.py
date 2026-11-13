import json, gzip, os, re, sys, time, random, urllib.parse, urllib.request, collections
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '14'))
CAP = int(os.environ.get('CAP', '150'))
LOOK = int(os.environ.get('LOOK', '450'))
RAWF = os.path.join(OUT, 'raw.json.gz')
have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8'))) if os.path.exists(RAWF) else set()
MUST = {'rocko', 'doug', 'renstimpy', 'rugrats', 'heman', 'pokemon', 'mummies', 'tmnt'}
MHF = os.path.join(OUT, 'musthave.json.gz')
old = json.load(gzip.open(MHF, 'rt', encoding='utf-8')) if os.path.exists(MHF) else []
have |= set(x['i'] for x in old)
prev = collections.Counter(x['q'] for x in old)
SHOWS = [
 ('rocko', ["rocko's modern life", "rockos modern life", "rocko modern life"], r'static cling'),
 ('doug', ["nickelodeon doug", "doug nickelodeon", "doug funnie", "brand spanking new doug", "disney's doug", "disneys doug", "doug season", "doug complete", "doug episodes", "doug nicktoons", "doug 1991", "doug 1996", "doug's 1st movie", "doug's first movie", "doug vhs", "doug dvd"], r'annotated|best movies|worst movies|favorite|doug (walker|demuro|stanhope|ford|benson|polk|casey|tennapel)|dougie'),
 ('renstimpy', ["ren and stimpy", "ren & stimpy", "ren stimpy"], r'adult party|reboot'),
 ('rugrats', ["rugrats"], r'2021|reboot|all grown up|paramount|pre-?school daze|without rugrats'),
 ('realmonsters', ["real monsters"], ''),
 ('heyarnold', ["hey arnold"], r'jungle movie'),
 ('angrybeavers', ["angry beavers"], ''),
 ('catdog', ["catdog"], ''),
 ('kablam', ["kablam"], ''),
 ('thornberrys', ["wild thornberrys", "thornberrys"], ''),
 ('rocketpower', ["rocket power"], ''),
 ('spongebob', ["spongebob squarepants", "spongebob"], r'20(0[5-9]|[12]\d)|season (0?[4-9]|1\d)\b|s(0[4-9]|1\d)e|(fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth) season|kamp koral|patrick star show|sponge on the run|musical'),
 ('zim', ["invader zim"], r'florpus'),
 ('oddparents', ["fairly oddparents", "fairly odd parents"], r'fairly odder|new wish|20(0[5-9]|[12]\d)'),
 ('neutron', ["jimmy neutron"], r'planet sheen'),
 ('heman', ["he-man", "he man and the masters", "masters of the universe"], r'2002|200x|2021|revelation|revolution|new adventures of he-man|motu origins'),
 ('shera', ["she-ra", "she ra princess"], r'princesses of power|2018|netflix'),
 ('thundercats', ["thundercats"], r'2011|roar'),
 ('beastwars', ["beast wars", "beast machines"], ''),
 ('transformers', ["transformers g1", "transformers generation 1", "the transformers 1984", "the transformers season", "transformers 1984", "transformers 1985", "transformers 1986", "transformers the movie 1986", "transformers armada", "transformers robots in disguise 2001", "transformers headmasters", "the transformers"], r'animated 2007|prime|cyberverse|earthspark|rescue bots|bayverse|bumblebee|2007|age of extinction|dark of the moon|revenge of the fallen|last knight|rise of the beasts|war for cybertron'),
 ('gijoe', ["g.i. joe", "gi joe"], r'renegades|sigma 6|resolute|rise of cobra|retaliation|snake eyes'),
 ('silverhawks', ["silverhawks"], ''),
 ('mask', ["m.a.s.k.", "mask 1985", "mask cartoon", "mask animated series", "mask the animated series"], ''),
 ('voltron', ["voltron"], r'legendary defender|voltron force|2016'),
 ('robotech', ["robotech"], r'shadow chronicles|love live alive'),
 ('bravestarr', ["bravestarr"], ''),
 ('centurions', ["centurions"], r'centurions of rome'),
 ('dinoriders', ["dino-riders", "dino riders"], ''),
 ('visionaries', ["visionaries knights", "visionaries 1987", "visionaries cartoon", "visionaries episode", "visionaries complete"], ''),
 ('inhumanoids', ["inhumanoids"], ''),
 ('galaxyrangers', ["galaxy rangers"], ''),
 ('jayce', ["jayce and the wheeled warriors"], ''),
 ('thundarr', ["thundarr"], ''),
 ('pokemon', ["pokemon", "pokémon"], r'20(0[5-9]|[12]\d)|diamond|pearl|black (and|&) white|\bxy\b|sun (and|&) moon|journeys|horizons|sinnoh|unova|kalos|alola|galar|battle frontier|origins|generations|twilight wings|darkrai|arceus|giratina|zoroark|lucario|manaphy|ranger|art guide|sprites|detective pikachu|season (0?[89]|[12]\d)\b|chronicles'),
 ('dragonball', ["dragon ball z", "dragonball z", "dbz", "dragon ball", "dragonball"], r'super|kai\b|daima|heroes|evolution|battle of gods|resurrection|broly 2018|sparking|xenoverse|budokai'),
 ('sailormoon', ["sailor moon"], r'crystal|eternal|cosmos|viz'),
 ('digimon', ["digimon"], r'data squad|savers|fusion|xros|adventure tri|adventure 2020|last evolution|ghost game|appmon|20(0[5-9]|[12]\d)'),
 ('yugioh', ["yu-gi-oh", "yugioh"], r'gx|5d|zexal|arc-v|vrains|sevens|go rush|abridged'),
 ('cardcaptors', ["cardcaptors", "cardcaptor sakura"], r'clear card'),
 ('gundamwing', ["gundam wing", "mobile suit gundam", "g gundam"], r'seed|00|unicorn|iron-blooded|witch from mercury|build fighters'),
 ('tenchi', ["tenchi muyo", "tenchi universe", "tenchi in tokyo"], ''),
 ('outlawstar', ["outlaw star"], ''),
 ('bebop', ["cowboy bebop"], r'netflix|2021'),
 ('ronin', ["ronin warriors"], ''),
 ('speedracer', ["speed racer"], r'next generation|2008'),
 ('astroboy', ["astro boy"], r'2009'),
 ('starblazers', ["star blazers"], r'2199|2202'),
 ('gforce', ["battle of the planets", "g-force guardians of space"], ''),
 ('pizzacats', ["samurai pizza cats"], ''),
 ('teknoman', ["teknoman"], ''),
 ('monsterrancher', ["monster rancher"], ''),
 ('medabots', ["medabots"], ''),
 ('zoids', ["zoids"], r'wild|genesis'),
 ('yuyu', ["yu yu hakusho"], r'netflix|2023'),
 ('kenshin', ["rurouni kenshin", "samurai x"], r'2023|live action'),
 ('bigo', ["the big o"], ''),
 ('trigun', ["trigun"], r'stampede'),
 ('toonami', ["toonami", "saturday anime", "midnight run"], r'20(1[2-9]|2\d)|rewind'),
 ('animefilm', ["akira 1988", "ghost in the shell 1995", "ninja scroll", "vampire hunter d", "fist of the north star", "project a-ko", "macross", "lupin the third", "castle of cagliostro", "my neighbor totoro", "kiki's delivery service", "princess mononoke"], r'stand alone complex|arise|2017|sac_2045'),
 ('mummies', ["mummies alive", "mummies alive the legend begins"], ''),
 ('extremegb', ["extreme ghostbusters"], ''),
 ('reboot', ["reboot season", "reboot 1994", "reboot complete", "reboot episode", "reboot mainframe", "reboot the series", "reboot s0"], r'guardian code'),
 ('streetsharks', ["street sharks"], ''),
 ('mightymax', ["mighty max"], ''),
 ('exosquad', ["exosquad", "exo-squad"], ''),
 ('gargoyles', ["gargoyles"], ''),
 ('roadrovers', ["road rovers"], ''),
 ('bigguy', ["big guy and rusty"], ''),
 ('mib', ["men in black the series", "men in black: the series", "men in black animated"], ''),
 ('godzilla', ["godzilla the series", "godzilla: the series"], ''),
 ('tmnt', ["teenage mutant ninja turtles", "tmnt 1987", "ninja turtles 1987", "tmnt"], r'2012|2018|rise of the|mutant mayhem|tales of the|fast forward|back to the sewer|turtles forever|out of the shadows|2014|2016|2007|cowabunga collection|shredder.s revenge'),
 ('batman', ["batman the animated series", "batman: the animated series", "batman tas", "new batman adventures", "batman beyond", "the batman 2004", "mask of the phantasm"], r'caped crusader|brave and the bold|beware the batman'),
 ('xmen', ["x-men the animated series", "x-men: the animated series", "x-men 1992", "x-men tas", "pryde of the x-men", "x-men evolution", "x-men: evolution"], r"97|wolverine and the x-men"),
 ('spiderman', ["spider-man the animated series", "spider-man: the animated series", "spider-man 1994", "spider-man tas", "spider-man and his amazing friends", "spider-man unlimited", "spider-man 1981"], r'spectacular|ultimate|2017|freshman'),
 ('superman', ["superman the animated series", "superman: the animated series", "superman tas"], ''),
 ('justiceleague', ["justice league 2001", "justice league season", "justice league animated", "justice league unlimited", "justice league secret origins"], r'action|snyder|2017|crisis'),
 ('superfriends', ["super friends", "superfriends", "super powers team"], ''),
 ('ironman', ["iron man 1994", "iron man the animated series", "iron man: the animated series", "marvel action hour"], r'armored adventures'),
 ('fantastic4', ["fantastic four 1994", "fantastic four the animated series", "fantastic four: the animated series", "fantastic four 1978", "fantastic four 1967"], r"world's greatest"),
 ('hulk', ["incredible hulk 1996", "incredible hulk animated", "incredible hulk the animated series", "incredible hulk 1982"], ''),
 ('silversurfer', ["silver surfer 1998", "silver surfer the animated series", "silver surfer animated", "silver surfer: the animated series"], ''),
 ('staticshock', ["static shock"], ''),
 ('teentitans', ["teen titans 2003", "teen titans season", "teen titans complete", "teen titans s0"], r'go!|go '),
 ('tick', ["the tick 1994", "the tick animated", "the tick season", "the tick the animated series", "the tick fox kids", "the tick vs"], r'2016|amazon|2001 live'),
 ('wildcats', ["wildc.a.t.s", "wildcats 1994", "wildcats animated"], ''),
 ('savagedragon', ["savage dragon"], ''),
 ('ultraforce', ["ultraforce"], ''),
 ('planeteers', ["captain planet"], ''),
 ('darkwing', ["darkwing duck"], ''),
 ('freakazoid', ["freakazoid"], ''),
 ('swampthing', ["swamp thing 1991", "swamp thing animated", "swamp thing the animated series", "swamp thing cartoon"], ''),
 ('toxic', ["toxic crusaders"], ''),
 ('bucky', ["bucky o'hare", "bucky ohare"], ''),
 ('bikermice', ["biker mice from mars"], r'2006'),
 ('powerrangers', ["mighty morphin power rangers", "power rangers zeo", "power rangers turbo", "power rangers in space", "power rangers lost galaxy", "power rangers lightspeed", "power rangers time force", "power rangers wild force", "power rangers ninja storm", "power rangers dino thunder"], r'2017|once (and|&) always'),
 ('vrtroopers', ["vr troopers"], ''),
 ('beetleborgs', ["beetleborgs"], ''),
 ('maskedrider', ["masked rider 1995", "saban's masked rider", "sabans masked rider", "masked rider saban"], ''),
 ('sybersquad', ["superhuman samurai syber-squad", "superhuman samurai", "syber-squad"], ''),
]
DS = lambda t: '(description:(%s) OR subject:(%s))' % (t, t)
ALT = {
 'doug': (['title:(doug) AND ' + DS('nickelodeon OR nicktoons OR "jumbo pictures" OR funnie OR quailman OR "disney\'s doug" OR "one saturday morning"'), 'creator:("jumbo pictures")', 'title:("how did i get into this mess" OR "doug christmas story" OR "mayonnaise for me" OR "bags a neematoad" OR "dog\'s date" OR quailman OR "doug funnie" OR "doug s01" OR "doug s02" OR "doug s03" OR "doug s04" OR "doug season" OR "doug complete series" OR "doug the complete" OR "disney\'s doug" OR "brand spanking new doug" OR "doug nickelodeon" OR "nickelodeon doug")', 'description:("doug funnie" OR quailman OR "skeeter valentine" OR "patti mayonnaise" OR "porkchop") AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR vhstvshows OR classic_tv_1990s OR opensource_movies)'], r' doug | dougs |quailman', r'nickelodeon|nicktoons|\bnick\b|disney|jumbo|funnie|quailman|cartoon|animated|skeeter|porkchop'),
 'superman': (['title:(superman) AND ' + DS('"animated series" OR "kids wb" OR "bruce timm" OR tas OR "1996"'), 'title:("superman tas" OR "superman animated" OR "superman s01" OR "superman s02" OR "superman s03" OR "superman 1996")'], r' superman ', r'animated series|kids.? ?wb|\btas\b|timm|1996'),
 'justiceleague': (['title:("justice league") AND ' + DS('animated OR "cartoon network" OR 2001 OR "bruce timm" OR unlimited'), 'title:("justice league s01" OR "justice league s02" OR "justice league unlimited s0" OR "justice league complete" OR "jlu")'], r' justice league | jlu ', r'animated|cartoon network|2001|timm|unlimited|season|s0\d'),
 'ironman': (['title:("iron man") AND ' + DS('1994 OR "animated series" OR "marvel action hour" OR "fox kids"'), 'title:("iron man tas" OR "iron man s01" OR "iron man s02" OR "iron man animated")'], r' iron man ', r'1994|animated|action hour|fox kids|cartoon'),
 'tick': (['title:(tick) AND ' + DS('"fox kids" OR animated OR "ben edlund" OR cartoon OR 1994'), 'title:("the tick s01" OR "the tick s02" OR "the tick s03" OR "the tick complete" OR "the tick cartoon" OR "tick animated")'], r' the tick | tick animated ', r'fox kids|animated|edlund|cartoon|1994|season|s0\d'),
 'freakazoid': (['title:(freakazoid)', 'description:(freakazoid) AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR vhstvshows OR classic_tv_1990s)'], r' freakazoid ', ''),
 'exosquad': (['title:(exosquad OR "exo squad" OR "exo-squad")', DS('exosquad') + ' AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR vhstvshows)'], r' exosquad | exo squad ', ''),
 'beastwars': (['title:("beast wars" OR "beast machines" OR beasties)'], r' beast wars | beast machines | beasties ', ''),
 'bikermice': (['title:("biker mice")', DS('"biker mice"') + ' AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR vhstvshows)'], r' biker mice ', ''),
 'visionaries': (['title:(visionaries) AND ' + DS('knights OR hasbro OR 1987 OR cartoon OR animated OR sunbow')], r' visionaries ', r'knights|hasbro|1987|cartoon|animated|sunbow'),
 'wildcats': (['title:(wildcats OR "wild c.a.t.s" OR "wildc.a.t.s" OR "wild cats") AND ' + DS('animated OR 1994 OR cartoon OR "jim lee" OR nelvana OR cbs')], r' wildcats | wildc a t s | wild c a t s | wild cats ', r'animated|1994|cartoon|jim lee|nelvana'),
 'shera': (['title:("she-ra" OR "she ra" OR shera OR "secret of the sword" OR "princess of power")'], r' she ra | shera | secret of the sword | princess of power ', ''),
 'silverhawks': (['title:(silverhawks OR "silver hawks")'], r' silverhawks | silver hawks ', ''),
 'realmonsters': (['title:("real monsters" OR aaahh OR "aaahh!!!")', DS('"real monsters"') + ' AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR vhstvshows)'], r' real monsters | aaahh ', ''),
 'bucky': (['title:("bucky o\'hare" OR "bucky ohare" OR "toad wars" OR "bucky o hare")'], r' bucky o ?hare | bucky ohare | toad wars ', ''),
 'hulk': (['title:(hulk) AND ' + DS('1996 OR "animated series" OR upn OR 1982 OR cartoon'), 'title:("incredible hulk s01" OR "incredible hulk s02" OR "hulk 1996" OR "hulk animated")'], r' hulk ', r'1996|animated|upn|1982|cartoon'),
 'silversurfer': (['title:("silver surfer")'], r' silver surfer ', ''),
 'teentitans': (['title:("teen titans")'], r' teen titans ', ''),
}
XREJ = {'superman': r'fleischer|194\d|returns|man of steel|lois (and|&) clark|smallville|doomsday|unbound|serial|1948|1978|quest for peace|superman (ii|iii|iv)\b|george reeves|adventures of superman', 'justiceleague': r'action|snyder|\bwar\b|dark|doom|throne|flashpoint|gods and monsters|new frontier|\bvs\b|2017|crisis|movie', 'ironman': r'armored|2008|2010|2013|iron man [23]\b|mcu|1966|rise of technovore', 'hulk': r'2003|2008|ang lee|hogan|lou ferrigno|bill bixby|1977|1978|ragnarok|agents of smash|she-hulk|vs\b', 'silversurfer': r'rise of|2007', 'teentitans': r'go!|\bgo\b|judas contract|trouble in tokyo 20', 'tick': r'2016|2017|amazon|live.action|warburton|deer tick|ticks?\b.*(bite|lyme)', 'doug': r'doug (walker|demuro|stanhope|ford|benson|polk|casey|tennapel|swisher|herman|e doug|loves movies)|dougie|annotated|best movies|worst movies|favorite|podcast', 'shera': r'princesses of power|2018|netflix', 'visionaries': r'tedx|podcast|interview', 'wildcats': r'football|basketball|high school|kentucky|wrestling|game\b'}
GBAD = r"\b(minecraft|nostalgia critic|critic|arcade|all scenes|download links|fan wiki|mod showcase|inbetweens|banned|svenskt|filipino|ces dessins|tour|fly casting|swisher|herman|smithsonian|japanese|mega evolution|speedruns?|tas run|how to|why i|worst|best of 20\d\d|secret galaxy|letsplay|reconstruction|ramble|tournament|guide|rant|debut|20(0[5-9]|[12]\d)|amv|abridged|review|reviews|reaction|reacts|parody|fan ?dub|fandub|fan ?edit|fan ?made|fan film|ytp|youtube poop|soundtrack|ost|theme song|opening|intro|outro|ending|credits|trailer|teaser|promo|commercial|commercials|toy|toys|unboxing|gameplay|walkthrough|longplay|playthrough|let'?s play|speedrun|rom ?hack|nes|snes|genesis game|game boy|gba|nds|ps1|ps2|n64|gamecube|xbox|pc game|video game|podcast|interview|panel|convention|documentary|making of|behind the scenes|tribute|music video|remix|cover|karaoke|audiobook|comic|manga|scanlation|storyboard|animatic|pitch|pilot pitch|lost media search|creepypasta|analysis|explained|ranking|top \d+|tier list|vlog|stream|livestream|bootleg game|mugen|cosplay|deleted scenes|bloopers)\b"
GFOR = r"\b(capitulo|cap[ií]tulo|episodio|epis[oó]dio|temporada|el|la|los|las|del|de|una|homenaje|napisy|lektor pl|rus|desafio|latino|castellano|espa[nñ]ol|spanish|dublado|portugu[eê]s|brasil|deutsch|german|fran[cç]ais|french|vf|vostfr|italiano|italian|ita|polski|polish|lektor|dubbing pl|russian|рус|magyar|hungarian|svenska|swedish|norsk|dansk|suomi|nederlands|dutch|greek|turkish|türkçe|arabic|hindi|tamil|telugu|tagalog|indonesia|malay|korean|cantonese|mandarin|hebrew|romana|cesky|czech|raw|subbed|sub ?only|eng ?sub|english sub|fansub|subtitled|japanese audio|jpn|jap dub|uk vhs|pal)\b"
BLK = r'\b(nickelodeon|nicktoons|snick|nick|saturday morning|cartoons?|toonami|fox kids|kids.? ?wb|cartoon network|usa cartoon express|disney afternoon|vhs)\b'
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q, mx=6000):
    out, cursor = [], None
    while len(out) < mx:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,downloads,language,collection', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor: break
    return out
def norm(s):
    s = str(s).lower().replace('&', ' and ').replace('é', 'e')
    s = re.sub(r"[’'`!]", '', s)
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s).strip() + ' '
def langok(l):
    if not l: return True
    if isinstance(l, list): l = ' '.join(map(str, l))
    l = str(l).lower()
    return bool(re.search(r'eng|english|^en$|\ben\b', l))
PH = {tag: ([norm(p).strip() for p in ph], rj) for tag, ph, rj in SHOWS}
def okold(x):
    tl = x['t'].lower().replace('_', ' '); nt = norm(x['t']); ph, rj = PH.get(x['q'], ([], ''))
    if x['q'] == 'transformers' and re.search(r' beast wars | beast machines ', nt): x['q'] = 'beastwars'
    xr = XREJ.get(x['q'], '')
    if xr and re.search(xr, tl): return False
    if x['q'] == 'doug' and not re.search(r' doug | dougs |quailman', nt): return False
    if x['i'].startswith('youtube-') or re.search(GBAD, tl) or re.search(GFOR, tl) or (rj and re.search(rj, tl)): return False
    return any((' ' + p + ' ') in nt for p in ph) or bool(re.search(BLK, tl))
n_old = len(old); old = [x for x in old if okold(x)]; prev = collections.Counter(x['q'] for x in old)
print('old kept', len(old), 'of', n_old, flush=True)
cands = {}
stat = collections.Counter()
for tag, phrases, rej in SHOWS:
    if prev[tag] >= CAP: continue
    ors = ' OR '.join('"%s"' % p for p in phrases)
    qs = [('t', 'title:(%s) AND mediatype:movies' % ors)]
    if tag in MUST: qs.append(('d', '(subject:(%s) OR description:(%s)) AND mediatype:movies AND collection:(vhskids OR childrenstelevision OR saturdaymorningcartoons OR vhsvault OR television OR classic_tv_1990s OR classic_tv_1980s OR vhstvshows OR animationandcartoons OR cartoonnetwork OR nickelodeon OR toonami)' % (ors, ors)))
    acc = conf = ''
    if tag in ALT:
        aq, acc, conf = ALT[tag]
        qs += [('a', '(%s) AND mediatype:movies' % q) for q in aq]
    xr = XREJ.get(tag, '')
    np = [norm(p).strip() for p in phrases]
    n0 = n1 = 0
    for kind, q in qs:
        for it in scrape(q):
            n0 += 1
            i = it['identifier']
            if i in have or i in cands or i.startswith('youtube-'): continue
            t = it.get('title') or ''
            if isinstance(t, list): t = ' '.join(t)
            tl = str(t).lower().replace('_', ' '); nt = norm(t)
            hit = any((' ' + p + ' ') in nt for p in np)
            if kind == 't' and not hit: continue
            if kind == 'd' and not hit and not re.search(BLK, tl): continue
            if kind == 'a' and not hit and not re.search(acc, nt) and not re.search(BLK, tl): continue
            if re.search(GBAD, tl) or re.search(GFOR, tl) or re.search(r'[^\x00-ɏ‐-‧]', t): stat['rej_title'] += 1; continue
            if (rej and re.search(rej, tl)) or (xr and re.search(xr, tl)): stat['rej_reboot'] += 1; continue
            if not langok(it.get('language')): stat['rej_lang'] += 1; continue
            cands[i] = {'identifier': i, 'q': tag, 'downloads': it.get('downloads') or 0, 'conf': conf if (kind == 'a' and not hit) else ''}
            n1 += 1
    print('search', tag, 'hits', n0, 'kept', n1, flush=True)
by = collections.defaultdict(list)
for c in cands.values(): by[c['q']].append(c)
todo = []
for tag, L in by.items():
    L.sort(key=lambda x: -x['downloads']); todo += L[:LOOK]
print('lookups', len(todo), 'of', len(cands), flush=True)
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    if not langok(m.get('language')): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(map(str, desc))
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(map(str, subj))
    blob = (str(subj) + ' ' + str(desc)[:300]).lower()
    if re.search(r'\b(latino|castellano|dublado|doblaje|deutsch|fran[cç]ais|italiano|fansub|subbed|japanese audio|raw japanese|gameplay|longplay|fan ?edit|abridged)\b', blob): return None
    if it.get('conf') and not re.search(it['conf'], (str(m.get('title', '')) + ' ' + blob + ' ' + ' '.join(map(str, m.get('collection', []) if isinstance(m.get('collection'), list) else [m.get('collection', '')]))).lower()): return None
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
        if d < 240: continue
        if re.search(r'(?i)(sample|trailer|preview|promo|opening|intro|credits)', b['name']): continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (d / 60) > 30: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files or sum(f[1] for f in files) < 600: return None
    files.sort(key=lambda f: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', f[0])])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    return {'i': it['identifier'], 'q': it['q'], 't': str(m.get('title', ''))[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': ' '.join(str(desc).split())[:400], 'f': files[:60], 'dl': it['downloads']}
res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, todo)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), flush=True)
keep, per = list(old), collections.Counter(x['q'] for x in old)
for r in sorted(res, key=lambda x: -x['dl']):
    if per[r['q']] >= CAP: continue
    per[r['q']] += 1; keep.append(r)
with gzip.open(MHF, 'wt', encoding='utf-8') as f:
    json.dump(keep, f, ensure_ascii=False, separators=(',', ':'))
print(dict(stat))
print('TABLE show items files hours')
for tag, _, _ in SHOWS:
    L = [r for r in keep if r['q'] == tag]
    nf = sum(len(r['f']) for r in L); hrs = sum(sum(f[1] for f in r['f']) for r in L) / 3600
    print('ROW %-14s %4d %5d %7.1f %s' % (tag, len(L), nf, hrs, 'THIN' if len(L) < 5 else ''), flush=True)
random.seed(7)
for r in random.sample(keep, min(50, len(keep))): print('SAMPLE', r['q'], '|', r['t'][:80], '|', r['d'][:10], '|', len(r['f']), 'files', round(sum(f[1] for f in r['f']) / 60), 'min |', r['i'][:50])
for tag in sorted(MUST | set(ALT)):
    for r in [x for x in keep if x['q'] == tag][:10]: print('MUST', tag, '|', r['t'][:80], '|', len(r['f']), 'files', round(sum(f[1] for f in r['f']) / 60), 'min | dl', r['dl'])
print('done', len(keep))
