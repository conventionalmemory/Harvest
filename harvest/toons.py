import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog')
os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '16'))
LIMIT = int(os.environ.get('LIMIT', '45000'))
CAP = int(os.environ.get('CAP', '250'))
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
T0 = time.time()
RAWF = os.path.join(OUT, 'raw.json.gz')
have = set()
if os.path.exists(RAWF):
    have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8')))
print('existing', len(have), flush=True)

ERA = [
 ('he-man', ['he-man', 'he man and the masters', 'masters of the universe']), ('she-ra', ['she-ra', 'she ra princess']), ('transformers', ['transformers']), ('gi joe', ['g.i. joe', 'gi joe']),
 ('thundercats', ['thundercats']), ('silverhawks', ['silverhawks']), ('mask', ['m.a.s.k.']), ('voltron', ['voltron']), ('robotech', ['robotech']), ('jem', ['jem and the holograms']),
 ('inspector gadget', ['inspector gadget']), ('heathcliff', ['heathcliff']), ('care bears', ['care bears']), ('my little pony', ["my little pony 'n friends", 'my little pony n friends', 'my little pony and friends', 'my little pony tales', 'my little pony 1984', 'my little pony 1986', 'my little pony vhs', 'my little pony g1']), ('rainbow brite', ['rainbow brite']),
 ('smurfs', ['smurfs']), ('snorks', ['snorks']), ('muppet babies', ['muppet babies']), ('real ghostbusters', ['real ghostbusters']), ('garfield', ['garfield and friends']),
 ('alvin', ['alvin and the chipmunks']), ('ducktales', ['ducktales', 'duck tales']), ('rescue rangers', ['rescue rangers']), ('talespin', ['talespin', 'tale spin']), ('darkwing duck', ['darkwing duck']),
 ('goof troop', ['goof troop']), ('gummi bears', ['gummi bears']), ('gargoyles', ['gargoyles']), ('tiny toon', ['tiny toon']), ('animaniacs', ['animaniacs']), ('pinky and the brain', ['pinky and the brain']),
 ('freakazoid', ['freakazoid']), ('batman tas', ['batman the animated series', 'batman: the animated', 'adventures of batman & robin', 'batman beyond']), ('superman tas', ['superman the animated series', 'superman: the animated']),
 ('x-men', ['x-men animated', 'x-men the animated', 'x-men: the animated', 'x-men evolution', 'x-men 1992']), ('spider-man', ['spider-man the animated', 'spider-man: the animated', 'spider-man and his amazing friends', 'spider-man 1994', 'spider-man unlimited']),
 ('tmnt', ['teenage mutant ninja turtles', 'tmnt']), ('bucky ohare', ["bucky o'hare"]), ('cops', ['c.o.p.s.']), ('bravestarr', ['bravestarr']), ('dino-riders', ['dino-riders', 'dino riders']),
 ('captain planet', ['captain planet']), ('swat kats', ['swat kats']), ('biker mice', ['biker mice from mars']), ('mighty max', ['mighty max']), ('exosquad', ['exosquad', 'exo-squad']), ('reboot', ['reboot mainframe', 'reboot season', 'reboot episode', 'reboot s0']),
 ('beast wars', ['beast wars']), ('sonic', ['sonic the hedgehog', 'adventures of sonic', 'sonic satam', 'sonic underground']), ('super mario', ['super mario bros super show', 'super mario bros. super show', 'super mario world cartoon', 'adventures of super mario bros']),
 ('captain n', ['captain n']), ('zelda', ['legend of zelda cartoon', 'legend of zelda animated', 'legend of zelda 1989']), ('dragon ball z', ['dragon ball z', 'dragonball z']), ('sailor moon', ['sailor moon']), ('pokemon', ['pokemon indigo', 'pokemon season 1', 'pokemon season 2', 'pokemon season 3', 'pokemon season 4', 'pokemon season 5', 'pokemon johto', 'pokemon orange', 'pokemon master quest', 'pokemon s01', 'pokemon s02', 'pokemon s03', 'pokemon s04', 'pokemon s05', 'pokemon kids wb', 'pokemon 1998', 'pokemon 1999', 'pokemon 2000']), ('digimon', ['digimon']),
 ('rugrats', ['rugrats']), ('doug', ["doug nickelodeon", "disney's doug", 'brand spanking new doug', 'doug season', 'doug episode']), ('ren & stimpy', ['ren & stimpy', 'ren and stimpy']), ('rocko', ["rocko's modern life"]), ('real monsters', ['real monsters']),
 ('hey arnold', ['hey arnold']), ('angry beavers', ['angry beavers']), ('catdog', ['catdog']), ('spongebob', ['spongebob squarepants season 1', 'spongebob squarepants season 2', 'spongebob squarepants season 3', 'spongebob season 1', 'spongebob season 2', 'spongebob season 3', 'spongebob s01', 'spongebob s02', 'spongebob s03', 'spongebob 1999', 'spongebob 2000', 'spongebob 2001', 'spongebob 2002', 'spongebob 2003', 'spongebob 2004', 'spongebob vhs', 'spongebob nickelodeon']), ('dexter', ["dexter's laboratory", "dexter's lab"]), ('johnny bravo', ['johnny bravo']),
 ('powerpuff', ['powerpuff girls']), ('cow and chicken', ['cow and chicken']), ('courage', ['courage the cowardly dog']), ('ed edd', ['ed, edd', 'ed edd n eddy']), ('space ghost', ['space ghost coast to coast']),
 ('2 stupid dogs', ['2 stupid dogs']), ('the tick', ['the tick animated', 'the tick 1994', 'the tick cartoon', 'the tick season']), ('eek', ['eek! the cat', 'eek the cat', 'eek!stravaganza']), ("bobby's world", ["bobby's world"]), ('life with louie', ['life with louie']),
 ('recess', ["disney's recess", 'recess season', 'recess episode', 'recess s0']), ('pepper ann', ['pepper ann']), ('arthur', ['arthur pbs', 'arthur season', 'arthur episode', 'arthur s0']), ('magic school bus', ['magic school bus']),
 ('denver', ['denver the last dinosaur']), ('pound puppies', ['pound puppies']), ('wuzzles', ['wuzzles']), ('get along gang', ['get along gang']), ('dungeons', ['dungeons & dragons cartoon', 'dungeons and dragons cartoon', 'dungeons & dragons animated', 'dungeons and dragons animated']),
 ('centurions', ['centurions']), ('galaxy rangers', ['galaxy rangers']), ('gobots', ['gobots']), ('inhumanoids', ['inhumanoids']), ('visionaries', ['visionaries knights']), ('pac-man', ['pac-man cartoon', 'pac-man animated', 'pac-man 1982']),
 ('beetlejuice', ['beetlejuice animated', 'beetlejuice cartoon', 'beetlejuice the animated']), ('ghostbusters filmation', ['filmation ghostbusters', "filmation's ghostbusters"]), ('teddy ruxpin', ['teddy ruxpin']), ('kissyfur', ['kissyfur']),
 ('mighty mouse', ['mighty mouse the new adventures', 'mighty mouse: the new']), ('bonkers', ['bonkers']), ('aladdin', ['aladdin the series', 'aladdin: the series']), ('timon', ['timon & pumbaa', 'timon and pumbaa']), ('quack pack', ['quack pack']), ('mighty ducks', ['mighty ducks animated', 'mighty ducks the animated']),
 ('hercules', ['hercules the animated', 'hercules: the animated']), ('earthworm jim', ['earthworm jim']), ('street sharks', ['street sharks']), ('extreme ghostbusters', ['extreme ghostbusters']), ('men in black', ['men in black the series', 'men in black: the series']),
 ('jackie chan', ['jackie chan adventures']), ('static shock', ['static shock']), ('justice league', ['justice league animated', 'justice league season', 'justice league 2001']), ('teen titans', ['teen titans 2003', 'teen titans season']), ('samurai jack', ['samurai jack']),
 ('kim possible', ['kim possible']), ('fairly oddparents', ['fairly oddparents', 'fairly odd parents']), ('jimmy neutron', ['jimmy neutron']), ('invader zim', ['invader zim']), ('rocket power', ['rocket power']), ('wild thornberrys', ['wild thornberrys']),
 ('as told by ginger', ['as told by ginger']), ('kablam', ['kablam']), ('oh yeah', ['oh yeah! cartoons']), ('what a cartoon', ['what a cartoon']), ('i am weasel', ['i am weasel']), ('sheep', ['sheep in the big city']), ('mike lu og', ['mike, lu & og', 'mike lu and og']),
 ('yu-gi-oh', ['yu-gi-oh']), ('cardcaptors', ['cardcaptors']), ('gundam wing', ['gundam wing']), ('ronin warriors', ['ronin warriors']), ('histeria', ['histeria']), ('road rovers', ['road rovers']), ('taz-mania', ['taz-mania', 'tazmania']),
 ('sylvester tweety', ['sylvester and tweety mysteries', 'sylvester & tweety mysteries']), ('garfield specials', ['garfield special']), ('peanuts', ['charlie brown and snoopy show']), ('fraggle animated', ['fraggle rock animated', 'fraggle rock: the animated']),
]
CLASSIC = [
 ('looney tunes', ['looney tunes', 'merrie melodies', 'bugs bunny', 'daffy duck', 'road runner show', 'porky pig']), ('tom and jerry', ['tom and jerry', 'tom & jerry']), ('flintstones', ['flintstones']), ('jetsons', ['jetsons']),
 ('scooby-doo', ['scooby-doo', 'scooby doo']), ('yogi', ['yogi bear', "yogi's"]), ('popeye', ['popeye']), ('woody woodpecker', ['woody woodpecker']), ('pink panther', ['pink panther show', 'pink panther cartoon']),
 ('rocky and bullwinkle', ['rocky and bullwinkle', 'rocky & bullwinkle', 'bullwinkle show']), ('underdog', ['underdog']), ('speed racer', ['speed racer']), ('jonny quest', ['jonny quest']), ('super friends', ['super friends', 'superfriends']),
 ('schoolhouse rock', ['schoolhouse rock']), ('huckleberry hound', ['huckleberry hound']), ('top cat', ['top cat']), ('wacky races', ['wacky races']), ('josie', ['josie and the pussycats']), ('fat albert', ['fat albert']),
 ('casper', ['casper the friendly ghost', 'casper cartoon']), ('mighty mouse classic', ['mighty mouse playhouse', 'mighty mouse cartoon']), ('heckle', ['heckle and jeckle', 'heckle & jeckle']), ('felix', ['felix the cat']), ('gumby', ['gumby']),
 ('hanna-barbera', ['hanna-barbera', 'hanna barbera']), ('captain caveman', ['captain caveman']), ('hong kong phooey', ['hong kong phooey']), ('space ghost classic', ['space ghost and dino boy', 'space ghost 1966']), ('thundarr', ['thundarr']), ('herculoids', ['herculoids']),
 ('battle of the planets', ['battle of the planets', 'g-force guardians']), ('star blazers', ['star blazers']), ('laff-a-lympics', ['laff-a-lympics', 'laff a lympics']), ('archies', ['archie show', 'the archies cartoon']), ('droopy', ['droopy']),
]
BLOCKS = [
 ('blk saturday', ['saturday morning cartoons', 'saturday morning', 'saturday cartoons']), ('blk fox kids', ['fox kids']), ('blk kids wb', ["kids' wb", 'kids wb']), ('blk disney afternoon', ['disney afternoon']), ('blk one saturday', ['one saturday morning']),
 ('blk cartoon express', ['cartoon express']), ('blk toonami', ['toonami']), ('blk ccf', ['cartoon cartoon fridays', 'cartoon cartoon friday']), ('blk boomerang', ['boomerang block', 'boomerang cartoon network', 'boomerang channel', 'boomerang broadcast']),
 ('blk nicktoons', ['nicktoons']), ('blk toon disney', ['toon disney']), ('blk cartoon network', ['cartoon network']), ('blk nickelodeon', ['nickelodeon', 'snick']), ('blk afternoon', ['afternoon cartoons', 'weekday cartoons', 'morning cartoons', 'cartoon block', 'cartoons with commercials']),
 ('blk tbs', ['tbs cartoons', 'tnt cartoons', 'wgn cartoons', 'tnt toons', 'tbs superstation cartoons', 'usa cartoon', 'bozo show', 'cbs storybreak', 'abc weekend special', 'tnbc']),
]
XCOL = {'gamevideos', 'speed_runs', 'social-media-video', 'mirrortube', 'podcasts-video', 'podcasts', 'vlogs', 'game_replays', 'worldoflongplays', 'gameinformerarchive', 'videogamemagazines', 'magazine_rack', 'altcensored', 'fringe', 'newsandpublicaffairs', 'community_media', 'bliptv', 'video_blender', 'classic_tv_commercials', 'vhsopenings', 'fansubmarine', 'BSLTV', 'youtubecrawl', 'archiveteam', 'vhscommercials', 'stream_only', 'gamefootage', 'videogamelibrary', 'electricsheep', 'computersandtechvideos'}
COLS = ['saturdaymorningcartoons', 'childrenstelevision', 'vhskids', 'cartoonnetwork', 'classic_cartoons', 'animationandcartoons', 'more_animation', 'saturday_morning_cartoons', 'kidstelevision', 'nickelodeon', 'foxkids', 'toonami']

