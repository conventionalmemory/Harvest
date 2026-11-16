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
def iam(vid):
    j = L.get('https://archive.org/metadata/youtube-' + vid, tries=2)
    if not j or not j.get('files'): return None
    fs = [f for f in j['files'] if str(f.get('name', '')).lower().endswith('.mp4')]
    if not fs: return None
    fs.sort(key=lambda f: (0 if 'h.264' in str(f.get('format', '')).lower() else 1, int(f.get('size') or 0)))
    return ['youtube-' + vid, fs[0]['name']]
def tsegs(vid, dur):
    try: ds = L.Y.describe(vid) or ''
    except Exception: return None
    P = []
    for m in re.finditer(r'(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])', ds):
        t = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        if not P or t > P[-1]: P.append(t)
    if len(P) < 4: return None
    P.append(dur)
    out = []
    for a, b in zip(P, P[1:]):
        if 9.5 <= b - a <= 65: out.append([float(a), float(b - a)])
    return out or None
def yt_url2(vid):
    for cl in ('tv_embedded', 'mweb', 'web_embedded', 'ios', 'android'):
        try:
            p = subprocess.run(['yt-dlp', '-q', '--no-warnings', '--extractor-args', 'youtube:player_client=' + cl, '-f', 'worst[ext=mp4][height>=144]/worst', '-g', 'https://www.youtube.com/watch?v=' + vid], capture_output=True, text=True, timeout=90)
            u = p.stdout.strip().splitlines()
            if u: return u[0]
        except Exception: pass
    return None
if MODE == 'check':
    sh, n = int(os.environ['SHARD']), int(os.environ['SHARDS'])
    rows = json.load(gzip.open(SRC, 'rt', encoding='utf-8'))['rows']
    todo = [x for x in rows if want(x)]
    todo = [x for i, x in enumerate(todo) if i % n == sh]
    out = {}
    for x in todo:
        if L.left() < 300: break
        if x['src'] == 'yt':
            mir = iam(x['i'])
            u = None
            if mir: u = 'https://archive.org/download/' + urllib.parse.quote(mir[0]) + '/' + '/'.join(urllib.parse.quote(p) for p in mir[1].split('/'))
            if not u: u = yt_url2(x['i'])
            if not u:
                ts = tsegs(x['i'], x.get('d') or 0)
                out['yt:' + x['i']] = {'seg': ts, 'iam': None, 'ts': 1} if ts else None
                print('nourl', x['i'], 'timestamps', len(ts or []), flush=True); continue
            pts = L.cuts(u, x['d'])
            out['yt:' + x['i']] = None if pts is None else {'seg': L.segs(pts, x['d']), 'iam': mir}
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
                elif isinstance(got[k], dict):
                    x['seg'] = got[k]['seg']; n += 1
                    if got[k].get('iam'): x['iam'] = got[k]['iam']
                else: x['seg'] = got[k]; n += 1
        else:
            for f in x['f']:
                k = 'ia:' + x['i'] + '|' + f[0]
                if k in got and got[k] is not None:
                    while len(f) < 3: f.append([])
                    f[2] = got[k]; n += 1
    json.dump(rows_doc, gzip.open(SRC, 'wt', encoding='utf-8'))
    print('merged', n, len(got))
