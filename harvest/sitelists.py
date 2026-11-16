import gzip, json, os, re, sys, time, random
from concurrent.futures import ThreadPoolExecutor
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
    with gzip.open(os.path.join(M.PARTS, 'sitelists-%d.json.gz' % M.SHARD), 'wt', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(out), 'of', len(mine), dict(M.ST), flush=True)


if __name__ == '__main__':
    {'plan': plan, 'look': look}[MODE]()