BAD = re.compile(r"\b(capitulo|cap[ií]tulos?|pel[ií]cula|temporada|episodio|bangla|india|urdu|telugu|malay|indonesia|vietsub|thai|remake|critic|nostalgia|tell your tale|make your mark|pony life|a new generation|xyz|sun & moon|sun and moon|journeys|horizons|black & white|diamond and pearl|advanced generation|duel master'?s guide|gx|5d'?s|zexal|arc-v|vrains|dragon ball kai|dragon ball super|dragon ball gt|boruto|data squad|ghost game|commercial breaks?|shorts|crossover|versus|my version|fanmade|ai|upscaled?|4k|8k|60fps|lost media|creepypasta|theory|explained|ranking|ranked|top \d+|all intros|intros?|openings?|endings?|clips?|scenes?|moments|meme|memes|vine|tiktok|shitpost|hack|mods?|sparta|amv|abridged|parody|parodies|review|reviews|reaction|reacts|fan ?made|fan ?edit|fan ?dub|fandub|fan film|tribute|podcast|commentary|let'?s play|gameplay|walkthrough|longplay|speedrun|playthrough|playstation|ps[1-5]|xbox|nintendo|snes|nes|genesis|game ?boy|gba|n64|rom ?hack|arcade|pc game|video ?game|soundtrack|ost|theme song|music video|karaoke|remix|mashup|ytp|youtube poop|trailer|trailers|teaser|promo|promos|bumpers?|commercials only|toy|toys|unboxing|comic|comics|manga|audiobook|audio book|read along|book|coloring|interview|panel|convention|documentary|making of|behind the scenes|storyboard|animatic|pencil test|leica reel|pitch|script|cosplay|live action|the movie|movie|film|friendship is magic|equestria|legendary defender|robots in disguise 2015|transformers prime|cyberverse|rescue bots|war for cybertron|earthspark|rise of the|mutant mayhem|2012 series|ducktales 2017|reboot 2017|the guardian code|mystery incorporated|be cool|scooby-doo and guess who|velma|go!|teen titans go|powerpuff girls 2016|ppg 2016|thundercats roar|thundercats 2011|voltron force|she-ra and the princesses|princesses of power|revelation|revolution|unikitty|south park|family guy|beavis|simpsons|futurama|king of the hill|adult swim|hentai|xxx|nsfw|uncensored|raw japanese|japanese version|subbed|sub ita|sub esp|dublado|doblaje|doblada|latino|castellano|espa[nñ]ol|deutsch|german|fran[cç]ais|french|italiano|italian|portugu[eê]s|brasil|russian|polish|polski|dutch|nederlands|svenska|swedish|norsk|dansk|suomi|arabic|hindi|tamil|korean|tagalog|filipino|hebrew|greek|turkish|magyar|hungarian|czech|uk vhs|uk tv|pal|bbc|itv|cbbc|citv|ytv|teletoon|global tv|cbc)\b", re.I)
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]|[ãõçñÃÕÇÑ]')
TOONW = re.compile(r'\b(cartoons?|animated|animation|toons?|saturday morning|nickelodeon|nicktoons|fox kids|kids.? wb|disney afternoon)\b', re.I)

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True)
                return None
            time.sleep(3 * (k + 1))

