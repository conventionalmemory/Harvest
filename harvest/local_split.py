import gzip, json, os, re, sys, time, subprocess, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.environ['MODE'] = 'lib'
import local as L
SRC = os.path.join(ROOT, 'catalog', 'local.json.gz')
MODE = os.environ.get('MODE_SPLIT', 'check')
CALL = re.compile(r'(?i)\bW(REX|TVO|IFR|QRF)\b|rockford|loves park|machesney|belvidere|freeport')
SKIP = re.compile(r'(?i)fosgate|dyno|dance team|clock ?tower|knez|abortion|slam dunk|mall\b(?!.*commercial)|as it aired|with commercials|\bnews\b|basketball|rockford files|tv land|edge of night|jennifer slept')
def want(x):
    y = x.get('y') or 0
    if not (1980 <= y <= 2004) or x.get('kind') != 'ad' or not CALL.search(x['t']) or SKIP.search(x['t']): return False
    if x['src'] == 'yt': return (x.get('d') or 0) > 75 and not x.get('seg')
    return any(f[1] > 75 and not (len(f) > 2 and isinstance(f[2], list) and f[2]) for f in x['f'])
if MODE == 'check':
    sh, n = int(os.environ['SHARD']), int(os.environ['SHARDS'])
    rows = json.load(gzip.open(SRC, 'rt', encoding='utf-8'))['rows']
    todo = [x for x in rows if want(x)]
    todo = [x for i, x in enumerate(todo) if i % n == sh]
    out = {}
    for x in todo:
        if L.left() < 300: break
        if x['src'] == 'yt':
            u = L.yt_url(x['i'])
            if not u: out['yt:' + x['i']] = None; print('nourl', x['i'], flush=True); continue
            pts = L.cuts(u, x['d'])
            out['yt:' + x['i']] = None if pts is None else L.segs(pts, x['d'])
        else:
            for f in x['f']:
                if f[1] > 75:
                    u = 'https://archive.org/download/' + urllib.parse.quote(x['i']) + '/' + '/'.join(urllib.parse.quote(p) for p in f[0].split('/'))
                    pts = L.cuts(u, f[1])
                    out['ia:' + x['i'] + '|' + f[0]] = None if pts is None else L.segs(pts, f[1])
        print('done', x['src'], x['i'], flush=True)
    os.makedirs(os.path.join(ROOT, 'parts'), exist_ok=True)
    json.dump(out, gzip.open(os.path.join(ROOT, 'parts', 'lsplit-%d.json.gz' % sh), 'wt', encoding='utf-8'))
    print('shard', sh, len(todo), sum(1 for v in out.values() if v), flush=True)
else:
    rows_doc = json.load(gzip.open(SRC, 'rt', encoding='utf-8'))
    got = {}
    for p in os.listdir(os.path.join(ROOT, 'parts')):
        if p.startswith('lsplit-'): got.update(json.load(gzip.open(os.path.join(ROOT, 'parts', p), 'rt', encoding='utf-8')))
    n = 0
    for x in rows_doc['rows']:
        if x['src'] == 'yt':
            k = 'yt:' + x['i']
            if k in got:
                if got[k] is None: x['nourl'] = 1
                else: x['seg'] = got[k]; n += 1
        else:
            for f in x['f']:
                k = 'ia:' + x['i'] + '|' + f[0]
                if k in got and got[k] is not None:
                    while len(f) < 3: f.append([])
                    f[2] = got[k]; n += 1
    json.dump(rows_doc, gzip.open(SRC, 'wt', encoding='utf-8'))
    print('merged', n, len(got))
