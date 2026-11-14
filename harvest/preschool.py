import json, gzip, os, re, sys, time, random, glob, collections, urllib.parse, urllib.request
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
S = [
 ('sesame street', ['sesame street', 'sesame songs', 'my sesame street home video', 'big bird', 'elmo\'s world', 'elmos world', 'elmo saves christmas', 'elmopalooza', 'follow that bird', 'christmas eve on sesame street', 'play with me sesame', 'sesame street presents', 'cookie monster', 'bert and ernie', 'ernie and bert'], 1984, 2004),
 ('mister rogers', ['mister rogers', 'mr. rogers', 'mr rogers neighborhood', 'misterogers'], 1984, 2001),
 ('captain kangaroo', ['captain kangaroo'], 1984, 1993),
 ('romper room', ['romper room'], 1984, 1994),
 ('electric company', ['the electric company', 'electric company'], 1984, 2000),
 ('reading rainbow', ['reading rainbow'], 1984, 2004),
 ('shining time station', ['shining time station'], 1989, 1998),
 ('thomas the tank engine', ['thomas the tank engine', 'thomas & friends', 'thomas and friends', 'thomas gets tricked', 'thomas gets bumped', 'james learns a lesson', 'tenders and turntables', 'better late than never', 'trust thomas', 'percy\'s ghostly trick', 'daisy and other', 'rusty to the rescue', 'thomas and the magic railroad', 'cranky bugs', 'best of thomas', 'best of percy', 'best of james', 'spills and chills', 'races, rescues', 'thomas\' christmas party', 'thomas christmas'], 1989, 2004),
 ('barney', ['barney & friends', 'barney and friends', 'barney and the backyard gang', 'barney & the backyard gang', 'barney in concert', 'barney live', 'barney\'s', 'barney home video', 'barney safety', 'barney rhymes', 'waiting for santa', 'barney goes to school', 'rock with barney'], 1988, 2004),
 ('lamb chop', ['lamb chop', 'shari lewis', 'charlie horse music pizza'], 1984, 1999),
 ('fraggle rock', ['fraggle rock'], 1984, 1996),
 ('muppet babies', ['muppet babies'], 1984, 2000),
 ('muppet show', ['the muppet show', 'muppet show', 'muppets tonight', 'muppet family christmas', 'jim henson hour', 'muppet video', 'muppet sing alongs', 'muppet sing-alongs'], 1984, 2004),
 ('mother goose stories', ['mother goose stories', 'mother goose rock', 'mother goose video treasury'], 1987, 1998),
 ('pinwheel', ['pinwheel'], 1984, 1990),
 ('todays special', ['today\'s special', 'todays special'], 1984, 1991),
 ('eureekas castle', ['eureeka\'s castle', 'eureekas castle', 'eureeka'], 1989, 1999),
 ('elephant show', ['elephant show', 'sharon, lois', 'sharon lois', 'skinnamarink'], 1984, 2000),
 ('fred penner', ['fred penner'], 1985, 1997),
 ('kidsongs', ['kidsongs'], 1985, 2002),
 ('wee sing', ['wee sing'], 1985, 2000),
 ('zoobilee zoo', ['zoobilee zoo'], 1986, 2000),
 ('hugga bunch', ['hugga bunch'], 1985, 1988),
 ('teddy ruxpin', ['teddy ruxpin'], 1985, 1992),
 ('care bears', ['care bears', 'care bear'], 1984, 1996),
 ('rainbow brite', ['rainbow brite'], 1984, 1990),
 ('my little pony', ['my little pony'], 1984, 1995),
 ('strawberry shortcake', ['strawberry shortcake'], 1984, 2004),
 ('pound puppies', ['pound puppies'], 1985, 1992),
 ('get along gang', ['get along gang'], 1984, 1988),
 ('gummi bears', ['gummi bears'], 1985, 1997),
 ('pooh corner', ['welcome to pooh corner', 'pooh corner'], 1984, 1995),
 ('dumbos circus', ['dumbo\'s circus', 'dumbos circus'], 1985, 1995),
 ('winnie the pooh', ['new adventures of winnie the pooh', 'winnie the pooh', 'book of pooh', 'pooh\'s grand adventure', 'tigger movie', 'pooh playtime', 'pooh learning', 'pooh friendship'], 1984, 2004),
 ('mousercise', ['mousercise'], 1984, 1996),
 ('disney sing along', ['disney sing along', 'disney sing-along', 'disney\'s sing along', 'disney\'s sing-along', 'sing along songs', 'sing-along songs'], 1986, 2004),
 ('adventures in wonderland', ['adventures in wonderland'], 1992, 1998),
 ('under the umbrella tree', ['under the umbrella tree'], 1987, 1997),
 ('mickey mouse club', ['mickey mouse club', 'all new mickey mouse club'], 1984, 1996),
 ('bear in the big blue house', ['bear in the big blue house', 'big blue house'], 1997, 2004),
 ('rolie polie olie', ['rolie polie olie'], 1998, 2004),
 ('pb&j otter', ['pb&j otter', 'pb & j otter', 'pb and j otter'], 1998, 2004),
 ('out of the box', ['out of the box'], 1998, 2004),
 ('stanley', ['playhouse disney stanley', 'stanley playhouse disney', 'disney\'s stanley'], 2001, 2004),
 ('jojos circus', ['jojo\'s circus', 'jojos circus'], 2003, 2004),
 ('playhouse disney', ['playhouse disney'], 1999, 2004),
 ('blues clues', ['blue\'s clues', 'blues clues', 'blue\'s big', 'blues big'], 1996, 2004),
 ('gullah gullah island', ['gullah gullah island', 'gullah gullah'], 1994, 2000),
 ('allegras window', ['allegra\'s window', 'allegras window'], 1994, 1998),
 ('little bear', ['maurice sendak\'s little bear', 'little bear'], 1995, 2004),
 ('franklin', ['franklin the turtle', 'franklin and friends', 'franklin plays', 'franklin\'s', 'franklin goes'], 1997, 2004),
 ('maisy', ['maisy'], 1999, 2004),
 ('kipper', ['kipper the dog', 'kipper -', 'kipper:', 'kipper vhs', 'kipper season'], 1997, 2004),
 ('dora the explorer', ['dora the explorer'], 2000, 2004),
 ('oswald', ['oswald the octopus', 'nick jr oswald', 'oswald nick jr'], 2001, 2004),
 ('bob the builder', ['bob the builder'], 2001, 2004),
 ('max & ruby', ['max & ruby', 'max and ruby'], 2002, 2004),
 ('little bill', ['little bill'], 1999, 2004),
 ('nick jr', ['nick jr', 'nick jr.', 'nickjr', 'face nick jr', 'nick junior'], 1988, 2004),
 ('teletubbies', ['teletubbies'], 1998, 2004),
 ('dragon tales', ['dragon tales'], 1999, 2004),
 ('clifford', ['clifford the big red dog', 'clifford\'s', 'cliffords'], 1988, 2004),
 ('arthur', ['pbs arthur', 'arthur pbs', 'arthur season', 'arthur marc brown', 'arthur episode', 'arthur vhs'], 1996, 2004),
 ('caillou', ['caillou'], 2000, 2004),
 ('zoboomafoo', ['zoboomafoo'], 1999, 2004),
 ('between the lions', ['between the lions'], 2000, 2004),
 ('wishbone', ['wishbone'], 1995, 2001),
 ('puzzle place', ['puzzle place'], 1995, 1998),
 ('storytime', ['pbs storytime', 'storytime pbs', 'kino\'s storytime', 'kinos storytime'], 1992, 1998),
 ('tots tv', ['tots tv'], 1996, 1999),
 ('noddy', ['noddy'], 1998, 2004),
 ('big comfy couch', ['big comfy couch'], 1995, 2004),
 ('theodore tugboat', ['theodore tugboat'], 1996, 2001),
 ('madeline', ['madeline'], 1989, 2004),
 ('babar', ['babar'], 1989, 2002),
 ('richard scarry', ['richard scarry', 'busytown'], 1989, 2000),
 ('rupert', ['rupert bear', 'rupert nelvana', 'rupert and'], 1991, 1999),
 ('paddington', ['paddington bear', 'paddington'], 1984, 1999),
 ('berenstain bears', ['berenstain bears', 'berenstein bears'], 1985, 2004),
 ('raggedy ann', ['raggedy ann'], 1984, 1992),
 ('raccoons', ['the raccoons'], 1985, 1995),
 ('littles', ['the littles'], 1984, 1990),
 ('maple town', ['maple town'], 1987, 1990),
 ('sylvanian families', ['sylvanian families'], 1987, 1990),
 ('noozles', ['noozles'], 1988, 1993),
 ('little koala', ['little koala'], 1987, 1993),
 ('maya the bee', ['maya the bee'], 1990, 1993),
 ('david the gnome', ['david the gnome', 'wisdom of the gnomes'], 1987, 1998),
 ('doctor snuggles', ['doctor snuggles', 'dr. snuggles', 'dr snuggles'], 1984, 1990),
 ('grimms fairy tale classics', ['grimm\'s fairy tale classics', 'grimms fairy tale classics', 'grimm masterpiece theater'], 1988, 1996),
 ('little prince', ['adventures of the little prince'], 1984, 1990),
 ('belle and sebastian', ['belle and sebastian'], 1984, 1990),
 ('faerie tale theatre', ['faerie tale theatre', 'faerie tale theater', 'tall tales & legends', 'tall tales and legends'], 1984, 1996),
 ('bedtime stories', ['shelley duvall\'s bedtime stories', 'bedtime stories shelley'], 1992, 1996),
 ('rabbit ears', ['rabbit ears', 'storybook classics', 'we all have tales'], 1985, 1996),
 ('golden book video', ['golden book video', 'golden book'], 1985, 1996),
 ('baby songs', ['baby songs', 'hap palmer'], 1987, 2000),
 ('baby einstein', ['baby einstein', 'baby mozart', 'baby bach', 'baby van gogh', 'baby shakespeare', 'baby newton', 'baby galileo', 'baby santa', 'baby neptune', 'baby macdonald', 'baby da vinci'], 1997, 2004),
 ('veggietales', ['veggietales', 'veggie tales'], 1993, 2004),
 ('real wheels', ['there goes a', 'real wheels'], 1993, 2004),
 ('mighty machines', ['mighty machines'], 1994, 2004),
 ('road construction ahead', ['road construction ahead', 'fire and rescue vhs', 'cleared for takeoff', 'heavy equipment operator', 'i love toy trains', 'tm books and video', 'big adventure series', 'let\'s go to the farm', 'farm country ahead'], 1991, 2004),
 ('raffi', ['raffi'], 1984, 2000),
 ('disney channel', ['disney channel'], 1984, 2004),
 ('pbs kids', ['pbs kids', 'ptv park', 'pbs kids block', 'pbs children'], 1993, 2004),
 ('mickey donald', ['donald duck presents', 'mickey mouse and friends', 'mickey\'s mouse tracks', 'good morning mickey', 'mouseterpiece theater', 'donald\'s quack attack', 'cartoon classics limited', 'walt disney cartoon classics', 'walt disney mini classics', 'mini classics'], 1984, 2000),
 ('gumby', ['gumby'], 1984, 2000),
 ('smurfs', ['the smurfs', 'smurfs'], 1984, 1995),
 ('snorks', ['snorks'], 1984, 1992),
 ('shirt tales', ['shirt tales', 'monchhichis', 'wuzzles', 'popples', 'kissyfur', 'glo friends', 'moondreamers', 'potato head kids', 'lady lovely locks', 'poochie', 'rose petal place', 'star fairies', 'pound puppy'], 1984, 1992),
 ('fluppy dogs', ['fluppy dogs', 'gnomes special', 'herself the elf', 'peter and the magic egg', 'the charmkins', 'cabbage patch kids', 'my pet monster', 'the hugga', 'serendipity the pink dragon', 'here comes peter cottontail'], 1984, 1995),
 ('magic school bus', ['magic school bus'], 1994, 2004),
 ('bananas in pajamas', ['bananas in pajamas', 'bananas in pyjamas'], 1995, 2000),
 ('wimzies house', ['wimzie\'s house', 'wimzies house'], 1997, 2001),
 ('huggabug club', ['huggabug club', 'the kidsongs', 'kidsongs tv', 'the reppies', 'the dooley and pals', 'dooley and pals', 'groundling marsh', 'jay jay the jet plane', 'the wiggles', 'wiggles', 'hi-5', 'sagwa', 'timothy goes to school', 'seven little monsters', 'george shrinks', 'marvin the tap', 'elliot moose', 'angelina ballerina', 'boohbah', 'the save-ums', 'save-ums', 'connie the cow', 'miss spider', 'little robots', 'make way for noddy', 'rubbadubbers', 'pingu', 'spot the dog', 'adventures of spot', 'postman pat', 'fireman sam', 'the koala brothers', 'peep and the big wide world', 'jakers', 'cyberchase', 'liberty\'s kids', 'zoom pbs', 'the charlie horse', 'the book of virtues', 'adventures from the book of virtues', 'the country mouse and the city mouse', 'the neverending story animated', 'little mermaid series', 'timon and pumbaa', 'jungle cubs', '101 dalmatians the series', 'the wubbulous world of dr. seuss', 'wubbulous world', 'dr. seuss', 'dr seuss', 'the cat in the hat', 'curious george', 'peter rabbit', 'world of peter rabbit', 'beatrix potter', 'the snowman 1982', 'the snowman raymond', 'frog and toad', 'really rosie', 'chicken soup with rice', 'where the wild things are', 'weston woods', 'children\'s circle', 'scholastic video', 'reading rainbow', 'schoolhouse rock', 'school house rock', 'the letter people', 'letter people', 'hooked on phonics', 'rock \'n learn', 'rock n learn', 'richard simmons kids', 'kidvidz', 'professor iris', 'see how they grow', 'eyewitness video', 'national geographic kids', 'really wild animals', 'geokids', 'animal alphabet', 'baby\'s first', 'bill nye', 'beakman', 'kratts\' creatures', 'kratts creatures', 'new zoo revue', 'hodge podge lodge', 'gigglesnort', 'bozo', 'bozo the clown', 'bozo show', 'great space coaster', 'kids incorporated', 'kids inc', 'welcome to pooh', 'imagination station', 'the adventures of timmy the tooth', 'timmy the tooth', 'mcgee and me', 'adventures in odyssey', 'the donut man', 'donut repair club', 'psalty', 'gerbert', 'quigley\'s village', 'joy junction', 'superbook', 'flying house', 'the greatest adventure stories from the bible', 'greatest adventure'], 1984, 2004),
]
S2 = []
for tag, phs, a, b in S:
    if tag == 'huggabug club':
        for p in phs: S2.append((p.replace('the ', '', 1) if p.startswith('the ') else p, [p], a, b))
    else: S2.append((tag, phs, a, b))
