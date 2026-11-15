import json, gzip, math, os, re, subprocess, time, urllib.parse, glob
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'run'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '330')) * 60; PAR = int(os.environ.get('PAR', '8')); T0 = time.time()
LF = os.path.join(OUT, 'loud.json.gz')
done = json.load(gzip.open(LF, 'rt')) if os.path.exists(LF) else {}
RL = re.compile(r'I:\s+(-?[\d.]+) LUFS'); RP = re.compile(r'Peak:\s+(-?[\d.]+|-inf) dBFS')
def url(i, f): return 'https://archive.org/download/' + urllib.parse.quote(i, safe='') + '/' + '/'.join(urllib.parse.quote(x, safe='') for x in f.split('/'))
def meas(u, ss=None, t=None):
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'info', '-reconnect', '1', '-reconnect_delay_max', '5', '-rw_timeout', '25000000']
    if ss is not None: cmd += ['-ss', '%.1f' % ss, '-t', '%.1f' % t]
    cmd += ['-i', u, '-vn', '-sn', '-dn', '-af', 'ebur128=framelog=verbose:peak=sample', '-f', 'null', '-']
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=150 if ss is not None else 300)
    except Exception:
        return None
    li = RL.findall(p.stderr); pk = RP.findall(p.stderr)
    if not li: return None
    return float(li[-1]), (float(pk[-1]) if pk and pk[-1] != '-inf' else None)
def probe(row):
    i, f, dur = row
    if time.time() - T0 > BUDGET: return None
    u = url(i, f)
    if dur <= 420: W = [meas(u)]
    else: W = [meas(u, dur * x, 30) for x in (0.3, 0.7)]
    W = [w for w in W if w and w[0] > -70]
    if not W: return [i, f, None]
    e = sum(10 ** (w[0] / 10) for w in W) / len(W)
    o = {'l': round(10 * math.log10(e), 1)}
    P = [w[1] for w in W if w[1] is not None]
    if P: o['p'] = round(max(P), 1)
    return [i, f, o]
if MODE == 'run':
    want = json.load(gzip.open(os.path.join(here, 'loud_want.json.gz'), 'rt'))
    todo = [r for r in want if (r[0] + '|' + r[1]) not in done][SHARD::SHARDS]
    print('shard', SHARD, 'todo', len(todo), 'done before', len(done), flush=True)
    res = {}; n = ok = 0
    with ThreadPoolExecutor(PAR) as ex:
        for r in ex.map(probe, todo):
            if r is None: continue
            n += 1
            if r[2] is not None: res[r[0] + '|' + r[1]] = r[2]; ok += 1
            if n % 100 == 0: print(n, 'measured', ok, 'ok', round((time.time() - T0) / 60, 1), 'min', flush=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'loud-%d.json.gz' % SHARD), 'wt'))
    print('shard done', n, ok, flush=True)
if MODE == 'merge':
    for fn in glob.glob(os.path.join(PARTS, '**', 'loud-*.json.gz'), recursive=True):
        done.update(json.load(gzip.open(fn, 'rt')))
    json.dump(done, gzip.open(LF, 'wt'), separators=(',', ':'))
    print('total', len(done))