def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,subject,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor or len(out) >= 40000: break
    return out

def flat(v):
    if isinstance(v, list): return ' '.join(str(x) for x in v)
    return str(v or '')

def year_of(it):
    ys = [int(x) for x in re.findall(r'(?<!\d)(19[3-9]\d|20[0-2]\d)(?!\d)', flat(it.get('title')))]
    inr = [y for y in ys if 1984 <= y <= 2004]
    m = re.match(r'(\d{4})', flat(it.get('date')) or flat(it.get('year')))
    my = int(m.group(1)) if m else 0
    return inr[0] if inr else 0, my, ys

def lang_ok(it):
    l = flat(it.get('language')).lower().strip()
    return (not l) or bool(re.search(r'eng|english|^en\b', l))

def accept(it, kind, phrases):
    t = flat(it.get('title'))
    low = t.lower()
    if not t or NONLAT.search(t) or BAD.search(low) or not lang_ok(it): return False
    cs = it.get('collection') or []
    if isinstance(cs, str): cs = [cs]
    if set(cs) & XCOL: return False
    ty, my, ys = year_of(it)
    if kind == 'smc':
        return bool(ty) or not (my > 2004 or any(y > 2004 for y in ys))
    if kind == 'block':
        if not (ty or 1984 <= my <= 2004): return False
        if ys and not ty: return False
        return True
    if not any(p in low for p in phrases): return False
    if kind == 'era':
        if ty: return True
        if any(y > 2004 for y in ys): return False
        if my > 2004 and not re.search(r'(s\d+ ?e\d+|season \d|episode \d|ep\.? ?\d+|vhs|complete series|\d+x\d+)', low): return False
        return True
    if any(y > 2004 for y in ys) and not ty: return False
    if my > 2004 and not re.search(r'(s\d+ ?e\d+|season|episode|ep\.? ?\d+|vhs|dvd|complete|collection|cartoons|show|volume|vol\.? ?\d)', low): return False
    return True

