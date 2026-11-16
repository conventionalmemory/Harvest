import json, gzip, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (archive harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog', 'holcook.json.gz')
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1: print('fail', url[:120], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads,language,subject,description', 'q': q, 'count': 2000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += [x for x in (j.get('items') or []) if isinstance(x, dict) and x.get('identifier')]; cursor = j.get('cursor')
        if not cursor or len(out) > 8000: break
    return out
HOL = r'christmas|xmas|x-mas|holiday|holidays|thanksgiving|turkey day|yule|gingerbread|eggnog|new year|hanukkah|chanukah|easter|valentine|halloween|noel|santa|festive|cookie exchange|plum pudding|fruitcake'
COOK = r'cook|cooking|cookery|chef|chefs|kitchen|recipe|recipes|bake|baking|bake-off|bakeoff|gourmet|cuisine|dinner|feast|cookies|candy|candies|dessert|desserts|menu|entertaining|turkey|stuffing|pie|pies|roast|food'
SHOWS = ['pillsbury bake-off', 'pillsbury bake off', 'frugal gourmet', 'julia child', 'martha stewart', 'yan can cook', 'great chefs', 'graham kerr', 'justin wilson', 'two fat ladies', 'emeril', 'good eats', 'molto mario', 'galloping gourmet', 'jacques pepin', 'jacques pépin', 'nathalie dupree', 'earl peyroux', 'jeff smith', 'paul prudhomme', 'madeleine kamman', 'pierre franey', 'lidia', 'sara moulton', 'master chefs', 'baking with julia', 'dinner at julia', 'butterball', 'ready set cook', 'iron chef', 'food network', 'tv food network', 'cooking with', 'the french chef', 'mr. food', 'mr food', 'ciao italia', 'great british', 'nick stellino', 'everyday cooking', 'wok with yan', 'cajun cooking', 'creative living', 'the victory garden', 'chef paul', 'hot off the grill', 'too hot tamales', 'east meets west', 'essence of emeril', 'how to boil water', 'taste', 'the urban peasant', 'bobby flay', 'barefoot contessa', 'paula', 'rachael ray', '30 minute meals', 'naked chef', 'jamie oliver', 'nigella', 'cooking live', 'food 911', 'grillin', 'country cooking', 'southern cooking', 'baking', 'cookie', 'gingerbread house']
QS = [
    'mediatype:movies AND title:(' + ' OR '.join('"%s"' % w if ' ' in w else w for w in ['christmas', 'xmas', 'holiday', 'holidays', 'thanksgiving', 'gingerbread', 'eggnog', 'yule', 'hanukkah', 'fruitcake']) + ') AND (title:(cooking OR cook OR chef OR kitchen OR recipe OR recipes OR baking OR bake OR "bake-off" OR gourmet OR cookies OR feast OR dinner OR menu OR candy OR desserts OR turkey) OR subject:(cooking OR cookery OR recipes OR baking OR food))',
    'mediatype:movies AND subject:(cooking OR "cooking show" OR cookery OR "cooking shows") AND (title:(christmas OR holiday OR thanksgiving OR xmas OR turkey OR cookies) OR description:(christmas OR thanksgiving OR "holiday"))',
    'mediatype:movies AND title:("pillsbury bake-off" OR "pillsbury bake off" OR "bake-off" OR "cook-off" OR "cooking contest" OR "baking contest" OR "recipe contest" OR "chili cook-off")',
] + ['mediatype:movies AND title:("%s") AND (title:(christmas OR holiday OR thanksgiving OR xmas OR turkey OR cookies OR "new year") OR description:(christmas OR thanksgiving OR "holiday"))' % s for s in ['frugal gourmet', 'julia child', 'martha stewart', 'yan can cook', 'great chefs', 'graham kerr', 'justin wilson', 'two fat ladies', 'emeril', 'good eats', 'molto mario', 'galloping gourmet', 'jacques pepin', 'nathalie dupree', 'earl peyroux', 'paul prudhomme', 'ciao italia', 'mr. food', 'food network', 'baking with julia', 'cooking with master chefs', 'butterball', 'iron chef', 'ready set cook', 'cooking live', 'too hot tamales', 'great british']]
X_FOR = r'\b(castellano|espa[nñ]ol|latino|doblaje|dublado|legendado|portugu[eê]s|brasil|deutsch|fran[cç]ais|vostfr|italiano|nederlands|svenska|norsk|dansk|suomi|polski|русск|日本|中文|한국|türk|magyar|ceske|česk|hrvat|srpsk|ελλην|arab|hindi|tamil|telugu|urdu|tagalog|filipino|indonesia|malay|thai|vietnam)'
X_JUNK = r'\b(video ?game|gameplay|longplay|walkthrough|let\'?s play|minecraft|roblox|fortnite|sims|animal crossing|asmr|mukbang|reaction|unboxing|haul|vlog|podcast|audiobook|radio show|old time radio|otr|music video|lyric|karaoke|cover song|soundtrack|movie trailer|trailer|teaser|full movie|feature film|commercial compilation only|stop motion|lego|toy review|cartoon|animated|anime|sermon|church service|webinar|zoom|lecture|class \d|tutorial|how to make|diy|ai generated|upscaled)\b'
X_MOD = r'(?<!\d)(20(0[5-9]|[1-3]\d))(?!\d)|\b(youtube|tiktok|instagram|netflix|hulu|disney\+|streaming|livestream|twitch)\b'
def yr(x):
    for f in ('date', 'year'):
        m = re.match(r'(\d{4})', str(x.get(f) or ''))
        if m: return int(m.group(1)), str(x.get(f))
    return 0, ''
def tyr(t):
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', t)
    return int(m.group(1)) if m else 0
def tdate(t):
    m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](19[89]\d|200[0-4]|[89]\d)(?!\d)', t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3)); y = y if y > 1900 else 1900 + y
        if 1 <= a <= 12 and 1 <= b <= 31: return '%04d-%02d-%02d' % (y, a, b)
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])[-.](\d{2})[-.](\d{2})(?!\d)', t)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%s-%s' % m.groups()
    return ''
