import json, gzip, os, re, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); PARTS = os.path.join(here, '..', 'parts'); os.makedirs(PARTS, exist_ok=True)
MODE = os.environ.get('MODE', 'run'); SHARD = int(os.environ.get('SHARD', '0')); SHARDS = int(os.environ.get('SHARDS', '1'))
BUDGET = float(os.environ.get('BUDGET_MIN', '320')) * 60; PAR = int(os.environ.get('PAR', '3')); T0 = time.time()
BF = os.path.join(OUT, 'breaks.json.gz')
done = json.load(gzip.open(BF, 'rt')) if os.path.exists(BF) else {}
def url(i, f): return 'https://archive.org/download/' + urllib.parse.quote(i, safe='') + '/' + '/'.join(urllib.parse.quote(x, safe='') for x in f.split('/'))
RL = re.compile(r'I:\s+(-?[\d.]+) LUFS'); RP = re.compile(r'Peak:\s+(-?[\d.]+|-inf) dBFS'); RB = re.compile(r'black_start:([\d.]+) black_end:([\d.]+)'); RS = re.compile(r'silence_start: ([\d.]+)'); RE = re.compile(r'silence_end: ([\d.]+)')
def probe(row):
    i, f, dur = row
    if time.time() - T0 > BUDGET: return None
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'info', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '6', '-rw_timeout', '30000000', '-threads', '2', '-i', url(i, f),
           '-vf', 'fps=6,scale=96:-2,blackdetect=d=0.2:pic_th=0.90:pix_th=0.12', '-af', 'silencedetect=n=-42dB:d=0.25,ebur128=framelog=verbose:peak=sample', '-f', 'null', '-']
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max(240, dur * 0.6))
    except Exception as e:
        return [i, f, None, str(e)[:80]]
    err = p.stderr
    bl = [[round(float(a), 2), round(float(b), 2)] for a, b in RB.findall(err)]
    ss = [float(x) for x in RS.findall(err)]; se = [float(x) for x in RE.findall(err)]
    sil = [[round(a, 2), round(b, 2)] for a, b in zip(ss, se)]
    if not bl and p.returncode != 0: return [i, f, None, (err.strip().splitlines() or ['err'])[-1][:80]]
    o = {'b': bl, 's': sil[:400]}
    li = RL.findall(err); pk = RP.findall(err)
    if li and float(li[-1]) > -70: o['l'] = round(float(li[-1]), 1)
    if pk and pk[-1] != '-inf': o['p'] = round(float(pk[-1]), 1)
    return [i, f, o, '']
if MODE == 'run':
    want = json.load(gzip.open(os.path.join(here, 'breaks_want.json.gz'), 'rt'))
    todo = [r for r in want if (r[0] + '|' + r[1]) not in done][SHARD::SHARDS]
    print('shard', SHARD, 'todo', len(todo), 'done before', len(done), flush=True)
    res = {}; n = ok = 0
    with ThreadPoolExecutor(PAR) as ex:
        for r in ex.map(probe, todo):
            if r is None: continue
            n += 1
            if r[2] is not None: res[r[0] + '|' + r[1]] = r[2]; ok += 1
            if n % 25 == 0: print(n, 'probed', ok, 'ok', round((time.time() - T0) / 60, 1), 'min', flush=True)
    json.dump(res, gzip.open(os.path.join(PARTS, 'breaks-%d.json.gz' % SHARD), 'wt'))
    print('shard done', n, ok, flush=True)
if MODE == 'merge':
    import glob
    for fn in glob.glob(os.path.join(PARTS, '**', 'breaks-*.json.gz'), recursive=True):
        done.update(json.load(gzip.open(fn, 'rt')))
    json.dump(done, gzip.open(BF, 'wt'), separators=(',', ':'))
    nb = sum(1 for v in done.values() if v['b'])
    print('total', len(done), 'with black frames', nb)