seen_t = set(); S = []
for x in S2:
    if x[0] not in seen_t: seen_t.add(x[0]); S.append(x)
PH = []
for tag, phs, a, b in S:
    for p in phs:
        PH.append((p.lower(), tag, a, b))
PH.sort(key=lambda x: -len(x[0]))
ERA = {tag: (a, b) for tag, phs, a, b in S}
COLS = ['vhskids', 'childrenstelevision', 'dvdkids', 'saturdaymorningcartoons']
BAD = re.compile(r"(?i)\b(castellano|espa[nñ]ol|espanol|latino|doblaje|dublado|portugu[eê]s|brasil|deutsch|german|fran[cç]ais|french|italiano|italian|nederlands|dutch|svenska|swedish|norsk|dansk|suomi|polski|polish|russian|hebrew|arabic|hindi|japanese|korean|chinese|cantonese|mandarin|greek|turkish|magyar|hungarian|czech|romanian|uk version|uk vhs|bbc|cbeebies|itv|abc for kids|australian|canadian french|en fran[cç]ais|en espa[nñ]ol|ytp|youtube poop|parody|reaction|review|unboxing|toy review|toys|fan ?made|fan ?edit|fanmade|creepypasta|lost episode fake|amv|remix|mashup|karaoke|soundtrack|audiobook|audio only|full album|podcast|commentary|let'?s play|gameplay|walkthrough|video game|pc game|cd-rom|cdrom|playstation|nintendo|game boy|sega|trailer|trailers|teaser|promo only|logo history|logos|closing logos|opening to|closing to|opening and closing|opening previews|dvd menu|menu walkthrough|credits only|end credits|theme song only|intro only|wiki|analysis|documentary about|behind the scenes of|interview with|tribute|memorial|rip |cgi series|reboot|go go thomas|big world! big adventures|all engines go|paw patrol|peppa|bluey|cocomelon|super why|sid the science|dinosaur train|daniel tiger|team umizoomi|bubble guppies|yo gabba|wonder pets|backyardigans|little einsteins|mickey mouse clubhouse|handy manny|doc mcstuffins|sofia the first|friendship is magic|equestria|adventures in care-a-lot|welcome to care-a-lot|unlock the magic|berry bitty|elmo'?s world: |the furchester|sesame street season (3[6-9]|[45]\d)|season (3[6-9]|[45]\d) sesame|barney season (1[0-4])|goanimate|go ?animate|vyond|grounded|gets grounded|punishment day|held back|misbehaves|behaves at|trial day|testif\w+|proclamation|read aloud|read by|credits|in different languages|multilanguage|multi-language|the music of|\buk\b|u\.k\.|international copy|logo|bumpers? only|unknown .* part \d|fake|leaked|scrapped|what if|rant|ytpmv|sparta|g4tv|shoots|attacks|revenge|dies|killed|killers?|electrocuted|beers|thrasher|adult|xxx|porn|hentai|nsfw|gore|horror edit)\b")
NONLAT = re.compile(r'[^\x00-\xff‐-‧™]')
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor: break
    return out
