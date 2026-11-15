import gzip, json, os, re, sys, time, random, subprocess, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.environ['MODE_SAVED'] = os.environ.get('MODE', ''); os.environ['MODE'] = 'lib'
import yt_needs as Y
OUT = os.path.join(ROOT, 'catalog', 'local.json.gz')
T0 = time.time(); BUDGET = float(os.environ.get('BUDGET_MIN', '100')) * 60
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
AREA = r"rockford|loves park|machesney|belvidere|freeport|rockton|roscoe|cherry ?vale|cherry valley|winnebago county|boone county|stateline|state line|byron,? il|pecatonica|durand|south beloit|beloit|janesville|dixon,? il|sterling,? il|rochelle|n\.? ?illinois|northern illinois"
AREAX = re.compile(r'(?i)\b(' + AREA + r')\b')
STN = re.compile(r'(?i)\b(wrex|wtvo|wifr|wqrf|wrex-?tv|wtvo-?tv|wifr-?tv|wqrf-?tv|fox ?39|13 ?wrex|17 ?wtvo|23 ?wifr|channel 13 rockford|channel 17 rockford|channel 23 rockford|channel 39 rockford|insight cable rockford|tci cable rockford|cablevision rockford|rockford cable)\b')
LOCX = re.compile(r'(?i)\b(magic waters|cherryvale mall|cherry vale mall|machesney park mall|north towne mall|colonial village mall|edgebrook|clock tower resort|clocktower|rockford icehogs|icehogs|rockford lightning|rockford cubbies|rockford expos|rockford riverhawks|rockford royals|metrocentre|metro centre|coronado theat|time museum|discovery center museum|burpee museum|anderson japanese gardens|sinnissippi|forest city|blackhawk|rock river|alpine bank|amcore|stockholm inn|lino|mary\'?s market|lombardo|beef-?a-?roo|ziggy\'?s|bravo pizza|giovanni|lord stanley|hoffman house|gerry\'?s|pierre|kegel\'?s|rockford dodge|rockford chevrolet|anderson (bmw|toyota|nissan)|bergstrom|sullivan\'?s|schnucks|logli\'?s|eagle food)\b')
ADW = re.compile(r'(?i)\b(commercials?|ads?|adverts?|advertisements?|tv spots?|spots?|promos?|station ids?|ident|sign[- ]?(on|off)|news (open|intro|promo|tease)|bumpers?|jingle)\b')
BADX = re.compile(r'(?i)\b(reaction|review|podcast|documentary|history of|tour|walkthrough|vlog|haul|unboxing|tiktok|shorts|202\d|201\d|200[6-9]|ranking|top \d+|interview|full movie|trailer|radio)\b')
YR = re.compile(r'(?<![\d$#])(19[89]\d|200[0-4])(?!\d)')
def left(): return BUDGET - (time.time() - T0)
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception: time.sleep(2 + k * 3)
    return None
def scrape(q):
    out, cur = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads,description', 'q': q, 'count': 5000, **({'cursor': cur} if cur else {})})
        j = get(u)
        if not j: break
        out += j.get('items', []); cur = j.get('cursor')
        if not cur: break
    return out
def secs(v):
    try:
        if isinstance(v, (int, float)): return float(v)
        if ':' in str(v):
            t = 0
            for x in str(v).split(':'): t = t * 60 + float(x)
            return t
        return float(v)
    except Exception: return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
def year_of(*s):
    for x in s:
        m = YR.search(str(x or ''))
        if m: return int(m.group(1))
    return 0
