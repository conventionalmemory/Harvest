import csv, gzip, io, json, os, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'weather.json.gz')
UA = {'User-Agent': 'Mozilla/5.0 (retrotv weather)'}
USAF, WBAN, GHCN = os.environ.get('USAF', '725430'), os.environ.get('WBAN', '94822'), os.environ.get('GHCN', 'USW00094822')
Y0, Y1 = int(os.environ.get('Y0', '1983')), int(os.environ.get('Y1', '2005'))
def get(u, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r: return r.read()
        except Exception as e:
            print('retry', u, e, flush=True); time.sleep(3 + k * 5)
    return None
hist = get('https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv')
if hist:
    for row in csv.reader(io.StringIO(hist.decode('latin-1'))):
        if len(row) > 2 and row[0] == USAF and row[1] == WBAN: print('station', row, flush=True)
H = {}
for y in range(Y0, Y1 + 1):
    b = get('https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/%d/%s-%s-%d.gz' % (y, USAF, WBAN, y))
    if not b: print('no hourly', y, flush=True); continue
    rows = []
    for ln in gzip.decompress(b).decode('latin-1').splitlines():
        p = ln.split()
        if len(p) < 12: continue
        v = [int(x) for x in p[:12]]
        rows.append([v[1] * 10000 + v[2] * 100 + v[3]] + v[4:11])
    H[str(y)] = rows
    print('hourly', y, len(rows), flush=True)
D = {}
b = get('https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/%s.csv' % GHCN)
if b:
    rd = csv.DictReader(io.StringIO(b.decode('latin-1')))
    keep = ['TMAX', 'TMIN', 'PRCP', 'SNOW', 'SNWD', 'AWND', 'WSF2', 'WT01', 'WT03', 'WT04', 'WT05', 'WT06', 'WT08', 'WT09', 'WT11', 'WT16', 'WT18']
    for r in rd:
        d = r.get('DATE', '')
        if not d or not (str(Y0) <= d[:4] <= str(Y1)): continue
        o = {}
        for k in keep:
            x = (r.get(k) or '').strip()
            if x != '':
                try: o[k] = int(float(x))
                except Exception: pass
        D[d] = o
    print('daily', len(D), flush=True)
json.dump({'st': [USAF, WBAN, GHCN], 'h': H, 'd': D}, gzip.open(OUT, 'wt', encoding='utf-8'), separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT), flush=True)
if not H or not D: sys.exit(1)