seen = {}
def add(items, tag, kind, phrases):
    n = 0
    for it in items:
        i = it['identifier']
        if i in have or i in seen: continue
        if not accept(it, kind, phrases): continue
        it['q'] = tag; it['k'] = kind
        seen[i] = it; n += 1
    print(tag, len(items), 'kept', n, 'total', len(seen), flush=True)

def tq(phrases):
    return 'title:(' + ' OR '.join('"' + p.replace('"', '') + '"' for p in phrases) + ')'

RANGE = '(year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + ' OR '.join(str(y) for y in range(1984, 2005)) + '))'
for tag, ph in BLOCKS:
    add(scrape(tq(ph) + ' AND mediatype:movies AND ' + RANGE), tag, 'block', ph)
for tag, ph in ERA:
    add(scrape(tq(ph) + ' AND mediatype:movies'), tag, 'era', ph)
for tag, ph in CLASSIC:
    add(scrape(tq(ph) + ' AND mediatype:movies'), tag, 'classic', ph)
ALLP = [(tag, ph, 'era') for tag, ph in ERA] + [(tag, ph, 'classic') for tag, ph in CLASSIC]
for col in COLS:
    items = scrape('collection:(' + col + ') AND mediatype:movies')
    n = 0
    for it in items:
        i = it['identifier']
        if i in have or i in seen: continue
        low = flat(it.get('title')).lower()
        hit = None
        for tag, ph, kind in ALLP:
            if any(p in low for p in ph):
                hit = (tag, kind, ph); break
        if hit:
            if not accept(it, hit[1], hit[2]): continue
            it['q'] = hit[0]; it['k'] = hit[1]
        else:
            if col == 'vhskids' and not TOONW.search(low): continue
            if col in ('childrenstelevision', 'kidstelevision', 'nickelodeon') and not TOONW.search(low + ' ' + flat(it.get('subject')).lower()): continue
            if not accept(it, 'smc' if col == 'saturdaymorningcartoons' else 'block', []): continue
            it['q'] = 'col ' + col; it['k'] = 'block'
        seen[i] = it; n += 1
    print('col', col, len(items), 'kept', n, 'total', len(seen), flush=True)