def ia_meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): return None
    m = j.get('metadata', {})
    title = str(m.get('title', ''))
    desc = m.get('description', ''); desc = ' '.join(desc) if isinstance(desc, list) else str(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', desc).split())[:500]
    lang = m.get('language', ''); lang = ' '.join(lang) if isinstance(lang, list) else str(lang)
    if lang and not re.search(r'eng|english|^en\b', lang.lower()): return None
    files = {}
    for f in j['files']:
        n = f.get('name', '')
        if not n.lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else n
        r = RANK.get(f.get('format', ''), 9)
        if r == 9: continue
        d = secs(f.get('length') or 0)
        if key not in files or r < files[key][2]: files[key] = [n, round(d, 1), r]
    fl = sorted([v[:2] for v in files.values() if v[1] >= 5], key=lambda v: v[0])
    if not fl: return None
    y = year_of(title, m.get('date'), m.get('year'), desc)
    return {'src': 'ia', 'i': it['identifier'], 't': title[:200], 'ds': desc[:300], 'y': y, 'date': str(m.get('date') or '')[:10], 'f': fl}
def search_ia():
    qs = ['(title:(' + ' OR '.join('"%s"' % a for a in ['rockford', 'loves park', 'machesney park', 'belvidere', 'freeport illinois', 'winnebago county', 'rockton', 'roscoe illinois', 'cherryvale']) + ')) AND mediatype:movies',
          'title:(wrex OR wtvo OR wifr OR wqrf OR "fox 39 rockford" OR "13 wrex" OR "17 wtvo" OR "23 wifr") AND mediatype:movies',
          'description:(rockford) AND title:(commercial OR commercials OR ad OR ads OR promo OR promos OR "station id" OR news) AND mediatype:movies']
    seen = {}
    for q in qs:
        for it in scrape(q): seen[it['identifier']] = it
    print('ia candidates', len(seen), flush=True)
    out = []
    with ThreadPoolExecutor(12) as ex:
        for r in ex.map(ia_meta, list(seen.values())):
            if r: out.append(r)
    keep = []
    for r in out:
        blob = r['t'] + ' ' + r['ds']
        if not (AREAX.search(blob) or STN.search(blob) or LOCX.search(blob)): continue
        if r['y'] and not (1980 <= r['y'] <= 2005): continue
        if BADX.search(r['t']): continue
        r['kind'] = 'stn' if STN.search(r['t']) and not ADW.search(r['t']) else 'ad' if ADW.search(r['t']) or all(f[1] <= 125 for f in r['f']) else 'rec'
        keep.append(r)
    print('ia kept', len(keep), flush=True)
    return keep
QY = ['rockford illinois commercial', 'rockford il commercial', 'rockford commercials 80s', 'rockford commercials 90s', 'rockford tv commercials', 'rockford local commercials', 'old rockford commercials', 'rockford commercial 1980s', 'rockford commercial 1990s',
      'wrex commercials', 'wrex 13 rockford', 'wtvo commercials', 'wtvo 17 rockford', 'wifr commercials', 'wifr 23 rockford', 'wqrf fox 39', 'wqrf commercials', 'wrex news open', 'wtvo news open', 'wifr news open', 'rockford station id',
      'magic waters commercial', 'magic waters rockford', 'cherryvale mall commercial', 'machesney park mall commercial', 'north towne mall rockford', 'colonial village mall rockford', 'clock tower resort rockford commercial', 'rockford icehogs commercial', 'rockford lightning cba',
      'rockford cubbies', 'rockford expos baseball', 'rockford metro centre commercial', 'stockholm inn rockford', 'lino rockford commercial', 'beef a roo commercial', 'amcore bank commercial', 'alpine bank rockford commercial', 'logli supermarket commercial', 'eagle food rockford commercial',
      'belvidere illinois commercial', 'freeport illinois commercial', 'loves park commercial', 'beloit wisconsin commercial 80s', 'janesville commercial 80s', 'insight cable rockford', 'rockford cable commercial', 'rockford car dealer commercial', 'rockford furniture commercial 80s', 'rockford illinois 1980s tv']
def search_yt():
    found = {}
    for q in QY:
        if left() < 600: break
        try: res = Y.search(q, pages=2, params='EgIQAQ==')
        except Exception as e: print('search fail', q, e); res = []
        for c in res:
            if c['vid'] in found: continue
            c['q'] = q; found[c['vid']] = c
        time.sleep(0.6 + random.random())
    print('yt candidates', len(found), flush=True)
    keep = []
    for c in found.values():
        t = c['t'] or ''
        if c.get('live') or not (5 <= (c.get('dur') or 0) <= 2400): continue
        if BADX.search(t): continue
        blob = t + ' ' + (c.get('ch') or '')
        if not (AREAX.search(blob) or STN.search(blob) or LOCX.search(blob)): continue
        y = year_of(t)
        if y and not (1980 <= y <= 2005): continue
        if not (ADW.search(t) or STN.search(t) or LOCX.search(t) or YR.search(t)): continue
        keep.append({'src': 'yt', 'i': c['vid'], 't': t[:200], 'ch': c.get('ch', '')[:60], 'y': y, 'd': c['dur'], 'views': c.get('views', 0), 'kind': 'stn' if STN.search(t) and not ADW.search(t) else 'ad'})
    for k in keep:
        if left() < 300: break
        try: k['ds'] = (Y.describe(k['i']) or '')[:400]
        except Exception: k['ds'] = ''
        if not k['y']: k['y'] = year_of(k['ds'])
        time.sleep(0.3)
    keep = [k for k in keep if not k['y'] or 1980 <= k['y'] <= 2005]
    print('yt kept', len(keep), flush=True)
    return keep
def cuts(url, dur):
    try:
        p = subprocess.run(['ffmpeg', '-nostats', '-hide_banner', '-t', str(min(dur, 2400)), '-i', url, '-vf', 'scale=160:-2,blackdetect=d=0.08:pix_th=0.12', '-af', 'silencedetect=n=-45dB:d=0.15', '-f', 'null', '-'], capture_output=True, text=True, timeout=900)
    except Exception as e: return None
    bl = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', p.stderr)]
    ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', p.stderr)]
    se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', p.stderr)]
    sil = list(zip(ss, se))
    pts = []
    for a, b in bl:
        m = (a + b) / 2
        if any(x - .4 <= m <= y + .4 for x, y in sil) or b - a > .25: pts.append(round(m, 2))
    return pts
def segs(pts, dur):
    P = [0.0] + [p for p in pts if 3 < p < dur - 3] + [dur]
    out = []
    for a, b in zip(P, P[1:]):
        L = b - a
        if 9.5 <= L <= 65: out.append([round(a, 2), round(L, 2)])
    return out
def yt_url(vid):
    try:
        p = subprocess.run(['yt-dlp', '-q', '--no-warnings', '-f', 'worst[ext=mp4][height>=144]/worst', '-g', 'https://www.youtube.com/watch?v=' + vid], capture_output=True, text=True, timeout=90)
        u = p.stdout.strip().splitlines()
        return u[0] if u else None
    except Exception: return None
def split(rows):
    n = 0
    for r in rows:
        if left() < 240: break
        if r['src'] == 'ia':
            for f in r['f']:
                if f[1] > 75 and left() > 240:
                    u = 'https://archive.org/download/' + urllib.parse.quote(r['i']) + '/' + '/'.join(urllib.parse.quote(x) for x in f[0].split('/'))
                    pts = cuts(u, f[1])
                    if pts is not None: f.append(segs(pts, f[1])); n += 1
        elif r['d'] > 75:
            u = yt_url(r['i'])
            if not u: r['nourl'] = 1; continue
            pts = cuts(u, r['d'])
            if pts is not None: r['seg'] = segs(pts, r['d']); n += 1
    print('split', n, flush=True)
if __name__ == '__main__':
    ia = search_ia()
    yt = search_yt()
    rows = ia + yt
    rows.sort(key=lambda r: (r['src'], r['i']))
    split(rows)
    json.dump({'rows': rows}, gzip.open(OUT, 'wt', encoding='utf-8'))
    print('wrote', len(rows), os.path.getsize(OUT), flush=True)
