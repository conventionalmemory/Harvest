import gzip, json, os, re, sys, time, random
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.parse, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import myretro as M

MODE = os.environ.get('MODE', 'plan')
PLAN = os.path.join(M.PARTS, 'sitelists_plan.json')
YT = re.compile(r'^[A-Za-z0-9_-]{11}$')
MTVK = '80s 90s 2000s raps metal 120minutes club jams country soultrain popupvideo vh1smooth trl unplugged 1stday commercials hairmetal grunge newwave motown deathrow defjam tommyboy springbreak liveaid amp mtv2 fuse sixtysongs90s animated familyfriendly markgoodman makingthevideo disco funk yachtrock britpop'.split()
CHANNELS = {'fuzzy': 'UC-ssAZ6qVu0glgFUIsC8VSA'}


def jget(url):
    st, raw = M.http(url, tries=5, timeout=60)
    if st != 200:
        print('fetch', url, st, flush=True)
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode('utf-8', 'replace')


def mtvrewind():
    out = []
    j = jget('https://wantmymtv.org/public/mtv-playlists.json') or {}
    for k in MTVK:
        for v in j.get(k) or []:
            if isinstance(v, str) and YT.match(v):
                out.append((v, 'mtv:' + k, 0))
    tm = jget('https://wantmymtv.org/public/time-machine.json?v=1') or {}
    for y, L in tm.items():
        if y.isdigit() and 1984 <= int(y) <= 2004:
            for v in L or []:
                if isinstance(v, str) and YT.match(v):
                    out.append((v, 'mtv:year', int(y)))
    print('mtvrewind', len(out), flush=True)
    return out


def crttv():
    s = jget('https://arcade.pirillo.com/crt-tv.html') or ''
    if not isinstance(s, str):
        return []
    i = s.find('const POOL=[')
    body = s[i:s.find('];', i)] if i >= 0 else ''
    out = [(v, 'crt:adcomp', 0) for v in re.findall(r"'([A-Za-z0-9_-]{11})'", body)]
    print('crttv', len(out), flush=True)
    return out


