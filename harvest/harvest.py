import json, gzip, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
BASE = 'mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
NOT = ' AND NOT title:("opening to" OR "closing to" OR "opening and closing" OR mock OR trailer OR "vhs opening" OR "dvd opening" OR "promo reel")'
here = os.path.dirname(os.path.abspath(__file__))
QFILES = os.environ.get('QFILES', 'queries.txt').split(',')
QUERIES = [l.strip() for qf in QFILES for l in open(os.path.join(here, qf)) if l.strip() and not l.startswith('#')]
OUT = os.path.join(here, '..', 'catalog')
os.makedirs(OUT, exist_ok=True)
LIMIT = int(os.environ.get('LIMIT', '14000'))
THREADS = int(os.environ.get('THREADS', '10'))
RAWF = os.path.join(OUT, 'raw.json.gz')
old = json.load(gzip.open(RAWF, 'rt', encoding='utf-8')) if os.path.exists(RAWF) else []
have = set(x['i'] for x in old)
print('existing', len(old), flush=True)

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
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,collection,downloads', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor: break
    return out

MODE = os.environ.get('MODE', 'all')
SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '0')) * 60
T0 = time.time()
seen = {}
if MODE == 'meta':
    QUERIES = []
    for x in json.load(gzip.open(os.path.join(here, '..', 'parts', 'cands.json.gz'), 'rt', encoding='utf-8')): seen[x['identifier']] = x
for q in QUERIES:
    tag, expr = q.split('|', 1)
    items = scrape('(' + expr + ') AND ' + BASE + NOT)
    for it in items:
        i = it['identifier']
        if i not in seen and i not in have:
            it['q'] = tag
            seen[i] = it
    print(tag, len(items), 'total', len(seen), flush=True)

SKIP = '|'.join(['(?:' + p + ')' for p in [r"\b(opening to|closing to|opening and closing|trailers?|teasers?|bumpers?|promo reel|home movies?|camcorder|family video|wedding|funeral|sermon|lecture|conference|seminar|webinar|instructional|workout|aerobics|karaoke|mock|fan ?made|fanmade|reupload|longplay|gameplay|playthrough|speedrun|walkthrough|let's play|unboxing|review of|reaction|podcast|audiobook|slideshow|screensaver|test pattern only|ident|idents|logos?|intros?|outros?|theme songs?|credits only|blooper reel|remaster(ed)?|fan remaster|restored|restoration|upscaled?|ai enhanced|colorized|storybook|making of|behind the scenes|sing along|singalong)\b", r"(castellano|español|espanol|deutsch|français|francais|italiano|português|portugues|nederlands|svenska|suomi|mainoks|русск|日本|telenovela|doblaje|dublado|latino|brasil|globo|\brai\b|\bzdf\b|\bard\b|\bbbc\b|\bitv\b|\bcbc\b|\bctv\b|\btvo\b|australia|tvnz|\btf1\b|antenne|\bbritish\b|\(uk\)|\buk\b|canad|bulgar|polsk|czech|magyar|türk|greek|hindi|tamil|korea|chinese|mandarin|cantonese|tagalog|filipino|japan|anime|mexic|argentin|chile|venezuel|colombia|perú|\bperu\b|german|france|italy|italian|spain|spanish|dutch|holland|sweden|swedish|norw|denmark|danish|finland|finnish|russia|poland|hungar|portugal|brazil|india\b|china|philippin|europe|\bnhk\b|\bsbs\b|\by los\b|\bdel universo|\bcap[ií]tulo|\bepisodio|\btemporada|\bla serie\b|\bdoblado|\bversi[oó]n|januari|februari|maart|augustus|\bmei\b|\bjuni\b|\bjuli\b)", r"\b(nfl|nba|mlb|nhl|super bowl|world series|olympics?|ncaa|football|baseball|basketball|hockey|soccer|fifa|nascar|indy ?500|golf|tennis|stanley cup|playoffs?|bowl game)\b", r"\b(xxx|porn|nude|nudity|erotic|playboy|sex|strip|stripper|fetish|hentai)\b", r"\b(commercials? (compilation|block|break)s?|tv commercials|vintage commercials|commercial compilation|ads from|commercials from|commercials of|commercials \d|\d+ commercials|commercial breaks?)\b|^commercials\b", r"\b(700 club|praise the lord|\btbn\b|c-span|cspan|qvc|home shopping|infomercial|paid program|church|mass\b|telethon)\b"]])
def pri(x):
    q = x['q']
    if q.startswith('col_'): return 2
    if q.startswith('yr'): return 3
    return 1
cands = [x for x in seen.values() if not re.search(SKIP, (str(x.get('title') or '') + ' ').lower())]
print('after title filter', len(cands), 'of', len(seen), flush=True)
cands.sort(key=lambda x: (pri(x), -(x.get('downloads') or 0)))
cands = cands[:LIMIT]
print('candidates', len(cands), flush=True)
if MODE == 'plan':
    PF = os.path.join(here, '..', 'parts'); os.makedirs(PF, exist_ok=True)
    with gzip.open(os.path.join(PF, 'cands.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(cands, f, ensure_ascii=False, separators=(',', ':'))
    sys.exit(0)

def secs(v):
    try:
        if ':' in str(v):
            p = [float(x) for x in str(v).split(':')]
            s = 0
            for x in p: s = s * 60 + x
            return s
        return float(v)
    except Exception:
        return 0

RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    vids = [f for f in j['files'] if f.get('name', '').lower().endswith('.mp4')]
    groups = {}
    for f in vids:
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
    if not files: return None
    files.sort(key=lambda f: f[0])
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    return {'i': it['identifier'], 'q': it['q'], 't': str(m.get('title', ''))[:200], 'd': str(m.get('date', '') or ''), 'y': str(m.get('year', '') or ''),
            'c': col[:4], 's': str(subj)[:200], 'ds': ' '.join(str(desc).split())[:400], 'f': files[:60], 'dl': it.get('downloads') or 0}

if MODE == 'meta':
    cands = cands[SHARD::SHARDS]
    print('shard', SHARD, 'of', SHARDS, 'items', len(cands), flush=True)
def meta2(it):
    if BUDGET and time.time() - T0 > BUDGET: return None
    return meta(it)
res = []
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta2, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), round((time.time() - T0) / 60, 1), 'min', flush=True)
if MODE == 'meta':
    PF = os.path.join(here, '..', 'parts'); os.makedirs(PF, exist_ok=True)
    with gzip.open(os.path.join(PF, 'shard-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(res)); sys.exit(0)
with gzip.open(RAWF, 'wt', encoding='utf-8') as f:
    json.dump(old + res, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(res), 'total', len(old) + len(res))