def flat(v): return ' '.join(v) if isinstance(v, list) else str(v or '')
def dur(v):
    try:
        if ':' in str(v):
            s = 0
            for p in str(v).split(':'): s = s * 60 + float(p)
            return s
        return float(v)
    except Exception: return 0
def files(i):
    m = get('https://archive.org/metadata/' + urllib.parse.quote(i, safe=''))
    if not m: return []
    fs = m.get('files') or []; out = []
    names = set(f.get('name') for f in fs)
    for f in fs:
        n = f.get('name') or ''; fmt = str(f.get('format') or '')
        if not re.search(r'\.mp4$', n, re.I) or re.search(r'(?i)sample|trailer|\bpreview\b', n): continue
        if not n.endswith('.ia.mp4') and n.rsplit('.', 1)[0] + '.ia.mp4' in names and 'h.264' not in fmt.lower(): continue
        d = dur(f.get('length'))
        if 480 <= d <= 7800: out.append([n, int(d), fmt])
    ia = [x for x in out if x[0].endswith('.ia.mp4')]
    orig = [x for x in out if not x[0].endswith('.ia.mp4')]
    keep = {x[0].rsplit('.ia.mp4', 1)[0] for x in ia}
    out = [x for x in orig if x[0].rsplit('.', 1)[0] not in keep or 'h.264' in x[2].lower()] + [x for x in ia if not any(o[0].rsplit('.', 1)[0] == x[0].rsplit('.ia.mp4', 1)[0] and 'h.264' in o[2].lower() for o in orig)]
    return sorted(out)[:40]
def ktitle(t):
    s = re.sub(r'(?i)\b(vhs|betamax|beta|dvd|tv|recording|rip|full episode|episode|ep\.?|complete|broadcast|aired|original airing|with commercials|w/ ?commercials|commercials)\b', ' ', t)
    s = re.sub(r'(?<!\d)(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|19[89]\d|200[0-4])(?!\d)', ' ', s)
    s = re.sub(r'[_\[\]\(\)]+', ' ', s); s = re.sub(r'\s*[-:|,]+\s*$', '', re.sub(r'\s+', ' ', s)).strip(' -:|,.')
    return s.upper()[:70]
def main():
    seen = {}
    for q in QS:
        r = scrape(q); print(len(r), q[:110], flush=True)
        for x in r: seen.setdefault(x['identifier'], x)
    cand = []
    for i, x in seen.items():
        t = flat(x.get('title')); low = (t + ' ').lower(); ds = flat(x.get('description'))[:1500]; sj = flat(x.get('subject')).lower(); lang = flat(x.get('language')).lower()
        if re.search(X_FOR, low + ' ' + lang) or (lang and not re.search(r'eng|en\b|english', lang)): continue
        if re.search(X_JUNK, low) or re.search(X_MOD, low): continue
        y, d0 = yr(x); ty = tyr(t)
        Y = ty or (y if 1984 <= y <= 2004 else 0)
        if not Y: continue
        named = any(s in low for s in SHOWS)
        hol_t = re.search(HOL, low); hol_d = re.search(HOL, ds.lower())
        cook_t = re.search(r'\b(' + COOK + r')', low) or re.search(r'cook|food|recipe|bak', sj)
        contest = re.search(r'bake-?off|cook-?off|cooking contest|baking contest|recipe contest', low)
        if not ((hol_t and (cook_t or named)) or (named and hol_d and cook_t) or contest): continue
        ad = tdate(t) or (d0[:10] if len(d0) >= 10 and d0[:4] == str(Y) else '')
        cand.append({'i': i, 't': t, 'd': d0, 'y': str(x.get('year') or ''), 'c': x.get('collection') if isinstance(x.get('collection'), list) else [x.get('collection')], 's': flat(x.get('subject'))[:300], 'ds': ds[:600], 'dl': x.get('downloads') or 0, 'e': Y, 'ad': ad, 'k': ktitle(t), 'why': 'contest' if contest and not hol_t else 'holiday'})
    print('candidates', len(cand), flush=True)
    with ThreadPoolExecutor(12) as ex:
        fl = list(ex.map(lambda c: files(c['i']), cand))
    out = []
    for c, f in zip(cand, fl):
        if f: c['f'] = f; out.append(c)
    out.sort(key=lambda c: (c['e'], c['t']))
    json.dump(out, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False)
    print('kept', len(out))
    for c in out: print(c['e'], c['ad'] or '-', c['why'], '|', c['t'][:90], '|', len(c['f']), 'files', sum(x[1] for x in c['f']) // 60, 'min', flush=True)
main()
