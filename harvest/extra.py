import json, gzip, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog', 'extra.json.gz')
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1: print('fail', url[:100], e, flush=True); return None
            time.sleep(3 * (k + 1))
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception: return 0
def y2(y):
    y = int(y)
    return y + (1900 if y >= 70 else 2000) if y < 100 else y
def text_date(s):
    s = s or ''
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])[-./](\d{1,2})[-./](\d{1,2})(?!\d)', s)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31: return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19[89]\d|200[0-4])\b', s)
    if m: return '%s-%02d-%02d' % (m.group(3), MON[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](19[89]\d|200[0-4]|[89]\d|0[0-4])(?!\d)', s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31: return '%d-%02d-%02d' % (y2(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r'(?<!\d)(19[89]\d|200[0-4])(?!\d)', s)
    return m.group(1) if m else ''
def meta(row):
    q, i = row
    j = get('https://archive.org/metadata/' + urllib.parse.quote(i))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': return None
    t = m.get('title', '')
    t = ' '.join(t) if isinstance(t, list) else str(t)
    ds = m.get('description', '')
    ds = re.sub(r'<[^>]+>', ' ', ' '.join(ds) if isinstance(ds, list) else str(ds))
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        groups.setdefault(f.get('original') if f.get('source') == 'derivative' else f['name'], []).append(f)
    files = []
    for g in groups.values():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        du = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if du >= 60: files.append([b['name'], round(du), b.get('format', '')])
    if not files: return None
    files.sort(key=lambda f: f[0])
    md = str(m.get('date') or '')
    d = md[:10] if re.match(r'(19[89]\d|200[0-4])-\d\d-\d\d', md) and md[5:10] != '01-01' else ''
    d = d or text_date(t) or text_date(i.replace('_', ' ')) or text_date(ds[:600]) or (md[:4] if re.match(r'(19[89]\d|200[0-4])', md) else '') or (str(m.get('year')) if str(m.get('year', '')).isdigit() else '')
    col = m.get('collection', [])
    col = [col] if isinstance(col, str) else col
    subj = m.get('subject', '')
    subj = ';'.join(subj) if isinstance(subj, list) else str(subj)
    return {'i': i, 'q': q, 't': t[:200], 'd': d, 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': subj[:200], 'ds': ' '.join(ds.split())[:400], 'f': files[:80], 'dl': 0}
rows = [l.split(None, 1) for l in open(os.path.join(here, 'extra_ids.txt')) if l.strip()]
rows = [(a, b.strip()) for a, b in rows]
with ThreadPoolExecutor(12) as ex: res = [r for r in ex.map(meta, rows) if r]
with gzip.open(OUT, 'wt', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(res), 'of', len(rows))
