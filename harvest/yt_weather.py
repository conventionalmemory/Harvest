import gzip, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_events as E
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'catalog', 'yt_weather.json.gz')
BUDGET = float(os.environ.get('BUDGET_MIN', '40')) * 60; T0 = time.time()
KEEP = re.compile(r"(?i)weather channel|\btwc\b|weather ?star|local on the 8'?s|local forecast|weatherscan|storm stories|weather center live|atmospheric|evening edition|first outlook|tropical update")
BAD = re.compile(r"(?i)simulat|emulat|recreat|remake|mock ?up|\bfake\b|parody|ws4kp|ws ?4000\+|weatherstar 4000\+|retrocast|reaction|review|unboxing|music only|music playlist|playlist|soundtrack|\bost\b|\bremix\b|cover\b|tutorial|how to|vs\.? today|then and now|minecraft|roblox|gmod|\bmod\b|blender|\b20(0[5-9]|1\d|2\d)\b")
Y = re.compile(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)')
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
def date_of(t):
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', t)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](19[89]\d|200[0-4]|[89]\d|0[0-4])(?!\d)', t)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        y = int(m.group(3)); y = y + (1900 if y >= 70 else 2000) if y < 100 else y
        return '%d-%02d-%02d' % (y, int(m.group(1)), int(m.group(2)))
    m = Y.search(t)
    return m.group(1) if m else ''
qs = []
for y in range(1984, 2005):
    qs += ['the weather channel %d' % y, 'weather channel %d recording' % y, 'local on the 8s %d' % y, 'twc %d' % y]
    if y >= 1990: qs += ['weatherstar 4000 %d' % y]
qs += ['weather channel 1980s recording', 'weather channel 1990s recording', 'weather channel early 2000s', 'weather channel vhs recording', 'weather channel full hour', 'weather channel hurricane coverage 1990s', 'weather channel blizzard 1996', 'weather channel hurricane andrew 1992', 'weather channel superstorm 1993', 'weather channel hurricane hugo 1989', 'weather channel hurricane floyd 1999', 'weather channel hurricane isabel 2003', 'weather channel 1980s local forecast', 'weatherstar jr local forecast', 'weatherstar xl 1998', 'weather channel storm stories 2003', 'weather channel evening edition', 'weather channel first outlook', 'weather channel atmospheric', 'weather channel tropical update 1990s']
seen = {}
for n, q in enumerate(qs):
    if time.time() - T0 > BUDGET: break
    try: rs = E.search(q, pages=2, long=False)
    except Exception as e: print('fail', q, e, flush=True); continue
    for r in rs:
        t = r.get('t') or ''; d = int(r.get('dur') or 0)
        if not KEEP.search(t) or BAD.search(t) or not (60 <= d <= 14400): continue
        ad = date_of(t)
        if not ad: continue
        x = seen.get(r['vid'])
        if not x: seen[r['vid']] = {'vid': r['vid'], 't': t[:200], 'ch': (r.get('ch') or '')[:80], 'dur': d, 'ad': ad, 'q': q}
    if n % 10 == 0: print(n, q, 'kept', len(seen), flush=True)
L = sorted(seen.values(), key=lambda x: (x['ad'], x['vid']))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(L, gzip.open(OUT, 'wt', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
by = {}
for x in L: by[x['ad'][:4]] = by.get(x['ad'][:4], 0) + 1
print('kept', len(L), 'hours', round(sum(x['dur'] for x in L) / 3600, 1), sorted(by.items()), dict(E.STATS), flush=True)