per = collections.Counter(); cands = []
for it in sorted(seen.values(), key=lambda x: -(x.get('downloads') or 0)):
    lim = CAP * 2 if it['k'] != 'block' else 4000
    if per[it['q']] >= lim: continue
    per[it['q']] += 1; cands.append(it)
cands = cands[:LIMIT]
print('candidates', len(cands), 'of', len(seen), flush=True)

def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception:
        return 0

RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    l = flat(m.get('language')).lower().strip()
    if l and not re.search(r'eng|english|^en\b', l): return None
    desc = ' '.join(flat(m.get('description')).split())
    if re.search(r'\b(dublado|doblaje|latino|castellano|deutsch|fran[cç]ais|italiano|fandub|fan ?edit|gameplay|longplay)\b', desc[:600].lower()): return None
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
    if not files or sum(f[1] for f in files) < 600: return None
    files.sort(key=lambda f: f[0])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    if set(col) & XCOL: return None
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    return {'i': it['identifier'], 'q': it['q'], 't': str(flat(m.get('title')))[:200], 'd': str(flat(m.get('date')) or ''), 'y': str(flat(m.get('year')) or ''),
            'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': it['k']}

res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
per = collections.Counter(); out = []
for r in sorted(res, key=lambda x: -x['dl']):
    if r['k'] != 'block' and per[r['q']] >= CAP: continue
    per[r['q']] += 1; out.append(r)
with gzip.open(os.path.join(OUT, 'toons.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(out), 'of', len(res))
print('kinds', dict(collections.Counter(r['k'] for r in out)))
print('by show', collections.Counter(r['q'] for r in out).most_common(200))
def yr(r):
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', r['t']) or re.match(r'(\d{4})', r['d'] or r['y'])
    return m.group(1) if m else '?'
print('by year', sorted(collections.Counter(yr(r) for r in out).items()))
print('by collection', collections.Counter(c for r in out for c in r['c']).most_common(40))
print('hours', round(sum(sum(f[1] for f in r['f']) for r in out) / 3600))
random.seed(7)
for r in random.sample(out, min(50, len(out))):
    print('SAMPLE', r['k'], '|', r['q'], '|', r['t'][:90], '|', r['d'][:10], '|', round(sum(f[1] for f in r['f']) / 60), 'min', len(r['f']), 'files')
