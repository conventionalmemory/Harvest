import csv, datetime, gzip, io, json, os, re, sys, time, urllib.request
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
def okta(v):
    m = None
    for x in v:
        mm = re.search(r':(\d\d)', x or '')
        if mm: m = max(m or 0, int(mm.group(1)))
    return m if m is not None and m <= 9 else -9999
def num(x, k=10):
    try: return int(round(float(x) * k))
    except Exception: return -9999
for y in range(Y0, Y1 + 1):
    b = get('https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/%d/%s-%s-%d.gz' % (y, USAF, WBAN, y), tries=2)
    if not b or b[:2] != b'\x1f\x8b': break
    rows = []
    for ln in gzip.decompress(b).decode('latin-1').splitlines():
        p = ln.split()
        if len(p) < 12: continue
        v = [int(x) for x in p[:12]]
        rows.append([v[1] * 10000 + v[2] * 100 + v[3]] + v[4:11])
    H[str(y)] = rows
    print('hourly isd', y, len(rows), flush=True)
if not H:
    b = None
    for u in ['https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-station/GHCNh_%s_por.psv' % GHCN]:
        b = get(u, tries=4)
        if b and not b.lstrip().startswith(b'<'): print('ghcnh', u, len(b), flush=True); break
        b = None
    if b:
        lines = b.decode('utf-8', 'replace').splitlines()
        hd = lines[0].split('|'); ix = {k: i for i, k in enumerate(hd)}
        print('cols', [k for k in hd if not k.endswith(('_Measurement_Code', '_Quality_Code', '_Report_Type', '_Source_Code', '_Source_Station_ID'))][:40], flush=True)
        sk = [k for k in hd if re.fullmatch(r'sky_cover_\d', k) or re.fullmatch(r'sky_cover_layer_\d', k)]
        best = {}
        for ln in lines[1:]:
            c = ln.split('|')
            if len(c) < len(hd): continue
            d = c[ix['DATE']]
            yy = int(d[:4])
            if not (Y0 <= yy <= Y1): continue
            mo, dd, hh, mi = int(d[5:7]), int(d[8:10]), int(d[11:13]), int(d[14:16])
            t = datetime.datetime(yy, mo, dd, hh) + datetime.timedelta(hours=1 if mi >= 30 else 0)
            key = (t.year, t.month * 10000 + t.day * 100 + t.hour)
            g = lambda k, m=10: num(c[ix[k]], m) if k in ix else -9999
            row = [key[1], g('temperature'), g('dew_point_temperature'), g('sea_level_pressure'), g('wind_direction', 1), g('wind_speed'), okta([c[ix[k]] for k in sk]), g('precipitation')]
            dist = abs(mi - 52) if mi >= 30 else 60
            o = best.get(key)
            if o is None or dist < o[0] or (row[7] > 0 and (o[1][7] or 0) <= 0): best[key] = (dist, row) if o is None or dist < o[0] else (o[0], o[1][:7] + [row[7]])
        for (yy, k), (_, row) in sorted(best.items()): H.setdefault(str(yy), []).append(row)
        for yy in sorted(H): print('hourly ghcnh', yy, len(H[yy]), flush=True)
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
