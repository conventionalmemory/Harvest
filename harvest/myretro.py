import gzip, json, os, random, re, sys, threading, time, collections, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'parts')
os.makedirs(PARTS, exist_ok=True)
SITES = [s for s in os.environ.get('SITES', '90s').split(',') if s]
SHARD, SHARDS = int(os.environ.get('SHARD', '0')), int(os.environ.get('SHARDS', '1'))
THREADS = int(os.environ.get('THREADS', '6'))
BUDGET = float(os.environ.get('BUDGET_MIN', '100')) * 60
T0 = time.time()
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
CTX = {'client': {'clientName': 'WEB', 'clientVersion': '2.20240620.05.00', 'hl': 'en', 'gl': 'US'}}
LOCK = threading.Lock()
ST = collections.Counter()
BASE = {'80s': 1980, '90s': 1990, '00s': 2000}


def h(s):
    v = 7
    for ch in s:
        v = (v * 31 + ord(ch)) & 0xffffffff
    return v


def left():
    return BUDGET - (time.time() - T0)


def http(url, data=None, headers=None, tries=4, timeout=25):
    hd = {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}
    if headers:
        hd.update(headers)
    last = 0
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hd), timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code in (400, 401, 403, 404):
                return e.code, b''
            time.sleep(2 + a * 4 + random.random() * 3)
        except Exception:
            time.sleep(1.5 + a * 3 + random.random() * 2)
    return last, b''


def lineup(site):
    st, raw = http('https://%s.myretrotvs.com/d.json' % site, tries=5, timeout=60)
    if st != 200:
        print('lineup', site, st, flush=True)
        return []
    j = json.loads(raw)
    out = []
    for u, s in enumerate(j.get('x') or []):
        for i in range(0, len(s), 12):
            r = s[i:i + 12]
            if len(r) == 12:
                c = r[-1]
                out.append((r[:11], c.lower(), BASE[site] + u, 1 if c == c.lower() else 0, site))
    return out


def player(vid):
    b = {'videoId': vid, 'context': CTX}
    st, raw = http('https://www.youtube.com/youtubei/v1/player?prettyPrint=false', json.dumps(b).encode(), {'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com', 'X-YouTube-Client-Name': '1', 'X-YouTube-Client-Version': CTX['client']['clientVersion']})
    with LOCK: ST['player_%s' % st] += 1
    if st != 200:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def oembed(vid):
    st, raw = http('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote('https://www.youtube.com/watch?v=' + vid, safe=''), tries=3, timeout=15)
    with LOCK: ST['oembed_%s' % st] += 1
    if st != 200:
        return st, None
    try:
        return st, json.loads(raw)
    except Exception:
        return st, None


def one(rec):
    vid, cat, year, grp, site = rec
    if left() < 90:
        return None
    r = {'v': vid, 'c': cat, 'y': year, 'g': grp, 's': site}
    d = player(vid)
    vd = (d or {}).get('videoDetails') or {}
    ps = (d or {}).get('playabilityStatus') or {}
    mf = ((d or {}).get('microformat') or {}).get('playerMicroformatRenderer') or {}
    if vd.get('title'):
        r['t'] = vd.get('title', '')[:200]
        r['ch'] = vd.get('author', '')[:80]
        r['d'] = int(vd.get('lengthSeconds') or 0)
        r['ds'] = (vd.get('shortDescription') or '')[:300]
        r['vw'] = int(vd.get('viewCount') or 0)
        r['st'] = ps.get('status', '')
        r['em'] = 1 if ps.get('playableInEmbed') else 0
        r['up'] = (mf.get('uploadDate') or mf.get('publishDate') or '')[:10]
        ac = mf.get('availableCountries')
        if ac is not None:
            r['us'] = 1 if 'US' in ac else 0
        with LOCK: ST['full'] += 1
        return r
    oc, oe = oembed(vid)
    r['oe'] = oc
    if oe:
        r['t'] = str(oe.get('title') or '')[:200]
        r['ch'] = str(oe.get('author_name') or '')[:80]
        r['st'] = ps.get('status', '') or 'OK'
        r['em'] = 1
        with LOCK: ST['title_only'] += 1
    else:
        r['st'] = 'GONE' if oc in (400, 401, 403, 404) else 'UNKNOWN'
        with LOCK: ST['gone' if oc in (400, 401, 403, 404) else 'unknown'] += 1
    return r


def main():
    recs = []
    for s in SITES:
        L = lineup(s)
        print('site', s, 'clips', len(L), flush=True)
        recs += L
    seen = set()
    mine = []
    for r in recs:
        if r[0] in seen:
            continue
        seen.add(r[0])
        if h(r[0]) % SHARDS == SHARD:
            mine.append(r)
    random.seed(SHARD)
    random.shuffle(mine)
    print('shard', SHARD, 'of', SHARDS, 'clips', len(mine), flush=True)
    out = []
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(one, mine)):
            if r:
                out.append(r)
            if n % 1000 == 0:
                print('done', n, dict(ST), round((time.time() - T0) / 60, 1), 'min', flush=True)
    with gzip.open(os.path.join(PARTS, 'myretro-%d.json.gz' % SHARD), 'wt', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('shard done', len(out), 'of', len(mine), dict(ST), round((time.time() - T0) / 60, 1), 'min', flush=True)


if __name__ == '__main__':
    main()