def norm(t):
    return re.sub(r'\s+', ' ', str(t or '').lower().replace('’', "'").replace('‘', "'").replace('&amp;', '&'))
def tag_of(low):
    for p, tag, a, b in PH:
        i = low.find(p)
        if i < 0: continue
        if (i > 0 and low[i - 1].isalnum()) or (i + len(p) < len(low) and low[i + len(p)].isalnum() and not p.endswith("'s")): continue
        return tag
    return None
def lang_ok(l):
    if not l: return True
    if isinstance(l, list): l = ' '.join(str(x) for x in l)
    l = str(l).lower()
    return bool(re.search(r'eng|english|^en\b|en-us|en_us|american', l)) or l.strip() in ('', 'und', 'none', 'no linguistic content', 'zxx')
TH = {1: 1989, 2: 1989, 3: 1992, 4: 1995, 5: 1998, 6: 2002, 7: 2003, 8: 2004}
def era_of(tag, title, date, year):
    a, b = ERA[tag]
    sm = re.search(r'\b(?:season|series|s)\s*0?(\d{1,2})\b', title)
    if tag == 'thomas the tank engine' and sm:
        n = int(sm.group(1))
        if n > 8 or n < 1: return None
        return TH[n]
    if tag == 'sesame street':
        if sm and 1 <= int(sm.group(1)) <= 60:
            y = 1968 + int(sm.group(1))
            return None if y > 2004 else max(y, 1984)
        em = re.search(r'\b(?:episode|ep\.?|show)\s*#?(\d{4})\b', title)
        if em and 1 <= int(em.group(1)) <= 4999:
            y = 1969 + (int(em.group(1)) - 1) // 130
            return None if y > 2004 else max(y, 1984)
    ys = [int(y) for y in re.findall(r'(?<!\d)(19[5-9]\d|20[0-2]\d)(?!\d)', title)]
    ok = [y for y in ys if 1950 <= y <= 2004]
    if ys and not ok: return None
    if ok:
        y = ok[0]
        return min(max(y, 1984), 2004) if y < 1984 else y
    m = re.search(r"(?<![\w'])'([89]\d)(?!\d)", title)
    if m: return 1900 + int(m.group(1))
    for v in (date, year):
        m = re.match(r'(\d{4})', str(v or ''))
        if m and a <= int(m.group(1)) <= b: return int(m.group(1))
    return (a + min(b, a + 6)) // 2 if b - a > 8 else (a + b) // 2
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
    if str(m.get('mediatype', 'movies')) != 'movies': return None
    if not lang_ok(m.get('language')): return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(str(x) for x in desc)
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(str(x) for x in subj)
    blob = norm(str(m.get('title', '')) + ' ' + str(subj) + ' ' + str(desc)[:300])
    if BAD.search(blob): return None
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
    if not files or sum(f[1] for f in files) < 480: return None
    files.sort(key=lambda f: f[0])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    return {'i': it['identifier'], 'q': 'kids', 't': str(m.get('title', ''))[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': ' '.join(str(desc).split())[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': it['k'], 'e': it['e']}
if MODE == 'plan':
    RAWF = os.path.join(OUT, 'raw.json.gz')
    have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8'))) if os.path.exists(RAWF) else set()
    print('known', len(have), flush=True)
    cols = set(COLS)
    for pat in ('*pbskids*', '*pbs-kids*', '*pbs_kids*', '*nickjr*', '*nick-jr*', '*nick_jr*', '*playhousedisney*', '*playhouse-disney*', '*playhouse_disney*', '*sesamestreet*', '*sesame-street*', '*sesame_street*', '*barney*', '*kidsvhs*', '*kids-vhs*', '*kids_vhs*', '*vhskid*', '*childrensvhs*', '*childrens-vhs*', '*preschool*', '*misterrogers*', '*thomasthetank*', '*bluesclues*', '*kidsongs*', '*veggietales*', '*teletubbies*', '*childrenstv*', '*kidstv*', '*disneychannel*', '*disney-channel*', '*disneyvhs*', '*disney-vhs*', '*muppet*', '*henson*'):
        for it in scrape('mediatype:collection AND identifier:(' + pat + ')'):
            if not it['identifier'].startswith('fav-'): cols.add(it['identifier'])
    print('collections', sorted(cols), flush=True)
    seen = {}; rej = collections.Counter(); hits = collections.Counter()
    def take(items, need_tag, src, force=None):
        for it in items:
            i = it['identifier']
            if i in seen or i in have: continue
            t = it.get('title')
            if isinstance(t, list): t = ' '.join(str(x) for x in t)
            low = norm(t)
            if NONLAT.search(str(t or '')): rej['nonlatin'] += 1; continue
            if BAD.search(low): rej['bad'] += 1; continue
            if not lang_ok(it.get('language')): rej['lang'] += 1; continue
            tag = tag_of(low) or force
            if not tag:
                rej['notag'] += 1; continue
            e = era_of(tag, low, it.get('date'), it.get('year'))
            if e is None or e > 2004: rej['modern'] += 1; continue
            it['k'] = tag; it['e'] = e; it['title'] = str(t or '')[:200]
            seen[i] = it; hits[tag] += 1
    need_tag_default = None
    done = set()
    for p, tag, a, b in PH:
        if p in done: continue
        done.add(p)
        items = scrape('title:("' + p.replace('"', '') + '") AND mediatype:movies')
        n0 = len(seen); take(items, True, p)
        print('q', p, len(items), '+', len(seen) - n0, flush=True)
    for c in sorted(cols):
        items = scrape('collection:(' + c + ') AND mediatype:movies')
        n0 = len(seen); take(items, True, c)
        print('col', c, len(items), '+', len(seen) - n0, flush=True)
    for sq in ('subject:("sesame street" OR "pbs kids" OR "nick jr" OR "playhouse disney" OR "preschool" OR "children\'s television" OR "childrens television" OR "kids vhs" OR "children\'s vhs")',):
        items = scrape(sq + ' AND mediatype:movies')
        n0 = len(seen); take(items, True, 'subject')
        print('subject', len(items), '+', len(seen) - n0, flush=True)
    for tag, phs, a, b in S:
        if hits[tag] >= 15: continue
        for p in phs[:3]:
            items = scrape('subject:("' + p.replace('"', '') + '") AND mediatype:movies')
            n0 = len(seen); take(items, True, p, tag)
            print('subj', p, len(items), '+', len(seen) - n0, flush=True)
    cands = sorted(seen.values(), key=lambda x: -(x.get('downloads') or 0))
    print('rejected', dict(rej)); print('candidates', len(cands)); print('per tag', hits.most_common())
    with gzip.open(os.path.join(PARTS, 'pcands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump([{'identifier': x['identifier'], 'k': x['k'], 'e': x['e'], 'downloads': x.get('downloads') or 0} for x in cands], f, separators=(',', ':'))
elif MODE == 'meta':
    cands = json.load(gzip.open(os.path.join(PARTS, 'pcands.json.gz'), 'rt', encoding='utf-8'))[SHARD::SHARDS]
    print('shard', SHARD, 'items', len(cands), flush=True)
    res = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(meta, cands)):
            if r: res.append(r)
            if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'pshard-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res))
else:
    res = []; seen = set()
    PF = os.path.join(OUT, 'preschool.json.gz')
    old = json.load(gzip.open(PF, 'rt', encoding='utf-8')) if os.path.exists(PF) else []
    for p in sorted(glob.glob(os.path.join(PARTS, 'pshard-*.json.gz'))):
        for x in json.load(gzip.open(p, 'rt', encoding='utf-8')):
            if x['i'] not in seen: seen.add(x['i']); res.append(x)
    for x in old:
        if x['i'] not in seen: seen.add(x['i']); res.append(x)
    res.sort(key=lambda x: (x['k'], -x['dl']))
    with gzip.open(os.path.join(OUT, 'preschool.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    tot = sum(sum(f[1] for f in x['f']) for x in res)
    print('TOTAL items', len(res), 'files', sum(len(x['f']) for x in res), 'hours', round(tot / 3600))
    by = collections.defaultdict(lambda: [0, 0, 0])
    for x in res:
        b = by[x['k']]; b[0] += 1; b[1] += len(x['f']); b[2] += sum(f[1] for f in x['f'])
    print('PER SHOW (items files hours)')
    for tag, phs, a, b in S:
        v = by.get(tag, [0, 0, 0])
        print(' ', tag.ljust(28), str(v[0]).rjust(5), str(v[1]).rjust(6), str(round(v[2] / 3600)).rjust(5), 'ZERO' if not v[0] else 'THIN' if v[0] < 5 else '')
    print('PER ERA YEAR', sorted(collections.Counter(x['e'] for x in res).items()))
    random.seed(7)
    print('SAMPLES')
    for x in random.sample(res, min(60, len(res))):
        print(' ', x['k'], '|', x['e'], '|', x['t'][:80], '|', len(x['f']), 'files', round(sum(f[1] for f in x['f']) / 60), 'min |', x['i'][:40])
