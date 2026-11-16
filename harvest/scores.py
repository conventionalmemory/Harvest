import csv, gzip, io, json, os, sys, urllib.request, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'scores.json.gz')
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
def get(u):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r: return r.read()
        except Exception as e: print('retry', u, e, flush=True)
    return None
rows = []
for y in range(1984, 2005):
    b = get('https://www.retrosheet.org/gamelogs/gl%d.zip' % y)
    if not b: print('no mlb', y, flush=True); continue
    z = zipfile.ZipFile(io.BytesIO(b))
    for name in z.namelist():
        for r in csv.reader(io.TextIOWrapper(z.open(name), encoding='latin-1')):
            try:
                d = r[0]; rows.append(['mlb', '%s-%s-%s' % (d[:4], d[4:6], d[6:8]), r[3], int(r[9]), r[6], int(r[10]), r[12][:1], int(r[18] or 0) if r[18].isdigit() else 0])
            except Exception: pass
    print('mlb', y, len(rows), flush=True)
b = get('https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv')
if b:
    n0 = len(rows)
    for r in csv.DictReader(io.StringIO(b.decode('utf-8'))):
        try:
            s = int(r['season'])
            if s > 2004 or not r['away_score'] or not r['home_score']: continue
            rows.append(['nfl', r['gameday'], r['away_team'], int(float(r['away_score'])), r['home_team'], int(float(r['home_score'])), r.get('gametime', ''), 0])
        except Exception: pass
    print('nfl', len(rows) - n0, flush=True)
json.dump({'rows': rows}, gzip.open(OUT, 'wt', encoding='utf-8'))
print('wrote', len(rows))
