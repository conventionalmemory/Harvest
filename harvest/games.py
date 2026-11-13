import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '14'))
LIMIT = int(os.environ.get('LIMIT', '60000'))
BUDGET = float(os.environ.get('BUDGET_MIN', '300')) * 60
T0 = time.time()
RAWF = os.path.join(OUT, 'raw.json.gz')
have = set(x['i'] for x in json.load(gzip.open(RAWF, 'rt', encoding='utf-8'))) if os.path.exists(RAWF) else set()
print('known', len(have), flush=True)
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
NOY = 'mediatype:movies'
BASE = 'mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
CTX = '(subject:("game show" OR gameshow OR "game shows" OR "quiz show") OR description:("game show" OR gameshow OR contestant OR contestants) OR title:("game show" OR gameshow OR episode OR gsn OR syndicated OR nbc OR cbs OR abc))'
SHOWS = ["classic concentration", "scrabble", "sale of the century", "super password", "password plus", "card sharks", "press your luck", "25,000 pyramid", "100,000 pyramid", "$25,000 pyramid", "$100,000 pyramid", "pyramid", "win, lose or draw", "win lose or draw", "hollywood squares", "joker's wild", "jokers wild", "tic tac dough", "love connection", "newlywed game", "dating game", "family feud", "wheel of fortune", "jeopardy", "price is right", "let's make a deal", "lets make a deal", "match game", "blockbusters", "chain reaction", "high rollers", "body language", "catch phrase", "bumper stumpers", "talk about", "split second", "liar's club", "liars club", "fun house", "double dare", "finders keepers", "nick arcade", "get the picture", "make the grade", "legends of the hidden temple", "nickelodeon guts", "global guts", "figure it out", "remote control", "singled out", "supermarket sweep", "shop 'til you drop", "shop til you drop", "born lucky", "trivial pursuit", "win ben stein's money", "who wants to be a millionaire", "weakest link", "twenty one", "hollywood showdown", "whammy", "russian roulette", "friend or foe", "street smarts", "star search", "american gladiators", "battle of the network stars", "chance of a lifetime", "64,000 question", "anything for money", "hot potato", "dream house", "hit man", "all-star blitz", "all star blitz", "headline chasers", "crosswits", "cross-wits", "break the bank", "strike it rich", "sweethearts", "relatively speaking", "second honeymoon", "rodeo drive", "the challengers", "quiz kids challenge", "trump card", "scattergories", "caesars challenge", "family secrets", "idiot savants", "inquizition", "extreme gong", "gong show", "name that tune", "truth or consequences", "to tell the truth", "what's my line", "i've got a secret", "tattletales", "now you see it", "just men", "battlestars", "fandango", "top card", "10 seconds", "think fast", "wild and crazy kids", "what would you do", "family double dare", "super sloppy double dare", "where in the world is carmen sandiego", "where in time is carmen sandiego", "pick your brain", "peer pressure", "wheel 2000", "jep!", "masters of the maze", "family challenge", "it takes two", "small talk", "wait 'til you have kids", "shopping spree", "pass the buck", "love at first sight", "studs", "personals", "night games", "the big date", "blind date", "change of heart", "elimidate", "the 5th wheel", "rendez-view", "lip service", "sandblast", "beat the geeks", "make me laugh", "you don't know jack", "burt luddin's love buffet", "all new 3's a crowd", "3's a crowd", "the new treasure hunt", "treasure hunt", "the $1.98 beauty show", "bzzz!", "ruckus", "pictionary", "the krypton factor", "teen win lose or draw", "contraption", "couch potatoes", "the last word", "yahtzee", "triple threat", "the big spin", "bonus bonanza", "illinois instant riches", "flamingo fortune", "lottery game show", "the cross-wits", "dealer's choice", "tic-tac-dough", "the diamond head game", "the magnificent marble machine", "whew!", "mindreaders", "play the percentages", "bullseye", "face the music", "hot streak", "bruce forsyth's hot streak", "trivia trap", "the new battlestars", "your number's up", "every second counts", "the $1,000,000 chance of a lifetime", "matchmaker", "perfect match", "all about us", "wordplay", "the home shopping game", "wipeout 1988", "pitfall", "definition", "jackpot!", "card sharks 2001", "pyramid 2002", "paranoia", "greed", "winning lines", "it's your chance of a lifetime", "you lose you choose", "dog eat dog", "the chair", "the chamber", "cram", "win ben stein", "turn ben stein on", "wintuition", "mall masters", "all new press your luck", "balderdash", "lingo gsn", "hollywood squares 1986", "hollywood squares 1998", "tom bergeron hollywood squares", "new hollywood squares", "password", "concentration", "lingo", "wipeout", "jackpot", "monopoly", "shuffle", "boggle", "jumble", "debt", "time machine", "guts", "taboo", "game show network", "gsn", "buzzr"]
AMB = {"to tell the truth", "truth or consequences", "what's my line", "i've got a secret", "password plus", "the big date", "just men", "paranoia", "the chair", "definition", "you don't know jack", "dog eat dog", "figure it out", "get the picture", "make the grade", "think fast", "double dare", "finders keepers", "the gong show", "gong show", "name that tune", "now you see it", "monopoly", "pyramid", "password", "concentration", "lingo", "wipeout", "jackpot", "monopoly", "shuffle", "boggle", "jumble", "debt", "time machine", "guts", "taboo", "click", "taken", "trashed", "vs.", "whew!", "bullseye", "definition", "paranoia", "greed", "the chair", "the chamber", "cram", "pitfall", "matchmaker", "perfect match", "all about us", "studs", "personals", "twenty one", "scrabble", "sweethearts", "blockbusters", "whammy", "hit man", "dream house", "split second", "talk about", "fun house", "remote control", "blind date", "it takes two", "small talk", "100% ", "treasure hunt", "contraption", "yahtzee", "balderdash", "fandango", "top card", "think fast", "peer pressure", "boot camp", "ruckus", "night games", "trivial pursuit", "pictionary", "strike it rich", "break the bank", "hot potato", "chain reaction", "high rollers", "body language", "catch phrase", "the challengers", "trump card", "family secrets", "relatively speaking", "second honeymoon", "rodeo drive", "born lucky", "russian roulette", "friend or foe", "street smarts", "star search", "make me laugh", "what would you do", "triple threat", "the last word", "couch potatoes", "face the music", "hot streak", "every second counts", "wordplay", "shopping spree", "pass the buck", "love at first sight", "change of heart", "lip service", "10 seconds"}
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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cursor = j.get('cursor')
        if not cursor: break
    return out
