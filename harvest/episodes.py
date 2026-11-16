import json, gzip, os, re, subprocess, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'run'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '150')) * 60; PAR = int(os.environ.get('PAR', '3')); T0 = time.time()
EF = os.path.join(OUT, 'episodes.json.gz')
done = json.load(gzip.open(EF, 'rt')) if os.path.exists(EF) else {}
def url(i, f): return 'https://archive.org/download/' + urllib.parse.quote(i, safe='') + '/' + '/'.join(urllib.parse.quote(x, safe='') for x in f.split('/'))
RB = re.compile(r'black_start:([\d.]+) black_end:([\d.]+)'); RS = re.compile(r'silence_start: ([\d.]+)'); RE = re.compile(r'silence_end: ([\d.]+)')
NET = ['-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '6', '-rw_timeout', '30000000']
def ff(args, tmo):
    try: return subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'info'] + args, capture_output=True, text=True, timeout=tmo)
    except Exception as e: return None
def probe(row):
    i, f, dur = row[:3]
    if time.time() - T0 > BUDGET: return None
    tmp = '/tmp/ep_%d_%d.mp4' % (SHARD, abs(hash(i + f)) % 10**8)
    try:
        d = subprocess.run(['curl', '-sSL', '--retry', '4', '--max-time', '1500', '-o', tmp, url(i, f)], capture_output=True, text=True)
        if d.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) < 1e6: return [i, f, None, 'download']
        a = ff(['-i', tmp, '-vn', '-af', 'silencedetect=n=-38dB:d=0.35', '-f', 'null', '-'], 900)
        v = ff(['-skip_frame', 'nokey', '-i', tmp, '-an', '-vf', 'scale=96:-2,blackdetect=d=0:pic_th=0.92:pix_th=0.12', '-f', 'null', '-'], 900)
    finally:
        try: os.remove(tmp)
        except Exception: pass
    if a is None and v is None: return [i, f, None, 'ffmpeg']
    ss = [float(x) for x in RS.findall(a.stderr if a else '')]; se = [float(x) for x in RE.findall(a.stderr if a else '')]
    sil = [[round(x, 2), round(y, 2)] for x, y in zip(ss, se)]
    bl = [[round(float(x), 2), round(float(y), 2)] for x, y in RB.findall(v.stderr if v else '')]
    return [i, f, {'s': sil, 'b': bl, 'd': dur}, '']
if MODE == 'run':
    want = json.load(gzip.open(os.path.join(here, 'episodes_want.json.gz'), 'rt'))
    todo = [r for r in want if (r[0] + '|' + r[1]) not in done][SHARD::SHARDS]
    print('shard', SHARD, 'todo', len(todo), flush=True)
    res = {}; n = 0
    with ThreadPoolExecutor(PAR) as ex:
        for r in ex.map(probe, todo):
            if r is None: continue
            n += 1
            if r[2] is not None: res[r[0] + '|' + r[1]] = r[2]
            print(n, r[0][:60], 'ok' if r[2] else r[3], (len(r[2]['s']), len(r[2]['b'])) if r[2] else '', round((time.time() - T0) / 60, 1), 'min', flush=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'episodes-%d.json.gz' % SHARD), 'wt'))
if MODE == 'merge':
    import glob
    for fn in glob.glob(os.path.join(PARTS, '**', 'episodes-*.json.gz'), recursive=True):
        done.update(json.load(gzip.open(fn, 'rt')))
    json.dump(done, gzip.open(EF, 'wt'), separators=(',', ':'))
    print('total', len(done))
