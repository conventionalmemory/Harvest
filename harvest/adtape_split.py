import gzip, json, os, re, subprocess, time, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'catalog', 'extra.json.gz'); OUT = os.path.join(ROOT, 'catalog', 'adtapes.json.gz'); PARTS = os.path.join(ROOT, 'parts')
MODE = os.environ.get('MODE', 'check'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '100')) * 60; T0 = time.time()
Q = {'adtape', 'aad', 'vad', 'jad'}
def left(): return BUDGET - (time.time() - T0)
def url(i, f): return 'https://archive.org/download/' + urllib.parse.quote(i, safe='') + '/' + '/'.join(urllib.parse.quote(x, safe='') for x in f.split('/'))
def cuts(u, dur):
    cap = left() - 60
    if cap < 120: return None
    try:
        p = subprocess.run(['ffmpeg', '-nostdin', '-nostats', '-hide_banner', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '6', '-rw_timeout', '30000000', '-t', str(min(dur, 5400)), '-i', u, '-vf', 'scale=160:-2,blackdetect=d=0.08:pix_th=0.12', '-af', 'silencedetect=n=-45dB:d=0.15', '-f', 'null', '-'], capture_output=True, text=True, timeout=min(2400, cap))
    except Exception:
        return None
    if p.returncode != 0 and 'black_start' not in p.stderr and 'silence_start' not in p.stderr: return None
    bl = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', p.stderr)]
    ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', p.stderr)]
    se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', p.stderr)]
    sil = list(zip(ss, se))
    pts = []
    for a, b in bl:
        m = (a + b) / 2
        if any(x - .4 <= m <= y + .4 for x, y in sil) or b - a > .25: pts.append(round(m, 2))
    return pts
def segs(pts, dur):
    P = [0.0] + [p for p in sorted(set(pts)) if 3 < p < dur - 3] + [dur]
    out = []
    for a, b in zip(P, P[1:]):
        L = b - a
        if 9.5 <= L <= 65: out.append([round(a, 2), round(L, 2)])
    return out
def save(res):
    os.makedirs(PARTS, exist_ok=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'adtapes-%d.json.gz' % SHARD), 'wt', encoding='utf-8'))
if MODE == 'check':
    have = json.load(gzip.open(OUT, 'rt', encoding='utf-8')) if os.path.exists(OUT) else {}
    rows = json.load(gzip.open(SRC, 'rt', encoding='utf-8'))
    todo = sorted((x['i'], f[0], f[1]) for x in rows if x.get('q') in Q for f in (x.get('f') or []) if (f[1] or 0) > 75 and (x['i'] + '|' + f[0]) not in have)
    todo = todo[SHARD::SHARDS]
    print('shard', SHARD, 'files', len(todo), 'hours', round(sum(t[2] for t in todo) / 3600, 1), flush=True)
    res = {}; n = 0
    for i, f, d in todo:
        if left() < 180: break
        pts = cuts(url(i, f), d)
        n += 1
        if pts is not None: res[i + '|' + f] = segs(pts, d)
        print(n, i[:50], f[:40], 'spots', len(res.get(i + '|' + f) or []) if pts is not None else 'fail', round((time.time() - T0) / 60, 1), 'min', flush=True)
        if n % 5 == 0: save(res)
    save(res)
    print('shard', SHARD, 'done', n, 'cut', len(res), 'spots', sum(len(v) for v in res.values()), flush=True)
else:
    have = json.load(gzip.open(OUT, 'rt', encoding='utf-8')) if os.path.exists(OUT) else {}
    n = 0
    if os.path.isdir(PARTS):
        for p in sorted(os.listdir(PARTS)):
            if p.startswith('adtapes-') and p.endswith('.json.gz'):
                try: got = json.load(gzip.open(os.path.join(PARTS, p), 'rt', encoding='utf-8'))
                except Exception: continue
                for k, v in got.items():
                    if v is not None: have[k] = v; n += 1
    json.dump(have, gzip.open(OUT, 'wt', encoding='utf-8'), separators=(',', ':'))
    print('merged', n, 'total', len(have), 'spots', sum(len(v) for v in have.values()))