cols = set(['gameshows', 'gameshows_miscellaneous', 'gameshow_jeopardy', 'gameshow_tpir'])
for pat in ('gameshow*', 'game_show*', 'game-show*', 'gameshows*', '*gameshow*', 'buzzr*', 'gsn*', '*game_shows*'):
    for it in scrape('mediatype:collection AND identifier:(' + pat + ')'):
        cols.add(it['identifier'])
for it in scrape('mediatype:collection AND title:("game show" OR "game shows" OR gameshow OR gameshows)'):
    cols.add(it['identifier'])
GC = set(c for c in cols if not c.startswith(('fav-', 'TVPROGRAM')) and c not in ('gsns_spanish', 'thisorthat', 'gameshow-mag-turk'))
cols = GC
print('collections', sorted(cols), flush=True)
QS = [('col', 'collection:(' + ' OR '.join(sorted(cols)) + ')'), ('subj', 'subject:("game show" OR gameshow OR "game shows" OR "gameshows" OR "quiz show")'), ('desc', 'description:("game show" OR gameshow) AND title:(episode OR ' + YRS + ')')]
clear = [s for s in SHOWS if s not in AMB]
amb = [s for s in SHOWS if s in AMB]
def tq(names): return 'title:(' + ' OR '.join('"' + n.replace('"', '').strip() + '"' for n in names) + ')'
for i in range(0, len(clear), 30): QS.append(('t%d' % (i // 30), tq(clear[i:i + 30])))
for i in range(0, len(amb), 30): QS.append(('a%d' % (i // 30), tq(amb[i:i + 30]) + ' AND ' + CTX))
seen = {}
for tag, expr in QS:
    items = scrape('(' + expr + ') AND ' + (NOY if tag == 'col' or tag[0] == 't' else BASE))
    n = 0
    for it in items:
        i = it['identifier']
        if i in seen or i in have: continue
        it['q'] = tag; seen[i] = it; n += 1
    print(tag, len(items), 'new', n, 'total', len(seen), flush=True)
X_FOR = r"\b(uk|u\.k\.|british|britain|itv|bbc|channel 4|australia|australian|aussie|nine network|network ten|canada|canadian|cbc|ctv|quebec|qu[eé]bec|france|french|german|germany|deutsch|italia|italian|espa[nñ]ol|spanish|mexico|televisa|brasil|brazil|portugu|japan|japanese|korea|korean|philippine|filipino|india|hindi|russia|russian|polish|dutch|nederland|sweden|swedish|new zealand|nz|ireland|irish|rte|greek|turkish|arabic|indonesia|malaysia|thai|vietnam|chinese|hong kong|tvb|bullseye uk|catchphrase|bob monkhouse|bruce forsyth|chris tarrant|family fortunes|blankety blank|countdown|fifteen to one|going for gold|the crystal maze|strike it lucky|play your cards right|wheel of fortune australia|burgo|sale of the century australia|glenn ridge|tony barber|seizoen|aflevering|noel'?s|rtc|university college|series \d+ episode|catchword|telly addicts|generation game|big break|bullseye \(uk|wheel of fortune \(uk|uk version|australian version|canadian version)\b"
X_JUNK = r"\b(video ?game|gameplay|longplay|walkthrough|playthrough|nes|snes|genesis|playstation|ps1|ps2|xbox|game boy|gameboy|dos game|pc game|cd-rom|cdrom|rom|emulator|board game|commercial|commercials|promo|promos|bumper|bumpers|intro|intros|opening|openings|theme song|theme music|music cues?|cues|soundtrack|bloopers?|outtakes?|compilation|fan ?made|fan-made|recreation|remake|parody|mock|powerpoint|flash game|roblox|minecraft|unaired pilot recreation|review|podcast|reaction|trailer|interview|tribute|documentary|behind the scenes|ost|wrestling|czw|nba|nfl|mlb|nhl|finals|conference|museum|horror|slot machine|pinball|lottery drawing|home movie|wedding|sermon|church|xxx|porn|adult)\b"
X_MOD = r"(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)"
def ok_title(t):
    low = (t or '').lower() + ' '
    if re.search(r'[^\x00-\xff‐-‧™]', t or ''): return False
    if re.search(X_FOR, low) or re.search(X_JUNK, low) or re.search(X_MOD, low): return False
    return True
cands = [x for x in seen.values() if ok_title(str(x.get('title') or ''))]
print('after title filter', len(cands), 'of', len(seen), flush=True)
cands.sort(key=lambda x: (0 if x['q'] == 'col' else 1 if x['q'].startswith('t') else 2, -(x.get('downloads') or 0)))
cands = cands[:LIMIT]
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
SH = sorted(set(SHOWS), key=len, reverse=True)
def meta(it):
    if time.time() - T0 > BUDGET: return None
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'(?i)eng|english|^en', str(lang)): return None
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
    if not files or sum(f[1] for f in files) < 900: return None
    files.sort(key=lambda f: f[0])
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    title = str(m.get('title', ''))
    if not ok_title(title): return None
    blob = (title + ' ' + str(subj) + ' ' + desc[:600]).lower()
    if re.search(X_FOR, blob): return None
    incol = bool(set(col) & GC)
    ctx = re.search(r'game ?shows?|quiz show|contestants?|\bgsn\b|buzzr', blob)
    tl = re.sub(r"^(the |new |all[- ]new |\$)+", '', re.sub(r'^[\s\d./:-]+', '', title.lower()))
    hit = next((s for s in SH if s.strip() in title.lower()), '')
    starts = bool(hit) and tl.startswith(re.sub(r'^(the |\$)+', '', hit.strip()))
    if not (incol or (hit and hit not in AMB and (starts or ctx)) or (hit and ctx and starts)): return None
    ys = [int(x) for x in re.findall(r'(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)', title + ' ' + str(m.get('date', '') or '')[:4] + ' ' + str(m.get('year', '') or ''))]
    if not ys: ys = [int(x) for x in re.findall(r'(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)', desc[:300] + ' ' + it['identifier'])]
    era = [y for y in ys if 1984 <= y <= 2004]
    if not era:
        m2 = re.search(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-]([89]\d)(?!\d)', title)
        if m2 and int(m2.group(3)) >= 84: era = [1900 + int(m2.group(3))]
    if not era: return None
    return {'i': it['identifier'], 'q': 'game', 't': title[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': hit, 'e': era[0]}
res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
with gzip.open(os.path.join(OUT, 'games.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
def yr(x): return str(x['e'])
print('done', len(res))
print('years', sorted(collections.Counter(yr(x) for x in res).items()))
print('shows', collections.Counter(x['k'] or '(other)' for x in res).most_common(70))
print('hours', round(sum(sum(f[1] for f in x['f']) for x in res) / 3600))
random.seed(4)
for x in random.sample(res, min(45, len(res))): print('SAMPLE', yr(x), '|', x['t'][:90], '|', x['i'][:40], '|', round(sum(f[1] for f in x['f']) / 60), 'min')