def browse(name, chid, maxpages=600):
    def walk(o, key, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    acc.append(v)
                else:
                    walk(v, key, acc)
        elif isinstance(o, list):
            for v in o:
                walk(v, key, acc)
        return acc
    def inner(body):
        b = dict(body)
        b['context'] = M.CTX
        st, raw = M.http('https://www.youtube.com/youtubei/v1/browse?prettyPrint=false', json.dumps(b).encode(), {'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com', 'X-YouTube-Client-Name': '1', 'X-YouTube-Client-Version': M.CTX['client']['clientVersion']})
        if st != 200:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
    out, seen = [], set()
    d = inner({'browseId': chid, 'params': 'EgZ2aWRlb3PyBgQKAjoA'})
    for _ in range(maxpages):
        if not d:
            break
        got = 0
        for v in walk(d, 'videoRenderer', []):
            vid = v.get('videoId')
            if vid and vid not in seen:
                seen.add(vid); out.append((vid, 'yt:' + name, 0)); got += 1
        for v in walk(d, 'lockupViewModel', []):
            vid = v.get('contentId')
            if vid and YT.match(vid) and vid not in seen:
                seen.add(vid); out.append((vid, 'yt:' + name, 0)); got += 1
        tk = [c.get('token') for c in walk(d, 'continuationCommand', []) if c.get('token')]
        if not tk or not got:
            break
        time.sleep(0.4 + random.random() * 0.6)
        d = inner({'continuation': tk[-1]})
    print('channel', name, len(out), flush=True)
    return out


def plan():
    recs = mtvrewind() + crttv()
    for n, ch in CHANNELS.items():
        recs += browse(n, ch)
    best = {}
    for v, c, y in recs:
        if v not in best or (y and not best[v][1]):
            best[v] = (c, y)
    out = [[v, c, y] for v, (c, y) in best.items()]
    json.dump(out, open(PLAN, 'w'))
    print('plan', len(out), flush=True)


MBUA = 'ConventionalMemoryRetroTV/1.0 ( https://github.com/conventionalmemory/Harvest )'
MBLAST = [0.0]
DEC = {'80s': (1980, 1989), '90s': (1990, 1999), '2000s': (2000, 2009)}


def mbget(url):
    w = 1.1 - (time.time() - MBLAST[0])
    if w > 0:
        time.sleep(w)
    MBLAST[0] = time.time()
    for k in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': MBUA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as f:
                return json.loads(f.read())
        except urllib.error.HTTPError as e:
            if e.code == 503:
                time.sleep(3 + 3 * k); MBLAST[0] = time.time(); continue
            return None
        except Exception:
            time.sleep(2)
    return None


def split_title(t, ch):
    t = re.sub(r'\s*[\(\[][^)\]]*(official|video|audio|lyric|hd|hq|remaster|4k|explicit|clean|version|edit|live|visualizer)[^)\]]*[\)\]]', '', t, flags=re.I)
    t = re.sub(r'(?i)\s*(\||//)\s*(official|music video|video|lyrics?|hd|4k|remaster|from |the album|mtv).*$', '', t).strip()
    m = re.match(r'^(.+?)\s+[-\u2013\u2014~:|]\s+(.+)$', t)
    if m:
        a, s = m.group(1), m.group(2)
    else:
        a = re.sub(r'(?i)vevo$|\s*-\s*topic$|official$', '', ch).strip()
        a = re.sub(r'([a-z])([A-Z])', r'\1 \2', a); s = t
    s = re.sub(r'(?i)\s+(ft\.?|feat\.?|featuring)\s+.*$', '', s).strip(' "\'')
    a = re.sub(r'(?i)\s+(ft\.?|feat\.?|featuring|&|and|x|with)\s+.*$', '', a).strip(' "\'')
    return a, s


def songyear(t, ch, c):
    a, s = split_title(t, ch)
    if not a or not s or len(s) > 80:
        return 0
    q = 'recording:"%s" AND artist:"%s"' % (s.replace('"', ''), a.replace('"', ''))
    j = mbget('https://musicbrainz.org/ws/2/recording?fmt=json&limit=15&query=' + urllib.parse.quote(q))
    if not j:
        return 0
    lo, hi = DEC.get(c.split(':', 1)[1], (1950, 2009))
    na = re.sub(r'[^a-z0-9]', '', a.lower())
    ys = []
    for rec in j.get('recordings') or []:
        if int(rec.get('score') or 0) < 85:
            continue
        cr = ' '.join((x.get('name') or '') + ' ' + ((x.get('artist') or {}).get('name') or '') for x in rec.get('artist-credit') or [])
        if na and na[:12] not in re.sub(r'[^a-z0-9]', '', cr.lower()):
            continue
        d = rec.get('first-release-date') or ''
        if re.match(r'^(19|20)\d\d', d):
            ys.append(int(d[:4]))
    ys = [y for y in ys if 1950 <= y <= 2009]
    if not ys:
        return 0
    y = min(ys)
    return y if lo <= y <= hi else 0


def look():
    L = json.load(open(PLAN))
    mine = [(v, c, y, 0, c.split(':')[0]) for v, c, y in L if M.h(v) % M.SHARDS == M.SHARD]
    random.seed(M.SHARD)
    random.shuffle(mine)
    print('shard', M.SHARD, 'of', M.SHARDS, 'clips', len(mine), flush=True)
    out = []
    with ThreadPoolExecutor(M.THREADS) as ex:
        for n, r in enumerate(ex.map(M.one, mine)):
            if r:
                out.append(r)
            if n % 1000 == 0:
                print('done', n, dict(M.ST), round((time.time() - M.T0) / 60, 1), 'min', flush=True)
    mb = [r for r in out if str(r.get('c', '')).startswith('mtv:') and not r.get('y') and r.get('t') and r.get('st') == 'OK']
    print('song years to look up', len(mb), flush=True)
    for n, r in enumerate(mb):
        if M.left() < 240:
            break
        y = songyear(r['t'], r.get('ch') or '', r['c'])
        if y:
            r['y'] = y; r['yb'] = 'mb'
            M.ST['mb_year'] += 1
        else:
            M.ST['mb_none'] += 1
        if n % 500 == 0:
            print('years', n, M.ST['mb_year'], M.ST['mb_none'], round((time.time() - M.T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(M.PARTS, 'sitelists-%d.json.gz' % M.SHARD), 'wt', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(out), 'of', len(mine), dict(M.ST), flush=True)


if __name__ == '__main__':
    {'plan': plan, 'look': look}[MODE]()
