import gzip, json, os, sys, time, glob, datetime, threading, collections, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WANT = os.path.join(ROOT, 'catalog', 'week_want.json.gz')
OUT = os.path.join(ROOT, 'catalog', 'week_health.json.gz')
PARTS = os.path.join(ROOT, 'parts')
os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'check')
SHARD, SHARDS = int(os.environ.get('SHARD', '0')), int(os.environ.get('SHARDS', '1'))
THREADS = int(os.environ.get('THREADS', '8'))
BUDGET = float(os.environ.get('BUDGET_MIN', '90')) * 60
T0 = time.time()
UA = {'User-Agent': 'Mozilla/5.0 (retrotv weekly check)'}
LOCK = threading.Lock()
ST = collections.Counter()


def h(s):
    v = 7
    for ch in s:
        v = (v * 31 + ord(ch)) & 0xffffffff
    return v


def left():
    return BUDGET - (time.time() - T0)


def meta(i):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request('https://archive.org/metadata/' + urllib.parse.quote(i), headers=UA), timeout=40) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError:
            time.sleep(3 + k * 5)
        except Exception:
            time.sleep(2 + k * 4)
    return None


def fetch_ok(i, f):
    u = 'https://archive.org/download/' + urllib.parse.quote(i) + '/' + '/'.join(urllib.parse.quote(x) for x in f.split('/'))
    for k in range(3):
        try:
            req = urllib.request.Request(u, headers={**UA, 'Range': 'bytes=0-4095'})
            with urllib.request.urlopen(req, timeout=40) as r:
                b = r.read(4096)
                return r.status in (200, 206) and len(b) > 0
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 410):
                return False
            time.sleep(3 + k * 4)
        except Exception:
            time.sleep(2 + k * 3)
    return None


def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'):
                s = s * 60 + float(x)
            return s
        return float(v)
    except Exception:
        return 0


def one_ia(item):
    i, files = item
    if left() < 60:
        return None
    j = meta(i)
    if j is None:
        with LOCK: ST['ia_err'] += 1
        return None
    if not j.get('files') or j.get('is_dark') or str((j.get('metadata') or {}).get('access-restricted-item', '')).lower() == 'true':
        with LOCK: ST['ia_dead'] += 1
        return [i, 'dead', [], {}]
    by = {f.get('name', ''): f for f in j['files']}
    miss, dur = [], {}
    for fn, want_d, where in files:
        f = by.get(fn)
        if not f:
            miss.append(fn)
            continue
        L = secs(f.get('length') or 0)
        if not L and f.get('original'):
            L = secs((by.get(f['original']) or {}).get('length') or 0)
        if L and want_d and abs(L - want_d) > max(90, 0.15 * want_d):
            dur[fn] = round(L)
    present = [x[0] for x in files if x[0] not in miss]
    bad = []
    for fn in present[:2]:
        if fetch_ok(i, fn) is False:
            time.sleep(5)
            if fetch_ok(i, fn) is False:
                bad.append(fn)
    st = 'miss' if (miss or bad) else 'dur' if dur else 'ok'
    with LOCK: ST['ia_' + st] += 1
    return [i, st, miss + bad, dur]


def check():
    W = json.load(gzip.open(WANT, 'rt', encoding='utf-8'))
    ia = sorted((i, fs) for i, fs in W['ia'].items() if h(i) % SHARDS == SHARD)
    yt = sorted(v for v in W['yt'] if h(v) % SHARDS == SHARD)
    print('shard', SHARD, 'archive items', len(ia), 'youtube', len(yt), flush=True)
    res = {'ia': {}, 'yt': {}}
    with ThreadPoolExecutor(THREADS) as ex:
        for n, r in enumerate(ex.map(one_ia, ia)):
            if r:
                res['ia'][r[0]] = r[1:]
            if n % 500 == 0:
                print('archive', n, dict(ST), round((time.time() - T0) / 60, 1), 'min', flush=True)
    if yt and left() > 120:
        import yt_health as Y
        Y.BUDGET = left()
        Y.T0 = time.time()
        try:
            usable = Y.setup()
        except Exception as e:
            usable = False
            print('youtube setup', type(e).__name__, e, flush=True)
        if not usable:
            yt = []
        def one_yt(v):
            if left() < 60:
                return None
            obs = [Y.observe(v)]
            if obs[0]['s'] != 'ok':
                obs.append(Y.observe(v))
            s = Y.settle(obs) or obs[-1]
            return v, [s['s'], s['r'][:160]]
        with ThreadPoolExecutor(3) as ex:
            for r in ex.map(one_yt, yt):
                if r:
                    res['yt'][r[0]] = r[1]
                    with LOCK: ST['yt_' + r[1][0]] += 1
    json.dump(res, open(os.path.join(PARTS, 'week_%d.json' % SHARD), 'w'))
    print('done', dict(ST), round((time.time() - T0) / 60, 1), 'min', flush=True)


def merge():
    W = json.load(gzip.open(WANT, 'rt', encoding='utf-8'))
    out = {'checked': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'base': W.get('base'), 'ia': {}, 'yt': {}}
    for p in glob.glob(os.path.join(PARTS, '**', 'week_*.json'), recursive=True):
        r = json.load(open(p))
        out['ia'].update(r.get('ia', {}))
        out['yt'].update(r.get('yt', {}))
    c = collections.Counter(v[0] for v in out['ia'].values())
    y = collections.Counter(v[0] for v in out['yt'].values())
    print('archive', dict(c), 'of', len(W['ia']), '| youtube', dict(y), 'of', len(W['yt']))
    for i, v in out['ia'].items():
        if v[0] != 'ok':
            print('  ', v[0].ljust(5), i[:60], v[1][:2], list(v[2].items())[:2], '|', (W['ia'].get(i) or [['', 0, '']])[0][2][:90])
    for k, v in out['yt'].items():
        if v[0] != 'ok':
            print('  ', v[0].ljust(10), k, v[1][:100], '|', (W['yt'].get(k) or [0, ''])[1][:80])
    with gzip.open(OUT, 'wt', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))


if __name__ == '__main__':
    {'check': check, 'merge': merge}[MODE]()
