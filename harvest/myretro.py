import gzip, json, os, random, re, sys, threading, time, collections, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import yt_health as Y

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
YMIN, YMAX = int(os.environ.get('YMIN', '1984')), int(os.environ.get('YMAX', '2004'))


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


def perms(site):
    st, raw = http('https://%s.myretrotvs.com/' % site, tries=4, timeout=60)
    if st != 200:
        return None
    for js in sorted(set(re.findall(r'assets/index-[\w-]+\.js', raw.decode('utf-8', 'replace'))), key=lambda x: 'legacy' in x):
        st2, b = http('https://%s.myretrotvs.com/%s' % (site, js), tries=4, timeout=60)
        if st2 != 200:
            continue
        t = b.decode('utf-8', 'replace')
        cands = re.findall(r'map\(\w=>\w\[\w\]\)\.join\(""\)\}\}\}\((\[\[[\d,\[\]]+\]\])\)', t)
        m = re.search(r'map\(\w=>\w\[\w\]\)\.join\(""\)\}\}\}\(([A-Za-z_$][\w$]*)\)', t)
        if m:
            cands += re.findall(r'(?<![\w$.])' + re.escape(m.group(1)) + r'=(\[\[[\d,\[\]]+\]\])', t)
        for c in cands:
            P = json.loads(c)
            if P and all(sorted(x) == list(range(11)) for x in P):
                return P
    return None


def lineup(site):
    P = perms(site)
    if not P:
        print('lineup', site, 'no decoder', flush=True)
        return []
    st, raw = http('https://%s.myretrotvs.com/d.json' % site, tries=5, timeout=60)
    if st != 200:
        print('lineup', site, st, flush=True)
        return []
    j = json.loads(raw)
    out = []
    for u, s in enumerate(j.get('x') or []):
        for i in range(0, len(s), 12):
            r = s[i:i + 12]
            if len(r) == 12 and YMIN <= BASE[site] + u <= YMAX:
                c = r[-1]; t = r[:11]
                out.append((''.join(t[k] for k in P[sum(map(ord, t)) % len(P)]), c.lower(), BASE[site] + u, 1 if c == c.lower() else 0, site))
    print('lineup', site, len(out), 'decoder', len(P), flush=True)
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
    oc, oe = oembed(vid)
    r['oe'] = oc
    if not oe:
        r['st'] = 'NOEMBED' if oc == 401 else 'GONE' if oc in (400, 403, 404) else 'UNKNOWN'
        r['em'] = 0
        with LOCK: ST['noembed' if oc == 401 else 'gone' if oc in (400, 403, 404) else 'unknown'] += 1
        return r
    r['t'] = str(oe.get('title') or '')[:200]
    r['ch'] = str(oe.get('author_name') or '')[:80]
    code, body, fin = Y.fetch('https://www.youtube.com/embed/' + vid, ref=True)
    e = Y.parse(body) if code == 200 and body else None
    m = re.search(r'\\?"videoDurationSeconds\\?"\s*:\s*\\?"(\d+)', body or '')
    if e:
        r['st'] = e['st']
        r['em'] = 1 if e.get('emb') is not False and e['st'] == 'OK' else 0
        if e.get('why'): r['why'] = e['why'][:120]
    else:
        r['st'] = 'UNKNOWN'; r['em'] = 1
    if m:
        r['d'] = int(m.group(1))
    with LOCK: ST['full' if m and e and e['st'] == 'OK' else 'title_only'] += 1
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
